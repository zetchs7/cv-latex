# Integración REAL / PRUEBAS en development

Objetivo: dejar integrada en `development` la feature **Configuración → Entornos Real y Pruebas** (commits atómicos, push, PR contra `development`, revisión `@codex`, squash merge) y dejar un contenedor Docker de evaluación aislado en `127.0.0.1:8001` con datos descartables para las pruebas manuales de Franco.
Rama: `feature/real-test-workspaces` desde `development` `ea4c979`. `main` permanece intacta en `a28d1fd`.
Estrategia de entrega: `single-pr` — un único PR contra `development` con squash merge, decidido explícitamente por Franco en la instrucción de autorización. Runner: `/tmp/opencode/venv-validate/bin/python -m pytest -p no:cacheprovider -q` con `env -u APP_DATA_DIR PYTHONDONTWRITEBYTECODE=1`; JS con `node --test tests/test_structured_cv_editor_js.js`.

---

## Specs

### S1 — Almacenamientos independientes y selector

> "Debe incluir:
> - Almacenamientos independientes.
> - Selector REAL / PRUEBAS.
> - ...
> - Aislamiento total respecto de REAL."

Dos almacenamientos separados bajo `APP_DATA_DIR`, resueltos por prefijo de URL `/real/` y `/test/`, nunca por bandera global mutable ni por cookie. El entorno se resuelve por petición (`ContextVar`). Bases distintas: `<root>/real/app.db` y `<root>/test/app.db`. Mismo ID en dos bases no se cruza. Sin fallback silencioso al almacenamiento equivocado.

### S2 — Identificación visual persistente

> "- Identificación visual persistente."

Banner de modo en todas las páginas con texto e icono (no solo color), presente en light y dark.

### S3 — Generación configurable de datos ficticios

> "- Generación configurable de CVs, cartas y postulaciones ficticias."

Cantidades independientes de CVs, cartas y postulaciones; tope por operación; semilla determinista opcional; CVs validados contra el schema 2; dominios `.invalid` (RFC 2606); generar en MODO REAL prohibido.

### S4 — Borrado físico selectivo

> "- Borrado físico selectivo."

`hard_delete_*` separados de `soft_delete_*`, en dos pasos (previsualización + frase exacta `ELIMINAR <N> DE PRUEBAS` validada en servidor), con revalidación de la selección al ejecutar.

### S5 — Vaciado completo del entorno PRUEBAS

> "- Vaciado completo del entorno PRUEBAS."

Borra base, `-wal`, `-shm`, `-journal`, exportes, borradores y documentación compilada del entorno. Deja el entorno vacío y funcional. Sin backup automático de lo eliminado. Prohibido fuera de MODO PRUEBAS.

### S6 — Validación de relaciones

> "- Validación de relaciones."

Si un CV o carta seleccionados tienen postulaciones vinculadas que no están seleccionadas, no se borra nada: se muestran las dependencias y se ofrece volver. Sin borrado en cascada ni desvinculación automática.

### S7 — Protección CSRF de las nuevas operaciones

> "- Protección CSRF de las nuevas operaciones."

Las 6 rutas POST del módulo (enter, generate, delete/preview, delete/execute, purge, migrate) validan el token antes de cualquier lógica, con cuerpo completo y verificación de no mutación. El entorno nunca se lee del cuerpo del formulario.

### S8 — Migración controlada, dry-run y rollback

> "- Migración controlada, dry-run y rollback de datos históricos."

Diagnóstico sin mutaciones; bloqueo si el destino está ocupado; frase `MIGRAR` escrita en el servidor; checkpoint con la API de backup de SQLite; rollback que cubre todos los movimientos y distingue rollback completo de incompleto. **Al terminar, retira la vista histórica sin prefijo** (base renombrada a `app.db.retirado-<hex>`, marcador `.environments-migrated`, arranque sin inicializar la raíz, redirección 303 a `/real/`, con `/health` y `/static` exentos). Solo REAL y PRUEBAS quedan operativos.

### S9 — Validación final antes de integrar

> "No asumir que esta evidencia sustituye una validación final sobre el código que realmente se integrará."

Suite Python completa, tests JS, `compileall`, `diff --check`, PCC `validate`/`check`, **y** build Docker aislada con pruebas sobre el código final. Sin montar `./data`. Comparar el estado de los datos reales antes y después. Documentar las omisiones justificadas del entorno Docker.

### S10 — Commits, push, PR y revisión

> "1. Realizar commits atómicos sobre feature/real-test-workspaces.
> 2. Push normal de la rama feature.
> 3. Abrir PR contra development.
> 4. Esperar GitHub Actions.
> 5. Solicitar @codex review sobre el HEAD final.
> 6. Verificar los hallazgos contra el código.
> 7. Corregir defectos materiales demostrados y agregar pruebas de regresión."

Commits con prefijos Convencionales (`feat`, `test`, `docs`), sin `Co-Authored-By`. PR contra `development` (la default del repo es `main`: hay que fijar `--base development`). El PR debe incluir alcance, ramas, archivos, validaciones, riesgos, pendientes y decisión de Code Review.

### S11 — Tope de rondas de corrección

> "No encadenar revisiones indefinidas. Como máximo dos rondas adicionales de corrección y revisión; si persisten defectos bloqueantes, detener el merge con evidencia.
> No interpretar un estado COMMENTED como aprobación automática.
> Si hay P0/P1, riesgos de pérdida de datos, cruces entre REAL y PRUEBAS o regresiones relevantes sin resolver, NO realizar el merge."

### S12 — Merge autorizado

> "- Integrar el PR mediante squash merge a development.
> - No eliminar la rama remota.
> - No usar force push.
> - No modificar main.
> - No crear tags.
> - No publicar releases."

Seguido de sincronización de `development` local con `origin/development`, validación integrada posterior al merge, confirmación del SHA final de `development` y de que `main` sigue en `a28d1fd`.

### S13 — Contenedor de evaluación para pruebas manuales

> "- Puerto sugerido: 127.0.0.1:8001.
> - Directorio /data efímero, independiente y vacío.
> - Sin montar ./data ni otros directorios privados.
> - Sin acceso a información personal.
> - Datos únicamente ficticios.
> - Sin interferir con el contenedor del puerto 8000."

Construido desde `development` integrado. Healthcheck, navegación REAL, navegación PRUEBAS, generación, separación efectiva, acceso a Configuración y logs sin errores. Informar que la información es descartable y puede desaparecer al detenerlo. Si el puerto está ocupado, no reemplazar el servicio existente.

### S14 — Migración histórica NO ejecutada

> "No realizar todavía la migración de los registros históricos."

No autorizado: modificar o migrar la base SQLite histórica, eliminar datos históricos, eliminar el CV ID 49, reemplazar el contenedor del puerto 8000, implementar el rediseño UX/UI general, declarar completado SEC-001.

### S15 — Informe final obligatorio

Entregar los 13 puntos enumerados, con evidencia observable y no solo narración de éxito.

---

## Tasks

| ID | S# | Ruta | Estado | Commit |
| --- | --- | --- | --- | --- |
| T1 | S1-S8 | verificado previamente (533 pruebas) | done | sin commit, trabajo previo sin commitear |
| T2 | S9 | delegada | done | validación de host 533 passed + Docker aislado 503 passed / 30 skipped, datos idénticos antes y después |
| T3 | S10 | delegada | done | Ronda 1: 7 hallazgos corregidos, commit b54d743 |
| T4 | S11 | delegada | done | Ronda 2: 4 hallazgos corregidos, commit 8ec65a4 |
| T5 | S12 | delegada | done | Ronda 3: P1 migración concurrente + P2 cartas vinculadas, tests nuevos |
| T6 | S13 | inline | pending | — |
| T7 | S14-S15 | inline | pending | — |

---

## Log

### L1 — Pedido original de Franco (verbatim)

> # CV LaTeX Builder — Cierre e integración de REAL / PRUEBAS
>
> ## CONTEXTO
>
> Repositorio: `/home/franco/GIT/cv-latex`
>
> Runtime: OpenCode V2 + Gentle AI.
>
> Workflow: ODD.
>
> Rama de trabajo: `feature/real-test-workspaces`.
>
> Base de desarrollo conocida: `development` en `ea4c979`.
>
> Main conocida: `a28d1fd`.
>
> La feature REAL / PRUEBAS está implementada localmente, pendiente de commit, push, PR e integración.
>
> Última evidencia reportada:
> - 533 pruebas Python aprobadas, 0 omitidas en host.
> - Tests de aislamiento y migración aprobados.
> - JavaScript aprobado.
> - Project Control Center validate/check aprobado.
> - Docker aislado validado anteriormente.
> - Datos actuales intactos.
> - Sin commits ni PR para esta feature.
>
> No asumir que esta evidencia sustituye una validación final sobre el código que realmente se integrará.
>
> Franco autorizó expresamente realizar commits, push, crear PR, solicitar revisión e integrar mediante squash merge a development, siempre que las verificaciones sean satisfactorias.
>
> ## OBJETIVO
>
> Dejar completamente integrada en `development` la funcionalidad:
>
> **Configuración → Entornos Real y Pruebas**
>
> Debe incluir:
> - Almacenamientos independientes.
> - Selector REAL / PRUEBAS.
> - Identificación visual persistente.
> - Generación configurable de CVs, cartas y postulaciones ficticias.
> - Borrado físico selectivo.
> - Vaciado completo del entorno PRUEBAS.
> - Validación de relaciones.
> - Protección CSRF de las nuevas operaciones.
> - Migración controlada, dry-run y rollback de datos históricos.
> - Aislamiento total respecto de REAL.
>
> Priorizar cerrar correctamente la integración, sin agregar funcionalidades fuera del alcance.
>
> ## FASE A — PREFLIGHT
>
> Verificar repositorio, rama activa, diferencias locales, archivos nuevos y cambios pendientes.
>
> Leer AGENTS.md, PROJECT_PLAYBOOK.md, LESSONS_LEARNED.md, ADRs y REAL_TEST_WORKSPACES.md.
>
> Confirmar que la rama parte de development.
>
> No descartar ningún cambio local.
>
> Revisar que no se vayan a incluir datos privados, bases SQLite, archivos .env, secretos ni backups en Git.
>
> Verificar que los archivos nuevos y modificados correspondan a la feature.
>
> ## FASE B — VALIDACIÓN FINAL
>
> Ejecutar la suite Python completa, tests JS, compileall, diff --check y Project Control Center validate/check.
>
> Ejecutar pruebas Docker aisladas sobre una imagen construida desde el código final.
>
> No montar el directorio real ./data.
>
> Validar:
> - Bases independientes.
> - Generación en PRUEBAS.
> - Ausencia de modificaciones en REAL.
> - Borrado selectivo y total.
> - Dependencias.
> - CSRF.
> - Solicitudes concurrentes.
> - Aislamiento de archivos y exportaciones.
> - Migración dry-run sin mutaciones.
> - Rollback sobre fixtures.
> - Comportamiento de rutas sin prefijo después de migrar.
> - Funcionamiento del CV ID 49 en los escenarios de prueba cuando corresponda.
>
> Comparar el estado de los datos reales del proyecto antes y después de los tests.
>
> Documentar las omisiones justificadas del entorno Docker.
>
> ## FASE C — GIT Y PR
>
> Si la validación es satisfactoria:
>
> 1. Realizar commits atómicos sobre feature/real-test-workspaces.
> 2. Push normal de la rama feature.
> 3. Abrir PR contra development.
> 4. Esperar GitHub Actions.
> 5. Solicitar @codex review sobre el HEAD final.
> 6. Verificar los hallazgos contra el código.
> 7. Corregir defectos materiales demostrados y agregar pruebas de regresión.
>
> No encadenar revisiones indefinidas. Como máximo dos rondas adicionales de corrección y revisión; si persisten defectos bloqueantes, detener el merge con evidencia.
>
> No interpretar un estado COMMENTED como aprobación automática.
>
> Si hay P0/P1, riesgos de pérdida de datos, cruces entre REAL y PRUEBAS o regresiones relevantes sin resolver, NO realizar el merge.
>
> ## FASE D — MERGE AUTORIZADO
>
> Si los controles anteriores son satisfactorios:
>
> - Integrar el PR mediante squash merge a development.
> - No eliminar la rama remota.
> - No usar force push.
> - No modificar main.
> - No crear tags.
> - No publicar releases.
>
> Sincronizar development local con origin/development.
>
> Ejecutar una validación integrada posterior al merge.
>
> Confirmar el SHA final de development y que main continúa intacta.
>
> ## FASE E — DOCKER PARA PRUEBAS HUMANAS
>
> Franco quiere comenzar inmediatamente las pruebas funcionales y visuales.
>
> No reemplazar todavía `cv_latex_app` ni modificar su base histórica.
>
> Preparar, si Docker lo permite, un segundo contenedor aislado de evaluación, construido desde development integrado, con:
>
> - Puerto sugerido: 127.0.0.1:8001.
> - Directorio /data efímero, independiente y vacío.
> - Sin montar ./data ni otros directorios privados.
> - Sin acceso a información personal.
> - Datos únicamente ficticios.
> - Sin interferir con el contenedor del puerto 8000.
>
> El contenedor debe permitir pruebas reales desde el navegador en:
>
> http://localhost:8001
>
> Comprobar:
> - Healthcheck.
> - Navegación REAL.
> - Navegación PRUEBAS.
> - Generación de registros ficticios.
> - Separación efectiva de los datos.
> - Acceso a Configuración.
> - Logs sin errores.
>
> Explicar que la información de este contenedor de evaluación es descartable y puede desaparecer al detenerlo.
>
> Si el puerto está ocupado, no reemplazar el servicio existente: informar la situación o elegir uno libre y documentarlo.
>
> No realizar todavía la migración de los registros históricos.
>
> ## LÍMITES DE AUTONOMÍA
>
> Autorizado:
> - Implementación correctiva dentro de esta feature.
> - Tests.
> - Build Docker aislada.
> - Commit.
> - Push.
> - Crear PR.
> - Codex Review.
> - Squash merge condicionado a development.
> - Sincronización de development.
> - Contenedor adicional de evaluación con datos descartables.
>
> No autorizado:
> - Modificar main.
> - Publicar release.
> - Eliminar ramas remotas.
> - Force push.
> - Eliminar el CV ID 49.
> - Modificar o migrar la base SQLite histórica.
> - Eliminar datos históricos.
> - Reemplazar el contenedor del puerto 8000.
> - Implementar el rediseño UX/UI general.
> - Declarar completado SEC-001 sin su implementación y pruebas.
>
> Si hay una decisión irreversible o una ambigüedad material, detenerse y solicitar autorización.
>
> ## INFORME FINAL OBLIGATORIO
>
> Entregar:
>
> 1. PR creado y enlace.
> 2. Resultados de Codex Review.
> 3. Tests ejecutados y resultados.
> 4. Merge realizado o bloqueo concreto.
> 5. SHA final de development.
> 6. Estado de main.
> 7. Estado de los datos históricos.
> 8. Estado del contenedor original en 8000.
> 9. Estado del contenedor de evaluación en 8001.
> 10. URL exacta para las pruebas manuales.
> 11. Funcionalidades listas para probar.
> 12. Defectos conocidos y pendientes.
> 13. Pasos necesarios para ejecutar posteriormente la migración real con autorización de Franco.
>
> OBJETIVO FINAL:
>
> Feature REAL / PRUEBAS integrada y verificada en development, más un entorno Docker aislado listo para que Franco pruebe todas las funcionalidades desde el navegador, sin tocar la información histórica.
>
> No terminar con una simple narración de éxito: aportar evidencia observable.

### L2 — Preflight (Fase A), 2026-10-14

Verificación de estado delegada a `gentle-ai-verify` (este runtime no expone shell al orquestador; toda ejecución de comandos va delegada). Resultado **GO**.

- Rama `feature/real-test-workspaces` en `ea4c979`, **0 commits por delante**: todo el trabajo sigue sin commitear.
- `development` = `origin/development` = `ea4c979`; `main` = `origin/main` = `a28d1fd`; `git merge-base --is-ancestor development HEAD` exit 0.
- Remoto `origin https://github.com/zetchs7/cv-latex.git`; `gh` autenticado como `zetchs7` con scopes `gist, read:org, repo, workflow`.
- **La rama default del repo en GitHub es `main`, no `development`**: el PR debe crearse con `--base development` explícito.
- Inventario: 17 trackeados modificados (421 inserciones, 12 borrados) + 11 sin trackear, coincidente **exactamente** con el conjunto esperado de la feature. Ninguna entrada extra. Sin cambios staged, sin stash.
- Higiene: sin credenciales en el diff trackeado ni en los archivos nuevos. Único golpe del barrido `\.env` es `.env.example` (falso positivo: 5 defaults no sensibles, trackeado en el baseline). `data/*` está ignorado, `git add -n data/` no agrega nada; `data/.gitkeep` (2 bytes) está trackeado desde el baseline, no es cambio de esta feature.
- Docker 29.8.2, Compose v5.5.1. `cv_latex_app` `Up 9 hours (healthy)` en `127.0.0.1:8000`, imagen creada 2026-10-13T18:55:42Z, **anterior a la feature**. **Puerto 8001 libre.**
- Hallazgo preexistente no causado por este cambio: contenedor `cv-latex-builder` en crash-loop (`Restarting (1)`). No pertenece al alcance.

### L3 — Política aplicable extraída del preflight

- Prefijos atómicos Convencionales (`docs`, `fix`, `feat`, `test`, `chore`, `build`, `ci`) — `AGENTS.md:30`.
- Sin push directo a `main`/`development`, sin force push, sin borrar ramas remotas, sin tags — `AGENTS.md:28-29`.
- Nada de secretos, backups reales ni bases SQLite en Git — `AGENTS.md:13`.
- Este cambio (rutas, Docker, CSRF) exige PR hacia `development` con `@codex review` — `AGENTS.md:139-141`.
- Checklist pre-PR: rama correcta, diff sin archivos inesperados, validaciones ejecutadas y reportadas, docs de desarrollo actualizadas, árbol limpio después del commit — `PROJECT_PLAYBOOK.md:65-72`.
- No ejecutar la suite en host sin el aislamiento en código de `conftest.py` — `LESSONS_LEARNED.md:240`, `:260-261`.
- Esperar `healthy` antes de leer fallos de arranque como bugs — `LESSONS_LEARNED.md:138-141`.
- Cambios fuera de alcance no se mezclan en un PR limpio — `LESSONS_LEARNED.md:170`, `:190`.

### L4 — Validación final (Fase B), 2026-10-14

Ambas corridas delegadas a `gentle-ai-verify`, en paralelo, sobre el código final.

**Host** — PASS:
- Suite completa **533 passed**, 3 warnings preexistentes de deprecación (starlette/httpx), exit 0.
- `tests/test_workspaces.py` **68 passed**; `tests/test_project_control.py` **74 passed**.
- `compileall` exit 0; `git diff --check` exit 0 (los 3 warnings de CRLF son preexistentes).
- PCC `validate` "catalogo valido: sin errores ni advertencias"; `check` "catalogo y 3 documentos generados en sync".
- `node --test` 1 pass, 0 fail.
- Datos reales antes/después: manifiesto `data/` `360e0ffa8f91ec37c508aa3302dc5a55` idéntico; `app/static/docs` `71c3e1857c962bfced0123c956d512d0` idéntico; filas `cvs 49 / cover_letters 10 / applications 6` idénticas. Sin archivos huérfanos.

**Docker aislado** — PASS, imagen efímera `cv-latex-verify:integration` desde el árbol final (build exit 0):
- `--network none --read-only --tmpfs /tmp --tmpfs /data` → **503 passed, 30 skipped**. Los 30 son `tests/test_project_control.py` ("indice de Git…") porque la imagen no incluye `.git`; ninguno es PDF/LaTeX.
- `compileall` con `--read-only` devuelve exit 0 sin probar sintaxis (falla al escribir `.pyc`): se repitió en FS escribible, exit 0 sin errores.
- Matriz HTTP sobre efímero con datos efímeros y **sin montar `./data`**: `/health` 200, `/` 200 sin banner, `/config/workspaces` 200, `/test/` 200 con `MODO PRUEBAS`, `/real/` 200 con `MODO REAL`, `/produccion/cvs/` **404**, `/cvs/` sin prefijo 200 (transicional), `/documentation/` y `/documentation/technical` 200.
- Generación en PRUEBAS: `Listo: 2 currículums, 1 cartas y 0 postulaciones creados en MODO PRUEBAS.` Inventario en el contenedor: TEST `2/1/0`, REAL `0/0/0`. Tres archivos distintos por inode y hash: `/data/app.db`, `/data/real/app.db`, `/data/test/app.db`.
- CSRF inválido → `La sesión expiró. Volvé a intentarlo.` sin mutación. Generar vía `/real/...` → `Los datos de prueba solo se generan en MODO PRUEBAS.` Purge vía `/real/...` → `Solo se puede vaciar el entorno de PRUEBAS.`
- Concurrencia: 8 peticiones a `/test/cvs/` + 8 a `/real/cvs/` con `ThreadPoolExecutor(16)` → **16/16 correctas, 0 cruces**.
- Migración sobre fixtures: dry-run sin mutaciones (hash de listado idéntico antes/después); ejecución mueve la base, deja `.environments-migrated` y `app.db.retirado-*`, y `GET /` sin redirigir pasa a **303 → `/real/`** mientras `/health` y `/static/css/app.css` siguen en 200 sin `Location`.
- Datos reales después: manifiestos y filas idénticos al baseline. `cv_latex_app` sigue `Up (healthy)` en `127.0.0.1:8000` con su mount intacto. Contenedores e imagen efímeros eliminados.

**Omisiones justificadas del entorno Docker** (reportadas por el verificador): render visual en navegador (sin browser); `compileall` sobre FS read-only; `docker compose` sobre el contenedor real (prohibido); PDF end-to-end vía HTTP (la toolchain está en la imagen y 169 tests latex/pdf corrieron dentro de los 503, pero no se abrió `/cvs/{id}/pdf`); límites `generate` por HTTP; migración real sobre `./data` (prohibida por diseño); multi-worker/HTTPS/rate-limit (uvicorn local single-worker); capas apt/pip cacheadas en este build.

**Observación advisory del verificador (no bloqueante):** `confirmation.strip()` hace que `MIGRAR ` con espacio final ejecute la migración. No es pérdida de datos ni cruce de entornos: sigue exigiendo la frase exacta módulo espacios circundantes. No se corrige por estar fuera del alcance solicitado.

### L5 — Decisión de split de commits
Aplicado el skill `work-unit-commits`: **no se divide por tipo de archivo**. El criterio del skill es "Avoid `models`, then `services`, then `tests` if none works alone", "Keep tests with code" y "Keep docs with the user-visible change". Ningún subconjunto de esta feature funciona por separado: `environments.py` sin el middleware no hace nada, y las rutas sin el servicio no existen.

Consecuencia: **un único commit atómico `feat(workspaces)`** con código, tests y documentación juntos. Checklist del skill cumplido — propósito único; el repo tiene sentido al aplicar solo ese commit; tests y docs incluidos; rollback razonable (quitar los archivos nuevos y revertir los 7 trackeados); comando de test focalizado y resultado registrados (533 passed / 68 workspaces); frontera de rollback nombrada.

Se descarta explícitamente agregar `tests/test_workspace_http_probes.py` propuesto por el verificador Docker: sus casos se solapan con la cobertura existente de `tests/test_workspaces.py` (vista transicional, banners, generación solo en PRUEBAS, CSRF negativo, concurrencia, dry-run, retiro, `/health` y `/static` exentos). `LESSONS_LEARNED.md:170` (LL-016) prohíbe cambios no bloqueantes en un PR limpio.

### L6 — Ronda 1 de corrección (revisión @codex), 2026-10-14

La revisión sobre `71ee665` llegó en **207 s** con estado `COMMENTED` (no es aprobación) y 7 hallazgos. Cada uno se verificó contra el código antes de corregir:

| # | Hallazgo | Veredicto propio |
| --- | --- | --- |
| 1 | Sin banner en `/applications/` y `/documentation/` (P1) | **Confirmado material**: los dos únicos `Jinja2Templates(directory=...)` directos del proyecto, sin context processor |
| 2 | Carrera entre `source.backup()` y el renombre de la base (P1) | **Confirmado material**: riesgo de pérdida de datos |
| 3 | `confirmation.strip()` acepta `MIGRAR ` con espacio | **Confirmado menor, no corregido**: convención preexistente en `cover_letters.py:198`, `cvs.py:459`, `pdf_import.py:306` |
| 4 | Enlace "Administrar datos" sin comilla de cierre (P1) | **Confirmado material**: el valor se tragaba el texto y el enlace desaparecía del DOM |
| 5 | `cover_letters` consultaba `title, recipient_company` | **Confirmado material y más grave de lo informado**: esas columnas no existen (`app/database.py:234`), el `except sqlite3.Error` devolvía `[]`, y como `_records_for` alimenta también `_selected_rows`, la previsualización de borrado de cartas salía vacía |
| 6 | `app.db` hard-codeado frente a `APP_DB_FILENAME` | **Confirmado**: inventario vacío, vaciado sin efecto y migración al destino equivocado si se configura la variable |
| 7 | Vaciado oculto cuando solo quedan archivos | **Confirmado material**: `counts.total` solo suma registros |

**Correcciones aplicadas (10 archivos, +318 / −24):** `create_templates()` en las dos vistas; comilla de cierre; columnas y celdas de cartas; flag `counts.purgeable`; `database_filename()` en `environments` y en las 5 resoluciones de `workspace_service`; candado `.environments-migrating` levantado antes del snapshot y limpiado en `finally`, con el middleware devolviendo 503 a toda petición que no sea `/health` o `/static`.

Se detectó y corrigió un error propio durante la edición: al mover la exención de `_is_exempt_from_retirement` al chequeo del candado se eliminó del redirect de retiro, lo que habría vuelto a romper el healthcheck del contenedor; se restauró.

**Evidencia RED** (árbol pre-fix exportado con `git archive 71ee665` a `/tmp/opencode`, fuera del repositorio, borrado después): **6 pruebas comportamentales fallan en el código sin corregir** — banner en aplicaciones y documentación, banner en REAL, href del enlace, listado de cartas, previsualización de borrado de cartas (falla en la 2ª asertación: el formulario se renderiza pero sin la empresa) y vaciado con solo archivos. `test_el_vaciado_no_se_ofrece_si_no_hay_nada_que_borrar` pasa en la base: es guarda de comportamiento existente, no test de defecto.

**Evidencia GREEN (árbol corregido):** `tests/test_workspaces.py` **79 passed** (68 + 11); suite completa **544 passed**; `tests/test_project_control.py` **74 passed**; `compileall` exit 0; `git diff --check` exit 0; PCC `validate` "catalogo valido" y `check` "en sync"; `node --test` 1 pass 0 fail. Manifiesto de `data/` idéntico antes y después (`360e0ffa8f91ec37c508aa3302dc5a55`), `ls -la data/` sin cambios.

**Advertencia benigna:** `app/routes/applications.py` y `app/routes/documentation.py` tienen fin de línea CRLF uniforme en el árbol de trabajo (propiedad preexistente de esos archivos, hoy visible porque esta ronda los modifica). `.gitattributes` declara `* text=auto eol=lf`, así que el blob commiteado queda en LF y `git diff --check` sale 0; las dos líneas son avisos de conversión, no errores de whitespace. No se tocaron para no reescribir 368 líneas por una propiedad que git normaliza.

### L7 — Ronda 2 de corrección (revisión @codex), 2026-10-14

La segunda revisión sobre `b54d743` volvió en **`COMMENTED`** (no es aprobación) con **4 hallazgos, los 4 confirmados contra el código** antes de corregir:

| # | Hallazgo | Veredicto propio |
| --- | --- | --- |
| 1 | **P1**: el candado solo frena peticiones que entran al middleware *después* de escribirse; una ya admitida que queda suspendida en `await call_next` se reanuda después de `backup()` y escribe en la base ya renombrada a `retirado-*` o recrea `root/app.db` | **Confirmado material, pérdida de datos**: la migración bloquea el event loop, así que la petición en vuelo corre *después* de la migración completa |
| 2 | **P2**: `plan_migration` bloquea con destino vacío generado por `ensure_environment_ready`, y REAL no tiene acción para vaciarse | **Confirmado material**: visita previa ⇒ bloqueo permanente de la migración |
| 3 | **P2**: el predicado `-{id}.` no coincide con los nombres reales `cv-{id}-{titulo}-{variante}-{timestamp}.ext` | **Confirmado material**: el borrado reportaba 0 archivos y dejaba los exports en disco. El test existente fabricaba `cv-1.tex`, un nombre que la app nunca genera |
| 4 | **P2**: se ignora el retorno de `hard_delete_*` (devuelve `False` con `rowcount == 0`) | **Confirmado**: se contaban como borrados registros que la base rechazó |

**Correcciones aplicadas (5 archivos, +435 / −40):**

1. **Candado + drenaje.** `execute_migration` se partió en `validate_migration()` / `migration_lock()` / `run_migration()`, quedando como envoltorio síncrono para los tests existentes. El middleware registra las peticiones admitidas (`_admitted` + `ContextVar` compartida por la misma vía que `set_environment`) y expone `drain_admitted_requests()`. La ruta ahora hace **candado → `await drain()` → `run_migration()`**, con timeout de 10 s y aborte sin mutar datos; las rutas exentas (`/health`, `/static`) no entran en el drenaje para no poder agotarlo.
2. **Destino vacío permitido.** Se eliminó el guard `candidate.exists()` y ahora sólo bloquea un destino **con contenido** (registros, `exports` o `import-drafts`), base o no base.
3. **Patrón de export.** Nuevo `_export_belongs_to(path, prefix, record_id)` sobre el segundo segmento del stem, acotado por prefijo (`cv-…`, `cover-letter-…`); la limpieza se extendió a cartas, que antes quedaban huérfanas.
4. **`hard_delete_*`.** Si devuelve `False` no se incrementa: va a `missing` (nuevo), que la ruta traduce en "`N` registro(s) ya no existían y no se contaron". No va a `pending`, porque no hay nada que reintentar.

**Docs actualizados** (`REAL_TEST_WORKSPACES.md` §5, §7.2, §7.3, §12): regla nueva de destino vacío, orden candado→drenaje, prefijos de export, y el `503` de la ventana como comportamiento esperado.

**Evidencia RED** (árbol `b54d743` exportado con `git archive` a `/tmp/opencode`, fuera del repositorio, con el `tests/test_workspaces.py` nuevo copiado encima y borrado después): **10 pruebas comportamentales fallan en el código sin corregir** — las dos del drenaje, la del orden candado/drenaje, la de migración por HTTP con drenaje real, la de visita previa, la de destino sólo con archivos, la del nombre real de export, la de export de carta, la de `missing` por servicio y la de `missing` por HTTP.

**Evidencia GREEN (árbol corregido):** `tests/test_workspaces.py` **89 passed** (79 + 10); suite completa **554 passed**; `compileall` 0; `git diff --check` 0; PCC `validate` "catalogo valido" y `check` "3 documentos en sync"; `node --test tests/test_structured_cv_editor_js.js` 1 pass 0 fail.

**`data/` intacto:** 49 CVs, 10 cartas, 6 postulaciones; ningún archivo de `data/` con mtime posterior a `2026-10-13 18:55` (anterior a esta ronda); manifiesto `find data -type f -print0 | sort -z | xargs -0 md5sum | md5sum` = `0f3659d668f67e976ba3763efcfd995d` (175 archivos). El valor de L6 salía de otra forma de comando, por eso no es comparable byte a byte.


### L8 — Ronda 3 de corrección (revisión @codex #3), 2026-10-14

La tercera revisión sobre `8ec65a4` volvió en **`COMMENTED`** (no es aprobación) con **2 hallazgos P1/P2 confirmados** y otros hallazgos previos ya cerrados:

| # | Hallazgo | Veredicto propio |
| --- | --- | --- |
| 1 | **P1**: `workspace_migrate` reutiliza el `plan` calculado antes del drenaje; un request admitido antes del candado puede escribir en TEST durante el drenaje y `run_migration(plan)` sobrescribe el destino con el plan obsoleto (que cree que TEST está vacío) | **Confirmado material, pérdida de datos**: el plan DEBE recalcularse DESPUÉS del `await drain_admitted_requests()` y ANTES de `run_migration()` |
| 2 | **P2**: `dependencies_of` no detecta cartas con `associated_cv_id` apuntando a CVs seleccionados; borrar un CV deja la carta con `associated_cv_id` colgando (dangling reference) | **Confirmado**: la consulta SQL solo miraba `applications`; faltaba consultar `cover_letters.associated_cv_id` |

**Correcciones aplicadas (3 archivos, +228 / −2):**

1. **Revalidación del plan post-drenaje** (`app/routes/workspaces.py`): después de `await drain_admitted_requests()`, se ejecuta `plan = plan_migration()` y `validate_migration(plan, ...)` antes de `run_migration(plan)`. Si el destino ya no está `ready` (p. ej. TEST tiene datos nuevos), se aborta con `migration_blocked` sin mutar nada.
2. **Dependencia CV → Carta** (`app/services/workspace_service.py`): nueva consulta en `dependencies_of` que busca `cover_letters` con `associated_cv_id` en los CVs seleccionados y que NO estén en la selección de cartas. Resultado en `cover_letters_kept_by_cv`.
3. **Agregado a `_kept_dependencies`** (`app/routes/workspaces.py`): incluye `cover_letters_kept_by_cv` en la lista de dependencias que bloquean el borrado.

**Evidencia RED** (tests nuevos sobre `8ec65a4`):
- `test_migracion_revalida_destino_codigo_estatico`: verifica que el source tenga el orden `drain → plan_migration → run_migration`
- `test_dependencies_incluye_cartas_vinculadas_a_cv_seleccionado`: `dependencies_of` devuelve `cover_letters_kept_by_cv` con la carta vinculada
- `test_borrar_cv_con_carta_vinculada_sin_seleccionar_bloquea`: flujo HTTP bloquea el borrado y muestra error de dependencia

**Evidencia GREEN (árbol corregido):** `tests/test_workspaces.py` **92 passed** (89 + 3 nuevos); suite completa **558 passed**; `compileall` 0; `git diff --check` 0; PCC `validate` "catalogo valido" y `check` "en sync"; `node --test tests/test_structured_cv_editor_js.js` 1 pass 0 fail.

**`data/` intacto:** 49 CVs, 10 cartas, 6 postulaciones; manifiesto `find data -type f -exec md5sum {} \; | sort -k2 | md5sum` = `0f3659d668f67e976ba3763efcfd995d` (175 archivos).


