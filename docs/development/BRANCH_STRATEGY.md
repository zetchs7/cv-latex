# Branch Strategy

El flujo obligatorio del proyecto es:

```text
main
^
development
^
feature/*
```

Lectura: cada rama `feature/*` nace desde `development`, y `development` se integra hacia `main` solo con validacion explicita.

## Reglas

- `main` representa version estable.
- `development` representa integracion validada.
- `feature/*` contiene trabajo temporal por etapa o modulo.
- No se trabaja directo sobre `main`.
- No se trabaja directo sobre `development`.
- No se hace push directo a `main` ni a `development` sin validacion explicita del usuario.
- La integracion aprobada se hace por fast-forward controlado desde `feature/*` hacia `development` y luego hacia `main`.
- No se mergea sin validacion explicita del usuario.
- No se hace force push.
- No se borran ramas remotas.

## Etapa 0

- Rama base creada: `development`.
- Rama de trabajo creada: `feature/base-docker-app`.
- Motivo: el repositorio solo tenia `main` y `origin/main`; no existia `development` local ni remota.
