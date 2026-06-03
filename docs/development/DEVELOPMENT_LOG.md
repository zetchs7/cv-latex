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
