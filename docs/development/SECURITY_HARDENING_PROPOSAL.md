# Propuesta de endurecimiento de seguridad para producción

**Estado**: propuesta para aprobación. **Nada de esto está implementado.**
**Fecha**: 2026-10-12
**Origen**: investigación de solo lectura, con evidencia citada por archivo y línea
**Relacionada**: `SEC-001`, `SEC-002`, `SEC-003`, `SEC-005` del catálogo; `OPS-001`

Esta propuesta sale de auditar la app real, no de una checklist. Lo que sigue está
verificado con comandos y lecturas concretas. No hay ningún cambio de código asociado.

## 1. Modelo de amenazas

La aplicación está diseñada para **uso local y sin autenticación**. Eso es una decisión de
diseño válida. Lo que la hace insegura no es la falta de login, sino que **nada verifica el
origen de las peticiones**: la app acepta cualquier `Host`, cualquier `Origin`, y ejecuta
cualquier POST que llegue.

Actores considerados:

| Actor | Qué puede hacer hoy |
| --- | --- |
| Usuario legítimo en localhost | Uso normal |
| Cualquier sitio web que el usuario visite mientras la app corre | Crear y modificar CVs, cartas y postulaciones |
| Un atacante con DNS propio y TTL bajo | Leer todos los CVs y exportarlos |
| Otro usuario del mismo host | Leer la base (según permisos) |
| Alguien con acceso a cambiar `.env` | Exponer la app a toda la LAN sin auth |

Lo que explícitamente **no** se considera amenaza aquí: robo de credenciales (no hay),
inyección SQL (no hay queries concatenadas), y path traversal en subidas (verificado ausente).

## 2. Hallazgos verificados

### 2.1 Request forgery sobre 14 endpoints POST — **Severidad alta, explotable hoy**

La app registra **cero middleware**: `app/main.py:26-39` solo crea la instancia e incluye 6
routers. No hay `CORSMiddleware`, no hay `TrustedHostMiddleware`, no hay CSRF.

Catorce rutas escriben, todas POST:

```
POST /applications/            POST /cvs/                      POST /cvs/{id}/edit
POST /applications/{id}/edit   POST /cvs/new/structured       POST /cvs/{id}/structured-edit
POST /applications/{id}/delete POST /cvs/import/json          POST /cvs/{id}/duplicate
POST /cover-letters/           POST /cvs/{id}/edit             POST /cvs/{id}/delete
POST /cover-letters/{id}/edit  POST /cover-letters/{id}/delete POST /cover-letters/{id}/edit
```

**Mecanismo.** Un `<form method="post" enctype="application/x-www-form-urlencoded">` en un
sitio atacante apuntando a `http://127.0.0.1:8000/cvs/` es una *simple request*: **no dispara
preflight**, el navegador la envía y la app la ejecuta.

Hay que ser preciso aquí, porque es fácil confundirse: **la ausencia de CORS es irrelevante.**
CORS controla si se puede *leer* una respuesta cruzada, no si la petición se *envía*. Y como
no hay cookies ni sesión, el "CSRF clásico" tampoco aplica. Lo que hay es **request forgery
sobre un servicio local sin verificación de origen**.

El atacante no necesita leer nada: los IDs son enteros secuenciales
(`app/database.py:195`), así que puede iterar `POST /cvs/1/edit`, `/cvs/2/edit`, ... y
sobrescribir CVs a ciegas.

**Mitigación parcial existente:** borrar exige coincidencia exacta del título
(`app/routes/cvs.py:458-459`), que un atacante ciego no conoce. Destrucción difícil;
**corrupción de contenido fácil**.

### 2.2 DNS rebinding — **Severidad media, explotable hoy**

Sin `TrustedHostMiddleware`, cualquier `Host` pasa.

**Mecanismo.** El atacante controla el DNS de su dominio con TTL bajo. La víctima visita el
sitio. El JavaScript resuelve primero al servidor real (para servir el payload) y luego
re-bindea el dominio a `127.0.0.1`. El navegador de la víctima conecta desde su propia máquina
a su propia loopback.

**El bind `127.0.0.1` no protege.** Este es el punto que casi siempre se afirma al revés: la
restricción de interfaz controla desde dónde se aceptan conexiones, no peticiones que el
propio navegador del usuario origina localmente.

La Same-Origin Policy tampoco ayuda, porque el `origin` sigue siendo el dominio del atacante
—que ahora resuelve a loopback— así que el JavaScript **sí puede leer las respuestas**:
exfiltración completa de CVs, cartas y exportaciones.

`TrustedHostMiddleware` corta exactamente aquí: validaría `Host: attacker.com` y fallaría.

### 2.3 Backup potencialmente inconsistente — **Severidad media**

El procedimiento de *restore* es consistente porque exige detener la app
(`README.md:161-171`, `docs/user/WEB_USAGE_MANUAL.md:147-153`). El de *backup* no:
`README.md:149` hace `cp data/app.db backups/...` **con la app corriendo**, y SQLite en journal
mode default puede producir una copia a medio escribir.

No es un problema de seguridad directa; es un problema de que el backup puede no funcionar el
día que se necesita.

### 2.4 `APP_HOST_BIND=0.0.0.0` — **Severidad alta si se cambia**

`docker-compose.yml:13` publica `"${APP_HOST_BIND:-127.0.0.1}:8000:8000"`. Cambiar esa
variable y recrear expone la app a toda la LAN: lectura y escritura total sin autenticación.
Nada advierte que se hizo.

### 2.5 Sin cap de tamaño de request — **Severidad baja**

No hay límite de body. Un POST urlencoded enorme se parsea completo en memoria antes de la
validación por campo. El import JSON sí corta a ~520 KB en streaming
(`app/services/export_service.py:32-33`).

**Corrección respecto de una versión anterior de este documento**, que proponía un cap global de
2 MiB: eso es **incompatible con el importador de PDF**, que autoriza 10 MiB
(`MAX_PDF_BYTES`, rama `feature/pdf-cv-import`). Un cap único obligaría a elegir entre rechazar
PDFs legítimos o aceptar cuerpos enormes en todas las rutas. La política correcta es **por
endpoint**, no global: cada ruta declara el máximo que realmente necesita, y las rutas de formulario
heredan un tope pequeño porque sus campos están acotados.

### 2.6 `pdflatex` sin `-no-shell-escape` — **Severidad baja**

`app/services/pdf_service.py:79-85` invoca `pdflatex` sin el flag. El control real es el
sanitizador (`app/validations/latex_sanitizer.py:1-12`, que escapa `\ & % $ # _ { } ~ ^`), y TeX
Live moderno ya restringe shell-escape por defecto. Es defensa en profundidad, no un vector
confirmado.

## 3. Verificado como **ausente**

Esto importa tanto como la lista de arriba, para no gastar esfuerzo donde no hace falta:

- **Sin path traversal** en subidas ni exportaciones: los nombres se construyen server-side con
  `sanitize_filename_component` (whitelist `[a-zA-Z0-9._-]`, `app/services/file_naming.py:7-8`)
  y las rutas de descarga derivan de registros de base, no de input.
- **Sin secretos en el repositorio**: sin `api_key`/`secret`/`password`/`token` en `app/`; el
  único `.env` es `.env.example` con defaults no sensibles.
- **Sin root en el contenedor**: el `Dockerfile` crea `appuser` y termina con `USER appuser`
  (`:23`, `:34`).
- **Sin fuga de trazas al usuario**: los 500 devuelven texto genérico; los mensajes visibles son
  strings propios, y el detalle técnico va al logger.
- **Sin logging de datos personales**: los logs registran IDs, no nombres ni emails.
- `data/` excluido en `.gitignore` y `.dockerignore` (verificado con `git check-ignore`).

## 4. Arquitectura recomendada

**Para el modelo de uso actual (localhost, un solo usuario)**, el objetivo no es convertir la
app en un sistema con login. Es cerrar las dos puertas que permiten que **un tercero** la
opere sin estar presente.

```
Peticion entrante
  └─ TrustedHostMiddleware          → rechaza Host no permitido   (cierra 2.2)
       └─ cap de tamanio de request → antes de parsear           (cierra 2.5)
            └─ token CSRF por sesion→ valida todo POST           (cierra 2.1)
                 └─ rutas actuales, sin cambios
```

El token CSRF **no requiere login**: se emite en una cookie de sesión opaca al servir el
primer GET, se incrusta en cada formulario, y se compara en el POST. Un sitio atacante no
puede leer la cookie ni predecir el token, así que la simple request se vuelve rechazable.

Esto preserva el modelo de uso: sin usuario, sin contraseña, sin base de sesiones.

## 5. Alternativas consideradas

| Alternativa | Por qué no |
| --- | --- |
| Validar `Origin`/`Referer` a mano | Funciona, pero es frágil: hay que acordarse de cada ruta nueva y `Referer` puede omitirse. Es una defensa que se deteriora sola. |
| Autenticación con usuario y contraseña | Correcta si la app va a exponerse, pero contradice el diseño local. Es la Opción 3, no un parche. |
| Solo CORS | **Inútil aquí.** CORS no bloquea el envío, solo la lectura. Sería una solución que parece resolver el problema y no lo toca. |
| Bind único en loopback y nada más | Ya es el default y no cubre ni el forgery ni el rebinding. |

## 6. Cambios necesarios

1. `app/main.py`: registrar `TrustedHostMiddleware` con una lista permitida derivada de
   `APP_ALLOWED_HOSTS` (default `localhost,127.0.0.1`).
2. **Cap de tamaño por endpoint, no global.** Tabla de máximos por ruta, aplicada antes del
   parseo completo del cuerpo. Ver §5.2.
2. Sesión opaca: emitir una cookie de sesión en el primer GET y generar un token CSRF por
   sesión. Sin base de datos nueva: el token vive en memoria del proceso o en una cookie
   firmada.
3. Un helper de plantilla que inyecte el campo oculto, aplicado a las 8 plantillas con
   `method="post"`. Sin él, el día que se agregue un formulario se olvidará el token.
4. Advertencia visible al arrancar si `APP_HOST_BIND` no es loopback.
5. `OPS-001`/`SEC-003`: cambiar el backup documentado a `sqlite3 data/app.db ".backup"`.
6. Opcional y barato: `-no-shell-escape` en `pdflatex`.

### 5.1 Matriz de límites por ruta

La tabla es la política. Agregar una ruta sin entrada aquí es un defecto, igual que olvidar el
token CSRF.

| Ruta | Método | Cap | Motivo |
| --- | --- | --- | --- |
| `/cvs/` y `/cvs/{id}/edit` | POST | 256 KB | Formulario con campos acotados por `cv_validations` |
| `/cvs/new/structured` y `/cvs/{id}/structured-edit` | POST | 1 MiB | Payload estructurado, tope de 512 KB + sobre |
| `/cvs/import/json` | POST | 1 MiB | Límite real de ~520 KB |
| `/cvs/import/pdf` | POST | **10 MiB + 64 KB** | Límite autorizado para PDFs |
| `/cover-letters/*` | POST | 256 KB | Igual que CVs |
| `/applications/*` | POST | 256 KB | Igual que CVs |
| Cualquier ruta GET | — | 8 KB | No deberían llevar cuerpo |

El sobre de 64 KB del PDF es para el multipart. **El cap se aplica antes de leer el cuerpo**, con
un stream que corta al alcanzarlo: un archivo de 500 MB debe rechazarse con 413 sin haberse leído.

### 5.2 Por qué no un cap global

Un único valor obliga a elegir entre dos males: 2 MiB rechaza PDFs legítimos de 6 MiB, y 10 MiB
acepta cuerpos enormes en todas las rutas de formulario. La segunda opción es peor: son la mayoría
y es donde vive el request forgery. Con cap por ruta, subir el techo del PDF no ensancha la
superficie de las demás.

## 7. Tests de seguridad

- POST sin token → 403.
- POST con token de otra sesión → 403.
- POST con token válido → funciona (no romper la app).
- `Host` no permitido → 403; `Host: localhost` → funciona.
- Request por encima del cap → 413 antes del parseo.
- Regresión: las 14 rutas de escritura siguen funcionando con token.

## 8. Compatibilidad y reversión

**Compatibilidad:** los cambios son internos. La interfaz no cambia, el flujo no cambia, y no
hay migración de datos. El único efecto visible es que un POST sin token falla.

**Reversión:** quitar los middleware y el helper. No hay datos que migrar ni esquema que
deshacer. Es una reversión de código puro.

## 9. Criterios de aceptación

1. Un sitio externo no puede crear ni modificar ningún registro (verificado con test, no con
   argumento).
2. Un atacante con DNS rebinding no puede leer respuestas.
3. Las 14 rutas de escritura funcionan normalmente desde la interfaz.
4. Un bind no-loopback produce advertencia al arrancar.
5. El backup documentado produce una copia que `PRAGMA integrity_check` valida.
6. La suite completa sigue verde.

## 10. Decisiones que requiere Franco

1. **¿Se implementa el hardening en esta iteración o después del merge de #18 y #20?** Mi
   recomendación: después. Son ortogonales y mezclarlos retrasa ambos.
2. **¿El token CSRF alcanza, o se quiere autenticación real?** Depende de si la app sigue
   siendo local. Si va a exponerse, la respuesta es autenticación, no CSRF.
3. **¿`TrustedHostMiddleware` con lista fija o derivada de variable de entorno?** Recomiendo
   variable, con default conservador.
4. **¿Se aprueba la tabla de límites por ruta del §5.1?** Es la decisión que reemplaza al cap
   global de 2 MiB, que era inviable con el importador de PDF de 10 MiB.

## 11. Estado

**Nada implementado.** Esta propuesta es la próxima feature candidata y queda registrada en el
catálogo con evidencia, para que no se pierda ni se vuelva a auditar desde cero.
