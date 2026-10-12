# Roadmap

<!-- Generado por tools/project_control.py desde docs/development/project_control/catalog.json. No editar a mano: editar el catalogo y ejecutar `python3 tools/project_control.py render`. -->

Ordenado por estado y por dependencia, no por fecha. **Este documento no asigna fechas:**
ninguna fecha del roadmap tiene evidencia que la respalde.

## Como se lee

El roadmap se construye desde el catalogo. Una tarea aparece en la seccion que
corresponde a su estado, y el orden dentro de cada seccion es por prioridad y luego
por dependencia. Para reconstruir el camino critico, mirar `depends_on` en `BACKLOG.md`.

## 1. Trabajo completado

- **QLT-001** [P2] Pipeline que ejecute la suite en la imagen del proyecto _(propuesta, no aprobada)_ — sin dependencias

## 2. Trabajo en curso

- **PCC-001** [P1] Project Control Center v1 — sin dependencias
- **DOC-001** [P2] Corregir el drift de README y del historial de rollback _(propuesta, no aprobada)_ — sin dependencias

## 3. Trabajo listo para iniciar

- **SEC-001** [P0] TrustedHostMiddleware y proteccion contra DNS rebinding _(propuesta, no aprobada)_ — sin dependencias
- **REL-001** [P1] Publicar v0.10.0 con la etapa 9.x _(propuesta, no aprobada)_ — espera: DOC-001
- **SEC-002** [P1] Proteccion CSRF para formularios POST _(propuesta, no aprobada)_ — espera: SEC-001
- **SEC-004** [P2] Unificar la confirmacion destructiva del tracker con el criterio de los demas modulos _(propuesta, no aprobada)_ — sin dependencias

## 4. Trabajo pendiente acordado

- **CV-001** [P1] Importar Curriculum Vitae desde PDF — sin dependencias
- **SEC-003** [P1] Estrategia de autenticacion si la app se expone fuera de localhost _(propuesta, no aprobada)_ — espera: SEC-002
- **OPS-001** [P2] Procedimiento de backup documentado pero inseguro y sin verificar _(propuesta, no aprobada)_ — sin dependencias
- **QLT-002** [P2] Reejecutar los flujos de navegador real del editor estructurado _(propuesta, no aprobada)_ — sin dependencias
- **SEC-005** [P2] Cap de tamaño de request por endpoint _(propuesta, no aprobada)_ — espera: SEC-001
- **AIX-001** [P3] Integraciones asistidas por IA _(propuesta, no aprobada)_ — sin dependencias
- **ATS-001** [P3] UX residual del modulo ATS _(propuesta, no aprobada)_ — sin dependencias
- **CLEAN-001** [P3] Limpieza del CV id 49 y artefactos de validacion en data/ _(propuesta, no aprobada)_ — sin dependencias
- **DBV-001** [P3] Migraciones versionadas por pasos _(propuesta, no aprobada)_ — sin dependencias
- **DOC-002** [P3] Derivar la version de release de la documentacion de la version del proyecto _(propuesta, no aprobada)_ — sin dependencias
- **EDT-001** [P3] Drag and drop en el editor estructurado _(propuesta, no aprobada)_ — sin dependencias
- **IMP-001** [P3] Exportaciones e importaciones mas amplias que JSON _(propuesta, no aprobada)_ — sin dependencias
- **QLT-003** [P3] Adoptar black y ruff como dependencias de desarrollo _(propuesta, no aprobada)_ — sin dependencias

## 5. Trabajo bloqueado

_Vacio._

## 6. Trabajo cancelado

_Vacio._

## Criterio de cierre del MVP

1. Los modulos core — CV Builder, editor estructurado, ATS, cartas, tracker, dashboard, exportaciones y documentacion — estan integrados en `development` con suite verde.
2. Todo backlog con prioridad P0 esta cerrado o cuenta con decision explicita de Franco.
3. El riesgo de exposicion de red esta resuelto o documentado como limitacion aceptada.
4. Existe un criterio verificable para importar un CV existente, no solo crear uno de cero.
5. La documentacion de usuario describe el comportamiento real y sus PDFs fueron validados.

## Vision ampliada (fuera del MVP)

1. Importacion de CV existente (PDF) con revision humana antes de guardar.
2. Exportaciones e importaciones mas amplias que JSON (DOCX, Markdown).
3. Mejoras de UX residuals del modulo ATS.
4. Integraciones asistidas por IA, si Franco define alcance y limites.
5. Estrategia de autenticacion si la aplicacion deja de ser estrictamente local.

## Release y mantenimiento

- Version estable actual: **0.9.0**.
- Los tags se crean solo con autorizacion explicita.
- Publicar en `main` exige: suite verde, artefactos de documentacion regenerados si cambiaron sus fuentes, changelog actualizado y decision humana.
- `main` nunca se modifica sin autorizacion explicita.
