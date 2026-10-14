"""Configuración → Entornos y datos.

Todas las operaciones destructivas exigen:
- que el entorno venga del prefijo de la ruta, nunca de un campo del formulario;
- un token CSRF por sesión, comparado con `hmac.compare_digest`;
- una frase de confirmación exacta escrita por la persona.

La confirmación visual no se trata como medida de seguridad: es una protección
contra errores, no contra una petición forjada. Por eso la frase se valida en el
servidor y la selección se revalida en el momento de ejecutar, sin confiar en la
previsualización.

Las rutas viven bajo `/config` sin prefijo propio, de modo que son alcanzables
tanto en global (`/config/workspaces`) como dentro de un entorno
(`/test/config/workspaces`). En el segundo caso el middleware ya fijó el
entorno, así que ninguna operación tiene que adivinar de qué base depende.
"""

from __future__ import annotations

import hmac
import secrets

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.environments import Environment, current_environment, legacy_storage_in_use, prefix_of, resolved_data_root
from app.services.workspace_service import (
    MAX_GENERATE_PER_KIND,
    DummyDataError,
    delete_selected,
    dependencies_of,
    execute_migration,
    generate_dummy_data,
    inventory,
    plan_migration,
    purge_environment,
    selected_records,
)

router = APIRouter(prefix="/config", tags=["config"])

CSRF_COOKIE = "gentle_workspace_csrf"

KIND_LABELS = {
    "cvs": "Currículum",
    "cover_letters": "Carta",
    "applications": "Postulación",
}


# --- CSRF --------------------------------------------------------------------


def _csrf_token(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)


def _csrf_valid(request: Request, submitted: str) -> bool:
    expected = request.cookies.get(CSRF_COOKIE)
    if not expected or not submitted:
        return False
    return hmac.compare_digest(expected, submitted)


def _render(request: Request, template: str, context: dict, status_code: int = 200):
    from app.template_utils import create_templates

    templates = create_templates()
    payload = {
        "request": request,
        "csrf_token": _csrf_token(request),
        "max_generate_per_kind": MAX_GENERATE_PER_KIND,
        **context,
    }
    response = templates.TemplateResponse(request, template, payload, status_code=status_code)
    # `httponly` y `samesite` no son adornos: sin ellos el token sería legible
    # desde JavaScript y viajaría en peticiones cruzadas, que es justo lo que el
    # token existe para impedir.
    response.set_cookie(
        CSRF_COOKIE,
        payload["csrf_token"],
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return response


def _message(request: Request, text: str, level: str, template: str = "workspaces/settings.html"):
    return _render(
        request,
        template,
        {"notice": text, "notice_level": level, "environments": list(Environment)},
    )


def _require_environment(request: Request, expected: Environment) -> Environment | None:
    environment = current_environment()
    if environment is expected:
        return environment

    if expected is Environment.TEST:
        return _message(
            request,
            "Estas herramientas solo funcionan en MODO PRUEBAS. "
            "Entrá desde Configuración → Entornos y datos.",
            "error",
        )
    return None


# --- Selección de entorno ----------------------------------------------------


@router.get("/workspaces", response_class=HTMLResponse, name="workspace_settings")
async def workspace_settings(request: Request):
    plan = plan_migration()
    try:
        pending = legacy_storage_in_use(resolved_data_root())
    except OSError:
        pending = False

    return _render(
        request,
        "workspaces/settings.html",
        {
            "environments": list(Environment),
            "legacy_pending": pending,
            "counts": inventory(current_environment()) if current_environment() else None,
        },
    )


@router.post("/workspaces/enter", name="workspace_enter")
async def workspace_enter(request: Request, environment: str = Form(...), csrf_token: str = Form("")):
    if not _csrf_valid(request, csrf_token):
        return _message(request, "La sesión expiró. Volvé a intentarlo.", "error")

    target = Environment(environment) if environment in ("real", "test") else Environment.REAL
    return RedirectResponse(url=f"{prefix_of(target)}/", status_code=303)


# --- Administrar datos de PRUEBAS -------------------------------------------


def _records_for(environment: Environment, kind: str) -> list[dict]:
    if kind not in KIND_LABELS:
        kind = "cvs"
    return selected_records(environment, kind)


@router.get("/workspaces/manage/{kind}", response_class=HTMLResponse, name="workspace_manage")
async def workspace_manage(request: Request, kind: str = "cvs"):
    environment = current_environment()
    if environment is None:
        return RedirectResponse(url=request.url_for("workspace_settings"), status_code=303)
    if environment is Environment.REAL:
        return _message(
            request,
            "En el entorno REAL no hay herramientas de datos de prueba. "
            "Cambiá a MODO PRUEBAS para generar o borrar datos ficticios.",
            "error",
        )

    if kind not in KIND_LABELS:
        kind = "cvs"

    return _render(
        request,
        "workspaces/manage.html",
        {
            "kind": kind,
            "records": _records_for(environment, kind),
            "counts": {name: len(_records_for(environment, name)) for name in KIND_LABELS},
        },
    )


@router.post("/workspaces/generate", name="workspace_generate")
async def workspace_generate(
    request: Request,
    cvs: int = Form(0),
    cover_letters: int = Form(0),
    applications: int = Form(0),
    csrf_token: str = Form(""),
):
    if not _csrf_valid(request, csrf_token):
        return _message(request, "La sesión expiró. Volvé a intentarlo.", "error")

    environment = current_environment()
    if environment is not Environment.TEST:
        return _message(
            request, "Los datos de prueba solo se generan en MODO PRUEBAS.", "error"
        )

    try:
        result = generate_dummy_data(
            environment, cvs=cvs, cover_letters=cover_letters, applications=applications
        )
    except DummyDataError as error:
        return _message(request, error.user_message, "error")

    return _message(
        request,
        f"Listo: {len(result.cvs)} currículums, {len(result.cover_letters)} cartas y "
        f"{len(result.applications)} postulaciones creados en MODO PRUEBAS.",
        "success",
    )


# Tope de seleccion por tipo. Coincide con el `LIMIT 500` de `selected_records`,
# asi que nadie puede mandar mas ids de los que la pantalla podria mostrar, y el
# cuerpo del formulario queda acotado en el orden de los 64 KB que declara la
# matriz de limites.
MAX_SELECTION_PER_KIND = 500


def _selection_from_form(
    cvs: list[int], cover_letters: list[int], applications: list[int]
) -> dict[str, list[int]]:
    selection = {
        "cvs": sorted({int(value) for value in cvs}),
        "cover_letters": sorted({int(value) for value in cover_letters}),
        "applications": sorted({int(value) for value in applications}),
    }
    for kind, ids in selection.items():
        if len(ids) > MAX_SELECTION_PER_KIND:
            raise DummyDataError(
                f"Seleccionaste mas de {MAX_SELECTION_PER_KIND} registros de tipo "
                f"{kind}. Hacelo en dos tandas.",
                code="selection_too_large",
            )
    return selection


def _selected_rows(environment: Environment, selection: dict[str, list[int]]) -> list[dict]:
    rows: list[dict] = []
    for kind, ids in selection.items():
        if not ids:
            continue
        by_id = {record["id"]: record for record in _records_for(environment, kind)}
        for record_id in ids:
            record = by_id.get(record_id)
            if record is None:
                continue
            title = (
                record.get("title")
                or record.get("company")
                or record.get("full_name")
                or "Sin título"
            )
            rows.append(
                {"kind_label": KIND_LABELS[kind], "title": title, "id": record_id}
            )
    return rows


def _kept_dependencies(environment: Environment, selection: dict[str, list[int]]) -> list[dict]:
    """Postulaciones que usan registros seleccionados pero no están seleccionadas."""

    dependencies = dependencies_of(environment, selection)
    kept = dependencies.get("applications_kept", []) + dependencies.get(
        "applications_kept_by_letter", []
    )
    seen: set[int] = set()
    unique: list[dict] = []
    for row in kept:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        unique.append(row)
    return unique


@router.post("/workspaces/delete/preview", name="workspace_delete_preview")
async def workspace_delete_preview(
    request: Request,
    cvs: list[int] = Form(default=[]),
    cover_letters: list[int] = Form(default=[]),
    applications: list[int] = Form(default=[]),
    csrf_token: str = Form(""),
):
    if not _csrf_valid(request, csrf_token):
        return _message(request, "La sesión expiró. Volvé a intentarlo.", "error")

    environment = _require_environment(request, Environment.TEST)
    if not isinstance(environment, Environment):
        return environment

    try:
        selection = _selection_from_form(cvs, cover_letters, applications)
    except DummyDataError as error:
        return _message(request, error.user_message, "error")
    total = sum(len(values) for values in selection.values())
    if total == 0:
        return RedirectResponse(url=request.url_for("workspace_manage", kind="cvs"), status_code=303)

    return _render(
        request,
        "workspaces/confirm_delete.html",
        {
            "kind": "cvs",
            "selection": selection,
            "records": _selected_rows(environment, selection),
            "dependencies": _kept_dependencies(environment, selection),
            "total": total,
            "expected_phrase": f"ELIMINAR {total} DE PRUEBAS",
        },
    )


@router.post("/workspaces/delete/execute", name="workspace_delete_execute")
async def workspace_delete_execute(
    request: Request,
    cvs: list[int] = Form(default=[]),
    cover_letters: list[int] = Form(default=[]),
    applications: list[int] = Form(default=[]),
    typed_confirmation: str = Form(""),
    csrf_token: str = Form(""),
):
    if not _csrf_valid(request, csrf_token):
        return _message(request, "La sesión expiró. Volvé a intentarlo.", "error")

    environment = _require_environment(request, Environment.TEST)
    if not isinstance(environment, Environment):
        return environment

    try:
        selection = _selection_from_form(cvs, cover_letters, applications)
    except DummyDataError as error:
        return _message(request, error.user_message, "error")
    total = sum(len(values) for values in selection.values())
    expected = f"ELIMINAR {total} DE PRUEBAS"
    if typed_confirmation.strip() != expected:
        return _render(
            request,
            "workspaces/confirm_delete.html",
            {
                "kind": "cvs",
                "selection": selection,
                "records": _selected_rows(environment, selection),
                "dependencies": _kept_dependencies(environment, selection),
                "total": total,
                "expected_phrase": expected,
                "notice": f"Para borrar, escribí exactamente: {expected}",
                "notice_level": "error",
            },
            status_code=422,
        )

    # Se revalida contra la base real en este instante: una previsualización vieja
    # no sirve, porque los registros pudieron cambiar entre las dos pantallas.
    kept = _kept_dependencies(environment, selection)
    if kept:
        return _render(
            request,
            "workspaces/confirm_delete.html",
            {
                "kind": "cvs",
                "selection": selection,
                "records": _selected_rows(environment, selection),
                "dependencies": kept,
                "total": total,
                "expected_phrase": expected,
                "notice": (
                    f"Hay {len(kept)} postulación(es) que usan estos registros y no estaban "
                    "seleccionadas. No se borró nada."
                ),
                "notice_level": "error",
            },
            status_code=409,
        )

    try:
        result = delete_selected(environment, selection)
    except DummyDataError as error:
        return _message(request, error.user_message, "error")

    if result["pending"]:
        return _message(
            request,
            f"Se borraron {result['cvs']} currículums, {result['cover_letters']} cartas y "
            f"{result['applications']} postulaciones, pero quedaron {len(result['pending'])} "
            "elementos sin borrar. Revisalos antes de reintentar.",
            "error",
        )

    return _message(
        request,
        f"Borrados: {result['cvs']} currículums, {result['cover_letters']} cartas y "
        f"{result['applications']} postulaciones, más {result['files']} archivos.",
        "success",
    )


# --- Vaciar todo el entorno de PRUEBAS ---------------------------------------


@router.get("/workspaces/purge-confirm", response_class=HTMLResponse, name="workspace_purge_confirm")
async def workspace_purge_confirm(request: Request):
    environment = current_environment()
    if environment is None:
        return RedirectResponse(url=request.url_for("workspace_settings"), status_code=303)
    if environment is Environment.REAL:
        return _message(request, "Solo se puede vaciar el entorno de PRUEBAS.", "error")

    summary = inventory(environment)
    return _render(
        request,
        "workspaces/confirm_purge.html",
        {
            "counts": {
                "cvs": summary.cvs,
                "cover_letters": summary.cover_letters,
                "applications": summary.applications,
                "soft_total": (
                    summary.soft_deleted_cvs
                    + summary.soft_deleted_cover_letters
                    + summary.soft_deleted_applications
                ),
                "exports": summary.exports,
                "drafts": summary.drafts,
                "total": summary.total,
            }
        },
    )


@router.post("/workspaces/purge", name="workspace_purge")
async def workspace_purge(
    request: Request,
    confirmation: str = Form(""),
    csrf_token: str = Form(""),
):
    if not _csrf_valid(request, csrf_token):
        return _message(request, "La sesión expiró. Volvé a intentarlo.", "error")

    environment = current_environment()
    if environment is not Environment.TEST:
        return _message(request, "Solo se puede vaciar el entorno de PRUEBAS.", "error")

    if confirmation.strip() != "VACIAR PRUEBAS":
        return _message(
            request, "Para vaciar todo, escribí exactamente: VACIAR PRUEBAS", "error"
        )

    try:
        result = purge_environment(environment)
    except DummyDataError as error:
        return _message(request, error.user_message, "error")

    if result["pending"]:
        return _message(
            request,
            f"Se vaciaron {result['files']} elementos pero quedaron "
            f"{len(result['pending'])} pendientes. Revisalos antes de reintentar.",
            "error",
        )

    return _message(request, "MODO PRUEBAS vaciado. Quedó listo para generar datos nuevos.", "success")


# --- Migración ---------------------------------------------------------------


@router.get("/workspaces/migration", response_class=HTMLResponse, name="workspace_migration")
async def workspace_migration(request: Request):
    plan = plan_migration()
    return _render(
        request,
        "workspaces/migration.html",
        {
            "plan": plan,
            "counts": plan.counts,
            "problems": plan.problems,
            "exports": plan.exports,
            "drafts": plan.drafts,
        },
    )


@router.post("/workspaces/migrate", name="workspace_migrate")
async def workspace_migrate(
    request: Request,
    confirmation: str = Form(""),
    csrf_token: str = Form(""),
):
    if not _csrf_valid(request, csrf_token):
        return _message(request, "La sesión expiró. Volvé a intentarlo.", "error")

    plan = plan_migration()
    try:
        result = execute_migration(require_confirmation=confirmation.strip())
    except DummyDataError as error:
        return _render(
            request,
            "workspaces/migration.html",
            {
                "plan": plan,
                "counts": plan.counts,
                "problems": plan.problems,
                "exports": plan.exports,
                "drafts": plan.drafts,
                "error": error.user_message,
            },
            status_code=422,
        )

    return _render(
        request,
        "workspaces/migration.html",
        {
            "plan": plan_migration(),
            "counts": result["counts"],
            "problems": [],
            "exports": 0,
            "drafts": 0,
            "done": "Migración completada. La base original se conserva como checkpoint.",
        },
    )
