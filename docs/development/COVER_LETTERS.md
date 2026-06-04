# Cover Letters

## Version

`0.5.0`

## Objetivo

Implementar y mantener el modulo base de cartas de presentacion para crear, listar, ver detalle, editar, eliminar logicamente, asociar opcionalmente a un CV existente y exportar TEX/PDF desde datos guardados en SQLite.

## Archivos principales

- `app/models.py`: modelo `CoverLetter`.
- `app/schemas.py`: schema `CoverLetterFormData`.
- `app/database.py`: inicializacion de tabla `cover_letters`.
- `app/repositories/cover_letter_repository.py`: acceso a datos SQLite del modulo.
- `app/routes/cover_letters.py`: rutas HTTP del modulo.
- `app/validations/cover_letter_validations.py`: validaciones centralizadas.
- `app/templates/cover_letters/index.html`: listado.
- `app/templates/cover_letters/form.html`: crear y editar.
- `app/templates/cover_letters/detail.html`: detalle y exportaciones.
- `app/templates/cover_letters/confirm_delete.html`: confirmacion de eliminacion.
- `app/latex_templates/cover_letter/classic_letter.tex`: plantilla LaTeX base del modulo.
- `app/services/latex_service.py`: generacion TEX reutilizando entorno Jinja2 y sanitizacion.
- `app/services/pdf_service.py`: compilacion PDF reutilizando pipeline actual.

## Rutas

| Metodo | Ruta | Objetivo |
| --- | --- | --- |
| GET | `/cover-letters/` | Listar cartas activas. |
| GET | `/cover-letters/new` | Mostrar formulario de creacion. |
| POST | `/cover-letters/` | Crear carta. |
| GET | `/cover-letters/{cover_letter_id}` | Ver detalle. |
| GET | `/cover-letters/{cover_letter_id}/edit` | Mostrar formulario de edicion. |
| POST | `/cover-letters/{cover_letter_id}/edit` | Actualizar carta. |
| GET | `/cover-letters/{cover_letter_id}/delete` | Mostrar confirmacion de eliminacion. |
| POST | `/cover-letters/{cover_letter_id}/delete` | Eliminar logicamente carta. |
| GET | `/cover-letters/{cover_letter_id}/export/tex` | Descargar TEX. |
| GET | `/cover-letters/{cover_letter_id}/export/pdf` | Generar y descargar PDF. |

## Modelo SQLite

Tabla: `cover_letters`

- `id`: entero autoincremental.
- `company`: empresa objetivo obligatoria.
- `position`: puesto objetivo obligatorio.
- `contact`: contacto opcional.
- `greeting`: saludo obligatorio.
- `introduction`: introduccion opcional.
- `body`: cuerpo principal obligatorio.
- `closing`: cierre opcional.
- `signature`: firma obligatoria.
- `associated_cv_id`: referencia opcional a un CV activo.
- `created_at`: timestamp de creacion.
- `updated_at`: timestamp de ultima actualizacion.
- `deleted_at`: timestamp de eliminacion logica.

## Validaciones

Las validaciones viven en `app/validations/cover_letter_validations.py`.

- `company` obligatorio.
- `position` obligatorio.
- `greeting` obligatorio.
- `body` obligatorio.
- `signature` obligatorio.
- Limites de longitud por campo.
- Normalizacion basica de espacios.
- `associated_cv_id` opcional, pero si se informa debe ser numerico y debe apuntar a un CV activo.

## Exportaciones

- TEX: usa la plantilla `classic_letter` y guarda el archivo en `/data/exports`.
- PDF: reutiliza `pdflatex` dentro del contenedor y guarda el resultado final en `/data/exports`.
- Sanitizacion: todos los campos pasan por `app/validations/latex_sanitizer.py` antes de renderizar.
- Filenames: el nombre final se sanitiza, conserva legibilidad y queda acotado a `180` caracteres para evitar errores del filesystem con `company` y `position` largos.

## Persistencia

Las cartas se guardan en SQLite dentro de `/data/app.db`. En Docker, `/data` corresponde al bind mount local `./data`.

## Eliminacion

La eliminacion es logica. El registro no se borra fisicamente; se setea `deleted_at` y deja de aparecer en listados activos.

## Como probar

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose exec app python -m pytest
```

Abrir:

```text
http://localhost:8000/cover-letters/
```

Flujo manual:

1. Crear un CV en `/cvs/` si se quiere asociar la carta.
2. Crear una carta desde `/cover-letters/new`.
3. Editar la carta.
4. Ver detalle.
5. Descargar TEX.
6. Generar PDF.
7. Confirmar que los archivos aparecen en `./data/exports`.
8. Eliminar logicamente la carta desde la pantalla de confirmacion.

## Validaciones tecnicas ejecutadas

- Compilacion Python con `python -m compileall app tests`.
- Build Docker.
- Arranque Docker Compose.
- Healthcheck.
- Requests HTTP a listado, formulario, detalle y exportaciones.
- Creacion, edicion y eliminacion por POST.
- Asociacion opcional a un CV existente.
- Generacion TEX y PDF con persistencia en `/data/exports`.
- Validacion basica de extraccion de texto PDF con `pdftotext`.

## Limitaciones

- Solo hay una plantilla de carta en esta etapa: `classic_letter`.
- No implementa tracker de postulaciones.
- No implementa ATS Basic Check.
- No implementa IA.
