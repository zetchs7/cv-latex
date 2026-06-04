from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile

from app.models import CV
from app.services.export_service import (
    ExportedFile,
    build_pdf_export_path,
    ensure_pdf_temp_root,
    export_generated_tex_document,
)
from app.services.latex_service import generate_cv_tex_document


PDFLATEX_COMMAND = "pdflatex"
PDF_COMPILATION_TIMEOUT_SECONDS = 45


@dataclass(frozen=True)
class PdfCompilationResult:
    exported_pdf: ExportedFile
    exported_tex: ExportedFile


class PdfCompilationError(RuntimeError):
    pass


def generate_cv_pdf_export(cv: CV, template_key: str) -> PdfCompilationResult:
    generated_document = generate_cv_tex_document(cv, template_key)
    exported_tex = export_generated_tex_document(cv, generated_document)
    export_path, filename = build_pdf_export_path(cv, generated_document.template.key)

    with tempfile.TemporaryDirectory(prefix="cv-pdf-", dir=ensure_pdf_temp_root()) as temp_directory_name:
        temp_directory = Path(temp_directory_name)
        tex_path = temp_directory / generated_document.filename
        tex_path.write_text(generated_document.content, encoding="utf-8")

        _run_pdflatex(temp_directory, tex_path)

        compiled_pdf = temp_directory / f"{tex_path.stem}.pdf"
        if not compiled_pdf.exists():
            raise PdfCompilationError("La compilacion LaTeX finalizo sin generar un PDF.")

        shutil.copy2(compiled_pdf, export_path)

    return PdfCompilationResult(
        exported_pdf=ExportedFile(path=export_path, filename=filename, media_type="application/pdf"),
        exported_tex=exported_tex,
    )


def _run_pdflatex(temp_directory: Path, tex_path: Path) -> None:
    command = [
        PDFLATEX_COMMAND,
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={temp_directory}",
        tex_path.name,
    ]

    try:
        result = subprocess.run(
            command,
            cwd=temp_directory,
            capture_output=True,
            text=True,
            timeout=PDF_COMPILATION_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as error:
        raise PdfCompilationError("El motor LaTeX 'pdflatex' no esta instalado en el contenedor.") from error
    except subprocess.TimeoutExpired as error:
        raise PdfCompilationError("La compilacion LaTeX excedio el tiempo maximo permitido.") from error

    if result.returncode != 0:
        error_output = _extract_latex_error(result.stdout, result.stderr, temp_directory / f"{tex_path.stem}.log")
        raise PdfCompilationError(f"Fallo la compilacion LaTeX: {error_output}")


def _extract_latex_error(stdout: str, stderr: str, log_path: Path) -> str:
    candidates = [stderr.strip(), stdout.strip()]
    if log_path.exists():
        candidates.append(log_path.read_text(encoding="utf-8", errors="replace").strip())

    for candidate in candidates:
        if candidate:
            return _last_relevant_lines(candidate)

    return "sin detalle disponible."


def _last_relevant_lines(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return "\n".join(lines[-12:]) if lines else "sin detalle disponible."
