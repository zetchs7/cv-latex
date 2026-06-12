from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from markupsafe import Markup


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTATION_SOURCE_DIR = REPO_ROOT / "docs" / "user"
DOCUMENTATION_OUTPUT_DIR = REPO_ROOT / "app" / "static" / "docs"
DOCUMENTATION_BUILD_DIR = REPO_ROOT / "data" / "documentation-build"
PDFLATEX_COMMAND = "pdflatex"
PDFLATEX_TIMEOUT_SECONDS = 45
DOCUMENTATION_RELEASE_VERSION = "v0.9.0"
DOCUMENTATION_RELEASE_DATE = "2026-06-11"
DOCUMENTATION_STATUS = "Release estable local"


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


@dataclass(frozen=True)
class DocumentationBlock:
    kind: str
    content: object


@dataclass(frozen=True)
class DocumentationSection:
    anchor: str
    title: str
    tone: str
    blocks: tuple[DocumentationBlock, ...]


@dataclass(frozen=True)
class DocumentationPage:
    asset: DocumentationAsset
    heading: str
    intro: str
    sections: tuple[DocumentationSection, ...]


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


def load_documentation_page(document_key: str) -> DocumentationPage | None:
    asset = get_documentation_asset(document_key)
    if asset is None:
        return None

    markdown_content = asset.source_path.read_text(encoding="utf-8")
    heading, sections = _parse_markdown_sections(markdown_content)
    intro = _extract_intro(sections) or asset.summary

    return DocumentationPage(
        asset=asset,
        heading=heading,
        intro=intro,
        sections=sections,
    )


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
    DOCUMENTATION_BUILD_DIR.mkdir(parents=True, exist_ok=True)

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

        for _ in range(2):
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
    escaped_status = _escape_latex(DOCUMENTATION_STATUS)

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
\usepackage[table]{{xcolor}}
\usepackage{{fancyvrb}}
\usepackage{{fancyhdr}}
\usepackage{{titlesec}}
\usepackage{{needspace}}
\usepackage[most]{{tcolorbox}}
\geometry{{margin=2.05cm, top=2.2cm, bottom=2.35cm}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{0.62em}}
\renewcommand{{\arraystretch}}{{1.28}}
\definecolor{{DocPaper}}{{HTML}}{{fbf8f1}}
\definecolor{{DocSurface}}{{HTML}}{{fffdf8}}
\definecolor{{DocAccent}}{{HTML}}{{8c5a37}}
\definecolor{{DocAccentDark}}{{HTML}}{{6e4225}}
\definecolor{{DocBorder}}{{HTML}}{{d8c7b5}}
\definecolor{{DocMuted}}{{HTML}}{{6b5f54}}
\definecolor{{DocRow}}{{HTML}}{{f4ede2}}
\definecolor{{DocCalloutBg}}{{HTML}}{{fff7ed}}
\definecolor{{DocCalloutTitle}}{{HTML}}{{fff7ef}}
\pagecolor{{DocPaper}}
\color{{black}}
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyhead[L]{{\small\textcolor{{DocMuted}}{{CV LaTeX Builder}}}}
\fancyhead[R]{{\small\textcolor{{DocMuted}}{{{DOCUMENTATION_RELEASE_VERSION}}}}}
\fancyfoot[L]{{\small\textcolor{{DocMuted}}{{{escaped_title}}}}}
\fancyfoot[R]{{\small\textcolor{{DocMuted}}{{Pagina \thepage}}}}
\renewcommand{{\headrulewidth}}{{0.3pt}}
\renewcommand{{\footrulewidth}}{{0.3pt}}
\titleformat{{\section}}{{\Large\bfseries\color{{DocAccentDark}}}}{{}}{{0pt}}{{}}
\titleformat{{\subsection}}{{\large\bfseries\color{{DocAccentDark}}}}{{}}{{0pt}}{{}}
\titleformat{{\subsubsection}}{{\normalsize\bfseries\color{{DocAccent}}}}{{}}{{0pt}}{{}}
\hypersetup{{
    colorlinks=true,
    linkcolor=DocAccentDark,
    urlcolor=DocAccentDark
}}
\DefineVerbatimEnvironment{{DocCode}}{{Verbatim}}{{fontsize=\small, frame=single, framesep=3mm, rulecolor=\color{{DocAccent}}}}
\newtcolorbox{{DocCallout}}[1]{{
    enhanced,
    breakable,
    colback=DocCalloutBg,
    colbacktitle=DocAccent,
    colframe=DocAccent,
    coltitle=DocCalloutTitle,
    fonttitle=\bfseries,
    title=#1,
    boxrule=0.7pt,
    arc=2mm,
    left=4mm,
    right=4mm,
    top=2mm,
    bottom=2mm
}}
\begin{{document}}
\begin{{titlepage}}
\vspace*{{1.2cm}}
{{\color{{DocAccent}}\rule{{\linewidth}}{{1.4pt}}}}\\[1.2cm]
{{\Huge\bfseries\color{{DocAccentDark}} {escaped_title}}}\\[0.6cm]
{{\Large CV LaTeX Builder}}\\[1.2cm]
\begin{{DocCallout}}{{Resumen del documento}}
\textbf{{Version:}} {DOCUMENTATION_RELEASE_VERSION}\\
\textbf{{Fecha:}} {DOCUMENTATION_RELEASE_DATE}\\
\textbf{{Estado:}} {escaped_status}\\
\textbf{{Proyecto:}} documentacion HTML/PDF servida localmente.
\end{{DocCallout}}
\vfill
{{\color{{DocAccent}}\rule{{\linewidth}}{{0.8pt}}}}\\[0.25cm]
{{\small Documento generado desde fuentes Markdown versionadas en \texttt{{docs/user}}.}}
\end{{titlepage}}
\tableofcontents
\newpage
{body}
\end{{document}}
"""


def _parse_markdown_sections(markdown_content: str) -> tuple[str, tuple[DocumentationSection, ...]]:
    lines = markdown_content.splitlines()
    heading = ""
    sections: list[DocumentationSection] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("# "):
            heading = stripped[2:].strip()
            continue

        if stripped.startswith("## "):
            if current_title is not None:
                sections.append(_build_section(current_title, current_lines))
            current_title = stripped[3:].strip()
            current_lines = []
            continue

        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append(_build_section(current_title, current_lines))

    return heading, tuple(sections)


def _build_section(title: str, lines: list[str]) -> DocumentationSection:
    blocks = _parse_section_blocks(lines)
    anchor = _slugify(title)
    tone = _section_tone(title)

    return DocumentationSection(
        anchor=anchor,
        title=title,
        tone=tone,
        blocks=tuple(blocks),
    )


def _parse_section_blocks(lines: list[str]) -> list[DocumentationBlock]:
    blocks: list[DocumentationBlock] = []
    paragraph_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        paragraph = " ".join(line.strip() for line in paragraph_lines).strip()
        if paragraph:
            blocks.append(DocumentationBlock(kind="paragraph", content=_format_inline_html(paragraph)))
        paragraph_lines.clear()

    while index < len(lines):
        stripped = lines[index].strip()

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
            blocks.append(DocumentationBlock(kind="code", content="\n".join(code_lines)))
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            callout, next_index = _consume_callout(lines, index)
            blocks.append(
                DocumentationBlock(
                    kind="callout",
                    content={
                        "tone": callout["tone"],
                        "title": _format_inline_html(str(callout["title"])),
                        "body": tuple(_format_inline_html(item) for item in callout["body"]),
                    },
                )
            )
            index = next_index
            continue

        if _is_table_header(lines, index):
            flush_paragraph()
            table_rows, next_index = _consume_table(lines, index)
            blocks.append(
                DocumentationBlock(
                    kind="table",
                    content={
                        "headers": tuple(_format_inline_html(cell) for cell in table_rows[0]),
                        "rows": tuple(
                            tuple(_format_inline_html(cell) for cell in row)
                            for row in table_rows[1:]
                        ),
                    },
                )
            )
            index = next_index
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            blocks.append(DocumentationBlock(kind="subheading", content=_format_inline_html(stripped[4:].strip())))
            index += 1
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            items, next_index = _consume_list(lines, index, ordered=False)
            blocks.append(
                DocumentationBlock(
                    kind="list",
                    content=tuple(_format_inline_html(item) for item in items),
                )
            )
            index = next_index
            continue

        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            items, next_index = _consume_list(lines, index, ordered=True)
            blocks.append(
                DocumentationBlock(
                    kind="ordered_list",
                    content=tuple(_format_inline_html(item) for item in items),
                )
            )
            index = next_index
            continue

        paragraph_lines.append(stripped)
        index += 1

    flush_paragraph()
    return blocks


def _extract_intro(sections: tuple[DocumentationSection, ...]) -> str:
    for section in sections:
        for block in section.blocks:
            if block.kind == "paragraph":
                return str(block.content)
    return ""


def _section_tone(title: str) -> str:
    normalized = title.lower()

    if "resumen" in normalized or "objetivo" in normalized or "estado final" in normalized:
        return "summary"
    if "comando" in normalized or "levantar" in normalized or "tests" in normalized or "backup" in normalized or "restore" in normalized:
        return "commands"
    if "riesgo" in normalized or "alcance" in normalized:
        return "warning"
    if "backlog" in normalized:
        return "backlog"
    if "como " in normalized or "git flow" in normalized or "validaciones" in normalized or "prs" in normalized:
        return "steps"
    return "neutral"


def _slugify(value: str) -> str:
    normalized = value.lower().strip()
    normalized = normalized.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    normalized = normalized.replace("ñ", "n").replace("ü", "u")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "section"


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
            output.append(r"\Needspace{6\baselineskip}")
            output.append(r"\begin{DocCode}")
            output.extend(code_lines if code_lines else [""])
            output.append(r"\end{DocCode}")
            output.append("")
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            callout, next_index = _consume_callout(lines, index)
            output.append(r"\Needspace{6\baselineskip}")
            output.append(r"\begin{DocCallout}{" + _format_inline(str(callout["title"])) + "}")
            body = [item for item in callout["body"] if str(item).strip()]
            output.append(_format_inline(" ".join(str(item) for item in body)) if body else "")
            output.append(r"\end{DocCallout}")
            output.append("")
            index = next_index
            continue

        if _is_table_header(lines, index):
            flush_paragraph()
            table_rows, next_index = _consume_table(lines, index)
            output.append(r"\Needspace{7\baselineskip}")
            output.extend(_render_table(table_rows))
            output.append("")
            index = next_index
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            index += 1
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            heading = _format_inline(stripped[3:].strip())
            output.append(r"\Needspace{7\baselineskip}")
            output.append(r"\phantomsection")
            output.append(r"\addcontentsline{toc}{subsection}{" + heading + "}")
            output.append(r"\subsection*{" + heading + "}")
            output.append("")
            index += 1
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            heading = _format_inline(stripped[4:].strip())
            output.append(r"\Needspace{5\baselineskip}")
            output.append(r"\phantomsection")
            output.append(r"\addcontentsline{toc}{subsubsection}{" + heading + "}")
            output.append(r"\subsubsection*{" + heading + "}")
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
    column_spec = "|" + "|".join("p{0.27\\textwidth}" for _ in range(column_count)) + "|"
    rendered = [
        r"\rowcolors{2}{DocRow}{DocSurface}",
        r"\begin{longtable}{" + column_spec + "}",
        r"\hline",
    ]

    header = rows[0]
    rendered.append(" & ".join(r"\textbf{" + _format_inline(cell) + "}" for cell in header) + r" \\ \hline")

    for row in rows[1:]:
        normalized_row = row + [""] * (column_count - len(row))
        rendered.append(" & ".join(_format_inline(cell) for cell in normalized_row[:column_count]) + r" \\ \hline")

    rendered.append(r"\end{longtable}")
    rendered.append(r"\rowcolors{2}{}{}")
    return rendered


def _consume_callout(lines: list[str], start_index: int) -> tuple[dict[str, object], int]:
    raw_items: list[str] = []
    index = start_index

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped.startswith(">"):
            break
        raw_items.append(stripped[1:].strip())
        index += 1

    first = raw_items[0] if raw_items else ""
    match = re.match(r"^\[!([A-Za-z0-9_-]+)\]\s*(.*)$", first)
    if match:
        tone = match.group(1).lower()
        title = match.group(2).strip() or tone.title()
        body = raw_items[1:]
    else:
        tone = "nota"
        title = "Nota"
        body = raw_items

    return {"tone": tone, "title": title, "body": body}, index


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


def _format_inline_html(text: str) -> Markup:
    parts = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", text)
    rendered: list[str] = []

    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            rendered.append(f"<code>{_escape_html(part[1:-1])}</code>")
            continue
        if part.startswith("**") and part.endswith("**"):
            rendered.append(f"<strong>{_escape_html(part[2:-2])}</strong>")
            continue
        rendered.append(_escape_html(part))

    return Markup("".join(rendered))


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


def _escape_html(value: str) -> str:
    escaped = value
    for source, target in (
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
        ('"', "&quot;"),
        ("'", "&#39;"),
    ):
        escaped = escaped.replace(source, target)
    return escaped


if __name__ == "__main__":
    generated_files = generate_all_documentation_pdfs()
    for generated_file in generated_files:
        print(generated_file)
