from dataclasses import dataclass
from datetime import UTC, datetime
from io import BufferedReader, BytesIO
import json
from pathlib import Path
import re

from app.database import get_data_dir
from app.models import CV, CoverLetter
from app.schemas import CVFormData
from app.services.file_naming import SAFE_EXPORT_FILENAME_MAX_LENGTH, build_capped_filename, sanitize_filename_component
from app.services.latex_service import GeneratedLatexDocument, generate_cv_tex_document
from app.services.structured_cv_service import NormalizedCV, resolve_normalized_cv
from app.validations.cv_validations import FIELD_LIMITS, build_cv_form_data, validate_cv_form
from app.validations.structured_cv_validations import validate_structured_payload_v2


EXPORTS_DIRECTORY_NAME = "exports"
MAX_JSON_IMPORT_BYTES = 512 * 1024
JSON_IMPORT_CHUNK_BYTES = 64 * 1024
JSON_EXPORT_SCHEMA_VERSION = 1
STRUCTURED_JSON_EXPORT_SCHEMA_VERSION = 2
SUPPORTED_JSON_SCHEMA_VERSIONS = (JSON_EXPORT_SCHEMA_VERSION, STRUCTURED_JSON_EXPORT_SCHEMA_VERSION)
IMPORTED_TITLE_SUFFIX = " (importado)"


@dataclass(frozen=True)
class ExportedFile:
    path: Path
    filename: str
    media_type: str


@dataclass(frozen=True)
class CVJsonImportResult:
    """Resultado del import JSON resuelto por schema.

    Schema 1 expone `form_data` listo para crear un CV legacy nuevo. Schema 2
    expone `structured_title` con sufijo y `structured_payload` completo para
    crear un CV estructurado nuevo via `create_structured_cv`; el payload no
    se descarta aplanandolo a `CVFormData`.
    """

    schema_version: int
    form_data: CVFormData | None = None
    structured_title: str | None = None
    structured_payload: dict[str, object] | None = None


class ExportServiceError(ValueError):
    pass


def read_limited_upload_bytes(
    file_object: BufferedReader | BytesIO,
    *,
    max_bytes: int = MAX_JSON_IMPORT_BYTES,
    chunk_size: int = JSON_IMPORT_CHUNK_BYTES,
) -> bytes:
    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = file_object.read(chunk_size)
        if not chunk:
            break

        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise ExportServiceError("El archivo JSON supera el maximo permitido.")

        chunks.append(chunk)

    return b"".join(chunks)


def ensure_exports_directory() -> Path:
    exports_directory = get_data_dir() / EXPORTS_DIRECTORY_NAME
    exports_directory.mkdir(parents=True, exist_ok=True)
    return exports_directory


def ensure_pdf_temp_root() -> Path:
    temp_root = ensure_exports_directory() / "_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root


def export_cv_tex(cv: CV, template_key: str) -> ExportedFile:
    generated_document = generate_cv_tex_document(cv, template_key)
    filename = _build_entity_export_filename(cv.id, cv.title, generated_document.template.key, "tex", entity_prefix="cv")
    return _write_export_file(filename, generated_document.content.encode("utf-8"), "application/x-tex")


def export_generated_tex_document(cv: CV, generated_document: GeneratedLatexDocument) -> ExportedFile:
    filename = _build_entity_export_filename(cv.id, cv.title, generated_document.template.key, "tex", entity_prefix="cv")
    return _write_export_file(filename, generated_document.content.encode("utf-8"), "application/x-tex")


def export_cover_letter_generated_tex_document(
    cover_letter: CoverLetter,
    generated_document: GeneratedLatexDocument,
) -> ExportedFile:
    filename = _build_entity_export_filename(
        cover_letter.id,
        _build_cover_letter_export_title(cover_letter),
        generated_document.template.key,
        "tex",
        entity_prefix="cover-letter",
    )
    return _write_export_file(filename, generated_document.content.encode("utf-8"), "application/x-tex")


def export_cv_json(cv: CV, *, schema_version: int | None = None) -> ExportedFile:
    payload = build_cv_json_payload(cv, schema_version=schema_version)
    variant = "cv" if payload["schema_version"] == JSON_EXPORT_SCHEMA_VERSION else "cv-schema2"
    filename = _build_entity_export_filename(cv.id, cv.title, variant, "json", entity_prefix="cv")
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return _write_export_file(filename, content, "application/json")


def build_cv_json_payload(cv: CV, *, schema_version: int | None = None) -> dict[str, object]:
    """Construye el payload de export JSON desde la fuente canonica unica.

    Sin `schema_version` explicito exporta el schema canonico: 2 para un CV
    estructurado valido y 1 (plano) para cualquier CV legacy o con fallback
    legacy (payload invalido, stale o de version futura), sin mezclar fuentes.
    Con `schema_version=1` se puede pedir el export plano de un CV
    estructurado (snapshot legacy derivado) para compatibilidad.
    """
    normalized = resolve_normalized_cv(cv)
    requested_schema_version = _resolve_requested_export_schema_version(
        schema_version,
        structured=normalized.is_structured,
    )

    if requested_schema_version == JSON_EXPORT_SCHEMA_VERSION:
        return _build_legacy_json_payload(normalized)

    return _build_structured_json_payload(normalized)


def _resolve_requested_export_schema_version(schema_version: int | None, *, structured: bool) -> int:
    if schema_version is None:
        return STRUCTURED_JSON_EXPORT_SCHEMA_VERSION if structured else JSON_EXPORT_SCHEMA_VERSION

    if isinstance(schema_version, bool) or schema_version not in SUPPORTED_JSON_SCHEMA_VERSIONS:
        raise ExportServiceError("El schema de exportacion JSON pedido no esta soportado; usa 1 o 2.")

    if schema_version == STRUCTURED_JSON_EXPORT_SCHEMA_VERSION and not structured:
        raise ExportServiceError("La exportacion JSON schema 2 requiere un CV estructurado valido.")

    return schema_version


def _build_legacy_json_payload(normalized: NormalizedCV) -> dict[str, object]:
    snapshot = normalized.legacy_snapshot
    return {
        "schema_version": JSON_EXPORT_SCHEMA_VERSION,
        "exported_at": _current_export_timestamp(),
        "source_cv_id": normalized.cv_id,
        "cv": {
            "title": snapshot.title,
            "full_name": snapshot.full_name,
            "email": snapshot.email,
            "phone": snapshot.phone,
            "professional_summary": snapshot.professional_summary,
            "experience_summary": snapshot.experience_summary,
            "education_summary": snapshot.education_summary,
            "skills": snapshot.skills,
        },
    }


def _build_structured_json_payload(normalized: NormalizedCV) -> dict[str, object]:
    return {
        "schema_version": STRUCTURED_JSON_EXPORT_SCHEMA_VERSION,
        "exported_at": _current_export_timestamp(),
        "source_cv_id": normalized.cv_id,
        "cv": {
            "title": normalized.title,
            "structured_payload": normalized.sections,
        },
    }


def build_cv_form_data_from_json(raw_content: bytes) -> CVFormData:
    """Entrada legacy del import JSON: solo acepta schema 1 (o sin version).

    Un JSON con schema_version 2 explicito se rechaza en lugar de aplanarse
    para no descartar contenido solo-estructurado; el flujo estructurado
    usa `build_cv_json_import_result`.
    """
    payload = _parse_json_import_payload(raw_content)
    schema_version = _resolve_import_schema_version(payload)

    if schema_version != JSON_EXPORT_SCHEMA_VERSION:
        raise ExportServiceError(
            "El JSON usa schema_version 2; importalo con el flujo estructurado desde el listado de CVs."
        )

    return _build_legacy_import_form_data(payload)


def build_cv_json_import_result(raw_content: bytes) -> CVJsonImportResult:
    """Resuelve el import JSON segun schema sin escribir en la base.

    Schema 1 (o version ausente) devuelve el `CVFormData` legacy con sufijo
    `(importado)`. Schema 2 valida el payload estructurado con el contrato
    unico v2 y devuelve titulo con sufijo mas el payload completo para crear
    un CV estructurado nuevo; nunca sobrescribe el CV de origen.
    """
    payload = _parse_json_import_payload(raw_content)
    schema_version = _resolve_import_schema_version(payload)

    if schema_version == STRUCTURED_JSON_EXPORT_SCHEMA_VERSION:
        return _build_structured_import_result(payload)

    return CVJsonImportResult(
        schema_version=schema_version,
        form_data=_build_legacy_import_form_data(payload),
    )


def _parse_json_import_payload(raw_content: bytes) -> dict[str, object]:
    if len(raw_content) > MAX_JSON_IMPORT_BYTES:
        raise ExportServiceError("El archivo JSON supera el maximo permitido.")

    try:
        payload = json.loads(raw_content.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ExportServiceError("El archivo JSON debe estar codificado en UTF-8.") from error
    except json.JSONDecodeError as error:
        raise ExportServiceError("El archivo JSON no tiene un formato valido.") from error

    if not isinstance(payload, dict):
        raise ExportServiceError("El JSON debe contener un objeto principal.")

    return payload


def _resolve_import_schema_version(payload: dict[str, object]) -> int:
    if "schema_version" not in payload:
        return JSON_EXPORT_SCHEMA_VERSION

    raw_version = payload["schema_version"]
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise ExportServiceError("El campo 'schema_version' debe ser un numero entero.")

    if raw_version not in SUPPORTED_JSON_SCHEMA_VERSIONS:
        raise ExportServiceError(f"El schema_version {raw_version} no esta soportado. Usa 1 o 2.")

    return raw_version


def _build_legacy_import_form_data(payload: dict[str, object]) -> CVFormData:
    cv_payload = _extract_cv_payload(payload)
    form_data = build_cv_form_data(_normalize_import_payload(cv_payload))
    form_data = CVFormData(
        title=_build_imported_title(form_data.title),
        full_name=form_data.full_name,
        email=form_data.email,
        phone=form_data.phone,
        professional_summary=form_data.professional_summary,
        experience_summary=form_data.experience_summary,
        education_summary=form_data.education_summary,
        skills=form_data.skills,
    )

    errors = validate_cv_form(form_data)
    if errors:
        joined_errors = "; ".join(f"{field}: {message}" for field, message in errors.items())
        raise ExportServiceError(f"El JSON no representa un CV valido: {joined_errors}")

    return form_data


def _build_structured_import_result(payload: dict[str, object]) -> CVJsonImportResult:
    cv_payload = _extract_cv_payload(payload)

    raw_structured_payload = cv_payload.get("structured_payload")
    if not isinstance(raw_structured_payload, dict):
        raise ExportServiceError("El JSON schema 2 debe incluir 'structured_payload' como objeto.")

    raw_title = cv_payload.get("title", "")
    if raw_title is None:
        raw_title = ""
    if not isinstance(raw_title, str):
        raise ExportServiceError("El campo 'title' debe ser texto.")

    validation = validate_structured_payload_v2(
        raw_structured_payload,
        declared_schema_version=STRUCTURED_JSON_EXPORT_SCHEMA_VERSION,
    )
    if not validation.is_valid or validation.normalized_payload is None:
        joined_errors = "; ".join(_translate_structured_validation_errors(validation.errors))
        raise ExportServiceError(f"El JSON estructurado no es valido: {joined_errors}")

    return CVJsonImportResult(
        schema_version=STRUCTURED_JSON_EXPORT_SCHEMA_VERSION,
        structured_title=_build_imported_title(raw_title),
        structured_payload=validation.normalized_payload,
    )


def build_pdf_export_path(cv: CV, template_key: str) -> tuple[Path, str]:
    filename = _build_entity_export_filename(cv.id, cv.title, template_key, "pdf", entity_prefix="cv")
    export_path = _safe_export_path(filename)
    return export_path, filename


def build_cover_letter_pdf_export_path(cover_letter: CoverLetter, template_key: str) -> tuple[Path, str]:
    filename = _build_entity_export_filename(
        cover_letter.id,
        _build_cover_letter_export_title(cover_letter),
        template_key,
        "pdf",
        entity_prefix="cover-letter",
    )
    export_path = _safe_export_path(filename)
    return export_path, filename


def _write_export_file(filename: str, content: bytes, media_type: str) -> ExportedFile:
    export_path = _safe_export_path(filename)
    export_path.write_bytes(content)
    return ExportedFile(path=export_path, filename=filename, media_type=media_type)


def _safe_export_path(filename: str) -> Path:
    safe_filename = sanitize_filename(filename)
    exports_directory = ensure_exports_directory().resolve()
    export_path = (exports_directory / safe_filename).resolve()

    if export_path.parent != exports_directory:
        raise ExportServiceError("Ruta de exportacion no permitida.")

    return export_path


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()

    safe_stem = sanitize_filename_component(stem)
    safe_suffix = re.sub(r"[^a-z0-9.]+", "", suffix)

    if not safe_stem:
        safe_stem = "cv-export"

    if safe_suffix not in {".tex", ".pdf", ".json"}:
        raise ExportServiceError("Extension de exportacion no permitida.")

    return f"{safe_stem}{safe_suffix}"


def _build_entity_export_filename(
    entity_id: int,
    title_value: str,
    variant: str,
    extension: str,
    *,
    entity_prefix: str,
) -> str:
    safe_variant = sanitize_filename_component(variant)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return build_capped_filename(
        leading_parts=[entity_prefix, str(entity_id)],
        variable_part=title_value,
        trailing_parts=[safe_variant, timestamp],
        extension=f".{extension}",
        default_stem=f"{entity_prefix}-{entity_id}-{safe_variant}-{timestamp}",
        max_length=SAFE_EXPORT_FILENAME_MAX_LENGTH,
    )


def _translate_structured_validation_errors(errors: tuple[str, ...]) -> list[str]:
    """Traduce los codigos del contrato v2 a mensajes accionables en espanol."""
    return [_translate_structured_validation_error(error) for error in errors]


_STRUCTURED_ERROR_EXACT_MESSAGES = {
    "payload_must_be_object": "el payload estructurado debe ser un objeto",
    "schema_version_missing": "el payload estructurado debe declarar schema_version 2",
    "schema_version_must_be_integer": "schema_version debe ser un numero entero",
    "schema_version_unsupported": "schema_version no es la version 2 esperada",
    "contact_links_must_be_list": "la lista 'links' de 'contact' debe ser una lista",
    "contact_links_too_many_items": "la lista 'links' de 'contact' supera el maximo de items",
}

_STRUCTURED_ERROR_PATTERN_MESSAGES: tuple[tuple[str, str], ...] = (
    (r"^contact_links_(?P<index>\d+)_must_be_string$", "un valor de la lista 'links' de 'contact' (item {index}) debe ser texto"),
    (r"^contact_links_(?P<index>\d+)_too_long$", "un valor de la lista 'links' de 'contact' (item {index}) supera el maximo de caracteres"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_(?P<field>[a-z_]+)_must_be_boolean$", "el campo '{field}' del item {index} de '{section}' debe ser booleano"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_(?P<field>[a-z_]+)_must_be_list$", "la lista '{field}' del item {index} de '{section}' debe ser una lista"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_(?P<field>[a-z_]+)_too_many_items$", "la lista '{field}' del item {index} de '{section}' supera el maximo de items"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_(?P<field>[a-z_]+)_\d+_must_be_string$", "un valor de la lista '{field}' del item {index} de '{section}' debe ser texto"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_(?P<field>[a-z_]+)_\d+_too_long$", "un valor de la lista '{field}' del item {index} de '{section}' supera el maximo de caracteres"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_(?P<field>[a-z_]+)_must_be_string$", "el campo '{field}' del item {index} de '{section}' debe ser texto"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_(?P<field>[a-z_]+)_too_long$", "el campo '{field}' del item {index} de '{section}' supera el maximo de caracteres"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_must_be_object$", "el item {index} de '{section}' debe ser un objeto"),
    (r"^(?P<section>[a-z_]+)_(?P<index>\d+)_order_must_be_integer$", "el campo 'order' del item {index} de '{section}' debe ser un numero entero"),
    (r"^(?P<section>personal|contact|metadata)_(?P<field>[a-z_]+)_must_be_string$", "el campo '{field}' de '{section}' debe ser texto"),
    (r"^(?P<section>personal|contact|metadata)_(?P<field>[a-z_]+)_too_long$", "el campo '{field}' de '{section}' supera el maximo de caracteres"),
    (r"^(?P<section>[a-z_]+)_must_be_object$", "la seccion '{section}' debe ser un objeto"),
    (r"^(?P<section>[a-z_]+)_must_be_string$", "la seccion '{section}' debe ser texto"),
    (r"^(?P<section>[a-z_]+)_must_be_list$", "la seccion '{section}' debe ser una lista"),
    (r"^(?P<section>[a-z_]+)_too_many_items$", "la seccion '{section}' supera el maximo de items"),
    (r"^(?P<section>[a-z_]+)_too_long$", "la seccion '{section}' supera el maximo de caracteres"),
)


def _translate_structured_validation_error(error: str) -> str:
    exact_message = _STRUCTURED_ERROR_EXACT_MESSAGES.get(error)
    if exact_message:
        return exact_message

    for pattern, message in _STRUCTURED_ERROR_PATTERN_MESSAGES:
        match = re.match(pattern, error)
        if match:
            groups = dict(match.groupdict())
            if "index" in groups:
                groups["index"] = str(int(groups["index"]) + 1)
            return message.format(**groups)

    return error


def _current_export_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _extract_cv_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ExportServiceError("El JSON debe contener un objeto principal.")

    cv_payload = payload.get("cv", payload)
    if not isinstance(cv_payload, dict):
        raise ExportServiceError("El JSON debe contener un objeto 'cv'.")

    return cv_payload


def _normalize_import_payload(cv_payload: dict[str, object]) -> dict[str, str]:
    allowed_fields = {
        "title",
        "full_name",
        "email",
        "phone",
        "professional_summary",
        "experience_summary",
        "education_summary",
        "skills",
    }

    normalized: dict[str, str] = {}
    for field in allowed_fields:
        value = cv_payload.get(field, "")
        if value is None:
            normalized[field] = ""
            continue
        if not isinstance(value, str):
            raise ExportServiceError(f"El campo '{field}' debe ser texto.")
        normalized[field] = value

    return normalized


def _build_imported_title(title: str) -> str:
    """Titulo del CV importado, acotado al limite de `title`.

    Un JSON exportado desde la app siempre tiene que poder reimportarse, asi que
    el sufijo se agrega recortando la base en lugar de exceder el limite (igual
    que hace `build_duplicate_title`).
    """
    max_length = FIELD_LIMITS["title"]
    if not title:
        return IMPORTED_TITLE_SUFFIX.strip()

    available_length = max_length - len(IMPORTED_TITLE_SUFFIX)
    if available_length <= 0:
        return title[:max_length]

    base_title = title[:available_length].rstrip()
    if not base_title:
        return title[:max_length]

    return f"{base_title}{IMPORTED_TITLE_SUFFIX}"


def _build_cover_letter_export_title(cover_letter: CoverLetter) -> str:
    title_parts = [cover_letter.company, cover_letter.position]
    title = " ".join(part for part in title_parts if part).strip()
    return title or f"cover-letter-{cover_letter.id}"
