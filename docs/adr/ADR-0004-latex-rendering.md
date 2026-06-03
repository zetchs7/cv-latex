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

## Consecuencias

- La logica LaTeX queda separada de rutas y templates HTML.
- Los datos del CV se sanitizan antes de entrar a las plantillas.
- Las plantillas pueden manejar secciones vacias sin romper.
- La etapa no introduce compilacion PDF ni descargas, evitando adelantar Etapa 3.
