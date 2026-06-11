# CV Builder Core

## Version

`0.9.0`

## Objetivo

Implementar y mantener el modulo base de CVs para crear, listar, ver detalle, editar, duplicar, eliminar logicamente, importar JSON y disparar exportaciones desde datos guardados en SQLite, conviviendo con el modulo de cartas de presentacion.

## Archivos principales

- `app/models.py`: modelo `CV`.
- `app/schemas.py`: schema de formulario `CVFormData`.
- `app/database.py`: inicializacion de tabla `cvs`.
- `app/repositories/cv_repository.py`: acceso a datos SQLite.
- `app/routes/cvs.py`: rutas HTTP del modulo.
- `app/validations/cv_validations.py`: validaciones centralizadas.
- `app/templates/cvs/index.html`: listado.
- `app/templates/cvs/form.html`: crear y editar.
- `app/templates/cvs/detail.html`: detalle.
- `app/templates/cvs/confirm_delete.html`: confirmacion de eliminacion.
- `app/static/css/app.css`: estilos de formularios, tablas y botones.

## Rutas

| Metodo | Ruta | Objetivo |
| --- | --- | --- |
| GET | `/cvs/` | Listar CVs activos. |
| GET | `/cvs/new` | Mostrar formulario de creacion. |
| POST | `/cvs/` | Crear CV. |
| GET | `/cvs/{cv_id}` | Ver detalle de CV. |
| GET | `/cvs/{cv_id}/edit` | Mostrar formulario de edicion. |
| POST | `/cvs/{cv_id}/edit` | Actualizar CV. |
| POST | `/cvs/{cv_id}/duplicate` | Duplicar CV. |
| GET | `/cvs/{cv_id}/delete` | Mostrar confirmacion de eliminacion. |
| POST | `/cvs/{cv_id}/delete` | Eliminar logicamente CV. |
| POST | `/cvs/import/json` | Importar un CV desde JSON y crear un registro nuevo. |
| GET | `/cvs/{cv_id}/export/json` | Descargar JSON del CV. |
| GET | `/cvs/{cv_id}/export/tex` | Descargar TEX del CV con plantilla. |
| GET | `/cvs/{cv_id}/export/pdf` | Generar y descargar PDF del CV con plantilla. |

## Modelo SQLite

Tabla: `cvs`

- `id`: entero autoincremental.
- `title`: titulo interno obligatorio.
- `full_name`: nombre completo obligatorio.
- `email`: email opcional.
- `phone`: telefono opcional.
- `professional_summary`: perfil profesional.
- `experience_summary`: experiencia.
- `education_summary`: educacion.
- `skills`: skills.
- `created_at`: timestamp de creacion.
- `updated_at`: timestamp de ultima actualizacion.
- `deleted_at`: timestamp de eliminacion logica.

## Validaciones

Las validaciones viven en `app/validations/cv_validations.py`.

- `title` obligatorio.
- `full_name` obligatorio.
- `email` debe tener formato valido si se informa.
- Limites de longitud por campo.
- Normalizacion basica de espacios.
- El duplicado reutiliza las validaciones existentes y recorta el titulo para cerrar con el sufijo `(copia)` sin exceder el limite.
- La importacion JSON se lee por chunks con limite maximo de `512 KB`.

## Calculos

No hay calculos financieros ni de negocio complejo en esta etapa.

## Persistencia

Los CVs se guardan en SQLite dentro de `/data/app.db`. En Docker, `/data` corresponde al bind mount local `./data`.

## Eliminacion

La eliminacion es logica. El registro no se borra fisicamente; se setea `deleted_at` y deja de aparecer en listados activos.

## Como probar

```bash
docker compose build
docker compose up -d
docker compose ps
```

Abrir:

```text
http://localhost:8000/cvs/
```

Flujo manual:

1. Crear un CV desde `/cvs/new`.
2. Ver detalle del CV creado.
3. Editar el CV.
4. Duplicar el CV.
5. Confirmar eliminacion.
6. Exportar JSON, TEX y PDF.
7. Importar JSON valido desde el listado.
8. Verificar que el CV eliminado no aparece en el listado.

## Validaciones tecnicas ejecutadas

- Compilacion Python con `python -m compileall app`.
- Build Docker.
- Arranque Docker Compose.
- Healthcheck.
- Requests HTTP a dashboard, listado y formulario.
- Creacion, edicion, duplicado y eliminacion logica por POST.
- Validacion negativa de formulario con respuesta 422.
- Verificacion SQLite de activos e inactivos.
- Rechazo de import JSON por tamano excedido.
- Duplicado con titulo al limite sin romper validaciones.
- Error PDF seguro hacia la UI con detalle tecnico separado.

## Limitaciones

- No implementa cartas de presentacion.
- No implementa tracker de postulaciones.
- El analisis ATS se consume desde el flujo del CV, pero no cambia la persistencia propia del modulo.
- No implementa IA.
