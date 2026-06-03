# Module Index

| Modulo | Ruta | Objetivo | Version | Estado | Dependencias | Documentacion relacionada |
| --- | --- | --- | --- | --- | --- | --- |
| App | `app/main.py` | Crear instancia FastAPI, montar estaticos, registrar rutas y exponer healthcheck. | 0.1.0 | Activo Etapa 0 | FastAPI | `README.md`, `docs/development/DEVELOPMENT_LOG.md` |
| Dashboard | `app/routes/dashboard.py`, `app/templates/` | Mostrar estado base y placeholders de modulos futuros. | 0.1.0 | Activo Etapa 0 | FastAPI, Jinja2 | `README.md` |
| Database | `app/database.py` | Preparar SQLite local en `/data/app.db` sin modelos de negocio. | 0.1.0 | Activo Etapa 0 | sqlite3 | `docs/adr/ADR-0001-stack-mvp.md` |
| Docker | `Dockerfile`, `docker-compose.yml` | Ejecutar la app en un contenedor portable con bind mount `./data:/data`. | 0.1.0 | Activo Etapa 0 | Docker Compose | `docs/adr/ADR-0002-docker-compose-portability.md` |
| Docs | `docs/development/`, `docs/adr/` | Registrar decisiones, comandos, versionado, ramas y cambios por etapa. | 0.1.0 | Activo Etapa 0 | Markdown | `docs/development/COMMAND_LOG.md` |
