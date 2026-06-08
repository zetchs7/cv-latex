from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import initialize_database
from app.main import app
from app.repositories.cv_repository import create_cv
from app.schemas import CVFormData


class ConfirmationModalSecurityTest(unittest.TestCase):
    def test_confirm_modal_uses_text_content_for_dynamic_values(self):
        script = Path("app/static/js/app.js").read_text(encoding="utf-8")
        confirm_modal_block = script.split("function openConfirmModal", 1)[1].split("async function openAtsModal", 1)[0]

        self.assertNotIn("innerHTML", confirm_modal_block)
        self.assertNotIn("insertAdjacentHTML", confirm_modal_block)
        self.assertNotIn("outerHTML", confirm_modal_block)
        self.assertIn("titleElement.textContent = title", confirm_modal_block)
        self.assertIn("messageElement.textContent = message", confirm_modal_block)
        self.assertIn("acceptButton.textContent = confirmLabel", confirm_modal_block)

    def test_malicious_cv_title_is_escaped_in_confirm_attributes(self):
        malicious_title = '\"><img src=x onerror=alert(1)> <script>alert(1)</script>'

        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(
                    CVFormData(
                        title=malicious_title,
                        full_name="Persona Seguridad",
                        email="security@example.com",
                        phone="+54 11 4000 9999",
                        professional_summary="Perfil profesional de seguridad.",
                        experience_summary="Experiencia en validaciones y pruebas.",
                        education_summary="Formacion tecnica.",
                        skills="Python, testing, seguridad",
                    )
                )

                with TestClient(app) as client:
                    list_response = client.get("/cvs/")
                    detail_response = client.get(f"/cvs/{cv_id}")

                self.assertEqual(list_response.status_code, 200)
                self.assertEqual(detail_response.status_code, 200)

                for response in (list_response, detail_response):
                    self.assertIn("data-confirm-message", response.text)
                    self.assertNotIn('data-confirm-message="Se va a crear una copia de "><img', response.text)
                    self.assertNotIn('data-confirm-message="Se va a crear una copia de <script>', response.text)
                    self.assertIn("&lt;img src=x onerror=alert(1)&gt;", response.text)
                    self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", response.text)


if __name__ == "__main__":
    unittest.main()
