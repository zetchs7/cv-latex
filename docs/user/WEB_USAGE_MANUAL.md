# CV LaTeX Builder - Manual de Uso Web

## Como levantar la app

1. Ejecutar `docker compose build`.
2. Ejecutar `docker compose up -d`.
3. Verificar `docker compose ps`.

## URL local

- Dashboard principal: `http://localhost:8000`
- Centro de documentacion: `http://localhost:8000/documentation/`

## Como crear un CV

1. Entrar a `CVs`.
2. Hacer click en `Nuevo CV`.
3. Completar titulo, nombre, contacto, resumen, experiencia, educacion y skills.
4. Guardar el formulario.

## Como editar, ver, duplicar y eliminar CV

- Desde el listado de `CVs` se puede abrir el detalle.
- En el detalle se puede editar el formulario.
- El boton `Duplicar` crea una copia validada del CV.
- El boton `Eliminar` abre una confirmacion antes de la eliminacion logica.

## Como exportar TEX, PDF y JSON

- Desde el detalle de un CV se puede descargar TEX.
- Desde el mismo detalle se puede generar y descargar PDF.
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

## Como crear postulaciones

1. Entrar a `Postulaciones`.
2. Crear una nueva postulacion.
3. Completar empresa, puesto, link, fuente y estado.
4. Asociar opcionalmente un CV y una carta.

## Como asociar CV y carta

- En formularios de cartas y postulaciones hay selectores de entidades activas.
- La asociacion es opcional y se valida antes de guardar.

## Como usar ATS Basic Check

1. Abrir `ATS` desde el header o el dashboard.
2. Elegir un CV guardado.
3. Revisar score, checklist, advertencias y recomendaciones.
4. Si falta una seccion critica, el estado no queda como `Bueno`.

## Donde quedan los exports

- Dentro del contenedor: `/data/exports`
- En el host: `./data/exports`

## Como correr tests

- Ejecutar `docker compose exec app python -m pytest`

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
