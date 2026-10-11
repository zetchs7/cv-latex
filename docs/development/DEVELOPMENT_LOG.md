# Development Log


## Cierre tecnico previo al PR - politica EOL, navegacion del editor, documentacion y compatibilidad TEX

- Fecha: 2026-10-10
- Rama: `feature/structured-cv-complete` (commits locales, sin push ni PR)
- Objetivo: cerrar los pendientes P2 detectados tras la auditoria y la correccion P0/P1, y agregar la prueba de compatibilidad que faltaba.
- Alcance ejecutado:
  - Politica de finales de linea: nuevo `.gitattributes` con `* text=auto eol=lf` y binarios declarados. Sin renormalizar el historico y sin tocar la configuracion de Git. Los 79 archivos con diferencias solo-CRLF quedan fuera y siguen byte-identicos a `a28d1fd`.
  - Navegacion: las acciones "Editar" del listado de CVs y de las vistas de ATS apuntan al editor estructurado o al legacy segun el tipo de CV, sin saltos de redireccion. Las guardas de backend y la proteccion P0 quedan intactas.
  - Documentacion: `MODULE_INDEX.md`, `ADR-0003`, `CHANGELOG_GENERAL.md` y `CV_BUILDER_CORE.md` alineados con la implementacion real, siempre como feature no publicada. El ADR conserva sus decisiones originales y solo cambia su estado.
  - Compatibilidad TEX legacy: fixtures generados desde `a28d1fd` y prueba de identidad byte a byte en las cuatro plantillas, con verificacion de que el guard detecta una diferencia real.
- Evidencia (CMD-085 a CMD-089): suite completa `207 passed, 1 warning`, JavaScript `8 pasan`, `compileall exit 0`, ambos diff check en `exit 0`, y hashes TEX identicos entre baseline y codigo vigente en las cuatro plantillas.
- Pendientes que no se tocaron: enlaces de edicion en `ats/index.html` y cualquier construccion de URLs en `app/static/js/app.js` (fuera de alcance, sin impacto en datos porque las guardas de backend siguen activas); normalizacion historica de EOL como tarea independiente; y la revision independiente de la feature, que sigue sin realizarse.

## Cierre T6 - verificacion funcional, documental y de integracion de Feature 1

- Fecha: 2026-10-10
- Rama: `feature/structured-cv-complete` (sin commits por restriccion explicita del usuario)
- Contexto: T6 quedo inconclusa porque el proveedor NVIDIA fallo por desconexiones y el verificador `gentle-ai-verify` devolvio salida corrupta sin ejecutar herramientas. CMD-072 determino que las descargas finales existentes NO tenian prueba admisible de correspondencia con el workspace actual. La sesion de cierre ejecuto los checks faltantes directamente, sin repetir ninguna tarea cerrada.
- Modulos afectados en este cierre: `docs/user/WEB_USAGE_MANUAL.md` (una linea de prosa), `app/static/docs/*.pdf` (regeneracion), `docs/development/COMMAND_LOG.md`, `docs/development/MVP_VALIDATION.md` y el documento ODD. Sin cambios en codigo de aplicacion, renderer ni plantillas.
- Alcance ejecutado:
  - Recuperacion de estado: rama en `a28d1fd` sin staged changes, 108 archivos tracked modificados (27 con diferencia real de contenido y 81 reescrituras solo-CRLF preexistentes), 11 untracked. La evidencia intermedia en `/tmp` se habia perdido por limpieza de `/tmp`; el contenedor `cv-t6-correction-http` ya no existia.
  - Verificacion funcional sobre el estado final: suite completa `180 passed, 1 warning in 2.65s` y reejecutada tras la correccion final con `180 passed, 1 warning in 2.53s`; `compileall` exit 0; `git -c core.whitespace=cr-at-eol diff --check` exit 0; tests unitarios Node del editor `8 pasaron, 0 fallaron`.
  - Prueba HTTP admisible: runtime aislado con el workspace montado en solo lectura, tmpfs de datos y puerto `127.0.0.1:8134`. `/health`, las tres rutas de documentacion y ambos PDFs respondieron 200, y el SHA256 de cada PDF descargado fue IDENTICO al del archivo en disco. Esto cierra el hueco explicitamente declarado en CMD-072.
  - Determinismo por contenido: reconstruir ambos PDFs desde las fuentes actuales produce texto extraido IDENTICO al de los PDFs del workspace. El hash de bytes difiere entre ejecuciones porque pdfTeX embebe `CreationDate`; la equivalencia se prueba por texto, nunca por hash.
  - Defecto preexistente detectado y corregido: el token inline-code `docs/development/CHANGELOG_GENERAL.md` se renderizaba como `docs/development/CHANGELOG_GENERAL.m` (se perdia la `d`) por desbordar el margen derecho. El mismo recorte existe en el PDF de HEAD, por lo que era preexistente de v0.9.0 y no una regresion de Feature 1. Correccion minima de una linea de prosa que separa el nombre de archivo de su carpeta, sin tocar el renderer.
  - Prueba de no-truncamiento: los 62 tokens inline de 14 o mas caracteres de ambas fuentes (25 del manual, 37 de la tecnica) aparecen completos en la capa de texto de los PDFs; 0 recortados.
  - Prueba visual: 18 PNGs generados con `pdftoppm -png -r 100` desde los bytes servidos por HTTP e inspeccionados directamente: portadas, indices poblados, pagina interna con contenido de Feature 1 y cierre de ambos documentos. Sin texto cortado, sin paginas vacias, sin titulos huerfanos, sin solapamientos y sin problemas de contraste.
  - Limpieza: eliminado unicamente `cv-t6-final-http`. `cv_latex_app` quedo `healthy` e intacto; `cv-latex-builder` en `Restarting` es preexistente y ajeno a T6. `./data` nunca se monto ni se escribio.
- Evidencia (CMD-073 a CMD-079).
- Criterio de aceptacion:
  - Suite completa, compile y diff check en verde sobre el estado final; PDFs servidos identicos byte a byte a los del workspace; correspondencia de contenido con las fuentes Markdown probada; documentacion servida sin texto recortado ni paginas defectuosas.
- Pendientes:
  - `black` y `ruff` no estan disponibles en host ni en la imagen: el check de formato queda cubierto solo por el diff check CRLF-aware, sin instalar paquetes.
  - Los flujos de navegador real del editor (4 flujos CDP sobre Chromium) no se reejecutaron: `app/static/js/structured_editor.js` no fue modificado (mtime 2026-10-09 06:20, anterior a todo el trabajo documental de T6) y T6 no altera el comportamiento del editor. La evidencia de T4 sigue siendo aplicable.
  - Commits, push, PR, merge, tag y release siguen diferidos hasta autorizacion explicita.


## Correccion T5 - wrapping de tokens largos ininterrumpidos en renders estructurados

- Fecha: 2026-10-09
- Rama: `feature/structured-cv-complete` (sin commits por restriccion explicita del usuario)
- Objetivo: corregir el desborde del margen derecho en los 4 CV PDF templates con texto estructurado aceptado de tokens largos ininterrumpidos (highlight de 240, URL de 300, rol de 120, etc.), incluyendo el overfull confirmado de 27.71626pt en el header de contacto de modern.
- Modulos afectados: `app/services/structured_cv_rendering.py`, `tests/test_structured_cv_consumers.py`, `tests/test_latex_service.py`, `tests/test_pdf_service.py` y documentacion de desarrollo. Plantillas LaTeX y `latex_service.py` SIN cambios (TEX legacy byte-identico verificado contra HEAD en las 4 plantillas).
- Alcance ejecutado:
  - Wrapping solo-estructurado en `structured_cv_rendering`: `_structured_latex_text` sanitiza con `sanitize_latex_text` y luego interpola el separador confiable `\allowbreak \hspace{0pt plus 0.06em}` SOLO entre atomos ya sanitizados de tokens con 24+ atomos (secuencias de escape TeX cuentan 1 atomo; palabras normales quedan intactas con su silabeo).
  - Seguridad: la sanitizacion es siempre previa; las macros se generan solo desde codigo confiable; `_split_latex_atoms` consume cada secuencia de escape completa (longest match, nunca por dentro), por lo que ninguna macro de corte parte una secuencia TeX ni expone LaTeX crudo del usuario; contenido 100% preservado (el separador no agrega glifos: la macro es penalty de ancho cero, su espacio se consume al tokenizar y el \hspace tiene ancho natural nulo).
  - Dos causas raiz encontradas y cerradas con compilacion real: (1) sin espacio de terminacion la macro absorbe letras siguientes (`\allowbreakt` -> Undefined control sequence, 126 errores en ronda HTTP intermedia; el primer experimento con solo grep de Overfull fue invalido y se documento); (2) lineas sin pegamento propio (token puro) no pueden justificarse sin estiramiento y dejaban restos Overfull de 3.42227pt; el \hspace con estiramiento minimo vuelve factible el corte y el estiramiento aplicado es invisible.
  - Cobertura: nombre, titulo/headline, detalles de contacto, resumen, experiencia (rol/empresa/fechas/ubicacion/resumen/bullets/tecnologias), educacion, skills, certificaciones, idiomas, proyectos, links e informacion adicional; ATS sin macros de corte (scoring intacto); unknown payload sigue sin renderizarse.
- Evidencia (CMD-057 a CMD-071):
  - RED: 4 failed/36 passed en el cuarteto (tokens largos sin oportunidades de corte confiable; token crudo presente) + evidencia objetiva pre-fix de logs pdflatex: Overfull classic 1183.32pt, modern 27.71626pt (header) + 1015.92pt, compact 992.16pt, tech 1022.61pt.
  - GREEN: 40 passed cuarteto enfocado (33 previos + 7 nuevos) y 180 passed / 1 warning preexistente en la suite completa; compileall aislado OK; diff check CRLF-aware exit 0 (44246 lineas flaggeadas del plain check = 106 archivos CRLF preexistentes, 0 mixto); TEX legacy byte-identico contra HEAD.
  - PDFs reales por HTTP en runtime aislado (tmpfs, 127.0.0.1:8126, mismo payload sintetico confirmado defectuoso): 4x HTTP 200 application/pdf; logs de recompilacion: 0 errores, 0 Overfull en las 4 plantillas (Underfull 4/4/0/0 preexistentes identicos al estado previo); pdftotext: 24 marcadores presentes, corrida A*200 completa preservada a traves del wrapping, sin leaks de metadata ni macros visibles, `\end{document}` malicioso neutralizado; ATS HTTP 200 Bueno 100/100; SHA256 registrados; 9 PNGs (todas las paginas) en /tmp/cv-t5-wrap-proof/png con cobertura de tinta (classic 3 paginas: p3 es resto legitimo de Informacion adicional).
- Criterio de aceptacion:
  - Tokens largos aceptados envuelven dentro del margen en las 4 plantillas sin truncar, sin achicar fuentes y sin tocar el camino legacy; preservacion total de caracteres probada por TEX (reconstruccion) y PDF (pdftotext aplanado); seguridad de atomos probada por test de residuo.
- Pendientes: inspeccion visual independiente del padre sobre los 9 PNGs nuevos (el writer no puede ingerir imagenes); verificacion independiente de T5 (checkbox ODD sin marcar); T6 bloqueado hasta ese cierre; commits diferidos hasta autorizacion explicita.

## Etapa T5 - representacion normalizada compartida en LaTeX/PDF y ATS

- Fecha: 2026-10-09
- Rama: `feature/structured-cv-complete` (sin commits por restriccion explicita del usuario)
- Objetivo: integrar la representacion normalizada unica (`resolve_normalized_cv`) en TEX/PDF (4 plantillas) y ATS basico, con fallback legacy integral sin mezcla, orden consistente, escape LaTeX robusto y scoring ATS exactamente igual al existente.
- Modulos afectados: `app/services/structured_cv_rendering.py` (nuevo), `app/services/latex_service.py`, `app/services/ats_service.py`, `app/latex_templates/cv/{classic,modern,compact,tech}.tex`, `tests/test_structured_cv_consumers.py` (nuevo), `tests/test_latex_service.py`, `tests/test_ats_service.py`, `tests/test_pdf_service.py` y documentacion de desarrollo.
- Alcance ejecutado:
  - `latex_service.generate_cv_tex_document` resuelve la fuente canonica con `resolve_normalized_cv`: CV estructurado valido renderiza un contexto enriquecido desde las secciones del payload (aun si el snapshot legacy quedo obsoleto); legacy/invalido/stale/futuro usa el camino flat exactamente igual que antes (byte-identidad verificada contra HEAD en las 4 plantillas).
  - Contexto estructurado: nombre, headline (o titulo interno como fallback), email/telefono/ubicacion/links de contacto, resumen, experiencia (rol - empresa, fechas con Presente, ubicacion, resumen, bullets, Tecnologias), educacion (titulo - institucion, fechas, Campo, resumen), skills (label (categoria, nivel)), certificaciones, idiomas, proyectos (link, Tecnologias), links e informacion adicional; metadata interna y claves desconocidas nunca se renderizan (persistencia intacta).
  - Listados ordenados consistentemente por `(order, posicion)` con la misma semantica que el snapshot T2; campos opcionales robustos (items minimos no generan secciones vacias ni entradas huerfanas).
  - Plantillas: rama `entries` (headline/meta/cuerpo/bullets) identica conceptualmente en las 4 con variacion minima de estilo; guardias de agrupacion solo para renders estructurados (`keep_with_next`, `use_needspace`): `\Needspace*{4\baselineskip}` antes de titulos en compact/modern/tech y `\par\nopagebreak` post-colorbox en tech; el TEX legacy queda byte-identico (paquete `needspace` cargado solo en renders estructurados).
  - ATS: `analyze_cv_ats` consume la misma fuente canonica; los 6 campos de scoring derivan del snapshot legacy proyectado (equivalencia canonica exacta con el CV legacy equivalente) y `total_characters` usa la extraccion normalizada completa `build_structured_ats_text` que incluye todo el contenido soportado (incluye solo-estructurados, excluye metadata). Los 7 criterios, pesos, topes, umbrales, estados y resultados legacy quedan intactos.
  - Escape: todo texto estructurado pasa por `sanitize_latex_text`; `\end{document}` malicioso queda tipografiado como texto literal neutralizado y el PDF compila completo.
- Evidencia (CMD-045 a CMD-056):
  - RED: 13 failed/20 passed en el cuarteto enfocado (contenido solo-estructurado ausente en TEX/PDF/ATS; ATS leia columnas planas obsoletas).
  - GREEN: 33 passed cuarteto enfocado; suite completa 173 passed (155 base + 18 nuevas), 1 warning preexistente; compileall aislado OK; `git diff --check` CRLF-aware: 106 archivos pre-existentes CRLF completos, 0 lineas non-CRLF, archivos nuevos limpios.
  - PDFs reales por HTTP en runtime aislado (tmpfs, 127.0.0.1:8125): 4x HTTP 200 application/pdf, 2 paginas A4 cada uno, pdftotext con todos los marcadores y sin leaks de metadata; SHA256 registrados en COMMAND_LOG; PNGs de portada y pagina interna en /tmp/cv-t5-proof/png con cobertura de tinta registrada.
  - Paginacion: huérfano real de titulo "Links" en compact detectado en la primera ronda; experimentos deterministas demostraron que `\\*` y `\par\nobreak` no evitan el corte titulo->itemize (`\@beginparpenalty`) y que `\Needspace*` si; tras el fix las 4 plantillas cortan limpio (verificado por texto por pagina).
- Criterio de aceptacion:
  - CV estructurado valido renderiza todo el contenido soportado desde el payload canonico en las 4 plantillas; legacy y fallbacks producen exactamente el TEX/ATS previo; ATS equivalente legacy vs estructurado convertido; sin criterios de scoring nuevos.
- Pendientes: verificacion independiente del padre (visual de PNGs incluida, el modelo de este writer no puede inspeccionar imagenes); T6 (cierre, docs, integracion); commits diferidos hasta autorizacion explicita.

## Etapa T4 - editor estructurado completo con orden de items

- Fecha: 2026-10-09
- Rama: `feature/structured-cv-complete` (sin commits por restriccion explicita del usuario)
- Objetivo: implementar el editor estructurado completo (creacion y edicion aditivas) con CRUD y orden de items, validacion 100% servidor, bootstrap seguro y conversion legacy explicita, sin drag/drop, IA, live preview ni cambios de scoring.
- Modulos afectados: `app/services/structured_cv_editor_service.py` (nuevo), `app/routes/cvs.py`, `app/templates/cvs/structured_form.html` (nuevo), `app/templates/cvs/detail.html`, `app/templates/cvs/index.html`, `app/static/js/structured_editor.js` (nuevo), `app/static/css/app.css`, `tests/test_structured_cv_editor.py` (nuevo), `tests/test_structured_cv_editor_js.js` (nuevo) y documentacion de desarrollo.
- Alcance ejecutado:
  - Rutas aditivas `GET/POST /cvs/new/structured` y `GET/POST /cvs/{cv_id}/structured-edit` declaradas antes de las rutas dinamicas; los flujos legacy quedan intactos y verificados.
  - Bootstrap canonico via `resolve_normalized_cv`: un CV estructurado valido se edita desde su payload (nunca se regenera desde campos planos); legacy/invalido/stale/futuro bootstrapea integramente desde campos legacy con advertencia explicita de conversion y limites por campo.
  - Contrato de envio unico: `title` + `structured_payload` (JSON). El servidor rechaza payload ausente (mensaje de JavaScript requerido), no-JSON, no-objeto o mayor a 512 KB; valida con el contrato v2 y el write bundle T2 y persiste atomicamente; sin validacion solo-cliente y sin escrituras parciales.
  - Preservacion total de claves desconocidas de payload, secciones e items a traves de ediciones, ordenes y envios fallidos; el rerender 422 conserva exactamente lo ingresado con errores accionables en espanol (codigos v2 traducidos y errores de snapshot con etiquetas en espanol).
  - Metadata server-owned mostrada como informacion interna y re-estampada deliberadamente (`structured_editor`) al guardar; nunca oculta ni destruida.
  - UI 100% espanol con datos personales/contacto, titulo profesional, resumen, experiencia, educacion, skills, certificaciones, idiomas, proyectos, links, informacion adicional e informacion interna; items con agregar/quitar/subir/bajar, orden denso 1..n persistido, checkbox de trabajo actual y listas por linea (logros, tecnologias, links de contacto).
  - Seguridad: bootstrap serializado con `| tojson` de Jinja dentro de `<script type="application/json">`; todo el contenido dinamico del cliente se inserta con nodos DOM y `textContent`/`value`, nunca `innerHTML` con datos del usuario (regla LL-001).
- Evidencia (CMD-032 a CMD-044):
  - RED: 20/21 pruebas de rutas fallando por ausencia de comportamiento (solo paso el 404 trivial) y modulo JS con MODULE_NOT_FOUND.
  - GREEN servidor: 21 passed enfocadas; suite completa 155 passed (134 baseline + 21 nuevas) con 1 warning preexistente; compileall aislado sin errores; `git diff --check` CRLF-aware limpio.
  - GREEN JS/navegador: 8 tests unitarios en Node y 4 flujos reales de browser con chromium headless (Chrome for Testing 153.0.8010.12) via CDP contra un runtime Docker temporal en 127.0.0.1:8123 con tmpfs de datos: flujo completo con orden persistido, submit fallido preservando lo ingresado, no-ejecucion de payloads maliciosos y conversion legacy con advertencia.
- Criterio de aceptacion:
  - Editor usable sin drag/drop; guardar no pierde campos legacy ni contenido solo-estructurado; los CVs legacy siguen operativos y solo se convierten por accion explicita del usuario al guardar.
  - Bad inputs accionables sin escrituras parciales; sin downcast de versiones futuras; rutas legacy compatibles.
- Pendientes: verificacion independiente del contrato de persistencia de alto riesgo acordada con el padre; T5 (consumidores LaTeX/PDF/ATS normalizados) y T6 (cierre, docs, integracion); commits diferidos hasta autorizacion explicita.

## Etapa T3 - import/export JSON schema 2 con compatibilidad schema 1

- Fecha: 2026-10-08
- Rama: `feature/structured-cv-complete` (sin commits por restriccion explicita del usuario)
- Objetivo: implementar el export/import JSON schema 2 lossless con compatibilidad total de schema 1, reutilizando el contrato normalizado y las escrituras estructuradas verificadas de T2, sin tocar editor, LaTeX/PDF, ATS ni IA.
- Modulos afectados: `app/services/export_service.py`, `app/routes/cvs.py`, `app/templates/cvs/detail.html`, `app/templates/cvs/index.html`, `tests/test_cv_json_schema2.py` (nuevo), `tests/test_export_service.py`, `tests/test_ui_routes.py` y documentacion de desarrollo (plan, bitacora de comandos).
- Alcance ejecutado:
  - Export canonico via `resolve_normalized_cv`: CV estructurado valido exporta envelope schema 2 lossless (`cv.title` + `cv.structured_payload` con secciones, claves extra, `order` y `metadata` preservados); legacy/invalido/stale/futuro exporta schema 1 plano desde el snapshot legacy, sin mezclar fuentes.
  - Descarga explicita schema 1 para CV estructurado via query `?schema_version=1` mas enlace aditivo en el detalle; `schema_version=2` sobre CV no estructurado y valores no soportados/booleanos se rechazan con error accionable, sin downcast.
  - Import con gate estricto: version ausente o 1 mantiene el flujo legacy (CV nuevo legacy canonico via `create_cv`); version 2 explicita valida con el contrato unico v2, traduce errores a espanol y crea un CV NUEVO estructurado via `create_structured_cv(metadata_source="json_import")` preservando el payload completo; jamas sobrescribe el CV de origen ni deja escrituras parciales.
  - `build_cv_form_data_from_json` se conserva para callers legacy y rechaza schema 2 explicito en lugar de aplanarlo; nuevo entrypoint `build_cv_json_import_result` -> `CVJsonImportResult`.
  - Limite de 512 KB por streaming antes del parseo para ambos schemas; payload serializado limitado por `MAX_STRUCTURED_PAYLOAD_BYTES` en la escritura T2.
  - Panel de import del listado documenta schemas 1/2 y que siempre crea un registro nuevo.
- Validaciones ejecutadas (imagen `cv-latex-app:latest`, workspace read-only, tmpfs en `/workspace/data`; CMD-022 a CMD-031):
  - RED observado: error de coleccion por `ImportError` del nuevo entrypoint `build_cv_json_import_result` (CMD-022) y 3 fallos conductuales de gate de versiones/copy de UI con 30 preexistentes en verde (CMD-023).
  - GREEN enfocado final: 54 passed en `test_export_service.py`, `test_ui_routes.py`, `test_structured_cv_normalization.py` y `test_cv_json_schema2.py`, incluido el test de triangulacion que rechaza un payload interno con version futura 3 bajo envelope schema 2.
  - Suite completa final: 134 passed, 1 warning preexistente (`anyio.abc.BlockingPortal`).
  - `python -m compileall -q app tests` sin errores; `git -c core.whitespace=cr-at-eol diff --check` limpio con CRLF preservado.
- Criterio de aceptacion:
  - Roundtrip estructurado export -> import -> nuevo CV estructurado conserva secciones, claves extra, `order` y metadata (salvo `metadata.source` reestampado a `json_import` por el contrato de escritura T2).
  - Imports corruptos, de version no soportada/no entera/booleana o con payload invalido fallan antes de escribir, con mensajes en espanol por la UI existente.
  - Schema 1 sigue siendo backward compatible, incluidos payloads planos sin version.
- Pendientes: T4 (editor estructurado), T5 (consumidores LaTeX/PDF/ATS normalizados), T6 (cierre, docs e integracion); commits diferidos hasta autorizacion explicita.

## Etapa T2 - contrato normalizado v2 y escritura estructurada atomica

- Fecha: 2026-10-08
- Rama: `feature/structured-cv-complete` (sin commits por restriccion explicita del usuario)
- Objetivo: completar el contrato normalizado unico, la validacion estricta del schema 2 soportado y las rutas de escritura estructurada del repositorio, base para editor, JSON y consumidores LaTeX/PDF/ATS de T3-T5.
- Estado previo confirmado: baseline `a28d1fd` en `main`, imagen `cv-latex-app:latest` `e32f6f86ba11`, 78 tests baseline pasando en corridas enfocadas con tmpfs.
- Modulos afectados: `app/validations/structured_cv_validations.py` (nuevo), `app/services/structured_cv_service.py`, `app/repositories/cv_repository.py`, `tests/test_structured_cv_service.py`, `tests/test_cv_repository.py`, `tests/test_structured_cv_normalization.py` (nuevo) y documentacion de desarrollo.
- Alcance ejecutado:
  - Se crea `structured_cv_validations.py` como contrato unico de validacion/normalizacion v2; el servicio delega y reexporta su API publica.
  - Se agrega `resolve_normalized_cv(cv)` que devuelve `NormalizedCV` (modo, `sections` completos, `legacy_snapshot`) como representacion unica para todos los consumidores futuros.
  - Solo schema 2 explicito con estado `valid` y payload validado es canonico estructurado; versiones futuras o invalidas caen 100% a legacy.
  - Se conserva la compatibilidad 9.2: payloads parciales con defaults, payload sin `schema_version` interno con version de fila 2, y rechazo de tipos incorrectos.
  - Se amplian las secciones master: `headline` (titulo profesional), `additional_info`, items completos de `experience`/`education` y validacion acotada de tipos/longitudes/orden en todas las secciones, con tope de items y de 512 KB del payload serializado; las claves extra se preservan.
  - Se agregan `build_structured_cv_write_bundle` y las operaciones `create_structured_cv`/`update_structured_cv` que persisten snapshot legacy y columnas estructuradas en una sola sentencia atomica, rechazando con `StructuredCVWriteError` antes de cualquier escritura parcial.
  - El snapshot legacy derivado nunca trunca contenido: si excede los limites legacy, la escritura se rechaza con error por campo.
  - No se tocan UI, rutas visibles, templates, LaTeX/PDF, export/import JSON visible, ATS scoring, DB ni migraciones.
- Validaciones ejecutadas (imagen `e32f6f86ba11`, workspace read-only, tmpfs en `/workspace/data`):
  - RED observado: 2 errores de coleccion (API inexistente) y 10 fallos conductuales de limites en `tests/test_structured_cv_service.py`.
  - GREEN enfocado: 57 passed (`test_structured_cv_service.py`, `test_cv_repository.py`, `test_database_migrations.py`, `test_structured_cv_normalization.py`).
  - Suite completa: 109 passed, 1 warning preexistente.
  - `python -m compileall -q app tests` sin errores; `git diff --check` limpio (CRLF-aware).
- Criterio de aceptacion:
  - Escrituras estructuradas invalidas no dejan cambios parciales persistidos.
  - Duplicate/update legacy/import schema 1 conservan las reglas 9.2 vigentes.
  - Todos los tests de regresion existentes siguen pasando.
- Pendientes: T3 (JSON schema 2), T4 (editor), T5 (consumidores normalizados), T6 (cierre); commits diferidos hasta autorizacion explicita.

## Etapa 9.2 - servicios de CV estructurado y escritura segura

- Fecha: 2026-06-14
- Rama: `feature/structured-cv-services`
- Objetivo: implementar servicios internos para construir, validar, serializar, invalidar y resolver `structured_payload` v2 sin cambiar UI, PDF/TEX, JSON visible ni ATS scoring.
- Estado previo confirmado: `main`, `development`, `origin/main` y `origin/development` sincronizados en `5b007a9` despues del cierre de PR #13.
- Modulos afectados: `app/services/structured_cv_service.py`, `app/repositories/cv_repository.py`, tests de repositorio/servicio y documentacion de desarrollo.
- Alcance ejecutado:
  - Se define schema minimo v2 con `personal`, `contact`, `summary`, `skills`, `experience`, `education`, `certifications`, `languages`, `projects`, `links` y `metadata`.
  - Se agrega validacion estructural, serializacion deterministica y conversion legacy -> payload v2.
  - El resolver solo acepta `structured_schema_version >= 2`, payload v2 valido y estado `valid`; cualquier payload ausente, invalido, stale o no valido cae a legacy canonico.
  - El update legacy de un CV ya estructurado regenera payload desde los campos legacy actualizados en el mismo `UPDATE`; si la regeneracion falla, vuelve a legacy canonico.
  - Los CVs legacy nuevos y existentes siguen operando como legacy; duplicate/copy conserva payload valido cuando el contenido copiado no cambia.
- Criterio de aceptacion:
  - CVs legacy siguen creando, leyendo, actualizando, duplicando y exportando por los flujos existentes.
  - No queda payload estructurado viejo marcado como valido cuando se actualiza un CV estructurado por flujo legacy.
  - No se modifica UI, templates productivos, PDFs servidos, renderer LaTeX/PDF, ATS scoring ni export JSON visible.

## Etapa 9.1 - modelo de datos y migracion segura para CV estructurado

- Fecha: 2026-06-13
- Rama: `feature/structured-cv-data-migration`
- Objetivo: agregar la base de persistencia compatible para CV estructurado sin cambiar UI, render LaTeX/PDF, export JSON visible ni ATS scoring.
- Estado previo confirmado: `main`, `development`, `origin/main` y `origin/development` sincronizados en `41daa8a` despues del cierre de PR #12.
- Modulos afectados: `app/database.py`, `app/models.py`, `app/repositories/cv_repository.py`, `app/services/structured_cv_service.py`, tests de migracion/repositorio/servicio y documentacion de desarrollo.
- Alcance ejecutado:
  - Se agregan columnas idempotentes en `cvs`: `structured_schema_version`, `structured_payload` y `structured_payload_status`.
  - La migracion usa `PRAGMA table_info(cvs)` y `ALTER TABLE ADD COLUMN` condicionado para preservar bases existentes.
  - Los CVs legacy quedan en modo canonico legacy cuando no hay payload valido.
  - El update por flujo legacy limpia payload estructurado para evitar stale data.
  - El duplicado preserva payload estructurado valido cuando el contenido copiado sigue consistente.
  - Se agrega servicio minimo para resolver modo legacy vs estructurado preparado sin conectar aun PDF/JSON/ATS al payload.
- Criterio de aceptacion:
  - DB nueva y DB legacy reciben columnas nuevas.
  - La migracion repetida es segura.
  - CVs legacy siguen creando, leyendo, actualizando, duplicando y exportando por los flujos existentes.
  - No se modifica UI, PDFs servidos, renderer LaTeX/PDF, ATS scoring ni export JSON visible.

## Etapa 9.0 - diseno tecnico del editor estructurado de CV

- Fecha: 2026-06-13
- Rama: `feature/structured-cv-editor-design`
- Objetivo: disenar arquitectura y plan de implementacion del futuro editor estructurado de CV sin tocar codigo funcional, DB, rutas, templates productivos, renderer LaTeX/PDF, import/export JSON ni ATS.
- Estado previo confirmado: `main`, `development`, `origin/main` y `origin/development` sincronizados en `e5752b6` despues del cierre de PR #11.
- Modulos analizados: `CV Builder Core`, export/import JSON, LaTeX/PDF, ATS, tests, documentacion de gobernanza y validaciones de release.
- Alcance ejecutado:
  - Se crea ADR de diseno para comparar alternativas de modelo de datos y recomendar transicion hibrida con payload JSON estructurado versionado.
  - Se crea plan por subetapas 9.1 a 9.7 con archivos probables, validaciones, criterios de aceptacion y limites.
  - Se enlaza el diseno desde `AGENTS.md`, `MODULE_INDEX.md`, `MVP_VALIDATION.md` y `PROJECT_PLAYBOOK.md`.
  - Se corrigen hallazgos de review del PR #12 definiendo ADR unica `ADR-0003`, fuente canonica entre legacy/payload estructurado, reglas de duplicate/update/import legacy y migracion idempotente para DBs existentes.
- Criterio de aceptacion:
  - La documentacion cubre compatibilidad con CVs existentes, fuente canonica, export/import JSON, LaTeX/PDF, ATS, migracion idempotente/rollback, tests, riesgos, subetapas y confirma que 9.0 no implementa funcionalidad.

## Etapa 8.4 - lessons learned y playbook operativo

- Fecha: 2026-06-13
- Rama: `feature/lessons-learned-playbook-v0.9.0`
- Objetivo: consolidar aprendizajes reales del proyecto y dejar un playbook reusable para futuras etapas y proyectos con Codex/ChatGPT, sin tocar runtime, PDFs, DB ni features.
- Estado previo confirmado: `main`, `development` y el cierre de PR #10 quedaron sincronizados en `71f1215`.
- Modulos afectados: `AGENTS.md`, `docs/development/`.
- Alcance ejecutado:
  - Se crea `LESSONS_LEARNED.md` con errores reales, causa raiz, correccion, validacion, regla futura e instruccion sugerida para prompts futuros.
  - Se crea `PROJECT_PLAYBOOK.md` con flujo operativo reusable para iniciar etapas, elegir configuracion, preparar prompts, validar cambios, pedir review y cerrar PRs/releases.
  - Se actualizan `AGENTS.md`, `MODULE_INDEX.md`, `MVP_VALIDATION.md` y `COMMAND_LOG.md` para enlazar la nueva gobernanza documental.
- Criterio de aceptacion:
  - La etapa deja documentados al menos los 18 aprendizajes reales requeridos.
  - El playbook cubre inicio de etapa, Git Flow, PR, merge, tag, review y validaciones minimas por tipo de cambio.
  - No se tocan PDFs, assets estaticos funcionales, DB ni features fuera de alcance.

## Etapa 8.3 - fix titulos huerfanos y listas PDF

- Fecha: 2026-06-12
- Rama: `feature/traceability-docs-v0.9.0`
- Objetivo: corregir titulos huerfanos y listas cortas partidas en PDFs generados, manteniendo indice funcional, contraste aprobado y consistencia HTML/PDF.
- Modulos afectados: `app/services/documentation_service.py`, `app/static/docs`, `AGENTS.md`, `docs/development`, `tests`.
- Resumen de cambios:
  - El renderer PDF estima el espacio necesario segun el bloque posterior a cada heading para evitar que secciones como `Modulos implementados` queden solas al final de pagina.
  - Las listas cortas se mantienen juntas cuando su tamano permite moverlas completas sin forzar saltos de pagina globales.
  - Se documenta que las validaciones PDF deben revisar listas cortas partidas, paginas internas afectadas, hashes, `pdftotext`, PNGs y descarga real desde `/static/docs/`.
- Resultado esperado: PDFs de documentacion `v0.9.0` sin titulos huerfanos ni listas cortas partidas de forma visualmente pobre antes de mergear PR #10.

## Etapa 8.3 - fix TOC y paginacion PDF

- Fecha: 2026-06-12
- Rama: `feature/traceability-docs-v0.9.0`
- Objetivo: corregir el indice vacio de PDFs generados, mejorar cortes visuales de secciones y dejar reglas permanentes para documentacion PDF actual y futura.
- Modulos afectados: `app/services/documentation_service.py`, `app/static/docs`, `AGENTS.md`, `docs/development`, `tests`.
- Resumen de cambios:
  - El renderer PDF mantiene `\tableofcontents`, pero ahora agrega entradas reales para headings no numerados y compila con dos pasadas de `pdflatex`.
  - Se agregan reservas de espacio antes de secciones, subsecciones, callouts, tablas y bloques de codigo para reducir titulos huerfanos y cortes visuales pobres.
  - Se documenta que no se publican PDFs con indice vacio, que los PDFs deben regenerarse cuando cambian fuentes o renderer, y que la validacion incluye `pdftotext`, PNG de portada/indice/pagina interna, hashes y descarga real desde `/static/docs/`.
  - Se refuerza que no se deben inventar timestamps historicos y que los Prompt IDs son externos a Codex.
- Resultado esperado: PDFs de documentacion `v0.9.0` con indice funcional, mejor lectura visual y reglas de validacion persistentes antes de mergear PR #10.

## Etapa 8.3 - trazabilidad y documentacion visual

- Fecha: 2026-06-11
- Rama: `feature/traceability-docs-v0.9.0`
- Objetivo: mejorar trazabilidad persistente del repo y elevar la documentacion HTML/PDF a un formato mas profesional, escaneable y consistente.
- Modulos afectados: `AGENTS.md`, `documentation`, `static/docs`, `docs/user`, `docs/development`, `tests`.
- Resumen de cambios:
  - Se crea `AGENTS.md` del repo con reglas especificas de stack, Git Flow, validaciones, documentacion, PDF, seguridad, Code Review y Prompt IDs externos a Codex.
  - Se documenta que los Prompt IDs son externos a Codex y no deben incluirse dentro de prompts ejecutables.
  - Se actualizan reglas de timestamps: `COMMAND_LOG.md` para comandos nuevos, `DEVELOPMENT_LOG.md` para hitos, `MVP_VALIDATION.md` para validaciones fuertes, `CHANGELOG_GENERAL.md` por release, `MODULE_INDEX.md` como mapa y `VERSIONING.md` para fechas de release/tag.
  - Se mejora el renderer de documentacion para soportar callouts en HTML/PDF y generar PDFs con portada, version, fecha, estado, tabla de contenidos, footer, tablas con filas alternadas y bloques visuales.
  - Se actualiza `PROJECT_HISTORY_ROLLBACK.md` para reflejar `v0.9.0` como release estable actual y `v0.8.0` como release anterior.
  - Se cambia el copy menor del sidebar de `Base estable: v0.8.0` a `Release anterior: v0.8.0`.
- Resultado esperado: documentacion mas clara y auditable, sin cambios funcionales nuevos ni cambios de DB.

## Fix PR #9 - bundled technical PDF before v0.9.0 release

- Fecha: 2026-06-10
- Rama: `feature/release-v0.9.0`
- Objetivo: corregir el P1 de Codex Review para que el PDF descargable de `/documentation/technical` coincida con la documentacion tecnica vigente de `v0.9.0`.
- Modulos afectados: `app/static/docs`, `docs/development`.
- Resumen de cambios:
  - Se regenero `app/static/docs/Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf` desde `docs/user/PROJECT_TECHNICAL_DOCUMENTATION.md`.
  - Se uso el pipeline existente de `app.services.documentation_service` con `pdflatex` dentro de la imagen Docker `cv-latex-app`.
  - Se valido con `pdftotext` que el PDF contiene `v0.9.0`, `Dashboard privado disponible`, `Curriculum Vitae + ATS` y `PR #8`.
  - Se confirmo que el PDF ya no contiene `feature/ui-private-dashboard`, `Rama visual actual` ni referencias al PR visual como pendiente.
- Hash anterior del PDF tecnico: `9725c5180bdfb1d29b57d512abac00a0e0706d5a`.
- Hash nuevo del PDF tecnico: `0726772249a27d6e90304164d6972f07684bdf20`.
- Resultado esperado: artefacto PDF descargable alineado al release `v0.9.0`, sin cambios funcionales nuevos.

## Fix PR #9 - shipped docs before v0.9.0 release

- Fecha: 2026-06-10
- Rama: `feature/release-v0.9.0`
- Objetivo: corregir el P1 de Codex Review para que `/documentation/technical` refleje el estado integrado real antes del merge a `development`.
- Modulos afectados: `docs/user`, `docs/development`, `tests`.
- Resumen de cambios:
  - Se actualizo `PROJECT_TECHNICAL_DOCUMENTATION.md` para reflejar `v0.9.0` como version preparada.
  - Se removio el estado obsoleto que seguia tratando `feature/ui-private-dashboard` como rama actual o la UI privada como pendiente.
  - Se documento explicitamente que el PR `#8` ya fue mergeado y que dashboard privado, sidebar persistente, dark/light, `Curriculum Vitae + ATS`, badge ATS, modal ATS compacto y fix XSS ya forman parte del release preparado.
  - Se agrego una prueba de regresion para evitar que `/documentation/technical` vuelva a publicar ese estado obsoleto.
- Resultado esperado: documentacion servida alineada al release `v0.9.0`, sin cambios funcionales nuevos.

## Release v0.9.0

- Fecha: 2026-06-08
- Rama: `feature/release-v0.9.0`
- Objetivo: alinear version, changelog, docs operativas y validaciones despues de integrar la UI privada y el flujo ATS dentro de `Curriculum Vitae`.
- Modulos afectados: `versioning`, `docker`, `runtime`, `docs/development`, `README`.
- Resumen de cambios:
  - Se actualizo la version vigente de `0.8.0` a `0.9.0` en `VERSION`, `Dockerfile`, `docker-compose.yml`, `.env.example` y `app/main.py`.
  - Se mantuvieron intactas las referencias historicas al tag `v0.8.0` dentro de rollback, changelog y documentacion de referencia.
  - Se documento que `v0.9.0` incluye dashboard privado redisenado, sidebar persistente, dark/light mode, flujo `Curriculum Vitae + ATS`, badge ATS en listados, modal ATS compacto, exportacion unificada, confirmaciones seguras, fix XSS y versionado de assets.
  - Se actualizaron `README.md`, `CHANGELOG_GENERAL.md`, `VERSIONING.md`, `MODULE_INDEX.md` y `MVP_VALIDATION.md` para reflejar la nueva version vigente.
- Resultado esperado: release `v0.9.0` preparado y validado, sin tag todavia y listo para PR hacia `development`.

## Etapa 8.1 - UI privada y dashboard operativo

- Fecha: 2026-06-06
- Rama: `feature/ui-private-dashboard`
- Objetivo: redisenar la experiencia visual de la app privada local sin tocar DB, login ni exportaciones profundas.
- Modulos afectados: `layout`, `dashboard`, `cvs`, `cover_letters`, `static/css`, `static/js`, `docs/development`, `docs/user`, `tests`.
- Resumen de cambios:
  - Se reemplazo el header horizontal por una sidebar fija con version visible y acceso a los modulos principales y secundarios.
  - Se agrego toggle dark/light persistido en `localStorage`.
  - El dashboard pasa a enfocarse en CVs y cartas con listas recientes y modulos secundarios aparte.
  - El listado de CVs y el de cartas se redisenaron como filas compactas con preview visual tipo documento.
  - El detalle de CV unifica la seleccion de plantilla para exportar TEX y PDF.
  - La confirmacion de borrado de CVs y cartas exige coincidencia exacta del texto esperado.
  - Se agrego `PROJECT_HISTORY_ROLLBACK.md` para documentar la base estable `v0.8.0` y los comandos de rollback de referencia.
- Resultado esperado: base funcional del MVP preservada con una UI privada mas moderna y segura para operar localmente.

### Correccion urgente - restauracion visual

- Diagnostico: el HTML nuevo estaba presente, pero el sintoma reportado era consistente con assets CSS/JS obsoletos o cacheados sin versionado.
- Se agrego version de assets en `layout.html` usando `request.app.state.asset_version`.
- Se expuso `APP_ASSET_VERSION` desde `app/main.py`.
- Se reforzo el estilo base de botones, selects y toggle para evitar apariencia HTML nativa si el navegador reutiliza cache parcial.
- El estado activo de la sidebar queda marcado tambien desde el render del template, no solo desde JavaScript.

### Ajuste 8.1.2.9 - popup ATS compacto

- Se redisenio el popup `Analisis ATS` como dashboard compacto de dos columnas.
- `Estado general` mantiene score, badge, longitud, referencia real de longitud y suma barra visual de progreso.
- `Resumen rapido` queda debajo de `Estado general` como mini cards compactas.
- `Checklist` queda en filas densas con indicador circular y badge `OK`/`Revisar`.
- `Recomendaciones` y `Advertencias` quedan como cards inferiores compactas.
- No se modifico scoring ATS, persistencia, rutas de datos ni features futuras.

### Ajuste 8.1.2.10 - indicadores de score

- La referencia de score del modal ATS suma puntos de color semanticos por rango.
- La barra del score agrega glow sutil en la punta para mejorar lectura visual del progreso.
- El ajuste queda encapsulado en el partial ATS y en CSS especifico, sin cambiar layout, checklist ni acciones del modal.

### Correccion P1 - confirmaciones seguras

- Se corrigio el modal de confirmacion para no interpolar `data-confirm-title`, `data-confirm-message` ni `data-confirm-label` mediante `innerHTML`.
- El dialogo se construye con nodos DOM y los textos dinamicos se asignan con `textContent`.
- Se agregaron tests contra regresiones de XSS usando titulos maliciosos de CV.

## Documentation Center

- Fecha: 2026-06-05
- Rama: `feature/documentation-center`
- Objetivo: agregar una seccion web de documentacion con PDFs embebidos, servidos localmente y generados desde fuentes Markdown editables.
- Modulos afectados: `documentation`, `dashboard`, `layout`, `static/docs`, `docs/user`, `docs/development`, `tests`.
- Resumen de cambios:
  - Se agrego la ruta `app/routes/documentation.py`.
  - Se agrego el template `app/templates/documentation/index.html`.
  - Se incorporo el acceso `Documentacion` en header y dashboard.
  - Se agrego `app/services/documentation_service.py` para catalogar documentos y generar PDFs desde Markdown.
  - Se crearon las fuentes `docs/user/PROJECT_TECHNICAL_DOCUMENTATION.md` y `docs/user/WEB_USAGE_MANUAL.md`.
  - Se generaron y publicaron los PDFs en `app/static/docs/`.
  - Se agregaron tests basicos de rutas para la nueva seccion.
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker run --rm -v "${PWD}:/workspace" -w /workspace cv-latex-app python -m app.services.documentation_service`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - `Invoke-WebRequest` sobre `/documentation/`, `/documentation/technical` y los dos PDFs estaticos
  - `pdftotext` y `pdftoppm` dentro del contenedor para validar legibilidad
  - `git diff --check`
- Resultado: seccion de documentacion funcional, assets PDF locales servidos desde la app y contenido legible validado antes del tag `v0.8.0`.

### Ajuste posterior - lectura HTML

- Cambio de decision: la lectura principal deja de usar `iframe` PDF y pasa a paginas HTML dentro de la app.
- Se agrego parsing simple de Markdown a secciones HTML para `technical` y `usage`.
- Cada pagina mantiene indice, bloques visuales y accion `Descargar PDF`.
- Los PDFs quedan como artefacto descargable y no como flujo principal de lectura.
- La imagen Docker pasa a incluir `docs/` para que el runtime pueda leer las fuentes Markdown durante el render HTML.

## Release Cleanup v0.8.0 - Changelog Consolidation

- Fecha: 2026-06-05
- Rama: `feature/release-cleanup-v0.8.0`
- Objetivo: integrar las notas del cleanup dentro de la unica entrada `0.8.0` del changelog.
- Modulos afectados: `docs/development`.
- Resumen de cambios:
  - Se elimino el encabezado duplicado `0.8.0 - 2026-06-05`.
  - Las notas de cleanup quedaron integradas en la entrada existente `0.8.0 - 2026-06-04`.
- Resultado: la documentacion de release queda no ambigua y sin versiones repetidas.

## Release Cleanup v0.8.0

- Fecha: 2026-06-05
- Rama: `feature/release-cleanup-v0.8.0`
- Objetivo: alinear version y documentacion antes del tag `v0.8.0`.
- Modulos afectados: `Dockerfile`, `README.md`, `docs/development`.
- Resumen de cambios:
  - Se actualizo `APP_VERSION` en `Dockerfile` a `0.8.0`.
  - Se limpio la seccion `ATS Basic Check` del README para que describa solo el analisis ATS.
  - Se registro el ajuste en logs de desarrollo para dejar trazabilidad del release cleanup.
- Resultado: cambio menor de consistencia aplicado sin tocar logica funcional ni rutas.

## Etapa 0 - Base tecnica, Docker y documentacion inicial

- Fecha: 2026-06-02
- Rama: `feature/base-docker-app`
- Objetivo: crear la base minima del proyecto con FastAPI, Jinja2, SQLite preparado, Docker Compose y documentacion inicial.
- Modulos afectados: `app`, `dashboard`, `database`, `docker`, `docs`.
- Resumen de cambios:
  - Se creo una app FastAPI minima con dashboard renderizado por Jinja2.
  - Se preparo SQLite en `/data/app.db` con una tabla tecnica `app_metadata`.
  - Se agregaron archivos estaticos CSS/JS.
  - Se agrego Dockerfile y docker-compose con montaje `./data:/data`.
  - Se creo documentacion inicial de desarrollo, versionado, ramas y ADRs.
- Archivos principales:
  - `app/main.py`
  - `app/database.py`
  - `app/routes/dashboard.py`
  - `app/templates/layout.html`
  - `app/templates/dashboard.html`
  - `Dockerfile`
  - `docker-compose.yml`
  - `README.md`
  - `VERSION`
- Validaciones ejecutadas:
  - `git status`
  - `git branch --all`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`
  - `Invoke-WebRequest` sobre CSS y JS estaticos
  - `Test-Path -LiteralPath data`
  - `Get-ChildItem -Force -LiteralPath data`
  - `docker compose exec app ls -la /data`
  - `docker compose down`
  - `docker compose up -d` nuevamente
  - `docker compose ps` nuevamente
- Resultado: completado localmente. La app levanta en `http://localhost:8000`, el contenedor queda `healthy`, `/health` devuelve `status: ok`, `/data/app.db` existe y los assets estaticos responden 200.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 1.
  - Preparar PR hacia `development` solo si el usuario lo indica.

### Observaciones de validacion

- `docker compose build` fallo inicialmente dentro del sandbox por permisos sobre `C:\Users\zetchs\.docker`; se reejecuto con permiso elevado y finalizo correctamente.
- La verificacion con navegador interno fallo por una limitacion del runtime (`windows sandbox failed: spawn setup refresh`). Se valido por HTTP directo el dashboard, `/health`, CSS y JavaScript.

### Limites de alcance confirmados

No se implemento CV Builder, LaTeX, PDF, cartas de presentacion, postulaciones, ATS ni IA.

## Etapa 1 - CV Builder Core

- Fecha: 2026-06-02
- Rama: `feature/cv-builder-core`
- Objetivo: implementar el modulo base de CVs con CRUD simple, formularios HTML y persistencia SQLite.
- Modulos afectados: `app`, `dashboard`, `database`, `cv-builder`, `validations`, `docs`, `docker`.
- Resumen de cambios:
  - Se agrego modelo base `CV`.
  - Se agrego schema de formulario `CVFormData`.
  - Se creo tabla SQLite `cvs` con timestamps y eliminacion logica mediante `deleted_at`.
  - Se implementaron rutas para listar, crear, ver detalle, editar, duplicar, confirmar eliminacion y eliminar logicamente.
  - Se agregaron templates HTML simples para listado, formulario, detalle y confirmacion.
  - Se agrego navegacion desde dashboard y header hacia `CVs`.
  - Se centralizaron validaciones del formulario en `app/validations/cv_validations.py`.
  - Se actualizo la version a `0.2.0`.
- Archivos principales:
  - `app/models.py`
  - `app/schemas.py`
  - `app/database.py`
  - `app/repositories/cv_repository.py`
  - `app/routes/cvs.py`
  - `app/templates/cvs/index.html`
  - `app/templates/cvs/form.html`
  - `app/templates/cvs/detail.html`
  - `app/templates/cvs/confirm_delete.html`
  - `app/validations/cv_validations.py`
  - `app/static/css/app.css`
  - `docs/development/CV_BUILDER_CORE.md`
- Validaciones ejecutadas:
  - `python -m compileall app`
  - `rg -n -P "[^\\x00-\\x7F]"`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/cvs/new -UseBasicParsing`
  - POST de creacion de CV
  - POST de edicion de CV
  - POST de duplicado de CV
  - GET de confirmacion de eliminacion
  - POST de eliminacion logica
  - Verificacion SQLite de CVs activos e inactivos
  - POST invalido con respuesta 422
- Resultado: completado localmente. El contenedor queda `healthy`, la version de `/health` es `0.2.0`, el flujo CRUD basico funciona y los registros eliminados logicamente no aparecen activos.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 2.
  - Preparar push o PR solo si el usuario lo indica.

### Observaciones de validacion Etapa 1

- El primer arranque fallo por anotaciones de retorno `HTMLResponse | RedirectResponse` en rutas FastAPI. Causa: FastAPI intento construir un response model Pydantic con esa union. Correccion aplicada: quitar esas anotaciones en las rutas POST afectadas.
- Los CVs de prueba creados durante validacion quedaron eliminados logicamente. El listado activo quedo en cero; SQLite conserva dos registros con `deleted_at` por trazabilidad local.

### Limites de alcance confirmados Etapa 1

No se implemento LaTeX, generacion PDF, export TEX, export JSON, cartas de presentacion, tracker de postulaciones, ATS ni IA.

## Etapa 2 - Plantillas LaTeX y sanitizacion

- Fecha: 2026-06-02
- Rama: `feature/latex-templates`
- Objetivo: implementar plantillas LaTeX propias, sanitizacion y generacion de contenido `.tex` desde CVs guardados.
- Modulos afectados: `latex_templates`, `latex_service`, `latex_sanitizer`, `cv-builder`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego `app/latex_templates/cv/`.
  - Se crearon plantillas propias `classic.tex`, `modern.tex`, `compact.tex` y `tech.tex`.
  - Se agrego `app/services/latex_service.py`.
  - Se agrego `app/validations/latex_sanitizer.py`.
  - Se agrego vista de previsualizacion TEX en `/cvs/{cv_id}/tex`.
  - Se agrego boton `Ver TEX` en el detalle de CV.
  - Se agregaron tests basicos de sanitizacion y servicio.
  - Se actualizo la version a `0.3.0`.
- Archivos principales:
  - `app/latex_templates/cv/classic.tex`
  - `app/latex_templates/cv/modern.tex`
  - `app/latex_templates/cv/compact.tex`
  - `app/latex_templates/cv/tech.tex`
  - `app/services/latex_service.py`
  - `app/validations/latex_sanitizer.py`
  - `app/templates/cvs/tex_preview.html`
  - `tests/test_latex_sanitizer.py`
  - `tests/test_latex_service.py`
  - `docs/development/LATEX_TEMPLATES.md`
  - `docs/adr/ADR-0004-latex-rendering.md`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `python -m unittest discover -s tests`
  - `git diff --check`
  - `rg -n -P "[^\\x00-\\x7F]"`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -UseBasicParsing`
  - POST de creacion de CV con caracteres en espanol y especiales LaTeX
  - GET de `/cvs/{id}/tex` con `classic`, `modern`, `compact` y `tech`
  - GET de plantilla invalida con respuesta 404
  - Verificacion directa del contenido TEX dentro del contenedor
  - Eliminacion logica del CV de prueba de la etapa
- Resultado: completado localmente. El contenedor queda `healthy`, `/health` devuelve `version: 0.3.0`, las cuatro plantillas generan vista TEX y el sanitizador escapa caracteres especiales preservando texto comun en espanol.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 3.
  - Preparar push o PR solo si el usuario lo indica.

### Observaciones de validacion Etapa 2

- La primera validacion local de `test_latex_service.py` fallo porque el Python local no tiene `jinja2`; se ajusto el test para saltar solo esa prueba cuando falta la dependencia local. La generacion del servicio fue validada en Docker, donde `jinja2` esta instalado por `requirements.txt`.
- La primera validacion de vistas TEX fallo por usar `section.items`, que colisionaba con el metodo `dict.items` de Jinja. Se corrigio usando `section.item_list`.
- Se creo y elimino logicamente un CV de prueba de Etapa 2. Se conservo un CV activo preexistente (`SysAdmin Linux`) porque no corresponde a datos de prueba de esta etapa.

### Limites de alcance confirmados Etapa 2

No se implemento compilacion PDF final, descarga PDF, export TEX, export JSON, import JSON, cartas de presentacion, tracker de postulaciones, ATS ni IA.

## Correccion de validacion Etapa 2 - pytest en contenedor

- Fecha: 2026-06-03
- Rama: `feature/fix-pytest-validation`
- Objetivo: corregir la validacion pendiente de Etapa 2 agregando `pytest` a la imagen Docker para ejecutar tests dentro del contenedor.
- Modulos afectados: `docker`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego `pytest` a `requirements.txt`.
  - Se ajusto `Dockerfile` para copiar `tests/` dentro de la imagen.
  - Se reconstruyo la imagen del servicio `app`.
  - Se ejecuto `python -m pytest` dentro del contenedor.
  - Se actualizo la documentacion operativa con el flujo y el resultado.
- Archivos principales:
  - `Dockerfile`
  - `requirements.txt`
  - `docs/development/COMMAND_LOG.md`
  - `docs/development/DEVELOPMENT_LOG.md`
  - `docs/development/CHANGELOG_GENERAL.md`
- Validaciones ejecutadas:
  - `git status --short --branch`
  - `git branch --all`
  - `git fetch origin`
  - `git switch development`
  - `git merge --ff-only main`
  - `git switch -c feature/fix-pytest-validation`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose exec app python -m pytest`
- Resultado: validacion corregida. El contenedor ahora incluye `pytest` y la suite corre dentro de Docker.
- Pendientes:
  - No hacer merge automatico.
  - Esperar validacion explicita del usuario antes de cualquier paso posterior.

### Observaciones de la correccion

- El primer intento con `docker compose exec app python -m pytest` dejo `pytest` disponible pero fallo con `collected 0 items` porque la imagen solo copiaba `app/` y no `tests/`.
- La correccion minima fue sumar `pytest` a `requirements.txt` y copiar `tests/` en `Dockerfile`. Con eso la validacion en contenedor paso con `6 passed`.

## Etapa 3 - Export Engine PDF/TEX/JSON

- Fecha: 2026-06-03
- Rama: `feature/export-engine`
- Objetivo: implementar exportacion TEX/PDF/JSON e importacion JSON desde CVs guardados, con rutas seguras y persistencia en `/data/exports`.
- Modulos afectados: `cvs`, `export_service`, `pdf_service`, `latex_service`, `docker`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego `app/services/export_service.py` para exportar TEX/JSON, sanitizar nombres y crear directorios en `/data/exports`.
  - Se agrego `app/services/pdf_service.py` para compilar con `pdflatex` dentro de un temporal controlado y guardar PDF final.
  - Se agregaron rutas de descarga TEX, descarga JSON, generacion PDF e importacion JSON.
  - Se agrego importacion JSON desde formulario multipart creando siempre un nuevo CV.
  - Se agregaron tests unitarios para exportaciones, importacion y compilacion PDF mockeada.
  - Se actualizo Dockerfile con TeX Live para compilar las plantillas actuales.
  - Se actualizo la version a `0.4.0`.
- Archivos principales:
  - `app/services/export_service.py`
  - `app/services/pdf_service.py`
  - `app/routes/cvs.py`
  - `app/templates/cvs/detail.html`
  - `app/templates/cvs/index.html`
  - `app/templates/cvs/tex_preview.html`
  - `Dockerfile`
  - `tests/test_export_service.py`
  - `tests/test_pdf_service.py`
- Validaciones ejecutadas:
  - `git status --short --branch`
  - `git fetch origin`
  - `git rev-list --left-right --count development...origin/development`
  - `git switch -c feature/export-engine`
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `docker compose exec app python -m pytest`
  - Creacion de CV de prueba desde el contenedor
  - `GET /cvs/6/export/tex?template_key=tech`
  - `GET /cvs/6/export/json`
  - `POST /cvs/import/json`
  - `GET /cvs/6/export/pdf?template_key=tech`
  - Verificacion de archivos persistidos en `/data/exports`
  - `GET /cvs/6/tex?template_key=modern`
  - `GET /cvs/8`
- Resultado: completado localmente. El contenedor queda `healthy`, `/health` devuelve `version: 0.4.0`, `pytest` pasa con 13 tests y las exportaciones TEX/JSON/PDF funcionan por HTTP.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 4.
  - No hacer merge automatico.
  - Mantener ramas feature existentes hasta que el usuario indique limpieza.

### Observaciones de validacion Etapa 3

- `python -m pytest` local en Windows no se pudo ejecutar porque ese Python local no tiene `pytest`; la validacion obligatoria se ejecuto dentro del contenedor y paso con `13 passed`.
- La primera prueba funcional detecto colision de nombres cuando TEX y PDF se generaban en paralelo para el mismo CV/plantilla en el mismo segundo. Se corrigio usando timestamp con microsegundos.
- La primera vista TEX posterior al cambio fallo por usar query params dentro de `url_for`; se corrigio construyendo el query string fuera de `url_for`.
- Dockerfile instala TeX Live en lugar de Tectonic. Motivo: Tectonic puede requerir descarga de bundles en runtime; TeX Live deja la imagen mas pesada pero reproducible. Impacto observado durante build: aproximadamente 509 MB adicionales.

### Limites de alcance confirmados Etapa 3

No se implemento cartas de presentacion, tracker de postulaciones, ATS, IA, login, PostgreSQL ni deploy cloud.

## Etapa 3.1 - PDF ATS Text Extraction / Encoding Fix

- Fecha: 2026-06-03
- Rama: `feature/pdf-ats-text-extraction`
- Objetivo: mejorar el mapeo de texto en PDFs generados para copy/paste, extraccion con herramientas PDF y compatibilidad futura con parsers ATS.
- Modulos afectados: `latex_templates`, `docker`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego `\\input{glyphtounicode}` y `\\pdfgentounicode=1` a `classic`, `modern`, `compact` y `tech`.
  - Se agrego `\\usepackage{cmap}` a las cuatro plantillas.
  - Se agrego `\\usepackage{lmodern}` para usar fuentes Latin Modern con encoding T1.
  - Se agrego `lmodern` al Dockerfile porque `lmodern.sty` no venia incluido solo con `fonts-lmodern`.
  - Se agrego `poppler-utils` al Dockerfile para validar extraccion real con `pdftotext`.
  - Se actualizo la version a `0.4.1`.
- Archivos principales:
  - `app/latex_templates/cv/classic.tex`
  - `app/latex_templates/cv/modern.tex`
  - `app/latex_templates/cv/compact.tex`
  - `app/latex_templates/cv/tech.tex`
  - `Dockerfile`
  - `tests/test_latex_service.py`
  - `README.md`
  - `docs/adr/ADR-0004-latex-rendering.md`
- Validaciones ejecutadas:
  - `git status --short --branch`
  - `git fetch origin`
  - `git switch development`
  - `git rev-list --left-right --count development...origin/development`
  - `git switch -c feature/pdf-ats-text-extraction`
  - `python -m compileall app tests`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - `docker compose exec app which pdftotext`
  - Creacion de CV de prueba con texto acentuado y caracteres espanoles.
  - Generacion de PDF con `classic`, `modern`, `compact` y `tech`.
  - Extraccion de texto con `pdftotext` para cada PDF.
- Resultado: validacion completada. Los cuatro PDFs compilan y `pdftotext` preserva `Perfil`, `tecnico` acentuado, `gestion`, `informacion`, `analisis`, `educacion`, `comunicacion`, `ñandu`, `accion` y `configuracion` con acentos en el texto extraido.
- Pendientes:
  - No avanzar a Etapa 4 sin validacion explicita.
  - Mantener pruebas con parsers ATS reales para una etapa futura.

### Observaciones de validacion Etapa 3.1

- La primera compilacion fallo por falta de `lmodern.sty`; se corrigio agregando el paquete Debian `lmodern`.
- `pdftotext` quedo disponible por `poppler-utils`, agregado solo para validacion tecnica de extraccion.
- El build final reporto aproximadamente 587 MB adicionales por dependencias LaTeX/PDF.

## Etapa 3.2 - Baseline Hardening & Consistency

- Fecha: 2026-06-04
- Rama: `feature/baseline-hardening`
- Objetivo: corregir hallazgos altos y medios del baseline antes de avanzar a nuevas features.
- Modulos afectados: `docker`, `cvs`, `export_service`, `pdf_service`, `validations`, `tests`, `docs`.
- Resumen de cambios:
  - Se limito la publicacion HTTP por defecto a `127.0.0.1` mediante `APP_HOST_BIND`.
  - Se agrego lectura controlada por chunks para import JSON con limite temprano de `512 KB`.
  - Se separo el mensaje seguro para UI del detalle tecnico de fallos PDF.
  - Se reforzo el duplicado de CV para reutilizar validaciones y truncar titulos largos de forma segura.
  - Se actualizaron tests y documentacion del baseline actual.
- Archivos principales:
  - `docker-compose.yml`
  - `.env.example`
  - `app/routes/cvs.py`
  - `app/services/export_service.py`
  - `app/services/pdf_service.py`
  - `app/repositories/cv_repository.py`
  - `app/validations/cv_validations.py`
  - `tests/test_export_service.py`
  - `tests/test_pdf_service.py`
  - `tests/test_cv_repository.py`
- Validaciones ejecutadas:
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - `Invoke-WebRequest` a `http://localhost:8000` y `/health`
  - Import JSON valido y rechazo de import excedido
  - Duplicado de CV con titulo al limite
  - Generacion PDF luego del hardening
  - `git diff --check`
- Resultado: baseline endurecido sin avanzar a Etapa 4. La app sigue operativa en localhost, el import corta por tamano, el duplicado respeta limites y el error PDF visible en UI deja de exponer logs completos.
- Pendientes:
  - Mantener este baseline como piso minimo antes de sumar modulos nuevos.
  - Validar parsers ATS reales en una etapa futura.

## Etapa 4 - Cover Letters

- Fecha: 2026-06-04
- Rama: `feature/cover-letters`
- Objetivo: implementar el modulo de cartas de presentacion con CRUD basico, asociacion opcional a CV y exportacion TEX/PDF.
- Modulos afectados: `cover_letters`, `database`, `latex_service`, `export_service`, `pdf_service`, `dashboard`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego el modelo `CoverLetter` y el schema `CoverLetterFormData`.
  - Se creo la tabla SQLite `cover_letters` con eliminacion logica y referencia opcional a CV.
  - Se implemento el repositorio `cover_letter_repository.py`.
  - Se agregaron rutas FastAPI para listar, crear, ver detalle, editar, confirmar eliminacion, eliminar, exportar TEX y generar PDF.
  - Se agregaron templates HTML bajo `app/templates/cover_letters/`.
  - Se agrego navegacion a `Cartas` desde dashboard y header.
  - Se creo la plantilla LaTeX `app/latex_templates/cover_letter/classic_letter.tex`.
  - Se extendieron `latex_service`, `export_service` y `pdf_service` para soportar cartas reutilizando el pipeline existente.
  - Se agrego documentacion especifica del modulo y se actualizo la version a `0.5.0`.
- Archivos principales:
  - `app/models.py`
  - `app/schemas.py`
  - `app/database.py`
  - `app/repositories/cover_letter_repository.py`
  - `app/routes/cover_letters.py`
  - `app/templates/cover_letters/index.html`
  - `app/templates/cover_letters/form.html`
  - `app/templates/cover_letters/detail.html`
  - `app/templates/cover_letters/confirm_delete.html`
  - `app/latex_templates/cover_letter/classic_letter.tex`
  - `app/validations/cover_letter_validations.py`
  - `docs/development/COVER_LETTERS.md`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `docker compose exec app python -m pytest`
  - `Invoke-WebRequest` a `http://localhost:8000`
  - POST de creacion de CV base para asociacion
  - POST de creacion de carta asociada
  - GET de listado y detalle de carta
  - POST de edicion de carta
  - GET de confirmacion y POST de eliminacion de carta
  - Descarga TEX y generacion PDF por HTTP
  - Verificacion de artefactos persistidos en `/data/exports`
  - Extraccion basica de texto PDF con `pdftotext`
- Resultado: etapa implementada y validada localmente. El modulo de cartas queda operativo, asociado al dashboard y reutiliza correctamente sanitizacion, exportacion TEX y compilacion PDF.
- Pendientes:
  - Esperar validacion explicita del usuario antes de cualquier merge.
  - Preparar push de la rama feature y PR hacia `development`.
  - Pedir `@codex review` manual despues del PR.

## Etapa 8.1.1 - Ajustes finos visuales y UX post-review

- Fecha: 2026-06-06
- Rama: `feature/ui-private-dashboard`
- Objetivo: pulir dashboard, listados, acciones secundarias, modal ATS y documentacion web sin tocar DB ni etapas futuras.
- Modulos afectados: `dashboard`, `cvs`, `cover_letters`, `ats`, `documentation`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - Se simplifico la card de resumen del dashboard para mostrar metricas claras de curriculums, cartas y postulaciones.
  - Se quitaron referencias visuales a `SQLite activo` en el listado de CVs.
  - Se movieron acciones principales de CVs y cartas al extremo derecho de cada fila.
  - Se agrego cierre de menus `Mas acciones` con click externo y tecla `Escape`.
  - Se incorporo un modal ATS reutilizando el servicio existente y manteniendo la ruta completa `/ats/cvs/{cv_id}`.
  - Se reagruparon acciones secundarias del detalle de CV como botones consistentes.
  - Se removio `Abrir PDF directo` del centro de documentacion.
  - Se aumento el asset version para evitar cache obsoleta tras el refinamiento.
- Archivos principales:
  - `app/routes/dashboard.py`
  - `app/routes/ats.py`
  - `app/templates/dashboard.html`
  - `app/templates/cvs/index.html`
  - `app/templates/cvs/detail.html`
  - `app/templates/cover_letters/index.html`
  - `app/templates/ats/index.html`
  - `app/templates/ats/cv_analysis.html`
  - `app/templates/ats/_analysis_sections.html`
  - `app/templates/ats/modal.html`
  - `app/templates/documentation/index.html`
  - `app/templates/documentation/detail.html`
  - `app/static/css/app.css`
  - `app/static/js/app.js`
  - `tests/test_ui_routes.py`
  - `tests/test_ats_routes.py`
  - `tests/test_documentation_routes.py`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d --force-recreate`
  - `docker compose ps`
  - `docker compose logs app --tail 80`
  - `docker compose exec app python -m pytest`
  - Requests HTTP y validacion DOM sobre `/`, `/cvs/`, `/cover-letters/`, `/applications/`, `/ats/`, `/documentation/`, `/documentation/technical`, `/documentation/usage`, `/ats/cvs/43` y `/ats/cvs/43/modal`
  - `git diff --check`
- Resultado: refinamiento UX aplicado con runtime estable, tests en verde y compatibilidad ATS/documentacion conservada.
- Pendientes:
  - Validacion visual manual del modal ATS y del cierre de menus en un navegador real.
  - Crear PR hacia `development` cuando el usuario lo pida.

## Etapa 8.1.2 - Pulido fino del dashboard privado, listados y ATS modal

- Fecha: 2026-06-06
- Rama: `feature/ui-private-dashboard`
- Objetivo: terminar el pulido fino visual de dashboard, listados, detalle de CV y modal ATS antes del PR.
- Modulos afectados: `dashboard`, `cvs`, `ats`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - Se compactaron las metricas del resumen del workspace y se removio texto sobrante.
  - Se convirtieron las acciones `Abrir CVs` y `Abrir cartas` en botones visibles dentro de cards con previews CSS.
  - Se movio `Importar JSON` a una seccion secundaria `Herramientas avanzadas`.
  - Se integro la fecha del listado de CVs como metadata secundaria mejor alineada.
  - Se agrego confirmacion modal para `Duplicar CV` tanto en detalle como en listado.
  - Se ordeno el modal ATS con acciones superiores y score/estado mejor agrupados.
  - Se documento que las miniaturas reales de PDF quedan como backlog futuro y no se implementan en esta etapa.
- Archivos principales:
  - `app/routes/dashboard.py`
  - `app/templates/dashboard.html`
  - `app/templates/cvs/index.html`
  - `app/templates/cvs/detail.html`
  - `app/templates/ats/modal.html`
  - `app/templates/ats/_analysis_sections.html`
  - `app/static/css/app.css`
  - `app/static/js/app.js`
  - `tests/test_ui_routes.py`
  - `tests/test_ats_routes.py`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d --force-recreate`
  - `docker compose ps`
  - `docker compose logs app --tail 80`
  - `docker compose exec app python -m pytest`
  - Validacion HTTP/DOM sobre dashboard, listado CVs, listado cartas, detalle CV, modal ATS y documentacion
  - `git diff --check`
- Resultado: iteracion 8.1.2 estable, sin regresiones de tests y con mejor jerarquia visual para dashboard, CVs y ATS.
- Pendientes:
  - Validacion manual real del cierre de menus y del modal de duplicado en navegador interactivo.
  - PR hacia `development` cuando el usuario lo pida.

## Etapa 8.1.2.1 - Correccion fina visual final antes del PR

- Fecha: 2026-06-06
- Rama: `feature/ui-private-dashboard`
- Objetivo: cerrar el pulido visual fino del dashboard privado, listados, detalle de CV y modal ATS sin avanzar a la etapa 8.2.
- Modulos afectados: `dashboard`, `cvs`, `cover_letters`, `ats`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - Se corrigio el resumen del workspace para evitar cortes de palabras, centrar mejor las metricas y bajar el peso visual de `Postulaciones`.
  - Se mantuvieron las cards principales del dashboard con CTA de boton y se dejaron las miniaturas reales como backlog de la etapa 8.1.3.
  - Se formatearon fechas visibles de CVs y cartas a `dd/mm/yyyy HH:mm` y se alinearon como metadata secundaria.
  - Se pulieron `Exportacion` y `Ficha rapida` en el detalle del CV con spacing mas compacto, labels mas cortos y helper comun de templates.
  - Se refino el modal ATS con badge semantico, resumen rapido mas compacto y mejor alineacion de score, estado y longitud.
  - Se corrigio la cabecera de `Editar CV` para mostrar contexto del CV y de la persona tambien desde el flujo ATS.
  - Se documento explicitamente que miniaturas reales y selector de paletas quedan para la etapa 8.1.3, mientras que IA real queda para la etapa 8.3.
- Archivos principales:
  - `app/template_utils.py`
  - `app/main.py`
  - `app/routes/cvs.py`
  - `app/routes/cover_letters.py`
  - `app/routes/ats.py`
  - `app/routes/dashboard.py`
  - `app/templates/dashboard.html`
  - `app/templates/cvs/index.html`
  - `app/templates/cvs/detail.html`
  - `app/templates/cvs/form.html`
  - `app/templates/cover_letters/index.html`
  - `app/templates/ats/_analysis_sections.html`
  - `app/static/css/app.css`
  - `tests/test_ui_routes.py`
  - `tests/test_ats_routes.py`
- Validaciones previstas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d --force-recreate`
  - `docker compose ps`
  - `docker compose logs app --tail 80`
  - `docker compose exec app python -m pytest`
  - Validacion HTTP/DOM sobre dashboard, listados, detalle de CV y modal ATS
  - `git diff --check`
- Pendientes:
  - Validacion visual manual fina del modal ATS y del cierre real de menus con navegador interactivo.
  - PR hacia `development` cuando el usuario lo pida.

## Etapa 8.1.2.2 - Cierre visual definitivo antes del PR

- Fecha: 2026-06-06
- Rama: `feature/ui-private-dashboard`
- Objetivo: simplificar los componentes visuales que seguian cargados o desalineados antes de abrir PR.
- Modulos afectados: `dashboard`, `cvs`, `cover_letters`, `ats`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - Se reemplazo el resumen del workspace con cuadrados internos por una linea horizontal simple: `CVs`, `Cartas`, `Postulaciones`.
  - Se eliminaron los numeros grandes de las cards principales `Curriculum Vitae` y `Cartas de presentacion`.
  - Se elimino la CTA duplicada `Nueva carta` dentro de recientes; las altas quedan en las acciones rapidas superiores.
  - `Herramientas avanzadas` en CVs paso a verse como boton secundario, manteniendo `Importar JSON` dentro de la seccion colapsable.
  - Se ajustaron fecha y metadata de CVs/cartas para mantener formato `dd/mm/yyyy HH:mm` sin competir con los botones.
  - Se separaron las acciones secundarias de `Exportacion` y se mantuvieron labels cortos en `Ficha rapida`.
  - Se reordeno `Estado general` en el modal ATS con badge semantico arriba, score destacado y longitud estimada debajo.
  - Se limpio el subtitulo contextual de `Editar CV` desde ATS con formato `titulo - persona`.
- Pendientes:
  - Validacion visual manual final antes de PR.
  - Miniaturas reales de PDF y selector de paletas quedan fuera de esta etapa.

## Etapa 8.1.2.3 - Micro-ajuste final visual antes del PR

- Fecha: 2026-06-06
- Rama: `feature/ui-private-dashboard`
- Objetivo: aplicar ajustes visuales puntuales sin tocar componentes ya aprobados.
- Modulos afectados: `dashboard`, `cvs`, `cover_letters`, `ats`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - Se redujo el alto del resumen del workspace manteniendo el formato simple `CVs | Cartas | Postulaciones`.
  - Se reforzo el contraste de los numeros del resumen en dark mode mediante el color de acento existente.
  - Se actualizo el formato visible de fechas a `dd/mm/yyyy HH:mm hs`.
  - Se reubico `Actualizado`/`Actualizada` debajo de los datos principales en los listados de CVs y cartas.
  - Se mantuvieron los encabezados de `Exportacion` y `Ficha rapida` coherentes y se bajo levemente el bloque de acciones secundarias.
  - Se agrando el badge de estado ATS y se agrego una referencia breve de score debajo de la longitud estimada.
  - El formulario de edicion de CV ahora usa la persona o titulo del CV como H1 principal y deja `Editar CV` como contexto.
- Pendientes:
  - Validacion visual manual final de estos puntos antes de PR.

## Etapa 8.1.2.4 - Cierre de ultimos detalles visuales antes del PR

- Fecha: 2026-06-06
- Rama: `feature/ui-private-dashboard`
- Objetivo: cerrar gaps visuales puntuales sin tocar logica, DB ni backlog ya diferido.
- Modulos afectados: `cvs`, `ats`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - Se reforzo el mismo acento visual entre `Exportacion` y `Ficha rapida` en el detalle del CV.
  - Se corrigio la vista `Ver TEX` para mantener `Export Engine` dentro del mismo layout y mejorar el comportamiento de titulos largos.
  - `Estado general` del ATS conserva score, badge y longitud, pero ahora muestra una referencia vertical mas legible.
  - Se agrego la referencia real de longitud ATS usando el rango existente en codigo (`280` a `4500` caracteres).
  - Se mantuvo intacto `Resumen rapido` y no se tocaron reglas de scoring.
- Pendientes:
  - Validacion visual manual final del bloque `Ver TEX` y del modal ATS antes de abrir PR.

## Etapa 8.1.2.5 - ATS integrado al flujo principal de Curriculum Vitae

- Fecha: 2026-06-07
- Rama: `feature/ui-private-dashboard`
- Objetivo: acercar ATS al modulo `Curriculum Vitae` y reducir scroll del reporte, sin tocar DB ni logica de scoring.
- Modulos afectados: `cvs`, `ats`, `layout`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - El listado de CVs ahora calcula ATS en runtime para cada fila y muestra un badge semantico reutilizando `ats_service`.
  - El badge ATS abre el modal del reporte sin salir del flujo de `CVs`, manteniendo tambien `Analizar ATS` dentro de `Mas acciones`.
  - La sidebar degrada el acceso a ATS como `ATS directo`, dejando `Curriculum Vitae` como flujo principal recomendado.
  - El reporte ATS se compacta con checklist mas bajo, menos padding y bloques de feedback mas discretos.
  - Las rutas `/ats/` y `/ats/cvs/{id}` siguen vigentes para acceso directo y compatibilidad.
- Pendientes:
  - Validacion visual manual del badge ATS en varias densidades de datos antes del PR.

## Etapa 8.1.2.6 - Cierre visual de ATS integrado en Curriculum Vitae

- Fecha: 2026-06-07
- Rama: `feature/ui-private-dashboard`
- Objetivo: cerrar la integracion visual de ATS dentro de `CVs` y reducir scroll del modal sin tocar scoring ni DB.
- Modulos afectados: `layout`, `cvs`, `ats`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - Se elimina la entrada lateral separada `ATS directo` y se renombra el acceso principal a `Curriculum Vitae + ATS`.
  - El badge ATS baja desde la esquina superior al bloque de metadata del CV para quedar alineado con email y fecha.
  - El modal ATS reduce paddings y altura util en `Estado general`, `Resumen rapido`, checklist y feedbacks.
  - Las rutas `/ats/` y `/ats/cvs/{id}` siguen accesibles por URL para compatibilidad y validacion directa.
- Pendientes:
  - Validacion visual manual del ajuste fino de densidad en el modal ATS antes del PR.

## Etapa 8.1.2.8 - Ajuste final de posicion del badge ATS

- Fecha: 2026-06-07
- Rama: `feature/ui-private-dashboard`
- Objetivo: dejar el badge ATS asociado al titulo del CV sin redisenar el resto del listado.
- Modulos afectados: `cvs`, `static`, `tests`, `docs`.
- Resumen de cambios:
  - El badge ATS deja la metadata inferior y pasa a la fila del titulo del CV.
  - Se habilita wrap prolijo entre titulo largo y badge, manteniendo el nombre de persona debajo.
  - El badge sigue clickeando al modal y `Analizar ATS` se conserva en `Mas acciones`.

## Fix ATS - Critical Sections Status Cap

- Fecha: 2026-06-04
- Rama: `feature/ats-basic-check`
- Objetivo: impedir que CVs con secciones core faltantes queden clasificados como `Bueno`.
- Modulos afectados: `ats_service`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego deteccion de `critical_missing_sections`.
  - El score queda capado a `84` si falta una seccion critica.
  - Si faltan experiencia y educacion juntas, el score queda capado a `59` y el estado pasa a `Insuficiente`.
  - Se ampliaron los tests para cubrir CV completo, CV con experiencia sin educacion, CV con educacion sin experiencia, CV largo sin ambas y CV incompleto.
- Resultado: el status ATS ahora es consistente con recomendaciones y advertencias.

## Etapa 6 - ATS Basic Check

- Fecha: 2026-06-04
- Rama: `feature/ats-basic-check`
- Objetivo: agregar un chequeo ATS basico sobre CVs existentes con score simple, checklist, advertencias y recomendaciones sin IA.
- Modulos afectados: `ats`, `cvs`, `dashboard`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego `app/services/ats_service.py` con reglas deterministicas de validacion basica.
  - Se creo la ruta `app/routes/ats.py` para analizar CVs existentes sin mezclar la logica en `cvs.py`.
  - Se agrego un template dedicado bajo `app/templates/ats/`.
  - Se incorporo la accion `Analizar ATS` en el detalle del CV.
  - Se actualizaron dashboard, README, module index y logs a `0.7.0`.
  - Se agregaron tests del servicio ATS y una prueba basica de ruta.
  - Se agrego `httpx` a `requirements.txt` para soportar `TestClient` en los tests de rutas.
- Archivos principales:
  - `app/services/ats_service.py`
  - `app/routes/ats.py`
  - `app/templates/ats/cv_analysis.html`
  - `app/templates/cvs/detail.html`
  - `tests/test_ats_service.py`
  - `tests/test_ats_routes.py`
  - `docs/development/ATS_BASIC_CHECK.md`
- Validaciones ejecutadas:
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Analisis ATS de un CV completo
  - Analisis ATS de un CV incompleto
  - Verificacion visual de checklist, score, recomendaciones y advertencias
  - `git diff --check`
- Resultado: etapa implementada y validada localmente. El chequeo ATS queda operativo solo sobre CVs guardados y sin dependencias externas.
- Pendientes:
  - Esperar validacion explicita del usuario antes de cualquier merge.
  - Preparar push de la rama feature y PR hacia `development`.
  - Pedir `@codex review` manual despues del PR.

## Fix P1 - Cap cover-letter export filenames

- Fecha: 2026-06-04
- Rama: `feature/cover-letters`
- Objetivo: corregir el hallazgo P1 de Code Review que permitia generar filenames demasiado largos en exportaciones TEX/PDF de cartas.
- Modulos afectados: `export_service`, `latex_service`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego un helper comun para construir filenames sanitizados y capped.
  - Se acoto a `180` caracteres el filename final de exportaciones de cartas.
  - Se aplico el mismo criterio al `.tex` generado de cover letters.
  - Se mantuvo unicidad mediante `id` y timestamp en exportaciones persistidas.
  - Se agregaron tests para `company` y `position` de `160` caracteres.
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Creacion de carta con `company` y `position` al maximo permitido
  - Export TEX por HTTP
  - Export PDF por HTTP
  - Verificacion de artefactos persistidos en `/data/exports`
  - Validacion basica con `pdftotext`
  - `git diff --check`
- Resultado: fix aplicado. TEX y PDF de cartas con nombres extremos exportan correctamente sin `OSError` y los filenames finales quedan en `180` caracteres.
- Pendientes:
  - Actualizar PR #2 con el commit del fix.
  - Esperar nueva revision manual antes de merge.

## Etapa 7 - Pulido final del MVP

- Fecha: 2026-06-04
- Rama: `feature/mvp-final-polish`
- Objetivo: cerrar el MVP local con una pasada de consistencia visual, navegacion clara, documentacion operativa y validacion funcional completa.
- Modulos afectados: `dashboard`, `ats`, `cvs`, `cover_letters`, `applications`, `docs`, `docker`, `tests`.
- Resumen de cambios:
  - Se agrego una entrada dedicada `ATS` en la navegacion superior y una vista `GET /ats/` para seleccionar CVs a analizar.
  - Se ajustaron textos visibles del dashboard, ATS, Cartas y Postulaciones para mantener naming consistente.
  - La version visible del layout ahora usa `request.app.version` para evitar drift con `APP_VERSION`.
  - Se actualizo la version del proyecto a `0.8.0`.
  - Se actualizo `README.md` con arranque, detencion, rebuild, tests, persistencia, exports y backup/restore basicos.
  - Se creo `docs/development/MVP_VALIDATION.md` como checklist manual del MVP.
  - Se alinearon `MODULE_INDEX.md`, `VERSIONING.md`, `BRANCH_STRATEGY.md` y docs de modulos al baseline del MVP.
- Archivos principales:
  - `app/routes/ats.py`
  - `app/routes/dashboard.py`
  - `app/templates/layout.html`
  - `app/templates/dashboard.html`
  - `app/templates/ats/index.html`
  - `app/templates/ats/cv_analysis.html`
  - `README.md`
  - `docs/development/MVP_VALIDATION.md`
  - `docs/development/MODULE_INDEX.md`
  - `tests/test_ats_routes.py`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Requests HTTP a dashboard, `/ats/`, `/cvs/`, `/cover-letters/` y `/applications/`
  - Creacion, edicion y detalle de CV de prueba
  - Exportacion TEX/PDF/JSON de CV e importacion JSON
  - Creacion, edicion, detalle y exportacion TEX/PDF de carta
  - Creacion, edicion, detalle y asociaciones de postulacion
  - Analisis ATS sobre CV completo e incompleto
  - Verificacion de `/data/exports` y extraccion PDF con `pdftotext`
  - `git diff --check`
- Resultado: MVP local validado con Docker Compose, `pytest` en verde y flujos principales accesibles desde dashboard y header.
- Pendientes:
  - Crear PR hacia `development`.
  - Pedir `@codex review` manual.
  - Esperar validacion explicita antes de merge.

## Etapa 5 - Application Tracker

- Fecha: 2026-06-04
- Rama: `feature/application-tracker`
- Objetivo: implementar el modulo de seguimiento de postulaciones con CRUD basico, estados y asociaciones opcionales a CV y carta.
- Modulos afectados: `applications`, `database`, `dashboard`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego el modelo `Application` y el schema `ApplicationFormData`.
  - Se creo la tabla SQLite `applications` con eliminacion logica y asociaciones opcionales a CV y cover letter.
  - Se implemento el repositorio `application_repository.py`.
  - Se agregaron rutas FastAPI para listar, crear, ver detalle, editar, confirmar eliminacion y eliminar postulaciones.
  - Se agregaron templates HTML bajo `app/templates/applications/`.
  - Se agrego navegacion a `Postulaciones` desde dashboard y header.
  - Se agregaron estados permitidos y validaciones de fechas, URL y asociaciones.
  - Se agrego documentacion especifica del modulo y se actualizo la version a `0.6.0`.
- Archivos principales:
  - `app/models.py`
  - `app/schemas.py`
  - `app/database.py`
  - `app/repositories/application_repository.py`
  - `app/routes/applications.py`
  - `app/templates/applications/index.html`
  - `app/templates/applications/form.html`
  - `app/templates/applications/detail.html`
  - `app/templates/applications/confirm_delete.html`
  - `app/validations/application_validations.py`
  - `docs/development/APPLICATION_TRACKER.md`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Requests HTTP a listado, formulario, detalle y borrado
  - Creacion de CV y carta base para asociaciones
  - Creacion, edicion y eliminacion de postulacion
  - Cambio de estado y validacion de persistencia
- Resultado: etapa implementada y validada localmente. El modulo de postulaciones queda operativo, visible en dashboard y vinculado a CVs y cartas activas.
- Pendientes:
  - Esperar validacion explicita del usuario antes de cualquier merge.
  - Preparar push de la rama feature y PR hacia `development`.
  - Pedir `@codex review` manual despues del PR.

## Etapa 9.9 - Aislamiento de pruebas independiente de Docker

- Fecha: 2026-10-11
- Rama: `fix/test-data-isolation` (desde `development` `97e2577`, sin push)
- Objetivo: que ninguna corrida de pruebas pueda modificar la base de datos o los artefactos del entorno normal de la aplicacion.
- Causa raiz: no existia `tests/conftest.py`. El aislamiento provenia del runner de Docker (workspace de solo lectura y tmpfs sobre `data`), no del codigo. Ademas `DOCUMENTATION_BUILD_DIR` era una constante de modulo sobre `REPO_ROOT` que ignoraba `APP_DATA_DIR`, y nueve de los veinte archivos de test nunca parcheaban la variable.
- Alcance ejecutado:
  - `tests/conftest.py`: temporal unico, `APP_DATA_DIR` y marcador `CV_LATEX_TESTING=1` en tiempo de importacion, y verificacion fail-closed que aborta la sesion antes de escribir si la resolucion no cae en el temporal.
  - `app/database.py`: `get_data_dir()` rechaza el directorio de datos del repositorio bajo marcador o con `pytest` importado, sin alterar el comportamiento normal.
  - `app/services/documentation_service.py`: `DOCUMENTATION_BUILD_DIR` pasa a `get_documentation_build_dir()`, derivado de `get_data_dir()` y evaluado en la llamada.
  - `tests/test_test_isolation.py`: once pruebas que demuestran que la corrida escribe solo en el temporal y que la guardia aborta.
- Evidencia (CMD-092 y CMD-093): suite completa **sin `APP_DATA_DIR`** en el entorno con `240 passed, 1 warning`; manifiesto recursivo de `data/` identico antes y despues; cero temporales huerfanos; `compileall` y `diff --check` en exit 0.
- Diagnostico de Docker: WSL2 con systemd activo; el motor es Docker Desktop del lado Windows y no esta corriendo. El contexto activo apunta a un socket unix sin demonio escuchando y el contexto `desktop-linux` a un named pipe de Windows inaccesible desde WSL. Sin sudo y sin instalar motor nativo, no se puede resolver desde esta sesion.
- Pendiente: cuando Docker vuelva a estar disponible, reejecutar la suite en la imagen para confirmar el mismo resultado por la segunda via. LL-023 queda superada por LL-025.
