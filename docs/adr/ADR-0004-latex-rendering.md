# ADR-0004 - LaTeX Rendering

- Estado: Aprobado
- Fecha: 2026-06-02

## Contexto

El MVP necesita generar CVs y cartas de presentacion en LaTeX con plantillas propias. La compilacion final a PDF comenzo en Etapa 3, por lo que el sistema requiere producir contenido `.tex` seguro desde datos guardados en SQLite y luego compilarlo dentro del contenedor.

## Decision

Crear plantillas LaTeX propias en `app/latex_templates/cv/` y `app/latex_templates/cover_letter/` y renderizarlas con Jinja2 usando delimitadores personalizados:

- Bloques: `[% ... %]`
- Variables: `[[ ... ]]`

Centralizar sanitizacion en `app/validations/latex_sanitizer.py` y generacion en `app/services/latex_service.py`.

En Etapa 3 se agrega compilacion PDF con `pdflatex` dentro del contenedor Docker. Se eligio TeX Live sobre Tectonic porque evita descarga dinamica de bundles en runtime y permite validaciones reproducibles sin depender de red durante la generacion. El costo aceptado es una imagen Docker mas pesada.

Los PDF se compilan en un directorio temporal controlado bajo `/data/exports/_tmp` y el archivo final se copia a `/data/exports`. Los nombres de archivo se sanitizan y no se aceptan rutas de salida enviadas por el usuario.

En Etapa 3.1 se refuerza la extraccion de texto para PDF agregando `cmap`, Latin Modern (`lmodern`), `glyphtounicode` y `pdfgentounicode=1` a las plantillas. Tambien se agrega `poppler-utils` al contenedor para validar con `pdftotext` que palabras con acentos, `ñ`, `ü` y signos comunes en espanol se extraigan correctamente.

En Etapa 3.2 los fallos de compilacion PDF dejan de exponerse completos al usuario final. La UI recibe un mensaje resumido y el detalle tecnico queda separado para logs y troubleshooting.

En Etapa 4 se reutiliza el mismo pipeline de LaTeX/PDF para cartas de presentacion. Las cartas tienen su propia plantilla `classic_letter`, conservan sanitizacion, nombres de archivo seguros y persistencia final en `/data/exports`.

## Consecuencias

- La logica LaTeX queda separada de rutas y templates HTML.
- Los datos de CVs y cartas se sanitizan antes de entrar a las plantillas.
- Las plantillas pueden manejar secciones vacias sin romper.
- La compilacion PDF depende de TeX Live instalado en la imagen.
- `/data/exports` concentra los artefactos persistidos TEX, JSON y PDF.
- La imagen Docker crece de forma relevante por las dependencias LaTeX.
- La imagen incluye `poppler-utils` para validacion tecnica de extraccion de texto PDF.
- Los errores PDF mantienen capacidad de diagnostico sin exponer logs completos en la interfaz.
- La compatibilidad ATS mejora a nivel de texto extraible, pero parsers ATS reales pueden tener comportamientos propios y deberan validarse en una etapa futura.
