# Development Log

## Etapa 0 - Base tecnica, Docker y documentacion inicial

- Fecha: 2026-06-02
- Rama: `feature/base-docker-app`
- Objetivo: crear la base minima del proyecto con FastAPI, Jinja2, SQLite preparado, Docker Compose y documentacion inicial.
- Modulos afectados: `app`, `dashboard`, `database`, `docker`, `docs`.
- Resumen de cambios:
  - Se creo una app FastAPI minima con dashboard renderizado por Jinja2.
  - Se preparo SQLite en `/data/app.db` con una tabla tecnica `app_metadata`.
  - Se agregaron archivos estaticos CSS/JS.
  - Se agrego Dockerfile y docker-compose con montaje `./data:/data`.
  - Se creo documentacion inicial de desarrollo, versionado, ramas y ADRs.
- Archivos principales:
  - `app/main.py`
  - `app/database.py`
  - `app/routes/dashboard.py`
  - `app/templates/layout.html`
  - `app/templates/dashboard.html`
  - `Dockerfile`
  - `docker-compose.yml`
  - `README.md`
  - `VERSION`
- Validaciones ejecutadas:
  - `git status`
  - `git branch --all`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`
  - `Invoke-WebRequest` sobre CSS y JS estaticos
  - `Test-Path -LiteralPath data`
  - `Get-ChildItem -Force -LiteralPath data`
  - `docker compose exec app ls -la /data`
  - `docker compose down`
  - `docker compose up -d` nuevamente
  - `docker compose ps` nuevamente
- Resultado: completado localmente. La app levanta en `http://localhost:8000`, el contenedor queda `healthy`, `/health` devuelve `status: ok`, `/data/app.db` existe y los assets estaticos responden 200.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 1.
  - Preparar PR hacia `development` solo si el usuario lo indica.

### Observaciones de validacion

- `docker compose build` fallo inicialmente dentro del sandbox por permisos sobre `C:\Users\zetchs\.docker`; se reejecuto con permiso elevado y finalizo correctamente.
- La verificacion con navegador interno fallo por una limitacion del runtime (`windows sandbox failed: spawn setup refresh`). Se valido por HTTP directo el dashboard, `/health`, CSS y JavaScript.

### Limites de alcance confirmados

No se implemento CV Builder, LaTeX, PDF, cartas de presentacion, postulaciones, ATS ni IA.

## Etapa 1 - CV Builder Core

- Fecha: 2026-06-02
- Rama: `feature/cv-builder-core`
- Objetivo: implementar el modulo base de CVs con CRUD simple, formularios HTML y persistencia SQLite.
- Modulos afectados: `app`, `dashboard`, `database`, `cv-builder`, `validations`, `docs`, `docker`.
- Resumen de cambios:
  - Se agrego modelo base `CV`.
  - Se agrego schema de formulario `CVFormData`.
  - Se creo tabla SQLite `cvs` con timestamps y eliminacion logica mediante `deleted_at`.
  - Se implementaron rutas para listar, crear, ver detalle, editar, duplicar, confirmar eliminacion y eliminar logicamente.
  - Se agregaron templates HTML simples para listado, formulario, detalle y confirmacion.
  - Se agrego navegacion desde dashboard y header hacia `CVs`.
  - Se centralizaron validaciones del formulario en `app/validations/cv_validations.py`.
  - Se actualizo la version a `0.2.0`.
- Archivos principales:
  - `app/models.py`
  - `app/schemas.py`
  - `app/database.py`
  - `app/repositories/cv_repository.py`
  - `app/routes/cvs.py`
  - `app/templates/cvs/index.html`
  - `app/templates/cvs/form.html`
  - `app/templates/cvs/detail.html`
  - `app/templates/cvs/confirm_delete.html`
  - `app/validations/cv_validations.py`
  - `app/static/css/app.css`
  - `docs/development/CV_BUILDER_CORE.md`
- Validaciones ejecutadas:
  - `python -m compileall app`
  - `rg -n -P "[^\\x00-\\x7F]"`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/cvs/new -UseBasicParsing`
  - POST de creacion de CV
  - POST de edicion de CV
  - POST de duplicado de CV
  - GET de confirmacion de eliminacion
  - POST de eliminacion logica
  - Verificacion SQLite de CVs activos e inactivos
  - POST invalido con respuesta 422
- Resultado: completado localmente. El contenedor queda `healthy`, la version de `/health` es `0.2.0`, el flujo CRUD basico funciona y los registros eliminados logicamente no aparecen activos.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 2.
  - Preparar push o PR solo si el usuario lo indica.

### Observaciones de validacion Etapa 1

- El primer arranque fallo por anotaciones de retorno `HTMLResponse | RedirectResponse` en rutas FastAPI. Causa: FastAPI intento construir un response model Pydantic con esa union. Correccion aplicada: quitar esas anotaciones en las rutas POST afectadas.
- Los CVs de prueba creados durante validacion quedaron eliminados logicamente. El listado activo quedo en cero; SQLite conserva dos registros con `deleted_at` por trazabilidad local.

### Limites de alcance confirmados Etapa 1

No se implemento LaTeX, generacion PDF, export TEX, export JSON, cartas de presentacion, tracker de postulaciones, ATS ni IA.
