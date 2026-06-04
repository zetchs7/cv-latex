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
            "status": "Activo - Etapa 4",
            "description": "Creacion, edicion, importacion JSON y exportacion TEX/PDF/JSON.",
            "url_name": "cvs_list",
            "is_active": True,
        },
        {
            "name": "Cartas de presentacion",
            "status": "Activo - Etapa 4",
            "description": "CRUD basico de cartas con asociacion opcional a CV y exportacion TEX/PDF.",
            "url_name": "cover_letters_list",
            "is_active": True,
        },
        {
            "name": "Postulaciones",
            "status": "Pendiente - Etapa 5",
            "description": "Seguimiento de oportunidades laborales, estados y proximas acciones.",
            "url_name": None,
            "is_active": False,
        },
        {
            "name": "Configuracion",
            "status": "Pendiente",
            "description": "Opciones locales de la aplicacion cuando el MVP lo requiera.",
            "url_name": None,
            "is_active": False,
        },
    ]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": "CV LaTeX Builder",
            "app_status": "CVs y cartas activos",
            "database_status": get_database_status(),
            "modules": modules,
        },
    )
