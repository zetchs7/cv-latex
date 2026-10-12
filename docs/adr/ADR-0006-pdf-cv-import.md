# ADR-0006 — Importación de Curriculum Vitae desde PDF

- **Estado**: Aceptada e implementada
- **Fecha**: 2026-10-12
- **Contexto**: Issue [#14](https://github.com/zetchs7/cv-latex/issues/14)
- **Rama**: `feature/pdf-cv-import`
- **Relacionada**: `ADR-0003-structured-cv-editor.md`, `ADR-0004-latex-rendering.md`,
  `ADR-0005-project-control-center.md`, `docs/development/IMPORT_PDF_DESIGN_PROPOSAL.md`

## Contexto

El Issue #14 pide subir un CV en PDF e interpretarlo para cargarlo en el modelo interno. Especifica
15 criterios de aceptación y dos secciones obligatorias en la pantalla de revisión: **"Campos con
dudas o información incompleta"** y **"Información no clasificada"**.

La investigación de `IMPORT_PDF_DESIGN_PROPOSAL.md` encontró la restricción que define la
arquitectura: **siete campos que el Issue pide no tienen dónde entrar en schema 2** — `seniority`,
modalidad de trabajo, rol/impacto/empresa de proyecto, y descripción y estado de certificación.
`additional_info` existe pero renderiza contenido visible en el CV, así que no sirve como almacén
de incertidumbre: mezclar dudas ahí produciría exactamente lo contrario de lo pedido.

## Decisiones ya tomadas por Franco

No se re-discutieron: staging separado de schema 2 · conservar la información dudosa durante la
revisión en lugar de descartarla · sin OCR en v1 · 10 MiB y 20 páginas · botón en el listado de
Curriculum Vitae · interfaz en español, interpretando español e inglés · procesamiento local sin
proveedores externos.

## Decisión

**Una capa de staging en disco entre el PDF y el modelo persistente.**

```
PDF → extraer texto → clasificar con confianza → STAGING (JSON con TTL)
    → pantalla de revisión obligatoria → decisiones explícitas
    → payload schema 2 plano → create_structured_cv() → editor estructurado
```

El staging **no es schema 2** y nunca se escribe en `cvs`. Existe porque es la única forma de
satisfacer simultáneamente dos requisitos que el modelo persistente no puede cumplir a la vez:
representar incertidumbre visible y guardar un CV limpio.

### Por qué el payload schema 2 es plano

El payload se construye con las secciones en la raíz junto a `schema_version`. Anidarlas bajo una
clave `sections` hace que el validador las acepte pero que el snapshot legacy salga vacío: el CV se
crea sin nombre ni email y el error aparece como un fallo genérico de escritura, muy lejos de la
causa. El contrato real está en `build_legacy_snapshot_from_payload`.

### Por qué la detección de cifrado lee los bytes

`pdfinfo` sale con error ante un PDF cifrado exactamente como ante uno corrupto. Consultar el
resultado de `pdfinfo` hacía que un PDF protegido se reportara como dañado. La marca `/Encrypt` en
el contenido crudo es determinista.

### Por qué el análisis es determinista y no semántico

No hay modelo de lenguaje ni embeddings en el proyecto, y la decisión de Franco fue procesamiento
local sin proveedores externos. El clasificador es un conjunto de reglas comprobables: encabezados
conocidos en español e inglés, rangos de fechas, etiquetas explícitas y taxonomías.

Cada detección lleva un nivel de confianza **ordinal con criterios declarados**, no un porcentaje
estimado:

| Nivel | Criterio |
| --- | --- |
| Alta | Etiqueta explícita (`Email: ...`) o patrón inequívoco (correo válido, rango completo con etiqueta) |
| Media | Sección reconocida pero campo sin etiqueta, o rango de fechas incompleto |
| Baja | Sin señal suficiente; se propone para que la persona confirme o descarte |

La separación entre empresa y cargo nunca llega a confianza alta: el orden correcto no es
determinable sin semántica, y adivinar en silencio sería inventar un dato.

### Por qué nada se descarta en silencio

La clasificación es una resta: se parte de **todas** las líneas del documento y se descuenta lo que
quedó representado en algún campo o elemento. Un PDF sin encabezados reconocibles —el caso más
común de un CV bien maquetado— habría perdido el 100 % del contenido antes de este cambio.

Confirmar se rechaza mientras quede un solo elemento pendiente. Descartar es siempre una decisión
explícita.

## Alternativas consideradas

### Guardar el staging en SQLite

Exigía una migración de esquema. El Issue no la justifica y una tabla nueva para datos
efímeros agrega superficie sin beneficio. El staging vive en `<data>/import-drafts/`, fuera de
cualquier directorio publicado, con identificador impredecible y vencimiento.

### OCR en la v1

No hay `tesseract` ni en el host ni en la imagen. El Issue lo permite explícitamente: informar que
el PDF no contiene texto extraíble y no fallar en silencio. Añadir OCR es una decisión de producto,
no técnica.

### Descartar lo dudoso automáticamente

Simplificaba la pantalla pero viola el Issue de forma directa. La confianza baja se muestra y se
decide; no se borra sola.

## Consecuencias

### Positivas

- El modelo persistente no cambia: ni schema, ni migración, ni plantillas, ni ATS.
- Nada se escribe en `cvs` antes de la confirmación, y un fallo al guardar conserva el borrador.
- El PDF original nunca se persiste; los borradores expiran y se limpian solos.

### Negativas

- El análisis determinista se equivoca. Un CV a dos columnas o sin encabezados se clasifica mal,
  y la corrección es manual. Esto está asumido y documentado, no resuelto.
- El staging es estado en disco que hay que limpiar. Tiene TTL y purga, pero es una responsabilidad
  nueva.
- Los campos que schema 2 no tiene (seniority, modalidad, impacto) se muestran en revisión pero no
  llegan al CV estructurado. Se conservan en staging durante la sesión y se descartan al confirmar.

### Riesgo de seguridad

La aplicación no registra ningún middleware: no hay CSRF, ni CORS, ni `TrustedHost`, ni
autenticación. Las rutas nuevas heredan esa exposición y **no la empeoran** por sí solas, pero
tampoco la mitigan. La mitigación global (`SEC-001`, `SEC-002` en el catálogo) sigue siendo una tarea
independiente y prioritaria. Decidir esa política transversal no pertenece a esta feature.

## Criterios de reversión

Borrar `app/services/pdf_import_service.py`, `app/services/pdf_section_parser.py`,
`app/services/import_staging_service.py`, `app/routes/pdf_import.py`, las dos plantillas, los tests
y las fixtures, y quitar una línea de `app/main.py`. No hay migración que deshacer ni datos que
migrar: si un borrador queda sin usar, expira solo.