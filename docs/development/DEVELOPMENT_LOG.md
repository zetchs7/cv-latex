# Development Log

## Documentation Center

- Fecha: 2026-06-05
- Rama: `feature/documentation-center`
- Objetivo: agregar una seccion web de documentacion con PDFs embebidos, servidos localmente y generados desde fuentes Markdown editables.
- Modulos afectados: `documentation`, `dashboard`, `layout`, `static/docs`, `docs/user`, `docs/development`, `tests`.
- Resumen de cambios:
  - Se agrego la ruta `app/routes/documentation.py`.
  - Se agrego el template `app/templates/documentation/index.html`.
  - Se incorporo el acceso `Documentacion` en header y dashboard.
  - Se agrego `app/services/documentation_service.py` para catalogar documentos y generar PDFs desde Markdown.
  - Se crearon las fuentes `docs/user/PROJECT_TECHNICAL_DOCUMENTATION.md` y `docs/user/WEB_USAGE_MANUAL.md`.
  - Se generaron y publicaron los PDFs en `app/static/docs/`.
  - Se agregaron tests basicos de rutas para la nueva seccion.
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker run --rm -v "${PWD}:/workspace" -w /workspace cv-latex-app python -m app.services.documentation_service`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - `Invoke-WebRequest` sobre `/documentation/`, `/documentation/technical` y los dos PDFs estaticos
  - `pdftotext` y `pdftoppm` dentro del contenedor para validar legibilidad
  - `git diff --check`
- Resultado: seccion de documentacion funcional, assets PDF locales servidos desde la app y contenido legible validado antes del tag `v0.8.0`.

### Ajuste posterior - lectura HTML

- Cambio de decision: la lectura principal deja de usar `iframe` PDF y pasa a paginas HTML dentro de la app.
- Se agrego parsing simple de Markdown a secciones HTML para `technical` y `usage`.
- Cada pagina mantiene indice, bloques visuales y accion `Descargar PDF`.
- Los PDFs quedan como artefacto descargable y no como flujo principal de lectura.
- La imagen Docker pasa a incluir `docs/` para que el runtime pueda leer las fuentes Markdown durante el render HTML.

## Release Cleanup v0.8.0 - Changelog Consolidation

- Fecha: 2026-06-05
- Rama: `feature/release-cleanup-v0.8.0`
- Objetivo: integrar las notas del cleanup dentro de la unica entrada `0.8.0` del changelog.
- Modulos afectados: `docs/development`.
- Resumen de cambios:
  - Se elimino el encabezado duplicado `0.8.0 - 2026-06-05`.
  - Las notas de cleanup quedaron integradas en la entrada existente `0.8.0 - 2026-06-04`.
- Resultado: la documentacion de release queda no ambigua y sin versiones repetidas.

## Release Cleanup v0.8.0

- Fecha: 2026-06-05
- Rama: `feature/release-cleanup-v0.8.0`
- Objetivo: alinear version y documentacion antes del tag `v0.8.0`.
- Modulos afectados: `Dockerfile`, `README.md`, `docs/development`.
- Resumen de cambios:
  - Se actualizo `APP_VERSION` en `Dockerfile` a `0.8.0`.
  - Se limpio la seccion `ATS Basic Check` del README para que describa solo el analisis ATS.
  - Se registro el ajuste en logs de desarrollo para dejar trazabilidad del release cleanup.
- Resultado: cambio menor de consistencia aplicado sin tocar logica funcional ni rutas.

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

## Etapa 2 - Plantillas LaTeX y sanitizacion

- Fecha: 2026-06-02
- Rama: `feature/latex-templates`
- Objetivo: implementar plantillas LaTeX propias, sanitizacion y generacion de contenido `.tex` desde CVs guardados.
- Modulos afectados: `latex_templates`, `latex_service`, `latex_sanitizer`, `cv-builder`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego `app/latex_templates/cv/`.
  - Se crearon plantillas propias `classic.tex`, `modern.tex`, `compact.tex` y `tech.tex`.
  - Se agrego `app/services/latex_service.py`.
  - Se agrego `app/validations/latex_sanitizer.py`.
  - Se agrego vista de previsualizacion TEX en `/cvs/{cv_id}/tex`.
  - Se agrego boton `Ver TEX` en el detalle de CV.
  - Se agregaron tests basicos de sanitizacion y servicio.
  - Se actualizo la version a `0.3.0`.
- Archivos principales:
  - `app/latex_templates/cv/classic.tex`
  - `app/latex_templates/cv/modern.tex`
  - `app/latex_templates/cv/compact.tex`
  - `app/latex_templates/cv/tech.tex`
  - `app/services/latex_service.py`
  - `app/validations/latex_sanitizer.py`
  - `app/templates/cvs/tex_preview.html`
  - `tests/test_latex_sanitizer.py`
  - `tests/test_latex_service.py`
  - `docs/development/LATEX_TEMPLATES.md`
  - `docs/adr/ADR-0004-latex-rendering.md`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `python -m unittest discover -s tests`
  - `git diff --check`
  - `rg -n -P "[^\\x00-\\x7F]"`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`
  - `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -UseBasicParsing`
  - POST de creacion de CV con caracteres en espanol y especiales LaTeX
  - GET de `/cvs/{id}/tex` con `classic`, `modern`, `compact` y `tech`
  - GET de plantilla invalida con respuesta 404
  - Verificacion directa del contenido TEX dentro del contenedor
  - Eliminacion logica del CV de prueba de la etapa
- Resultado: completado localmente. El contenedor queda `healthy`, `/health` devuelve `version: 0.3.0`, las cuatro plantillas generan vista TEX y el sanitizador escapa caracteres especiales preservando texto comun en espanol.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 3.
  - Preparar push o PR solo si el usuario lo indica.

### Observaciones de validacion Etapa 2

- La primera validacion local de `test_latex_service.py` fallo porque el Python local no tiene `jinja2`; se ajusto el test para saltar solo esa prueba cuando falta la dependencia local. La generacion del servicio fue validada en Docker, donde `jinja2` esta instalado por `requirements.txt`.
- La primera validacion de vistas TEX fallo por usar `section.items`, que colisionaba con el metodo `dict.items` de Jinja. Se corrigio usando `section.item_list`.
- Se creo y elimino logicamente un CV de prueba de Etapa 2. Se conservo un CV activo preexistente (`SysAdmin Linux`) porque no corresponde a datos de prueba de esta etapa.

### Limites de alcance confirmados Etapa 2

No se implemento compilacion PDF final, descarga PDF, export TEX, export JSON, import JSON, cartas de presentacion, tracker de postulaciones, ATS ni IA.

## Correccion de validacion Etapa 2 - pytest en contenedor

- Fecha: 2026-06-03
- Rama: `feature/fix-pytest-validation`
- Objetivo: corregir la validacion pendiente de Etapa 2 agregando `pytest` a la imagen Docker para ejecutar tests dentro del contenedor.
- Modulos afectados: `docker`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego `pytest` a `requirements.txt`.
  - Se ajusto `Dockerfile` para copiar `tests/` dentro de la imagen.
  - Se reconstruyo la imagen del servicio `app`.
  - Se ejecuto `python -m pytest` dentro del contenedor.
  - Se actualizo la documentacion operativa con el flujo y el resultado.
- Archivos principales:
  - `Dockerfile`
  - `requirements.txt`
  - `docs/development/COMMAND_LOG.md`
  - `docs/development/DEVELOPMENT_LOG.md`
  - `docs/development/CHANGELOG_GENERAL.md`
- Validaciones ejecutadas:
  - `git status --short --branch`
  - `git branch --all`
  - `git fetch origin`
  - `git switch development`
  - `git merge --ff-only main`
  - `git switch -c feature/fix-pytest-validation`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose exec app python -m pytest`
- Resultado: validacion corregida. El contenedor ahora incluye `pytest` y la suite corre dentro de Docker.
- Pendientes:
  - No hacer merge automatico.
  - Esperar validacion explicita del usuario antes de cualquier paso posterior.

### Observaciones de la correccion

- El primer intento con `docker compose exec app python -m pytest` dejo `pytest` disponible pero fallo con `collected 0 items` porque la imagen solo copiaba `app/` y no `tests/`.
- La correccion minima fue sumar `pytest` a `requirements.txt` y copiar `tests/` en `Dockerfile`. Con eso la validacion en contenedor paso con `6 passed`.

## Etapa 3 - Export Engine PDF/TEX/JSON

- Fecha: 2026-06-03
- Rama: `feature/export-engine`
- Objetivo: implementar exportacion TEX/PDF/JSON e importacion JSON desde CVs guardados, con rutas seguras y persistencia en `/data/exports`.
- Modulos afectados: `cvs`, `export_service`, `pdf_service`, `latex_service`, `docker`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego `app/services/export_service.py` para exportar TEX/JSON, sanitizar nombres y crear directorios en `/data/exports`.
  - Se agrego `app/services/pdf_service.py` para compilar con `pdflatex` dentro de un temporal controlado y guardar PDF final.
  - Se agregaron rutas de descarga TEX, descarga JSON, generacion PDF e importacion JSON.
  - Se agrego importacion JSON desde formulario multipart creando siempre un nuevo CV.
  - Se agregaron tests unitarios para exportaciones, importacion y compilacion PDF mockeada.
  - Se actualizo Dockerfile con TeX Live para compilar las plantillas actuales.
  - Se actualizo la version a `0.4.0`.
- Archivos principales:
  - `app/services/export_service.py`
  - `app/services/pdf_service.py`
  - `app/routes/cvs.py`
  - `app/templates/cvs/detail.html`
  - `app/templates/cvs/index.html`
  - `app/templates/cvs/tex_preview.html`
  - `Dockerfile`
  - `tests/test_export_service.py`
  - `tests/test_pdf_service.py`
- Validaciones ejecutadas:
  - `git status --short --branch`
  - `git fetch origin`
  - `git rev-list --left-right --count development...origin/development`
  - `git switch -c feature/export-engine`
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `docker compose exec app python -m pytest`
  - Creacion de CV de prueba desde el contenedor
  - `GET /cvs/6/export/tex?template_key=tech`
  - `GET /cvs/6/export/json`
  - `POST /cvs/import/json`
  - `GET /cvs/6/export/pdf?template_key=tech`
  - Verificacion de archivos persistidos en `/data/exports`
  - `GET /cvs/6/tex?template_key=modern`
  - `GET /cvs/8`
- Resultado: completado localmente. El contenedor queda `healthy`, `/health` devuelve `version: 0.4.0`, `pytest` pasa con 13 tests y las exportaciones TEX/JSON/PDF funcionan por HTTP.
- Pendientes:
  - Esperar validacion explicita del usuario antes de Etapa 4.
  - No hacer merge automatico.
  - Mantener ramas feature existentes hasta que el usuario indique limpieza.

### Observaciones de validacion Etapa 3

- `python -m pytest` local en Windows no se pudo ejecutar porque ese Python local no tiene `pytest`; la validacion obligatoria se ejecuto dentro del contenedor y paso con `13 passed`.
- La primera prueba funcional detecto colision de nombres cuando TEX y PDF se generaban en paralelo para el mismo CV/plantilla en el mismo segundo. Se corrigio usando timestamp con microsegundos.
- La primera vista TEX posterior al cambio fallo por usar query params dentro de `url_for`; se corrigio construyendo el query string fuera de `url_for`.
- Dockerfile instala TeX Live en lugar de Tectonic. Motivo: Tectonic puede requerir descarga de bundles en runtime; TeX Live deja la imagen mas pesada pero reproducible. Impacto observado durante build: aproximadamente 509 MB adicionales.

### Limites de alcance confirmados Etapa 3

No se implemento cartas de presentacion, tracker de postulaciones, ATS, IA, login, PostgreSQL ni deploy cloud.

## Etapa 3.1 - PDF ATS Text Extraction / Encoding Fix

- Fecha: 2026-06-03
- Rama: `feature/pdf-ats-text-extraction`
- Objetivo: mejorar el mapeo de texto en PDFs generados para copy/paste, extraccion con herramientas PDF y compatibilidad futura con parsers ATS.
- Modulos afectados: `latex_templates`, `docker`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego `\\input{glyphtounicode}` y `\\pdfgentounicode=1` a `classic`, `modern`, `compact` y `tech`.
  - Se agrego `\\usepackage{cmap}` a las cuatro plantillas.
  - Se agrego `\\usepackage{lmodern}` para usar fuentes Latin Modern con encoding T1.
  - Se agrego `lmodern` al Dockerfile porque `lmodern.sty` no venia incluido solo con `fonts-lmodern`.
  - Se agrego `poppler-utils` al Dockerfile para validar extraccion real con `pdftotext`.
  - Se actualizo la version a `0.4.1`.
- Archivos principales:
  - `app/latex_templates/cv/classic.tex`
  - `app/latex_templates/cv/modern.tex`
  - `app/latex_templates/cv/compact.tex`
  - `app/latex_templates/cv/tech.tex`
  - `Dockerfile`
  - `tests/test_latex_service.py`
  - `README.md`
  - `docs/adr/ADR-0004-latex-rendering.md`
- Validaciones ejecutadas:
  - `git status --short --branch`
  - `git fetch origin`
  - `git switch development`
  - `git rev-list --left-right --count development...origin/development`
  - `git switch -c feature/pdf-ats-text-extraction`
  - `python -m compileall app tests`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - `docker compose exec app which pdftotext`
  - Creacion de CV de prueba con texto acentuado y caracteres espanoles.
  - Generacion de PDF con `classic`, `modern`, `compact` y `tech`.
  - Extraccion de texto con `pdftotext` para cada PDF.
- Resultado: validacion completada. Los cuatro PDFs compilan y `pdftotext` preserva `Perfil`, `tecnico` acentuado, `gestion`, `informacion`, `analisis`, `educacion`, `comunicacion`, `ñandu`, `accion` y `configuracion` con acentos en el texto extraido.
- Pendientes:
  - No avanzar a Etapa 4 sin validacion explicita.
  - Mantener pruebas con parsers ATS reales para una etapa futura.

### Observaciones de validacion Etapa 3.1

- La primera compilacion fallo por falta de `lmodern.sty`; se corrigio agregando el paquete Debian `lmodern`.
- `pdftotext` quedo disponible por `poppler-utils`, agregado solo para validacion tecnica de extraccion.
- El build final reporto aproximadamente 587 MB adicionales por dependencias LaTeX/PDF.

## Etapa 3.2 - Baseline Hardening & Consistency

- Fecha: 2026-06-04
- Rama: `feature/baseline-hardening`
- Objetivo: corregir hallazgos altos y medios del baseline antes de avanzar a nuevas features.
- Modulos afectados: `docker`, `cvs`, `export_service`, `pdf_service`, `validations`, `tests`, `docs`.
- Resumen de cambios:
  - Se limito la publicacion HTTP por defecto a `127.0.0.1` mediante `APP_HOST_BIND`.
  - Se agrego lectura controlada por chunks para import JSON con limite temprano de `512 KB`.
  - Se separo el mensaje seguro para UI del detalle tecnico de fallos PDF.
  - Se reforzo el duplicado de CV para reutilizar validaciones y truncar titulos largos de forma segura.
  - Se actualizaron tests y documentacion del baseline actual.
- Archivos principales:
  - `docker-compose.yml`
  - `.env.example`
  - `app/routes/cvs.py`
  - `app/services/export_service.py`
  - `app/services/pdf_service.py`
  - `app/repositories/cv_repository.py`
  - `app/validations/cv_validations.py`
  - `tests/test_export_service.py`
  - `tests/test_pdf_service.py`
  - `tests/test_cv_repository.py`
- Validaciones ejecutadas:
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - `Invoke-WebRequest` a `http://localhost:8000` y `/health`
  - Import JSON valido y rechazo de import excedido
  - Duplicado de CV con titulo al limite
  - Generacion PDF luego del hardening
  - `git diff --check`
- Resultado: baseline endurecido sin avanzar a Etapa 4. La app sigue operativa en localhost, el import corta por tamano, el duplicado respeta limites y el error PDF visible en UI deja de exponer logs completos.
- Pendientes:
  - Mantener este baseline como piso minimo antes de sumar modulos nuevos.
  - Validar parsers ATS reales en una etapa futura.

## Etapa 4 - Cover Letters

- Fecha: 2026-06-04
- Rama: `feature/cover-letters`
- Objetivo: implementar el modulo de cartas de presentacion con CRUD basico, asociacion opcional a CV y exportacion TEX/PDF.
- Modulos afectados: `cover_letters`, `database`, `latex_service`, `export_service`, `pdf_service`, `dashboard`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego el modelo `CoverLetter` y el schema `CoverLetterFormData`.
  - Se creo la tabla SQLite `cover_letters` con eliminacion logica y referencia opcional a CV.
  - Se implemento el repositorio `cover_letter_repository.py`.
  - Se agregaron rutas FastAPI para listar, crear, ver detalle, editar, confirmar eliminacion, eliminar, exportar TEX y generar PDF.
  - Se agregaron templates HTML bajo `app/templates/cover_letters/`.
  - Se agrego navegacion a `Cartas` desde dashboard y header.
  - Se creo la plantilla LaTeX `app/latex_templates/cover_letter/classic_letter.tex`.
  - Se extendieron `latex_service`, `export_service` y `pdf_service` para soportar cartas reutilizando el pipeline existente.
  - Se agrego documentacion especifica del modulo y se actualizo la version a `0.5.0`.
- Archivos principales:
  - `app/models.py`
  - `app/schemas.py`
  - `app/database.py`
  - `app/repositories/cover_letter_repository.py`
  - `app/routes/cover_letters.py`
  - `app/templates/cover_letters/index.html`
  - `app/templates/cover_letters/form.html`
  - `app/templates/cover_letters/detail.html`
  - `app/templates/cover_letters/confirm_delete.html`
  - `app/latex_templates/cover_letter/classic_letter.tex`
  - `app/validations/cover_letter_validations.py`
  - `docs/development/COVER_LETTERS.md`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose logs app`
  - `docker compose exec app python -m pytest`
  - `Invoke-WebRequest` a `http://localhost:8000`
  - POST de creacion de CV base para asociacion
  - POST de creacion de carta asociada
  - GET de listado y detalle de carta
  - POST de edicion de carta
  - GET de confirmacion y POST de eliminacion de carta
  - Descarga TEX y generacion PDF por HTTP
  - Verificacion de artefactos persistidos en `/data/exports`
  - Extraccion basica de texto PDF con `pdftotext`
- Resultado: etapa implementada y validada localmente. El modulo de cartas queda operativo, asociado al dashboard y reutiliza correctamente sanitizacion, exportacion TEX y compilacion PDF.
- Pendientes:
  - Esperar validacion explicita del usuario antes de cualquier merge.
  - Preparar push de la rama feature y PR hacia `development`.
  - Pedir `@codex review` manual despues del PR.

## Fix ATS - Critical Sections Status Cap

- Fecha: 2026-06-04
- Rama: `feature/ats-basic-check`
- Objetivo: impedir que CVs con secciones core faltantes queden clasificados como `Bueno`.
- Modulos afectados: `ats_service`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego deteccion de `critical_missing_sections`.
  - El score queda capado a `84` si falta una seccion critica.
  - Si faltan experiencia y educacion juntas, el score queda capado a `59` y el estado pasa a `Insuficiente`.
  - Se ampliaron los tests para cubrir CV completo, CV con experiencia sin educacion, CV con educacion sin experiencia, CV largo sin ambas y CV incompleto.
- Resultado: el status ATS ahora es consistente con recomendaciones y advertencias.

## Etapa 6 - ATS Basic Check

- Fecha: 2026-06-04
- Rama: `feature/ats-basic-check`
- Objetivo: agregar un chequeo ATS basico sobre CVs existentes con score simple, checklist, advertencias y recomendaciones sin IA.
- Modulos afectados: `ats`, `cvs`, `dashboard`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego `app/services/ats_service.py` con reglas deterministicas de validacion basica.
  - Se creo la ruta `app/routes/ats.py` para analizar CVs existentes sin mezclar la logica en `cvs.py`.
  - Se agrego un template dedicado bajo `app/templates/ats/`.
  - Se incorporo la accion `Analizar ATS` en el detalle del CV.
  - Se actualizaron dashboard, README, module index y logs a `0.7.0`.
  - Se agregaron tests del servicio ATS y una prueba basica de ruta.
  - Se agrego `httpx` a `requirements.txt` para soportar `TestClient` en los tests de rutas.
- Archivos principales:
  - `app/services/ats_service.py`
  - `app/routes/ats.py`
  - `app/templates/ats/cv_analysis.html`
  - `app/templates/cvs/detail.html`
  - `tests/test_ats_service.py`
  - `tests/test_ats_routes.py`
  - `docs/development/ATS_BASIC_CHECK.md`
- Validaciones ejecutadas:
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Analisis ATS de un CV completo
  - Analisis ATS de un CV incompleto
  - Verificacion visual de checklist, score, recomendaciones y advertencias
  - `git diff --check`
- Resultado: etapa implementada y validada localmente. El chequeo ATS queda operativo solo sobre CVs guardados y sin dependencias externas.
- Pendientes:
  - Esperar validacion explicita del usuario antes de cualquier merge.
  - Preparar push de la rama feature y PR hacia `development`.
  - Pedir `@codex review` manual despues del PR.

## Fix P1 - Cap cover-letter export filenames

- Fecha: 2026-06-04
- Rama: `feature/cover-letters`
- Objetivo: corregir el hallazgo P1 de Code Review que permitia generar filenames demasiado largos en exportaciones TEX/PDF de cartas.
- Modulos afectados: `export_service`, `latex_service`, `tests`, `docs`.
- Resumen de cambios:
  - Se agrego un helper comun para construir filenames sanitizados y capped.
  - Se acoto a `180` caracteres el filename final de exportaciones de cartas.
  - Se aplico el mismo criterio al `.tex` generado de cover letters.
  - Se mantuvo unicidad mediante `id` y timestamp en exportaciones persistidas.
  - Se agregaron tests para `company` y `position` de `160` caracteres.
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Creacion de carta con `company` y `position` al maximo permitido
  - Export TEX por HTTP
  - Export PDF por HTTP
  - Verificacion de artefactos persistidos en `/data/exports`
  - Validacion basica con `pdftotext`
  - `git diff --check`
- Resultado: fix aplicado. TEX y PDF de cartas con nombres extremos exportan correctamente sin `OSError` y los filenames finales quedan en `180` caracteres.
- Pendientes:
  - Actualizar PR #2 con el commit del fix.
  - Esperar nueva revision manual antes de merge.

## Etapa 7 - Pulido final del MVP

- Fecha: 2026-06-04
- Rama: `feature/mvp-final-polish`
- Objetivo: cerrar el MVP local con una pasada de consistencia visual, navegacion clara, documentacion operativa y validacion funcional completa.
- Modulos afectados: `dashboard`, `ats`, `cvs`, `cover_letters`, `applications`, `docs`, `docker`, `tests`.
- Resumen de cambios:
  - Se agrego una entrada dedicada `ATS` en la navegacion superior y una vista `GET /ats/` para seleccionar CVs a analizar.
  - Se ajustaron textos visibles del dashboard, ATS, Cartas y Postulaciones para mantener naming consistente.
  - La version visible del layout ahora usa `request.app.version` para evitar drift con `APP_VERSION`.
  - Se actualizo la version del proyecto a `0.8.0`.
  - Se actualizo `README.md` con arranque, detencion, rebuild, tests, persistencia, exports y backup/restore basicos.
  - Se creo `docs/development/MVP_VALIDATION.md` como checklist manual del MVP.
  - Se alinearon `MODULE_INDEX.md`, `VERSIONING.md`, `BRANCH_STRATEGY.md` y docs de modulos al baseline del MVP.
- Archivos principales:
  - `app/routes/ats.py`
  - `app/routes/dashboard.py`
  - `app/templates/layout.html`
  - `app/templates/dashboard.html`
  - `app/templates/ats/index.html`
  - `app/templates/ats/cv_analysis.html`
  - `README.md`
  - `docs/development/MVP_VALIDATION.md`
  - `docs/development/MODULE_INDEX.md`
  - `tests/test_ats_routes.py`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Requests HTTP a dashboard, `/ats/`, `/cvs/`, `/cover-letters/` y `/applications/`
  - Creacion, edicion y detalle de CV de prueba
  - Exportacion TEX/PDF/JSON de CV e importacion JSON
  - Creacion, edicion, detalle y exportacion TEX/PDF de carta
  - Creacion, edicion, detalle y asociaciones de postulacion
  - Analisis ATS sobre CV completo e incompleto
  - Verificacion de `/data/exports` y extraccion PDF con `pdftotext`
  - `git diff --check`
- Resultado: MVP local validado con Docker Compose, `pytest` en verde y flujos principales accesibles desde dashboard y header.
- Pendientes:
  - Crear PR hacia `development`.
  - Pedir `@codex review` manual.
  - Esperar validacion explicita antes de merge.

## Etapa 5 - Application Tracker

- Fecha: 2026-06-04
- Rama: `feature/application-tracker`
- Objetivo: implementar el modulo de seguimiento de postulaciones con CRUD basico, estados y asociaciones opcionales a CV y carta.
- Modulos afectados: `applications`, `database`, `dashboard`, `docs`, `tests`.
- Resumen de cambios:
  - Se agrego el modelo `Application` y el schema `ApplicationFormData`.
  - Se creo la tabla SQLite `applications` con eliminacion logica y asociaciones opcionales a CV y cover letter.
  - Se implemento el repositorio `application_repository.py`.
  - Se agregaron rutas FastAPI para listar, crear, ver detalle, editar, confirmar eliminacion y eliminar postulaciones.
  - Se agregaron templates HTML bajo `app/templates/applications/`.
  - Se agrego navegacion a `Postulaciones` desde dashboard y header.
  - Se agregaron estados permitidos y validaciones de fechas, URL y asociaciones.
  - Se agrego documentacion especifica del modulo y se actualizo la version a `0.6.0`.
- Archivos principales:
  - `app/models.py`
  - `app/schemas.py`
  - `app/database.py`
  - `app/repositories/application_repository.py`
  - `app/routes/applications.py`
  - `app/templates/applications/index.html`
  - `app/templates/applications/form.html`
  - `app/templates/applications/detail.html`
  - `app/templates/applications/confirm_delete.html`
  - `app/validations/application_validations.py`
  - `docs/development/APPLICATION_TRACKER.md`
- Validaciones ejecutadas:
  - `python -m compileall app tests`
  - `git diff --check`
  - `docker compose build`
  - `docker compose up -d`
  - `docker compose ps`
  - `docker compose exec app python -m pytest`
  - Requests HTTP a listado, formulario, detalle y borrado
  - Creacion de CV y carta base para asociaciones
  - Creacion, edicion y eliminacion de postulacion
  - Cambio de estado y validacion de persistencia
- Resultado: etapa implementada y validada localmente. El modulo de postulaciones queda operativo, visible en dashboard y vinculado a CVs y cartas activas.
- Pendientes:
  - Esperar validacion explicita del usuario antes de cualquier merge.
  - Preparar push de la rama feature y PR hacia `development`.
  - Pedir `@codex review` manual despues del PR.
