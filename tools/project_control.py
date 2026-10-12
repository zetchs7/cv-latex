#!/usr/bin/env python3
"""Project Control Center de cv-latex.

Catalogo canonico:  docs/development/project_control/catalog.json
Documentos derivados: docs/development/PROJECT_STATUS.md
                       docs/development/BACKLOG.md
                       docs/development/ROADMAP.md

La aplicacion web no importa este modulo. Vive en ``tools/`` y solo se ejecuta
desde la linea de comandos. Ver ``docs/adr/ADR-0005-project-control-center.md``.

Uso:
    python3 tools/project_control.py validate
    python3 tools/project_control.py status
    python3 tools/project_control.py render   [--only BACKLOG|ROADMAP|PROJECT_STATUS]
    python3 tools/project_control.py check     [--only BACKLOG|ROADMAP|PROJECT_STATUS]

``validate``, ``status`` y ``check`` son de solo lectura. ``render`` es el unico
verbo que escribe archivos.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPOSITORY_ROOT / "docs" / "development" / "project_control" / "catalog.json"
DOCUMENTS_DIRECTORY = REPOSITORY_ROOT / "docs" / "development"

SUPPORTED_SCHEMA_VERSIONS = {1}

PRIORITIES = ("P0", "P1", "P2", "P3")
TASK_STATUSES = ("backlog", "ready", "in_progress", "blocked", "done", "cancelled")
ORIGINS = ("franco", "defect", "engineering", "debt")
MODULE_STATES = ("planned", "in_development", "in_development_branch", "in_main")
RISK_SEVERITIES = ("low", "medium", "high")
RISK_STATUSES = ("open", "mitigated", "accepted", "closed")

GENERATED_DOCUMENTS = {
    "PROJECT_STATUS": "PROJECT_STATUS.md",
    "BACKLOG": "BACKLOG.md",
    "ROADMAP": "ROADMAP.md",
}

GENERATED_NOTICE = (
    "<!-- Generado por tools/project_control.py desde "
    "docs/development/project_control/catalog.json. No editar a mano: editar el "
    "catalogo y ejecutar `python3 tools/project_control.py render`. -->"
)

ROADMAP_SECTIONS = (
    ("done", "1. Trabajo completado"),
    ("in_progress", "2. Trabajo en curso"),
    ("ready", "3. Trabajo listo para iniciar"),
    ("backlog", "4. Trabajo pendiente acordado"),
    ("blocked", "5. Trabajo bloqueado"),
    ("cancelled", "6. Trabajo cancelado"),
)


class Problem:
    """Un problema encontrado al validar el catalogo."""

    def __init__(self, level: str, location: str, message: str) -> None:
        self.level = level
        self.location = location
        self.message = message

    def render(self) -> str:
        return f"  [{self.level.upper():7}] {self.location}: {self.message}"


class CatalogError(Exception):
    """El catalogo no se pudo leer o no es un objeto JSON valido."""


def load_catalog(path: Path | None = None) -> dict:
    """Lee el catalogo. `path` se resuelve en tiempo de llamada, no al importar:

    un valor por defecto ligado al modulo congelaria la ruta y la haria
    insustituible en tests y en cualquier reutilizacion.
    """

    path = CATALOG_PATH if path is None else path
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise CatalogError(f"no existe el catalogo: {path}") from error
    except OSError as error:
        raise CatalogError(f"no se pudo leer {path}: {error}") from error

    try:
        catalog = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CatalogError(f"JSON invalido en {path}:{error.lineno}:{error.colno}: {error.msg}") from error

    if not isinstance(catalog, dict):
        raise CatalogError(f"el catalogo debe ser un objeto JSON, no {type(catalog).__name__}")

    return catalog


def _require_text(container: dict, key: str, location: str, problems: list[Problem]) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        problems.append(Problem("error", f"{location}.{key}", "debe ser texto no vacio"))
        return ""
    return value.strip()


def _require_choice(container: dict, key: str, allowed: tuple[str, ...], location: str, problems: list[Problem]) -> str:
    value = _require_text(container, key, location, problems)
    if value and value not in allowed:
        problems.append(
            Problem("error", f"{location}.{key}", f"valor '{value}' fuera de {list(allowed)}")
        )
    return value


def _require_list(container: dict, key: str, location: str, problems: list[Problem]) -> list:
    value = container.get(key)
    if not isinstance(value, list):
        problems.append(Problem("error", f"{location}.{key}", "debe ser una lista"))
        return []
    return value


def _iterable_or_empty(value: object) -> list:
    """Itera solo si el valor es iterable. Un `depends_on: 7` no debe romper."""

    if isinstance(value, list):
        return value
    if isinstance(value, str) or value is None:
        return []
    try:
        return list(value)  # type: ignore[call-overload]
    except TypeError:
        return []


def _detect_cycles(tasks: list[dict], problems: list[Problem]) -> None:
    graph = {
        task.get("id"): [dep for dep in _iterable_or_empty(task.get("depends_on")) if isinstance(dep, str)]
        for task in tasks
        if isinstance(task, dict)
    }

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for neighbour in graph.get(node, []):
            if neighbour not in graph:
                continue
            if state.get(neighbour) == 1:
                cycle = " -> ".join(stack[stack.index(neighbour):] + [neighbour])
                problems.append(Problem("error", f"tasks[{node}]", f"ciclo de dependencias: {cycle}"))
            elif neighbour not in state:
                visit(neighbour)
        stack.pop()
        state[node] = 2

    for node in graph:
        if node not in state:
            visit(node)


def validate_catalog(catalog: dict) -> list[Problem]:
    problems: list[Problem] = []

    meta = catalog.get("meta")
    if not isinstance(meta, dict):
        problems.append(Problem("error", "meta", "debe ser un objeto"))
    else:
        schema_version = meta.get("schema_version")
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            problems.append(
                Problem(
                    "error",
                    "meta.schema_version",
                    f"version {schema_version!r} no soportada; se admiten {sorted(SUPPORTED_SCHEMA_VERSIONS)}",
                )
            )

    project = catalog.get("project")
    if not isinstance(project, dict):
        problems.append(Problem("error", "project", "debe ser un objeto"))
    else:
        for key in (
            "name",
            "stable_version",
            "main_branch",
            "development_branch",
            "last_verified_on",
            "last_verification_evidence",
        ):
            _require_text(project, key, "project", problems)
        for key in ("mvp_criteria", "expanded_vision", "release_policy"):
            values = _require_list(project, key, "project", problems)
            if not values:
                problems.append(
                    Problem("error", f"project.{key}", "no puede ser una lista vacia")
                )

    modules = _require_list(catalog, "modules", "catalog", problems)
    module_ids: set[str] = set()
    for index, module in enumerate(modules):
        location = f"modules[{index}]"
        if not isinstance(module, dict):
            problems.append(Problem("error", location, "debe ser un objeto"))
            continue
        module_id = _require_text(module, "id", location, problems)
        if module_id:
            if module_id in module_ids:
                problems.append(Problem("error", f"{location}.id", f"id duplicado '{module_id}'"))
            module_ids.add(module_id)
        _require_text(module, "name", location, problems)
        _require_choice(module, "state", MODULE_STATES, location, problems)
        for flag in ("in_development", "in_main"):
            if not isinstance(module.get(flag), bool):
                problems.append(Problem("error", f"{location}.{flag}", "debe ser booleano"))
        evidence = _require_text(module, "evidence", location, problems)
        if not evidence:
            problems.append(Problem("error", f"{location}.evidence", "un modulo sin evidencia no es verificable"))
        if module.get("in_main") and module.get("state") == "in_development":
            problems.append(
                Problem("error", f"{location}.state", "in_main=true contradice state='in_development'")
            )

    risks = _require_list(catalog, "risks", "catalog", problems)
    risk_ids: set[str] = set()
    for index, risk in enumerate(risks):
        location = f"risks[{index}]"
        if not isinstance(risk, dict):
            problems.append(Problem("error", location, "debe ser un objeto"))
            continue
        risk_id = _require_text(risk, "id", location, problems)
        if risk_id:
            if risk_id in risk_ids:
                problems.append(Problem("error", f"{location}.id", f"id duplicado '{risk_id}'"))
            risk_ids.add(risk_id)
        _require_text(risk, "title", location, problems)
        _require_choice(risk, "severity", RISK_SEVERITIES, location, problems)
        _require_choice(risk, "status", RISK_STATUSES, location, problems)
        _require_text(risk, "mitigation", location, problems)
        _require_text(risk, "evidence", location, problems)

    tasks = _require_list(catalog, "tasks", "catalog", problems)

    # Se calcula antes del bucle porque la comprobacion de dependencias
    # canceladas lo consulta por cada tarea.
    cancelled_ids = {
        task.get("id")
        for task in tasks
        if isinstance(task, dict) and task.get("status") == "cancelled" and isinstance(task.get("id"), str)
    }

    task_ids: set[str] = set()
    for index, task in enumerate(tasks):
        location = f"tasks[{index}]"
        if not isinstance(task, dict):
            problems.append(Problem("error", location, "debe ser un objeto"))
            continue
        task_id = _require_text(task, "id", location, problems)
        if task_id:
            if task_id in task_ids:
                problems.append(Problem("error", f"{location}.id", f"id duplicado '{task_id}'"))
            task_ids.add(task_id)
        _require_text(task, "title", location, problems)
        _require_text(task, "description", location, problems)
        _require_choice(task, "origin", ORIGINS, location, problems)
        _require_choice(task, "priority", PRIORITIES, location, problems)
        status = _require_choice(task, "status", TASK_STATUSES, location, problems)
        _require_text(task, "module", location, problems)
        _require_text(task, "next_action", location, problems)
        _require_text(task, "evidence", location, problems)

        if not isinstance(task.get("approved"), bool):
            problems.append(
                Problem("error", f"{location}.approved", "debe ser booleano: distingue requisito de propuesta")
            )
        elif task.get("approved") and task.get("origin") != "franco":
            # La garantia de que una recomendacion de ingenieria nunca se
            # presenta como un pedido depende de esto: sin el cruce, un
            # `approved: true` mal puesto legitima cualquier sugerencia.
            problems.append(
                Problem(
                    "error",
                    f"{location}.approved",
                    f"solo una tarea de origen 'franco' puede estar aprobada; esta es '{task.get('origin')}'",
                )
            )

        acceptance = _require_list(task, "acceptance", location, problems)
        if not acceptance:
            problems.append(
                Problem("error", f"{location}.acceptance", "una tarea sin criterio de aceptacion no es una tarea")
            )
        else:
            for position, criterion in enumerate(acceptance):
                if not isinstance(criterion, str) or not criterion.strip():
                    problems.append(
                        Problem("error", f"{location}.acceptance[{position}]", "debe ser texto no vacio")
                    )

        depends_on = _require_list(task, "depends_on", location, problems)
        for position, dependency in enumerate(_iterable_or_empty(task.get("depends_on"))):
            if not isinstance(dependency, str) or not dependency.strip():
                problems.append(
                    Problem("error", f"{location}.depends_on[{position}]", "debe ser un id de tarea")
                )
            elif dependency == task_id:
                problems.append(Problem("error", f"{location}.depends_on", "una tarea no puede depender de si misma"))
            elif dependency in cancelled_ids:
                # Esperar algo que se descarto deja la tarea bloqueada para
                # siempre, sin que nada lo diga.
                problems.append(
                    Problem("error", f"{location}.depends_on", f"depende de '{dependency}', que esta cancelada")
                )

        github_issue = task.get("github_issue")
        # `isinstance(True, int)` es True en Python: un booleano pasaria como
        # numero de issue y colisionaria con el issue 1. Se rechaza en vez de
        # normalizarlo a null, porque aceptarlo en silencio seria peor.
        if isinstance(github_issue, bool):
            problems.append(
                Problem("error", f"{location}.github_issue", "debe ser null o un numero de issue, no un booleano")
            )
        elif github_issue is not None and (not isinstance(github_issue, int) or github_issue <= 0):
            problems.append(Problem("error", f"{location}.github_issue", "debe ser null o un numero de issue positivo"))

        if status == "done" and not acceptance:
            problems.append(Problem("error", f"{location}.status", "tarea cerrada sin criterios de aceptacion"))

    known_task_ids = {
        task.get("id") for task in tasks if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        for position, dependency in enumerate(_iterable_or_empty(task.get("depends_on"))):
            if isinstance(dependency, str) and dependency.strip() and dependency not in known_task_ids:
                problems.append(
                    Problem("error", f"tasks[{index}].depends_on[{position}]", f"dependencia inexistente '{dependency}'")
                )

    _detect_cycles(tasks, problems)

    seen_issues: dict[int, str] = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        issue = task.get("github_issue")
        task_id = task.get("id")
        if isinstance(issue, int) and not isinstance(issue, bool) and isinstance(task_id, str):
            if issue in seen_issues:
                problems.append(
                    Problem(
                        "error",
                        f"tasks[{index}].github_issue",
                        f"el issue #{issue} ya esta registrado por '{seen_issues[issue]}'",
                    )
                )
            seen_issues[issue] = task_id

    return problems


def _sorted(items: list[dict], key: str = "id") -> list[dict]:
    return sorted(items, key=lambda item: str(item.get(key, "")))


def _escape_cell(value: object) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _render_table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> list[str]:
    if not rows:
        return ["_Sin entradas._", ""]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape_cell(cell) for cell in row) + " |")
    lines.append("")
    return lines


def _escape_block_text(text: object) -> str:
    """Convierte texto multilinea en algo que no rompe el Markdown.

    Una descripcion o un criterio de aceptacion con un salto de linea se
    insertaba crudo y partia el parrafo o inyectaba marcado.
    """

    collapsed = " ".join(str(text or "").split())
    return collapsed


def _origin_label(origin: str) -> str:
    return {
        "franco": "Solicitud de Franco",
        "defect": "Defecto verificado",
        "engineering": "Recomendacion de ingenieria",
        "debt": "Deuda documentada",
    }.get(origin, origin)


def render_project_status(catalog: dict) -> str:
    project = catalog.get("project", {})
    modules = _sorted(catalog.get("modules", []))
    risks = _sorted(catalog.get("risks", []))
    tasks = catalog.get("tasks", [])

    open_risks = [risk for risk in risks if risk.get("status") == "open"]
    by_priority = {priority: 0 for priority in PRIORITIES}
    by_status: dict[str, int] = {}
    for task in tasks:
        if isinstance(task, dict):
            priority = task.get("priority")
            if priority in by_priority:
                by_priority[priority] += 1
            status = task.get("status")
            if isinstance(status, str):
                by_status[status] = by_status.get(status, 0) + 1

    next_ready = sorted(
        (task for task in tasks if isinstance(task, dict) and task.get("status") == "ready"),
        key=lambda task: (str(task.get("priority")), str(task.get("id"))),
    )

    lines = [
        "# Project Status",
        "",
        GENERATED_NOTICE,
        "",
        "## Identificacion del proyecto",
        "",
    ]
    lines += _render_table(
        ("Campo", "Valor"),
        [
            ("Proyecto", project.get("name")),
            ("Version estable", project.get("stable_version")),
            ("Rama estable", project.get("main_branch")),
            ("Rama de integracion", project.get("development_branch")),
            ("Ultima verificacion", project.get("last_verified_on")),
            ("Evidencia de la verificacion", project.get("last_verification_evidence")),
        ],
    )

    lines += ["## Ramas: que hay en cada una", "", _RAMA_NOTE, ""]
    lines += _render_table(
        ("Rama", "Significado", "Estado"),
        [
            (
                project.get("main_branch"),
                "Estable publicada. Es la unica que ve un usuario final.",
                "Release publicada, no toca `main` sin autorizacion explicita.",
            ),
            (
                project.get("development_branch"),
                "Integracion validada. Aqui llega lo aprobado.",
                "Integracion abierta.",
            ),
            (
                "feature/*",
                "Implementacion o correccion acotada en curso.",
                "Se integra por squash merge hacia `development`.",
            ),
        ],
    )

    lines += ["## Modulos", ""]
    lines += _render_table(
        ("Modulo", "Rutas", "Estado", "En development", "En main", "Evidencia"),
        [
            (
                module.get("name"),
                module.get("routes", ""),
                module.get("state"),
                "si" if module.get("in_development") else "no",
                "si" if module.get("in_main") else "no",
                module.get("evidence"),
            )
            for module in modules
        ],
    )

    lines += ["## Riesgos abiertos", ""]
    if open_risks:
        lines += _render_table(
            ("ID", "Riesgo", "Severidad", "Mitigacion", "Evidencia"),
            [
                (risk.get("id"), risk.get("title"), risk.get("severity"), risk.get("mitigation"), risk.get("evidence"))
                for risk in open_risks
            ],
        )
    else:
        lines += ["_Sin riesgos abiertos._", ""]

    lines += ["## Backlog en un vistazo", ""]
    lines += _render_table(("Prioridad", "Tareas"), [(priority, count) for priority, count in by_priority.items()])
    status_rows = [(status, by_status.get(status, 0)) for status in TASK_STATUSES]
    lines += _render_table(("Estado", "Tareas"), status_rows)

    lines += ["## Proxima tarea concreta", ""]
    if next_ready:
        for task in next_ready:
            lines.append(f"- **{task.get('id')}** ({task.get('priority')}) {task.get('title')}")
            lines.append(f"  - Siguiente paso: {task.get('next_action')}")
    else:
        lines.append("_No hay tareas en estado `ready`. Revisar `BACKLOG.md`._")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


_RAMA_NOTE = (
    "`main`, `development` y las ramas `feature/*` son hechos distintos. Confundirlos "
    "es la fuente de error mas frecuente de este repositorio, por eso la tabla los "
    "separa en lugar de resumirlos en un unico numero de avance."
)


def render_backlog(catalog: dict) -> str:
    tasks = _sorted(catalog.get("tasks", []))
    pending = [task for task in tasks if task.get("status") not in ("done", "cancelled")]

    lines = [
        "# Backlog",
        "",
        GENERATED_NOTICE,
        "",
        "## Como leer este backlog",
        "",
        "- **Origen** distingue de donde sale la tarea: `Solicitud de Franco`, `Defecto verificado`,",
        "  `Recomendacion de ingenieria` o `Deuda documentada`. Una recomendacion de ingenieria",
        "  **no** es un requisito aprobado.",
        "- **Aprobado** indica si Franco aprobo la tarea. `no` significa propuesta.",
        "- **Estado** `done` significa cerrada; `cancelled` significa descartada con motivo.",
        "",
        "## Tareas abiertas",
        "",
    ]
    for task in pending:
        lines += _render_task(task)

    lines += ["## Tareas cerradas", "", "### Cerradas", ""]
    closed = [task for task in tasks if task.get("status") == "done"]
    if closed:
        for task in closed:
            lines += _render_task(task, compact=True)
    else:
        lines += ["_Sin tareas cerradas registradas en el catalogo._", ""]

    cancelled = [task for task in tasks if task.get("status") == "cancelled"]
    if cancelled:
        lines += ["### Descartadas", ""]
        for task in cancelled:
            lines += _render_task(task, compact=True)

    return "\n".join(lines).rstrip() + "\n"


def _render_task(task: dict, compact: bool = False) -> list[str]:
    lines = [
        f"### {task.get('id')} — {task.get('title')}",
        "",
    ]
    lines += _render_table(
        ("Campo", "Valor"),
        [
            ("Prioridad", task.get("priority")),
            ("Estado", task.get("status")),
            ("Origen", _origin_label(str(task.get("origin")))),
            ("Aprobado por Franco", "si" if task.get("approved") else "no"),
            ("Modulo", task.get("module")),
            ("Issue de GitHub", f"#{task['github_issue']}" if task.get("github_issue") else "—"),
            ("Depende de", ", ".join(task.get("depends_on") or []) or "—"),
            ("Evidencia", task.get("evidence")),
            ("Proxima accion", task.get("next_action")),
        ],
    )
    lines += [_escape_block_text(task.get("description")), "", "**Criterios de aceptacion**", ""]
    for criterion in task.get("acceptance") or []:
        lines.append(f"- [ ] {_escape_block_text(criterion)}")
    lines.append("")
    if compact:
        lines = [line for line in lines if line]
    return lines


def render_roadmap(catalog: dict) -> str:
    tasks = _sorted(catalog.get("tasks", []))
    project = catalog.get("project", {})

    lines = [
        "# Roadmap",
        "",
        GENERATED_NOTICE,
        "",
        "Ordenado por estado y por dependencia, no por fecha. **Este documento no asigna fechas:**",
        "ninguna fecha del roadmap tiene evidencia que la respalde.",
        "",
        "## Como se lee",
        "",
        "El roadmap se construye desde el catalogo. Una tarea aparece en la seccion que",
        "corresponde a su estado, y el orden dentro de cada seccion es por prioridad y luego",
        "por dependencia. Para reconstruir el camino critico, mirar `depends_on` en `BACKLOG.md`.",
        "",
    ]

    by_status: dict[str, list[dict]] = {}
    for task in tasks:
        by_status.setdefault(str(task.get("status")), []).append(task)

    for status, title in ROADMAP_SECTIONS:
        section = by_status.get(status, [])
        lines += [f"## {title}", ""]
        if not section:
            lines += ["_Vacio._", ""]
            continue
        for task in sorted(section, key=lambda item: (str(item.get("priority")), str(item.get("id")))):
            blockers = task.get("depends_on") or []
            blocker_text = (
                "espera: " + ", ".join(blockers) if blockers else "sin dependencias"
            )
            flag = "" if task.get("approved") else " _(propuesta, no aprobada)_"
            lines.append(f"- **{task.get('id')}** [{task.get('priority')}] {task.get('title')}{flag} — {blocker_text}")
        lines.append("")

    lines += ["## Criterio de cierre del MVP", ""]
    lines += _numbered(project.get("mvp_criteria"))
    lines += ["## Vision ampliada (fuera del MVP)", ""]
    lines += _numbered(project.get("expanded_vision"))
    lines += [
        "## Release y mantenimiento",
        "",
        f"- Version estable actual: **{project.get('stable_version')}**.",
    ]
    lines += [f"- {rule}" for rule in project.get("release_policy") or []]
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _numbered(items: list) -> list[str]:
    if not items:
        return ["_Sin definir._", ""]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)] + [""]


RENDERERS = {
    "PROJECT_STATUS": render_project_status,
    "BACKLOG": render_backlog,
    "ROADMAP": render_roadmap,
}


def _selected_documents(only: str | None) -> list[str]:
    if only is None:
        return list(GENERATED_DOCUMENTS)
    if only not in GENERATED_DOCUMENTS:
        raise CatalogError(f"documento desconocido: {only}; opciones {sorted(GENERATED_DOCUMENTS)}")
    return [only]


def _render_all(catalog: dict, only: str | None) -> dict[str, str]:
    rendered = {}
    for name in _selected_documents(only):
        content = RENDERERS[name](catalog)
        rendered[GENERATED_DOCUMENTS[name]] = content if content.endswith("\n") else content + "\n"
    return rendered


def command_validate(_: argparse.Namespace) -> int:
    try:
        catalog = load_catalog()
    except CatalogError as error:
        print(f"project_control: {error}")
        return 1

    problems = validate_catalog(catalog)
    errors = [problem for problem in problems if problem.level == "error"]
    warnings = [problem for problem in problems if problem.level == "warning"]

    for problem in problems:
        print(problem.render())

    if not problems:
        print("catalogo valido: sin errores ni advertencias")
        return 0

    print(f"\n{len(errors)} error(es), {len(warnings)} advertencia(s)")
    return 1 if errors else 0


def command_status(_: argparse.Namespace) -> int:
    try:
        catalog = load_catalog()
    except CatalogError as error:
        print(f"project_control: {error}")
        return 1

    project = catalog.get("project", {})
    tasks = [task for task in catalog.get("tasks", []) if isinstance(task, dict)]

    print(f"Proyecto           : {project.get('name')}")
    print(f"Version estable    : {project.get('stable_version')}")
    print(f"Ultima verificacion: {project.get('last_verified_on')}")
    print()

    counts: dict[str, int] = {}
    for task in tasks:
        counts[str(task.get("status"))] = counts.get(str(task.get("status")), 0) + 1
    print("Tareas por estado:")
    for status in TASK_STATUSES:
        print(f"  {status:<12}: {counts.get(status, 0)}")
    print()

    approved = sum(1 for task in tasks if task.get("approved"))
    print(f"Aprobadas por Franco: {approved} | propuestas: {len(tasks) - approved}")

    ready = sorted(
        (task for task in tasks if task.get("status") == "ready"),
        key=lambda task: (str(task.get("priority")), str(task.get("id"))),
    )
    print()
    print("Listas para iniciar:")
    if not ready:
        print("  (ninguna)")
    for task in ready:
        print(f"  {task.get('priority')}  {task.get('id')}  {task.get('title')}")

    open_risks = [
        risk
        for risk in catalog.get("risks", [])
        if isinstance(risk, dict) and risk.get("status") == "open"
    ]
    print()
    print(f"Riesgos abiertos: {len(open_risks)}")
    for risk in sorted(open_risks, key=lambda item: str(item.get("id"))):
        print(f"  {risk.get('severity'):<7} {risk.get('id')}  {risk.get('title')}")

    return 0


def command_render(arguments: argparse.Namespace) -> int:
    try:
        catalog = load_catalog()
        rendered = _render_all(catalog, arguments.only)
    except CatalogError as error:
        print(f"project_control: {error}")
        return 1

    problems = validate_catalog(catalog)
    errors = [problem for problem in problems if problem.level == "error"]
    if errors:
        print("no se renderiza con un catalogo invalido:")
        for problem in errors:
            print(problem.render())
        return 1

    for filename, content in rendered.items():
        target = DOCUMENTS_DIRECTORY / filename
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError:
            existing = None
        if existing == content:
            print(f"  sin cambios  {filename}")
        else:
            target.write_text(content, encoding="utf-8")
            print(f"  escrito      {filename}")
    return 0


def _read_staged_bytes(relative_path: Path) -> bytes | None:
    """Contenido de un archivo en el indice de Git, o None si no esta.

    Sin esto, `check` compara solo el working tree y el estado exacto desde el
    que se hace commit —catalogo staged y Markdown recien renderizado sin
    stagear— passa como sincronizado.
    """

    try:
        result = subprocess.run(
            ["git", "show", f":{relative_path.as_posix()}"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return None

    if result.returncode != 0:
        return None

    return result.stdout


def command_check(arguments: argparse.Namespace) -> int:
    """Compara el Markdown contra el catalogo. Solo lectura por construccion."""

    try:
        catalog = load_catalog()
        rendered = _render_all(catalog, arguments.only)
    except CatalogError as error:
        print(f"project_control: {error}")
        return 1

    problems = validate_catalog(catalog)
    errors = [problem for problem in problems if problem.level == "error"]
    for problem in problems:
        print(problem.render())
    if errors:
        print(f"\n{len(errors)} error(es) de validacion")
        return 1

    drifted = []
    missing = []
    unstaged = []
    expected_bytes = {name: content.encode("utf-8") for name, content in rendered.items()}

    for filename, expected in expected_bytes.items():
        try:
            relative = (DOCUMENTS_DIRECTORY / filename).relative_to(REPOSITORY_ROOT)
        except ValueError:
            # Fuera del repositorio no hay indice que consultar.
            relative = None

        # Se comparan BYTES, no texto: `read_text()` normaliza los finales de
        # linea, asi que un archivo con CRLF pareceria identico y la deriva
        # pasaria inadvertida justo en un repositorio con politica de EOL.
        try:
            working_tree = (DOCUMENTS_DIRECTORY / filename).read_bytes()
        except FileNotFoundError:
            working_tree = None
        except OSError as error:
            drifted.append(f"{filename}: no se pudo leer ({error})")
            continue

        if working_tree is None:
            missing.append(filename)
            continue

        if working_tree != expected:
            drifted.append(filename)
            continue

        # El working tree puede estar bien y el indice no: ese es el estado desde
        # el que se hace commit.
        if relative is not None:
            staged = _read_staged_bytes(relative)
            if staged is not None and staged != expected:
                unstaged.append(filename)

    if unstaged:
        drifted.extend(f"{name} (stale en el indice de git)" for name in unstaged)

    if missing or drifted:
        if missing:
            print("\nfaltan documentos generados: " + ", ".join(sorted(missing)))
        if drifted:
            print("documentos desactualizados respecto del catalogo: " + ", ".join(sorted(drifted)))
        print("\nEjecutar: python3 tools/project_control.py render")
        return 1

    print(f"catalogo y {len(rendered)} documentos generados en sync")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project_control",
        description="Project Control Center de cv-latex: valida el catalogo y verifica la documentacion derivada.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="valida la estructura del catalogo (solo lectura)").set_defaults(
        handler=command_validate
    )
    subparsers.add_parser("status", help="resumen textual del estado (solo lectura)").set_defaults(
        handler=command_status
    )

    render_parser = subparsers.add_parser(
        "render", help="escribe el Markdown derivado desde el catalogo (unico verbo que escribe)"
    )
    render_parser.add_argument("--only", choices=sorted(GENERATED_DOCUMENTS), default=None)
    render_parser.set_defaults(handler=command_render)

    check_parser = subparsers.add_parser(
        "check", help="compara el Markdown contra el catalogo sin escribir nada"
    )
    check_parser.add_argument("--only", choices=sorted(GENERATED_DOCUMENTS), default=None)
    check_parser.set_defaults(handler=command_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    return int(arguments.handler(arguments))


if __name__ == "__main__":
    sys.exit(main())