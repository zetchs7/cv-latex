"""Servicio del editor estructurado de CV (T4).

Prepara el contexto de bootstrap del editor (nuevo o existente), parsea el
envio del formulario (titulo + payload JSON), traduce los codigos de error del
contrato v2 a mensajes accionables en espanol y construye el contexto de
rerender para envios fallidos preservando lo ingresado.

Reglas clave:
- La fuente canonica se resuelve unicamente via `resolve_normalized_cv`: un CV
  estructurado valido se bootstrap-ea desde su payload (nunca se regenera
  desde campos planos); un CV legacy, invalido, stale o de version futura se
  bootstrap-ea integramente desde los campos legacy con advertencia explicita.
- El servidor es el unico validador: el editor no confia en el cliente y no
  hay escrituras parciales (el write bundle valida todo antes de persistir).
- La metadata de procedencia es server-owned: se re-estampa deliberadamente al
  guardar con `metadata_source = "structured_editor"`, nunca oculta.
- Las claves desconocidas del payload, secciones e items viajan intactas por
  bootstrap -> edicion -> submit -> validacion -> persistencia.
"""

from dataclasses import dataclass
import json

from app.models import CV
from app.services.export_service import _translate_structured_validation_errors
from app.services.structured_cv_service import (
    MAX_STRUCTURED_PAYLOAD_BYTES,
    resolve_normalized_cv,
)
from app.validations.structured_cv_validations import CURRENT_STRUCTURED_SCHEMA_VERSION


STRUCTURED_EDITOR_METADATA_SOURCE = "structured_editor"

_NO_PAYLOAD_ERROR = (
    "No se recibio el contenido estructurado del editor. "
    "El editor estructurado requiere JavaScript activo para armar el payload."
)
_PAYLOAD_TOO_LARGE_ERROR = (
    f"El contenido estructurado enviado supera el maximo de {MAX_STRUCTURED_PAYLOAD_BYTES // 1024} KB."
)
_PAYLOAD_INVALID_JSON_ERROR = "El contenido estructurado enviado no es un JSON valido."
_PAYLOAD_MUST_BE_OBJECT_ERROR = "El contenido estructurado debe ser un objeto JSON."

_LEGACY_SOURCE_WARNINGS = {
    "schema_version_legacy_or_missing": "version de schema legacy o ausente",
    "payload_not_marked_valid": "payload no marcado como valido",
    "payload_missing": "payload ausente",
    "payload_invalid": "payload invalido",
}

_SNAPSHOT_FIELD_LABELS = {
    "title": "Titulo interno",
    "full_name": "Nombre completo",
    "email": "Email",
    "phone": "Telefono",
    "professional_summary": "Resumen profesional",
    "experience_summary": "Experiencia laboral",
    "education_summary": "Educacion",
    "skills": "Skills",
}

_EXACT_EDITOR_ERROR_MESSAGES = {
    "summary_too_long": "Resumen profesional: Maximo 1200 caracteres.",
    "structured_payload_too_large": _PAYLOAD_TOO_LARGE_ERROR,
}

_EDITOR_OBJECT_SECTIONS = ("personal", "contact", "metadata")
_EDITOR_STRING_SECTIONS = ("summary",)
_EDITOR_ITEM_SECTIONS = (
    "skills",
    "experience",
    "education",
    "certifications",
    "languages",
    "projects",
    "links",
    "additional_info",
)


@dataclass(frozen=True)
class StructuredEditorContext:
    """Contexto de render del editor estructurado.

    `payload` es el bootstrap que el template serializa con `| tojson` y que
    el editor cliente usa como estado inicial. En envios fallidos contiene el
    payload exacto enviado por el usuario para no perder datos ingresados.
    """

    title: str
    payload: dict[str, object]
    is_structured: bool
    mode_reason: str
    source_warning: str
    errors: tuple[str, ...] = ()
    cv_id: int | None = None


def build_new_editor_context() -> StructuredEditorContext:
    return StructuredEditorContext(
        title="",
        payload=build_empty_structured_editor_payload(),
        is_structured=False,
        mode_reason="new_structured_cv",
        source_warning="",
    )


def build_structured_editor_context_for_cv(cv: CV) -> StructuredEditorContext:
    normalized = resolve_normalized_cv(cv)
    return StructuredEditorContext(
        title=cv.title,
        payload=dict(normalized.sections),
        is_structured=normalized.is_structured,
        mode_reason=normalized.reason,
        source_warning="" if normalized.is_structured else _legacy_source_warning(normalized.reason),
        cv_id=cv.id,
    )


def build_failed_submission_context(
    *,
    title: str,
    payload: dict[str, object] | None,
    errors: list[str],
    cv_id: int | None = None,
    is_structured: bool = False,
    mode_reason: str = "failed_submission",
    source_warning: str = "",
) -> StructuredEditorContext:
    """Contexto de rerender tras un envio fallido.

    Preserva el payload tal como lo envio el usuario (incluidas claves
    desconocidas) y el estado de advertencia del CV subyacente para que el
    usuario no pierda datos ni contexto al corregir y reintentar.
    """
    return StructuredEditorContext(
        title=title,
        payload=payload if payload is not None else build_empty_structured_editor_payload(),
        is_structured=is_structured,
        mode_reason=mode_reason,
        source_warning=source_warning,
        errors=tuple(errors),
        cv_id=cv_id,
    )


def build_empty_structured_editor_payload() -> dict[str, object]:
    """Payload v2 vacio para el editor de un CV nuevo."""
    return {
        "schema_version": CURRENT_STRUCTURED_SCHEMA_VERSION,
        "personal": {"full_name": "", "headline": "", "location": ""},
        "contact": {"email": "", "phone": "", "links": []},
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "links": [],
        "additional_info": [],
        "metadata": {"source": "", "synced_from_legacy_at": ""},
    }


def parse_structured_editor_submission(raw_payload: str) -> tuple[dict[str, object] | None, list[str]]:
    """Parsea el campo `structured_payload` del formulario del editor.

    Devuelve `(payload, errors)`. `payload` es `None` cuando el envio no se
    puede rerenderizar (payload ausente, demasiado grande o JSON invalido).
    """
    if not raw_payload or not raw_payload.strip():
        return None, [_NO_PAYLOAD_ERROR]

    if len(raw_payload.encode("utf-8")) > MAX_STRUCTURED_PAYLOAD_BYTES:
        return None, [_PAYLOAD_TOO_LARGE_ERROR]

    try:
        payload = _loads_structured_payload(raw_payload)
    except ValueError:
        return None, [_PAYLOAD_INVALID_JSON_ERROR]

    if not isinstance(payload, dict):
        return None, [_PAYLOAD_MUST_BE_OBJECT_ERROR]

    renderable_payload, shape_errors = normalize_renderable_structured_payload(payload)
    if shape_errors:
        return renderable_payload, shape_errors

    return payload, []


def normalize_renderable_structured_payload(payload: dict[str, object]) -> tuple[dict[str, object], list[str]]:
    """Devuelve un payload con la forma que el template del editor siempre puede renderizar.

    El template asume secciones de tipo correcto. Un envio con la forma
    equivocada no debe llegar al render: se corrige solo la forma incompatible
    (el resto del contenido enviado se preserva) y se reportan errores en
    espanol para que la ruta responda 422 en vez de fallar con 500. Esta
    correccion no reemplaza niDebilita la validacion del modelo estructurado:
    el payload original sigue sin persistir.
    """
    renderable_payload = dict(payload)
    errors: list[str] = []

    for section in _EDITOR_OBJECT_SECTIONS:
        section_value = renderable_payload.get(section)
        if section_value is None or isinstance(section_value, dict):
            continue
        renderable_payload[section] = {}
        errors.append(
            f"La seccion '{section}' del contenido estructurado enviado debe ser un objeto."
        )

    contact_section = renderable_payload.get("contact")
    contact_links = contact_section.get("links") if isinstance(contact_section, dict) else None
    if contact_links is not None and not isinstance(contact_links, list):
        renderable_payload["contact"] = dict(contact_section, links=[])
        errors.append(
            "La lista 'links' de 'contact' del contenido estructurado enviado debe ser una lista."
        )

    for section in _EDITOR_STRING_SECTIONS:
        section_value = renderable_payload.get(section)
        if section_value is None or isinstance(section_value, str):
            continue
        renderable_payload[section] = ""
        errors.append(
            f"La seccion '{section}' del contenido estructurado enviado debe ser texto."
        )

    for section in _EDITOR_ITEM_SECTIONS:
        section_value = renderable_payload.get(section)
        if section_value is None or isinstance(section_value, list):
            continue
        renderable_payload[section] = []
        errors.append(
            f"La seccion '{section}' del contenido estructurado enviado debe ser una lista."
        )

    return renderable_payload, errors


def translate_structured_editor_errors(errors: tuple[str, ...]) -> list[str]:
    """Traduce codigos del contrato v2 y errores de snapshot a espanol accionable."""
    translated = []
    for error in errors:
        message = _EXACT_EDITOR_ERROR_MESSAGES.get(error)
        if message is None:
            message = _prettify_snapshot_error(_translate_structured_validation_errors([error])[0])
        if message and message not in translated:
            translated.append(message)
    return translated


def _loads_structured_payload(raw_payload: str) -> object:
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError as error:
        raise ValueError(str(error)) from error


def _legacy_source_warning(reason: str) -> str:
    reason_text = _LEGACY_SOURCE_WARNINGS.get(reason, reason)
    return (
        f"Este CV todavia no tiene datos estructurados validos (motivo: {reason_text}). "
        "El editor arranca desde los campos planos actuales; al guardar, el CV "
        "se convierte en estructurado y reemplaza cualquier dato estructurado "
        "previo no disponible. Revisa los limites por campo antes de guardar."
    )


def _prettify_snapshot_error(error: str) -> str:
    for field, label in _SNAPSHOT_FIELD_LABELS.items():
        prefix = f"{field}: "
        if error.startswith(prefix):
            return f"{label}: {error[len(prefix):]}"
    return error
