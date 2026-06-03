from dataclasses import dataclass
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.models import CV
from app.validations.latex_sanitizer import sanitize_latex_text, split_sanitized_items


DEFAULT_TEMPLATE_KEY = "classic"
TEMPLATE_DIRECTORY = Path(__file__).resolve().parents[1] / "latex_templates" / "cv"


@dataclass(frozen=True)
class LatexTemplate:
    key: str
    name: str
    filename: str


@dataclass(frozen=True)
class GeneratedLatexDocument:
    filename: str
    template: LatexTemplate
    content: str


class LatexTemplateError(ValueError):
    pass


CV_TEMPLATES = {
    "classic": LatexTemplate("classic", "Classic", "classic.tex"),
    "modern": LatexTemplate("modern", "Modern", "modern.tex"),
    "compact": LatexTemplate("compact", "Compact", "compact.tex"),
    "tech": LatexTemplate("tech", "Tech", "tech.tex"),
}


def available_cv_templates() -> list[LatexTemplate]:
    return list(CV_TEMPLATES.values())


def generate_cv_tex_document(
    cv: CV,
    template_key: str = DEFAULT_TEMPLATE_KEY,
) -> GeneratedLatexDocument:
    template = _get_template(template_key)
    environment = _build_environment()
    renderer = environment.get_template(template.filename)
    context = _build_cv_context(cv)

    content = renderer.render(**context).strip() + "\n"

    return GeneratedLatexDocument(
        filename=_build_filename(cv, template.key),
        template=template,
        content=content,
    )


def _get_template(template_key: str) -> LatexTemplate:
    template = CV_TEMPLATES.get(template_key)
    if template is None:
        raise LatexTemplateError(f"Plantilla LaTeX no disponible: {template_key}")

    return template


def _build_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIRECTORY),
        autoescape=False,
        undefined=StrictUndefined,
        block_start_string="[%",
        block_end_string="%]",
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="[#",
        comment_end_string="#]",
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _build_cv_context(cv: CV) -> dict[str, object]:
    personal_details = [
        value
        for value in [
            sanitize_latex_text(cv.email),
            sanitize_latex_text(cv.phone),
        ]
        if value
    ]

    sections = [
        _build_section("Perfil profesional", cv.professional_summary),
        _build_section("Experiencia laboral", cv.experience_summary),
        _build_section("Educacion", cv.education_summary),
    ]

    skills = split_sanitized_items(cv.skills)
    if skills:
        sections.append({"title": "Skills", "item_list": skills, "body": ""})

    return {
        "full_name": sanitize_latex_text(cv.full_name),
        "title": sanitize_latex_text(cv.title),
        "personal_details": personal_details,
        "sections": [section for section in sections if section is not None],
    }


def _build_section(title: str, body: str) -> dict[str, object] | None:
    sanitized_body = sanitize_latex_text(body)
    if not sanitized_body:
        return None

    return {
        "title": sanitize_latex_text(title),
        "body": sanitized_body,
        "item_list": [],
    }


def _build_filename(cv: CV, template_key: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9]+", "-", cv.title.strip()).strip("-").lower()
    if not safe_name:
        safe_name = f"cv-{cv.id}"

    return f"{safe_name}-{template_key}.tex"
