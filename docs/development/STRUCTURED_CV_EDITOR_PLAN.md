# Structured CV Editor Plan

## Objetivo

Planificar la implementacion futura del editor estructurado de CV sin tocar codigo funcional en Etapa 9.0. Este documento define subetapas, alcance, archivos probables, validaciones, criterios de aceptacion y limites.

## Estado de Etapa 9.0

- Estado: diseno tecnico solamente.
- No implementa editor.
- No cambia DB.
- No crea migraciones.
- No toca rutas funcionales, templates productivos, renderer LaTeX/PDF, import/export JSON ni ATS scoring.
- Documento arquitectonico asociado: `docs/adr/ADR-0003-structured-cv-editor.md`.

## Estado de Etapa 9.1

- Estado: fundacion de persistencia y compatibilidad minima.
- Agrega columnas idempotentes en `cvs`: `structured_schema_version`, `structured_payload` y `structured_payload_status`.
- La migracion preserva `/data/app.db` y no depende solo de `CREATE TABLE IF NOT EXISTS`; tambien usa `PRAGMA table_info(cvs)` y `ALTER TABLE ADD COLUMN` condicionado.
- No cambia UI, templates productivos, render LaTeX/PDF, export JSON visible ni ATS scoring.
- Los consumidores actuales siguen usando campos legacy hasta una etapa posterior de representacion normalizada.

## Estado de Etapa 9.2

- Estado: servicios internos de payload estructurado y reglas de escritura segura.
- Define schema minimo v2 para `structured_payload` con `personal`, `contact`, `summary`, `skills`, `experience`, `education`, `certifications`, `languages`, `projects`, `links` y `metadata`.
- Agrega conversion legacy -> payload v2, validacion, serializacion, deserializacion y helpers de columnas para estados `legacy`, `valid`, `invalid` y `stale`.
- La validacion v2 es backward-compatible con payloads parciales previamente aceptados: si faltan secciones opcionales, el servicio las normaliza con defaults vacios sin subir a schema `3`.
- Si la fila ya declara `structured_schema_version = 2`, un payload v2 sin `schema_version` interno se normaliza agregando `schema_version = 2`; si el campo existe y no es integer, el payload sigue siendo invalido.
- `update_cv()` regenera payload desde campos legacy cuando el CV existente ya era estructurado; si no puede regenerar, vuelve a legacy canonico.
- `duplicate_cv()` mantiene la regla de preservar payload valido solo cuando el contenido copiado no cambia.
- No cambia UI, templates productivos, render LaTeX/PDF, export JSON visible, import JSON visible ni ATS scoring.

## Estado de T2 - contrato normalizado v2 y escritura estructurada

- Estado: implementado sobre la Etapa 9.2 con tests enfocados y suite completa en verde. Sin commits por restriccion explicita del usuario.
- `app/validations/structured_cv_validations.py` es el contrato unico de validacion/normalizacion del payload v2; `structured_cv_service` delega en el y reexporta su API publica.
- `resolve_normalized_cv(cv)` devuelve la representacion normalizada unica `NormalizedCV` con:
  - `mode`/`is_structured`/`reason`: resolucion de fuente canonica.
  - `sections`: forma completa v2 siempre disponible, desde payload estructurado valido o derivada de campos legacy (`build_structured_sections_from_legacy`, proyeccion de lectura sin timestamps de sincronizacion).
  - `legacy_snapshot`: proyeccion plana (`CVFormData`) para rutas, LaTeX/PDF y ATS existentes.
  - Ningun consumidor debe leer `structured_payload` y campos planos por separado; todos deben pedir `NormalizedCV`.
- Solo schema 2 explicito con estado `valid` y payload validado es canonico estructurado; versiones futuras (3+) o invalidas caen 100% a legacy y nunca se tratan como 2.
- Compatibilidad 9.2 conservada: payloads parciales aceptados con defaults vacios; payload sin `schema_version` interno con version de fila 2 se normaliza a 2; `schema_version` no entero es invalido.
- Validacion acotada por campo y seccion:
  - `personal`: `full_name` 160, `headline` 160 (titulo profesional), `location` 160.
  - `contact`: `email` 180, `phone` 80, `links` lista de strings (300 c/u, maximo 10).
  - `summary`: string 1200.
  - `skills`: items con `label` 120, `category` 80, `level` 80; maximo 40 items.
  - `experience`: items con `company` 120, `role` 120, `location` 120, `start_date` 40, `end_date` 40, `current` booleano, `summary` 600, `highlights` (240 c/u, maximo 12), `technologies` (60 c/u, maximo 16); maximo 30 items.
  - `education`: items con `institution` 160, `degree` 160, `field` 120, `start_date` 40, `end_date` 40, `summary` 600; maximo 30 items.
  - `certifications`: items con `name` 160, `issuer` 120, `date` 40; maximo 30 items.
  - `languages`: items con `name` 60, `level` 60; maximo 20 items.
  - `projects`: items con `name` 160, `summary` 600, `link` 300, `technologies` (60 c/u, maximo 16); maximo 30 items.
  - `links`: items con `label` 80, `url` 300; maximo 30 items.
  - `additional_info` (informacion adicional): items con `title` 120, `content` 600; maximo 20 items.
  - `metadata`: `source` 60, `synced_from_legacy_at` 60.
  - `order` entero (bool rechazado), autocompletado con la posicion cuando falta.
  - El payload serializado no puede superar 512 KB (`MAX_STRUCTURED_PAYLOAD_BYTES`).
  - Las claves extra dentro de items, secciones y nivel superior se preservan sin validar para no perder campos solo-estructurados.
- Escritura estructurada:
  - `build_structured_cv_write_bundle(title, payload, metadata_source)` valida el payload, estampa `metadata.source`/`synced_from_legacy_at`, deriva el snapshot legacy y lo valida con `validate_cv_form` antes de serializar. Cualquier fallo lanza `StructuredCVWriteError` con errores accionables.
  - `create_structured_cv`/`update_structured_cv` persisten campos legacy y columnas estructuradas en una sola sentencia atomica; un CV legacy actualizado por este flujo queda estructurado. No hay escritura parcial ante errores.
- Reglas del snapshot legacy (explicitas, sin truncamiento silencioso):
  - `personal.full_name` -> `full_name`; `contact.email`/`phone` -> `email`/`phone`; `summary` -> `professional_summary`.
  - `skills`: labels unidos con `", "` respetando `(order, posicion)`.
  - `experience`: bloques `Role - Company (inicio - fin/Presente)` con `summary`, bullets `• highlight` y linea `Tecnologias: ...`; unidos por linea vacia.
  - `education`: bloques `Titulo - Institucion (inicio - fin)` con `Campo: ...` y `summary`.
  - `headline`, `certifications`, `languages`, `projects`, `links`, `additional_info` y `metadata` son solo-estructurados: viven en el payload y el snapshot no los destruye.
  - Si el snapshot derivado excede los limites legacy, la escritura se rechaza con error por campo; nunca se trunca contenido.
- Duplicate, update legacy e import schema 1 mantienen las reglas 9.2 vigentes (payload preservado al duplicar; regeneracion o vuelta a legacy canonico al editar legacy).

## Estado de T3 - import/export JSON schema 2 con compatibilidad schema 1

- Estado: implementado sobre T2 con tests enfocados y suite completa en verde. Sin commits por restriccion explicita del usuario.
- Export JSON canonico via `resolve_normalized_cv` (fuente unica, sin mezcla):
  - Un CV estructurado valido exporta un envelope schema 2 lossless con `schema_version`, `exported_at`, `source_cv_id` y `cv` conteniendo `title` mas `structured_payload` completo: todas las secciones soportadas, claves extra, `order` y `metadata` se preservan tal cual estan en el payload canonico.
  - CVs legacy, con payload invalido, stale o de version futura exportan schema 1 plano desde el snapshot legacy canonico; nunca se mezclan payload y campos planos en un mismo export.
  - `export_cv_json`/`build_cv_json_payload` aceptan `schema_version` explicito: `1` fuerza el export plano de un CV estructurado (desde el snapshot derivado) para compatibilidad; `2` sobre un CV no estructurado se rechaza con error 400; cualquier otro valor o booleano se rechaza sin downcast.
  - El filename del export schema 2 usa la variante `cv-schema2` para trazabilidad visual.
- Import JSON con gate estricto de version:
  - Nueva entrada estructurada `build_cv_json_import_result(raw_content)` que devuelve `CVJsonImportResult(schema_version, form_data | structured_title + structured_payload)`.
  - `schema_version` ausente o explicito 1 mantiene el flujo legacy exacto: sufijo `(importado)`, validaciones vigentes y creacion de un CV NUEVO en modo legacy canonico via `create_cv`.
  - `schema_version` 2 explicito valida tipos y limites con el contrato unico v2 (traduciendo los codigos de error a mensajes accionables en espanol), exige `cv.structured_payload` como objeto y `title` como texto, aplica el sufijo `(importado)` y crea un CV NUEVO estructurado via `create_structured_cv(metadata_source="json_import")`, preservando el payload completo en lugar de aplanarlo a `CVFormData`. Los limites de titulo y del snapshot legacy los valida el bundle T2 antes de persistir, sin escrituras parciales.
  - Versiones explicitas no soportadas, no enteras o booleanas se rechazan al resolver la version, antes de extraer contenido del CV; nunca se hace downcast a schema 1.
  - `build_cv_form_data_from_json` se conserva para callers legacy: acepta schema 1 explicito o ausente y rechaza schema 2 explicito para no descartar contenido solo-estructurado.
  - El limite de 512 KB se aplica por streaming (`read_limited_upload_bytes`) antes del parseo para ambos schemas, y el payload serializado sigue limitado por `MAX_STRUCTURED_PAYLOAD_BYTES` dentro de la escritura T2.
- UI (cambio aditivo minimo, sin editor):
  - El detalle de un CV estructurado agrega el enlace "Descargar JSON plano (schema 1)" apuntando a `/cvs/{id}/export/json?schema_version=1`.
  - El panel de import del listado documenta que acepta JSON schema 1 (plano) y schema 2 (estructurado) y que la importacion siempre crea un registro nuevo.
- Decision sobre import schema 1: se mantiene la creacion de CV nuevo en modo legacy canonico (opcion admitida por ADR-0003: "dejar el registro en modo legacy canonico"); la derivacion inmediata de payload desde imports schema 1 queda fuera de T3 y solo se retomara si el editor estructurado la exige. La importacion jamas sobrescribe el CV de origen (`source_id`) ni registros existentes.
- Tests: `tests/test_cv_json_schema2.py` (nuevo) cubre envelope lossless, fallback legacy sin mezcla, export explicito schema 1/2, gate de versiones, errores accionables en espanol, limites, roundtrip estructurado completo, creacion de CV nuevo sin sobrescribir el origen y las rutas HTTP de export/import/detalle; se suman casos de version explicita en `tests/test_export_service.py` y de copy de UI en `tests/test_ui_routes.py`.

## Estado de T4 - editor estructurado completo y orden de items

- Estado: implementado sobre T2/T3 con tests enfocados, suite completa y prueba real de navegador en verde. Sin commits por restriccion explicita del usuario. Verificacion independiente del contrato de persistencia pendiente (acordada con el padre).
- Rutas aditivas (sin sombrear rutas existentes):
  - `GET/POST /cvs/new/structured` (`cvs_new_structured`, `cvs_create_structured`): creacion estructurada desde cero.
  - `GET/POST /cvs/{cv_id}/structured-edit` (`cvs_structured_edit`, `cvs_structured_update`): edicion estructurada de cualquier CV activo; declaradas antes de las rutas dinamicas genericas.
  - Enlaces aditivos: "Crear CV estructurado" en el listado y "Editar estructurado" en el detalle; los flujos legacy siguen intactos.
- Servicio nuevo `app/services/structured_cv_editor_service.py`:
  - Bootstrap canonico unicamente via `resolve_normalized_cv`: CV estructurado valido edita desde su payload completo (con claves desconocidas); legacy/invalido/stale/futuro bootstrapea integramente desde campos legacy con advertencia explicita en espanol (motivo, conversion al guardar, limites por campo).
  - Parseo del envio: rechaza payload ausente (mensaje de JavaScript requerido), no-JSON, no-objeto y mayor a 512 KB antes de tocar el repositorio.
  - Traduce codigos del contrato v2 a espanol accionable reutilizando el traductor de import T3, anade mensajes exactos con limites concretos (p.ej. `summary_too_long`) y etiqueta en espanol los errores de snapshot legacy (p.ej. `title:` -> `Titulo interno:`).
  - Rerender de envios fallidos con el payload tal como lo envio el usuario (incluidas claves desconocidas) y el estado de advertencia del CV subyacente.
- Editor de cliente `app/static/js/structured_editor.js` (UMD; API pura testeable en Node + montaje DOM):
  - Estado inicial desde `<script id="structured-editor-bootstrap" type="application/json">` serializado con `| tojson` (escapado seguro); sin `innerHTML` con datos del usuario: solo nodos DOM, `textContent` y `value`.
  - Items de 8 secciones con agregar/quitar/subir/bajar; renumeracion densa 1..n en cada mutacion y en el submit; checkbox de trabajo actual; listas por linea para logros, tecnologias y links de contacto.
  - Merge final que preserva claves desconocidas de payload, secciones e items; metadata intacta (el servidor la re-estampa); nunca baja versiones de schema.
  - Limites de items y `maxlength` como guia UX; la validacion real es 100% servidor (write bundle T2, sin escrituras parciales).
- Template `app/templates/cvs/structured_form.html` con UI 100% espanol: datos personales/contacto, titulo profesional, resumen, experiencia, educacion, skills, certificaciones, idiomas, proyectos, links, informacion adicional e informacion interna (metadata de solo lectura con nota de procedencia server-owned); `noscript` con advertencia propia (clase `structured-noscript-warning`).
- Reglas de seguridad y compatibilidad verificadas:
  - CVs legacy, invalidos, stale o de version futura: bootstrap 100% desde campos legacy y advertencia; guardar convierte explicitamente y reemplaza datos estructurados previos no disponibles.
  - CVs estructurados validos jamas se regeneran desde campos planos.
  - Envios con version futura se rechazan sin downcast; errores accionables sin escrituras parciales.
- Tests:
  - `tests/test_structured_cv_editor.py` (nuevo, 21 pruebas TestClient): render de secciones y bootstrap, creacion con provenance, titulo obligatorio sin escrituras parciales, JSON invalido/ausente/oversize, version futura, limites de snapshot, bootstrap canonico con claves desconocidas, advertencia legacy, fallback invalido/stale/futuro, orden persistido, edicion sin cambios preserva extensiones, rerender 422 preserva lo ingresado sin mutar lo guardado, conversion legacy, 404, XSS escapado, roundtrip editor -> export schema 2 -> import, compatibilidad de rutas legacy y enlaces de UI.
  - `tests/test_structured_cv_editor_js.js` (nuevo): 8 tests unitarios Node del contrato puro + 4 flujos reales de browser via CDP directo sobre chromium headless (sin dependencias npm): flujo completo con orden persistido en DB, submit fallido preservando datos con error en espanol, no-ejecucion de payloads maliciosos y conversion legacy con advertencia.

## Estado de T5 - representacion normalizada en LaTeX/PDF y ATS

- Estado: implementado sobre T2/T3/T4 con tests enfocados, suite completa y prueba real de PDFs/HTTP en verde. Sin commits por restriccion explicita del usuario. Verificacion independiente pendiente (acordada con el padre); el checkbox de T5 en el documento ODD queda deliberadamente sin marcar hasta esa verificacion.
- Servicio nuevo `app/services/structured_cv_rendering.py` como unico punto de conversion desde `NormalizedCV`:
  - `build_structured_cv_latex_context(normalized)`: contexto LaTeX enriquecido para las 4 plantillas desde las secciones v2 (fullname, headline con fallback al titulo interno, email/telefono/ubicacion/links de contacto, resumen, experiencia con rol - empresa, fechas con Presente, ubicacion, resumen, bullets y Tecnologias, educacion con Campo, skills como `label (categoria, nivel)`, certificaciones, idiomas, proyectos con link y Tecnologias, links e informacion adicional).
  - `build_structured_ats_text(normalized)`: extraccion de texto plano con TODO el contenido soportado (incluye solo-estructurados; excluye metadata interna); para un payload derivado de campos legacy degenera exactamente en la estimacion legacy, garantizando equivalencia canonica de scoring.
  - Orden consistente por `(order, posicion)` con la misma semantica que el snapshot T2; items minimos no generan secciones ni entradas vacias; todo texto pasa por `sanitize_latex_text`.
- `latex_service.generate_cv_tex_document` resuelve la fuente con `resolve_normalized_cv` y bifurca: estructurado valido -> contexto enriquecido desde el payload (aun con snapshot legacy obsoleto); cualquier otro caso -> camino flat previo. El TEX legacy es byte-identico al pre-T5 en las 4 plantillas (verificado contra HEAD).
- Plantillas `classic/modern/compact/tech`: rama `entries` (headline/meta/cuerpo/bullets) con estilizacion minima por plantilla; guardias de agrupacion solo estructurados (`keep_with_next` + `use_needspace`): `\Needspace*{4\baselineskip}` antes de titulos (compact/modern/tech), `\par\nopagebreak` post-colorbox (tech) y `\nopagebreak` vertical post-`\section*` (classic). Evidencia determinista: `\\*` y `\par\nobreak` NO evitan el corte titulo->itemize (el itemize inserta `\@beginparpenalty`); `\Needspace*` si. El huerfano real de "Links" en compact se detecto en PDF real y se corrigio.
- ATS sin nuevos criterios: los 6 campos de scoring derivan del snapshot legacy proyectado; `total_characters` usa la extraccion normalizada completa; 7 criterios/pesos/topes/umbrales/estados y resultados legacy intactos; equivalencia exacta legacy vs estructurado convertido (dataclass completo) probada, incluido el caso vacio.
- Metadata interna (`metadata.source`, `synced_from_legacy_at`, `schema_version`) y claves de extension desconocidas nunca se renderizan en TEX/PDF/ATS (persistencia intacta); probado con payloads con `\end{document}` malicioso y caracteres `& % $ # _ { } ~ ^`.
- Tests: `tests/test_structured_cv_consumers.py` (nuevo: 4 plantillas, no-mix con snapshot obsoleto, orden, escape, linebreaks/secciones vacias, no-leak de metadata/extensiones, fallback byte-equal corrupt/stale/invalid/future, ATS canonico y no-mix, longitud con solo-estructurados, fuente compartida TEX/ATS); adiciones en `test_latex_service.py` (2), `test_ats_service.py` (3) y `test_pdf_service.py` (1, export PDF estructurado 4 plantillas con pdflatex simulado).
- Evidencia real: PDFs descargados por HTTP en runtime aislado (4x 200 application/pdf, 2 paginas A4, pdftotext completo sin leaks, SHA256 en COMMAND_LOG, PNGs en /tmp/cv-t5-proof/png, ATS HTTP 100/100 Bueno). RED 13/20 -> GREEN 33 -> suite 173 passed (1 warning preexistente).
- Correccion T5 (tokens largos, CMD-057..071): la inspeccion visual independiente confirmo desborde del margen derecho en las 4 plantillas (highlight de 200+ caracteres ininterrumpidos; header de modern overfull 27.71626pt). Fix solo-estructurado en `structured_cv_rendering.py`: `_structured_latex_text` sanitiza y luego interpola el separador confiable `\allowbreak \hspace{0pt plus 0.06em}` SOLO entre atomos ya sanitizados de tokens de 24+ atomos (secuencias de escape TeX indivisibles; palabras normales y TEX legacy intactos). Causas raiz cerradas con compilacion real: espacio de terminacion obligatorio de la macro (sin el, `\allowbreakt` es Undefined control sequence) y `\hspace` de ancho natural nulo con estiramiento minimo para que lineas sin pegamento propio justifiquen sin restos overfull. Evidencia: RED 4/36 + logs pre-fix (1183.32/27.71626+1015.92/992.16/1022.61pt) -> GREEN 40 focused/180 full (1 warning preexistente), 0 Overfull en los 4 logs finales, pdftotext con corrida A*200 completa y sin leaks, legacy byte-identico contra HEAD, 9 PNGs en /tmp/cv-t5-wrap-proof/png; classic quedo en 3 paginas (p3 resto legitimo).

## Mapa actual del modulo CV

### Estructura de datos actual

- Modelo `CV` en `app/models.py`.
- Schema `CVFormData` en `app/schemas.py`.
- Tabla SQLite `cvs` creada desde `app/database.py`.
- Campos planos: `title`, `full_name`, `email`, `phone`, `professional_summary`, `experience_summary`, `education_summary`, `skills`, `created_at`, `updated_at`, `deleted_at`.

### Persistencia

- `create_cv()` inserta campos planos.
- `update_cv()` actualiza campos planos y `updated_at`.
- `list_cvs()` y `get_cv()` filtran `deleted_at IS NULL`.
- `soft_delete_cv()` marca `deleted_at` y no borra fisicamente.

### Duplicado

- `duplicate_cv()` lee el CV fuente, crea `CVFormData`, aplica `build_duplicate_title()` y reutiliza validaciones.

### Import/export JSON

- `export_cv_json()` genera schema `1` con objeto `cv` plano.
- `build_cv_form_data_from_json()` acepta `{"cv": ...}` o payload plano, normaliza campos permitidos, agrega sufijo `(importado)` y valida.
- Upload JSON limitado a `512 KB`, leido por chunks.

### TEX/PDF

- `latex_service.py` genera contexto LaTeX desde `CV` plano.
- `professional_summary`, `experience_summary` y `education_summary` se vuelven secciones.
- `skills` se divide con `split_sanitized_items()`.
- `pdf_service.py` compila con `pdflatex` en temporal controlado bajo `/data/exports/_tmp`.

### ATS

- `ats_service.py` calcula score desde campos planos.
- Evalua email, telefono, resumen, experiencia, educacion, skills y longitud estimada.
- Penaliza secciones criticas faltantes.

### Tests actuales relacionados

- `tests/test_cv_repository.py`: duplicado con titulo al limite.
- `tests/test_export_service.py`: export TEX, export/import JSON, limite de upload y filenames.
- `tests/test_latex_service.py`: TEX CV, plantillas y mapeo de texto PDF.
- `tests/test_pdf_service.py`: PDF export y errores de compilacion.
- `tests/test_ats_service.py`: score ATS para CVs completos/incompletos.
- `tests/test_ats_routes.py`: paginas y modal ATS.
- `tests/test_ui_routes.py`: listado, detalle, TEX preview, edicion y borrado seguro.

## Limitaciones actuales

- Experiencia y educacion son bloques monoliticos.
- Skills es texto libre dividido tarde para LaTeX.
- No hay items reordenables.
- Validaciones son por campo plano, no por item/seccion.
- Export/import JSON no tiene schema estructurado.
- LaTeX/PDF y ATS dependen de campos planos.
- Dividir automaticamente texto libre en items podria perder informacion.

## Arquitectura recomendada

Usar transicion hibrida:

- Mantener campos planos.
- Agregar payload JSON estructurado versionado en etapa futura.
- Centralizar conversion en un servicio nuevo.
- Mantener schema JSON `1` como compatibilidad.
- Introducir schema JSON `2` cuando exista payload estructurado.
- Adaptar consumidores mediante representacion normalizada antes de tocar templates o scoring.

## Fuente canonica y stale data

Regla obligatoria para las etapas futuras:

- Si `structured_payload` es valido y `structured_schema_version >= 2`, el payload estructurado es la fuente canonica.
- Si no hay payload valido, los campos planos legacy son la fuente canonica.
- Los campos planos se mantienen como snapshot derivado para compatibilidad, no como fuente paralela cuando el payload estructurado es valido.
- Render, export JSON schema `2`, LaTeX/PDF y ATS deben consumir una representacion normalizada desde el servicio estructurado.
- Ningun consumidor debe leer `structured_payload` y campos planos por separado.

Decision operativa recomendada:

- Cuando un CV estructurado se edite por el flujo legacy, regenerar `structured_payload` desde los campos legacy en la misma operacion logica.
- Marcar metadata de sincronizacion del payload, por ejemplo `source = "legacy_edit"` y `synced_from_legacy_at`.
- Si la regeneracion falla, limpiar o ignorar el payload y dejar el CV en modo legacy canonico para evitar usar contenido stale.
- No bloquear el flujo legacy en la primera etapa funcional, porque eso agregaria friccion y riesgo para CVs existentes.

Regla para import schema `1`:

- Un import schema `1` debe crear un CV nuevo desde campos planos y derivar payload estructurado si la version ya lo soporta.
- Si la derivacion no valida, el CV queda en modo legacy canonico.
- Nunca debe reutilizarse un `structured_payload` previo ni mezclarse con contenido importado plano.

## Duplicate vs update/import legacy

- Duplicate/copy de un CV estructurado puede preservar `structured_payload` y `structured_schema_version` si el contenido no cambia.
- La copia debe persistir campos legacy derivados consistentes con el payload preservado.
- Update legacy sobre CV estructurado no debe conservar payload viejo como valido.
- La opcion recomendada para este proyecto es regenerar payload desde los campos legacy actualizados dentro de la misma operacion logica.
- Si esa regeneracion falla, limpiar o invalidar el payload y volver a modo legacy canonico.
- Import schema `1` sobre un CV estructurado debe tratarse como overwrite legacy y regenerar o limpiar el payload en la misma operacion.
- PDF, TEX, JSON y ATS siempre deben resolver una unica fuente canonica consistente por registro.

## Subetapas

## Etapa 9.1 - Fundacion de migracion y compatibilidad minima

Alcance:

- Agregar columnas compatibles en `cvs` para payload estructurado versionado.
- Mantener campos planos obligatorios como compatibilidad.
- Crear servicio minimo para resolver modo legacy vs estructurado preparado.
- Evitar payload stale en updates legacy limpiando o invalidando el payload.
- Preservar payload valido en duplicate/copy cuando el contenido copiado sigue consistente.

Archivos probables:

- `app/database.py`
- `app/models.py`
- `app/repositories/cv_repository.py`
- `app/services/structured_cv_service.py`
- `tests/test_database_migrations.py`
- `tests/test_cv_repository.py`
- `tests/test_structured_cv_service.py`
- documentacion de migracion/rollback

Validaciones:

- `python -m compileall app tests`
- `git diff --check`
- DB nueva crea columnas nuevas;
- DB existente sin columnas se migra sin perder CVs;
- migracion repetida corre dos veces sin fallar;
- CVs legacy siguen creando, leyendo, actualizando, duplicando y exportando por flujos existentes;
- `docker compose exec app python -m pytest`

Criterios de aceptacion:

- DB nueva funciona con columnas estructuradas.
- DB existente schema `1` recibe columnas nuevas sin perdida.
- Ejecutar migracion dos veces no falla.
- Payload ausente o schema `1` queda en legacy canonico.
- Schema `2` con payload valido y estado `valid` queda preparado como estructurado.
- Payload invalido, stale o no marcado como valido vuelve a legacy seguro.
- Update legacy limpia o invalida payload previo para evitar stale data.
- Duplicate/copy preserva payload valido cuando el contenido copiado sigue consistente.
- No cambia UI, rutas visibles, PDF/TEX, export JSON visible ni ATS.

No hacer:

- No tocar templates productivos.
- No cambiar export/import.
- No parsear ni backfillear masivamente datos reales.

## Etapa 9.2 - Servicios estructurados y persistencia compatible

Alcance:

- Expandir la persistencia ya creada en 9.1 hacia escritura estructurada real desde servicios internos.
- Mantener campos planos obligatorios.
- Construir, validar, serializar y resolver payload v2 sin romper CVs legacy.
- Dejar preparada la conversion estructurado -> legacy para cuando exista editor o import schema `2`.
- Mantener consistencia explicita para duplicate/copy frente a update/import legacy.

Archivos probables:

- `app/repositories/cv_repository.py`
- `app/services/structured_cv_service.py`
- `tests/test_cv_repository.py`
- `tests/test_structured_cv_service.py`
- documentacion de migracion/rollback

Validaciones:

- inicializacion de DB nueva;
- DB existente con tabla legacy;
- `PRAGMA table_info(cvs)` detecta columnas antes de migrar;
- `ALTER TABLE ADD COLUMN` se ejecuta solo cuando falta la columna;
- correr la migracion dos veces no falla;
- crear, editar, duplicar y soft delete CVs legacy y estructurados;
- duplicar CV estructurado conserva payload valido y campos legacy consistentes;
- editar por flujo legacy regenera payload o deja legacy canonico sin stale payload;
- import schema `1` sobre CV estructurado regenera o limpia payload en la misma operacion;
- payload v2 tolera secciones faltantes previamente aceptadas y las normaliza con defaults, pero sigue rechazando tipos incorrectos o payloads corruptos;
- `docker compose exec app python -m pytest`.

Criterios de aceptacion:

- CVs existentes siguen funcionando.
- Payload v2 parcial previamente aceptado sigue resolviendo modo estructurado sin caer a legacy.
- Duplicar un CV estructurado conserva `structured_payload` valido cuando no cambia el contenido.
- Editar por flujo legacy un CV estructurado regenera `structured_payload` o lo limpia/invalida en la misma operacion.
- Importar schema `1` sobre un CV estructurado regenera `structured_payload` o lo limpia/invalida en la misma operacion.
- PDF/TEX/JSON/ATS nunca consumen `structured_payload` obsoleto.
- Duplicar CV estructurado conserva payload valido.
- Editar legacy CV estructurado regenera o limpia payload.
- Import schema `1` sobre CV estructurado no deja payload stale.
- DB nueva funciona.
- DB existente schema `1` funciona.
- Migracion idempotente corre dos veces sin error.
- CVs existentes siguen renderizando PDF/TEX/JSON.
- Import/export schema `1` sigue funcionando.
- Rollback posible ignorando columnas nuevas.

No hacer:

- No convertir masivamente texto libre sin aprobacion.
- No borrar campos legacy.
- No depender solo de `CREATE TABLE IF NOT EXISTS` para evolucionar una DB existente.

## Etapa 9.3 - Import/export JSON schema `2`

Alcance:

- Exportar schema `2` con payload estructurado.
- Mantener import/export schema `1`.
- Validar tipos y errores por seccion.

Archivos probables:

- `app/services/export_service.py`
- `app/services/structured_cv_service.py`
- `app/validations/structured_cv_validations.py`
- `tests/test_export_service.py`

Validaciones:

- export schema `1` desde CV legacy;
- export schema `2` desde CV estructurado;
- import schema `1`;
- import schema `2`;
- import schema `1` sobre una version con estructura deriva payload o deja modo legacy canonico;
- rechazo de payload invalido;
- limite de `512 KB`.

Criterios de aceptacion:

- Backward compatibility completa.
- Import schema `2` crea CV usable por rutas actuales.

No hacer:

- No romper consumidores existentes de JSON.
- No cambiar nombres de rutas sin necesidad.

## Etapa 9.4 - LaTeX/PDF sobre representacion normalizada

Alcance:

- Adaptar `latex_service.py` para consumir una representacion normalizada.
- Renderizar experiencia, educacion, proyectos, certificaciones y skills estructurados.
- Mantener templates robustos ante secciones vacias.

Archivos probables:

- `app/services/latex_service.py`
- `app/latex_templates/cv/*.tex`
- `app/services/structured_cv_service.py`
- `tests/test_latex_service.py`
- `tests/test_pdf_service.py`

Validaciones:

- TEX generado sin placeholders.
- PDF compila para templates `classic`, `modern`, `compact`, `tech`.
- `pdftotext` conserva contenido clave.
- No se rompen CVs legacy.

Criterios de aceptacion:

- Legacy y estructurado generan TEX/PDF correctos.
- Se mantiene texto ATS-friendly.

No hacer:

- No redisenar visualmente templates salvo necesidad concreta.
- No tocar documentation PDFs de `app/static/docs/`.

## Etapa 9.5 - ATS compatible con estructura

Alcance:

- Hacer que ATS lea texto normalizado desde CV estructurado o legacy.
- Mantener scoring actual.
- Agregar tests comparativos.

Archivos probables:

- `app/services/ats_service.py`
- `app/services/structured_cv_service.py`
- `tests/test_ats_service.py`
- `tests/test_ats_routes.py`

Validaciones:

- CV legacy completo/incompleto mantiene resultado esperado.
- CV estructurado equivalente produce resultado comparable.
- No se usa IA ni matching avanzado.

Criterios de aceptacion:

- ATS no queda acoplado a JSON crudo.
- No cambia el significado del score.

No hacer:

- No agregar IA.
- No cambiar scoring comercialmente.

## Etapa 9.6 - UI del editor por secciones

Alcance:

- Agregar rutas y templates nuevos o modo nuevo para editor estructurado.
- Editor por secciones con cards plegables.
- Agregar/eliminar items.
- Validaciones por seccion.
- Preview textual o resumen de cambios.

Archivos probables:

- `app/routes/cvs.py` o router nuevo `app/routes/structured_cvs.py`
- `app/templates/cvs/structured_form.html`
- `app/static/css/app.css`
- `app/static/js/app.js`
- `tests/test_ui_routes.py`

Validaciones:

- crear/editar estructura;
- errores por seccion;
- confirmaciones seguras;
- no `innerHTML` con datos dinamicos;
- rutas legacy siguen accesibles.

Criterios de aceptacion:

- Editor usable sin drag/drop.
- Guardado no pierde campos legacy.
- UX compatible con la app privada actual.

No hacer:

- No implementar drag/drop salvo etapa explicita.
- No agregar thumbnails, paletas funcionales ni IA.

## Etapa 9.7 - Migracion opcional y hardening

Alcance:

- Evaluar backfill de CVs existentes.
- Crear herramienta de validacion antes/despues.
- Documentar rollback probado.

Archivos probables:

- scripts o comando interno si se justifica;
- docs de migracion;
- tests de compatibilidad.

Validaciones:

- backup previo;
- conteo antes/despues;
- export JSON/TEX/PDF antes/despues;
- ATS antes/despues;
- rollback documentado.

Criterios de aceptacion:

- No hay perdida de datos.
- La migracion es reversible o desactivable.

No hacer:

- No ejecutar backfill sobre datos reales sin confirmacion explicita.
- No borrar campos planos.

## Checklist transversal

- Compatibilidad con CVs existentes.
- Export/import JSON versionado.
- Fuente canonica clara: payload estructurado valido o legacy canonico, nunca mezcla stale.
- Migracion idempotente basada en `PRAGMA table_info(cvs)` y `ALTER TABLE ADD COLUMN` condicionado.
- Duplicate, update legacy e import schema `1` mantienen consistencia sin dejar payload obsoleto.
- LaTeX/PDF validado con `pdftotext` si cambia rendering.
- ATS no cambia scoring sin etapa especifica.
- Tests por repository, service, route, UI route, export/import, LaTeX, PDF y ATS.
- Rollback documentado antes de migraciones.
- No implementar funcionalidad en Etapa 9.0.
