import logging

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.repositories import cv_repository
from app.repositories.cv_repository import DuplicateCVError, StructuredCVLegacyUpdateError
from app.models import CV
from app.schemas import CVFormData
from app.services import structured_cv_editor_service
from app.services.ats_service import analyze_cv_ats
from app.services.export_service import (
    ExportServiceError,
    STRUCTURED_JSON_EXPORT_SCHEMA_VERSION,
    build_cv_json_import_result,
    export_cv_json,
    export_cv_tex,
    read_limited_upload_bytes,
)
from app.services.latex_service import (
    DEFAULT_TEMPLATE_KEY,
    LatexTemplateError,
    available_cv_templates,
    generate_cv_tex_document,
)
from app.services.pdf_service import PdfCompilationError, generate_cv_pdf_export
from app.services.structured_cv_service import StructuredCVWriteError, resolve_structured_cv_state
from app.template_utils import create_templates
from app.validations.cv_validations import build_cv_form_data, validate_cv_form


router = APIRouter(prefix="/cvs", tags=["CVs"])
templates = create_templates()
logger = logging.getLogger(__name__)

LEGACY_EDIT_BLOCKED_MESSAGE = (
    "Este CV tiene datos estructurados y no se puede editar con el formulario plano porque "
    "ese formulario no puede representar ni conservar los datos de schema 2. "
    "Usa el editor estructurado."
)


@router.get("/", response_class=HTMLResponse, name="cvs_list")
def list_cvs(request: Request, message: str | None = None) -> HTMLResponse:
    cvs = cv_repository.list_cvs()
    return templates.TemplateResponse(
        request,
        "cvs/index.html",
        {
            "cvs": cvs,
            "cv_cards": _build_cv_cards(cvs),
            "message": message,
            "templates": available_cv_templates(),
            "default_template": DEFAULT_TEMPLATE_KEY,
        },
    )


@router.get("/new", response_class=HTMLResponse, name="cvs_new")
def new_cv(request: Request) -> HTMLResponse:
    return _render_form(
        request=request,
        form_data=_empty_form_data(),
        errors={},
        action_url=str(request.url_for("cvs_create")),
        page_title="Crear CV",
        submit_label="Crear CV",
    )


@router.get("/new/structured", response_class=HTMLResponse, name="cvs_new_structured")
def new_structured_cv(request: Request) -> HTMLResponse:
    context = structured_cv_editor_service.build_new_editor_context()
    return _render_structured_form(
        request,
        context,
        action_url=str(request.url_for("cvs_create_structured")),
        page_title="Crear CV estructurado",
        submit_label="Crear CV estructurado",
    )


@router.post("/new/structured", response_class=HTMLResponse, name="cvs_create_structured")
def create_structured_cv(
    request: Request,
    title: str = Form(""),
    structured_payload: str = Form(""),
) -> HTMLResponse:
    payload, errors = structured_cv_editor_service.parse_structured_editor_submission(structured_payload)

    if not errors:
        try:
            cv_id = cv_repository.create_structured_cv(
                title=title,
                payload=payload,
                metadata_source=structured_cv_editor_service.STRUCTURED_EDITOR_METADATA_SOURCE,
            )
            return _redirect_to_detail(request, cv_id, "CV estructurado creado correctamente.")
        except StructuredCVWriteError as error:
            errors = structured_cv_editor_service.translate_structured_editor_errors(error.errors)

    context = structured_cv_editor_service.build_failed_submission_context(
        title=title,
        payload=payload,
        errors=errors,
        cv_id=None,
        is_structured=False,
        mode_reason="new_structured_cv",
        source_warning="",
    )
    return _render_structured_form(
        request,
        context,
        action_url=str(request.url_for("cvs_create_structured")),
        page_title="Crear CV estructurado",
        submit_label="Crear CV estructurado",
        status_code=422,
    )


@router.post("/", response_class=HTMLResponse, name="cvs_create")
def create_cv(
    request: Request,
    title: str = Form(""),
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    professional_summary: str = Form(""),
    experience_summary: str = Form(""),
    education_summary: str = Form(""),
    skills: str = Form(""),
):
    form_data = _build_form_data_from_fields(
        title,
        full_name,
        email,
        phone,
        professional_summary,
        experience_summary,
        education_summary,
        skills,
    )
    errors = validate_cv_form(form_data)

    if errors:
        return _render_form(
            request=request,
            form_data=form_data,
            errors=errors,
            action_url=str(request.url_for("cvs_create")),
            page_title="Crear CV",
            submit_label="Crear CV",
            status_code=422,
        )

    cv_id = cv_repository.create_cv(form_data)
    return _redirect_to_detail(request, cv_id, "CV creado correctamente.")


@router.post("/import/json", response_class=HTMLResponse, name="cvs_import_json")
def import_cv_json(request: Request, json_file: UploadFile = File(...)) -> RedirectResponse:
    try:
        raw_content = read_limited_upload_bytes(json_file.file)
        import_result = build_cv_json_import_result(raw_content)
    except ExportServiceError as error:
        return _redirect_to_list(request, f"No se pudo importar el JSON: {error}")

    if import_result.schema_version == STRUCTURED_JSON_EXPORT_SCHEMA_VERSION:
        try:
            cv_id = cv_repository.create_structured_cv(
                title=import_result.structured_title,
                payload=import_result.structured_payload,
                metadata_source="json_import",
            )
        except StructuredCVWriteError as error:
            return _redirect_to_list(request, f"No se pudo importar el JSON: {error}")

        return _redirect_to_detail(request, cv_id, "CV importado desde JSON correctamente.")

    cv_id = cv_repository.create_cv(import_result.form_data)
    return _redirect_to_detail(request, cv_id, "CV importado desde JSON correctamente.")


@router.get("/{cv_id}", response_class=HTMLResponse, name="cvs_detail")
def cv_detail(request: Request, cv_id: int, message: str | None = None) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return templates.TemplateResponse(
        request,
        "cvs/detail.html",
        {
            "cv": cv,
            "message": message,
            "templates": available_cv_templates(),
            "default_template": DEFAULT_TEMPLATE_KEY,
            "is_structured": resolve_structured_cv_state(cv).is_structured,
        },
    )


@router.get("/{cv_id}/tex", response_class=HTMLResponse, name="cvs_tex_preview")
def cv_tex_preview(
    request: Request,
    cv_id: int,
    template_key: str = DEFAULT_TEMPLATE_KEY,
) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    try:
        generated_document = generate_cv_tex_document(cv, template_key)
    except LatexTemplateError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return templates.TemplateResponse(
        request,
        "cvs/tex_preview.html",
        {
            "cv": cv,
            "generated_document": generated_document,
            "templates": available_cv_templates(),
            "selected_template": template_key,
        },
    )


@router.get("/{cv_id}/export/tex", name="cvs_export_tex")
def export_tex(cv_id: int, template_key: str = DEFAULT_TEMPLATE_KEY) -> FileResponse:
    cv = _get_existing_cv(cv_id)

    try:
        exported_file = export_cv_tex(cv, template_key)
    except LatexTemplateError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ExportServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _download_file(exported_file.path, exported_file.filename, exported_file.media_type)


@router.get("/{cv_id}/export/json", name="cvs_export_json")
def export_json(cv_id: int, schema_version: int | None = None) -> FileResponse:
    cv = _get_existing_cv(cv_id)

    try:
        exported_file = export_cv_json(cv, schema_version=schema_version)
    except ExportServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _download_file(exported_file.path, exported_file.filename, exported_file.media_type)


@router.get("/{cv_id}/export/pdf", name="cvs_export_pdf")
def export_pdf(request: Request, cv_id: int, template_key: str = DEFAULT_TEMPLATE_KEY):
    cv = _get_existing_cv(cv_id)

    try:
        result = generate_cv_pdf_export(cv, template_key)
    except LatexTemplateError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PdfCompilationError as error:
        logger.error(
            "PDF generation failed for cv_id=%s template=%s: %s",
            cv_id,
            template_key,
            error.technical_detail or str(error),
        )
        return _redirect_to_detail(request, cv_id, error.user_message)
    except ExportServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _download_file(result.exported_pdf.path, result.exported_pdf.filename, result.exported_pdf.media_type)


@router.get("/{cv_id}/edit", response_class=HTMLResponse, name="cvs_edit")
def edit_cv(request: Request, cv_id: int) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    if resolve_structured_cv_state(cv).is_structured:
        return _redirect_to_structured_edit(request, cv_id, LEGACY_EDIT_BLOCKED_MESSAGE)

    return _render_form(
        request=request,
        form_data=CVFormData(
            title=cv.title,
            full_name=cv.full_name,
            email=cv.email,
            phone=cv.phone,
            professional_summary=cv.professional_summary,
            experience_summary=cv.experience_summary,
            education_summary=cv.education_summary,
            skills=cv.skills,
        ),
        errors={},
        action_url=str(request.url_for("cvs_update", cv_id=cv.id)),
        page_title="Editar CV",
        submit_label="Guardar cambios",
        cv_id=cv.id,
        context_title=cv.title,
        context_full_name=cv.full_name,
    )


@router.post("/{cv_id}/edit", response_class=HTMLResponse, name="cvs_update")
def update_cv(
    request: Request,
    cv_id: int,
    title: str = Form(""),
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    professional_summary: str = Form(""),
    experience_summary: str = Form(""),
    education_summary: str = Form(""),
    skills: str = Form(""),
):
    current_cv = cv_repository.get_cv(cv_id)
    if current_cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    if resolve_structured_cv_state(current_cv).is_structured:
        return _redirect_to_detail(request, cv_id, LEGACY_EDIT_BLOCKED_MESSAGE)

    form_data = _build_form_data_from_fields(
        title,
        full_name,
        email,
        phone,
        professional_summary,
        experience_summary,
        education_summary,
        skills,
    )
    errors = validate_cv_form(form_data)

    if errors:
        return _render_form(
            request=request,
            form_data=form_data,
            errors=errors,
            action_url=str(request.url_for("cvs_update", cv_id=cv_id)),
            page_title="Editar CV",
            submit_label="Guardar cambios",
            cv_id=cv_id,
            context_title=form_data.title or current_cv.title,
            context_full_name=form_data.full_name or current_cv.full_name,
            status_code=422,
        )

    try:
        updated = cv_repository.update_cv(cv_id, form_data)
    except StructuredCVLegacyUpdateError as error:
        logger.warning("Legacy CV update blocked for structured cv_id=%s: %s", cv_id, error)
        return _redirect_to_detail(request, cv_id, LEGACY_EDIT_BLOCKED_MESSAGE)

    if not updated:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return _redirect_to_detail(request, cv_id, "CV actualizado correctamente.")


@router.get("/{cv_id}/structured-edit", response_class=HTMLResponse, name="cvs_structured_edit")
def structured_edit_cv(request: Request, cv_id: int, message: str | None = None) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    context = structured_cv_editor_service.build_structured_editor_context_for_cv(cv)
    return _render_structured_form(
        request,
        context,
        action_url=str(request.url_for("cvs_structured_update", cv_id=cv_id)),
        page_title="Editar CV estructurado",
        submit_label="Guardar cambios estructurados",
        message=message or "",
    )


@router.post("/{cv_id}/structured-edit", response_class=HTMLResponse, name="cvs_structured_update")
def structured_update_cv(
    request: Request,
    cv_id: int,
    title: str = Form(""),
    structured_payload: str = Form(""),
) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    payload, errors = structured_cv_editor_service.parse_structured_editor_submission(structured_payload)

    if not errors:
        try:
            if not cv_repository.update_structured_cv(
                cv_id,
                title=title,
                payload=payload,
                metadata_source=structured_cv_editor_service.STRUCTURED_EDITOR_METADATA_SOURCE,
            ):
                raise HTTPException(status_code=404, detail="CV no encontrado.")
            return _redirect_to_detail(request, cv_id, "CV estructurado actualizado correctamente.")
        except StructuredCVWriteError as error:
            errors = structured_cv_editor_service.translate_structured_editor_errors(error.errors)

    current_context = structured_cv_editor_service.build_structured_editor_context_for_cv(cv)
    context = structured_cv_editor_service.build_failed_submission_context(
        title=title,
        payload=payload if payload is not None else current_context.payload,
        errors=errors,
        cv_id=cv_id,
        is_structured=current_context.is_structured,
        mode_reason=current_context.mode_reason,
        source_warning=current_context.source_warning,
    )
    return _render_structured_form(
        request,
        context,
        action_url=str(request.url_for("cvs_structured_update", cv_id=cv_id)),
        page_title="Editar CV estructurado",
        submit_label="Guardar cambios estructurados",
        status_code=422,
    )


@router.post("/{cv_id}/duplicate", response_class=HTMLResponse, name="cvs_duplicate")
def duplicate_cv(request: Request, cv_id: int) -> RedirectResponse:
    try:
        duplicate_id = cv_repository.duplicate_cv(cv_id)
        if duplicate_id is None:
            raise HTTPException(status_code=404, detail="CV no encontrado.")
    except DuplicateCVError as error:
        logger.warning("CV duplication blocked for cv_id=%s: %s", cv_id, error)
        return _redirect_to_detail(request, cv_id, "No se pudo duplicar el CV porque los datos no cumplen las validaciones actuales.")

    return _redirect_to_detail(request, duplicate_id, "CV duplicado correctamente.")


@router.get("/{cv_id}/delete", response_class=HTMLResponse, name="cvs_confirm_delete")
def confirm_delete_cv(request: Request, cv_id: int) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return _render_delete_confirmation(request, cv)


@router.post("/{cv_id}/delete", response_class=HTMLResponse, name="cvs_delete")
def delete_cv(request: Request, cv_id: int, confirmation_value: str = Form("")):
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    expected_title = cv.title.strip()
    if confirmation_value.strip() != expected_title:
        return _render_delete_confirmation(
            request,
            cv,
            error="El texto ingresado no coincide exactamente con el titulo del CV.",
            entered_value=confirmation_value,
            status_code=422,
        )

    if not cv_repository.soft_delete_cv(cv_id):
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return _redirect_to_list(request, "CV eliminado correctamente.")


def _build_form_data_from_fields(
    title: str,
    full_name: str,
    email: str,
    phone: str,
    professional_summary: str,
    experience_summary: str,
    education_summary: str,
    skills: str,
) -> CVFormData:
    return build_cv_form_data(
        {
            "title": title,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "professional_summary": professional_summary,
            "experience_summary": experience_summary,
            "education_summary": education_summary,
            "skills": skills,
        }
    )


def _empty_form_data() -> CVFormData:
    return CVFormData(
        title="",
        full_name="",
        email="",
        phone="",
        professional_summary="",
        experience_summary="",
        education_summary="",
        skills="",
    )


def _get_existing_cv(cv_id: int) -> CV:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")
    return cv


def _download_file(path, filename: str, media_type: str) -> FileResponse:
    return FileResponse(
        path=path,
        filename=filename,
        media_type=media_type,
    )


def _render_form(
    request: Request,
    form_data: CVFormData,
    errors: dict[str, str],
    action_url: str,
    page_title: str,
    submit_label: str,
    cv_id: int | None = None,
    context_title: str | None = None,
    context_full_name: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "cvs/form.html",
        {
            "form_data": form_data,
            "errors": errors,
            "action_url": action_url,
            "page_title": page_title,
            "submit_label": submit_label,
            "cv_id": cv_id,
            "context_title": context_title,
            "context_full_name": context_full_name,
        },
        status_code=status_code,
    )


def _render_structured_form(
    request: Request,
    context: structured_cv_editor_service.StructuredEditorContext,
    *,
    action_url: str,
    page_title: str,
    submit_label: str,
    status_code: int = 200,
    message: str = "",
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "cvs/structured_form.html",
        {
            "editor": context,
            "action_url": action_url,
            "page_title": page_title,
            "submit_label": submit_label,
            "message": message,
        },
        status_code=status_code,
    )


def _redirect_to_detail(request: Request, cv_id: int, message: str) -> RedirectResponse:
    url = request.url_for("cvs_detail", cv_id=cv_id).include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)


def _redirect_to_structured_edit(request: Request, cv_id: int, message: str) -> RedirectResponse:
    url = request.url_for("cvs_structured_edit", cv_id=cv_id).include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)


def _redirect_to_list(request: Request, message: str) -> RedirectResponse:
    url = request.url_for("cvs_list").include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)


def _render_delete_confirmation(
    request: Request,
    cv: CV,
    *,
    error: str | None = None,
    entered_value: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "cvs/confirm_delete.html",
        {
            "cv": cv,
            "expected_value": cv.title,
            "entered_value": entered_value,
            "error": error,
        },
        status_code=status_code,
    )


def _build_cv_cards(cvs: list[CV]) -> list[dict[str, object]]:
    return [
        {
            "cv": cv,
            "ats_analysis": analyze_cv_ats(cv),
        }
        for cv in cvs
    ]
