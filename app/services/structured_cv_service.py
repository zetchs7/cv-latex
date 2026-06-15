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
    normalized_payload: dict[str, object] | None = None


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

    validation = validate_structured_payload_v2(
        payload,
        declared_schema_version=structured_schema_version,
    )
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

    return json.dumps(validation.normalized_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deserialize_structured_payload(raw_payload: str) -> dict[str, object] | None:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def validate_structured_payload_v2(
    payload: object,
    *,
    declared_schema_version: int | None = None,
) -> StructuredPayloadValidation:
    normalized_payload, errors = _normalize_structured_payload_v2(
        payload,
        declared_schema_version=declared_schema_version,
    )
    return StructuredPayloadValidation(
        is_valid=not errors,
        errors=tuple(errors),
        normalized_payload=normalized_payload,
    )


def normalize_structured_payload_v2(
    payload: object,
    *,
    declared_schema_version: int | None = None,
) -> dict[str, object] | None:
    validation = validate_structured_payload_v2(
        payload,
        declared_schema_version=declared_schema_version,
    )
    return validation.normalized_payload


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


def _normalize_structured_payload_v2(
    payload: object,
    *,
    declared_schema_version: int | None,
) -> tuple[dict[str, object] | None, list[str]]:
    errors: list[str] = []

    if not isinstance(payload, dict):
        return None, ["payload_must_be_object"]

    if declared_schema_version is not None:
        if not isinstance(declared_schema_version, int):
            return None, ["schema_version_must_be_integer"]
        if declared_schema_version != CURRENT_STRUCTURED_SCHEMA_VERSION:
            return None, ["schema_version_unsupported"]

    schema_version_present = "schema_version" in payload
    schema_version = payload["schema_version"] if schema_version_present else _MISSING_SCHEMA_VERSION
    normalized_schema_version = _resolve_payload_schema_version(
        schema_version,
        schema_version_present=schema_version_present,
        declared_schema_version=declared_schema_version,
        errors=errors,
    )
    if normalized_schema_version is not None and normalized_schema_version < CURRENT_STRUCTURED_SCHEMA_VERSION:
        errors.append("schema_version_unsupported")

    if errors:
        return None, errors

    normalized_payload = dict(payload)
    normalized_payload["schema_version"] = normalized_schema_version
    normalized_payload["personal"] = _normalize_object_field(
        payload,
        "personal",
        errors,
        defaults={
            "full_name": "",
            "headline": "",
            "location": "",
        },
    )
    normalized_payload["contact"] = _normalize_object_field(
        payload,
        "contact",
        errors,
        defaults={
            "email": "",
            "phone": "",
            "links": [],
        },
    )
    normalized_payload["metadata"] = _normalize_object_field(
        payload,
        "metadata",
        errors,
        defaults={
            "source": "",
            "synced_from_legacy_at": "",
        },
    )
    normalized_payload["summary"] = _normalize_string_field(payload, "summary", errors, default="")
    normalized_payload["skills"] = _normalize_structured_items(
        payload,
        "skills",
        errors,
        defaults={
            "label": "",
            "category": "",
            "level": "",
        },
    )
    normalized_payload["experience"] = _normalize_structured_items(
        payload,
        "experience",
        errors,
        defaults={"summary": ""},
    )
    normalized_payload["education"] = _normalize_structured_items(
        payload,
        "education",
        errors,
        defaults={"summary": ""},
    )

    for list_field in ("certifications", "languages", "projects", "links"):
        normalized_payload[list_field] = _normalize_list_field(payload, list_field, errors)

    if errors:
        return None, errors

    return normalized_payload, errors


def _normalize_object_field(
    payload: dict[str, object],
    field_name: str,
    errors: list[str],
    *,
    defaults: dict[str, object],
) -> dict[str, object]:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return dict(defaults)
    if not isinstance(raw_value, dict):
        errors.append(f"{field_name}_must_be_object")
        return dict(defaults)

    normalized_value = dict(raw_value)
    for key, default_value in defaults.items():
        current_value = normalized_value.get(key)
        if current_value is None:
            normalized_value[key] = default_value
            continue
        if isinstance(default_value, list):
            if not isinstance(current_value, list):
                errors.append(f"{field_name}_{key}_must_be_list")
        elif not isinstance(current_value, str):
            errors.append(f"{field_name}_{key}_must_be_string")

    return normalized_value


def _normalize_string_field(
    payload: dict[str, object],
    field_name: str,
    errors: list[str],
    *,
    default: str,
) -> str:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return default
    if not isinstance(raw_value, str):
        errors.append(f"{field_name}_must_be_string")
        return default
    return raw_value


def _normalize_list_field(payload: dict[str, object], field_name: str, errors: list[str]) -> list[object]:
    raw_value = payload.get(field_name)
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        errors.append(f"{field_name}_must_be_list")
        return []
    return list(raw_value)


def _normalize_structured_items(
    payload: dict[str, object],
    field_name: str,
    errors: list[str],
    *,
    defaults: dict[str, str],
) -> list[dict[str, object]]:
    raw_items = payload.get(field_name)
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        errors.append(f"{field_name}_must_be_list")
        return []

    normalized_items: list[dict[str, object]] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            errors.append(f"{field_name}_{index - 1}_must_be_object")
            continue

        normalized_item = dict(item)
        for key, default_value in defaults.items():
            current_value = normalized_item.get(key)
            if current_value is None:
                normalized_item[key] = default_value
                continue
            if not isinstance(current_value, str):
                errors.append(f"{field_name}_{index - 1}_{key}_must_be_string")

        current_order = normalized_item.get("order")
        if current_order is None:
            normalized_item["order"] = index
        elif not isinstance(current_order, int):
            errors.append(f"{field_name}_{index - 1}_order_must_be_integer")

        normalized_items.append(normalized_item)

    return normalized_items


def _resolve_payload_schema_version(
    payload_schema_version: object,
    *,
    schema_version_present: bool,
    declared_schema_version: int | None,
    errors: list[str],
) -> int | None:
    if not schema_version_present:
        if declared_schema_version is None:
            errors.append("schema_version_missing")
            return None
        if not isinstance(declared_schema_version, int):
            errors.append("schema_version_must_be_integer")
            return None
        if declared_schema_version != CURRENT_STRUCTURED_SCHEMA_VERSION:
            errors.append("schema_version_unsupported")
            return None
        return declared_schema_version

    if payload_schema_version is None:
        errors.append("schema_version_must_be_integer")
        return None

    if not isinstance(payload_schema_version, int):
        errors.append("schema_version_must_be_integer")
        return None

    if payload_schema_version != CURRENT_STRUCTURED_SCHEMA_VERSION:
        errors.append("schema_version_unsupported")
        return None

    return payload_schema_version


_MISSING_SCHEMA_VERSION = object()
