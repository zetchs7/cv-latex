"""Middleware que resuelve el entorno desde el prefijo de la ruta.

`/real/cvs/` y `/test/cvs/` se enrutan como `/cvs/` gracias a `root_path`, que
es el mecanismo con el que ASGI describe "esta aplicacion esta montada bajo un
prefijo". No se recorta `scope["path"]` a mano: la especificacion pide que
`path` conserve el prefijo y que el enrutado use `path - root_path`, y usar la
primitiva en vez de reimplementarla hace que las redirecciones internas de
Starlette (barra final, rutas no encontradas) conserven el entorno sin codigo
adicional.

Tampoco se toca `url_for`: con `root_path` activo devuelve el prefijo solo,
asique los enlaces, formularios y estaticos quedan dentro del entorno.

El estado vive en un `ContextVar`, no en el proceso: dos peticiones simultaneas
ven valores distintos. La cookie no participa de la decision, asi que dos
pestanas abiertas en entornos distintos no se pisan.
"""

from __future__ import annotations

import asyncio
import itertools
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.environments import (
    ENVIRONMENT_PREFIXES,
    Environment,
    PREFIX_BY_ENVIRONMENT,
    current_environment,
    legacy_migrated,
    migration_in_progress,
    prefix_of,
    reset_environment,
    resolved_data_root,
    set_environment,
)
from app.services.workspace_service import ensure_environment_ready


# Rutas sin prefijo que no leen ni escriben datos, y que por eso siguen igual
# despues de la migracion. `/health` es el healthcheck del contenedor: si se
# redirigiera, `urllib.urlopen` caeria en `/real/health` (404) y el contenedor
# quedaria unhealthy aunque la app este bien. Mismo criterio durante el candado
# de migracion: `health` y `static` no tocan datos, y tumbar el healthcheck
# durante unos segundos haria que el contenedor se reiniciara en peor momento.
_UNPREFIXED_EXEMPT = ("/static", "/health")


def _is_exempt_from_retirement(path: str) -> bool:
    return path in _UNPREFIXED_EXEMPT or path.startswith("/static/")


def _migration_in_progress() -> HTMLResponse:
    """503 mientras se copia la base historica.

    No es un error de la aplicacion sino una ventana deliberada: contestar
    cualquier cosa que no sea leer `/health` o `/static` durante el snapshot
    permitiria una escritura que quedaria solo en la base retirada. El mensaje
    incluye la salida porque el candado vive en el disco de datos: si un corte
    abrupto lo dejara puesto, nadie puede llegar a la pantalla de migracion para
    enterarse, y esta respuesta es la unica que va a ver.
    """

    return HTMLResponse(
        "<h1>La migracion de entornos esta en curso</h1>"
        "<p>Se estan moviendo los datos historicos. Espera unos segundos y "
        "recarga.</p>"
        "<p>Si esto sigue igual mas tarde, revisa el archivo "
        "<code>.environments-migrating</code> en la raiz de datos: borrarlo "
        "vuelve a habilitar la aplicacion.</p>",
        status_code=503,
        headers={"Retry-After": "5"},
    )


# Peticiones admitidas en este momento. El drenaje de la migracion la usa para
# garantizar que no quede ninguna escritura en vuelo cuando empieza el snapshot:
# una peticion que ya paso el chequeo del candado puede seguir corriendo despues
# de que el archivo exista, y esa escritura quedaria presente en la base
# retirada pero ausente del destino.
_admitted: set[int] = set()
_admission: ContextVar[int | None] = ContextVar("workspace_admission", default=None)
_next_admission = itertools.count(1)


async def _admit(call_next, request: Request):
    """Corre la peticion y la deja registrada mientras esta admitida.

    El identificador se comparte con el handler por la misma via con la que
    `set_environment` comparte el entorno, asi que una vista puede descartar su
    propia peticion al drenar sin depender de la identidad del objeto Request.
    """

    identifier = next(_next_admission)
    _admitted.add(identifier)
    token = _admission.set(identifier)
    try:
        return await call_next(request)
    finally:
        _admission.reset(token)
        _admitted.discard(identifier)


async def drain_admitted_requests(*, timeout: float = 10.0) -> bool:
    """Espera a que no quede ninguna peticion admitida salvo la actual.

    Se llama con el candado de migracion puesto, asi que ninguna peticion nueva
    entra: solo resta esperar a las que ya estaban adentro. Drena cediendo el
    loop, que es lo que permite a esas peticiones terminar; no puede esperarse
    sin ceder, porque en ese caso nunca se ejecutarian y el tiempo se agotaria.

    Devuelve False si se agota el plazo, y entonces no se migra nada: la
    alternativa seria correr el riesgo que el drenaje viene a cerrar.
    """

    mine = _admission.get()
    if not _admitted - {mine}:
        return True

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while _admitted - {mine}:
        if loop.time() >= deadline:
            return False
        await asyncio.sleep(0.01)

    return True


def _redirect_to_real(request: Request, path: str) -> RedirectResponse:
    """Retira la vista historica mandando a REAL, no a PRUEBAS.

    El prefijo de destino sale del catalogo, no de un literal: si un dia se
    agregara un entorno, esta ruta no quedaria apuntando a uno escrito a mano.

    303 y no 307 a proposito: un POST que llegue sin prefijo se convierte en GET
    y no escribe nada. En la aplicacion nadie manda POST sin prefijo (todos los
    enlaces salen con el prefijo), pero si alguien llegara a mandar uno, el
    resultado seguro es no escribir, no redirigir la escritura a REAL.
    """

    query = request.scope.get("query_string", b"")
    target = f"{PREFIX_BY_ENVIRONMENT[Environment.REAL]}{path}"
    if query:
        target = f"{target}?{query.decode('latin-1')}"
    return RedirectResponse(url=target, status_code=303)


class WorkspaceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.scope.get("path", "")
        matched = None
        for prefix, environment in ENVIRONMENT_PREFIXES.items():
            if path == prefix or path.startswith(prefix + "/"):
                matched = (prefix, environment)
                break

        if not _is_exempt_from_retirement(path) and migration_in_progress(
            resolved_data_root()
        ):
            return _migration_in_progress()

        if matched is None:
            exempt = _is_exempt_from_retirement(path)
            # Sin prefijo: mientras no se migro, la vista historica sigue
            # operando sobre la base de siempre. Una vez migrada se retira, para
            # que no quede un tercer espacio de trabajo conviviendo con REAL y
            # PRUEBAS.
            if legacy_migrated(resolved_data_root()) and not exempt:
                return _redirect_to_real(request, path)
            if exempt:
                # No tocan datos: registrarlas en el drenaje solo le agrega
                # ruido, y una forma de agotarlo sin motivo.
                return await call_next(request)
            return await _admit(call_next, request)

        prefix, environment = matched
        request.scope["root_path"] = prefix
        request.state.environment = environment

        token = set_environment(environment)
        try:
            # El directorio del entorno puede no existir aun: el arranque solo
            # inicializa la base legacy. Sin esto, la primera peticion de cada
            # entorno muere antes de llegar a ninguna ruta.
            ensure_environment_ready(environment)
            return await _admit(call_next, request)
        finally:
            reset_environment(token)


def redirect_to_current(request: Request, name: str, **path_params) -> RedirectResponse:
    """Redirige dentro del entorno de la peticion, o al raiz si no hay prefijo.

    `request.url_for` ya incorpora `root_path`, asi que aca no se concatena nada
    a mano: concatenarlo de nuevo produciria `/test/test/cvs`.
    """

    prefix = prefix_of(current_environment())
    try:
        url = request.url_for(name, **path_params)
    except Exception:  # noqa: BLE001 - una ruta sin nombre no debe tumbar la peticion
        url = "/"
    return RedirectResponse(url=str(url) or f"{prefix}/", status_code=303)
