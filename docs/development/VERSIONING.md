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

- Version vigente en la rama de trabajo del MVP: `0.9.0`
- Tag estable actual: `v0.9.0`
- Fecha de tag `v0.9.0`: `2026-06-11`
- Commit de tag `v0.9.0`: `cbd10fa chore(release): prepare v0.9.0 (#9)`
- Release anterior: `v0.8.0`
- Criterio aplicado:
  - `0.1.0`: base tecnica inicial.
  - `0.2.0` a `0.7.0`: nuevas capacidades funcionales por etapa.
  - `0.8.0`: cierre del MVP local previo a la UI privada integrada.
  - `0.9.0`: release de UI privada, ATS integrado y endurecimiento final del flujo local.

## Reglas de registro temporal

- `VERSIONING.md` registra fechas de release y tags, no cada comando.
- Los comandos ejecutados se registran en `docs/development/COMMAND_LOG.md`.
- Si una fecha historica no puede reconstruirse con certeza, usar `timestamp exacto no reconstruido con certeza`.
- No inventar timestamps para hitos antiguos.

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
| `0.9.0` | 8.1 / 8.2 / 8.3 | UI privada, ATS integrado, release cleanup y trazabilidad/documentacion visual posterior. |
