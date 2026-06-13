import unittest

from app.services.structured_cv_service import resolve_structured_payload_state


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
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload='{"schema_version": 2, "personal": {"full_name": "Ana"}}',
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
        state = resolve_structured_payload_state(
            structured_schema_version=2,
            structured_payload='{"schema_version": 2}',
            structured_payload_status="stale",
        )

        self.assertFalse(state.is_structured)
        self.assertEqual(state.reason, "payload_not_marked_valid")


if __name__ == "__main__":
    unittest.main()
