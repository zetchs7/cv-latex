from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.documentation_service import get_documentation_asset, list_documentation_assets


router = APIRouter(prefix="/documentation", tags=["Documentation"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="documentation_index")
def documentation_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "documentation/index.html",
        {
            "documents": list_documentation_assets(),
            "selected_document": None,
        },
    )


@router.get("/{document_key}", response_class=HTMLResponse, name="documentation_view")
def documentation_view(request: Request, document_key: str) -> HTMLResponse:
    selected_document = get_documentation_asset(document_key)
    if selected_document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    return templates.TemplateResponse(
        request,
        "documentation/index.html",
        {
            "documents": list_documentation_assets(),
            "selected_document": selected_document,
        },
    )
