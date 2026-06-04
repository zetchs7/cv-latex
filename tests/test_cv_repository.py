import os
import tempfile
import unittest
from unittest.mock import patch

from app.database import initialize_database
from app.repositories.cv_repository import create_cv, duplicate_cv, get_cv
from app.schemas import CVFormData
from app.validations.cv_validations import FIELD_LIMITS


class CVRepositoryTest(unittest.TestCase):
    def test_duplicate_truncates_title_safely_when_original_is_at_limit(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                source_id = create_cv(
                    CVFormData(
                        title="A" * FIELD_LIMITS["title"],
                        full_name="Nombre Valido",
                        email="cv@example.com",
                        phone="",
                        professional_summary="Perfil",
                        experience_summary="Experiencia",
                        education_summary="Educacion",
                        skills="Python",
                    )
                )

                duplicate_id = duplicate_cv(source_id)

                self.assertIsNotNone(duplicate_id)
                duplicated_cv = get_cv(duplicate_id)
                self.assertIsNotNone(duplicated_cv)
                self.assertEqual(len(duplicated_cv.title), FIELD_LIMITS["title"])
                self.assertTrue(duplicated_cv.title.endswith("(copia)"))


if __name__ == "__main__":
    unittest.main()
