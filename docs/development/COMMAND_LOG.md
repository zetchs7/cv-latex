# Command Log

## 2026-06-05 - Documentation Center

Accion:
Agregar una seccion web de documentacion con dos PDFs embebidos y fuentes editables en Markdown.

Motivo:
Cerrar el MVP local con documentacion visible desde la propia app antes del tag estable `v0.8.0`.

Comandos:
- `git status --short --branch`
- `git fetch origin`
- `git checkout development`
- `git checkout -b feature/documentation-center`
- `Get-Content` sobre `app/main.py`, `app/routes/dashboard.py`, `app/templates/layout.html`, `app/templates/dashboard.html`, `app/static/css/app.css`, `README.md` y docs operativas
- `python -m compileall app tests`
- `docker compose build`
- `docker run --rm -v "${PWD}:/workspace" -w /workspace cv-latex-app python -m app.services.documentation_service`
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose exec app python -m pytest`
- `Invoke-WebRequest -Uri http://localhost:8000/documentation/ -UseBasicParsing`
- `Invoke-WebRequest -Uri http://localhost:8000/documentation/technical -UseBasicParsing`
- `Invoke-WebRequest` sobre ambos PDFs bajo `/static/docs/`
- `docker compose exec app pdftotext ...`
- `docker compose exec app pdftoppm ...`
- `git diff --check`

Resultado:
- Se creo el centro de documentacion en la web con visor embebido, links de apertura y descarga.
- Los dos PDFs se generaron desde fuentes Markdown usando `python -m app.services.documentation_service` y `pdflatex` del contenedor.
- La legibilidad de ambos PDFs se valido con `pdftotext` y render de la primera pagina a PNG.

## 2026-06-05 - Release cleanup changelog merge

Accion:
Fusionar las notas de cleanup dentro de la entrada existente `0.8.0` del changelog.

Motivo:
Evitar duplicar encabezados de release y dejar la documentacion del cierre del MVP en una sola entrada.

Comandos:
- `Get-Content docs/development/CHANGELOG_GENERAL.md`
- `apply_patch`

Resultado:
- La entrada `0.8.0` queda unica y contiene tanto el baseline del MVP como las notas del release cleanup.

## 2026-06-05 - Release cleanup v0.8.0

Accion:
Corregir consistencia final de version y documentacion antes del tag `v0.8.0`.

Motivo:
Eliminar una referencia vieja de `APP_VERSION` en `Dockerfile` y aclarar la seccion `ATS Basic Check` del README para que no mezcle campos de Postulaciones.

Comandos:
- `git status --short --branch`
- `git fetch origin`
- `git checkout development`
- `git checkout -b feature/release-cleanup-v0.8.0`
- `Get-Content Dockerfile`
- `Get-Content README.md`
- `Get-Content docs/development/COMMAND_LOG.md`
- `Get-Content docs/development/DEVELOPMENT_LOG.md`
- `Get-Content docs/development/CHANGELOG_GENERAL.md`
- `Get-Content VERSION`

Resultado:
- `Dockerfile` quedo alineado con `APP_VERSION=0.8.0`.
- `README.md` dejo de mezclar datos de Application Tracker dentro de ATS Basic Check.
- La documentacion de desarrollo quedo lista para el cierre de release.

## 2026-06-02 - Preparacion de ramas y estado inicial

Accion:
Leer el pedido adjunto del usuario.

Motivo:
Confirmar el alcance exacto de la ejecucion antes de modificar archivos.

Comando: `Get-Content -LiteralPath 'C:\Users\zetchs\.codex\attachments\58e3e23a-2a47-474b-8a0a-8be940a4ff61\pasted-text.txt'`

Argumentos:
- `Get-Content`: lee el contenido del archivo.
- `-LiteralPath`: usa la ruta exacta sin interpretar comodines.
- Ruta del adjunto: archivo con el requerimiento completo de Etapa 0.

Resultado: pedido leido; se confirma que solo debe ejecutarse la Etapa 0.

---

Accion:
Listar archivos existentes en el repositorio.

Motivo:
Identificar el estado inicial del proyecto antes de crear estructura.

Comando: `Get-ChildItem -Force`

Argumentos:
- `-Force`: incluye archivos y carpetas ocultas como `.git`.

Resultado: solo existian `.git` y `README.md`.

---

Accion:
Listar archivos versionables detectados por ripgrep.

Motivo:
Confirmar estructura minima existente.

Comando: `rg --files`

Argumentos:
- Sin argumentos: lista archivos bajo el directorio actual.

Resultado: solo existia `README.md`.

---

Accion:
Revisar rama y estado resumido.

Motivo:
Confirmar que no hubiera cambios pendientes antes de operar ramas.

Comando: `git status --short --branch`

Argumentos:
- `--short`: salida resumida.
- `--branch`: incluye rama y tracking.

Resultado: `## main...origin/main`.

---

Accion:
Leer README inicial.

Motivo:
Verificar contenido existente antes de reemplazarlo con documentacion real de Etapa 0.

Comando: `Get-Content -LiteralPath README.md`

Argumentos:
- `-LiteralPath README.md`: lee el archivo README existente.

Resultado: contenido inicial minimo `# cv-latex`.

---

Accion:
Listar ramas locales y remotas.

Motivo:
Verificar existencia de `main` y `development`.

Comando: `git branch --all`

Argumentos:
- `--all`: muestra ramas locales y remotas.

Resultado: existian `main`, `origin/main` y `origin/HEAD`; no existia `development`.

---

Accion:
Revisar remoto configurado.

Motivo:
Confirmar si existe remoto antes de actualizar referencias o preparar PR futuro.

Comando: `git remote -v`

Argumentos:
- `-v`: muestra URL de fetch y push.

Resultado: remoto `origin` configurado en `https://github.com/zetchs7/cv-latex.git`.

---

Accion:
Revisar estado completo del repo.

Motivo:
Confirmar arbol limpio antes de crear ramas.

Comando: `git status`

Argumentos:
- Sin argumentos: muestra estado completo.

Resultado: rama `main`, actualizada con `origin/main`, sin cambios pendientes.

---

Accion:
Actualizar referencias remotas.

Motivo:
Partir desde una referencia actualizada antes de crear `development`.

Comando: `git fetch origin`

Argumentos:
- `origin`: remoto a consultar.

Resultado: fallo inicial con `error: cannot open '.git/FETCH_HEAD': Permission denied` por restricciones de escritura del sandbox sobre `.git`.

---

Accion:
Reintentar actualizacion de referencias remotas con permiso elevado.

Motivo:
El comando anterior necesitaba escribir en `.git/FETCH_HEAD`.

Comando: `git fetch origin`

Argumentos:
- `origin`: remoto a consultar.

Resultado: ejecutado correctamente.

---

Accion:
Listar ramas luego del fetch.

Motivo:
Verificar si aparecio `development` remota.

Comando: `git branch --all`

Argumentos:
- `--all`: muestra ramas locales y remotas.

Resultado: solo existian `main`, `origin/main` y `origin/HEAD`; no existia `development`.

---

Accion:
Crear rama `development` desde `main`.

Motivo:
Cumplir el flujo `main -> development -> feature/*` en un repo recien iniciado sin `development`.

Comando: `git switch -c development`

Argumentos:
- `switch`: cambia de rama.
- `-c development`: crea la rama local `development` desde la rama actual.

Resultado: `Switched to a new branch 'development'`.

---

Accion:
Crear rama de trabajo de Etapa 0.

Motivo:
Implementar la etapa sin trabajar directo en `main` ni en `development`.

Comando: `git switch -c feature/base-docker-app`

Argumentos:
- `switch`: cambia de rama.
- `-c feature/base-docker-app`: crea la rama local de trabajo desde `development`.

Resultado: `Switched to a new branch 'feature/base-docker-app'`.

---

Accion:
Confirmar rama actual.

Motivo:
Verificar que la implementacion se haga en la feature branch.

Comando: `git branch --show-current`

Argumentos:
- `--show-current`: imprime solo la rama activa.

Resultado: `feature/base-docker-app`.

---

Accion:
Convertir mecanicamente `README.md` de UTF-16LE a UTF-8.

Motivo:
`apply_patch` no podia modificar el archivo porque el README inicial estaba en UTF-16LE con BOM.

Comando: `$readmeContent = Get-Content -LiteralPath README.md -Raw`

Argumentos:
- `$readmeContent`: variable temporal con el contenido original.
- `Get-Content`: lee el archivo.
- `-LiteralPath README.md`: ruta exacta del README.
- `-Raw`: conserva el contenido como texto completo.

Resultado: contenido cargado para conversion de codificacion.

Comando: `Set-Content -LiteralPath README.md -Value $readmeContent -Encoding utf8`

Argumentos:
- `Set-Content`: escribe el archivo.
- `-LiteralPath README.md`: ruta exacta del README.
- `-Value $readmeContent`: contenido original sin cambios funcionales.
- `-Encoding utf8`: escribe el archivo en UTF-8.

Resultado: README convertido a UTF-8 para permitir edicion normal con `apply_patch`.

---

Accion:
Crear estructura base de Etapa 0.

Motivo:
Implementar la app minima FastAPI, Docker, SQLite preparado y documentacion inicial.

Comando: `apply_patch`

Argumentos:
- Se agregaron archivos bajo `app/`, `docs/`, `data/`, `tests/` y archivos raiz del proyecto.
- Se reemplazo el README inicial por documentacion real de Etapa 0.

Resultado: estructura inicial creada.

## 2026-06-02 - Validaciones de Etapa 0

Accion:
Construir imagen Docker.

Motivo:
Validar que el Dockerfile y requirements permiten construir la app.

Comando: `docker compose build`

Argumentos:
- `compose`: usa Docker Compose v2.
- `build`: construye la imagen del servicio `app` usando `Dockerfile`.

Resultado: fallo inicial dentro del sandbox con `CreateFile C:\Users\zetchs\.docker\buildx\instances: Access is denied`.

---

Accion:
Reintentar build Docker con permiso elevado.

Motivo:
Docker necesita acceder a la configuracion local de `C:\Users\zetchs\.docker`.

Comando: `docker compose build`

Argumentos:
- `compose`: usa Docker Compose v2.
- `build`: construye la imagen local.

Resultado: imagen `cv-latex-app:latest` construida correctamente.

---

Accion:
Levantar la app en segundo plano.

Motivo:
Validar arranque del servicio `app`.

Comando: `docker compose up -d`

Argumentos:
- `up`: crea e inicia servicios del Compose.
- `-d`: ejecuta en segundo plano.

Resultado: red `cv-latex_default` y contenedor `cv_latex_app` creados; contenedor iniciado.

---

Accion:
Revisar contenedores activos.

Motivo:
Confirmar que el servicio queda arriba y saludable.

Comando: `docker compose ps`

Argumentos:
- `ps`: lista servicios del stack Compose.

Resultado: `cv_latex_app` quedo `Up` y `healthy`, con puerto `8000:8000`.

---

Accion:
Revisar logs del servicio app.

Motivo:
Confirmar que Uvicorn y FastAPI iniciaron sin errores.

Comando: `docker compose logs app`

Argumentos:
- `logs`: muestra logs de servicios.
- `app`: limita la salida al servicio principal.

Resultado: logs muestran `Application startup complete` y `Uvicorn running on http://0.0.0.0:8000`.

---

Accion:
Probar acceso HTTP al dashboard.

Motivo:
Validar que `http://localhost:8000` responde.

Comando: `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`

Argumentos:
- `-Uri http://localhost:8000`: URL local del dashboard.
- `-UseBasicParsing`: parseo compatible desde PowerShell.

Resultado: `StatusCode: 200`, `Content-Type: text/html; charset=utf-8`, contenido incluye `Dashboard - CV LaTeX Builder`.

---

Accion:
Probar endpoint de salud.

Motivo:
Validar estado tecnico de la app y SQLite.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`

Argumentos:
- `-Uri http://localhost:8000/health`: endpoint tecnico.
- `-UseBasicParsing`: parseo compatible desde PowerShell.

Resultado: `StatusCode: 200`, JSON con `status: ok`, `version: 0.1.0`, `database.path: /data/app.db`, `exists: true`.

---

Accion:
Verificar existencia de carpeta persistente local.

Motivo:
Confirmar que `./data` existe en el host.

Comando: `Test-Path -LiteralPath data`

Argumentos:
- `-LiteralPath data`: ruta exacta de la carpeta persistente local.

Resultado: `True`.

---

Accion:
Listar contenido de `./data`.

Motivo:
Confirmar que SQLite fue creado en el bind mount local.

Comando: `Get-ChildItem -Force -LiteralPath data`

Argumentos:
- `-Force`: incluye `.gitkeep`.
- `-LiteralPath data`: ruta exacta de la carpeta persistente.

Resultado: existen `.gitkeep` y `app.db`.

---

Accion:
Verificar montaje `/data` desde el contenedor.

Motivo:
Confirmar que el contenedor ve la persistencia montada.

Comando: `docker compose exec app ls -la /data`

Argumentos:
- `exec`: ejecuta un comando dentro del servicio.
- `app`: servicio objetivo.
- `ls -la /data`: lista el directorio persistente dentro del contenedor.

Resultado: `/data` contiene `.gitkeep` y `app.db`; `app.db` pertenece a `appuser`.

---

Accion:
Detener el stack.

Motivo:
Validar ciclo de apagado solicitado.

Comando: `docker compose down`

Argumentos:
- `down`: detiene y elimina contenedor y red del stack.

Resultado: contenedor `cv_latex_app` detenido y removido; red `cv-latex_default` removida.

---

Accion:
Levantar el stack nuevamente.

Motivo:
Validar que la app arranca correctamente despues de detenerse.

Comando: `docker compose up -d`

Argumentos:
- `up`: crea e inicia servicios.
- `-d`: ejecuta en segundo plano.

Resultado: red y contenedor recreados; `cv_latex_app` iniciado.

---

Accion:
Revisar contenedor despues del segundo arranque.

Motivo:
Confirmar estabilidad despues del ciclo `down` y `up`.

Comando: `docker compose ps`

Argumentos:
- `ps`: lista servicios del stack.

Resultado: `cv_latex_app` quedo `Up` y `healthy`, con puerto `8000:8000`.

---

Accion:
Probar CSS estatico.

Motivo:
Confirmar que static files funcionan.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/static/css/app.css -UseBasicParsing`

Argumentos:
- `-Uri`: ruta CSS estatica.
- `-UseBasicParsing`: parseo compatible desde PowerShell.

Resultado: `StatusCode: 200`, `Content-Type: text/css; charset=utf-8`.

---

Accion:
Probar JavaScript estatico.

Motivo:
Confirmar que static files funcionan.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/static/js/app.js -UseBasicParsing`

Argumentos:
- `-Uri`: ruta JavaScript estatica.
- `-UseBasicParsing`: parseo compatible desde PowerShell.

Resultado: `StatusCode: 200`, `Content-Type: text/javascript; charset=utf-8`.

---

Accion:
Intentar verificacion visual con navegador interno.

Motivo:
Revisar render visual del dashboard local.

Comando: `node_repl browser verification`

Argumentos:
- URL objetivo: `http://localhost:8000`.
- Checks buscados: nombre de app, estado `MVP base funcionando`, placeholders y assets.

Resultado: no se pudo ejecutar por limitacion del runtime del navegador interno: `windows sandbox failed: spawn setup refresh`. Se mantuvo la verificacion HTTP directa como evidencia.

---

Accion:
Revisar ramas finales.

Motivo:
Confirmar que se trabajo en la feature branch y que existe `development`.

Comando: `git branch --all`

Argumentos:
- `--all`: muestra ramas locales y remotas.

Resultado: existen `development`, `feature/base-docker-app`, `main`, `origin/main` y `origin/HEAD`.

---

Accion:
Revisar estado final antes del commit.

Motivo:
Confirmar cambios preparados para commit de Etapa 0.

Comando: `git status --short --branch`

Argumentos:
- `--short`: salida resumida.
- `--branch`: incluye rama activa.

Resultado: rama `feature/base-docker-app` con cambios de Etapa 0 pendientes de commit.

## 2026-06-02 - Preparacion de Etapa 1

Accion:
Revisar estado actual del repositorio.

Motivo:
Confirmar rama, limpieza del arbol y base disponible antes de crear la rama de Etapa 1.

Comando: `git status --short --branch`

Argumentos:
- `--short`: salida resumida.
- `--branch`: incluye rama activa.

Resultado: rama `feature/base-docker-app`, arbol limpio.

---

Accion:
Listar ramas locales y remotas.

Motivo:
Verificar que existe `development` y confirmar que no hubo merge de Etapa 0.

Comando: `git branch --all`

Argumentos:
- `--all`: muestra ramas locales y remotas.

Resultado: existen `development`, `feature/base-docker-app`, `main`, `origin/main` y `origin/HEAD`.

---

Accion:
Revisar historial reciente.

Motivo:
Confirmar que `development` seguia en el commit inicial y que Etapa 0 estaba solo en `feature/base-docker-app`.

Comando: `git log --oneline --decorate --graph --all -n 8`

Argumentos:
- `--oneline`: formato compacto.
- `--decorate`: muestra ramas.
- `--graph`: muestra relacion de commits.
- `--all`: incluye todas las ramas.
- `-n 8`: limita a ocho commits.

Resultado: `feature/base-docker-app` contiene `6a1408f`; `development` sigue en el commit inicial.

---

Accion:
Listar archivos existentes.

Motivo:
Identificar la estructura aprobada de Etapa 0 antes de extenderla.

Comando: `rg --files`

Argumentos:
- Sin argumentos: lista archivos bajo el directorio actual.

Resultado: estructura base FastAPI/Docker/docs disponible.

---

Accion:
Crear rama de Etapa 1.

Motivo:
Implementar CV Builder Core sin trabajar directo en `main`, `development` ni `feature/base-docker-app`. Se creo desde la rama aprobada de Etapa 0 porque no habia merge autorizado hacia `development`.

Comando: `git switch -c feature/cv-builder-core`

Argumentos:
- `switch`: cambia de rama.
- `-c feature/cv-builder-core`: crea la rama local de trabajo de Etapa 1.

Resultado: `Switched to a new branch 'feature/cv-builder-core'`.

## 2026-06-02 - Implementacion de CV Builder Core

Accion:
Crear modelo, schema, repositorio, rutas, templates y validaciones de CVs.

Motivo:
Implementar el alcance de Etapa 1: modelo base, CRUD, formularios, duplicado, eliminacion con confirmacion y persistencia SQLite.

Comando: `apply_patch`

Argumentos:
- Modifico `app/database.py` para crear tabla `cvs`.
- Agrego `app/models.py`.
- Agrego `app/schemas.py`.
- Agrego `app/repositories/cv_repository.py`.
- Agrego `app/validations/cv_validations.py`.
- Agrego `app/routes/cvs.py`.
- Agrego templates bajo `app/templates/cvs/`.
- Actualiza dashboard, layout y CSS.

Resultado: modulo CV Builder Core creado.

---

Accion:
Actualizar version del proyecto.

Motivo:
Etapa 1 agrega funcionalidad nueva compatible, por lo que corresponde pasar de `0.1.0` a `0.2.0`.

Comando: `apply_patch`

Argumentos:
- Actualiza `VERSION`.
- Actualiza `Dockerfile`.
- Actualiza `docker-compose.yml`.
- Actualiza `.env.example`.
- Actualiza `README.md`.
- Actualiza version visible en layout.

Resultado: version `0.2.0` aplicada.

---

Accion:
Compilar archivos Python.

Motivo:
Detectar errores de sintaxis antes de validar con Docker.

Comando: `python -m compileall app`

Argumentos:
- `-m compileall`: ejecuta el modulo de compilacion.
- `app`: carpeta objetivo.

Resultado: compilacion correcta.

---

Accion:
Buscar caracteres no ASCII accidentales.

Motivo:
Mantener archivos portables y consistentes con la politica de edicion.

Comando: `rg -n -P "[^\\x00-\\x7F]"`

Argumentos:
- `-n`: muestra linea.
- `-P`: usa expresiones PCRE.
- Patron: busca caracteres fuera de ASCII.

Resultado: sin coincidencias.

---

Accion:
Revisar whitespace del diff.

Motivo:
Detectar espacios conflictivos antes de commit.

Comando: `git diff --check`

Argumentos:
- `--check`: valida whitespace y marcadores conflictivos.

Resultado: sin errores; Git mostro advertencias normales de CRLF en Windows.

## 2026-06-02 - Validaciones Docker y CRUD Etapa 1

Accion:
Construir imagen Docker con Etapa 1.

Motivo:
Validar que el contenedor puede construirse con el modulo CVs.

Comando: `docker compose build`

Argumentos:
- `compose`: usa Docker Compose v2.
- `build`: construye la imagen local.

Resultado: build correcto.

---

Accion:
Levantar servicio actualizado.

Motivo:
Validar arranque real de la app.

Comando: `docker compose up -d`

Argumentos:
- `up`: crea o recrea servicios.
- `-d`: ejecuta en segundo plano.

Resultado: el contenedor se recreo, pero entro en reinicio.

---

Accion:
Revisar estado y logs del fallo.

Motivo:
Identificar causa del reinicio del contenedor.

Comando: `docker compose ps`

Argumentos:
- `ps`: muestra estado del servicio.

Resultado: `cv_latex_app` aparecio como `Restarting (1)`.

Comando: `docker compose logs app`

Argumentos:
- `logs`: muestra logs.
- `app`: limita al servicio principal.

Resultado: error `FastAPIError: Invalid args for response field` por anotacion `HTMLResponse | RedirectResponse` en rutas POST.

---

Accion:
Corregir anotaciones de rutas FastAPI.

Motivo:
FastAPI intento construir un response model Pydantic con una union de clases Response.

Comando: `apply_patch`

Argumentos:
- Se quitaron las anotaciones `HTMLResponse | RedirectResponse` en rutas POST afectadas.

Resultado: correccion aplicada.

---

Accion:
Recompilar Python despues de la correccion.

Motivo:
Confirmar que el cambio no introdujo errores de sintaxis.

Comando: `python -m compileall app`

Argumentos:
- `app`: carpeta objetivo.

Resultado: compilacion correcta.

---

Accion:
Reconstruir imagen corregida.

Motivo:
Actualizar el contenedor con la correccion.

Comando: `docker compose build`

Argumentos:
- `build`: reconstruye imagen local.

Resultado: build correcto.

---

Accion:
Levantar servicio corregido.

Motivo:
Validar que la app arranca correctamente.

Comando: `docker compose up -d`

Argumentos:
- `up`: crea o recrea servicios.
- `-d`: ejecuta en segundo plano.

Resultado: contenedor recreado e iniciado.

---

Accion:
Revisar contenedor corregido.

Motivo:
Confirmar healthcheck.

Comando: `docker compose ps`

Argumentos:
- `ps`: muestra estado de servicios.

Resultado: `cv_latex_app` quedo `Up` y `healthy`, con puerto `8000:8000`.

---

Accion:
Validar endpoint de salud.

Motivo:
Confirmar version, base y arranque.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`

Argumentos:
- `-Uri`: endpoint `/health`.
- `-UseBasicParsing`: parseo compatible desde PowerShell.

Resultado: `StatusCode: 200`, `version: 0.2.0`, SQLite existente.

---

Accion:
Validar dashboard.

Motivo:
Confirmar navegacion hacia CVs.

Comando: `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`

Argumentos:
- `-Uri`: dashboard.
- `-UseBasicParsing`: parseo compatible.

Resultado: `StatusCode: 200`, links a `/cvs/` presentes.

---

Accion:
Validar listado de CVs.

Motivo:
Confirmar ruta principal del modulo.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -UseBasicParsing`

Argumentos:
- `-Uri`: listado de CVs.
- `-UseBasicParsing`: parseo compatible.

Resultado: `StatusCode: 200`.

---

Accion:
Validar formulario de creacion.

Motivo:
Confirmar que el formulario HTML carga.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/new -UseBasicParsing`

Argumentos:
- `-Uri`: formulario nuevo CV.
- `-UseBasicParsing`: parseo compatible.

Resultado: `StatusCode: 200`.

---

Accion:
Crear CV de prueba.

Motivo:
Validar POST de creacion y persistencia SQLite.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -Method Post -UseBasicParsing -Body @{ ... }`

Argumentos:
- `-Uri`: endpoint de creacion.
- `-Method Post`: envia formulario.
- `-Body`: campos `title`, `full_name`, `email`, `phone`, `professional_summary`, `experience_summary`, `education_summary`, `skills`.

Resultado: redireccion a `http://localhost:8000/cvs/1?message=CV+creado+correctamente.`

---

Accion:
Editar CV de prueba.

Motivo:
Validar POST de actualizacion.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/1/edit -Method Post -UseBasicParsing -Body @{ ... }`

Argumentos:
- `-Uri`: endpoint de edicion del CV `1`.
- `-Method Post`: envia formulario.
- `-Body`: campos actualizados.

Resultado: redireccion a `http://localhost:8000/cvs/1?message=CV+actualizado+correctamente.`

---

Accion:
Duplicar CV de prueba.

Motivo:
Validar accion de duplicado.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/1/duplicate -Method Post -UseBasicParsing`

Argumentos:
- `-Uri`: endpoint de duplicado del CV `1`.
- `-Method Post`: ejecuta la accion.

Resultado: redireccion a `http://localhost:8000/cvs/2?message=CV+duplicado+correctamente.`

---

Accion:
Abrir confirmacion de eliminacion.

Motivo:
Validar que la eliminacion requiere confirmacion.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/2/delete -UseBasicParsing`

Argumentos:
- `-Uri`: pantalla de confirmacion para CV `2`.
- `-UseBasicParsing`: parseo compatible.

Resultado: `StatusCode: 200`.

---

Accion:
Eliminar logicamente CV duplicado.

Motivo:
Validar eliminacion con confirmacion.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/2/delete -Method Post -UseBasicParsing -Body @{ confirm_delete = 'yes' }`

Argumentos:
- `-Uri`: endpoint de eliminacion.
- `-Method Post`: ejecuta accion.
- `confirm_delete = 'yes'`: confirma eliminacion.

Resultado: redireccion a `http://localhost:8000/cvs/?message=CV+eliminado+correctamente.`

---

Accion:
Eliminar logicamente CV original de prueba.

Motivo:
Dejar el listado visible sin datos de prueba activos.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/1/delete -Method Post -UseBasicParsing -Body @{ confirm_delete = 'yes' }`

Argumentos:
- `-Uri`: endpoint de eliminacion del CV `1`.
- `-Method Post`: ejecuta accion.
- `confirm_delete = 'yes'`: confirma eliminacion.

Resultado: redireccion a `http://localhost:8000/cvs/?message=CV+eliminado+correctamente.`

---

Accion:
Verificar conteo SQLite.

Motivo:
Confirmar que la eliminacion es logica y que no quedan CVs activos.

Comando: `docker compose exec app python -c "import sqlite3; con=sqlite3.connect('/data/app.db'); print(con.execute('select count(*) from cvs where deleted_at is null').fetchone()[0]); print(con.execute('select count(*) from cvs where deleted_at is not null').fetchone()[0])"`

Argumentos:
- `exec app`: ejecuta dentro del contenedor.
- `python -c`: consulta SQLite.
- Primera consulta: cuenta CVs activos.
- Segunda consulta: cuenta CVs eliminados logicamente.

Resultado: `0` activos y `2` eliminados logicamente.

---

Accion:
Validar formulario invalido.

Motivo:
Confirmar errores de validacion del lado servidor.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -Method Post -UseBasicParsing -Body @{ title = ''; full_name = ''; email = 'email-invalido'; ... }`

Argumentos:
- `-Uri`: endpoint de creacion.
- `-Method Post`: envia formulario invalido.
- `-Body`: datos incompletos y email invalido.

Resultado: respuesta HTTP `422`.

## 2026-06-02 - Preparacion de Etapa 2

Accion:
Revisar estado actual del repositorio.

Motivo:
Confirmar que Etapa 1 estaba aprobada y el arbol estaba limpio antes de crear la nueva rama.

Comando: `git status --short --branch`

Argumentos:
- `--short`: salida resumida.
- `--branch`: incluye rama activa.

Resultado: rama `feature/cv-builder-core`, arbol limpio.

---

Accion:
Listar ramas locales y remotas.

Motivo:
Verificar que no hubo merge hacia `development` y que correspondia partir desde la rama aprobada de Etapa 1.

Comando: `git branch --all`

Argumentos:
- `--all`: muestra ramas locales y remotas.

Resultado: existen `development`, `feature/base-docker-app`, `feature/cv-builder-core`, `main`, `origin/main` y `origin/HEAD`.

---

Accion:
Revisar historial reciente.

Motivo:
Confirmar que `feature/cv-builder-core` contiene Etapa 1 y `development` sigue sin merge.

Comando: `git log --oneline --decorate --graph --all -n 10`

Argumentos:
- `--oneline`: formato compacto.
- `--decorate`: muestra ramas.
- `--graph`: muestra relaciones.
- `--all`: incluye todas las ramas.
- `-n 10`: limita a diez commits.

Resultado: `feature/cv-builder-core` contiene `eb6e82b`; `development` sigue en el commit inicial.

---

Accion:
Crear rama de Etapa 2.

Motivo:
Implementar plantillas LaTeX sin trabajar directo en ramas previas ni hacer merge.

Comando: `git switch -c feature/latex-templates`

Argumentos:
- `switch`: cambia de rama.
- `-c feature/latex-templates`: crea la rama local de trabajo de Etapa 2.

Resultado: `Switched to a new branch 'feature/latex-templates'`.

## 2026-06-02 - Implementacion de plantillas LaTeX

Accion:
Crear servicio, sanitizador, plantillas y vista TEX.

Motivo:
Implementar el alcance de Etapa 2: plantillas propias, sanitizacion y generacion de contenido `.tex` desde CV guardado.

Comando: `apply_patch`

Argumentos:
- Agrega `app/services/latex_service.py`.
- Agrega `app/validations/latex_sanitizer.py`.
- Agrega `app/latex_templates/cv/classic.tex`.
- Agrega `app/latex_templates/cv/modern.tex`.
- Agrega `app/latex_templates/cv/compact.tex`.
- Agrega `app/latex_templates/cv/tech.tex`.
- Agrega `app/templates/cvs/tex_preview.html`.
- Actualiza rutas y detalle de CV.

Resultado: base de generacion TEX creada.

---

Accion:
Agregar tests de sanitizacion y servicio.

Motivo:
Validar escapes LaTeX, caracteres comunes en espanol y generacion basica.

Comando: `apply_patch`

Argumentos:
- Agrega `tests/test_latex_sanitizer.py`.
- Agrega `tests/test_latex_service.py`.

Resultado: tests agregados.

---

Accion:
Compilar Python.

Motivo:
Detectar errores de sintaxis.

Comando: `python -m compileall app tests`

Argumentos:
- `app tests`: carpetas objetivo.

Resultado: compilacion correcta.

---

Accion:
Ejecutar tests unitarios.

Motivo:
Validar sanitizacion y pruebas disponibles localmente.

Comando: `python -m unittest discover -s tests`

Argumentos:
- `discover`: descubre tests.
- `-s tests`: usa carpeta `tests`.

Resultado: fallo inicial porque el Python local no tenia `jinja2`, requerido por `latex_service.py`.

---

Accion:
Ajustar test del servicio para dependencia local faltante.

Motivo:
Permitir ejecutar tests de sanitizacion localmente sin instalar dependencias fuera de Docker.

Comando: `apply_patch`

Argumentos:
- `tests/test_latex_service.py` salta tests del servicio solo si falta `jinja2`.

Resultado: suite local pasa con `4` tests ejecutados y `2` saltados.

---

Accion:
Revisar whitespace del diff.

Motivo:
Detectar espacios conflictivos antes de validar Docker.

Comando: `git diff --check`

Argumentos:
- `--check`: valida whitespace y conflictos.

Resultado: sin errores; solo advertencias normales de CRLF en Windows.

---

Accion:
Buscar caracteres no ASCII accidentales.

Motivo:
Mantener codigo y docs en ASCII salvo contenido LaTeX/test donde se validan caracteres en espanol.

Comando: `rg -n -P "[^\\x00-\\x7F]"`

Argumentos:
- `-n`: muestra linea.
- `-P`: usa PCRE.
- Patron: busca caracteres no ASCII.

Resultado: sin coincidencias no esperadas.

## 2026-06-02 - Validaciones Docker y TEX Etapa 2

Accion:
Construir imagen Docker.

Motivo:
Validar que la app con plantillas LaTeX construye correctamente.

Comando: `docker compose build`

Argumentos:
- `compose`: usa Docker Compose v2.
- `build`: construye imagen local.

Resultado: build correcto.

---

Accion:
Levantar servicio actualizado.

Motivo:
Validar arranque real de Etapa 2.

Comando: `docker compose up -d`

Argumentos:
- `up`: crea o recrea servicios.
- `-d`: ejecuta en segundo plano.

Resultado: contenedor iniciado.

---

Accion:
Validar contenedor y healthcheck.

Motivo:
Confirmar estado del servicio.

Comando: `docker compose ps`

Argumentos:
- `ps`: lista servicios.

Resultado: `cv_latex_app` quedo `Up` y `healthy`.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`

Argumentos:
- `-Uri`: endpoint de salud.
- `-UseBasicParsing`: parseo compatible.

Resultado: `StatusCode: 200`, `version: 0.3.0`.

---

Accion:
Crear CV de prueba para TEX.

Motivo:
Validar acentos, caracteres especiales LaTeX y secciones vacias.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -Method Post -UseBasicParsing -Body @{ ... }`

Argumentos:
- `-Method Post`: crea CV.
- `-Body`: incluye `María`, `Español`, `&`, `%`, `_`, `#`, `$` y una seccion `education_summary` vacia.

Resultado: redireccion a `http://localhost:8000/cvs/5?message=CV+creado+correctamente.`

---

Accion:
Validar plantillas TEX.

Motivo:
Confirmar que las cuatro plantillas generan vista desde el CV guardado.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/5/tex?template_key=classic' -UseBasicParsing`

Argumentos:
- `template_key=classic`: plantilla classic.

Resultado: fallo inicial `500 Internal Server Error`.

Comando: `docker compose logs app`

Argumentos:
- `logs app`: lee error del servicio principal.

Resultado: error `TypeError: 'builtin_function_or_method' object is not iterable` por usar `section.items` en Jinja.

---

Accion:
Corregir contexto de plantillas.

Motivo:
Evitar colision con el metodo `dict.items` de Jinja.

Comando: `apply_patch`

Argumentos:
- Cambia clave de contexto `items` a `item_list`.
- Actualiza las cuatro plantillas.

Resultado: correccion aplicada.

---

Accion:
Reconstruir y levantar servicio corregido.

Motivo:
Validar plantillas luego de la correccion.

Comando: `docker compose build`

Argumentos:
- `build`: reconstruye imagen local.

Resultado: build correcto.

Comando: `docker compose up -d`

Argumentos:
- `up -d`: recrea e inicia el servicio.

Resultado: contenedor iniciado y healthy.

---

Accion:
Validar previsualizacion de las cuatro plantillas.

Motivo:
Confirmar generacion TEX para `classic`, `modern`, `compact` y `tech`.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/5/tex?template_key=classic' -UseBasicParsing`

Argumentos:
- `template_key=classic`: plantilla classic.

Resultado: `StatusCode: 200`.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/5/tex?template_key=modern' -UseBasicParsing`

Argumentos:
- `template_key=modern`: plantilla modern.

Resultado: `StatusCode: 200`.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/5/tex?template_key=compact' -UseBasicParsing`

Argumentos:
- `template_key=compact`: plantilla compact.

Resultado: `StatusCode: 200`.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/5/tex?template_key=tech' -UseBasicParsing`

Argumentos:
- `template_key=tech`: plantilla tech.

Resultado: `StatusCode: 200`.

---

Accion:
Validar plantilla inexistente.

Motivo:
Confirmar manejo de error de template no permitido.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/5/tex?template_key=invalid' -UseBasicParsing`

Argumentos:
- `template_key=invalid`: valor no registrado.

Resultado: `404`.

---

Accion:
Verificar contenido TEX generado dentro del contenedor.

Motivo:
Confirmar escapes y preservacion de caracteres comunes en espanol.

Comando: `docker compose exec app python -c "from app.repositories.cv_repository import get_cv; from app.services.latex_service import generate_cv_tex_document; cv=get_cv(5); content=generate_cv_tex_document(cv, 'classic').content; print('María' in content); print('Español' in content); print('\\\\&' in content); print('50\\\\%' in content); print('Python\\\\_FastAPI' in content); print('Educacion' in content); print(content[:500])"`

Argumentos:
- `get_cv(5)`: obtiene CV de prueba.
- `generate_cv_tex_document`: genera TEX classic.
- Checks booleanos: valida acentos, escapes y ausencia de seccion vacia.

Resultado: `True` para acentos y escapes; `False` para `Educacion`, confirmando omision de seccion vacia.

---

Accion:
Eliminar logicamente CV de prueba.

Motivo:
No dejar activo el registro usado en validacion.

Comando: `Invoke-WebRequest -Uri http://localhost:8000/cvs/5/delete -Method Post -UseBasicParsing -Body @{ confirm_delete = 'yes' }`

Argumentos:
- `-Method Post`: ejecuta eliminacion.
- `confirm_delete = 'yes'`: confirma accion.

Resultado: redireccion a `http://localhost:8000/cvs/?message=CV+eliminado+correctamente.`

---

Accion:
Verificar CVs activos restantes.

Motivo:
Confirmar estado de la base local luego de pruebas.

Comando: `docker compose exec app python -c "import sqlite3; con=sqlite3.connect('/data/app.db'); print(con.execute('select count(*) from cvs where deleted_at is null').fetchone()[0]); print(con.execute('select count(*) from cvs where deleted_at is not null').fetchone()[0])"`

Argumentos:
- Primera consulta: CVs activos.
- Segunda consulta: CVs eliminados logicamente.

Resultado: `1` activo y `4` eliminados logicamente.

---

Accion:
Identificar CV activo restante.

Motivo:
Evitar borrar datos que no pertenecen a pruebas de esta etapa.

Comando: `docker compose exec app python -c "import sqlite3; con=sqlite3.connect('/data/app.db'); con.row_factory=sqlite3.Row; rows=con.execute('select id,title,full_name,created_at from cvs where deleted_at is null').fetchall(); [print(dict(row)) for row in rows]"`

Argumentos:
- Consulta CVs activos con datos basicos.

Resultado: CV activo `SysAdmin Linux` de `Franco Pablo Damian`; se conservo porque no corresponde a datos de prueba de Etapa 2.

---

Accion:
Agregar `pytest` a dependencias del contenedor.

Motivo:
Corregir la validacion pendiente de Etapa 2 para ejecutar tests dentro de Docker.

Comando: edicion manual de `requirements.txt`

Argumentos:
- `pytest==8.3.4`: dependencia de test para `python -m pytest`.

Resultado: dependencia agregada.

---

Accion:
Reconstruir imagen Docker con la nueva dependencia.

Motivo:
Instalar `pytest` dentro del contenedor `app`.

Comando: `docker compose build`

Argumentos:
- Servicio `app`: rebuild completo desde `Dockerfile`.

Resultado: build exitoso; `pytest` quedo instalado en la imagen, pero la suite aun no estaba disponible dentro del contenedor.

---

Accion:
Levantar o refrescar el servicio `app`.

Motivo:
Ejecutar la nueva imagen antes de correr tests.

Comando: `docker compose up -d`

Argumentos:
- `-d`: arranque en segundo plano.

Resultado: contenedor `cv_latex_app` recreado e iniciado correctamente con la imagen reconstruida.

---

Accion:
Ejecutar suite de tests dentro del contenedor.

Motivo:
Confirmar que la validacion pendiente de Etapa 2 queda resuelta.

Comando: `docker compose exec app python -m pytest`

Argumentos:
- `python -m pytest`: usa la dependencia instalada en la imagen.

Resultado: primer intento con `pytest` instalado pero `collected 0 items`, porque la imagen no contenia `tests/`.

---

Accion:
Actualizar imagen Docker para incluir la carpeta `tests/`.

Motivo:
Permitir que `pytest` descubra y ejecute los casos dentro del contenedor.

Comando: edicion manual de `Dockerfile`

Argumentos:
- `COPY tests ./tests`: copia la suite al filesystem de la imagen.

Resultado: Dockerfile ajustado.

---

Accion:
Reconstruir imagen Docker luego del ajuste en `Dockerfile`.

Motivo:
Aplicar la inclusion de `tests/` en la imagen final.

Comando: `docker compose build`

Argumentos:
- Servicio `app`: rebuild sobre la imagen previa con `pytest` ya instalado.

Resultado: build exitoso; la imagen `cv-latex-app:latest` quedo actualizada.

---

Accion:
Recrear el contenedor con la nueva imagen.

Motivo:
Ejecutar la suite sobre el contenedor corregido.

Comando: `docker compose up -d`

Argumentos:
- `Recreate`: reemplazo del contenedor `cv_latex_app`.

Resultado: contenedor recreado e iniciado correctamente.

---

Accion:
Reejecutar suite de tests dentro del contenedor corregido.

Motivo:
Confirmar que la validacion pendiente de Etapa 2 queda resuelta.

Comando: `docker compose exec app python -m pytest`

Argumentos:
- `python -m pytest`: ejecucion de la suite incluida en la imagen.

Resultado: `6 passed in 0.07s`.

---

Accion:
Crear rama de Etapa 3 desde `development`.

Motivo:
Respetar Git Flow y no trabajar directo sobre `main` ni `development`.

Comando: `git switch -c feature/export-engine`

Argumentos:
- Rama base: `development` sincronizada con `origin/development`.

Resultado: rama `feature/export-engine` creada.

---

Accion:
Agregar servicios de exportacion e importacion.

Motivo:
Implementar descarga TEX, export JSON, import JSON y base segura para PDF.

Comando: edicion manual de `app/services/export_service.py`, `app/services/pdf_service.py` y rutas CV.

Argumentos:
- `/data/exports`: directorio persistente de artefactos.
- `sanitize_filename`: evita rutas arbitrarias y extensiones no permitidas.
- Directorio temporal PDF bajo `/data/exports/_tmp`.

Resultado: servicios y rutas implementados.

---

Accion:
Agregar TeX Live al contenedor.

Motivo:
Compilar plantillas LaTeX actuales con `pdflatex` dentro de Docker.

Comando: edicion manual de `Dockerfile`

Argumentos:
- `texlive-latex-base`
- `texlive-latex-recommended`
- `texlive-latex-extra`
- `texlive-fonts-recommended`
- `texlive-lang-spanish`

Resultado: Dockerfile actualizado. Impacto observado durante build: aproximadamente 509 MB adicionales.

---

Accion:
Validar sintaxis Python.

Motivo:
Detectar errores basicos antes de reconstruir Docker.

Comando: `python -m compileall app tests`

Argumentos:
- `app tests`: modulos de aplicacion y suite.

Resultado: compilacion OK.

---

Accion:
Intentar tests locales.

Motivo:
Validacion rapida previa a Docker.

Comando: `python -m pytest`

Argumentos:
- Suite completa.

Resultado: no ejecutado localmente porque el Python de Windows no tiene `pytest`.

---

Accion:
Reconstruir imagen Docker para Etapa 3.

Motivo:
Instalar TeX Live y copiar codigo/tests actualizados.

Comando: `docker compose build`

Argumentos:
- Servicio `app`.

Resultado: build exitoso.

---

Accion:
Levantar servicio de Etapa 3.

Motivo:
Ejecutar validaciones HTTP y tests en contenedor.

Comando: `docker compose up -d`

Argumentos:
- `-d`: arranque en segundo plano.

Resultado: contenedor `cv_latex_app` iniciado.

---

Accion:
Verificar estado Docker.

Motivo:
Confirmar contenedor disponible y healthcheck.

Comando: `docker compose ps`

Argumentos:
- Servicio `app`.

Resultado: `cv_latex_app` quedo `Up` y `healthy`.

---

Accion:
Revisar logs de app.

Motivo:
Confirmar arranque sin errores.

Comando: `docker compose logs app`

Argumentos:
- Servicio `app`.

Resultado: Uvicorn inicio correctamente y `/health` respondio 200.

---

Accion:
Ejecutar tests dentro del contenedor.

Motivo:
Validar servicios de exportacion, sanitizacion, LaTeX y PDF.

Comando: `docker compose exec app python -m pytest`

Argumentos:
- Suite completa dentro de la imagen.

Resultado: `13 passed in 0.11s`.

---

Accion:
Crear CV de prueba de Etapa 3.

Motivo:
Disponer de un CV guardado para validar exportaciones reales.

Comando: `docker compose exec app python -c "... cv_repository.create_cv(...); print(cv_id)"`

Argumentos:
- Titulo: `Etapa 3 Export Test`.
- Plantillas validadas: `modern` y `tech`.

Resultado: CV de prueba creado con id `6`.

---

Accion:
Descargar TEX por HTTP.

Motivo:
Confirmar que la descarga TEX funciona y no queda vacia.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/6/export/tex?template_key=tech' -UseBasicParsing -OutFile data\\final-download-cv6.tex`

Argumentos:
- `template_key=tech`.

Resultado: descarga OK; archivo local de verificacion con `1360` bytes.

---

Accion:
Exportar JSON por HTTP.

Motivo:
Confirmar descarga JSON de CV.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/6/export/json' -UseBasicParsing -OutFile data\\final-export-cv6.json`

Argumentos:
- CV id `6`.

Resultado: descarga OK; archivo local de verificacion con `491` bytes.

---

Accion:
Importar JSON por HTTP.

Motivo:
Confirmar que la importacion crea un CV nuevo.

Comando: `curl.exe -s -D data\\final-import-response-cv6-headers.txt -o data\\final-import-response-cv6-body.txt -F "json_file=@data/final-export-cv6.json;type=application/json" http://localhost:8000/cvs/import/json`

Argumentos:
- Multipart field: `json_file`.

Resultado: `303 See Other` hacia `/cvs/8?message=CV+importado+desde+JSON+correctamente.`

---

Accion:
Generar y descargar PDF por HTTP.

Motivo:
Confirmar compilacion LaTeX y descarga PDF.

Comando: `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/6/export/pdf?template_key=tech' -UseBasicParsing -OutFile data\\final-download-cv6.pdf`

Argumentos:
- `template_key=tech`.

Resultado: descarga OK; PDF local de verificacion con `29620` bytes.

---

Accion:
Verificar archivos persistidos en `/data/exports`.

Motivo:
Confirmar persistencia de artefactos finales.

Comando: `docker compose exec app python -c "from pathlib import Path; p=Path('/data/exports'); print(...)"`.

Argumentos:
- Listado de archivos directos en `/data/exports`.

Resultado: existen JSON, TEX y PDF exportados para CV id `6`; ejemplo final `cv-6-etapa-3-export-test-tech-20260604005656577451.pdf` con `29620` bytes.

---

Accion:
Crear rama de mini-etapa 3.1 desde `development`.

Motivo:
Corregir mapeo de texto PDF sin trabajar directo sobre `main` ni `development`.

Comando: `git switch -c feature/pdf-ats-text-extraction`

Argumentos:
- Rama base: `development` sincronizada con `origin/development`.

Resultado: rama `feature/pdf-ats-text-extraction` creada.

---

Accion:
Actualizar preambulos LaTeX para extraccion de texto.

Motivo:
Mejorar copy/paste, extraccion con herramientas PDF y compatibilidad futura con ATS.

Comando: edicion manual de `classic.tex`, `modern.tex`, `compact.tex` y `tech.tex`

Argumentos:
- `\input{glyphtounicode}`
- `\pdfgentounicode=1`
- `\usepackage{cmap}`
- `\usepackage{lmodern}`

Resultado: las cuatro plantillas quedaron con mapeo Unicode y fuente Latin Modern.

---

Accion:
Agregar herramientas de validacion PDF al contenedor.

Motivo:
Compilar con `lmodern` y validar extraccion con `pdftotext`.

Comando: edicion manual de `Dockerfile`

Argumentos:
- `lmodern`: provee `lmodern.sty`.
- `poppler-utils`: provee `pdftotext`.

Resultado: Dockerfile actualizado.

---

Accion:
Validar sintaxis y diff.

Motivo:
Detectar errores antes de reconstruir Docker.

Comandos:
- `python -m compileall app tests`
- `git diff --check`

Argumentos:
- `app tests`: modulos y suite.

Resultado: ambas validaciones OK.

---

Accion:
Reconstruir imagen Docker para Etapa 3.1.

Motivo:
Instalar `poppler-utils` y luego `lmodern`.

Comando: `docker compose build`

Argumentos:
- Servicio `app`.

Resultado: primer build OK con `poppler-utils`, pero la primera compilacion PDF fallo por falta de `lmodern.sty`. Se agrego `lmodern` y el build final fue exitoso.

---

Accion:
Levantar servicio final de Etapa 3.1.

Motivo:
Ejecutar tests y validaciones PDF reales.

Comando: `docker compose up -d`

Argumentos:
- `-d`: arranque en segundo plano.

Resultado: contenedor recreado e iniciado.

---

Accion:
Verificar estado Docker.

Motivo:
Confirmar que el contenedor esta operativo.

Comando: `docker compose ps`

Argumentos:
- Servicio `app`.

Resultado: `cv_latex_app` quedo `Up` y `healthy`.

---

Accion:
Ejecutar suite en contenedor.

Motivo:
Validar que el cambio de plantillas no rompe servicios existentes.

Comando: `docker compose exec app python -m pytest`

Argumentos:
- Suite completa.

Resultado: `14 passed in 0.12s`.

---

Accion:
Confirmar herramienta de extraccion.

Motivo:
Validar que el contenedor permite probar texto extraido de PDF.

Comando: `docker compose exec app which pdftotext`

Argumentos:
- Binario `pdftotext`.

Resultado: `/usr/bin/pdftotext`.

---

Accion:
Crear CV de prueba con texto ATS.

Motivo:
Validar acentos y glifos comunes de espanol.

Comando: `docker compose exec app python -c "... cv_repository.create_cv(...); print(cv_id)"`

Argumentos:
- Texto: `Perfil tecnico con gestion de informacion, analisis, educacion, comunicacion, ñandu, accion, configuracion.` con acentos en el dato real.

Resultado: CV de prueba creado con id `11`.

---

Accion:
Generar PDF con las cuatro plantillas.

Motivo:
Confirmar que `classic`, `modern`, `compact` y `tech` compilan con el nuevo preambulo.

Comando: `docker compose exec app python -c "... generate_cv_pdf_export(...)"`.

Argumentos:
- Plantillas: `classic`, `modern`, `compact`, `tech`.

Resultado:
- `classic`: `/data/exports/cv-11-etapa-3.1-ats-text-extraction-classic-20260604030609609031.pdf`
- `modern`: `/data/exports/cv-11-etapa-3.1-ats-text-extraction-modern-20260604030609957022.pdf`
- `compact`: `/data/exports/cv-11-etapa-3.1-ats-text-extraction-compact-20260604030610282686.pdf`
- `tech`: `/data/exports/cv-11-etapa-3.1-ats-text-extraction-tech-20260604030610552827.pdf`

---

Accion:
Extraer texto de PDFs generados.

Motivo:
Validar que `Perfil` y texto con caracteres espanoles no se rompen.

Comando: `docker compose exec app python -c "... subprocess.run(['pdftotext', str(path), '-'], ...)"`.

Argumentos:
- Palabras esperadas: `Perfil`, texto acentuado, `ñandu`, `accion` y `configuracion` con caracteres reales en el PDF.

Resultado: `missing=none` para `classic`, `modern`, `compact` y `tech`.

---

## 2026-06-04 - Etapa 3.2 Baseline Hardening & Consistency

Accion:
Crear rama de hardening desde `development`.

Motivo:
Corregir hallazgos altos y medios del baseline sin trabajar directo sobre `main` ni `development`.

Comandos:
- `git status --short --branch`
- `git fetch origin`
- `git switch development`
- `git rev-list --left-right --count development...origin/development`
- `git switch -c feature/baseline-hardening`

Resultado: rama `feature/baseline-hardening` creada desde `development` sincronizada.

---

Accion:
Endurecer import JSON, duplicado de CV, errores PDF y bind local de Docker Compose.

Motivo:
Reducir superficie de exposicion local, evitar lectura completa de uploads excesivos, separar mensaje seguro de detalle tecnico y cerrar el caso de titulos duplicados al limite.

Comando: `apply_patch`

Argumentos:
- `docker-compose.yml`: bind por defecto `127.0.0.1:8000:8000` mediante `APP_HOST_BIND`.
- `.env.example`: documentacion de `APP_HOST_BIND`.
- `app/services/export_service.py`: lectura por chunks con limite temprano de `512 KB`.
- `app/services/pdf_service.py`: mensaje seguro para UI y detalle tecnico separado.
- `app/routes/cvs.py`: uso del lector limitado y redirect seguro ante fallo PDF.
- `app/repositories/cv_repository.py` y `app/validations/cv_validations.py`: duplicado validado y truncado seguro.
- `tests/`: cobertura minima de import limite, duplicado con titulo largo y error PDF seguro.
- `README.md` y docs de desarrollo: baseline 3.2 documentado.

Resultado: cambio aplicado sin modificar el alcance funcional fuera de la mini-etapa.

---

Accion:
Validar sintaxis y diff local.

Motivo:
Detectar errores tempranos antes de reconstruir Docker.

Comandos:
- `python -m compileall app tests`
- `git diff --check`

Resultado: compilacion Python correcta y `git diff --check` sin errores; solo advertencias CRLF normales en Windows.

---

Accion:
Reconstruir y levantar la app endurecida.

Motivo:
Validar que el contenedor sigue funcionando y que el puerto publicado queda limitado a localhost.

Comandos:
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs app`

Resultado: contenedor `cv_latex_app` iniciado y `healthy`; `docker compose ps` confirma `127.0.0.1:8000->8000/tcp`.

---

Accion:
Ejecutar tests dentro del contenedor.

Motivo:
Confirmar que el baseline endurecido no rompe la funcionalidad previa y cubre los nuevos casos minimos.

Comando: `docker compose exec app python -m pytest`

Argumentos:
- Suite completa dentro de la imagen actualizada.

Resultado: `17 passed in 0.15s`.

---

Accion:
Validar respuesta HTTP local y flujos obligatorios.

Motivo:
Comprobar import JSON valido/excedido, duplicado con titulo largo y generacion PDF real.

Comandos:
- `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`
- `Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing`
- `docker compose exec app python -c "... create_cv(...)"` para crear CVs de prueba `12` y `13`
- `docker compose exec app python -c "... export_cv_json(...)"` para export JSON valido
- `curl.exe -s -D - -o NUL -F "json_file=@data/exports/<archivo>.json;type=application/json" http://localhost:8000/cvs/import/json`
- `curl.exe -s -D - -o NUL -F "json_file=@data/oversized-import-hardening.json;type=application/json" http://localhost:8000/cvs/import/json`
- `curl.exe -s -D - -o NUL -X POST http://localhost:8000/cvs/13/duplicate`
- `docker compose exec app python -c "... get_cv(15) ..."` para verificar titulo duplicado
- `Invoke-WebRequest -Uri 'http://localhost:8000/cvs/12/export/pdf?template_key=classic' -UseBasicParsing -OutFile 'data\\hardening-pdf-validation.pdf'`
- `docker compose exec app python -c "... Path('/data/exports').glob(...)"` para verificar PDF persistido

Resultado:
- `http://localhost:8000` responde `200`.
- `/health` devuelve `version: 0.4.2`.
- Import JSON valido redirige a `/cvs/14?message=CV+importado+desde+JSON+correctamente.`.
- Import excedido redirige a `/cvs/?message=No+se+pudo+importar+el+JSON%3A+El+archivo+JSON+supera+el+maximo+permitido.`.
- El duplicado del titulo largo crea `cv_id=15` con longitud final `120` y sufijo `(copia)`.
- La generacion PDF sigue funcionando; ejemplo persistido: `/data/exports/cv-12-hardening-import-source-classic-20260604044658516376.pdf`.

---

## 2026-06-04 - Etapa 4 Cover Letters

Accion:
Crear rama de Etapa 4 desde `development`.

Motivo:
Respetar Git Flow y no trabajar directo sobre `main` ni `development`.

Comandos:
- `git status --short --branch`
- `git fetch origin`
- `git switch development`
- `git rev-list --left-right --count development...origin/development`
- `git switch -c feature/cover-letters`

Resultado: rama `feature/cover-letters` creada desde `development` sincronizada.

---

Accion:
Agregar modelo, tabla SQLite, repositorio, validaciones, rutas y templates de Cover Letters.

Motivo:
Implementar CRUD basico de cartas con asociacion opcional a CV y navegacion desde la app.

Comando: `apply_patch`

Argumentos:
- `app/models.py`: nuevo modelo `CoverLetter`.
- `app/schemas.py`: nuevo schema `CoverLetterFormData`.
- `app/database.py`: nueva tabla `cover_letters` e indices.
- `app/repositories/cover_letter_repository.py`: acceso a datos SQLite.
- `app/validations/cover_letter_validations.py`: reglas del formulario.
- `app/routes/cover_letters.py`: CRUD y exportaciones.
- `app/templates/cover_letters/`: listado, formulario, detalle y confirmacion.
- `app/routes/dashboard.py`, `app/templates/dashboard.html`, `app/templates/layout.html`: navegacion y estado de modulo.

Resultado: modulo web de cartas integrado al dashboard y al header.

---

Accion:
Extender pipeline LaTeX/PDF/exports para cartas.

Motivo:
Reutilizar la infraestructura actual para exportar TEX y generar PDF de cartas sin duplicar logica.

Comando: `apply_patch`

Argumentos:
- `app/latex_templates/cover_letter/classic_letter.tex`: plantilla propia.
- `app/services/latex_service.py`: generacion TEX para cover letters.
- `app/services/export_service.py`: escritura segura de TEX/PDF para cartas.
- `app/services/pdf_service.py`: compilacion PDF para cartas usando el mismo flujo controlado.
- `tests/test_latex_service.py`, `tests/test_pdf_service.py`, `tests/test_cover_letter_repository.py`: cobertura basica del nuevo soporte.

Resultado: las cartas pueden exportarse a TEX y PDF con nombres de archivo seguros y persistencia en `/data/exports`.

---

Accion:
Actualizar version y documentacion de la etapa.

Motivo:
Dejar trazabilidad de la nueva capacidad y evitar docs desfasadas respecto del baseline real.

Comando: `apply_patch`

Argumentos:
- `VERSION`, `.env.example`, `docker-compose.yml`, `Dockerfile`, `README.md`
- `docs/development/COVER_LETTERS.md`
- `docs/development/CV_BUILDER_CORE.md`
- `docs/development/CHANGELOG_GENERAL.md`
- `docs/development/MODULE_INDEX.md`
- `docs/adr/ADR-0004-latex-rendering.md`

Resultado: version `0.5.0` documentada y modulo de cartas cubierto en README y docs de desarrollo.

---

Accion:
Validar sintaxis local y whitespace.

Motivo:
Detectar errores tempranos antes de reconstruir Docker.

Comandos:
- `python -m compileall app tests`
- `git diff --check`

Resultado: compilacion Python correcta y `git diff --check` sin errores; solo advertencias CRLF normales en Windows.

---

Accion:
Reconstruir y levantar la app con Cover Letters.

Motivo:
Validar el modulo dentro del contenedor real antes de probar flujos HTTP.

Comandos:
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose logs app`

Resultado: contenedor `cv_latex_app` iniciado y `healthy`; `docker compose ps` confirma `127.0.0.1:8000->8000/tcp`.

---

Accion:
Ejecutar tests dentro del contenedor.

Motivo:
Confirmar que el nuevo modulo no rompe la base actual y que los tests minimos del modulo pasan.

Comando: `docker compose exec app python -m pytest`

Argumentos:
- Suite completa dentro de la imagen actualizada.

Resultado: `21 passed in 0.20s`.

---

Accion:
Validar flujos HTTP reales del modulo Cover Letters.

Motivo:
Comprobar creacion, edicion, listado, detalle, asociacion a CV, exportacion TEX/PDF y eliminacion con confirmacion.

Comandos:
- `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`
- `Invoke-WebRequest -Uri http://localhost:8000/cvs/ -Method Post -Body @{ ... }`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/ -Method Post -Body @{ ... associated_cv_id = '16' }`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/ -UseBasicParsing`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/1 -UseBasicParsing`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/1/edit -Method Post -Body @{ ... }`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/1/export/tex -UseBasicParsing -OutFile data\\cover-letter-stage4.tex`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/1/export/pdf -UseBasicParsing -OutFile data\\cover-letter-stage4.pdf`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/1/delete -UseBasicParsing`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/1/delete -Method Post -Body @{ confirm_delete = 'yes' }`

Resultado:
- `http://localhost:8000` responde `200`.
- Se creo `cv_id=16` para asociacion de carta.
- Se creo `cover_letter_id=1` y redirigio a `/cover-letters/1?message=Carta+creada+correctamente.`.
- El listado mostro `Empresa Azul` y `Backend Engineer`.
- El detalle mostro `CV Etapa 4 Base`, `Descargar TEX` y `Generar PDF`.
- La edicion redirigio a `/cover-letters/1?message=Carta+actualizada+correctamente.`.
- La confirmacion de eliminacion respondio `200`.
- La eliminacion logica redirigio a `/cover-letters/?message=Carta+eliminada+correctamente.` y la carta dejo de aparecer en el listado.

---

Accion:
Verificar persistencia de artefactos y extraccion de texto PDF.

Motivo:
Confirmar que TEX/PDF quedan en `/data/exports` y que el PDF generado mantiene texto extraible basico.

Comandos:
- `docker compose exec app python -c "from pathlib import Path; paths=sorted(Path('/data/exports').glob('cover-letter-1-*')); [print(p) for p in paths]"`
- `docker compose exec app python -c "from pathlib import Path; import subprocess; pdf=sorted(Path('/data/exports').glob('cover-letter-1-*.pdf'))[-1]; result=subprocess.run(['pdftotext', str(pdf), '-'], capture_output=True, text=True, check=True); ..."`

Resultado:
- Archivos persistidos:
  - `/data/exports/cover-letter-1-empresa-azul-sa-senior-backend-engineer-classic_letter-20260604123535254711.tex`
  - `/data/exports/cover-letter-1-empresa-azul-sa-senior-backend-engineer-classic_letter-20260604123535270431.tex`
  - `/data/exports/cover-letter-1-empresa-azul-sa-senior-backend-engineer-classic_letter-20260604123535274462.pdf`
- `pdftotext` encontro correctamente `Perfil tecnico`, `Empresa Azul SA` y `Senior Backend Engineer`.

---

## 2026-06-04 - Fix P1 cover-letter export filenames

Accion:
Revisar el problema reportado por Codex Review sobre filenames demasiado largos en cartas.

Motivo:
Inputs validos de `company` y `position` de hasta `160` caracteres podian producir `OSError: [Errno 36] File name too long` en TEX/PDF.

Comandos:
- `git status --short --branch`
- `Get-Content app/services/export_service.py`
- `Get-Content app/services/latex_service.py`
- `Get-Content tests/test_export_service.py`
- `Get-Content tests/test_latex_service.py`
- `Get-Content tests/test_pdf_service.py`

Resultado: se confirmo que el naming de cover letters no tenia cap en `export_service` ni en el `.tex` generado por `latex_service`.

---

Accion:
Implementar helper comun para filenames capped.

Motivo:
Aplicar un criterio consistente y reutilizable entre TEX generado y exportaciones persistidas.

Comando: `apply_patch`

Argumentos:
- `app/services/file_naming.py`: nuevo helper comun.
- `app/services/export_service.py`: filenames capped para exportaciones.
- `app/services/latex_service.py`: filename capped para `.tex` generado.
- `tests/`: nuevos casos de borde para nombres largos.

Resultado: filenames de cartas quedan capped a `180` caracteres, con `id` y timestamp para unicidad.

---

Accion:
Validar sintaxis local.

Motivo:
Detectar errores de import o sintaxis antes de reconstruir Docker.

Comandos:
- `python -m compileall app tests`
- `python -m pytest tests/test_export_service.py tests/test_latex_service.py tests/test_pdf_service.py`

Resultado:
- `compileall` OK.
- `pytest` local no disponible en Windows: `No module named pytest`.

---

Accion:
Reconstruir y levantar la app con el fix.

Motivo:
Ejecutar validaciones reales del P1 dentro del contenedor.

Comandos:
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose exec app python -m pytest`

Resultado:
- Primer `pytest` detecto una expectativa vieja de test sobre el nombre de `.tex` generado.
- Se ajusto el test y se reconstruyo la imagen.
- Validacion final: `24 passed in 0.22s`.

---

Accion:
Probar exportaciones reales con `company` y `position` al maximo permitido.

Motivo:
Confirmar que el fix cubre el caso reportado y evita `OSError` en rutas reales.

Comandos:
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/ -Method Post -Body @{ company = 'A' * 160; position = 'B' * 160; ... }`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/2/export/tex -UseBasicParsing -OutFile data\\cover-letter-long.tex`
- `Invoke-WebRequest -Uri http://localhost:8000/cover-letters/2/export/pdf -UseBasicParsing -OutFile data\\cover-letter-long.pdf`
- `docker compose exec app python -c "from pathlib import Path; files=sorted(Path('/data/exports').glob('cover-letter-2-*')); [print(f'{len(p.name)} {p.name}') for p in files]"`
- `docker compose exec app python -c "from pathlib import Path; import subprocess; pdf=sorted(Path('/data/exports').glob('cover-letter-2-*.pdf'))[-1]; ..."`
- `git diff --check`

Resultado:
- Se creo `cover_letter_id=2`.
- Export TEX OK.
- Export PDF OK.
- Archivos persistidos con longitud `180`.
- `pdftotext` encontro el contenido esperado.
- `git diff --check` sin errores; solo advertencias CRLF normales en Windows.

---

## 2026-06-04 - Etapa 5 Application Tracker

Accion:
Crear rama de Etapa 5 desde `development`.

Motivo:
Respetar Git Flow y no trabajar directo sobre `main` ni `development`.

Comandos:
- `git status --short --branch`
- `git fetch origin`
- `git rev-list --left-right --count development...origin/development`
- `git switch development`
- `git switch -c feature/application-tracker`

Resultado: rama `feature/application-tracker` creada desde `development` sincronizada.

---

Accion:
Agregar modelo, tabla SQLite, repositorio, validaciones, rutas y templates del modulo Postulaciones.

Motivo:
Implementar CRUD basico de postulaciones con estados y asociaciones opcionales a CV y cover letter.

Comando: `apply_patch`

Argumentos:
- `app/models.py`: nuevo modelo `Application`.
- `app/schemas.py`: nuevo schema `ApplicationFormData`.
- `app/database.py`: nueva tabla `applications` e indices.
- `app/repositories/application_repository.py`: acceso a datos SQLite.
- `app/validations/application_validations.py`: reglas del formulario.
- `app/routes/applications.py`: CRUD del modulo.
- `app/templates/applications/`: listado, formulario, detalle y confirmacion.
- `app/main.py`, `app/routes/dashboard.py`, `app/templates/dashboard.html`, `app/templates/layout.html`: integracion del modulo.

Resultado: modulo web de postulaciones integrado al dashboard y al header.

---

Accion:
Agregar tests y documentacion de Etapa 5.

Motivo:
Cubrir persistencia, asociaciones, estados y dejar trazabilidad operativa del modulo.

Comando: `apply_patch`

Argumentos:
- `tests/test_application_repository.py`
- `tests/test_application_validations.py`
- `README.md`
- `docs/development/APPLICATION_TRACKER.md`
- `docs/development/CHANGELOG_GENERAL.md`
- `docs/development/DEVELOPMENT_LOG.md`
- `docs/development/COMMAND_LOG.md`
- `docs/development/MODULE_INDEX.md`
- `VERSION`, `.env.example`, `Dockerfile`, `docker-compose.yml`

Resultado: version `0.6.0` documentada y modulo Application Tracker cubierto en docs y tests.

---

Accion:
Validar el modulo Application Tracker en Docker y por HTTP.

Motivo:
Confirmar que el CRUD, las asociaciones opcionales, los cambios de estado y la persistencia funcionan sobre la app levantada.

Comandos:
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose exec app python -m pytest`
- `Invoke-WebRequest http://localhost:8000`
- Requests HTTP `POST` y `GET` a `/cvs/`, `/cover-letters/` y `/applications/`
- `docker compose exec app python -c "... sqlite3 ..."`

Resultado:
- Contenedor `cv_latex_app` healthy en `127.0.0.1:8000`.
- Suite `pytest` en Docker: `28 passed`.
- Creacion, edicion, detalle, cambio de estado y eliminacion de postulaciones validados por HTTP.
- Asociaciones a CV y cover letter verificadas.
- Persistencia comprobada en SQLite, incluyendo `deleted_at` para eliminacion logica.

---

Accion:
Crear rama de Etapa 6 desde `development`.

Motivo:
Respetar Git Flow y no trabajar directo sobre `main` ni `development`.

Comandos:
- `git status --short --branch`
- `git fetch origin`
- `git rev-list --left-right --count development...origin/development`
- `git switch development`
- `git switch -c feature/ats-basic-check`

Resultado: rama `feature/ats-basic-check` creada desde `development` sincronizada.

---

Accion:
Agregar servicio ATS basico, ruta dedicada y template de analisis para CVs.

Motivo:
Implementar el chequeo ATS de forma modular, sin IA y sin mezclar la logica funcional dentro de `cvs.py`.

Comando: `apply_patch`

Argumentos:
- `app/services/ats_service.py`: score, checklist, advertencias y recomendaciones.
- `app/routes/ats.py`: endpoint para analizar un CV existente.
- `app/templates/ats/cv_analysis.html`: vista del resultado ATS.
- `app/templates/cvs/detail.html`: nueva accion `Analizar ATS`.
- `app/main.py`, `app/routes/dashboard.py`, `app/templates/dashboard.html`, `app/static/css/app.css`: integracion visual minima.

Resultado: modulo ATS Basic Check integrado a CVs existentes sin dependencias externas.

---

Accion:
Agregar tests y documentacion de Etapa 6.

Motivo:
Cubrir el servicio ATS, la ruta de analisis y dejar trazabilidad del alcance real de la etapa.

Comando: `apply_patch`

Argumentos:
- `tests/test_ats_service.py`
- `tests/test_ats_routes.py`
- `README.md`
- `docs/development/ATS_BASIC_CHECK.md`
- `docs/development/CHANGELOG_GENERAL.md`
- `docs/development/DEVELOPMENT_LOG.md`
- `docs/development/COMMAND_LOG.md`
- `docs/development/MODULE_INDEX.md`
- `VERSION`, `.env.example`, `Dockerfile`, `docker-compose.yml`

Resultado: version `0.7.0` documentada y modulo ATS cubierto en docs y tests.

---

Accion:
Agregar dependencia de testing para rutas.

Motivo:
`fastapi.testclient` requiere `httpx` para ejecutar la prueba basica de la ruta ATS dentro del contenedor.

Comando: `apply_patch`

Argumentos:
- `requirements.txt`
- `docs/development/CHANGELOG_GENERAL.md`

Resultado: dependencia `httpx==0.28.1` agregada para soportar tests de rutas.

---

Accion:
Validar el modulo ATS Basic Check en Docker y por HTTP.

Motivo:
Confirmar que el score, checklist, advertencias y recomendaciones se muestran correctamente sobre CVs completos e incompletos.

Comandos:
- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `docker compose exec app python -m pytest`
- `Invoke-WebRequest http://localhost:8000`
- Requests HTTP `POST` y `GET` a `/cvs/` y `/ats/cvs/{cv_id}`

Resultado:
- Contenedor `cv_latex_app` healthy en `127.0.0.1:8000`.
- Suite `pytest` en Docker: `31 passed`.
- CV completo validado con link visible `Analizar ATS`, score visible, checklist y recomendaciones presentes.
- CV incompleto validado con estado `Insuficiente`, advertencias de email, telefono, resumen y skills, mas recomendaciones de completitud.

---

Accion:
Corregir la clasificacion ATS cuando faltan secciones core.

Motivo:
Evitar que un CV con experiencia o educacion faltante quede en estado `Bueno` por tener score alto derivado del resto de checks.

Comando: `apply_patch`

Argumentos:
- `app/services/ats_service.py`
- `tests/test_ats_service.py`
- `docs/development/ATS_BASIC_CHECK.md`
- `docs/development/CHANGELOG_GENERAL.md`

Resultado:
- Se agrego cap de score para secciones criticas faltantes.
- Ningun CV con secciones core faltantes puede quedar en `Bueno`.
- Si faltan experiencia y educacion juntas, el estado queda forzado a `Insuficiente`.

---

## 2026-06-04 - Etapa 7 MVP final polish

Accion:
Crear rama de Etapa 7 desde `development`.

Motivo:
Respetar Git Flow y no trabajar directo sobre `main` ni `development`.

Comandos:
- `git status --short --branch`
- `git fetch origin`
- `git switch development`
- `git rev-list --left-right --count development...origin/development`
- `git switch -c feature/mvp-final-polish`

Resultado: rama `feature/mvp-final-polish` creada desde `development` sincronizada.

---

Accion:
Agregar acceso dedicado a ATS, alinear textos visibles y actualizar versionado del MVP.

Motivo:
Cerrar inconsistencias de navegacion, copy y version visible antes del cierre funcional del MVP.

Comando: `apply_patch`

Argumentos:
- `app/routes/ats.py`: nueva ruta `GET /ats/`.
- `app/routes/dashboard.py`: estados, descripciones y acciones del dashboard.
- `app/templates/layout.html`: link global `ATS` y version dinamica.
- `app/templates/dashboard.html`, `app/templates/ats/`, `app/templates/cover_letters/`, `app/templates/applications/`: copy y navegacion.
- `app/static/css/app.css`: ajuste menor de soporte.
- `VERSION`, `.env.example`, `docker-compose.yml`, `app/main.py`: version `0.8.0`.

Resultado: la navegacion superior ahora expone `ATS`, el dashboard refleja el MVP local y la version visible se alinea con la configuracion real.

---

Accion:
Actualizar documentacion operativa del MVP.

Motivo:
Dejar comandos de uso, persistencia, exports, backup/restore y checklist manual coherentes con el baseline final.

Comando: `apply_patch`

Argumentos:
- `README.md`
- `docs/development/MVP_VALIDATION.md`
- `docs/development/MODULE_INDEX.md`
- `docs/development/VERSIONING.md`
- `docs/development/BRANCH_STRATEGY.md`
- `docs/development/CV_BUILDER_CORE.md`
- `docs/development/COVER_LETTERS.md`
- `docs/development/APPLICATION_TRACKER.md`
- `docs/development/ATS_BASIC_CHECK.md`
- `docs/development/CHANGELOG_GENERAL.md`

Resultado: documentacion alineada a `0.8.0`, con checklist manual del MVP y operacion local documentada.

---

Accion:
Agregar smoke test de la nueva vista ATS index.

Motivo:
No dejar la nueva ruta de navegacion sin cobertura basica.

Comando: `apply_patch`

Argumentos:
- `tests/test_ats_routes.py`: nuevo test de `GET /ats/` y ajuste de copy esperado en la vista de analisis.

Resultado: cobertura minima de la entrada global a ATS agregada.

---

Accion:
Validar sintaxis, build, tests y flujo manual completo del MVP.

Motivo:
Confirmar que el cierre del MVP funciona localmente con Docker Compose sin introducir cambios fuera de alcance.

Comandos:
- `python -m compileall app tests`
- `git diff --check`
- `docker compose build`
- `docker compose up -d`
- `docker compose up -d --force-recreate`
- `docker compose ps`
- `docker compose logs app --tail 80`
- `docker compose exec app python -m pytest`
- `Invoke-WebRequest -Uri http://localhost:8000 -UseBasicParsing`
- `Invoke-WebRequest -Uri http://localhost:8000/ats/ -UseBasicParsing`
- POST por HTTP para crear `cv_id=41` y `cv_id=42`
- GET/POST por HTTP sobre `/cvs/41` y `/cvs/41/edit`
- Descargas HTTP de TEX/PDF/JSON para `cv_id=41`
- `curl.exe -F "json_file=@data/validation/mvp-cv-41.json;type=application/json" http://localhost:8000/cvs/import/json`
- POST por HTTP para crear `cover_letter_id=8`
- GET/POST por HTTP sobre `/cover-letters/8` y `/cover-letters/8/edit`
- Descargas HTTP de TEX/PDF para `cover_letter_id=8`
- POST por HTTP para crear `application_id=6`
- GET/POST por HTTP sobre `/applications/6` y `/applications/6/edit`
- GET por HTTP sobre `/ats/cvs/41` y `/ats/cvs/42`
- `docker compose exec app python -c "... Path('/data/exports').glob(...)"` para verificar artefactos
- `docker compose exec app python -c "... pdftotext ..."` para validar lectura basica de PDFs

Resultado:
- `pytest`: `35 passed in 0.76s`.
- Dashboard y `/ats/` responden `200`.
- `cv_id=41` creado, editado y exportado en TEX/PDF/JSON.
- Import JSON creo `cv_id=43`.
- `cover_letter_id=8` creada, editada y exportada en TEX/PDF.
- `application_id=6` creada, editada y asociada a `cv_id=41` y `cover_letter_id=8`.
- ATS completo (`cv_id=41`) responde `Bueno`.
- ATS incompleto (`cv_id=42`) responde `Insuficiente`.
- `/data/exports` contiene archivos persistidos de CV y carta del flujo de validacion.
