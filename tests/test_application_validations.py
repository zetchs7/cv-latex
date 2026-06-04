import unittest

from app.schemas import ApplicationFormData
from app.validations.application_validations import APPLICATION_STATUSES, validate_application_form


class ApplicationValidationsTest(unittest.TestCase):
    def test_rejects_invalid_status_and_dates(self):
        form_data = ApplicationFormData(
            company="ACME",
            position="Backend Engineer",
            link="https://example.com/job",
            source="LinkedIn",
            applied_on="2026-13-40",
            status="desconocido",
            associated_cv_id=None,
            associated_cover_letter_id=None,
            notes="",
            next_action="",
            follow_up_date="2026-99-99",
        )

        errors = validate_application_form(form_data)

        self.assertIn("applied_on", errors)
        self.assertIn("status", errors)
        self.assertIn("follow_up_date", errors)

    def test_accepts_allowed_statuses(self):
        for application_status in APPLICATION_STATUSES:
            with self.subTest(application_status=application_status):
                form_data = ApplicationFormData(
                    company="ACME",
                    position="Backend Engineer",
                    link="",
                    source="",
                    applied_on="2026-06-04",
                    status=application_status,
                    associated_cv_id=None,
                    associated_cover_letter_id=None,
                    notes="",
                    next_action="",
                    follow_up_date="",
                )

                self.assertEqual(validate_application_form(form_data), {})


if __name__ == "__main__":
    unittest.main()
