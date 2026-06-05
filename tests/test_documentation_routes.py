import unittest

from fastapi.testclient import TestClient

from app.main import app


class DocumentationRoutesTest(unittest.TestCase):
    def test_renders_documentation_index(self):
        with TestClient(app) as client:
            response = client.get("/documentation/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Centro de documentacion", response.text)
        self.assertIn("Documentacion tecnica", response.text)
        self.assertIn("Manual de uso web", response.text)

    def test_renders_documentation_viewer_for_known_document(self):
        with TestClient(app) as client:
            response = client.get("/documentation/technical")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Documentacion tecnica", response.text)
        self.assertIn("iframe", response.text)
        self.assertIn("Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf", response.text)

    def test_returns_not_found_for_unknown_document(self):
        with TestClient(app) as client:
            response = client.get("/documentation/otra-cosa")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
