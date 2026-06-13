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

## Como editar, ver, duplicar y eliminar CV

- Desde el listado de `CVs` se puede abrir el detalle.
- En el detalle se puede editar el formulario.
- El boton `Duplicar` crea una copia validada del CV.
- El boton `Eliminar` abre una confirmacion que exige escribir el titulo exacto antes de borrar logicamente.

## Como exportar TEX, PDF y JSON

- Desde el detalle de un CV se elige una unica plantilla: `Classic`, `Modern`, `Compact` o `Tech`.
- Desde el mismo selector se puede descargar TEX o generar PDF.
- Tambien existe export JSON del CV guardado.

## Como importar JSON

1. Ir al listado de `CVs`.
2. Usar el panel de importacion JSON.
3. Seleccionar un archivo valido.
4. Confirmar que se crea un nuevo CV con sufijo `(importado)`.

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

## Donde quedan los exports

- Dentro del contenedor: `/data/exports`
- En el host: `./data/exports`

## Como correr tests

- Ejecutar `docker compose exec app python -m pytest`

## Como validar documentacion y PDFs

1. Abrir `http://localhost:8000/documentation/`.
2. Leer `Documentacion tecnica` y `Manual de uso web` dentro de la app.
3. Descargar ambos PDFs desde los botones `Descargar PDF`.
4. Confirmar que la documentacion tecnica menciona `v0.9.0`.
5. Confirmar que no aparecen referencias obsoletas al estado visual anterior ni tareas de integracion visual ya cerradas.

> [!COMANDO] Validacion tecnica de PDF
> Para validar el texto extraible dentro del contenedor se puede usar `pdftotext /app/app/static/docs/Proyecto_CV_LaTeX_Builder_Documentacion_Tecnica.pdf -`.

## Como registrar comandos del proyecto

- Registrar comandos relevantes en `docs/development/COMMAND_LOG.md`.
- Usar timestamp local con zona horaria, etapa e ID secuencial `CMD-###`.
- Registrar accion, motivo, comando exacto, argumentos, resultado, error completo y reintento si aplica.
- No usar `COMMAND_LOG.md` como changelog de release; para eso existe `docs/development/CHANGELOG_GENERAL.md`.

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
