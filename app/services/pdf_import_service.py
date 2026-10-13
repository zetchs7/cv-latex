"""Validacion y extraccion de texto de un PDF subido por el usuario.

El PDF es **fuente de datos, nunca documento final**: este servicio solo lo lee,
lo acota y devuelve texto. No persiste el archivo original, no lo publica y no
manda nada a servicios externos.

Las herramientas son `pdfinfo` y `pdftotext` de poppler, que ya estan en la
imagen del proyecto (`Dockerfile` instala `poppler-utils`). No hay OCR: si el
PDF no tiene texto extraible, se informa con un mensaje claro y no se falla en
silencio.

Patron de invocacion calcado al de `pdf_service.py` y `documentation_service.py`:
lista de argumentos sin shell, timeout, `check=False` y temporal controlado.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ElementTree

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 20
PDF_EXTRACTION_TIMEOUT_SECONDS = 45
PDF_TEMP_PREFIX = "cv-pdf-import-"

PDF_MAGIC_PREFIX = b"%PDF-"
PDF_ENCRYPT_MARKER = b"/Encrypt"
MINIMUM_EXTRACTABLE_CHARACTERS = 120

_PDFINFO_KEYS = {"pages", "encrypted", "page_size"}


class PdfImportError(Exception):
    """Error de importacion de PDF con mensaje seguro para el usuario.

    `code` es estable y sirve para tests y registros. `user_message` esta
    escrito para mostrarse tal cual: nunca incluye rutas del servidor, nombres
    de archivo temporales ni detalle tecnico.
    """

    def __init__(self, code: str, user_message: str) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


class PdfUnclassifiableDocument(Exception):
    """Documento legible pero demasiado grande para clasificarlo sin perdida."""


@dataclass(frozen=True)
class ExtractedWord:
    """Una palabra con su pagina y su posicion vertical."""

    text: str
    page: int
    y: float


@dataclass(frozen=True)
class ExtractedPdf:
    """Resultado de leer un PDF. Nunca incluye el archivo original."""

    page_count: int
    text: str
    words: tuple[ExtractedWord, ...]
    used_word_coordinates: bool

    @property
    def has_extractable_text(self) -> bool:
        return len(self.text.strip()) >= MINIMUM_EXTRACTABLE_CHARACTERS


def read_limited_pdf_bytes(file_object, *, max_bytes: int = MAX_PDF_BYTES, chunk_size: int = 64 * 1024) -> bytes:
    """Lee el stream con tope, igual que hace `read_limited_upload_bytes` para JSON.

    El tope se aplica leyendo por bloques: un archivo gigante no llega a
    descargarse completo en memoria antes de decidir que es demasiado grande.
    """

    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = file_object.read(chunk_size)
        if not chunk:
            break

        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise PdfImportError(
                "pdf_too_large",
                f"El PDF supera el tamano maximo permitido de {max_bytes // (1024 * 1024)} MiB.",
            )

        chunks.append(chunk)

    return b"".join(chunks)


def validate_pdf_bytes(raw_content: bytes, *, max_bytes: int = MAX_PDF_BYTES, max_pages: int = MAX_PDF_PAGES) -> None:
    """Valida formato real, tamano y numero de paginas antes de extraer nada."""

    if not raw_content:
        raise PdfImportError("pdf_empty_file", "El archivo esta vacio. Volve a seleccionar el PDF.")

    if len(raw_content) > max_bytes:
        raise PdfImportError(
            "pdf_too_large",
            f"El PDF supera el tamano maximo permitido de {max_bytes // (1024 * 1024)} MiB.",
        )

    if not raw_content.lstrip()[:5].startswith(PDF_MAGIC_PREFIX):
        raise PdfImportError(
            "pdf_not_a_pdf",
            "El archivo no es un PDF valido. Verifica que tenga extension .pdf y que no este danado.",
        )

    # El cifrado se lee de los bytes y no del resultado de `pdfinfo`: poppler
    # sale con error ante un PDF cifrado, igual que ante uno corrupto, y esa
    # indistinguibilidad hacia que un PDF protegido se reportara como danado.
    if PDF_ENCRYPT_MARKER in raw_content:
        raise PdfImportError(
            "pdf_encrypted",
            "El PDF esta protegido con contrasena. Subi una copia sin contrasena.",
        )


def extract_pdf(raw_content: bytes, *, max_pages: int = MAX_PDF_PAGES) -> ExtractedPdf:
    """Valida y extrae el texto de un PDF.

    El archivo vive en un temporal que se borra al salir del `with`, exista o
    no error: el PDF original nunca queda en disco mas alla del procesamiento.
    """

    validate_pdf_bytes(raw_content, max_pages=max_pages)

    with tempfile.TemporaryDirectory(prefix=PDF_TEMP_PREFIX) as temporary_directory_name:
        pdf_path = Path(temporary_directory_name) / "cv.pdf"
        pdf_path.write_bytes(raw_content)
        try:
            os.chmod(pdf_path, 0o600)
        except OSError:
            pass

        page_count, is_encrypted = _read_pdfinfo(pdf_path, max_pages=max_pages)
        if is_encrypted:
            raise PdfImportError(
                "pdf_encrypted",
                "El PDF esta protegido con contrasena. Subi una copia sin contrasena.",
            )

        words, used_word_coordinates = _read_words(pdf_path)
        text = _read_plain_text(pdf_path)

        if not text.strip():
            raise PdfImportError(
                "pdf_without_text",
                "No se pudo extraer texto del PDF. Es posible que sea un escaneo o una imagen. "
                "Proba con un PDF que tenga texto seleccionable.",
            )

    return ExtractedPdf(
        page_count=page_count,
        text=text,
        words=words,
        used_word_coordinates=used_word_coordinates,
    )


def _run(command: list[str], *, stdin_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Ejecuta una herramienta PDF sin shell, con timeout y sin heredar la entrada."""

    try:
        return subprocess.run(
            command,
            stdin=None,
            capture_output=True,
            text=True,
            timeout=PDF_EXTRACTION_TIMEOUT_SECONDS,
            check=False,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"},
        )
    except FileNotFoundError as error:
        raise PdfImportError(
            "pdf_tool_missing",
            "El servidor no puede procesar PDF en este momento.",
        ) from error
    except subprocess.TimeoutExpired as error:
        raise PdfImportError(
            "pdf_timeout",
            "El PDF demoro demasiado en procesarse. Proba con uno mas chico o con menos paginas.",
        ) from error


def _read_pdfinfo(pdf_path: Path, *, max_pages: int) -> tuple[int, bool]:
    result = _run(["pdfinfo", str(pdf_path)])

    if result.returncode != 0:
        raise PdfImportError(
            "pdf_unreadable",
            "No se pudo leer el PDF. Verifica que el archivo no este danado.",
        )

    values = _parse_pdfinfo(result.stdout)
    page_count = values.get("pages", 0)

    if page_count <= 0:
        raise PdfImportError(
            "pdf_without_pages",
            "El PDF no tiene paginas legibles.",
        )

    if page_count > max_pages:
        raise PdfImportError(
            "pdf_too_many_pages",
            f"El PDF tiene {page_count} paginas y el maximo permitido es {max_pages}.",
        )

    return page_count, values.get("encrypted", False)


def _parse_pdfinfo(output: str) -> dict[str, object]:
    values: dict[str, object] = {}

    for line in output.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()

        if key == "pages":
            try:
                values["pages"] = int(value.strip())
            except ValueError:
                values["pages"] = 0
        elif key == "encrypted":
            values["encrypted"] = value.strip().lower() == "yes"
        elif key == "page size":
            values["page_size"] = value.strip()

    return values


def _read_plain_text(pdf_path: Path) -> str:
    """Texto con disposicion preservada: mantiene la alineacion por columnas."""

    result = _run(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"])

    if result.returncode != 0:
        raise PdfImportError(
            "pdf_unreadable",
            "No se pudo extraer el texto del PDF. Verifica que el archivo no este danado.",
        )

    return result.stdout


def _read_words(pdf_path: Path) -> tuple[tuple[ExtractedWord, ...], bool]:
    """Coordenadas por palabra, que es lo que permite reconstruir secciones.

    Si el XML no se puede leer, se degrada a texto plano sin coordenadas en
    lugar de fallar: la importacion sigue siendo posible, solo pierde la
    capacidad de distinguir columnas.
    """

    result = _run(["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(pdf_path), "-"])

    if result.returncode != 0 or not result.stdout.strip():
        return (), False

    try:
        root = ElementTree.fromstring(result.stdout)
    except ElementTree.ParseError:
        return (), False

    words: list[ExtractedWord] = []
    # El XML de poppler no numera los <page>: el numero es el orden en el
    # documento. Leer un atributo inexistente devolvia 1 para todas las paginas
    # y hacia creer que el documento tenia una sola.
    for page_number, page_element in enumerate(_elements_named(root, "page"), start=1):
        for word_element in _elements_named(page_element, "word"):
            text = (word_element.text or "").strip()
            if not text:
                continue
            words.append(
                ExtractedWord(
                    text=text,
                    page=page_number,
                    y=_word_coordinate(word_element),
                )
            )

    return tuple(words), True


def _elements_named(element: ElementTree.Element, name: str):
    """Itera los descendientes con ese nombre, ignorando el namespace XHTML."""

    for descendant in element.iter():
        if descendant.tag.rsplit("}", 1)[-1] == name:
            yield descendant


def _word_coordinate(word_element: ElementTree.Element) -> float:
    raw = word_element.attrib.get("yMin", "0")
    try:
        return float(raw)
    except ValueError:
        return 0.0