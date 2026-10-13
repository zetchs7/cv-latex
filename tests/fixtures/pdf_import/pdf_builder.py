"""Minimal, dependency-free PDF builder used by the PDF import fixtures.

Only the Python standard library is used, so the test-suite never needs a
third-party PDF library. Every ``build_*`` helper returns deterministic
``bytes`` that poppler (``pdfinfo`` / ``pdftotext``) can read.

Design notes:

* Objects are emitted in ascending number order, which keeps the ``xref``
  table trivial to build and therefore always offset-correct.
* Text is encoded with WinAnsiEncoding (CP1252), the encoding that covers
  the Spanish characters used by the fixtures (``á é í ó ú ñ ¿ ¡`` plus the
  typographic punctuation of the standard 14 fonts).
* Bytes outside WinAnsi cannot be represented in a standard-font PDF, so
  they are replaced by ``?``.  The output stays a valid PDF instead of
  failing, which is the behaviour the import code must tolerate.
* All bytes above 127 are written as octal escapes so the emitted file is
  pure 7-bit ASCII and immune to encoding surprises downstream.
"""

from __future__ import annotations

from typing import List, Sequence

#: Version written in the PDF header.
PDF_VERSION = b"1.4"

#: Standard 14 fonts that need no embedded font program.
STANDARD_FONTS = (
    "Helvetica",
    "Helvetica-Bold",
    "Courier",
    "Courier-Bold",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Symbol",
    "ZapfDingbats",
)

#: A4 page in points.
PAGE_WIDTH = 595
PAGE_HEIGHT = 842

#: Text layout used by :func:`build_text_pdf`.
FONT_SIZE = 10
TEXT_ORIGIN_X = 40
TEXT_ORIGIN_Y = 760
LINE_STEP = 12

#: Lowest baseline still comfortably inside the bottom margin.
MIN_TEXT_Y = 56

#: Maximum number of lines that fit on a single page.
MAX_LINES_PER_PAGE = (TEXT_ORIGIN_Y - MIN_TEXT_Y) // LINE_STEP + 1

_ESCAPED = {0x28: "\\(", 0x29: "\\)", 0x5C: "\\\\"}


def to_winansi(text: str) -> bytes:
    """Return *text* encoded as WinAnsi (CP1252) bytes.

    Characters that CP1252 cannot represent become ``?`` so the resulting
    PDF always remains structurally valid.
    """
    return text.encode("cp1252", errors="replace")


def escape_pdf_string(text: str) -> str:
    """Escape *text* for use inside a PDF literal string ``(...)``."""
    out: List[str] = []
    for byte in to_winansi(text):
        replacement = _ESCAPED.get(byte)
        if replacement is not None:
            out.append(replacement)
        elif 32 <= byte < 127:
            out.append(chr(byte))
        elif byte < 32 or byte == 127:
            out.append(" ")
        else:
            out.append("\\%03o" % byte)
    return "".join(out)


def _normalize_font(font: str) -> str:
    if font not in STANDARD_FONTS:
        raise ValueError(
            "font %r is not one of the standard 14 fonts: %s"
            % (font, ", ".join(STANDARD_FONTS))
        )
    return font


def _paginate(blocks: Sequence[str], pages: int) -> List[List[str]]:
    """Split *blocks* into exactly *pages* groups, distributing evenly."""
    if pages < 1:
        raise ValueError("pages must be >= 1, got %r" % (pages,))
    total = len(blocks)
    base, remainder = divmod(total, pages)
    grouped: List[List[str]] = []
    start = 0
    for index in range(pages):
        size = base + (1 if index < remainder else 0)
        grouped.append(list(blocks[start : start + size]))
        start += size
    return grouped


def _content_stream(lines: Sequence[str]) -> bytes:
    """Build a content stream drawing *lines* top-down, one Tj per line."""
    operators: List[str] = []
    for offset, line in enumerate(lines):
        y = TEXT_ORIGIN_Y - offset * LINE_STEP
        operators.append(
            "BT /F1 %d Tf %d %d Td (%s) Tj ET"
            % (FONT_SIZE, TEXT_ORIGIN_X, y, escape_pdf_string(line))
        )
    return ("\n".join(operators) + "\n").encode("ascii")


def _blank_content_stream() -> bytes:
    """Content stream that strokes a thick horizontal rule and no text."""
    return (
        "%s w\n"
        "0 0 0 RG\n"
        "40 %d m\n"
        "%d %d l\n"
        "S\n" % (2, PAGE_HEIGHT // 2, PAGE_WIDTH - 40, PAGE_HEIGHT // 2)
    ).encode("ascii")


def _assemble(objects: Sequence[bytes], root: int, info: int) -> bytes:
    """Concatenate *objects* into a PDF file with a correct ``xref`` table.

    ``objects`` is indexed by object number minus one, so object ``n`` is
    stored as ``objects[n - 1]`` and must start with its ``n 0 obj`` header.
    """
    out = bytearray()
    out += b"%PDF-" + PDF_VERSION + b"\n"
    # Binary marker so tools treat the file as binary even on Windows.
    out += b"%\xe2\xe3\xcf\xd3\n"

    offsets: List[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number
        out += body
        if not body.endswith(b"\n"):
            out += b"\n"
        out += b"endobj\n"

    xref_offset = len(out)
    size = len(objects) + 1
    out += b"xref\n"
    out += b"0 %d\n" % size
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset

    out += b"trailer\n"
    out += b"<< /Size %d /Root %d 0 R /Info %d 0 R >>\n" % (size, root, info)
    out += b"startxref\n"
    out += b"%d\n" % xref_offset
    out += b"%%EOF\n"
    return bytes(out)


def _info_dict() -> bytes:
    return b"<< /Producer (cv-latex pdf_builder) >>"


def build_text_pdf(
    blocks: List[str],
    *,
    pages: int = 1,
    font: str = "Helvetica",
) -> bytes:
    """Return a valid single-document PDF containing *blocks*.

    Each block is rendered as one text line.  ``pages`` controls how the
    lines are distributed across sheets: the remainder is spread one line at
    a time over the first sheets, so the split stays balanced.
    """
    base_font = _normalize_font(font)
    grouped = _paginate(blocks, pages)
    for group in grouped:
        if len(group) > MAX_LINES_PER_PAGE:
            raise ValueError(
                "page would need %d lines but only %d fit; reduce the "
                "number of blocks or raise pages" % (len(group), MAX_LINES_PER_PAGE)
            )

    page_count = len(grouped)
    # Object layout: 1 catalog, 2 pages, 3 font, 4 info,
    # then (page, contents) pairs starting at 5.
    font_obj = 3
    info_obj = 4
    page_objs: List[int] = []
    contents_objs: List[int] = []
    next_number = 5
    for _ in range(page_count):
        page_objs.append(next_number)
        next_number += 1
        contents_objs.append(next_number)
        next_number += 1

    objects: List[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(b"%d 0 R" % number for number in page_objs)
        + b"] /Count %d >>" % page_count,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /"
        + base_font.encode("ascii")
        + b" /Encoding /WinAnsiEncoding >>",
        _info_dict(),
    ]

    resources = b"<< /Font << /F1 %d 0 R >> >>" % font_obj
    for index, group in enumerate(grouped):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources "
            % (PAGE_WIDTH, PAGE_HEIGHT)
            + resources
            + b" /Contents %d 0 R >>" % contents_objs[index]
        )
        stream = _content_stream(group)
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream"
        )

    return _assemble(objects, root=1, info=info_obj)


def build_empty_pdf(*, pages: int = 1, font: str = "Helvetica") -> bytes:
    """Return a valid PDF whose pages draw no text at all.

    Each page only strokes a thick horizontal rule, so ``pdftotext`` yields
    an empty document while ``pdfinfo`` still reports the correct page count.
    """
    _normalize_font(font)
    if pages < 1:
        raise ValueError("pages must be >= 1, got %r" % (pages,))

    page_objs: List[int] = []
    contents_objs: List[int] = []
    next_number = 5
    for _ in range(pages):
        page_objs.append(next_number)
        next_number += 1
        contents_objs.append(next_number)
        next_number += 1

    objects: List[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(b"%d 0 R" % number for number in page_objs)
        + b"] /Count %d >>" % pages,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>"
        % font.encode("ascii"),
        _info_dict(),
    ]

    resources = b"<< /Font << /F1 3 0 R >> >>"
    for index in range(pages):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources "
            % (PAGE_WIDTH, PAGE_HEIGHT)
            + resources
            + b" /Contents %d 0 R >>" % contents_objs[index]
        )
        stream = _blank_content_stream()
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream"
        )

    return _assemble(objects, root=1, info=4)


def build_corrupt_pdf(blocks: List[str]) -> bytes:
    """Return bytes that claim to be a PDF but carry a broken cross-reference.

    The header is intact so sniffing sees ``%PDF-``, but the ``xref`` table is
    truncated, every offset points at garbage, and the trailer is cut off
    before ``%%EOF``.
    """
    valid = build_text_pdf(blocks, pages=1)
    head = valid[: valid.index(b"xref")]
    return (
        head
        + b"xref\n"
        + b"0 99\n"
        + b"9999999999 65535 f \n"
        + b"truncated garbage offset table\n"
        + b"trailer\n"
        + b"<< /Size 99 /R"
    )