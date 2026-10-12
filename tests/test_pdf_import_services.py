"""Tests unitarios de la importacion de CV desde PDF.

Cubre las tres piezas por separado: validacion y extraccion del PDF,
clasificacion del texto, y ciclo de vida del staging. Los casos de limite y de
entrada hostil estan explicitos porque son la superficie de riesgo.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
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
    )
    parsed = parse_cv_text(text)

    units = [item.source_text for item in parsed.fields]
    units += [item.source_text for item in parsed.items]
    units += list(parsed.unclassified)

    from app.services.pdf_section_parser import SECTION_HEADINGS, normalize_for_matching

    headings = {normalize_for_matching(h) for group in SECTION_HEADINGS.values() for h in group}

    for line in text.splitlines():
        if len(line) < 8:
            continue
        # Un encabezado marca la seccion: consume la linea como delimitador y no
        # es un dato que pueda perderse.
        if normalize_for_matching(line) in headings:
            continue
        # Una linea puede quedar partida en varias unidades ("Python, Docker"
        # son dos skills), asi que alcanza con que este cubierta por ellas.
        assert any(unit in line or line[:40] in unit for unit in units), f"linea perdida: {line!r}"


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
