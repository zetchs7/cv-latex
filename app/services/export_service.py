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
from app.validations.cv_validations import build_cv_form_data, validate_cv_form


EXPORTS_DIRECTORY_NAME = "exports"
MAX_JSON_IMPORT_BYTES = 512 * 1024
JSON_IMPORT_CHUNK_BYTES = 64 * 1024
JSON_EXPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ExportedFile:
    path: Path
    filename: str
    media_type: str


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


def export_cv_json(cv: CV) -> ExportedFile:
    payload = build_cv_json_payload(cv)
    filename = _build_entity_export_filename(cv.id, cv.title, "cv", "json", entity_prefix="cv")
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return _write_export_file(filename, content, "application/json")


def build_cv_json_payload(cv: CV) -> dict[str, object]:
    return {
        "schema_version": JSON_EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_cv_id": cv.id,
        "cv": {
            "title": cv.title,
            "full_name": cv.full_name,
            "email": cv.email,
            "phone": cv.phone,
            "professional_summary": cv.professional_summary,
            "experience_summary": cv.experience_summary,
            "education_summary": cv.education_summary,
            "skills": cv.skills,
        },
    }


def build_cv_form_data_from_json(raw_content: bytes) -> CVFormData:
    if len(raw_content) > MAX_JSON_IMPORT_BYTES:
        raise ExportServiceError("El archivo JSON supera el maximo permitido.")

    try:
        payload = json.loads(raw_content.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ExportServiceError("El archivo JSON debe estar codificado en UTF-8.") from error
    except json.JSONDecodeError as error:
        raise ExportServiceError("El archivo JSON no tiene un formato valido.") from error

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
    if not title:
        return "CV importado"
    return f"{title} (importado)"


def _build_cover_letter_export_title(cover_letter: CoverLetter) -> str:
    title_parts = [cover_letter.company, cover_letter.position]
    title = " ".join(part for part in title_parts if part).strip()
    return title or f"cover-letter-{cover_letter.id}"
