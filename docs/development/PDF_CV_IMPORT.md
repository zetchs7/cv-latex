# Importación de Curriculum Vitae desde PDF

Implementa el Issue [#14](https://github.com/zetchs7/cv-latex/issues/14). Diseño en
`docs/adr/ADR-0006-pdf-cv-import.md`, análisis previo en
`docs/development/IMPORT_PDF_DESIGN_PROPOSAL.md`.

## Qué es y qué no es

El PDF es **fuente de datos, nunca documento final**. El sistema lee el PDF, interpreta su texto,
propone una clasificación revisable y, solo después de que la persona confirme, crea un CV
estructurado que se renderiza con las plantillas propias del proyecto. El diseño visual del PDF
original no se copia en ningún momento.

## Formatos y límites

| Límite | Valor | Motivo de la respuesta |
| --- | --- | --- |
| Formato | PDF únicamente, validado por bytes mágicos (`%PDF-`), no por extensión | Una extensión `.pdf` no dice nada del contenido |
| Tamaño máximo | 10 MiB | Decisión aprobada. Se lee por bloques: un archivo gigante no se descarga entero para decidir que es demasiado grande |
| Páginas máximas | 20 | Decisión aprobada. Se comprueba antes de extraer texto |
| Idioma | Se interpretan español e inglés | La interfaz está en español |

## Qué se rechaza, y con qué mensaje

Todos los mensajes están en español y **no incluyen rutas del servidor ni detalle técnico**.

| Situación | Qué ve la persona |
| --- | --- |
| Archivo vacío | El archivo está vacío. Volvé a seleccionar el PDF. |
| No es un PDF | El archivo no es un PDF válido. Verificá que tenga extensión .pdf y que no esté dañado. |
| Demasiado grande | El PDF supera el tamaño máximo permitido de 10 MiB. |
| Demasiadas páginas | El PDF tiene N páginas y el máximo permitido es 20. |
| Protegido con contraseña | El PDF está protegido con contraseña. Subí una copia sin contraseña. |
| Dañado | No se pudo leer el PDF. Verificá que el archivo no esté dañado. |
| Sin texto extraíble | No se pudo extraer texto del PDF. Es posible que sea un escaneo o una imagen. Probá con un PDF que tenga texto seleccionable. |
| Sin herramientas en el servidor | El servidor no puede procesar PDF en este momento. |
| Tarda demasiado | El PDF demoró demasiado en procesarse. Probá con uno más chico o con menos páginas. |

## Qué información se intenta detectar

**Datos personales**: nombre completo, email, teléfono, ubicación, y enlaces (LinkedIn, GitHub,
portfolio, sitio web). **Perfil**: título profesional y resumen.

**Secciones de lista**: experiencia laboral, educación, skills, idiomas, certificaciones y
proyectos.

En experiencia se intentan separar empresa, cargo, fechas, descripción, logros y tecnologías.
En educación: institución, título y fechas.

### Qué significa cada nivel de confianza

Los niveles son **ordinales y deterministas**, no porcentajes estimados. La regla es explícita:

| Nivel | Cuándo | Qué hacer |
| --- | --- | --- |
| **Alta** | Hay una etiqueta explícita (`Email: ...`) o un patrón inequívoco: una dirección de correo con formato válido, o un rango de años completo con encabezado | Se precarga. Revisá igual, pero es probable que esté bien |
| **Media** | La sección se reconoció pero el campo no tiene etiqueta; o el rango de fechas está incompleto; o la categoría de una tecnología no es deducible | Revisá antes de confirmar |
| **Baja** | No hay señal suficiente. El caso típico: hay fechas pero no se puede distinguir con certeza qué parte es el cargo y cuál es la empresa | El campo se propone vacío o marcado, y **se muestra en "Campos con dudas"** |

Un dato de confianza baja **nunca** se carga como confirmado por el sistema: siempre pasa por la
decisión de la persona.

## Cómo funciona la revisión

Después de subir el PDF se abre **"Resultado de la importación del CV"**, con cuatro bloques:

1. **Datos del CV** — el título, que se completa con el nombre detectado si se deja vacío.
2. **Datos detectados** — todas las secciones con campos editables, el texto original del PDF
   plegable, y el motivo del nivel de confianza.
3. **Campos con dudas o información incompleta** — lo mismo, filtrado a confianza media y baja.
4. **Información no clasificada** — el texto que el sistema no pudo ubicar con seguridad.

Además, si el PDF menciona valores distintos para el mismo campo, aparece un bloque de
**contradicciones** arriba con los candidatos en conflicto.

Cada elemento tiene tres decisiones: **confirmar y usar**, **conservar** o **descartar**.
Los elementos sin clasificar además se pueden asignar a una sección.

## Qué pasa con la información no clasificada

No se descarta en silencio, que es el requisito explícito del Issue. El clasificador funciona por
resta: toma **todas** las líneas del documento y descuenta lo que quedó representado en algún campo.
Lo que sobra se muestra completo, con su texto original, y espera una decisión.

Es un caso real, no hipotético: un PDF sin encabezados reconocibles —el formato más común de un CV
bien maquetado a dos columnas— no produce ninguna sección detectada, pero **no pierde nada**. Todo
el texto aparece para que la persona lo ubique a mano.

## Cómo se confirma el CV

Al confirmar:

1. Se validan **todas** las decisiones antes de tocar nada. Si una es inválida, no se guarda nada y
   no se pierde lo que ya habías escrito.
2. Se rechaza la confirmación **si queda un solo elemento pendiente**.
3. Se rechaza si falta el nombre completo.
4. Se convierte lo aprobado a payload **schema 2 plano**.
5. Se ejecuta la validación de dominio real (`validate_structured_payload_v2`) y la del snapshot
   legacy, antes de escribir.
6. Se crea el CV con `create_structured_cv()`, que inserta en una sola sentencia: **no hay
   escrituras parciales**.
7. El borrador se borra y se redirige al editor estructurado del CV nuevo.

Si el guardado falla, **el borrador sobrevive** y se puede reintentar sin perder correcciones.

## Qué datos se almacenan y cuánto tiempo

| Dato | Dónde | Cuánto |
| --- | --- | --- |
| El PDF original | **En ningún lado** | Se procesa en un temporal que se borra al terminar, incluso si hay error |
| El texto extraído | Solo dentro del borrador | 2 horas desde la última actualización |
| El borrador de revisión | `<data>/import-drafts/<id>.json` | 2 horas, con purga automática |

El identificador del borrador se genera con `secrets` (32 caracteres) y **se vuelve a validar al
recuperarlo**: un identificador manipulado se rechaza antes de tocar el sistema de archivos. La
expiración se aplica al leer y en una purga que corre en cada acceso.

**Si el servidor se reinicia**, los borradores en disco sobreviven: no están en memoria. Solo se
pierden los que ya vencieron, que la purga limpia.

El directorio de borradores está fuera de cualquier ruta publicada: los drafts no se sirven como
archivos estáticos.

## Qué no soporta la versión actual

- **No hay OCR.** Sin texto seleccionable, el sistema lo dice y pide otro PDF. El Issue lo permite.
- **No hay análisis semántico.** Las reglas son deterministas. Un CV a dos columnas, sin
  encabezados o con un formato inusual se clasifica mal y hay que corregirlo a mano.
- **No se detectan siete campos** que el Issue menciona: `seniority`, modalidad de trabajo,
  rol/impacto/empresa de proyecto, y descripción y estado de certificación. Schema 2 no tiene dónde
  guardarlos y **no se los mezcló dentro del CV visible**. Se ven en la revisión mientras dura la
  sesión.
- **No se detectan múltiples empleadores en un mismo bloque** de descripción, ni se separan
  los casos que no esten etiquetados.
- **Solo se interpretan español e inglés** en los encabezados reconocidos.

## Por qué no hay OCR

No hay `tesseract` en el host ni en la imagen del proyecto. Agregar OCR cambia el tamaño de la
imagen y el tiempo de procesamiento de cada importación, y es una decisión de producto. El Issue lo
acepta explícitamente: informar que el PDF no contiene texto extraíble, sin fallar en silencio.

## Limitaciones conocidas del análisis determinista

1. **La separación empresa/cargo no es fiable.** "Desarrollador, Acme" y "Acme, Desarrollador" son
   indistinguibles sin semántica. Se propone con confianza media o baja y se pide confirmación.
2. **Las columnas se mezclan.** `pdftotext -layout` preserva la alineación, pero un CV a dos
   columnas puede entrelazar líneas. Las coordenadas por palabra se extraen pero hoy no se usan
   para reordenar.
3. **Una sección mal nombrada no se reconoce.** Los encabezados están en una lista cerrada en
   español e inglés. Un encabezado inventado cae en "Información no clasificada".
4. **Las tecnologías se detectan por vocabulario**, no por contexto. Una mención dentro de una
   descripción se propone como tecnología de la experiencia, no como skill.
5. **Fechas sin año completo** se reducen al año, y las fechas en formatos raros pueden no
   reconocerse.
6. **Los enlaces sin contexto** se marcan con confianza baja: una URL puede ser un portfolio o una
   cita aleatoria.

Todas son asumidas. La respuesta del sistema ante la duda no es adivinar: es mostrar el dato, decir
por qué no está seguro, y dejar que la persona decida.

## Seguridad

| Control | Implementación |
| --- | --- |
| Tipo real del archivo | Bytes mágicos `%PDF-`, no extensión |
| Tamaño | 10 MiB, leído por bloques con corte temprano |
| Páginas | 20, verificadas antes de extraer |
| Cifrado | Marca `/Encrypt` leída del contenido crudo |
| Ejecución externa | Lista de argumentos, **sin shell**, sin interpolación, con timeout |
| Contenido del PDF | **Datos no confiables**: nunca se interpreta como órdenes, HTML ni código |
| Temporal | Directorio propio, borrado al salir incluso con error |
| Rutas internas | Ningún mensaje visible las incluye |
| Red | **Ninguna.** El CV no sale del servidor |
| Traversal | El identificador se re-valida y se comprueba que la ruta resuelva dentro del directorio |
| Exposición en directorios publicados | El staging no está bajo `/static` |
| Inyección vía contenido extraído | El contenido llega a la interfaz solo por autoescape de Jinja2 |

La app **no registra ningún middleware**: sin CSRF, CORS ni `TrustedHost`. Las rutas nuevas heredan
esa condición y no la empeoran, pero tampoco la corrigen. La mitigación global es una tarea
independiente y prioritaria (`SEC-001` y `SEC-002` del catálogo).

## Archivos

| Archivo | Responsabilidad |
| --- | --- |
| `app/services/pdf_import_service.py` | Validación del archivo y extracción con `pdfinfo` y `pdftotext` |
| `app/services/pdf_section_parser.py` | Clasificación del texto con niveles de confianza |
| `app/services/import_staging_service.py` | Ciclo de vida del borrador, decisiones y mapeo a schema 2 |
| `app/routes/pdf_import.py` | Rutas del flujo |
| `app/templates/cvs/import_form.html` | Pantalla de carga |
| `app/templates/cvs/import_review.html` | Pantalla de revisión |
| `tests/test_pdf_import_services.py` | Tests unitarios de las tres piezas |
| `tests/test_pdf_import_flow.py` | Flujo completo extremo a extremo |
| `tests/fixtures/pdf_import/` | PDFs deterministas, regenerables y versionados |

## Estado frente a los criterios de aceptación del Issue

| Criterio | Estado |
| --- | --- |
| Botón "Importar CV desde PDF" en Curriculum Vitae | Implementado |
| El usuario puede subir un PDF y la app lo valida | Implementado |
| Extrae texto de un PDF con texto seleccionable | Implementado |
| Detecta datos personales, experiencia, educación, skills y resumen | Implementado |
| Mapea la información al modelo interno | Implementado |
| Pantalla de revisión antes de guardar | Implementado |
| El usuario puede editar antes de confirmar | Implementado |
| Los campos dudosos se muestran claramente | Implementado |
| Sección "Campos con dudas o información incompleta" | Implementado |
| Sección "Información no clasificada" | Implementado |
| Corregir, completar, mover, descartar o confirmar | Implementado |
| No inventa información | Implementado, con confianza declarada |
| No descarta en silencio lo que no pudo clasificar | Implementado |
| El CV final usa las plantillas propias | Implementado |
| El PDF no reemplaza el formato interno | Implementado |
| Validaciones para PDF corrupto, vacío, protegido o ilegible | Implementado |
| Mensajes de error claros | Implementado |
| Funcionalidad documentada | Este documento |
| Tests básicos del flujo | 75 pruebas |
| Tests para casos ambiguos o incompletos | Implementado |

**Pendiente**: la documentación de usuario servida (`docs/user/`) y sus PDFs **no** se actualizaron
todavía. La feature no está publicada; hacerlo antes del release documentaría algo que los usuarios
todavía no tienen. Corresponde hacerlo junto con `REL-001`.