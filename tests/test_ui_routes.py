import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import initialize_database
from app.main import app
from app.repositories.cover_letter_repository import create_cover_letter
from app.repositories.cv_repository import create_cv
from app.schemas import CVFormData, CoverLetterFormData


class UIRoutesTest(unittest.TestCase):
    def test_dashboard_renders_private_workspace_layout(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with TestClient(app) as client:
                    response = client.get("/")

                self.assertEqual(response.status_code, 200)
                self.assertIn("Panel de control", response.text)
                self.assertIn("Curriculum Vitae", response.text)
                self.assertIn("data-theme-toggle", response.text)

    def test_cv_delete_requires_exact_title_match(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(
                    CVFormData(
                        title="CV Privado",
                        full_name="Persona Test",
                        email="persona@example.com",
                        phone="",
                        professional_summary="Perfil",
                        experience_summary="Experiencia",
                        education_summary="Educacion",
                        skills="Python",
                    )
                )

                with TestClient(app) as client:
                    failed_response = client.post(
                        f"/cvs/{cv_id}/delete",
                        data={"confirmation_value": "Titulo incorrecto"},
                    )
                    success_response = client.post(
                        f"/cvs/{cv_id}/delete",
                        data={"confirmation_value": "CV Privado"},
                        follow_redirects=False,
                    )

                self.assertEqual(failed_response.status_code, 422)
                self.assertIn("no coincide exactamente", failed_response.text)
                self.assertEqual(success_response.status_code, 303)
                self.assertTrue(success_response.headers["location"].endswith("/cvs/?message=CV+eliminado+correctamente."))

    def test_cover_letter_delete_requires_exact_display_name_match(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cover_letter_id = create_cover_letter(
                    CoverLetterFormData(
                        company="Acme",
                        position="Backend Engineer",
                        contact="RRHH",
                        greeting="Hola",
                        introduction="Intro",
                        body="Body",
                        closing="Cierre",
                        signature="Firma",
                        associated_cv_id=None,
                    )
                )

                with TestClient(app) as client:
                    failed_response = client.post(
                        f"/cover-letters/{cover_letter_id}/delete",
                        data={"confirmation_value": "Acme"},
                    )
                    success_response = client.post(
                        f"/cover-letters/{cover_letter_id}/delete",
                        data={"confirmation_value": "Acme - Backend Engineer"},
                        follow_redirects=False,
                    )

                self.assertEqual(failed_response.status_code, 422)
                self.assertIn("no coincide exactamente", failed_response.text)
                self.assertEqual(success_response.status_code, 303)
                self.assertTrue(success_response.headers["location"].endswith("/cover-letters/?message=Carta+eliminada+correctamente."))


if __name__ == "__main__":
    unittest.main()
