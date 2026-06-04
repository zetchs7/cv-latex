import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import CV
from app.services.pdf_service import PdfCompilationError, generate_cv_pdf_export


class PdfServiceTest(unittest.TestCase):
    def test_generates_pdf_export_with_controlled_temp_directory(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                with patch("app.services.pdf_service.subprocess.run", side_effect=_successful_pdflatex):
                    result = generate_cv_pdf_export(_build_cv(), "classic")

                self.assertTrue(result.exported_pdf.path.exists())
                self.assertEqual(result.exported_pdf.path.parent, Path(data_directory) / "exports")
                self.assertEqual(result.exported_pdf.media_type, "application/pdf")
                self.assertTrue(result.exported_tex.path.exists())
                self.assertEqual(list((Path(data_directory) / "exports" / "_tmp").glob("cv-pdf-*")), [])

    def test_reports_missing_latex_engine(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                with patch("app.services.pdf_service.subprocess.run", side_effect=FileNotFoundError):
                    with self.assertRaises(PdfCompilationError) as context:
                        generate_cv_pdf_export(_build_cv(), "classic")

        self.assertIn("motor LaTeX", str(context.exception))
        self.assertIn("pdflatex", context.exception.technical_detail)

    def test_reports_safe_message_for_compilation_failure(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                with patch("app.services.pdf_service.subprocess.run", side_effect=_failed_pdflatex):
                    with self.assertRaises(PdfCompilationError) as context:
                        generate_cv_pdf_export(_build_cv(), "classic")

        self.assertEqual(
            str(context.exception),
            "No se pudo generar el PDF con la plantilla seleccionada. Revisa el contenido del CV o consulta los logs tecnicos.",
        )
        self.assertIn("Undefined control sequence", context.exception.technical_detail)


def _successful_pdflatex(command, cwd, **kwargs):
    tex_filename = command[-1]
    pdf_path = Path(cwd) / f"{Path(tex_filename).stem}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")


def _failed_pdflatex(command, cwd, **kwargs):
    log_path = Path(cwd) / f"{Path(command[-1]).stem}.log"
    log_path.write_text("! Undefined control sequence.\nl.42", encoding="utf-8")
    return subprocess.CompletedProcess(command, 1, stdout="", stderr="")


def _build_cv() -> CV:
    return CV(
        id=8,
        title="CV PDF",
        full_name="Juan Perez",
        email="juan@example.com",
        phone="",
        professional_summary="Perfil",
        experience_summary="Experiencia",
        education_summary="Educacion",
        skills="Python",
        created_at="2026-06-03 00:00:00",
        updated_at="2026-06-03 00:00:00",
        deleted_at=None,
    )


if __name__ == "__main__":
    unittest.main()
