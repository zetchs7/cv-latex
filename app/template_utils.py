from datetime import datetime

from fastapi.templating import Jinja2Templates

from app.environments import Environment, current_environment, legacy_storage_in_use, prefix_of


def workspace_context(request) -> dict:
    """Contexto compartido por todas las vistas.

    `workspace_path` es la ruta SIN el prefijo de entorno, que es la que las
    plantillas usan para saber cual es la seccion activa del menu. Si se dejara
    `request.url.path` con el prefijo, `/test/cvs` no matchearia con
    `startswith('/cvs')` y el menu quedaria siempre apagado en MODO PRUEBAS.
    """

    environment = current_environment()
    root = request.scope.get("root_path", "")
    path = request.url.path
    if root and path.startswith(root):
        path = path[len(root) :] or "/"

    return {
        "environment": environment,
        "is_test_mode": environment is Environment.TEST,
        "is_real_mode": environment is Environment.REAL,
        "is_legacy_mode": environment is None,
        "prefix": prefix_of(environment),
        "workspace_path": path,
        "legacy_storage_pending": environment is None and legacy_storage_unmigrated(),
    }


def legacy_storage_unmigrated() -> bool:
    from app.environments import resolved_data_root

    try:
        return legacy_storage_in_use(resolved_data_root())
    except OSError:
        return False


def create_templates() -> Jinja2Templates:
    templates = Jinja2Templates(
        directory="app/templates", context_processors=[workspace_context]
    )
    templates.env.filters["format_datetime_ar"] = format_datetime_ar
    templates.env.filters["ats_status_variant"] = ats_status_variant
    return templates


def format_datetime_ar(value: str | None) -> str:
    if not value:
        return "Sin dato"

    parsed_value = _parse_datetime(value)
    if parsed_value is None:
        return value

    return parsed_value.strftime("%d/%m/%Y %H:%M hs")


def ats_status_variant(status: str | None, score: int | None = None, max_score: int | None = None) -> str:
    if score is not None and max_score and score >= max_score:
        return "excellent"

    normalized_status = (status or "").strip().lower()
    if normalized_status == "bueno":
        return "good"
    if normalized_status == "mejorable":
        return "warning"
    if normalized_status == "insuficiente":
        return "danger"
    return "neutral"


def _parse_datetime(value: str) -> datetime | None:
    normalized_value = value.strip()
    if not normalized_value:
        return None

    candidates = [
        normalized_value,
        normalized_value.replace("Z", "+00:00"),
        normalized_value.replace(" ", "T"),
    ]

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue

    return None
