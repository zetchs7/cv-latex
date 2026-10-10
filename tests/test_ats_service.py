import unittest

from app.models import CV
from app.services.ats_service import MAX_ATS_SCORE, analyze_cv_ats
from app.services.structured_cv_service import (
    build_structured_cv_write_bundle,
    build_structured_payload_from_legacy,
    serialize_structured_payload,
)


class AtsServiceTest(unittest.TestCase):
    def test_returns_strong_result_for_complete_cv(self):
        cv = CV(
            id=1,
            title="CV Completo",
            full_name="Persona Completa",
            email="persona@example.com",
            phone="+54 11 4444 4444",
            professional_summary="Backend engineer con experiencia en APIs, datos, producto y trabajo con equipos cross-functional.",
            experience_summary="Desarrolle servicios con FastAPI, integraciones internas y mejoras de observabilidad para producto SaaS.",
            education_summary="Ingenieria en Sistemas y cursos de arquitectura de software.",
            skills="Python, FastAPI, SQL, Docker, Testing, Observabilidad",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        result = analyze_cv_ats(cv)

        self.assertEqual(result.status, "Bueno")
        self.assertEqual(result.score, MAX_ATS_SCORE)
        self.assertEqual(result.empty_sections, [])
        self.assertEqual(len(result.recommendations), 1)
        self.assertIn("cubre los puntos basicos", result.recommendations[0])

    def test_penalizes_missing_education_even_with_experience(self):
        cv = CV(
            id=2,
            title="CV Sin Educacion",
            full_name="Persona Sin Educacion",
            email="persona@example.com",
            phone="+54 11 4444 4444",
            professional_summary="Backend engineer con experiencia concreta en producto y APIs.",
            experience_summary="Experiencia sostenida en desarrollo backend, mantenimiento y observabilidad.",
            education_summary="",
            skills="Python, FastAPI, SQL, Docker",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        result = analyze_cv_ats(cv)

        self.assertEqual(result.status, "Mejorable")
        self.assertEqual(result.score, 71)
        self.assertLess(result.score, MAX_ATS_SCORE)
        self.assertIn("Educacion", result.empty_sections)
        self.assertTrue(any("Agregar educacion" in item for item in result.recommendations))

    def test_penalizes_missing_experience_even_with_education(self):
        cv = CV(
            id=3,
            title="CV Sin Experiencia",
            full_name="Persona Sin Experiencia",
            email="persona@example.com",
            phone="+54 11 4444 4444",
            professional_summary="Perfil tecnico con base academica y foco en backend.",
            experience_summary="",
            education_summary="Ingenieria en Sistemas, cursos de APIs y bases de datos.",
            skills="Python, FastAPI, SQL, Docker",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        result = analyze_cv_ats(cv)

        self.assertEqual(result.status, "Mejorable")
        self.assertEqual(result.score, 71)
        self.assertLess(result.score, MAX_ATS_SCORE)
        self.assertIn("Experiencia", result.empty_sections)
        self.assertTrue(any("Agregar experiencia laboral" in item for item in result.recommendations))

    def test_penalizes_missing_experience_and_education_strongly(self):
        cv = CV(
            id=4,
            title="CV Largo Sin Core",
            full_name="Persona Sin Core",
            email="persona@example.com",
            phone="+54 11 4444 4444",
            professional_summary="Perfil backend amplio con foco en APIs, calidad, producto, mantenimiento y colaboracion tecnica sostenida.",
            experience_summary="",
            education_summary="",
            skills="Python, FastAPI, SQL, Docker, Testing, Observabilidad",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        result = analyze_cv_ats(cv)

        self.assertEqual(result.status, "Insuficiente")
        self.assertLess(result.score, 60)
        self.assertLessEqual(result.score, 59)
        self.assertLess(result.score, 60)
        self.assertIn("Experiencia", result.empty_sections)
        self.assertIn("Educacion", result.empty_sections)
        self.assertTrue(any("Cargar experiencia, educacion o ambas" in item for item in result.recommendations))

    def test_keeps_existing_incomplete_cv_as_insufficient(self):
        cv = CV(
            id=5,
            title="CV Incompleto",
            full_name="Persona Incompleta",
            email="",
            phone="",
            professional_summary="",
            experience_summary="",
            education_summary="",
            skills="",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        result = analyze_cv_ats(cv)

        self.assertEqual(result.status, "Insuficiente")
        self.assertEqual(result.score, 0)
        self.assertLess(result.score, 50)
        self.assertIn("Email", result.empty_sections)
        self.assertIn("Experiencia", result.empty_sections)
        self.assertIn("Educacion", result.empty_sections)
        self.assertIn("Resumen profesional", result.empty_sections)
        self.assertTrue(any("Agregar un email" in item for item in result.recommendations))
        self.assertTrue(any("Cargar experiencia, educacion o ambas" in item for item in result.recommendations))
        self.assertTrue(any("Seccion vacia detectada: Skills." == item for item in result.warnings))

    def test_structured_cv_scores_from_canonical_payload_not_stale_flat_columns(self):
        payload = {
            "schema_version": 2,
            "personal": {"full_name": "Ana Perez", "headline": "", "location": ""},
            "contact": {"email": "ana@example.com", "phone": "+54 11 1234 5678", "links": []},
            "summary": "Perfil estructurado con foco en plataformas, datos, calidad de servicio y equipos distribuidos.",
            "skills": [
                {"label": "Python", "category": "", "level": "", "order": 1},
                {"label": "SQL", "category": "", "level": "", "order": 2},
            ],
            "experience": [
                {
                    "company": "Globex",
                    "role": "Lider Tecnico",
                    "location": "",
                    "start_date": "2022",
                    "end_date": "",
                    "current": True,
                    "summary": "Liderazgo tecnico de la plataforma interna con foco en confiabilidad.",
                    "highlights": ["Diseno de plataforma", "Reduccion de incidentes recurrentes"],
                    "technologies": ["Python", "FastAPI"],
                    "order": 1,
                }
            ],
            "education": [
                {
                    "institution": "UBA",
                    "degree": "Ingenieria en Sistemas",
                    "field": "",
                    "start_date": "2013",
                    "end_date": "2019",
                    "summary": "Promedio destacado y becas academicas.",
                    "order": 1,
                }
            ],
            "certifications": [
                {"name": "Certificacion AWS Solutions Architect", "issuer": "Amazon Web Services", "date": "2024", "order": 1},
            ],
            "languages": [
                {"name": "Ingles", "level": "Avanzado", "order": 1},
            ],
            "additional_info": [
                {"title": "Disponibilidad", "content": "Full-time remoto.", "order": 1},
            ],
        }
        cv = CV(
            id=6,
            title="CV Estructurado",
            full_name="SNAPSHOT-LEGACY-OBSOLETO",
            email="stale@example.com",
            phone="",
            professional_summary="SNAPSHOT-LEGACY-OBSOLETO",
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

        result = analyze_cv_ats(cv)

        self.assertEqual(result.status, "Bueno")
        self.assertEqual(result.score, MAX_ATS_SCORE)
        self.assertEqual(result.empty_sections, [])
        phone_check = next(item for item in result.checklist if item.key == "phone")
        self.assertTrue(phone_check.passed)
        experience_check = next(item for item in result.checklist if item.key == "experience_summary")
        self.assertTrue(experience_check.passed)

    def test_structured_cv_equivalent_to_legacy_projection(self):
        legacy_cv = CV(
            id=7,
            title="CV Equivalente",
            full_name="Persona Completa",
            email="persona@example.com",
            phone="+54 11 4444 4444",
            professional_summary="Backend engineer con experiencia en APIs, datos y trabajo con equipos.",
            experience_summary="Desarrolle servicios con FastAPI e integraciones internas.",
            education_summary="Ingenieria en Sistemas y cursos de arquitectura.",
            skills="Python, FastAPI, SQL, Docker",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        payload = build_structured_payload_from_legacy(legacy_cv, metadata_source="conversion_test")
        bundle = build_structured_cv_write_bundle(
            title=legacy_cv.title,
            payload=payload,
            metadata_source="conversion_test",
        )
        structured_cv = _structured_cv_from_bundle(legacy_cv, bundle)

        self.assertEqual(analyze_cv_ats(structured_cv), analyze_cv_ats(legacy_cv))

    def test_empty_structured_conversion_keeps_insufficient_result(self):
        legacy_cv = CV(
            id=8,
            title="CV Vacio",
            full_name="Persona Vacia",
            email="",
            phone="",
            professional_summary="",
            experience_summary="",
            education_summary="",
            skills="",
            created_at="2026-06-04 00:00:00",
            updated_at="2026-06-04 00:00:00",
            deleted_at=None,
        )

        payload = build_structured_payload_from_legacy(legacy_cv, metadata_source="conversion_test")
        bundle = build_structured_cv_write_bundle(
            title=legacy_cv.title,
            payload=payload,
            metadata_source="conversion_test",
        )
        structured_cv = _structured_cv_from_bundle(legacy_cv, bundle)

        legacy_result = analyze_cv_ats(legacy_cv)
        structured_result = analyze_cv_ats(structured_cv)

        self.assertEqual(structured_result, legacy_result)
        self.assertEqual(structured_result.score, 0)
        self.assertEqual(structured_result.status, "Insuficiente")


def _structured_cv_from_bundle(legacy_cv, bundle):
    columns = bundle.structured_columns
    form_data = bundle.form_data
    return CV(
        id=legacy_cv.id,
        title=legacy_cv.title,
        full_name=form_data.full_name,
        email=form_data.email,
        phone=form_data.phone,
        professional_summary=form_data.professional_summary,
        experience_summary=form_data.experience_summary,
        education_summary=form_data.education_summary,
        skills=form_data.skills,
        created_at=legacy_cv.created_at,
        updated_at=legacy_cv.updated_at,
        deleted_at=None,
        structured_schema_version=columns["structured_schema_version"],
        structured_payload=columns["structured_payload"],
        structured_payload_status=columns["structured_payload_status"],
    )


if __name__ == "__main__":
    unittest.main()
