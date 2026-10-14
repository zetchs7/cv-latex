from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import get_database_status, initialize_database
from app.environments import legacy_migrated, resolved_data_root
from app.routes.applications import router as applications_router
from app.routes.ats import router as ats_router
from app.routes.cover_letters import router as cover_letters_router
from app.routes.cvs import router as cvs_router
from app.routes.dashboard import router as dashboard_router
from app.routes.pdf_import import router as pdf_import_router
from app.routes.documentation import router as documentation_router
from app.routes.workspaces import router as workspaces_router
from app.workspace_middleware import WorkspaceMiddleware


APP_VERSION = os.getenv("APP_VERSION", "0.9.0")
APP_ASSET_VERSION = os.getenv("APP_ASSET_VERSION", f"{APP_VERSION}-ui81210xss1")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Si la vista historica ya quedo retirada, arrancar creando una base nueva en
    # la raiz fabricaria un tercer espacio de trabajo en cada boot. Se omite a
    # proposito: sin prefijo no hay almacenamiento operativo.
    if not legacy_migrated(resolved_data_root()):
        initialize_database()
    yield


app = FastAPI(
    title="CV LaTeX Builder",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(WorkspaceMiddleware)
app.state.asset_version = APP_ASSET_VERSION

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(workspaces_router)
app.include_router(dashboard_router)
app.include_router(documentation_router)
app.include_router(cvs_router)
app.include_router(pdf_import_router)
app.include_router(ats_router)
app.include_router(cover_letters_router)
app.include_router(applications_router)


@app.get("/health", name="health")
def health() -> dict[str, object]:
    database_status = get_database_status()

    return {
        "status": "ok",
        "version": APP_VERSION,
        "database": {
            "path": database_status.path,
            "exists": database_status.exists,
            "directory_exists": database_status.directory_exists,
        },
    }
