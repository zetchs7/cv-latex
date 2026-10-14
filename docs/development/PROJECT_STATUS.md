# Project Status

<!-- Generado por tools/project_control.py desde docs/development/project_control/catalog.json. No editar a mano: editar el catalogo y ejecutar `python3 tools/project_control.py render`. -->

## Identificacion del proyecto

| Campo | Valor |
| --- | --- |
| Proyecto | CV LaTeX Builder |
| Version estable | 0.9.0 |
| Rama estable | main |
| Rama de integracion | development |
| Ultima verificacion | 2026-10-12 |
| Evidencia de la verificacion | `development` en `9ddaf25`; `main` en `a28d1fd`, sin ancestry de los commits de desarrollo: `97e2577` y `e19ea5a` son alcanzables solo desde `development`. Suite Python 322 passed en host y en Docker con rootfs de solo lectura y sin red; 8 tests JavaScript; `project_control.py validate` y `check` en verde; GitHub Actions en verde sobre cada PR hacia `development`. |

## Ramas: que hay en cada una

`main`, `development` y las ramas `feature/*` son hechos distintos. Confundirlos es la fuente de error mas frecuente de este repositorio, por eso la tabla los separa en lugar de resumirlos en un unico numero de avance.

| Rama | Significado | Estado |
| --- | --- | --- |
| main | Estable publicada. Es la unica que ve un usuario final. | Release publicada, no toca `main` sin autorizacion explicita. |
| development | Integracion validada. Aqui llega lo aprobado. | Integracion abierta. |
| feature/* | Implementacion o correccion acotada en curso. | Se integra por squash merge hacia `development`. |

## Modulos

| Modulo | Rutas | Estado | En development | En main | Evidencia |
| --- | --- | --- | --- | --- | --- |
| Application Tracker | `app/routes/applications.py`, `app/repositories/application_repository.py` | in_main | si | si | CRUD con pipeline de 6 estados. La confirmacion destructiva usa el token fijo `confirm_delete == 'yes'` (`applications.py:201`), mas debil que el criterio de texto exacto de CVs y cartas. |
| Chequeo ATS basico | `app/routes/ats.py`, `app/services/ats_service.py` | in_main | si | si | Score heuristico de 7 criterios, topes 100/84/59 (`ats_service.py:11-12`). Consume la representacion normalizada del CV estructurado. |
| Cartas de presentacion | `app/routes/cover_letters.py`, `app/repositories/cover_letter_repository.py` | in_main | si | si | CRUD con exportacion TEX/PDF. Sin exportacion JSON y sin editor estructurado, a diferencia de los CVs. |
| CV Builder (editor legacy) | `app/routes/cvs.py`, `app/repositories/cv_repository.py` | in_main | si | si | CRUD completo, soft delete con confirmacion por coincidencia exacta de titulo (`cvs.py:458-466`). |
| Dashboard privado | `app/routes/dashboard.py`, `app/templates/` | in_main | si | si | Release v0.9.0 en `cbd10fa`; integrado en `main` via `a28d1fd`. |
| Centro de documentacion | `app/routes/documentation.py`, `app/services/documentation_service.py` | in_main | si | si | Fuentes en `docs/user/` (2) y PDFs servidos en `app/static/docs/` (2) coinciden 1:1 y estan versionados. |
| Exportaciones PDF/TEX/JSON | `app/services/export_service.py`, `app/services/pdf_service.py`, `app/services/latex_service.py` | in_main | si | si | Golden fixtures en `tests/fixtures/legacy_tex_a28d1fd/` prueban identidad byte a byte del TEX legacy contra el baseline `a28d1fd`. Path traversal bloqueado (`export_service.py:379`). |
| Importacion JSON de CVs | `app/routes/cvs.py:160`, `app/services/export_service.py` | in_main | si | si | Acepta schema 1 y 2, limite de 520 KB en dos capas (streaming por chunks `export_service.py:68` y guard de tamano `:265`). No existe importacion de PDF, DOCX, LaTeX ni Markdown. |
| Project Control Center | `tools/project_control.py`, `docs/development/project_control/catalog.json` | in_development_branch | no | no | Rama `feature/project-control-center`, sin publicar por instruccion explicita. Diseno en `docs/adr/ADR-0005-project-control-center.md`. |
| Editor estructurado de CV (schema 2) | `app/routes/cvs.py:71,367`, `app/services/structured_cv_*.py`, `app/validations/structured_cv_validations.py` | in_development | si | no | PR #16 squash-mergeado en `97e2577`. Sin version, release ni tag: no publicado. ADR-0003 lo declara 'implementada sin publicar'. |
| Aislamiento de la suite de pruebas | `tests/conftest.py`, `app/database.py`, `tests/test_test_isolation.py` | in_development | si | no | PR #17 squash-mergeado en `e19ea5a`. Aislamiento fail-closed en codigo con manifiesto `(size, mtime_ns)` comparado en `pytest_sessionfinish`. |
| Entornos y datos (MODO REAL / MODO PRUEBAS) | `app/environments.py`, `app/workspace_middleware.py`, `app/routes/workspaces.py`, `app/services/workspace_service.py`, `app/templates/workspaces/` | in_development | si | no | Rama `feature/real-test-workspaces` desde `development` `ea4c979`; suite completa 533 passed. Sin merge: la migracion de los datos actuales requiere autorizacion explicita. |

## Riesgos abiertos

| ID | Riesgo | Severidad | Mitigacion | Evidencia |
| --- | --- | --- | --- | --- |
| RSK-001 | 14 endpoints POST forjables desde cualquier sitio web | high | Ver SEC-001 (P0). Propuesta completa en `docs/development/SECURITY_HARDENING_PROPOSAL.md`. | Cero `add_middleware` en `app/main.py:26-39`. Un POST con `Form(...)` es una simple request: sin preflight, el navegador lo envia y la app lo ejecuta. IDs secuenciales permiten iterarlos. |
| RSK-002 | Drift entre la documentacion y el estado real del repositorio | medium | `tools/project_control.py check` detecta la deriva del backlog. La deriva en README e historial requiere correccion manual: DOC-001. | `README.md:8` declara `v0.8.0` como ultimo tag cuando existe `v0.9.0` en `cbd10fa`; `PROJECT_HISTORY_ROLLBACK.md:61` afirma que `main` y `development` estan en `cbd10fa` y `development` esta en `e19ea5a`; `README.md:240-251` lista 11 de los 22 archivos de test. |
| RSK-003 | La suite de 248 pruebas solo corre localmente | medium | Pipeline que ejecute la suite en la imagen del proyecto. Ver QLT-001. | No existe `.github/`, ni `pytest.ini`, ni `pyproject.toml`. La unica via automatizada es `docker compose exec app python -m pytest`. |
| RSK-004 | `development` esta 2 commits adelante de `main`: la etapa 9.x no esta publicada | medium | Decidir y ejecutar el release. Ver REL-001. | `git rev-list --count main..development` = 2 (`97e2577`, `e19ea5a`). `main` sigue en `a28d1fd` y solo contiene la release v0.9.0. |
| RSK-005 | `CURRENT_SCHEMA_VERSION` es un rotulo, no un control de flujo de migraciones | medium | Esquema de migraciones por pasos cuando la proxima migracion no sea una simple columna. Ver DBV-001. | `app/database.py:157-163` concentra toda la migracion en `migrate_cvs_table()`, idempotente por diseno pero sin historial ni orden. La version se sobreescribe en `app_metadata` (`database.py:182-191`). |
| RSK-006 | La version de release de la documentacion esta fijada por constante | low | Derivar la constante de `VERSION` o de `APP_VERSION`. Ver DOC-002. | `documentation_service.py:19` fija `DOCUMENTATION_RELEASE_VERSION = 'v0.9.0'` y la fecha en `:21`; un cambio de version no las actualiza. |
| RSK-007 | Sin formatters disponibles: el control de formato es solo el diff check | low | Adoptar `black` y `ruff` como dependencias de desarrollo. Ver QLT-003. | `DEVELOPMENT_LOG.md:36-38`: 'black y ruff no estan disponibles en host ni en la imagen'. |
| RSK-008 | Backup documentado puede producir una copia inconsistente | medium | Usar `sqlite3 data/app.db ".backup"` o detener la app antes de copiar. Ver OPS-001/SEC-003. | `README.md:149` y `docs/user/WEB_USAGE_MANUAL.md` hacen `cp data/app.db` con la app corriendo. |
| RSK-009 | Migracion de la base historica sin ejecutar | medium | `plan_migration()` audita sin mutar y se niega a sobrescribir un destino ocupado; la ejecucion exige la frase `MIGRAR`, genera un checkpoint con la API de backup de SQLite, renombra la base historica fuera del camino vivo, marca `.environments-migrated` y revierte ante cualquier fallo. Ese retiro impide que quede un tercer espacio de trabajo: el arranque deja de inicializar la raiz y las rutas sin prefijo redirigen a MODO REAL. No se ejecuta sin autorizacion explicita de Franco. | `docs/development/REAL_TEST_WORKSPACES.md` §7; `tests/test_workspaces.py::test_plan_de_migracion_no_modifica_nada` y `::test_migracion_con_destino_ocupado_no_toca_nada`. |

## Backlog en un vistazo

| Prioridad | Tareas |
| --- | --- |
| P0 | 1 |
| P1 | 5 |
| P2 | 6 |
| P3 | 8 |

| Estado | Tareas |
| --- | --- |
| backlog | 13 |
| ready | 4 |
| in_progress | 2 |
| blocked | 0 |
| done | 1 |
| cancelled | 0 |

## Proxima tarea concreta

- **SEC-001** (P0) TrustedHostMiddleware y proteccion contra DNS rebinding
  - Siguiente paso: Decidir si se agrega CSRF en la misma entrega; ver SEC-002.
- **REL-001** (P1) Publicar v0.10.0 con la etapa 9.x
  - Siguiente paso: Franco debe decidir la version objetivo y si el release incluye tambien el Project Control Center.
- **SEC-002** (P1) Proteccion CSRF para formularios POST
  - Siguiente paso: Confirmar con Franco si el modelo de uso sigue siendo estrictamente local antes de implementar.
- **SEC-004** (P2) Unificar la confirmacion destructiva del tracker con el criterio de los demas modulos
  - Siguiente paso: Implementar siguiendo el patron ya establecido en `tests/test_confirmation_modal_security.py`.
