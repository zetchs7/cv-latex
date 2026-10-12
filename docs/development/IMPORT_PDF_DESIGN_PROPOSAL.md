# Propuesta: importación de Curriculum Vitae desde PDF

**Estado**: propuesta para aprobación. No implementada.
**Tarea del catálogo**: `CV-001`
**Issue**: [#14](https://github.com/zetchs7/cv-latex/issues/14), creado por `zetchs7` el 2026-06-13
**Fecha**: 2026-10-12
**Investigación**: solo lectura. Ningún archivo de `app/` fue modificado.

## 1. Por qué esta propuesta existe

El Issue #14 está escrito en detalle funcional y tiene 15 criterios de aceptación. Pero antes
de escribir código hay que responder una pregunta que el issue no hace y que cambia
completamente el tamaño del trabajo:

> ¿Los datos que el issue pide tienen dónde entrar en el modelo interno que ya existe?

La respuesta es **parcialmente no**. Eso define la arquitectura.

## 2. Inventario verificado

### Herramientas disponibles

| Herramienta | Host | Imagen Docker | Nota |
| --- | --- | --- | --- |
| `pdftotext` | sí | sí | `poppler-utils`, ya instalado por el `Dockerfile` |
| `pdftoppm` | sí | sí | idem |
| `pdfinfo` | sí | sí | idem |
| `qpdf` | sí | **no** | no está en el `Dockerfile`; no contarla |
| `gs` (Ghostscript) | no | no | |
| `tesseract` (OCR) | no | no | |
| Biblioteca Python de PDF | ninguna | ninguna | `requirements.txt` no declara ninguna |

`pdf_service.py` ya compila con `pdflatex` y `pdf_service` ya usa un timeout de 45 s. El
proyecto tiene antecedentes de trabajar con binarios del sistema: `ADR-0004-latex-rendering.md`.

### Schema 2, campos reales

Extraído de `app/validations/structured_cv_validations.py`:

| Sección | Campos | Tope de items |
| --- | --- | --- |
| `personal` | `full_name`, `headline`, `location` | — |
| `contact` | `email`, `phone` | — |
| `metadata` | `source`, `synced_from_legacy_at` | — |
| `summary` | texto plano | 1200 chars |
| `skills` | `label`, `category`, `level` | 40 |
| `experience` | `company`, `role`, `location`, `start_date`, `end_date`, `summary`, `highlights`, `technologies` | 30 |
| `education` | `institution`, `degree`, `field`, `start_date`, `end_date`, `summary` | 30 |
| `certifications` | `name`, `issuer`, `date` | 30 |
| `languages` | `name`, `level` | 20 |
| `projects` | `name`, `summary`, `link`, `technologies` | 30 |
| `links` | `label`, `url` | 30 |
| `additional_info` | `title`, `content` | 20 |

## 3. Brecha entre lo que pide el Issue #14 y lo que el modelo admite

| Requisito del Issue | Dónde entra | Estado |
| --- | --- | --- |
| Nombre completo | `personal.full_name` | directo |
| Email, teléfono | `contact.email`, `contact.phone` | directo |
| Ubicación | `personal.location` | directo |
| LinkedIn, GitHub, portfolio, web | `links[]` | directo |
| Descripción profesional, resumen de experiencia | `summary` | directo |
| Rol principal | `personal.headline` | directo |
| **Seniority** | — | **no existe** |
| **Áreas de especialización** | `skills[].category` | reutilizable |
| Empresa, cargo, fechas, trabajo actual | `experience.company/role/start_date/end_date` | directo |
| **Duración estimada** | derivable de las fechas | derivable |
| Descripción del rol | `experience.summary` | directo |
| **Responsabilidades principales** | `experience.summary` | se mezcla con el resto |
| **Logros relevantes** | `experience.highlights` | directo |
| Tecnologías | `experience.technologies` | directo |
| **Herramientas**, **plataformas**, **clientes** | `experience.technologies` | se mezclan con tecnologías |
| **Modalidad de trabajo** | — | **no existe** |
| Institución, carrera, fechas | `education.institution/degree/start_date/end_date` | directo |
| **Estado** (completo, en curso) | derivable de las fechas | derivable |
| Descripción de formación | `education.summary` | directo |
| Skills clasificados por categoría | `skills[].category` | directo |
| Idioma y nivel | `languages.name/level` | directo |
| **Certificación asociada a un idioma** | `certifications[]` | se separa del idioma |
| Certificación: nombre, institución, fecha | `certifications.name/issuer/date` | directo |
| **Descripción y estado de la certificación** | — | **no existe** |
| Proyecto: nombre, descripción, tecnologías | `projects.name/summary/technologies` | directo |
| **Rol del usuario en el proyecto** | — | **no existe** |
| **Resultado o impacto** | — | **no existe** |
| **Empresa o cliente del proyecto** | — | **no existe** |
| **Información no clasificada** | `additional_info` | existe pero es contenido visible del CV, no un contenedor de incertidumbre |

**Resumen de la brecha**: siete campos que el Issue pide no tienen dónde entrar
(`seniority`, `modalidad`, descripción y estado de certificación, rol, impacto y empresa del
proyecto), y varios mas requieren ser mezclados con otros.

### El problema de fondo

`additional_info` **sí** existe, pero renderiza contenido visible en el CV. No es un almacén
de incertidumbre: meter ahí "no sé si esta fecha es de inicio o de fin" ensuciaría el
documento final.

El Issue exige, en cambio, dos secciones explícitas que no existen en el modelo:

- **Campos con dudas o información incompleta**
- **Información no clasificada**

Y exige que el sistema **no elimine silenciosamente** nada. Con el schema actual, cumplir eso
obligaría a mezclar datos dudosos en el CV visible, que es justo lo contrario de lo pedido.

## 4. El hallazgo que habilita la solución

`app/validations/structured_cv_validations.py`, docstring del contrato:

> Las claves extra (campos solo-estructurados o desconocidos) se preservan sin validarse para
> no perder contenido.

El validador es estricto en **versión** —solo acepta schema 2, y versiones futuras o menores
se rechazan sin downcast— pero es **permisivo en claves**: un campo desconocido dentro de una
sección se conserva.

Eso significa que agregar campos nuevos al schema 2 **no requiere cambiar la versión ni
migrar la base**. No es gratis: los campos nuevos no se validarían en longitud, y las
plantillas LaTeX y el ATS los ignorarían hasta que se actualicen.

## 5. Tres opciones de arquitectura

### Opción A — Zona de staging de importación, sin tocar el schema

El parser produce un **borrador que no es schema 2**. La pantalla de revisión trabaja sobre
ese borrador. Solo al confirmar se mapea a schema 2; lo que no entra se muestra como campos
con dudas y queda **registrado en el borrador, visible para el usuario**, pero no renderizado
en el CV.

- **A favor**: cero cambios en el schema, las plantillas, el ATS o la base. Ninguna
  migración. Cumple literalmente la separación que pide el Issue entre "datos dudosos" y "CV
  final".
- **En contra**: se pierde el dato al confirmar. El usuario corrigió el campo, pero si lo
  descartó queda fuera. El Issue no exige persistir lo descartado, así que es aceptable.
- **Riesgo**: que "guardar solo después de confirmar" signifique que la información no
  clasificada se puede perder. Mitigable mostrando un aviso explícito en la confirmación.

### Opción B — Ampliar schema 2 con campos opcionales

Agregar los siete campos faltantes como opcionales dentro de las secciones existentes. El
validador los preserva sin cambios; el modelo gana `experience[].seniority`,
`projects[].role`, etc.

- **A favor**: el dato queda persistido y disponible. Sin migración, sin cambio de versión.
- **En contra**: los campos nuevos no se validan en longitud. Hay que agregar esos limites a
  mano en la validacion, en lugar de confiar en el payload de 512 KB.
- **Riesgo**: extender un schema que ya se declaró "estricto" erosiona ese contrato. Y
  requiere tocar plantillas LaTeX y ATS para que el dato se vea, que es trabajo extra dentro
  del mismo alcance.

### Opción C — Schema 3

Versión nueva con los campos formalizados, migración de los CVs existentes y actualización
coordinada de validación, renderizado, ATS y exportación.

- **A favor**: el modelo queda coherente y los campos quedan tipados y validados.
- **En contra**: es el cambio de mayor riesgo del proyecto. Toca migración de datos reales,
  las cuatro plantillas LaTeX, el ATS, la exportación JSON y los tests golden de identidad
  byte a byte del TEX legacy. El Issue #14 no pide nada de eso.
- **Veredicto**: desproporcionado para este alcance. No lo recomiendo ahora.

### Recomendación

**Opción A para la v1**, con una reserva explícita:

- El staging resuelve el 90 % del Issue sin tocar el modelo que ya funciona.
- La Opción B queda documentada como camino natural si Franco quiere que seniority,
  impacto, rol y modalidad **se persistan y se rendericen**.
- La Opción C queda descartada hasta que una necesidad real la justifique.

Lo que hay que decidir antes de escribir código es si los datos dudosos **se descartan al
confirmar** (Opción A) o **se persisten** (Opción B parcial).

## 6. Flujo de usuario propuesto

```text
CV Builder → "Importar CV desde PDF"
  → seleccionar archivo
  → validaciones (formato, tamaño, páginas, legible)
  → extracción de texto
  → detección de secciones
  → PANTALLA "Resultado de importación del CV"      ← obligatoria, antes de guardar
       · secciones editables con el dato detectado
       · "Campos con dudas o información incompleta"  ← motivo + confianza + acción
       · "Información no clasificada"                 ← texto original + a dónde asignarlo
  → el usuario corrige, mueve, descarta o confirma
  → confirmar
  → se crea el CV estructurado con las plantillas propias del proyecto
```

El PDF **nunca** se guarda ni se adjunta. Es fuente de datos, tal como pide el Issue.

## 7. Extracción de texto

**Recomendación: `pdftotext -bbox-layout`**, invocado como subproceso con timeout.

- Ya está en la imagen por `poppler-utils`. Cero dependencias nuevas.
- `-bbox-layout` devuelve **coordenadas por palabra**, que es lo que necesita la detección de
  secciones para decidir "este bloque es una experiencia laboral".
- `pdfinfo` da número de páginas y dimensiones antes de extraer, para rechazar por tamaño.

Alternativas descartadas:

- **`pdfplumber` / `pypdf`**: mejor API y salida estructurada, pero agregan dependencias que
  duplican una capacidad que ya está en la imagen, y amplían el `Dockerfile`.
- **OCR**: no hay `tesseract` en el host ni en la imagen. Agregar OCR es una decisión de
  producto, no técnica. El Issue lo permite explícitamente: informar que el PDF no contiene
  texto extraíble y no fallar en silencio.

## 8. Detección de secciones

Es la parte genuinamente difícil y hay que decirlo sin adornos: **no es fiable en general**.
Un CV en dos columnas, uno sin encabezados, o con una carta de presentación pegada, rompen
cualquier heurística.

Modelo de confianza propuesto:

| Nivel | Señal | Tratamiento |
| --- | --- | --- |
| **Alto** | Encabezado reconocido (`EXPERIENCIA`, `EDUCACIÓN`, `APTITUDES`…) **y** rango de fechas encontrado | Se precarga, editable |
| **Medio** | Solo rango de fechas, o solo encabezado | Se precarga **marcado** para revisión |
| **Bajo** | Texto libre sin señal | Va a "Información no clasificada" |

El principio que el Issue enuncia y que hay que respetar: **la confianza baja nunca se
presenta como dato confirmado**. Un campo de confianza media aparece precargado pero
visualmente distinto y listado en la sección de dudas.

## 9. Seguridad del archivo

| Control | Implementación |
| --- | --- |
| Tamaño máximo | Reutilizar el patrón de `read_limited_upload_bytes` con un límite propio para PDF |
| Tipo real, no extensión | Verificar los bytes mágicos `%PDF-`, no solo `.pdf` |
| Tope de páginas | `pdfinfo` antes de extraer; rechazar PDFs con páginas excesivas |
| Tiempo de ejecución | Timeout en `pdftotext`, siguiendo el patrón de `pdf_service` |
| Almacenamiento | `TemporaryDirectory`, eliminado en un `finally`. El PDF no se persiste |
| Rutas internas | Mensajes de error sin rutas del servidor, como ya hace `pdf_service` |
| Red | Ninguna. La v1 no envía el CV a ningún servicio externo |
| Renderizado | Nunca se muestra el PDF crudo al navegador |

## 10. Casos límite a cubrir

El Issue los enumera y la implementación debe contestarlos todos. Los que agregarían trabajo
extra si se descubren tarde:

- **PDF protegido por contraseña** → mensaje claro, no error 500.
- **PDF sin texto extraíble** → mensaje que sugiera subir un PDF con texto seleccionable.
- **PDF con muchas páginas** → rechazo con límite explícito.
- **Fechas en formatos ambiguos** (`2021`, `01/2021`, `presente`, `actualidad`) → nunca
  interpretar en silencio; siempre marcar.
- **Empresa detectada sin cargo**, y el inverso → regla explícita del Issue.
- **Tecnología mencionada dentro de una descripción** → sugerirla, no cargarla como skill
  confirmada.
- **Dos empresas en un mismo bloque de descripción** → separar y marcar.
- **Texto en español y en inglés** → el mapeo de encabezados tiene que considerar ambos.

## 11. Plan de ejecución propuesto

Cada subetapa es independiente y entregable, con commits atómicos.

| Subetapa | Alcance | Riesgo |
| --- | --- | --- |
| **S1** | `pdf_upload_service`: validar archivo, extraer texto con `pdftotext`, límite de tamaño y páginas, timeout, temporales | Bajo |
| **S2** | `pdf_section_parser`: segmentar texto en secciones con nivel de confianza, sin tocar la app | Bajo, testeable sin UI |
| **S3** | Mapeo a schema 2 + criterios de aceptación por sección | Medio |
| **S4** | Rutas + pantalla de revisión editable con las dos secciones obligatorias | Medio |
| **S5** | Casos límite, tests y documentación de usuario | Medio |
| **S6** | Opcional, solo si Franco elige Opción B: persistencia de los campos nuevos y renderizado | Alto |

S1 y S2 no tocan rutas ni plantillas. Son la parte que más uncertainty tiene y la más
verificable, así que conviene empezar por ahí.

## 12. Tests y aceptación

- Unitarios del parser: sección por sección, en español y en inglés, con casos de baja confianza.
- Unitarios de extracción: vacío, corrupto, protegido por contraseña, escaneado, multipágina.
- Integration: PDF → borrador → schema 2 válido, verificado con el validador real
  (`validate_structured_payload_v2`), no con un mock.
- Regresión: que un CV creado desde un PDF pase por el mismo camino de validación y renderizado
  que uno creado a mano, y que el TEX generado sea válido.
- Seguridad: tamaño excedido, tipo falso, camino de temporal no limpiado.

Criterio de cierre: los **15 criterios de aceptación** del Issue #14, verificados uno por uno.

## 13. Decisiones que requieren a Franco

Estas **no** se pueden tomar por ingeniería, y bloquean S3 en adelante:

1. **¿Opción A, B o C?** La recomendación es A, pero B cambia el alcance de forma relevante.
2. **Los datos dudosos, ¿se descartan al confirmar o se persisten?** Si se descartan, hace
   falta un aviso explícito antes de confirmar. Si se persisten, hace falta decidir dónde.
3. **¿OCR en la v1?** Hoy no hay `tesseract`. Añadirlo cambia el tamaño de la imagen y el
   tiempo de procesamiento. El Issue permite no tenerlo.
4. **¿Límite de tamaño y de páginas del PDF?** El issue dice "tamaño máximo permitido" sin
   fijar el valor.
5. **¿El botón va en la lista de CVs o dentro del detalle?** El Issue pide "en la sección
   Curriculum Vitae", que es ambiguo entre las dos.
6. **Idioma de los mensajes de la pantalla de revisión.** La interfaz actual es en español.

## 14. Estado

Nada de esto está implementado. `app/` no fue tocado. El Issue #14 sigue abierto y sin
modificar, con sus requisitos intactos.