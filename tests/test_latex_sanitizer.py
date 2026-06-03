import unittest

from app.validations.latex_sanitizer import sanitize_latex_text, split_sanitized_items


class LatexSanitizerTest(unittest.TestCase):
    def test_escapes_latex_special_characters(self):
        raw_value = r"50% & $value_1# {ok} ~ ^ \ path"

        sanitized_value = sanitize_latex_text(raw_value)

        self.assertIn(r"50\%", sanitized_value)
        self.assertIn(r"\&", sanitized_value)
        self.assertIn(r"\$value\_1\#", sanitized_value)
        self.assertIn(r"\{ok\}", sanitized_value)
        self.assertIn(r"\textasciitilde{}", sanitized_value)
        self.assertIn(r"\textasciicircum{}", sanitized_value)
        self.assertIn(r"\textbackslash{}", sanitized_value)

    def test_preserves_common_spanish_characters(self):
        raw_value = "Español, acción, pingüino, ¿pregunta?, ¡exito!"

        sanitized_value = sanitize_latex_text(raw_value)

        self.assertIn("Español", sanitized_value)
        self.assertIn("acción", sanitized_value)
        self.assertIn("pingüino", sanitized_value)
        self.assertIn("¿pregunta?", sanitized_value)
        self.assertIn("¡exito!", sanitized_value)

    def test_empty_values_are_safe(self):
        self.assertEqual(sanitize_latex_text(None), "")
        self.assertEqual(sanitize_latex_text("   "), "")

    def test_splits_and_sanitizes_items(self):
        items = split_sanitized_items("Python, FastAPI\nSQLite & LaTeX")

        self.assertEqual(items, ["Python", "FastAPI", r"SQLite \& LaTeX"])


if __name__ == "__main__":
    unittest.main()
