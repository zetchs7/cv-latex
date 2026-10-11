import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import initialize_database
from app.main import app
from app.models import CV
from app.repositories import cv_repository
from app.schemas import CVFormData
from app.services.export_service import (
    ExportServiceError,
    JSON_IMPORT_ENVELOPE_HEADROOM_BYTES,
    MAX_JSON_IMPORT_BYTES,
    build_cv_json_import_result,
    build_cv_json_payload,
    export_cv_json,
)
from app.services.structured_cv_service import (
    MAX_STRUCTURED_PAYLOAD_BYTES,
    StructuredCVWriteError,
    resolve_normalized_cv,
    serialize_structured_payload,
)
from app.validations.cv_validations import FIELD_LIMITS


STRUCTURED_PAYLOAD_SECTIONS = (
    "schema_version",
    "personal",
    "contact",
    "summary",
    "skills",
    "experience",
    "education",
    "certifications",
    "languages",
    "projects",
    "links",
    "additional_info",
    "metadata",
)

_LIMIT_METADATA_SOURCE = "limit_test"
_LIMIT_METADATA_TIMESTAMP = "2020-01-01T00:00:00+00:00"


class Schema2ExportServiceTest(unittest.TestCase):
    def test_structured_cv_exports_lossless_schema2_envelope(self):
        payload = _build_full_payload()
        payload["experience"][0]["custom_note"] = "dato interno"
        payload["unknown_section"] = {"keep": True}
        cv = _build_structured_cv_row(payload)

        exported = build_cv_json_payload(cv)

        self.assertEqual(exported["schema_version"], 2)
        self.assertIn("exported_at", exported)
        self.assertEqual(exported["source_cv_id"], 7)
        cv_payload = exported["cv"]
        self.assertEqual(cv_payload["title"], "CV Estructurado")
        structured_payload = cv_payload["structured_payload"]
        self.assertEqual(structured_payload["schema_version"], 2)
        for section in STRUCTURED_PAYLOAD_SECTIONS:
            self.assertIn(section, structured_payload)
        self.assertEqual(structured_payload["personal"]["full_name"], "Ana Perez")
        self.assertEqual(structured_payload["personal"]["headline"], "Tech Lead")
        self.assertEqual(structured_payload["metadata"]["source"], "structured_test")
        self.assertEqual(structured_payload["experience"][0]["custom_note"], "dato interno")
        self.assertEqual(structured_payload["unknown_section"], {"keep": True})
        self.assertEqual(structured_payload["skills"][0]["order"], 1)
        self.assertEqual(
            [skill["label"] for skill in structured_payload["skills"]],
            ["Python", "SQL"],
        )

    def test_fallback_rows_export_schema1_without_mixed_source(self):
        legacy_cv = _build_cv_row(
            structured_schema_version=None,
            structured_payload=None,
            structured_payload_status="legacy",
        )
        stale_cv = _build_cv_row(
            structured_schema_version=2,
            structured_payload=serialize_structured_payload(_build_minimal_payload()),
            structured_payload_status="stale",
        )
        corrupt_cv = _build_cv_row(
            structured_schema_version=2,
            structured_payload="{invalid-json",
            structured_payload_status="valid",
        )
        future_cv = _build_cv_row(
            structured_schema_version=3,
            structured_payload='{"schema_version": 3, "personal": {"full_name": "Futuro"}}',
            structured_payload_status="valid",
        )

        for cv in (legacy_cv, stale_cv, corrupt_cv, future_cv):
            with self.subTest(cv=cv.title):
                exported = build_cv_json_payload(cv)

                self.assertEqual(exported["schema_version"], 1)
                self.assertNotIn("structured_payload", exported["cv"])
                self.assertEqual(exported["cv"]["title"], "CV Estructurado")
                self.assertEqual(exported["cv"]["full_name"], "Nombre Legacy")
                self.assertEqual(exported["cv"]["skills"], "Python, SQL")

    def test_structured_cv_explicit_schema1_export_uses_derived_snapshot(self):
        cv = _build_structured_cv_row(_build_full_payload())

        exported = build_cv_json_payload(cv, schema_version=1)

        self.assertEqual(exported["schema_version"], 1)
        self.assertNotIn("structured_payload", exported["cv"])
        self.assertEqual(exported["cv"]["full_name"], "Ana Perez")
        self.assertEqual(exported["cv"]["email"], "ana@example.com")
        self.assertEqual(exported["cv"]["skills"], "Python, SQL")
        self.assertIn("Lider Tecnico - Globex (2022 - Presente)", exported["cv"]["experience_summary"])

    def test_explicit_schema_export_requests_are_validated_strictly(self):
        legacy_cv = _build_cv_row(
            structured_schema_version=None,
            structured_payload=None,
            structured_payload_status="legacy",
        )
        structured_cv = _build_structured_cv_row(_build_full_payload())

        with self.assertRaises(ExportServiceError):
            build_cv_json_payload(legacy_cv, schema_version=2)
        with self.assertRaises(ExportServiceError):
            build_cv_json_payload(legacy_cv, schema_version=3)
        with self.assertRaises(ExportServiceError):
            build_cv_json_payload(structured_cv, schema_version=True)

    def test_export_cv_json_filename_marks_schema2_variant(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                structured_export = export_cv_json(_build_structured_cv_row(_build_full_payload()))
                legacy_export = export_cv_json(
                    _build_cv_row(
                        structured_schema_version=None,
                        structured_payload=None,
                        structured_payload_status="legacy",
                    )
                )

                self.assertIn("cv-schema2", structured_export.filename)
                self.assertNotIn("cv-schema2", legacy_export.filename)
                structured_content = json.loads(structured_export.path.read_text(encoding="utf-8"))
                self.assertEqual(structured_content["schema_version"], 2)
                legacy_content = json.loads(legacy_export.path.read_text(encoding="utf-8"))
                self.assertEqual(legacy_content["schema_version"], 1)


class Schema2ImportServiceTest(unittest.TestCase):
    def test_import_schema2_returns_suffixed_title_and_full_payload(self):
        payload = _build_full_payload()
        payload["experience"][0]["custom_note"] = "dato interno"
        raw_content = _encode_json(build_cv_json_payload(_build_structured_cv_row(payload)))

        result = build_cv_json_import_result(raw_content)

        self.assertEqual(result.schema_version, 2)
        self.assertEqual(result.structured_title, "CV Estructurado (importado)")
        self.assertEqual(result.structured_payload["personal"]["headline"], "Tech Lead")
        self.assertEqual(result.structured_payload["experience"][0]["custom_note"], "dato interno")
        self.assertEqual(result.structured_payload["metadata"]["source"], "structured_test")
        self.assertIsNone(result.form_data)

    def test_import_schema2_creates_new_structured_cv_losslessly(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_full_payload()
                payload["experience"][0]["custom_note"] = "dato interno"
                payload["unknown_section"] = {"keep": True}
                raw_content = _encode_json(build_cv_json_payload(_build_structured_cv_row(payload)))

                result = build_cv_json_import_result(raw_content)
                new_cv_id = cv_repository.create_structured_cv(
                    title=result.structured_title,
                    payload=result.structured_payload,
                    metadata_source="json_import",
                )

                normalized = resolve_normalized_cv(cv_repository.get_cv(new_cv_id))
                self.assertTrue(normalized.is_structured)
                self.assertEqual(normalized.title, "CV Estructurado (importado)")
                actual_sections = {
                    key: value for key, value in normalized.sections.items() if key != "metadata"
                }
                expected_sections = {key: value for key, value in payload.items() if key != "metadata"}
                self.assertEqual(actual_sections, expected_sections)
                self.assertEqual(normalized.sections["metadata"]["source"], "json_import")
                self.assertEqual(normalized.legacy_snapshot.full_name, "Ana Perez")

    def test_import_schema2_invalid_payload_is_rejected_in_spanish_without_writes(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                raw_content = _encode_json(
                    {
                        "schema_version": 2,
                        "cv": {
                            "title": "CV Roto",
                            "structured_payload": {"schema_version": 2, "skills": ["broken"]},
                        },
                    }
                )

                with self.assertRaises(ExportServiceError) as context:
                    build_cv_json_import_result(raw_content)

                message = str(context.exception)
                self.assertIn("El JSON estructurado no es valido", message)
                self.assertIn("skills", message)
                self.assertEqual(len(cv_repository.list_cvs()), 0)

    def test_import_rejects_unsupported_and_non_integer_schema_versions(self):
        cases = (
            (3, "no esta soportado"),
            ("2", "numero entero"),
            (1.5, "numero entero"),
            (True, "numero entero"),
        )
        for raw_version, expected_fragment in cases:
            with self.subTest(raw_version=raw_version):
                raw_content = _encode_json({"schema_version": raw_version, "cv": {}})

                with self.assertRaises(ExportServiceError) as context:
                    build_cv_json_import_result(raw_content)

                self.assertIn(expected_fragment, str(context.exception))

    def test_import_schema2_rejects_payload_with_future_internal_version(self):
        raw_content = _encode_json(
            {
                "schema_version": 2,
                "cv": {
                    "title": "CV Futuro",
                    "structured_payload": {"schema_version": 3, "personal": {"full_name": "Ana"}},
                },
            }
        )

        with self.assertRaises(ExportServiceError) as context:
            build_cv_json_import_result(raw_content)

        self.assertIn("El JSON estructurado no es valido", str(context.exception))
        self.assertIn("schema_version", str(context.exception))

    def test_import_schema2_requires_structured_payload_object(self):
        raw_content = _encode_json({"schema_version": 2, "cv": {"title": "Sin payload"}})

        with self.assertRaises(ExportServiceError) as context:
            build_cv_json_import_result(raw_content)

        self.assertIn("structured_payload", str(context.exception))

    def test_import_rejects_oversized_file_before_parsing(self):
        with self.assertRaises(ExportServiceError) as context:
            build_cv_json_import_result(b"x" * (MAX_JSON_IMPORT_BYTES + 1))

        self.assertIn("supera el maximo permitido", str(context.exception))

    def test_import_rejects_non_utf8_content(self):
        with self.assertRaises(ExportServiceError) as context:
            build_cv_json_import_result(b'{"schema_version": 2, "cv": \xff\xfe}')

        self.assertIn("UTF-8", str(context.exception))

    def test_import_flat_payload_without_version_keeps_schema1_legacy_flow(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                raw_content = _encode_json(
                    {
                        "cv": {
                            "title": "CV Plano",
                            "full_name": "Persona Plana",
                            "email": "plana@example.com",
                            "phone": "",
                            "professional_summary": "Perfil",
                            "experience_summary": "Experiencia",
                            "education_summary": "",
                            "skills": "Python",
                        }
                    }
                )

                result = build_cv_json_import_result(raw_content)

                self.assertEqual(result.schema_version, 1)
                self.assertEqual(result.form_data.title, "CV Plano (importado)")
                self.assertEqual(result.form_data.full_name, "Persona Plana")
                self.assertIsNone(result.structured_payload)

                new_cv_id = cv_repository.create_cv(result.form_data)
                stored = cv_repository.get_cv(new_cv_id)
                self.assertIsNone(stored.structured_schema_version)
                self.assertEqual(stored.structured_payload_status, "legacy")

    def test_import_schema2_title_over_limit_is_capped_instead_of_rejected(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                raw_content = _encode_json(
                    {
                        "schema_version": 2,
                        "cv": {"title": "T" * 118, "structured_payload": _build_minimal_payload()},
                    }
                )

                result = build_cv_json_import_result(raw_content)
                new_cv_id = cv_repository.create_structured_cv(
                    title=result.structured_title,
                    payload=result.structured_payload,
                    metadata_source="json_import",
                )

                stored = cv_repository.get_cv(new_cv_id)
                self.assertLessEqual(len(stored.title), FIELD_LIMITS["title"])
                self.assertTrue(stored.title.endswith("(importado)"))
                self.assertTrue(resolve_normalized_cv(stored).is_structured)

    def test_import_schema1_titles_at_boundary_lengths_are_importable(self):
        for title_length in (109, 110, 119, 120):
            with self.subTest(title_length=title_length):
                with tempfile.TemporaryDirectory() as data_directory:
                    with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                        initialize_database()
                        raw_content = _encode_json(
                            {
                                "cv": {
                                    "title": "T" * title_length,
                                    "full_name": "Persona Plana",
                                    "email": "plana@example.com",
                                    "phone": "",
                                    "professional_summary": "Perfil",
                                    "experience_summary": "Experiencia",
                                    "education_summary": "",
                                    "skills": "Python",
                                }
                            }
                        )

                        result = build_cv_json_import_result(raw_content)
                        new_cv_id = cv_repository.create_cv(result.form_data)
                        stored = cv_repository.get_cv(new_cv_id)

                        self.assertLessEqual(len(result.form_data.title), FIELD_LIMITS["title"])
                        self.assertLessEqual(len(stored.title), FIELD_LIMITS["title"])
                        self.assertTrue(result.form_data.title.endswith(" (importado)"))
                        self.assertEqual(stored.structured_payload_status, "legacy")

    def test_import_schema2_titles_at_boundary_lengths_are_importable(self):
        for title_length in (109, 110, 119, 120):
            with self.subTest(title_length=title_length):
                with tempfile.TemporaryDirectory() as data_directory:
                    with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                        initialize_database()
                        cv_id = cv_repository.create_structured_cv(
                            title="T" * title_length,
                            payload=_build_full_payload(),
                            metadata_source="structured_test",
                        )
                        exported = build_cv_json_payload(cv_repository.get_cv(cv_id))

                        result = build_cv_json_import_result(_encode_json(exported))
                        imported_id = cv_repository.create_structured_cv(
                            title=result.structured_title,
                            payload=result.structured_payload,
                            metadata_source="json_import",
                        )

                        stored = cv_repository.get_cv(imported_id)
                        self.assertLessEqual(len(result.structured_title), FIELD_LIMITS["title"])
                        self.assertTrue(result.structured_title.endswith(" (importado)"))
                        self.assertEqual(stored.title, result.structured_title)
                        self.assertTrue(resolve_normalized_cv(stored).is_structured)


class Schema2ExportImportSizeContractTest(unittest.TestCase):
    """Todo export schema 2 emitido por la app debe ser reimportable por la app."""

    def test_export_of_payload_at_persistence_limit_is_importable_and_round_trips(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_payload_with_unknown_extensions_at_limit(MAX_STRUCTURED_PAYLOAD_BYTES)

                cv_id = cv_repository.create_structured_cv(
                    title="CV Al Limite",
                    payload=payload,
                    metadata_source=_LIMIT_METADATA_SOURCE,
                )
                stored = cv_repository.get_cv(cv_id)
                self.assertEqual(len(stored.structured_payload.encode("utf-8")), MAX_STRUCTURED_PAYLOAD_BYTES)

                exported_file = export_cv_json(stored)
                raw_content = exported_file.path.read_bytes()

                self.assertLessEqual(len(raw_content), MAX_JSON_IMPORT_BYTES)

                result = build_cv_json_import_result(raw_content)
                self.assertEqual(result.schema_version, 2)
                self.assertTrue(result.structured_title.endswith("(importado)"))

                imported_payload = result.structured_payload
                self.assertEqual(imported_payload["personal"]["full_name"], "Ana Perez")
                self.assertEqual(imported_payload["personal"]["headline"], "Tech Lead")
                self.assertEqual(imported_payload["certifications"][0]["name"], "AWS Solutions Architect")
                self.assertEqual(imported_payload["unknown_section"], {"keep": True, "extra": ["a", "b"]})
                self.assertEqual(imported_payload["experience"][0]["custom_note"], "dato interno")
                self.assertEqual(imported_payload["_pad"], payload["_pad"])

                imported_id = cv_repository.create_structured_cv(
                    title=result.structured_title,
                    payload=imported_payload,
                    metadata_source=_LIMIT_METADATA_SOURCE,
                )
                imported_stored = cv_repository.get_cv(imported_id)
                self.assertTrue(resolve_normalized_cv(imported_stored).is_structured)
                self.assertEqual(imported_stored.full_name, "Ana Perez")
                self.assertEqual(
                    json.loads(imported_stored.structured_payload)["unknown_section"],
                    {"keep": True, "extra": ["a", "b"]},
                )

    def test_import_limit_is_derived_from_payload_limit_plus_documented_headroom(self):
        self.assertGreater(MAX_JSON_IMPORT_BYTES, MAX_STRUCTURED_PAYLOAD_BYTES)
        self.assertEqual(
            MAX_JSON_IMPORT_BYTES - MAX_STRUCTURED_PAYLOAD_BYTES,
            JSON_IMPORT_ENVELOPE_HEADROOM_BYTES,
        )

    def test_oversized_import_is_still_rejected_with_controlled_spanish_error(self):
        with self.assertRaises(ExportServiceError) as context:
            build_cv_json_import_result(b"x" * (MAX_JSON_IMPORT_BYTES + 1))

        self.assertIn("supera el maximo permitido", str(context.exception))

    def test_schema1_export_still_round_trips_after_export_serialization_change(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_cv(_build_legacy_form_data())

                exported_file = export_cv_json(cv_repository.get_cv(cv_id), schema_version=1)
                raw_content = exported_file.path.read_bytes()

                payload = json.loads(raw_content.decode("utf-8"))
                self.assertEqual(payload["schema_version"], 1)
                self.assertIn("\n", raw_content.decode("utf-8"))

                result = build_cv_json_import_result(raw_content)
                self.assertEqual(result.schema_version, 1)
                self.assertEqual(result.form_data.full_name, payload["cv"]["full_name"])
                self.assertEqual(result.form_data.title, payload["cv"]["title"] + " (importado)")


class NonFiniteJsonImportTest(unittest.TestCase):
    """NaN / Infinity / -Infinity se rechazan antes de tocar la base."""

    def test_schema2_import_rejects_non_finite_numbers_without_writes(self):
        templates = (
            '{"schema_version": 2, "cv": {"title": "CV Roto", "structured_payload": {"schema_version": 2, "personal": {"full_name": "Ana"}}}, "extra": %s}',
            '{"schema_version": %s, "cv": {"title": "CV Roto", "structured_payload": {"schema_version": 2, "personal": {"full_name": "Ana"}}}}',
        )
        for token in ("NaN", "Infinity", "-Infinity"):
            for template in templates:
                raw_content = (template % token).encode("utf-8")
                with self.subTest(token=token, raw_content=raw_content):
                    with tempfile.TemporaryDirectory() as data_directory:
                        with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                            initialize_database()

                            with self.assertRaises(ExportServiceError) as context:
                                build_cv_json_import_result(raw_content)

                            self.assertIn("no es JSON valido", str(context.exception))
                            self.assertEqual(cv_repository.list_cvs(), [])

    def test_schema2_import_rejects_non_finite_number_inside_unknown_extension(self):
        raw_content = (
            '{"schema_version": 2, "cv": {"title": "CV Con Extension", "structured_payload": '
            '{"schema_version": 2, "personal": {"full_name": "Ana"}, "custom_extension": {"score": NaN}}}}'
        ).encode("utf-8")

        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with self.assertRaises(ExportServiceError) as context:
                    build_cv_json_import_result(raw_content)

                self.assertIn("no es JSON valido", str(context.exception))
                self.assertEqual(cv_repository.list_cvs(), [])

    def test_schema1_import_rejects_non_finite_number_inside_unknown_extension(self):
        raw_content = b'{"cv": {"title": "CV Plano", "full_name": "Ana"}, "custom_extension": {"score": Infinity}}'

        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with self.assertRaises(ExportServiceError) as context:
                    build_cv_json_import_result(raw_content)

                self.assertIn("no es JSON valido", str(context.exception))
                self.assertEqual(cv_repository.list_cvs(), [])

    def test_valid_extension_values_still_round_trip(self):
        payload = _build_full_payload()
        payload["unknown_section"] = {"keep": True, "score": 4.5, "ratio": -0.25}

        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Con Extension",
                    payload=payload,
                    metadata_source="structured_test",
                )

                exported = export_cv_json(cv_repository.get_cv(cv_id))
                result = build_cv_json_import_result(exported.path.read_bytes())

                self.assertEqual(result.structured_payload["unknown_section"], {"keep": True, "score": 4.5, "ratio": -0.25})


class StructuredPayloadSizeLimitTest(unittest.TestCase):
    """El limite de bytes del payload se convierte en error de dominio controlado."""

    def test_payload_exactly_at_limit_is_persisted(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_payload_with_exact_serialized_size(MAX_STRUCTURED_PAYLOAD_BYTES)

                self.assertEqual(
                    len(serialize_structured_payload(payload).encode("utf-8")),
                    MAX_STRUCTURED_PAYLOAD_BYTES,
                )

                cv_id = cv_repository.create_structured_cv(
                    title="CV Al Limite",
                    payload=payload,
                    metadata_source=_LIMIT_METADATA_SOURCE,
                )

                stored = cv_repository.get_cv(cv_id)
                self.assertEqual(stored.structured_payload_status, "valid")
                self.assertEqual(len(stored.structured_payload.encode("utf-8")), MAX_STRUCTURED_PAYLOAD_BYTES)

    def test_payload_one_byte_over_limit_raises_domain_error_without_writing(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                at_limit = _build_payload_with_exact_serialized_size(MAX_STRUCTURED_PAYLOAD_BYTES)
                over_limit = _build_payload_one_byte_over_limit()

                self.assertEqual(over_limit["_pad"], at_limit["_pad"] + "x")

                with self.assertRaises(StructuredCVWriteError) as context:
                    cv_repository.create_structured_cv(
                        title="CV Excedido",
                        payload=over_limit,
                        metadata_source=_LIMIT_METADATA_SOURCE,
                    )

                self.assertIn("structured_payload_too_large", context.exception.errors)
                self.assertEqual(len(cv_repository.list_cvs()), 0)

    def test_payload_one_byte_over_limit_raises_domain_error_on_update_without_writing(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Al Limite",
                    payload=_build_full_payload(),
                    metadata_source="structured_test",
                )
                stored_before = cv_repository.get_cv(cv_id)
                over_limit = _build_payload_one_byte_over_limit()

                with self.assertRaises(StructuredCVWriteError):
                    cv_repository.update_structured_cv(
                        cv_id,
                        title="CV Excedido",
                        payload=over_limit,
                        metadata_source=_LIMIT_METADATA_SOURCE,
                    )

                stored_after = cv_repository.get_cv(cv_id)
                self.assertEqual(stored_after.title, stored_before.title)
                self.assertEqual(stored_after.structured_payload, stored_before.structured_payload)


class Schema2JSONRoutesTest(unittest.TestCase):
    def test_export_json_route_serves_canonical_schema2_and_explicit_schema1(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Fuente",
                    payload=_build_full_payload(),
                    metadata_source="structured_test",
                )

                with TestClient(app) as client:
                    canonical_response = client.get(f"/cvs/{cv_id}/export/json")
                    schema1_response = client.get(f"/cvs/{cv_id}/export/json?schema_version=1")

                self.assertEqual(canonical_response.status_code, 200)
                canonical_payload = json.loads(canonical_response.content)
                self.assertEqual(canonical_payload["schema_version"], 2)
                self.assertEqual(
                    canonical_payload["cv"]["structured_payload"]["personal"]["headline"],
                    "Tech Lead",
                )
                self.assertIn(
                    "cv-schema2",
                    canonical_response.headers.get("content-disposition", ""),
                )

                self.assertEqual(schema1_response.status_code, 200)
                schema1_payload = json.loads(schema1_response.content)
                self.assertEqual(schema1_payload["schema_version"], 1)
                self.assertEqual(schema1_payload["cv"]["full_name"], "Ana Perez")
                self.assertNotIn("structured_payload", schema1_payload["cv"])

    def test_export_json_route_rejects_schema2_for_legacy_cv(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_cv(_build_legacy_form_data())

                with TestClient(app) as client:
                    response = client.get(f"/cvs/{cv_id}/export/json?schema_version=2")

                self.assertEqual(response.status_code, 400)
                self.assertIn("requiere un CV estructurado", response.text)

    def test_import_schema2_route_creates_new_structured_cv_without_overwriting_source(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                source_payload = _build_full_payload()
                source_payload["experience"][0]["custom_note"] = "dato interno"
                source_id = cv_repository.create_structured_cv(
                    title="CV Fuente",
                    payload=source_payload,
                    metadata_source="structured_test",
                )

                with TestClient(app) as client:
                    export_response = client.get(f"/cvs/{source_id}/export/json")
                    import_response = client.post(
                        "/cvs/import/json",
                        files={"json_file": ("cv.json", export_response.content, "application/json")},
                        follow_redirects=False,
                    )

                self.assertEqual(import_response.status_code, 303)
                location = import_response.headers["location"]
                self.assertIn("message=CV+importado+desde+JSON+correctamente", location)
                imported_id = int(location.split("/")[-1].split("?")[0])
                self.assertNotEqual(imported_id, source_id)

                source_after = resolve_normalized_cv(cv_repository.get_cv(source_id))
                self.assertTrue(source_after.is_structured)
                self.assertEqual(source_after.sections["metadata"]["source"], "structured_test")
                self.assertEqual(source_after.sections["experience"][0]["custom_note"], "dato interno")

                imported = resolve_normalized_cv(cv_repository.get_cv(imported_id))
                self.assertTrue(imported.is_structured)
                self.assertEqual(imported.title, "CV Fuente (importado)")
                self.assertEqual(imported.sections["personal"]["headline"], "Tech Lead")
                self.assertEqual(imported.sections["experience"][0]["custom_note"], "dato interno")
                self.assertEqual(imported.sections["metadata"]["source"], "json_import")

    def test_import_schema2_invalid_payload_redirects_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_repository.create_cv(_build_legacy_form_data())
                count_before = len(cv_repository.list_cvs())
                raw_content = _encode_json(
                    {
                        "schema_version": 2,
                        "cv": {
                            "title": "CV Roto",
                            "structured_payload": {"schema_version": 2, "skills": ["broken"]},
                        },
                    }
                )

                with TestClient(app) as client:
                    response = client.post(
                        "/cvs/import/json",
                        files={"json_file": ("cv.json", raw_content, "application/json")},
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 303)
                self.assertIn("No+se+pudo+importar+el+JSON", response.headers["location"])
                self.assertEqual(len(cv_repository.list_cvs()), count_before)

    def test_import_unsupported_schema_version_shows_actionable_spanish_error(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                raw_content = _encode_json({"schema_version": 3, "cv": {}})

                with TestClient(app) as client:
                    response = client.post(
                        "/cvs/import/json",
                        files={"json_file": ("cv.json", raw_content, "application/json")},
                        follow_redirects=True,
                    )

                self.assertEqual(response.status_code, 200)
                self.assertIn("No se pudo importar el JSON", response.text)
                self.assertIn("no esta soportado", response.text)

    def test_detail_offers_schema1_download_link_for_structured_cv_only(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                structured_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_full_payload(),
                    metadata_source="structured_test",
                )
                legacy_id = cv_repository.create_cv(_build_legacy_form_data())

                with TestClient(app) as client:
                    structured_detail = client.get(f"/cvs/{structured_id}")
                    legacy_detail = client.get(f"/cvs/{legacy_id}")

                self.assertEqual(structured_detail.status_code, 200)
                self.assertIn(f"/cvs/{structured_id}/export/json?schema_version=1", structured_detail.text)
                self.assertIn("Descargar JSON plano (schema 1)", structured_detail.text)
                self.assertEqual(legacy_detail.status_code, 200)
                self.assertNotIn("?schema_version=1", legacy_detail.text)


def _encode_json(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _build_legacy_form_data() -> CVFormData:
    return CVFormData(
        title="CV Legacy",
        full_name="Persona Legacy",
        email="legacy@example.com",
        phone="",
        professional_summary="Perfil legacy",
        experience_summary="Experiencia legacy",
        education_summary="Educacion legacy",
        skills="Python",
    )


def _build_cv_row(*, structured_schema_version, structured_payload, structured_payload_status):
    return CV(
        id=7,
        title="CV Estructurado",
        full_name="Nombre Legacy",
        email="legacy@example.com",
        phone="11 1111 1111",
        professional_summary="Perfil legacy",
        experience_summary="Experiencia legacy",
        education_summary="Educacion legacy",
        skills="Python, SQL",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        deleted_at=None,
        structured_schema_version=structured_schema_version,
        structured_payload=structured_payload,
        structured_payload_status=structured_payload_status,
    )


def _build_structured_cv_row(payload: dict[str, object]) -> CV:
    return _build_cv_row(
        structured_schema_version=2,
        structured_payload=serialize_structured_payload(payload),
        structured_payload_status="valid",
    )


def _build_minimal_payload() -> dict[str, object]:
    return {"schema_version": 2, "personal": {"full_name": "Ana"}}


def _build_full_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "personal": {"full_name": "Ana Perez", "headline": "Tech Lead", "location": "Buenos Aires"},
        "contact": {"email": "ana@example.com", "phone": "+54 11 1234 5678", "links": ["https://ana.example.com"]},
        "summary": "Perfil estructurado",
        "skills": [
            {"label": "Python", "category": "Backend", "level": "Avanzado", "order": 1},
            {"label": "SQL", "category": "Datos", "level": "Intermedio", "order": 2},
        ],
        "experience": [
            {
                "company": "Globex",
                "role": "Lider Tecnico",
                "location": "Remoto",
                "start_date": "2022",
                "end_date": "",
                "current": True,
                "summary": "Liderazgo de plataforma",
                "highlights": ["Diseno de plataforma"],
                "technologies": ["Python", "FastAPI"],
                "order": 2,
            },
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
            },
        ],
        "education": [
            {
                "institution": "UNLP",
                "degree": "Ing. en Sistemas",
                "field": "Sistemas",
                "start_date": "2012",
                "end_date": "2017",
                "summary": "",
                "order": 1,
            },
        ],
        "certifications": [{"name": "AWS Solutions Architect", "issuer": "Amazon", "date": "2024", "order": 1}],
        "languages": [{"name": "Espanol", "level": "Nativo", "order": 1}],
        "projects": [
            {
                "name": "cv-latex",
                "summary": "App de CVs",
                "technologies": ["Python"],
                "link": "https://github.com/example/cv-latex",
                "order": 1,
            },
        ],
        "links": [{"label": "LinkedIn", "url": "https://linkedin.com/in/ana", "order": 1}],
        "additional_info": [{"title": "Disponibilidad", "content": "Full-time remoto", "order": 1}],
        "metadata": {"source": "structured_test", "synced_from_legacy_at": ""},
    }


def _build_payload_with_exact_serialized_size(target_bytes: int) -> dict:
    """Ajusta un payload valido hasta que su serializacion ocupe `target_bytes`.

    Solo sirve para objetivos dentro del limite permitido: si el serializador
    rechaza el candidato no se puede medir su tamano exacto. La metadata se
    precarga con la misma longitud que eliestampa real del write bundle, asi
    el tamano medido es el que se persiste.
    """
    payload = _build_full_payload()
    payload["metadata"] = {
        "source": _LIMIT_METADATA_SOURCE,
        "synced_from_legacy_at": _LIMIT_METADATA_TIMESTAMP,
    }

    pad = 0
    for _ in range(5):
        candidate = dict(payload)
        candidate["_pad"] = "x" * pad
        current = len(serialize_structured_payload(candidate).encode("utf-8"))
        if current == target_bytes:
            return candidate
        pad += target_bytes - current

    raise AssertionError("No se pudo ajustar el tamano del payload estructurado")



def _build_payload_with_unknown_extensions_at_limit(target_bytes: int) -> dict:
    """Payload v2 valido con extensiones desconocidas ajustado al tamano exacto."""
    payload = _build_full_payload()
    payload["experience"][0]["custom_note"] = "dato interno"
    payload["unknown_section"] = {"keep": True, "extra": ["a", "b"]}
    payload["metadata"] = {
        "source": _LIMIT_METADATA_SOURCE,
        "synced_from_legacy_at": _LIMIT_METADATA_TIMESTAMP,
    }

    pad = 0
    for _ in range(5):
        candidate = dict(payload)
        candidate["_pad"] = "x" * pad
        current = len(serialize_structured_payload(candidate).encode("utf-8"))
        if current == target_bytes:
            return candidate
        pad += target_bytes - current

    raise AssertionError("No se pudo ajustar el tamano del payload estructurado")

def _build_payload_one_byte_over_limit() -> dict:
    """Payload valido que excede el limite por exactamente un byte."""
    at_limit = _build_payload_with_exact_serialized_size(MAX_STRUCTURED_PAYLOAD_BYTES)
    return dict(at_limit, _pad=at_limit["_pad"] + "x")


if __name__ == "__main__":
    unittest.main()
