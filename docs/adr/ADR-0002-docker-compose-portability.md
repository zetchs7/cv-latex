# ADR-0002 - Docker Compose Portability

- Estado: Aprobado
- Fecha: 2026-06-02

## Contexto

La aplicacion debe poder levantarse localmente de forma clara y reproducible. Los datos persistentes no deben quedar dentro de la imagen Docker ni depender de una nube especifica.

## Decision

Usar Docker Compose con un unico servicio llamado `app`, puerto `8000:8000` y bind mount:

```text
./data:/data
```

El contenedor ejecuta Uvicorn y la app FastAPI. SQLite se prepara dentro de `/data/app.db`.

## Consecuencias

- El proyecto puede moverse entre entornos conservando `./data`.
- La imagen no contiene datos persistentes.
- La operacion local se reduce a comandos Docker Compose estandar.
- Debe evitarse versionar bases SQLite reales o datos personales.
