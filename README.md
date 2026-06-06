# CV LaTeX Builder

Aplicacion web local, pequena y portable para construir CVs, cartas de presentacion, seguimiento de postulaciones y chequeos ATS basicos con formularios web, plantillas LaTeX propias y exportaciones TEX/PDF/JSON. El proyecto se trabajo por etapas auditables; esta version corresponde al pulido final del MVP local.

## Estado actual

- Version: `0.8.0`
- Base estable: `tag v0.8.0`
- Commit base estable: `eab9556 fix(docs): render documentation as html with pdf downloads`
- Etapa visual en trabajo: `8.1.2.1 - Correccion fina visual final antes del PR`
- Dashboard local: `http://localhost:8000`
- Persistencia: `./data` en el host, montado como `/data` dentro del contenedor
- Exportaciones: `/data/exports` dentro del contenedor, visible en `./data/exports` en el host

## Stack

- Backend: Python, FastAPI
- Templates: Jinja2
- Frontend: HTML server-side, CSS propio con dark/light mode y JavaScript minimo para UX local
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

## Reconstruir la app

```bash
docker compose build
docker compose up -d
```

## Ver logs

```bash
docker compose logs app
```

## Detener

```bash
docker compose down
```

## Correr tests

```bash
docker compose exec app python -m pytest
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

## Backup basico

Base SQLite:

```bash
mkdir -p backups
cp data/app.db backups/app-YYYYMMDD-HHMMSS.db
```

Exportaciones:

```bash
mkdir -p backups
cp -r data/exports backups/exports-YYYYMMDD-HHMMSS
```

## Restore basico

Detener la app:

```bash
docker compose down
```

Restaurar base:

```bash
cp backups/app-YYYYMMDD-HHMMSS.db data/app.db
```

Restaurar exportaciones:

```bash
rm -rf data/exports
cp -r backups/exports-YYYYMMDD-HHMMSS data/exports
```

Volver a levantar:

```bash
docker compose up -d
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
|   |   |-- ats.py
|   |   |-- cover_letters.py
|   |   |-- cvs.py
|   |   |-- dashboard.py
|   |   `-- documentation.py
|   |-- services/
|   |   |-- ats_service.py
|   |   |-- documentation_service.py
|   |   |-- export_service.py
|   |   |-- file_naming.py
|   |   |-- latex_service.py
|   |   `-- pdf_service.py
|   |-- template_utils.py
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
|   |   |-- ats/
|   |   |   |-- cv_analysis.html
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
|   |   |-- documentation/
|   |   |   |-- detail.html
|   |   |   `-- index.html
|   |   `-- layout.html
|   |-- validations/
|   |   |-- application_validations.py
|   |   |-- cover_letter_validations.py
|   |   |-- cv_validations.py
|   |   `-- latex_sanitizer.py
|   `-- static/
|       |-- css/
|       |   `-- app.css
|       |-- docs/
|       |   |-- Manual_Uso_Web_CV_LaTeX_Builder.pdf
|       |   `-- Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf
|       `-- js/
|           `-- app.js
|-- data/
|   `-- .gitkeep
|-- docs/
|   |-- user/
|   |   |-- PROJECT_TECHNICAL_DOCUMENTATION.md
|   |   `-- WEB_USAGE_MANUAL.md
|   |-- development/
|   |   `-- PROJECT_HISTORY_ROLLBACK.md
|   `-- adr/
|-- tests/
|   |-- test_application_repository.py
|   |-- test_application_validations.py
|   |-- test_ats_routes.py
|   |-- test_ats_service.py
|   |-- test_cover_letter_repository.py
|   |-- test_cv_repository.py
|   |-- test_documentation_routes.py
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
- Etapa 6: ATS Basic Check. Completada.
- Etapa 7: Pulido final del MVP. Completada en la rama de trabajo actual.
- Mini-etapa: Documentation Center. Incluida antes del tag estable `v0.8.0`.
- Etapa 8.1: rediseno visual privado con sidebar fija, dashboard operativo, dark/light mode y borrado seguro por coincidencia exacta. En curso sobre `feature/ui-private-dashboard`.
- Correccion urgente UI: restauracion de layout pulido, cache busting de assets y navegacion privada visible dentro de la misma rama `feature/ui-private-dashboard`.
- Etapa 8.1.2.1: correccion fina visual final de dashboard, listados, detalle CV y modal ATS antes de abrir PR. En curso sobre `feature/ui-private-dashboard`.

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
- `GET /cvs/{cv_id}/delete`: confirmacion de eliminacion con texto exacto.
- `POST /cvs/{cv_id}/delete`: eliminacion logica si coincide el titulo exacto.
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
- `GET /cover-letters/{cover_letter_id}/delete`: confirmacion de eliminacion con texto exacto.
- `POST /cover-letters/{cover_letter_id}/delete`: eliminacion logica si coincide empresa y puesto exactos.
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

### ATS Basic Check

Rutas disponibles:

- `GET /ats/`: listar CVs disponibles para analisis ATS.
- `GET /ats/cvs/{cv_id}`: mostrar score, checklist y recomendaciones ATS basicas para un CV existente.

El modulo ATS Basic Check solo analiza CVs guardados y muestra:

- estado general
- score simple
- checklist de campos y secciones criticas
- advertencias
- recomendaciones

### Documentacion

Rutas disponibles:

- `GET /documentation/`: listar las dos documentaciones disponibles.
- `GET /documentation/technical`: leer la documentacion tecnica como HTML dentro de la web.
- `GET /documentation/usage`: leer el manual de uso como HTML dentro de la web.

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

## Centro de documentacion

- Fuentes editables:
  - `docs/user/PROJECT_TECHNICAL_DOCUMENTATION.md`
  - `docs/user/WEB_USAGE_MANUAL.md`
- Lectura principal en la app:
  - `http://localhost:8000/documentation/technical`
  - `http://localhost:8000/documentation/usage`
- PDFs servidos por la app:
  - `app/static/docs/Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf`
  - `app/static/docs/Manual_Uso_Web_CV_LaTeX_Builder.pdf`
- Generacion reproducible:
  - `docker run --rm -v ${PWD}:/workspace -w /workspace cv-latex-app python -m app.services.documentation_service`
- Historial y rollback visual:
  - `docs/development/PROJECT_HISTORY_ROLLBACK.md`

## Prueba manual rapida

1. Abrir `http://localhost:8000`.
2. Revisar el dashboard, la sidebar izquierda y el toggle dark/light.
3. Confirmar que la card de resumen del dashboard muestra metricas limpias de `Curriculums`, `Cartas` y `Postulaciones`, sin cortes de palabras.
4. Revisar que `Abrir CVs` y `Abrir cartas` se muestran como botones y no como links de texto.
5. Verificar que el dashboard usa previews visuales CSS y que las miniaturas PDF reales quedan como backlog futuro.
6. Entrar a `CVs` y crear o reutilizar un CV.
7. Revisar que cada fila muestra acciones principales a la derecha, fecha `dd/mm/yyyy HH:mm` integrada en metadata y `Mas acciones` con cierre por click externo o `Escape`.
8. Verificar que `Importar JSON` queda en `Herramientas avanzadas` y no domina la vista principal.
9. Abrir el detalle del CV y confirmar que `Exportacion` y `Ficha rapida` usan spacing mas compacto, labels cortos y fechas `dd/mm/yyyy HH:mm`.
10. Probar `Duplicar CV` y confirmar que primero aparece un modal de confirmacion.
11. Ejecutar `Analizar ATS` desde el detalle o desde `ATS` y confirmar que abre un modal sin sacar al usuario de la pagina actual.
12. Revisar que el modal ATS mantiene acciones superiores, badge semantico de estado y cards compactas sin cortes de palabras.
13. Desde el modal ATS, entrar a `Editar CV` y confirmar que la pantalla muestra contexto del CV y de la persona.
14. Entrar a `ATS` y repetir el analisis completo sobre un CV desde la ruta dedicada.
15. Entrar a `Cartas` y crear o reutilizar una carta.
16. Exportar TEX y PDF de la carta y verificar acciones alineadas a la derecha y fecha `dd/mm/yyyy HH:mm` en el listado.
17. Entrar a `Postulaciones`.
18. Crear una postulacion y asociarla opcionalmente a un CV y a una carta.
19. Editar la postulacion y cambiar su estado.
20. Abrir el detalle y confirmar persistencia en SQLite.
21. Confirmar que los archivos de export siguen quedando en `./data/exports`.
22. Exportar un CV a JSON e importarlo de nuevo.
23. Probar un JSON artificialmente grande y verificar el rechazo con mensaje claro.
24. Probar eliminacion segura de un CV y una carta con texto incorrecto y correcto.
25. Entrar a `Documentacion`, leer ambas documentaciones en HTML dentro de la misma web y confirmar que solo quede `Descargar PDF`.

## Troubleshooting basico

- Si el puerto `8000` esta ocupado, detener el proceso que lo usa o ajustar el host bind/puerto publicado en `docker-compose.yml`.
- Si la app no inicia, revisar `docker compose logs app`.
- Si SQLite no se crea, verificar que exista `./data` y que Docker pueda montar esa carpeta.
- Si Docker no responde, verificar que Docker Desktop o el daemon de Docker esten activos.
- Si un PDF falla al compilar, revisar `docker compose logs app` para el detalle tecnico del error LaTeX.

## Alcance de esta version

Incluye dashboard, CV Builder Core, cover letters, application tracker, ATS Basic Check, centro de documentacion con lectura HTML y descarga PDF, plantillas LaTeX propias, sanitizacion, generacion de contenido `.tex`, exportacion TEX/PDF/JSON, importacion JSON con lectura acotada, hardening basico de errores PDF, inicializacion tecnica de SQLite, archivos estaticos, Docker Compose y documentacion minima de operacion local del MVP.

## Backlog visual posterior

- Etapa 8.1.3:
  - Miniaturas reales de PDF para dashboard y listados usando `pdftoppm` o equivalente.
  - Cache local de previews y regeneracion cuando cambie el CV o la carta.
  - Selector de paleta visual local con persistencia en `localStorage`, sin DB al inicio.
- Etapa 8.2:
  - Profundizar la evolucion visual privada despues del PR de 8.1.x.
- Etapa 8.3:
  - IA real y posibles integraciones con OpenAI API, fuera del alcance actual.

No incluye IA, login, PostgreSQL ni deploy cloud.
