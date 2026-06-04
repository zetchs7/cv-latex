# Application Tracker

## Version

`0.6.0`

## Objetivo

Implementar y mantener el modulo base de seguimiento de postulaciones para crear, listar, ver detalle, editar, eliminar logicamente y asociar opcionalmente cada oportunidad a un CV existente y a una carta existente.

## Archivos principales

- `app/models.py`: modelo `Application`.
- `app/schemas.py`: schema `ApplicationFormData`.
- `app/database.py`: inicializacion de tabla `applications`.
- `app/repositories/application_repository.py`: acceso a datos SQLite del modulo.
- `app/routes/applications.py`: rutas HTTP del modulo.
- `app/validations/application_validations.py`: validaciones centralizadas.
- `app/templates/applications/index.html`: listado.
- `app/templates/applications/form.html`: crear y editar.
- `app/templates/applications/detail.html`: detalle.
- `app/templates/applications/confirm_delete.html`: confirmacion de eliminacion.

## Rutas

| Metodo | Ruta | Objetivo |
| --- | --- | --- |
| GET | `/applications/` | Listar postulaciones activas. |
| GET | `/applications/new` | Mostrar formulario de creacion. |
| POST | `/applications/` | Crear postulacion. |
| GET | `/applications/{application_id}` | Ver detalle. |
| GET | `/applications/{application_id}/edit` | Mostrar formulario de edicion. |
| POST | `/applications/{application_id}/edit` | Actualizar postulacion. |
| GET | `/applications/{application_id}/delete` | Mostrar confirmacion de eliminacion. |
| POST | `/applications/{application_id}/delete` | Eliminar logicamente postulacion. |

## Modelo SQLite

Tabla: `applications`

- `id`: entero autoincremental.
- `company`: empresa objetivo obligatoria.
- `position`: puesto objetivo obligatorio.
- `link`: link opcional a la vacante.
- `source`: fuente opcional de la oportunidad.
- `applied_on`: fecha de aplicacion obligatoria.
- `status`: estado obligatorio.
- `associated_cv_id`: referencia opcional a un CV activo.
- `associated_cover_letter_id`: referencia opcional a una carta activa.
- `notes`: notas libres.
- `next_action`: proxima accion.
- `follow_up_date`: fecha de seguimiento opcional.
- `created_at`: timestamp de creacion.
- `updated_at`: timestamp de ultima actualizacion.
- `deleted_at`: timestamp de eliminacion logica.

## Estados permitidos

- `pendiente`
- `enviado`
- `entrevista`
- `rechazado`
- `oferta`
- `pausado`

## Validaciones

Las validaciones viven en `app/validations/application_validations.py`.

- `company` obligatorio.
- `position` obligatorio.
- `applied_on` obligatorio en formato `YYYY-MM-DD`.
- `status` obligatorio y dentro del set permitido.
- `link` opcional, pero si se informa debe ser `http://` o `https://`.
- `follow_up_date` opcional en formato `YYYY-MM-DD`.
- Limites de longitud por campo.
- `associated_cv_id` y `associated_cover_letter_id` opcionales, pero si se informan deben apuntar a registros activos.

## Como probar

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose exec app python -m pytest
```

Abrir:

```text
http://localhost:8000/applications/
```

Flujo manual:

1. Crear un CV y una carta si se quieren asociar.
2. Crear una postulacion desde `/applications/new`.
3. Cambiar el estado desde la edicion.
4. Ver detalle.
5. Eliminar logicamente desde la confirmacion.
6. Confirmar persistencia en SQLite.

## Limitaciones

- No implementa calendario.
- No implementa automatizaciones.
- No implementa emails.
- No implementa ATS Basic Check.
- No implementa IA.
