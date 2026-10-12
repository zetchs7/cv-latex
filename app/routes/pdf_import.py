"""Rutas de importacion de Curriculum Vitae desde PDF.

Cumple el flujo obligatorio del Issue #14:

    Subir PDF -> Validar -> Extraer -> Interpretar -> Clasificar -> Revisar ->
    Corregir -> Confirmar -> Guardar CV estructurado

Reglas que estas rutas respetan:

- El PDF original **nunca** se persiste. Solo el texto extraido, en un
  borrador con vencimiento.
- Nada se escribe en `cvs` hasta la confirmacion explicita, y confirmar exige
  que cada elemento pendiente tenga una decision.
- Si algo falla al guardar, el borrador sobrevive y se puede reintentar sin
  perder correcciones.
- Los mensajes de error visibles nunca incluyen rutas del servidor.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.repositories import cv_repository
from app.services.structured_cv_service import StructuredCVWriteError
from app.services.import_staging_service import (
    DECISION_STATUSES,
    StagedEntry,
    UnclassifiedEntry,
    STATUS_CONFIRMED,
    STATUS_DISCARDED,
    STATUS_KEPT,
    STATUS_PENDING,
    ImportDraft,
    ImportStagingError,
    apply_review,
    confirm_draft,
    create_draft,
    delete_draft,
    load_draft,
    pending_summary,
    purge_expired_drafts,
)
from app.services.pdf_import_service import (
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    PdfImportError,
    PdfUnclassifiableDocument,
    extract_pdf,
    read_limited_pdf_bytes,
)
from app.services.pdf_section_parser import CONFIDENCE_LABELS, parse_cv_text
from app.template_utils import create_templates

logger = logging.getLogger(__name__)
templates = create_templates()

router = APIRouter(prefix="/cvs/import", tags=["cvs"])


@router.get("/pdf", response_class=HTMLResponse)
def pdf_import_form(request: Request) -> HTMLResponse:
    purge_expired_drafts()
    return _render(request, "cvs/import_form.html", page_title="Importar CV desde PDF")


@router.post("/pdf", response_class=HTMLResponse)
def pdf_import_submit(request: Request, pdf_file: UploadFile = File(...)) -> HTMLResponse:
    if pdf_file is None or not getattr(pdf_file, "filename", ""):
        return _render(
            request,
            "cvs/import_form.html",
            page_title="Importar CV desde PDF",
            error_message="Selecciona un archivo PDF.",
            status=422,
        )

    try:
        raw_content = read_limited_pdf_bytes(pdf_file.file)
        extracted = extract_pdf(raw_content)
    except PdfImportError as error:
        # El codigo sirve para registros; el mensaje es el que ve la persona.
        logger.info("pdf import rejected: %s", error.code)
        return _render(
            request,
            "cvs/import_form.html",
            page_title="Importar CV desde PDF",
            error_message=error.user_message,
            max_bytes=MAX_PDF_BYTES,
            max_pages=MAX_PDF_PAGES,
            status=422,
        )

    try:
        parsed = parse_cv_text(extracted.text)
    except PdfUnclassifiableDocument as error:
        # Documento legible pero demasiado grande para revisarlo sin perder nada.
        # Se rechaza antes de crear un borrador incompleto.
        logger.info("pdf import unclassifiable: pages=%d", extracted.page_count)
        return _render(
            request,
            "cvs/import_form.html",
            page_title="Importar CV desde PDF",
            error_message=str(error),
            max_bytes=MAX_PDF_BYTES,
            max_pages=MAX_PDF_PAGES,
            status=422,
        )

    draft = create_draft(
        parsed,
        source_filename=pdf_file.filename or "cv.pdf",
        page_count=extracted.page_count,
    )

    logger.info(
        "pdf import staged: draft=%s entries=%d unclassified=%d pages=%d",
        draft.draft_id,
        len(draft.entries),
        len(draft.unclassified),
        extracted.page_count,
    )

    return RedirectResponse(url=request.url_for("pdf_import_review", draft_id=draft.draft_id), status_code=303)


@router.get("/{draft_id}", response_class=HTMLResponse)
def pdf_import_review(request: Request, draft_id: str) -> HTMLResponse:
    try:
        draft = load_draft(draft_id)
    except ImportStagingError as error:
        return _render_gone(request, error)

    return _render_review(request, draft)


@router.post("/{draft_id}", response_class=HTMLResponse)
async def pdf_import_save(request: Request, draft_id: str) -> HTMLResponse:
    try:
        draft = load_draft(draft_id)
    except ImportStagingError as error:
        return _render_gone(request, error)

    form = await await_form(request)

    try:
        draft = apply_review(
            draft,
            values=form["values"],
            decisions=form["decisions"],
            unclassified_assignments=form["assignments"],
            title=form["title"],
        )
    except ImportStagingError as error:
        # El borrador NO se toco: apply_review valida antes de aplicar. Se
        # vuelve a pintar con los valores enviados para que no se pierda nada.
        return _render_review(request, draft, error_message=error.user_message, status=422, submitted=form)

    return _render_review(request, draft, notice="Cambios guardados en la revision.")


@router.post("/{draft_id}/confirm", response_class=HTMLResponse)
async def pdf_import_confirm(request: Request, draft_id: str) -> HTMLResponse:
    try:
        draft = load_draft(draft_id)
    except ImportStagingError as error:
        return _render_gone(request, error)

    form = await await_form(request)

    try:
        draft = apply_review(
            draft,
            values=form["values"],
            decisions=form["decisions"],
            unclassified_assignments=form["assignments"],
            title=form["title"],
        )
    except ImportStagingError as error:
        return _render_review(request, draft, error_message=error.user_message, status=422, submitted=form)

    default_title = _suggest_title(draft)
    title = (form["title"] or "").strip() or draft.proposed_title or default_title

    try:
        payload = confirm_draft(draft, title=title)
    except ImportStagingError as error:
        return _render_review(request, draft, error_message=error.user_message, status=422, submitted=form)

    try:
        cv_id = cv_repository.create_structured_cv(
            title=title,
            payload=payload,
            metadata_source="pdf_import",
        )
    except StructuredCVWriteError as error:
        # El borrador sobrevive: la persona puede reintentar sin perder nada de
        # lo que corrigio. No se expone el detalle tecnico.
        logger.info("pdf import write failed: %s", error)
        return _render_review(
            request,
            draft,
            error_message="No se pudo guardar el CV con los datos revisados. "
                          "Revisa los campos obligatorios e intenta de nuevo; tu revision se conserva.",
            status=422,
            submitted=form,
        )

    delete_draft(draft_id)
    logger.info("pdf import finalized: cv_id=%s", cv_id)

    return RedirectResponse(
        url=request.url_for("cvs_structured_edit", cv_id=cv_id),
        status_code=303,
    )


@router.post("/{draft_id}/discard")
async def pdf_import_discard(request: Request, draft_id: str) -> RedirectResponse:
    """Descarta el borrador, pero solo con confirmacion de texto exacto.

    Un clic accidental sobre el boton de peligro borraria horas de revision. El
    patron es el mismo que usan CVs y cartas, y la comprobacion va en el
    servidor: `confirm()` del navegador no es una validacion.
    """

    try:
        draft = load_draft(draft_id)
    except ImportStagingError:
        return RedirectResponse(url=request.url_for("cvs_list"), status_code=303)

    form = await await_form(request)
    expected = _suggest_title(draft)
    if (form["discard_confirmation"] or "").strip() != expected:
        return _render_review(
            request,
            draft,
            error_message="Para descartar la importacion escribe exactamente el nombre del CV.",
            status=422,
            submitted=form,
        )

    delete_draft(draft_id)
    return RedirectResponse(url=request.url_for("cvs_list"), status_code=303)


# --- Apoyo ---------------------------------------------------------------


async def await_form(request: Request) -> dict[str, dict[str, str]]:
    """Lee el formulario plano de la pantalla de revision.

    Se leen TODOS los valores primero y despues se validan, para que un error
    en una decision no descarte lo que la persona ya escribio en otros campos.
    """

    form = await request.form()
    values: dict[str, str] = {}
    decisions: dict[str, str] = {}
    assignments: dict[str, str] = {}
    title = ""
    discard_confirmation = ""

    for raw_key, raw_value in form.multi_items():
        key = str(raw_key)
        value = str(raw_value)

        if key == "cv_title":
            title = value
            continue

        if key == "confirm_discard":
            discard_confirmation = value[:160]
            continue

        if key.startswith("value__"):
            values[key[len("value__"):]] = value
        elif key.startswith("decision__"):
            if value in DECISION_STATUSES:
                decisions[key[len("decision__"):]] = value
        elif key.startswith("assign__"):
            assignments[key[len("assign__"):]] = value

    return {
        "values": values,
        "decisions": decisions,
        "assignments": assignments,
        "title": title,
        "discard_confirmation": discard_confirmation,
    }


def _render(request: Request, template_name: str, *, status: int = 200, **context) -> HTMLResponse:
    return templates.TemplateResponse(request, template_name, context, status_code=status)


def _suggest_title(draft: ImportDraft) -> str:
    for entry in draft.entries:
        if entry.key == "personal.full_name" and entry.value.strip():
            return entry.value.strip()[:120]
    return "CV importado desde PDF"


def _render_review(
    request: Request,
    draft: ImportDraft,
    *,
    error_message: str = "",
    notice: str = "",
    status: int = 200,
    submitted: dict | None = None,
) -> HTMLResponse:
    submitted = submitted or {}
    draft_view = _with_submitted(draft, submitted)
    entries_pending, unclassified_pending = pending_summary(draft_view)

    return _render(
        request,
        "cvs/import_review.html",
        page_title="Resultado de la importacion del CV",
        draft=draft_view,
        confidence_labels=CONFIDENCE_LABELS,
        decision_statuses=DECISION_STATUSES,
        error_message=error_message,
        notice=notice,
        entries_pending=entries_pending,
        unclassified_pending=unclassified_pending,
        can_confirm=entries_pending == 0 and unclassified_pending == 0,
        status=status,
        suggested_title=_suggest_title(draft),
    )


def _with_submitted(draft: ImportDraft, submitted: dict) -> ImportDraft:
    """Copia superficial con los valores enviados, para no perder edicion."""

    if not submitted.get("values") and not submitted.get("assignments"):
        return draft

    clone = ImportDraft(
        draft_id=draft.draft_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        source_filename=draft.source_filename,
        page_count=draft.page_count,
        entries=[StagedEntry(**{**entry.__dict__, "values": dict(entry.values)}) for entry in draft.entries],
        unclassified=[UnclassifiedEntry(**item.__dict__) for item in draft.unclassified],
        conflicts=list(draft.conflicts),
        version=draft.version,
        finalized_cv_id=draft.finalized_cv_id,
        proposed_title=draft.proposed_title,
    )

    for entry in clone.entries:
        if entry.key in submitted["values"]:
            entry.value = submitted["values"][entry.key]
        for submitted_key, value in submitted["values"].items():
            if submitted_key.startswith(f"{entry.key}:") and entry.values:
                field_name = submitted_key.split(":", 1)[1]
                if field_name in entry.values:
                    entry.values[field_name] = value

    for item in clone.unclassified:
        if item.key in submitted["values"]:
            # La persona pudo acortar el bloque que el sistema rechazo. Se guarda
            # lo que escribio, sin recortarlo: si sigue largo, la validacion lo
            # dira con el mensaje correspondiente.
            item.text = submitted["values"][item.key][:2000]
        if item.key in submitted["assignments"]:
            item.assigned_section = submitted["assignments"][item.key]

    return clone


def _render_gone(request: Request, error: ImportStagingError) -> HTMLResponse:
    return _render(
        request,
        "cvs/import_form.html",
        page_title="Importar CV desde PDF",
        error_message=error.user_message,
        status=404 if error.code == "draft_not_found" else 422,
    )


# Los estados se re-exportan para las plantillas sin importar el servicio.
IMPORT_DECISION_STATES = {
    STATUS_PENDING: "Pendiente",
    STATUS_CONFIRMED: "Confirmar",
    STATUS_KEPT: "Conservar",
    STATUS_DISCARDED: "Descartar",
}