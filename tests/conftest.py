"""Aislamiento automatico del directorio de datos para toda la suite.

Este modulo se ejecuta al importarse, antes de que pytest importe cualquier
test, porque varios modulos de la app resuelven el directorio de datos al
importarse. Aislar aqui significa que la suite no depende de que el entorno la
rodee (por ejemplo el runner Docker con tmpfs sobre `data`).

El chequeo es de cierre fallido: si el directorio de datos no resuelve al
temporal recien creado, la sesion aborta antes de que una prueba pueda escribir.
"""

from pathlib import Path
import atexit
import os
import shutil
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_DATA_DIR = REPO_ROOT / "data"
TEST_DATA_DIRECTORY_PREFIX = "cv-latex-tests-"
TESTING_MARKER_ENV_VAR = "CV_LATEX_TESTING"
KEEP_TEST_DATA_ENV_VAR = "CV_LATEX_KEEP_TEST_DATA"
REPOSITORY_DOCS_OUTPUT_DIR = REPO_ROOT / "app" / "static" / "docs"

# Los modulos `app.*` se importan por nombre de paquete: la raiz del repositorio
# tiene que estar en el path antes de importarlos, sin depender del cwd.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix=TEST_DATA_DIRECTORY_PREFIX)).resolve()


def _remove_test_data_dir() -> None:
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)


def _should_keep_test_data() -> bool:
    return bool(os.getenv(KEEP_TEST_DATA_ENV_VAR))


def _cleanup_test_data_dir() -> None:
    if _should_keep_test_data():
        return

    _remove_test_data_dir()


def _fail_closed(message: str) -> None:
    _remove_test_data_dir()
    raise RuntimeError("Aislamiento de tests fallido: " + message)


# Se registra antes de cualquier validacion para que ningun error inesperado
# durante la importacion deje el temporal huerfano en el sistema.
atexit.register(_cleanup_test_data_dir)

os.environ["APP_DATA_DIR"] = str(TEST_DATA_DIR)
os.environ[TESTING_MARKER_ENV_VAR] = "1"

from app.database import (  # noqa: E402  import tardio a proposito: exige APP_DATA_DIR
    DEFAULT_DB_FILENAME,
    get_data_dir,
    get_database_path,
)

# `APP_DB_FILENAME` puede venir del entorno del host como ruta absoluta o con
# `..`, y en ese caso `get_data_dir() / APP_DB_FILENAME` se sale del temporal
# aunque el directorio de datos este aislado. Se fija al nombre por defecto, que
# es el que esperan las pruebas de migracion, y con eso queda neutralizado
# cualquier valor hostil del host.
os.environ["APP_DB_FILENAME"] = DEFAULT_DB_FILENAME


RESOLVED_TEST_DATA_DIR = get_data_dir().resolve()

if RESOLVED_TEST_DATA_DIR != TEST_DATA_DIR:
    _fail_closed(
        f"get_data_dir() resolvio a {RESOLVED_TEST_DATA_DIR} en lugar de {TEST_DATA_DIR}. "
        "Ninguna prueba debe ejecutarse contra un directorio compartido."
    )

if RESOLVED_TEST_DATA_DIR == REPOSITORY_DATA_DIR.resolve() or REPOSITORY_DATA_DIR.resolve() in RESOLVED_TEST_DATA_DIR.parents:
    _fail_closed(
        f"el directorio de datos de la corrida es {RESOLVED_TEST_DATA_DIR}, "
        f"que pertenece al repositorio ({REPOSITORY_DATA_DIR}). "
        "Ninguna prueba debe escribir sobre el entorno real de la app."
    )

# La base tambien tiene que quedar dentro del temporal, no solo el directorio.
RESOLVED_TEST_DATABASE_PATH = get_database_path().resolve()
if TEST_DATA_DIR not in RESOLVED_TEST_DATABASE_PATH.parents:
    _fail_closed(
        f"get_database_path() resolvio a {RESOLVED_TEST_DATABASE_PATH}, fuera de "
        f"{TEST_DATA_DIR}. Revisa APP_DB_FILENAME."
    )


# --- Manifiesto del entorno que ninguna prueba debe tocar -------------------
#
# La comprobacion vive en un hook de fin de sesion y no dentro de un test: un
# test solo es el ultimo de su modulo, no de la corrida. aqui no se ejecutan
# escrituras reales, asi que comparar el estado final es seguro.
PROTECTED_PATHS = (REPOSITORY_DATA_DIR, REPOSITORY_DOCS_OUTPUT_DIR)


def _snapshot(paths: tuple[Path, ...]) -> dict[str, tuple[int, int] | None]:
    """Huella (ruta -> (tamano, mtime_ns)) del arbol de cada ruta protegida."""

    snapshot: dict[str, tuple[int, int] | None] = {}
    for root in paths:
        if not root.exists():
            snapshot[str(root)] = None
            continue

        for path in sorted(root.rglob("*")):
            if path.is_file():
                stat_result = path.stat()
                snapshot[str(path)] = (stat_result.st_size, stat_result.st_mtime_ns)

    return snapshot


PROTECTED_BASELINE = _snapshot(PROTECTED_PATHS)


def _diff_snapshots(before: dict, after: dict) -> list[str]:
    return sorted(
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    )


def _protected_paths_changed() -> list[str]:
    return _diff_snapshots(PROTECTED_BASELINE, _snapshot(PROTECTED_PATHS))


def pytest_sessionfinish(session, exitstatus) -> None:
    changed_paths = _protected_paths_changed()
    if changed_paths:
        sys.stderr.write(
            "\nCV LaTeX: FALLO DE AISLAMIENTO. La corrida modifico rutas del entorno "
            "real de la aplicacion:\n"
        )
        for path in changed_paths:
            sys.stderr.write(f"  - {path}\n")
        sys.stderr.flush()
        session.exitstatus = 1
        if not _should_keep_test_data():
            _remove_test_data_dir()
        return

    if _should_keep_test_data():
        sys.stdout.write(f"\nCV LaTeX: datos de la corrida conservados en {TEST_DATA_DIR}\n")
        sys.stdout.flush()
        return

    _remove_test_data_dir()