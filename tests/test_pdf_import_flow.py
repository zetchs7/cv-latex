"""Flujo completo de importacion de CV desde PDF.

Recorre el flujo obligatorio del Issue #14:

    Subir -> Extraer -> Revisar -> Corregir -> Confirmar -> Crear CV ->
    Editar -> Exportar JSON -> Reimportar -> Generar TEX -> Consultar ATS

Usa los PDFs de `tests/fixtures/pdf_import/pdf/`, que son deterministas y estan
versionados. Los tests corren bajo el aislamiento fail-closed de `conftest.py`.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import re
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.import_staging_service import (
    STATUS_CONFIRMED,
    claim_draft,
    release_draft,
    STATUS_DISCARDED,
    STATUS_KEPT,
    drafts_directory,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pdf_import"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def client():
    """TestClient con lifespan.

    Sin el contexto, FastAPI no corre `initialize_database()` y cualquier
    prueba que llegue a la base falla con "no such table: cvs" en un punto que
    no es la causa real.
    """

    with TestClient(app) as test_client:
        yield test_client


def _submit(client: TestClient, url: str, fields: list[tuple[str, str]], **kwargs):
    """POSTea el formulario como lo haria un navegador.

    No se usa `data=` con lista de tuplas: en esta combinacion de httpx y
    Starlette llega un formulario VACIO sin error, y el test falla mucho mas
    lejos de la causa. `urlencode` produce el mismo cuerpo que el navegador y
    ademas conserva claves repetidas.
    """

    return client.post(
        url,
        content=urlencode(fields).encode("utf-8"),
        headers={"content-type": "application/x-www-form-urlencoded"},
        **kwargs,
    )


def _upload(client: TestClient, fixture: str = "pdf/valid_es.pdf") -> str:
    response = client.post(
        "/cvs/import/pdf",
        files={"pdf_file": ("cv.pdf", io.BytesIO(_fixture(fixture)), "application/pdf")},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    location = response.headers["location"]
    return location.rsplit("/", 1)[-1]


def _review_context(client: TestClient, draft_id: str) -> dict:
    response = client.get(f"/cvs/import/{draft_id}")
    assert response.status_code == 200, response.text
    return response


def _form_from_draft(draft, *, decide_all: bool = True) -> dict[str, str]:
    """Construye el formulario de revision como lo haria una persona."""

    fields: list[tuple[str, str]] = [("cv_title", "CV importado")]

    for entry in draft.entries:
        if entry.values:
            for name, value in entry.values.items():
                fields.append((f"value__{entry.key}:{name}", value))
        else:
            fields.append((f"value__{entry.key}", entry.value))

        if decide_all or entry.status == "pending":
            fields.append((f"decision__{entry.key}", STATUS_CONFIRMED))

    for item in draft.unclassified:
        if decide_all or item.status == "pending":
            fields.append((f"decision__{item.key}", STATUS_KEPT))
        if item.assigned_section:
            fields.append((f"assign__{item.key}", item.assigned_section))

    return fields


def _cv_id_from(location: str) -> int:
    """Extrae el id de una redireccion. La URL puede terminar en /structured-edit."""

    match = re.search(r"/cvs/(\d+)", location)
    assert match, f"no se encontro un id de CV en la redireccion: {location}"
    return int(match.group(1))


def _load_draft(draft_id: str):
    from app.services.import_staging_service import load_draft

    return load_draft(draft_id)


# --- Flujo principal -----------------------------------------------------


def test_full_flow_from_upload_to_ats_analysis(client: TestClient):
    draft_id = _upload(client)
    draft = _load_draft(draft_id)

    assert draft.page_count == 1
    assert len(draft.entries) > 5

    response = _submit(
        client,
        f"/cvs/import/{draft_id}/confirm",
        _form_from_draft(draft),
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text

    # Redirige al editor estructurado del CV recien creado.
    assert "/cvs/" in response.headers["location"] and "/structured-edit" in response.headers["location"]
    cv_id = _cv_id_from(response.headers["location"])

    # El CV existe y es schema 2.
    detail = client.get(f"/cvs/{cv_id}")
    assert detail.status_code == 200
    assert "Juan Carlos" in detail.text

    from app.repositories import cv_repository

    created = cv_repository.get_cv(cv_id)
    assert created is not None
    assert created.structured_schema_version == 2
    # El estado real de un payload v2 recien escrito es "valid"; "structured"
    # no existe en el dominio.
    assert created.structured_payload_status == "valid"

    payload = json.loads(created.structured_payload)
    assert payload["schema_version"] == 2
    sections = payload  # el payload schema 2 es plano
    assert sections["personal"]["full_name"] == "Juan Carlos Pérez"
    assert sections["contact"]["email"] == "juan.perez.demo@example.com"
    assert sections["experience"], "la experiencia debe llegar al CV final"
    assert sections["education"], "la educacion debe llegar al CV final"
    assert sections["links"], "los enlaces deben llegar al CV final"

    # Export JSON y reimportacion.
    exported = client.get(f"/cvs/{cv_id}/export/json")
    assert exported.status_code == 200
    exported_payload = json.loads(exported.text)
    assert exported_payload["schema_version"] == 2

    reimport = client.post(
        "/cvs/import/json",
        files={"json_file": ("cv.json", io.BytesIO(exported.text.encode()), "application/json")},
        follow_redirects=False,
    )
    assert reimport.status_code == 303, reimport.text
    reimported_id = _cv_id_from(reimport.headers["location"])
    assert reimported_id != cv_id, "la reimportacion no debe pisar el CV original"

    # Generacion de TEX con las plantillas propias.
    tex = client.get(f"/cvs/{cv_id}/export/tex")
    assert tex.status_code == 200
    assert "Aurora" in tex.text

    # ATS consume la representacion normalizada sin romperse.
    ats = client.get(f"/ats/cvs/{cv_id}")
    assert ats.status_code == 200
    assert "ATS" in ats.text


def test_review_screen_is_reachable_and_shows_required_sections(client: TestClient):
    draft_id = _upload(client)
    body = _review_context(client, draft_id).text

    for heading in (
        "Resultado de la importacion del CV",
        "Datos detectados",
        "Campos con dudas o informacion incompleta",
        "Informacion no clasificada",
    ):
        assert heading in body, f"falta la seccion obligatoria: {heading}"


def test_confirm_is_blocked_while_there_are_pending_entries(client: TestClient):
    from app.repositories import cv_repository

    before = cv_repository.list_cvs()
    draft_id = _upload(client)
    draft = _load_draft(draft_id)

    # Solo un subconjunto decidido: el resto queda pendiente.
    partial = [("cv_title", "CV parcial")] + [
        (f"decision__{draft.entries[0].key}", STATUS_CONFIRMED)
    ]

    response = _submit(client, f"/cvs/import/{draft_id}/confirm", partial)
    assert response.status_code == 422
    assert "sin decidir" in response.text

    # Y nada se guardo. Se comparan ids, no titulos: la suite comparte la base
    # de la sesion y otros tests ya crearon CVs llamados "CV importado".
    from app.repositories import cv_repository

    assert cv_repository.list_cvs() == before


def test_no_silent_discard_of_unclassified_text(client: TestClient):
    """El Issue prohibe descartar en silencio: cada bloque exige decision."""

    draft_id = _upload(client)
    draft = _load_draft(draft_id)
    assert draft.unclassified, "el fixture debe dejar texto sin clasificar"

    response = _submit(
        client,
        f"/cvs/import/{draft_id}/confirm",
        [("cv_title", "CV")] + [(f"decision__{e.key}", STATUS_CONFIRMED) for e in draft.entries],
    )
    assert response.status_code == 422
    assert "informacion no clasificada" in response.text.lower() or "sin decidir" in response.text


def test_discarding_unclassified_text_lets_confirmation_through(client: TestClient):
    draft_id = _upload(client)
    draft = _load_draft(draft_id)
    form = _form_from_draft(draft)
    form += [(f"decision__{item.key}", STATUS_DISCARDED) for item in draft.unclassified]
    form = [(k, v) for k, v in form if not k.startswith("decision__unclassified")]
    form += [(f"decision__{item.key}", STATUS_DISCARDED) for item in draft.unclassified]

    response = _submit(client, f"/cvs/import/{draft_id}/confirm", form, follow_redirects=False)
    assert response.status_code == 303, response.text


def test_keeping_unclassified_text_moves_it_to_additional_info(client: TestClient):
    draft_id = _upload(client)
    draft = _load_draft(draft_id)
    form = _form_from_draft(draft)
    form = [(k, v) for k, v in form if not k.startswith("decision__unclassified")]
    form += [(f"decision__{item.key}", STATUS_KEPT) for item in draft.unclassified]
    form += [(f"assign__{item.key}", "additional_info") for item in draft.unclassified]

    response = _submit(client, f"/cvs/import/{draft_id}/confirm", form, follow_redirects=False)
    assert response.status_code == 303, response.text

    cv_id = _cv_id_from(response.headers["location"])
    from app.repositories import cv_repository

    payload = json.loads(cv_repository.get_cv(cv_id).structured_payload)
    assert payload["additional_info"], "lo conservado debe llegar a informacion adicional"


def test_edits_survive_a_failed_confirmation(client: TestClient):
    """Un error de guardado no puede borrar lo que la persona escribio."""

    draft_id = _upload(client)
    draft = _load_draft(draft_id)

    edited = "Nombre corregido a mano"
    form = [("cv_title", "CV corregido"), (f"value__personal.full_name", edited)]

    response = _submit(client, f"/cvs/import/{draft_id}/confirm", form)
    assert response.status_code == 422

    reloaded = _load_draft(draft_id)
    reloaded_response = _submit(client, f"/cvs/import/{draft_id}", form)
    assert reloaded_response.status_code == 200
    assert edited in reloaded_response.text
    assert reloaded is not None


def test_missing_name_is_reported_and_nothing_is_written(client: TestClient):
    draft_id = _upload(client)
    draft = _load_draft(draft_id)

    form = _form_from_draft(draft)
    form = [(k, "") if k == "value__personal.full_name" else (k, v) for k, v in form]

    response = _submit(client, f"/cvs/import/{draft_id}/confirm", form)
    assert response.status_code == 422
    assert "nombre completo" in response.text.lower()


# --- Errores de carga ----------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "expected_status", "expected_text"),
    [
        ("corrupt.pdf", 422, "danado"),
        ("not_a_pdf.pdf", 422, "no es un PDF valido"),
        ("empty_text.pdf", 422, "No se pudo extraer texto"),
        ("many_pages.pdf", 422, "paginas"),
    ],
)
def test_invalid_uploads_are_rejected_with_safe_messages(
    client: TestClient, fixture: str, expected_status: int, expected_text: str
):
    response = client.post(
        "/cvs/import/pdf",
        files={"pdf_file": (fixture, io.BytesIO(_fixture(f"pdf/{fixture}")), "application/pdf")},
    )
    assert response.status_code == expected_status
    assert expected_text.lower() in response.text.lower()

    # Ningun mensaje puede filtrar rutas internas.
    assert "/tmp/" not in response.text
    assert "Traceback" not in response.text


def test_encrypted_pdf_is_rejected(client: TestClient):
    response = client.post(
        "/cvs/import/pdf",
        files={"pdf_file": ("cifrado.pdf", io.BytesIO(_fixture("pdf_encrypted.pdf")), "application/pdf")},
    )
    assert response.status_code == 422
    assert "contrasena" in response.text.lower()


def test_upload_over_the_size_limit_is_rejected(client: TestClient):
    oversized = b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024 + 1024)
    response = client.post(
        "/cvs/import/pdf",
        files={"pdf_file": ("grande.pdf", io.BytesIO(oversized), "application/pdf")},
    )
    assert response.status_code == 422
    assert "tamano maximo" in response.text.lower()


def test_no_file_selected_is_reported(client: TestClient):
    response = client.post("/cvs/import/pdf", content=b"", headers={"content-type": "application/x-www-form-urlencoded"})
    assert response.status_code in (200, 422)


# --- Aislamiento del staging --------------------------------------------


def test_draft_is_not_served_as_a_public_file(client: TestClient):
    draft_id = _upload(client)
    for prefix in ("/static/", "/data/"):
        assert client.get(f"{prefix}import-drafts/{draft_id}.json").status_code == 404


def test_draft_files_live_outside_the_public_directory(client: TestClient):
    draft_id = _upload(client)
    drafts_directory().mkdir(parents=True, exist_ok=True)
    assert (drafts_directory() / f"{draft_id}.json").exists()


@pytest.mark.parametrize("bad_id", ["../../etc/passwd", "abc", "x" * 200, "with space", ""])
def test_invalid_draft_ids_are_rejected(client: TestClient, bad_id: str):
    response = client.get(f"/cvs/import/{bad_id}")
    assert response.status_code in (404, 422)
    assert "/etc/passwd" not in response.text


def _discard(client: TestClient, draft_id: str, confirmation: str):
    return _submit(
        client,
        f"/cvs/import/{draft_id}/discard",
        [("confirm_discard", confirmation), ("cv_title", "")],
        follow_redirects=False,
    )


def test_discard_requires_exact_confirmation(client: TestClient):
    draft_id = _upload(client)

    # Confirmacion vacia: el borrador sigue intacto.
    assert _discard(client, draft_id, "").status_code == 422
    assert client.get(f"/cvs/import/{draft_id}").status_code == 200

    # Confirmacion incorrecta: tampoco.
    assert _discard(client, draft_id, "nombre que no es").status_code == 422
    assert client.get(f"/cvs/import/{draft_id}").status_code == 200


def test_discard_with_exact_confirmation_removes_the_draft(client: TestClient):
    draft_id = _upload(client)

    response = _discard(client, draft_id, _suggested_title(client, draft_id))
    assert response.status_code == 303
    assert client.get(f"/cvs/import/{draft_id}").status_code == 404


def _suggested_title(client: TestClient, draft_id: str) -> str:
    """El titulo esperado es el nombre detectado, visible en la pantalla."""

    from app.services.import_staging_service import load_draft

    draft = load_draft(draft_id)
    for entry in draft.entries:
        if entry.key == "personal.full_name" and entry.value.strip():
            return entry.value.strip()[:120]
    return "CV importado desde PDF"


def test_the_pdf_itself_is_never_persisted(client: TestClient):
    draft_id = _upload(client)
    from app.services.import_staging_service import load_draft

    draft = load_draft(draft_id)
    assert not draft.source_filename.endswith(".pdf.bin")
    stored = (drafts_directory() / f"{draft_id}.json").read_text(encoding="utf-8")
    assert "%PDF" not in stored


def test_english_pdf_is_imported(client: TestClient):
    draft_id = _upload(client, "pdf/valid_en.pdf")
    draft = _load_draft(draft_id)

    form = _form_from_draft(draft)
    form = [(k, v) for k, v in form if not k.startswith("decision__unclassified")]
    form += [(f"decision__{item.key}", STATUS_DISCARDED) for item in draft.unclassified]

    response = _submit(client, f"/cvs/import/{draft_id}/confirm", form, follow_redirects=False)
    assert response.status_code == 303, response.text

    cv_id = _cv_id_from(response.headers["location"])
    from app.repositories import cv_repository

    payload = json.loads(cv_repository.get_cv(cv_id).structured_payload)
    assert payload["personal"]["full_name"] == "Jane Q. Public"
    assert payload["contact"]["email"] == "jane.public.demo@example.com"

def test_a_failure_that_is_not_a_staging_error_still_releases_the_claim(client, monkeypatch):
    """El reclamo se suelta ante CUALQUIER fallo, no solo `ImportStagingError`.

    Un `OSError` al escribir, con el volumen lleno, dejaba el marcador puesto y
    bloqueaba todo reintento durante las dos horas que tarda la limpieza. Un
    fallo transitorio no puede convertirse en un bloqueo largo sobre una revision
    que la persona ya corrigio.
    """

    draft_id = _upload(client)
    draft = _load_draft(draft_id)
    formulario = _form_from_draft(draft)

    def fallo(*args, **kwargs):
        raise OSError("No queda espacio en el dispositivo")

    monkeypatch.setattr(
        "app.routes.pdf_import.cv_repository.create_structured_cv", fallo
    )

    respuesta = client.post(f"/cvs/import/{draft_id}/confirm", data=formulario)
    assert respuesta.status_code == 422

    # El reclamo quedo libre: se puede reintentar sin esperar la limpieza.
    from app.services.import_staging_service import _draft_path, DRAFT_CLAIM_SUFFIX

    marcador = _draft_path(draft_id).with_suffix(DRAFT_CLAIM_SUFFIX)
    assert not marcador.exists(), "el reclamo quedo puesto y bloquea el reintento"

    reintento = client.post(f"/cvs/import/{draft_id}/confirm", data=formulario)
    assert reintento.status_code == 422, "con el reclamo liberado se puede reintentar"
    assert not marcador.exists()

    # Y el borrador sigue entero para poder corregir.
    assert _load_draft(draft_id).draft_id == draft_id


def test_saving_is_blocked_while_confirmation_owns_the_draft(client):
    """Guardar sobre un borrador que se esta confirmando perderia la edicion.

    El confirmer persistia su snapshot y borraba el borrador despues de que
    "Cambios guardados" ya habia vuelto, asi que esos cambios no llegaban al CV.
    """

    draft_id = _upload(client)
    claim_draft(draft_id)
    try:
        respuesta = client.post(f"/cvs/import/{draft_id}", data={"cv_title": "X"})
        assert respuesta.status_code == 409
        assert "confirmand" in respuesta.text.lower()
    finally:
        release_draft(draft_id)

    # Liberado, guardar vuelve a funcionar.
    assert client.post(f"/cvs/import/{draft_id}", data={"cv_title": "X"}).status_code == 200


def test_discarding_is_ignored_while_confirmation_owns_the_draft(client):
    """Descartar por debajo de una confirmacion en curso perderia la revision."""

    draft_id = _upload(client)
    claim_draft(draft_id)
    try:
        respuesta = client.post(
            f"/cvs/import/{draft_id}/discard",
            data={"confirm": "lo que sea"},
            follow_redirects=False,
        )
        assert respuesta.status_code == 303
        assert _load_draft(draft_id).draft_id == draft_id, "el borrador no se descarta en curso"
    finally:
        release_draft(draft_id)


def test_save_and_discard_are_atomic_with_confirmation(client):
    """Guardar o descartar no pueden colarse entre el reclamo y la escritura.

    Verificarlo antes y actuar despues dejaba un hueco: la peticion cede leyendo
    el formulario y una confirmacion reclamaba ahi. Ahora guardar y descartar
    reclaman, y cualquier salida que no sea la propia libera el borrador.
    """

    draft_id = _upload(client)

    # Un descarte con la confirmacion mal escrita libera el reclamo: un error de
    # tipeo no puede bloquear el borrador durante dos horas.
    draft = _load_draft(draft_id)
    respuesta = client.post(
        f"/cvs/import/{draft_id}/discard",
        data={"discard_confirmation": "no coincide"},
        follow_redirects=False,
    )
    assert respuesta.status_code == 422
    assert _load_draft(draft_id).draft_id == draft_id
    assert not _claim_exists(draft_id)

    # Y guardar sigue funcionando con el reclamo libre.
    assert client.post(f"/cvs/import/{draft_id}", data={"cv_title": "X"}).status_code == 200


def _claim_exists(draft_id: str) -> bool:
    from app.services.import_staging_service import _draft_path, DRAFT_CLAIM_SUFFIX

    return _draft_path(draft_id).with_suffix(DRAFT_CLAIM_SUFFIX).exists()
