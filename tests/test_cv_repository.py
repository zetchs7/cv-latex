import os
import tempfile
import unittest
from unittest.mock import patch

from app.database import get_connection, initialize_database
from app.repositories.cv_repository import create_cv, duplicate_cv, get_cv, update_cv
from app.schemas import CVFormData
from app.services.structured_cv_service import build_valid_structured_columns_from_legacy, deserialize_structured_payload
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

    def test_update_legacy_cv_keeps_legacy_structured_state(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(_build_form_data(title="CV Legacy"))

                updated = update_cv(cv_id, _build_form_data(title="CV Updated"))

                self.assertTrue(updated)
                cv = get_cv(cv_id)
                self.assertIsNotNone(cv)
                self.assertEqual(cv.title, "CV Updated")
                self.assertIsNone(cv.structured_schema_version)
                self.assertIsNone(cv.structured_payload)
                self.assertEqual(cv.structured_payload_status, "legacy")

    def test_update_structured_cv_regenerates_payload_from_legacy_fields(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(_build_form_data(title="CV Structured"))
                old_payload = _mark_cv_as_structured(cv_id)

                updated = update_cv(cv_id, _build_form_data(title="CV Updated", skills="Python, FastAPI"))

                self.assertTrue(updated)
                cv = get_cv(cv_id)
                self.assertIsNotNone(cv)
                self.assertEqual(cv.title, "CV Updated")
                self.assertEqual(cv.structured_schema_version, 2)
                self.assertIsNotNone(cv.structured_payload)
                self.assertNotEqual(cv.structured_payload, old_payload)
                self.assertEqual(cv.structured_payload_status, "valid")
                payload = deserialize_structured_payload(cv.structured_payload)
                self.assertIsNotNone(payload)
                self.assertEqual(payload["metadata"]["source"], "legacy_edit")
                self.assertEqual(payload["skills"][1]["label"], "FastAPI")

    def test_duplicate_preserves_valid_structured_payload_when_content_is_copied(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                source_id = create_cv(_build_form_data(title="CV Structured"))
                payload = _mark_cv_as_structured(source_id)

                duplicate_id = duplicate_cv(source_id)

                self.assertIsNotNone(duplicate_id)
                duplicated_cv = get_cv(duplicate_id)
                self.assertIsNotNone(duplicated_cv)
                self.assertEqual(duplicated_cv.structured_schema_version, 2)
                self.assertEqual(duplicated_cv.structured_payload, payload)
                self.assertEqual(duplicated_cv.structured_payload_status, "valid")

def _build_form_data(*, title: str, skills: str = "Python") -> CVFormData:
    return CVFormData(
        title=title,
        full_name="Nombre Valido",
        email="cv@example.com",
        phone="",
        professional_summary="Perfil",
        experience_summary="Experiencia",
        education_summary="Educacion",
        skills=skills,
    )


def _mark_cv_as_structured(cv_id: int) -> str:
    structured_columns = build_valid_structured_columns_from_legacy(
        _build_form_data(title="CV Structured"),
        metadata_source="test",
    )
    payload = str(structured_columns["structured_payload"])
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cvs
            SET structured_schema_version = 2,
                structured_payload = ?,
                structured_payload_status = 'valid'
            WHERE id = ?
            """,
            (payload, cv_id),
        )
        connection.commit()

    return payload


if __name__ == "__main__":
    unittest.main()
