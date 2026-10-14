# Entornos y datos: MODO REAL y MODO PRUEBAS

Etapa 11.0. Rama `feature/real-test-workspaces` desde `development` `ea4c979`.
Documento de arquitectura, procedimiento de migracion, riesgos y checklist humano.

---

## 1. Problema

La aplicacion vive con una sola base SQLite. Franco clasifico **todos** los registros
actuales como Dummy Data, pero no hay forma de separarlos de la informacion real que
va a cargar despues. Sin separacion, cualquier ensayo de exportacion, cualquier
generacion de datos y cualquier borrado toca la base unica.

## 2. Arquitectura elegida

### 2.1 Separacion por prefijo de URL

`/real/...` y `/test/...` son prefijos. `WorkspaceMiddleware` los detecta, fija
`scope["root_path"]` y registra el entorno en un `ContextVar`.

**Por que no una bandera global de entorno.** Un flag de proceso cambia el valor que
ven todas las peticiones en vuelo. Dos requests simultaneas escribirian en la base
equivocada y nadie lo veria hasta mucho despues.

**Por que no una cookie.** Las cookies se comparten entre pestanas. Dos pestanas
abiertas en entornos distintos se pisarian sin aviso.

**Por que `root_path` y no recortar el path a mano.** `root_path` es el mecanismo con
el que ASGI describe "esta aplicacion esta montada bajo un prefijo". Usarlo en vez de
reimplementarlo tiene tres ventajas concretas:

- `url_for` devuelve el prefijo solo, asi que ningun enlace, formulario ni recurso
  estatico sale del entorno.
- Las redirecciones internas de Starlette (barra final, rutas no encontradas) lo
  conservan sin codigo adicional.
- El enrutado usa `path - root_path` (`starlette.routing.get_route_path`), asi que
  las 127 llamadas a `url_for` de las plantillas no se tocaron.

El entorno **nunca** se lee del cuerpo del formulario ni de un query parameter. Solo
de la ruta. Un POST a `/real/config/workspaces/generate` pidiendo `cvs=5` se rechaza.

### 2.2 Almacenamiento

```
<data_root>/app.db            base historica, SIN migrar todavia
<data_root>/.environments-migrated   marcador que retira la vista sin prefijo
<data_root>/real/app.db       MODO REAL
<data_root>/real/exports/
<data_root>/real/import-drafts/
<data_root>/real/documentation-build/
<data_root>/test/app.db       MODO PRUEBAS
<data_root>/test/exports/
<data_root>/test/import-drafts/
<data_root>/test/documentation-build/
```

`get_data_dir()` devuelve `<APP_DATA_DIR>/<entorno>`. **Sin entorno declarado devuelve
la raiz tal cual**, que es donde vive la base historica. Ese detalle no es un
descuido: mover la base habria roto todos los modulos actuales y toda la suite
existente por una decision de arquitectura, no por una necesidad.

**La vista sin prefijo es exclusivamente transitoria.** Existe para no dejar la
aplicacion inutilizable antes de migrar. Cuando `execute_migration` termina, saque la
base del camino vivo (la renombra a `app.db.retirado-<hex>`, no la borra), escribe
`.environments-migrated` y a partir de ahi:

- el arranque **no** inicializa una base nueva en la raiz, asi que ningun boot
  fabrica un tercer espacio de trabajo;
- las rutas sin prefijo redirigen a MODO REAL (303), salvo `/health` y `/static/`,
  que no leen ni escriben datos y quedan exentas para no romper el healthcheck del
  contenedor.

Quedan **solo dos espacios operativos: REAL y PRUEBAS**.

`environment_root()` resuelve con `resolve()` y exige que el resultado quede dentro de
la raiz de datos. Un `import-drafts` que sea enlace simbolico a otro arbol queda fuera
y se rechaza, en vez de seguirse.

### 2.3 Inicializacion

El arranque de la aplicacion solo inicializa la base legacy: no puede saber de
antemano en que entorno va a trabajar nadie. `ensure_environment_ready()` crea el
directorio y las tablas del entorno en la primera peticion que lo usa, memoizado por
entorno. Sin eso, la primera visita a `/test/` moria con `unable to open database
file` antes de llegar a ninguna ruta.

Ademas `generate_dummy_data`, `delete_selected`, `purge_environment` y
`execute_migration` envuelven **toda** su ejecucion en `in_environment(environment)`.
Aceptan el entorno explicito y lo fijan igual: si una funcion acepta un entorno pero
despues depende del ambiental, cualquier llamada fuera de una peticion (tarea en
background, script, test unitario) escribiria en la base equivocada.

### 2.4 Aislamiento verificado

| Requisito | Como se cumple |
| --- | --- |
| Bases distintas | `<root>/real/app.db` y `<root>/test/app.db` |
| Mismo ID no se confunde | cada base tiene su propio `sqlite_sequence` |
| Sin fallback silencioso | prefijo desconocido → 404; no hay directorio de tercer entorno |
| Path traversal | `resolve()` + `is_relative_to` en toda ruta resuelta |
| Symlinks | `_safe_write` rechaza `is_symlink()` y cualquier ruta fuera del entorno |
| Dos pestanas | el estado esta en la URL, no en la cookie |

## 3. Interfaz

- **`Configuracion`** en el sidebar, siempre visible.
- **`Configuracion → Entornos y datos`**: dos tarjetas, MODO REAL y MODO PRUEBAS, con
  el entorno activo marcado.
- **Banner persistente** en todas las paginas: `MODO PRUEBAS` con icono de tubo de
  ensayo, `MODO REAL` con candado. Solo color no alcanza, asi que hay texto e icono.
  En dark mode los colores se redefinen para mantener contraste.
- **Sin entorno declarado** (rutas historicas) el banner dice `DATOS SIN CLASIFICAR`
  si hay base historica pendiente de migrar.

## 4. Generador de Dummy Data

- Cantidades independientes de CVs, cartas y postulaciones.
- Tope `MAX_GENERATE_PER_KIND = 50` por operacion. Se rechaza con mensaje que nombra
  el maximo; nunca se trunca en silencio.
- Semilla determinista opcional para reproducir un escenario.
- Los CVs van por `create_structured_cv`, asi que salen validados contra el schema 2
  y son indistinguibles de los que crea una persona.
- Nombres, empresas, correos y telefonos ficticios con dominios `.invalid`
  (reservados por RFC 2606): no pueden resolver a una persona real.
- No consulta servicios externos ni usa IA.
- Generar en MODO REAL esta prohibido (`dummy_real_forbidden`).

## 5. Borrado selectivo

Dos pasos, no uno:

1. `POST .../delete/preview` muestra la lista exacta, los totales por tipo y las
   dependencias.
2. `POST .../delete/execute` pide la frase `ELIMINAR <N> DE PRUEBAS`, escrita por la
   persona y validada en el servidor.

**La seleccion se revalida en el momento de ejecutar**, contra la base real de ese
instante: una previsualizacion vieja no sirve si los registros cambiaron entre las dos
pantallas.

Si un CV o una carta seleccionados estan vinculados a postulaciones que **no** estan
seleccionadas, no se borra nada. Se muestran las dependencias y se ofrece volver. No
hay desvinculacion automatica ni borrado en cascada.

El borrado es **fisico** (`hard_delete_*`), no soft delete. Los `hard_delete_*` son
funciones nuevas en los repositorios: no comparten camino con el borrado normal que ve
el usuario, que sigue siendo `soft_delete_*`.

Los exportes se borran solo cuando el nombre corresponde a un CV borrado; los ajenos
quedan.

## 6. Vaciado completo

`VACIAR PRUEBAS` borra la base (con `-wal`, `-shm` y `-journal`), los exportes, los
borradores y la documentacion compilada del entorno. Deja el entorno vacio y funcional:
se puede generar de nuevo inmediatamente.

**No genera backup de lo eliminado.** Es deliberado: el requisito pide explicitamente
que no se respalde lo que el usuario decidio borrar. Eso se distingue de la
**migracion**, que conserva la base historica como `app.db.retirado-<hex>` en vez de
borrarla: alla nada se pierde, aqui se borra porque el usuario lo pidio.

## 7. Migracion

### 7.1 Diagnostico (dry-run)

`GET /config/workspaces/migration` corre `plan_migration()`. Inventaria la base
historica, comprueba integridad SQLite, detecta referencias rotas y muestra las
acciones previstas. **No modifica nada**: un test lo afirma comparando el listado del
directorio antes y despues.

### 7.2 Condiciones de bloqueo

El plan pasa a `blocked` si:

- alguna de las tres tablas no se puede leer;
- el destino (`real` o `test`) ya tiene una base — **nunca se sobrescribe**;
- `exports` o `import-drafts` existen pero no son directorios.

### 7.3 Ejecucion

1. Exige la frase `MIGRAR` escrita en el servidor.
2. Vuelve a correr el plan: si dejo de estar `ready`, se aborta.
3. Genera un checkpoint con la **API de backup de SQLite** (`Connection.backup`), no
   con una copia de archivo, que podria tomar la base a mitad de una escritura.
4. `os.replace` del checkpoint a `test/app.db`, y de `exports` e `import-drafts` a su
   lugar dentro de `test/`.
5. **Retira la vista historica**: renombra `data/app.db` a
   `data/app.db.retirado-<hex>` y escribe `data/.environments-migrated`.
6. Ante cualquier `OSError`, revierte lo ya movido en orden inverso y lanza un error
   controlado. El mensaje distingue "se revirtio" de "el rollback quedo incompleto
   en ...": decir lo primero cuando no fue asi seria mentir.

**La base historica NO se borra.** Sale del camino vivo con otro nombre, y ese archivo
es la fuente del rollback. Ojo con una confusion facil: el checkpoint generado en el
paso 3 **no sobrevive como `.bak`**, porque es el que acaba siendo `test/app.db`. El
artefacto que conserva el contenido historico es `app.db.retirado-<hex>`.

Sin el paso 5 quedarian tres bases vivas a la vez y las rutas sin prefijo seguirian
sirviendo datos historicos, que es exactamente lo que el requisito prohibe.

### 7.4 Rollback

Si la migracion fallo y se revirtio: no hay nada que hacer, el estado es el original.
Si la migracion **completo** y Franco quiere volver atras:

```bash
# 1. parar la app
docker compose stop app

# 2. devolver la base historica al camino vivo (renombrar, NO copiar)
mv data/app.db.retirado-* data/app.db

# 3. retirar el marcador de retiro
rm -f data/.environments-migrated

# 4. retirar los entornos creados
rm -rf data/real data/test

# 5. arrancar de nuevo
docker compose up -d app
```

**El paso 3 no es un detalle.** `legacy_migrated()` exige las DOS condiciones a la vez:
marcador presente **y** sin `app.db` en la raiz. La segunda condicion hace que
restaurar la base rehabilitue la vista historica por si sola, pero dejar el marcador ahi
deja la app diciendo "ya esta migrado" con una base sin clasificar al lado. Sacarlo deja
el estado idéntico al anterior a migrar.

Si el objetivo es volver atras **manteniendo** los entornos, basta con los pasos 1-3 y
5: `data/real` y `data/test` quedarian como archivos inertes que ninguna ruta alcanza
hasta que exista un marcador de migracion nuevo.

`data/app.db.retirado-<hex>` es la **unica** copia del contenido historico. No borrarla
antes de confirmar a mano que `data/test/app.db` quedo bien.

### 7.5 Reintento

Un segundo intento sobre un destino ya ocupado devuelve `migration_blocked` sin tocar
nada. No hay estado intermedio que herede la primera corrida.

## 8. Validacion ejecutada

| Verificacion | Resultado |
| --- | --- |
| Suite Python completa | **533 passed** (465 base + 68 nuevos) |
| Pruebas de entornos | **68 passed** |
| `python -m compileall -q app tests` | exit 0 |
| `git -c core.whitespace=cr-at-eol diff --check` | exit 0 |
| `tools/project_control.py validate` | catalogo valido, sin errores ni advertencias |
| `tools/project_control.py check` | catalogo y 3 documentos generados en sync |
| `node --test tests/test_structured_cv_editor_js.js` | 1 passed, 0 failed |
| Contenedor real y `data/` | **sin modificar** |

### Aislamiento demostrado

Los 68 tests de `tests/test_workspaces.py` cubren, sobre directorios temporales:

- bases distintas y mismo ID sin confusion;
- crear, editar, borrar y vaciar en PRUEBAS sin alterar REAL;
- exportes y borradores separados;
- dos hilos concurrentes escribiendo y leyendo sin cruzarse;
- dos `TestClient` abiertos a la vez sin cambios cruzados;
- prefijo desconocido → 404, sin directorio de tercer entorno;
- entorno manipulado en el cuerpo del formulario → rechazado;
- generacion con cantidades invalidas, excesivas y con semilla;
- borrado individual, multiple, fisico y con archivos asociados;
- dependencias detectadas sin borrado en silencio;
- fallo a mitad de borrado reportado, nunca presentado como exito;
- enlace simbolico fuera del entorno: rechazado, el archivo ajeno sobrevive;
- CSRF invalido y frase de confirmacion invalida rechazados;
- migracion: dry-run sin mutaciones, bloqueo, rollback, reintento y arranque antes
  y despues;
- **tras migrar no queda un tercer espacio de trabajo**: sin base en la raiz, marcador
  presente y un unico archivo retirado todavia legible;
- rutas sin prefijo redirigen a MODO REAL sin entregar datos historicos, y un POST sin
  prefijo no escribe nada (303 convierte el POST en GET);
- el arranque despues de migrar no recrea la base legacy;
- antes de migrar la vista historica sigue funcionando igual: el caracter es
  transitorio, no un cambio de comportamiento;
- `/health` y `/static` exentos de la retiro;
- restaurar la base rehabilita la vista historica por si sola;
- el diagnostico post-migracion dice `migrated`, distinto de `not_pending`;
- **barrera estructural**: las 6 rutas POST del modulo exigen CSRF, parametrizadas y
  con cuerpo completo, verificando ademas que no hubo mutacion;
- generar, previsualizar borrado, elegir entorno y migrar con CSRF invalido: rechazados
  y sin efecto sobre los datos;
- borrar seleccion, vaciar, generar y previsualizar via `/real/...`: rechazados con REAL
  intacto.

Ademas `tests/conftest.py` compara en el cierre de sesion el manifiesto recursivo de
`data/` y de `app/static/docs/`; si algo cambio, la corrida completa sale en error.

## 9. Limitaciones

- **La migracion NO se ejecuto.** Solo existe y esta probada sobre fixtures aislados.
  Requiere autorizacion explicita de Franco.
- **No hay validacion visual en navegador.** Solo se verifico HTTP, `healthcheck` y
  que el trafico quede en loopback. La revision visual la hace Franco.
- **SEC-001 sigue abierto.** El token CSRF de esta feature protege **solo** los
  formularios nuevos. El resto de la aplicacion sigue sin proteccion CSRF general y
  sin `TrustedHost`; eso es una etapa separada.
- **`MAX_STORED_DRAFT_BYTES` no se consulta al escribir** y la ventana entre
  `create_structured_cv` y `delete_draft` no es idempotente: son los dos P2 ya
  aceptados como deuda en el merge de #20, no se tocaron aca.
- **La vista sin prefijo es transitoria, solo antes de migrar.** Mientras no se
  ejecute la migracion, las rutas sin prefijo operan sobre la base historica para no
  dejar la aplicacion inutilizable: hay una tercera vista de datos, y es a proposito.
  **Despues de migrar esa vista queda retirada** (base renombrada + marcador +
  redireccion a MODO REAL) y solo REAL y PRUEBAS son operativos. El marcador se escribe
  unicamente con una migracion exitosa, asi que una migracion a medias jamas retira
  la vista.

## 10. Riesgos

| Riesgo | Mitigacion | Estado |
| --- | --- | --- |
| Escritura cruzada entre entornos | entorno en la ruta + `ContextVar` + `in_environment` en toda operacion mutante | cubierto por tests |
| Path traversal / symlink | `resolve()` + `is_relative_to` + rechazo de `is_symlink()` | cubierto por test |
| Borrado accidental | frase exacta validada en servidor + CSRF + revalidacion en ejecucion | cubierto por test |
| Perdida silenciosa a mitad de operacion | `pending` no vacio impide reportar exito | cubierto por test |
| Sobreescritura durante la migracion | destino ocupado → `blocked`, sin sobrescribir | cubierto por test |
| Tercer espacio de trabajo tras migrar | base renombrada fuera del camino vivo + marcador + arranque sin inicializar la raiz + redireccion a REAL | cubierto por test |
| Rollback que deja estado mixto | `legacy_migrated` exige marcador Y sin base en la raiz: restaurar la base rehabilita la vista sin tocar el marcador | cubierto por test |
| Consumo de recursos | tope de 50 por tipo y de 500 ids por seleccion | cubierto por test |
| Contenedor de uso normal | no se recreo ni se detuvo | verificado |

## 11. Archivos nuevos y modificados

**Nuevos**

- `app/environments.py`
- `app/workspace_middleware.py`
- `app/routes/workspaces.py`
- `app/services/workspace_service.py`
- `app/templates/workspaces/settings.html`
- `app/templates/workspaces/manage.html`
- `app/templates/workspaces/confirm_delete.html`
- `app/templates/workspaces/confirm_purge.html`
- `app/templates/workspaces/migration.html`
- `tests/test_workspaces.py`
- `docs/development/REAL_TEST_WORKSPACES.md`

**Modificados**

- `app/database.py` — `get_data_dir()` resuelve por entorno
- `app/main.py` — middleware y router de configuracion
- `app/template_utils.py` — context processor con entorno y `workspace_path`
- `app/routes/dashboard.py` — "Entornos y datos" reemplaza al placeholder
- `app/repositories/cv_repository.py` — `hard_delete_cv`
- `app/repositories/cover_letter_repository.py` — `hard_delete_cover_letter`
- `app/repositories/application_repository.py` — `hard_delete_application`
- `app/templates/layout.html` — banner de entorno y enlace de configuracion
- `app/static/css/app.css` — estilos del banner y las tarjetas
- `docs/development/SECURITY_HARDENING_PROPOSAL.md` — matriz de limites: 17 a 23 rutas

## 12. Checklist humano para Franco

Nada de esto se ejecuta sin su autorizacion. El orden importa.

**Antes de migrar**

- [ ] `git status` limpio en `development` y `data/` con copia de seguridad hecha a mano.
- [ ] Abrir `http://127.0.0.1:8000/config/workspaces` y leer el diagnostico de migracion.
- [ ] Confirmar que las cantidades del diagnostico coinciden con lo esperado
      (49 CVs de los cuales 11 borrados logicos, 10 cartas de las cuales 3 borradas
      lógicamente, 6 postulaciones de las cuales 3 borradas lógicamente).
- [ ] Revisar que el bloqueo no aparezca. Si aparece, no migrar.

**Para migrar**

- [ ] Autorizar la migracion de forma explicita.
- [ ] Verificar que `data/app.db.retirado-*` existe, es SQLite legible y contiene los
      registros esperados. Es la unica copia del contenido historico.
- [ ] Comprobar en el navegador que `MODO PRUEBAS` muestra los registros heredados.
- [ ] Comprobar que `MODO REAL` arranca vacio.

**Despues**

- [ ] Generar datos de prueba y confirmar que se ven en `MODO PRUEBAS` solamente.
- [ ] Borrar una seleccion y verificar que `MODO REAL` no cambio.
- [ ] Vaciar `MODO PRUEBAS` y verificar que la app sigue funcionando.
- [ ] Comprobar que `data/.environments-migrated` existe y que una URL sin prefijo
      (por ejemplo `http://127.0.0.1:8000/cvs/`) redirige a MODO REAL.
- [ ] Aprobar o no la eliminacion definitiva de `data/app.db.retirado-*`. Hacerlo solo
      cuando `data/test/app.db` este confirmada a mano. **No borrar
      `.environments-migrated` en esta etapa**: eso rehabilitaria la vista historica
      y volveria a habilitar un tercer espacio de trabajo.
