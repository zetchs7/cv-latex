# Project Playbook

## Objetivo

Playbook operativo para ejecutar etapas con Codex/ChatGPT en proyectos reales, mantener trazabilidad, evitar drift entre artefactos y cerrar PRs con evidencia suficiente.

## 1. Como iniciar una etapa

1. Leer el pedido completo y aislar restricciones explicitas.
2. Leer `~/.codex/AGENTS.md`, `~/.codex/config.toml`, `AGENTS.md` del repo y verificar si existe `.codex/config.toml`.
3. Verificar estado Git con `git status --short --branch`, `git branch --show-current`, `git log --oneline --decorate -7` y `git fetch origin`.
4. Confirmar rama base correcta y partir desde `development` actualizado salvo instruccion distinta.
5. Identificar archivos probables, riesgos y validaciones minimas antes de editar.

## 2. Como decidir modelo, reasoning y speed

- `GPT-5.5`: PDF/LaTeX, Docker delicado, seguridad, refactors grandes, integraciones complejas, bugs dificiles.
- `GPT-5.4`: desarrollo normal, docs, rutas, validaciones, cierres de PR, fixes controlados.
- `GPT-5.4-Mini`: tareas menores de copy, estilos simples o cambios muy acotados.
- `Reasoning Low`: textos y cambios triviales.
- `Reasoning Medium`: fixes chicos o etapas documentales con trazabilidad.
- `Reasoning High`: cambios funcionales medianos o validaciones mas profundas.
- `Reasoning Extra High`: arquitectura, seguridad, DB, PDF complejo o riesgo alto.
- `Speed Standard`: por defecto.
- `Speed Fast`: solo si el alcance es chico o el usuario prioriza urgencia sobre profundidad.

## 3. Como preparar un prompt para Codex

- Declarar etapa, objetivo y motivo.
- Fijar alcance permitido y lista explicita de "No hacer".
- Definir rama esperada, base, commit o PR si aplica.
- Enumerar pasos operativos y validaciones obligatorias.
- Pedir formato final con campos concretos si se necesita auditoria.
- Incluir restricciones de Git, Docker, DB, seguridad y release cuando correspondan.

## 4. Como usar Prompt IDs externos

- Tratar el Prompt ID como referencia externa entre Franco y ChatGPT.
- No incluirlo dentro del texto ejecutable para Codex.
- Si hace falta documentarlo, hacerlo como metadato de trazabilidad humana, nunca como instruccion tecnica.

## 5. Git Flow de trabajo

```text
main <- development <- feature/*
```

- `main`: estable.
- `development`: integracion validada.
- `feature/*`: implementacion o correccion acotada.
- No push directo a `main` o `development` sin autorizacion explicita.
- No merge, force push, tag o borrado de ramas remotas sin pedido expreso.

## 6. Como cerrar una etapa

1. Revisar diff y confirmar que no se filtraron cambios fuera de alcance.
2. Ejecutar validaciones tecnicas y funcionales aplicables.
3. Actualizar solo la documentacion que realmente corresponde.
4. Registrar comandos y decisiones en los logs correctos.
5. Hacer commit atomico.
6. Push de la rama feature.
7. Crear PR a `development`.
8. Pedir `@codex review` si el alcance lo requiere.

## 7. Checklist antes de PR

- Rama feature correcta.
- Diff sin archivos inesperados.
- Validaciones ejecutadas y reportadas.
- Docs de desarrollo actualizadas si el cambio lo exige.
- Working tree limpio despues del commit.
- Titulo y descripcion del PR alineados al alcance real.

## 8. Checklist antes de merge

- PR apunta a la base correcta.
- Ultimo review sin blockers.
- Hallazgos corregidos en la misma rama si siguen dentro del alcance.
- Runtime y tests validados sobre el diff final.
- No quedan conversaciones abiertas relevantes.

## 9. Checklist antes de tag

- `main` y `development` sincronizadas segun estrategia del repo.
- Version visible alineada en runtime, Docker y docs.
- Release notes y changelog coherentes.
- Tests y healthcheck en verde.
- Artefactos descargables regenerados y validados si forman parte del release.

## 10. Cuando usar `@codex review`

- Cambios de release, rutas, seguridad, Docker, PDFs, documentacion servida, exportaciones, DB o integraciones.
- PRs con riesgo de regresion o impacto amplio.
- Re-review cuando cambia el commit revisado.
- No hace falta para typos o cambios triviales sin riesgo real.

## 11. Como resolver hallazgos de Codex Review

1. Leer el hallazgo completo.
2. Confirmar si es blocker real o falso positivo.
3. Aplicar el cambio minimo que corrige la causa raiz.
4. Repetir validaciones relevantes.
5. Mantener el fix en la misma rama y PR si sigue dentro del mismo alcance.
6. Publicar `@codex review` nuevamente cuando el diff cambie de forma relevante.

## 12. Validaciones minimas por tipo de cambio

### Docs simples

- `python -m compileall app tests`
- `git diff --check`
- revisar diff final

### UI

- `python -m compileall app tests`
- `docker compose up -d --force-recreate`
- `docker compose exec app python -m pytest`
- validacion HTTP/DOM o navegador real segun riesgo

### Docker

- `docker compose build`
- `docker compose up -d --force-recreate`
- `docker compose ps`
- `docker compose logs app --tail 80`
- tests o healthcheck

### PDF

- regeneracion por pipeline oficial
- `pdftotext`
- render PNG de portada, indice si existe y pagina interna
- hash anterior/nuevo
- descarga real del artefacto servido

### Seguridad

- revisar superficie afectada
- tests de regresion si existen
- validar que no se introduzcan sinks inseguros como `innerHTML`

### DB o migraciones

- validar migracion, rollback y compatibilidad
- tests o checks sobre datos
- no mezclar con cambios no relacionados

### Exportaciones

- generar artefacto real
- verificar persistencia/descarga
- validar contenido y nombres de archivo

### Release o tag

- version alineada
- tests, healthcheck y runtime
- artefactos y docs consistentes
- estado limpio de ramas y remotos

## 13. Reglas para documentacion PDF

- No publicar TOC vacio.
- No dejar titulos huerfanos al final de pagina.
- No partir listas cortas si pueden moverse completas.
- Validar contraste de callouts y encabezados.
- Renderizar portada, indice si existe y paginas internas relevantes.
- Pasar `pdftotext`.
- Registrar hash anterior y hash nuevo.
- Verificar la descarga real desde la app.

## 14. Reglas para logs

- `COMMAND_LOG.md` registra comandos nuevos con timestamp, accion, motivo, comando, argumentos, resultado, error y reintento.
- `COMMAND_LOG.md` no es changelog.
- `DEVELOPMENT_LOG.md` registra hitos de etapa.
- Si un comando falla, documentar el error completo y la correccion aplicada.

## 15. Reglas para backfill

- Solo completar fechas u horas historicas cuando exista evidencia verificable.
- Si la hora exacta no puede reconstruirse, usar `timestamp exacto no reconstruido con certeza`.
- No disfrazar aproximaciones como precision real.

## 16. Reglas para futuros proyectos

- Empezar con `AGENTS.md` desde etapa 0.
- Definir stack, comandos, Docker, DB, tests, docs y Git Flow desde el inicio.
- Separar de entrada logs de comandos, hitos, changelog y validaciones.
- No esperar al cierre para documentar reglas que ya se demostraron necesarias.

## 17. Reglas para diseno previo a features grandes

- Crear ADR antes de tocar DB, migraciones, import/export, LaTeX/PDF, ATS o UI amplia.
- Documentar alternativas con ventajas, riesgos, impacto en tests y rollback.
- Elegir una arquitectura que preserve compatibilidad con datos existentes.
- Dividir implementacion en subetapas chicas con criterios de aceptacion.
- Para el editor estructurado de CV, leer `docs/adr/ADR-0003-structured-cv-editor.md` y `docs/development/STRUCTURED_CV_EDITOR_PLAN.md` antes de implementar.
