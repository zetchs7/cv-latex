from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3


DEFAULT_DATA_DIR = "/data"
DEFAULT_DB_FILENAME = "app.db"


@dataclass(frozen=True)
class DatabaseStatus:
    path: str
    exists: bool
    directory_exists: bool


def get_data_dir() -> Path:
    return Path(os.getenv("APP_DATA_DIR", DEFAULT_DATA_DIR))


def get_database_path() -> Path:
    return get_data_dir() / os.getenv("APP_DB_FILENAME", DEFAULT_DB_FILENAME)


def initialize_database() -> DatabaseStatus:
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    database_path = get_database_path()

    with sqlite3.connect(database_path) as connection:
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
            VALUES ('schema_version', '0')
            ON CONFLICT(metadata_key) DO UPDATE SET
                metadata_value = excluded.metadata_value,
                updated_at = CURRENT_TIMESTAMP
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
