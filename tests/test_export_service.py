import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.models import CV, CoverLetter
from app.services.export_service import (
    ExportServiceError,
    MAX_JSON_IMPORT_BYTES,
    SAFE_EXPORT_FILENAME_MAX_LENGTH,
    build_cv_form_data_from_json,
    export_cv_json,
    export_cover_letter_generated_tex_document,
    export_cv_tex,
    read_limited_upload_bytes,
    sanitize_filename,
)
from app.services.latex_service import generate_cover_letter_tex_document


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

    def test_exports_cover_letter_tex_with_long_company_and_position(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                cover_letter = _build_long_cover_letter()
                generated_document = generate_cover_letter_tex_document(cover_letter, "classic_letter")
                exported_file = export_cover_letter_generated_tex_document(cover_letter, generated_document)

                self.assertTrue(exported_file.path.exists())
                self.assertLessEqual(len(exported_file.filename), SAFE_EXPORT_FILENAME_MAX_LENGTH)
                self.assertLessEqual(len(generated_document.filename), SAFE_EXPORT_FILENAME_MAX_LENGTH)
                self.assertTrue(exported_file.filename.startswith("cover-letter-31-"))

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


def _build_long_cover_letter() -> CoverLetter:
    return CoverLetter(
        id=31,
        company="A" * 160,
        position="B" * 160,
        contact="Hiring Team",
        greeting="Estimado equipo,",
        introduction="Presento mi candidatura.",
        body="Experiencia con Python y FastAPI.",
        closing="Saludos cordiales.",
        signature="Juan Perez",
        associated_cv_id=None,
        associated_cv_title=None,
        created_at="2026-06-04 00:00:00",
        updated_at="2026-06-04 00:00:00",
        deleted_at=None,
    )


if __name__ == "__main__":
    unittest.main()
