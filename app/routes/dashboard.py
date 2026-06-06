from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.repositories import application_repository, cover_letter_repository, cv_repository
from app.template_utils import create_templates


router = APIRouter()
templates = create_templates()


@router.get("/", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request) -> HTMLResponse:
    cvs = cv_repository.list_cvs()
    cover_letters = cover_letter_repository.list_cover_letters()
    applications = application_repository.list_applications()

    primary_modules = [
        {
            "name": "Curriculum Vitae",
            "count": len(cvs),
            "description": "CRUD completo, importacion JSON y exportaciones TEX, PDF y JSON.",
            "url_name": "cvs_list",
            "action_label": "Abrir CVs",
            "preview_total": min(len(cvs), 3),
        },
        {
            "name": "Cartas de presentacion",
            "count": len(cover_letters),
            "description": "Cartas reutilizables con exportacion TEX y PDF y asociacion opcional a un CV.",
            "url_name": "cover_letters_list",
            "action_label": "Abrir cartas",
            "preview_total": min(len(cover_letters), 3),
        },
    ]

    secondary_modules = [
        {
            "name": "Postulaciones",
            "status": f"{len(applications)} activas",
            "description": "Seguimiento local de oportunidades y proximas acciones.",
            "url_name": "applications_list",
            "action_label": "Ver pipeline",
            "is_active": True,
        },
        {
            "name": "ATS",
            "status": "Chequeo basico",
            "description": "Score y checklist rapido sobre CVs guardados.",
            "url_name": "ats_index",
            "action_label": "Analizar CVs",
            "is_active": True,
        },
        {
            "name": "Documentacion",
            "status": "HTML + PDF",
            "description": "Manual web, documentacion tecnica y referencia de rollback.",
            "url_name": "documentation_index",
            "action_label": "Abrir docs",
            "is_active": True,
        },
        {
            "name": "Configuracion local",
            "status": "Placeholder",
            "description": "Reservado para ajustes locales futuros fuera del alcance de esta etapa.",
            "url_name": None,
            "action_label": "Proximamente",
            "is_active": False,
        },
    ]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "app_name": "CV LaTeX Builder",
            "primary_modules": primary_modules,
            "secondary_modules": secondary_modules,
            "recent_cvs": cvs[:3],
            "recent_cover_letters": cover_letters[:3],
            "counts": {
                "cvs": len(cvs),
                "cover_letters": len(cover_letters),
                "applications": len(applications),
            },
        },
    )
