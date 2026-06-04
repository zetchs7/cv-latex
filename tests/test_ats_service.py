import unittest

from app.models import CV
from app.services.ats_service import MAX_ATS_SCORE, analyze_cv_ats


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


if __name__ == "__main__":
    unittest.main()
