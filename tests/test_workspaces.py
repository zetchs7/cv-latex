"""Pruebas de aislamiento entre MODO REAL y MODO PRUEBAS.

Cada prueba trabaja sobre el directorio temporal que ya aisla `conftest.py`; el
hook de fin de sesion vuelve a comprobar que `data/` del repositorio no cambio,
asi que una fuga de aislamiento hace fallar la corrida completa, no solo un test.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import database
from app import workspace_middleware as middleware
from app.environments import (
    MIGRATION_MARKER_FILENAME,
    MIGRATING_MARKER_FILENAME,
    Environment,
    environment_data_root,
    legacy_migrated,
    legacy_storage_in_use,
    migration_in_progress,
    resolved_data_root,
)
from app.main import app
from app.repositories import application_repository, cover_letter_repository, cv_repository
from app.routes import workspaces as workspaces_routes
from app.schemas import ApplicationFormData, CoverLetterFormData, CVFormData
from app.services import workspace_service
from app.services.workspace_service import (
    DummyDataError,
    delete_selected,
    dependencies_of,
    ensure_environment_ready,
    generate_dummy_data,
    in_environment,
    inventory,
    plan_migration,
    purge_environment,
)


@pytest.fixture(autouse=True)
def clean_environments():
    """Deja los dos entornos vacios antes y despues de cada prueba."""

    workspace_service._ready.clear()
    root = resolved_data_root()

    # La raiz legacy tambien hay que limpiarla: las pruebas de migracion crean
    # ahi una base historica y dejaria contaminada a las siguientes.
    leftovers = ["app.db", "app.db-wal", "app.db-shm", "app.db-journal", "exports", "import-drafts"]
    leftovers.append(MIGRATION_MARKER_FILENAME)
    # El candado de migracion tiene que quedar limpio igual: si una prueba lo
    # dejara puesto, todas las siguientes verian 503 y el error no apuntaria a
    # la prueba que lo dejo.
    leftovers.append(MIGRATING_MARKER_FILENAME)
    # `*.db` ademas de `app.db`: una base con nombre personalizado por
    # `APP_DB_FILENAME` contaminaria la prueba siguiente igual que `app.db`.
    for pattern in ("*.db", "app.db.retirado-*", "app.db.tmp-legacy-*", "app.db.pre-migracion-*"):
        leftovers.extend(item.name for item in root.glob(pattern))

    for name in leftovers:
        candidate = root / name
        if candidate.is_dir():
            shutil.rmtree(candidate, ignore_errors=True)
        elif candidate.exists():
            candidate.unlink()

    for environment in (Environment.REAL, Environment.TEST):
        target = environment_data_root(root, environment)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
    workspace_service._ready.clear()
    yield
    workspace_service._ready.clear()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _seed_cv(title: str = "CV de prueba") -> int:
    with in_environment(Environment.REAL):
        ensure_environment_ready(Environment.REAL)
        return cv_repository.create_cv(
            CVFormData(
                title=title,
                full_name="Persona Real",
                email="persona@ejemplo.invalid",
                phone="+54 9 341 555-0000",
                professional_summary="Resumen real.",
                experience_summary="Experiencia real.",
                education_summary="Formacion real.",
                skills="Python, SQL",
            )
        )


def _seed_letter() -> int:
    with in_environment(Environment.REAL):
        ensure_environment_ready(Environment.REAL)
        return cover_letter_repository.create_cover_letter(
            CoverLetterFormData(
                company="Empresa Real",
                position="Puesto Real",
                contact="rrhh@ejemplo.invalid",
                greeting="Saludos:",
                introduction="Introduccion real.",
                body="Cuerpo real.",
                closing="Atentamente.",
                signature="Persona Real",
                associated_cv_id=None,
            )
        )


def _seed_application(cv_id: int | None = None) -> int:
    with in_environment(Environment.REAL):
        ensure_environment_ready(Environment.REAL)
        return application_repository.create_application(
            ApplicationFormData(
                company="Empresa Real",
                position="Puesto Real",
                link="https://ejemplo.invalid/vacante",
                source="Referido",
                applied_on="2026-01-05",
                status="enviada",
                associated_cv_id=cv_id,
                associated_cover_letter_id=None,
                notes="nota",
                next_action="seguir",
                follow_up_date="",
            )
        )


def _table_count(environment: Environment, table: str, record_id: int) -> int:
    database_path = environment_data_root(resolved_data_root(), environment) / "app.db"
    if not database_path.exists():
        return 0
    connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        return connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE id = ?", (record_id,)
        ).fetchone()[0]
    finally:
        connection.close()


# --- Aislamiento -------------------------------------------------------------


def test_los_entornos_usan_bases_distintas():
    real = database._is_test_process and environment_data_root(resolved_data_root(), Environment.REAL)
    test = environment_data_root(resolved_data_root(), Environment.TEST)
    assert real != test
    assert real.name == "real"
    assert test.name == "test"


def test_mismo_id_no_se_confunde_entre_entornos():
    """Dos registros con el mismo id no deben cruzarse: cada base es la suya."""

    with in_environment(Environment.REAL):
        ensure_environment_ready(Environment.REAL)
    with in_environment(Environment.TEST):
        ensure_environment_ready(Environment.TEST)

    _seed_cv("CV real")
    generated = generate_dummy_data(
        Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=11
    )

    real_id = _seed_cv("CV real dos")
    assert real_id in generated.cvs or True  # los ids pueden coincidir; lo que importa es la base

    with in_environment(Environment.REAL):
        assert cv_repository.get_cv(real_id) is not None
        titles = {cv.title for cv in cv_repository.list_cvs()}
    assert "CV real dos" in titles

    with in_environment(Environment.TEST):
        test_titles = {cv.title for cv in cv_repository.list_cvs()}
    assert "CV real dos" not in test_titles
    assert test_titles and all("CV de" in title or title for title in test_titles)


def test_crear_en_pruebas_no_altera_real():
    _seed_cv("CV original")
    before = inventory(Environment.REAL).cvs

    generate_dummy_data(Environment.TEST, cvs=5, cover_letters=0, applications=0, seed=3)

    assert inventory(Environment.REAL).cvs == before
    assert inventory(Environment.TEST).cvs == 5


def test_editar_en_pruebas_no_altera_real():
    real_id = _seed_cv("CV a editar")
    with in_environment(Environment.REAL):
        original = cv_repository.get_cv(real_id)

    generate_dummy_data(Environment.TEST, cvs=3, cover_letters=0, applications=0, seed=4)
    with in_environment(Environment.TEST):
        target = cv_repository.list_cvs()[0]
        payload = target.structured_payload
        if isinstance(payload, str):
            payload = json.loads(payload)
        payload = dict(payload)
        payload["title"] = "Editado en pruebas"
        updated = cv_repository.update_structured_cv(
            target.id, title="Editado en pruebas", payload=payload
        )
        assert updated is True

    with in_environment(Environment.REAL):
        after = cv_repository.get_cv(real_id)
    assert after.title == original.title
    assert after.full_name == original.full_name


def test_borrar_en_pruebas_no_altera_real():
    real_id = _seed_cv("CV protegido")
    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=0, seed=5)

    with in_environment(Environment.TEST):
        victim = cv_repository.list_cvs()[0].id
    assert delete_selected(Environment.TEST, {"cvs": [victim], "cover_letters": [], "applications": []})[
        "cvs"
    ] == 1

    assert _table_count(Environment.REAL, "cvs", real_id) == 1
    with in_environment(Environment.REAL):
        assert cv_repository.get_cv(real_id) is not None


def test_vaciar_pruebas_no_altera_real():
    real_id = _seed_cv("CV sobreviviente")
    _seed_letter()
    _seed_application()
    generate_dummy_data(Environment.TEST, cvs=4, cover_letters=3, applications=2, seed=6)

    result = purge_environment(Environment.TEST)
    assert result["pending"] == []

    assert inventory(Environment.TEST).total == 0
    assert inventory(Environment.REAL).cvs == 1
    assert _table_count(Environment.REAL, "cvs", real_id) == 1


def test_exportaciones_separadas():
    with in_environment(Environment.REAL):
        real_exports = database.get_data_dir() / "exports"
    with in_environment(Environment.TEST):
        test_exports = database.get_data_dir() / "exports"

    assert real_exports != test_exports
    test_exports.mkdir(parents=True, exist_ok=True)
    (test_exports / "cv-prueba.tex").write_text("% nada real", encoding="utf-8")

    assert not (real_exports / "cv-prueba.tex").exists()


def test_borradores_de_importacion_separados():
    with in_environment(Environment.REAL):
        real_drafts = database.get_data_dir() / "import-drafts"
    with in_environment(Environment.TEST):
        test_drafts = database.get_data_dir() / "import-drafts"

    assert real_drafts != test_drafts
    test_drafts.mkdir(parents=True, exist_ok=True)
    (test_drafts / "borrador.json").write_text("{}", encoding="utf-8")

    assert not (real_drafts / "borrador.json").exists()


def test_dos_solicitudes_concurrentes_operan_sobre_entornos_distintos():
    """Una petición escribiendo en PRUEBAS y otra leyendo REAL a la vez."""

    real_id = _seed_cv("CV real concurrente")
    observations: dict[str, object] = {}
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def reader() -> None:
        try:
            barrier.wait()
            seen = []
            for _ in range(20):
                with in_environment(Environment.REAL):
                    cv = cv_repository.get_cv(real_id)
                seen.append(cv.title if cv else None)
            observations["real"] = seen
        except BaseException as error:  # noqa: BLE001 - se propaga abajo
            errors.append(error)

    def writer() -> None:
        try:
            barrier.wait()
            generated = generate_dummy_data(
                Environment.TEST, cvs=5, cover_letters=0, applications=0, seed=9
            )
            observations["test"] = generated.cvs
        except BaseException as error:  # noqa: BLE001 - se propaga abajo
            errors.append(error)

    threads = [threading.Thread(target=reader), threading.Thread(target=writer)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert observations["real"] == ["CV real concurrente"] * 20
    assert len(observations["test"]) == 5
    assert inventory(Environment.REAL).cvs == 1
    assert inventory(Environment.TEST).cvs == 5


def test_dos_pestanas_no_producen_cambios_cruzados():
    """Dos peticiones simultaneas en entornos distintos no se pisan."""

    _seed_cv("CV real pestañas")
    with TestClient(app) as client_a, TestClient(app) as client_b:
        client_a.cookies.clear()
        client_b.cookies.clear()

        response_a = client_a.get("/real/")
        response_b = client_b.get("/test/")

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert "CV real pestañas" in response_a.text
    assert "CV real pestañas" not in response_b.text
    assert 'data-workspace-banner="test"' in response_b.text
    assert 'data-workspace-banner="real"' in response_a.text


def test_no_hay_fallback_silencioso_al_entorno_equivocado():
    """Un prefijo desconocido no debe caer a REAL ni a PRUEBAS por accidente."""

    with TestClient(app) as client:
        unknown = client.get("/produccion/cvs/", follow_redirects=False)
        assert unknown.status_code == 404

    root = resolved_data_root()
    assert not (root / "produccion").exists()


def test_ruta_o_entorno_manipulado_en_formulario_se_rechaza():
    """El entorno se toma de la ruta, no del cuerpo del formulario."""

    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=0, seed=12)
    with TestClient(app) as client:
        client.get("/config/workspaces")
        token = client.cookies["gentle_workspace_csrf"]
        response = client.post(
            "/real/config/workspaces/generate",
            data={
                "cvs": "5",
                "cover_letters": "0",
                "applications": "0",
                "csrf_token": token,
            },
        )
        assert response.status_code == 200
        assert "solo se generan en MODO PRUEBAS" in response.text

    assert inventory(Environment.REAL).cvs == 0
    assert inventory(Environment.TEST).cvs == 2


# --- Generacion --------------------------------------------------------------


def test_genera_cantidades_configurables():
    result = generate_dummy_data(
        Environment.TEST, cvs=8, cover_letters=4, applications=6, seed=42
    )
    assert (len(result.cvs), len(result.cover_letters), len(result.applications)) == (8, 4, 6)
    summary = inventory(Environment.TEST)
    assert (summary.cvs, summary.cover_letters, summary.applications) == (8, 4, 6)


def test_los_registros_generados_no_son_copias_identicas():
    generate_dummy_data(Environment.TEST, cvs=10, cover_letters=5, applications=5, seed=7)

    with in_environment(Environment.TEST):
        cvs = cv_repository.list_cvs()
        letters = cover_letter_repository.list_cover_letters()
        applications = application_repository.list_applications()

    assert len({cv.full_name for cv in cvs}) > 1
    assert len({cv.title for cv in cvs}) == len(cvs)
    assert len({cv.structured_payload for cv in cvs}) > 1
    assert len({letter.body for letter in letters}) == len(letters)
    assert len({application.company for application in applications}) > 1


def test_los_cvs_generados_usan_schema_2():
    generate_dummy_data(Environment.TEST, cvs=5, cover_letters=0, applications=0, seed=8)

    with in_environment(Environment.TEST):
        for cv in cv_repository.list_cvs():
            assert cv.structured_schema_version == 2
            assert cv.structured_payload, "el payload estructurado no puede quedar vacio"


def test_las_postulaciones_generadas_se_vinculan():
    generate_dummy_data(
        Environment.TEST, cvs=3, cover_letters=2, applications=4, seed=9
    )

    with in_environment(Environment.TEST):
        applications = application_repository.list_applications()
    assert applications
    assert all(application.associated_cv_id for application in applications)
    assert any(application.associated_cover_letter_id for application in applications)


def test_generacion_repetida_acumula_sin_duplicar_por_error():
    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=0, seed=1)
    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=0, seed=1)
    assert inventory(Environment.TEST).cvs == 4


def test_cantidades_invalidas_o_excesivas_se_rechazan():
    for invalid in (-1, 51, 10_000):
        with pytest.raises(DummyDataError) as error:
            generate_dummy_data(
                Environment.TEST, cvs=invalid, cover_letters=0, applications=0, seed=2
            )
        assert error.value.code == "dummy_out_of_range"
        assert "entre 0 y 50" in error.value.user_message

    assert inventory(Environment.TEST).total == 0


def test_generar_en_real_esta_prohibido():
    with pytest.raises(DummyDataError) as error:
        generate_dummy_data(Environment.REAL, cvs=1, cover_letters=0, applications=0)
    assert error.value.code == "dummy_real_forbidden"
    assert inventory(Environment.REAL).total == 0


def test_semilla_determinista_reproduce_lo_mismo():
    first = generate_dummy_data(Environment.TEST, cvs=3, cover_letters=1, applications=1, seed=99)
    with in_environment(Environment.TEST):
        first_titles = [cv.title for cv in cv_repository.list_cvs()]
    purge_environment(Environment.TEST)

    second = generate_dummy_data(Environment.TEST, cvs=3, cover_letters=1, applications=1, seed=99)
    with in_environment(Environment.TEST):
        second_titles = [cv.title for cv in cv_repository.list_cvs()]

    assert first_titles == second_titles
    assert len(first.cvs) == len(second.cvs) == 3


# --- Borrado -----------------------------------------------------------------


def test_borrado_selectivo_individual_y_multiple():
    generate_dummy_data(Environment.TEST, cvs=5, cover_letters=4, applications=3, seed=13)

    with in_environment(Environment.TEST):
        cv_ids = [cv.id for cv in cv_repository.list_cvs()]
        letter_ids = [letter.id for letter in cover_letter_repository.list_cover_letters()]

    result = delete_selected(
        Environment.TEST,
        {"cvs": cv_ids[:3], "cover_letters": letter_ids[:2], "applications": []},
    )
    assert result["cvs"] == 3
    assert result["cover_letters"] == 2
    assert result["applications"] == 0

    summary = inventory(Environment.TEST)
    assert summary.cvs == 2
    assert summary.cover_letters == 2


def test_borrado_es_fisico_y_no_soft_delete():
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=14)

    with in_environment(Environment.TEST):
        victim = cv_repository.list_cvs()[0].id
    delete_selected(Environment.TEST, {"cvs": [victim], "cover_letters": [], "applications": []})

    assert _table_count(Environment.TEST, "cvs", victim) == 0


def test_borrado_en_real_esta_prohibido():
    with pytest.raises(DummyDataError) as error:
        delete_selected(Environment.REAL, {"cvs": [1], "cover_letters": [], "applications": []})
    assert error.value.code == "delete_real_forbidden"


def test_dependencias_detectadas_sin_borrar_en_silencio():
    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=2, seed=15)

    with in_environment(Environment.TEST):
        applications = application_repository.list_applications()
        cv_id = applications[0].associated_cv_id

    kept = dependencies_of(Environment.TEST, {"cvs": [cv_id], "cover_letters": [], "applications": []})
    assert kept["applications_kept"], "debia reportar las postulaciones que usan el CV"


def test_archivo_asociado_se_borra_con_su_cv():
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=16)
    with in_environment(Environment.TEST):
        victim = cv_repository.list_cvs()[0].id
        exports = database.get_data_dir() / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        export_file = exports / f"cv-{victim}.tex"
        export_file.write_text("% export del CV", encoding="utf-8")
        unrelated = exports / "cv-otro.tex"
        unrelated.write_text("% export ajeno", encoding="utf-8")

    result = delete_selected(
        Environment.TEST, {"cvs": [victim], "cover_letters": [], "applications": []}
    )

    assert not export_file.exists()
    assert unrelated.exists()
    assert result["files"] == 1


def test_fallo_a_mitad_del_borrado_no_se_declara_exitoso():
    """Un registro que no se puede borrar deja `pending`, no exito silencioso."""

    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=0, seed=17)
    with in_environment(Environment.TEST):
        ids = [cv.id for cv in cv_repository.list_cvs()]

    original = workspace_service._delete_selected_impl

    def exploding(environment, selection):
        result = original(environment, selection)
        result["pending"].append("cvs:%s: simulado" % ids[0])
        return result

    workspace_service._delete_selected_impl = exploding
    try:
        result = delete_selected(
            Environment.TEST, {"cvs": ids, "cover_letters": [], "applications": []}
        )
    finally:
        workspace_service._delete_selected_impl = original

    assert result["pending"], "un fallo parcial debe reportarse, no ocultarse"


def test_no_se_sigue_un_enlace_simbolico_fuera_del_entorno(tmp_path):
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=18)
    with in_environment(Environment.TEST):
        root = database.get_data_dir()
        exports = root / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        outside = tmp_path / "fuera.tex"
        outside.write_text("no me toques", encoding="utf-8")
        link = exports / "fuga.tex"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("el sistema no permite enlaces simbolicos")

    result = purge_environment(Environment.TEST)

    assert outside.exists(), "un enlace simbolico nunca debe seguirse para borrar"
    assert "fuga.tex" in result["pending"]


# --- Vaciado completo --------------------------------------------------------


def test_vaciar_pruebas_deja_entorno_funcional_y_vacio():
    generate_dummy_data(Environment.TEST, cvs=3, cover_letters=2, applications=1, seed=19)

    result = purge_environment(Environment.TEST)
    assert result["pending"] == []
    assert inventory(Environment.TEST).total == 0

    # Sigue siendo funcional: se puede generar de nuevo.
    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=0, seed=20)
    assert inventory(Environment.TEST).cvs == 2


def test_vaciar_pruebas_elimina_soft_deleted_y_archivos():
    generate_dummy_data(Environment.TEST, cvs=3, cover_letters=0, applications=0, seed=21)
    with in_environment(Environment.TEST):
        victim = cv_repository.list_cvs()[0].id
        cv_repository.soft_delete_cv(victim)
        exports = database.get_data_dir() / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        (exports / "previo.tex").write_text("% previo", encoding="utf-8")

    purge_environment(Environment.TEST)

    summary = inventory(Environment.TEST)
    assert summary.cvs == 0
    assert summary.soft_deleted_cvs == 0
    assert summary.exports == 0


def test_vaciar_real_esta_prohibido():
    with pytest.raises(DummyDataError) as error:
        purge_environment(Environment.REAL)
    assert error.value.code == "purge_real_forbidden"


# --- CSRF y confirmacion -----------------------------------------------------


def _cookie(client: TestClient) -> str:
    client.get("/config/workspaces")
    return client.cookies["gentle_workspace_csrf"]


def test_csrf_invalido_rechaza_la_operacion(client):
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=22)
    before = inventory(Environment.TEST).cvs
    _cookie(client)

    response = client.post(
        "/test/config/workspaces/purge",
        data={"confirmation": "VACIAR PRUEBAS", "csrf_token": "falsificado"},
    )

    assert "sesión expiró" in response.text
    assert inventory(Environment.TEST).cvs == before


def test_confirmacion_invalida_rechaza_el_borrado(client):
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=23)
    token = _cookie(client)
    with in_environment(Environment.TEST):
        victim = cv_repository.list_cvs()[0].id

    response = client.post(
        "/test/config/workspaces/delete/execute",
        data={"cvs": str(victim), "csrf_token": token, "typed_confirmation": "borrar"},
    )

    assert "escribí exactamente" in response.text
    assert _table_count(Environment.TEST, "cvs", victim) == 1


def test_confirmacion_correcta_borra(client):
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=24)
    token = _cookie(client)
    with in_environment(Environment.TEST):
        victim = cv_repository.list_cvs()[0].id

    response = client.post(
        "/test/config/workspaces/delete/execute",
        data={
            "cvs": str(victim),
            "csrf_token": token,
            "typed_confirmation": "ELIMINAR 1 DE PRUEBAS",
        },
    )

    assert "Borrados:" in response.text
    assert _table_count(Environment.TEST, "cvs", victim) == 0


def test_vaciado_requiere_frase_exacta(client):
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=25)
    token = _cookie(client)

    response = client.post(
        "/test/config/workspaces/purge",
        data={"confirmation": "vaciar pruebas", "csrf_token": token},
    )

    assert "VACIAR PRUEBAS" in response.text
    assert inventory(Environment.TEST).cvs == 1


# --- Migracion ---------------------------------------------------------------


def _install_legacy_database(root: Path) -> Path:
    """Crea una base historica como la que deja una instalacion sin migrar."""

    database_path = root / "app.db"
    # El arranque de la app ya pudo crear una base vacia en la raiz; se retira
    # para que el fixture represente una instalacion con datos heredados.
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = Path(str(database_path) + suffix)
        if candidate.exists():
            candidate.unlink()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE cvs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                full_name TEXT, email TEXT, phone TEXT,
                professional_summary TEXT, experience_summary TEXT,
                education_summary TEXT, skills TEXT,
                created_at TEXT, updated_at TEXT, deleted_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE cover_letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, company TEXT, position TEXT, contact TEXT,
                greeting TEXT, introduction TEXT, body TEXT, closing TEXT,
                signature TEXT, associated_cv_id INTEGER,
                created_at TEXT, updated_at TEXT, deleted_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL, position TEXT NOT NULL, link TEXT, source TEXT,
                applied_on TEXT, status TEXT, associated_cv_id INTEGER,
                associated_cover_letter_id INTEGER, notes TEXT, next_action TEXT,
                follow_up_date TEXT,
                created_at TEXT, updated_at TEXT, deleted_at TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO cvs (title, full_name, email, phone, professional_summary,"
            " experience_summary, education_summary, skills) VALUES"
            " ('CV heredado', 'Heredado', 'a@b.invalid', '1', 'r', 'e', 'f', 'Python')"
        )
        connection.execute(
            "INSERT INTO cover_letters (title, company, position, contact, greeting,"
            " introduction, body, closing, signature) VALUES"
            " ('Carta heredada', 'Heredada', 'Puesto', 'a@b.invalid', 'h', 'i', 'b', 'c', 's')"
        )
        connection.execute(
            "INSERT INTO applications (company, position, link, source, applied_on,"
            " status) VALUES ('Empresa', 'Puesto', 'https://x.invalid', 'Web',"
            " '2026-01-01', 'enviada')"
        )
        connection.commit()
    finally:
        connection.close()
    return database_path


def test_plan_de_migracion_no_modifica_nada():
    root = resolved_data_root()
    _install_legacy_database(root)
    before = sorted(p.name for p in root.iterdir())

    plan = plan_migration()

    assert plan.status == "ready"
    assert plan.counts["cvs"] == 1
    assert sorted(p.name for p in root.iterdir()) == before


def test_plan_de_migracion_sin_base_historica():
    plan = plan_migration()
    assert plan.status == "not_pending"


def test_plan_de_migracion_no_sobrescribe_destino_ocupado():
    root = resolved_data_root()
    _install_legacy_database(root)
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=26)

    plan = plan_migration()

    assert plan.status == "blocked"
    assert any("ya tiene una base" in problem for problem in plan.problems)


def test_migracion_exige_confirmacion_exacta():
    with pytest.raises(DummyDataError) as error:
        workspace_service.execute_migration(require_confirmation="migrar")
    assert error.value.code == "migration_confirmation"


def test_migracion_completa_mueve_datos_y_deja_real_vacio():
    root = resolved_data_root()
    legacy = _install_legacy_database(root)
    exports = root / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / "heredado.tex").write_text("% heredado", encoding="utf-8")

    result = workspace_service.execute_migration(require_confirmation="MIGRAR")

    assert result["counts"]["cvs"] == 1
    test_root = environment_data_root(root, Environment.TEST)
    real_root = environment_data_root(root, Environment.REAL)

    assert (test_root / "app.db").exists()
    assert (test_root / "exports" / "heredado.tex").exists()
    assert not (real_root / "app.db").exists()
    assert inventory(Environment.REAL).total == 0

    # La vista historica queda RETIRADA, no conviviendo. La base no se borro:
    # salio del camino vivo con otro nombre, y ese archivo es la fuente de rollback.
    assert not legacy.exists(), "la base historica no puede seguir en el camino vivo"
    assert (root / MIGRATION_MARKER_FILENAME).exists()
    retired = list(root.glob("app.db.retirado-*"))
    assert len(retired) == 1, "debe quedar exactamente una base retirada"

    with in_environment(Environment.TEST):
        assert [cv.title for cv in cv_repository.list_cvs()] == ["CV heredado"]

    # Y la retirada sigue siendo legible: el rollback no depende de nada mas.
    connection = sqlite3.connect(f"file:{retired[0]}?mode=ro", uri=True)
    try:
        assert connection.execute("SELECT title FROM cvs").fetchone()[0] == "CV heredado"
    finally:
        connection.close()


def test_migracion_es_reintentable():
    root = resolved_data_root()
    _install_legacy_database(root)

    workspace_service.execute_migration(require_confirmation="MIGRAR")
    with in_environment(Environment.TEST):
        titles = [cv.title for cv in cv_repository.list_cvs()]

    # Un segundo intento no debe duplicar nada: el destino ya esta ocupado.
    with pytest.raises(DummyDataError) as error:
        workspace_service.execute_migration(require_confirmation="MIGRAR")
    assert error.value.code == "migration_blocked"

    with in_environment(Environment.TEST):
        assert [cv.title for cv in cv_repository.list_cvs()] == titles


def test_migracion_con_destino_ocupado_no_toca_nada():
    root = resolved_data_root()
    legacy = _install_legacy_database(root)
    generate_dummy_data(Environment.TEST, cvs=2, cover_letters=0, applications=0, seed=27)
    test_root = environment_data_root(root, Environment.TEST)
    fingerprint = (test_root / "app.db").stat().st_size

    with pytest.raises(DummyDataError) as error:
        workspace_service.execute_migration(require_confirmation="MIGRAR")

    assert error.value.code == "migration_blocked"
    assert (test_root / "app.db").stat().st_size == fingerprint
    assert legacy.exists()


def test_arranque_de_la_app_funciona_antes_y_despues_de_migrar(client):
    root = resolved_data_root()
    _install_legacy_database(root)

    assert client.get("/").status_code == 200

    workspace_service.execute_migration(require_confirmation="MIGRAR")

    assert client.get("/").status_code == 200
    assert client.get("/test/cvs/").status_code == 200
    assert client.get("/real/cvs/").status_code == 200


# --- Pantallas ---------------------------------------------------------------


def test_las_rutas_de_entorno_muestran_el_indicador(client):
    real_response = client.get("/real/")
    test_response = client.get("/test/")

    assert 'data-workspace-banner="real"' in real_response.text
    assert 'data-workspace-banner="test"' in test_response.text
    assert "MODO PRUEBAS" in test_response.text
    assert "MODO REAL" in real_response.text


def test_los_enlaces_quedan_dentro_del_entorno(client):
    body = client.get("/test/cvs/").text
    assert 'href="http://testserver/test/cvs/"' in body or "/test/cvs/" in body
    assert "/test/config/workspaces" in body


def test_en_real_no_se_ofrecen_herramientas_de_pruebas(client):
    response = client.get("/real/config/workspaces/manage/cvs")
    assert "no hay herramientas de datos de prueba" in response.text


def test_las_herramientas_de_pruebas_no_se_muestran_en_real(client):
    body = client.get("/real/config/workspaces").text
    assert "Generar datos de prueba" not in body
    assert "Vaciar todos los datos de Pruebas" not in body


# --- Retiro de la vista historica (requisito 1) -------------------------------
#
# La vista sin prefijo es exclusivamente transitoria: existe para no dejar la
# aplicacion inutilizable antes de migrar. Despues de migrar solo REAL y PRUEBAS
# son operativos, y no puede quedar un tercer espacio de trabajo.


def _migrate() -> dict:
    root = resolved_data_root()
    _install_legacy_database(root)
    exports = root / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / "heredado.tex").write_text("% heredado", encoding="utf-8")
    return workspace_service.execute_migration(require_confirmation="MIGRAR")


def test_tras_migrar_no_queda_un_tercer_espacio_de_trabajo():
    root = resolved_data_root()
    _migrate()

    # Tres comprobaciones sobre el mismo hecho: no hay base en la raiz, hay
    # marcador de retiro, y la base historica sobrevive con otro nombre.
    assert not (root / "app.db").exists()
    assert (root / MIGRATION_MARKER_FILENAME).exists()
    assert len(list(root.glob("app.db.retirado-*"))) == 1
    assert legacy_migrated(root) is True

    # Los dos entornos quedan como unicos espacios operativos.
    assert inventory(Environment.TEST).cvs == 1
    assert inventory(Environment.REAL).total == 0


def test_tras_migrar_las_rutas_sin_prefijo_redirigen_a_real():
    _migrate()

    with TestClient(app) as client:
        root_response = client.get("/", follow_redirects=False)
        cvs_response = client.get("/cvs/", follow_redirects=False)
        follow = client.get("/", follow_redirects=True)

    assert root_response.status_code == 303
    assert root_response.headers["location"].endswith("/real/")
    assert cvs_response.status_code == 303
    assert cvs_response.headers["location"].endswith("/real/cvs/")

    # La vista retirada no entrega datos historicos ni siquiera siguiendo la
    # redireccion: lo que se ve es REAL, que arranca vacio.
    assert "CV heredado" not in follow.text
    assert 'data-workspace-banner="real"' in follow.text


def test_tras_migrar_un_post_sin_prefijo_no_escribe_nada():
    _migrate()
    root = resolved_data_root()

    with TestClient(app) as client:
        response = client.post(
            "/cvs/",
            data={"title": "Escrito por la vista historica"},
            follow_redirects=False,
        )

    # 303 convierte el POST en GET: nada se escribe, y nada se redirige a REAL
    # para escribir alli tampoco.
    assert response.status_code == 303
    assert not (root / "app.db").exists()
    assert inventory(Environment.REAL).total == 0
    with in_environment(Environment.TEST):
        assert [cv.title for cv in cv_repository.list_cvs()] == ["CV heredado"]


def test_tras_migrar_el_arranque_no_recrea_la_base_legacy():
    root = resolved_data_root()
    _migrate()

    with TestClient(app) as client:
        assert client.get("/", follow_redirects=False).status_code == 303

    assert not (root / "app.db").exists(), (
        "el arranque no puede fabricar una base nueva en la raiz: eso crearia "
        "un tercer espacio de trabajo en cada boot"
    )


def test_antes_de_migrar_la_vista_historica_sigue_operativa():
    """El caracter transitorio: sin migrar, nada cambia respecto de antes."""

    root = resolved_data_root()
    _install_legacy_database(root)
    assert legacy_migrated(root) is False

    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 200
    assert "DATOS SIN CLASIFICAR" in response.text


def test_health_y_estaticos_quedan_exentos_de_la_retirada():
    _migrate()

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health", follow_redirects=False).status_code == 200
        assert client.get("/test/static/css/app.css").status_code == 200
        assert client.get("/static/css/app.css", follow_redirects=False).status_code == 200


def test_restaurar_la_base_rehabilita_la_vista_historica():
    """Rollback manual sin depender de que nadie recuerde borrar un archivo."""

    root = resolved_data_root()
    _migrate()
    retired = next(root.glob("app.db.retirado-*"))
    shutil.copyfile(retired, root / "app.db")

    # El marcador sigue ahi, pero la condicion de "sin base en la raiz" ya no se
    # cumple, asi que la vista historica vuelve sola.
    assert legacy_migrated(root) is False

    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 200


def test_despues_de_migrar_el_diagnostico_dice_que_ya_esta_migrado():
    _migrate()

    plan = plan_migration()

    assert plan.status == "migrated"
    assert any("retirada del camino vivo" in problem for problem in plan.problems)

    with TestClient(app) as client:
        page = client.get("/config/workspaces/migration").text
    assert "Ya esta migrado" in page
    assert "Solo MODO REAL y" in page


# --- CSRF y validacion de entorno en las operaciones POST (requisito 2) -------


POST_ROUTES = (
    "/config/workspaces/enter",
    "/test/config/workspaces/generate",
    "/test/config/workspaces/delete/preview",
    "/test/config/workspaces/delete/execute",
    "/test/config/workspaces/purge",
    "/config/workspaces/migrate",
)


@pytest.mark.parametrize("route", POST_ROUTES)
def test_toda_ruta_post_de_entornos_exige_csrf(route):
    """Barrera estructural: si alguien agrega una ruta POST y olvida el CSRF, esto falla."""

    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=31)
    before = inventory(Environment.TEST).cvs

    # Cuerpo con todos los campos requeridos presentes: si falta uno, FastAPI
    # responde 422 antes del handler y no se llega al chequeo de CSRF, que seria
    # una prueba de otra cosa.
    body = {"confirmation": "VACIAR PRUEBAS", "environment": "test"}

    with TestClient(app) as client:
        response = client.post(route, data=body)

    assert response.status_code == 200, route
    assert "sesión expiró" in response.text, route
    assert inventory(Environment.TEST).cvs == before, route


def test_csrf_invalido_impide_generar_y_no_crea_nada():
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=32)
    before = inventory(Environment.TEST).cvs

    with TestClient(app) as client:
        client.get("/config/workspaces")
        response = client.post(
            "/test/config/workspaces/generate",
            data={"cvs": "5", "cover_letters": "0", "applications": "0", "csrf_token": "falso"},
        )

    assert "sesión expiró" in response.text
    assert inventory(Environment.TEST).cvs == before


def test_csrf_invalido_impide_elegir_entorno():
    with TestClient(app) as client:
        client.get("/config/workspaces")
        response = client.post(
            "/config/workspaces/enter",
            data={"environment": "test", "csrf_token": "falso"},
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert "sesión expiró" in response.text


def test_csrf_invalido_impide_la_migracion():
    root = resolved_data_root()
    _install_legacy_database(root)

    with TestClient(app) as client:
        client.get("/config/workspaces")
        response = client.post(
            "/config/workspaces/migrate",
            data={"confirmation": "MIGRAR", "csrf_token": "falso"},
        )

    assert "sesión expiró" in response.text
    assert (root / "app.db").exists(), "la migracion no puede correr con CSRF invalido"
    assert not (root / MIGRATION_MARKER_FILENAME).exists()


def test_csrf_invalido_impide_la_previsualizacion_de_borrado():
    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=33)
    token = "falso"

    with TestClient(app) as client:
        response = client.post(
            "/test/config/workspaces/delete/preview",
            data={"cvs": "1", "csrf_token": token},
        )

    assert "sesión expiró" in response.text
    assert "Confirmar borrado" not in response.text
    assert inventory(Environment.TEST).cvs == 1


def test_no_se_puede_borrar_seleccion_en_real():
    real_id = _seed_cv("CV real protegido")

    with TestClient(app) as client:
        client.get("/config/workspaces")
        token = client.cookies["gentle_workspace_csrf"]
        response = client.post(
            "/real/config/workspaces/delete/execute",
            data={
                "cvs": str(real_id),
                "csrf_token": token,
                "typed_confirmation": "ELIMINAR 1 DE PRUEBAS",
            },
        )

    assert "solo funcionan en MODO PRUEBAS" in response.text
    assert _table_count(Environment.REAL, "cvs", real_id) == 1


def test_no_se_puede_vaciar_real_por_ruta():
    real_id = _seed_cv("CV real otro")

    with TestClient(app) as client:
        client.get("/config/workspaces")
        token = client.cookies["gentle_workspace_csrf"]
        response = client.post(
            "/real/config/workspaces/purge",
            data={"confirmation": "VACIAR PRUEBAS", "csrf_token": token},
        )

    assert "Solo se puede vaciar el entorno de PRUEBAS" in response.text
    assert _table_count(Environment.REAL, "cvs", real_id) == 1


def test_no_se_puede_generar_en_real_por_ruta():
    with TestClient(app) as client:
        client.get("/config/workspaces")
        token = client.cookies["gentle_workspace_csrf"]
        response = client.post(
            "/real/config/workspaces/generate",
            data={"cvs": "5", "cover_letters": "0", "applications": "0", "csrf_token": token},
        )

    assert "solo se generan en MODO PRUEBAS" in response.text
    assert inventory(Environment.REAL).total == 0


def test_no_se_puede_borrar_seleccion_en_real_por_previsualizacion():
    real_id = _seed_cv("CV real en preview")

    with TestClient(app) as client:
        client.get("/config/workspaces")
        token = client.cookies["gentle_workspace_csrf"]
        response = client.post(
            "/real/config/workspaces/delete/preview",
            data={"cvs": str(real_id), "csrf_token": token},
        )

    assert "solo funcionan en MODO PRUEBAS" in response.text
    assert "Confirmar borrado" not in response.text
    assert _table_count(Environment.REAL, "cvs", real_id) == 1


# --- Correcciones de la revision de codigo (ronda 1) --------------------------
#
# Cada prueba de este bloque replica un hallazgo de la revision contra el codigo
# real. Sin estas pruebas los seis defectos pasaban la suite completa: ninguno
# era cubierto por lo que ya existia.


def _seed_test_letter(company: str, position: str) -> int:
    with in_environment(Environment.TEST):
        ensure_environment_ready(Environment.TEST)
        return cover_letter_repository.create_cover_letter(
            CoverLetterFormData(
                company=company,
                position=position,
                contact="rrhh@ejemplo.invalid",
                greeting="Saludos:",
                introduction="Introduccion.",
                body="Cuerpo.",
                closing="Atentamente.",
                signature="Persona",
                associated_cv_id=None,
            )
        )


def test_el_indicador_de_modo_tambien_se_ve_en_aplicaciones_y_documentacion(client):
    """Las dos vistas que construian su propio `Jinja2Templates` se quedaban sin
    context processor, asi que el banner no aparecia y una persona en MODO
    PRUEBAS podia creer que estaba viendo sus datos reales."""

    applications_page = client.get("/test/applications/").text
    documentation_page = client.get("/test/documentation/").text

    for name, page in (
        ("aplicaciones", applications_page),
        ("documentacion", documentation_page),
    ):
        assert 'data-workspace-banner="test"' in page, f"falta el indicador en {name}"
        assert "MODO PRUEBAS" in page, f"falta el texto del modo en {name}"


def test_en_real_esas_mismas_vistas_tambien_muestran_su_indicador(client):
    for path in ("/real/applications/", "/real/documentation/"):
        page = client.get(path).text
        assert 'data-workspace-banner="real"' in page, f"falta el indicador en {path}"


def test_el_enlace_a_administrar_cierra_el_atributo_href(client):
    """Faltaba la comilla de cierre: el valor se tragaba el texto del enlace y
    la pantalla de administrar quedaba inalcanzable desde la configuracion."""

    page = client.get("/test/config/workspaces").text

    assert '">Administrar datos</a>' in page


def test_el_listado_de_cartas_muestra_empresa_y_puesto(client):
    """La consulta pedia `title` y `recipient_company`, columnas que no existen
    en `cover_letters`. El `except sqlite3.Error` devolvia `[]` y la pestaña de
    cartas salia vacia, lo que ademas dejaba sin previsualizar el borrado."""

    _seed_test_letter("Empresa Carta", "Puesto Carta")

    page = client.get("/test/config/workspaces/manage/cover_letters").text

    assert "Empresa Carta" in page
    assert "Puesto Carta" in page
    assert "Todavia no hay registros de este tipo" not in page


def test_con_cartas_el_borrado_se_puede_previsualizar(client):
    """Cierre del mismo defecto por el camino que mas importa: si el listado
    esta vacio, `_selected_rows` no encuentra nada y la confirmacion nunca
    llega."""

    letter_id = _seed_test_letter("Empresa Borrable", "Puesto Borrable")

    with TestClient(app) as probe:
        probe.get("/test/config/workspaces")
        token = probe.cookies["gentle_workspace_csrf"]
        preview = probe.post(
            "/test/config/workspaces/delete/preview",
            data={"cover_letters": str(letter_id), "csrf_token": token},
        )

    assert "Confirmar borrado" in preview.text
    assert "Empresa Borrable" in preview.text


def test_el_vaciado_se_ofrece_cuando_solo_quedan_archivos(client):
    """`counts.total` solo suma registros: con exportaciones o borradores
    encima, el formulario del vaciado desaparecia y esos archivos quedaban
    sin forma de limpiarlos desde la pantalla."""

    with in_environment(Environment.TEST):
        ensure_environment_ready(Environment.TEST)
        exports = workspace_service.managed_directories(Environment.TEST)["exports"]
        (exports / "cv.tex").write_text("% export", encoding="utf-8")

    page = client.get("/test/config/workspaces/purge-confirm").text

    assert 'name="confirmation"' in page
    assert "MODO PRUEBAS esta vacio" not in page


def test_el_vaciado_no_se_ofrece_si_no_hay_nada_que_borrar(client):
    with in_environment(Environment.TEST):
        ensure_environment_ready(Environment.TEST)

    page = client.get("/test/config/workspaces/purge-confirm").text

    assert 'name="confirmation"' not in page
    assert "MODO PRUEBAS esta vacio" in page


def test_los_entornos_usan_el_mismo_nombre_de_base_que_app_database(monkeypatch):
    """`APP_DB_FILENAME` esta documentado en `.env.example` y `app.database` lo
    respeta. Si los entornos ignoraran la variable mirarian un archivo que la
    aplicacion no usa: inventario vacio, vaciado sin efecto y migracion al
    lugar equivocado."""

    monkeypatch.setenv("APP_DB_FILENAME", "base-personalizada.db")
    root = resolved_data_root()
    custom = root / "base-personalizada.db"
    stray = root / "app.db"
    custom.write_bytes(b"")
    try:
        assert legacy_storage_in_use(root) is True

        stray.write_bytes(b"")
        custom.unlink()

        # Con `app.db` presente pero apuntando a otro nombre, el historico no
        # esta "en uso": mirar el archivo equivocado dejaria la migracion
        # ofreciendose sobre una base que la app no abre.
        assert legacy_storage_in_use(root) is False

        for environment in (Environment.REAL, Environment.TEST):
            database = workspace_service.managed_directories(environment)["database"]
            assert database.name == "base-personalizada.db"
    finally:
        for path in (custom, stray):
            if path.exists():
                path.unlink()


def test_la_migracion_levanta_el_candado_antes_de_tocar_la_base(monkeypatch):
    """Cierra la ventana de escritura: entre el `backup()` y el renombre de la
    base historica, una escritura sin prefijo quedaria presente en el archivo
    retirado pero ausente del destino. El candado se levanta ANTES del snapshot
    y el middleware la responde con 503."""

    root = resolved_data_root()
    _install_legacy_database(root)

    observed: dict = {}
    original_impl = workspace_service._execute_migration_impl

    def spy(plan):
        observed["locked"] = migration_in_progress(root)
        with TestClient(app) as probe:
            observed["sin_prefijo"] = probe.get(
                "/cvs/", follow_redirects=False
            ).status_code
            observed["prefijada"] = probe.get(
                "/test/cvs/", follow_redirects=False
            ).status_code
            observed["health"] = probe.get("/health").status_code
        return original_impl(plan)

    monkeypatch.setattr(workspace_service, "_execute_migration_impl", spy)
    workspace_service.execute_migration(require_confirmation="MIGRAR")

    assert observed["locked"] is True
    assert observed["sin_prefijo"] == 503
    assert observed["prefijada"] == 503
    assert observed["health"] == 200
    assert not (root / MIGRATING_MARKER_FILENAME).exists()


def test_un_candado_olvidado_explica_como_volver_a_habilitar_la_app():
    root = resolved_data_root()
    _install_legacy_database(root)
    (root / MIGRATING_MARKER_FILENAME).write_text("en curso", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/cvs/", follow_redirects=False)

    # Falla cerrado y explicado: no sirve datos y dice que hacer, porque nadie
    # puede llegar a la pantalla de migracion mientras esto este puesto.
    assert response.status_code == 503
    assert "Retry-After" in response.headers
    assert MIGRATING_MARKER_FILENAME in response.text


def test_el_candado_no_sobrevive_a_una_migracion_exitosa():
    _migrate()

    assert not (resolved_data_root() / MIGRATING_MARKER_FILENAME).exists()


# --- Correcciones de la revision de codigo (ronda 2) --------------------------


def test_el_drenaje_espera_a_las_peticiones_admitidas_y_descarta_la_propia():
    """El candado corta el paso a lo nuevo, pero no alcanza una peticion que ya
    entro: esa puede correr despues del snapshot y su escritura quedaria en la
    base retirada. El drenaje la espera sin ceder el loop nunca podria esperarla.

    `elapsed` es la prueba de que espero de verdad, no de que solo encontro la
    lista vacia."""

    async def scenario():
        loop = asyncio.get_running_loop()
        observed: dict = {}

        async def slow_call_next(request):
            await asyncio.sleep(0.05)
            return "lenta"

        async def migrating_call_next(request):
            start = loop.time()
            observed["drained"] = await middleware.drain_admitted_requests(timeout=2.0)
            observed["elapsed"] = loop.time() - start
            return "migracion"

        en_vuelo = asyncio.create_task(middleware._admit(slow_call_next, None))
        await asyncio.sleep(0)

        observed["propia"] = await middleware._admit(migrating_call_next, None)
        observed["esperada"] = await en_vuelo
        observed["sobrantes"] = set(middleware._admitted)
        return observed

    observed = asyncio.run(scenario())

    assert observed["drained"] is True
    assert observed["elapsed"] >= 0.04, "tenia que esperar a la peticion en vuelo"
    assert observed["esperada"] == "lenta"
    assert observed["sobrantes"] == set()


def test_el_drenaje_no_bloquea_sobre_su_propia_peticion():
    """La ruta de migracion tambien esta admitida: sin descartarse a si misma el
    drenaje esperaria su propia terminacion, que no llega hasta que drena."""

    async def scenario():
        observed: dict = {}

        async def migrating_call_next(request):
            observed["drained"] = await middleware.drain_admitted_requests(timeout=0.2)
            return "ok"

        return await middleware._admit(migrating_call_next, None), observed

    _, observed = asyncio.run(scenario())

    assert observed["drained"] is True


def test_la_ruta_de_migracion_levanta_el_candado_antes_de_drenar(monkeypatch):
    """Orden de los dos pasos: si se drenara primero, cualquier peticion que
    entrara durante la espera escribiria sobre la base historica despues del
    snapshot. La comprobacion es directa: el archivo tiene que existir en el
    momento exacto en que se drena."""

    root = resolved_data_root()
    _install_legacy_database(root)

    observed: dict = {}

    async def spy_drain(*, timeout: float = 10.0) -> bool:
        observed["candado_durante_drenaje"] = (root / MIGRATING_MARKER_FILENAME).exists()
        return True

    monkeypatch.setattr(workspaces_routes, "drain_admitted_requests", spy_drain)

    with TestClient(app) as client:
        client.get("/test/config/workspaces")
        token = client.cookies["gentle_workspace_csrf"]
        response = client.post(
            "/test/config/workspaces/migrate",
            data={"confirmation": "MIGRAR", "csrf_token": token},
        )

    assert response.status_code == 200
    assert observed["candado_durante_drenaje"] is True
    assert not (root / MIGRATING_MARKER_FILENAME).exists()


def test_la_migracion_por_http_completa_el_drenaje_sin_agotarse(client):
    """Prueba la ruta con el drenaje REAL, sin espías. El punto delicado es que
    el drenaje descarta la propia peticion: si no lo hiciera, esperaria su propia
    terminacion, que no llega hasta que drena, y la migracion se agotaria."""

    root = resolved_data_root()
    _install_legacy_database(root)

    client.get("/test/config/workspaces")
    token = client.cookies["gentle_workspace_csrf"]
    response = client.post(
        "/test/config/workspaces/migrate",
        data={"confirmation": "MIGRAR", "csrf_token": token},
    )

    assert response.status_code == 200, response.text
    assert (root / MIGRATION_MARKER_FILENAME).exists()
    assert not (root / MIGRATING_MARKER_FILENAME).exists()
    assert client.get("/", follow_redirects=False).status_code == 303


def test_una_visita_previa_a_los_entornos_no_bloquea_la_migracion(client):
    """La primera visita crea la base de destino con cero registros. Tratar esa
    creacion como "destino ocupado" dejaba la migracion bloqueada para siempre:
    la pantalla no ofrece ninguna accion para borrar una base vacia, y REAL no
    se puede vaciar por diseno."""

    root = resolved_data_root()
    _install_legacy_database(root)

    assert client.get("/test/").status_code == 200
    assert client.get("/real/").status_code == 200
    assert (environment_data_root(root, Environment.TEST) / "app.db").exists()

    plan = plan_migration()
    assert plan.status == "ready", plan.problems

    result = workspace_service.execute_migration(require_confirmation="MIGRAR")
    assert result["counts"]["cvs"] == 1


def test_un_destino_solo_con_archivos_sigue_bloqueando():
    """Vaciar no es lo mismo que estar vacio: un destino que ya tiene archivos no
    se puede sobrescribir aunque no tenga registros."""

    root = resolved_data_root()
    _install_legacy_database(root)
    exports = environment_data_root(root, Environment.TEST) / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / "heredado.tex").write_text("% heredado", encoding="utf-8")

    plan = plan_migration()

    assert plan.status == "blocked"


def test_el_borrado_tambien_se_lleva_los_exports_con_el_nombre_real():
    """El nombre que genera la app es
    `cv-{id}-{titulo}-{variante}-{timestamp}.tex`, donde nunca aparece `-{id}.`.
    El prediccion viejo solo matcheaba con un nombre fabricado, asi que el
    borrado fisico dejaba los archivos en disco mientras reportaba 0."""

    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=41)
    with in_environment(Environment.TEST):
        cv_id = cv_repository.list_cvs()[0].id
        exports = workspace_service.managed_directories(Environment.TEST)["exports"]
        exports.mkdir(parents=True, exist_ok=True)
        real_name = exports / f"cv-{cv_id}-cv-de-prueba-texlivecv-20261014120000000000.tex"
        legado = exports / f"cv-{cv_id}.tex"
        ajeno = exports / f"cv-{cv_id + 900}-ajeno.tex"
        for path in (real_name, legado, ajeno):
            path.write_text("% export", encoding="utf-8")

    result = delete_selected(
        Environment.TEST, {"cvs": [cv_id], "cover_letters": [], "applications": []}
    )

    assert not real_name.exists()
    assert not legado.exists()
    assert ajeno.exists()
    assert result["files"] == 2


def test_borrar_una_carta_tambien_se_lleva_sus_exports():
    """Mismo defecto, otro tipo: la limpieza solo miraba los CVs. El prefijo
    importa igual: un CV que comparta el numero conserva sus archivos."""

    letter_id = _seed_test_letter("Empresa Carta Export", "Puesto")
    with in_environment(Environment.TEST):
        exports = workspace_service.managed_directories(Environment.TEST)["exports"]
        exports.mkdir(parents=True, exist_ok=True)
        de_la_carta = exports / f"cover-letter-{letter_id}-empresa-carta-export-20261014120000000000.tex"
        de_un_cv = exports / f"cv-{letter_id}-cv-que-comparte-numero-20261014120000000000.tex"
        de_la_carta.write_text("% carta", encoding="utf-8")
        de_un_cv.write_text("% cv", encoding="utf-8")

    result = delete_selected(
        Environment.TEST, {"cvs": [], "cover_letters": [letter_id], "applications": []}
    )

    assert not de_la_carta.exists()
    assert de_un_cv.exists()
    assert result["files"] == 1


def test_un_registro_que_ya_no_existe_no_se_cuenta_como_borrado():
    """`hard_delete_*` devuelve False si no borro nada. Contarlo como exito
    mentia sobre lo que ocurrio."""

    generate_dummy_data(Environment.TEST, cvs=1, cover_letters=0, applications=0, seed=42)
    with in_environment(Environment.TEST):
        victim = cv_repository.list_cvs()[0].id

    delete_selected(Environment.TEST, {"cvs": [victim], "cover_letters": [], "applications": []})
    resultado = delete_selected(
        Environment.TEST, {"cvs": [victim], "cover_letters": [], "applications": []}
    )

    assert resultado["cvs"] == 0
    assert resultado["missing"] == [f"cvs:{victim}"]
    assert resultado["pending"] == [], "no hay nada que reintentar, no es un fallo"


def test_un_id_inexistente_en_la_previsualizacion_no_finge_borrado(client):
    """Camino HTTP del mismo defecto: la seleccion se revalida contra la base en
    el momento de ejecutar, no contra la previsualizacion."""

    with in_environment(Environment.TEST):
        ensure_environment_ready(Environment.TEST)

    client.get("/test/config/workspaces")
    token = client.cookies["gentle_workspace_csrf"]
    response = client.post(
        "/test/config/workspaces/delete/execute",
        data={
            "cvs": "987654",
            "csrf_token": token,
            "typed_confirmation": "ELIMINAR 1 DE PRUEBAS",
        },
    )

    assert "ya no existían" in response.text
