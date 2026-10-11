"""Pruebas que demuestran que la suite de pytest nunca toca el entorno real.

La app persiste en ``data/app.db`` y exporta en ``data/exports``. Ese directorio
es el entorno real del usuario: la suite debe escribir siempre en un temporal
nuevo y fallar de forma cerrada si no logra aislarse.

Este modulo se importa durante la coleccion, antes de ejecutar cualquier prueba,
por lo que el snapshot de abajo es la referencia del inicio de la corrida.
"""

from pathlib import Path
import os
import subprocess
import sys
import tempfile

import pytest
from unittest.mock import patch

import conftest

from app.database import get_data_dir, get_database_path
from app.services import documentation_service
from app.services.export_service import ensure_exports_directory, ensure_pdf_temp_root


REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_DATA_DIR = REPO_ROOT / "data"
REPOSITORY_DOCS_OUTPUT_DIR = REPO_ROOT / "app" / "static" / "docs"
DOCUMENTATION_OUTPUT_DIR = REPO_ROOT / "app" / "static" / "docs"
SYSTEM_TEMP_ROOT = Path(tempfile.gettempdir()).resolve()
TESTING_MARKER_ENV_VAR = "CV_LATEX_TESTING"


def snapshot_directory_tree(root: Path) -> dict[str, tuple[int, int]] | None:
    """Map every entry under ``root`` to its size and modification time.

    Returns ``None`` when ``root`` does not exist, so callers can also detect
    creation of a directory that was absent at the beginning of the run.
    """

    if not root.exists():
        return None

    snapshot: dict[str, tuple[int, int]] = {}
    for path in sorted(root.rglob("*")):
        try:
            entry_stat = path.stat()
        except OSError:
            continue
        snapshot[path.relative_to(root).as_posix()] = (entry_stat.st_size, entry_stat.st_mtime_ns)

    return snapshot


# Taken while pytest collects this module, before any test in the suite runs.
SNAPSHOT_AT_COLLECTION_TIME = {
    REPOSITORY_DATA_DIR: snapshot_directory_tree(REPOSITORY_DATA_DIR),
    DOCUMENTATION_OUTPUT_DIR: snapshot_directory_tree(DOCUMENTATION_OUTPUT_DIR),
}


def test_data_dir_resolves_under_the_system_temp_root():
    data_dir = get_data_dir().resolve()

    assert data_dir == Path(os.environ["APP_DATA_DIR"]).resolve()
    assert data_dir.is_relative_to(SYSTEM_TEMP_ROOT), f"El directorio de datos no esta bajo el temporal del sistema: {data_dir}"
    assert get_database_path().resolve().is_relative_to(data_dir)


def test_data_dir_is_not_the_repository_data_dir():
    data_dir = get_data_dir().resolve()
    repository_data_dir = REPOSITORY_DATA_DIR.resolve()

    assert data_dir != repository_data_dir
    assert not data_dir.is_relative_to(repository_data_dir)


def test_documentation_build_dir_resolves_under_the_test_data_dir():
    build_dir = documentation_service.get_documentation_build_dir().resolve()
    data_dir = get_data_dir().resolve()

    assert build_dir.is_relative_to(data_dir)
    assert not build_dir.is_relative_to(REPOSITORY_DATA_DIR.resolve())


def test_documentation_compilation_writes_only_under_the_test_data_dir(monkeypatch):
    """Run the LaTeX compilation path with a fake pdflatex and a fictional document."""

    used_working_directories: list[Path] = []
    snapshot_before = snapshot_directory_tree(REPOSITORY_DATA_DIR)
    output_snapshot_before = snapshot_directory_tree(DOCUMENTATION_OUTPUT_DIR)
    fictional_output = get_data_dir() / "fictional-documentation" / "fictional.pdf"

    def fake_run(command, cwd, capture_output, text, timeout, check):
        used_working_directories.append(Path(cwd))
        (Path(cwd) / "documentation.pdf").write_bytes(b"%PDF-1.4 fictional\n")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(documentation_service.subprocess, "run", fake_run)

    documentation_service._compile_latex_to_pdf(
        _render_fictional_document(),
        fictional_output,
    )

    assert used_working_directories, "El stub de pdflatex nunca fue invocado."
    for working_directory in used_working_directories:
        assert working_directory.is_relative_to(documentation_service.get_documentation_build_dir())
        assert working_directory.is_relative_to(get_data_dir().resolve())

    build_dir = documentation_service.get_documentation_build_dir()
    assert build_dir.is_relative_to(get_data_dir().resolve())
    assert build_dir.exists()
    assert fictional_output.exists()
    assert not DOCUMENTATION_OUTPUT_DIR.joinpath("fictional.pdf").exists()

    assert snapshot_directory_tree(DOCUMENTATION_OUTPUT_DIR) == output_snapshot_before
    assert snapshot_directory_tree(REPOSITORY_DATA_DIR) == snapshot_before


def test_export_and_pdf_temp_roots_resolve_under_the_test_data_dir():
    snapshot_before = snapshot_directory_tree(REPOSITORY_DATA_DIR)
    data_dir = get_data_dir().resolve()

    exports_directory = ensure_exports_directory().resolve()
    pdf_temp_root = ensure_pdf_temp_root().resolve()

    assert exports_directory.is_relative_to(data_dir)
    assert pdf_temp_root.is_relative_to(exports_directory)
    assert not exports_directory.is_relative_to(REPOSITORY_DATA_DIR.resolve())
    assert snapshot_directory_tree(REPOSITORY_DATA_DIR) == snapshot_before


def test_guard_rejects_repository_data_dir_with_marker(monkeypatch):
    monkeypatch.setenv(TESTING_MARKER_ENV_VAR, "1")
    monkeypatch.setenv("APP_DATA_DIR", str(REPOSITORY_DATA_DIR))

    with pytest.raises(RuntimeError):
        get_data_dir()


def test_guard_rejects_repository_data_dir_when_pytest_is_loaded(monkeypatch):
    monkeypatch.delenv(TESTING_MARKER_ENV_VAR, raising=False)
    monkeypatch.setenv("APP_DATA_DIR", str(REPOSITORY_DATA_DIR))

    assert "pytest" in sys.modules, "La suite corre bajo pytest; esta deteccion debe estar disponible."

    with pytest.raises(RuntimeError):
        get_data_dir()


def test_guard_allows_repository_data_dir_without_test_detection(monkeypatch):
    monkeypatch.delenv(TESTING_MARKER_ENV_VAR, raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    monkeypatch.setenv("APP_DATA_DIR", str(REPOSITORY_DATA_DIR))

    assert get_data_dir().resolve() == REPOSITORY_DATA_DIR.resolve()


def test_default_data_dir_is_unchanged_without_test_detection(monkeypatch):
    monkeypatch.delenv(TESTING_MARKER_ENV_VAR, raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    monkeypatch.delenv("APP_DATA_DIR", raising=False)

    assert get_data_dir() == Path("/data")


def test_marker_alone_activates_the_guard_outside_pytest():
    script = (
        "from app.database import get_data_dir\n"
        "get_data_dir()\n"
    )
    environment = dict(os.environ)
    environment["APP_DATA_DIR"] = str(REPOSITORY_DATA_DIR)
    environment["CV_LATEX_TESTING"] = "1"
    environment["PYTHONPATH"] = str(REPO_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=environment,
    )

    assert result.returncode != 0, "El guard deberia rechazar el directorio de datos del repositorio."
    assert "CV_LATEX_TESTING" in result.stderr


def test_manifest_helpers_detect_a_created_and_a_modified_file():
    """`_diff_snapshots` debe ver altas y cambios sin depender del entorno.

    Trabaja sobre un temporal propio: escribir dentro de `data/` del repositorio
    no es una operacion valida y en un contenedor con rootfs de solo lectura
    ni siquiera seria posible.
    """

    with tempfile.TemporaryDirectory() as temporary_directory:
        watched_root = Path(temporary_directory)
        before = conftest._snapshot((watched_root,))
        assert conftest._diff_snapshots(before, conftest._snapshot((watched_root,))) == []

        created = watched_root / "aislamiento-ficticio.txt"
        created.write_text("contenido", encoding="utf-8")
        assert conftest._diff_snapshots(before, conftest._snapshot((watched_root,))) == [str(created)]

        before_with_file = conftest._snapshot((watched_root,))
        created.write_text("contenido distinto", encoding="utf-8")
        assert str(created) in conftest._diff_snapshots(
            before_with_file, conftest._snapshot((watched_root,))
        )

        created.unlink()
        assert conftest._diff_snapshots(before_with_file, conftest._snapshot((watched_root,))) == [str(created)]


def test_manifest_covers_a_missing_protected_directory():
    """Un directorio protegido ausente se registra, no se ignora en silencio."""

    with tempfile.TemporaryDirectory() as temporary_directory:
        absent = Path(temporary_directory) / "no-existe"
        snapshot = conftest._snapshot((absent,))
        assert snapshot == {str(absent): None}
        assert conftest._diff_snapshots(snapshot, conftest._snapshot((absent,))) == []


def test_conftest_snapshots_the_real_environment_at_import_time():
    """El baseline se toma al importar conftest y cubre cada ruta protegida."""

    baseline = conftest.PROTECTED_BASELINE
    assert baseline, "el manifiesto inicial debe estar capturado"
    for protected in conftest.PROTECTED_PATHS:
        prefix = str(protected) + os.sep
        # Una ruta protegida existente aparece a traves de sus archivos; una
        # ausente aparece con valor None.
        assert str(protected) in baseline or any(path.startswith(prefix) for path in baseline), (
            f"el manifiesto inicial no cubre {protected}"
        )


# Los dos siguientes cubren hallazgos P1 del review de codex: directorios de
# datos externos al temporal y nombres de base que escapan del temporal.
def _assert_guard_rejects(environment_overrides: dict[str, str], expected_fragment: str) -> None:
    script = (
        "from app.database import get_database_path, get_data_dir\n"
        "get_data_dir()\n"
        "get_database_path()\n"
    )
    environment = dict(os.environ)
    environment["CV_LATEX_TESTING"] = "1"
    environment["PYTHONPATH"] = str(REPO_ROOT)
    environment.update(environment_overrides)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=environment,
    )

    assert result.returncode != 0, "El guard deberia abortar la corrida."
    assert expected_fragment in result.stderr


def test_guard_rejects_the_compose_data_store_during_tests():
    """`/data` es el store real montado por Compose: no puede usarse en tests."""

    _assert_guard_rejects({"APP_DATA_DIR": "/data"}, "raiz temporal")


def test_guard_rejects_an_absolute_database_filename_during_tests():
    _assert_guard_rejects({"APP_DB_FILENAME": "/data/app.db"}, "APP_DB_FILENAME")


# Hallazgo P1 del review de codex sobre `ae64a2b`: `get_data_dir()` valida el
# directorio raiz, pero un subdirectorio derivado puede ser un enlace simbolico a
# otro arbol y las escrituras lo seguirian.
def test_derived_writes_reject_a_symlink_that_escapes_the_data_dir():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        data_directory = root / "data"
        outside_directory = root / "fuera-del-ambiente"
        data_directory.mkdir()
        outside_directory.mkdir()
        (data_directory / "exports").symlink_to(outside_directory, target_is_directory=True)
        (data_directory / documentation_service.DOCUMENTATION_BUILD_SUBDIRECTORY).symlink_to(
            outside_directory, target_is_directory=True
        )

        with patch.dict(os.environ, {"APP_DATA_DIR": str(data_directory)}):
            with pytest.raises(RuntimeError, match="directorio de exportaciones"):
                ensure_exports_directory()

            with pytest.raises(RuntimeError, match="directorio de compilacion"):
                documentation_service.get_documentation_build_dir()

        assert not list(outside_directory.iterdir()), "no debe haberse escrito fuera"


def test_derived_writes_still_work_for_a_real_subdirectory():
    """El guard no puede convertirse en un falso positivo en el caso normal."""

    with tempfile.TemporaryDirectory() as temporary_directory:
        with patch.dict(os.environ, {"APP_DATA_DIR": temporary_directory}):
            exports_directory = ensure_exports_directory()
            pdf_temp_root = ensure_pdf_temp_root()
            build_directory = documentation_service.get_documentation_build_dir()

        assert exports_directory == Path(temporary_directory) / "exports"
        assert pdf_temp_root == exports_directory / "_tmp"
        assert build_directory == (
            Path(temporary_directory) / documentation_service.DOCUMENTATION_BUILD_SUBDIRECTORY
        )
        assert exports_directory.is_dir()
        assert pdf_temp_root.is_dir()


def test_derived_paths_are_not_restricted_outside_a_test_run():
    """Fuera de una corrida de pruebas el guard es inerte y la app no cambia.

    Va en un subproceso porque `_is_test_process()` tambien detecta `pytest` en
    `sys.modules`, y en este proceso esa condicion siempre es cierta.
    """

    # No se escribe nada: se comprueba que el directorio de datos por defecto
    # sigue siendo `/data` y que el guard devuelve la ruta intacta en vez de
    # rechazarla, que es lo que haria dentro de una corrida de pruebas.
    script = (
        "from pathlib import Path\n"
        "from app.database import DEFAULT_DATA_DIR, ensure_isolated_path, get_data_dir\n"
        "assert str(get_data_dir()) == DEFAULT_DATA_DIR, get_data_dir()\n"
        "outside = Path('/data/exports')\n"
        "assert ensure_isolated_path(outside, 'exports') == outside\n"
        "print('MODO NORMAL INTACTO')\n"
    )
    environment = dict(os.environ)
    environment.pop("CV_LATEX_TESTING", None)
    environment.pop("APP_DATA_DIR", None)
    environment["PYTHONPATH"] = str(REPO_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert "MODO NORMAL INTACTO" in result.stdout


def test_guard_rejects_a_database_filename_with_parent_traversal():
    _assert_guard_rejects(
        {"APP_DB_FILENAME": "../escapada/app.db"},
        "APP_DB_FILENAME",
    )


def _render_fictional_document() -> str:
    return "\\documentclass{article}\n\\begin{document}Fictional\n\\end{document}\n"