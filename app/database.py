from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3


DEFAULT_DATA_DIR = "/data"
DEFAULT_DB_FILENAME = "app.db"
CURRENT_SCHEMA_VERSION = "2"
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


def get_data_dir() -> Path:
    return Path(os.getenv("APP_DATA_DIR", DEFAULT_DATA_DIR))


def get_database_path() -> Path:
    return get_data_dir() / os.getenv("APP_DB_FILENAME", DEFAULT_DB_FILENAME)


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
