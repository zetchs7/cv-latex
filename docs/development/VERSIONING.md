# Versioning

El proyecto usa versionado semantico:

```text
MAJOR.MINOR.PATCH
```

- `MAJOR`: cambios incompatibles o reestructuraciones grandes.
- `MINOR`: funcionalidades nuevas compatibles.
- `PATCH`: correcciones o mejoras menores compatibles.

La version inicial es `0.1.0` y esta registrada en el archivo `VERSION`.

No se crean tags sin validacion explicita del usuario.

## Version actual

- Version vigente en la rama de trabajo del MVP: `0.8.0`
- Criterio aplicado:
  - `0.1.0`: base tecnica inicial.
  - `0.2.0` a `0.7.0`: nuevas capacidades funcionales por etapa.
  - `0.8.0`: pulido final del MVP local, sin modulos nuevos grandes.

## Mapa rapido por etapa

| Version | Etapa | Alcance principal |
| --- | --- | --- |
| `0.1.0` | 0 | Base tecnica con FastAPI, Docker y SQLite. |
| `0.2.0` | 1 | CV Builder Core. |
| `0.3.0` | 2 | Plantillas LaTeX y sanitizacion. |
| `0.4.0` | 3 | Export Engine TEX/PDF/JSON. |
| `0.4.1` | 3.1 | Fix de extraccion PDF/ATS. |
| `0.4.2` | 3.2 | Hardening baseline. |
| `0.5.0` / `0.5.1` | 4 | Cover Letters y fix de filenames. |
| `0.6.0` | 5 | Application Tracker. |
| `0.7.0` | 6 | ATS Basic Check. |
| `0.8.0` | 7 | Pulido final del MVP local. |
