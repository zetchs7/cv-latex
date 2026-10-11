import json
import re
import unittest

from app.models import CV
from app.services.ats_service import analyze_cv_ats
from app.services.structured_cv_service import (
    resolve_normalized_cv,
    serialize_structured_payload,
)

try:
    from app.services.latex_service import generate_cv_tex_document

    JINJA2_AVAILABLE = True
except ModuleNotFoundError as error:
    if error.name != "jinja2":
        raise
    JINJA2_AVAILABLE = False


CV_TEMPLATE_KEYS = ("classic", "modern", "compact", "tech")
STALE_MARKER = "SNAPSHOT-OBSOLETO-123"
# Separador de corte completo y confiable usado por structured_cv_rendering:
# la macro termina en espacio (TeX extiende nombres de control con letras
# siguientes; el espacio se consume al tokenizar) y el \hspace de ancho
# natural nulo con estiramiento minimo vuelve factible la justificacion de
# lineas sin pegamento propio; el estiramiento aplicado es invisible.
LATEX_BREAK_SEPARATOR = r"\allowbreak \hspace{0pt plus 0.06em}"

EXPECTED_TEX_MARKERS = (
    "Ana Perez",
    "Tech Lead de Plataformas",
    "Buenos Aires, Argentina",
    "ana@example.com",
    "+54 11 1234 5678",
    "https://ana.example.com",
    "Perfil estructurado",
    "Desarrolladora Backend",
    "Initech",
    "Lider Tecnico",
    "Globex",
    "Migracion progresiva a microservicios",
    "Ingenieria en Sistemas",
    "Universidad de Buenos Aires",
    "SQL (Datos, Intermedio)",
    "Python (Backend, Avanzado)",
    "Certificacion AWS Solutions Architect",
    "Professional Scrum Master",
    "Espanol (Nativo)",
    "Observabilidad Abierta",
    "https://git.example.com/obs",
    "Grafana",
    "GitHub",
    "https://github.com/anaperez",
    "Disponibilidad",
    "Full-time remoto",
)


def _full_structured_payload():
    return {
        "schema_version": 2,
        "personal": {
            "full_name": "Ana Perez",
            "headline": "Tech Lead de Plataformas",
            "location": "Buenos Aires, Argentina",
        },
        "contact": {
            "email": "ana@example.com",
            "phone": "+54 11 1234 5678",
            "links": ["https://ana.example.com", "https://linkedin.com/in/anaperez"],
        },
        "summary": "Perfil estructurado con foco en plataformas, datos y calidad.",
        "skills": [
            {"label": "Python", "category": "Backend", "level": "Avanzado", "order": 2},
            {"label": "SQL", "category": "Datos", "level": "Intermedio", "order": 1},
            {"label": "Kubernetes", "category": "Infraestructura", "level": "", "order": 3},
        ],
        "experience": [
            {
                "company": "Globex",
                "role": "Lider Tecnico",
                "location": "Remoto",
                "start_date": "2022",
                "end_date": "",
                "current": True,
                "summary": "Liderazgo de la plataforma interna.",
                "highlights": ["Diseno de plataforma", "Reduccion del tiempo de despliegue"],
                "technologies": ["Python", "FastAPI"],
                "order": 2,
                "internal_note": "dato-interno-no-renderizado",
            },
            {
                "company": "Initech",
                "role": "Desarrolladora Backend",
                "location": "Buenos Aires",
                "start_date": "2019",
                "end_date": "2022",
                "current": False,
                "summary": "Desarrollo de APIs internas.",
                "highlights": ["Migracion progresiva a microservicios"],
                "technologies": ["Django", "PostgreSQL"],
                "order": 1,
            },
        ],
        "education": [
            {
                "institution": "Universidad de Buenos Aires",
                "degree": "Ingenieria en Sistemas",
                "field": "Sistemas de informacion",
                "start_date": "2013",
                "end_date": "2019",
                "summary": "Promedio destacado y becas.",
                "order": 1,
            },
        ],
        "certifications": [
            {
                "name": "Certificacion AWS Solutions Architect",
                "issuer": "Amazon Web Services",
                "date": "2024",
                "order": 2,
            },
            {
                "name": "Professional Scrum Master",
                "issuer": "Scrum.org",
                "date": "2023",
                "order": 1,
            },
        ],
        "languages": [
            {"name": "Espanol", "level": "Nativo", "order": 1},
            {"name": "Ingles", "level": "Avanzado", "order": 2},
        ],
        "projects": [
            {
                "name": "Observabilidad Abierta",
                "summary": "Paneles y alertas listos para produccion.",
                "link": "https://git.example.com/obs",
                "technologies": ["Grafana", "Prometheus"],
                "order": 1,
            },
        ],
        "links": [
            {"label": "GitHub", "url": "https://github.com/anaperez", "order": 1},
        ],
        "additional_info": [
            {"title": "Disponibilidad", "content": "Full-time remoto con solapamiento US.", "order": 1},
        ],
        "metadata": {
            "source": "structured_test",
            "synced_from_legacy_at": "2026-10-09T00:00:00+00:00",
        },
    }


def _malicious_structured_payload():
    payload = _full_structured_payload()
    payload["personal"]["full_name"] = "Ana \\textbf{Perez}"
    payload["personal"]["headline"] = "Tech Lead 100% $ & # _ { } ~ ^"
    payload["summary"] = (
        "Linea uno.\n\nLinea dos con \\end{document} y \\section*{falso} dentro del resumen."
    )
    payload["experience"][0]["highlights"] = ["Bullet & especial con $100 _ bajo"]
    payload["experience"][0]["technologies"] = ["FastAPI^2", "Py~thon"]
    payload["projects"][0]["link"] = "https://git.example.com/obs?param=1%2F2"
    return payload


def _structured_cv(payload, *, cv_id=701, title="CV Estructurado"):
    return CV(
        id=cv_id,
        title=title,
        full_name=STALE_MARKER,
        email="stale@example.com",
        phone="",
        professional_summary=STALE_MARKER,
        experience_summary=STALE_MARKER,
        education_summary=STALE_MARKER,
        skills=STALE_MARKER,
        created_at="2026-10-09 00:00:00",
        updated_at="2026-10-09 00:00:00",
        deleted_at=None,
        structured_schema_version=2,
        structured_payload=serialize_structured_payload(payload),
        structured_payload_status="valid",
    )


def _legacy_cv(cv_id=702):
    return CV(
        id=cv_id,
        title="CV Legacy",
        full_name="Juan Perez",
        email="juan@example.com",
        phone="+54 11 2222 3333",
        professional_summary="Perfil legacy completo y orientado a resultados.",
        experience_summary="Experiencia legacy sostenida en backend y datos.",
        education_summary="Educacion legacy con formacion continua.",
        skills="Python, SQL",
        created_at="2026-10-09 00:00:00",
        updated_at="2026-10-09 00:00:00",
        deleted_at=None,
        structured_schema_version=None,
        structured_payload=None,
        structured_payload_status="legacy",
    )


def _fallback_cv(variant, *, cv_id=702):
    legacy = _legacy_cv()
    payload = _full_structured_payload()
    if variant == "corrupt":
        structured_payload = "{not-valid-json"
        structured_schema_version = 2
        structured_payload_status = "valid"
    elif variant == "stale":
        structured_payload = serialize_structured_payload(payload)
        structured_schema_version = 2
        structured_payload_status = "stale"
    elif variant == "invalid":
        structured_payload = serialize_structured_payload(payload)
        structured_schema_version = 2
        structured_payload_status = "invalid"
    elif variant == "future":
        structured_payload = json.dumps({"schema_version": 3, "personal": {"full_name": "Futuro"}})
        structured_schema_version = 3
        structured_payload_status = "valid"
    else:
        raise ValueError(f"Variante de fallback desconocida: {variant}")

    return CV(
        id=cv_id,
        title=legacy.title,
        full_name=legacy.full_name,
        email=legacy.email,
        phone=legacy.phone,
        professional_summary=legacy.professional_summary,
        experience_summary=legacy.experience_summary,
        education_summary=legacy.education_summary,
        skills=legacy.skills,
        created_at=legacy.created_at,
        updated_at=legacy.updated_at,
        deleted_at=None,
        structured_schema_version=structured_schema_version,
        structured_payload=structured_payload,
        structured_payload_status=structured_payload_status,
    )


@unittest.skipUnless(JINJA2_AVAILABLE, "jinja2 is required for latex service rendering")
class StructuredCvTexConsumersTest(unittest.TestCase):
    def test_structured_cv_tex_renders_all_supported_sections_for_every_template(self):
        cv = _structured_cv(_full_structured_payload())

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                generated_document = generate_cv_tex_document(cv, template_key)
                content_without_breaks = generated_document.content.replace(LATEX_BREAK_SEPARATOR, "")

                for marker in EXPECTED_TEX_MARKERS:
                    self.assertIn(marker, content_without_breaks)
                self.assertNotIn("[[", generated_document.content)
                self.assertNotIn("SNAPSHOT", generated_document.content)
                self.assertNotIn("stale@example.com", generated_document.content)

    def test_structured_cv_tex_renders_payload_not_stale_flat_snapshot(self):
        cv = _structured_cv(_full_structured_payload())

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content

                self.assertNotIn(STALE_MARKER, content)
                self.assertNotIn("stale@example.com", content)
                self.assertIn("Ana Perez", content)

    def test_structured_cv_tex_orders_items_by_normalized_contract(self):
        cv = _structured_cv(_full_structured_payload())

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content

                self.assertLess(
                    content.index("Desarrolladora Backend"),
                    content.index("Lider Tecnico"),
                    "La experiencia con order 1 debe aparecer antes que la de order 2.",
                )
                self.assertLess(
                    content.index("SQL (Datos"),
                    content.index("Python (Backend"),
                    "Los skills deben respetar (order, posicion).",
                )
                self.assertLess(
                    content.index("Python (Backend"),
                    content.index("Kubernetes"),
                    "Los skills deben respetar (order, posicion).",
                )
                self.assertLess(
                    content.index("Professional Scrum Master"),
                    content.index("Certificacion AWS"),
                    "Las certificaciones deben respetar (order, posicion).",
                )

    def test_structured_cv_tex_escapes_malicious_latex_content(self):
        cv = _structured_cv(_malicious_structured_payload())

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content

                self.assertIn(r"100\%", content)
                self.assertIn(r"\&", content)
                self.assertIn(r"\_", content)
                self.assertIn(r"\{ \}", content)
                self.assertIn(r"\textasciitilde{}", content)
                self.assertIn(r"\textasciicircum{}", content)
                self.assertIn(r"\textbackslash{}textbf\{Perez\}", content)
                self.assertIn(r"\textbackslash{}end\{document\}", content)
                self.assertEqual(
                    content.count("\\end{document}"),
                    1,
                    "Solo debe existir el \\end{document} propio de la plantilla.",
                )
                self.assertNotIn("\\section*{falso}", content)

    def test_structured_cv_tex_keeps_linebreaks_and_omits_empty_sections(self):
        cv = _structured_cv(_malicious_structured_payload())

        content = generate_cv_tex_document(cv, "classic").content

        self.assertIn("Linea uno.\n\nLinea dos", content)

        empty_payload = {
            "schema_version": 2,
            "personal": {"full_name": "Ana Perez", "headline": "", "location": ""},
            "contact": {"email": "", "phone": "", "links": []},
            "summary": "",
        }
        empty_cv = _structured_cv(empty_payload, cv_id=704, title="CV Vacio")
        empty_content = generate_cv_tex_document(empty_cv, "classic").content

        self.assertIn("Ana Perez", empty_content)
        for section_title in (
            "Perfil profesional",
            "Experiencia laboral",
            "Educacion",
            "Skills",
            "Certificaciones",
            "Idiomas",
            "Proyectos",
            "Links",
            "Informacion adicional",
        ):
            self.assertNotIn(section_title, empty_content)
        self.assertNotIn("[[", empty_content)

    def test_structured_cv_tex_does_not_leak_internal_metadata_or_unknown_extensions(self):
        cv = _structured_cv(_full_structured_payload())

        normalized = resolve_normalized_cv(cv)
        self.assertEqual(
            normalized.sections["experience"][0]["internal_note"],
            "dato-interno-no-renderizado",
        )

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content

                self.assertNotIn("structured_test", content)
                self.assertNotIn("synced_from_legacy_at", content)
                self.assertNotIn("schema_version", content)
                self.assertNotIn("dato-interno-no-renderizado", content)

    def test_fallback_rows_render_tex_exactly_like_legacy(self):
        legacy = _legacy_cv()

        for variant in ("corrupt", "stale", "invalid", "future"):
            with self.subTest(variant=variant):
                fallback = _fallback_cv(variant)

                for template_key in CV_TEMPLATE_KEYS:
                    with self.subTest(template_key=template_key):
                        legacy_content = generate_cv_tex_document(legacy, template_key).content
                        fallback_content = generate_cv_tex_document(fallback, template_key).content

                        self.assertEqual(legacy_content, fallback_content)
                        self.assertNotIn("Ana Perez", fallback_content)
                        self.assertNotIn("Tech Lead de Plataformas", fallback_content)


class StructuredCvAtsConsumersTest(unittest.TestCase):
    def test_ats_uses_canonical_payload_not_stale_flat_columns(self):
        cv = _structured_cv(_full_structured_payload())

        result = analyze_cv_ats(cv)

        self.assertEqual(result.score, 100)
        self.assertEqual(result.status, "Bueno")
        self.assertEqual(result.empty_sections, [])
        phone_check = next(item for item in result.checklist if item.key == "phone")
        email_check = next(item for item in result.checklist if item.key == "email")
        self.assertTrue(phone_check.passed)
        self.assertTrue(email_check.passed)

    def test_ats_fallback_rows_match_legacy_analysis_exactly(self):
        legacy_result = analyze_cv_ats(_legacy_cv())

        for variant in ("corrupt", "stale", "invalid", "future"):
            with self.subTest(variant=variant):
                fallback_result = analyze_cv_ats(_fallback_cv(variant))

                self.assertEqual(fallback_result, legacy_result)

    def test_ats_text_extraction_contains_supported_only_content_without_metadata(self):
        from app.services.structured_cv_rendering import build_structured_ats_text

        normalized = resolve_normalized_cv(_structured_cv(_full_structured_payload()))

        ats_text = build_structured_ats_text(normalized)

        for marker in (
            "Tech Lead de Plataformas",
            "Buenos Aires, Argentina",
            "Certificacion AWS Solutions Architect",
            "Espanol (Nativo)",
            "Observabilidad Abierta",
            "https://git.example.com/obs",
            "Disponibilidad",
            "Full-time remoto",
        ):
            self.assertIn(marker, ats_text)
        self.assertNotIn("structured_test", ats_text)
        self.assertNotIn("synced_from_legacy_at", ats_text)
        self.assertNotIn("schema_version", ats_text)
        self.assertNotIn("dato-interno-no-renderizado", ats_text)

    def test_ats_result_counts_supported_only_content_in_total_length(self):
        payload = {
            "schema_version": 2,
            "personal": {"full_name": "Ana Perez", "headline": "", "location": ""},
            "contact": {"email": "", "phone": "", "links": []},
            "summary": "",
            "certifications": [
                {
                    "name": "Certificacion extendida en arquitectura de soluciones cloud con foco en confiabilidad",
                    "issuer": "Proveedor internacional de certificaciones tecnicas",
                    "date": "2024",
                    "order": 1,
                },
                {
                    "name": "Diploma avanzado en observabilidad de plataformas distribuidas y grandes volumenes",
                    "issuer": "Instituto tecnico de postgrado",
                    "date": "2023",
                    "order": 2,
                },
            ],
            "projects": [
                {
                    "name": "Plataforma interna",
                    "summary": (
                        "Diseno e implementacion completa de una plataforma interna con paneles, "
                        "alertas y automatizaciones listas para produccion en multiples regiones."
                    ),
                    "link": "",
                    "technologies": [],
                    "order": 1,
                },
            ],
        }
        cv = _structured_cv(payload, cv_id=705)

        result = analyze_cv_ats(cv)

        self.assertGreaterEqual(result.total_characters, 280)
        length_check = next(item for item in result.checklist if item.key == "length")
        self.assertTrue(length_check.passed)

    def test_tex_and_ats_share_the_same_normalized_source(self):
        from app.services.structured_cv_rendering import build_structured_ats_text

        cv = _structured_cv(_full_structured_payload())
        normalized = resolve_normalized_cv(cv)

        ats_text = build_structured_ats_text(normalized)

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content

                for marker in (
                    "Tech Lead de Plataformas",
                    "Certificacion AWS Solutions Architect",
                    "Observabilidad Abierta",
                    "Disponibilidad",
                ):
                    self.assertIn(marker, content)
                    self.assertIn(marker, ats_text)


@unittest.skipUnless(JINJA2_AVAILABLE, "jinja2 is required for latex service rendering")
class StructuredCvLongTokenWrappingTest(unittest.TestCase):
    """T5 correction: trusted break opportunities for long unbroken tokens.

    Accepted structured text (highlights de 240 caracteres, URLs de 300,
    roles de 120, etc.) puede contener tokens ininterrumpidos que TeX no
    puede cortar y desbordan el margen derecho (overfull confirmado en las
    4 plantillas; header de modern 27.71626pt). El contrato exige:

    - oportunidades de corte confiables (macro `\\allowbreak` + `\\hspace`
      de ancho natural nulo) solo-estructuradas, generadas DESPUES de
      `sanitize_latex_text`;
    - nunca partir secuencias de escape TeX ni macros (limites de atomo);
    - preservar todos los caracteres y el contenido completo;
    - TEX legacy y CVs estructurados con tokens cortos sin cambios;
    - texto ATS sin macros de corte (scoring intacto).
    """

    LONG_UNBROKEN_TOKEN = "A" * 240
    LONG_URL = "https://git.example.com/" + "r" * 276
    LONG_ROLE = "R" * 120
    LATEX_BREAK = LATEX_BREAK_SEPARATOR

    def test_long_tokens_gain_trusted_break_opportunities_in_all_templates(self):
        payload = _full_structured_payload()
        payload["experience"][0]["highlights"] = [self.LONG_UNBROKEN_TOKEN]
        payload["experience"][0]["role"] = self.LONG_ROLE
        payload["links"][0]["url"] = self.LONG_URL
        cv = _structured_cv(payload)

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content

                self.assertIn(self.LATEX_BREAK, content)
                for long_token in (self.LONG_UNBROKEN_TOKEN, self.LONG_ROLE, self.LONG_URL):
                    self.assertNotIn(long_token, content)
                    self.assertIn(long_token, content.replace(self.LATEX_BREAK, ""))

    def test_break_opportunities_respect_latex_atom_boundaries(self):
        payload = _full_structured_payload()
        payload["experience"][0]["highlights"] = ["B" * 60 + r" \ & $ # _ { } ~ ^"]
        cv = _structured_cv(payload)
        trusted_sequences = (
            self.LATEX_BREAK,
            r"\textbackslash{}",
            r"\textasciitilde{}",
            r"\textasciicircum{}",
            r"\&",
            r"\%",
            r"\$",
            r"\#",
            r"\_",
            r"\{",
            r"\}",
        )
        known_pattern = "|".join(
            re.escape(sequence) for sequence in sorted(trusted_sequences, key=len, reverse=True)
        )

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content
                item_line = next(
                    line
                    for line in content.splitlines()
                    if line.lstrip().startswith(r"\item") and LATEX_BREAK_SEPARATOR in line
                )
                item_text = item_line.lstrip().split(" ", 1)[1]

                # Ninguna barra invertida de la linea del item queda fuera de
                # las secuencias confiables: la macro de corte nunca parte una
                # secuencia de escape TeX ni expone LaTeX crudo del usuario.
                residue = re.sub(known_pattern, "", item_text)
                self.assertNotIn("\\", residue)

                self.assertIn(r"\textbackslash{}", content)
                self.assertIn(r"\& \$ \# \_ \{ \} \textasciitilde{} \textasciicircum{}", content)
                unwrapped = content.replace(self.LATEX_BREAK, "")
                self.assertIn("B" * 60, unwrapped)
                self.assertNotIn("B" * 60, content)

    def test_wrapping_covers_every_structured_rendering_surface(self):
        payload = {
            "schema_version": 2,
            "personal": {
                "full_name": "N" * 160,
                "headline": "H" * 160,
                "location": "L" * 160,
            },
            "contact": {
                "email": "a" * 166 + "@example.com",
                "phone": "+5" + "4" * 77,
                "links": ["https://contact.example.com/" + "k" * 271],
            },
            "summary": "S" * 200 + " token corto.",
            "skills": [{"label": "K" * 120, "category": "", "level": "", "order": 1}],
            "experience": [
                {
                    "company": "C" * 120,
                    "role": "R" * 120,
                    "location": "X" * 120,
                    "start_date": "2" * 40,
                    "end_date": "2" * 40,
                    "current": False,
                    "summary": "W" * 300,
                    "highlights": [self.LONG_UNBROKEN_TOKEN],
                    "technologies": ["T" * 60],
                    "order": 1,
                }
            ],
            "education": [
                {
                    "institution": "I" * 160,
                    "degree": "D" * 160,
                    "field": "F" * 120,
                    "start_date": "",
                    "end_date": "",
                    "summary": "E" * 300,
                    "order": 1,
                }
            ],
            "certifications": [
                {"name": "Z" * 160, "issuer": "U" * 120, "date": "2" * 40, "order": 1}
            ],
            "languages": [{"name": "G" * 60, "level": "V" * 60, "order": 1}],
            "projects": [
                {
                    "name": "P" * 160,
                    "summary": "Q" * 300,
                    "link": "https://project.example.com/" + "j" * 271,
                    "technologies": ["M" * 60],
                    "order": 1,
                }
            ],
            "links": [{"label": "B" * 80, "url": self.LONG_URL, "order": 1}],
            "additional_info": [{"title": "O" * 120, "content": "Y" * 300, "order": 1}],
        }
        long_tokens = (
            "N" * 160,
            "H" * 160,
            "L" * 160,
            "a" * 166 + "@example.com",
            "+5" + "4" * 77,
            "https://contact.example.com/" + "k" * 271,
            "S" * 200,
            "K" * 120,
            "C" * 120,
            "R" * 120,
            "X" * 120,
            "2" * 40,
            "W" * 300,
            self.LONG_UNBROKEN_TOKEN,
            "T" * 60,
            "I" * 160,
            "D" * 160,
            "F" * 120,
            "E" * 300,
            "Z" * 160,
            "U" * 120,
            "G" * 60,
            "V" * 60,
            "P" * 160,
            "Q" * 300,
            "https://project.example.com/" + "j" * 271,
            "M" * 60,
            "B" * 80,
            self.LONG_URL,
            "O" * 120,
            "Y" * 300,
        )
        cv = _structured_cv(payload)

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content
                unwrapped = content.replace(self.LATEX_BREAK, "")

                self.assertIn(self.LATEX_BREAK, content)
                for long_token in long_tokens:
                    self.assertNotIn(long_token, content)
                    self.assertIn(long_token, unwrapped)

    def test_short_token_structured_rendering_stays_unwrapped(self):
        short_payload = {
            "schema_version": 2,
            "personal": {
                "full_name": "Ana Perez",
                "headline": "Tech Lead de Plataformas",
                "location": "Buenos Aires",
            },
            "contact": {
                "email": "ana@example.com",
                "phone": "+54 11 1234 5678",
                "links": ["https://ana.example.com"],
            },
            "summary": "Perfil estructurado con foco en plataformas y calidad.",
            "experience": [
                {
                    "company": "Globex",
                    "role": "Lider Tecnico",
                    "location": "Remoto",
                    "start_date": "2022",
                    "end_date": "",
                    "current": True,
                    "summary": "Liderazgo de la plataforma interna.",
                    "highlights": ["Diseno de plataforma confiable"],
                    "technologies": ["Python"],
                    "order": 1,
                }
            ],
            "links": [{"label": "GitHub", "url": "https://github.com/ana", "order": 1}],
        }
        cv = _structured_cv(short_payload)

        for template_key in CV_TEMPLATE_KEYS:
            with self.subTest(template_key=template_key):
                content = generate_cv_tex_document(cv, template_key).content

                self.assertNotIn(self.LATEX_BREAK, content)

        payload = _full_structured_payload()
        payload["unknown_extension"] = [{"hidden": "A" * 240}]
        unknown_cv = _structured_cv(payload)
        unknown_content = generate_cv_tex_document(unknown_cv, "classic").content

        self.assertNotIn("A" * 240, unknown_content.replace(self.LATEX_BREAK, ""))

    def test_ats_text_is_unaffected_by_break_opportunities(self):
        from app.services.structured_cv_rendering import build_structured_ats_text

        payload = _full_structured_payload()
        payload["experience"][0]["highlights"] = [self.LONG_UNBROKEN_TOKEN]
        payload["links"][0]["url"] = self.LONG_URL
        cv = _structured_cv(payload)

        ats_text = build_structured_ats_text(resolve_normalized_cv(cv))

        self.assertNotIn(self.LATEX_BREAK, ats_text)
        self.assertIn(self.LONG_UNBROKEN_TOKEN, ats_text)
        self.assertIn(self.LONG_URL, ats_text)


if __name__ == "__main__":
    unittest.main()
