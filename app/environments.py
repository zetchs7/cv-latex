"""Entornos de trabajo: REAL y PRUEBAS.

La separacion es por RUTA, no por una bandera global mutable. `/real/...` y
`/test/...` son prefijos que la capa de middleware quita antes de enrutar y
registra en un `ContextVar`, que es el mecanismo estandar de contexto por
peticion en asincrono: dos peticiones concurrentes ven valores distintos aunque
compartan proceso, asi que no hay estado que una pueda cambiarle a la otra.

No se usa un flag de entorno global porque podria cambiar mientras hay peticiones
en vuelo. Tampoco se confia en una cookie: las cookies se comparten entre
pestanas, asi que dos pestanas en entornos distintos se pisarian. El prefijo de
la URL es explicito, admite bookmarks y sobrevive a cualquier numero de pestanas.
"""

from __future__ import annotations

from contextvars import ContextVar
from enum import Enum
from pathlib import Path
import os


class Environment(str, Enum):
    """Los dos almacenamientos independientes."""

    REAL = "real"
    TEST = "test"


# Prefijo de URL -> entorno. El orden importa solo para el mensaje de error, no
# para la resolucion: los prefijos no son prefijos entre si.
ENVIRONMENT_PREFIXES: dict[str, Environment] = {
    "/real": Environment.REAL,
    "/test": Environment.TEST,
}

PREFIX_BY_ENVIRONMENT = {environment: prefix for prefix, environment in ENVIRONMENT_PREFIXES.items()}

# `None` significa "sin entorno declarado": las rutas historicas (`/cvs/`, ...)
# siguen resolviendo el almacenamiento legacy, exactamente como antes. La
# separacion de entornos no cambia el comportamiento de lo que ya funciona.
_current: ContextVar[Environment | None] = ContextVar(
    "gentle_environment", default=None
)


def current_environment() -> Environment | None:
    return _current.get()


def set_environment(environment: Environment | None) -> object:
    """Fija el entorno de esta peticion y devuelve el token para restaurarlo."""

    return _current.set(environment)


def reset_environment(token: object) -> None:
    _current.reset(token)


def prefix_of(environment: Environment | None) -> str:
    return PREFIX_BY_ENVIRONMENT[environment] if environment else ""


def environment_data_root(data_root: Path, environment: Environment | None) -> Path:
    """Directorio de datos de un entorno concreto.

    Sin entorno declarado devuelve la raiz tal cual, que es donde vive la base
    legacy. Esto es deliberado: moverla habria roto todos los modulos actuales y
    todos los tests existentes por una decision de arquitectura, no por una
    necesidad.
    """

    if environment is None:
        return data_root
    return data_root / environment.value


def legacy_storage_in_use(data_root: Path) -> bool:
    """True si la raiz sigue teniendo la base historica sin migrar.

    La aplicacion lo usa para ofrecer una situacion de mantenimiento diagnosticable
    en vez de interpretar esos datos como pertenecientes a REAL, que seria el
    fallback silencioso que el requisito prohibe.
    """

    return (data_root / DEFAULT_DB_FILENAME).exists()


def legacy_migrated(data_root: Path) -> bool:
    """True cuando la vista historica sin prefijo ya quedo retirada.

    La vista sin entorno es exclusivamente transitoria: existe para no dejar la
    aplicacion inutilizable antes de migrar, no para convivir con los dos
    entornos. Despues de migrar solo REAL y PRUEBAS son operativos, asi que las
    rutas sin prefijo dejan de servir datos y redirigen a REAL.

    Exige las DOS condiciones a la vez:

    - que exista el marcador que escribe la migracion al terminar;
    - que la base historica NO este en la raiz.

    La segunda condicion es deliberada. Un rollback manual consiste en volver a
    poner `app.db` en la raiz; con la marca sola, esa operacion dejaria la
    aplicacion redirigiendo a REAL con la base historica muerta al lado, que es
    peor que el problema original. Con las dos condiciones, restaurar la base
    rehabilita la vista historica por si misma, sin depender de que nadie recuerde
    borrar un archivo.
    """

    if not (data_root / MIGRATION_MARKER_FILENAME).exists():
        return False
    return not legacy_storage_in_use(data_root)


def resolved_data_root() -> Path:
    """Raiz de datos ANTES de aplicar el entorno.

    Es `APP_DATA_DIR`, igual que siempre. El entorno es una subdivision, no un
    reemplazo de la variable.
    """

    return Path(os.getenv("APP_DATA_DIR", DEFAULT_DATA_DIR))


DEFAULT_DATA_DIR = "/data"
DEFAULT_DB_FILENAME = "app.db"
# Marcador de que la vista historica sin prefijo ya quedo retirada. Se escribe
# solo al final de una migracion exitosa; ver `legacy_migrated`.
MIGRATION_MARKER_FILENAME = ".environments-migrated"
