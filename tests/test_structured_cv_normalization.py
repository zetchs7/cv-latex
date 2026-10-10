import json
import unittest

from app.models import CV
from app.schemas import CVFormData
from app.services.structured_cv_service import (
    StructuredCVWriteError,
    build_legacy_snapshot_from_payload,
    build_structured_cv_write_bundle,
    normalize_structured_payload_v2,
    resolve_normalized_cv,
    serialize_structured_payload,
)


class ResolveNormalizedCVTest(unittest.TestCase):
    def test_structured_cv_resolves_payload_sections_and_legacy_projection(self):
        payload = _build_full_payload()
        cv = _build_cv(
            structured_schema_version=2,
            structured_payload=serialize_structured_payload(payload),
            structured_payload_status="valid",
        )

        normalized = resolve_normalized_cv(cv)

        self.assertTrue(normalized.is_structured)
        self.assertEqual(normalized.mode, "structured")
        self.assertEqual(normalized.reason, "payload_valid")
        self.assertEqual(normalized.title, "CV Estructurado")
        self.assertEqual(normalized.sections["schema_version"], 2)
        self.assertEqual(normalized.sections["personal"]["headline"], "Tech Lead")
        self.assertEqual(normalized.sections["additional_info"][0]["title"], "Disponibilidad")
        self.assertEqual(normalized.sections["metadata"]["source"], "structured_test")
        self.assertEqual(normalized.legacy_snapshot.title, "CV Estructurado")
        self.assertEqual(normalized.legacy_snapshot.full_name, "Ana Perez")
        self.assertEqual(normalized.legacy_snapshot.email, "ana@example.com")
        self.assertEqual(normalized.legacy_snapshot.phone, "+54 11 1234 5678")
        self.assertEqual(normalized.legacy_snapshot.professional_summary, "Perfil estructurado")
        self.assertEqual(normalized.legacy_snapshot.skills, "Python, SQL")

    def test_legacy_cv_resolves_legacy_fields_as_canonical_source(self):
        cv = _build_cv(structured_schema_version=None, structured_payload=None, structured_payload_status="legacy")

        normalized = resolve_normalized_cv(cv)

        self.assertFalse(normalized.is_structured)
        self.assertEqual(normalized.mode, "legacy")
        self.assertEqual(normalized.reason, "schema_version_legacy_or_missing")
        self.assertEqual(
            normalized.legacy_snapshot,
            CVFormData(
                title="CV Estructurado",
                full_name="Nombre Legacy",
                email="legacy@example.com",
                phone="11 1111 1111",
                professional_summary="Perfil legacy",
                experience_summary="Experiencia legacy",
                education_summary="Educacion legacy",
                skills="Python, SQL",
            ),
        )
        self.assertEqual(normalized.sections["schema_version"], 2)
        self.assertEqual(normalized.sections["personal"]["full_name"], "Nombre Legacy")
        self.assertEqual(normalized.sections["summary"], "Perfil legacy")
        self.assertEqual(normalized.sections["skills"][0]["label"], "Python")
        self.assertEqual(normalized.sections["skills"][1]["label"], "SQL")
        self.assertEqual(normalized.sections["experience"][0]["summary"], "Experiencia legacy")
        self.assertEqual(normalized.sections["education"][0]["summary"], "Educacion legacy")
        self.assertEqual(normalized.sections["certifications"], [])
        self.assertEqual(normalized.sections["languages"], [])
        self.assertEqual(normalized.sections["projects"], [])
        self.assertEqual(normalized.sections["links"], [])
        self.assertEqual(normalized.sections["additional_info"], [])
        self.assertEqual(normalized.sections["metadata"]["source"], "legacy_view")
        self.assertEqual(normalized.sections["metadata"]["synced_from_legacy_at"], "")

    def test_corrupt_payload_row_falls_back_entirely_to_legacy(self):
        cv = _build_cv(
            structured_schema_version=2,
            structured_payload="{invalid-json",
            structured_payload_status="valid",
        )

        normalized = resolve_normalized_cv(cv)

        self.assertFalse(normalized.is_structured)
        self.assertEqual(normalized.reason, "payload_invalid")
        self.assertEqual(normalized.legacy_snapshot.full_name, "Nombre Legacy")
        self.assertEqual(normalized.legacy_snapshot.experience_summary, "Experiencia legacy")
        self.assertEqual(normalized.sections["personal"]["full_name"], "Nombre Legacy")

    def test_future_schema_version_row_falls_back_entirely_to_legacy(self):
        cv = _build_cv(
            structured_schema_version=3,
            structured_payload='{"schema_version": 3, "personal": {"full_name": "Futuro"}}',
            structured_payload_status="valid",
        )

        normalized = resolve_normalized_cv(cv)

        self.assertFalse(normalized.is_structured)
        self.assertEqual(normalized.reason, "payload_invalid")
        self.assertEqual(normalized.legacy_snapshot.full_name, "Nombre Legacy")
        self.assertEqual(normalized.sections["personal"]["full_name"], "Nombre Legacy")

    def test_stale_status_row_falls_back_entirely_to_legacy(self):
        payload = serialize_structured_payload({"schema_version": 2, "personal": {"full_name": "Ana"}})
        cv = _build_cv(structured_schema_version=2, structured_payload=payload, structured_payload_status="stale")

        normalized = resolve_normalized_cv(cv)

        self.assertFalse(normalized.is_structured)
        self.assertEqual(normalized.reason, "payload_not_marked_valid")
        self.assertEqual(normalized.sections["personal"]["full_name"], "Nombre Legacy")

    def test_structured_only_fields_survive_normalization_losslessly(self):
        payload = _build_full_payload()
        payload["experience"][0]["custom_note"] = "dato interno"
        payload["unknown_section"] = {"anything": True}

        normalized_payload = normalize_structured_payload_v2(payload)

        self.assertEqual(normalized_payload["experience"][0]["custom_note"], "dato interno")
        self.assertEqual(normalized_payload["unknown_section"], {"anything": True})


class LegacySnapshotDerivationTest(unittest.TestCase):
    def test_snapshot_maps_structured_sections_to_legacy_fields(self):
        payload = _build_full_payload()

        snapshot = build_legacy_snapshot_from_payload(payload, title="CV Titulo")

        self.assertEqual(snapshot.title, "CV Titulo")
        self.assertEqual(snapshot.full_name, "Ana Perez")
        self.assertEqual(snapshot.email, "ana@example.com")
        self.assertEqual(snapshot.phone, "+54 11 1234 5678")
        self.assertEqual(snapshot.professional_summary, "Perfil estructurado")
        self.assertEqual(snapshot.skills, "Python, SQL")

    def test_snapshot_formats_experience_items_in_declared_order(self):
        payload = _build_full_payload()

        snapshot = build_legacy_snapshot_from_payload(payload, title="CV Titulo")

        self.assertLess(
            snapshot.experience_summary.index("Desarrollador"),
            snapshot.experience_summary.index("Lider Tecnico"),
        )
        self.assertIn("Desarrollador - Acme (2020 - 2021)", snapshot.experience_summary)
        self.assertIn("Lider Tecnico - Globex (2022 - Presente)", snapshot.experience_summary)
        self.assertIn("• Diseno de plataforma", snapshot.experience_summary)
        self.assertIn("Tecnologias: Python, FastAPI", snapshot.experience_summary)

    def test_snapshot_formats_education_items(self):
        payload = _build_full_payload()

        snapshot = build_legacy_snapshot_from_payload(payload, title="CV Titulo")

        self.assertIn("Ing. en Sistemas - UNLP (2012 - 2017)", snapshot.education_summary)
        self.assertIn("Campo: Sistemas", snapshot.education_summary)

    def test_snapshot_rejects_long_content_without_truncation(self):
        payload = {
            "schema_version": 2,
            "experience": [{"summary": "x" * 600} for _ in range(4)],
        }

        normalized_payload = normalize_structured_payload_v2(payload)
        self.assertEqual(len(normalized_payload["experience"][0]["summary"]), 600)

        with self.assertRaises(StructuredCVWriteError) as context:
            build_structured_cv_write_bundle(title="CV Titulo", payload=payload, metadata_source="editor")
        self.assertIn("experience_summary", " ".join(context.exception.errors))


class StructuredWriteBundleTest(unittest.TestCase):
    def test_builds_valid_bundle_with_stamped_metadata_and_snapshot(self):
        bundle = build_structured_cv_write_bundle(
            title="CV Nuevo",
            payload=_build_full_payload(),
            metadata_source="structured_editor",
        )

        self.assertEqual(bundle.form_data.title, "CV Nuevo")
        self.assertEqual(bundle.form_data.full_name, "Ana Perez")
        self.assertEqual(bundle.payload["schema_version"], 2)
        self.assertEqual(bundle.payload["metadata"]["source"], "structured_editor")
        self.assertNotEqual(bundle.payload["metadata"]["synced_from_legacy_at"], "")
        self.assertEqual(bundle.structured_columns["structured_schema_version"], 2)
        self.assertEqual(bundle.structured_columns["structured_payload_status"], "valid")
        self.assertEqual(json.loads(bundle.serialized_payload), bundle.payload)

    def test_rejects_invalid_payload_before_building_snapshot(self):
        with self.assertRaises(StructuredCVWriteError) as context:
            build_structured_cv_write_bundle(
                title="CV Titulo",
                payload={"schema_version": 2, "skills": ["broken"]},
                metadata_source="editor",
            )

        self.assertIn("skills_0_must_be_object", context.exception.errors)

    def test_rejects_snapshot_exceeding_legacy_limits_without_truncation(self):
        payload = {
            "schema_version": 2,
            "skills": [{"label": "s" * 120} for _ in range(15)],
        }

        with self.assertRaises(StructuredCVWriteError) as context:
            build_structured_cv_write_bundle(title="CV Titulo", payload=payload, metadata_source="editor")

        self.assertIn("skills", " ".join(context.exception.errors))

    def test_rejects_missing_title_and_full_name_like_legacy_flow(self):
        payload = {"schema_version": 2, "personal": {"full_name": ""}}

        with self.assertRaises(StructuredCVWriteError) as context:
            build_structured_cv_write_bundle(title="", payload=payload, metadata_source="editor")

        joined_errors = " ".join(context.exception.errors)
        self.assertIn("title", joined_errors)
        self.assertIn("full_name", joined_errors)


def _build_cv(*, structured_schema_version, structured_payload, structured_payload_status):
    return CV(
        id=1,
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


def _build_full_payload():
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


if __name__ == "__main__":
    unittest.main()
