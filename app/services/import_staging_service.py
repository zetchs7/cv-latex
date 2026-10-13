"""Staging de la importacion de CV desde PDF.

El staging es una capa **entre el PDF y el modelo persistente**. No es schema 2
y nunca se escribe en la tabla `cvs`. Existe por una razon concreta: el Issue
#14 pide dos secciones visibles —"Campos con dudas" e "Informacion no
clasificada"— que el modelo persistente no puede representar sin ensuciar el CV
final. Mezclar dudas dentro de `additional_info` seria exactamente lo contrario
de lo pedido.

Reglas de este modulo:

- El PDF original **nunca** se guarda. Solo sobrevive el texto ya extraido.
- Los borradores viven en `<data>/import-drafts/`, fuera de cualquier directorio
  publicado, y se borran por antiguedad.
- Los identificadores se generan con `secrets` y se vuelven a validar al
  recuperarlos: un id manipulado no puede escapar del directorio.
- Nada se guarda en `cvs` hasta que la persona confirma de forma explicita, y
  confirmar exige que cada elemento pendiente tenga una decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import secrets

from app.database import ensure_isolated_path, get_data_dir
from app.services.pdf_section_parser import (
    CONFIDENCE_LABELS,
    ParsedCvDocument,
    _LABELLED_VALUE,
)

DRAFTS_DIRECTORY_NAME = "import-drafts"
DRAFT_TTL = timedelta(hours=2)
MAX_DRAFTS = 200
DRAFT_ID_BYTES = 24
DRAFT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,64}$")
MAX_STORED_DRAFT_BYTES = 2 * 1024 * 1024

# El contrato schema 2 se importa UNA vez a nivel de modulo: los limites de
# este servicio se derivan de el, y una segunda tabla a mano se desincroniza.
from app.validations import structured_cv_validations as schema


STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_DISCARDED = "discarded"
STATUS_KEPT = "kept"
DECISION_STATUSES = (STATUS_CONFIRMED, STATUS_DISCARDED, STATUS_KEPT)

# El bloque de tecnologias excedentes NO es una skill mas: vive en su propia
# seccion para que `_collect_items(confirmed, "skills")` no lo convierta en la
# skill 41, que el schema rechaza despues de una revision aparentemente valida.
SKILLS_OVERFLOW_SECTION = "skills_overflow"

# Limites de schema 2, DERIVADOS del contrato real en lugar de copiados a mano.
# La tabla duplicada que habia antes se desincronizo: permitia 30 skills cuando el
# schema admite 40, y rechazaba resumenes de proyecto que si entraban.
def _build_field_limits() -> dict[str, int]:
    from app.validations import structured_cv_validations as schema

    limits: dict[str, int] = {}

    for section, specs in schema.OBJECT_SECTION_SPECS.items():
        for spec in specs:
            limits[f"{section}.{spec.field}"] = spec.max_length

    for section, max_length in schema.STRING_SECTION_SPECS.items():
        limits[section] = max_length

    for section, item_spec in schema.ITEM_SECTION_SPECS.items():
        for spec in item_spec.string_fields:
            limits[f"{section}.{spec.field}"] = spec.max_length

    for section, max_length in schema.STRING_SECTION_SPECS.items():
        limits.setdefault(section, max_length)

    # El titulo del CV no es parte del payload schema 2: es metadato del
    # documento. Se declara aqui, con su motivo, en vez de duplicarlo en otro lado.
    limits["cv_title"] = 120
    limits["additional_info.content"] = schema.ITEM_SECTION_SPECS["additional_info"].string_fields[1].max_length

    return limits


FIELD_LIMITS: dict[str, int] = _build_field_limits()


def _build_list_field_limits() -> dict[str, tuple[int, int]]:
    """(max_items, max_por_elemento) para los campos de lista del schema.

    Sin esto, `experience.highlights` y `experience.technologies` no se validaban
    nunca: una experiencia con 17 tecnologias pasaba la revision y reventaba al
    guardar, lejos del sitio donde la persona podia corregirlo.

    El tope sale de `spec.max_items`, que es el del CAMPO, y no de
    `item_spec.max_items`, que es el de la SECCION que lo contiene. Son distintos:
    `experience` admite 30 items pero `highlights` solo 12 y `technologies` 16.
    Con el tope equivocado, 17 tecnologias pasaban la revision y el schema las
    rechazaba al guardar.
    """

    from app.validations import structured_cv_validations as schema

    result: dict[str, tuple[int, int]] = {}
    for section, item_spec in schema.ITEM_SECTION_SPECS.items():
        for spec in item_spec.string_list_fields:
            result[f"{section}.{spec.field}"] = (spec.max_items, spec.item_max_length)
    return result


LIST_FIELD_LIMITS: dict[str, tuple[int, int]] = _build_list_field_limits()

# Estos dos vivian a mano y el de contenido contradecía al contrato: el schema
# admite 600 caracteres, la constante decia 1000. El derivado de abajo es la
# UNICA fuente; una segunda tabla no puede desincronizarse.
MAX_ADDITIONAL_INFO = schema.ITEM_SECTION_SPECS["additional_info"].max_items
MAX_SKILL_LABEL = next(
    spec.max_length
    for spec in schema.ITEM_SECTION_SPECS["skills"].string_fields
    if spec.field == "label"
)
ADDITIONAL_INFO_CONTENT_LIMIT = FIELD_LIMITS["additional_info.content"]

UNCLASSIFIED_TARGET_SECTIONS = (
    "additional_info",
    "skills",
    "certifications",
    "projects",
)

_LINK_LABELS = (
    ("linkedin.com", "LinkedIn"),
    ("github.com", "GitHub"),
    ("gitlab.com", "GitLab"),
    ("behance.net", "Behance"),
    ("dribbble.com", "Dribbble"),
    ("medium.com", "Medium"),
    ("stackoverflow.com", "Stack Overflow"),
)


class ImportStagingError(Exception):
    """Error de staging con mensaje seguro para la persona que importa."""

    def __init__(self, code: str, user_message: str) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


@dataclass
class StagedEntry:
    key: str
    section: str
    source_text: str
    confidence: str
    reason: str
    status: str = STATUS_PENDING
    value: str = ""
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class UnclassifiedEntry:
    key: str
    text: str
    reason: str
    suggested_section: str = ""
    assigned_section: str = ""
    status: str = STATUS_PENDING


@dataclass
class ImportDraft:
    draft_id: str
    created_at: str
    updated_at: str
    source_filename: str
    page_count: int
    entries: list[StagedEntry] = field(default_factory=list)
    unclassified: list[UnclassifiedEntry] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    version: int = 1
    finalized_cv_id: int | None = None
    # El titulo se guarda en el borrador: sin esto, un error de validacion
    # re-pinta la pantalla y la persona pierde lo que escribio ahi.
    proposed_title: str = ""
    # Bloques conservados que no caben en la seccion elegida y se envian a
    # informacion adicional para no perderlos.
    overflow_unclassified: list[str] = field(default_factory=list)

    def pending_entries(self) -> list[StagedEntry]:
        return [entry for entry in self.entries if entry.status == STATUS_PENDING]

    def pending_unclassified(self) -> list[UnclassifiedEntry]:
        return [item for item in self.unclassified if item.status == STATUS_PENDING]

    def by_section(self) -> dict[str, list[StagedEntry]]:
        grouped: dict[str, list[StagedEntry]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.section, []).append(entry)
        return grouped

    def confidence_label(self, value: str) -> str:
        return CONFIDENCE_LABELS.get(value, value)

    def to_json(self) -> dict:
        return {
            "draft_id": self.draft_id,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_filename": self.source_filename,
            "page_count": self.page_count,
            "entries": [asdict(entry) for entry in self.entries],
            "unclassified": [asdict(item) for item in self.unclassified],
            "conflicts": self.conflicts,
            "finalized_cv_id": self.finalized_cv_id,
            "proposed_title": self.proposed_title,
            "overflow_unclassified": list(self.overflow_unclassified),
        }

    @classmethod
    def from_json(cls, payload: dict) -> "ImportDraft":
        return cls(
            draft_id=payload["draft_id"],
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
            source_filename=payload["source_filename"],
            page_count=int(payload.get("page_count", 0)),
            entries=[StagedEntry(**entry) for entry in payload.get("entries", [])],
            unclassified=[UnclassifiedEntry(**item) for item in payload.get("unclassified", [])],
            conflicts=list(payload.get("conflicts", [])),
            version=int(payload.get("version", 1)),
            finalized_cv_id=payload.get("finalized_cv_id"),
            proposed_title=payload.get("proposed_title", ""),
            overflow_unclassified=list(payload.get("overflow_unclassified", [])),
        )


# --- Directorio de borradores ---------------------------------------------


def drafts_directory() -> Path:
    """Directorio de borradores, con la misma proteccion que los exports."""

    directory = get_data_dir() / DRAFTS_DIRECTORY_NAME
    ensure_isolated_path(directory, "El directorio de borradores de importacion")
    directory.mkdir(parents=True, exist_ok=True)

    # `ensure_isolated_path` no hace nada fuera de una corrida de pruebas, asi
    # que en produccion un `import-drafts` que sea un enlace simbolico se
    # aceptaria en silencio y los borradores se escribirian donde apunte. Un
    # enlace alli no es un caso esperable y si aparece es un montaje incorrecto.
    if directory.is_symlink():
        raise ImportStagingError(
            "drafts_directory_symlinked",
            "El almacenamiento de importaciones no esta disponible. Contacta al administrador.",
        )

    return directory


def _draft_path(draft_id: str) -> Path:
    """Resuelve un id a ruta, rechazando cualquier forma de traversal."""

    if not DRAFT_ID_PATTERN.match(draft_id):
        raise ImportStagingError(
            "draft_invalid_id",
            "El enlace de importacion no es valido. Volve a empezar la importacion.",
        )

    directory = drafts_directory()
    candidate = directory / f"{draft_id}.json"
    resolved = candidate.resolve()

    if resolved.parent != directory.resolve():
        raise ImportStagingError(
            "draft_invalid_id",
            "El enlace de importacion no es valido. Volve a empezar la importacion.",
        )

    return candidate


def _now() -> datetime:
    return datetime.now(UTC)


def purge_expired_drafts(*, now: datetime | None = None) -> int:
    """Borra borradores vencidos. Devuelve cuantos elimino.

    Es idempotente y seguro de llamar en cada acceso: si el directorio no
    existe no hace nada.
    """

    directory = drafts_directory()
    reference = now or _now()
    removed = 0

    # Un reclamo huerfano solo aparece si el proceso muere en el instante exacto
    # entre el reclamo y la escritura. Todo otro camino lo libera. Se limpia por
    # antiguedad: un reclamo vivo dura milisegundos, asi que tocar uno reciente
    # romperia una confirmacion en curso. Sin esa condicion, mis primeras versiones
    # de este bloque borraban todos los reclamos y dejaban via libre al duplicado.
    for claimant in sorted(directory.glob(f"*{DRAFT_CLAIM_SUFFIX}")):
        try:
            claimed_at = datetime.fromtimestamp(claimant.stat().st_mtime, UTC)
        except OSError:
            continue
        if claimed_at < reference - DRAFT_TTL:
            claimant.unlink(missing_ok=True)

    for candidate in sorted(directory.glob("*.json")):
        if not DRAFT_ID_PATTERN.match(candidate.stem):
            candidate.unlink(missing_ok=True)
            removed += 1
            continue

        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            updated_at = datetime.fromisoformat(payload["updated_at"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            candidate.unlink(missing_ok=True)
            removed += 1
            continue

        if reference - updated_at > DRAFT_TTL:
            candidate.unlink(missing_ok=True)
            removed += 1

    _enforce_draft_cap(directory)
    return removed


def _enforce_draft_cap(directory: Path) -> None:
    existing = [candidate for candidate in directory.glob("*.json") if DRAFT_ID_PATTERN.match(candidate.stem)]
    if len(existing) <= MAX_DRAFTS:
        return

    def _age(candidate: Path) -> float:
        try:
            return candidate.stat().st_mtime
        except OSError:
            return 0.0

    for candidate in sorted(existing, key=_age)[: len(existing) - MAX_DRAFTS]:
        candidate.unlink(missing_ok=True)


# --- Ciclo de vida --------------------------------------------------------


def create_draft(parsed: ParsedCvDocument, *, source_filename: str, page_count: int) -> ImportDraft:
    """Convierte el resultado del parser en un borrador revisable."""

    timestamp = _now().isoformat()
    draft = ImportDraft(
        draft_id=secrets.token_urlsafe(DRAFT_ID_BYTES),
        created_at=timestamp,
        updated_at=timestamp,
        source_filename=source_filename[:160],
        page_count=page_count,
    )

    for staged_field in parsed.fields:
        draft.entries.append(
            StagedEntry(
                key=staged_field.key,
                section=staged_field.section,
                value=staged_field.value,
                source_text=staged_field.source_text,
                confidence=staged_field.confidence,
                reason=staged_field.reason,
            )
        )

    for index, staged_item in enumerate(parsed.items):
        draft.entries.append(
            StagedEntry(
                key=f"{staged_item.section}.{index}",
                section=staged_item.section,
                values=dict(staged_item.values),
                source_text=staged_item.source_text,
                confidence=staged_item.confidence,
                reason=staged_item.reason,
            )
        )

    for index, text in enumerate(parsed.unclassified):
        draft.unclassified.append(
            UnclassifiedEntry(
                key=f"unclassified.{index}",
                text=text,
                reason="El texto del PDF no se pudo asignar a una seccion con certeza.",
                suggested_section=_guess_unclassified_section(text),
            )
        )

    draft.conflicts = [asdict(conflict) for conflict in parsed.conflicts]

    save_draft(draft)
    # El tope se aplica tambien aqui: `purge_expired_drafts` solo corre cuando
    # alguien visita el formulario, y un cliente que suba PDFs seguidos sin
    # pasar por el formulario lo evitaria.
    _enforce_draft_cap(drafts_directory())
    return draft


def _guess_unclassified_section(text: str) -> str:
    normalized = text.lower()
    if any(marker in normalized for marker in ("certific", "curso", "diplom", "course")):
        return "certifications"
    if any(marker in normalized for marker in ("proyecto", "project")):
        return "projects"
    return "additional_info"


def save_draft(draft: ImportDraft) -> ImportDraft:
    path = _draft_path(draft.draft_id)
    draft.updated_at = _now().isoformat()
    serialized = json.dumps(draft.to_json(), ensure_ascii=False, indent=2)

    # Se escribe a un temporal y se renombra: `write_text` trunca el archivo
    # destino antes de escribir, y un disco lleno o un proceso interrumpido
    # dejarian un borrador corrupto en lugar del anterior intacto.
    temporary_path = path.with_suffix(".json.tmp")
    try:
        temporary_path.write_text(serialized, encoding="utf-8")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return draft


def load_draft(draft_id: str) -> ImportDraft:
    path = _draft_path(draft_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ImportStagingError(
            "draft_not_found",
            "La importacion ya expiro o nunca existio. Volve a subir el PDF.",
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise ImportStagingError(
            "draft_unreadable",
            "No se pudo leer la importacion en curso. Volve a subir el PDF.",
        ) from error

    draft = ImportDraft.from_json(payload)
    if _now() - datetime.fromisoformat(draft.updated_at) > DRAFT_TTL:
        delete_draft(draft_id)
        raise ImportStagingError(
            "draft_expired",
            "La importacion expiro. Volve a subir el PDF para empezar de nuevo.",
        )

    return draft


DRAFT_CLAIM_SUFFIX = ".claiming"


def claim_draft(draft_id: str) -> None:
    """Reclama el borrador de forma atomica para que no se confirme dos veces.

    Dos peticiones simultaneas sobre el mismo borrador podian llegar las dos a la
    escritura: la primera creaba el CV y borraba el borrador, y la segunda seguia
    teniendo el objeto en memoria, asi que creaba un segundo CV. Un doble clic o
    un reintento bastaban.

    El reclamo es un archivo MARCADOR creado con `O_CREAT | O_EXCL`, que es
    atomico y falla si el archivo ya existe: solo una peticion puede pasar. El
    borrador en si no se mueve, asi que sigue siendo legible durante toda la
    confirmacion — moverlo de sitio dejaba la ruta vacia y rompia la recarga.
    """

    claim = _draft_path(draft_id).with_suffix(DRAFT_CLAIM_SUFFIX)
    try:
        descriptor = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise ImportStagingError(
            "draft_already_being_confirmed",
            "Esta importacion ya se esta procesando. Espera a que termine o empeza de nuevo.",
        ) from error
    except FileNotFoundError as error:
        raise ImportStagingError(
            "draft_expired",
            "El borrador de importacion ya no existe. Empeza de nuevo la importacion.",
        ) from error

    os.close(descriptor)


def release_draft(draft_id: str) -> None:
    """Suelta el reclamo si la confirmacion fallo.

    Sin esto, un fallo de escritura dejaria el borrador bloqueado y la persona
    no podria reintentar: perderia toda la revision que ya habia corregido.
    """

    _draft_path(draft_id).with_suffix(DRAFT_CLAIM_SUFFIX).unlink(missing_ok=True)


def delete_draft(draft_id: str) -> None:
    _draft_path(draft_id).unlink(missing_ok=True)
    _draft_path(draft_id).with_suffix(DRAFT_CLAIM_SUFFIX).unlink(missing_ok=True)


def apply_review(
    draft: ImportDraft,
    *,
    values: dict[str, str],
    decisions: dict[str, str],
    unclassified_assignments: dict[str, str],
    title: str = "",
) -> ImportDraft:
    """Aplica las correcciones y decisiones de la pantalla de revision.

    Nunca descarta en silencio: si una entrada no aparece en `decisions` queda
    en `pending`, y confirmar con pendientes es un error explicito.
    """

    # Se validan TODAS las decisiones antes de tocar el borrador. Si una sola
    # fuera invalida, no se guarda nada: la persona no puede perder lo que
    # escribio por un error de la pantalla.
    #
    # La lista global no alcanza. `kept` en una entrada detectada se aceptaba, y
    # `_collect_items` solo mira `confirmed`: la entrada desaparecia del CV
    # mientras su pendiente se limpiaba. Es la misma perdida silenciosa que el
    # staging existe para evitar, alcanzada por otra via.
    entry_keys = {entry.key for entry in draft.entries}
    unclassified_keys = {item.key for item in draft.unclassified}

    for key, decision in decisions.items():
        if decision not in DECISION_STATUSES:
            raise ImportStagingError(
                "review_invalid_decision",
                "Una de las decisiones de la revision no es valida.",
            )
        if key in unclassified_keys and decision == STATUS_CONFIRMED:
            raise ImportStagingError(
                "review_invalid_decision",
                "Un bloque sin clasificar se conserva o se descarta; no se confirma.",
            )
        if key in entry_keys and decision == STATUS_KEPT:
            raise ImportStagingError(
                "review_invalid_decision",
                "Un dato detectado se confirma o se descarta; no se conserva.",
            )

    for key, section in unclassified_assignments.items():
        if section and section not in UNCLASSIFIED_TARGET_SECTIONS:
            raise ImportStagingError(
                "review_invalid_assignment",
                "La seccion elegida para un dato sin clasificar no existe.",
            )

    for entry in draft.entries:
        # Campos escalares llegan como "<clave>"; los campos de un item como
        # "<clave>:<campo>". Separarlos aqui evita que editar un campo de un
        # item pise el valor escalar de otra entrada.
        for submitted_key, submitted_value in values.items():
            # Los bloques sin clasificar se editan con la misma clave que se
            # muestran: aca se persiste lo que la persona escribio.
            if any(item.key == submitted_key for item in draft.unclassified):
                continue
            if submitted_key == entry.key:
                entry.value = submitted_value
            elif submitted_key.startswith(f"{entry.key}:") and entry.values:
                field_name = submitted_key.split(":", 1)[1]
                if field_name in entry.values:
                    entry.values[field_name] = submitted_value

        if entry.key in decisions:
            entry.status = decisions[entry.key]

    if title:
        # El snapshot legacy limita el titulo a 120. Aceptar mas acáoria que el
        # guardado fallara despues, con un mensaje que no ayuda.
        if len(title) > FIELD_LIMITS["cv_title"]:
            raise ImportStagingError(
                "review_title_too_long",
                f"El titulo del CV supera los {FIELD_LIMITS['cv_title']} caracteres que admite "
                "el CV. Acortalos y volve a confirmar.",
            )
        draft.proposed_title = title

    for item in draft.unclassified:
        if item.key in values:
            item.text = values[item.key][:2000]
        if item.key in decisions:
            item.status = decisions[item.key]
        if item.key in unclassified_assignments:
            item.assigned_section = unclassified_assignments[item.key]

    return save_draft(draft)


def pending_summary(draft: ImportDraft) -> tuple[int, int]:
    return len(draft.pending_entries()), len(draft.pending_unclassified())


# --- Mapeo a schema 2 -----------------------------------------------------


def build_schema2_payload(draft: ImportDraft, *, title: str) -> dict:
    """Convierte el borrador aprobado en un payload schema 2.

    Solo entran las entradas confirmadas. Lo que quedo en `pending` o fue
    descartado no aparece: por eso `confirm_draft` exige antes que no quede
    ningun pendiente.
    """

    confirmed = [entry for entry in draft.entries if entry.status == STATUS_CONFIRMED]

    personal: dict[str, str] = {}
    contact: dict[str, str] = {}
    summary = ""
    links: list[dict[str, str]] = []

    for entry in confirmed:
        if entry.section == "personal" and entry.key.startswith("personal."):
            personal[entry.key.split(".", 1)[1]] = entry.value
        elif entry.section == "contact" and entry.key.startswith("contact."):
            contact[entry.key.split(".", 1)[1]] = entry.value
        elif entry.section == "summary":
            summary = entry.value
        elif entry.section == "links":
            url = entry.value
            links.append({"label": _link_label(url), "url": url})

    # El payload schema 2 es PLANO: las secciones viven en la raiz junto a
    # `schema_version`. Anidarlas bajo una clave `sections` hacia que el
    # validador las aceptara pero el snapshot legacy saliera vacio, y el CV
    # se creara sin nombre ni email.
    return {
        "schema_version": 2,
        "title": title,
        "personal": personal,
        "contact": contact,
        "metadata": {"source": "pdf_import"},
        "summary": summary,
        "experience": _collect_items(confirmed, "experience"),
        "education": _collect_items(confirmed, "education"),
        "skills": _collect_items(confirmed, "skills") + _build_assigned_unclassified(draft)["skills"],
        "languages": _collect_items(confirmed, "languages"),
        "certifications": _collect_items(confirmed, "certifications")
        + _build_assigned_unclassified(draft)["certifications"],
        "projects": _collect_items(confirmed, "projects") + _build_assigned_unclassified(draft)["projects"],
        "links": links,
        "additional_info": _build_additional_info(draft),
    }


def _link_label(url: str) -> str:
    lowered = url.lower()
    for domain, label in _LINK_LABELS:
        if domain in lowered:
            return label
    return "Sitio web"


# Campos que el schema 2 define como listas y no como texto. El staging los
# guarda como texto porque en la revision se editan en un input; la conversion
# ocurre recien al construir el payload.
_LIST_FIELDS = ("technologies", "highlights")


def _to_list(value: str) -> list[str]:
    parts = re.split(r"\s*[,;|·]\s*|\n+", value)
    return [part for part in (piece.strip() for piece in parts) if part]


def _collect_items(confirmed: list[StagedEntry], section: str) -> list[dict]:
    collected: list[dict] = []
    for entry in confirmed:
        if entry.section != section or not entry.values:
            continue
        values: dict = {}
        for key, value in entry.values.items():
            if not value:
                continue
            values[key] = _to_list(value) if key in _LIST_FIELDS else value
        if values:
            collected.append(values)
    return collected


def _build_assigned_unclassified(draft: ImportDraft) -> dict[str, list[dict]]:
    """Texto sin clasificar conservado y asignado a una seccion concreta.

    Ignorarlo seria perdida silenciosa: la persona eligio conservar el bloque y
    ademas destino, y el bloque desaparecia del CV.
    """

    assigned: dict[str, list[dict]] = {"skills": [], "certifications": [], "projects": []}
    _overflow: list[str] = []

    for item in draft.unclassified:
        if item.status != STATUS_KEPT or item.assigned_section not in assigned:
            continue
        text = item.text.strip()
        if not text:
            continue

        if item.assigned_section == "skills":
            # Ni `label` ni `category` se recortan. Un bloque que no entra va a
            # informacion adicional con el texto entero, y un campo que excede el
            # limite del contrato se rechaza al confirmar con un mensaje que
            # nombra el campo. Recortar aqui perdia datos en silencio.
            if len(text) <= MAX_SKILL_LABEL:
                label, _, category = text.partition(":")
                assigned["skills"].append({"label": label.strip(), "category": category.strip()})
            else:
                _overflow.append(item.key)
        elif item.assigned_section == "certifications":
            # Sin recorte: el texto completo se guarda y se valida contra el
            # limite real de `certifications[].name` al confirmar. Recortar aqui
            # ocultaria el problema y perderia informacion en silencio.
            assigned["certifications"].append({"name": text, "issuer": "", "date": ""})
        else:
            name, separator, rest = text.partition(" - ")
            assigned["projects"].append(
                {
                    "name": (name if separator else text).strip(),
                    "summary": rest.strip(),
                    "link": "",
                    "technologies": [],
                }
            )

    if _overflow:
        _set_overflow(draft, _overflow)

    return assigned


def _set_overflow(draft: ImportDraft, keys: list[str]) -> None:
    """Marca bloques que no caben en su seccion y van a informacion adicional."""

    draft.overflow_unclassified = keys


def _build_additional_info(draft: ImportDraft) -> list[dict[str, str]]:
    """Informacion adicional solo con lo que la persona eligio conservar.

    Un elemento sin clasificar que quedo en `pending` no entra: confirmar sin
    decisiones pendientes ya es imposible, asi que llegar aqui significa que
    la persona lo resolvio de forma explicita.
    """

    additional: list[dict[str, str]] = []

    for entry in draft.entries:
        if entry.section == "additional_info" and entry.status == STATUS_CONFIRMED:
            values = {key: value for key, value in entry.values.items() if value}
            if values:
                additional.append(values)

    for item in draft.unclassified:
        if item.status != STATUS_KEPT:
            continue

        if item.key in draft.overflow_unclassified:
            title, content = _split_additional_text(item.text)
            additional.append({"title": title, "content": content})
            continue

        if item.assigned_section == "additional_info" or not item.assigned_section:
            title, content = _split_additional_text(item.text)
            additional.append({"title": title, "content": content})

    return additional


def _split_additional_text(text: str) -> tuple[str, str]:
    """Si el texto conservado ya trae etiqueta, la usa de titulo."""

    match = _LABELLED_VALUE.match(text.strip())
    if match:
        return match.group("label").strip(), match.group("value").strip()
    # Sin recorte: si el texto excede el limite real del contrato, el error lo
    # nombra al confirmar y el borrador sigue editable. Recortar a 1000
    # sobrepasaba ademas el limite de 600 del schema.
    return "Informacion del PDF", text


def _validate_field_limits(draft: ImportDraft) -> None:
    """Rechaza con mensaje especifico lo que no entra en schema 2.

    Recortar en su lugar seria perdida silenciosa. El borrador se conserva
    intacto, asi que la persona puede acortar el valor y reintentar.
    """

    overlong: list[str] = []

    for entry in draft.entries:
        if entry.status != STATUS_CONFIRMED:
            continue

        candidates = list(entry.values.items()) if entry.values else [(entry.key, entry.value)]
        for field_name, value in candidates:
            limit = FIELD_LIMITS.get(f"{entry.section}.{field_name}") or FIELD_LIMITS.get(field_name)
            if limit is not None and len(value) > limit:
                overlong.append(f"{field_name} ({len(value)} de {limit} caracteres)")

    for item in draft.unclassified:
        if item.status != STATUS_KEPT:
            continue

        # Asignado a skills o certificaciones: los campos construidos se validan
        # solos, porque el texto entra en uno. Asignado a proyectos, el bloque se
        # parte en `name` y `summary`, asi que medir el bloque crudo contra el
        # limite de `name` rechazaba proyectos perfectamente validos
        # ("MiProyecto - " + un resumen largo excede 160, pero `name` son pocos).
        # Sin seccion (o "informacion adicional"): se valida el contenido de
        # `additional_info`, que antes no se comprobaba nunca.
        if item.assigned_section == "projects":
            continue
        if item.assigned_section and item.assigned_section != "additional_info":
            limit = FIELD_LIMITS.get(f"{item.assigned_section}.name")
            section = item.assigned_section
        else:
            limit = ADDITIONAL_INFO_CONTENT_LIMIT
            section = "informacion adicional"

        if limit is not None and len(item.text) > limit:
            overlong.append(f"{section} ({len(item.text)} de {limit} caracteres)")

    # Campos de lista: cantidad de elementos y tamano de cada uno. Un campo de
    # texto que se parte en lista solo al armar el payload no se validaba nunca.
    for entry in draft.entries:
        if entry.status != STATUS_CONFIRMED or not entry.values:
            continue

        for field_name, raw_value in entry.values.items():
            limits = LIST_FIELD_LIMITS.get(f"{entry.section}.{field_name}")
            if limits is None:
                continue

            max_items, max_item_length = limits
            parts = [part.strip() for part in re.split(r"[,;\n]+", raw_value) if part.strip()]

            if len(parts) > max_items:
                overlong.append(f"{field_name} ({len(parts)} elementos, maximo {max_items})")
            elif any(len(part) > max_item_length for part in parts):
                overlong.append(f"{field_name} (un elemento supera {max_item_length} caracteres)")

    if overlong:
        raise ImportStagingError(
            "review_value_too_long",
            "Algunos valores superan el largo que admite el CV y fueron recortados o "
            "rechazados para no perder informacion en silencio: "
            + "; ".join(overlong[:6])
            + ". Editalos para acortarlos y volve a confirmar.",
        )


def _validate_additional_info_count(draft: ImportDraft) -> None:
    """`additional_info` admite 20 elementos: mas de eso se rechaza, no se recorta."""

    payload_preview = build_schema2_payload(draft, title="previsualizacion")
    if len(payload_preview.get("additional_info", [])) > MAX_ADDITIONAL_INFO:
        raise ImportStagingError(
            "review_too_much_additional_info",
            f"Conservaste mas bloques de informacion adicional que los {MAX_ADDITIONAL_INFO} que "
            "admite el CV. Combina los que hablen de lo mismo, reasignalos a otra seccion o "
            "descartalos antes de confirmar.",
        )


def _describe_schema_errors(errors: tuple[str, ...]) -> str:
    """Traduce los codigos del validador canonico a algo accionable.

    El codigo solo (`experience_technologies_too_long`) no le dice a nadie que
    corregir. Se nombra el campo y el limite real del contrato.
    """

    ETIQUETAS = {
        "skills": "la lista de tecnologias",
        "experience": "la experiencia",
        "projects": "los proyectos",
        "additional_info": "la informacion adicional",
        "summary": "el resumen",
        "personal": "los datos personales",
        "contact": "los datos de contacto",
        "languages": "los idiomas",
        "certifications": "las certificaciones",
    }

    explicados: list[str] = []
    for code in errors:
        seccion, _, resto = code.partition("_")
        etiqueta = ETIQUETAS.get(seccion, seccion.replace("_", " "))
        if resto.endswith("_too_long"):
            campo = resto[: -len("_too_long")].replace("_", " ")
            explicados.append(f"{etiqueta}: el campo '{campo}' excede su limite")
        elif resto.endswith("_too_many_items"):
            explicados.append(f"{etiqueta} tiene mas elementos de los que admite el CV")
        elif "must_be_string" in code or "must_be_object" in code:
            explicados.append(f"{etiqueta} tiene un valor con el formato incorrecto")
        else:
            explicados.append(f"{etiqueta}: {code.replace('_', ' ')}")

    return (
        "La revision no termina en un CV valido todavia. Corregi estos puntos: "
        + "; ".join(dict.fromkeys(explicados))
        + ". El borrador queda intacto, asi que podes corregirlos y reintentar."
    )


def confirm_draft(draft: ImportDraft, *, title: str) -> dict:
    """Valida que no queden pendientes y devuelve el payload schema 2.

    No escribe en la base: eso lo hace la capa de rutas, con el mismo patron
    que usa el resto de la aplicacion (validar todo antes de escribir).
    """

    entries_pending, unclassified_pending = pending_summary(draft)

    _validate_field_limits(draft)
    _validate_additional_info_count(draft)

    if entries_pending or unclassified_pending:
        raise ImportStagingError(
            "review_incomplete",
            "Todavia hay datos sin decidir. Confirma, conserva o descarta cada elemento "
            "de las secciones con dudas y de informacion no clasificada antes de guardar.",
        )

    # Tiene que estar confirmado Y tener contenido: confirmar un campo vacio
    # no es una decision valida, solo un dato que falta.
    if not any(
        entry.key == "personal.full_name"
        and entry.status == STATUS_CONFIRMED
        and entry.value.strip()
        for entry in draft.entries
    ):
        raise ImportStagingError(
            "review_missing_required",
            "Falta el nombre completo, que es obligatorio para crear el CV.",
        )

    # Las tecnologias excedentes no son una skill mas: viven en su propia seccion
    # para no romper el tope del schema. Si la persona las conserva sin resolver,
    # se rechaza con un motivo accionable en vez de dejarlas caer en silencio.
    kept_overflow = [
        entry for entry in draft.entries
        if entry.section == SKILLS_OVERFLOW_SECTION and entry.status != STATUS_DISCARDED
    ]
    if kept_overflow:
        limite = schema.ITEM_SECTION_SPECS["skills"].max_items
        raise ImportStagingError(
            "review_skills_overflow_pending",
            "El PDF lista mas tecnologias de las que el CV admite "
            f"({limite}). Las que sobraron quedaron aparte, en un bloque que no se guarda. "
            "Quita las que no quieras de la lista de tecnologias y despues descarta "
            "ese bloque, o borra tecnologias de la lista hasta que entre todas.",
        )

    payload = build_schema2_payload(draft, title=title)

    # Validacion canonica contra el MISMO contrato que usa la persistencia.
    #
    # Antes, staging y schema 2 eran dos fuentes de verdad: staging tenia sus
    # limites y el schema los suyos, y cualquier divergencia seEDIA como un
    # error generico de guardado despues de una revision que parecia valida.
    # Preguntar al validador canonico hace que esa divergencia sea imposible por
    # construccion: si el payload no entra, no se entrega.
    validation = schema.validate_structured_payload_v2(payload)
    if not validation.is_valid:
        raise ImportStagingError(
            "review_schema_invalid",
            _describe_schema_errors(validation.errors),
        )

    return payload