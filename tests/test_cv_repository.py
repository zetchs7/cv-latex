import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.database import get_connection, initialize_database
from app.repositories.cv_repository import (
    StructuredCVLegacyUpdateError,
    create_cv,
    create_structured_cv,
    duplicate_cv,
    get_cv,
    update_cv,
    update_structured_cv,
)
from app.schemas import CVFormData
from app.services.structured_cv_service import (
    StructuredCVWriteError,
    build_valid_structured_columns_from_legacy,
    resolve_normalized_cv,
)
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

    def test_update_structured_cv_raises_domain_error_and_preserves_schema2_only_data(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_schema2_only_payload(),
                    metadata_source="structured_test",
                )
                stored_before = get_cv(cv_id)
                sections_before = resolve_normalized_cv(stored_before).sections

                with self.assertRaises(StructuredCVLegacyUpdateError):
                    update_cv(cv_id, _build_form_data(title="CV Actualizado", skills="Rust"))

                stored_after = get_cv(cv_id)
                self.assertEqual(stored_after.title, "CV Estructurado")
                self.assertEqual(stored_after.structured_schema_version, 2)
                self.assertEqual(stored_after.structured_payload_status, "valid")
                self.assertEqual(stored_after.structured_payload, stored_before.structured_payload)
                sections_after = resolve_normalized_cv(stored_after).sections
                self.assertEqual(sections_after, sections_before)
                self.assertEqual(sections_after["personal"]["headline"], "Arquitecto de Software")
                self.assertEqual(sections_after["personal"]["location"], "Cordoba")
                self.assertEqual(sections_after["certifications"][0]["name"], "AWS Solutions Architect")
                self.assertEqual(sections_after["projects"][0]["name"], "Motor de reportes")
                self.assertEqual(sections_after["languages"][0]["name"], "Espanol")
                self.assertEqual(sections_after["links"][0]["url"], "https://cv.example.com")
                self.assertEqual(sections_after["additional_info"][0]["title"], "Disponibilidad")
                self.assertEqual(sections_after["contact"]["links"], ["https://cv.example.com"])
                self.assertEqual(sections_after["metadata"]["source"], "structured_test")

    def test_update_structured_cv_with_partial_v2_payload_raises_without_clearing_to_legacy(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(_build_form_data(title="CV Structured"))
                partial_payload = _mark_cv_as_partial_structured(cv_id)

                with self.assertRaises(StructuredCVLegacyUpdateError):
                    update_cv(cv_id, _build_form_data(title="CV Updated", skills="Python, SQL"))

                cv = get_cv(cv_id)
                self.assertEqual(cv.title, "CV Structured")
                self.assertEqual(cv.structured_schema_version, 2)
                self.assertEqual(cv.structured_payload_status, "valid")
                self.assertEqual(cv.structured_payload, partial_payload)

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

    def test_create_structured_cv_persists_payload_and_derived_snapshot_atomically(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                cv_id = create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_structured_payload(),
                    metadata_source="structured_editor",
                )

                cv = get_cv(cv_id)
                self.assertIsNotNone(cv)
                self.assertEqual(cv.title, "CV Estructurado")
                self.assertEqual(cv.full_name, "Nombre Estructurado")
                self.assertEqual(cv.email, "struct@example.com")
                self.assertEqual(cv.skills, "Python, Docker")
                self.assertEqual(cv.structured_schema_version, 2)
                self.assertEqual(cv.structured_payload_status, "valid")
                stored_payload = json.loads(cv.structured_payload)
                self.assertEqual(stored_payload["personal"]["full_name"], "Nombre Estructurado")
                self.assertEqual(stored_payload["personal"]["headline"], "Tech Lead")
                self.assertEqual(stored_payload["additional_info"][0]["title"], "Disponibilidad")
                self.assertEqual(stored_payload["metadata"]["source"], "structured_editor")
                self.assertTrue(resolve_normalized_cv(cv).is_structured)

    def test_create_structured_cv_rejects_invalid_payload_without_persisting(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with self.assertRaises(StructuredCVWriteError):
                    create_structured_cv(title="CV Roto", payload={"skills": ["broken"]}, metadata_source="x")

                with get_connection() as connection:
                    row_count = connection.execute("SELECT COUNT(*) FROM cvs").fetchone()[0]
                self.assertEqual(row_count, 0)

    def test_create_structured_cv_rejects_invalid_snapshot_without_persisting(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = {
                    "schema_version": 2,
                    "personal": {"full_name": "Nombre Estructurado"},
                    "contact": {"email": "no-es-mail"},
                }

                with self.assertRaises(StructuredCVWriteError) as context:
                    create_structured_cv(title="CV Roto", payload=payload, metadata_source="x")

                self.assertIn("email", " ".join(context.exception.errors))
                with get_connection() as connection:
                    row_count = connection.execute("SELECT COUNT(*) FROM cvs").fetchone()[0]
                self.assertEqual(row_count, 0)

    def test_update_structured_cv_switches_legacy_cv_to_structured_atomically(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(_build_form_data(title="CV Legacy"))

                updated = update_structured_cv(
                    cv_id,
                    title="CV Ahora Estructurado",
                    payload=_build_structured_payload(),
                    metadata_source="structured_editor",
                )

                self.assertTrue(updated)
                cv = get_cv(cv_id)
                self.assertIsNotNone(cv)
                self.assertEqual(cv.title, "CV Ahora Estructurado")
                self.assertEqual(cv.full_name, "Nombre Estructurado")
                self.assertEqual(cv.email, "struct@example.com")
                self.assertEqual(cv.structured_schema_version, 2)
                self.assertEqual(cv.structured_payload_status, "valid")
                stored_payload = json.loads(cv.structured_payload)
                self.assertEqual(stored_payload["metadata"]["source"], "structured_editor")
                self.assertTrue(resolve_normalized_cv(cv).is_structured)

    def test_update_structured_cv_rejects_invalid_payload_leaving_row_untouched(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = create_cv(_build_form_data(title="CV Legacy"))
                update_structured_cv(
                    cv_id,
                    title="CV Estructurado",
                    payload=_build_structured_payload(),
                    metadata_source="structured_editor",
                )
                cv_before = get_cv(cv_id)

                with self.assertRaises(StructuredCVWriteError):
                    update_structured_cv(cv_id, title="CV Roto", payload={"skills": ["broken"]}, metadata_source="x")

                cv_after = get_cv(cv_id)
                self.assertEqual(cv_after.title, cv_before.title)
                self.assertEqual(cv_after.structured_payload, cv_before.structured_payload)
                self.assertEqual(cv_after.structured_payload_status, cv_before.structured_payload_status)

    def test_update_structured_cv_returns_false_for_missing_cv(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                updated = update_structured_cv(
                    999999,
                    title="CV Inexistente",
                    payload={"schema_version": 2},
                    metadata_source="structured_editor",
                )

                self.assertFalse(updated)

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


def _build_structured_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "personal": {"full_name": "Nombre Estructurado", "headline": "Tech Lead", "location": ""},
        "contact": {"email": "struct@example.com", "phone": "", "links": []},
        "summary": "Perfil estructurado",
        "skills": [
            {"label": "Python", "category": "", "level": "", "order": 1},
            {"label": "Docker", "category": "", "level": "", "order": 2},
        ],
        "experience": [
            {
                "company": "Acme",
                "role": "Desarrollador",
                "location": "",
                "start_date": "2020",
                "end_date": "2021",
                "current": False,
                "summary": "Desarrollo backend",
                "highlights": [],
                "technologies": [],
                "order": 1,
            }
        ],
        "education": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "links": [],
        "additional_info": [{"title": "Disponibilidad", "content": "Remoto", "order": 1}],
        "metadata": {"source": "editor", "synced_from_legacy_at": ""},
    }


def _build_schema2_only_payload() -> dict[str, object]:
    """Payload v2 con contenido que solo existe en columnas estructuradas."""
    return {
        "schema_version": 2,
        "personal": {
            "full_name": "Nombre Estructurado",
            "headline": "Arquitecto de Software",
            "location": "Cordoba",
        },
        "contact": {"email": "struct@example.com", "phone": "", "links": ["https://cv.example.com"]},
        "summary": "Perfil estructurado",
        "skills": [
            {"label": "Python", "category": "", "level": "", "order": 1},
        ],
        "experience": [],
        "education": [],
        "certifications": [
            {"name": "AWS Solutions Architect", "issuer": "Amazon", "date": "2023", "order": 1}
        ],
        "languages": [{"name": "Espanol", "level": "Nativo", "order": 1}],
        "projects": [
            {
                "name": "Motor de reportes",
                "summary": "Automatizacion de reportes",
                "link": "https://git.example.com/repo",
                "technologies": ["Python"],
                "order": 1,
            }
        ],
        "links": [{"label": "Web", "url": "https://cv.example.com", "order": 1}],
        "additional_info": [{"title": "Disponibilidad", "content": "Remoto", "order": 1}],
        "metadata": {"source": "structured_test", "synced_from_legacy_at": ""},
    }


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


def _mark_cv_as_partial_structured(cv_id: int) -> str:
    payload = '{"personal":{"full_name":"Nombre Valido"}}'
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
