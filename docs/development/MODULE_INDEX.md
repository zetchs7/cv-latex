# Module Index

| Modulo | Ruta | Objetivo | Version | Estado | Dependencias | Documentacion relacionada |
| --- | --- | --- | --- | --- | --- | --- |
| App | `app/main.py` | Crear instancia FastAPI, montar estaticos, registrar rutas y exponer healthcheck. | 0.3.0 | Activo Etapa 2 | FastAPI | `README.md`, `docs/development/DEVELOPMENT_LOG.md` |
| Dashboard | `app/routes/dashboard.py`, `app/templates/` | Mostrar estado de la app y navegar al modulo CVs. | 0.3.0 | Activo Etapa 2 | FastAPI, Jinja2 | `README.md` |
| Database | `app/database.py` | Preparar SQLite local en `/data/app.db` y crear tablas tecnicas y `cvs`. | 0.3.0 | Activo Etapa 2 | sqlite3 | `docs/adr/ADR-0001-stack-mvp.md` |
| CV Builder Core | `app/routes/cvs.py`, `app/repositories/cv_repository.py`, `app/templates/cvs/` | CRUD basico de CVs con formularios HTML, SQLite y acceso a vista TEX. | 0.3.0 | Activo Etapa 2 | FastAPI, Jinja2, sqlite3 | `docs/development/CV_BUILDER_CORE.md` |
| CV Model | `app/models.py`, `app/schemas.py` | Modelo base `CV` y schema de formulario `CVFormData`. | 0.3.0 | Activo Etapa 2 | dataclasses | `docs/development/CV_BUILDER_CORE.md` |
| CV Validations | `app/validations/cv_validations.py` | Validar campos obligatorios, email y limites de longitud. | 0.3.0 | Activo Etapa 2 | re | `docs/development/CV_BUILDER_CORE.md` |
| LaTeX Templates | `app/latex_templates/cv/` | Plantillas propias para generar contenido `.tex` de CVs. | 0.3.0 | Activo Etapa 2 | LaTeX, Jinja2 | `docs/development/LATEX_TEMPLATES.md` |
| LaTeX Service | `app/services/latex_service.py` | Renderizar contenido `.tex` desde CVs guardados y plantillas disponibles. | 0.3.0 | Activo Etapa 2 | Jinja2 | `docs/development/LATEX_TEMPLATES.md` |
| LaTeX Sanitizer | `app/validations/latex_sanitizer.py` | Escapar caracteres especiales LaTeX preservando caracteres comunes en espanol. | 0.3.0 | Activo Etapa 2 | Python stdlib | `docs/development/LATEX_TEMPLATES.md` |
| Docker | `Dockerfile`, `docker-compose.yml` | Ejecutar la app en un contenedor portable con bind mount `./data:/data`. | 0.3.0 | Activo Etapa 2 | Docker Compose | `docs/adr/ADR-0002-docker-compose-portability.md` |
| Docs | `docs/development/`, `docs/adr/` | Registrar decisiones, comandos, versionado, ramas y cambios por etapa. | 0.3.0 | Activo Etapa 2 | Markdown | `docs/development/COMMAND_LOG.md` |
