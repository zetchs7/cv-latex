import unittest

from app.models import CV, CoverLetter


try:
    from app.services.latex_service import generate_cover_letter_tex_document, generate_cv_tex_document

    JINJA2_AVAILABLE = True
except ModuleNotFoundError as error:
    if error.name != "jinja2":
        raise
    JINJA2_AVAILABLE = False


@unittest.skipUnless(JINJA2_AVAILABLE, "jinja2 is required for latex service rendering")
class LatexServiceTest(unittest.TestCase):
    def test_generates_tex_from_cv_with_empty_sections(self):
        cv = CV(
            id=10,
            title="CV Desarrollador",
            full_name="María Muñoz",
            email="maria@example.com",
            phone="",
            professional_summary="Construye APIs seguras & mantenibles.",
            experience_summary="",
            education_summary="",
            skills="Python, FastAPI",
            created_at="2026-06-02 00:00:00",
            updated_at="2026-06-02 00:00:00",
            deleted_at=None,
        )

        generated_document = generate_cv_tex_document(cv, "classic")

        self.assertEqual(generated_document.filename, "cv-desarrollador-classic.tex")
        self.assertIn(r"María Muñoz", generated_document.content)
        self.assertIn(r"Construye APIs seguras \& mantenibles.", generated_document.content)
        self.assertIn(r"\item Python", generated_document.content)
        self.assertIn(r"\item FastAPI", generated_document.content)
        self.assertNotIn("[[", generated_document.content)
        self.assertNotIn("Experiencia laboral", generated_document.content)

    def test_generates_all_supported_templates(self):
        cv = CV(
            id=11,
            title="CV QA",
            full_name="Juan Perez",
            email="juan@example.com",
            phone="+54 11 1234 5678",
            professional_summary="Perfil",
            experience_summary="Experiencia",
            education_summary="Educacion",
            skills="Testing",
            created_at="2026-06-02 00:00:00",
            updated_at="2026-06-02 00:00:00",
            deleted_at=None,
        )

        for template_key in ["classic", "modern", "compact", "tech"]:
            with self.subTest(template_key=template_key):
                generated_document = generate_cv_tex_document(cv, template_key)
                self.assertIn(r"\documentclass", generated_document.content)
                self.assertIn("Juan Perez", generated_document.content)

    def test_legacy_cv_tex_never_contains_break_macros(self):
        cv = CV(
            id=15,
            title="CV Legacy Largo",
            full_name="Juan Perez",
            email="juan@example.com",
            phone="+54 11 1234 5678",
            professional_summary="Perfil con un token larguisimo " + "A" * 240,
            experience_summary="Experiencia",
            education_summary="Educacion",
            skills="Python",
            created_at="2026-06-03 00:00:00",
            updated_at="2026-06-03 00:00:00",
            deleted_at=None,
        )

        for template_key in ["classic", "modern", "compact", "tech"]:
            with self.subTest(template_key=template_key):
                generated_document = generate_cv_tex_document(cv, template_key)

                self.assertIn("A" * 240, generated_document.content)
                self.assertNotIn(r"\allowbreak", generated_document.content)

    def test_templates_include_pdf_text_extraction_mapping(self):
        cv = CV(
            id=12,
            title="CV ATS",
            full_name="Ana Alvarez",
            email="ana@example.com",
            phone="",
            professional_summary="Perfil tecnico con analisis y educacion.",
            experience_summary="",
            education_summary="",
            skills="Comunicacion",
            created_at="2026-06-03 00:00:00",
            updated_at="2026-06-03 00:00:00",
            deleted_at=None,
        )

        for template_key in ["classic", "modern", "compact", "tech"]:
            with self.subTest(template_key=template_key):
                generated_document = generate_cv_tex_document(cv, template_key)
                self.assertIn(r"\input{glyphtounicode}", generated_document.content)
                self.assertIn(r"\pdfgentounicode=1", generated_document.content)
                self.assertIn(r"\usepackage{cmap}", generated_document.content)
                self.assertIn(r"\usepackage{lmodern}", generated_document.content)

    def test_generates_tex_from_structured_cv_canonical_sections(self):
        from app.services.structured_cv_service import serialize_structured_payload

        payload = {
            "schema_version": 2,
            "personal": {"full_name": "Ana Perez", "headline": "Tech Lead de Plataformas", "location": ""},
            "contact": {"email": "ana@example.com", "phone": "+54 11 1234 5678", "links": []},
            "summary": "Perfil estructurado.",
            "certifications": [
                {"name": "Certificacion AWS", "issuer": "Amazon Web Services", "date": "2024", "order": 1},
            ],
        }
        cv = CV(
            id=13,
            title="CV Estructurado",
            full_name="SNAPSHOT-LEGACY-OBSOLETO",
            email="stale@example.com",
            phone="",
            professional_summary="SNAPSHOT-LEGACY-OBSOLETO",
            experience_summary="",
            education_summary="",
            skills="",
            created_at="2026-06-03 00:00:00",
            updated_at="2026-06-03 00:00:00",
            deleted_at=None,
            structured_schema_version=2,
            structured_payload=serialize_structured_payload(payload),
            structured_payload_status="valid",
        )

        generated_document = generate_cv_tex_document(cv, "classic")

        self.assertIn("Ana Perez", generated_document.content)
        self.assertIn("Tech Lead de Plataformas", generated_document.content)
        self.assertIn("Certificacion AWS", generated_document.content)
        self.assertNotIn("SNAPSHOT-LEGACY-OBSOLETO", generated_document.content)
        self.assertNotIn("stale@example.com", generated_document.content)
        self.assertNotIn("[[", generated_document.content)
        self.assertNotIn("Experiencia laboral", generated_document.content)

    def test_generates_tex_from_structured_cv_with_empty_sections(self):
        from app.services.structured_cv_service import serialize_structured_payload

        payload = {
            "schema_version": 2,
            "personal": {"full_name": "Ana Perez", "headline": "", "location": ""},
            "contact": {"email": "", "phone": "", "links": []},
            "summary": "",
        }
        cv = CV(
            id=14,
            title="CV Vacio Estructurado",
            full_name="SNAPSHOT-LEGACY-OBSOLETO",
            email="",
            phone="",
            professional_summary="",
            experience_summary="",
            education_summary="",
            skills="",
            created_at="2026-06-03 00:00:00",
            updated_at="2026-06-03 00:00:00",
            deleted_at=None,
            structured_schema_version=2,
            structured_payload=serialize_structured_payload(payload),
            structured_payload_status="valid",
        )

        generated_document = generate_cv_tex_document(cv, "classic")

        self.assertIn("Ana Perez", generated_document.content)
        self.assertNotIn("Perfil profesional", generated_document.content)
        self.assertNotIn("Certificaciones", generated_document.content)
        self.assertNotIn("[[", generated_document.content)

    def test_generates_cover_letter_tex_document(self):
        cover_letter = CoverLetter(
            id=21,
            company="ACME Corp",
            position="Backend Engineer",
            contact="Hiring Team",
            greeting="Estimado equipo,",
            introduction="Presento mi candidatura para el puesto.",
            body="Tengo experiencia con Python y FastAPI.",
            closing="Quedo a disposicion para conversar.",
            signature="Juan Perez",
            associated_cv_id=7,
            associated_cv_title="CV Backend",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        generated_document = generate_cover_letter_tex_document(cover_letter, "classic_letter")

        self.assertEqual(generated_document.filename, "cover-letter-21-acme-corp-backend-engineer-classic_letter.tex")
        self.assertIn("ACME Corp", generated_document.content)
        self.assertIn("Backend Engineer", generated_document.content)
        self.assertIn(r"Python y FastAPI.", generated_document.content)
        self.assertIn(r"\usepackage{lmodern}", generated_document.content)
        self.assertNotIn("[[", generated_document.content)

    def test_caps_cover_letter_generated_filename_with_long_company_and_position(self):
        cover_letter = CoverLetter(
            id=31,
            company="A" * 160,
            position="B" * 160,
            contact="Hiring Team",
            greeting="Estimado equipo,",
            introduction="Presento mi candidatura para el puesto.",
            body="Tengo experiencia con Python y FastAPI.",
            closing="Quedo a disposicion para conversar.",
            signature="Juan Perez",
            associated_cv_id=7,
            associated_cv_title="CV Backend",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        generated_document = generate_cover_letter_tex_document(cover_letter, "classic_letter")

        self.assertLessEqual(len(generated_document.filename), 180)
        self.assertTrue(generated_document.filename.startswith("cover-letter-31-"))
        self.assertTrue(generated_document.filename.endswith(".tex"))


if __name__ == "__main__":
    unittest.main()
