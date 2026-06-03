# ADR-0001 - Stack MVP

- Estado: Aprobado
- Fecha: 2026-06-02

## Contexto

El producto necesita una aplicacion web local, pequena, portable y mantenible para construir CVs profesionales en etapas futuras. El MVP debe evitar complejidad innecesaria como PostgreSQL, Redis, Celery, microservicios, cloud o IA obligatoria.

## Decision

Usar:

- Python con FastAPI para el backend.
- Jinja2 para templates HTML server-side.
- CSS simple y JavaScript minimo para la interfaz inicial.
- SQLite como base local en `/data/app.db`.
- Docker Compose para ejecucion local reproducible.

HTMX queda adoptado como direccion para interacciones progresivas futuras, pero Etapa 0 no implementa interacciones dinamicas porque solo corresponde crear la base tecnica.

## Consecuencias

- La aplicacion puede ejecutarse localmente con pocos componentes.
- La persistencia queda simple y portable.
- El stack permite crecer por etapas sin introducir infraestructura pesada.
- Las funcionalidades futuras deben mantener separacion entre rutas, servicios, validaciones, templates y acceso a datos.
