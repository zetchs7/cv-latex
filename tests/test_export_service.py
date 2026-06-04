import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.models import CV
from app.services.export_service import (
    ExportServiceError,
    MAX_JSON_IMPORT_BYTES,
    build_cv_form_data_from_json,
    export_cv_json,
    export_cv_tex,
    read_limited_upload_bytes,
    sanitize_filename,
)


class ExportServiceTest(unittest.TestCase):
    def test_sanitizes_filename_and_rejects_unknown_extensions(self):
        self.assertEqual(sanitize_filename("../Mi CV final.tex"), "mi-cv-final.tex")

        with self.assertRaises(ExportServiceError):
            sanitize_filename("cv.exe")

    def test_exports_tex_inside_data_exports(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                exported_file = export_cv_tex(_build_cv(), "classic")

                self.assertTrue(exported_file.path.exists())
                self.assertEqual(exported_file.path.parent.name, "exports")
                self.assertEqual(exported_file.media_type, "application/x-tex")
                self.assertIn(r"\documentclass", exported_file.path.read_text(encoding="utf-8"))

    def test_export_filenames_do_not_collide_for_close_requests(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                first_export = export_cv_tex(_build_cv(), "classic")
                second_export = export_cv_tex(_build_cv(), "classic")

                self.assertNotEqual(first_export.filename, second_export.filename)
                self.assertTrue(first_export.path.exists())
                self.assertTrue(second_export.path.exists())

    def test_exports_and_imports_json_payload(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                exported_file = export_cv_json(_build_cv())
                payload = json.loads(exported_file.path.read_text(encoding="utf-8"))
                imported_form = build_cv_form_data_from_json(json.dumps(payload).encode("utf-8"))

                self.assertEqual(payload["schema_version"], 1)
                self.assertEqual(imported_form.full_name, "Maria Munoz")
                self.assertEqual(imported_form.title, "CV Backend (importado)")

    def test_rejects_invalid_json_import(self):
        with self.assertRaises(ExportServiceError):
            build_cv_form_data_from_json(b'{"cv": {"title": 10}}')

    def test_rejects_oversized_json_upload_before_loading_everything(self):
        oversized_stream = io.BytesIO(b"a" * (MAX_JSON_IMPORT_BYTES + 1))

        with self.assertRaises(ExportServiceError) as context:
            read_limited_upload_bytes(oversized_stream)

        self.assertIn("supera el maximo permitido", str(context.exception))


def _build_cv() -> CV:
    return CV(
        id=7,
        title="CV Backend",
        full_name="Maria Munoz",
        email="maria@example.com",
        phone="+54 11 1234 5678",
        professional_summary="APIs seguras & mantenibles.",
        experience_summary="FastAPI",
        education_summary="",
        skills="Python, SQLite",
        created_at="2026-06-03 00:00:00",
        updated_at="2026-06-03 00:00:00",
        deleted_at=None,
    )


if __name__ == "__main__":
    unittest.main()
