# Propuestas de Issues para GitHub

**Documento transitorio.** Contiene los Issues que el catálogo recomienda publicar y que
**todavía no existen en GitHub**. Franco los revisa y decide cuáles se publican.

Estado actual verificado el 2026-10-12: el repositorio tiene **1 solo Issue abierto**,
el #14. Los 17 PRs están cerrados.

Cuando cada propuesta se publique o se descarte, se actualiza la fila de estado y el enlace.

## Criterio usado

No todo lo que está en el backlog merece un Issue. Se propone un Issue solo si:

1. El trabajo es rastreable por otra persona, no solo por quien lo escribe.
2. Tiene consecuencia para el usuario o para la confiabilidad del repositorio.
3. El catálogo ya tiene aceptación verificable, así que el Issue no queda en "pendiente de
   pensar".

Quedan fuera los P3 y las ideas sin problema detrás: viven en el catálogo, que es más barato
de mantener.

| # | Propuesta | Tarea | Prioridad | Estado |
| --- | --- | --- | --- | --- |
| 1 | Cierre de la app local a sitios web ajenos | SEC-001 | P1 | ⬜ Sin publicar |
| 2 | Confirmación destructiva del tracker más débil que la del resto | SEC-004 | P2 | ⬜ Sin publicar |
| 3 | Documentación que afirma un estado que ya no existe | DOC-001 | P2 | ⬜ Sin publicar |
| 4 | Las 248 pruebas solo corren localmente | QLT-001 | P2 | ⬜ Sin publicar |
| 5 | Procedimiento de backup documentado pero inseguro y sin verificar | OPS-001 | P2 | ⬜ Sin publicar |

---

## 1. Cierre de la app local a sitios web ajenos

- **Tarea**: `SEC-001`
- **Labels sugeridos**: `tipo:bug`, `p:P1`, `modulo:project`
- **Riesgo asociado**: `RSK-001`

```markdown
## Qué pasa

La aplicación no registra ningún middleware. No hay autenticación, ni CSRF, ni CORS, ni
validación de `Host`.

Un formulario POST con `Form(...)` es una petición simple: no dispara preflight CORS. Eso
significa que cualquier sitio web que visited el usuario puede enviar POST a
`http://127.0.0.1:8000/cvs` y crear, modificar o borrar CVs sin que el navegador lo bloquee
y sin que la aplicación lo compruebe.

## Resultado esperado

La aplicación rechaza peticiones cuyo encabezado `Host` no esté permitido, y el bind por
defecto sigue siendo `127.0.0.1`.

## Evidencia

`app/main.py:26-39` no contiene ningún `add_middleware`. Un grep de
`middleware|Depends(|Security(|csrf` sobre `app/**/*.py` no devuelve resultados.

`docker-compose.yml:13` usa `APP_HOST_BIND=127.0.0.1` por defecto, lo que reduce la
exposición pero no protege contra peticiones desde el navegador a loopback.

## Riesgo si no se hace

El modelo de uso documentado es local y sin login. Mientras siga así, el impacto es acotado.
Si alguna vez se cambia el bind o se publica la app, el problema deja de ser hipotético.

## Criterios de aceptación

- [ ] La aplicación valida el encabezado `Host` y rechaza hosts no permitidos
- [ ] Existe test de regresión que demuestra que un host ajeno es rechazado
- [ ] El bind por defecto sigue siendo `127.0.0.1`
- [ ] La limitación queda documentada en README y en la documentación de usuario
```

---

## 2. Confirmación destructiva del tracker más débil que la del resto

- **Tarea**: `SEC-004`
- **Labels sugeridos**: `tipo:debt`, `p:P2`, `modulo:project`

```markdown
## Qué pasa

CVs y cartas exigen confirmar la eliminación escribiendo el texto exacto de lo que se
borra. El Application Tracker acepta un token fijo:

    `applications.py:201` → confirm_delete == "yes"

Es más fácil de disparar por error y no protege de nada: cualquiera que llegue al formulario
con ese valor confirma el borrado.

## Por qué importa

Es una inconsistencia dentro de la misma aplicación. El usuario que aprendió el patrón de
CVs y cartas espera el mismo cuidado en el tracker.

## Evidencia

- `cvs.py:458-466` — coincidencia exacta del título
- `cover_letters.py:178` — coincidencia exacta del título
- `applications.py:201` — token fijo `"yes"`

## Criterios de aceptación

- [ ] El tracker exige confirmar con la misma coincidencia exacta
- [ ] Un POST con el token fijo deja de eliminar el registro
- [ ] Existe test de regresión para el caso negativo
```

---

## 3. Documentación que afirma un estado que ya no existe

- **Tarea**: `DOC-001`
- **Labels sugeridos**: `tipo:docs`, `p:P2`, `modulo:project`

```markdown
## Qué pasa

El README y el historial de rollback describen un estado del proyecto que ya cambió.

## Evidencia

- `README.md:8` declara `v0.8.0` como último tag estable. El tag real es `v0.9.0`, en `cbd10fa`.
- `README.md:9` declara como base estable `eab9556`, que corresponde a `v0.8.0`.
- `README.md:10` anuncia "Release en preparación: 8.2 - Release cleanup v0.9.0". Ese release
  ya cerró en el PR #9.
- `README.md:240-251` lista 11 archivos de test. En disco hay 22.
- `PROJECT_HISTORY_ROLLBACK.md:61` afirma que `main` y `development` están en `cbd10fa`.
  `development` está dos commits adelante.

## Por qué importa

La documentación es la puerta de entrada del proyecto. Quien la lea primero se lleva una
impresión equivocada de qué está publicado y qué no.

## Criterios de aceptación

- [ ] El README declara el último tag estable real
- [ ] El README refleja la diferencia real entre `main` y `development`
- [ ] El árbol de archivos de test está completo o se reemplaza por una referencia al directorio
- [ ] El historial de rollback no afirma sincronización donde no la hay
- [ ] No se reescribe historia: se corrigen afirmaciones obsoletas y se conserva lo que tiene
      valor de auditoría
```

---

## 4. Las 248 pruebas solo corren localmente

- **Tarea**: `QLT-001`
- **Labels sugeridos**: `tipo:debt`, `p:P2`, `modulo:project`

```markdown
## Qué pasa

La suite completa existe y está en verde, pero no se ejecuta automáticamente. No hay
`.github/`, ni `pytest.ini`, ni `pyproject.toml`. La única forma de correrla es localmente o
con `docker compose exec app python -m pytest`.

## Por qué importa

Cada cambio depende de que alguien recuerde ejecutarla. Con 17 PRs ya integrados y una
suite de 248 pruebas, la probabilidad de que una regresión pase sin que nadie lo note es
real.

## Evidencia

Ausencia de `.github/` en el repositorio. `requirements.txt` ya fija `pytest 8.3.4`, así que
la dependencia no es el obstáculo.

## Decisión pendiente

Si Franco quiere que la suite siga siendo deliberadamente local —porque el proyecto es de un
solo desarrollador y el costo de mantener un pipeline no se justifica— este Issue se cierra
con esa decisión registrada, no como tarea pendiente.

## Criterios de aceptación

- [ ] La suite completa se ejecuta automáticamente sobre cada PR hacia `development`
- [ ] El pipeline usa el aislamiento de datos integrado y no monta `./data` del host
- [ ] El resultado es visible en el PR
- [ ] El pipeline no requiere secretos
```

---

## 5. Procedimiento de backup documentado pero inseguro

- **Tarea**: `OPS-001`
- **Labels sugeridos**: `tipo:debt`, `p:P2`, `modulo:project`

```markdown
## Qué pasa

El procedimiento de backup y restore ya existe en el README. El problema no es que falte,
es que lo documentado no es seguro.

`README.md:112-121`:

    cp data/app.db backups/app-YYYYMMDD-HHMMSS.db

Copiar el archivo de SQLite mientras la aplicación escribe puede capturar un estado a medio
escribir. La forma segura es `.backup` de SQLite, o detener la app antes de copiar. El propio
README dice detener la app para el restore, pero no para el backup.

## Por qué importa

El trabajo del usuario —CVs, cartas, postulaciones— vive ahí. Un backup que parece funcionar
y en realidad no sirve es peor que no tener backup: da una confianza que no corresponde.

Además, el procedimiento no cubre el respaldo previo a una migración de esquema. El único
respaldo que existe en disco, `data/app.db.stage9.1-pre-migration.bak`, se hizo a mano y sin
procedimiento asociado.

## Evidencia

- `README.md:112-151` — procedimiento actual con `cp`
- `data/app.db.stage9.1-pre-migration.bak` — respaldo suelto, sin procedimiento

## Criterios de aceptación

- [ ] El procedimiento usa una forma de copia consistente de SQLite, no `cp` con la app escribiendo
- [ ] El procedimiento indica si la app debe estar detenida durante la copia
- [ ] La restauración se verifica ejecutándola y comprobando `PRAGMA integrity_check`
- [ ] Existe un procedimiento de respaldo previo a una migración de esquema
- [ ] La documentación de usuario refleja el procedimiento corregido
```

---

## Notas de publicación

- Los cinco se pueden publicar con las plantillas de `.github/ISSUE_TEMPLATE/`.
- Al publicar, agregar el número obtenido al campo `github_issue` de la tarea en
  `catalog.json` y correr `python3 tools/project_control.py render`.
- `REL-001` (publicar v0.10.0) **no** se propone como Issue: es una decisión de Franco, no
  trabajo faltante.
- `CLEAN-001` (limpiar el CV id 49) tampoco: es una decisión personal sobre datos ficticios,
  no una tarea del producto.
- `OPS-001` se propone **corrigiendo** el hallazgo inicial: el procedimiento de backup ya
  existe en `README.md`; lo que falta es que sea seguro y que se haya verificado.