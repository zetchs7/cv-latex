LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def sanitize_latex_text(value: str | None) -> str:
    if value is None:
        return ""

    normalized_value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized_value:
        return ""

    return "".join(LATEX_REPLACEMENTS.get(character, character) for character in normalized_value)


def split_sanitized_items(value: str | None) -> list[str]:
    if value is None:
        return []

    raw_items = []
    for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        raw_items.extend(line.split(","))

    return [
        sanitized_item
        for sanitized_item in (sanitize_latex_text(item) for item in raw_items)
        if sanitized_item
    ]
