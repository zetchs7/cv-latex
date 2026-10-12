# PDF import fixtures

Deterministic PDF fixtures for the CV-from-PDF import tests. The import code
is expected to drive `pdfinfo` and `pdftotext` (poppler-utils), so every
fixture here was validated against the real binaries, not against a Python
PDF library.

Everything under `pdf/` plus `pdf_encrypted.pdf` is **committed to the
repository**. Tests never regenerate a fixture and never require `qpdf` to be
installed.

## Layout

| Path | What it is |
| --- | --- |
| `pdf_builder.py` | Stdlib-only PDF writer. Builds valid, byte-deterministic PDF 1.4 files. |
| `generate.py` | Regenerates every fixture. Also builds `pdf_encrypted.pdf` when `qpdf` is present. |
| `pdf/valid_es.pdf` | 1 page, Spanish CV with all eight canonical section headings. |
| `pdf/valid_en.pdf` | 1 page, English CV with the English headings. |
| `pdf/ambiguous.pdf` | 1 page, no recognizable headings; one experience-like block without dates, plus unclassifiable stray text. |
| `pdf/multipage.pdf` | 3 pages of a continuous CV, used to exercise per-page iteration. |
| `pdf/empty_text.pdf` | 1 valid page whose content stream strokes a thick rule and draws no text. |
| `pdf/corrupt.pdf` | Starts with `%PDF-` but the `xref` table is truncated and the trailer is cut off. |
| `pdf/not_a_pdf.pdf` | Plain text with a `.pdf` extension; no `%PDF-` header at all. |
| `pdf/many_pages.pdf` | 21 pages, used to exercise the maximum-page limit. |
| `pdf_encrypted.pdf` | AES-256 encrypted PDF produced by `qpdf`. |

All people, companies, mailboxes and URLs inside the fixtures are fictional.
`example.com` is reserved by RFC 2606 and never resolves to a real inbox.

## Fixture contents

### `valid_es.pdf`

Headings: `DATOS PERSONALALES`, `PERFIL PROFESIONAL`, `EXPERIENCIA LABORAL`,
`EDUCACIÓN`, `APTITUDES TÉCNICAS`, `IDIOMAS`, `CERTIFICACIONES`, `PROYECTOS`.

Carries an email, a phone, a location, a LinkedIn URL, a GitHub URL, two work
entries with company / role / date range, one degree with institution and date
range, a skills list, three languages with levels, one certification with
issuer and year, and one project with description and stack.

It deliberately includes `á é í ó ú ñ ¿ ¡ €` so WinAnsi round-tripping is
exercised by every test that reads it.

### `valid_en.pdf`

Same shape in English. Headings: `CONTACT`, `PROFILE`, `WORK EXPERIENCE`,
`EDUCATION`, `SKILLS`, `LANGUAGES`, `CERTIFICATIONS`, `PROJECTS`.

### `ambiguous.pdf`

No heading is present. It contains one paragraph that reads like a job
description but carries no dates, and two stray sentences that belong to no
section at all. Used to assert the importer degrades gracefully instead of
inventing structure.

### `empty_text.pdf`

`pdfinfo` reports `Pages: 1` and `Encrypted: no`, but `pdftotext` returns only
the page separator byte `0x0C`. Tests should strip whitespace before asserting
the result is empty.

### `corrupt.pdf` and `not_a_pdf.pdf`

Both make `pdftotext` exit non-zero with `Couldn't read xref table` and emit no
text. They exercise the two distinct failure modes: a file that claims to be a
PDF but is damaged, and a file that never claimed to be a PDF at all.

### `pdf_encrypted.pdf`

AES-256 (PDF 1.7, revision 6) via `qpdf`. Verified behaviour:

```console
$ pdfinfo pdf_encrypted.pdf
Command Line Error: Incorrect password          # exit 1

$ pdfinfo -upw usuarioPropietario pdf_encrypted.pdf
Pages:           1
Encrypted:       yes (print:yes copy:yes change:yes addNotes:yes algorithm:AES-256)

$ pdftotext pdf_encrypted.pdf -
Command Line Error: Incorrect password          # exit 1
```

Passwords, both hardcoded in `generate.py`:

- user password: `usuarioPropietario`
- owner password: `propietario`

## Regenerating

All fixtures except `pdf_encrypted.pdf` come from the standard library alone:

```bash
python3 tests/fixtures/pdf_import/generate.py
```

The eight files in `pdf/` are byte-deterministic: the builder never embeds a
timestamp, a random ID or anything derived from the current time, so
re-running it reproduces identical hashes. `pdf_encrypted.pdf` is the single
exception, for the reason given below.

### `pdf_encrypted.pdf` requires `qpdf`

`generate.py` shells out to `qpdf` for this one file:

```bash
qpdf --encrypt usuarioPropietario propietario 256 -- in.pdf pdf_encrypted.pdf
```

`qpdf` encrypts with AES-256, so the result is a PDF 1.7 document.

**This file is not byte-reproducible.** AES-256 encryption in PDF revision 6
draws a random file key and random per-object salts and IVs on every run, so
two invocations of `qpdf` over identical input produce different bytes and a
different SHA-256. That is a property of the PDF encryption standard, not a bug
in this fixture: every run yields an equally valid, equally password-protected
document. Re-running `generate.py` therefore always churns this one file in
`git`, while the other eight stay identical. Commit the file as-is and let the
first generation define its hash.

When `qpdf` is missing the script prints
`SKIPPED: qpdf not available` and leaves the committed copy in place instead
of failing, so `generate.py` still succeeds on a host without poppler's
sibling tools.

## How the builder works

`build_text_pdf()` emits objects in ascending number order — catalog, pages,
font, info, then a `(page, contents)` pair per sheet — so the `xref` offsets
are simply the byte position of each `N 0 obj` header. Each content stream is
one `BT /F1 10 Tf 40 <y> Td (<line>) Tj ET` per line, with the baseline
descending 12 pt from `y = 760`.

Text is encoded as WinAnsiEncoding (CP1252), the encoding that covers the
Spanish characters used here. Bytes above 127 are written as octal escapes, so
the emitted file is pure 7-bit ASCII. Characters CP1252 cannot represent become
`?` rather than raising, which keeps the PDF structurally valid and mirrors
what the importer must tolerate.

`build_empty_pdf()` writes the same object graph but replaces the content stream
with a stroked rule, which keeps `pdfinfo` happy while yielding empty text.

## Verifying by hand

```bash
cd tests/fixtures/pdf_import
pdfinfo pdf/valid_es.pdf
pdftotext -layout pdf/valid_es.pdf -
pdftotext pdf/corrupt.pdf - ; echo $?     # 1
pdftotext pdf/empty_text.pdf - | wc -c   # 1, the page separator
pdftotext pdf_encrypted.pdf - ; echo $?  # 1, "Incorrect password"
```