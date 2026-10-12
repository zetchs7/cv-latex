"""Tests del Project Control Center.

Verifican el catalogo real del repositorio y el comportamiento de
`tools/project_control.py` bajo entradas invalidas. Son de solo lectura sobre
`data/` y `app/static/docs/`: no abren SQLite ni escriben artefactos de la app.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPOSITORY_ROOT / "tools" / "project_control.py"
CATALOG_PATH = REPOSITORY_ROOT / "docs" / "development" / "project_control" / "catalog.json"


def _load_tool():
    """Importa la herramienta sin convertir `tools/` en un paquete."""
    spec = importlib.util.spec_from_file_location("project_control", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


project_control = _load_tool()


def _valid_catalog() -> dict:
    return {
        "meta": {"schema_version": 1},
        "project": {
            "name": "Ejemplo",
            "stable_version": "1.0.0",
            "main_branch": "main",
            "development_branch": "development",
            "last_verified_on": "2026-01-01",
            "last_verification_evidence": "Suite en verde el 2026-01-01.",
            "mvp_criteria": ["Criterio uno."],
            "expanded_vision": ["Vision uno."],
            "release_policy": ["Politica una."],
        },
        "modules": [
            {
                "id": "modulo",
                "name": "Modulo",
                "routes": "`app/x.py`",
                "state": "in_main",
                "in_development": True,
                "in_main": True,
                "evidence": "`app/x.py:1`",
            }
        ],
        "risks": [],
        "tasks": [
            {
                "id": "TAREA-001",
                "title": "Tarea de prueba",
                "description": "Descripcion.",
                "origin": "engineering",
                "priority": "P2",
                "status": "ready",
                "module": "modulo",
                "depends_on": [],
                "acceptance": ["Criterio verificable."],
                "evidence": "`tests/`",
                "github_issue": None,
                "next_action": "Hacer algo.",
                "approved": False,
            }
        ],
    }


def _errors(catalog: dict) -> list[str]:
    return [
        problem.message
        for problem in project_control.validate_catalog(catalog)
        if problem.level == "error"
    ]


def _error_locations(catalog: dict) -> list[str]:
    return [
        problem.location
        for problem in project_control.validate_catalog(catalog)
        if problem.level == "error"
    ]


# --- Catalogo real -------------------------------------------------------


def test_real_catalog_is_valid():
    problems = project_control.validate_catalog(project_control.load_catalog())
    assert problems == [], "\n".join(problem.render() for problem in problems)


def test_real_catalog_and_documents_are_in_sync():
    arguments = argparse.Namespace(only=None)
    assert project_control.command_check(arguments) == 0


def test_real_catalog_distinguishes_approved_from_proposed():
    catalog = project_control.load_catalog()
    approved = [task for task in catalog["tasks"] if task["approved"]]
    proposed = [task for task in catalog["tasks"] if not task["approved"]]
    assert approved, "debe existir al menos una tarea aprobada por Franco"
    assert proposed, "debe existir al menos una propuesta de ingenieria"
    origins = {task["origin"] for task in approved}
    assert origins <= {"franco"}, "una tarea aprobada solo puede provenir de Franco"


# --- Estructura y valores admitidos --------------------------------------


def test_baseline_catalog_has_no_errors():
    assert _errors(_valid_catalog()) == []


def test_duplicate_task_id_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"].append(copy.deepcopy(catalog["tasks"][0]))
    assert any("duplicado" in message for message in _errors(catalog))


def test_invalid_priority_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["priority"] = "P9"
    assert any("fuera de" in message for message in _errors(catalog))


def test_invalid_status_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["status"] = "haciendo"
    assert any("fuera de" in message for message in _errors(catalog))


def test_invalid_origin_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["origin"] = "idea"
    assert any("fuera de" in message for message in _errors(catalog))


def test_unsupported_schema_version_is_rejected():
    catalog = _valid_catalog()
    catalog["meta"]["schema_version"] = 99
    assert any("no soportada" in message for message in _errors(catalog))


def test_module_state_contradicting_in_main_is_rejected():
    catalog = _valid_catalog()
    catalog["modules"][0]["in_main"] = True
    catalog["modules"][0]["state"] = "in_development"
    assert any("contradice" in message for message in _errors(catalog))


def test_task_without_acceptance_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["acceptance"] = []
    assert "tasks[0].acceptance" in _error_locations(catalog)


def test_task_without_approved_flag_is_rejected():
    catalog = _valid_catalog()
    del catalog["tasks"][0]["approved"]
    assert "tasks[0].approved" in _error_locations(catalog)


def test_task_without_evidence_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["evidence"] = "   "
    assert "tasks[0].evidence" in _error_locations(catalog)


# --- Dependencias --------------------------------------------------------


def test_unknown_dependency_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["depends_on"] = ["NO-EXISTE"]
    assert any("dependencia inexistente" in message for message in _errors(catalog))
    assert "tasks[0].depends_on[0]" in _error_locations(catalog)


def test_dependency_cycle_is_rejected():
    catalog = _valid_catalog()
    first = catalog["tasks"][0]
    second = copy.deepcopy(first)
    second["id"] = "TAREA-002"
    first["depends_on"] = ["TAREA-002"]
    second["depends_on"] = ["TAREA-001"]
    catalog["tasks"].append(second)
    assert any("ciclo de dependencias" in message for message in _errors(catalog))


def test_task_depending_on_itself_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["depends_on"] = ["TAREA-001"]
    assert any("no puede depender de si misma" in message for message in _errors(catalog))


def test_duplicate_github_issue_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["github_issue"] = 7
    second = copy.deepcopy(catalog["tasks"][0])
    second["id"] = "TAREA-002"
    catalog["tasks"].append(second)
    assert any("ya esta registrado" in message for message in _errors(catalog))


def test_non_positive_github_issue_is_rejected():
    catalog = _valid_catalog()
    catalog["tasks"][0]["github_issue"] = -1
    assert any("numero de issue positivo" in message for message in _errors(catalog))


# --- Renderizado ---------------------------------------------------------


def test_render_is_deterministic():
    catalog = project_control.load_catalog()
    first = project_control._render_all(catalog, None)
    second = project_control._render_all(copy.deepcopy(catalog), None)
    assert first == second
    assert all(content.endswith("\n") for content in first.values())


def test_render_preserves_utf8_and_accents():
    catalog = _valid_catalog()
    catalog["tasks"][0]["title"] = "Importar desde PDF con revisiòn — ñandú"
    catalog["tasks"][0]["description"] = "Acentuación, emeñe y símbolos: áéíóú."
    rendered = project_control._render_all(catalog, "BACKLOG")
    assert "revisiòn" in rendered["BACKLOG.md"]
    assert "ñandú" in rendered["BACKLOG.md"]
    assert "Acentuación" in rendered["BACKLOG.md"]


def test_generated_documents_carry_the_generated_notice():
    catalog = project_control.load_catalog()
    rendered = project_control._render_all(catalog, None)
    for filename, content in rendered.items():
        assert project_control.GENERATED_NOTICE in content, filename


def test_render_refuses_an_invalid_catalog(tmp_path, monkeypatch):
    catalog = _valid_catalog()
    catalog["tasks"][0]["acceptance"] = []
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    monkeypatch.setattr(project_control, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(project_control, "DOCUMENTS_DIRECTORY", tmp_path)

    assert project_control.command_render(argparse.Namespace(only=None)) == 1
    assert not list(tmp_path.glob("*.md"))


# --- check: solo lectura -------------------------------------------------


def test_check_does_not_modify_documents():
    targets = [
        project_control.DOCUMENTS_DIRECTORY / filename
        for filename in project_control.GENERATED_DOCUMENTS.values()
    ]
    before = {target: hashlib.sha256(target.read_bytes()).hexdigest() for target in targets}
    catalog_before = hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()

    assert project_control.command_check(argparse.Namespace(only=None)) == 0

    after = {target: hashlib.sha256(target.read_bytes()).hexdigest() for target in targets}
    assert before == after
    assert catalog_before == hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()


def test_check_reports_drift_without_writing(tmp_path, monkeypatch):
    documents = tmp_path / "docs"
    documents.mkdir()
    catalog = _valid_catalog()
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(project_control, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(project_control, "DOCUMENTS_DIRECTORY", documents)

    assert project_control.command_check(argparse.Namespace(only=None)) == 1

    project_control.command_render(argparse.Namespace(only=None))
    assert project_control.command_check(argparse.Namespace(only=None)) == 0

    drifted = documents / "BACKLOG.md"
    drifted.write_text(
        drifted.read_text(encoding="utf-8") + "\nlinea editada a mano\n", encoding="utf-8"
    )
    drifted_hash = hashlib.sha256(drifted.read_bytes()).hexdigest()

    assert project_control.command_check(argparse.Namespace(only=None)) == 1
    assert hashlib.sha256(drifted.read_bytes()).hexdigest() == drifted_hash


def test_check_detects_a_missing_document(tmp_path, monkeypatch):
    documents = tmp_path / "docs"
    documents.mkdir()
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(_valid_catalog()), encoding="utf-8")
    monkeypatch.setattr(project_control, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(project_control, "DOCUMENTS_DIRECTORY", documents)

    assert project_control.command_check(argparse.Namespace(only=None)) == 1


# --- Entradas invalidas --------------------------------------------------


def test_invalid_json_is_reported_not_raised(tmp_path):
    broken = tmp_path / "catalog.json"
    broken.write_text("{ esto no es json", encoding="utf-8")
    with pytest.raises(project_control.CatalogError):
        project_control.load_catalog(broken)


def test_missing_catalog_is_reported(tmp_path):
    with pytest.raises(project_control.CatalogError):
        project_control.load_catalog(tmp_path / "no-existe.json")


def test_non_object_catalog_is_rejected(tmp_path):
    listed = tmp_path / "catalog.json"
    listed.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(project_control.CatalogError):
        project_control.load_catalog(listed)


def test_validate_and_status_do_not_write():
    targets = [
        project_control.DOCUMENTS_DIRECTORY / filename
        for filename in project_control.GENERATED_DOCUMENTS.values()
    ]
    before = {target: hashlib.sha256(target.read_bytes()).hexdigest() for target in targets}
    assert project_control.command_validate(argparse.Namespace()) == 0
    assert project_control.command_status(argparse.Namespace()) == 0
    after = {target: hashlib.sha256(target.read_bytes()).hexdigest() for target in targets}
    assert before == after


# --- Restricciones de diseno ---------------------------------------------


def test_tool_has_no_network_or_subprocess_imports():
    source = TOOL_PATH.read_text(encoding="utf-8")
    forbidden = re.findall(r"^\s*(?:import|from)\s+(\w+)", source, flags=re.MULTILINE)
    banned = {"socket", "urllib", "http", "requests", "subprocess", "ssl", "ftplib", "asyncio"}
    assert not banned.intersection(forbidden), f"imports prohibidos: {banned.intersection(forbidden)}"


def test_tool_never_references_the_application_database():
    source = TOOL_PATH.read_text(encoding="utf-8")
    for forbidden in ("sqlite3", "app.db", "get_data_dir", "from app"):
        assert forbidden not in source, f"la herramienta no debe conocer {forbidden}"


def test_tool_lives_outside_the_application_package():
    assert TOOL_PATH.parts[-2] == "tools"
    assert not (REPOSITORY_ROOT / "app" / "tools").exists()


def test_catalog_is_not_inside_the_application_data_directory():
    assert "data" not in CATALOG_PATH.parts
    assert CATALOG_PATH.suffix == ".json"


# --- Integridad de las referencias que introduce el Control Center -------


PCC_REQUIRED_PATHS = (
    "docs/development/project_control/catalog.json",
    "docs/development/project_control/README.md",
    "docs/development/PROJECT_STATUS.md",
    "docs/development/BACKLOG.md",
    "docs/development/ROADMAP.md",
    "docs/development/GITHUB_ISSUES_PROJECTS_GUIDE.md",
    "docs/development/GITHUB_ISSUES_PROPUESTAS.md",
    "docs/adr/ADR-0005-project-control-center.md",
    "tools/project_control.py",
    "odd/tasks/project-control-center.md",
)


def test_required_paths_exist():
    missing = [name for name in PCC_REQUIRED_PATHS if not (REPOSITORY_ROOT / name).exists()]
    assert missing == [], f"referencias del Control Center inexistentes: {missing}"


@pytest.mark.parametrize(
    "document",
    ["README.md", "docs/development/MODULE_INDEX.md", "docs/development/PROJECT_PLAYBOOK.md"],
)
def test_control_center_links_in_documents_resolve(document):
    """Toda referencia relativa a un archivo del Control Center debe resolver."""

    text = (REPOSITORY_ROOT / document).read_text(encoding="utf-8")
    # Tanto enlaces Markdown como rutas entre backticks, que es como este
    # repositorio referencia archivos en tablas y prosa.
    candidates = set(re.findall(r"\]\((docs/[^)]+|tools/[^)]+)\)", text))
    candidates |= set(re.findall(r"`(docs/[^`\n]+|tools/[^`\n]+)`", text))
    broken = sorted(name for name in candidates if not (REPOSITORY_ROOT / name).exists())
    assert broken == [], f"{document} referencia rutas inexistentes: {broken}"


def test_catalog_readme_documents_every_required_field():
    """El esquema esta documentado junto al JSON porque JSON no admite comentarios."""

    readme = (REPOSITORY_ROOT / "docs/development/project_control/README.md").read_text(encoding="utf-8")
    catalog = project_control.load_catalog()
    for field in ("approved", "origin", "depends_on", "acceptance", "github_issue", "next_action"):
        assert f"`{field}`" in readme, f"campo sin documentar: {field}"
    assert catalog["meta"]["generated_by"] == "tools/project_control.py"


# --- Regresion de los hallazgos del review --------------------------------


def test_approved_task_must_originate_from_franco():
    """La garantia depende de esto: una sugerencia no puede quedar 'aprobada'."""

    catalog = _valid_catalog()
    catalog["tasks"][0]["origin"] = "engineering"
    catalog["tasks"][0]["approved"] = True
    assert "tasks[0].approved" in _error_locations(catalog)


def test_task_cannot_depend_on_a_cancelled_task():
    catalog = _valid_catalog()
    cancelled = copy.deepcopy(catalog["tasks"][0])
    cancelled["id"] = "TAREA-002"
    cancelled["status"] = "cancelled"
    catalog["tasks"].append(cancelled)
    catalog["tasks"][0]["depends_on"] = ["TAREA-002"]
    assert any("esta cancelada" in message for message in _errors(catalog))


@pytest.mark.parametrize("malformed", [7, "TAREA-002", None, True, {"a": 1}])
def test_non_list_depends_on_does_not_crash_validation(malformed):
    catalog = _valid_catalog()
    catalog["tasks"][0]["depends_on"] = malformed
    problems = project_control.validate_catalog(catalog)
    assert any(problem.level == "error" for problem in problems)


def test_boolean_github_issue_is_rejected():
    """`isinstance(True, int)` es True: un booleano colisionaria con el issue 1."""

    catalog = _valid_catalog()
    catalog["tasks"][0]["github_issue"] = True
    assert "tasks[0].github_issue" in _error_locations(catalog)


def test_project_requires_verification_evidence():
    catalog = _valid_catalog()
    del catalog["project"]["last_verification_evidence"]
    assert "project.last_verification_evidence" in _error_locations(catalog)


def test_render_escapes_block_level_content():
    """Un salto de linea en una descripcion no debe romper el Markdown."""

    catalog = _valid_catalog()
    catalog["tasks"][0]["description"] = "Primera linea\n\n- item que parece marcado"
    catalog["tasks"][0]["acceptance"] = ["Criterio con\nsalto de linea"]
    rendered = project_control._render_all(catalog, "BACKLOG")["BACKLOG.md"]

    assert "Primera linea - item que parece marcado" in rendered
    assert "Criterio con salto de linea" in rendered
    assert "Criterio con\n" not in rendered


def test_check_detects_crlf_drift(tmp_path, monkeypatch):
    """La deriva de EOL se compara a nivel de bytes, no de texto."""

    documents = tmp_path / "docs"
    documents.mkdir()
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(_valid_catalog(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(project_control, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(project_control, "DOCUMENTS_DIRECTORY", documents)

    project_control.command_render(argparse.Namespace(only=None))
    assert project_control.command_check(argparse.Namespace(only=None)) == 0

    target = documents / "BACKLOG.md"
    target.write_bytes(target.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))

    assert project_control.command_check(argparse.Namespace(only=None)) == 1
