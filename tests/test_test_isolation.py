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

from app.database import get_data_dir, get_database_path
from app.services import documentation_service
from app.services.export_service import ensure_exports_directory, ensure_pdf_temp_root


REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_DATA_DIR = REPO_ROOT / "data"
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


# Defined last on purpose: pytest runs tests in definition order, so this one
# compares the end of the run against the snapshot taken at collection time.
def test_repository_data_dir_is_unchanged_after_the_suite_ran():
    for watched_directory, snapshot_at_collection_time in SNAPSHOT_AT_COLLECTION_TIME.items():
        assert snapshot_directory_tree(watched_directory) == snapshot_at_collection_time, (
            f"La suite modifico {watched_directory}, que pertenece al entorno real de la app."
        )


def _render_fictional_document() -> str:
    return "\\documentclass{article}\n\\begin{document}Fictional\n\\end{document}\n"