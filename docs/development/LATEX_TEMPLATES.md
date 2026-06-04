# Plantillas LaTeX y Sanitizacion

## Version

`0.4.2`

## Objetivo

Generar contenido `.tex` desde un CV guardado, usando plantillas LaTeX propias y sanitizacion estricta de texto antes de insertar datos en la plantilla.

## Archivos principales

- `app/latex_templates/cv/classic.tex`
- `app/latex_templates/cv/modern.tex`
- `app/latex_templates/cv/compact.tex`
- `app/latex_templates/cv/tech.tex`
- `app/services/latex_service.py`
- `app/validations/latex_sanitizer.py`
- `app/templates/cvs/tex_preview.html`
- `tests/test_latex_sanitizer.py`
- `tests/test_latex_service.py`

## Rutas

| Metodo | Ruta | Objetivo |
| --- | --- | --- |
| GET | `/cvs/{cv_id}/tex` | Previsualizar contenido `.tex` generado desde un CV guardado. |

Parametro opcional:

- `template_key`: `classic`, `modern`, `compact` o `tech`.

## Servicio

`app/services/latex_service.py` expone:

- `available_cv_templates()`: lista las plantillas disponibles.
- `generate_cv_tex_document(cv, template_key)`: genera un objeto con nombre de archivo, plantilla usada y contenido `.tex`.

El servicio genera contenido `.tex` para previsualizacion, exportacion TEX y compilacion PDF mediante `pdf_service.py`.

## Sanitizacion

`app/validations/latex_sanitizer.py` escapa caracteres especiales de LaTeX:

- `\`
- `&`
- `%`
- `$`
- `#`
- `_`
- `{`
- `}`
- `~`
- `^`

Tambien preserva caracteres comunes en espanol como `á`, `é`, `í`, `ó`, `ú`, `ñ`, `ü`, `¿` y `¡`, apoyandose en plantillas con UTF-8.

## Extraccion de texto PDF

Desde Etapa 3.1 las cuatro plantillas incluyen:

- `\input{glyphtounicode}`
- `\pdfgentounicode=1`
- `\usepackage{cmap}`
- `\usepackage[utf8]{inputenc}`
- `\usepackage[T1]{fontenc}`
- `\usepackage{lmodern}`

Este bloque mejora el mapeo Unicode de los glifos generados por `pdflatex`, lo que ayuda a copy/paste, `pdftotext` y parsers tipo ATS.

Si la compilacion PDF falla, la UI muestra un mensaje seguro y resumido. El detalle tecnico queda para logs y troubleshooting.

## Secciones vacias

El servicio omite secciones sin contenido para que la plantilla no genere bloques rotos o titulos sin datos.

## Como probar

```bash
python -m unittest discover -s tests
docker compose build
docker compose up -d
```

Flujo manual:

1. Crear o abrir un CV en `http://localhost:8000/cvs/`.
2. Entrar al detalle.
3. Usar `Ver TEX`.
4. Cambiar `template_key` entre `classic`, `modern`, `compact` y `tech`.

## Limitaciones

- La compatibilidad con parsers ATS reales debe validarse en una etapa futura con herramientas concretas.
- No implementa cartas de presentacion.
- No implementa tracker de postulaciones.
- No implementa ATS.
- No implementa IA.
