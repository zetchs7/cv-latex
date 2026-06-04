from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.repositories import cv_repository
from app.services.ats_service import analyze_cv_ats


router = APIRouter(prefix="/ats", tags=["ATS"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="ats_index")
def ats_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "ats/index.html",
        {
            "cvs": cv_repository.list_cvs(),
        },
    )


@router.get("/cvs/{cv_id}", response_class=HTMLResponse, name="ats_cv_analysis")
def ats_cv_analysis(request: Request, cv_id: int) -> HTMLResponse:
    cv = cv_repository.get_cv(cv_id)
    if cv is None:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    analysis = analyze_cv_ats(cv)

    return templates.TemplateResponse(
        request,
        "ats/cv_analysis.html",
        {
            "cv": cv,
            "analysis": analysis,
        },
    )
