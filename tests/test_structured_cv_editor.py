import json
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import get_connection, initialize_database
from app.main import app
from app.repositories import cv_repository
from app.schemas import CVFormData
from app.services.structured_cv_service import (
    MAX_STRUCTURED_PAYLOAD_BYTES,
    resolve_normalized_cv,
    serialize_structured_payload,
)
from app.services.structured_cv_editor_service import (
    parse_structured_editor_submission,
)


BOOTSTRAP_MARKER = '<script id="structured-editor-bootstrap" type="application/json">'


class StructuredEditorRoutesTest(unittest.TestCase):
    def test_new_structured_editor_page_renders_sections_and_bootstrap(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with TestClient(app) as client:
                    response = client.get("/cvs/new/structured")

                self.assertEqual(response.status_code, 200)
                self.assertIn("Crear CV estructurado", response.text)
                self.assertIn('action="http://testserver/cvs/new/structured"', response.text)
                self.assertIn("Datos personales y contacto", response.text)
                self.assertIn("Titulo profesional", response.text)
                self.assertIn("Resumen profesional", response.text)
                self.assertIn("Experiencia laboral", response.text)
                self.assertIn("Educacion", response.text)
                self.assertIn("Skills", response.text)
                self.assertIn("Certificaciones", response.text)
                self.assertIn("Idiomas", response.text)
                self.assertIn("Proyectos", response.text)
                self.assertIn("Informacion adicional", response.text)
                self.assertIn("Informacion interna", response.text)
                self.assertIn("Links de contacto", response.text)
                self.assertIn(BOOTSTRAP_MARKER, response.text)
                self.assertIn('name="structured_payload"', response.text)
                bootstrap = _extract_bootstrap(response.text)
                self.assertEqual(bootstrap["schema_version"], 2)
                self.assertEqual(bootstrap["experience"], [])
                self.assertEqual(bootstrap["metadata"]["source"], "")

    def test_create_structured_cv_route_persists_payload_and_provenance(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()

                with TestClient(app) as client:
                    response = _post_structured(client, "/cvs/new/structured", payload)

                self.assertEqual(response.status_code, 303)
                location = response.headers["location"]
                self.assertIn("message=CV+estructurado+creado+correctamente", location)
                cv_id = _cv_id_from_location(location)

                normalized = resolve_normalized_cv(cv_repository.get_cv(cv_id))
                self.assertTrue(normalized.is_structured)
                self.assertEqual(normalized.sections["personal"]["full_name"], "Ana Perez")
                self.assertEqual(normalized.sections["personal"]["headline"], "Tech Lead")
                self.assertEqual(normalized.sections["contact"]["email"], "ana@example.com")
                self.assertEqual(normalized.sections["skills"][0]["label"], "Python")
                self.assertEqual(normalized.sections["experience"][0]["company"], "Globex")
                self.assertEqual(normalized.sections["additional_info"][0]["title"], "Disponibilidad")
                self.assertEqual(normalized.sections["metadata"]["source"], "structured_editor")
                self.assertTrue(normalized.sections["metadata"]["synced_from_legacy_at"])

    def test_create_structured_cv_route_requires_title_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                count_before = len(cv_repository.list_cvs())

                with TestClient(app) as client:
                    response = _post_structured(client, "/cvs/new/structured", payload, title="")

                self.assertEqual(response.status_code, 422)
                self.assertIn("El titulo interno del CV es obligatorio", response.text)
                self.assertIn("No se pudo guardar el CV estructurado", response.text)
                bootstrap = _extract_bootstrap(response.text)
                self.assertEqual(bootstrap["personal"]["full_name"], "Ana Perez")
                self.assertEqual(bootstrap["experience"][0]["company"], "Globex")
                self.assertIn('value="Ana Perez"', response.text)
                self.assertEqual(len(cv_repository.list_cvs()), count_before)

    def test_create_structured_cv_route_rejects_invalid_json_with_spanish_error(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                count_before = len(cv_repository.list_cvs())

                with TestClient(app) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={"title": "CV Roto", "structured_payload": "{not-json"},
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("no es un JSON valido", response.text)
                self.assertEqual(len(cv_repository.list_cvs()), count_before)

    def test_create_structured_cv_route_rejects_missing_payload_field(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                count_before = len(cv_repository.list_cvs())

                with TestClient(app) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={"title": "CV Sin Payload", "structured_payload": ""},
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("JavaScript", response.text)
                self.assertEqual(len(cv_repository.list_cvs()), count_before)

    def test_create_structured_cv_route_rejects_oversized_payload_without_parsing(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                count_before = len(cv_repository.list_cvs())
                oversized_payload = "x" * (512 * 1024 + 1)

                with TestClient(app) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={"title": "CV Grande", "structured_payload": oversized_payload},
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("512 KB", response.text)
                self.assertEqual(len(cv_repository.list_cvs()), count_before)

    def test_create_structured_cv_route_rejects_future_schema_version_without_downcast(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                payload["schema_version"] = 3
                count_before = len(cv_repository.list_cvs())

                with TestClient(app) as client:
                    response = _post_structured(client, "/cvs/new/structured", payload)

                self.assertEqual(response.status_code, 422)
                self.assertIn("no es la version 2 esperada", response.text)
                self.assertEqual(len(cv_repository.list_cvs()), count_before)

    def test_create_structured_cv_route_surfaces_snapshot_limit_errors(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                payload["skills"] = [
                    {"label": "skill-" + "a" * 100, "category": "", "level": "", "order": index + 1}
                    for index in range(40)
                ]
                count_before = len(cv_repository.list_cvs())

                with TestClient(app) as client:
                    response = _post_structured(client, "/cvs/new/structured", payload)

                self.assertEqual(response.status_code, 422)
                self.assertIn("Skills", response.text)
                self.assertIn("Maximo 1200 caracteres", response.text)
                self.assertEqual(len(cv_repository.list_cvs()), count_before)

    def test_structured_edit_page_bootstraps_canonical_payload_with_unknown_keys(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                payload["experience"][0]["custom_note"] = "dato interno"
                payload["unknown_section"] = {"keep": True}
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=payload,
                    metadata_source="structured_test",
                )

                with TestClient(app) as client:
                    response = client.get(f"/cvs/{cv_id}/structured-edit")

                self.assertEqual(response.status_code, 200)
                self.assertIn("Editar CV estructurado", response.text)
                self.assertIn("Datos estructurados validos", response.text)
                self.assertNotIn("structured-warning", response.text)
                self.assertIn('action="http://testserver/cvs/%d/structured-edit"' % cv_id, response.text)
                bootstrap = _extract_bootstrap(response.text)
                self.assertEqual(bootstrap["personal"]["full_name"], "Ana Perez")
                self.assertEqual(bootstrap["experience"][0]["custom_note"], "dato interno")
                self.assertEqual(bootstrap["unknown_section"], {"keep": True})
                self.assertEqual(bootstrap["metadata"]["source"], "structured_test")

    def test_structured_edit_page_for_legacy_cv_warns_and_bootstraps_from_legacy(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_cv(_build_legacy_form_data())

                with TestClient(app) as client:
                    response = client.get(f"/cvs/{cv_id}/structured-edit")

                self.assertEqual(response.status_code, 200)
                self.assertIn("structured-warning", response.text)
                self.assertIn("no tiene datos estructurados", response.text)
                self.assertIn("campos planos", response.text)
                bootstrap = _extract_bootstrap(response.text)
                self.assertEqual(bootstrap["personal"]["full_name"], "Persona Legacy")
                self.assertEqual(bootstrap["contact"]["email"], "legacy@example.com")
                self.assertEqual(bootstrap["summary"], "Perfil legacy")
                self.assertEqual(bootstrap["experience"][0]["summary"], "Experiencia legacy")
                self.assertEqual(bootstrap["education"][0]["summary"], "Educacion legacy")
                self.assertEqual(bootstrap["skills"][0]["label"], "Python")

    def test_structured_edit_page_for_invalid_stale_and_future_payloads_falls_back_to_legacy(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                payload["personal"]["full_name"] = "Otro Nombre"
                serialized = serialize_structured_payload(payload)

                for version, status in ((2, "invalid"), (2, "stale"), (3, "valid")):
                    with self.subTest(status=status, version=version):
                        cv_id = cv_repository.create_structured_cv(
                            title="CV Base",
                            payload=_build_editor_payload(),
                            metadata_source="structured_test",
                        )
                        _set_structured_columns(
                            cv_id,
                            structured_schema_version=version,
                            structured_payload=serialized,
                            structured_payload_status=status,
                        )

                        with TestClient(app) as client:
                            response = client.get(f"/cvs/{cv_id}/structured-edit")

                        self.assertEqual(response.status_code, 200)
                        self.assertIn("structured-warning", response.text)
                        bootstrap = _extract_bootstrap(response.text)
                        self.assertEqual(bootstrap["personal"]["full_name"], "Ana Perez")
                        self.assertNotEqual(bootstrap["personal"]["full_name"], "Otro Nombre")

    def test_structured_update_route_persists_ordering_and_edited_content(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=payload,
                    metadata_source="structured_test",
                )
                reordered = _build_editor_payload()
                reordered["experience"] = [
                    dict(payload["experience"][1], order=1, summary="Desarrollo actualizado"),
                    dict(payload["experience"][0], order=2),
                ]
                reordered["skills"] = [dict(payload["skills"][1], order=1), dict(payload["skills"][0], order=2)]

                with TestClient(app) as client:
                    response = _post_structured(
                        client,
                        f"/cvs/{cv_id}/structured-edit",
                        reordered,
                        title="CV Estructurado",
                    )

                self.assertEqual(response.status_code, 303)
                self.assertIn("message=CV+estructurado+actualizado+correctamente", response.headers["location"])

                normalized = resolve_normalized_cv(cv_repository.get_cv(cv_id))
                self.assertTrue(normalized.is_structured)
                experience = normalized.sections["experience"]
                self.assertEqual(experience[0]["company"], "Acme")
                self.assertEqual(experience[0]["order"], 1)
                self.assertEqual(experience[0]["summary"], "Desarrollo actualizado")
                self.assertEqual(experience[1]["company"], "Globex")
                self.assertEqual(experience[1]["order"], 2)
                self.assertEqual(
                    [skill["label"] for skill in normalized.sections["skills"]],
                    ["SQL", "Python"],
                )

    def test_structured_update_preserves_unknown_keys_through_unchanged_edit(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                payload["experience"][0]["custom_note"] = "dato interno"
                payload["skills"][0]["internal_weight"] = 7
                payload["unknown_section"] = {"keep": True}
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=payload,
                    metadata_source="structured_test",
                )

                with TestClient(app) as client:
                    edit_page = client.get(f"/cvs/{cv_id}/structured-edit")
                    bootstrap = _extract_bootstrap(edit_page.text)
                    response = _post_structured(
                        client,
                        f"/cvs/{cv_id}/structured-edit",
                        bootstrap,
                        title="CV Estructurado",
                    )

                self.assertEqual(response.status_code, 303)
                normalized = resolve_normalized_cv(cv_repository.get_cv(cv_id))
                self.assertTrue(normalized.is_structured)
                self.assertEqual(normalized.sections["experience"][0]["custom_note"], "dato interno")
                self.assertEqual(normalized.sections["skills"][0]["internal_weight"], 7)
                self.assertEqual(normalized.sections["unknown_section"], {"keep": True})

    def test_structured_update_failed_validation_preserves_entered_data(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=payload,
                    metadata_source="structured_test",
                )
                submitted = _build_editor_payload()
                submitted["personal"]["full_name"] = "Nombre Ingresado"
                submitted["experience"][0]["company"] = "Empresa Ingresada"
                submitted["summary"] = "x" * 1300
                stored_before = resolve_normalized_cv(cv_repository.get_cv(cv_id)).sections

                with TestClient(app) as client:
                    response = _post_structured(
                        client,
                        f"/cvs/{cv_id}/structured-edit",
                        submitted,
                        title="CV Estructurado",
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("Resumen profesional", response.text)
                self.assertIn("Maximo 1200 caracteres", response.text)
                self.assertIn('value="Nombre Ingresado"', response.text)
                bootstrap = _extract_bootstrap(response.text)
                self.assertEqual(bootstrap["personal"]["full_name"], "Nombre Ingresado")
                self.assertEqual(bootstrap["experience"][0]["company"], "Empresa Ingresada")

                stored_after = resolve_normalized_cv(cv_repository.get_cv(cv_id)).sections
                self.assertEqual(stored_after, stored_before)

    def test_structured_update_converts_legacy_cv_on_save(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_cv(_build_legacy_form_data())
                payload = _build_editor_payload()

                with TestClient(app) as client:
                    response = _post_structured(
                        client,
                        f"/cvs/{cv_id}/structured-edit",
                        payload,
                        title="CV Convertido",
                    )

                self.assertEqual(response.status_code, 303)
                normalized = resolve_normalized_cv(cv_repository.get_cv(cv_id))
                self.assertTrue(normalized.is_structured)
                self.assertEqual(normalized.title, "CV Convertido")
                self.assertEqual(normalized.sections["personal"]["full_name"], "Ana Perez")
                self.assertEqual(normalized.sections["metadata"]["source"], "structured_editor")
                self.assertTrue(normalized.sections["metadata"]["synced_from_legacy_at"])

    def test_structured_update_returns_404_for_missing_cv(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with TestClient(app) as client:
                    response = _post_structured(
                        client,
                        "/cvs/999/structured-edit",
                        _build_editor_payload(),
                        title="CV Inexistente",
                    )

                self.assertEqual(response.status_code, 404)

    def test_structured_edit_page_is_escaped_against_xss(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()
                payload["personal"]["full_name"] = '<script>alert("xss")</script>'
                payload["experience"][0]["company"] = '<img src=x onerror="window.__xss=1">'
                cv_id = cv_repository.create_structured_cv(
                    title="CV XSS",
                    payload=payload,
                    metadata_source="structured_test",
                )

                with TestClient(app) as client:
                    response = client.get(f"/cvs/{cv_id}/structured-edit")

                self.assertEqual(response.status_code, 200)
                self.assertNotIn('<script>alert("xss")</script>', response.text)
                self.assertNotIn('<img src=x onerror=', response.text)
                self.assertIn("\\u003cscript\\u003ealert", response.text)
                self.assertIn("<script>", response.text)

    def test_structured_editor_create_then_json_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_editor_payload()

                with TestClient(app) as client:
                    create_response = _post_structured(client, "/cvs/new/structured", payload)
                    cv_id = _cv_id_from_location(create_response.headers["location"])
                    export_response = client.get(f"/cvs/{cv_id}/export/json")
                    import_response = client.post(
                        "/cvs/import/json",
                        files={"json_file": ("cv.json", export_response.content, "application/json")},
                        follow_redirects=False,
                    )

                self.assertEqual(export_response.status_code, 200)
                exported = json.loads(export_response.content)
                self.assertEqual(exported["schema_version"], 2)
                self.assertEqual(import_response.status_code, 303)
                imported_id = _cv_id_from_location(import_response.headers["location"])
                self.assertNotEqual(imported_id, cv_id)

                imported = resolve_normalized_cv(cv_repository.get_cv(imported_id))
                self.assertTrue(imported.is_structured)
                self.assertEqual(imported.sections["personal"]["headline"], "Tech Lead")
                self.assertEqual(imported.sections["certifications"][0]["name"], "AWS SA")
                self.assertEqual(imported.sections["metadata"]["source"], "json_import")

    def test_legacy_routes_stay_compatible_and_new_routes_are_not_shadowed(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with TestClient(app) as client:
                    legacy_new = client.get("/cvs/new")
                    legacy_create = client.post(
                        "/cvs/",
                        data={
                            "title": "CV Legacy",
                            "full_name": "Persona Legacy",
                            "email": "legacy@example.com",
                            "phone": "",
                            "professional_summary": "Perfil",
                            "experience_summary": "Experiencia",
                            "education_summary": "Educacion",
                            "skills": "Python",
                        },
                        follow_redirects=False,
                    )
                    cv_id = _cv_id_from_location(legacy_create.headers["location"])
                    legacy_detail = client.get(f"/cvs/{cv_id}")
                    legacy_edit = client.get(f"/cvs/{cv_id}/edit")
                    structured_new = client.get("/cvs/new/structured")
                    structured_edit = client.get(f"/cvs/{cv_id}/structured-edit")

                self.assertEqual(legacy_new.status_code, 200)
                self.assertIn("Crear CV", legacy_new.text)
                self.assertEqual(legacy_create.status_code, 303)
                self.assertEqual(legacy_detail.status_code, 200)
                self.assertEqual(legacy_edit.status_code, 200)
                self.assertEqual(structured_new.status_code, 200)
                self.assertEqual(structured_edit.status_code, 200)
                self.assertIn("structured-warning", structured_edit.text)

    def test_detail_and_index_link_to_structured_editor(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_cv(_build_legacy_form_data())

                with TestClient(app) as client:
                    index_response = client.get("/cvs/")
                    detail_response = client.get(f"/cvs/{cv_id}")

                self.assertEqual(index_response.status_code, 200)
                self.assertIn("Crear CV estructurado", index_response.text)
                self.assertIn('href="http://testserver/cvs/new/structured"', index_response.text)
                self.assertEqual(detail_response.status_code, 200)
                self.assertIn("Editar estructurado", detail_response.text)
                self.assertIn(
                    'href="http://testserver/cvs/%d/structured-edit"' % cv_id,
                    detail_response.text,
                )

    def test_legacy_conversion_warning_mentions_section_limits(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_cv(_build_legacy_form_data())

                with TestClient(app) as client:
                    response = client.get(f"/cvs/{cv_id}/structured-edit")

                self.assertEqual(response.status_code, 200)
                self.assertIn("se convierte en estructurado", response.text)
                self.assertIn("limites", response.text)


class NonFiniteStructuredSubmissionTest(unittest.TestCase):
    """El editor nunca debe aceptar ni reemitir JSON no estandar."""

    def test_submission_with_non_finite_numbers_is_rejected_with_a_controlled_error(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            templates = (
                '{"schema_version": 2, "personal": {"full_name": "Ana"}, "custom_extension": {"score": %s}}',
                '{"schema_version": 2, "personal": {"full_name": "Ana"}, "score": %s}',
            )
            for template in templates:
                raw_payload = template % token
                with self.subTest(token=token, raw_payload=raw_payload):
                    payload, errors = parse_structured_editor_submission(raw_payload)

                    self.assertIsNone(payload)
                    self.assertEqual(len(errors), 1)
                    self.assertIn("no es un JSON valido", errors[0])

    def test_valid_extension_values_are_still_accepted(self):
        raw_payload = '{"schema_version": 2, "personal": {"full_name": "Ana"}, "custom_extension": {"score": 4.5}}'

        payload, errors = parse_structured_editor_submission(raw_payload)

        self.assertEqual(errors, [])
        self.assertEqual(payload["custom_extension"], {"score": 4.5})

    def test_route_rejects_non_finite_submission_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                raw_payload = '{"schema_version": 2, "personal": {"full_name": "Ana"}, "custom_extension": {"score": NaN}}'

                with TestClient(app) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={"title": "CV No Finito", "structured_payload": raw_payload},
                        follow_redirects=False,
                    )

                self.assertIn(response.status_code, (200, 303, 422))
                self.assertIn("no es un JSON valido", response.text)
                self.assertEqual(cv_repository.list_cvs(), [])


class LegacyEditOnStructuredCVTest(unittest.TestCase):
    """El formulario plano no puede pisar datos que solo viven en el payload v2."""

    def test_legacy_edit_get_for_structured_cv_redirects_to_structured_editor(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_schema2_only_payload(),
                    metadata_source="structured_test",
                )

                with TestClient(app) as client:
                    response = client.get(f"/cvs/{cv_id}/edit", follow_redirects=False)

                self.assertEqual(response.status_code, 303)
                self.assertIn(f"/cvs/{cv_id}/structured-edit", response.headers["location"])
                self.assertIn("message=", response.headers["location"])

                followed = client.get(response.headers["location"])

                self.assertEqual(followed.status_code, 200)
                self.assertIn("no se puede editar con el formulario plano", followed.text)
                self.assertIn("Datos estructurados validos", followed.text)

    def test_legacy_update_post_for_structured_cv_keeps_payload_and_never_writes(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_schema2_only_payload(),
                    metadata_source="structured_test",
                )
                stored_before = cv_repository.get_cv(cv_id)
                sections_before = resolve_normalized_cv(stored_before).sections

                with TestClient(app) as client:
                    response = client.post(
                        f"/cvs/{cv_id}/edit",
                        data=_legacy_form_fields(title="CV Pisado", skills="Rust"),
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 303)
                self.assertIn(f"/cvs/{cv_id}?", response.headers["location"])
                self.assertIn("message=", response.headers["location"])

                stored_after = cv_repository.get_cv(cv_id)
                self.assertEqual(stored_after.title, "CV Estructurado")
                self.assertEqual(stored_after.skills, "Python")
                self.assertEqual(stored_after.structured_payload, stored_before.structured_payload)
                self.assertEqual(resolve_normalized_cv(stored_after).sections, sections_before)

    def test_legacy_update_post_with_invalid_fields_never_renders_legacy_form(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_schema2_only_payload(),
                    metadata_source="structured_test",
                )
                stored_before = cv_repository.get_cv(cv_id)

                with TestClient(app) as client:
                    response = client.post(
                        f"/cvs/{cv_id}/edit",
                        data=_legacy_form_fields(title="", full_name="Sin titulo"),
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 303)
                self.assertEqual(cv_repository.get_cv(cv_id).structured_payload, stored_before.structured_payload)

    def test_structured_editor_still_works_after_blocked_legacy_update(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_schema2_only_payload(),
                    metadata_source="structured_test",
                )

                with TestClient(app) as client:
                    client.post(
                        f"/cvs/{cv_id}/edit",
                        data=_legacy_form_fields(title="CV Pisado"),
                        follow_redirects=False,
                    )
                    edited = _build_schema2_only_payload()
                    edited["personal"]["headline"] = "Headline Editado"
                    edited["certifications"][0]["name"] = "Azure Solutions Architect"
                    response = _post_structured(
                        client,
                        f"/cvs/{cv_id}/structured-edit",
                        edited,
                        title="CV Estructurado",
                    )

                self.assertEqual(response.status_code, 303)
                normalized = resolve_normalized_cv(cv_repository.get_cv(cv_id))
                self.assertTrue(normalized.is_structured)
                self.assertEqual(normalized.sections["personal"]["headline"], "Headline Editado")
                self.assertEqual(
                    normalized.sections["certifications"][0]["name"],
                    "Azure Solutions Architect",
                )
                self.assertEqual(normalized.sections["projects"][0]["name"], "Motor de reportes")
                self.assertEqual(normalized.sections["metadata"]["source"], "structured_editor")

    def test_legacy_cv_is_still_edited_through_the_legacy_path(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_cv(_build_legacy_form_data())

                with TestClient(app) as client:
                    edit_page = client.get(f"/cvs/{cv_id}/edit")
                    response = client.post(
                        f"/cvs/{cv_id}/edit",
                        data=_legacy_form_fields(
                            title="CV Legacy Editado",
                            full_name="Persona Renombrada",
                            skills="Python, SQL",
                        ),
                        follow_redirects=False,
                    )

                self.assertEqual(edit_page.status_code, 200)
                self.assertIn("Editar CV", edit_page.text)
                self.assertEqual(response.status_code, 303)
                self.assertIn("message=CV+actualizado+correctamente", response.headers["location"])

                stored = cv_repository.get_cv(cv_id)
                self.assertEqual(stored.title, "CV Legacy Editado")
                self.assertEqual(stored.full_name, "Persona Renombrada")
                self.assertEqual(stored.skills, "Python, SQL")
                self.assertEqual(stored.structured_payload_status, "legacy")

    def test_json_import_still_creates_new_cvs_with_the_legacy_guard_in_place(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                source_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_schema2_only_payload(),
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
                imported_id = _cv_id_from_location(import_response.headers["location"])
                self.assertNotEqual(imported_id, source_id)

                imported = resolve_normalized_cv(cv_repository.get_cv(imported_id))
                self.assertTrue(imported.is_structured)
                self.assertEqual(imported.sections["personal"]["headline"], "Arquitecto de Software")
                self.assertEqual(imported.sections["certifications"][0]["name"], "AWS Solutions Architect")
                self.assertEqual(resolve_normalized_cv(cv_repository.get_cv(source_id)).sections["personal"]["headline"], "Arquitecto de Software")


class MalformedStructuredSubmissionTest(unittest.TestCase):
    """Un payload con forma invalida se responde con 422, nunca con 500."""

    def test_non_object_personal_section_returns_controlled_error(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()

                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={
                            "title": "CV Roto",
                            "structured_payload": json.dumps(
                                _build_schema2_only_payload() | {"personal": "x"},
                                ensure_ascii=False,
                            ),
                        },
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("No se pudo guardar el CV estructurado", response.text)
                self.assertIn("personal", response.text)

    def test_non_list_contact_links_returns_controlled_error(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_schema2_only_payload()
                payload["contact"] = {"email": "struct@example.com", "phone": "", "links": 5}

                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={
                            "title": "CV Roto",
                            "structured_payload": json.dumps(payload, ensure_ascii=False),
                        },
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("links", response.text)

    def test_non_object_metadata_returns_controlled_error(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                cv_id = cv_repository.create_structured_cv(
                    title="CV Estructurado",
                    payload=_build_schema2_only_payload(),
                    metadata_source="structured_test",
                )
                stored_before = cv_repository.get_cv(cv_id)
                payload = _build_schema2_only_payload()
                payload["metadata"] = "no-objeto"
                payload["personal"]["full_name"] = "Nombre Ingresado"

                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.post(
                        f"/cvs/{cv_id}/structured-edit",
                        data={
                            "title": "CV Estructurado",
                            "structured_payload": json.dumps(payload, ensure_ascii=False),
                        },
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("metadata", response.text)
                self.assertIn('value="Nombre Ingresado"', response.text)
                self.assertEqual(
                    cv_repository.get_cv(cv_id).structured_payload,
                    stored_before.structured_payload,
                )

    def test_non_object_item_section_returns_controlled_error(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                payload = _build_schema2_only_payload()
                payload["skills"] = {"label": "Python"}

                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={
                            "title": "CV Roto",
                            "structured_payload": json.dumps(payload, ensure_ascii=False),
                        },
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("skills", response.text)

    def test_structured_payload_exceeding_limit_after_normalization_is_controlled(self):
        with tempfile.TemporaryDirectory() as data_directory:
            with patch.dict(os.environ, {"APP_DATA_DIR": data_directory}):
                initialize_database()
                count_before = len(cv_repository.list_cvs())
                payload = _build_payload_with_exact_raw_size(MAX_STRUCTURED_PAYLOAD_BYTES)

                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.post(
                        "/cvs/new/structured",
                        data={
                            "title": "CV Grande",
                            "structured_payload": json.dumps(payload, ensure_ascii=False),
                        },
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 422)
                self.assertIn("512 KB", response.text)
                self.assertEqual(len(cv_repository.list_cvs()), count_before)


def _legacy_form_fields(**overrides) -> dict[str, str]:
    fields = {
        "title": "CV Legacy Editado",
        "full_name": "Persona Legacy",
        "email": "legacy@example.com",
        "phone": "",
        "professional_summary": "Perfil",
        "experience_summary": "Experiencia",
        "education_summary": "Educacion",
        "skills": "Python",
    }
    fields.update(overrides)
    return fields


def _build_schema2_only_payload() -> dict:
    return {
        "schema_version": 2,
        "personal": {
            "full_name": "Ana Perez",
            "headline": "Arquitecto de Software",
            "location": "Cordoba",
        },
        "contact": {
            "email": "ana@example.com",
            "phone": "+54 11 1234 5678",
            "links": ["https://cv.example.com"],
        },
        "summary": "Perfil estructurado",
        "skills": [{"label": "Python", "category": "Backend", "level": "Avanzado", "order": 1}],
        "experience": [
            {
                "company": "Globex",
                "role": "Lider Tecnico",
                "location": "Remoto",
                "start_date": "2022",
                "end_date": "",
                "current": True,
                "summary": "Liderazgo de plataforma",
                "highlights": [],
                "technologies": ["Python"],
                "order": 1,
            }
        ],
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
        "additional_info": [{"title": "Disponibilidad", "content": "Remoto full-time", "order": 1}],
        "metadata": {
            "source": "structured_test",
            "synced_from_legacy_at": "2020-01-01T00:00:00+00:00",
        },
    }


def _build_payload_with_exact_raw_size(target_bytes: int) -> dict:
    """Ajusta un payload valido hasta que el JSON crudo ocupe `target_bytes`.

    Se omiten secciones para que la normalizacion agregue sus defaults, asi el
    JSON enviado entra justo en el limite pero su serializacion normalizada lo
    excede.
    """
    payload = _build_schema2_only_payload()
    for section in (
        "summary",
        "skills",
        "education",
        "certifications",
        "languages",
        "projects",
        "links",
        "additional_info",
        "metadata",
    ):
        payload.pop(section, None)
    pad = 0
    for _ in range(10):
        candidate = dict(payload)
        candidate["_pad"] = "x" * pad
        current = len(json.dumps(candidate, ensure_ascii=False).encode("utf-8"))
        if current == target_bytes:
            return candidate
        pad += target_bytes - current
    raise AssertionError("No se pudo ajustar el tamano del payload")


def _post_structured(client, url, payload, title="CV Estructurado"):
    return client.post(
        url,
        data={
            "title": title,
            "structured_payload": json.dumps(payload, ensure_ascii=False),
        },
        follow_redirects=False,
    )


def _extract_bootstrap(html):
    start = html.index(BOOTSTRAP_MARKER) + len(BOOTSTRAP_MARKER)
    end = html.index("</script>", start)
    return json.loads(html[start:end])


def _cv_id_from_location(location):
    path = location.split("?")[0]
    return int(path.rstrip("/").split("/")[-1])


def _set_structured_columns(cv_id, *, structured_schema_version, structured_payload, structured_payload_status):
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE cvs
            SET structured_schema_version = ?,
                structured_payload = ?,
                structured_payload_status = ?
            WHERE id = ?
            """,
            (
                structured_schema_version,
                structured_payload,
                structured_payload_status,
                cv_id,
            ),
        )
        connection.commit()


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


def _build_editor_payload() -> dict:
    return {
        "schema_version": 2,
        "personal": {
            "full_name": "Ana Perez",
            "headline": "Tech Lead",
            "location": "Buenos Aires",
        },
        "contact": {
            "email": "ana@example.com",
            "phone": "+54 11 1234 5678",
            "links": ["https://ana.example.com"],
        },
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
                "order": 1,
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
                "order": 2,
            },
        ],
        "education": [
            {
                "institution": "UNLP",
                "degree": "Ing. en Sistemas",
                "field": "Software",
                "start_date": "2014",
                "end_date": "2019",
                "summary": "Titulo de grado",
                "order": 1,
            }
        ],
        "certifications": [
            {"name": "AWS SA", "issuer": "Amazon", "date": "2023", "order": 1}
        ],
        "languages": [
            {"name": "Espanol", "level": "Nativo", "order": 1},
            {"name": "Ingles", "level": "Avanzado", "order": 2},
        ],
        "projects": [
            {
                "name": "Plataforma interna",
                "summary": "Automatizacion de reportes",
                "link": "https://git.example.com/repo",
                "technologies": ["Python"],
                "order": 1,
            }
        ],
        "links": [
            {"label": "Web personal", "url": "https://ana.example.com", "order": 1}
        ],
        "additional_info": [
            {"title": "Disponibilidad", "content": "Remoto full-time", "order": 1}
        ],
        "metadata": {
            "source": "structured_test",
            "synced_from_legacy_at": "2026-01-01T00:00:00+00:00",
        },
    }


if __name__ == "__main__":
    unittest.main()
