# MVP Validation

## Objetivo

Checklist manual minima para validar el MVP local antes de mergear una rama de cierre o preparar una release local.

Version objetivo actual: `0.9.0`

## Validaciones fuertes Etapa 9.0

- Confirmar que `docs/adr/ADR-0001-structured-cv-editor.md` existe y es una decision de arquitectura, no una implementacion.
- Confirmar que `docs/development/STRUCTURED_CV_EDITOR_PLAN.md` existe y divide la implementacion futura en subetapas verificables.
- Confirmar que ambos documentos mencionan compatibilidad con CVs existentes, export/import JSON, LaTeX/PDF, ATS, migracion/rollback, tests, riesgos, subetapas y no implementacion en 9.0.
- Confirmar que no se modificaron `app/`, `tests/`, `app/static/docs/`, DB, rutas funcionales, templates productivos ni renderer LaTeX/PDF en esta etapa.
- Confirmar que `AGENTS.md` y `MODULE_INDEX.md` enlazan la ADR y el plan antes de futuras etapas sobre editor estructurado.

## Validaciones fuertes Etapa 8.4

- Confirmar que `docs/development/LESSONS_LEARNED.md` existe y documenta aprendizajes reales, no consejos genericos.
- Confirmar que `docs/development/PROJECT_PLAYBOOK.md` existe y puede reutilizarse como procedimiento operativo.
- Confirmar que `AGENTS.md` referencia ambos documentos y exige leerlos antes de etapas nuevas o cambios sensibles.
- Confirmar que `MODULE_INDEX.md` documenta el objetivo de ambos archivos.
- Confirmar que `COMMAND_LOG.md` registra solo los comandos nuevos de la etapa 8.4 sin inventar timestamps historicos.
- Confirmar que no se modificaron PDFs, assets estaticos funcionales, DB ni codigo de negocio en una etapa documental.

## Validaciones fuertes Etapa 8.3

- Confirmar que existe `AGENTS.md` del repo con reglas reales de stack, Git Flow, validaciones, docs/PDF y Prompt IDs externos a Codex.
- Confirmar que `COMMAND_LOG.md` documenta el formato nuevo para comandos futuros con timestamp local, etapa, `CMD-###`, accion, motivo, comando exacto, argumentos, resultado, error completo y reintento.
- Confirmar que `DEVELOPMENT_LOG.md`, `CHANGELOG_GENERAL.md`, `MODULE_INDEX.md`, `VERSIONING.md` y `PROJECT_HISTORY_ROLLBACK.md` no inventan timestamps historicos.
- Confirmar que `/health` mantiene `version: 0.9.0`.
- Confirmar que los PDFs descargables fueron regenerados desde `docs/user/` y que el hash nuevo difiere del hash anterior cuando cambia el contenido o el layout.
- Confirmar con `pdftotext` que los PDFs contienen `v0.9.0` y no contienen referencias obsoletas a `feature/ui-private-dashboard`, `Rama visual actual` ni abrir/integrar el PR visual como pendiente.
- Confirmar que ningun PDF publicado tenga una pagina de indice/TOC vacia. Si hay indice, debe contener entradas reales; si no puede poblarse de forma limpia, debe eliminarse.
- Confirmar con render PNG que portada, indice si existe y una pagina interna de cada PDF son legibles y no tienen texto cortado, titulos huerfanos, listas cortas partidas innecesariamente, cortes pobres, espacios vacios excesivos, solapamientos, tablas rotas ni bloques ilegibles.
- Si se corrige paginacion o layout PDF, regenerar todos los PDFs servidos por la app antes de validar hashes y descargas.
- Confirmar hash anterior/nuevo y descarga real desde `/static/docs/` para cada PDF regenerado.

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
- Confirmar sidebar izquierda visible con `Panel de control`, `Curriculum Vitae + ATS`, `Cartas de presentacion`, `Postulaciones`, `Documentacion` y `Configuracion local`.
- Confirmar toggle dark/light arriba a la derecha.
- Confirmar que el tema persiste al recargar.
- Confirmar que la version visible coincide con `VERSION` y `/health`.
- Confirmar que `GET /static/css/app.css` y `GET /static/js/app.js` responden `200`.
- Confirmar que el resumen del workspace se ve como una linea horizontal simple y compacta, sin cuadrados internos ni numeros gigantes.
- Confirmar que `Abrir CVs` y `Abrir cartas` se ven como botones.
- Confirmar que las cards principales no muestran contadores grandes.
- Confirmar que no hay CTA duplicada `Nueva carta` dentro de recientes.
- Confirmar que `Postulaciones` se ve como metrica secundaria y no domina la card.

### CVs

- Crear un CV nuevo.
- Editar el CV.
- Ver el detalle.
- Confirmar que el listado no muestra `SQLite activo`.
- Confirmar que cada fila muestra `Actualizado: dd/mm/yyyy HH:mm hs` como metadata secundaria debajo de los datos principales, sin badge flotando arriba.
- Confirmar que cada fila muestra un badge `ATS` calculado en runtime junto al titulo del CV y que el badge puede abrir el modal del analisis.
- Confirmar que `Mas acciones` queda a la derecha y se cierra con click externo o `Escape`.
- Confirmar que `Herramientas avanzadas` se ve como boton secundario y que `Importar JSON` queda dentro.
- Confirmar que `Exportacion` y `Ficha rapida` usan el mismo acento visual, spacing consistente, labels cortos y fechas `dd/mm/yyyy HH:mm hs`.
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
- Confirmar que la fecha del listado se ve como metadata secundaria debajo de los datos principales en formato `Actualizada: dd/mm/yyyy HH:mm hs`.
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
- Confirmar que el modal ATS se ve como dashboard compacto, con `Estado general` y `Resumen rapido` a la izquierda, `Checklist` a la derecha y `Recomendaciones`/`Advertencias` abajo.
- Confirmar que `Estado general` muestra titulo, badge semantico visible, score, barra visual con glow sutil en la punta, longitud, rango real de longitud y referencia vertical de score en estructura clara.
- Confirmar que la referencia de score muestra puntos de color semanticos por rango sin romper el estilo del modal.
- Confirmar que el checklist ATS se ve compacto, con indicador circular por fila, descripcion breve y badge `OK`/`Revisar` alineado a la derecha.
- Confirmar que recomendaciones y advertencias quedan en cards inferiores compactas y no generan espacio vacio excesivo.
- Confirmar que desde `Editar CV` en el modal el H1 principal es la persona o titulo del CV y que `Editar CV` queda como contexto.
- Abrir `Ver TEX` y confirmar que `Export Engine` queda alineado dentro del mismo layout y que el nombre largo del archivo no rompe la cabecera.
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
- Confirmar que `/documentation/technical` refleja `v0.9.0` como version preparada y no muestra `feature/ui-private-dashboard` como rama actual ni la UI privada como backlog pendiente.
- Descargar el PDF tecnico y confirmar con `pdftotext` que contiene `v0.9.0`, `Dashboard privado disponible`, `Curriculum Vitae + ATS` y `PR #8`, sin referencias al PR visual como pendiente.
- Descargar el manual de uso PDF y confirmar con `pdftotext` que contiene `v0.9.0` y la regla de Prompt IDs externos a Codex.
- Confirmar que los PDFs tienen portada, version, fecha, estado, pie de pagina, indice poblado si existe, jerarquia visual, callouts, tablas legibles y bloques de comando diferenciados.
- Confirmar visualmente portada, indice si existe y pagina interna relevante renderizadas a PNG con `pdftoppm`, evitando titulos huerfanos, listas cortas partidas, cortes pobres y espacios vacios excesivos.

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
