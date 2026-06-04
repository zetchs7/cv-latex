import re


SAFE_EXPORT_FILENAME_MAX_LENGTH = 180


def sanitize_filename_component(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip(".-_").lower()


def build_capped_filename(
    *,
    leading_parts: list[str],
    variable_part: str,
    trailing_parts: list[str],
    extension: str,
    default_stem: str,
    max_length: int = SAFE_EXPORT_FILENAME_MAX_LENGTH,
) -> str:
    if not extension.startswith("."):
        raise ValueError("La extension debe incluir el punto inicial.")

    allowed_stem_length = max_length - len(extension)
    if allowed_stem_length <= 0:
        raise ValueError("El limite maximo de filename es demasiado corto para la extension.")

    safe_leading_parts = [part for part in (_sanitize_part(part) for part in leading_parts) if part]
    safe_trailing_parts = [part for part in (_sanitize_part(part) for part in trailing_parts) if part]
    safe_variable_part = _sanitize_part(variable_part)
    safe_default_stem = _sanitize_part(default_stem) or "export"

    if not safe_variable_part:
        safe_variable_part = safe_default_stem

    stem = _compose_stem(safe_leading_parts, safe_variable_part, safe_trailing_parts)
    if len(stem) > allowed_stem_length:
        safe_variable_part = _truncate_variable_part(
            safe_leading_parts,
            safe_variable_part,
            safe_trailing_parts,
            allowed_stem_length,
        )
        stem = _compose_stem(safe_leading_parts, safe_variable_part, safe_trailing_parts)

    if len(stem) > allowed_stem_length:
        stem = stem[:allowed_stem_length].rstrip(".-_")

    if not stem:
        stem = safe_default_stem[:allowed_stem_length].rstrip(".-_") or "export"

    return f"{stem}{extension}"


def _sanitize_part(value: str) -> str:
    return sanitize_filename_component(value)


def _compose_stem(leading_parts: list[str], variable_part: str, trailing_parts: list[str]) -> str:
    segments = [*leading_parts]
    if variable_part:
        segments.append(variable_part)
    segments.extend(trailing_parts)
    return "-".join(segment for segment in segments if segment)


def _truncate_variable_part(
    leading_parts: list[str],
    variable_part: str,
    trailing_parts: list[str],
    allowed_stem_length: int,
) -> str:
    stem = _compose_stem(leading_parts, variable_part, trailing_parts)
    if len(stem) <= allowed_stem_length:
        return variable_part

    excess = len(stem) - allowed_stem_length
    if excess >= len(variable_part):
        return ""

    return variable_part[:-excess].rstrip(".-_")
