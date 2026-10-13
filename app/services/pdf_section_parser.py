"""Clasificacion conservadora del texto extraido de un CV en PDF.

Este modulo **no inventa datos**. Su contrato es:

- Solo reconoce lo que puede señalar con una regla determinista.
- Cada deteccion lleva un nivel de confianza y el motivo por el que tiene ese
  nivel, para que la persona que revisa sepa cuanto fiarse de ella.
- Lo que no se puede clasificar con seguridad no se descarta: viaja a
  `unclassified` y se muestra en la pantalla de revision.
- Ante contradicciones, expone el conflicto en vez de elegir en silencio.

Los niveles de confianza se definen asi, de forma comprobable:

- ``high``:   hay una etiqueta explicita (`Email: ...`) o un patron inequivoco
              (direccion de correo valida, rango de anos completo).
- ``medium``: el valor es plausible pero le falta corroboracion: la seccion se
              reconocio pero el campo no tiene etiqueta, o el rango de fechas
              esta incompleto.
- ``low``:    no hay senal suficiente. Se propone para que la persona lo
              confirme o lo descarte; nunca se carga como dato verificado.

Ningun porcentaje de confianza: los niveles son ordinales y sus criterios son
los de arriba, no una estimacion estadistica.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
import re
import unicodedata

from app.services.pdf_import_service import PdfUnclassifiableDocument

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

CONFIDENCE_LABELS = {
    CONFIDENCE_HIGH: "Alta",
    CONFIDENCE_MEDIUM: "Media",
    CONFIDENCE_LOW: "Baja",
}

MAX_LINE_LENGTH_FOR_HEADING = 60
# Tope de items por seccion, derivado del schema 2 real. Un valor fijo se
# desincroniza: con 30 fijo se perdian skills validos, porque schema 2 admite 40.
def _max_items(section: str) -> int:
    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS

    return ITEM_SECTION_SPECS[section].max_items


MAX_ITEMS_PER_SECTION = 30  # compatibilidad: valor por defecto, no ya el tope real
MAX_SKILLS = 40
MAX_LANGUAGES = 20
# Tope de seguridad: si un documento deja mas texto sin clasificar que
# esto, se rechaza antes de crear un borrador incompleto. NO se recorta en
# silencio: el Issue #14 prohibe descartar informacion extraida del PDF.
MAX_UNCLASSIFIED_CHARACTERS = 200_000


@dataclass(frozen=True)
class StagedField:
    """Un valor escalar detectado, listo para ser revisado y corregido."""

    key: str
    section: str
    value: str
    source_text: str
    confidence: str
    reason: str


@dataclass(frozen=True)
class StagedItem:
    """Un elemento de una seccion de lista (experiencia, educacion, ...)."""

    key: str
    section: str
    values: dict[str, str]
    source_text: str
    confidence: str
    reason: str


@dataclass(frozen=True)
class StagedConflict:
    """Dos detecciones que se contradicen sobre el mismo campo."""

    key: str
    reason: str
    candidates: tuple[str, ...]


@dataclass(frozen=True)
class ParsedCvDocument:
    """Resultado completo del analisis. No es schema 2 y nunca se persiste asi."""

    fields: tuple[StagedField, ...] = ()
    items: tuple[StagedItem, ...] = ()
    unclassified: tuple[str, ...] = ()
    conflicts: tuple[StagedConflict, ...] = ()

    def sections(self) -> dict[str, list[StagedField]]:
        grouped: dict[str, list[StagedField]] = {}
        for staged_field in self.fields:
            grouped.setdefault(staged_field.section, []).append(staged_field)
        return grouped

    def items_by_section(self) -> dict[str, list[StagedItem]]:
        grouped: dict[str, list[StagedItem]] = {}
        for staged_item in self.items:
            grouped.setdefault(staged_item.section, []).append(staged_item)
        return grouped


# --- Vocabulario ---------------------------------------------------------

SECTION_HEADINGS: dict[str, tuple[str, ...]] = {
    "personal": (
        "DATOS PERSONALES", "DATOS DE CONTACTO", "INFORMACION DE CONTACTO",
        "PERSONAL DATA", "PERSONAL INFORMATION", "CONTACT", "CONTACT INFORMATION",
    ),
    "summary": (
        "PERFIL PROFESIONAL", "PERFIL", "RESUMEN", "RESUMEN PROFESIONAL",
        "SOBRE MI", "OBJETIVO PROFESIONAL", "SUMMARY", "PROFESSIONAL SUMMARY",
        "PROFILE", "ABOUT ME", "OBJECTIVE",
    ),
    "experience": (
        "EXPERIENCIA LABORAL", "EXPERIENCIA PROFESIONAL", "EXPERIENCIA",
        "EXPERIENCIAS", "HISTORIAL LABORAL", "WORK EXPERIENCE",
        "PROFESSIONAL EXPERIENCE", "EXPERIENCE", "EMPLOYMENT",
    ),
    "education": (
        "EDUCACION", "FORMACION", "FORMACION ACADEMICA", "ESTUDIOS",
        "EDUCATION", "ACADEMIC BACKGROUND", "ACADEMIC",
    ),
    "skills": (
        "APTITUDES", "APTITUDES TECNICAS", "HABILIDADES", "COMPETENCIAS",
        "HERRAMIENTAS", "TECNOLOGIAS", "CONOCIMIENTOS TECNICOS",
        "SKILLS", "TECHNICAL SKILLS", "TECHNOLOGIES", "TOOLS", "TECH STACK",
    ),
    "languages": ("IDIOMAS", "IDIOMA", "LANGUAGES", "LANGUAGE"),
    "certifications": (
        "CERTIFICACIONES", "CURSOS", "CAPACITACIONES", "FORMACIONES",
        "CERTIFICATIONS", "COURSES", "TRAINING",
    ),
    "projects": ("PROYECTOS", "PROYECTOS PERSONALES", "PROJECTS", "PERSONAL PROJECTS"),
    "links": ("LINKS", "ENLACES", "SITIO WEB", "LINKS Y REDES", "WEBSITES"),
    "additional_info": (
        "INFORMACION ADICIONAL", "OTRA INFORMACION", "OTROS DATOS",
        "ACTIVIDADES", "INTERESES", "REFERENCIAS",
        "ADDITIONAL INFORMATION", "OTHER INFORMATION", "ACTIVITIES",
        "INTERESTS", "REFERENCES",
    ),
}

FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "personal.full_name": ("NOMBRE", "NOMBRE COMPLETO", "APELLIDOS Y NOMBRE", "NAME", "FULL NAME"),
    "personal.location": ("UBICACION", "LOCALIDAD", "CIUDAD", "LOCATION", "CITY", "DOMICILIO"),
    "personal.headline": ("TITULO", "TITULO PROFESIONAL", "PROFESION", "HEADLINE", "TITLE", "ROL"),
    "contact.email": ("EMAIL", "CORREO", "CORREO ELECTRONICO", "MAIL", "E MAIL"),
    "contact.phone": ("TELEFONO", "TEL", "TELF", "MOVIL", "CELULAR", "PHONE", "CEL"),
}

SKILL_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Sistemas operativos": ("linux", "unix", "windows", "macos", "solaris", "aix"),
    "Lenguajes de programacion": ("python", "javascript", "typescript", "java", "golang", "c#", "c++", "php", "ruby", "rust", "scala", "kotlin", "sql", "bash", "shell", "perl"),
    "Bases de datos": ("postgresql", "postgres", "mysql", "mariadb", "sqlite", "mongodb", "redis", "oracle", "sql server", "dynamodb", "elasticsearch"),
    "Cloud": ("aws", "azure", "gcp", "google cloud", "cloudformation", "s3", "ec2", "lambda"),
    "Contenedores": ("docker", "kubernetes", "k8s", "podman", "containerd", "helm"),
    "DevOps": ("jenkins", "ansible", "terraform", "gitlab ci", "github actions", "ci/cd", "argocd", "flux"),
    "Monitoreo": ("prometheus", "grafana", "datadog", "nagios", "zabbix", "elk", "splunk", "kibana"),
    "Networking": ("tcp", "udp", "dns", "bgp", "vpc", "firewall", "load balancer", "networking", "redes"),
    "Virtualizacion": ("vmware", "virtualbox", "hyper-v", "proxmox", "kvm", "xen"),
    "Storage": ("nfs", "ceph", "gluster", "san", "nas", "zfs", "btrfs"),
    "Seguridad": ("owasp", "pentest", "sSIEM", "siem", "firewall audit", "hardening", "criptografia"),
    "Herramientas": ("git", "jira", "confluence", "excel", "word", "powerpoint", "notion", "slack"),
    "Plataformas": ("shopify", "salesforce", "sap", "magento", "wordpress", "sharepoint"),
    "Aplicaciones empresariales": ("sap", "erp", "crm", "helpdesk", "servicedesk"),
}

LANGUAGE_LEVEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Nativo": ("nativo", "native", "mother tongue", "lengua materna"),
    "C2": ("c2", "avanzado", "advanced", "fluent", "profesional"),
    "C1": ("c1", "avanzado intermedio", "upper intermediate"),
    "B2": ("b2", "intermedio alto", "intermediate"),
    "B1": ("b1", "intermedio", "intermediate"),
    "A2": ("a2", "basico", "basic", "elemental"),
    "A1": ("a1", "principiante", "beginner"),
}

# --- Patrones ------------------------------------------------------------

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s,;)]+", re.IGNORECASE)
LINKEDIN_PATTERN = re.compile(r"linkedin\.com/[^\s,;)]+", re.IGNORECASE)
GITHUB_PATTERN = re.compile(r"github\.com/[^\s,;)]+", re.IGNORECASE)

# El grupo no captura es parte de la constante, no del sitio de uso: sin el,
# al interpolar `_MONTH` dentro de otro patron su alternacion se aplana
# sobre la expresion completa y "January 2019" matchea solo "Jan".
_MONTH = (
    "(?:"
    "january|february|march|april|may|june|july|august|september|october|november|december"
    "|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
    "|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
    "|ene|abr|ago|sept|dic"
    ")"
)
CURRENT_MARKERS = ("actualidad", "presente", "actual", "current", "present", "today", "now", "hoy")

_YEAR = r"(?:19|20)\d{2}"
# Tres formas, de mas especifica a mas laxa: dia/mes/anio, mes/anio y anio.
# Sin la segunda, "01/2020" se reducia a "2020" y se perdia el mes en silencio.
_DATE = rf"(?:\d{{1,2}}[\/\-.]{_MONTH}[^\s,;]*[\/\-.]{_YEAR}|\d{{1,2}}[\/\-.]{_YEAR}|{_MONTH}\s+{_YEAR}|{_YEAR})"
RANGE_SEPARATOR = r"\s*(?:-|–|—|to|a|al|hasta)\s*"

DATE_RANGE_PATTERN = re.compile(
    rf"(?P<start>{_DATE})(?:{RANGE_SEPARATOR}(?P<end>{_DATE}|{'|'.join(CURRENT_MARKERS)}))?",
    re.IGNORECASE,
)

_SKILL_SEPARATOR_PATTERN = re.compile(r"\s*(?:·|•|,|;|\||/|\band\b|\by\b|\bo\b)\s+", re.IGNORECASE)
_TECHNOLOGY_LINE_PATTERN = re.compile(
    r"^\s*(?:stack|tecnologias|herramientas|technologies|tools)\s*:?\s*(?P<value>.+)$",
    re.IGNORECASE,
)
_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•·‣▪o]|\d+[.)])\s+")
_LABELLED_VALUE = re.compile(r"^(?P<label>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ /]{2,30}?)\s*[:\-–]\s+(?P<value>.+)$")

# Etiquetas con significado dentro de cada seccion. El formato
# "Empresa: Acme" en una linea es tan comun como "Acme -- 2021", asi que se
# reconoce explicitamente en vez de dejarlo en un bloque sin clasificar.
SECTION_ITEM_LABELS: dict[str, dict[str, tuple[str, ...]]] = {
    "experience": {
        "company": ("EMPRESA", "COMPANIA", "COMPANY", "ORGANIZACION", "ORGANISATION"),
        "role": ("CARGO", "PUESTO", "ROL", "ROLE", "POSITION", "TITLE"),
        "location": ("UBICACION", "LOCALIDAD", "LOCATION"),
        "summary": ("RESPONSABILIDADES", "DESCRIPCION", "SUMMARY", "RESPONSIBILITIES", "DESCRIPTION"),
    },
    "education": {
        "institution": ("INSTITUCION", "CENTRO", "UNIVERSIDAD", "INSTITUTION", "SCHOOL", "UNIVERSITY"),
        "degree": ("TITULACION", "CARRERA", "TITULO", "DEGREE", "COURSE"),
        "field": ("CARRERA", "AREA", "FIELD", "SPECIALIZATION"),
        "summary": ("DESCRIPCION", "DESCRIPTION", "NOTAS"),
    },
    "certifications": {
        "name": ("CERTIFICACION", "CURSO", "CAPACITACION", "CERTIFICATION", "COURSE"),
        "issuer": ("ENTIDAD", "INSTITUCION", "EMISOR", "ISSUER", "ORGANIZATION"),
        "date": ("FECHA", "ANIO", "YEAR", "DATE"),
    },
    "projects": {
        "name": ("PROYECTO", "PROJECT"),
        "summary": ("DESCRIPCION", "DESCRIPTION", "IMPACTO", "RESULTADO", "IMPACT"),
        "technologies": ("STACK", "TECNOLOGIAS", "HERRAMIENTAS", "TECHNOLOGIES", "TOOLS"),
    },
}

_DATE_LABEL = re.compile(r"^(?P<label>FECHAS?|FECHA|DATES?|PERIODO|PERIOD)\s*:?\s*(?P<value>.+)$", re.IGNORECASE)


def _split_labelled_line(line: str, labels: dict[str, tuple[str, ...]]) -> tuple[str, str] | None:
    """Devuelve (campo, valor) si la linea es una etiqueta reconocida."""

    match = _LABELLED_VALUE.match(line)
    if not match:
        return None

    label = normalize_for_matching(match.group("label"))
    value = match.group("value").strip()
    if not value:
        return None

    for field_name, candidates in labels.items():
        if any(label == candidate for candidate in candidates):
            return field_name, value

    return None


def _labelled_group(lines: list[str], labels: dict[str, tuple[str, ...]], section_name: str) -> list[StagedItem]:
    """Construye items a partir de lineas etiquetadas del tipo 'Campo: valor'.

    Devuelve lista vacia si las lineas no usan ese formato, para que el
    llamador pueda caer al parseo por fechas.
    """

    groups: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    extra: list[str] = []
    saw_label = False

    for line in lines:
        date_label_match = _DATE_LABEL.match(line)
        if date_label_match:
            saw_label = True
            if current is not None:
                current["_dates"] = date_label_match.group("value").strip()
                groups.append(current)
                current = None
            if current is None and groups:
                pass
            continue

        pair = _split_labelled_line(line, labels)
        if pair is not None:
            saw_label = True
            field_name, value = pair
            if field_name in ("company", "institution", "name") and current is not None:
                current = None
            if current is None:
                current = {}
            current[field_name] = value
            continue

        if current is not None and not current.get("_dates"):
            extra.append(line)
        elif current is not None:
            extra.append(line)

    if current is not None:
        groups.append(current)

    if not saw_label:
        return []

    items: list[StagedItem] = []
    for index, group in enumerate(groups):
        values = {key: value for key, value in group.items() if not key.startswith("_")}
        source_lines = [line for line in lines if any(value in line for value in values.values())]
        note = "Lineas con etiqueta explicita en el PDF."
        if group.get("_dates"):
            date_match = DATE_RANGE_PATTERN.search(group["_dates"])
            if date_match:
                values["start_date"] = date_match.group("start")
                if date_match.group("end"):
                    values["end_date"] = date_match.group("end")
                if (date_match.groupdict().get("end") or "").strip().lower() in CURRENT_MARKERS:
                    note += " Marca trabajo actual."
                else:
                    note += " La fecha de fin no se pudo determinar."
            else:
                note += " El periodo no pudo interpretarse como rango de fechas."
        else:
            note += " Sin rango de fechas legible: la persona debe completarlo."

        items.append(
            StagedItem(
                key=f"{index}.0",
                section=section_name,
                values=values,
                source_text=" / ".join(source_lines)[:600],
                confidence=CONFIDENCE_HIGH if group.get("_dates") else CONFIDENCE_MEDIUM,
                reason=note,
            )
        )

    return items


def normalize_for_matching(text: str) -> str:
    """Mayusculas sin acentos ni puntuacion, para comparar encabezados y etiquetas."""

    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    without_punctuation = re.sub(r"[^A-Za-z0-9/ ]+", " ", without_marks)
    return re.sub(r"\s+", " ", without_punctuation).strip().upper()


def parse_cv_text(text: str) -> ParsedCvDocument:
    """Analiza el texto completo de un CV y devuelve el staging propuesto."""

    lines = [line.rstrip() for line in text.splitlines()]
    segments = _split_into_sections(lines)

    fields: list[StagedField] = []
    links: list[StagedField] = []
    items: list[StagedItem] = []
    unclassified: list[str] = []

    _extract_contact_fields(segments, fields, links)
    _extract_summary(segments, fields)

    fields.extend(links)

    for section_name in ("experience", "education", "skills", "languages", "certifications", "projects"):
        _extract_items(section_name, segments, items)

    _collect_orphan_lines(segments, items, unclassified, fields)

    conflicts = _detect_conflicts(fields, items)

    total_unclassified_characters = sum(len(block) for block in unclassified)
    if total_unclassified_characters > MAX_UNCLASSIFIED_CHARACTERS:
        # Documento legible pero demasiado grande para revisarlo de forma util.
        # Se rechaza de forma controlada ANTES de crear un borrador que perderia
        # contenido sin que la persona se de cuenta.
        raise PdfUnclassifiableDocument(
            "El PDF dejo mas texto del que la pantalla de revision puede mostrar. "
            "Proba con un CV mas corto o con un PDF mejor estructurado."
        )

    return ParsedCvDocument(
        fields=tuple(fields),
        items=tuple(items),
        unclassified=tuple(unclassified),
        conflicts=tuple(conflicts),
    )


# --- Segmentacion por seccion --------------------------------------------


@dataclass
class _Section:
    name: str
    lines: list[str] = dataclass_field(default_factory=list)
    heading_found: bool = False


def _split_into_sections(lines: list[str]) -> list[_Section]:
    segments: list[_Section] = []
    prelude = _Section(name="preamble")
    segments.append(prelude)
    current = prelude

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        section_name = _match_heading(line)
        if section_name is not None:
            current = _Section(name=section_name, heading_found=True)
            segments.append(current)
            continue

        current.lines.append(line)

    return segments


def _match_heading(line: str) -> str | None:
    """Un encabezado es una linea corta, sola, que coincide con un nombre conocido."""

    if len(line) > MAX_LINE_LENGTH_FOR_HEADING:
        return None
    if EMAIL_PATTERN.search(line) or URL_PATTERN.search(line):
        return None
    if line.count(" ") < 0:
        return None

    normalized = normalize_for_matching(line)
    if not normalized:
        return None

    for section_name, headings in SECTION_HEADINGS.items():
        for heading in headings:
            if normalized == heading:
                return section_name

    return None


# --- Campos escalares -----------------------------------------------------


def _extract_contact_fields(
    segments: list[_Section],
    fields: list[StagedField],
    links: list[StagedField],
) -> None:
    """Datos personales: etiquetados, o deducidos solo con senal inequivoca.

    Los enlaces van a una lista aparte porque son multiples y cada uno necesita
    clave propia; mezclarlos con los campos escalares generaba conflictos
    falsos por clave repetida.
    """

    preamble = segments[0]
    contact_segments = [segment for segment in segments if segment.name in ("personal", "links")]
    candidates = preamble.lines + [line for segment in contact_segments for line in segment.lines]

    for line in candidates:
        _apply_labelled_field(line, fields)
        _apply_email(line, fields)
        _apply_phone(line, fields)
        _apply_links(line, links)


def _apply_labelled_field(line: str, fields: list[StagedField]) -> None:
    match = _LABELLED_VALUE.match(line)
    if not match:
        return

    label = normalize_for_matching(match.group("label"))
    value = match.group("value").strip()

    for key, labels in FIELD_LABELS.items():
        if any(label == candidate or label.startswith(candidate + " ") for candidate in labels):
            fields.append(
                StagedField(
                    key=key,
                    section=key.split(".")[0],
                    value=value,
                    source_text=line,
                    confidence=CONFIDENCE_HIGH,
                    reason="El valor aparece con una etiqueta explicita en el PDF.",
                )
            )
            return


def _apply_email(line: str, fields: list[StagedField]) -> None:
    if "contact.email" in {staged.key for staged in fields}:
        return

    match = EMAIL_PATTERN.search(line)
    if not match:
        return

    email = match.group(0).rstrip(".")
    fields.append(
        StagedField(
            key="contact.email",
            section="contact",
            value=email,
            source_text=line,
            confidence=CONFIDENCE_HIGH,
            reason="Direccion de correo con formato valido. Es la senal mas inequivoca de un CV.",
        )
    )


def _apply_phone(line: str, fields: list[StagedField]) -> None:
    if "contact.phone" in {staged.key for staged in fields}:
        return

    if not re.search(r"\b(tel|cel|movil|phone|telefono)\b", line, re.IGNORECASE):
        return

    digits = re.findall(r"\+?[\d][\d\s().\-]{6,}\d", line)
    if not digits:
        return

    fields.append(
        StagedField(
            key="contact.phone",
            section="contact",
            value=digits[0].strip(),
            source_text=line,
            confidence=CONFIDENCE_MEDIUM,
            reason="Numero junto a una palabra que indica telefono. La persona deberia confirmarlo: "
                   "el PDF tambien puede contener otros numeros.",
        )
    )


def _apply_links(line: str, links: list[StagedField]) -> None:
    already_linked = {staged.value for staged in links if staged.section == "links"}
    candidates = list(URL_PATTERN.findall(line))
    if not candidates:
        return

    if LINKEDIN_PATTERN.search(line) or GITHUB_PATTERN.search(line):
        confidence = CONFIDENCE_HIGH
        reason = "Enlace a una red profesional con dominio reconocible."
    elif "linkedin" in line.lower() or "github" in line.lower() or "portfolio" in line.lower() or "www." in line.lower():
        confidence = CONFIDENCE_MEDIUM
        reason = "Enlace precedido por una palabra que indica portfolio o perfil."
    else:
        confidence = CONFIDENCE_LOW
        reason = "El PDF contiene una URL pero no dice a que corresponde. Confirmar o descartar."

    for candidate in candidates[:5]:
        value = candidate.rstrip(".,;:)")
        if not value or value in already_linked:
            continue
        already_linked.add(value)
        links.append(
            StagedField(
                key=f"links.{len(links)}",
                section="links",
                value=value,
                source_text=line,
                confidence=confidence,
                reason=reason,
            )
        )


def _extract_summary(segments: list[_Section], fields: list[StagedField]) -> None:
    """El resumen se propone completo, pero con confianza media: puede ser un recorte."""

    summary_segments = [segment for segment in segments if segment.name == "summary"]
    if not summary_segments:
        return

    for segment in summary_segments:
        body = " ".join(line for line in segment.lines).strip()
        if not body:
            continue
        fields.append(
            StagedField(
                key="summary",
                section="summary",
                value=body,
                source_text=body,
                confidence=CONFIDENCE_MEDIUM,
                reason="Texto bajo un encabezado de perfil. Conviene revisarlo: puede incluir "
                       "lineas que no pertenecen al resumen.",
            )
        )
        return


# --- Elementos de seccion -------------------------------------------------


def _extract_items(section_name: str, segments: list[_Section], items: list[StagedItem]) -> None:
    matching = [segment for segment in segments if segment.name == section_name]
    if not matching:
        return

    builder = {
        "experience": _build_experience_item,
        "education": _build_education_item,
        "skills": _build_skill_items,
        "languages": _build_language_items,
        "certifications": _build_certification_items,
        "projects": _build_project_items,
    }.get(section_name)

    if builder is None:
        return

    section_labels = SECTION_ITEM_LABELS.get(section_name)
    date_anchored = section_name in ("experience", "education")

    def _candidates_for(segment_lines: list[str]) -> list[StagedItem]:
        if section_labels:
            labelled = _labelled_group(segment_lines, section_labels, section_name)
            if labelled:
                return labelled
        if date_anchored:
            produced: list[StagedItem] = []
            for group in _blocks_anchored_by_dates(segment_lines):
                value = builder(group)
                produced.append(value) if isinstance(value, StagedItem) else produced.extend(value)
            return produced
        value = builder(segment_lines)
        return [value] if isinstance(value, StagedItem) else list(value)

    counter = 0
    for segment in matching:
        for candidate in _candidates_for(segment.lines):
            # El item de overflow no cuenta contra el tope: es la senal de que
            # hubo excedente, no un elemento mas. Si se cortara, el excedente
            # volveria a desaparecer en silencio.
            if counter >= _max_items(section_name) and not candidate.key.endswith(".overflow"):
                return
            items.append(candidate)
            counter += 1


def _blocks_anchored_by_dates(lines: list[str]) -> list[list[str]]:
    """Agrupa lineas en bloques que arrancan en una linea con fecha.

    Es la heuristica central: en un CV las entradas de experiencia y educacion
    casi siempre llevan rango de fechas. Cuando no lo llevan, el bloque no se
    crea y el texto va a revision, que es el comportamiento correcto.
    """

    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if DATE_RANGE_PATTERN.search(line) and current:
            blocks.append(current)
            current = [line]
            continue
        if DATE_RANGE_PATTERN.search(line):
            current = [line]
            continue
        if current:
            current.append(line)

    if current:
        blocks.append(current)

    return blocks


def _build_experience_item(block: list[str]) -> StagedItem:
    values: dict[str, str] = {}
    notes: list[str] = []
    summary_parts: list[str] = []
    technology_parts: list[str] = []
    highlight_parts: list[str] = []
    headline = block[0]
    body = block[1:]

    date_match = DATE_RANGE_PATTERN.search(headline)
    if date_match:
        values["start_date"] = date_match.group("start")
        if date_match.group("end"):
            values["end_date"] = date_match.group("end")
            if date_match.group("end").strip().lower() in CURRENT_MARKERS:
                notes.append("Marca trabajo actual")
        else:
            notes.append("La fecha de fin no se pudo determinar")

    remainder = _strip_date_range(headline)

    separated = _split_role_and_company(remainder)
    if separated is not None:
        values["role"] = separated[0]
        values["company"] = separated[1]
        notes.append("Verificar que empresa y cargo no esten invertidos")
        confidence = CONFIDENCE_MEDIUM
        reason = "Cargo y empresa separados por un delimitador entre dos fechas."
    elif remainder:
        values["role"] = remainder.strip()
        notes.append("No se pudo separar empresa y cargo con certeza")
        confidence = CONFIDENCE_LOW
        reason = "Hay fecha pero el encabezado no permite distinguir empresa de cargo con seguridad."
    else:
        confidence = CONFIDENCE_LOW
        reason = "Entrada sin encabezado legible, solo con fechas."

    for line in body:
        technology_match = _TECHNOLOGY_LINE_PATTERN.match(line)
        if technology_match:
            technology_parts.append(technology_match.group("value").strip())
            continue
        if _looks_like_technology_line(line):
            technology_parts.append(line)
            continue
        # El Issue distingue "responsabilidades" de "logros relevantes". Una
        # linea con vineta se propone como logro; el resto, como descripcion.
        if _BULLET_PREFIX.match(line):
            highlight_parts.append(_BULLET_PREFIX.sub("", line).strip())
            continue
        summary_parts.append(line.strip())

    if technology_parts:
        # Sin recorte: 400 caracteres podian cortar technologies a mitad de lista
        # sin dejar rastro. El exceso se rechaza al confirmar, con el campo nombrado.
        values["technologies"] = ", ".join(technology_parts)
    if summary_parts:
        values["summary"] = ". ".join(summary_parts)
    if highlight_parts:
        values["highlights"] = "\n".join(highlight_parts)

    if not values.get("end_date"):
        confidence = CONFIDENCE_LOW if confidence == CONFIDENCE_HIGH else confidence

    return StagedItem(
        key="experience.0",
        section="experience",
        values=values,
        source_text=" / ".join(block)[:600],
        confidence=confidence,
        reason=reason + (" Observaciones: " + "; ".join(notes) if notes else ""),
    )


_ROLE_TOKENS = (
    "developer", "engineer", "analyst", "architect", "manager", "lead", "senior",
    "junior", "desarrollador", "ingeniero", "analista", "arquitecto", "lider",
    "coordinador", "consultor", "administrador", "tecnico", "programador",
    "scientist", "specialist", "administrator", "director", "supervisor",
)


def _split_role_and_company(text: str) -> tuple[str, str] | None:
    """Separa cargo y empresa por un delimitador, en el orden mas probable.

    Solo devuelve algo cuando hay dos lados con contenido. Cuando el primer
    lado empieza por un termino tipico de cargo, se asume que el orden es
    `cargo, empresa`; en cualquier otro caso se invierte. La confianza nunca
    llega a alta: el orden correcto no es determinable sin entender la
    semantica, y adivinar en silencio seria inventar un dato.
    """

    for separator in (" -- ", " - ", " | ", ", ", " @ ", " en "):
        if separator not in text:
            continue
        left, _, right = text.partition(separator)
        left, right = left.strip(" -–—|·•"), right.strip(" -–—|·•")
        if not left or not right or len(right) > 120:
            continue

        left_normalized = normalize_for_matching(left)
        left_is_role = any(_matches_keyword(left_normalized, token) for token in _ROLE_TOKENS)
        if left_is_role:
            return left, right
        return right, left

    return None


def _strip_date_range(text: str) -> str:
    return DATE_RANGE_PATTERN.sub("", text).strip(" -–—|·•,").strip()


def _looks_like_technology_line(line: str) -> bool:
    """Distingue una lista de tecnologias de una frase que las menciona.

    Contar terminos tecnicos no alcanza: "Responsable de APIs en Python y
    FastAPI sobre Docker" menciona cuatro y es una descripcion. Lo que
    distingue a una lista es la forma: varios elementos separados por coma,
    punto y coma o barra vertical, en una linea corta.

    El Issue pide que una tecnologia mencionada dentro de una descripcion se
    sugiera pero no se cargue como confirmada. Por eso la forma manda.
    """

    if len(line) > 300:
        return False

    separators = len(re.findall(r"[,;|·]", line))
    if separators < 2:
        return False

    matches = sum(
        1
        for keywords in SKILL_CATEGORY_KEYWORDS.values()
        for keyword in keywords
        if _matches_keyword(line, keyword)
    )
    return matches >= 2


def _build_education_item(block: list[str]) -> StagedItem:
    values: dict[str, str] = {}
    notes: list[str] = []

    date_match = DATE_RANGE_PATTERN.search(block[0])
    if date_match:
        values["start_date"] = date_match.group("start")
        if date_match.group("end"):
            values["end_date"] = date_match.group("end")
        else:
            notes.append("La fecha de fin no se pudo determinar")

    remainder = _strip_date_range(block[0])
    if remainder:
        values["degree"] = remainder
        values["institution"] = block[1] if len(block) > 1 else ""
        confidence = CONFIDENCE_MEDIUM
        reason = "Formacion con rango de fechas. Verificar que el titulo y la institucion no esten invertidos."
    else:
        confidence = CONFIDENCE_LOW
        reason = "Entrada de formacion sin titulo legible."

    if len(block) > 2:
        values["summary"] = " ".join(block[2:])

    return StagedItem(
        key="education.0",
        section="education",
        values=values,
        source_text=" / ".join(block)[:600],
        confidence=confidence,
        reason=reason + (" Observaciones: " + "; ".join(notes) if notes else ""),
    )


def _build_skill_items(lines: list[str]) -> list[StagedItem]:
    collected: list[str] = []

    for line in lines:
        technology_match = _TECHNOLOGY_LINE_PATTERN.match(line)
        value = technology_match.group("value") if technology_match else line
        for chunk in _SKILL_SEPARATOR_PATTERN.split(value):
            candidate = chunk.strip(" .·•-–—|")
            if 1 < len(candidate) <= 60:
                collected.append(candidate)

    unique: list[str] = []
    for candidate in collected:
        normalized = candidate.lower()
        if normalized not in {existing.lower() for existing in unique}:
            unique.append(candidate)

    limite = _max_items("skills")
    items: list[StagedItem] = []
    overflow: list[str] = []

    # Los excedentes NO se descartan: van a revision para que la persona decida.
    # Recortarlos en silencio era perdida de informacion, que es exactamente lo
    # que el Issue #14 prohibe.
    for candidate in unique[:limite]:
        category = _categorize_skill(candidate)
        confidence = CONFIDENCE_HIGH if category else CONFIDENCE_MEDIUM
        reason = (
            f"Tecnologia reconocida en la categoria '{category}'."
            if category
            else "Termino listado como aptitud pero sin categoria deducible. Revisar la categoria."
        )
        items.append(
            StagedItem(
                key="skills.0",
                section="skills",
                values={"label": candidate, "category": category or ""},
                source_text=candidate[:200],
                confidence=confidence,
                reason=reason,
            )
        )

    overflow = list(unique[limite:])
    if overflow:
        items.append(
            StagedItem(
                key="skills.overflow",
                # Seccion propia: si fuera "skills", confirmarla la convertiria en
                # una skill mas y el payload tendria 41 elementos, que el schema
                # rechaza con skills_too_many_items.
                section="skills_overflow",
                values={"label": ", ".join(overflow), "category": ""},
                source_text=", ".join(overflow),
                confidence=CONFIDENCE_LOW,
                reason=(
                    f"El PDF lista mas tecnologias que las {limite} que admite el CV. "
                    "Separa con comas las que quieras conservar y editalas, o descarta "
                    "las que no apliquen."
                ),
            )
        )

    return items


def _matches_keyword(text: str, keyword: str) -> bool:
    """Coincidencia por token.

    Buscar por subcadena hacia que `postgres` matchee `sql` y `docker` matchee
    `go`, y clasifique mal technologies. Se exige que el token completo
    aparezca, y los simbolos como `c#` se comparan literalmente.
    """

    normalized = text.lower()
    keyword_lower = keyword.lower()
    if not keyword_lower[0].isalnum():
        return keyword_lower in normalized
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword_lower)}(?![A-Za-z0-9])", normalized) is not None


def _categorize_skill(skill: str) -> str | None:
    for category, keywords in SKILL_CATEGORY_KEYWORDS.items():
        if any(_matches_keyword(skill, keyword) for keyword in keywords):
            return category
    return None


def _build_language_items(lines: list[str]) -> list[StagedItem]:
    items: list[StagedItem] = []

    for line in lines:
        for chunk in _split_language_entries(line):
            name, level = _parse_language_entry(chunk)
            if not name:
                continue
            confidence = CONFIDENCE_HIGH if level else CONFIDENCE_MEDIUM
            reason = (
                "Idioma con nivel declarado en el PDF."
                if level
                else "Idioma detectado sin nivel. Se propone sin nivel para que lo completes."
            )
            items.append(
                StagedItem(
                    key="languages.0",
                    section="languages",
                    values={"name": name, "level": level},
                    source_text=chunk[:200],
                    confidence=confidence,
                    reason=reason,
                )
            )
            if len(items) >= MAX_LANGUAGES:
                return items

    return items


def _split_language_entries(line: str) -> list[str]:
    if ";" in line or "•" in line or "|" in line:
        return [chunk for chunk in re.split(r"\s*[;•|]\s*", line) if chunk.strip()]

    entries = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+){0,2}\s*[-–—(:]\s*[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 +/]{2,24}\)?", line)
    if entries:
        return entries

    stripped = line.strip()
    return [stripped] if stripped else []


def _parse_language_entry(entry: str) -> tuple[str, str]:
    normalized = normalize_for_matching(entry)
    level = ""
    # Un codigo CEFR explicito ("C1") es mas preciso que un adjetivo
    # ("advanced"), asi que se busca primero. Sin esto, "Advanced (C1)"
    # terminaba clasificado como C2.
    for label in ("C2", "C1", "B2", "B1", "A2", "A1"):
        if re.search(rf"(?<![A-Z0-9]){label}(?![A-Z0-9])", normalized):
            return re.split(r"[-–—(:(]", entry)[0].strip(), label

    for label, keywords in LANGUAGE_LEVEL_KEYWORDS.items():
        if label in ("C2", "C1", "B2", "B1", "A2", "A1"):
            continue
        if any(keyword.upper() in normalized for keyword in keywords):
            level = label
            break

    name = re.split(r"[-–—(:(]", entry)[0].strip()
    return name, level


def _build_certification_items(lines: list[str]) -> list[StagedItem]:
    items: list[StagedItem] = []

    for line in lines:
        chunks = _SKILL_SEPARATOR_PATTERN.split(line) if ";" in line or "•" in line else [line]
        for chunk in chunks:
            cleaned = _BULLET_PREFIX.sub("", chunk).strip()
            if not cleaned or len(cleaned) < 3:
                continue

            values: dict[str, str] = {"name": cleaned, "issuer": "", "date": ""}
            confidence = CONFIDENCE_MEDIUM
            reason = "Certificacion detectada en su seccion. Verificar institucion y fecha."

            date_match = DATE_RANGE_PATTERN.search(cleaned)
            if date_match:
                values["date"] = date_match.group("start")
                remainder = _strip_date_range(cleaned)
                if remainder and remainder != cleaned:
                    values["name"] = remainder
                    confidence = CONFIDENCE_HIGH
                    reason = "Certificacion con fecha explicita."

            if "," in values["name"] and not values["issuer"]:
                head, _, tail = values["name"].partition(",")
                values["name"] = head.strip()
                values["issuer"] = tail.strip()

            items.append(
                StagedItem(
                    key="certifications.0",
                    section="certifications",
                    values=values,
                    source_text=cleaned[:300],
                    confidence=confidence,
                    reason=reason,
                )
            )

    return items


def _build_project_items(lines: list[str]) -> list[StagedItem]:
    items: list[StagedItem] = []

    for line in lines:
        cleaned = _BULLET_PREFIX.sub("", line).strip()
        if not cleaned or len(cleaned) < 3:
            continue

        values = {"name": cleaned, "summary": "", "link": "", "technologies": ""}
        confidence = CONFIDENCE_MEDIUM
        reason = "Proyecto detectado en su seccion. El nombre puede ser la primera parte de la linea."

        separator_positions = [
            cleaned.find(separator)
            for separator in (" -- ", " - ", " – ", " — ", " | ")
            if cleaned.find(separator) > 0
        ]
        if separator_positions:
            split_at = min(separator_positions)
            values["name"] = cleaned[:split_at].strip()
            rest = cleaned[split_at + 3:].strip()
            if _looks_like_technology_line(rest):
                values["technologies"] = rest
                confidence = CONFIDENCE_HIGH
                reason = "Proyecto con nombre y tecnologias separados por un separador claro."
            else:
                values["summary"] = rest
        else:
            values["summary"] = cleaned

        link_match = URL_PATTERN.search(cleaned)
        if link_match:
            values["link"] = link_match.group(0).rstrip(".,;:)")

        items.append(
            StagedItem(
                key="projects.0",
                section="projects",
                values=values,
                source_text=cleaned[:400],
                confidence=confidence,
                reason=reason,
            )
        )

    return items


# --- Textos sin clasificar y conflictos -----------------------------------


def _collect_orphan_lines(
    segments: list[_Section],
    items: list[StagedItem],
    unclassified: list[str],
    fields: list[StagedField],
) -> None:
    """Todo texto que ningun extractor consumio viaja a revision.

    El Issue #14 es explicito: "La aplicacion no debe eliminar silenciosamente
    informacion extraida del PDF sin mostrarla antes al usuario". Por eso el
    criterio es de resta, no de seccion: se parte de todas las lineas del
    documento y se descuenta lo que ya quedo representado en algun campo o item.

    Sin esto, un PDF sin encabezados reconocibles —el caso mas comun de un CV
    bien maquetado con dos columnas— perdia el cien por cien del contenido.
    """

    consumed: set[str] = set()

    def _mark(text: str) -> None:
        if not text:
            return
        for line in text.replace(" / ", "\n").splitlines():
            cleaned = line.strip()
            if cleaned:
                consumed.add(cleaned)

    for staged_field in fields:
        _mark(staged_field.source_text)
    for staged_item in items:
        _mark(staged_item.source_text)

    seen: set[str] = set()
    for segment in segments:
        for line in segment.lines:
            cleaned = line.strip()
            if not cleaned or cleaned in seen:
                continue
            # Una linea corta sigue siendo contenido. `Python`, `AWS`, `SQL` y
            # `Go` son nombres normales en un CV, y el filtro por longitud los
            # descartaba sin que nada lo dijera: no llegaban ni a skills ni a
            # revision. Ahora solo se salta lo que no tiene ni una letra ni un
            # digito, que es decoracion, no informacion. El limite del documento
            # completo se comprueba antes de crear el borrador, asi que un PDF
            # con demasiadas lineas cortas se rechaza de forma controlada en vez
            # de recortarse en silencio.
            if not any(character.isalnum() for character in cleaned):
                continue
            if cleaned in consumed:
                continue
            if any(cleaned in text or text in cleaned for text in consumed):
                continue
            if EMAIL_PATTERN.search(cleaned) or URL_PATTERN.search(cleaned):
                continue
            if DATE_RANGE_PATTERN.search(cleaned) and len(cleaned) < 40:
                continue
            seen.add(cleaned)
            # Sin recorte por linea: el unico limite es el total del documento,
            # que se comprueba antes de crear el borrador. Recortar cada linea
            # perderia informacion sin que nada lo dijera.
            unclassified.append(cleaned)


def _detect_conflicts(fields: list[StagedField], items: list[StagedItem]) -> list[StagedConflict]:
    conflicts: list[StagedConflict] = []

    by_key: dict[str, list[str]] = {}
    for staged_field in fields:
        by_key.setdefault(staged_field.key, []).append(staged_field.value)

    for key, values in by_key.items():
        distinct = {value.strip().lower() for value in values if value.strip()}
        if len(distinct) > 1:
            conflicts.append(
                StagedConflict(
                    key=key,
                    reason="El PDF menciona valores distintos para el mismo campo.",
                    candidates=tuple(values),
                )
            )

    return conflicts