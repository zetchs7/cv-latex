# CV LaTeX Builder

Aplicacion web local, pequena y portable para construir curriculums vitae profesionales con formularios web y plantillas LaTeX propias. El proyecto se trabaja por etapas auditables; esta version corresponde a la Etapa 2 y genera contenido `.tex` sin compilar PDF.

## Estado actual

- Version: `0.3.0`
- Etapa: `2 - Plantillas LaTeX y sanitizacion`
- Dashboard local: `http://localhost:8000`
- Persistencia: `./data` en el host, montado como `/data` dentro del contenedor

## Stack

- Backend: Python, FastAPI
- Templates: Jinja2
- Frontend: HTML, CSS simple, JavaScript minimo
- Persistencia: SQLite en `/data/app.db`
- Contenedores: Docker Compose

HTMX queda previsto para interacciones progresivas en etapas posteriores. Las funcionalidades actuales se mantienen server-side con HTML simple.

## Requisitos

- Docker
- Docker Compose v2

## Configuracion

Copiar `.env.example` a `.env` solo si se necesita ajustar configuracion local. El proyecto funciona con los valores por defecto definidos en `docker-compose.yml`.

Variables principales:

- `APP_ENV`: entorno logico de ejecucion.
- `APP_DATA_DIR`: directorio persistente dentro del contenedor. En Docker debe ser `/data`.
- `APP_DB_FILENAME`: nombre del archivo SQLite.
- `APP_VERSION`: version visible de la aplicacion.

## Levantar la aplicacion

```bash
docker compose build
docker compose up -d
docker compose ps
```

Abrir:

```text
http://localhost:8000
```

## Ver logs

```bash
docker compose logs app
```

## Detener

```bash
docker compose down
```

Advertencia: `docker compose down -v` elimina volumenes nombrados si existieran. En esta etapa la persistencia usa bind mount `./data:/data`, por lo que no debe usarse para limpiar datos sin revisar antes.

## Persistencia

La carpeta local `./data` se monta como `/data` dentro del contenedor. La base SQLite se prepara en:

```text
/data/app.db
```

El repositorio solo versiona `data/.gitkeep`; no se versionan bases SQLite reales ni datos personales.

## Estructura actual

```text
.
|-- app/
|   |-- main.py
|   |-- database.py
|   |-- models.py
|   |-- schemas.py
|   |-- repositories/
|   |   `-- cv_repository.py
|   |-- routes/
|   |   |-- cvs.py
|   |   `-- dashboard.py
|   |-- services/
|   |   `-- latex_service.py
|   |-- latex_templates/
|   |   `-- cv/
|   |       |-- classic.tex
|   |       |-- modern.tex
|   |       |-- compact.tex
|   |       `-- tech.tex
|   |-- templates/
|   |   |-- layout.html
|   |   |-- dashboard.html
|   |   `-- cvs/
|   |       |-- index.html
|   |       |-- form.html
|   |       |-- detail.html
|   |       |-- tex_preview.html
|   |       `-- confirm_delete.html
|   |-- validations/
|   |   |-- cv_validations.py
|   |   `-- latex_sanitizer.py
|   `-- static/
|       |-- css/
|       |   `-- app.css
|       `-- js/
|           `-- app.js
|-- data/
|   `-- .gitkeep
|-- docs/
|   |-- development/
|   `-- adr/
|-- tests/
|   |-- test_latex_sanitizer.py
|   `-- test_latex_service.py
|-- docker-compose.yml
|-- Dockerfile
|-- requirements.txt
|-- .env.example
|-- .gitignore
`-- VERSION
```

## Roadmap

- Etapa 0: Base tecnica, Docker, SQLite preparado y documentacion inicial. Completada.
- Etapa 1: CV Builder Core. Completada.
- Etapa 2: Plantillas LaTeX propias y sanitizacion. Completada.
- Etapa 3: Export Engine PDF/TEX/JSON.
- Etapa 4: Cartas de presentacion.
- Etapa 5: Tracker de postulaciones.
- Etapa 6: ATS Basic Check.
- Etapa 7: Pulido final del MVP.

## CV Builder Core

Rutas disponibles:

- `GET /cvs/`: listar CVs activos.
- `GET /cvs/new`: formulario de creacion.
- `POST /cvs/`: crear CV.
- `GET /cvs/{cv_id}`: detalle.
- `GET /cvs/{cv_id}/edit`: formulario de edicion.
- `POST /cvs/{cv_id}/edit`: actualizar CV.
- `POST /cvs/{cv_id}/duplicate`: duplicar CV.
- `GET /cvs/{cv_id}/delete`: confirmacion de eliminacion.
- `POST /cvs/{cv_id}/delete`: eliminacion logica.
- `GET /cvs/{cv_id}/tex?template_key=classic`: previsualizar contenido `.tex`.

La eliminacion no borra fisicamente el registro; marca `deleted_at` en SQLite.

## Plantillas LaTeX

Plantillas propias disponibles:

- `classic`
- `modern`
- `compact`
- `tech`

La ruta `/cvs/{cv_id}/tex` genera una previsualizacion del contenido `.tex` desde un CV guardado. Esta etapa no implementa descarga, exportacion ni compilacion PDF.

La sanitizacion esta en `app/validations/latex_sanitizer.py` y escapa caracteres especiales de LaTeX como `%`, `&`, `$`, `_`, `#`, `{`, `}`, `~`, `^` y `\`, preservando caracteres comunes en espanol mediante UTF-8.

## Prueba manual rapida

1. Abrir `http://localhost:8000`.
2. Entrar a `CVs`.
3. Crear un CV.
4. Editarlo.
5. Duplicarlo.
6. Eliminarlo desde la pantalla de confirmacion.
7. Abrir `Ver TEX` desde el detalle de un CV.
8. Cambiar entre plantillas.
9. Confirmar que no aparece en el listado activo si se elimina.

## Troubleshooting basico

- Si el puerto `8000` esta ocupado, detener el proceso que lo usa o ajustar el puerto publicado en `docker-compose.yml`.
- Si la app no inicia, revisar `docker compose logs app`.
- Si SQLite no se crea, verificar que exista `./data` y que Docker pueda montar esa carpeta.
- Si Docker no responde, verificar que Docker Desktop o el daemon de Docker esten activos.

## Alcance de esta version

Incluye dashboard, CV Builder Core, plantillas LaTeX propias, sanitizacion, generacion de contenido `.tex`, inicializacion tecnica de SQLite, archivos estaticos, Docker Compose y documentacion.

No incluye compilacion PDF, descarga PDF, export TEX, export JSON, import JSON, cartas, postulaciones, ATS ni IA.
