import re

from app.schemas import CVFormData


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

FIELD_LIMITS = {
    "title": 120,
    "full_name": 160,
    "email": 180,
    "phone": 80,
    "professional_summary": 1200,
    "experience_summary": 2000,
    "education_summary": 1600,
    "skills": 1200,
}


def build_cv_form_data(raw_values: dict[str, str]) -> CVFormData:
    return CVFormData(
        title=_normalize(raw_values.get("title", "")),
        full_name=_normalize(raw_values.get("full_name", "")),
        email=_normalize(raw_values.get("email", "")),
        phone=_normalize(raw_values.get("phone", "")),
        professional_summary=_normalize(raw_values.get("professional_summary", "")),
        experience_summary=_normalize(raw_values.get("experience_summary", "")),
        education_summary=_normalize(raw_values.get("education_summary", "")),
        skills=_normalize(raw_values.get("skills", "")),
    )


def validate_cv_form(form_data: CVFormData) -> dict[str, str]:
    errors: dict[str, str] = {}

    if not form_data.title:
        errors["title"] = "El titulo interno del CV es obligatorio."

    if not form_data.full_name:
        errors["full_name"] = "El nombre completo es obligatorio."

    if form_data.email and not EMAIL_PATTERN.match(form_data.email):
        errors["email"] = "El email debe tener un formato valido."

    for field_name, max_length in FIELD_LIMITS.items():
        field_value = getattr(form_data, field_name)
        if len(field_value) > max_length:
            errors[field_name] = f"Maximo {max_length} caracteres."

    return errors


def _normalize(value: str) -> str:
    return " ".join(value.strip().split()) if "\n" not in value else value.strip()
