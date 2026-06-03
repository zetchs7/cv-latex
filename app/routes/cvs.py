from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.repositories import cv_repository
from app.schemas import CVFormData
from app.validations.cv_validations import build_cv_form_data, validate_cv_form


router = APIRouter(prefix="/cvs", tags=["CVs"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="cvs_list")
def list_cvs(request: Request, message: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(
        "cvs/index.html",
        {
            "request": request,
            "cvs": cv_repository.list_cvs(),
            "message": message,
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


@router.get("/{cv_id}", response_class=HTMLResponse, name="cvs_detail")
def cv_detail(request: Request, cv_id: int, message: str | None = None) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return templates.TemplateResponse(
        "cvs/detail.html",
        {
            "request": request,
            "cv": cv,
            "message": message,
        },
    )


@router.get("/{cv_id}/edit", response_class=HTMLResponse, name="cvs_edit")
def edit_cv(request: Request, cv_id: int) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

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
            status_code=422,
        )

    if not cv_repository.update_cv(cv_id, form_data):
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return _redirect_to_detail(request, cv_id, "CV actualizado correctamente.")


@router.post("/{cv_id}/duplicate", response_class=HTMLResponse, name="cvs_duplicate")
def duplicate_cv(request: Request, cv_id: int) -> RedirectResponse:
    duplicate_id = cv_repository.duplicate_cv(cv_id)
    if duplicate_id is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return _redirect_to_detail(request, duplicate_id, "CV duplicado correctamente.")


@router.get("/{cv_id}/delete", response_class=HTMLResponse, name="cvs_confirm_delete")
def confirm_delete_cv(request: Request, cv_id: int) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    return templates.TemplateResponse(
        "cvs/confirm_delete.html",
        {
            "request": request,
            "cv": cv,
        },
    )


@router.post("/{cv_id}/delete", response_class=HTMLResponse, name="cvs_delete")
def delete_cv(request: Request, cv_id: int, confirm_delete: str = Form("")) -> RedirectResponse:
    if confirm_delete != "yes":
        return _redirect_to_detail(request, cv_id, "Eliminacion cancelada.")

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


def _render_form(
    request: Request,
    form_data: CVFormData,
    errors: dict[str, str],
    action_url: str,
    page_title: str,
    submit_label: str,
    cv_id: int | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "cvs/form.html",
        {
            "request": request,
            "form_data": form_data,
            "errors": errors,
            "action_url": action_url,
            "page_title": page_title,
            "submit_label": submit_label,
            "cv_id": cv_id,
        },
        status_code=status_code,
    )


def _redirect_to_detail(request: Request, cv_id: int, message: str) -> RedirectResponse:
    url = request.url_for("cvs_detail", cv_id=cv_id).include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)


def _redirect_to_list(request: Request, message: str) -> RedirectResponse:
    url = request.url_for("cvs_list").include_query_params(message=message)
    return RedirectResponse(str(url), status_code=303)
