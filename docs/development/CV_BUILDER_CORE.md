# CV Builder Core

## Version

`0.9.0`

## Objetivo

Implementar y mantener el modulo base de CVs para crear, listar, ver detalle, editar, duplicar, eliminar logicamente, importar JSON y disparar exportaciones desde datos guardados en SQLite, conviviendo con el modulo de cartas de presentacion.

El modulo sostiene dos editores. El editor plano legacy por formulario y el editor estructurado por secciones. Ambos comparten la misma tabla y las mismas rutas de exportacion, listado y detalle.

## Editores

### Editor plano legacy

Formulario de campos planos, validado en servidor por `app/validations/cv_validations.py`. Sigue siendo el camino por defecto para crear y editar un CV legacy. Las rutas y los flujos existentes no cambian.

### Editor estructurado

Disponible en la rama `feature/structured-cv-complete`, **sin publicar**: no tiene version, release ni tag. Implementado sobre `a28d1fd`.

Trabaja sobre un payload JSON versionado con `schema_version` 2. El editor es por secciones:

- Datos personales y contacto.
- Titulo profesional.
- Resumen.
- Experiencia.
- Educacion.
- Skills.
- Certificaciones.
- Idiomas.
- Proyectos.
- Links.
- Informacion adicional.
- Metadata interna de solo lectura.

Los items de las secciones de lista se agregan, eliminan y reordenan con botones `Subir`/`Bajar`, con renumeracion automatica y densa. No hay drag and drop.

La validacion es 100% servidor, con errores accionables en espanol y sin escrituras parciales. Un envio fallido responde 422 y el formulario se re-renderiza preservando exactamente lo que el usuario escribio.

Archivos involucrados:

- `app/validations/structured_cv_validations.py`: validacion estricta del payload schema v2, con strings acotados y colecciones acotadas.
- `app/services/structured_cv_service.py`: contrato normalizado y resolucion de la fuente canonica.
- `app/services/structured_cv_editor_service.py`: bootstrap del editor y parseo del envio.
- `app/services/structured_cv_rendering.py`: representacion normalizada compartida por LaTeX/PDF y ATS.
- `app/templates/cvs/structured_form.html` y `app/static/js/structured_editor.js`: el editor por secciones.

### Fuente canonica

`resolve_normalized_cv` devuelve la fuente estructurada completa o un fallback legacy completo. Las fuentes nunca se mezclan, y ningun consumidor decide por su cuenta entre JSON y campos planos: todos piden la representacion normalizada al servicio estructurado.

Solo se acepta `schema_version` 2. Las versiones desconocidas, futuras, nulas o no enteras se rechazan sin downcast.

## Archivos principales

- `app/models.py`: modelo `CV`.
- `app/schemas.py`: schema de formulario `CVFormData`.
- `app/database.py`: inicializacion de tabla `cvs`.
- `app/repositories/cv_repository.py`: acceso a datos SQLite.
- `app/routes/cvs.py`: rutas HTTP del modulo.
- `app/validations/cv_validations.py`: validaciones del formulario plano.
- `app/validations/structured_cv_validations.py`: validaciones del payload estructurado.
- `app/services/structured_cv_service.py`: contrato normalizado y fuente canonica.
- `app/services/structured_cv_editor_service.py`: bootstrap y parseo del editor estructurado.
- `app/services/structured_cv_rendering.py`: representacion normalizada para LaTeX/PDF y ATS.
- `app/templates/cvs/index.html`: listado.
- `app/templates/cvs/form.html`: crear y editar por el formulario plano.
- `app/templates/cvs/structured_form.html`: crear y editar por el editor estructurado.
- `app/templates/cvs/detail.html`: detalle.
- `app/templates/cvs/confirm_delete.html`: confirmacion de eliminacion.
- `app/static/css/app.css`: estilos de formularios, tablas y botones.
- `app/static/js/structured_editor.js`: comportamiento del editor estructurado.

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

### Rutas del editor estructurado

Aditivas, sin publicar y disponibles en `feature/structured-cv-complete`. No reemplazan las rutas legacy.

| Metodo | Ruta | Objetivo |
| --- | --- | --- |
| GET | `/cvs/new/structured` | Mostrar el editor estructurado de creacion. |
| POST | `/cvs/new/structured` | Crear un CV estructurado validando el payload schema v2. |
| GET | `/cvs/{cv_id}/structured-edit` | Mostrar el editor estructurado de edicion. |
| POST | `/cvs/{cv_id}/structured-edit` | Actualizar un CV estructurado validando el payload schema v2. |

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

Columnas estructuradas agregadas por migracion idempotente, disponibles solo desde la rama `feature/structured-cv-complete`:

- `structured_schema_version`: version del schema del payload.
- `structured_payload`: payload JSON versionado.
- `structured_payload_status`: distingue payload legacy, valido, invalido o stale.

Los campos planos quedan como snapshot derivado para los CVs estructurados. Un CV legacy sigue teniendo esos campos planos como fuente canonica.

## Regla de edicion: un CV estructurado no se edita por el formulario plano

El formulario plano legacy **no puede modificar un CV estructurado**. La operacion esta bloqueada en tres capas:

1. `app/repositories/cv_repository.py` lanza `StructuredCVLegacyUpdateError` antes de abrir una conexion a la base.
2. Las rutas redirigen al editor estructurado con una explicacion en espanol.
3. La UI dirige la accion principal al editor estructurado cuando el CV es estructurado.

El motivo es la integridad de datos. Guardar un CV estructurado por la ruta legacy regeneraba el payload desde los campos planos y descartaba silenciosamente todas las secciones que solo existen en schema `2` (certificaciones, proyectos, idiomas, links, headline y ubicacion), mientras el CV seguia apareciendo como estructurado.

## Intercambio JSON

El modulo exporta e importa dos schemas.

### Export

- **schema `2`**: para un CV estructurado valido. Produce un sobre con `schema_version`, `exported_at`, `source_cv_id` y `cv` con `title` y `structured_payload`. El nombre de archivo usa la variante `cv-schema2`.
- **schema `1`**: plano, desde el snapshot legacy. Se mantiene para CVs legacy, invalidos, stale o de version futura.

### Import

- Acepta schema `1` y schema `2`.
- Mantiene el limite de `512 KB`.
- **Siempre crea un CV nuevo**. Nunca sobrescribe el CV de origen.
- Un import schema `2` valida el payload y deriva los campos planos de compatibilidad.

## Validaciones

Las validaciones del formulario plano viven en `app/validations/cv_validations.py`.

- `title` obligatorio.
- `full_name` obligatorio.
- `email` debe tener formato valido si se informa.
- Limites de longitud por campo.
- Normalizacion basica de espacios.
- El duplicado reutiliza las validaciones existentes y recorta el titulo para cerrar con el sufijo `(copia)` sin exceder el limite.

Las validaciones del editor estructurado viven en `app/validations/structured_cv_validations.py`.

- Schema v2 estricto.
- Strings acotados en longitud.
- Colecciones acotadas en tamano.
- Errores accionables en espanol.
- Validacion 100% servidor, sin escrituras parciales.

La importacion JSON se lee por chunks con limite maximo de `512 KB` en ambos flujos.

## Compatibilidad de consumidores

- **LaTeX/PDF**: las cuatro plantillas de `app/latex_templates/cv/` reciben la representacion normalizada. El TEX de un CV legacy queda sin cambios.
- **ATS**: lee la misma representacion normalizada y mantiene los mismos siete criterios, pesos, topes y umbrales. No se agrega ningun criterio.

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

Flujo manual del editor estructurado, disponible solo en `feature/structured-cv-complete`:

1. Crear un CV desde `/cvs/new/structured`.
2. Completar las secciones, agregar items y reordenarlos con `Subir`/`Bajar`.
3. Verificar que un envio invalido responde 422 y conserva lo tipeado.
4. Editar el mismo CV desde `/cvs/{cv_id}/structured-edit`.
5. Verificar que el formulario plano legacy no modifica un CV estructurado.
6. Exportar JSON y comprobar el sobre schema `2` con la variante `cv-schema2`.
7. Reimportar ese JSON y verificar que crea un CV nuevo sin tocar el origen.
8. Exportar TEX y PDF y revisar que el contenido sale completo.

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
- El editor estructurado no esta publicado: vive solo en `feature/structured-cv-complete`, sin version, release ni tag.
- El editor estructurado no tiene drag and drop. El reordenamiento es por botones.
- Un CV estructurado no puede editarse desde el formulario plano legacy.
