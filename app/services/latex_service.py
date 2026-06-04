from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.models import CV, CoverLetter
from app.services.file_naming import SAFE_EXPORT_FILENAME_MAX_LENGTH, build_capped_filename, sanitize_filename_component
from app.validations.latex_sanitizer import sanitize_latex_text, split_sanitized_items


DEFAULT_TEMPLATE_KEY = "classic"
DEFAULT_COVER_LETTER_TEMPLATE_KEY = "classic_letter"
CV_TEMPLATE_DIRECTORY = Path(__file__).resolve().parents[1] / "latex_templates" / "cv"
COVER_LETTER_TEMPLATE_DIRECTORY = Path(__file__).resolve().parents[1] / "latex_templates" / "cover_letter"


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

COVER_LETTER_TEMPLATES = {
    "classic_letter": LatexTemplate("classic_letter", "Classic Letter", "classic_letter.tex"),
}


def available_cv_templates() -> list[LatexTemplate]:
    return list(CV_TEMPLATES.values())


def available_cover_letter_templates() -> list[LatexTemplate]:
    return list(COVER_LETTER_TEMPLATES.values())


def generate_cv_tex_document(
    cv: CV,
    template_key: str = DEFAULT_TEMPLATE_KEY,
) -> GeneratedLatexDocument:
    template = _get_template(template_key)
    environment = _build_environment(CV_TEMPLATE_DIRECTORY)
    renderer = environment.get_template(template.filename)
    context = _build_cv_context(cv)

    content = renderer.render(**context).strip() + "\n"

    return GeneratedLatexDocument(
        filename=_build_filename(cv, template.key),
        template=template,
        content=content,
    )


def generate_cover_letter_tex_document(
    cover_letter: CoverLetter,
    template_key: str = DEFAULT_COVER_LETTER_TEMPLATE_KEY,
) -> GeneratedLatexDocument:
    template = _get_cover_letter_template(template_key)
    environment = _build_environment(COVER_LETTER_TEMPLATE_DIRECTORY)
    renderer = environment.get_template(template.filename)
    context = _build_cover_letter_context(cover_letter)

    content = renderer.render(**context).strip() + "\n"

    return GeneratedLatexDocument(
        filename=_build_cover_letter_filename(cover_letter, template.key),
        template=template,
        content=content,
    )


def _get_template(template_key: str) -> LatexTemplate:
    template = CV_TEMPLATES.get(template_key)
    if template is None:
        raise LatexTemplateError(f"Plantilla LaTeX no disponible: {template_key}")

    return template


def _get_cover_letter_template(template_key: str) -> LatexTemplate:
    template = COVER_LETTER_TEMPLATES.get(template_key)
    if template is None:
        raise LatexTemplateError(f"Plantilla LaTeX no disponible: {template_key}")

    return template


def _build_environment(template_directory: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(template_directory),
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


def _build_cover_letter_context(cover_letter: CoverLetter) -> dict[str, object]:
    return {
        "company": sanitize_latex_text(cover_letter.company),
        "position": sanitize_latex_text(cover_letter.position),
        "contact": sanitize_latex_text(cover_letter.contact),
        "greeting": sanitize_latex_text(cover_letter.greeting),
        "introduction": sanitize_latex_text(cover_letter.introduction),
        "body": sanitize_latex_text(cover_letter.body),
        "closing": sanitize_latex_text(cover_letter.closing),
        "signature": sanitize_latex_text(cover_letter.signature),
        "associated_cv_title": sanitize_latex_text(cover_letter.associated_cv_title),
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
    return build_capped_filename(
        leading_parts=[],
        variable_part=cv.title,
        trailing_parts=[sanitize_filename_component(template_key)],
        extension=".tex",
        default_stem=f"cv-{cv.id}-{template_key}",
        max_length=SAFE_EXPORT_FILENAME_MAX_LENGTH,
    )


def _build_cover_letter_filename(cover_letter: CoverLetter, template_key: str) -> str:
    title_parts = [cover_letter.company.strip(), cover_letter.position.strip()]
    title_value = " ".join(part for part in title_parts if part).strip()
    return build_capped_filename(
        leading_parts=["cover-letter", str(cover_letter.id)],
        variable_part=title_value,
        trailing_parts=[sanitize_filename_component(template_key)],
        extension=".tex",
        default_stem=f"cover-letter-{cover_letter.id}-{template_key}",
        max_length=SAFE_EXPORT_FILENAME_MAX_LENGTH,
    )
