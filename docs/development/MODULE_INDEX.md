# Module Index

| Modulo | Ruta | Objetivo | Version | Estado | Dependencias | Documentacion relacionada |
| --- | --- | --- | --- | --- | --- | --- |
| App | `app/main.py` | Crear instancia FastAPI, montar estaticos, registrar rutas y exponer healthcheck. | 0.1.0 | Activo Etapa 0 | FastAPI | `README.md`, `docs/development/DEVELOPMENT_LOG.md` |
| Dashboard | `app/routes/dashboard.py`, `app/templates/` | Mostrar estado de la app y navegar al modulo CVs. | 0.2.0 | Activo Etapa 1 | FastAPI, Jinja2 | `README.md` |
| Database | `app/database.py` | Preparar SQLite local en `/data/app.db` y crear tablas tecnicas y `cvs`. | 0.2.0 | Activo Etapa 1 | sqlite3 | `docs/adr/ADR-0001-stack-mvp.md` |
| CV Builder Core | `app/routes/cvs.py`, `app/repositories/cv_repository.py`, `app/templates/cvs/` | CRUD basico de CVs con formularios HTML y SQLite. | 0.2.0 | Activo Etapa 1 | FastAPI, Jinja2, sqlite3 | `docs/development/CV_BUILDER_CORE.md` |
| CV Model | `app/models.py`, `app/schemas.py` | Modelo base `CV` y schema de formulario `CVFormData`. | 0.2.0 | Activo Etapa 1 | dataclasses | `docs/development/CV_BUILDER_CORE.md` |
| CV Validations | `app/validations/cv_validations.py` | Validar campos obligatorios, email y limites de longitud. | 0.2.0 | Activo Etapa 1 | re | `docs/development/CV_BUILDER_CORE.md` |
| Docker | `Dockerfile`, `docker-compose.yml` | Ejecutar la app en un contenedor portable con bind mount `./data:/data`. | 0.2.0 | Activo Etapa 1 | Docker Compose | `docs/adr/ADR-0002-docker-compose-portability.md` |
| Docs | `docs/development/`, `docs/adr/` | Registrar decisiones, comandos, versionado, ramas y cambios por etapa. | 0.2.0 | Activo Etapa 1 | Markdown | `docs/development/COMMAND_LOG.md` |
