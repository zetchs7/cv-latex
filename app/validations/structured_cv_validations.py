"""Validacion y normalizacion estricta del payload estructurado schema v2.

Contrato unico para `structured_payload`:
- Solo schema 2 es aceptado; versiones futuras o menores nunca se tratan como 2.
- Los payloads parciales previamente aceptados siguen siendo validos: las
  secciones faltantes se normalizan con defaults vacios.
- Si la fila declara `structured_schema_version = 2`, un payload sin
  `schema_version` interno se normaliza agregando `schema_version = 2`.
- Los campos conocidos se validan por tipo, longitud acotada y orden entero.
- Las claves extra (campos solo-estructurados o desconocidos) se preservan
  sin validarse para no perder contenido.
"""

from dataclasses import dataclass


CURRENT_STRUCTURED_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class StringFieldSpec:
    field: str
    max_length: int
    default: str = ""


@dataclass(frozen=True)
class StringListFieldSpec:
    field: str
    item_max_length: int
    max_items: int


@dataclass(frozen=True)
class ItemSectionSpec:
    max_items: int
    string_fields: tuple[StringFieldSpec, ...] = ()
    boolean_fields: tuple[str, ...] = ()
    string_list_fields: tuple[StringListFieldSpec, ...] = ()


@dataclass(frozen=True)
class StructuredPayloadValidation:
    is_valid: bool
    errors: tuple[str, ...]
    normalized_payload: dict[str, object] | None = None


OBJECT_SECTION_SPECS: dict[str, tuple[StringFieldSpec, ...]] = {
    "personal": (
        StringFieldSpec("full_name", 160),
        StringFieldSpec("headline", 160),
        StringFieldSpec("location", 160),
    ),
    "contact": (
        StringFieldSpec("email", 180),
        StringFieldSpec("phone", 80),
    ),
    "metadata": (
        StringFieldSpec("source", 60),
        StringFieldSpec("synced_from_legacy_at", 60),
    ),
}

CONTACT_LINKS_SPEC = StringListFieldSpec("links", 300, 10)

STRING_SECTION_SPECS: dict[str, int] = {
    "summary": 1200,
}

ITEM_SECTION_SPECS: dict[str, ItemSectionSpec] = {
    "skills": ItemSectionSpec(
        max_items=40,
        string_fields=(
            StringFieldSpec("label", 120),
            StringFieldSpec("category", 80),
            StringFieldSpec("level", 80),
        ),
    ),
    "experience": ItemSectionSpec(
        max_items=30,
        string_fields=(
            StringFieldSpec("company", 120),
            StringFieldSpec("role", 120),
            StringFieldSpec("location", 120),
            StringFieldSpec("start_date", 40),
            StringFieldSpec("end_date", 40),
            StringFieldSpec("summary", 600),
        ),
        boolean_fields=("current",),
        string_list_fields=(
            StringListFieldSpec("highlights", 240, 12),
            StringListFieldSpec("technologies", 60, 16),
        ),
    ),
    "education": ItemSectionSpec(
        max_items=30,
        string_fields=(
            StringFieldSpec("institution", 160),
            StringFieldSpec("degree", 160),
            StringFieldSpec("field", 120),
            StringFieldSpec("start_date", 40),
            StringFieldSpec("end_date", 40),
            StringFieldSpec("summary", 600),
        ),
    ),
    "certifications": ItemSectionSpec(
        max_items=30,
        string_fields=(
            StringFieldSpec("name", 160),
            StringFieldSpec("issuer", 120),
            StringFieldSpec("date", 40),
        ),
    ),
    "languages": ItemSectionSpec(
        max_items=20,
        string_fields=(
            StringFieldSpec("name", 60),
            StringFieldSpec("level", 60),
        ),
    ),
    "projects": ItemSectionSpec(
        max_items=30,
        string_fields=(
            StringFieldSpec("name", 160),
            StringFieldSpec("summary", 600),
            StringFieldSpec("link", 300),
        ),
        string_list_fields=(StringListFieldSpec("technologies", 60, 16),),
    ),
    "links": ItemSectionSpec(
        max_items=30,
        string_fields=(
            StringFieldSpec("label", 80),
            StringFieldSpec("url", 300),
        ),
    ),
    "additional_info": ItemSectionSpec(
        max_items=20,
        string_fields=(
            StringFieldSpec("title", 120),
            StringFieldSpec("content", 600),
        ),
    ),
}

STRUCTURED_ITEM_SECTIONS = tuple(ITEM_SECTION_SPECS)


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


_MISSING_SCHEMA_VERSION = object()


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

    for section_name, field_specs in OBJECT_SECTION_SPECS.items():
        normalized_payload[section_name] = _normalize_object_section(
            payload,
            section_name,
            field_specs,
            errors,
        )

    contact_section = normalized_payload["contact"]
    if isinstance(contact_section, dict):
        contact_section["links"] = _normalize_string_list_value(
            contact_section.get("links"),
            "contact_links",
            CONTACT_LINKS_SPEC,
            errors,
        )

    for section_name, max_length in STRING_SECTION_SPECS.items():
        normalized_payload[section_name] = _normalize_string_section(
            payload,
            section_name,
            max_length,
            errors,
        )

    for section_name, section_spec in ITEM_SECTION_SPECS.items():
        normalized_payload[section_name] = _normalize_item_section(
            payload,
            section_name,
            section_spec,
            errors,
        )

    if errors:
        return None, errors

    return normalized_payload, errors


def _normalize_object_section(
    payload: dict[str, object],
    section_name: str,
    field_specs: tuple[StringFieldSpec, ...],
    errors: list[str],
) -> dict[str, object]:
    raw_value = payload.get(section_name)
    defaults = {field_spec.field: field_spec.default for field_spec in field_specs}
    if raw_value is None:
        return defaults
    if not isinstance(raw_value, dict):
        errors.append(f"{section_name}_must_be_object")
        return defaults

    normalized_value = dict(raw_value)
    for field_spec in field_specs:
        current_value = normalized_value.get(field_spec.field)
        if current_value is None:
            normalized_value[field_spec.field] = field_spec.default
        elif not isinstance(current_value, str):
            errors.append(f"{section_name}_{field_spec.field}_must_be_string")
        elif len(current_value) > field_spec.max_length:
            errors.append(f"{section_name}_{field_spec.field}_too_long")

    return normalized_value


def _normalize_string_section(
    payload: dict[str, object],
    section_name: str,
    max_length: int,
    errors: list[str],
) -> str:
    raw_value = payload.get(section_name)
    if raw_value is None:
        return ""
    if not isinstance(raw_value, str):
        errors.append(f"{section_name}_must_be_string")
        return ""
    if len(raw_value) > max_length:
        errors.append(f"{section_name}_too_long")
    return raw_value


def _normalize_item_section(
    payload: dict[str, object],
    section_name: str,
    section_spec: ItemSectionSpec,
    errors: list[str],
) -> list[dict[str, object]]:
    raw_items = payload.get(section_name)
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        errors.append(f"{section_name}_must_be_list")
        return []
    if len(raw_items) > section_spec.max_items:
        errors.append(f"{section_name}_too_many_items")
        return []

    normalized_items: list[dict[str, object]] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            errors.append(f"{section_name}_{index}_must_be_object")
            continue

        normalized_item = dict(item)
        for field_spec in section_spec.string_fields:
            current_value = normalized_item.get(field_spec.field)
            if current_value is None:
                normalized_item[field_spec.field] = field_spec.default
            elif not isinstance(current_value, str):
                errors.append(f"{section_name}_{index}_{field_spec.field}_must_be_string")
            elif len(current_value) > field_spec.max_length:
                errors.append(f"{section_name}_{index}_{field_spec.field}_too_long")

        for boolean_field in section_spec.boolean_fields:
            current_value = normalized_item.get(boolean_field)
            if current_value is None:
                normalized_item[boolean_field] = False
            elif not isinstance(current_value, bool):
                errors.append(f"{section_name}_{index}_{boolean_field}_must_be_boolean")

        for list_spec in section_spec.string_list_fields:
            normalized_item[list_spec.field] = _normalize_string_list_value(
                normalized_item.get(list_spec.field),
                f"{section_name}_{index}_{list_spec.field}",
                list_spec,
                errors,
            )

        order_value = normalized_item.get("order")
        if order_value is None:
            normalized_item["order"] = index + 1
        elif isinstance(order_value, bool) or not isinstance(order_value, int):
            errors.append(f"{section_name}_{index}_order_must_be_integer")

        normalized_items.append(normalized_item)

    return normalized_items


def _normalize_string_list_value(
    raw_value: object,
    label: str,
    list_spec: StringListFieldSpec,
    errors: list[str],
) -> list[object]:
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        errors.append(f"{label}_must_be_list")
        return []
    if len(raw_value) > list_spec.max_items:
        errors.append(f"{label}_too_many_items")
        return []

    normalized_values: list[object] = []
    for index, value in enumerate(raw_value):
        if not isinstance(value, str):
            errors.append(f"{label}_{index}_must_be_string")
        elif len(value) > list_spec.item_max_length:
            errors.append(f"{label}_{index}_too_long")
        normalized_values.append(value)

    return normalized_values


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
