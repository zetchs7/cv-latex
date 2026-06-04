import os
import tempfile
import unittest
from unittest.mock import patch

from app.database import initialize_database
from app.repositories.cover_letter_repository import create_cover_letter, get_cover_letter, list_cover_letters, update_cover_letter
from app.repositories.cv_repository import create_cv
from app.schemas import CVFormData, CoverLetterFormData


class CoverLetterRepositoryTest(unittest.TestCase):
    def test_creates_and_reads_cover_letter_with_associated_cv(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(
                    CVFormData(
                        title="CV Base",
                        full_name="Nombre Valido",
                        email="cv@example.com",
                        phone="",
                        professional_summary="Perfil",
                        experience_summary="Experiencia",
                        education_summary="Educacion",
                        skills="Python",
                    )
                )

                cover_letter_id = create_cover_letter(
                    CoverLetterFormData(
                        company="ACME Corp",
                        position="Backend Engineer",
                        contact="Hiring Team",
                        greeting="Hola,",
                        introduction="Intro",
                        body="Cuerpo",
                        closing="Cierre",
                        signature="Firma",
                        associated_cv_id=cv_id,
                    )
                )

                cover_letter = get_cover_letter(cover_letter_id)

                self.assertIsNotNone(cover_letter)
                self.assertEqual(cover_letter.associated_cv_id, cv_id)
                self.assertEqual(cover_letter.associated_cv_title, "CV Base")

    def test_updates_cover_letter_and_lists_active_records(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cover_letter_id = create_cover_letter(
                    CoverLetterFormData(
                        company="ACME Corp",
                        position="Backend Engineer",
                        contact="Hiring Team",
                        greeting="Hola,",
                        introduction="Intro",
                        body="Cuerpo",
                        closing="Cierre",
                        signature="Firma",
                        associated_cv_id=None,
                    )
                )

                updated = update_cover_letter(
                    cover_letter_id,
                    CoverLetterFormData(
                        company="Globex",
                        position="Platform Engineer",
                        contact="People Team",
                        greeting="Estimados,",
                        introduction="Nueva intro",
                        body="Nuevo cuerpo",
                        closing="Nuevo cierre",
                        signature="Nueva firma",
                        associated_cv_id=None,
                    ),
                )

                self.assertTrue(updated)
                cover_letters = list_cover_letters()
                self.assertEqual(len(cover_letters), 1)
                self.assertEqual(cover_letters[0].company, "Globex")
                self.assertEqual(cover_letters[0].position, "Platform Engineer")


if __name__ == "__main__":
    unittest.main()
