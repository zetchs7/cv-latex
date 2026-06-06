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
- Confirmar sidebar izquierda visible con `Panel de control`, `Curriculum Vitae`, `Cartas de presentacion`, `Postulaciones`, `ATS`, `Documentacion` y `Configuracion local`.
- Confirmar toggle dark/light arriba a la derecha.
- Confirmar que el tema persiste al recargar.
- Confirmar que la version visible coincide con `VERSION` y `/health`.
- Confirmar que `GET /static/css/app.css` y `GET /static/js/app.js` responden `200`.
- Confirmar que el resumen del workspace se ve compacto, sin palabras partidas.
- Confirmar que `Abrir CVs` y `Abrir cartas` se ven como botones.
- Confirmar que el dashboard usa previews CSS y que las miniaturas PDF reales siguen pendientes.
- Confirmar que `Postulaciones` se ve como metrica secundaria y no domina la card.

### CVs

- Crear un CV nuevo.
- Editar el CV.
- Ver el detalle.
- Confirmar que el listado no muestra `SQLite activo`.
- Confirmar que cada fila muestra la fecha `dd/mm/yyyy HH:mm` como metadata secundaria, sin badge flotando arriba.
- Confirmar que `Mas acciones` queda a la derecha y se cierra con click externo o `Escape`.
- Confirmar que `Importar JSON` queda en `Herramientas avanzadas`.
- Confirmar que `Exportacion` y `Ficha rapida` usan spacing consistente, labels cortos y fechas `dd/mm/yyyy HH:mm`.
- Duplicar el CV.
- Confirmar que `Duplicar CV` pide confirmacion antes de ejecutar.
- Exportar TEX desde el selector unificado.
- Exportar PDF desde el selector unificado.
- Exportar JSON.
- Importar el JSON y confirmar que crea un nuevo CV.
- Intentar eliminar con titulo incorrecto y confirmar rechazo.
- Eliminar con titulo exacto y confirmar exito.

### Cartas

- Crear una carta.
- Editar la carta.
- Ver el detalle.
- Confirmar que `Abrir`, `Generar PDF`, `Descargar TEX` y `Mas acciones` quedan a la derecha.
- Confirmar que la fecha del listado se ve como metadata secundaria en formato `dd/mm/yyyy HH:mm`.
- Asociarla opcionalmente a un CV existente.
- Exportar TEX.
- Exportar PDF.
- Intentar eliminar con texto incorrecto y confirmar rechazo.
- Eliminar con `Empresa - Puesto` exacto y confirmar exito.

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
- Ejecutar `Analizar ATS` desde el detalle del CV y confirmar apertura modal.
- Confirmar que el modal ATS muestra `Abrir vista completa`, `Editar CV` y `Cerrar` arriba.
- Confirmar que el badge del estado usa color semantico y que score/estado/longitud quedan mejor alineados.
- Confirmar que desde `Editar CV` en el modal se ve contexto del CV y de la persona en la cabecera del formulario.
- Ejecutar analisis sobre un CV completo.
- Ejecutar analisis sobre un CV incompleto.
- Confirmar score, checklist, recomendaciones y advertencias.

### Documentacion

- Abrir `http://localhost:8000/documentation/`.
- Confirmar que aparecen las dos documentaciones del MVP.
- Abrir `http://localhost:8000/documentation/technical`.
- Abrir `http://localhost:8000/documentation/usage`.
- Confirmar lectura HTML dentro de la web para ambas paginas.
- Confirmar boton visible de descarga PDF en ambas paginas y ausencia de `Abrir PDF directo`.

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
- Miniaturas reales de PDF y selector de paletas quedan como backlog posterior, no como funcionalidad actual.
