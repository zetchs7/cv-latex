import os
import tempfile
import unittest
from unittest.mock import patch

from app.database import initialize_database
from app.repositories.application_repository import (
    create_application,
    get_application,
    list_applications,
    soft_delete_application,
    update_application,
)
from app.repositories.cover_letter_repository import create_cover_letter
from app.repositories.cv_repository import create_cv
from app.schemas import ApplicationFormData, CoverLetterFormData, CVFormData


class ApplicationRepositoryTest(unittest.TestCase):
    def test_creates_and_reads_application_with_associations(self):
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

                application_id = create_application(
                    ApplicationFormData(
                        company="Globex",
                        position="Platform Engineer",
                        link="https://example.com/job",
                        source="LinkedIn",
                        applied_on="2026-06-04",
                        status="enviado",
                        associated_cv_id=cv_id,
                        associated_cover_letter_id=cover_letter_id,
                        notes="Aplicacion enviada.",
                        next_action="Esperar respuesta.",
                        follow_up_date="2026-06-10",
                    )
                )

                application = get_application(application_id)

                self.assertIsNotNone(application)
                self.assertEqual(application.associated_cv_id, cv_id)
                self.assertEqual(application.associated_cv_title, "CV Base")
                self.assertEqual(application.associated_cover_letter_id, cover_letter_id)
                self.assertEqual(application.associated_cover_letter_label, "ACME Corp - Backend Engineer")
                self.assertEqual(application.status, "enviado")

    def test_updates_lists_and_soft_deletes_application(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                application_id = create_application(
                    ApplicationFormData(
                        company="Globex",
                        position="Platform Engineer",
                        link="",
                        source="Referral",
                        applied_on="2026-06-04",
                        status="pendiente",
                        associated_cv_id=None,
                        associated_cover_letter_id=None,
                        notes="Nota inicial.",
                        next_action="Enviar CV.",
                        follow_up_date="",
                    )
                )

                updated = update_application(
                    application_id,
                    ApplicationFormData(
                        company="Globex",
                        position="Senior Platform Engineer",
                        link="https://example.com/jobs/1",
                        source="Referral",
                        applied_on="2026-06-04",
                        status="entrevista",
                        associated_cv_id=None,
                        associated_cover_letter_id=None,
                        notes="Agendada primera entrevista.",
                        next_action="Preparar preguntas.",
                        follow_up_date="2026-06-12",
                    ),
                )

                self.assertTrue(updated)
                applications = list_applications()
                self.assertEqual(len(applications), 1)
                self.assertEqual(applications[0].position, "Senior Platform Engineer")
                self.assertEqual(applications[0].status, "entrevista")

                deleted = soft_delete_application(application_id)
                self.assertTrue(deleted)
                self.assertEqual(list_applications(), [])


if __name__ == "__main__":
    unittest.main()
