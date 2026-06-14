import unittest

from app.schemas import CVFormData
from app.services.structured_cv_service import (
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

    def test_partial_v2_payload_still_resolves_as_structured(self):
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload='{"schema_version":2,"personal":{"full_name":"Ana"}}',
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

    def test_partial_v2_payload_is_normalized_with_defaults(self):
        normalized_payload = normalize_structured_payload_v2(
            {
                "schema_version": 2,
                "personal": {"full_name": "Ana Perez"},
            }
        )

        self.assertIsNotNone(normalized_payload)
        self.assertEqual(normalized_payload["summary"], "")
        self.assertEqual(normalized_payload["contact"]["email"], "")
        self.assertEqual(normalized_payload["skills"], [])
        self.assertEqual(normalized_payload["metadata"]["source"], "")

    def test_rejects_payload_with_corrupt_top_level_types(self):
        validation = validate_structured_payload_v2({"schema_version": 2, "contact": "broken"})

        self.assertFalse(validation.is_valid)
        self.assertIn("contact_must_be_object", validation.errors)

    def test_rejects_payload_with_corrupt_item_types(self):
        validation = validate_structured_payload_v2({"schema_version": 2, "skills": ["python"]})

        self.assertFalse(validation.is_valid)
        self.assertIn("skills_0_must_be_object", validation.errors)


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


if __name__ == "__main__":
    unittest.main()
