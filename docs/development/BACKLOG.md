# Backlog

<!-- Generado por tools/project_control.py desde docs/development/project_control/catalog.json. No editar a mano: editar el catalogo y ejecutar `python3 tools/project_control.py render`. -->

## Como leer este backlog

- **Origen** distingue de donde sale la tarea: `Solicitud de Franco`, `Defecto verificado`,
  `Recomendacion de ingenieria` o `Deuda documentada`. Una recomendacion de ingenieria
  **no** es un requisito aprobado.
- **Aprobado** indica si Franco aprobo la tarea. `no` significa propuesta.
- **Estado** `done` significa cerrada; `cancelled` significa descartada con motivo.

## Tareas abiertas

### AIX-001 — Integraciones asistidas por IA

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | project_control |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `CHANGELOG_GENERAL.md:95` y `PROJECT_HISTORY_ROLLBACK.md:62` lo dejan fuera del alcance de v0.9.0; `README.md:451` lo marca como fuera de alcance actual. |
| Proxima accion | Ninguna. Es la linea de trabajo mas abierta y la de mayor riesgo de privacidad. |

Se ha mencionado IA real, integraciones con OpenAI API, paletas funcionales y thumbnails. Ninguna esta aprobada ni implementada.

**Criterios de aceptacion**

- [ ] Franco define alcance, limites de datos y proveedor
- [ ] Existe una decision sobre si el CV del usuario puede enviarse a un servicio externo

### ATS-001 — UX residual del modulo ATS

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | ats |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `CHANGELOG_GENERAL.md:95` lo registra como backlog de etapas futuras; `README.md:441-451` describe Etapa 8.1.3 y 8.2. |
| Proxima accion | Sin fecha: es mejora estetica, no riesgo. |

El modulo ATS funciona y esta verificado. Lo pendiente es suica visual: selector de paletas, miniaturas reales de PDF y evolucion visual de cards.

**Criterios de aceptacion**

- [ ] El alcance visual esta acotado y aprobado antes de implementar
- [ ] No cambia el scoring, los pesos ni los criterios existentes
- [ ] El criterio de aceptacion es visual y queda validado en navegador real

### CLEAN-001 — Limpieza del CV id 49 y artefactos de validacion en data/

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Defecto verificado |
| Aprobado por Franco | no |
| Modulo | database |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `data/app.db` con 49 CVs verificado integro; 175 archivos en `data/`, de los cuales 107 en `exports/` y 37 en `documentation-qa/` son artefactos de validacion. |
| Proxima accion | Esperar la decision de Franco; es una escritura irreversible sobre datos ficticios. |

`data/app.db` contiene un CV id 49 creado por una corrida de pruebas que escribio sobre la base real. El aislamiento quedo corregido y verificado, pero el registro y unos 150 artefactos de exportacion y validacion siguen en disco.

**Criterios de aceptacion**

- [ ] Franco decide si el CV 49 se borra o se conserva como evidencia
- [ ] `data/` queda con un estado conocido y documentado
- [ ] La decision queda registrada en LESSONS_LEARNED

### CV-001 — Importar Curriculum Vitae desde PDF

| Campo | Valor |
| --- | --- |
| Prioridad | P1 |
| Estado | backlog |
| Origen | Solicitud de Franco |
| Aprobado por Franco | si |
| Modulo | imports_json |
| Issue de GitHub | #14 |
| Depende de | — |
| Evidencia | GitHub Issue #14, creado por `zetchs7` el 2026-06-13. Requisitos transcritos sin alterar. |
| Proxima accion | Aprobar la propuesta de arquitectura y el alcance de OCR antes de implementar. |

Permitir subir un CV en PDF, extraer e interpretar su contenido y cargarlo en el modelo interno del proyecto. El PDF es fuente de datos, nunca documento final: se muestra una pantalla de revision editable y el CV se genera con las plantillas propias. El sistema no debe inventar datos ni descartar silenciosamente informacion que no pudo clasificar.

**Criterios de aceptacion**

- [ ] Existe el boton 'Importar CV desde PDF' en la seccion Curriculum Vitae
- [ ] El usuario sube un PDF y la app valida formato, tamano y legibilidad
- [ ] Se extrae texto correctamente de un PDF con texto seleccionable
- [ ] Se detectan y estructuran datos personales, experiencia, educacion, skills y resumen
- [ ] La informacion se mapea al modelo interno del CV
- [ ] Existe una pantalla de revision antes de guardar, con campos editables
- [ ] Existe la seccion visible 'Campos con dudas o informacion incompleta'
- [ ] Existe la seccion visible 'Informacion no clasificada'
- [ ] El usuario puede corregir, completar, mover, descartar o confirmar campos dudosos
- [ ] La app no inventa informacion faltante ni elimina informacion sin mostrar
- [ ] El CV final se genera con las plantillas propias del proyecto
- [ ] Hay validaciones para PDF vacio, corrupto, protegido por contrasena y escaneado sin OCR
- [ ] Los temporales del archivo subido se eliminan tras el procesamiento
- [ ] Existen tests para el flujo y para casos ambiguos o incompletos
- [ ] La funcionalidad queda documentada

### DBV-001 — Migraciones versionadas por pasos

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | structured_cv |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `app/database.py:157-163` y `app/database.py:182-191`. |
| Proxima accion | No es urgente: activar antes de la siguiente migracion que no sea una columna. |

Toda la migracion vive en una unica funcion idempotente que anade columnas. Funciona hoy; no escala a transformaciones de datos ni a una secuencia de versiones, y la constante de version es un rotulo que no controla el flujo.

**Criterios de aceptacion**

- [ ] Cada migracion tiene version y es idempotente
- [ ] El historial de versiones aplicadas es consultable en `app_metadata`
- [ ] Una base existente migra al estado actual sin perder datos
- [ ] Existe test de migracion desde cada version previa

### DOC-001 — Corregir el drift de README y del historial de rollback

| Campo | Valor |
| --- | --- |
| Prioridad | P2 |
| Estado | in_progress |
| Origen | Deuda documentada |
| Aprobado por Franco | no |
| Modulo | docs |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | Corregido: `README.md` bloque 'Estado actual' (antes declaraba `v0.8.0` como ultimo tag y un release en preparacion ya cerrado) y nueva seccion 'Gobierno del proyecto'. Pendiente: `README.md:240-251` lista 11 de los 22 archivos de test, y `PROJECT_HISTORY_ROLLBACK.md:61` afirma que `main` y `development` estan en `cbd10fa`. |
| Proxima accion | Corregir el arbol de archivos de test y la afirmacion de sincronizacion del historial de rollback. |

El bloque 'Estado actual' del README ya fue corregido durante la instalacion del Project Control Center, y ahora declara el tag real y la diferencia entre `main` y `development`. Queda corregir el arbol de archivos de test y la afirmacion de sincronizacion del historial de rollback.

**Criterios de aceptacion**

- [ ] El bloque 'Estado actual' del README declara el ultimo tag estable real y la diferencia entre `main` y `development`
- [ ] El README enlaza al `PROJECT_STATUS.md` como fuente del estado completo
- [ ] El arbol de archivos de test esta completo o se reemplaza por una referencia al directorio
- [ ] `PROJECT_HISTORY_ROLLBACK.md` no afirma sincronizacion donde no la hay
- [ ] No se reescribe historia: se corrigen afirmaciones obsoletas y se conservan las que tienen valor de auditoria

### DOC-002 — Derivar la version de release de la documentacion de la version del proyecto

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | documentation |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `app/services/documentation_service.py:19-21`. |
| Proxima accion | Resolver junto con REL-001 para no tocar dos veces la misma constante. |

`DOCUMENTATION_RELEASE_VERSION` y su fecha estan fijadas por constante y no se actualizan al cambiar la version del proyecto, lo que puede rotular PDFs servidos con una version vieja.

**Criterios de aceptacion**

- [ ] La version mostrada en la documentacion deriva de una fuente unica
- [ ] Cambiar la version del proyecto actualiza la documentacion sin editar dos lugares
- [ ] Existe test que detecta la desincronizacion

### EDT-001 — Drag and drop en el editor estructurado

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | structured_cv |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `CHANGELOG_GENERAL.md:30-36` lo lista como 'no incluido'; `MODULE_INDEX.md` describe el editor sin drag and drop. |
| Proxima accion | Solo si Franco lo pide; es mejora, no bloqueo. |

El editor reordena items con botones `Subir`/`Bajar` y renumeracion automatica. El drag and drop quedo explicitamente fuera del alcance hasta ahora.

**Criterios de aceptacion**

- [ ] El alcance y la decision estan aprobados por Franco
- [ ] La reordenacion por botones se conserva como alternativa accesible

### IMP-001 — Exportaciones e importaciones mas amplias que JSON

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | imports_json |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `export_service.py` limita la whitelist a `.tex`, `.pdf` y `.json` (`:396-397`). |
| Proxima accion | Ninguna hasta que exista pedido explicito. |

Hoy solo hay exportacion e importacion JSON para CVs. DOCX, Markdown y otros formatos quedan como posibilidad, no como requisito.

**Criterios de aceptacion**

- [ ] El formato a agregar esta definido por Franco
- [ ] El roundtrip a CV editable esta cubierto con tests

### OPS-001 — Procedimiento de backup documentado pero inseguro y sin verificar

| Campo | Valor |
| --- | --- |
| Prioridad | P2 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | database |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `README.md:112-151` documenta backup y restore con `cp data/app.db backups/app-...db`. Copiar el archivo de SQLite en caliente puede capturar un estado a medio escribir. El unico respaldo existente en disco es `data/app.db.stage9.1-pre-migration.bak`, hecho a mano y sin procedimiento asociado. |
| Proxima accion | Decidir la forma de backup segura, ejecutarla y verificar que la restauracion devuelve una base integra con `PRAGMA integrity_check`. |

El procedimiento de backup y restore ya existe en el README, asi que no falta documentacion. El problema es otro y es mas serio: el procedimiento documentado copia `data/app.db` con `cp` mientras la aplicacion puede estar escribiendo, lo que puede producir una copia inconsistente. La forma segura es `.backup` de SQLite o detener la app antes de copiar. Ademas el procedimiento no se ha verificado ejecutandolo y no cubre el escenario de respaldo previo a una migracion de esquema.

**Criterios de aceptacion**

- [ ] El procedimiento documentado usa una forma de copia consistente de SQLite, no `cp` con la app escribiendo
- [ ] El procedimiento indica si la app debe estar detenida durante la copia
- [ ] La restauracion se verifica ejecutandola y comprobando `PRAGMA integrity_check` sobre la copia restaurada
- [ ] Existe un procedimiento de respaldo previo a una migracion de esquema
- [ ] La documentacion de usuario refleja el procedimiento corregido

### PCC-001 — Project Control Center v1

| Campo | Valor |
| --- | --- |
| Prioridad | P1 |
| Estado | in_progress |
| Origen | Solicitud de Franco |
| Aprobado por Franco | si |
| Modulo | project_control |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `docs/adr/ADR-0005-project-control-center.md`, rama `feature/project-control-center`. |
| Proxima accion | Completar inventario del backlog, plantillas de issues, tests e integracion documental; cerrar con commits locales sin publicar. |

Sistema interno de gobierno del proyecto: catalogo canonico en JSON, herramienta de validacion con Python standard library, documentos centrales generados y guia de gobernanza de GitHub. Es una herramienta para gobernar el desarrollo, no una funcionalidad del producto final.

**Criterios de aceptacion**

- [ ] `python3 tools/project_control.py validate` pasa sin errores ni advertencias
- [ ] `python3 tools/project_control.py check` no modifica ningun archivo y falla ante deriva
- [ ] El catalogo detecta IDs duplicados, dependencias inexistentes, ciclos, estados y prioridades invalidas
- [ ] PROJECT_STATUS.md, BACKLOG.md y ROADMAP.md se generan de forma determinista desde el catalogo
- [ ] Los documentos distinguen requisito aprobado de propuesta de ingenieria
- [ ] Los tests nuevos pasan y no escriben en `data/` ni en `app/static/docs/`

### QLT-001 — Pipeline que ejecute la suite en la imagen del proyecto

| Campo | Valor |
| --- | --- |
| Prioridad | P2 |
| Estado | ready |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | tests_isolation |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | Ausencia de `.github/`; `requirements.txt` ya fija `pytest 8.3.4`. |
| Proxima accion | Decidir si se habilita GitHub Actions o si la suite queda deliberadamente local. |

Las 248 pruebas solo corren localmente. No existe `.github/`, ni configuracion de pytest, y la unica via automatizada es ejecutar pytest dentro del contenedor.

**Criterios de aceptacion**

- [ ] La suite completa se ejecuta automaticamente sobre cada PR hacia `development`
- [ ] El pipeline usa el aislamiento de datos integrado y no monta `./data` del host
- [ ] El resultado es visible en el PR
- [ ] El pipeline no requiere secretos

### QLT-002 — Reejecutar los flujos de navegador real del editor estructurado

| Campo | Valor |
| --- | --- |
| Prioridad | P2 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | structured_cv |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `tests/test_structured_cv_editor_js.js:413,511,556,601`; `DEVELOPMENT_LOG.md:36-38` registra que no se reejecutaron. |
| Proxima accion | Requiere la app levantada; usar el contenedor efimero y puerto de loopback ya validados. |

Los 4 flujos CDP sobre Chromium existen en `tests/test_structured_cv_editor_js.js` pero no se reejecutaron en la validacion final de la etapa 9.x. La validacion automatizada del editor fue 31 pruebas de servicio y 35 de rutas HTTP.

**Criterios de aceptacion**

- [ ] Los 4 flujos CDP se ejecutan contra la app en ejecucion y pasan
- [ ] El resultado queda registrado con el commit validado
- [ ] Si fallan, se corrige la causa o se documenta por que no aplica

### QLT-003 — Adoptar black y ruff como dependencias de desarrollo

| Campo | Valor |
| --- | --- |
| Prioridad | P3 |
| Estado | backlog |
| Origen | Deuda documentada |
| Aprobado por Franco | no |
| Modulo | tests_isolation |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `DEVELOPMENT_LOG.md:36-38`. |
| Proxima accion | Medir cuanto reformateo exigiria antes de decidir. |

No hay formatters ni linters disponibles en el host ni en la imagen. El control de formato queda cubierto solo por el diff check CRLF-aware, que detecta ruido de fin de linea pero no estilo.

**Criterios de aceptacion**

- [ ] `black` y `ruff` estan declarados como dependencias de desarrollo
- [ ] El lint pasa en el estado actual sin reformatear el historial
- [ ] El pipeline ejecuta el lint

### REL-001 — Publicar v0.10.0 con la etapa 9.x

| Campo | Valor |
| --- | --- |
| Prioridad | P1 |
| Estado | ready |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | docs |
| Issue de GitHub | — |
| Depende de | DOC-001 |
| Evidencia | `git rev-list --count main..development` = 2 (`97e2577`, `e19ea5a`). `VERSION` sigue en `0.9.0` y `main` en `a28d1fd`. |
| Proxima accion | Franco debe decidir la version objetivo y si el release incluye tambien el Project Control Center. |

`development` esta 2 commits adelante de `main`: el editor estructurado y el aislamiento de pruebas estan integrados pero sin version, release ni tag. Un usuario que solo use `main` no ve ninguna de las dos mejoras.

**Criterios de aceptacion**

- [ ] Version alineada en `VERSION`, `app/main.py`, `Dockerfile`, `docker-compose.yml`, `.env.example` y README
- [ ] Suite completa en verde sobre el commit a publicar
- [ ] PDFs de documentacion regenerados si cambio su fuente o su renderer
- [ ] CHANGELOG_GENERAL actualizado con la entrada del release
- [ ] `main` y `development` sincronizadas segun la estrategia acordada
- [ ] Tag creado solo con autorizacion explicita

### SEC-001 — TrustedHostMiddleware y proteccion contra DNS rebinding

| Campo | Valor |
| --- | --- |
| Prioridad | P0 |
| Estado | ready |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | dashboard |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | Informe de amenazas 2026-10-12: `app/main.py:26-39` sin add_middleware; 14 rutas POST listadas en `app/routes/`; cero tokens CSRF en ninguna de las 8 plantillas con method=post; AUTOINCREMENT en `app/database.py:195`. |
| Proxima accion | Decidir si se agrega CSRF en la misma entrega; ver SEC-002. |

La app no registra ningun middleware: cero add_middleware en todo el repo. Sus 14 endpoints POST son ejecutables mediante request forgery desde cualquier sitio web, porque un POST con Form(...) o urlencoded es una simple request que no dispara preflight y el navegador la envia. El atacante obtiene creacion y modificacion arbitraria de CVs, cartas y postulaciones; los ids son enteros secuenciales, asi que puede iterar /cvs/1/edit, /cvs/2/edit sin leer nada. El borrado queda protegido por la coincidencia exacta de texto, que un atacante ciego no conoce.

**Criterios de aceptacion**

- [ ] La app valida el encabezado `Host` y rechaza hosts no permitidos
- [ ] Existe un test de regresion que demuestra que un host ajeno es rechazado
- [ ] El bind por defecto sigue siendo `127.0.0.1`
- [ ] La limitacion esta documentada en README y en la documentacion de usuario

### SEC-002 — Proteccion CSRF para formularios POST

| Campo | Valor |
| --- | --- |
| Prioridad | P1 |
| Estado | ready |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | dashboard |
| Issue de GitHub | — |
| Depende de | SEC-001 |
| Evidencia | Grep de `csrf\|Depends(\|Security(\|middleware` sobre `app/**/*.py` no devuelve resultados. |
| Proxima accion | Confirmar con Franco si el modelo de uso sigue siendo estrictamente local antes de implementar. |

Sin TrustedHostMiddleware, un DNS rebinding da lectura total de la app: el atacante controla el DNS de su dominio con TTL bajo, la victima visita el sitio, el JS rebindea a 127.0.0.1, y el navegador conecta desde la maquina de la victima a su propia loopback. El bind 127.0.0.1 NO protege: la restriccion de interfaz no controla peticiones que el propio navegador origina localmente. La SOP se pasa de largo porque el origin sigue siendo el dominio del atacante, que ahora resuelve a loopback, y el JS puede leer las respuestas: exfiltracion de CVs completos.

**Criterios de aceptacion**

- [ ] Toda ruta POST exige un token CSRF valido
- [ ] Los formularios incluyen el token
- [ ] Un POST sin token o con token invalido devuelve 403
- [ ] Existen tests de regresion para POST legitimo, POST sin token y POST con token ajeno

### SEC-003 — Estrategia de autenticacion si la app se expone fuera de localhost

| Campo | Valor |
| --- | --- |
| Prioridad | P1 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | dashboard |
| Issue de GitHub | — |
| Depende de | SEC-002 |
| Evidencia | `AGENTS.md` declara el uso local sin login y prohibe exponer fuera de localhost sin revisar auth, permisos, CSRF, CORS, headers y rate limits. |
| Proxima accion | Solo se activa si Franco decide cambiar el modelo de despliegue. |

OPS-001 cubria el riesgo de backup inconsistente: el procedimiento documentado copia `data/app.db` con `cp` mientras la app corre, y SQLite en journal mode default puede producir una copia a medio escribir. El RESTORE si es consistente porque exige detener la app; el backup no. La forma correcta es `sqlite3 data/app.db ".backup"` o detener la app antes de copiar.

**Criterios de aceptacion**

- [ ] Existe una decision registrada sobre si la app puede exponerse fuera de localhost
- [ ] Si se expone, el plan de autenticacion esta escrito y aprobado antes de tocar el bind

### SEC-004 — Unificar la confirmacion destructiva del tracker con el criterio de los demas modulos

| Campo | Valor |
| --- | --- |
| Prioridad | P2 |
| Estado | ready |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | applications |
| Issue de GitHub | — |
| Depende de | — |
| Evidencia | `applications.py:201` compara contra `confirm_delete == 'yes'`; `cvs.py:458-466` y `cover_letters.py:178` exigen coincidencia exacta. |
| Proxima accion | Implementar siguiendo el patron ya establecido en `tests/test_confirmation_modal_security.py`. |

CVs y cartas exigen confirmacion por coincidencia exacta del texto a eliminar. El Application Tracker acepta un token fijo, que es mas debil y facil de disparar por error.

**Criterios de aceptacion**

- [ ] El tracker exige confirmar con la misma coincidencia exacta que CVs y cartas
- [ ] Un POST con un token fijo deja de eliminar el registro
- [ ] Existe test de regresion para el caso negativo

### SEC-005 — Binding explicito y cap de tamano de request

| Campo | Valor |
| --- | --- |
| Prioridad | P2 |
| Estado | backlog |
| Origen | Recomendacion de ingenieria |
| Aprobado por Franco | no |
| Modulo | dashboard |
| Issue de GitHub | — |
| Depende de | SEC-001 |
| Evidencia | `docker-compose.yml:13`, `app/database.py:195`; informe de amenazas 2026-10-12. |
| Proxima accion | Se incluye con SEC-001 en la misma entrega de hardening. |

`APP_HOST_BIND=0.0.0.0` deja la app accesible desde toda la LAN sin autenticacion, con lectura y escritura total. Ademas no hay cap global de tamano de body: un POST urlencoded enorme se parsea completo en memoria antes de la validacion por campo. El peligro de puerto esta documentado, pero nada lo advierte cuando se cambia el bind.

**Criterios de aceptacion**

- [ ] Un bind distinto de 127.0.0.1 produce una advertencia visible al arrancar
- [ ] Existe un cap de tamanio de request aplicado antes del parseo completo

## Tareas cerradas

### Cerradas

_Sin tareas cerradas registradas en el catalogo._
