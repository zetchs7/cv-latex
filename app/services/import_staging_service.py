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

STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_DISCARDED = "discarded"
STATUS_KEPT = "kept"
DECISION_STATUSES = (STATUS_CONFIRMED, STATUS_DISCARDED, STATUS_KEPT)

MAX_SKILL_LABEL = 60
MAX_CV_TITLE = 120

# Limites reales de schema 2 (`ITEM_SECTION_SPECS`). Se validan al confirmar:
# recortar antes escondia el problema y perdia informacion sin avisar.
FIELD_LIMITS: dict[str, dict[str, int]] = {
    "personal.full_name": 160,
    "personal.location": 160,
    "personal.headline": 160,
    "contact.email": 180,
    "contact.phone": 80,
    "summary": 1200,
    "links": 200,
    "education.institution": 120,
    "education.degree": 120,
    "education.summary": 800,
    "certifications.name": 160,
    "certifications.issuer": 120,
    "certifications.date": 10,
    "projects.name": 160,
    "projects.summary": 1000,
    "projects.technologies": 300,
    "skills.label": 60,
    "skills.category": 60,
    "languages.name": 60,
    "languages.level": 20,
    "experience.company": 120,
    "experience.role": 120,
    "experience.location": 120,
    "experience.start_date": 10,
    "experience.end_date": 10,
    "experience.summary": 2000,
    "experience.technologies": 300,
    "experience.highlights": 2000,
}

MAX_ADDITIONAL_INFO = 20
ADDITIONAL_INFO_CONTENT_LIMIT = 1000

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


def delete_draft(draft_id: str) -> None:
    _draft_path(draft_id).unlink(missing_ok=True)


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
        draft.proposed_title = title[:MAX_CV_TITLE]

    for item in draft.unclassified:
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
            # `skills[].label` admite 60 caracteres. Un bloque mas largo no
            # entra, y recortarlo perderia el resto sin avisar. En ese caso el
            # texto completo va a informacion adicional, donde la persona puede
            # verlo entero y decidir que hacer con el.
            if len(text) <= MAX_SKILL_LABEL:
                label, _, category = text.partition(":")
                assigned["skills"].append({"label": label.strip(), "category": category.strip()[:60]})
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
                    "name": (name if separator else text).strip()[:160],
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
    return "Informacion del PDF", text[:1000]


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

        # Asignado a una seccion concreta: se valida el campo `name` de esa
        # seccion. Sin seccion (o "informacion adicional"): se valida el
        # contenido de `additional_info`, que antes no se comprobaba nunca.
        if item.assigned_section and item.assigned_section != "additional_info":
            limit = FIELD_LIMITS.get(f"{item.assigned_section}.name")
            section = item.assigned_section
        else:
            limit = ADDITIONAL_INFO_CONTENT_LIMIT
            section = "informacion adicional"

        if limit is not None and len(item.text) > limit:
            overlong.append(f"{section} ({len(item.text)} de {limit} caracteres)")

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

    return build_schema2_payload(draft, title=title)