# CV LaTeX Builder

Aplicacion web local, pequena y portable para construir curriculums vitae profesionales con formularios web y plantillas LaTeX propias. El proyecto se trabaja por etapas auditables; esta version inicial corresponde a la Etapa 0 y solo incluye la base tecnica.

## Estado actual

- Version: `0.2.0`
- Etapa: `1 - CV Builder Core`
- Dashboard local: `http://localhost:8000`
- Persistencia: `./data` en el host, montado como `/data` dentro del contenedor

## Stack

- Backend: Python, FastAPI
- Templates: Jinja2
- Frontend: HTML, CSS simple, JavaScript minimo
- Persistencia: SQLite en `/data/app.db`
- Contenedores: Docker Compose

HTMX queda previsto para interacciones progresivas en etapas posteriores. En Etapa 0 no se agrega comportamiento dinamico falso porque el alcance es solo la base tecnica.

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
|   |-- templates/
|   |   |-- layout.html
|   |   |-- dashboard.html
|   |   `-- cvs/
|   |       |-- index.html
|   |       |-- form.html
|   |       |-- detail.html
|   |       `-- confirm_delete.html
|   |-- validations/
|   |   `-- cv_validations.py
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
|   `-- .gitkeep
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
- Etapa 2: Plantillas LaTeX propias y sanitizacion.
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

La eliminacion no borra fisicamente el registro; marca `deleted_at` en SQLite.

## Prueba manual rapida

1. Abrir `http://localhost:8000`.
2. Entrar a `CVs`.
3. Crear un CV.
4. Editarlo.
5. Duplicarlo.
6. Eliminarlo desde la pantalla de confirmacion.
7. Confirmar que no aparece en el listado activo.

## Troubleshooting basico

- Si el puerto `8000` esta ocupado, detener el proceso que lo usa o ajustar el puerto publicado en `docker-compose.yml`.
- Si la app no inicia, revisar `docker compose logs app`.
- Si SQLite no se crea, verificar que exista `./data` y que Docker pueda montar esa carpeta.
- Si Docker no responde, verificar que Docker Desktop o el daemon de Docker esten activos.

## Alcance de esta version

Incluye dashboard, CV Builder Core, inicializacion tecnica de SQLite, archivos estaticos, Docker Compose y documentacion inicial.

No incluye LaTeX, PDF, exportaciones TEX/JSON, cartas, postulaciones, ATS ni IA.
