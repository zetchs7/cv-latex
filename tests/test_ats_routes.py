import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import initialize_database
from app.main import app
from app.repositories.cv_repository import create_cv
from app.schemas import CVFormData


class AtsRoutesTest(unittest.TestCase):
    def test_renders_analysis_page_for_existing_cv(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(
                    CVFormData(
                        title="CV ATS",
                        full_name="Persona ATS",
                        email="persona@example.com",
                        phone="+54 11 4000 0000",
                        professional_summary="Perfil profesional orientado a backend y APIs.",
                        experience_summary="Experiencia en FastAPI, SQL y despliegues.",
                        education_summary="Analista de sistemas.",
                        skills="Python, FastAPI, Docker",
                    )
                )

                with TestClient(app) as client:
                    response = client.get(f"/ats/cvs/{cv_id}")

                self.assertEqual(response.status_code, 200)
                self.assertIn("ATS Basic Check", response.text)
                self.assertIn("Checklist", response.text)
                self.assertIn("CV ATS", response.text)


if __name__ == "__main__":
    unittest.main()
