"""Almacenamiento, herramientas de Dummy Data y migracion controlada.

Regla que gobierna todo el modulo: ninguna operacion toca el entorno REAL salvo
la lectura, y ninguna ruta de entorno acepta un entorno que no venga del prefijo.
Los paths se resuelven siempre dentro del directorio del entorno y se rechaza
cualquier cosa que se salga por `..` o por un enlace simbolico.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import os
import random
import re
import secrets
import shutil
import sqlite3
import string

from app.database import get_data_dir
from app.environments import (
    Environment,
    MIGRATION_MARKER_FILENAME,
    MIGRATING_MARKER_FILENAME,
    database_filename,
    legacy_migrated,
    legacy_storage_in_use,
    reset_environment,
    resolved_data_root,
    set_environment,
)
from app.services.export_service import EXPORTS_DIRECTORY_NAME
from app.services.import_staging_service import DRAFTS_DIRECTORY_NAME
from app.services.documentation_service import DOCUMENTATION_BUILD_SUBDIRECTORY

# Topes por operacion. No se truncan cantidades en silencio: si la persona pide
# mas, se rechaza con un mensaje que dice cual es el maximo.
MAX_GENERATE_PER_KIND = 50

SKILL_POOL = [
    "Python", "FastAPI", "SQL", "Docker", "Linux", "PostgreSQL", "Redis", "Git",
    "Pytest", "Kubernetes", "AWS", "Terraform", "JavaScript", "TypeScript",
    "Pandas", "Ansible", "Nginx", "Grafana", "MongoDB", "GraphQL", "Bash",
    "Go", "Rust", "Elixir", "Kafka", "RabbitMQ", "Celery", "gRPC", "Sentry",
]

CITY_POOL = [
    "Rosario", "Cordoba", "Mendoza", "La Plata", "Mar del Plata", "Bariloche",
    "Salta", "Tucuman", "Santa Fe", "Neuquen", "Posadas", "San Juan",
]

PROFESSION_POOL = [
    ("Desarrollador Backend", ["Python", "FastAPI", "PostgreSQL", "Docker"]),
    ("Ingeniero de Datos", ["Python", "Pandas", "SQL", "AWS"]),
    ("Administrador de Sistemas", ["Linux", "Ansible", "Docker", "Nginx"]),
    ("Desarrollador Frontend", ["JavaScript", "TypeScript", "React", "CSS"]),
    ("Analista de QA", ["Pytest", "Selenium", "Bash", "Git"]),
    ("Arquitecto de Software", ["Python", "Kubernetes", "Terraform", "AWS"]),
    ("Ingeniero DevOps", ["Docker", "Kubernetes", "Terraform", "Grafana"]),
    ("Especialista en Seguridad", ["Linux", "Bash", "AWS", "Sentry"]),
]

COMPANY_POOL = [
    "Acme", "Nova Sistemas", "Vertice", "Austral Tech", "Delta Labs",
    "Meridian", "Pampa Digital", "Cobalto", "Sirius", "Aurora",
    "Tramontana", "Eolo", "Zenith", "Equinox",
]

POSITION_POOL = [
    "Desarrollador Backend", "Ingeniero de Datos", "Analista de QA",
    "Administrador de Sistemas", "Desarrollador Frontend", "DevOps Engineer",
    "Soporte Tecnico", "Arquitecto de Software",
]

SOURCE_POOL = ["LinkedIn", "Computrabajo", "Referido", "Sitio web", "Email"]

STATUS_POOL = ["enviada", "en revision", "entrevista", "rechazada", "oferta"]

FIRST_NAME_POOL = [
    "Ana", "Luis", "Marta", "Diego", "Sofia", "Pablo", "Lucia", "Martin",
    "Elena", "Tomas", "Valentina", "Joaquin", "Camila", "Facundo", "Rocio",
    "Ignacio", "Julieta", "Bruno", "Florencia", "Agustin",
]

LAST_NAME_POOL = [
    "Perez", "Gomez", "Fernandez", "Lopez", "Martinez", "Sanchez", "Romero",
    "Sosa", "Torres", "Ramirez", "Flores", "Benítez", "Silva", "Molina",
    "Castro", "Ortiz", "Nuñez", "Rojas",
]


# --- Rutas por entorno -------------------------------------------------------


def environment_root(environment: Environment) -> Path:
    """Raiz del entorno, resuelta y comprobada.

    Se resuelve con `resolve()` y se exige que el resultado este dentro de la raiz
    de datos: un `import-drafts` que sea enlace a otro arbol queda fuera y se
    rechaza, en vez de seguirse en silencio.
    """

    root = resolved_data_root()
    target = root / environment.value
    resolved = target.resolve()
    base = root.resolve()
    if resolved != base and not resolved.is_relative_to(base):
        raise PermissionError(f"el entorno {environment.value} queda fuera de los datos")
    return target


def managed_directories(environment: Environment) -> dict[str, Path]:
    """Todo lo que la aplicacion administra dentro de un entorno."""

    root = environment_root(environment)
    return {
        "database": root / database_filename(),
        "exports": root / EXPORTS_DIRECTORY_NAME,
        "drafts": root / DRAFTS_DIRECTORY_NAME,
        "documentation": root / DOCUMENTATION_BUILD_SUBDIRECTORY,
    }


# Entornos cuya base ya fue inicializada en este proceso. Sin este cache cada
# peticion abriria una conexion solo para confirmar lo que ya se sabe.
_ready: set[Environment] = set()


@contextmanager
def in_environment(environment: Environment):
    """Fija el entorno por la duracion del bloque y despues lo restaura.

    Todas las operaciones mutantes se ejecutan dentro de esto, aunque el llamador
    ya tenga el entorno puesto por el middleware. La razon es que `get_data_dir()`
    lee el `ContextVar`, y si una funcion acepta un entorno explicito pero despues
    depende del ambiental, cualquier llamada hecha fuera de una peticion (una
    tarea en background, un script, un test unitario) escribiria en la base
    equivocada. Ese es exactamente el fallback silencioso que hay que impedir.
    """

    token = set_environment(environment)
    try:
        yield
    finally:
        reset_environment(token)


def ensure_environment_ready(environment: Environment) -> Path:
    """Garantiza que el almacenamiento del entorno existe y su base esta creada.

    El arranque de la aplicacion solo inicializa la base legacy, porque no puede
    saber de antemano en que entorno va a trabajar nadie. Sin esto, la primera
    peticion a `/test/` fallaria con `unable to open database file` antes de que
    existiera el directorio, y las siguientes fallarian por tablas ausentes.
    """

    root = environment_root(environment)
    root.mkdir(parents=True, exist_ok=True)
    for name in (EXPORTS_DIRECTORY_NAME, DRAFTS_DIRECTORY_NAME):
        (root / name).mkdir(parents=True, exist_ok=True)

    database = root / database_filename()
    if environment in _ready and database.exists():
        return database

    from app.database import initialize_database

    initialize_database()
    _ready.add(environment)
    return database


def _within(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    return resolved == root or resolved.is_relative_to(root)


def _safe_write(path: Path, root: Path) -> bool:
    """Borra un archivo sin seguir enlaces ni salirse del entorno."""

    try:
        if path.is_symlink() or not _within(path, root):
            return False
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=False)
        else:
            path.unlink(missing_ok=True)
        return True
    except OSError:
        # Un fallo de archivo no aborta la operacion: se reporta al final para que
        # nada se declare exitoso cuando quedo algo pendiente.
        return False


# --- Inventario --------------------------------------------------------------


@dataclass(frozen=True)
class Inventory:
    cvs: int
    cover_letters: int
    applications: int
    soft_deleted_cvs: int
    soft_deleted_cover_letters: int
    soft_deleted_applications: int
    exports: int
    drafts: int
    database_bytes: int

    @property
    def total(self) -> int:
        return self.cvs + self.cover_letters + self.applications


def inventory(environment: Environment) -> Inventory:
    paths = managed_directories(environment)
    database = paths["database"]

    counts = {"cvs": 0, "cover_letters": 0, "applications": 0}
    soft = {"cvs": 0, "cover_letters": 0, "applications": 0}
    if database.exists():
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            for table in counts:
                try:
                    counts[table] = connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                    soft[table] = connection.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE deleted_at IS NOT NULL"
                    ).fetchone()[0]
                except sqlite3.Error:
                    continue
        finally:
            connection.close()

    return Inventory(
        cvs=counts["cvs"],
        cover_letters=counts["cover_letters"],
        applications=counts["applications"],
        soft_deleted_cvs=soft["cvs"],
        soft_deleted_cover_letters=soft["cover_letters"],
        soft_deleted_applications=soft["applications"],
        exports=sum(1 for _ in paths["exports"].rglob("*")) if paths["exports"].exists() else 0,
        drafts=sum(1 for _ in paths["drafts"].glob("*.json")) if paths["drafts"].exists() else 0,
        database_bytes=database.stat().st_size if database.exists() else 0,
    )


# --- Generacion de Dummy Data ------------------------------------------------


class DummyDataError(Exception):
    def __init__(self, message: str, code: str = "dummy_invalid"):
        super().__init__(message)
        self.code = code
        self.user_message = message


def _name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAME_POOL)} {rng.choice(LAST_NAME_POOL)}"


def _email(name: str, rng: random.Random) -> str:
    first, _, last = name.lower().partition(" ")
    domain = rng.choice(["ejemplo.invalid", "pruebas.invalid", "demo.invalid"])
    return f"{first}.{last}@{domain}"


def _phone(rng: random.Random) -> str:
    return f"+54 9 {rng.randint(300, 399)} {rng.randint(100, 999)}-{rng.randint(1000, 9999)}"


def _dates(rng: random.Random) -> tuple[str, str]:
    start_year = rng.randint(2012, 2020)
    end_year = start_year + rng.randint(1, 6)
    start_month = rng.randint(1, 12)
    end_month = rng.randint(1, 12)
    return (
        f"{start_year}-{start_month:02d}",
        f"{end_year}-{end_month:02d}",
    )


def _structured_payload(name: str, rng: random.Random) -> dict:
    profession, preferred = rng.choice(PROFESSION_POOL)
    skills = rng.sample(SKILL_POOL, rng.randint(6, 10))
    if not set(preferred) <= set(skills):
        skills = preferred + rng.sample(
            [s for s in SKILL_POOL if s not in preferred], rng.randint(2, 4)
        )

    start, end = _dates(rng)
    education_start, education_end = _dates(rng)

    return {
        "schema_version": 2,
        "title": f"CV de {name} — {profession}",
        "personal": {
            "full_name": name,
            "headline": profession,
            "location": rng.choice(CITY_POOL),
        },
        "contact": {
            "email": _email(name, rng),
            "phone": _phone(rng),
            "links": ["https://ejemplo.invalid/portafolio"],
        },
        "summary": (
            f"{profession} con {rng.randint(3, 12)} años de experiencia en "
            f"{', '.join(preferred[:2])}. Enfoque en entregas medibles y codigo mantenible."
        ),
        "experience": [
            {
                "company": rng.choice(COMPANY_POOL),
                "position": profession,
                "start": education_start,
                "end": education_end,
                "description": (
                    f"Responsable de {rng.choice(preferred)} en un equipo de "
                    f"{rng.randint(2, 9)} personas."
                ),
                "technologies": rng.sample(preferred, min(len(preferred), rng.randint(2, 4))),
                "highlights": [
                    f"Reduje tiempos de despliegue un {rng.randint(10, 70)}%.",
                    f"Automatice {rng.randint(2, 20)} procesos manuales.",
                ],
            }
        ],
        "education": [
            {
                "institution": rng.choice(["Universidad Nacional", "Instituto Tecnico", "UTN"]),
                "title": rng.choice(["Ingenieria en Sistemas", "Analista de Sistemas", "Licenciatura"]),
                "start": education_start,
                "end": education_end,
            }
        ],
        "skills": [{"name": skill, "level": rng.choice(["basico", "intermedio", "avanzado"])} for skill in skills],
        "languages": [
            {"name": "Español", "level": "nativo"},
            {"name": "Ingles", "level": rng.choice(["basico", "intermedio", "avanzado"])},
        ],
        "certifications": (
            [{"name": f"Certificacion en {rng.choice(preferred)}", "issuer": rng.choice(COMPANY_POOL)}]
            if rng.random() < 0.5 else []
        ),
        "projects": (
            [{"name": f"Proyecto {rng.choice(['Atlas', 'Orion', 'Lince'])}",
              "description": f"Desarrollo con {', '.join(rng.sample(preferred, 2))}.",
              "technologies": rng.sample(preferred, min(len(preferred), 3))}]
            if rng.random() < 0.6 else []
        ),
    }


def _letter_body(rng: random.Random, company: str, position: str) -> str:
    return (
        f"Estimado equipo de {company}:\n\n"
        f"Me dirijo a ustedes para postularme al puesto de {position}. "
        f"A lo largo de mi trayectoria he trabajado con "
        f"{', '.join(rng.sample(SKILL_POOL, 3))}, y creo que ese perfil se ajusta "
        f"a lo que buscan.\n\n"
        f"Quedo a disposicion para ampliar cualquier informacion.\n\n"
        f"Saludos cordiales."
    )


@dataclass(frozen=True)
class GenerationResult:
    cvs: list[int]
    cover_letters: list[int]
    applications: list[int]


def generate_dummy_data(
    environment: Environment,
    *,
    cvs: int,
    cover_letters: int,
    applications: int,
    seed: int | None = None,
) -> GenerationResult:
    """Genera registros ficticios SOLO en el entorno pedido.

    El entorno se fija explicitamente alrededor de toda la operacion, asi que
    aunque el llamador este fuera de una peticion no puede escribir en la base
    equivocada.
    """

    with in_environment(environment):
        return _generate_dummy_data_impl(
            environment,
            cvs=cvs,
            cover_letters=cover_letters,
            applications=applications,
            seed=seed,
        )


def _generate_dummy_data_impl(
    environment: Environment,
    *,
    cvs: int,
    cover_letters: int,
    applications: int,
    seed: int | None = None,
) -> GenerationResult:
    if environment is Environment.REAL:
        raise DummyDataError(
            "Los datos de prueba solo se generan en el entorno de PRUEBAS.",
            code="dummy_real_forbidden",
        )

    for kind, count in (("curriculums", cvs), ("cartas", cover_letters), ("postulaciones", applications)):
        if not isinstance(count, int) or count < 0 or count > MAX_GENERATE_PER_KIND:
            raise DummyDataError(
                f"La cantidad de {kind} debe estar entre 0 y {MAX_GENERATE_PER_KIND}.",
                code="dummy_out_of_range",
            )

    rng = random.Random(seed if seed is not None else secrets.randbelow(2**31))
    from app.repositories import application_repository, cover_letter_repository, cv_repository
    from app.schemas import ApplicationFormData, CoverLetterFormData, CVFormData

    ensure_environment_ready(environment)

    cv_ids: list[int] = []
    for _ in range(cvs):
        name = _name(rng)
        payload = _structured_payload(name, rng)
        form = CVFormData(
            title=payload["title"],
            full_name=name,
            email=_email(name, rng),
            phone=_phone(rng),
            professional_summary=payload["summary"],
            experience_summary=payload["experience"][0]["description"],
            education_summary=f'{payload["education"][0]["title"]} — {payload["education"][0]["institution"]}',
            skills=", ".join(skill["name"] for skill in payload["skills"]),
        )
        cv_ids.append(
            cv_repository.create_structured_cv(
                title=payload["title"], payload=payload, metadata_source="dummy"
            )
        )

    letter_ids: list[int] = []
    for _ in range(cover_letters):
        name = _name(rng)
        company, position = rng.choice(COMPANY_POOL), rng.choice(POSITION_POOL)
        letter_ids.append(
            cover_letter_repository.create_cover_letter(
                CoverLetterFormData(
                    company=company,
                    position=position,
                    contact=_email(name, rng),
                    greeting=f"Estimado equipo de {company}:",
                    introduction=(
                        f"Me dirijo a ustedes para postularme al puesto de {position}."
                    ),
                    body=_letter_body(rng, company, position),
                    closing="Quedo a disposicion para ampliar cualquier informacion.",
                    signature=name,
                    associated_cv_id=(cv_ids[len(letter_ids) % len(cv_ids)] if cv_ids else None),
                )
            )
        )

    application_ids: list[int] = []
    for index in range(applications):
        company, position = rng.choice(COMPANY_POOL), rng.choice(POSITION_POOL)
        application_ids.append(
            application_repository.create_application(
                ApplicationFormData(
                    company=company,
                    position=position,
                    link="https://ejemplo.invalid/vacante",
                    source=rng.choice(SOURCE_POOL),
                    applied_on=str(date.today() - timedelta(days=rng.randint(0, 120))),
                    status=rng.choice(STATUS_POOL),
                    associated_cv_id=(cv_ids[index % len(cv_ids)] if cv_ids else None),
                    associated_cover_letter_id=(
                        letter_ids[index % len(letter_ids)] if letter_ids else None
                    ),
                    notes="Registro generado por el entorno de PRUEBAS.",
                    next_action="",
                    follow_up_date="",
                )
            )
        )

    return GenerationResult(cvs=cv_ids, cover_letters=letter_ids, applications=application_ids)


# --- Borrado selectivo y vaciado --------------------------------------------


def selected_records(environment: Environment, kind: str) -> list[dict]:
    """Registros vigentes de un tipo, para la pantalla de seleccion."""

    from app import database

    paths = managed_directories(environment)
    if not paths["database"].exists():
        return []

    connection = sqlite3.connect(f"file:{paths['database']}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        columns = {
            "cvs": "id, title, full_name",
            "cover_letters": "id, company, position",
            "applications": "id, company, position",
        }[kind]
        order = {"cvs": "title", "cover_letters": "company", "applications": "company"}[kind]
        rows = connection.execute(
            f"SELECT {columns} FROM {kind} WHERE deleted_at IS NULL ORDER BY {order} LIMIT 500"
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        connection.close()
    _ = database


def dependencies_of(environment: Environment, selection: dict[str, list[int]]) -> dict[str, dict]:
    """Dependencias de una seleccion, para mostrarlas antes de borrar.

    Un CV vinculado a postulaciones o cartas que NO estan en la seleccion se
    reporta como dependencia: no se borra en silencio y no se borra lo que no se
    pidio.
    """

    from app import database

    paths = managed_directories(environment)
    result: dict[str, dict] = {}
    if not paths["database"].exists():
        return result

    cv_ids = set(selection.get("cvs", []))
    letter_ids = set(selection.get("cover_letters", []))
    application_ids = set(selection.get("applications", []))

    connection = sqlite3.connect(f"file:{paths['database']}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if cv_ids:
            dependents = connection.execute(
                f"SELECT id, company, associated_cv_id FROM applications "
                f"WHERE associated_cv_id IN ({','.join('?' * len(cv_ids))}) "
                f"AND id NOT IN ({','.join('?' * len(application_ids)) or '0'})",
                (*cv_ids, *application_ids),
            ).fetchall()
            result["applications_kept"] = [dict(row) for row in dependents]

            # Cartas vinculadas a los CVs seleccionados que NO estan en la seleccion
            dependents = connection.execute(
                f"SELECT id, company, position, associated_cv_id FROM cover_letters "
                f"WHERE associated_cv_id IN ({','.join('?' * len(cv_ids))}) "
                f"AND id NOT IN ({','.join('?' * len(letter_ids)) or '0'})",
                (*cv_ids, *letter_ids),
            ).fetchall()
            result["cover_letters_kept_by_cv"] = [dict(row) for row in dependents]
        if letter_ids:
            dependents = connection.execute(
                f"SELECT id, company, associated_cover_letter_id FROM applications "
                f"WHERE associated_cover_letter_id IN ({','.join('?' * len(letter_ids))}) "
                f"AND id NOT IN ({','.join('?' * len(application_ids)) or '0'})",
                (*letter_ids, *application_ids),
            ).fetchall()
            result["applications_kept_by_letter"] = [dict(row) for row in dependents]
    except sqlite3.Error:
        pass
    finally:
        connection.close()
    return result


def _export_belongs_to(path: Path, prefix: str, record_id: int) -> bool:
    """True si ese archivo de exportacion pertenece a ese registro.

    Los nombres reales salen de `_build_entity_export_filename`, que compone
    `{prefijo}-{id}-{titulo}-{variante}-{timestamp}.{ext}`. Lo que identifica al
    registro es el segundo segmento del stem, y lo que lo sigue es un guion,
    nunca un punto: por eso `-{id}.` no matchea con ningun archivo que la propia
    app haya generado, y el borrado fisico dejaba los exports en disco mientras
    reportaba 0 archivos.
    """

    stem = path.stem
    head = f"{prefix}-{record_id}"
    if stem == head or stem.startswith(f"{head}-"):
        return True

    # Forma legada `cv-1.tex` / `cover-letter_3.json`. Se conserva porque un
    # archivo de una version anterior sigue siendo del registro, pero acotada al
    # mismo prefijo: el borrado de una carta no se tiene que llevar los archivos
    # de un CV que comparta el numero.
    if not stem.startswith(f"{prefix}-") and not stem.startswith(f"{prefix}_"):
        return False
    return f"-{record_id}." in path.name or f"_{record_id}." in path.name


def delete_selected(environment: Environment, selection: dict[str, list[int]]) -> dict:
    """Borrado FISICO de una seleccion, solo en el entorno pedido."""

    with in_environment(environment):
        return _delete_selected_impl(environment, selection)


def _delete_selected_impl(environment: Environment, selection: dict[str, list[int]]) -> dict:
    """Borrado FISICO de una seleccion, solo en el entorno pedido.

    Devuelve un reseño honesto: si quedo algun archivo sin borrar, `pending`
    queda con contenido y el resultado no se presenta como exito completo.
    """

    if environment is Environment.REAL:
        raise DummyDataError(
            "El borrado de datos de prueba no esta disponible en el entorno REAL.",
            code="delete_real_forbidden",
        )

    paths = managed_directories(environment)
    if not paths["database"].exists():
        raise DummyDataError(
            "El entorno de PRUEBAS no tiene datos todavia.", code="dummy_empty"
        )

    from app.repositories import application_repository, cover_letter_repository, cv_repository

    ensure_environment_ready(environment)

    result = {
        "cvs": 0,
        "cover_letters": 0,
        "applications": 0,
        "files": 0,
        "pending": [],
        # Registros que ya no estaban. No es un error y no va en `pending`:
        # meterlo ahi convertiria la operacion en "quedaron elementos sin
        # borrar" cuando en realidad no queda nada que reintentar.
        "missing": [],
    }
    # Las postulaciones primero: referencian a CVs y a cartas, asi que borrarlas
    # antes evita que una restriccion de clave externa deje la operacion a medias.
    tables = (
        ("applications", "applications", application_repository.hard_delete_application),
        ("cover_letters", "cover_letters", cover_letter_repository.hard_delete_cover_letter),
        ("cvs", "cvs", cv_repository.hard_delete_cv),
    )
    for table, kind, hard_delete in tables:
        for record_id in selection.get(kind, []):
            try:
                if hard_delete(record_id):
                    result[kind] += 1
                else:
                    result["missing"].append(f"{table}:{record_id}")
            except Exception as error:  # noqa: BLE001 - se reporta, no se aborta
                result["pending"].append(f"{table}:{record_id}: {error}")

    # Exportaciones asociadas a los registros borrados. El prefijo no es
    # decorativo: sin el, borrar una carta se llevaria puestos los archivos de
    # un CV que compartiera el numero.
    for prefix, key in (("cv", "cvs"), ("cover-letter", "cover_letters")):
        record_ids = selection.get(key, [])
        if not record_ids or not paths["exports"].exists():
            continue
        for path in paths["exports"].rglob("*"):
            if not path.is_file():
                continue
            if not any(
                _export_belongs_to(path, prefix, record_id) for record_id in record_ids
            ):
                continue
            if _safe_write(path, paths["exports"]):
                result["files"] += 1
            else:
                result["pending"].append(f"archivo: {path.name}")

    return result


def purge_environment(environment: Environment) -> dict:
    """Vacia por completo un entorno de pruebas, fisicamente."""

    with in_environment(environment):
        return _purge_environment_impl(environment)


def _purge_environment_impl(environment: Environment) -> dict:
    """No genera backup de lo eliminado: el requisito pide explicitamente que
    no se respalde lo que se decidio borrar."""

    if environment is Environment.REAL:
        raise DummyDataError(
            "No se puede vaciar el entorno REAL.", code="purge_real_forbidden"
        )

    from app.database import get_database_path

    paths = managed_directories(environment)
    result = {"files": 0, "pending": []}

    database_path = paths["database"]
    if database_path.exists():
        for suffix in ("", "-wal", "-shm", "-journal"):
            candidate = Path(str(database_path) + suffix)
            if candidate.exists() and _safe_write(candidate, environment_root(environment)):
                result["files"] += 1
            elif candidate.exists():
                result["pending"].append(candidate.name)

    for name in ("exports", "drafts", "documentation"):
        directory = paths[name]
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*"), reverse=True):
            if _safe_write(path, directory):
                result["files"] += 1
            else:
                result["pending"].append(path.name)
        _safe_write(directory, environment_root(environment))

    # Queda un entorno funcional y vacio, listo para generar de nuevo.
    get_database_path().parent.mkdir(parents=True, exist_ok=True)
    # La base desaparecio: la proxima peticion tiene que volver a crearla.
    _ready.discard(environment)
    return result


# --- Migracion controlada ----------------------------------------------------


@dataclass(frozen=True)
class MigrationPlan:
    status: str
    legacy_database: Path | None
    counts: dict[str, int]
    exports: int
    drafts: int
    problems: list[str]


def plan_migration() -> MigrationPlan:
    """Diagnostico de la instalacion. No modifica nada."""

    root = resolved_data_root()
    legacy = root / database_filename()
    problems: list[str] = []
    counts = {"cvs": 0, "cover_letters": 0, "applications": 0}

    if not legacy_storage_in_use(root):
        if legacy_migrated(root):
            # Distinto de "not_pending": despues de migrar la vista sin prefijo
            # quedo retirada, y decirle al usuario "no hay nada pendiente" deja
            # sin explicar por que las rutas historicas ya no responden.
            return MigrationPlan(
                "migrated",
                None,
                counts,
                0,
                0,
                [
                    "La base historica ya fue migrada y retirada del camino vivo. "
                    "Solo REAL y PRUEBAS son operativos."
                ],
            )
        problems.append("No hay base historica en la raiz de datos.")
        return MigrationPlan("not_pending", None, counts, 0, 0, problems)

    try:
        connection = sqlite3.connect(f"file:{legacy}?mode=ro", uri=True)
        try:
            for table in counts:
                try:
                    counts[table] = connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                except sqlite3.Error as error:
                    problems.append(f"{table}: {error}")
        finally:
            connection.close()
    except sqlite3.Error as error:
        return MigrationPlan("blocked", legacy, counts, 0, 0, [str(error)])

    for environment in (Environment.REAL, Environment.TEST):
        # `ensure_environment_ready` crea la base en la primera visita aunque
        # nadie haya escrito nada. Tratar esa creacion como "destino ocupado"
        # dejaria la migracion bloqueada para siempre: la pantalla no ofrece
        # ninguna accion para borrar una base vacia, y el entorno REAL no se
        # puede vaciar por diseno. Solo un destino CON contenido manda a
        # bloquear, base o no base: un directorio con archivos sueltos tambien
        # se pierde si la migracion lo pisa.
        summary = inventory(environment)
        if summary.total == 0 and summary.exports == 0 and summary.drafts == 0:
            continue
        problems.append(
            f"El destino {environment.value} ya tiene una base: la migracion "
            "no sobrescribe. Recuperala o eliminala a mano antes de continuar."
        )

    for label, path in (
        ("exports", root / EXPORTS_DIRECTORY_NAME),
        ("borradores", root / DRAFTS_DIRECTORY_NAME),
    ):
        if path.exists() and not path.is_dir():
            problems.append(f"{label}: existe pero no es un directorio.")

    status = "ready" if not problems else "blocked"
    return MigrationPlan(
        status=status,
        legacy_database=legacy,
        counts=counts,
        exports=sum(1 for _ in (root / EXPORTS_DIRECTORY_NAME).rglob("*"))
        if (root / EXPORTS_DIRECTORY_NAME).exists() else 0,
        drafts=sum(1 for _ in (root / DRAFTS_DIRECTORY_NAME).glob("*.json"))
        if (root / DRAFTS_DIRECTORY_NAME).exists() else 0,
        problems=problems,
    )


def validate_migration(plan: MigrationPlan, *, require_confirmation: str) -> None:
    """Confirmacion y diagnostico. No muta nada y no levanta el candado."""

    if require_confirmation != "MIGRAR":
        raise DummyDataError(
            "La confirmacion no coincide. Escribi exactamente MIGRAR.",
            code="migration_confirmation",
        )

    if plan.status != "ready":
        raise DummyDataError(
            "La migracion no esta en condiciones de ejecutarse: "
            + "; ".join(plan.problems),
            code="migration_blocked",
        )


@contextmanager
def migration_lock():
    """Candado de la ventana de escritura, levantado en los dos caminos.

    Mientras la base historica sigue en la raiz, las rutas sin prefijo siguen
    operando. El middleware lee este archivo y contesta 503 a toda peticion que
    toque datos, asi que por el camino de la app no se cuela una escritura entre
    el snapshot de SQLite y el renombre.

    El orden importa: el candado se levanta ANTES de drenar, nunca despues. Solo
    asi la espera de drenaje queda cerrada hacia afuera, porque las peticiones
    que entren mientras drena ya ven el archivo y se van con 503.
    """

    lock = resolved_data_root() / MIGRATING_MARKER_FILENAME
    try:
        lock.write_text(
            "Migracion de entornos en curso. Si este archivo queda atras por un "
            "corte abrupto, borrarlo rehabilita la vista sin prefijo.\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise DummyDataError(
            f"No se pudo marcar la migracion como en curso: {error}",
            code="migration_failed",
        ) from error

    try:
        yield
    finally:
        # En los dos caminos, exito y rollback: si quedara puesto, la app
        # quedaria respondiendo 503 para siempre y habria que borrarlo a mano.
        lock.unlink(missing_ok=True)


def run_migration(plan: MigrationPlan) -> dict:
    """Ejecuta un plan ya validado. El candado debe estar levantado."""

    with in_environment(Environment.TEST):
        return _execute_migration_impl(plan)


def execute_migration(*, require_confirmation: str) -> dict:
    """Migra la base historica al entorno PRUEBAS, verificable y recuperable.

    No se ejecuta en esta sesion: queda reservado hasta la autorizacion de Franco
    y nunca borra la base original.

    La ruta asincrona NO pasa por esta funcion. Ella levanta el candado, drena
    las peticiones que quedaron en vuelo con el candado puesto y recien ahi llama
    a `run_migration`; pasar por ahi dejaria el drenaje despues de abrir la
    ventana, que es exactamente el hueco que el candado viene a cerrar.
    """

    plan = plan_migration()
    validate_migration(plan, require_confirmation=require_confirmation)
    with migration_lock():
        return run_migration(plan)


def _execute_migration_impl(plan: MigrationPlan) -> dict:
    root = resolved_data_root()
    target_root = environment_root(Environment.TEST)
    target_root.mkdir(parents=True, exist_ok=True)

    # Checkpoint consistente con la API de backup de SQLite: no es una copia de
    # archivo, que podria tomar una base a mitad de una escritura.
    checkpoint = root / f"app.db.pre-migracion-{secrets.token_hex(6)}.bak"
    source = sqlite3.connect(f"file:{plan.legacy_database}?mode=ro", uri=True)
    destination = sqlite3.connect(checkpoint)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    # Cada entrada es un movimiento que hay que deshacer en orden inverso si algo
    # falla despues. Se anota ANTES de mover: si el propio `os.replace` falla a
    # medias, la entrada ya esta registrada y el rollback la intenta igual.
    moves: list[tuple[Path, Path]] = []

    def move(source_path: Path, target_path: Path) -> None:
        moves.append((source_path, target_path))
        os.replace(source_path, target_path)

    retired: Path | None = None
    try:
        move(checkpoint, target_root / database_filename())

        for label in (EXPORTS_DIRECTORY_NAME, DRAFTS_DIRECTORY_NAME):
            directory = root / label
            if directory.exists():
                move(directory, target_root / label)

        # Retiro de la vista historica. La base NO se borra: sale del camino vivo
        # con otro nombre, y el checkpoint de arriba sigue disponible aparte.
        # Sin esto quedarian tres bases vivas a la vez y las rutas sin prefijo
        # seguirian sirviendo datos historicos.
        retired = root / f"{database_filename()}.retirado-{secrets.token_hex(6)}"
        move(plan.legacy_database, retired)

        (root / MIGRATION_MARKER_FILENAME).write_text(
            "Marcado por la migracion de entornos. Borrar este archivo para "
            "rehabilitar la vista historica sin prefijo.\n",
            encoding="utf-8",
        )
    except OSError as error:
        # Rollback documentado: lo que ya se movio vuelve a su sitio, al reves.
        failed: list[str] = []
        for source_path, target_path in reversed(moves):
            try:
                os.replace(target_path, source_path)
            except OSError:
                failed.append(target_path.name)
        # La asercion del rollback va en el mensaje: si no se pudo deshacer
        # completo, decir "se revirtio" seria mentir.
        summary = (
            "La migracion fallo y se revirtio"
            if not failed
            else f"La migracion fallo y el rollback quedo incompleto en {failed}"
        )
        raise DummyDataError(
            f"{summary}: {error}", code="migration_failed"
        ) from error

    return {
        "counts": plan.counts,
        "moved": {
            "database": str(target_root / database_filename()),
            "exports": str(target_root / EXPORTS_DIRECTORY_NAME),
            "drafts": str(target_root / DRAFTS_DIRECTORY_NAME),
        },
        "retired": str(retired) if retired else None,
        "note": "La base historica quedo retirada del camino vivo y la vista sin "
                "prefijo dejo de estar operativa. El checkpoint conservado permite "
                "volver atras.",
    }
