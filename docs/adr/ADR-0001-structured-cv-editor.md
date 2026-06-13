# ADR-0001 - Structured CV Editor

## Estado

Propuesta para Etapa 9.0. No implementada.

## Contexto

`cv-latex` mantiene actualmente el modulo CV con una tabla SQLite `cvs` y un modelo plano `CV`. Los campos actuales son:

- `title`
- `full_name`
- `email`
- `phone`
- `professional_summary`
- `experience_summary`
- `education_summary`
- `skills`
- timestamps de creacion, actualizacion y eliminacion logica

El flujo actual es simple y estable:

- `app/repositories/cv_repository.py` lista, lee, crea, actualiza, duplica y elimina logicamente CVs.
- `app/routes/cvs.py` arma formularios, valida, importa/exporta JSON, dispara TEX/PDF y muestra detalle/listado.
- `app/validations/cv_validations.py` valida campos planos y limites de longitud.
- `app/services/export_service.py` exporta JSON schema `1`, importa JSON limitado a `512 KB` y genera archivos en `/data/exports`.
- `app/services/latex_service.py` transforma el `CV` plano en secciones LaTeX.
- `app/services/pdf_service.py` compila el TEX generado con `pdflatex`.
- `app/services/ats_service.py` calcula score ATS basico desde los mismos campos planos.

El problema que se quiere resolver en etapas futuras es que experiencia, educacion, skills y otros bloques estan como texto monolitico. Eso limita edicion por item, reordenamiento, validaciones por seccion, export/import versionado y futura UI por cards.

La Etapa 9.0 solo define arquitectura. No cambia DB, codigo funcional, rutas, templates productivos, renderer LaTeX/PDF, import/export JSON ni ATS.

## Decision

Adoptar un enfoque hibrido progresivo:

1. Mantener la tabla `cvs` y los campos planos actuales como fuente compatible durante la transicion.
2. Agregar en una etapa posterior un payload JSON estructurado versionado dentro de `cvs`, por ejemplo `structured_payload TEXT` y `structured_schema_version INTEGER`.
3. Centralizar la conversion entre payload estructurado y `CV` plano en un servicio nuevo, sin mezclar esa logica en rutas ni templates.
4. Mantener export/import JSON backward compatible:
   - schema `1`: formato plano actual.
   - schema `2`: formato estructurado futuro.
5. Mantener LaTeX/PDF y ATS funcionando sobre una representacion normalizada. Si el CV tiene payload estructurado, se deriva una vista plana compatible para consumidores existentes mientras se migran templates y scoring.
6. Postergar tablas relacionales separadas hasta que exista una necesidad real de consultas complejas, reportes cruzados o filtros por item.

Esta decision prioriza compatibilidad, rollback simple y menor superficie de riesgo sobre normalizacion temprana.

## Alternativas consideradas

### Alternativa A - Tabla `cvs` con payload JSON estructurado

Descripcion: mantener `cvs` y agregar un campo JSON versionado con secciones estructuradas.

Ventajas:

- Cambio de DB acotado.
- Facil de mantener en SQLite.
- Rollback simple: los campos planos siguen existiendo.
- Export/import puede versionarse sin introducir varias tablas.
- Encaja con un editor por secciones sin requerir joins.

Riesgos:

- Menos validacion relacional a nivel DB.
- Consultas internas por experiencia, skill o educacion quedan limitadas.
- Requiere servicio de normalizacion para evitar duplicar conversiones.

Impacto en migracion:

- Migracion ligera para agregar columnas.
- Backfill opcional y reversible desde campos planos.
- Puede arrancar con compatibilidad lazy: si no hay payload, derivar estructura desde campos existentes al leer.

Impacto en export/import:

- Export schema `2` puede incluir `structured_cv`.
- Import schema `1` sigue creando CV plano.
- Import schema `2` valida payload y deriva campos planos de compatibilidad.

Impacto en tests:

- Tests de conversion plano -> estructurado.
- Tests de estructura -> plano.
- Tests de import/export schema `1` y `2`.
- Tests de LaTeX/PDF y ATS consumiendo ambos formatos.

Dificultad de rollback:

- Baja. Se puede ignorar `structured_payload` y seguir usando campos planos.

### Alternativa B - Tablas relacionales separadas

Descripcion: crear tablas como `cv_experiences`, `cv_education`, `cv_skills`, `cv_links`, `cv_projects`.

Ventajas:

- Modelo normalizado.
- Mejor integridad por item.
- Consultas por skill, empresa, fechas o educacion son mas directas.
- Ordenamiento puede modelarse con `position`.

Riesgos:

- Mucha superficie de migracion para el estado actual del proyecto.
- Mas repositorios, tests, joins y transacciones.
- Rollback mas delicado.
- Mayor riesgo de romper export/import, ATS y LaTeX antes de que el editor demuestre necesidad real.

Impacto en migracion:

- Alto. Requiere crear multiples tablas, migrar datos monoliticos con heuristicas o dejar campos legacy.
- Las heuristicas para dividir texto libre pueden producir resultados pobres.

Impacto en export/import:

- Export debe ensamblar varias tablas.
- Import debe validar y crear multiples registros de forma transaccional.
- Se necesita manejo cuidadoso de errores parciales.

Impacto en tests:

- Amplio: repositories por tabla, transacciones, ordenamiento, cascadas logicas, import/export y UI.

Dificultad de rollback:

- Media/alta. Requiere preservar campos legacy o recomponerlos desde tablas.

### Alternativa C - Enfoque hibrido JSON + tablas selectivas

Descripcion: comenzar con JSON estructurado en `cvs` y agregar tablas solo para partes que luego necesiten consulta o relacion.

Ventajas:

- Permite empezar simple.
- Deja camino de crecimiento.
- Evita normalizar antes de tener uso real.
- Mantiene rollback razonable.

Riesgos:

- Puede generar dos fuentes de verdad si no se define una regla clara.
- Requiere disciplina de servicios para no mezclar payload, campos legacy y posibles tablas.

Impacto en migracion:

- Bajo al inicio, medio si luego se agregan tablas.

Impacto en export/import:

- Similar a Alternativa A al comienzo.
- Las tablas futuras deberian reconstruirse desde payload o viceversa con estrategia explicita.

Impacto en tests:

- Inicialmente acotado.
- Crece por subetapas si se agregan tablas.

Dificultad de rollback:

- Baja al inicio. Media si aparecen tablas futuras.

## Arquitectura elegida

La arquitectura recomendada para 9.1+ es Alternativa C, comenzando por la Alternativa A:

- En la primera implementacion funcional, agregar payload JSON estructurado versionado en `cvs`.
- Mantener campos planos actuales como compatibilidad obligatoria.
- Introducir un servicio nuevo, por ejemplo `app/services/structured_cv_service.py`, responsable de:
  - construir estructura vacia;
  - derivar estructura desde CV plano legacy;
  - validar payload estructurado;
  - convertir estructura a campos planos para consumidores actuales;
  - preparar payload para export JSON schema `2`.
- Mantener `cv_repository.py` como capa de persistencia SQLite.
- Mantener `cv_validations.py` como validacion de formulario plano y crear validaciones estructuradas separadas cuando exista UI nueva.
- Mantener rutas existentes intactas al inicio y sumar rutas nuevas solo en subetapas posteriores.

## Forma propuesta del CV estructurado

El payload futuro deberia ser un objeto versionado:

```json
{
  "schema_version": 2,
  "personal": {
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "headline": ""
  },
  "summary": "",
  "skills": [
    {"label": "Python", "category": "Backend", "level": "", "order": 1}
  ],
  "experience": [
    {
      "company": "",
      "role": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "current": false,
      "summary": "",
      "highlights": [],
      "technologies": [],
      "order": 1
    }
  ],
  "education": [
    {
      "institution": "",
      "degree": "",
      "field": "",
      "start_date": "",
      "end_date": "",
      "summary": "",
      "order": 1
    }
  ],
  "certifications": [],
  "languages": [],
  "projects": [],
  "links": [],
  "optional_sections": [],
  "ats_metadata": {
    "target_role": "",
    "keywords": [],
    "last_checked_at": ""
  },
  "section_order": [
    "summary",
    "skills",
    "experience",
    "education",
    "certifications",
    "languages",
    "projects",
    "links"
  ]
}
```

## Compatibilidad con CVs existentes

- Todo CV existente debe seguir abriendo, editando, duplicando, exportando JSON, exportando TEX/PDF y analizandose con ATS.
- Si `structured_payload` esta vacio, el servicio debe derivar una estructura minima desde campos planos.
- El editor nuevo no debe destruir el contenido monolitico original hasta que haya una migracion validada.
- La conversion estructurado -> plano debe ser deterministica para mantener LaTeX/PDF y ATS mientras esos consumidores se adaptan.

## Migracion progresiva

### Fase inicial

- Agregar columnas en una migracion o inicializacion controlada:
  - `structured_schema_version INTEGER`
  - `structured_payload TEXT`
- No parsear automaticamente texto libre en multiples items sin confirmacion del usuario.
- Para CVs legacy, generar una vista estructurada con un item textual por seccion cuando se abre el editor nuevo.

### Backfill opcional

- Solo despues de tests y validacion manual.
- El backfill debe preservar campos planos.
- Registrar cantidad de CVs actualizados y errores.

### Validacion antes/despues

- Antes: exportar JSON schema `1`, TEX y PDF de CVs representativos.
- Despues: validar que el mismo CV sigue exportando TEX/PDF y ATS sin perdida.
- Comparar contenido textual con `pdftotext` para PDFs.

### Rollback

- Si falla el editor estructurado, desactivar rutas nuevas y seguir usando campos planos.
- No borrar columnas nuevas como primer rollback.
- Mantener export/import schema `1` disponible.

## UI futura

El editor futuro deberia ser por secciones:

- Datos personales/contacto.
- Resumen profesional.
- Skills como items editables.
- Experiencia laboral como cards plegables.
- Educacion como cards plegables.
- Certificaciones, idiomas, proyectos y links como secciones opcionales.
- Orden de secciones configurable dentro de un rango controlado.
- Validaciones por seccion antes de guardar.
- Preview de texto plano/LaTeX/PDF en etapa posterior.
- Acciones para agregar, eliminar y reordenar items, sin drag/drop al inicio salvo etapa especifica.

No implementar esta UI en 9.0.

## Impacto en LaTeX/PDF

- LaTeX debe recibir una representacion normalizada, no leer JSON crudo desde templates.
- Experiencia estructurada debe renderizar cargo, empresa, periodo, resumen, bullets y tecnologias.
- Educacion debe renderizar institucion, titulo, fechas y descripcion.
- Skills pueden seguir como lista ATS-friendly.
- Mantener sanitizacion con `sanitize_latex_text`.
- Mantener validacion PDF aprendida en 8.3:
  - TEX generado sin placeholders;
  - PDF compila;
  - `pdftotext` conserva contenido;
  - no se rompen secciones vacias;
  - validar PDF real descargado si se toca exportacion;
  - revisar layout visual si cambian templates.

## Impacto en ATS

- ATS debe consumir un texto normalizado derivado de estructura y campos legacy.
- El scoring actual no debe cambiar en la primera subetapa funcional.
- Agregar tests para que un CV legacy y su equivalente estructurado produzcan resultado comparable.
- `ats_metadata` no debe alterar scoring hasta que exista una etapa explicita.

## Impacto en import/export JSON

- Mantener schema `1` actual.
- Agregar schema `2` cuando exista estructura real.
- Import schema `1`: crea CV legacy y payload estructurado derivado opcional.
- Import schema `2`: valida estructura, crea campos planos derivados y guarda payload.
- Rechazar campos con tipos incorrectos y mantener limite de tamano.
- Reportar errores por campo/seccion de forma segura.

## Tests requeridos

- Repositories:
  - crear/leer CV con payload estructurado;
  - actualizar sin perder campos legacy;
  - duplicar payload y campos planos;
  - soft delete sin borrar payload.
- Services:
  - conversion legacy -> estructura;
  - estructura -> plano;
  - validacion de payload;
  - orden de secciones.
- Routes:
  - rutas existentes intactas;
  - rutas nuevas del editor estructurado cuando existan.
- UI routes:
  - formularios por seccion;
  - errores por seccion;
  - confirmaciones seguras sin `innerHTML`.
- Export JSON:
  - schema `1` backward compatible;
  - schema `2` estructurado.
- Import JSON:
  - schema `1` sigue funcionando;
  - schema `2` valida tipos y crea CV usable.
- LaTeX/PDF:
  - TEX desde legacy y estructurado;
  - PDF compila;
  - `pdftotext` preserva contenido.
- ATS:
  - resultado comparable para legacy y estructura equivalente.

## Riesgos

- Crear dos fuentes de verdad si no se centraliza conversion.
- Perder contenido legacy si se intenta parsear texto libre de forma agresiva.
- Romper export/import al cambiar schema sin compatibilidad.
- Romper LaTeX/PDF si templates reciben estructuras sin normalizar.
- Expandir UI antes de estabilizar modelo y servicios.
- Duplicidad de numeracion ADR por ruta requerida en esta etapa: ya existe `ADR-0001-stack-mvp.md`.

## Validaciones requeridas para implementar en 9.1+

- `python -m compileall app tests`
- `git diff --check`
- `docker compose build`
- `docker compose up -d --force-recreate`
- `docker compose ps`
- `docker compose exec app python -m pytest`
- flujos HTTP de crear, editar, duplicar, eliminar, exportar e importar CVs legacy y estructurados
- validacion TEX/PDF con `pdftotext` si cambia rendering
- backup local de datos antes de migracion real

## Plan por subetapas

- 9.1: servicio de modelo estructurado en memoria, sin DB.
- 9.2: persistencia compatible con columnas JSON versionadas.
- 9.3: import/export JSON schema `2` con compatibilidad schema `1`.
- 9.4: adaptacion LaTeX/PDF sobre representacion normalizada.
- 9.5: ATS leyendo estructura normalizada sin cambiar scoring.
- 9.6: editor UI por secciones sin drag/drop.
- 9.7: validacion integral, migracion opcional y hardening.

