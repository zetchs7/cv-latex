import unittest

from app.schemas import CVFormData
from app.services.structured_cv_service import (
    StructuredCVWriteError,
    build_structured_payload_from_legacy,
    deserialize_structured_payload,
    normalize_structured_payload_v2,
    serialize_structured_payload,
    validate_structured_payload_v2,
    resolve_structured_payload_state,
)


class StructuredCVServiceTest(unittest.TestCase):
    def test_missing_payload_is_legacy(self):
        state = resolve_structured_payload_state(
            structured_schema_version=None,
            structured_payload=None,
            structured_payload_status="legacy",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.mode, "legacy")

    def test_schema_version_one_is_legacy(self):
        state = resolve_structured_payload_state(
            structured_schema_version=1,
            structured_payload='{"schema_version": 1}',
            structured_payload_status="valid",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.reason, "schema_version_legacy_or_missing")

    def test_schema_version_two_with_valid_payload_is_structured(self):
        payload = serialize_structured_payload(_build_payload())
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload=payload,
            structured_payload_status="valid",
        )

        self.assertTrue(state.is_structured)
        self.assertEqual(state.mode, "structured")

    def test_invalid_payload_falls_back_to_legacy(self):
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload="{invalid-json",
            structured_payload_status="valid",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.reason, "payload_invalid")

    def test_payload_not_marked_valid_falls_back_to_legacy(self):
        payload = serialize_structured_payload(_build_payload())
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload=payload,
            structured_payload_status="stale",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.reason, "payload_not_marked_valid")

    def test_payload_without_internal_schema_version_uses_declared_row_version(self):
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload='{"personal":{"full_name":"Ana"}}',
            structured_payload_status="valid",
        )

        self.assertTrue(state.is_structured)
        self.assertEqual(state.reason, "payload_valid")

    def test_builds_valid_schema_two_payload_from_legacy_fields(self):
        payload = build_structured_payload_from_legacy(_build_form_data(), metadata_source="legacy_test")

        validation = validate_structured_payload_v2(payload)

        self.assertTrue(validation.is_valid)
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["personal"]["full_name"], "Ana Perez")
        self.assertEqual(payload["contact"]["email"], "ana@example.com")
        self.assertEqual(payload["summary"], "Perfil profesional")
        self.assertEqual(payload["skills"][0]["label"], "Python")
        self.assertEqual(payload["experience"][0]["summary"], "Experiencia principal")
        self.assertEqual(payload["education"][0]["summary"], "Educacion principal")
        self.assertEqual(payload["metadata"]["source"], "legacy_test")

    def test_serialized_payload_round_trips_as_valid_payload(self):
        serialized_payload = serialize_structured_payload(_build_payload())
        payload = deserialize_structured_payload(serialized_payload)

        self.assertIsNotNone(payload)
        validation = validate_structured_payload_v2(payload)
        self.assertTrue(validation.is_valid)

    def test_schema_less_payload_is_normalized_with_declared_v2_defaults(self):
        normalized_payload = normalize_structured_payload_v2(
            {
                "personal": {"full_name": "Ana Perez"},
            },
            declared_schema_version=2,
        )

        self.assertIsNotNone(normalized_payload)
        self.assertEqual(normalized_payload["schema_version"], 2)
        self.assertEqual(normalized_payload["summary"], "")
        self.assertEqual(normalized_payload["contact"]["email"], "")
        self.assertEqual(normalized_payload["skills"], [])
        self.assertEqual(normalized_payload["metadata"]["source"], "")

    def test_schema_less_payload_without_declared_version_is_rejected(self):
        validation = validate_structured_payload_v2({"personal": {"full_name": "Ana"}})

        self.assertFalse(validation.is_valid)
        self.assertIn("schema_version_missing", validation.errors)

    def test_schema_less_payload_with_declared_version_three_is_rejected(self):
        state = resolve_structured_payload_state(
            structured_schema_version=3,
            structured_payload='{"personal":{"full_name":"Ana"}}',
            structured_payload_status="valid",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.reason, "payload_invalid")

    def test_declared_version_three_with_internal_schema_version_two_is_rejected(self):
        state = resolve_structured_payload_state(
            structured_schema_version=3,
            structured_payload='{"schema_version":2,"personal":{"full_name":"Ana"}}',
            structured_payload_status="valid",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.reason, "payload_invalid")

    def test_payload_with_null_schema_version_is_rejected_even_if_row_declares_v2(self):
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload='{"schema_version":null,"personal":{"full_name":"Ana"}}',
            structured_payload_status="valid",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.reason, "payload_invalid")

    def test_payload_with_non_integer_schema_version_is_rejected(self):
        validation = validate_structured_payload_v2({"schema_version": "2", "personal": {"full_name": "Ana"}})

        self.assertFalse(validation.is_valid)
        self.assertIn("schema_version_must_be_integer", validation.errors)

    def test_payload_with_integer_schema_version_remains_valid(self):
        validation = validate_structured_payload_v2({"schema_version": 2, "personal": {"full_name": "Ana"}})

        self.assertTrue(validation.is_valid)
        self.assertIsNotNone(validation.normalized_payload)
        self.assertEqual(validation.normalized_payload["schema_version"], 2)

    def test_payload_with_integer_schema_version_three_is_rejected_by_v2_validator(self):
        validation = validate_structured_payload_v2({"schema_version": 3, "personal": {"full_name": "Ana"}})

        self.assertFalse(validation.is_valid)
        self.assertIn("schema_version_unsupported", validation.errors)

    def test_rejects_payload_with_corrupt_top_level_types(self):
        validation = validate_structured_payload_v2(
            {"personal": {"full_name": "Ana"}, "contact": "broken"},
            declared_schema_version=2,
        )

        self.assertFalse(validation.is_valid)
        self.assertIn("contact_must_be_object", validation.errors)

    def test_rejects_payload_with_corrupt_item_types(self):
        validation = validate_structured_payload_v2(
            {"skills": ["python"]},
            declared_schema_version=2,
        )

        self.assertFalse(validation.is_valid)
        self.assertIn("skills_0_must_be_object", validation.errors)

    def test_accepts_full_master_sections_payload(self):
        validation = validate_structured_payload_v2(_build_master_payload())

        self.assertTrue(validation.is_valid, validation.errors)
        self.assertIsNotNone(validation.normalized_payload)

    def test_defaults_missing_additional_info_and_headline_fields(self):
        normalized_payload = normalize_structured_payload_v2(
            {"personal": {"full_name": "Ana Perez"}},
            declared_schema_version=2,
        )

        self.assertEqual(normalized_payload["additional_info"], [])
        self.assertEqual(normalized_payload["personal"]["headline"], "")
        self.assertEqual(normalized_payload["metadata"]["source"], "")

    def test_rejects_summary_over_legacy_professional_summary_limit(self):
        validation = validate_structured_payload_v2({"schema_version": 2, "summary": "x" * 1201})

        self.assertFalse(validation.is_valid)
        self.assertIn("summary_too_long", validation.errors)

    def test_rejects_skill_label_over_limit(self):
        validation = validate_structured_payload_v2(
            {"schema_version": 2, "skills": [{"label": "x" * 121}]},
        )

        self.assertFalse(validation.is_valid)
        self.assertIn("skills_0_label_too_long", validation.errors)

    def test_rejects_non_object_items_in_every_list_section(self):
        payload = {
            "schema_version": 2,
            "certifications": ["AWS"],
            "languages": ["Espanol"],
            "projects": ["proyecto"],
            "links": ["link"],
            "additional_info": ["info"],
        }

        validation = validate_structured_payload_v2(payload)

        self.assertFalse(validation.is_valid)
        for section in ("certifications", "languages", "projects", "links", "additional_info"):
            self.assertIn(f"{section}_0_must_be_object", validation.errors)

    def test_rejects_too_many_items_per_section(self):
        payload = {
            "schema_version": 2,
            "languages": [{"name": f"Idioma {index}"} for index in range(21)],
        }

        validation = validate_structured_payload_v2(payload)

        self.assertFalse(validation.is_valid)
        self.assertIn("languages_too_many_items", validation.errors)

    def test_rejects_experience_item_with_non_boolean_current(self):
        validation = validate_structured_payload_v2(
            {"schema_version": 2, "experience": [{"current": "si"}]},
        )

        self.assertFalse(validation.is_valid)
        self.assertIn("experience_0_current_must_be_boolean", validation.errors)

    def test_rejects_boolean_order_values(self):
        validation = validate_structured_payload_v2(
            {"schema_version": 2, "skills": [{"order": True}]},
        )

        self.assertFalse(validation.is_valid)
        self.assertIn("skills_0_order_must_be_integer", validation.errors)

    def test_rejects_highlights_that_are_not_string_lists(self):
        validation = validate_structured_payload_v2(
            {"schema_version": 2, "experience": [{"highlights": "logro"}]},
        )

        self.assertFalse(validation.is_valid)
        self.assertIn("experience_0_highlights_must_be_list", validation.errors)

        validation_with_items = validate_structured_payload_v2(
            {"schema_version": 2, "experience": [{"highlights": [123]}]},
        )

        self.assertFalse(validation_with_items.is_valid)
        self.assertIn("experience_0_highlights_0_must_be_string", validation_with_items.errors)

    def test_rejects_contact_links_over_item_limit(self):
        payload = {
            "schema_version": 2,
            "contact": {"links": [f"https://link{index}.example.com" for index in range(11)]},
        }

        validation = validate_structured_payload_v2(payload)

        self.assertFalse(validation.is_valid)
        self.assertIn("contact_links_too_many_items", validation.errors)

    def test_rejects_payload_with_overlong_metadata_source(self):
        validation = validate_structured_payload_v2(
            {"schema_version": 2, "metadata": {"source": "x" * 61}},
        )

        self.assertFalse(validation.is_valid)
        self.assertIn("metadata_source_too_long", validation.errors)


def _build_master_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "personal": {"full_name": "Ana Perez", "headline": "Tech Lead", "location": "Buenos Aires"},
        "contact": {"email": "ana@example.com", "phone": "+54 11 1234 5678", "links": []},
        "summary": "Perfil profesional",
        "skills": [{"label": "Python", "category": "Backend", "level": "Avanzado", "order": 1}],
        "experience": [
            {
                "company": "Acme",
                "role": "Desarrollador",
                "location": "Remoto",
                "start_date": "2020",
                "end_date": "2021",
                "current": False,
                "summary": "Desarrollo backend",
                "highlights": ["Diseno de API"],
                "technologies": ["Python"],
                "order": 1,
            }
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
            }
        ],
        "certifications": [{"name": "AWS", "issuer": "Amazon", "date": "2024", "order": 1}],
        "languages": [{"name": "Espanol", "level": "Nativo", "order": 1}],
        "projects": [{"name": "cv-latex", "summary": "App de CVs", "technologies": [], "link": "", "order": 1}],
        "links": [{"label": "LinkedIn", "url": "https://linkedin.com/in/ana", "order": 1}],
        "additional_info": [{"title": "Disponibilidad", "content": "Full-time", "order": 1}],
        "metadata": {"source": "test", "synced_from_legacy_at": ""},
    }


def _build_form_data() -> CVFormData:
    return CVFormData(
        title="CV Ana",
        full_name="Ana Perez",
        email="ana@example.com",
        phone="+54 11 1234 5678",
        professional_summary="Perfil profesional",
        experience_summary="Experiencia principal",
        education_summary="Educacion principal",
        skills="Python, FastAPI",
    )


def _build_payload() -> dict[str, object]:
    return build_structured_payload_from_legacy(_build_form_data(), metadata_source="test")


class NonFiniteNumberSerializationTest(unittest.TestCase):
    """El payload persistido nunca puede emitir JSON no estandar."""

    def test_serialize_rejects_non_finite_numbers_with_a_dedicated_error_code(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                payload = dict(_build_payload(), custom_extension={"score": value})

                with self.assertRaises(StructuredCVWriteError) as context:
                    serialize_structured_payload(payload)

                self.assertIn("structured_payload_non_finite_number", context.exception.errors)
                self.assertIn("no es JSON valido", str(context.exception))

    def test_serialize_keeps_accepting_finite_floats_and_unknown_extensions(self):
        payload = dict(_build_payload(), custom_extension={"score": 4.5, "ratio": -0.25})

        serialized = serialize_structured_payload(payload)

        self.assertIn('"score":4.5', serialized)
        self.assertIn('"ratio":-0.25', serialized)


if __name__ == "__main__":
    unittest.main()
