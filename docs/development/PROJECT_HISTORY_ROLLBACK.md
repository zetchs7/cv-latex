# Project History and Rollback

## Objetivo

Documentar la referencia estable `v0.8.0` y dejar comandos de inspeccion o rollback temporal para la rama visual privada sin ejecutarlos automaticamente.

## Base estable

- Tag estable: `v0.8.0`
- Commit base: `eab9556 fix(docs): render documentation as html with pdf downloads`
- Rama visual actual: `feature/ui-private-dashboard`

## Objetivo de la etapa

- Rehacer la experiencia visual de la app privada local.
- Incorporar sidebar fija, dashboard operativo, dark/light mode y confirmaciones de borrado mas seguras.
- Mantener el backend funcional y la base de datos sin cambios estructurales.

## Como inspeccionar tags y referencias

```bash
git tag
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

## Como volver a la rama de trabajo actual

```bash
git checkout feature/ui-private-dashboard
```

## Nota operativa

- `main` y `development` deben seguir reflejando la base estable publicada hasta que la nueva etapa UI sea validada, mergeada y vuelva a pasar por review.
- La rama `feature/ui-private-dashboard` sigue en iteracion 8.1.x: miniaturas reales de PDF y selector de paletas quedan reservados para 8.1.3, mientras que IA real queda fuera hasta 8.3.
