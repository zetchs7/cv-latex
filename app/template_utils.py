from datetime import datetime

from fastapi.templating import Jinja2Templates


def create_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory="app/templates")
    templates.env.filters["format_datetime_ar"] = format_datetime_ar
    templates.env.filters["ats_status_variant"] = ats_status_variant
    return templates


def format_datetime_ar(value: str | None) -> str:
    if not value:
        return "Sin dato"

    parsed_value = _parse_datetime(value)
    if parsed_value is None:
        return value

    return parsed_value.strftime("%d/%m/%Y %H:%M")


def ats_status_variant(status: str | None, score: int | None = None, max_score: int | None = None) -> str:
    if score is not None and max_score and score >= max_score:
        return "excellent"

    normalized_status = (status or "").strip().lower()
    if normalized_status == "bueno":
        return "good"
    if normalized_status == "mejorable":
        return "warning"
    if normalized_status == "insuficiente":
        return "danger"
    return "neutral"


def _parse_datetime(value: str) -> datetime | None:
    normalized_value = value.strip()
    if not normalized_value:
        return None

    candidates = [
        normalized_value,
        normalized_value.replace("Z", "+00:00"),
        normalized_value.replace(" ", "T"),
    ]

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue

    return None
