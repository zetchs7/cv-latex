# Project Control Center v1

## Objetivo

Convertir el desarrollo de cv-latex de "avanzado con documentación dispersa" en "centralizado,
verificable y preparado para ejecutar las últimas features de forma ordenada".

Dos alcances:

- **Objetivo A**: cerrar el PR #17 (aislamiento de tests) si se cumplen las condiciones ya
  autorizadas.
- **Objetivo B**: implementar un sistema interno de gobierno del proyecto: estado verificable,
  backlog estructurado, roadmap por dependencias, guía de gobernanza de GitHub, catálogo
  canónico en JSON y una herramienta de validación reproducible con Python standard library.

## Problema

El proyecto tiene mucha documentación —16 archivos en `docs/development/`, 4 ADR, 25 lecciones
aprendidas— pero **no hay una fuente única que responda "¿en qué está el proyecto?"**. El estado
real está repartido entre `MODULE_INDEX.md`, `DEVELOPMENT_LOG.md`, issues de GitHub y memoria de
sesiones. Eso produce tres fallos concretos ya observados:

1. No se puede reconstruir el estado del proyecto en una sesión nueva sin leer mucho.
2. No hay backlog con IDs estables, prioridad, dependencias y criterios de aceptación.
3. No hay forma automática de detectar que la documentación quedó obsoleta respecto del código.

## Por qué ahora

El trabajo reciente (Feature 1 y PR #17) se apoyó en memoria de sesión y documentos dispersos
para reconstruir contexto. Con la aplicación ya integrada en `development` y la infraestructura
de pruebas arreglada, es el momento correcto para instalar la gobernanza **antes** de la última
ronda de features.

## Alcance

### Dentro de alcance

- Catálogo canónico en JSON con el estado de cada tarea del backlog.
- Herramienta `tools/project_control.py` (solo Python standard library, sin red, sin GitHub).
- `docs/development/PROJECT_STATUS.md`, `BACKLOG.md`, `ROADMAP.md`,
  `GITHUB_ISSUES_PROJECTS_GUIDE.md`.
- Plantillas en `.github/ISSUE_TEMPLATE/`.
- Tests de la herramienta y del catálogo.
- Integración selectiva con documentación existente.
- ADR que documente la decisión de diseño.
- Investigación de solo lectura de la siguiente feature (Issue #14, importación de CV desde PDF).

### Fuera de alcance

- No se agrega el sistema al dashboard del usuario final.
- No se crea ninguna base de datos adicional.
- No se instalan dependencias nuevas.
- No se modifica `main`.
- No se publica la feature: sin push, sin PR, sin merge, sin release, sin tags.
- No se crean Issues ni GitHub Projects en GitHub.
- No se modifica el código de producto de la aplicación.
- No se implementa la importación de CV desde PDF.

## Restricciones

- Fuentes de verdad única por dato, sin duplicación entre catálogo y Markdown.
- El comando de comprobación debe ser de solo lectura y no depender de GitHub.
- Nada de framework genérico: la herramienta existe solo para cv-latex.
- Preservar EOL por archivo al editar; `app/database.py`,
  `app/services/documentation_service.py` y los `docs/development/*.md` son CRLF.
- Nada de `reset`, `clean`, `restore`, `stash`, rebase, force push ni reescritura de historial.

## Estrategia de entrega

Previsión: ~1.200 líneas authored (documentación, herramienta, catálogo, tests), por encima del
presupuesto de ~400. **Estrategia: `ask-on-risk`.**

La publicación está diferida por instrucción explícita de Franco (sin push, sin PR). No hace
falta decidir estrategia de encadenado de PRs hasta que exista autorización de publicación. Los
commits se mantienen atómicos y auditables en la rama de feature para que la publicación futura
sea trivial.

## Criterios de aceptación

- `python3 tools/project_control.py validate` pasa sin errores ni advertencias.
- `python3 tools/project_control.py check` no modifica ningún archivo (verificado por hash).
- El catálogo detecta IDs duplicados, dependencias inexistentes, ciclos, estados inválidos,
  prioridades inválidas y ausencia de criterios de aceptación.
- Los cuatro documentos centrales existen, están enlazados entre sí y con el resto de la doc.
- Los tests nuevos pasan y no escriben en `data/` ni en `app/static/docs/`.
- `main` sigue en `a28d1df`.
- Working tree limpio al terminar.

## Tareas

| ID | Tarea | Estado | Ruta |
| --- | --- | --- | --- |
| T1 | Cerrar PR #17 con las condiciones ya autorizadas | ✅ hecho | directo (bash) |
| T2 | Auditoría del estado real del proyecto | 🔄 en curso | delegado (2 explore) |
| T3 | ADR-0005: diseño del Project Control Center | ⬜ pendiente | inline |
| T4 | Catálogo JSON + `tools/project_control.py` | ⬜ pendiente | inline |
| T5 | Documentos centrales (4 archivos) | ⬜ pendiente | inline |
| T6 | Inventario del backlog con evidencia | ⬜ pendiente | inline |
| T7 | Plantillas `.github/ISSUE_TEMPLATE/` | ⬜ pendiente | inline |
| T8 | Tests del sistema de control | ⬜ pendiente | inline |
| T9 | Integración documental selectiva | ⬜ pendiente | inline |
| T10 | Revisión de calidad (10 preguntas obligatorias) | ⬜ pendiente | inline |
| T11 | Commits temáticos locales | ⬜ pendiente | inline |
| T12 | Investigación de solo lectura Issue #14 | ⬜ pendiente | inline |

**Declaración de ruta**: T2 fired el trigger de mapeo (evidencia grande, más de 5 consultas
secuenciales) y se delegó en dos exploradores read-only en paralelo, uno por dominio, para no
inflar el contexto del padre. El resto se ejecuta inline porque el diseño ya está decidido por
ODD y por las restricciones explícitas de la fase 3, y porque el trabajo restante depende del
resultado de la auditoría, no de investigación adicional.

## Progreso

### T1 — Cerrar PR #17

**HECHO VERIFICADO.**

Preconditions re-verificadas, no asumidas:

- `fix/test-data-isolation` @ `35d1c23`, 4 commits sobre `development`.
- Codex Review **completado** sobre `35d1c23` el 2026-10-11T21:07:30Z con resultado
  "Didn't find any major issues. You're on a roll."
- Cero comentarios inline con `original_commit_id` = `35d1c23`. Los cuatro existentes
  corresponden a `ce46cfc` (3) y `ae64a2b` (1), ambos ya corregidos.
- `baseRefOid` = `97e2577`: `development` sin avance inesperado.
- `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, sin conflictos.
- Diff acotado a 8 archivos, todos de aislamiento y trazabilidad.

Spot-check de guardas ejecutado sobre el HEAD actual (no se re-auditó lo ya auditado):

| Escenario | Resultado esperado | Resultado observado |
| --- | --- | --- |
| `exports` legítimo en directorio aislado | permitido | permitido |
| `APP_DATA_DIR=/data` (store de Compose) | aborta | aborta |
| `APP_DB_FILENAME=/data/app.db` (absoluta) | aborta | aborta |
| `APP_DB_FILENAME=../x/app.db` (traversal) | aborta | aborta |
| `exports` como symlink fuera del directorio | aborta | aborta |

Archivos escritos fuera del directorio aislado: **0**.

Merge ejecutado: squash `e19ea5a`, `mergedAt=2026-10-12T04:01:56Z`, por `zetchs7`.
Rama correctiva remota preservada en `35d1c23`. `development` local y remoto en `e19ea5a`.
`main` intacta en `a28d1fd`. Tags sin cambios (`v0.8.0`, `v0.9.0`).

**Corrección de un reporte previo**: la sesión anterior cerró diciendo que la revisión estaba
pendiente. Era incorrecto: Codex terminó 2 minutos después del último sondeo. La forma correcta
de detectarlo fue leer el comentario resumen del conector, no el array `reviews`.

### T2 — Auditoría

En curso. Dos exploradores read-only en paralelo.

## Verificación acumulada

| Comprobación | Resultado |
| --- | --- |
| `git status` pre-merge | limpio |
| Suite Python (pre-existente, sobre `35d1c23`) | 248 passed |
| Manifiesto de `data/` antes/después | idéntico |
| Spot-check de guardas de aislamiento | 4/4 escapes bloqueados |
| `docker compose config` | exit 0 |

## Próximo paso

Consolidar T2 y escribir T3 (ADR-0005) antes de la primera escritura de código.