# ATS Basic Check

## Version

- Version del modulo: `0.7.0`
- Etapa: `6 - ATS Basic Check`

## Objetivo

Agregar un chequeo ATS basico, sin IA ni servicios externos, para analizar CVs ya guardados y devolver un resultado simple con score, checklist, advertencias y recomendaciones accionables.

## Archivos principales

- `app/services/ats_service.py`
- `app/routes/ats.py`
- `app/templates/ats/cv_analysis.html`
- `app/templates/cvs/detail.html`
- `tests/test_ats_service.py`
- `tests/test_ats_routes.py`

## Ruta HTTP

- `GET /ats/cvs/{cv_id}`: mostrar analisis ATS del CV indicado.

## Controles implementados

- Email presente.
- Telefono presente.
- Resumen profesional presente.
- Experiencia o educacion presentes.
- Skills cargadas.
- Longitud aproximada del CV dentro de un rango simple.
- Deteccion de secciones importantes vacias.

## Salida mostrada

- Estado general.
- Score simple sobre 100.
- Checklist de controles.
- Recomendaciones basicas.
- Advertencias por secciones vacias o longitud extrema.

## Como probar

1. Levantar la app con `docker compose up -d`.
2. Abrir un CV existente o crear uno nuevo.
3. Entrar al detalle del CV.
4. Usar la accion `Analizar ATS`.
5. Revisar score, checklist, recomendaciones y advertencias.
6. Repetir con un CV completo y con uno incompleto.

## Limitaciones

- No usa IA.
- No parsea PDFs externos.
- No replica scoring real de ATS comerciales.
- No hace matching contra job descriptions.
- El score es orientativo y deliberadamente simple.
