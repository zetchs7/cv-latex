# ADR-0005 — Project Control Center: catálogo canónico y validación reproducible

- **Estado**: Aceptada
- **Fecha**: 2026-10-12
- **Contexto**: Etapa 10.x — gobierno del proyecto
- **Rama**: `feature/project-control-center`
- **Reemplaza**: nada
- **Relacionada**: `ADR-0001-stack-mvp.md`, `PROJECT_PLAYBOOK.md` §17, `AGENTS.md`

## Contexto

cv-latex acumula 16 documentos en `docs/development/`, 4 ADR previos y 25 lecciones
aprendidas. La cobertura documental es buena, pero **no existe una fuente única que responda
"¿en qué está el proyecto?"**. El estado real está disperso entre `MODULE_INDEX.md`,
`DEVELOPMENT_LOG.md`, issues de GitHub y memoria de sesiones.

Eso ya produjo tres fallos concretos y observados:

1. Reconstruir el estado del proyecto en una sesión nueva exige leer mucho y adivinar.
2. No existe backlog con identificadores estables, prioridad, dependencias y criterios de
   aceptación verificables.
3. Nada detecta que la documentación haya quedado obsoleta respecto del código.

La app ya tiene 248 pruebas verdes y un aislamiento de datos confiable, así que la
infraestructura de desarrollo está en condiciones de sostener un sistema de gobierno propio.

## Decisión

Implementar un **Project Control Center** compuesto por:

1. **Un catálogo JSON canónico** — `docs/development/project_control/catalog.json` — que es la
   única fuente de verdad del estado de cada tarea y del estado de cada módulo.
2. **Una herramienta de validación** — `tools/project_control.py` — escrita solo con Python
   standard library, sin red y sin dependencia de GitHub.
3. **Markdown derivado** — `docs/development/PROJECT_STATUS.md`, `BACKLOG.md` y `ROADMAP.md` se
   generan desde el catálogo de forma determinista.
4. **Documentación de política escrita a mano** — `docs/development/GITHUB_ISSUES_PROJECTS_GUIDE.md`
   no se genera: describe convenciones, no estado.

### Esquema del catálogo

```jsonc
{
  "meta":    { "schema_version": 1, "generated_by": "tools/project_control.py" },
  "project": { "name", "stable_version", "main_branch", "development_branch",
               "last_verified_on", "last_verification_evidence" },
  "modules": [ { "id", "name", "routes", "state", "in_development",
                 "in_main", "verified_by", "evidence" } ],
  "risks":   [ { "id", "title", "severity", "status", "mitigation", "evidence" } ],
  "tasks":   [ { "id", "title", "description", "origin", "priority", "status",
                 "module", "depends_on", "acceptance", "evidence",
                 "github_issue", "next_action", "approved" } ]
}
```

Decisiones de esquema con consecuencias:

- **`tasks[].approved` es obligatorio.** Distingue un requisito acordado por Franco de una
  recomendación de ingeniería. Un backlog donde todo aparece "aprobado" miente.
- **`tasks[].origin` distingue la procedencia**: `franco`, `defect`, `engineering`, `debt`.
  Impide que una idea de IA se presente como pedido.
- **`modules[]` separa cuatro estados**: implementado, probado, integrado en `development`,
  publicado en `main`. Son cuatro hechos distintos y confundirlos es la causa raíz del
  malentendido más frecuente de este repositorio.
- **`tasks[].acceptance` es una lista no vacía.** Una tarea sin criterio verificable no es una
  tarea.
- **`depends_on` referencia `tasks[].id`.** La herramienta detecta referencias rotas y ciclos.

### Verbos de la herramienta

| Verbo | Efecto | Escribe |
| --- | --- | --- |
| `validate` | Valida estructura, IDs, prioridades, estados, dependencias, ciclos, aceptación | no |
| `status` | Resumen textual reproducible del estado del proyecto | no |
| `render` | Escribe el Markdown derivado desde el catálogo | **sí** |
| `check` | Compara el Markdown derivado contra el catálogo y falla si divergen | **no** |

`render` es el único que escribe. `check` es de solo lectura por diseño: es el comando que se
ejecuta en pre-commit y en revisión, y no puede tener efecto lateral.

### Determinismo

`render` produce siempre la misma salida para el mismo catálogo. No incluye timestamps de
ejecución ni ordena por tiempo de ejecución: todo se ordena por identificador. Sin esa propiedad,
`check` no podría distinguir "el Markdown quedó viejo" de "el render no es determinista".

## Alternativas consideradas

### Alternativa A — Markdown como fuente canónica

- **A favor**: cero herramientas, editables a mano, formato conocido.
- **En contra**: no hay forma de validar referencias rotas, IDs duplicados ni ciclos sin
  parsear Markdown, que es ambiguo. La validación quedaría en heuristics frágiles.
- **Rechazada**: el requisito central es *detectar inconsistencias*, y Markdown no lo soporta.

### Alternativa B — GitHub Issues como fuente canónica

- **A favor**: ya existe, es colaborativo, tiene historial.
- **En contra**: contradice "sin conexión permanente con GitHub". Validar el backlog requeriría
  red y credenciales, con lo que `check` dejaría de ser ejecutable sin red y dejaría de ser
  reproducible. Los issues son el registro externo de trabajo, no el catálogo interno.
- **Rechazada como canónica**; se conserva como destino opcional, referenciado por
  `tasks[].github_issue`.

### Alternativa C — SQLite adicional

- **A favor**: consultas y relaciones cómodas.
- **En contra**: agrega un artefacto binario que no se revisa en diffs, un segundo esquema que
  migrar y un archivo que puede desincronizarse del Git. El dato sería menos auditable, que es
  justo lo contrario de lo buscado.
- **Rechazada**: la contradicción es explícita en el diseño.

### Alternativa D — Adoptar un framework de especificación completo (SDD)

- **A favor**: estructura probada.
- **En contra**: costo de mantenimiento alto para un proyecto de un solo desarrollador; obliga a
  aprender un formalism para un problema que es de inventario. Introduce ceremonial donde la
  restricción real es "que alguien pueda entender el estado en cinco minutos".
- **Rechazada**: el diseño debe reducir carga cognitiva, no aumentarla.

## Consecuencias

### Positivas

- El estado del proyecto se reconstruye leyendo un archivo.
- La deriva entre documentación y realidad se detecta con un comando, no a los meses.
- `check` es ejecutable en cualquier entorno sin red ni credenciales.
- Los IDs estables permiten referenciar tareas desde ADRs, issues y commits.

### Negativas

- Dos archivos que mantener en vez de uno: el catálogo y el Markdown derivado. Se acepta a
  cambio de que la deriva sea detectable; si no fuera detectable, sería un problema.
- Editar el Markdown a mano se pierde en el siguiente `render`. Por eso los documentos
  generados llevan un encabezado que lo advierte.
- JSON no admite comentarios: la intención de cada campo tiene que vivir en el ADR y en el
  esquema documentado.

### Riesgo de mantenimiento

Bajo. La herramienta tiene un solo archivo, cero dependencias y cuatro verbos. El costo real
recae en mantener el catálogo actualizado, que es trabajo de fondo y no de código.

## Criterios de reversión

Si el sistema no se usa o se vuelve un estorbo, basta con borrar `tools/project_control.py`, el
directorio `docs/development/project_control/` y los cuatro documentos. No hay dependencia desde
la aplicación: `tools/` no se importa en `app/` y el catálogo no lo lee ningún módulo en
runtime. La reversión es una eliminación de archivos.