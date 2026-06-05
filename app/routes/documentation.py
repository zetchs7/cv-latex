from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.documentation_service import list_documentation_assets, load_documentation_page


router = APIRouter(prefix="/documentation", tags=["Documentation"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="documentation_index")
def documentation_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "documentation/index.html",
        {
            "documents": list_documentation_assets(),
        },
    )


@router.get("/{document_key}", response_class=HTMLResponse, name="documentation_view")
def documentation_view(request: Request, document_key: str) -> HTMLResponse:
    page = load_documentation_page(document_key)
    if page is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    return templates.TemplateResponse(
        request,
        "documentation/detail.html",
        {
            "documents": list_documentation_assets(),
            "page": page,
        },
    )
