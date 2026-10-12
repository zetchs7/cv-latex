# Catálogo del Project Control Center

Este directorio contiene el archivo que es la **fuente canónica** del estado de CV LaTeX
Builder: `catalog.json`. Los documentos `PROJECT_STATUS.md`, `BACKLOG.md` y `ROADMAP.md` se
generan desde acá con `tools/project_control.py`.

`docs/development/GITHUB_ISSUES_PROJECTS_GUIDE.md` **no** se genera: describe convenciones de
GitHub, no estado del proyecto.

## Cómo se usa

```bash
python3 tools/project_control.py validate   # estructura, IDs, dependencias, ciclos
python3 tools/project_control.py status     # resumen del estado actual
python3 tools/project_control.py render     # reescribe los Markdown generados
python3 tools/project_control.py check      # detecta deriva; no escribe nada
```

Flujo habitual cuando cambia una tarea:

1. Editar `catalog.json`.
2. `validate` — tiene que pasar antes de seguir.
3. `render` — regenera los documentos.
4. `check` — confirma que quedaron en sincronía.

## Campos

JSON no admite comentarios, así que el esquema está acá. El diseño completo, con las
alternativas descartadas, está en `docs/adr/ADR-0005-project-control-center.md`.

### `meta`

| Campo | Tipo | Qué es |
| --- | --- | --- |
| `schema_version` | número | Versión del formato. Hoy solo `1`. |
| `generated_by` | texto | Qué herramienta produce los documentos. |
| `purpose` | texto | Descripción del archivo. |

### `project`

| Campo | Tipo | Qué es |
| --- | --- | --- |
| `name` | texto | Nombre del proyecto. |
| `stable_version` | texto | Versión estable publicada, sin prefijo `v`. |
| `main_branch` / `development_branch` | texto | Nombres de las ramas. |
| `last_verified_on` | texto | Fecha de la última verificación real. |
| `last_verification_evidence` | texto | Qué se corrió y qué dio. |
| `mvp_criteria` | lista de texto | Qué tiene que cumplirse para dar el MVP por terminado. |
| `expanded_vision` | lista de texto | Qué queda fuera del MVP. |
| `release_policy` | lista de texto | Reglas de publicación en `main`. |

### `modules`

Qué partes del producto existen y en qué ramas.

| Campo | Tipo | Qué es |
| --- | --- | --- |
| `id` | texto | Identificador estable, único. |
| `name` | texto | Nombre legible. |
| `routes` | texto | Archivos donde vive. |
| `state` | `planned`, `in_development`, `in_development_branch`, `in_main` | En qué etapa está. |
| `in_development` | booleano | ¿Está en `development`? |
| `in_main` | booleano | ¿Está en `main`? |
| `evidence` | texto | Por qué se afirma eso. |

`state`, `in_development` e `in_main` son **hechos separados y pueden diferir**. Un módulo
puede estar implementado, estar integrado en `development` y aun así no estar publicado.
Esa distinción es el motivo de existir de esta tabla.

### `risks`

| Campo | Tipo | Qué es |
| --- | --- | --- |
| `id` | texto | `RSK-NNN`, único. |
| `title` | texto | El riesgo en una frase. |
| `severity` | `low`, `medium`, `high` | Gravedad. |
| `status` | `open`, `mitigated`, `accepted`, `closed` | Estado. |
| `mitigation` | texto | Qué se va a hacer. |
| `evidence` | texto | Por qué el riesgo es real. |

### `tasks`

| Campo | Tipo | Qué es |
| --- | --- | --- |
| `id` | texto | Identificador estable con prefijo de área, único y **permanente**. |
| `title` | texto | Título corto. |
| `description` | texto | Qué es y por qué importa. |
| `origin` | `franco`, `defect`, `engineering`, `debt` | De dónde sale. |
| `priority` | `P0`, `P1`, `P2`, `P3` | Prioridad. `P0` rompe el uso. |
| `status` | `backlog`, `ready`, `in_progress`, `blocked`, `done`, `cancelled` | Estado. |
| `module` | texto | Módulo afectado. |
| `depends_on` | lista de ids | Dependencias. No puede haber ciclos. |
| `acceptance` | lista de texto | Criterios verificables. No puede estar vacía. |
| `evidence` | texto | Por qué esta tarea existe. |
| `github_issue` | número o `null` | Issue asociado. No se repite entre tareas. |
| `next_action` | texto | El paso concreto siguiente. |
| `approved` | booleano | **`true` solo si Franco lo aprobó.** |

## La distinción que más importa

`approved` y `origin` no son adorno:

- `approved: true` + `origin: franco` → **requisito acordado.**
- `approved: false` → **propuesta de ingeniería.** En `BACKLOG.md` y `ROADMAP.md` aparece
  marcado como tal.

Una recomendación de IA no es un requisito hasta que alguien lo aprueba. El backlog tiene que
poder responder esa pregunta sin ambigüedad, y por eso esos dos campos son obligatorios en
toda tarea.

## Por qué JSON y no Markdown

Markdown se lee mejor pero no se puede validar: no hay forma confiable de detectar un `id`
duplicado, una dependencia rota o un ciclo. El JSON sí, y `validate` lo hace sin red, sin
credenciales y sin depender de GitHub. El costo — editar JSON sin comentarios — se paga con
este archivo.

## Regenerar todo desde cero

Si los documentos generados se corrompen o se borran:

```bash
python3 tools/project_control.py render
```

Eso los reconstruye desde el catálogo. El Markdown no es la fuente: es una vista.