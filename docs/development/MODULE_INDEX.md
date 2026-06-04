# Module Index

| Modulo | Ruta | Objetivo | Version | Estado | Dependencias | Documentacion relacionada |
| --- | --- | --- | --- | --- | --- | --- |
| App | `app/main.py` | Crear instancia FastAPI, montar estaticos, registrar rutas y exponer healthcheck. | 0.5.0 | Activo Etapa 4 | FastAPI | `README.md`, `docs/development/DEVELOPMENT_LOG.md` |
| Dashboard | `app/routes/dashboard.py`, `app/templates/` | Mostrar estado de la app y navegar a los modulos CVs y Cover Letters. | 0.5.0 | Activo Etapa 4 | FastAPI, Jinja2 | `README.md` |
| Database | `app/database.py` | Preparar SQLite local en `/data/app.db` y crear tablas tecnicas, `cvs` y `cover_letters`. | 0.5.0 | Activo Etapa 4 | sqlite3 | `docs/adr/ADR-0001-stack-mvp.md` |
| CV Builder Core | `app/routes/cvs.py`, `app/repositories/cv_repository.py`, `app/templates/cvs/` | CRUD de CVs con formularios HTML, importacion JSON limitada por tamano y exportaciones. | 0.5.0 | Activo Etapa 4 | FastAPI, Jinja2, sqlite3 | `docs/development/CV_BUILDER_CORE.md` |
| Cover Letters | `app/routes/cover_letters.py`, `app/repositories/cover_letter_repository.py`, `app/templates/cover_letters/` | CRUD de cartas con asociacion opcional a CV y exportaciones TEX/PDF. | 0.5.0 | Activo Etapa 4 | FastAPI, Jinja2, sqlite3 | `docs/development/COVER_LETTERS.md` |
| Domain Models | `app/models.py`, `app/schemas.py` | Modelos `CV` y `CoverLetter`, mas schemas de formulario asociados. | 0.5.0 | Activo Etapa 4 | dataclasses | `docs/development/CV_BUILDER_CORE.md`, `docs/development/COVER_LETTERS.md` |
| CV Validations | `app/validations/cv_validations.py` | Validar campos obligatorios, email, limites de longitud y titulo seguro de duplicado. | 0.5.0 | Activo Etapa 4 | re | `docs/development/CV_BUILDER_CORE.md` |
| Cover Letter Validations | `app/validations/cover_letter_validations.py` | Validar campos obligatorios, longitudes y asociacion opcional a CV activo. | 0.5.0 | Activo Etapa 4 | Python stdlib | `docs/development/COVER_LETTERS.md` |
| LaTeX Templates | `app/latex_templates/cv/`, `app/latex_templates/cover_letter/` | Plantillas propias con mapeo Unicode para generar contenido `.tex` y PDF extraible de CVs y cartas. | 0.5.0 | Activo Etapa 4 | LaTeX, Jinja2, cmap, lmodern | `docs/development/LATEX_TEMPLATES.md`, `docs/development/COVER_LETTERS.md` |
| LaTeX Service | `app/services/latex_service.py` | Renderizar contenido `.tex` desde CVs y cartas guardadas usando plantillas registradas. | 0.5.0 | Activo Etapa 4 | Jinja2 | `docs/development/LATEX_TEMPLATES.md` |
| Export Service | `app/services/export_service.py` | Guardar TEX/JSON en `/data/exports`, importar JSON por chunks y sanitizar nombres de archivo para CVs y cartas. | 0.5.0 | Activo Etapa 4 | Python stdlib | `README.md`, `docs/development/DEVELOPMENT_LOG.md` |
| PDF Service | `app/services/pdf_service.py` | Compilar TEX con `pdflatex` en temporal controlado y separar mensaje seguro de detalle tecnico para CVs y cartas. | 0.5.0 | Activo Etapa 4 | TeX Live, Python stdlib | `docs/adr/ADR-0004-latex-rendering.md` |
| PDF Text Extraction Validation | `Dockerfile`, `tests/test_latex_service.py` | Validar mapeo Unicode de plantillas y extraccion con `pdftotext`. | 0.5.0 | Activo Etapa 4 | poppler-utils | `docs/development/DEVELOPMENT_LOG.md` |
| LaTeX Sanitizer | `app/validations/latex_sanitizer.py` | Escapar caracteres especiales LaTeX preservando caracteres comunes en espanol. | 0.5.0 | Activo Etapa 4 | Python stdlib | `docs/development/LATEX_TEMPLATES.md` |
| Docker | `Dockerfile`, `docker-compose.yml` | Ejecutar la app en un contenedor portable con bind mount `./data:/data`, bind local `127.0.0.1` por defecto y utilidades PDF. | 0.5.0 | Activo Etapa 4 | Docker Compose, TeX Live, poppler-utils | `docs/adr/ADR-0002-docker-compose-portability.md` |
| Docs | `docs/development/`, `docs/adr/` | Registrar decisiones, comandos, versionado, ramas y cambios por etapa. | 0.5.0 | Activo Etapa 4 | Markdown | `docs/development/COMMAND_LOG.md` |
