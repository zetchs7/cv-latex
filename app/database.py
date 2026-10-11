from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


DEFAULT_DATA_DIR = "/data"
DEFAULT_DB_FILENAME = "app.db"
CURRENT_SCHEMA_VERSION = "2"
REPOSITORY_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TESTING_ENV_MARKER = "CV_LATEX_TESTING"
STRUCTURED_CV_COLUMNS = {
    "structured_schema_version": "INTEGER",
    "structured_payload": "TEXT",
    "structured_payload_status": "TEXT NOT NULL DEFAULT 'legacy'",
}


@dataclass(frozen=True)
class DatabaseStatus:
    path: str
    exists: bool
    directory_exists: bool


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return False


def _is_test_process() -> bool:
    """Indica si el proceso actual es una corrida de pruebas.

    El marcador explicito lo define `tests/conftest.py` antes de importar
    cualquier modulo de la app. La presencia de `pytest` en `sys.modules` cubre
    las corridas que importan la app desde una sesion de pruebas ya abierta.
    """

    if os.getenv(TESTING_ENV_MARKER):
        return True

    return "pytest" in sys.modules


def _is_inside_directory(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False

    return True


def _temporary_root() -> Path:
    return Path(tempfile.gettempdir())


def _ensure_test_data_dir_is_isolated(data_dir: Path) -> None:
    """Rechaza todo directorio de datos que no sea temporal durante las pruebas.

    Un unico chequeo contra `<repo>/data` no alcanza: un test o un fixture
    puede reasignar `APP_DATA_DIR` mas adelante en la corrida y apuntar, por
    ejemplo, a `/data`, que es el store real montado por Docker Compose.
    Durante una corrida de pruebas solo se admite un directorio bajo la raiz
    temporal del sistema. `resolve()` sigue symlinks, asi que un enlace que
    apunte al store real tambien queda rechazado.
    """

    if _is_inside_directory(data_dir, REPOSITORY_DATA_DIR):
        raise RuntimeError(
            "El directorio de datos del repositorio no puede usarse durante las pruebas: "
            f"{data_dir} esta dentro de {REPOSITORY_DATA_DIR}. "
            f"Apunta APP_DATA_DIR a un temporal y exporta {TESTING_ENV_MARKER}=1 "
            "(tests/conftest.py lo resuelve automaticamente) para aislar la corrida."
        )

    if not _is_inside_directory(data_dir, _temporary_root()):
        raise RuntimeError(
            "Durante las pruebas el directorio de datos debe estar bajo la raiz temporal "
            f"del sistema ({_temporary_root()}): {data_dir} queda fuera. "
            f"Apunta APP_DATA_DIR a un temporal; {TESTING_ENV_MARKER}=1 lo resuelve "
            "tests/conftest.py automaticamente."
        )


def get_data_dir() -> Path:
    data_dir = Path(os.getenv("APP_DATA_DIR", DEFAULT_DATA_DIR))

    if _is_test_process():
        _ensure_test_data_dir_is_isolated(data_dir)

    return data_dir


def get_database_path() -> Path:
    data_dir = get_data_dir()
    database_path = data_dir / os.getenv("APP_DB_FILENAME", DEFAULT_DB_FILENAME)

    # `Path / "ruta_absoluta"` devuelve la ruta absoluta y un `..` resuelve hacia
    # arriba, asi que `APP_DB_FILENAME` podria sacar la base fuera del directorio
    # de datos ya aislado. Se exige que quede dentro de ese directorio, no solo
    # bajo la raiz temporal: un `..` que suba un nivel seguiria dentro de `/tmp`
    # y escaparia del directorio de pruebas.
    if _is_test_process() and not _is_inside_directory(database_path, data_dir):
        raise RuntimeError(
            "Durante las pruebas la base de datos debe quedar dentro del directorio "
            f"de datos de la corrida ({data_dir}): {database_path} queda fuera. "
            "Revisa APP_DB_FILENAME; no admite rutas absolutas ni rutas con '..'."
        )

    return database_path


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(get_database_path(), factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    return connection


def get_table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    if not table_name.isidentifier():
        raise ValueError("Nombre de tabla invalido para inspeccion de schema.")

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def migrate_cvs_table(connection: sqlite3.Connection) -> None:
    existing_columns = get_table_columns(connection, "cvs")

    for column_name, column_definition in STRUCTURED_CV_COLUMNS.items():
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE cvs ADD COLUMN {column_name} {column_definition}")
            existing_columns.add(column_name)


def initialize_database() -> DatabaseStatus:
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    database_path = get_database_path()

    with sqlite3.connect(database_path, factory=ClosingConnection) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_metadata (
                metadata_key TEXT PRIMARY KEY,
                metadata_value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO app_metadata (metadata_key, metadata_value)
            VALUES ('schema_version', :schema_version)
            ON CONFLICT(metadata_key) DO UPDATE SET
                metadata_value = excluded.metadata_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            {"schema_version": CURRENT_SCHEMA_VERSION},
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cvs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                professional_summary TEXT NOT NULL DEFAULT '',
                experience_summary TEXT NOT NULL DEFAULT '',
                education_summary TEXT NOT NULL DEFAULT '',
                skills TEXT NOT NULL DEFAULT '',
                structured_schema_version INTEGER,
                structured_payload TEXT,
                structured_payload_status TEXT NOT NULL DEFAULT 'legacy',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            )
            """
        )
        migrate_cvs_table(connection)
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cvs_deleted_at_updated_at
            ON cvs (deleted_at, updated_at)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cover_letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL DEFAULT '',
                position TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                greeting TEXT NOT NULL DEFAULT '',
                introduction TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                closing TEXT NOT NULL DEFAULT '',
                signature TEXT NOT NULL DEFAULT '',
                associated_cv_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cover_letters_deleted_at_updated_at
            ON cover_letters (deleted_at, updated_at)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cover_letters_associated_cv_id
            ON cover_letters (associated_cv_id)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL DEFAULT '',
                position TEXT NOT NULL DEFAULT '',
                link TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                applied_on TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pendiente',
                associated_cv_id INTEGER,
                associated_cover_letter_id INTEGER,
                notes TEXT NOT NULL DEFAULT '',
                next_action TEXT NOT NULL DEFAULT '',
                follow_up_date TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_applications_deleted_at_updated_at
            ON applications (deleted_at, updated_at)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_applications_status_applied_on
            ON applications (status, applied_on)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_applications_associated_cv_id
            ON applications (associated_cv_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_applications_associated_cover_letter_id
            ON applications (associated_cover_letter_id)
            """
        )
        connection.commit()

    return get_database_status()


def get_database_status() -> DatabaseStatus:
    data_dir = get_data_dir()
    database_path = get_database_path()

    return DatabaseStatus(
        path=str(database_path),
        exists=database_path.exists(),
        directory_exists=data_dir.exists(),
    )
