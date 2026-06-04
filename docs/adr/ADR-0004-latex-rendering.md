# ADR-0004 - LaTeX Rendering

- Estado: Aprobado
- Fecha: 2026-06-02

## Contexto

El MVP necesita generar CVs en LaTeX con plantillas propias. La compilacion final a PDF corresponde a una etapa posterior, por lo que en esta etapa se requiere producir contenido `.tex` seguro desde datos guardados en SQLite.

## Decision

Crear plantillas LaTeX propias en `app/latex_templates/cv/` y renderizarlas con Jinja2 usando delimitadores personalizados:

- Bloques: `[% ... %]`
- Variables: `[[ ... ]]`

Centralizar sanitizacion en `app/validations/latex_sanitizer.py` y generacion en `app/services/latex_service.py`.

En Etapa 3 se agrega compilacion PDF con `pdflatex` dentro del contenedor Docker. Se eligio TeX Live sobre Tectonic porque evita descarga dinamica de bundles en runtime y permite validaciones reproducibles sin depender de red durante la generacion. El costo aceptado es una imagen Docker mas pesada.

Los PDF se compilan en un directorio temporal controlado bajo `/data/exports/_tmp` y el archivo final se copia a `/data/exports`. Los nombres de archivo se sanitizan y no se aceptan rutas de salida enviadas por el usuario.

## Consecuencias

- La logica LaTeX queda separada de rutas y templates HTML.
- Los datos del CV se sanitizan antes de entrar a las plantillas.
- Las plantillas pueden manejar secciones vacias sin romper.
- La compilacion PDF depende de TeX Live instalado en la imagen.
- `/data/exports` concentra los artefactos persistidos TEX, JSON y PDF.
- La imagen Docker crece de forma relevante por las dependencias LaTeX.
