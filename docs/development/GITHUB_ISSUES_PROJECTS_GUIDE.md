# Guía de Issues y Projects de GitHub

Cómo se registra, clasifica y concilia el trabajo de CV LaTeX Builder entre GitHub y el
catálogo interno del proyecto.

Este documento es **política escrita a mano**: no lo genera `tools/project_control.py`. El
generado son `PROJECT_STATUS.md`, `BACKLOG.md` y `ROADMAP.md`, que salen del catálogo en
`docs/development/project_control/catalog.json`.

## 1. Dos registros, un trabajo

| Registro | Para qué sirve | Quién lo mantiene | Cuándo se consulta |
| --- | --- | --- | --- |
| **Catálogo** (`catalog.json`) | Estado interno, prioridad, dependencias, aceptación | Desarrollo, en cada cambio | Al planificar o retomar trabajo |
| **GitHub Issues** | Comunicación externa, historial visible, adjuntos | Desarrollo, al reportar o publicar | Al compartir o revisar con otra persona |

**No son dos fuentes de verdad sobre el mismo dato.** El Issue es el registro *externo* del
trabajo; el catálogo es la fuente canónica *interna* de estado, prioridad y dependencias. El
catálogo apunta al Issue por número (`tasks[].github_issue`) y nunca al revés.

## 2. Convención de Issues

Formato de título:

```text
[Tipo] Descripción corta en imperativo
```

Tipos:

| Tipo | Cuándo | Ejemplo |
| --- | --- | --- |
| `bug` | Comportamiento incorrecto verificado | `[bug] El tracker borra con un token fijo` |
| `feature` | Funcionalidad pedida por Franco | `[feature] Importar Curriculum Vitae desde PDF` |
| `debt` | Deuda técnica documentada | `[debt] Derivar la versión de la documentación` |
| `docs` | Documentación desactualizada o faltante | `[docs] README declara un tag que ya no es el último` |

Reglas:

1. **Un Issue, un problema.** Si al escribirlo aparecen dos problemas distintos, son dos
   Issues.
2. **El cuerpo cita evidencia**: ruta y línea, commit, hash de PDF o salida de un comando.
   Un Issue sin evidencia no es accionable.
3. **No se crea un Issue para algo ya registrado.** Antes de crear, buscar por palabras del
   título y por el área afectada. El catálogo ya registra 19 tareas; varias tienen Issue.
4. **El Issue no se cierra por buena voluntad.** Se cierra cuando el trabajo está integrado y
   verificado, con el PR referenciado.

## 3. Labels recomendados

| Label | Significado |
| --- | --- |
| `tipo:bug`, `tipo:feature`, `tipo:debt`, `tipo:docs` | Clasificación |
| `p:P0`, `p:P1`, `p:P2`, `p:P3` | Prioridad, alineada con el catálogo |
| `modulo:cv`, `modulo:ats`, `modulo:export`, `modulo:project` | Módulo afectado |
| `estado:listo`, `estado:bloqueado` | Solo si el trabajo no puede arrancar |

**La prioridad en GitHub y la del catálogo no pueden contradecirse.** Si divergen, el
catálogo manda y el label se corrige.

## 4. Estados

GitHub no tiene estados intermedios reales; se usan labels.

| Estado GitHub | Estado del catálogo | Significado |
| --- | --- | --- |
| Open, sin `estado:*` | `backlog` | Registrado, sin decisión de arranque |
| Open, con `estado:listo` | `ready` | Aprobado y accionable sin más decisiones |
| Open, con `estado:bloqueado` | `blocked` | Espera una decisión o un insumo externo |
| Closed | `done` | Integrado y verificado |
| Closed sin PR | `cancelled` | Descartado con motivo registrado en el catálogo |

## 5. Relación entre Issue, rama, commit, PR y release

```text
Issue #14
  └─ rama feature/cv-import-pdf
       ├─ commit (Conventional Commits, referencia al issue)
       └─ PR → development   (squash merge, referencia al issue)
            └─ release: CHANGELOG_GENERAL + tag v0.10.0
```

Reglas:

- **Rama**: `feature/<area>-<resumen-corto>`. Números de Issue no empiezan las ramas.
- **Commit**: prefijo convencional (`feat`, `fix`, `docs`, `test`, `chore`, `build`, `ci`) y
  referencia al Issue cuando existe (`#14`).
- **PR**: hacia `development`, nunca hacia `main`. Cuerpo con alcance, causa raíz si es un fix,
  validaciones ejecutadas y riesgos.
- **Release**: `main` recibe el squash merge de `development` solo con autorización explícita.

El squash merge es la norma histórica de este repositorio: 17 de 17 PRs se integraron así y
`development` no tiene un solo merge commit. `git log --merges development` está vacío.

## 6. Registrar un pedido desde el móvil

Franco captura ideas fuera del escritorio. Flujo mínimo para que no se pierda:

1. Abrir GitHub → **New issue**.
2. Elegir la plantilla que corresponda.
3. Escribir **qué se quiere**, en una frase, y **por qué ahora**.
4. Marcar `tipo:feature` y `p:P2` como punto de partida.
5. Listo. No hace falta elegir módulo ni criterios de aceptación en el momento.

Después, el trabajo de clasificar en profundidad ocurre en el catálogo, no en el Issue. Un Issue
móvil puede ser deliberadamente escueto: su función es **no perder la idea**, no reemplazar la
planificación.

## 7. Mantener el backlog actualizado

Regla operativa: **si cambió el estado del trabajo, el catálogo se actualiza en el mismo commit.**

```bash
# 1. editar docs/development/project_control/catalog.json
python3 tools/project_control.py validate          # debe pasar
python3 tools/project_control.py render            # regenera los .md
python3 tools/project_control.py check             # confirma que no hay deriva
```

Los tres comandos son de solo lectura salvo `render`. `check` debe pasar en cada commit que
toque el catálogo.

Estados que se cambian con frecuencia:

| Cambio | Campo a editar |
| --- | --- |
| La tarea arrancó | `status` → `in_progress` |
| Franco aprobó | `approved` → `true` |
| Se decidió la prioridad | `priority` |
| Se detecto una dependencia | `depends_on` |
| Se quitó una dependencia | `depends_on` |
| Se cerró | `status` → `done` |

## 8. GitHub Projects

**No hay ningún Project creado.** `gh project list` falla con
`token is missing required scopes [read:project]`, así que su existencia no está confirmada y
tampoco se asume.

Si Franco decide habilitarlo, la configuración recomendada:

- Columnas: `Tarea` (texto), `Estado` (selección), `Prio` (selección), `Módulo` (selección),
  `Issue` (texto con el número).
- Una vista por módulo y una vista "P0/P1 sin bloqueantes".
- **Projects es una vista, no una fuente de verdad.** Si un campo se edita primero en Projects,
  se replica al catálogo. Si se edita en el catálogo, se replica a Projects.

## 9. Conciliar catálogo y GitHub

`tools/project_control.py` **no** consulta GitHub. La conciliación es manual y ocurre al
revisar el tablero:

1. `python3 tools/project_control.py status` — lista lo que el catálogo considera listo.
2. Revisar en GitHub si hay Issues abiertos que no figuren en el catálogo.
3. Para cada Issue nuevo que corresponda a trabajo real: agregar la tarea al catálogo con
   `github_issue` y `origin`.
4. Para cada Issue cerrado cuyo trabajo sigue `backlog`: cerrar la tarea en el catálogo.
5. Si un Issue quedó sin implementación, marcarlo `cancelled` con el motivo en `next_action`.

**Nunca editar el mismo dato en los dos lados sin decidir cuál manda antes.** Para el estado
del trabajo, manda el catálogo.

## 10. Qué NO hace esta guía

- No crea Issues automáticamente.
- No crea ni modifica GitHub Projects.
- No modifica Issues existentes.
- No cambia reglas de protección de ramas.
- No habilita GitHub Actions.

Cualquiera de esas acciones requiere autorización explícita de Franco.