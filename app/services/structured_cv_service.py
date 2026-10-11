from dataclasses import dataclass
from datetime import UTC, datetime
import json

from app.models import CV
from app.schemas import CVFormData
from app.validations.cv_validations import build_cv_form_data, validate_cv_form
from app.validations.structured_cv_validations import (
    CURRENT_STRUCTURED_SCHEMA_VERSION,
    StructuredPayloadValidation,
    normalize_structured_payload_v2,
    validate_structured_payload_v2,
)


STRUCTURED_PAYLOAD_STATUS_LEGACY = "legacy"
STRUCTURED_PAYLOAD_STATUS_VALID = "valid"
STRUCTURED_PAYLOAD_STATUS_INVALID = "invalid"
STRUCTURED_PAYLOAD_STATUS_STALE = "stale"

MAX_STRUCTURED_PAYLOAD_BYTES = 512 * 1024
MAX_METADATA_SOURCE_LENGTH = 60

NON_FINITE_JSON_CONSTANT_ERROR = (
    "El contenido estructurado contiene el valor numerico no estandar "
    "'{constant}', que no es JSON valido."
)


@dataclass(frozen=True)
class StructuredCVState:
    mode: str
    is_structured: bool
    reason: str


@dataclass(frozen=True)
class NormalizedCV:
    """Representacion normalizada unica de un CV para todos los consumidores.

    `sections` siempre expone la forma completa del payload v2 (secciones
    completas, incluyendo campos solo-estructurados), ya sea desde el payload
    estructurado valido o derivada de los campos legacy.
    `legacy_snapshot` expone la proyeccion plana compatible con rutas, LaTeX,
    PDF y ATS existentes. Ningun consumidor debe leer payload y campos planos
    por separado.
    """

    cv_id: int
    title: str
    mode: str
    is_structured: bool
    reason: str
    sections: dict[str, object]
    legacy_snapshot: CVFormData


class StructuredCVWriteError(ValueError):
    def __init__(self, message: str, errors: tuple[str, ...] = ()):
        super().__init__(message)
        self.errors = tuple(errors)


@dataclass(frozen=True)
class StructuredCVWriteBundle:
    form_data: CVFormData
    payload: dict[str, object]
    serialized_payload: str
    structured_columns: dict[str, object]


LegacyCVInput = CV | CVFormData


def resolve_normalized_cv(cv: CV) -> NormalizedCV:
    state = resolve_structured_cv_state(cv)

    if state.is_structured:
        payload = deserialize_structured_payload(cv.structured_payload)
        normalized_payload = normalize_structured_payload_v2(
            payload,
            declared_schema_version=cv.structured_schema_version,
        )
        if normalized_payload is not None:
            snapshot = build_legacy_snapshot_from_payload(normalized_payload, title=cv.title)
            return NormalizedCV(
                cv_id=cv.id,
                title=cv.title,
                mode=state.mode,
                is_structured=True,
                reason=state.reason,
                sections=normalized_payload,
                legacy_snapshot=snapshot,
            )

    sections = build_structured_sections_from_legacy(cv)
    snapshot = _build_legacy_snapshot_from_cv(cv)
    return NormalizedCV(
        cv_id=cv.id,
        title=cv.title,
        mode=state.mode,
        is_structured=False,
        reason=state.reason,
        sections=sections,
        legacy_snapshot=snapshot,
    )


def resolve_structured_cv_state(cv: CV) -> StructuredCVState:
    return resolve_structured_payload_state(
        structured_schema_version=cv.structured_schema_version,
        structured_payload=cv.structured_payload,
        structured_payload_status=cv.structured_payload_status,
    )


def resolve_structured_payload_state(
    *,
    structured_schema_version: int | None,
    structured_payload: str | None,
    structured_payload_status: str | None,
) -> StructuredCVState:
    if structured_schema_version is None or structured_schema_version < CURRENT_STRUCTURED_SCHEMA_VERSION:
        return StructuredCVState(mode="legacy", is_structured=False, reason="schema_version_legacy_or_missing")

    if structured_payload_status != STRUCTURED_PAYLOAD_STATUS_VALID:
        return StructuredCVState(mode="legacy", is_structured=False, reason="payload_not_marked_valid")

    if not structured_payload:
        return StructuredCVState(mode="legacy", is_structured=False, reason="payload_missing")

    payload = deserialize_structured_payload(structured_payload)
    if payload is None:
        return StructuredCVState(mode="legacy", is_structured=False, reason="payload_invalid")

    validation = validate_structured_payload_v2(
        payload,
        declared_schema_version=structured_schema_version,
    )
    if not validation.is_valid:
        return StructuredCVState(mode="legacy", is_structured=False, reason="payload_invalid")

    return StructuredCVState(mode="structured", is_structured=True, reason="payload_valid")


def build_structured_payload_from_legacy(
    legacy_cv: LegacyCVInput,
    *,
    metadata_source: str,
) -> dict[str, object]:
    payload = _build_sections_from_legacy_fields(
        legacy_cv,
        metadata_source=metadata_source,
        synced_from_legacy_at=_current_utc_timestamp(),
    )
    validation = validate_structured_payload_v2(payload)
    if not validation.is_valid:
        joined_errors = "; ".join(validation.errors)
        raise ValueError(f"Payload estructurado invalido: {joined_errors}")

    return payload


def build_structured_sections_from_legacy(legacy_cv: LegacyCVInput) -> dict[str, object]:
    """Deriva la vista de secciones v2 desde campos legacy sin validar para persistencia.

    Es una proyeccion de lectura: preserva el contenido legacy completo sin
    truncar y sin estampar marcas de sincronizacion.
    """
    return _build_sections_from_legacy_fields(
        legacy_cv,
        metadata_source="legacy_view",
        synced_from_legacy_at="",
    )


def build_legacy_snapshot_from_payload(payload: dict[str, object], *, title: str) -> CVFormData:
    """Deriva el snapshot plano legacy desde un payload v2 normalizado.

    Reglas explicitas (sin truncamiento silencioso):
    - personal.full_name -> full_name
    - contact.email/phone -> email/phone
    - summary -> professional_summary
    - skills: labels unidos con ", " en orden (order, posicion)
    - experience/education: bloques formateados y unidos con linea vacia
    - headline, certifications, languages, projects, links, additional_info y
      metadata viven solo en el payload; el snapshot no los destruye.
    """
    personal = payload.get("personal") or {}
    contact = payload.get("contact") or {}
    raw_values = {
        "title": title,
        "full_name": _string_value(personal.get("full_name")),
        "email": _string_value(contact.get("email")),
        "phone": _string_value(contact.get("phone")),
        "professional_summary": _string_value(payload.get("summary")),
        "experience_summary": _format_experience_section(payload.get("experience")),
        "education_summary": _format_education_section(payload.get("education")),
        "skills": _format_skill_labels(payload.get("skills")),
    }
    return build_cv_form_data(raw_values)


def build_structured_cv_write_bundle(
    *,
    title: str,
    payload: object,
    metadata_source: str,
) -> StructuredCVWriteBundle:
    """Valida un write estructurado completo antes de cualquier persistencia.

    Rechaza con `StructuredCVWriteError` si el payload v2 es invalido, si el
    snapshot legacy derivado viola las validaciones existentes (sin truncar
    contenido) o si el payload serializado supera el maximo de bytes.
    """
    if not metadata_source or len(metadata_source) > MAX_METADATA_SOURCE_LENGTH:
        raise StructuredCVWriteError(
            "El origen de metadata del payload estructurado es invalido.",
            ("metadata_source_invalid",),
        )

    validation = validate_structured_payload_v2(payload)
    if not validation.is_valid or validation.normalized_payload is None:
        joined_errors = "; ".join(validation.errors)
        raise StructuredCVWriteError(
            f"Payload estructurado invalido: {joined_errors}",
            validation.errors,
        )

    normalized_payload = dict(validation.normalized_payload)
    metadata = dict(normalized_payload.get("metadata") or {})
    metadata["source"] = metadata_source
    metadata["synced_from_legacy_at"] = _current_utc_timestamp()
    normalized_payload["metadata"] = metadata

    snapshot = build_legacy_snapshot_from_payload(normalized_payload, title=title)
    snapshot_errors = validate_cv_form(snapshot)
    if snapshot_errors:
        error_details = tuple(f"{field}: {message}" for field, message in snapshot_errors.items())
        joined_details = "; ".join(error_details)
        raise StructuredCVWriteError(
            f"El payload estructurado no genera un CV legacy valido: {joined_details}",
            error_details,
        )

    serialized_payload = serialize_structured_payload(normalized_payload)

    return StructuredCVWriteBundle(
        form_data=snapshot,
        payload=normalized_payload,
        serialized_payload=serialized_payload,
        structured_columns={
            "structured_schema_version": CURRENT_STRUCTURED_SCHEMA_VERSION,
            "structured_payload": serialized_payload,
            "structured_payload_status": STRUCTURED_PAYLOAD_STATUS_VALID,
        },
    )


def build_legacy_structured_columns() -> dict[str, object]:
    return {
        "structured_schema_version": None,
        "structured_payload": None,
        "structured_payload_status": STRUCTURED_PAYLOAD_STATUS_LEGACY,
    }


def build_valid_structured_columns_from_legacy(
    legacy_cv: LegacyCVInput,
    *,
    metadata_source: str,
) -> dict[str, object]:
    payload = build_structured_payload_from_legacy(legacy_cv, metadata_source=metadata_source)
    serialized_payload = serialize_structured_payload(payload)

    return {
        "structured_schema_version": CURRENT_STRUCTURED_SCHEMA_VERSION,
        "structured_payload": serialized_payload,
        "structured_payload_status": STRUCTURED_PAYLOAD_STATUS_VALID,
    }


def build_stale_structured_columns(raw_payload: str | None = None) -> dict[str, object]:
    return {
        "structured_schema_version": CURRENT_STRUCTURED_SCHEMA_VERSION,
        "structured_payload": raw_payload,
        "structured_payload_status": STRUCTURED_PAYLOAD_STATUS_STALE,
    }


def build_invalid_structured_columns(raw_payload: str | None = None) -> dict[str, object]:
    return {
        "structured_schema_version": CURRENT_STRUCTURED_SCHEMA_VERSION,
        "structured_payload": raw_payload,
        "structured_payload_status": STRUCTURED_PAYLOAD_STATUS_INVALID,
    }


def reject_non_finite_json_constant(constant: str) -> float:
    """Rechaza las constantes JSON no estandar `NaN`, `Infinity` y `-Infinity`.

    `json.loads` las acepta por defecto aunque JSON no las define. Si
    sobreviven a una importacion, el validador las preserva como claves
    desconocidas, se persisten, el export las reemite y el `JSON.parse`
    del navegador rechaza el bootstrap del editor, dejando el modulo
    inutilizable. Este helper se pasa como `parse_constant` en cada
    punto de entrada JSON no confiable.
    """
    raise ValueError(NON_FINITE_JSON_CONSTANT_ERROR.format(constant=constant))


def serialize_structured_payload(payload: dict[str, object]) -> str:
    """Serializa y valida un payload v2 para persistencia.

    Lanza `StructuredCVWriteError` (subclase de `ValueError`) tanto para un
    payload invalido como para uno que excede `MAX_STRUCTURED_PAYLOAD_BYTES`,
    para que los llamadores manejen un unico error de dominio y la escritura
    se corte antes de tocar la base.
    """
    validation = validate_structured_payload_v2(payload)
    if not validation.is_valid:
        joined_errors = "; ".join(validation.errors)
        raise ValueError(f"Payload estructurado invalido: {joined_errors}")

    try:
        serialized_payload = json.dumps(
            validation.normalized_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except ValueError as error:
        raise StructuredCVWriteError(
            NON_FINITE_JSON_CONSTANT_ERROR.format(constant="NaN, Infinity o -Infinity"),
            ("structured_payload_non_finite_number",),
        ) from error
    if len(serialized_payload.encode("utf-8")) > MAX_STRUCTURED_PAYLOAD_BYTES:
        raise StructuredCVWriteError(
            f"El contenido estructurado supera el maximo de {MAX_STRUCTURED_PAYLOAD_BYTES // 1024} KB.",
            ("structured_payload_too_large",),
        )

    return serialized_payload


def deserialize_structured_payload(raw_payload: str) -> dict[str, object] | None:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def _build_sections_from_legacy_fields(
    legacy_cv: LegacyCVInput,
    *,
    metadata_source: str,
    synced_from_legacy_at: str,
) -> dict[str, object]:
    return {
        "schema_version": CURRENT_STRUCTURED_SCHEMA_VERSION,
        "personal": {
            "full_name": legacy_cv.full_name,
            "headline": "",
            "location": "",
        },
        "contact": {
            "email": legacy_cv.email,
            "phone": legacy_cv.phone,
            "links": [],
        },
        "summary": legacy_cv.professional_summary,
        "skills": _build_skill_items(legacy_cv.skills),
        "experience": _build_text_section_items(legacy_cv.experience_summary),
        "education": _build_text_section_items(legacy_cv.education_summary),
        "certifications": [],
        "languages": [],
        "projects": [],
        "links": [],
        "additional_info": [],
        "metadata": {
            "source": metadata_source,
            "synced_from_legacy_at": synced_from_legacy_at,
        },
    }


def _build_legacy_snapshot_from_cv(cv: CV) -> CVFormData:
    return CVFormData(
        title=cv.title,
        full_name=cv.full_name,
        email=cv.email,
        phone=cv.phone,
        professional_summary=cv.professional_summary,
        experience_summary=cv.experience_summary,
        education_summary=cv.education_summary,
        skills=cv.skills,
    )


def _build_skill_items(raw_skills: str) -> list[dict[str, object]]:
    skill_labels = [item for item in _split_legacy_text_items(raw_skills) if item]
    return [
        {
            "label": label,
            "category": "",
            "level": "",
            "order": index,
        }
        for index, label in enumerate(skill_labels, start=1)
    ]


def _build_text_section_items(raw_text: str) -> list[dict[str, object]]:
    text = raw_text.strip()
    if not text:
        return []

    return [
        {
            "summary": text,
            "order": 1,
        }
    ]


def _split_legacy_text_items(raw_text: str) -> list[str]:
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace(";", "\n").replace(",", "\n")
    return [item.strip() for item in normalized.split("\n") if item.strip()]


def _format_skill_labels(raw_items: object) -> str:
    return ", ".join(
        label
        for label in (_item_string(item, "label") for item in _sorted_items(raw_items))
        if label
    )


def _format_experience_section(raw_items: object) -> str:
    return "\n\n".join(
        block
        for block in (_format_experience_item(item) for item in _sorted_items(raw_items))
        if block
    )


def _format_education_section(raw_items: object) -> str:
    return "\n\n".join(
        block
        for block in (_format_education_item(item) for item in _sorted_items(raw_items))
        if block
    )


def _format_experience_item(item: object) -> str:
    if not isinstance(item, dict):
        return ""

    header = " - ".join(
        part
        for part in (_item_string(item, "role"), _item_string(item, "company"))
        if part
    )
    date_range = _format_date_range(item)
    if header and date_range:
        header = f"{header} ({date_range})"
    elif not header:
        header = date_range

    lines = [header] if header else []

    summary = _item_string(item, "summary")
    if summary:
        lines.append(summary)

    highlights = item.get("highlights")
    if isinstance(highlights, list):
        for highlight in highlights:
            if isinstance(highlight, str) and highlight:
                lines.append(f"• {highlight}")

    technologies = ", ".join(
        technology
        for technology in (item.get("technologies") or [])
        if isinstance(technology, str) and technology
    )
    if technologies:
        lines.append(f"Tecnologias: {technologies}")

    return "\n".join(lines)


def _format_education_item(item: object) -> str:
    if not isinstance(item, dict):
        return ""

    header = " - ".join(
        part
        for part in (_item_string(item, "degree"), _item_string(item, "institution"))
        if part
    )
    date_range = _format_date_range(item)
    if header and date_range:
        header = f"{header} ({date_range})"
    elif not header:
        header = date_range

    lines = [header] if header else []

    field = _item_string(item, "field")
    if field:
        lines.append(f"Campo: {field}")

    summary = _item_string(item, "summary")
    if summary:
        lines.append(summary)

    return "\n".join(lines)


def _format_date_range(item: dict[str, object]) -> str:
    start_date = _item_string(item, "start_date")
    end_date = _item_string(item, "end_date")
    if item.get("current") is True:
        end_date = "Presente"
    if start_date and end_date:
        return f"{start_date} - {end_date}"
    return start_date or end_date


def _sorted_items(raw_items: object) -> list[object]:
    items = raw_items if isinstance(raw_items, list) else []
    return [
        item
        for _, item in sorted(
            enumerate(items),
            key=lambda pair: (_item_order(pair[1], pair[0]), pair[0]),
        )
    ]


def _item_order(item: object, fallback_index: int) -> int:
    if isinstance(item, dict):
        order = item.get("order")
        if isinstance(order, int) and not isinstance(order, bool):
            return order
    return fallback_index + 1


def _item_string(item: object, field: str) -> str:
    if isinstance(item, dict):
        value = item.get(field)
        if isinstance(value, str):
            return value
    return ""


def _string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def _current_utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
