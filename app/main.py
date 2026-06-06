from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import get_database_status, initialize_database
from app.routes.applications import router as applications_router
from app.routes.ats import router as ats_router
from app.routes.cover_letters import router as cover_letters_router
from app.routes.cvs import router as cvs_router
from app.routes.dashboard import router as dashboard_router
from app.routes.documentation import router as documentation_router


APP_VERSION = os.getenv("APP_VERSION", "0.8.0")
APP_ASSET_VERSION = os.getenv("APP_ASSET_VERSION", f"{APP_VERSION}-ui81fix1")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="CV LaTeX Builder",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.state.asset_version = APP_ASSET_VERSION

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(dashboard_router)
app.include_router(documentation_router)
app.include_router(cvs_router)
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
