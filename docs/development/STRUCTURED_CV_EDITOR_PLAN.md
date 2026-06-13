# Structured CV Editor Plan

## Objetivo

Planificar la implementacion futura del editor estructurado de CV sin tocar codigo funcional en Etapa 9.0. Este documento define subetapas, alcance, archivos probables, validaciones, criterios de aceptacion y limites.

## Estado de Etapa 9.0

- Estado: diseno tecnico solamente.
- No implementa editor.
- No cambia DB.
- No crea migraciones.
- No toca rutas funcionales, templates productivos, renderer LaTeX/PDF, import/export JSON ni ATS scoring.
- Documento arquitectonico asociado: `docs/adr/ADR-0001-structured-cv-editor.md`.

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

## Subetapas

## Etapa 9.1 - Modelo estructurado en memoria

Alcance:

- Crear dataclasses o tipos para CV estructurado sin persistirlos todavia.
- Crear servicio de conversion legacy -> estructura y estructura -> legacy.
- Crear validaciones puras del payload estructurado.

Archivos probables:

- `app/models.py`
- `app/schemas.py`
- `app/services/structured_cv_service.py`
- `app/validations/structured_cv_validations.py`
- `tests/test_structured_cv_service.py`

Validaciones:

- `python -m compileall app tests`
- `git diff --check`
- `docker compose exec app python -m pytest`

Criterios de aceptacion:

- Un `CV` plano puede convertirse a payload estructurado minimo.
- Un payload estructurado puede derivar campos planos compatibles.
- No cambia DB ni rutas.

No hacer:

- No tocar templates productivos.
- No cambiar export/import.
- No migrar datos.

## Etapa 9.2 - Persistencia compatible

Alcance:

- Agregar columnas compatibles en `cvs` para payload estructurado versionado.
- Mantener campos planos obligatorios.
- Leer/escribir payload sin romper CVs legacy.

Archivos probables:

- `app/database.py`
- `app/repositories/cv_repository.py`
- `app/models.py`
- `tests/test_cv_repository.py`
- documentacion de migracion/rollback

Validaciones:

- inicializacion de DB nueva;
- DB existente con tabla legacy;
- crear, editar, duplicar y soft delete CVs legacy y estructurados;
- `docker compose exec app python -m pytest`.

Criterios de aceptacion:

- CVs existentes siguen funcionando.
- Payload se preserva en update/duplicate.
- Rollback posible ignorando columnas nuevas.

No hacer:

- No convertir masivamente texto libre sin aprobacion.
- No borrar campos legacy.

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
- LaTeX/PDF validado con `pdftotext` si cambia rendering.
- ATS no cambia scoring sin etapa especifica.
- Tests por repository, service, route, UI route, export/import, LaTeX, PDF y ATS.
- Rollback documentado antes de migraciones.
- No implementar funcionalidad en Etapa 9.0.

