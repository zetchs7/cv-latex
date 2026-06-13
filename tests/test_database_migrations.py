import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app.database import get_connection, get_table_columns, initialize_database
from app.repositories.cv_repository import get_cv


STRUCTURED_COLUMNS = {
    "structured_schema_version",
    "structured_payload",
    "structured_payload_status",
}


class DatabaseMigrationTest(unittest.TestCase):
    def test_new_database_creates_structured_cv_columns(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with get_connection() as connection:
                    columns = get_table_columns(connection, "cvs")

                self.assertTrue(STRUCTURED_COLUMNS.issubset(columns))

    def test_existing_legacy_database_is_migrated_without_losing_cvs(self):
        with tempfile.TemporaryDirectory() as data_directory:
            database_path = os.path.join(data_directory, "app.db")
            _create_legacy_database(database_path)

            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with get_connection() as connection:
                    columns = get_table_columns(connection, "cvs")

                self.assertTrue(STRUCTURED_COLUMNS.issubset(columns))
                cv = get_cv(1)
                self.assertIsNotNone(cv)
                self.assertEqual(cv.title, "CV Legacy")
                self.assertIsNone(cv.structured_schema_version)
                self.assertIsNone(cv.structured_payload)
                self.assertEqual(cv.structured_payload_status, "legacy")

    def test_migration_is_idempotent_when_run_twice(self):
        with tempfile.TemporaryDirectory() as data_directory:
            database_path = os.path.join(data_directory, "app.db")
            _create_legacy_database(database_path)

            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                initialize_database()

                with get_connection() as connection:
                    columns = get_table_columns(connection, "cvs")
                    row_count = connection.execute("SELECT COUNT(*) FROM cvs").fetchone()[0]

                self.assertTrue(STRUCTURED_COLUMNS.issubset(columns))
                self.assertEqual(row_count, 1)


def _create_legacy_database(database_path: str) -> None:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE cvs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                professional_summary TEXT NOT NULL DEFAULT '',
                experience_summary TEXT NOT NULL DEFAULT '',
                education_summary TEXT NOT NULL DEFAULT '',
                skills TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO cvs (
                title,
                full_name,
                email,
                phone,
                professional_summary,
                experience_summary,
                education_summary,
                skills
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "CV Legacy",
                "Persona Legacy",
                "legacy@example.com",
                "",
                "Perfil",
                "Experiencia",
                "Educacion",
                "Python",
            ),
        )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    unittest.main()
