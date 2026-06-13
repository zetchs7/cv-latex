from dataclasses import dataclass
import json

from app.models import CV


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

    if not _payload_json_is_valid(structured_payload):
        return StructuredCVState(mode="legacy", is_structured=False, reason="payload_invalid")

    return StructuredCVState(mode="structured", is_structured=True, reason="payload_valid")


def build_legacy_structured_columns() -> dict[str, object]:
    return {
        "structured_schema_version": None,
        "structured_payload": None,
        "structured_payload_status": STRUCTURED_PAYLOAD_STATUS_LEGACY,
    }


def _payload_json_is_valid(raw_payload: str) -> bool:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return False

    if not isinstance(payload, dict):
        return False

    payload_schema_version = payload.get("schema_version")
    if payload_schema_version is not None and not isinstance(payload_schema_version, int):
        return False
    if payload_schema_version is not None and payload_schema_version < CURRENT_STRUCTURED_SCHEMA_VERSION:
        return False

    return True
