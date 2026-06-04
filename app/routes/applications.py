from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models import Application
from app.repositories import application_repository, cover_letter_repository, cv_repository
from app.schemas import ApplicationFormData
from app.validations.application_validations import (
    APPLICATION_STATUSES,
    build_application_form_data,
    validate_application_form,
)


router = APIRouter(prefix="/applications", tags=["Applications"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="applications_list")
def list_applications(request: Request, message: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        "applications/index.html",
        {
            "request": request,
            "applications": application_repository.list_applications(),
            "message": message,
        },
    )


@router.get("/new", response_class=HTMLResponse, name="applications_new")
def new_application(request: Request) -> HTMLResponse:
    return _render_form(
        request=request,
        form_data=_empty_form_data(),
        errors={},
        action_url=str(request.url_for("applications_create")),
        page_title="Crear postulacion",
        submit_label="Crear postulacion",
    )


@router.post("/", response_class=HTMLResponse, name="applications_create")
def create_application(
    request: Request,
    company: str = Form(""),
    position: str = Form(""),
    link: str = Form(""),
    source: str = Form(""),
    applied_on: str = Form(""),
    status: str = Form(""),
    associated_cv_id: str = Form(""),
    associated_cover_letter_id: str = Form(""),
    notes: str = Form(""),
    next_action: str = Form(""),
    follow_up_date: str = Form(""),
):
    form_data, errors = _build_application_form_with_errors(
        company=company,
        position=position,
        link=link,
        source=source,
        applied_on=applied_on,
        status=status,
        associated_cv_id_raw=associated_cv_id,
        associated_cover_letter_id_raw=associated_cover_letter_id,
        notes=notes,
        next_action=next_action,
        follow_up_date=follow_up_date,
    )

    if errors:
        return _render_form(
            request=request,
            form_data=form_data,
            errors=errors,
            action_url=str(request.url_for("applications_create")),
            page_title="Crear postulacion",
            submit_label="Crear postulacion",
            status_code=422,
        )

    application_id = application_repository.create_application(form_data)
    return _redirect_to_detail(request, application_id, "Postulacion creada correctamente.")


@router.get("/{application_id}", response_class=HTMLResponse, name="applications_detail")
def application_detail(request: Request, application_id: int, message: str | None = None) -> HTMLResponse:
    application = application_repository.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Postulacion no encontrada.")

    return templates.TemplateResponse(
        "applications/detail.html",
        {
            "request": request,
            "application": application,
            "message": message,
        },
    )


@router.get("/{application_id}/edit", response_class=HTMLResponse, name="applications_edit")
def edit_application(request: Request, application_id: int) -> HTMLResponse:
    application = application_repository.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Postulacion no encontrada.")

    return _render_form(
        request=request,
        form_data=ApplicationFormData(
            company=application.company,
            position=application.position,
            link=application.link,
            source=application.source,
            applied_on=application.applied_on,
            status=application.status,
            associated_cv_id=application.associated_cv_id,
            associated_cover_letter_id=application.associated_cover_letter_id,
            notes=application.notes,
            next_action=application.next_action,
            follow_up_date=application.follow_up_date,
        ),
        errors={},
        action_url=str(request.url_for("applications_update", application_id=application.id)),
        page_title="Editar postulacion",
        submit_label="Guardar cambios",
        application_id=application.id,
    )


@router.post("/{application_id}/edit", response_class=HTMLResponse, name="applications_update")
def update_application(
    request: Request,
    application_id: int,
    company: str = Form(""),
    position: str = Form(""),
    link: str = Form(""),
    source: str = Form(""),
    applied_on: str = Form(""),
    status: str = Form(""),
    associated_cv_id: str = Form(""),
    associated_cover_letter_id: str = Form(""),
    notes: str = Form(""),
    next_action: str = Form(""),
    follow_up_date: str = Form(""),
):
    form_data, errors = _build_application_form_with_errors(
        company=company,
        position=position,
        link=link,
        source=source,
        applied_on=applied_on,
        status=status,
        associated_cv_id_raw=associated_cv_id,
        associated_cover_letter_id_raw=associated_cover_letter_id,
        notes=notes,
        next_action=next_action,
        follow_up_date=follow_up_date,
    )

    if errors:
        return _render_form(
            request=request,
            form_data=form_data,
            errors=errors,
            action_url=str(request.url_for("applications_update", application_id=application_id)),
            page_title="Editar postulacion",
            submit_label="Guardar cambios",
            application_id=application_id,
            status_code=422,
        )

    if not application_repository.update_application(application_id, form_data):
        raise HTTPException(status_code=404, detail="Postulacion no encontrada.")

    return _redirect_to_detail(request, application_id, "Postulacion actualizada correctamente.")


@router.get("/{application_id}/delete", response_class=HTMLResponse, name="applications_confirm_delete")
def confirm_delete_application(request: Request, application_id: int) -> HTMLResponse:
    application = application_repository.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Postulacion no encontrada.")

    return templates.TemplateResponse(
        "applications/confirm_delete.html",
        {
            "request": request,
            "application": application,
        },
    )


@router.post("/{application_id}/delete", response_class=HTMLResponse, name="applications_delete")
def delete_application(
    request: Request,
    application_id: int,
    confirm_delete: str = Form(""),
) -> RedirectResponse:
    if confirm_delete != "yes":
        return _redirect_to_detail(request, application_id, "Eliminacion cancelada.")

    if not application_repository.soft_delete_application(application_id):
        raise HTTPException(status_code=404, detail="Postulacion no encontrada.")

    return _redirect_to_list(request, "Postulacion eliminada correctamente.")


def _build_application_form_with_errors(
    *,
    company: str,
    position: str,
    link: str,
    source: str,
    applied_on: str,
    status: str,
    associated_cv_id_raw: str,
    associated_cover_letter_id_raw: str,
    notes: str,
    next_action: str,
    follow_up_date: str,
) -> tuple[ApplicationFormData, dict[str, str]]:
    associated_cv_id = _parse_optional_id(associated_cv_id_raw)
    associated_cover_letter_id = _parse_optional_id(associated_cover_letter_id_raw)

    associated_cv_exists = True
    if associated_cv_id is not None:
        associated_cv_exists = cv_repository.get_cv(associated_cv_id) is not None

    associated_cover_letter_exists = True
    if associated_cover_letter_id is not None:
        associated_cover_letter_exists = cover_letter_repository.get_cover_letter(associated_cover_letter_id) is not None

    form_data = build_application_form_data(
        {
            "company": company,
            "position": position,
            "link": link,
            "source": source,
            "applied_on": applied_on,
            "status": status,
            "notes": notes,
            "next_action": next_action,
            "follow_up_date": follow_up_date,
        },
        associated_cv_id,
        associated_cover_letter_id,
    )
    errors = validate_application_form(
        form_data,
        associated_cv_id_raw=associated_cv_id_raw,
        associated_cover_letter_id_raw=associated_cover_letter_id_raw,
        associated_cv_exists=associated_cv_exists,
        associated_cover_letter_exists=associated_cover_letter_exists,
    )
    return form_data, errors


def _parse_optional_id(raw_value: str) -> int | None:
    normalized = raw_value.strip()
    if not normalized:
        return None
    if not normalized.isdigit():
        return None
    return int(normalized)


def _empty_form_data() -> ApplicationFormData:
    return ApplicationFormData(
        company="",
        position="",
        link="",
        source="",
        applied_on="",
        status="pendiente",
        associated_cv_id=None,
        associated_cover_letter_id=None,
        notes="",
        next_action="",
        follow_up_date="",
    )


def _get_cover_letter_options() -> list[dict[str, str | int]]:
    options: list[dict[str, str | int]] = []
    for cover_letter in cover_letter_repository.list_cover_letters():
        options.append(
            {
                "id": cover_letter.id,
                "label": f"{cover_letter.company} - {cover_letter.position}",
            }
        )
    return options


def _render_form(
    request: Request,
    form_data: ApplicationFormData,
    errors: dict[str, str],
    action_url: str,
    page_title: str,
    submit_label: str,
    application_id: int | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "applications/form.html",
        {
            "request": request,
            "form_data": form_data,
            "errors": errors,
            "action_url": action_url,
            "page_title": page_title,
            "submit_label": submit_label,
            "application_id": application_id,
            "available_cvs": cv_repository.list_cvs(),
            "available_cover_letters": _get_cover_letter_options(),
            "application_statuses": APPLICATION_STATUSES,
        },
        status_code=status_code,
    )


def _redirect_to_detail(request: Request, application_id: int, message: str) -> RedirectResponse:
    url = request.url_for("applications_detail", application_id=application_id).include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)


def _redirect_to_list(request: Request, message: str) -> RedirectResponse:
    url = request.url_for("applications_list").include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)
