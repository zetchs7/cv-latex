from dataclasses import dataclass
from datetime import UTC, datetime
import json

from app.models import CV
from app.schemas import CVFormData


CURRENT_STRUCTURED_SCHEMA_VERSION = 2
STRUCTURED_PAYLOAD_STATUS_LEGACY = "legacy"
STRUCTURED_PAYLOAD_STATUS_VALID = "valid"
STRUCTURED_PAYLOAD_STATUS_INVALID = "invalid"
STRUCTURED_PAYLOAD_STATUS_STALE = "stale"


@dataclass(frozen=True)
class StructuredCVState:
    mode: str
    is_structured: bool
    reason: str


@dataclass(frozen=True)
class StructuredPayloadValidation:
    is_valid: bool
    errors: tuple[str, ...]


LegacyCVInput = CV | CVFormData


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

    validation = validate_structured_payload_v2(payload)
    if not validation.is_valid:
        return StructuredCVState(mode="legacy", is_structured=False, reason="payload_invalid")

    return StructuredCVState(mode="structured", is_structured=True, reason="payload_valid")


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


def build_structured_payload_from_legacy(
    legacy_cv: LegacyCVInput,
    *,
    metadata_source: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": CURRENT_STRUCTURED_SCHEMA_VERSION,
        "personal": {
            "full_name": legacy_cv.full_name,
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
        "metadata": {
            "source": metadata_source,
            "synced_from_legacy_at": _current_utc_timestamp(),
        },
    }
    validation = validate_structured_payload_v2(payload)
    if not validation.is_valid:
        joined_errors = "; ".join(validation.errors)
        raise ValueError(f"Payload estructurado invalido: {joined_errors}")

    return payload


def serialize_structured_payload(payload: dict[str, object]) -> str:
    validation = validate_structured_payload_v2(payload)
    if not validation.is_valid:
        joined_errors = "; ".join(validation.errors)
        raise ValueError(f"Payload estructurado invalido: {joined_errors}")

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deserialize_structured_payload(raw_payload: str) -> dict[str, object] | None:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def validate_structured_payload_v2(payload: object) -> StructuredPayloadValidation:
    errors: list[str] = []

    if not isinstance(payload, dict):
        return StructuredPayloadValidation(False, ("payload_must_be_object",))

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int):
        errors.append("schema_version_must_be_integer")
    elif schema_version < CURRENT_STRUCTURED_SCHEMA_VERSION:
        errors.append("schema_version_unsupported")

    _require_object(payload, "personal", errors)
    _require_object(payload, "contact", errors)
    _require_string(payload, "summary", errors)
    _require_object(payload, "metadata", errors)

    for list_field in (
        "skills",
        "experience",
        "education",
        "certifications",
        "languages",
        "projects",
        "links",
    ):
        _require_list(payload, list_field, errors)

    _validate_ordered_items(payload.get("skills"), "skills", errors, required_text_field="label")
    _validate_ordered_items(payload.get("experience"), "experience", errors, required_text_field="summary")
    _validate_ordered_items(payload.get("education"), "education", errors, required_text_field="summary")

    return StructuredPayloadValidation(is_valid=not errors, errors=tuple(errors))


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


def _current_utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _require_object(payload: dict[str, object], field_name: str, errors: list[str]) -> None:
    if not isinstance(payload.get(field_name), dict):
        errors.append(f"{field_name}_must_be_object")


def _require_string(payload: dict[str, object], field_name: str, errors: list[str]) -> None:
    if not isinstance(payload.get(field_name), str):
        errors.append(f"{field_name}_must_be_string")


def _require_list(payload: dict[str, object], field_name: str, errors: list[str]) -> None:
    if not isinstance(payload.get(field_name), list):
        errors.append(f"{field_name}_must_be_list")


def _validate_ordered_items(
    items: object,
    field_name: str,
    errors: list[str],
    *,
    required_text_field: str,
) -> None:
    if not isinstance(items, list):
        return

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{field_name}_{index}_must_be_object")
            continue
        if not isinstance(item.get(required_text_field), str):
            errors.append(f"{field_name}_{index}_{required_text_field}_must_be_string")
        if not isinstance(item.get("order"), int):
            errors.append(f"{field_name}_{index}_order_must_be_integer")
