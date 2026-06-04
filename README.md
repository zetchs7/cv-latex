# CV LaTeX Builder

Aplicacion web local, pequena y portable para construir CVs, cartas de presentacion y seguimiento de postulaciones profesionales con formularios web, plantillas LaTeX propias y exportaciones TEX/PDF/JSON. El proyecto se trabaja por etapas auditables; esta version corresponde a la Etapa 5.

## Estado actual

- Version: `0.6.0`
- Etapa: `5 - Application Tracker`
- Dashboard local: `http://localhost:8000`
- Persistencia: `./data` en el host, montado como `/data` dentro del contenedor
- Exportaciones: `/data/exports` dentro del contenedor, visible en `./data/exports` en el host

## Stack

- Backend: Python, FastAPI
- Templates: Jinja2
- Frontend: HTML, CSS simple, JavaScript minimo
- Persistencia: SQLite en `/data/app.db`
- Contenedores: Docker Compose
- PDF: TeX Live con `pdflatex` dentro del contenedor
- Extraccion de texto PDF: `pdftotext` disponible en el contenedor para validacion tecnica

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
- `APP_HOST_BIND`: interfaz del host usada para publicar el puerto HTTP. Por defecto `127.0.0.1`.
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

Las exportaciones persistidas se guardan en:

```text
/data/exports
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
|   |   |-- application_repository.py
|   |   |-- cv_repository.py
|   |   `-- cover_letter_repository.py
|   |-- routes/
|   |   |-- applications.py
|   |   |-- cover_letters.py
|   |   |-- cvs.py
|   |   `-- dashboard.py
|   |-- services/
|   |   |-- export_service.py
|   |   |-- file_naming.py
|   |   |-- latex_service.py
|   |   `-- pdf_service.py
|   |-- latex_templates/
|   |   |-- cover_letter/
|   |   |   `-- classic_letter.tex
|   |   `-- cv/
|   |       |-- classic.tex
|   |       |-- modern.tex
|   |       |-- compact.tex
|   |       `-- tech.tex
|   |-- templates/
|   |   |-- applications/
|   |   |   |-- confirm_delete.html
|   |   |   |-- detail.html
|   |   |   |-- form.html
|   |   |   `-- index.html
|   |   |-- cover_letters/
|   |   |   |-- confirm_delete.html
|   |   |   |-- detail.html
|   |   |   |-- form.html
|   |   |   `-- index.html
|   |   |-- cvs/
|   |   |   |-- confirm_delete.html
|   |   |   |-- detail.html
|   |   |   |-- form.html
|   |   |   |-- index.html
|   |   |   `-- tex_preview.html
|   |   |-- dashboard.html
|   |   `-- layout.html
|   |-- validations/
|   |   |-- application_validations.py
|   |   |-- cover_letter_validations.py
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
|   |-- test_application_repository.py
|   |-- test_application_validations.py
|   |-- test_cover_letter_repository.py
|   |-- test_cv_repository.py
|   |-- test_export_service.py
|   |-- test_latex_sanitizer.py
|   |-- test_latex_service.py
|   `-- test_pdf_service.py
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
- Etapa 3: Export Engine PDF/TEX/JSON. Completada.
- Etapa 3.1: PDF ATS Text Extraction / Encoding Fix. Completada.
- Etapa 3.2: Baseline Hardening & Consistency. Completada.
- Etapa 4: Cartas de presentacion. Completada.
- Etapa 5: Tracker de postulaciones. Completada.
- Etapa 6: ATS Basic Check.
- Etapa 7: Pulido final del MVP.

## Modulos disponibles

### CV Builder Core

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
- `GET /cvs/{cv_id}/export/tex?template_key=classic`: descargar archivo `.tex`.
- `GET /cvs/{cv_id}/export/pdf?template_key=classic`: generar y descargar PDF.
- `GET /cvs/{cv_id}/export/json`: exportar CV a JSON.
- `POST /cvs/import/json`: importar CV desde JSON y crear un nuevo registro.

### Cover Letters

Rutas disponibles:

- `GET /cover-letters/`: listar cartas activas.
- `GET /cover-letters/new`: formulario de creacion.
- `POST /cover-letters/`: crear carta.
- `GET /cover-letters/{cover_letter_id}`: detalle.
- `GET /cover-letters/{cover_letter_id}/edit`: formulario de edicion.
- `POST /cover-letters/{cover_letter_id}/edit`: actualizar carta.
- `GET /cover-letters/{cover_letter_id}/delete`: confirmacion de eliminacion.
- `POST /cover-letters/{cover_letter_id}/delete`: eliminacion logica.
- `GET /cover-letters/{cover_letter_id}/export/tex`: descargar TEX.
- `GET /cover-letters/{cover_letter_id}/export/pdf`: generar y descargar PDF.

### Application Tracker

Rutas disponibles:

- `GET /applications/`: listar postulaciones activas.
- `GET /applications/new`: formulario de creacion.
- `POST /applications/`: crear postulacion.
- `GET /applications/{application_id}`: detalle.
- `GET /applications/{application_id}/edit`: formulario de edicion.
- `POST /applications/{application_id}/edit`: actualizar postulacion.
- `GET /applications/{application_id}/delete`: confirmacion de eliminacion.
- `POST /applications/{application_id}/delete`: eliminacion logica.

Campos del modulo:

- `company`
- `position`
- `link`
- `source`
- `applied_on`
- `status`
- `associated_cv_id` opcional
- `associated_cover_letter_id` opcional
- `notes`
- `next_action`
- `follow_up_date`

Estados permitidos:

- `pendiente`
- `enviado`
- `entrevista`
- `rechazado`
- `oferta`
- `pausado`

## Export Engine

Los artefactos generados se guardan en:

```text
/data/exports
```

En Docker Compose ese directorio queda persistido en:

```text
./data/exports
```

Formatos soportados:

- CVs:
  - TEX
  - PDF
  - JSON
- Cartas:
  - TEX
  - PDF

La importacion JSON siempre crea un CV nuevo con sufijo `(importado)` en el titulo. No acepta rutas de salida desde inputs del usuario, los nombres de archivo exportados se sanitizan y se acotan a un maximo seguro de `180` caracteres, y el upload JSON se lee en chunks con limite maximo de `512 KB`.

## Prueba manual rapida

1. Abrir `http://localhost:8000`.
2. Entrar a `CVs` y crear o reutilizar un CV.
3. Entrar a `Cartas` y crear o reutilizar una carta.
4. Entrar a `Postulaciones`.
5. Crear una postulacion y asociarla opcionalmente a un CV y a una carta.
6. Editar la postulacion y cambiar su estado.
7. Abrir el detalle.
8. Eliminarla desde la pantalla de confirmacion.
9. Confirmar persistencia en SQLite.
10. Confirmar que los archivos de export siguen quedando en `./data/exports`.
11. Exportar un CV a JSON e importarlo de nuevo.
12. Probar un JSON artificialmente grande y verificar el rechazo con mensaje claro.

## Troubleshooting basico

- Si el puerto `8000` esta ocupado, detener el proceso que lo usa o ajustar el host bind/puerto publicado en `docker-compose.yml`.
- Si la app no inicia, revisar `docker compose logs app`.
- Si SQLite no se crea, verificar que exista `./data` y que Docker pueda montar esa carpeta.
- Si Docker no responde, verificar que Docker Desktop o el daemon de Docker esten activos.
- Si un PDF falla al compilar, revisar `docker compose logs app` para el detalle tecnico del error LaTeX.

## Alcance de esta version

Incluye dashboard, CV Builder Core, cover letters, application tracker, plantillas LaTeX propias, sanitizacion, generacion de contenido `.tex`, exportacion TEX/PDF/JSON, importacion JSON con lectura acotada, hardening basico de errores PDF, inicializacion tecnica de SQLite, archivos estaticos, Docker Compose y documentacion.

No incluye ATS, IA, login, PostgreSQL ni deploy cloud.
