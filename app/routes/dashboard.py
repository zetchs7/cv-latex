from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database import get_database_status


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request) -> HTMLResponse:
    modules = [
        {
            "name": "CVs",
            "status": "Activo - MVP local",
            "description": "Crear, editar, importar y exportar CVs en TEX, PDF y JSON.",
            "url_name": "cvs_list",
            "is_active": True,
            "action_label": "Abrir CVs",
        },
        {
            "name": "Cartas de presentacion",
            "status": "Activo - MVP local",
            "description": "Gestionar cartas con asociacion opcional a CV y exportacion TEX/PDF.",
            "url_name": "cover_letters_list",
            "is_active": True,
            "action_label": "Abrir cartas",
        },
        {
            "name": "Postulaciones",
            "status": "Activo - MVP local",
            "description": "Registrar oportunidades, estados, seguimiento y asociaciones a CVs y cartas.",
            "url_name": "applications_list",
            "is_active": True,
            "action_label": "Abrir postulaciones",
        },
        {
            "name": "ATS Basic Check",
            "status": "Activo - MVP local",
            "description": "Analizar CVs guardados con checklist, score simple y recomendaciones sin IA.",
            "url_name": "ats_index",
            "is_active": True,
            "action_label": "Abrir ATS",
        },
        {
            "name": "Configuracion local",
            "status": "Pendiente",
            "description": "Reservado para ajustes operativos futuros fuera del alcance del MVP actual.",
            "url_name": None,
            "is_active": False,
        },
    ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": "CV LaTeX Builder",
            "app_status": "MVP local listo para validacion",
            "database_status": get_database_status(),
            "modules": modules,
        },
    )
