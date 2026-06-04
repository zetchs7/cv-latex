from datetime import date
from urllib.parse import urlparse

from app.schemas import ApplicationFormData


APPLICATION_STATUSES = (
    "pendiente",
    "enviado",
    "entrevista",
    "rechazado",
    "oferta",
    "pausado",
)

APPLICATION_FIELD_LIMITS = {
    "company": 160,
    "position": 160,
    "link": 500,
    "source": 160,
    "applied_on": 10,
    "status": 20,
    "notes": 4000,
    "next_action": 800,
    "follow_up_date": 10,
}


def build_application_form_data(
    raw_values: dict[str, str],
    associated_cv_id: int | None,
    associated_cover_letter_id: int | None,
) -> ApplicationFormData:
    return ApplicationFormData(
        company=_normalize(raw_values.get("company", "")),
        position=_normalize(raw_values.get("position", "")),
        link=_normalize(raw_values.get("link", "")),
        source=_normalize(raw_values.get("source", "")),
        applied_on=_normalize(raw_values.get("applied_on", "")),
        status=_normalize(raw_values.get("status", "")),
        associated_cv_id=associated_cv_id,
        associated_cover_letter_id=associated_cover_letter_id,
        notes=_normalize(raw_values.get("notes", "")),
        next_action=_normalize(raw_values.get("next_action", "")),
        follow_up_date=_normalize(raw_values.get("follow_up_date", "")),
    )


def validate_application_form(
    form_data: ApplicationFormData,
    *,
    associated_cv_id_raw: str = "",
    associated_cover_letter_id_raw: str = "",
    associated_cv_exists: bool = True,
    associated_cover_letter_exists: bool = True,
) -> dict[str, str]:
    errors: dict[str, str] = {}

    if not form_data.company:
        errors["company"] = "La empresa es obligatoria."

    if not form_data.position:
        errors["position"] = "El puesto es obligatorio."

    if not form_data.applied_on:
        errors["applied_on"] = "La fecha de aplicacion es obligatoria."
    elif not _is_valid_iso_date(form_data.applied_on):
        errors["applied_on"] = "La fecha de aplicacion debe tener formato YYYY-MM-DD."

    if not form_data.status:
        errors["status"] = "El estado es obligatorio."
    elif form_data.status not in APPLICATION_STATUSES:
        errors["status"] = "El estado seleccionado no es valido."

    if form_data.link and not _is_valid_url(form_data.link):
        errors["link"] = "El link debe comenzar con http:// o https:// y ser valido."

    if form_data.follow_up_date and not _is_valid_iso_date(form_data.follow_up_date):
        errors["follow_up_date"] = "La fecha de seguimiento debe tener formato YYYY-MM-DD."

    for field_name, max_length in APPLICATION_FIELD_LIMITS.items():
        field_value = getattr(form_data, field_name)
        if len(field_value) > max_length:
            errors[field_name] = f"Maximo {max_length} caracteres."

    if associated_cv_id_raw and form_data.associated_cv_id is None:
        errors["associated_cv_id"] = "El CV asociado debe ser un identificador valido."
    elif form_data.associated_cv_id is not None and not associated_cv_exists:
        errors["associated_cv_id"] = "El CV asociado no existe o fue eliminado."

    if associated_cover_letter_id_raw and form_data.associated_cover_letter_id is None:
        errors["associated_cover_letter_id"] = "La carta asociada debe ser un identificador valido."
    elif form_data.associated_cover_letter_id is not None and not associated_cover_letter_exists:
        errors["associated_cover_letter_id"] = "La carta asociada no existe o fue eliminada."

    return errors


def _is_valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize(value: str) -> str:
    return " ".join(value.strip().split()) if "\n" not in value else value.strip()
