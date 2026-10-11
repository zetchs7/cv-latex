import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import CV, CoverLetter
from app.services.pdf_service import PdfCompilationError, generate_cover_letter_pdf_export, generate_cv_pdf_export
from app.services.file_naming import SAFE_EXPORT_FILENAME_MAX_LENGTH


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

    def test_generates_pdf_export_for_structured_cv_all_templates(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                with patch("app.services.pdf_service.subprocess.run", side_effect=_successful_pdflatex):
                    for template_key in ("classic", "modern", "compact", "tech"):
                        with self.subTest(template_key=template_key):
                            result = generate_cv_pdf_export(_build_structured_cv(), template_key)

                            self.assertTrue(result.exported_pdf.path.exists())
                            self.assertEqual(result.exported_pdf.media_type, "application/pdf")
                            self.assertTrue(result.exported_tex.path.exists())
                            exported_tex_content = result.exported_tex.path.read_text(encoding="utf-8")
                            self.assertIn("Tech Lead de Plataformas", exported_tex_content)
                            self.assertIn("Certificacion AWS Solutions Architect", exported_tex_content)
                            self.assertIn("Observabilidad Abierta", exported_tex_content)
                            self.assertNotIn("SNAPSHOT-OBSOLETO", exported_tex_content)
                            self.assertNotIn("[[", exported_tex_content)

    def test_structured_pdf_export_tex_carries_break_opportunities_for_long_tokens(self):
        from app.services.structured_cv_service import serialize_structured_payload

        payload = {
            "schema_version": 2,
            "personal": {"full_name": "Ana Perez", "headline": "Tech Lead", "location": ""},
            "contact": {"email": "ana@example.com", "phone": "", "links": []},
            "summary": "",
            "experience": [
                {
                    "company": "Globex",
                    "role": "Lider",
                    "location": "",
                    "start_date": "2022",
                    "end_date": "",
                    "current": True,
                    "summary": "",
                    "highlights": ["A" * 240],
                    "technologies": [],
                    "order": 1,
                }
            ],
            "links": [{"label": "GitHub", "url": "https://git.example.com/" + "r" * 276, "order": 1}],
        }
        cv = CV(
            id=42,
            title="CV Estructurado Largo",
            full_name="SNAPSHOT-OBSOLETO",
            email="stale@example.com",
            phone="",
            professional_summary="",
            experience_summary="",
            education_summary="",
            skills="",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
            structured_schema_version=2,
            structured_payload=serialize_structured_payload(payload),
            structured_payload_status="valid",
        )

        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                with patch("app.services.pdf_service.subprocess.run", side_effect=_successful_pdflatex):
                    result = generate_cv_pdf_export(cv, "modern")

                exported_tex_content = result.exported_tex.path.read_text(encoding="utf-8")

        self.assertIn(r"\allowbreak \hspace{0pt plus 0.06em}", exported_tex_content)
        self.assertIn("A" * 240, exported_tex_content.replace(r"\allowbreak \hspace{0pt plus 0.06em}", ""))
        self.assertNotIn("A" * 240, exported_tex_content)
        self.assertNotIn("SNAPSHOT-OBSOLETO", exported_tex_content)

    def test_generates_cover_letter_pdf_export(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                with patch("app.services.pdf_service.subprocess.run", side_effect=_successful_pdflatex):
                    result = generate_cover_letter_pdf_export(_build_cover_letter(), "classic_letter")

                self.assertTrue(result.exported_pdf.path.exists())
                self.assertEqual(result.exported_pdf.path.parent, Path(data_directory) / "exports")
                self.assertTrue(result.exported_pdf.filename.startswith("cover-letter-"))
                self.assertTrue(result.exported_tex.path.exists())

    def test_generates_cover_letter_pdf_export_with_long_company_and_position(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                with patch("app.services.pdf_service.subprocess.run", side_effect=_successful_pdflatex):
                    result = generate_cover_letter_pdf_export(_build_long_cover_letter(), "classic_letter")

                self.assertTrue(result.exported_pdf.path.exists())
                self.assertTrue(result.exported_tex.path.exists())
                self.assertLessEqual(len(result.exported_pdf.filename), SAFE_EXPORT_FILENAME_MAX_LENGTH)
                self.assertLessEqual(len(result.exported_tex.filename), SAFE_EXPORT_FILENAME_MAX_LENGTH)
                self.assertTrue(result.exported_pdf.filename.startswith("cover-letter-32-"))


def _build_structured_cv():
    from app.services.structured_cv_service import serialize_structured_payload

    payload = {
        "schema_version": 2,
        "personal": {"full_name": "Ana Perez", "headline": "Tech Lead de Plataformas", "location": ""},
        "contact": {"email": "ana@example.com", "phone": "+54 11 1234 5678", "links": []},
        "summary": "Perfil estructurado con foco en plataformas y calidad.",
        "skills": [{"label": "Python", "category": "Backend", "level": "Avanzado", "order": 1}],
        "certifications": [
            {"name": "Certificacion AWS Solutions Architect", "issuer": "Amazon Web Services", "date": "2024", "order": 1},
        ],
        "projects": [
            {"name": "Observabilidad Abierta", "summary": "Paneles listos para produccion.", "link": "", "technologies": [], "order": 1},
        ],
    }
    return CV(
        id=41,
        title="CV Estructurado",
        full_name="SNAPSHOT-OBSOLETO",
        email="stale@example.com",
        phone="",
        professional_summary="SNAPSHOT-OBSOLETO",
        experience_summary="",
        education_summary="",
        skills="",
        created_at="2026-06-04 00:00:00",
        updated_at="2026-06-04 00:00:00",
        deleted_at=None,
        structured_schema_version=2,
        structured_payload=serialize_structured_payload(payload),
        structured_payload_status="valid",
    )


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


def _build_cover_letter() -> CoverLetter:
    return CoverLetter(
        id=22,
        company="ACME Corp",
        position="Backend Engineer",
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


def _build_long_cover_letter() -> CoverLetter:
    return CoverLetter(
        id=32,
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
