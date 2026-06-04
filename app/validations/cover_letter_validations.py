from app.schemas import CoverLetterFormData


COVER_LETTER_FIELD_LIMITS = {
    "company": 160,
    "position": 160,
    "contact": 160,
    "greeting": 200,
    "introduction": 1200,
    "body": 3000,
    "closing": 800,
    "signature": 160,
}


def build_cover_letter_form_data(
    raw_values: dict[str, str],
    associated_cv_id: int | None,
) -> CoverLetterFormData:
    return CoverLetterFormData(
        company=_normalize(raw_values.get("company", "")),
        position=_normalize(raw_values.get("position", "")),
        contact=_normalize(raw_values.get("contact", "")),
        greeting=_normalize(raw_values.get("greeting", "")),
        introduction=_normalize(raw_values.get("introduction", "")),
        body=_normalize(raw_values.get("body", "")),
        closing=_normalize(raw_values.get("closing", "")),
        signature=_normalize(raw_values.get("signature", "")),
        associated_cv_id=associated_cv_id,
    )


def validate_cover_letter_form(
    form_data: CoverLetterFormData,
    *,
    associated_cv_id_raw: str = "",
    associated_cv_exists: bool = True,
) -> dict[str, str]:
    errors: dict[str, str] = {}

    if not form_data.company:
        errors["company"] = "La empresa es obligatoria."

    if not form_data.position:
        errors["position"] = "El puesto es obligatorio."

    if not form_data.greeting:
        errors["greeting"] = "El saludo es obligatorio."

    if not form_data.body:
        errors["body"] = "El cuerpo de la carta es obligatorio."

    if not form_data.signature:
        errors["signature"] = "La firma es obligatoria."

    for field_name, max_length in COVER_LETTER_FIELD_LIMITS.items():
        field_value = getattr(form_data, field_name)
        if len(field_value) > max_length:
            errors[field_name] = f"Maximo {max_length} caracteres."

    if associated_cv_id_raw and form_data.associated_cv_id is None:
        errors["associated_cv_id"] = "El CV asociado debe ser un identificador valido."
    elif form_data.associated_cv_id is not None and not associated_cv_exists:
        errors["associated_cv_id"] = "El CV asociado no existe o fue eliminado."

    return errors


def _normalize(value: str) -> str:
    return " ".join(value.strip().split()) if "\n" not in value else value.strip()
