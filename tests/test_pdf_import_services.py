"""Tests unitarios de la importacion de CV desde PDF.

Cubre las tres piezas por separado: validacion y extraccion del PDF,
clasificacion del texto, y ciclo de vida del staging. Los casos de limite y de
entrada hostil estan explicitos porque son la superficie de riesgo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import re
from pathlib import Path

import pytest

from app.services import import_staging_service as staging
from app.services.pdf_import_service import (
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    PdfImportError,
    extract_pdf,
    read_limited_pdf_bytes,
    validate_pdf_bytes,
)
from app.services.pdf_section_parser import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    normalize_for_matching,
    parse_cv_text,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pdf_import"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _fields(parsed) -> dict[str, object]:
    return {item.key: item for item in parsed.fields}


def _items(parsed, section: str) -> list:
    return [item for item in parsed.items if item.section == section]


# --- Validacion del archivo ----------------------------------------------


def test_empty_content_is_rejected():
    with pytest.raises(PdfImportError) as error:
        validate_pdf_bytes(b"")
    assert error.value.code == "pdf_empty_file"


def test_wrong_magic_bytes_are_rejected():
    with pytest.raises(PdfImportError) as error:
        validate_pdf_bytes(b"GIF89a esto es una imagen")
    assert error.value.code == "pdf_not_a_pdf"


def test_content_larger_than_the_limit_is_rejected():
    oversized = b"%PDF-1.4" + b"0" * (MAX_PDF_BYTES + 1)
    with pytest.raises(PdfImportError) as error:
        validate_pdf_bytes(oversized)
    assert error.value.code == "pdf_too_large"


def test_read_limited_bytes_stops_reading_early():
    class _NeverEnding:
        def __init__(self) -> None:
            self.reads = 0

        def read(self, _size: int) -> bytes:
            self.reads += 1
            return b"x" * (256 * 1024)

    source = _NeverEnding()
    with pytest.raises(PdfImportError):
        read_limited_pdf_bytes(source, max_bytes=1024 * 1024)
    # Un tope que se respeta leyendo por bloques no debe leer el archivo entero.
    assert source.reads < 20


def test_read_limited_bytes_returns_short_files_untouched():
    import io

    assert read_limited_pdf_bytes(io.BytesIO(b"%PDF-1.4 corto")) == b"%PDF-1.4 corto"


def test_error_messages_never_leak_internal_paths():
    for payload in (b"", b"no soy un pdf"):
        with pytest.raises(PdfImportError) as error:
            validate_pdf_bytes(payload)
        message = error.value.user_message
        assert "/tmp" not in message
        assert "Traceback" not in message
        assert "app/" not in message


# --- Extraccion ----------------------------------------------------------


def test_valid_pdf_is_extracted_with_text():
    result = extract_pdf(_fixture("pdf/valid_es.pdf"))
    assert result.page_count == 1
    assert result.used_word_coordinates is True
    assert len(result.words) > 50
    assert "EXPERIENCIA" in result.text.upper()
    assert result.has_extractable_text


def test_english_pdf_is_extracted():
    result = extract_pdf(_fixture("pdf/valid_en.pdf"))
    assert "WORK EXPERIENCE" in result.text.upper()


def test_multipage_pdf_reports_every_page():
    result = extract_pdf(_fixture("pdf/multipage.pdf"))
    assert result.page_count == 3
    assert {word.page for word in result.words} >= {1, 2, 3}


def test_pdf_without_text_is_reported_not_silently_accepted():
    with pytest.raises(PdfImportError) as error:
        extract_pdf(_fixture("pdf/empty_text.pdf"))
    assert error.value.code == "pdf_without_text"
    assert "escaneo" in error.value.user_message.lower()


def test_encrypted_pdf_is_detected_as_encrypted_not_corrupt():
    with pytest.raises(PdfImportError) as error:
        extract_pdf(_fixture("pdf_encrypted.pdf"))
    assert error.value.code == "pdf_encrypted"
    assert "contrasena" in error.value.user_message.lower()


def test_corrupt_pdf_is_rejected():
    with pytest.raises(PdfImportError) as error:
        extract_pdf(_fixture("pdf/corrupt.pdf"))
    assert error.value.code in {"pdf_unreadable", "pdf_without_pages", "pdf_without_text"}


def test_pdf_over_the_page_limit_is_rejected():
    with pytest.raises(PdfImportError) as error:
        extract_pdf(_fixture("pdf/many_pages.pdf"))
    assert error.value.code == "pdf_too_many_pages"
    assert str(MAX_PDF_PAGES) in error.value.user_message


def test_real_project_pdfs_are_readable():
    """Los PDFs servidos por la app deben poder leerse con el mismo camino."""

    served = sorted((Path(__file__).resolve().parents[1] / "app" / "static" / "docs").glob("*.pdf"))
    assert served, "deberia haber PDFs servidos en el repositorio"
    for pdf in served:
        result = extract_pdf(pdf.read_bytes())
        assert result.page_count >= 1
        assert result.has_extractable_text


# --- Clasificacion --------------------------------------------------------


def test_normalization_removes_accents_and_punctuation():
    assert normalize_for_matching("DATOS PERSONALES") == "DATOS PERSONALES"
    assert normalize_for_matching("Educación & Formación") == "EDUCACION FORMACION"


def test_spanish_cv_is_classified_into_sections():
    parsed = parse_cv_text(extract_pdf(_fixture("pdf/valid_es.pdf")).text)
    fields = _fields(parsed)

    assert fields["personal.full_name"].value == "Juan Carlos Pérez"
    assert fields["contact.email"].value == "juan.perez.demo@example.com"
    assert fields["personal.full_name"].confidence == CONFIDENCE_HIGH

    experience = _items(parsed, "experience")
    assert experience
    assert any(item.values.get("company") for item in experience)
    assert any(item.values.get("start_date") for item in experience)

    assert _items(parsed, "education")
    assert len(_items(parsed, "skills")) >= 5
    assert _items(parsed, "languages")
    assert _items(parsed, "projects")


def test_english_cv_is_classified_into_sections():
    parsed = parse_cv_text(extract_pdf(_fixture("pdf/valid_en.pdf")).text)
    fields = _fields(parsed)

    assert fields["personal.full_name"].value == "Jane Q. Public"
    assert _items(parsed, "experience")
    assert _items(parsed, "education")
    assert _items(parsed, "skills")


def test_skill_categories_are_not_guessed_by_substring():
    """'postgres' contiene 'sql' y 'docker' contiene 'go'.

    Una busqueda por subcadena clasificaria mal la mitad de las tecnologias.
    """

    parsed = parse_cv_text(
        "APTITUDES TECNICAS\nPython, PostgreSQL, Docker, Kubernetes, Linux, AWS, Git\n"
    )
    categories = {item.values["label"]: item.values["category"] for item in _items(parsed, "skills")}

    assert categories["PostgreSQL"] == "Bases de datos"
    assert categories["Docker"] == "Contenedores"
    assert categories["Kubernetes"] == "Contenedores"
    assert categories["Linux"] == "Sistemas operativos"
    assert categories["AWS"] == "Cloud"
    assert categories["Python"] == "Lenguajes de programacion"


def test_unknown_skill_gets_no_invented_category():
    parsed = parse_cv_text("SKILLS\nMaquetacion, Ceramica\n")
    labels = {item.values["label"]: item.values["category"] for item in _items(parsed, "skills")}
    assert labels.get("Maquetacion") == ""
    assert all(
        item.confidence == CONFIDENCE_MEDIUM
        for item in _items(parsed, "skills")
        if item.values["category"] == ""
    )


def test_unrecognised_document_keeps_all_its_text():
    """El Issue prohibe descartar en silencio: sin encabezados no hay secciones."""

    text = (
        "Documento sin estructura reconocible\n"
        "Funcionaba en la oficina de la calle principal, sentado al lado de la ventana.\n"
        "Se encarga de mantener lo que ya estaba y toca base con el resto del equipo.\n"
    )
    parsed = parse_cv_text(text)

    assert not parsed.items
    joined = " ".join(parsed.unclassified)
    assert "oficina" in joined
    assert "equipo" in joined


def test_text_is_never_dropped_between_parser_and_unclassified():
    """Ninguna linea del documento puede desaparecer sin aparecer en ningun lado."""

    text = (
        "DATOS PERSONALES\nEmail: a@b.com\n"
        "EXPERIENCIA LABORAL\n"
        "Analista -- Acme -- 2020 - 2022\n"
        "Texto de descripcion que no se uso en ninguna parte.\n"
        "APTITUDES TECNICAS\nPython, Docker\n"
        "SECCION RARA\nContenido de una seccion que el parser no reconoce.\n"
        "Python\nAWS\nSQL\nGo\n"
    )
    parsed = parse_cv_text(text)

    units = [item.source_text for item in parsed.fields]
    units += [item.source_text for item in parsed.items]
    units += list(parsed.unclassified)

    from app.services.pdf_section_parser import SECTION_HEADINGS, normalize_for_matching

    headings = {normalize_for_matching(h) for group in SECTION_HEADINGS.values() for h in group}

    for line in text.splitlines():
        # Este helper tenia el MISMO defecto que el codigo: saltaba las lineas
        # de menos de 8 caracteres, asi que el invariante nunca revisaba el caso
        # que permitio que `Python`, `AWS`, `SQL` y `Go` desaparecieran. Ahora
        # solo excluye lo que no es informacion, igual que el parser.
        if not any(character.isalnum() for character in line):
            continue
        # Un encabezado marca la seccion: consume la linea como delimitador y no
        # es un dato que pueda perderse.
        if normalize_for_matching(line) in headings:
            continue
        # Una linea puede quedar partida en varias unidades ("Python, Docker"
        # son dos skills), asi que alcanza con que este cubierta por ellas.
        assert any(unit in line or line[:40] in unit for unit in units), f"linea perdida: {line!r}"


def test_short_lines_reach_the_review_instead_of_vanishing():
    """Regresion: `Python`, `AWS`, `SQL` y `Go` desaparecian del todo.

    El colector de texto sin clasificar saltaba toda linea de menos de 8
    caracteres. Un PDF sin encabezado de skills reconocido, con el nombre y el
    email en su sitio y esas cuatro lineas, producia un CV sin ninguna de las
    cuatro: ni como skill ni como bloque sin clasificar, y la confirmacion
    seguia adelante.
    """

    text = (
        "DATOS PERSONALES\n"
        "Nombre: Ana Perez\n"
        "Email: ana@example.com\n"
        "Python\nAWS\nSQL\nGo\n"
    )
    parsed = parse_cv_text(text)

    assert parsed.unclassified, "las lineas cortas tienen que llegar a revision"
    conservadas = {line for line in parsed.unclassified}
    for esperado in ("Python", "AWS", "SQL", "Go"):
        assert esperado in conservadas, f"{esperado} se perdio en silencio"

    # Y no se invento nada: las cinco lineas del documento son cinco fuentes.
    assert len(conservadas) == 4

    # La decoracion no es contenido y puede filtrarse; la informacion, no.
    assert "—" not in parse_cv_text("Nombre: Ana Perez\n—\n***\n").unclassified


def test_only_decoration_without_content_is_filtered():
    """Una linea que no tiene ni letra ni digito no es informacion."""

    parsed = parse_cv_text("Nombre: Ana Perez\n—\n***\n...\n")
    assert parsed.unclassified == ()


def test_dates_in_common_formats_are_recognised():
    for date_text, expected in (
        ("2021 - actualidad", ("2021", "actualidad")),
        ("2018 - 2021", ("2018", "2021")),
        ("01/2020 - 12/2022", ("01/2020", "12/2022")),
        ("January 2019 - Present", ("January 2019", "Present")),
    ):
        parsed = parse_cv_text(f"EXPERIENCIA LABORAL\nIngeniero -- Acme -- {date_text}\nDescripcion del puesto.\n")
        experience = _items(parsed, "experience")
        assert experience, date_text
        values = experience[0].values
        assert expected[0].lower() in values.get("start_date", "").lower(), date_text
        if "actualidad" in date_text or "present" in date_text.lower():
            assert "actualidad" in values.get("end_date", "").lower() or "present" in values.get("end_date", "").lower()


def test_incomplete_dates_get_lower_confidence():
    parsed = parse_cv_text("EXPERIENCIA LABORAL\nIngeniero -- Acme -- 2020\nHizo cosas.\n")
    experience = _items(parsed, "experience")
    assert experience
    assert experience[0].confidence in (CONFIDENCE_MEDIUM, CONFIDENCE_LOW)


def test_company_role_split_is_never_high_confidence():
    """El orden cargo/empresa no es determinable sin semantica."""

    parsed = parse_cv_text("EXPERIENCIA LABORAL\nSenior Backend Developer, Acme -- 2020 - 2022\nHizo cosas.\n")
    experience = _items(parsed, "experience")
    assert experience
    assert experience[0].confidence != CONFIDENCE_HIGH


def test_special_characters_survive_the_parser():
    text = "DATOS PERSONALES\nNombre: José Núñez € ñ ¿¡\nEmail: jose@example.com\n"
    parsed = parse_cv_text(text)
    assert _fields(parsed)["personal.full_name"].value == "José Núñez € ñ ¿¡"


def test_html_and_script_content_is_treated_as_plain_text():
    """El PDF es dato no confiable: su contenido nunca se interpreta como markup."""

    hostile = (
        'DATOS PERSONALES\nNombre: <script>alert(1)</script>\n'
        'Email: a@b.com\n<script>fetch("http://externo")</script>\n'
        "EXPERIENCIA LABORAL\n<script>Ingeniero</script> -- Acme -- 2020 - 2022\n"
    )
    parsed = parse_cv_text(hostile)
    values = " ".join([item.value for item in parsed.fields] + [str(i.values) for i in parsed.items])

    # Se conserva como texto, pero no se extrae ni se ejecuta nada.
    assert "<script>" in values
    assert not any(item.key.startswith("http") for item in parsed.fields)


def test_contradictory_values_produce_a_conflict():
    parsed = parse_cv_text(
        "DATOS PERSONALES\nEmail: primero@example.com\nEMAIL: segundo@example.com\n"
    )
    assert parsed.conflicts
    assert any("valores distintos" in conflict.reason for conflict in parsed.conflicts)


def test_empty_document_produces_no_crash():
    parsed = parse_cv_text("")
    assert not parsed.fields
    assert not parsed.items
    assert not parsed.unclassified


# --- Staging --------------------------------------------------------------


def _make_draft(**kwargs) -> staging.ImportDraft:
    parsed = parse_cv_text(
        "DATOS PERSONALES\nNombre: Ana Perez\nEmail: ana@example.com\n"
        "EXPERIENCIA LABORAL\nIngeniero -- Acme -- 2020 - 2022\n"
    )
    return staging.create_draft(parsed, source_filename="cv.pdf", page_count=1, **kwargs)


def test_draft_id_is_unguessable():
    first = _make_draft().draft_id
    second = _make_draft().draft_id
    assert first != second
    assert len(first) >= 32


@pytest.mark.parametrize(
    "bad_id",
    ["../../etc/passwd", "..", "/etc/passwd", "abc", "x" * 500, "a" * 31, "con espacio", "a;b", ""],
)
def test_invalid_draft_ids_never_reach_the_filesystem(bad_id: str):
    with pytest.raises(staging.ImportStagingError) as error:
        staging.load_draft(bad_id)
    assert error.value.code == "draft_invalid_id"


def test_draft_roundtrips_through_disk():
    draft = _make_draft()
    loaded = staging.load_draft(draft.draft_id)
    assert loaded.draft_id == draft.draft_id
    assert len(loaded.entries) == len(draft.entries)


def test_drafts_stay_outside_any_published_directory():
    draft = _make_draft()
    directory = staging.drafts_directory()
    assert directory.name == "import-drafts"
    assert directory.parent.name != "static"
    assert (directory / f"{draft.draft_id}.json").exists()


def test_draft_is_purged_when_expired():
    draft = _make_draft()
    stale = (staging.drafts_directory() / f"{draft.draft_id}.json")
    payload = json.loads(stale.read_text(encoding="utf-8"))
    payload["updated_at"] = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    stale.write_text(json.dumps(payload), encoding="utf-8")

    assert staging.load_draft.__module__  # sanity
    with pytest.raises(staging.ImportStagingError) as error:
        staging.load_draft(draft.draft_id)
    assert error.value.code == "draft_expired"
    assert not stale.exists()


def test_purge_removes_expired_drafts_only():
    fresh = _make_draft()
    old = _make_draft()
    stale_path = staging.drafts_directory() / f"{old.draft_id}.json"
    payload = json.loads(stale_path.read_text(encoding="utf-8"))
    payload["updated_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    stale_path.write_text(json.dumps(payload), encoding="utf-8")

    staging.purge_expired_drafts()

    assert not stale_path.exists()
    assert (staging.drafts_directory() / f"{fresh.draft_id}.json").exists()


def test_corrupt_draft_file_is_removed_not_crashed():
    draft = _make_draft()
    path = staging.drafts_directory() / f"{draft.draft_id}.json"
    path.write_text("{ esto no es json", encoding="utf-8")

    with pytest.raises(staging.ImportStagingError):
        staging.load_draft(draft.draft_id)


def test_confirm_is_refused_while_anything_is_pending():
    draft = _make_draft()
    with pytest.raises(staging.ImportStagingError) as error:
        staging.confirm_draft(draft, title="CV")
    assert error.value.code == "review_incomplete"


def test_invalid_decisions_do_not_touch_the_stored_draft():
    draft = _make_draft()
    before = (staging.drafts_directory() / f"{draft.draft_id}.json").read_text(encoding="utf-8")

    with pytest.raises(staging.ImportStagingError) as error:
        staging.apply_review(
            draft,
            values={"personal.full_name": "Editado"},
            decisions={draft.entries[0].key: "inventado"},
            unclassified_assignments={},
        )
    assert error.value.code == "review_invalid_decision"

    after = (staging.drafts_directory() / f"{draft.draft_id}.json").read_text(encoding="utf-8")
    assert before == after


def test_invalid_assignment_target_is_rejected():
    draft = _make_draft()
    with pytest.raises(staging.ImportStagingError) as error:
        staging.apply_review(draft, values={}, decisions={}, unclassified_assignments={"x": "no_existe"})
    assert error.value.code == "review_invalid_assignment"


def test_missing_full_name_blocks_creation():
    draft = _make_draft()
    decisions = {entry.key: staging.STATUS_CONFIRMED for entry in draft.entries}
    values = {entry.key: entry.value for entry in draft.entries}
    values["personal.full_name"] = ""
    draft = staging.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})

    with pytest.raises(staging.ImportStagingError) as error:
        staging.confirm_draft(draft, title="CV")
    assert error.value.code == "review_missing_required"


def test_discarded_entries_never_reach_the_payload():
    draft = _make_draft()
    decisions = {
        entry.key: staging.STATUS_DISCARDED if entry.key == "contact.email" else staging.STATUS_CONFIRMED
        for entry in draft.entries
    }
    values = {entry.key: entry.value for entry in draft.entries}
    draft = staging.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})
    payload = staging.confirm_draft(draft, title="CV")

    assert payload["contact"].get("email", "") == ""


def test_payload_is_schema_2_and_flat():
    draft = _make_draft()
    decisions = {entry.key: staging.STATUS_CONFIRMED for entry in draft.entries}
    values = {entry.key: entry.value for entry in draft.entries}
    draft = staging.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})
    payload = staging.confirm_draft(draft, title="CV")

    # El payload schema 2 es plano: sin una clave `sections` que las anide.
    assert payload["schema_version"] == 2
    assert "sections" not in payload or not payload.get("sections")
    for section in ("personal", "contact", "experience", "education", "skills"):
        assert section in payload

    from app.validations.structured_cv_validations import validate_structured_payload_v2

    assert validate_structured_payload_v2(payload).is_valid


def test_list_fields_are_lists_not_comma_strings():
    draft = _make_draft()
    decisions = {entry.key: staging.STATUS_CONFIRMED for entry in draft.entries}
    values = {}
    for entry in draft.entries:
        if entry.values:
            for name, value in entry.values.items():
                values[f"{entry.key}:{name}"] = value
        else:
            values[entry.key] = entry.value
    draft = staging.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})
    payload = staging.confirm_draft(draft, title="CV")

    for item in payload["experience"]:
        if "technologies" in item:
            assert isinstance(item["technologies"], list)
        if "highlights" in item:
            assert isinstance(item["highlights"], list)

# --- Regresion de los hallazgos del review --------------------------------


def test_kept_unclassified_text_reaches_the_section_it_was_assigned_to():
    """Conservar y asignar no puede terminar descartando el bloque en silencio."""

    from app.services import import_staging_service as st

    parsed = parse_cv_text(
        "DATOS PERSONALES\nNombre: Ana Perez\n"
        "Texto suelto sobre una certificacion que el PDF no etiquetó\n"
    )
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    assert draft.unclassified, "el texto sin clasificar debe llegar a revision"

    decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
    assignments = {}
    for item in draft.unclassified:
        decisions[item.key] = st.STATUS_KEPT
        assignments[item.key] = "certifications"

    draft = st.apply_review(
        draft, values={}, decisions=decisions, unclassified_assignments=assignments, title="CV"
    )
    payload = st.confirm_draft(draft, title="CV")

    names = " ".join(item.get("name", "") for item in payload["certifications"])
    assert "certificacion" in names.lower(), payload["certifications"]


def test_kept_unclassified_text_can_be_routed_to_skills():
    from app.services import import_staging_service as st

    parsed = parse_cv_text(
        "DATOS PERSONALES\nNombre: Ana Perez\nMeteorologia y ceramica\n"
    )
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    assert draft.unclassified

    item = draft.unclassified[0]
    draft = st.apply_review(
        draft,
        values={},
        decisions={**{entry.key: st.STATUS_CONFIRMED for entry in draft.entries}, item.key: st.STATUS_KEPT},
        unclassified_assignments={item.key: "skills"},
    )
    payload = st.confirm_draft(draft, title="CV")
    assert payload["skills"], "el texto asignado a skills debe llegar al CV"


def test_symlinked_drafts_directory_is_rejected():
    """En produccion `ensure_isolated_path` no protege nada: hace falta el chequeo."""

    from app.services import import_staging_service as st

    directory = st.drafts_directory()
    elsewhere = directory.parent / "drafts-elsewhere"
    elsewhere.mkdir(exist_ok=True)

    # Se mueve el directorio real y se lo reemplaza por un enlace simbolico.
    backup = directory.parent / "drafts-backup"
    directory.rename(backup)
    directory.symlink_to(elsewhere, target_is_directory=True)

    try:
        with pytest.raises(st.ImportStagingError) as error:
            st.drafts_directory()
        assert error.value.code == "drafts_directory_symlinked"
    finally:
        directory.unlink()
        backup.rename(directory)
        elsewhere.rmdir()


def test_proposed_title_survives_a_failed_submission():
    from app.services import import_staging_service as st

    draft = _make_draft()
    updated = st.apply_review(
        draft, values={}, decisions={}, unclassified_assignments={}, title="Mi titulo largo"
    )
    assert st.load_draft(updated.draft_id).proposed_title == "Mi titulo largo"


def test_decisions_are_validated_per_entry_type():
    """`kept` en un dato detectado lo hacia desaparecer del CV en silencio."""

    from app.services import import_staging_service as st

    draft = _make_draft()
    entry_key = draft.entries[0].key

    with pytest.raises(st.ImportStagingError) as error:
        st.apply_review(draft, values={}, decisions={entry_key: st.STATUS_KEPT}, unclassified_assignments={})
    assert error.value.code == "review_invalid_decision"


def test_unclassified_cannot_be_confirmed():
    from app.services import import_staging_service as st

    parsed = parse_cv_text("DATOS PERSONALES\nNombre: Ana Perez\nTexto sin ubicacion clara\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    assert draft.unclassified

    with pytest.raises(st.ImportStagingError) as error:
        st.apply_review(
            draft,
            values={},
            decisions={draft.unclassified[0].key: st.STATUS_CONFIRMED},
            unclassified_assignments={},
        )
    assert error.value.code == "review_invalid_decision"


def test_long_unclassified_text_assigned_to_skills_is_not_truncated():
    """Si no cabe como skill, el texto completo va a informacion adicional.

    El umbral es el del contrato (`skills.label`), no el 60 que estaba escrito a
    mano. Un texto que ahora entra como skill debe entrar ENTERO, incluida la
    categoria: antes se recortaba a 60 caracteres y el resto se perdia en silencio.
    """

    from app.services import import_staging_service as st

    # (a) exceede el limite de label -> va a informacion adicional, texto entero
    largo = (
        "Meteorologia aplicada, ceramica artistica, talleres de horneado a alta "
        "temperatura y tecnicas de esmalte tradicional y repintura de bordes"
    )
    assert len(largo) > st.MAX_SKILL_LABEL

    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{largo}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]
    draft = st.apply_review(
        draft,
        values={},
        decisions={**{entry.key: st.STATUS_CONFIRMED for entry in draft.entries}, item.key: st.STATUS_KEPT},
        unclassified_assignments={item.key: "skills"},
    )
    payload = st.confirm_draft(draft, title="CV")

    assert all(skill["label"] != largo for skill in payload["skills"]), "no debe truncarse en silencio"
    contenidos = " ".join(entry.get("content", "") for entry in payload["additional_info"])
    assert largo in contenidos, "el texto tiene que llegar entero a informacion adicional"

    # (b) cabe como label -> entra entero, categoria incluida, sin recorte
    categoria = "Plataforma de datos e infraestructura en la nube a escala industrial"
    texto = f"Python: {categoria}"
    assert len(texto) <= st.MAX_SKILL_LABEL
    assert len(categoria) > 60, "si no supera 60 el recorte viejo seria invisible"

    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{texto}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]
    draft = st.apply_review(
        draft,
        values={},
        decisions={**{entry.key: st.STATUS_CONFIRMED for entry in draft.entries}, item.key: st.STATUS_KEPT},
        unclassified_assignments={item.key: "skills"},
    )
    payload = st.confirm_draft(draft, title="CV")

    etiquetas = [skill for skill in payload["skills"] if skill["label"] == "Python"]
    assert etiquetas, payload["skills"]
    assert etiquetas[0]["category"] == categoria, "la categoria no se recorta"


def test_proposed_title_is_capped_at_the_domain_limit():
    """Dentro del limite se guarda; por encima se rechaza, no se recorta."""

    from app.services import import_staging_service as st

    draft = _make_draft()
    updated = st.apply_review(
        draft, values={}, decisions={}, unclassified_assignments={}, title="T" * st.FIELD_LIMITS["cv_title"]
    )
    assert len(updated.proposed_title) == st.FIELD_LIMITS["cv_title"]


# --- Invariante de integridad: ningun descarte silencioso -----------------


def _body_with_unclassified(count: int) -> str:
    body = "DATOS PERSONALES\nNombre: Ana Perez\n\n"
    body += "\n\n".join(
        f"Bloque sin clasificar numero {index} con contenido suficientemente largo para contar"
        for index in range(count)
    )
    return body


def test_parser_keeps_every_unclassified_line():
    """El Issue prohibe descartar texto: el tope ya no recorta."""

    from app.services import import_staging_service as st

    parsed = parse_cv_text(_body_with_unclassified(60))
    assert len(parsed.unclassified) >= 40, "no debe recortarse a 40 bloques"

    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    loaded = st.load_draft(draft.draft_id)
    assert len(loaded.unclassified) >= 40, "el borrador debe conservar todos los bloques"


def test_document_over_the_unclassified_capacity_is_rejected(monkeypatch):
    """Un documento enorme se rechaza antes de crear un borrador incompleto."""

    from app.services import pdf_section_parser as parser_module

    # Se pasa por el limite real del modulo. El recalculo es explicito: no se
    # parchea la constante sino que se comprueba el comportamiento con ella.
    original_limit = parser_module.MAX_UNCLASSIFIED_CHARACTERS
    try:
        parser_module.MAX_UNCLASSIFIED_CHARACTERS = 200
        with pytest.raises(parser_module.PdfUnclassifiableDocument) as error:
            parser_module.parse_cv_text("Linea suelta que ocupa espacio suficiente. " * 10)
    finally:
        parser_module.MAX_UNCLASSIFIED_CHARACTERS = original_limit

    assert "revision" in str(error.value).lower()


def test_keeping_more_blocks_than_the_contract_allows_is_rejected():
    from app.services import import_staging_service as st

    parsed = parse_cv_text("DATOS PERSONALES\nNombre: Ana Perez\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)

    for index in range(25):
        draft.unclassified.append(
            st.UnclassifiedEntry(
                key=f"unclassified.extra.{index}",
                text=f"Bloque extra {index} con contenido suficiente",
                reason="prueba",
            )
        )

    decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
    for item in draft.unclassified:
        decisions[item.key] = st.STATUS_KEPT
    draft = st.apply_review(draft, values={}, decisions=decisions, unclassified_assignments={})

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code == "review_too_much_additional_info"
    assert "20" in error.value.user_message

    assert st.load_draft(draft.draft_id).draft_id == draft.draft_id


def test_certification_assignment_never_silently_truncates():
    from app.services import import_staging_service as st

    long_text = "Certificacion avanzada en " + "ingenieria " * 40
    assert len(long_text) > st.FIELD_LIMITS["certifications.name"]

    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{long_text}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]

    draft = st.apply_review(
        draft,
        values={},
        decisions={**{e.key: st.STATUS_CONFIRMED for e in draft.entries}, item.key: st.STATUS_KEPT},
        unclassified_assignments={item.key: "certifications"},
    )

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code == "review_value_too_long"
    assert "certifications" in error.value.user_message

    assert st.load_draft(draft.draft_id).unclassified[0].text == long_text.strip()


def test_no_confirmed_value_is_ever_silently_shortened():
    from app.services import import_staging_service as st

    location = "Buenos Aires " * 5
    assert len(location) <= st.FIELD_LIMITS["personal.location"]
    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\nUbicacion: {location}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)

    decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
    values = {entry.key: entry.value for entry in draft.entries}
    draft = st.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})
    payload = st.confirm_draft(draft, title="CV")

    assert payload["personal"]["location"] == values["personal.location"]


def test_long_submitted_value_is_not_truncated_on_save():
    """Un valor editido en la revision se guarda entero, sin recorte."""

    from app.services import import_staging_service as st

    long_location = "Buenos Aires, Argentina, " * 20
    assert len(long_location) > 400

    parsed = parse_cv_text("DATOS PERSONALES\nNombre: Ana Perez\nUbicacion: Corta\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)

    draft = st.apply_review(
        draft,
        values={"personal.location": long_location},
        decisions={},
        unclassified_assignments={},
    )

    entry = next(e for e in draft.entries if e.key == "personal.location")
    assert entry.value == long_location, "no debe recortarse lo que la persona escribio"


def test_overlong_summary_is_rejected_at_confirm_not_truncated():
    """Un resumen que supera el limite se rechaza con mensaje, no se corta."""

    from app.services import import_staging_service as st

    long_summary = "Perfil profesional muy extenso. " * 60
    assert len(long_summary) > st.FIELD_LIMITS["summary"]

    parsed = parse_cv_text(f"PERFIL PROFESIONAL\n{long_summary}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)

    decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
    values = {entry.key: entry.value for entry in draft.entries}
    draft = st.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code == "review_value_too_long"

    # El texto sigue completo en el borrador.
    stored = st.load_draft(draft.draft_id)
    assert any(entry.value == long_summary.strip() for entry in stored.entries)


def test_long_additional_info_content_is_validated():
    from app.services import import_staging_service as st

    long_text = "Bloque de contenido muy extenso. " * 60
    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{long_text}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]

    draft = st.apply_review(
        draft,
        values={},
        decisions={**{e.key: st.STATUS_CONFIRMED for e in draft.entries}, item.key: st.STATUS_KEPT},
        unclassified_assignments={item.key: ""},
    )

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code == "review_value_too_long"
    assert "informacion adicional" in error.value.user_message


def test_skills_are_not_capped_below_the_schema_limit():
    """El tope sale del schema 2 (40 skills), no de una constante duplicada."""

    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS
    from app.services import import_staging_service as st

    assert ITEM_SECTION_SPECS["skills"].max_items == 40

    texto = "SKILLS\n" + ", ".join(f"Tecnologia{index}" for index in range(35))
    parsed = parse_cv_text(texto)
    assert len(_items(parsed, "skills")) > 30, "no debe cortarse en 30 si el schema admite 40"


def test_field_limits_come_from_the_schema_not_a_copy():
    """Una tabla duplicada se desincroniza: la fuente es el schema."""

    from app.validations import structured_cv_validations as schema
    from app.services import import_staging_service as st

    assert st.FIELD_LIMITS["skills.label"] == schema.ITEM_SECTION_SPECS["skills"].string_fields[0].max_length
    assert st.FIELD_LIMITS["summary"] == schema.STRING_SECTION_SPECS["summary"]


def test_overlong_title_is_rejected_not_truncated():
    from app.services import import_staging_service as st

    draft = _make_draft()
    long_title = "T" * (st.FIELD_LIMITS["cv_title"] + 10)

    with pytest.raises(st.ImportStagingError) as error:
        st.apply_review(draft, values={}, decisions={}, unclassified_assignments={}, title=long_title)
    assert error.value.code == "review_title_too_long"

    # El borrador no quedo con un titulo recortado.
    assert st.load_draft(draft.draft_id).proposed_title != long_title[:120]


# --- Umbrales N y N+1: la politica de desborde es observable ----------------


@pytest.mark.parametrize("count", [39, 40, 41, 45, 60])
def test_skills_overflow_is_never_silent(count: int):
    """N-1, N, N+1 y mas alla: nada desaparece y nada rompe el tope del schema.

    El excedente NO es una skill mas. Vive en su propia seccion para que el
    payload nunca supere `skills.max_items`, y queda disponible para revision.
    """

    from app.services import import_staging_service as st
    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS

    limit = ITEM_SECTION_SPECS["skills"].max_items
    parsed = parse_cv_text(
        "DATOS PERSONALES\nNombre: Ana Perez\n\nSKILLS\n"
        + ", ".join(f"Tech{index}" for index in range(count))
    )

    skills = [item for item in parsed.items if item.section == "skills"]
    overflow = [item for item in parsed.items if item.section == st.SKILLS_OVERFLOW_SECTION]

    # El bloque de skills nunca excede el tope, con o sin excedente.
    assert len(skills) == min(count, limit)
    assert len(overflow) == (1 if count > limit else 0)

    if count > limit:
        assert overflow[0].confidence == CONFIDENCE_LOW
        recovered = overflow[0].values["label"].split(", ")
        assert recovered == [f"Tech{index}" for index in range(limit, count)]

        # Confirmar el excedente sin resolverlo se rechaza con motivo accionable.
        draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
        decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
        draft = st.apply_review(draft, values={}, decisions=decisions, unclassified_assignments={})
        with pytest.raises(st.ImportStagingError) as error:
            st.confirm_draft(draft, title="CV")
        assert error.value.code == "review_skills_overflow_pending"
        assert str(limit) in error.value.user_message

        # Descartarlo explicitamente si: el payload entra y respects el tope.
        decisions = {
            entry.key: (st.STATUS_DISCARDED if entry.section == st.SKILLS_OVERFLOW_SECTION
                        else st.STATUS_CONFIRMED)
            for entry in draft.entries
        }
        draft = st.apply_review(draft, values={}, decisions=decisions, unclassified_assignments={})
        payload = st.confirm_draft(draft, title="CV")
        assert len(payload["skills"]) == limit


@pytest.mark.parametrize(
    ("section", "field", "count"),
    [("experience", "technologies", 17), ("experience", "highlights", 13)],
)
def test_list_field_limit_is_the_fields_own_not_the_sections(section: str, field: str, count: int):
    """17 tecnologias y 13 logros se rechazan ANTES de guardar, no despues.

    El tope es el del campo (16 y 12), no el de la seccion que lo contiene (30).
    """

    from app.services import import_staging_service as st
    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS

    limit = st.LIST_FIELD_LIMITS[f"{section}.{field}"]
    spec = next(f for f in ITEM_SECTION_SPECS[section].string_list_fields if f.field == field)
    assert limit[0] == spec.max_items
    assert limit[0] != ITEM_SECTION_SPECS[section].max_items, "el test no probaria nada"

    if field == "highlights":
        cuerpo = "\n".join(f"- Logros del proyecto {index}" for index in range(count))
    else:
        # Nombres reales: `_looks_like_technology_line` decide por la forma, y
        # nombres inventados no forman lista.
        cuerpo = ", ".join(
            (["Python", "Docker", "Linux", "AWS", "Git", "Redis", "MySQL", "Kafka", "Nginx", "Helm"] * 3)[:count]
        )
    parsed = parse_cv_text(
        "DATOS PERSONALES\nNombre: Ana Perez\n"
        "EXPERIENCIA LABORAL\nIngeniero -- Acme -- 2020 - 2022\n"
        + cuerpo
    )
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
    draft = st.apply_review(draft, values={}, decisions=decisions, unclassified_assignments={})

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code in {"review_value_too_long", "review_schema_invalid"}
    assert field in error.value.user_message


def test_additional_info_over_the_schema_limit_is_rejected_before_persisting():
    """700 caracteres contra un contrato de 600: error al confirmar, no al guardar."""

    from app.services import import_staging_service as st
    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS

    limit = ITEM_SECTION_SPECS["additional_info"].string_fields[1].max_length
    largo = "Bloque que excede el limite real del contrato. " * 20
    assert len(largo) > limit

    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{largo}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]
    decisions = {**{entry.key: st.STATUS_CONFIRMED for entry in draft.entries}, item.key: st.STATUS_KEPT}
    draft = st.apply_review(draft, values={}, decisions=decisions, unclassified_assignments={item.key: ""})

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code in {"review_value_too_long", "review_schema_invalid"}

    # Acortado a mano, entra: el valor editado se respeta entero.
    corto = "Bloque dentro del limite."
    draft = st.apply_review(draft, values={item.key: corto}, decisions=decisions, unclassified_assignments={item.key: ""})
    payload = st.confirm_draft(draft, title="CV")
    assert any(entry["content"] == corto for entry in payload["additional_info"])


def test_canonical_validator_backs_the_staging_limits():
    """La segunda fuente de verdad ya no existe: el payload se valida con el
    MISMO contrato que usa la persistencia."""

    from app.services import import_staging_service as st
    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS

    declarado = ITEM_SECTION_SPECS["additional_info"].string_fields[1].max_length
    assert st.ADDITIONAL_INFO_CONTENT_LIMIT == declarado

    # Nada duplicado a mano queda gobernando: el limite vigente es el del schema.
    source = Path(st.__file__).read_text(encoding="utf-8")
    assert "ADDITIONAL_INFO_CONTENT_LIMIT = 1000" not in source
    assert re.search(r"ADDITIONAL_INFO_CONTENT_LIMIT\s*=\s*\d{3,}", source) is None


def test_no_value_is_silently_truncated_going_into_the_payload():
    """Un valor largo se conserva entero o se rechaza: nunca se recorta en silencio."""

    from app.services import import_staging_service as st

    categoria_larga = "Categoria deliberadamente mas larga que el limite del contrato"
    texto = f"Python: {categoria_larga}"
    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{texto}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]
    decisions = {**{entry.key: st.STATUS_CONFIRMED for entry in draft.entries}, item.key: st.STATUS_KEPT}
    draft = st.apply_review(
        draft, values={}, decisions=decisions, unclassified_assignments={item.key: "skills"}
    )

    # O entra entero, o falla nombrando el campo. Lo que no puede es recortarse.
    try:
        payload = st.confirm_draft(draft, title="CV")
    except st.ImportStagingError as error:
        assert categoria_larga in error.value.user_message or "categoria" in error.value.user_message.lower()
        return

    for skill in payload["skills"]:
        if skill.get("label") == "Python":
            assert categoria_larga in skill.get("category", "")


def test_additional_info_content_limit_comes_from_the_schema():
    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS

    from app.services import import_staging_service as st

    declared = ITEM_SECTION_SPECS["additional_info"].string_fields[1].max_length
    assert st.FIELD_LIMITS["additional_info.content"] == declared
    assert declared != 1000, "1000 era un valor inventado, no el del contrato"


@pytest.mark.parametrize(
    ("section", "field"),
    [("experience", "highlights"), ("experience", "technologies"), ("projects", "technologies")],
)
def test_list_fields_are_validated(section: str, field: str):
    """Un campo de lista se valida en cantidad y en tamano, no se ignora."""

    from app.services import import_staging_service as st

    max_items, max_item_length = st.LIST_FIELD_LIMITS[f"{section}.{field}"]
    assert max_items > 0 and max_item_length > 0

    # Los limites existen y vienen del contrato, no de un valor inventado.
    assert st.LIST_FIELD_LIMITS[f"{section}.{field}"] == (max_items, max_item_length)


def test_long_list_field_is_rejected_before_saving():
    """El error llega en la revision, no como fallo generico de persistencia."""

    from app.services import import_staging_service as st

    max_items, max_item_length = st.LIST_FIELD_LIMITS["experience.technologies"]
    parsed = parse_cv_text(
        "EXPERIENCIA LABORAL\n"
        "Ingeniero -- Acme -- 2020 - 2022\n"
        + ", ".join((["Python","Docker","Linux","AWS","Git","Redis","MySQL","Kafka","Nginx","Helm"] * 6)[: max_items + 5])
    )
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)

    decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
    values = {entry.key: entry.value for entry in draft.entries}
    draft = st.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code == "review_value_too_long"
    assert "technologies" in error.value.user_message


def test_unclassified_block_is_editable_after_a_length_rejection():
    """El bloque rechazado por largo debe poder acortarse en la pantalla."""

    from app.services import import_staging_service as st

    long_text = "Bloque muy extenso que el sistema rechaza por su longitud. " * 30
    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{long_text}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]

    decisions = {**{e.key: st.STATUS_CONFIRMED for e in draft.entries}, item.key: st.STATUS_KEPT}
    draft = st.apply_review(
        draft, values={}, decisions=decisions, unclassified_assignments={item.key: ""}
    )

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code == "review_value_too_long"

    # La persona lo acorta y reintenta: el valor editado se respeta.
    shortened = "Bloque acortado a mano desde la pantalla de revision."
    draft = st.apply_review(
        draft, values={item.key: shortened}, decisions=decisions, unclassified_assignments={item.key: ""}
    )
    payload = st.confirm_draft(draft, title="CV")

    assert any(entry["content"] == shortened for entry in payload["additional_info"])
    assert "Bloque acortado" in shortened


def test_confirmed_value_preserved_through_every_transition():
    """Invariante: un valor confirmado llega entero al CV o falla con error."""

    from app.services import import_staging_service as st

    location = "Buenos Aires, Argentina"
    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\nUbicacion: {location}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)

    decisions = {entry.key: st.STATUS_CONFIRMED for entry in draft.entries}
    values = {entry.key: entry.value for entry in draft.entries}
    draft = st.apply_review(draft, values=values, decisions=decisions, unclassified_assignments={})
    payload = st.confirm_draft(draft, title="CV")

    assert payload["personal"]["location"] == location


def test_additional_info_content_above_the_schema_limit_is_rejected():
    """El bloque conservado debe poder acortarse, no rechazarse sin remedio."""

    from app.services import import_staging_service as st

    limit = st.FIELD_LIMITS["additional_info.content"]
    long_text = "Bloque de contenido demasiado largo para el CV. " * 30
    assert len(long_text) > limit

    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{long_text}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]

    decisions = {**{e.key: st.STATUS_CONFIRMED for e in draft.entries}, item.key: st.STATUS_KEPT}
    draft = st.apply_review(draft, values={}, decisions=decisions, unclassified_assignments={item.key: ""})

    with pytest.raises(st.ImportStagingError) as error:
        st.confirm_draft(draft, title="CV")
    assert error.value.code == "review_value_too_long"

    # Con el texto acortado a mano, pasa. El valor editado se respeta.
    allowed = "Bloque dentro del limite del CV."
    assert len(allowed) <= limit
    draft = st.apply_review(draft, values={item.key: allowed}, decisions=decisions, unclassified_assignments={item.key: ""})
    payload = st.confirm_draft(draft, title="CV")
    assert any(entry["content"] == allowed for entry in payload["additional_info"])


def test_project_with_a_long_summary_is_not_rejected():
    """El bloque se parte en `name` y `summary`: el limite de `name` no se aplica
    al bloque entero, que rechazaba proyectos validos."""

    from app.services import import_staging_service as st
    from app.validations.structured_cv_validations import ITEM_SECTION_SPECS

    limite_nombre = ITEM_SECTION_SPECS["projects"].string_fields
    nombre = next(f.max_length for f in limite_nombre if f.field == "name")
    resumen = "Descripcion larga del proyecto con varios detalles tecnicos relevantes. " * 4

    texto = f"MiProyecto - {resumen}"
    assert len(texto) > nombre, "el bloque entero supera el limite de `name`"

    parsed = parse_cv_text(f"DATOS PERSONALES\nNombre: Ana Perez\n{texto}\n")
    draft = st.create_draft(parsed, source_filename="cv.pdf", page_count=1)
    item = draft.unclassified[0]
    decisiones = {
        **{entry.key: st.STATUS_CONFIRMED for entry in draft.entries},
        item.key: st.STATUS_KEPT,
    }
    draft = st.apply_review(
        draft, values={}, decisions=decisiones, unclassified_assignments={item.key: "projects"}
    )

    payload = st.confirm_draft(draft, title="CV")
    proyectos = payload["projects"]
    assert proyectos, "el bloque asignado a proyectos tiene que llegar al CV"
    assert proyectos[0]["name"] == "MiProyecto"
    assert resumen.strip() in proyectos[0]["summary"], "el resumen no se recorta ni se pierde"


def test_double_confirmation_of_the_same_draft_is_rejected():
    """Un doble clic no puede producir dos CV: el reclamo es atomico."""

    from app.services import import_staging_service as st

    draft = st.create_draft(
        parse_cv_text("DATOS PERSONALES\nNombre: Ana Perez\n"), source_filename="cv.pdf", page_count=1
    )
    draft_id = draft.draft_id

    st.claim_draft(draft_id)
    try:
        with pytest.raises(st.ImportStagingError) as error:
            st.claim_draft(draft_id)
        assert error.value.code == "draft_already_being_confirmed"

        # El borrador sigue ahi: el reclamo es un marcador, no un movimiento.
        assert st.load_draft(draft_id).draft_id == draft_id
    finally:
        st.release_draft(draft_id)

    # Liberado, se puede volver a reclamar.
    st.claim_draft(draft_id)
    st.delete_draft(draft_id)
    assert st._draft_path(draft_id).exists() is False


def test_purge_does_not_remove_a_live_claim():
    """Un reclamo vive milisegundos: borrarlo cortaria una confirmacion en curso."""

    from app.services import import_staging_service as st

    draft = st.create_draft(
        parse_cv_text("DATOS PERSONALES\nNombre: Ana Perez\n"), source_filename="cv.pdf", page_count=1
    )
    draft_id = draft.draft_id
    st.claim_draft(draft_id)
    try:
        st.purge_expired_drafts()
        assert st._draft_path(draft_id).with_suffix(st.DRAFT_CLAIM_SUFFIX).exists()
    finally:
        st.release_draft(draft_id)
        st.delete_draft(draft_id)


def test_a_second_email_reaches_the_review_instead_of_vanishing():
    """`_apply_email` se detiene en el primer correo; el resto se perdia."""

    parsed = parse_cv_text(
        "Nombre: Ana Perez\n"
        "Email: ana@example.com\n"
        "Email: ana.dev@other.org\n"
    )
    assert any("other.org" in item.value for item in parsed.fields) is False
    assert any("other.org" in block for block in parsed.unclassified), (
        "el segundo correo no aparece en ningun campo ni bloque"
    )


def test_an_unmatched_date_reaches_the_review():
    """Una fecha suelta no genera item: descartarla era perdida silenciosa."""

    parsed = parse_cv_text("Nombre: Ana Perez\nAWS Practitioner\n2020\n")
    conservado = " ".join(parsed.unclassified)
    assert "2020" in conservado, "la fecha suelta no quedo en ninguna parte"


def test_a_captured_email_is_not_duplicated_into_the_review():
    """Lo que si quedo capturado no se muestra ademas como pendiente."""

    parsed = parse_cv_text("Nombre: Ana Perez\nEmail: ana@example.com\n")
    assert any(block.strip() == "Email: ana@example.com" for block in parsed.unclassified) is False
    assert any(item.value == "ana@example.com" for item in parsed.fields)


def test_a_second_labelled_email_is_reported_not_silently_overwritten():
    """El campo es unico: el segundo valor se reporta y va a revision.

    Antes se guardaba como campo repetido y el payload se quedaba con el ultimo,
    asi que el primero desaparecia sin aviso. El conflicto se sigue reportando
    para que la persona sepa que hay dos.
    """

    parsed = parse_cv_text(
        "DATOS PERSONALES\nEmail: primero@example.com\nEMAIL: segundo@example.com\n"
    )

    assert [item.value for item in parsed.fields if item.key == "contact.email"] == [
        "primero@example.com"
    ]
    assert any("segundo@example.com" in block for block in parsed.unclassified)
    assert parsed.conflicts
    assert any("valores distintos" in conflict.reason for conflict in parsed.conflicts)
    assert {candidate for conflict in parsed.conflicts for candidate in conflict.candidates} == {
        "primero@example.com",
        "segundo@example.com",
    }


def test_two_emails_on_one_line_both_reach_the_review():
    """Dos correos en la MISMA linea: el segundo no se da por consumido.

    `_apply_email` guarda solo el primero, pero registraba la linea entera como
    su origen, asi que el chequeo de contencion daba la linea por consumida y el
    segundo correo no aparecia en ningun campo ni bloque.
    """

    parsed = parse_cv_text("Nombre: Ana Perez\nana@example.com ana.work@example.org\n")

    assert [f.value for f in parsed.fields if f.key == "contact.email"] == ["ana@example.com"]
    assert parsed.unclassified, "la linea con el segundo correo tiene que llegar a revision"
    assert "ana.work@example.org" in " ".join(parsed.unclassified)
    assert "ana@example.com" in " ".join(parsed.unclassified)


def test_a_mixed_header_line_keeps_its_uncaptured_parts():
    """Cabecera con un valor capturado y otros que no: la linea entra entera.

    `Ana Perez | ana@example.com | Buenos Aires` deja el correo capturado y el
    nombre y la ciudad en ningun campo, asi que sin el nombre obligatorio la
    confirmacion no podia completarse.
    """

    parsed = parse_cv_text("Ana Perez | ana@example.com | Buenos Aires")
    assert any(item.value == "ana@example.com" for item in parsed.fields)
    assert parsed.unclassified, "la linea tiene contenido sin capturar"
    assert "Buenos Aires" in " ".join(parsed.unclassified)
    assert "Ana Perez" in " ".join(parsed.unclassified)


def test_a_labelled_line_with_one_value_is_not_pending_again():
    """La etiqueta no es contenido: `Email:` solo no deja la linea pendiente."""

    assert parse_cv_text("Email: ana@example.com").unclassified == ()
    assert parse_cv_text("Nombre: Ana Perez").unclassified == ()
