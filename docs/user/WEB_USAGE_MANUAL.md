# CV LaTeX Builder - Manual de Uso Web

## Como levantar la app

1. Ejecutar `docker compose build`.
2. Ejecutar `docker compose up -d`.
3. Verificar `docker compose ps`.

> [!RESULTADO] Resultado esperado
> El servicio `app` debe quedar `healthy` y `/health` debe responder `version: 0.9.0`.

## URL local

- Dashboard principal: `http://localhost:8000`
- Centro de documentacion: `http://localhost:8000/documentation/`

## Layout privado y tema

1. Al abrir la app aparece una sidebar fija a la izquierda.
2. Los modulos principales son `Curriculum Vitae` y `Cartas de presentacion`.
3. El boton arriba a la derecha alterna `Dark mode` y `Light mode`.
4. La preferencia de tema se mantiene al recargar porque se guarda en `localStorage`.

## Como crear un CV

1. Entrar a `CVs`.
2. Hacer click en `Nuevo CV`.
3. Completar titulo, nombre, contacto, resumen, experiencia, educacion y skills.
4. Guardar el formulario.

## Como crear un CV estructurado (Feature 1 sin publicar)

1. Entrar a `CVs`.
2. Hacer click en `Crear CV estructurado` o abrir `http://localhost:8000/cvs/new/structured`.
3. Completar las secciones: datos personales y contacto, titulo profesional, resumen profesional, experiencia, educacion, skills, certificaciones, idiomas, proyectos, links e informacion adicional.
4. Usar `Agregar`, `Quitar`, `Subir` y `Bajar` para gestionar y reordenar items; el orden se guarda con el CV.
5. Guardar el formulario; la validacion es en servidor y un envio fallido conserva lo ingresado.

## Como editar, ver, duplicar y eliminar CV

- Desde el listado de `CVs` se puede abrir el detalle.
- En el detalle se puede editar el formulario.
- El boton `Duplicar` crea una copia validada del CV.
- El boton `Eliminar` abre una confirmacion que exige escribir el titulo exacto antes de borrar logicamente.

## Editor estructurado (Feature 1 sin publicar)

- En el detalle de un CV, el boton `Editar estructurado` abre el editor por secciones.
- Secciones editables: datos personales y contacto, titulo profesional, resumen, experiencia, educacion, skills, certificaciones, idiomas, proyectos, links e informacion adicional.
- Items con alta, quitar y reordenar (`Subir`/`Bajar`); renumeracion automatica.
- Validacion 100% en servidor; errores accionables en espanol y sin escrituras parciales; un envio fallido (422) conserva lo ingresado.
- Si el CV no es estructurado valido, el editor arranca desde los campos legacy y avisa que la conversion ocurre al guardar.
- La metadata interna (origen de datos y ultima sincronizacion) es de solo lectura; el servidor la re-estampa al guardar.
- Requiere JavaScript activo; sin JS la app muestra una advertencia y no permite editar items.

## Como exportar TEX, PDF y JSON

- Desde el detalle de un CV se elige una unica plantilla: `Classic`, `Modern`, `Compact` o `Tech`.
- Desde el mismo selector se puede descargar TEX o generar PDF.
- Tambien existe export JSON del CV guardado.
- Para un CV estructurado, `Descargar JSON` genera el envelope schema 2 (archivo `cv-schema2`) y `Descargar JSON plano (schema 1)` fuerza el export plano compatible.

## Como importar JSON

1. Ir al listado de `CVs`.
2. Usar el panel de importacion JSON.
3. Seleccionar un archivo valido.
4. Confirmar que se crea un nuevo CV con sufijo `(importado)`.
- El panel acepta JSON schema 1 (plano) y schema 2 (estructurado), ambos con limite de `512 KB`.
- Schema 2 crea un CV estructurado nuevo; schema 1 mantiene el flujo plano. La importacion nunca sobrescribe el CV de origen.
- Versiones no soportadas se rechazan sin degradar a schema 1.

## Como crear cartas

1. Entrar a `Cartas`.
2. Crear una nueva carta.
3. Asociarla opcionalmente a un CV existente.
4. Completar empresa, puesto, saludo, cuerpo y firma.

## Como exportar cartas

- Desde el detalle de la carta se puede descargar TEX.
- Desde el mismo detalle se puede generar y descargar PDF.
- La eliminacion de cartas tambien exige escribir exactamente `Empresa - Puesto` cuando ambos datos existen.

## Como crear postulaciones

1. Entrar a `Postulaciones`.
2. Crear una nueva postulacion.
3. Completar empresa, puesto, link, fuente y estado.
4. Asociar opcionalmente un CV y una carta.

## Como asociar CV y carta

- En formularios de cartas y postulaciones hay selectores de entidades activas.
- La asociacion es opcional y se valida antes de guardar.

## Como usar ATS Basic Check

1. Abrir `ATS` desde la sidebar o el dashboard.
2. Elegir un CV guardado.
3. Revisar score, checklist, advertencias y recomendaciones.
4. Si falta una seccion critica, el estado no queda como `Bueno`.
- Para CVs estructurados, el chequeo usa el texto normalizado del payload (incluye el contenido solo-estructurado y excluye la metadata interna) con los mismos criterios y score.

## Donde quedan los exports

- Dentro del contenedor: `/data/exports`
- En el host: `./data/exports`

## Como correr tests

- Ejecutar `docker compose exec app python -m pytest`

## Como validar documentacion y PDFs

1. Abrir `http://localhost:8000/documentation/`.
2. Leer `Documentacion tecnica` y `Manual de uso web` dentro de la app.
3. Descargar ambos PDFs desde los botones `Descargar PDF`.
4. Confirmar que la documentacion tecnica menciona `v0.9.0` como release estable y distingue el editor estructurado como Feature 1 sin publicar.
5. Confirmar que no aparecen referencias obsoletas al estado visual anterior ni tareas de integracion visual ya cerradas.

> [!COMANDO] Validacion tecnica de PDF
> Para validar el texto extraible dentro del contenedor se puede usar `pdftotext /app/app/static/docs/Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf -`.

## Como registrar comandos del proyecto

- Registrar comandos relevantes en `docs/development/COMMAND_LOG.md`.
- Usar timestamp local con zona horaria, etapa e ID secuencial `CMD-###`.
- Registrar accion, motivo, comando exacto, argumentos, resultado, error completo y reintento si aplica.
- No usar `COMMAND_LOG.md` como changelog de release; para eso existe el archivo `CHANGELOG_GENERAL.md` dentro de `docs/development`.

## Prompt IDs

- Los Prompt IDs son referencias externas entre Franco y ChatGPT.
- No se incluyen dentro de prompts ejecutables para Codex.
- Si hace falta dejar trazabilidad, registrar la regla o el resultado, no el identificador como parte de una orden.

## Backup basico

```bash
mkdir -p backups
cp data/app.db backups/app-YYYYMMDD-HHMMSS.db
cp -r data/exports backups/exports-YYYYMMDD-HHMMSS
```

## Restore basico

```bash
docker compose down
cp backups/app-YYYYMMDD-HHMMSS.db data/app.db
rm -rf data/exports
cp -r backups/exports-YYYYMMDD-HHMMSS data/exports
docker compose up -d
```

## Alcance local actual

- Uso local sin login ni autenticacion.
- Sin integraciones cloud.
- Sin IA ni servicios externos obligatorios.

## Historial y rollback

- Referencia: `docs/development/PROJECT_HISTORY_ROLLBACK.md`
- Sirve para inspeccionar el tag estable actual `v0.9.0`, revisar el release anterior `v0.8.0` y recordar comandos de rollback sin ejecutarlos sin validacion previa.
