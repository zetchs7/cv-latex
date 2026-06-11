# Project History and Rollback

## Objetivo

Documentar la referencia estable actual `v0.9.0`, el release anterior `v0.8.0` y comandos de inspeccion o rollback temporal sin ejecutarlos automaticamente.

## Base estable actual

- Tag estable actual: `v0.9.0`
- Commit estable actual: `cbd10fa chore(release): prepare v0.9.0 (#9)`
- Release anterior: `v0.8.0`
- Commit de referencia anterior: `eab9556 fix(docs): render documentation as html with pdf downloads`

## Hitos seguros

- PR `#8` mergeado: integra UI privada y flujo ATS.
- Commit `175d084`: `feat(ui): add private dashboard and integrated ATS flow (#8)`.
- PR `#9` mergeado: release cleanup `v0.9.0`.
- Commit `cbd10fa`: `chore(release): prepare v0.9.0 (#9)`.
- Tag `v0.9.0`: publicado sobre `cbd10fa`.
- Fix XSS: confirmaciones renderizan textos dinamicos con `textContent` en lugar de `innerHTML`.
- PDF tecnico regenerado y validado contra `v0.9.0`.
- Tests del cierre de release: `50 passed`.
- `/health`: `version` confirmada en `0.9.0`.

Los timestamps historicos exactos de algunos hitos previos no se reconstruyen desde este archivo; cuando no esten confirmados con 100% de certeza, registrar `timestamp exacto no reconstruido con certeza`.

## Como inspeccionar tags y referencias

```bash
git tag
git show v0.9.0
git show v0.8.0
git log --oneline --decorate -7
```

## Como volver temporalmente a v0.8.0

Advertencia: no ejecutar sin validacion previa del estado del working tree y sin confirmar que no hay cambios locales que se quieran conservar.

```bash
git checkout v0.8.0
```

## Como crear una rama desde v0.8.0

Advertencia: usar solo si se necesita una linea paralela de trabajo basada en la release estable.

```bash
git checkout -b feature/nueva-rama-desde-v080 v0.8.0
```

## Como volver a development estable

```bash
git checkout development
```

## Nota operativa

- `main` y `development` estan sincronizadas en `cbd10fa` para el release `v0.9.0`.
- Miniaturas reales de PDF, selector de paletas, editor estructurado, drag/drop e IA siguen fuera del alcance de `v0.9.0`.
