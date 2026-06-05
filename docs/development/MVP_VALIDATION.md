# MVP Validation

## Objetivo

Checklist manual minima para validar el MVP local antes de mergear una rama de cierre o preparar una release local.

## Precondiciones

- Docker Desktop o daemon Docker activo.
- Puerto `8000` disponible en el host.
- Carpeta `./data` existente y montable.

## Comandos base

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose exec app python -m pytest
```

## Checklist manual

### Dashboard y navegacion

- Abrir `http://localhost:8000`.
- Confirmar que el dashboard carga sin errores.
- Confirmar accesos visibles a `CVs`, `Cartas`, `Postulaciones` y `ATS` desde el header.
- Confirmar acceso visible a `Documentacion` desde el header y el dashboard.
- Confirmar que la version visible coincide con `VERSION` y `/health`.

### CVs

- Crear un CV nuevo.
- Editar el CV.
- Ver el detalle.
- Duplicar el CV.
- Exportar TEX.
- Exportar PDF.
- Exportar JSON.
- Importar el JSON y confirmar que crea un nuevo CV.

### Cartas

- Crear una carta.
- Editar la carta.
- Ver el detalle.
- Asociarla opcionalmente a un CV existente.
- Exportar TEX.
- Exportar PDF.

### Postulaciones

- Crear una postulacion.
- Editarla.
- Ver el detalle.
- Asociarla opcionalmente a un CV.
- Asociarla opcionalmente a una carta.
- Cambiar el estado.
- Eliminarla desde la confirmacion.

### ATS

- Abrir `http://localhost:8000/ats/`.
- Ejecutar analisis sobre un CV completo.
- Ejecutar analisis sobre un CV incompleto.
- Confirmar score, checklist, recomendaciones y advertencias.

### Documentacion

- Abrir `http://localhost:8000/documentation/`.
- Confirmar que aparecen las dos documentaciones del MVP.
- Abrir `http://localhost:8000/documentation/technical`.
- Abrir `http://localhost:8000/documentation/usage`.
- Confirmar lectura HTML dentro de la web para ambas paginas.
- Confirmar boton visible de descarga PDF en ambas paginas.

### Persistencia y artefactos

- Confirmar que SQLite sigue en `./data/app.db`.
- Confirmar que los archivos exportados aparecen en `./data/exports`.
- Confirmar que `docker compose down` y `docker compose up -d` conservan los datos del bind mount.

## Resultado esperado

- App usable localmente solo con Docker Compose.
- Tests en verde.
- Navegacion consistente.
- Exportaciones funcionando.
- Persistencia en `./data`.
- Sin depender de IA, login ni servicios externos.
