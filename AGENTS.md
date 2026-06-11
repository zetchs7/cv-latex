# AGENTS.md - cv-latex

## Alcance

Estas instrucciones aplican al repositorio `cv-latex`. El proyecto es una app web local para construir CVs, cartas de presentacion, seguimiento de postulaciones y chequeos ATS basicos, con FastAPI, Jinja2, SQLite, Docker Compose, LaTeX/PDF y documentacion HTML/PDF servida por la propia app.

## Principios de trabajo

- Trabajar en etapas chicas, auditables y con validacion real.
- No agregar features no pedidas ni demos falsas.
- No tocar DB, migraciones, scoring ATS, IA, thumbnails, paletas funcionales, editor estructurado ni drag/drop salvo instruccion explicita.
- Respetar la arquitectura actual: rutas FastAPI, servicios en `app/services`, repositorios en `app/repositories`, validaciones en `app/validations`, templates Jinja2 y documentacion fuente en Markdown.
- No guardar secretos, tokens, claves, backups reales, bases SQLite reales ni datos privados en Git.
- No crear archivos de configuracion local de Codex por costumbre. Crear `.codex/config.toml` solo si hay una necesidad tecnica concreta.

## Git Flow

Flujo por defecto:

```text
main <- development <- feature/*
```

- `main`: rama estable publicada.
- `development`: integracion validada.
- `feature/*`: trabajo por etapa o correccion.
- Antes de empezar: `git fetch origin`, partir desde `development` actualizado y verificar `git status --short --branch`.
- No hacer push directo a `main` o `development` salvo autorizacion explicita.
- No hacer force push, borrar ramas remotas, cambiar protecciones, crear tags ni mergear PRs sin autorizacion explicita.
- Los commits deben ser atomicos y usar prefijos como `docs`, `fix`, `feat`, `test`, `chore`, `build` o `ci`.

## Comandos base

Inspeccion inicial:

```bash
git status --short --branch
git branch --show-current
git log --oneline --decorate -7
git fetch origin
```

Validacion Python:

```bash
python -m compileall app tests
git diff --check
```

Validacion Docker/runtime:

```bash
docker compose build
docker compose up -d --force-recreate
docker compose ps
docker compose logs app --tail 80
docker compose exec app python -m pytest
```

Validacion HTTP minima:

```text
GET /health
GET /documentation/
GET /documentation/technical
GET /documentation/usage
```

## Documentacion y trazabilidad

- `docs/development/COMMAND_LOG.md`: bitacora de comandos ejecutados. Cada bloque nuevo debe usar timestamp local con zona horaria, etapa e ID secuencial `CMD-###`.
- `docs/development/DEVELOPMENT_LOG.md`: hitos por etapa, no cada comando.
- `docs/development/MVP_VALIDATION.md`: validaciones fuertes y checklist manual.
- `docs/development/CHANGELOG_GENERAL.md`: cambios por version/release, no timestamp por comando.
- `docs/development/MODULE_INDEX.md`: mapa de modulos, no bitacora temporal.
- `docs/development/VERSIONING.md`: fechas de release/tag y criterio SemVer.
- Si un timestamp historico no puede reconstruirse con certeza, escribir `timestamp exacto no reconstruido con certeza`; no inventarlo.

Formato obligatorio para nuevos bloques en `COMMAND_LOG.md`:

```text
YYYY-MM-DD HH:MM:SS ART | Etapa X.Y | CMD-001
Accion:
Motivo:
Comando:
Argumentos:
Resultado:
Error completo:
Reintento/correccion:
```

## Prompt IDs

- Los Prompt IDs son externos a Codex.
- Sirven para trazabilidad entre Franco y ChatGPT.
- No deben incluirse dentro del texto ejecutable que Codex recibe como orden.
- Si un Prompt ID aparece en una conversacion, documentarlo solo como referencia externa cuando corresponda; no mezclarlo con comandos, prompts operativos ni instrucciones que Codex deba ejecutar.

## Documentacion HTML/PDF

- Las fuentes editables viven en `docs/user/`.
- La app renderiza HTML desde esas fuentes con `app/services/documentation_service.py`.
- Los PDFs servidos viven en `app/static/docs/` y se regeneran desde las mismas fuentes Markdown.
- Al cambiar fuentes de usuario o el renderer, regenerar PDFs con:

```bash
docker compose exec app python -m app.services.documentation_service
```

- Validar cada PDF con descarga real desde la app, `pdftotext`, hash anterior/nuevo y render visual a imagen con `pdftoppm`.
- Mantener consistencia entre HTML y PDF. No dejar strings obsoletos como `feature/ui-private-dashboard`, `Rama visual actual` o referencias a abrir/integrar el PR visual como pendiente.

## Versionado

- Version actual estable: `0.9.0`.
- Tag estable actual: `v0.9.0`.
- Release anterior: `v0.8.0`.
- No crear tags sin autorizacion explicita.
- Mantener `VERSION`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `app/main.py`, README y docs alineados cuando se cambie version.

## Seguridad y datos

- La app esta pensada para uso local sin login. No exponer fuera de localhost sin revisar auth, permisos, CSRF, CORS, headers, logs y rate limits.
- La persistencia real esta en `./data`, montada como `/data`; no versionar `app.db`, exports reales, backups ni uploads privados.
- Validar inputs en servidor aunque exista validacion visual.
- Mantener confirmaciones destructivas con coincidencia exacta de texto.

## Code Review y PR

- Para cambios de release, Docker, seguridad, rutas, docs servidas, PDFs o integraciones, abrir PR hacia `development` y solicitar `@codex review`.
- El PR debe incluir alcance, ramas origen/destino, archivos principales, validaciones, riesgos, pendientes y decision de Code Review.
- Corregir hallazgos bloqueantes en la misma rama feature antes de mergear.
