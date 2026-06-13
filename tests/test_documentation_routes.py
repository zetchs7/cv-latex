import unittest
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.documentation_service import _compile_latex_to_pdf, _render_markdown_document


class DocumentationRoutesTest(unittest.TestCase):
    def test_renders_documentation_index(self):
        with TestClient(app) as client:
            response = client.get("/documentation/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Centro de documentacion", response.text)
        self.assertIn("Documentacion tecnica", response.text)
        self.assertIn("Manual de uso web", response.text)
        self.assertIn("Leer en la web", response.text)
        self.assertNotIn("Abrir PDF directo", response.text)
        self.assertNotIn("iframe", response.text)

    def test_renders_technical_document_as_html(self):
        with TestClient(app) as client:
            response = client.get("/documentation/technical")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Documentacion tecnica", response.text)
        self.assertIn("Indice", response.text)
        self.assertIn("Arquitectura general", response.text)
        self.assertIn("Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf", response.text)
        self.assertIn("Release actual publicado", response.text)
        self.assertIn("v0.9.0", response.text)
        self.assertIn("PR <code>#8</code>", response.text)
        self.assertIn("PR <code>#9</code>", response.text)
        self.assertIn("Dashboard privado disponible", response.text)
        self.assertIn("Prompt IDs", response.text)
        self.assertIn("documentation-callout", response.text)
        self.assertNotIn("Abrir PDF directo", response.text)
        self.assertNotIn("iframe", response.text)
        self.assertNotIn("Rama visual actual", response.text)
        self.assertNotIn("feature/ui-private-dashboard", response.text)

    def test_renders_usage_document_as_html(self):
        with TestClient(app) as client:
            response = client.get("/documentation/usage")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Manual de uso web", response.text)
        self.assertIn("Como levantar la app", response.text)
        self.assertIn("Manual_Uso_Web_CV_LaTeX_Builder.pdf", response.text)
        self.assertIn("Prompt IDs", response.text)
        self.assertIn("documentation-callout", response.text)
        self.assertNotIn("Abrir PDF directo", response.text)
        self.assertNotIn("iframe", response.text)

    def test_returns_not_found_for_unknown_document(self):
        with TestClient(app) as client:
            response = client.get("/documentation/otra-cosa")

        self.assertEqual(response.status_code, 404)

    def test_pdf_latex_populates_toc_for_unnumbered_headings(self):
        latex = _render_markdown_document(
            "Documento de prueba",
            "# Documento de prueba\n\n## Seccion principal\n\nTexto.\n\n### Detalle interno\n\nMas texto.",
        )

        self.assertIn(r"\tableofcontents", latex)
        self.assertIn(r"\addcontentsline{toc}{subsection}{Seccion principal}", latex)
        self.assertIn(r"\addcontentsline{toc}{subsubsection}{Detalle interno}", latex)
        self.assertIn(r"\usepackage{needspace}", latex)
        self.assertIn(r"\Needspace{8\baselineskip}", latex)
        self.assertIn(r"\Needspace{7\baselineskip}", latex)

    def test_pdf_latex_keeps_short_lists_together(self):
        latex = _render_markdown_document(
            "Documento de prueba",
            "# Documento de prueba\n\n## Validaciones realizadas\n\n- Primer chequeo.\n- Segundo chequeo.\n- Tercer chequeo.",
        )

        self.assertIn(r"\Needspace{10\baselineskip}", latex)
        self.assertIn(r"\begin{samepage}", latex)
        self.assertIn(r"\begin{itemize}[leftmargin=1.5em]", latex)
        self.assertIn(r"\end{samepage}", latex)

    def test_pdf_compilation_runs_two_passes_for_toc(self):
        def successful_pdflatex(command, cwd, **kwargs):
            Path(cwd, "documentation.pdf").write_bytes(b"%PDF-1.4\n")
            return CompletedProcess(command, 0, "", "")

        with TemporaryDirectory() as output_directory:
            output_path = Path(output_directory) / "documentation.pdf"
            with patch(
                "app.services.documentation_service.subprocess.run",
                side_effect=successful_pdflatex,
            ) as run_pdflatex:
                _compile_latex_to_pdf(r"\documentclass{article}\begin{document}OK\end{document}", output_path)

        self.assertEqual(run_pdflatex.call_count, 2)


if __name__ == "__main__":
    unittest.main()
