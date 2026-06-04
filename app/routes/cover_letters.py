import logging

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models import CoverLetter
from app.repositories import cv_repository
from app.repositories import cover_letter_repository
from app.schemas import CoverLetterFormData
from app.services.export_service import ExportServiceError, export_cover_letter_generated_tex_document
from app.services.latex_service import (
    DEFAULT_COVER_LETTER_TEMPLATE_KEY,
    LatexTemplateError,
    generate_cover_letter_tex_document,
)
from app.services.pdf_service import PdfCompilationError, generate_cover_letter_pdf_export
from app.validations.cover_letter_validations import build_cover_letter_form_data, validate_cover_letter_form


router = APIRouter(prefix="/cover-letters", tags=["Cover Letters"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse, name="cover_letters_list")
def list_cover_letters(request: Request, message: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        "cover_letters/index.html",
        {
            "request": request,
            "cover_letters": cover_letter_repository.list_cover_letters(),
            "message": message,
        },
    )


@router.get("/new", response_class=HTMLResponse, name="cover_letters_new")
def new_cover_letter(request: Request) -> HTMLResponse:
    return _render_form(
        request=request,
        form_data=_empty_form_data(),
        errors={},
        action_url=str(request.url_for("cover_letters_create")),
        page_title="Crear carta",
        submit_label="Crear carta",
    )


@router.post("/", response_class=HTMLResponse, name="cover_letters_create")
def create_cover_letter(
    request: Request,
    company: str = Form(""),
    position: str = Form(""),
    contact: str = Form(""),
    greeting: str = Form(""),
    introduction: str = Form(""),
    body: str = Form(""),
    closing: str = Form(""),
    signature: str = Form(""),
    associated_cv_id: str = Form(""),
):
    form_data, errors = _build_cover_letter_form_with_errors(
        company=company,
        position=position,
        contact=contact,
        greeting=greeting,
        introduction=introduction,
        body=body,
        closing=closing,
        signature=signature,
        associated_cv_id_raw=associated_cv_id,
    )

    if errors:
        return _render_form(
            request=request,
            form_data=form_data,
            errors=errors,
            action_url=str(request.url_for("cover_letters_create")),
            page_title="Crear carta",
            submit_label="Crear carta",
            status_code=422,
        )

    cover_letter_id = cover_letter_repository.create_cover_letter(form_data)
    return _redirect_to_detail(request, cover_letter_id, "Carta creada correctamente.")


@router.get("/{cover_letter_id}", response_class=HTMLResponse, name="cover_letters_detail")
def cover_letter_detail(request: Request, cover_letter_id: int, message: str | None = None) -> HTMLResponse:
    cover_letter = cover_letter_repository.get_cover_letter(cover_letter_id)
    if cover_letter is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    return templates.TemplateResponse(
        "cover_letters/detail.html",
        {
            "request": request,
            "cover_letter": cover_letter,
            "message": message,
            "default_template": DEFAULT_COVER_LETTER_TEMPLATE_KEY,
        },
    )


@router.get("/{cover_letter_id}/edit", response_class=HTMLResponse, name="cover_letters_edit")
def edit_cover_letter(request: Request, cover_letter_id: int) -> HTMLResponse:
    cover_letter = cover_letter_repository.get_cover_letter(cover_letter_id)
    if cover_letter is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    return _render_form(
        request=request,
        form_data=CoverLetterFormData(
            company=cover_letter.company,
            position=cover_letter.position,
            contact=cover_letter.contact,
            greeting=cover_letter.greeting,
            introduction=cover_letter.introduction,
            body=cover_letter.body,
            closing=cover_letter.closing,
            signature=cover_letter.signature,
            associated_cv_id=cover_letter.associated_cv_id,
        ),
        errors={},
        action_url=str(request.url_for("cover_letters_update", cover_letter_id=cover_letter.id)),
        page_title="Editar carta",
        submit_label="Guardar cambios",
        cover_letter_id=cover_letter.id,
    )


@router.post("/{cover_letter_id}/edit", response_class=HTMLResponse, name="cover_letters_update")
def update_cover_letter(
    request: Request,
    cover_letter_id: int,
    company: str = Form(""),
    position: str = Form(""),
    contact: str = Form(""),
    greeting: str = Form(""),
    introduction: str = Form(""),
    body: str = Form(""),
    closing: str = Form(""),
    signature: str = Form(""),
    associated_cv_id: str = Form(""),
):
    form_data, errors = _build_cover_letter_form_with_errors(
        company=company,
        position=position,
        contact=contact,
        greeting=greeting,
        introduction=introduction,
        body=body,
        closing=closing,
        signature=signature,
        associated_cv_id_raw=associated_cv_id,
    )

    if errors:
        return _render_form(
            request=request,
            form_data=form_data,
            errors=errors,
            action_url=str(request.url_for("cover_letters_update", cover_letter_id=cover_letter_id)),
            page_title="Editar carta",
            submit_label="Guardar cambios",
            cover_letter_id=cover_letter_id,
            status_code=422,
        )

    if not cover_letter_repository.update_cover_letter(cover_letter_id, form_data):
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    return _redirect_to_detail(request, cover_letter_id, "Carta actualizada correctamente.")


@router.get("/{cover_letter_id}/delete", response_class=HTMLResponse, name="cover_letters_confirm_delete")
def confirm_delete_cover_letter(request: Request, cover_letter_id: int) -> HTMLResponse:
    cover_letter = cover_letter_repository.get_cover_letter(cover_letter_id)
    if cover_letter is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    return templates.TemplateResponse(
        "cover_letters/confirm_delete.html",
        {
            "request": request,
            "cover_letter": cover_letter,
        },
    )


@router.post("/{cover_letter_id}/delete", response_class=HTMLResponse, name="cover_letters_delete")
def delete_cover_letter(
    request: Request,
    cover_letter_id: int,
    confirm_delete: str = Form(""),
) -> RedirectResponse:
    if confirm_delete != "yes":
        return _redirect_to_detail(request, cover_letter_id, "Eliminacion cancelada.")

    if not cover_letter_repository.soft_delete_cover_letter(cover_letter_id):
        raise HTTPException(status_code=404, detail="Carta no encontrada.")

    return _redirect_to_list(request, "Carta eliminada correctamente.")


@router.get("/{cover_letter_id}/export/tex", name="cover_letters_export_tex")
def export_cover_letter_tex(cover_letter_id: int) -> FileResponse:
    cover_letter = _get_existing_cover_letter(cover_letter_id)

    try:
        generated_document = generate_cover_letter_tex_document(cover_letter, DEFAULT_COVER_LETTER_TEMPLATE_KEY)
        exported_file = export_cover_letter_generated_tex_document(cover_letter, generated_document)
    except LatexTemplateError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ExportServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _download_file(exported_file.path, exported_file.filename, exported_file.media_type)


@router.get("/{cover_letter_id}/export/pdf", name="cover_letters_export_pdf")
def export_cover_letter_pdf(request: Request, cover_letter_id: int):
    cover_letter = _get_existing_cover_letter(cover_letter_id)

    try:
        result = generate_cover_letter_pdf_export(cover_letter, DEFAULT_COVER_LETTER_TEMPLATE_KEY)
    except LatexTemplateError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PdfCompilationError as error:
        logger.error(
            "Cover letter PDF generation failed for cover_letter_id=%s: %s",
            cover_letter_id,
            error.technical_detail or str(error),
        )
        return _redirect_to_detail(request, cover_letter_id, error.user_message)
    except ExportServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _download_file(result.exported_pdf.path, result.exported_pdf.filename, result.exported_pdf.media_type)


def _build_cover_letter_form_with_errors(
    *,
    company: str,
    position: str,
    contact: str,
    greeting: str,
    introduction: str,
    body: str,
    closing: str,
    signature: str,
    associated_cv_id_raw: str,
) -> tuple[CoverLetterFormData, dict[str, str]]:
    associated_cv_id = _parse_associated_cv_id(associated_cv_id_raw)
    associated_cv_exists = True
    if associated_cv_id is not None:
        associated_cv_exists = cv_repository.get_cv(associated_cv_id) is not None

    form_data = build_cover_letter_form_data(
        {
            "company": company,
            "position": position,
            "contact": contact,
            "greeting": greeting,
            "introduction": introduction,
            "body": body,
            "closing": closing,
            "signature": signature,
        },
        associated_cv_id,
    )
    errors = validate_cover_letter_form(
        form_data,
        associated_cv_id_raw=associated_cv_id_raw,
        associated_cv_exists=associated_cv_exists,
    )
    return form_data, errors


def _parse_associated_cv_id(raw_value: str) -> int | None:
    normalized = raw_value.strip()
    if not normalized:
        return None
    if not normalized.isdigit():
        return None
    return int(normalized)


def _empty_form_data() -> CoverLetterFormData:
    return CoverLetterFormData(
        company="",
        position="",
        contact="",
        greeting="",
        introduction="",
        body="",
        closing="",
        signature="",
        associated_cv_id=None,
    )


def _get_existing_cover_letter(cover_letter_id: int) -> CoverLetter:
    cover_letter = cover_letter_repository.get_cover_letter(cover_letter_id)
    if cover_letter is None:
        raise HTTPException(status_code=404, detail="Carta no encontrada.")
    return cover_letter


def _download_file(path, filename: str, media_type: str) -> FileResponse:
    return FileResponse(path=path, filename=filename, media_type=media_type)


def _render_form(
    request: Request,
    form_data: CoverLetterFormData,
    errors: dict[str, str],
    action_url: str,
    page_title: str,
    submit_label: str,
    cover_letter_id: int | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "cover_letters/form.html",
        {
            "request": request,
            "form_data": form_data,
            "errors": errors,
            "action_url": action_url,
            "page_title": page_title,
            "submit_label": submit_label,
            "cover_letter_id": cover_letter_id,
            "available_cvs": cv_repository.list_cvs(),
        },
        status_code=status_code,
    )


def _redirect_to_detail(request: Request, cover_letter_id: int, message: str) -> RedirectResponse:
    url = request.url_for("cover_letters_detail", cover_letter_id=cover_letter_id).include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)


def _redirect_to_list(request: Request, message: str) -> RedirectResponse:
    url = request.url_for("cover_letters_list").include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)
