r"""Renderizado compartido del CV normalizado para LaTeX/PDF y ATS basico.

Este modulo es el unico punto de conversion desde la representacion
normalizada (`NormalizedCV`, resuelta por `resolve_normalized_cv`) hacia:

- el contexto LaTeX enriquecido que consumen las 4 plantillas de CV
  (`build_structured_cv_latex_context`);
- el texto plano normalizado con todo el contenido soportado que analiza el
  chequeo ATS basico (`build_structured_ats_text`).

Reglas del contrato T5:

- Ningun consumidor lee `structured_payload` o campos planos por su cuenta;
  todos parten de `resolve_normalized_cv`.
- Un CV estructurado valido renderiza desde las secciones del payload, aun
  si el snapshot legacy derivado quedo obsoleto.
- La metadata interna de procedencia (`metadata`) y las claves de extension
  desconocidas nunca se renderizan en salidas publicas.
- Los listados se ordenan de forma consistente por `(order, posicion)`, con
  la misma semantica que la derivacion del snapshot legacy de T2.
- Todo texto dirigido a LaTeX pasa por `sanitize_latex_text` y recibe
  oportunidades de corte confiables (`\allowbreak`) generadas por este modulo
  SOLO entre atomos ya sanitizados cuando un token largo no tendria puntos
  de corte naturales; nunca se insertan antes de sanitizar.
"""

import re

from app.services.structured_cv_service import NormalizedCV
from app.validations.latex_sanitizer import sanitize_latex_text


CV_TEX_SECTION_SUMMARY = "Perfil profesional"
CV_TEX_SECTION_EXPERIENCE = "Experiencia laboral"
CV_TEX_SECTION_EDUCATION = "Educacion"
CV_TEX_SECTION_SKILLS = "Skills"
CV_TEX_SECTION_CERTIFICATIONS = "Certificaciones"
CV_TEX_SECTION_LANGUAGES = "Idiomas"
CV_TEX_SECTION_PROJECTS = "Proyectos"
CV_TEX_SECTION_LINKS = "Links"
CV_TEX_SECTION_ADDITIONAL_INFO = "Informacion adicional"

META_PARTS_SEPARATOR = " · "
DATE_RANGE_SEPARATOR = " - "
CURRENT_ROLE_LABEL = "Presente"
EDUCATION_FIELD_PREFIX = "Campo: "
TECHNOLOGIES_PREFIX = "Tecnologias: "
HIGHLIGHT_BULLET_PREFIX = "• "

# Macro de corte confiable del kernel LaTeX (\penalty \z@): no tipografia
# nada por si misma y solo habilita un punto de corte cuando TeX lo necesita.
# El espacio final es imprescindible: LaTeX extiende los nombres de control
# con las letras siguientes (sin espacio, `h\allowbreakt` se lee como una
# unica macro inexistente); ese espacio se consume en la tokenizacion y no
# agrega ningun glifo.
# El \hspace de ancho natural nulo con estiramiento minimo vuelve factible
# la justificacion de lineas sin pegamento propio (tokens puros sin
# espacios): sin estiramiento disponible TeX deja restos overfull de hasta
# medio glifo en lugar de cortar una letra antes. El estiramiento aplicado
# (fracciones de punto repartidas entre decenas de cortes) es invisible.
LATEX_BREAK_OPPORTUNITY = r"\allowbreak \hspace{0pt plus 0.06em}"

# Umbral en atomos (secuencias de escape TeX cuentan como 1): los tokens mas
# cortos quedan exactamente como antes; las palabras normales no llegan a
# este largo y conservan silabeo/hyphenation intacto.
_LONG_TOKEN_ATOM_COUNT = 24

# Secuencias completas que puede producir `sanitize_latex_text`.
_SANITIZER_ESCAPE_ATOMS = (
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


def build_structured_cv_latex_context(normalized: NormalizedCV) -> dict[str, object]:
    """Construye el contexto LaTeX para un CV estructurado canonico.

    El contexto es la misma forma que consumen las plantillas para CVs
    legacy (`full_name`, `title`, `personal_details`, `sections`), ampliada
    con entradas enriquecidas (`entries`) por seccion. Renderiza todos los
    campos soportados del payload v2; nunca la metadata interna.
    """
    sections = normalized.sections
    personal = _section_object(sections, "personal")
    contact = _section_object(sections, "contact")

    headline = _item_string(personal, "headline")
    latex_sections: list[dict[str, object]] = []

    summary = _structured_latex_text(_string_value(sections.get("summary")))
    if summary:
        latex_sections.append(_body_latex_section(CV_TEX_SECTION_SUMMARY, summary))

    experience_entries = _experience_latex_entries(sections.get("experience"))
    if experience_entries:
        latex_sections.append(_entries_latex_section(CV_TEX_SECTION_EXPERIENCE, experience_entries))

    education_entries = _education_latex_entries(sections.get("education"))
    if education_entries:
        latex_sections.append(_entries_latex_section(CV_TEX_SECTION_EDUCATION, education_entries))

    skills_items = _skill_latex_items(sections.get("skills"))
    if skills_items:
        latex_sections.append(_item_list_latex_section(CV_TEX_SECTION_SKILLS, skills_items))

    certification_items = _named_date_latex_items(
        sections.get("certifications"),
        name_field="name",
        issuer_field="issuer",
        date_field="date",
    )
    if certification_items:
        latex_sections.append(_item_list_latex_section(CV_TEX_SECTION_CERTIFICATIONS, certification_items))

    language_items = _language_latex_items(sections.get("languages"))
    if language_items:
        latex_sections.append(_item_list_latex_section(CV_TEX_SECTION_LANGUAGES, language_items))

    project_entries = _project_latex_entries(sections.get("projects"))
    if project_entries:
        latex_sections.append(_entries_latex_section(CV_TEX_SECTION_PROJECTS, project_entries))

    link_items = _link_latex_items(sections.get("links"))
    if link_items:
        latex_sections.append(_item_list_latex_section(CV_TEX_SECTION_LINKS, link_items))

    additional_entries = _additional_info_latex_entries(sections.get("additional_info"))
    if additional_entries:
        latex_sections.append(_entries_latex_section(CV_TEX_SECTION_ADDITIONAL_INFO, additional_entries))

    return {
        "full_name": _structured_latex_text(_item_string(personal, "full_name")),
        "title": _structured_latex_text(headline or normalized.title),
        "personal_details": _personal_detail_lines(personal, contact),
        "sections": latex_sections,
        "use_needspace": True,
    }


def build_structured_ats_text(normalized: NormalizedCV) -> str:
    """Texto plano normalizado con todo el contenido soportado del CV.

    Incluye las secciones solo-estructuradas (headline, ubicacion, links de
    contacto, certificaciones, idiomas, proyectos, links e informacion
    adicional) y excluye la metadata interna de procedencia. Para un payload
    derivado de campos legacy, el texto degenera exactamente en la
    estimacion legacy, lo que garantiza equivalencia canonica de scoring.
    """
    sections = normalized.sections
    personal = _section_object(sections, "personal")
    contact = _section_object(sections, "contact")

    parts: list[str] = [
        normalized.title,
        _item_string(personal, "full_name"),
        _item_string(personal, "headline"),
        _item_string(personal, "location"),
        _item_string(contact, "email"),
        _item_string(contact, "phone"),
        *_contact_link_values(contact),
        _string_value(sections.get("summary")),
        *_experience_text_blocks(sections.get("experience")),
        *_education_text_blocks(sections.get("education")),
        _skills_text(sections.get("skills")),
        *_named_date_text_lines(
            sections.get("certifications"),
            name_field="name",
            issuer_field="issuer",
            date_field="date",
        ),
        *_language_text_lines(sections.get("languages")),
        *_project_text_blocks(sections.get("projects")),
        *_link_text_lines(sections.get("links")),
        *_additional_info_text_lines(sections.get("additional_info")),
    ]

    return " ".join(part for part in parts if part and part.strip())


def _structured_latex_text(value: str) -> str:
    r"""Sanitiza y agrega oportunidades de corte confiables para tokens largos.

    Reglas de seguridad del contrato T5:

    - la sanitizacion es SIEMPRE previa (`sanitize_latex_text`); las macros
      de corte se generan despues, solo desde codigo confiable;
    - solo se insertan ENTRE atomos ya sanitizados: cada secuencia de escape
      producida por el sanitizador (`\textbackslash{}`, `\&`, ...) es un
      atomo indivisible, por lo que ninguna macro de corte puede partir una
      secuencia TeX ni exponer LaTeX crudo del usuario;
    - todos los caracteres del contenido se preservan: la macro es un
      penalty de ancho cero, su espacio se consume al tokenizar y el glue
      agregado tiene ancho natural nulo, asi que no agregan ningun glifo.
    """
    return _add_trusted_break_opportunities(sanitize_latex_text(value))


def _add_trusted_break_opportunities(sanitized: str) -> str:
    r"""Interpola `\allowbreak` entre atomos de tokens largos sanitizados.

    Un "token" es una corrida sin espacios ni saltos: TeX solo puede cortar
    en espacios, guiones o silabeo, y un token ininterrumpido largo no tiene
    cortes posibles, por lo que desborda el margen derecho (overfull). El
    umbral se mide en atomos para no tocar palabras normales: los tokens con
    menos de `_LONG_TOKEN_ATOM_COUNT` atomos quedan exactamente como antes.
    """
    if len(sanitized) < _LONG_TOKEN_ATOM_COUNT:
        return sanitized

    parts = re.split(r"(\s+)", sanitized)
    rebuilt: list[str] = []
    for part in parts:
        if part and not part.isspace():
            atoms = _split_latex_atoms(part)
            if len(atoms) >= _LONG_TOKEN_ATOM_COUNT:
                rebuilt.append(LATEX_BREAK_OPPORTUNITY.join(atoms))
                continue
        rebuilt.append(part)
    return "".join(rebuilt)


def _split_latex_atoms(token: str) -> list[str]:
    """Parte texto ya sanitizado en atomos indivisibles para TeX.

    Tras `sanitize_latex_text`, toda barra invertida inicia una secuencia de
    escape conocida del sanitizador; se consume la secuencia completa como
    un unico atomo (longest match), jamas por dentro.
    """
    atoms: list[str] = []
    index = 0
    length = len(token)
    while index < length:
        atom = _sanitizer_escape_atom(token, index) if token[index] == "\\" else token[index]
        atoms.append(atom)
        index += len(atom)
    return atoms


def _sanitizer_escape_atom(token: str, index: int) -> str:
    """Devuelve la secuencia de escape completa que empieza en `index`."""
    for escape_atom in _SANITIZER_ESCAPE_ATOMS:
        if token.startswith(escape_atom, index):
            return escape_atom
    # Defensa: una barra suelta no puede provenir de `sanitize_latex_text`;
    # se trata como atomo propio para no partir ninguna secuencia futura.
    return token[index]


def _personal_detail_lines(personal: object, contact: object) -> list[str]:
    details = [
        _item_string(contact, "email"),
        _item_string(contact, "phone"),
        _item_string(personal, "location"),
        *_contact_link_values(contact),
    ]
    return [_structured_latex_text(detail) for detail in details if detail]


def _experience_latex_entries(raw_items: object) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for item in _sorted_items(raw_items):
        headline = _join_non_empty(
            DATE_RANGE_SEPARATOR,
            [_item_string(item, "role"), _item_string(item, "company")],
        )
        meta = _experience_meta_line(item)
        body = _summary_with_technologies(item)
        highlights = [_highlight_latex(value) for value in _string_list(item.get("highlights"))]

        if not headline and meta:
            headline, meta = meta, ""
        if not any((headline, meta, body, highlights)):
            continue

        entries.append(
            {
                "headline": _structured_latex_text(headline),
                "meta": _structured_latex_text(meta),
                "body": body,
                "highlights": highlights,
            }
        )
    return entries


def _education_latex_entries(raw_items: object) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for item in _sorted_items(raw_items):
        headline = _join_non_empty(
            DATE_RANGE_SEPARATOR,
            [_item_string(item, "degree"), _item_string(item, "institution")],
        )
        meta = _date_range(item)
        body = _join_non_empty(
            " ",
            [
                f"{EDUCATION_FIELD_PREFIX}{_structured_latex_text(_item_string(item, 'field'))}"
                if _item_string(item, "field")
                else "",
                _structured_latex_text(_item_string(item, "summary")),
            ],
        )

        if not headline and meta:
            headline, meta = meta, ""
        if not any((headline, meta, body)):
            continue

        entries.append(
            {
                "headline": _structured_latex_text(headline),
                "meta": _structured_latex_text(meta),
                "body": body,
                "highlights": [],
            }
        )
    return entries


def _project_latex_entries(raw_items: object) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for item in _sorted_items(raw_items):
        headline = _item_string(item, "name")
        meta = _item_string(item, "link")
        body = _summary_with_technologies(item)

        if not headline and meta:
            headline, meta = meta, ""
        if not any((headline, meta, body)):
            continue

        entries.append(
            {
                "headline": _structured_latex_text(headline),
                "meta": _structured_latex_text(meta),
                "body": body,
                "highlights": [],
            }
        )
    return entries


def _additional_info_latex_entries(raw_items: object) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for item in _sorted_items(raw_items):
        headline = _item_string(item, "title")
        body = _structured_latex_text(_item_string(item, "content"))
        if not headline and not body:
            continue

        entries.append(
            {
                "headline": _structured_latex_text(headline),
                "meta": "",
                "body": body,
                "highlights": [],
            }
        )
    return entries


def _skill_latex_items(raw_items: object) -> list[str]:
    items: list[str] = []
    for item in _sorted_items(raw_items):
        label = _item_string(item, "label")
        if not label:
            continue
        qualifiers = _join_non_empty(
            ", ",
            [_item_string(item, "category"), _item_string(item, "level")],
        )
        rendered = f"{label} ({qualifiers})" if qualifiers else label
        items.append(_structured_latex_text(rendered))
    return items


def _language_latex_items(raw_items: object) -> list[str]:
    items: list[str] = []
    for item in _sorted_items(raw_items):
        name = _item_string(item, "name")
        if not name:
            continue
        level = _item_string(item, "level")
        rendered = f"{name} ({level})" if level else name
        items.append(_structured_latex_text(rendered))
    return items


def _named_date_latex_items(
    raw_items: object,
    *,
    name_field: str,
    issuer_field: str,
    date_field: str,
) -> list[str]:
    items: list[str] = []
    for item in _sorted_items(raw_items):
        name = _join_non_empty(
            DATE_RANGE_SEPARATOR,
            [_item_string(item, name_field), _item_string(item, issuer_field)],
        )
        date_value = _item_string(item, date_field)
        if not name and not date_value:
            continue
        rendered = f"{name} ({date_value})" if name and date_value else name or date_value
        items.append(_structured_latex_text(rendered))
    return items


def _link_latex_items(raw_items: object) -> list[str]:
    items: list[str] = []
    for item in _sorted_items(raw_items):
        label = _item_string(item, "label")
        url = _item_string(item, "url")
        if not label and not url:
            continue
        rendered = f"{label} - {url}" if label and url else label or url
        items.append(_structured_latex_text(rendered))
    return items


def _experience_text_blocks(raw_items: object) -> list[str]:
    blocks: list[str] = []
    for item in _sorted_items(raw_items):
        if not isinstance(item, dict):
            continue
        header = _join_non_empty(
            DATE_RANGE_SEPARATOR,
            [_item_string(item, "role"), _item_string(item, "company")],
        )
        meta = _experience_meta_line(item)
        if header and meta:
            header = f"{header} ({meta})"
        elif not header:
            header = meta

        lines = [header] if header else []
        summary = _item_string(item, "summary")
        if summary:
            lines.append(summary)
        for highlight in _string_list(item.get("highlights")):
            lines.append(f"{HIGHLIGHT_BULLET_PREFIX}{highlight}")
        technologies = _join_non_empty(", ", _string_list(item.get("technologies")))
        if technologies:
            lines.append(f"{TECHNOLOGIES_PREFIX}{technologies}")

        block = "\n".join(lines)
        if block:
            blocks.append(block)
    return blocks


def _education_text_blocks(raw_items: object) -> list[str]:
    blocks: list[str] = []
    for item in _sorted_items(raw_items):
        if not isinstance(item, dict):
            continue
        header = _join_non_empty(
            DATE_RANGE_SEPARATOR,
            [_item_string(item, "degree"), _item_string(item, "institution")],
        )
        date_range = _date_range(item)
        if header and date_range:
            header = f"{header} ({date_range})"
        elif not header:
            header = date_range

        lines = [header] if header else []
        field = _item_string(item, "field")
        if field:
            lines.append(f"{EDUCATION_FIELD_PREFIX}{field}")
        summary = _item_string(item, "summary")
        if summary:
            lines.append(summary)

        block = "\n".join(lines)
        if block:
            blocks.append(block)
    return blocks


def _skills_text(raw_items: object) -> str:
    labels: list[str] = []
    for item in _sorted_items(raw_items):
        label = _item_string(item, "label")
        if not label:
            continue
        qualifiers = _join_non_empty(
            ", ",
            [_item_string(item, "category"), _item_string(item, "level")],
        )
        labels.append(f"{label} ({qualifiers})" if qualifiers else label)
    return ", ".join(labels)


def _named_date_text_lines(
    raw_items: object,
    *,
    name_field: str,
    issuer_field: str,
    date_field: str,
) -> list[str]:
    lines: list[str] = []
    for item in _sorted_items(raw_items):
        name = _join_non_empty(
            DATE_RANGE_SEPARATOR,
            [_item_string(item, name_field), _item_string(item, issuer_field)],
        )
        date_value = _item_string(item, date_field)
        if not name and not date_value:
            continue
        lines.append(f"{name} ({date_value})" if name and date_value else name or date_value)
    return lines


def _language_text_lines(raw_items: object) -> list[str]:
    lines: list[str] = []
    for item in _sorted_items(raw_items):
        name = _item_string(item, "name")
        if not name:
            continue
        level = _item_string(item, "level")
        lines.append(f"{name} ({level})" if level else name)
    return lines


def _project_text_blocks(raw_items: object) -> list[str]:
    blocks: list[str] = []
    for item in _sorted_items(raw_items):
        if not isinstance(item, dict):
            continue
        header = _join_non_empty(
            DATE_RANGE_SEPARATOR,
            [_item_string(item, "name"), _item_string(item, "link")],
        )
        lines = [header] if header else []
        summary = _item_string(item, "summary")
        if summary:
            lines.append(summary)
        technologies = _join_non_empty(", ", _string_list(item.get("technologies")))
        if technologies:
            lines.append(f"{TECHNOLOGIES_PREFIX}{technologies}")

        block = "\n".join(lines)
        if block:
            blocks.append(block)
    return blocks


def _link_text_lines(raw_items: object) -> list[str]:
    lines: list[str] = []
    for item in _sorted_items(raw_items):
        label = _item_string(item, "label")
        url = _item_string(item, "url")
        if not label and not url:
            continue
        lines.append(f"{label} - {url}" if label and url else label or url)
    return lines


def _additional_info_text_lines(raw_items: object) -> list[str]:
    lines: list[str] = []
    for item in _sorted_items(raw_items):
        title = _item_string(item, "title")
        content = _item_string(item, "content")
        if not title and not content:
            continue
        lines.append(f"{title}: {content}" if title and content else title or content)
    return lines


def _experience_meta_line(item: object) -> str:
    if not isinstance(item, dict):
        return ""
    return _join_non_empty(
        META_PARTS_SEPARATOR,
        [_date_range(item), _item_string(item, "location")],
    )


def _summary_with_technologies(item: object) -> str:
    if not isinstance(item, dict):
        return ""
    technologies = _join_non_empty(", ", _string_list(item.get("technologies")))
    parts = [
        _structured_latex_text(_item_string(item, "summary")),
        f"{TECHNOLOGIES_PREFIX}{_structured_latex_text(technologies)}" if technologies else "",
    ]
    return _join_non_empty(" ", parts)


def _highlight_latex(value: str) -> str:
    return _structured_latex_text(value)


def _body_latex_section(title: str, body: str) -> dict[str, object]:
    return {"title": title, "body": body, "item_list": [], "entries": [], "keep_with_next": True}


def _item_list_latex_section(title: str, item_list: list[str]) -> dict[str, object]:
    return {"title": title, "body": "", "item_list": item_list, "entries": [], "keep_with_next": True}


def _entries_latex_section(title: str, entries: list[dict[str, object]]) -> dict[str, object]:
    return {"title": title, "body": "", "item_list": [], "entries": entries, "keep_with_next": True}


def _section_object(sections: dict[str, object], key: str) -> object:
    value = sections.get(key)
    return value if isinstance(value, dict) else {}


def _contact_link_values(contact: object) -> list[str]:
    if not isinstance(contact, dict):
        return []
    return [value for value in contact.get("links") or [] if isinstance(value, str)]


def _date_range(item: dict[str, object]) -> str:
    start_date = _item_string(item, "start_date")
    end_date = _item_string(item, "end_date")
    if item.get("current") is True:
        end_date = CURRENT_ROLE_LABEL
    if start_date and end_date:
        return f"{start_date}{DATE_RANGE_SEPARATOR}{end_date}"
    return start_date or end_date


def _sorted_items(raw_items: object) -> list[object]:
    """Ordena items por `(order, posicion)`.

    Misma semantica que la derivacion del snapshot legacy en
    `structured_cv_service`: `order` entero (bool rechazado) con fallback a
    la posicion original, estable por indice.
    """
    items = raw_items if isinstance(raw_items, list) else []
    return [
        item
        for _, item in sorted(
            enumerate(items),
            key=lambda pair: (_item_order(pair[1], pair[0]), pair[0]),
        )
    ]


def _item_order(item: object, fallback_index: int) -> int:
    if isinstance(item, dict):
        order = item.get("order")
        if isinstance(order, int) and not isinstance(order, bool):
            return order
    return fallback_index + 1


def _item_string(item: object, field: str) -> str:
    if isinstance(item, dict):
        value = item.get(field)
        if isinstance(value, str):
            return value
    return ""


def _string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def _string_list(raw_values: object) -> list[str]:
    if not isinstance(raw_values, list):
        return []
    return [value for value in raw_values if isinstance(value, str) and value]


def _join_non_empty(separator: str, parts: list[str]) -> str:
    return separator.join(part for part in parts if part)
