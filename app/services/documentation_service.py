from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTATION_SOURCE_DIR = REPO_ROOT / "docs" / "user"
DOCUMENTATION_OUTPUT_DIR = REPO_ROOT / "app" / "static" / "docs"
DOCUMENTATION_BUILD_DIR = REPO_ROOT / "data" / "documentation-build"
PDFLATEX_COMMAND = "pdflatex"
PDFLATEX_TIMEOUT_SECONDS = 45


@dataclass(frozen=True)
class DocumentationAsset:
    key: str
    title: str
    summary: str
    source_markdown: str
    pdf_filename: str

    @property
    def source_path(self) -> Path:
        return DOCUMENTATION_SOURCE_DIR / self.source_markdown

    @property
    def output_path(self) -> Path:
        return DOCUMENTATION_OUTPUT_DIR / self.pdf_filename


DOCUMENTATION_ASSETS = (
    DocumentationAsset(
        key="technical",
        title="Documentacion tecnica",
        summary="Arquitectura, modulos, persistencia, validaciones, Git Flow y estado final del MVP local.",
        source_markdown="PROJECT_TECHNICAL_DOCUMENTATION.md",
        pdf_filename="Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf",
    ),
    DocumentationAsset(
        key="usage",
        title="Manual de uso web",
        summary="Guia operativa para levantar la app, usar cada modulo y localizar exports, tests y backups.",
        source_markdown="WEB_USAGE_MANUAL.md",
        pdf_filename="Manual_Uso_Web_CV_LaTeX_Builder.pdf",
    ),
)

DOCUMENTATION_ASSET_BY_KEY = {asset.key: asset for asset in DOCUMENTATION_ASSETS}


class DocumentationGenerationError(RuntimeError):
    pass


def list_documentation_assets() -> tuple[DocumentationAsset, ...]:
    return DOCUMENTATION_ASSETS


def get_documentation_asset(document_key: str) -> DocumentationAsset | None:
    return DOCUMENTATION_ASSET_BY_KEY.get(document_key)


def generate_all_documentation_pdfs() -> list[Path]:
    DOCUMENTATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTATION_BUILD_DIR.mkdir(parents=True, exist_ok=True)

    generated_paths: list[Path] = []

    for asset in DOCUMENTATION_ASSETS:
        markdown_content = asset.source_path.read_text(encoding="utf-8")
        latex_content = _render_markdown_document(asset.title, markdown_content)
        _compile_latex_to_pdf(latex_content, asset.output_path)
        generated_paths.append(asset.output_path)

    return generated_paths


def _compile_latex_to_pdf(latex_content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="docs-pdf-", dir=DOCUMENTATION_BUILD_DIR) as temp_directory_name:
        temp_directory = Path(temp_directory_name)
        tex_path = temp_directory / "documentation.tex"
        tex_path.write_text(latex_content, encoding="utf-8")

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
                timeout=PDFLATEX_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError as error:
            raise DocumentationGenerationError("pdflatex no esta disponible para generar los PDFs de documentacion.") from error
        except subprocess.TimeoutExpired as error:
            raise DocumentationGenerationError("La generacion de PDFs de documentacion excedio el tiempo maximo permitido.") from error

        if result.returncode != 0:
            error_excerpt = _build_latex_error_excerpt(result.stdout, result.stderr, temp_directory / "documentation.log")
            raise DocumentationGenerationError(
                "No se pudo compilar uno de los PDFs de documentacion.\n" + error_excerpt
            )

        compiled_pdf = temp_directory / "documentation.pdf"
        if not compiled_pdf.exists():
            raise DocumentationGenerationError("La compilacion finalizo sin generar el archivo PDF esperado.")

        shutil.copy2(compiled_pdf, output_path)


def _build_latex_error_excerpt(stdout: str, stderr: str, log_path: Path) -> str:
    candidates = [stderr.strip(), stdout.strip()]
    if log_path.exists():
        candidates.append(log_path.read_text(encoding="utf-8", errors="replace").strip())

    for candidate in candidates:
        if candidate:
            lines = [line.strip() for line in candidate.splitlines() if line.strip()]
            return "\n".join(lines[-12:])

    return "sin detalle disponible."


def _render_markdown_document(title: str, markdown_content: str) -> str:
    body = _markdown_to_latex(markdown_content)
    escaped_title = _escape_latex(title)

    return rf"""\documentclass[11pt,a4paper]{{article}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage[spanish]{{babel}}
\usepackage{{lmodern}}
\usepackage{{geometry}}
\usepackage{{hyperref}}
\usepackage{{enumitem}}
\usepackage{{longtable}}
\usepackage{{array}}
\usepackage{{xcolor}}
\usepackage{{fancyvrb}}
\geometry{{margin=2cm}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0.75em}}
\hypersetup{{
    colorlinks=true,
    linkcolor=black,
    urlcolor=blue
}}
\DefineVerbatimEnvironment{{DocCode}}{{Verbatim}}{{fontsize=\small, frame=single}}
\begin{{document}}
\begin{{center}}
{{\LARGE \textbf{{{escaped_title}}}}}\\[0.5em]
\end{{center}}
{body}
\end{{document}}
"""


def _markdown_to_latex(markdown_content: str) -> str:
    lines = markdown_content.splitlines()
    output: list[str] = []
    paragraph_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        paragraph = " ".join(line.strip() for line in paragraph_lines).strip()
        if paragraph:
            output.append(_format_inline(paragraph))
            output.append("")
        paragraph_lines.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            output.append(r"\begin{DocCode}")
            output.extend(code_lines if code_lines else [""])
            output.append(r"\end{DocCode}")
            output.append("")
            index += 1
            continue

        if _is_table_header(lines, index):
            flush_paragraph()
            table_rows, next_index = _consume_table(lines, index)
            output.extend(_render_table(table_rows))
            output.append("")
            index = next_index
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            output.append(r"\section*{" + _format_inline(stripped[2:].strip()) + "}")
            output.append("")
            index += 1
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            output.append(r"\subsection*{" + _format_inline(stripped[3:].strip()) + "}")
            output.append("")
            index += 1
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            output.append(r"\subsubsection*{" + _format_inline(stripped[4:].strip()) + "}")
            output.append("")
            index += 1
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            items, next_index = _consume_list(lines, index, ordered=False)
            output.append(r"\begin{itemize}[leftmargin=1.5em]")
            output.extend(r"\item " + _format_inline(item) for item in items)
            output.append(r"\end{itemize}")
            output.append("")
            index = next_index
            continue

        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            items, next_index = _consume_list(lines, index, ordered=True)
            output.append(r"\begin{enumerate}[leftmargin=1.8em]")
            output.extend(r"\item " + _format_inline(item) for item in items)
            output.append(r"\end{enumerate}")
            output.append("")
            index = next_index
            continue

        paragraph_lines.append(stripped)
        index += 1

    flush_paragraph()
    return "\n".join(output).strip() + "\n"


def _is_table_header(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False

    header = lines[index].strip()
    separator = lines[index + 1].strip()

    return (
        header.startswith("|")
        and header.endswith("|")
        and separator.startswith("|")
        and separator.endswith("|")
        and set(separator.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")) == set()
    )


def _consume_table(lines: list[str], start_index: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start_index

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            break
        if set(stripped.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")) == set():
            index += 1
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append(cells)
        index += 1

    return rows, index


def _render_table(rows: list[list[str]]) -> list[str]:
    column_count = len(rows[0])
    column_spec = "|" + "|".join("p{0.28\\textwidth}" for _ in range(column_count)) + "|"
    rendered = [
        r"\renewcommand{\arraystretch}{1.2}",
        r"\begin{longtable}{" + column_spec + "}",
        r"\hline",
    ]

    header = rows[0]
    rendered.append(" & ".join(r"\textbf{" + _format_inline(cell) + "}" for cell in header) + r" \\ \hline")

    for row in rows[1:]:
        normalized_row = row + [""] * (column_count - len(row))
        rendered.append(" & ".join(_format_inline(cell) for cell in normalized_row[:column_count]) + r" \\ \hline")

    rendered.append(r"\end{longtable}")
    return rendered


def _consume_list(lines: list[str], start_index: int, ordered: bool) -> tuple[list[str], int]:
    items: list[str] = []
    index = start_index
    pattern = r"^\d+\.\s+" if ordered else r"^[-*]\s+"

    while index < len(lines):
        stripped = lines[index].strip()
        if not re.match(pattern, stripped):
            break
        items.append(re.sub(pattern, "", stripped, count=1).strip())
        index += 1

    return items, index


def _format_inline(text: str) -> str:
    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", text)
    rendered: list[str] = []

    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            rendered.append(r"\texttt{" + _escape_latex(part[1:-1]) + "}")
            continue
        if part.startswith("**") and part.endswith("**"):
            rendered.append(r"\textbf{" + _format_inline(part[2:-2]) + "}")
            continue
        rendered.append(_escape_latex(part))

    return "".join(rendered)


def _escape_latex(value: str) -> str:
    escaped = value
    for source, target in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ):
        escaped = escaped.replace(source, target)
    return escaped


if __name__ == "__main__":
    generated_files = generate_all_documentation_pdfs()
    for generated_file in generated_files:
        print(generated_file)
