# Lessons Learned

## Objetivo

Consolidar errores reales detectados durante `cv-latex`, su causa raiz, la correccion aplicada, la validacion que la confirmo y la regla operativa para no repetirlos en este proyecto ni en proyectos futuros con Codex/ChatGPT.

## Uso recomendado

- Leer este documento antes de abrir una etapa nueva que toque UI, documentacion, PDFs, Docker, release o GitHub review.
- Usarlo como fuente de prompts operativos concretos, no como changelog.
- Mantener solo aprendizajes confirmados por evidencia real del repo.

## LL-001 - XSS por `innerHTML` con texto dinamico

- Problema detectado: el modal de confirmacion interpolaba texto dinamico con `innerHTML`.
- Causa raiz: se priorizo rapidez de render del dialogo por encima de seguridad de insercion DOM.
- Impacto/riesgo: un titulo o texto malicioso podia inyectar HTML o JavaScript en una accion sensible.
- Como se corrigio: el modal paso a construirse con nodos DOM y asignacion por `textContent`.
- Validacion que lo confirmo: tests de regresion sobre confirmaciones y revision de Codex sobre el hallazgo P1.
- Regla futura para evitarlo: no usar `innerHTML` con contenido dinamico salvo sanitizacion robusta y justificada.
- Instruccion sugerida para proximos prompts: "Si hay texto dinamico en DOM, usa `textContent` o nodos seguros; reporta cualquier `innerHTML` como riesgo de seguridad."

## LL-002 - Markdown actualizado pero HTML servido desactualizado

- Problema detectado: la fuente Markdown ya estaba corregida, pero `/documentation/technical` seguia mostrando estado obsoleto.
- Causa raiz: no se valido el HTML servido por la app despues de editar `docs/user/`.
- Impacto/riesgo: la documentacion visible quedaba atrasada respecto del estado real del release.
- Como se corrigio: se reviso el pipeline de render HTML de `documentation_service.py` y se ajusto el contenido fuente servido.
- Validacion que lo confirmo: requests HTTP/DOM sobre `/documentation/technical` y tests de rutas.
- Regla futura para evitarlo: cada cambio en `docs/user/` debe validarse en la ruta HTML correspondiente.
- Instruccion sugerida para proximos prompts: "No cierres una correccion documental hasta validar la fuente Markdown y la ruta HTML que la expone."

## LL-003 - HTML actualizado pero PDF descargable viejo

- Problema detectado: la pagina HTML reflejaba `v0.9.0`, pero el PDF descargable seguia viejo.
- Causa raiz: se asumio que actualizar la fuente o el HTML implicaba artefacto PDF alineado.
- Impacto/riesgo: descarga inconsistente, review bloqueante y trazabilidad rota entre lectura web y artefacto.
- Como se corrigio: se regeneraron los PDFs servidos bajo `app/static/docs/` usando el pipeline oficial.
- Validacion que lo confirmo: descarga real del PDF, `pdftotext` y ausencia de strings obsoletos.
- Regla futura para evitarlo: HTML y PDF se validan por separado; cambiar uno no confirma el otro.
- Instruccion sugerida para proximos prompts: "Si una documentacion web tiene PDF descargable, valida ambos artefactos explicitamente."

## LL-004 - PDF regenerado pero hash documentado viejo

- Problema detectado: el PDF final ya habia cambiado, pero la trazabilidad seguia mostrando hashes anteriores como si fueran vigentes.
- Causa raiz: no se actualizo la evidencia documental despues de la regeneracion final.
- Impacto/riesgo: la documentacion afirmaba una coincidencia falsa entre descarga real y hash final.
- Como se corrigio: se recalcularon los SHA256 finales y se actualizaron los logs donde debian quedar como referencia actual.
- Validacion que lo confirmo: comparacion entre hashes locales finales, hashes documentados y hashes de la descarga real.
- Regla futura para evitarlo: cada regeneracion final debe cerrar con hash final documentado, no con hashes intermedios.
- Instruccion sugerida para proximos prompts: "Si regeneras artefactos, documenta el hash final actual y distingue claramente cualquier hash intermedio."

## LL-005 - TOC vacio en PDF

- Problema detectado: los PDFs publicados incluian indice vacio.
- Causa raiz: headings no numerados sin entradas reales y compilacion insuficiente para poblar `\tableofcontents`.
- Impacto/riesgo: documento visualmente defectuoso y señal de renderer incompleto.
- Como se corrigio: se agregaron entradas reales al TOC y se compilo con las pasadas necesarias.
- Validacion que lo confirmo: render visual del indice y revision del texto extraido.
- Regla futura para evitarlo: si un PDF usa TOC, debe poblarse de forma real; si no, se elimina.
- Instruccion sugerida para proximos prompts: "No publiques PDFs con `tableofcontents` vacio; valida el indice renderizado como artefacto visual."

## LL-006 - Contraste pobre: texto marron sobre barra marron

- Problema detectado: el callout `Resumen del documento` quedaba con texto oscuro sobre fondo oscuro.
- Causa raiz: el estilo aprobado no se valido en el artefacto PDF real.
- Impacto/riesgo: lectura forzada, mala percepcion visual y necesidad de iteracion adicional.
- Como se corrigio: se mantuvo la barra marron y se paso el texto a un tono claro de alto contraste.
- Validacion que lo confirmo: render de portada/primera pagina a PNG e inspeccion visual.
- Regla futura para evitarlo: los callouts y captions deben verificarse en PNG o PDF real, no solo en CSS/HTML mental.
- Instruccion sugerida para proximos prompts: "Si cambias estilos PDF, valida contraste real de encabezados y callouts sobre el artefacto renderizado."

## LL-007 - Titulos huerfanos al final de pagina

- Problema detectado: algunos headings quedaban solos al pie de pagina y el cuerpo aparecia recien en la siguiente.
- Causa raiz: el renderer no reservaba espacio minimo para el bloque siguiente.
- Impacto/riesgo: lectura pobre y documento con cortes poco profesionales.
- Como se corrigio: se agregaron reglas para estimar espacio y mover el heading junto a su contenido.
- Validacion que lo confirmo: renders PNG de paginas internas afectadas y revision visual.
- Regla futura para evitarlo: un heading no debe cerrar pagina sin cuerpo suficiente debajo.
- Instruccion sugerida para proximos prompts: "Si tocas paginacion PDF, revisa headings huerfanos en paginas internas relevantes."

## LL-008 - Listas cortas partidas entre paginas

- Problema detectado: listas breves quedaban cortadas entre paginas aun cuando entraban completas en la siguiente.
- Causa raiz: el renderer trataba listas como flujo simple sin agrupar bloques cortos.
- Impacto/riesgo: mala lectura y sensacion de layout descuidado.
- Como se corrigio: se agruparon listas cortas para mantenerlas juntas cuando el espacio lo permitia.
- Validacion que lo confirmo: render PNG de paginas con listas y comprobacion visual del bloque completo.
- Regla futura para evitarlo: listas cortas deben mantenerse juntas si moverlas mejora claramente la lectura.
- Instruccion sugerida para proximos prompts: "Revisa listas cortas partidas y prioriza agrupacion visual si no genera un salto peor."

## LL-009 - Validar descarga real de artefactos

- Problema detectado: revisar solo el archivo local no garantizaba que la app sirviera el mismo artefacto.
- Causa raiz: se asumio equivalencia entre el archivo del repo y la descarga expuesta por runtime.
- Impacto/riesgo: falso positivo de validacion y trazabilidad incompleta.
- Como se corrigio: se agrego la descarga real desde `/static/docs/` como validacion obligatoria.
- Validacion que lo confirmo: descarga HTTP del archivo servido y comparacion de hash.
- Regla futura para evitarlo: los artefactos publicados se validan desde su endpoint real.
- Instruccion sugerida para proximos prompts: "No des por bueno un PDF o export si no verificaste la descarga real servida por la app."

## LL-010 - Validar `pdftotext` en PDFs

- Problema detectado: un PDF podia verse aceptable y aun asi tener texto extraido incompleto o roto.
- Causa raiz: se evaluaba solo apariencia visual o existencia del archivo.
- Impacto/riesgo: artefactos poco accesibles y contenido no verificable por texto.
- Como se corrigio: `pdftotext` paso a ser parte del checklist de PDFs servidos.
- Validacion que lo confirmo: extraccion de texto con version, headings y ausencia de strings obsoletos.
- Regla futura para evitarlo: todo PDF importante debe pasar una validacion basica de texto extraible.
- Instruccion sugerida para proximos prompts: "Incluye `pdftotext` cuando valides PDFs generados o regenerados."

## LL-011 - Validar hash anterior, hash nuevo y hash descargado

- Problema detectado: confirmar solo un hash final no mostraba si el artefacto efectivamente habia cambiado ni si la descarga coincidia.
- Causa raiz: validacion incompleta de trazabilidad.
- Impacto/riesgo: auditoria debil y posibilidad de documentar un artefacto incorrecto.
- Como se corrigio: se registraron hash anterior, hash nuevo y hash del archivo descargado.
- Validacion que lo confirmo: comparacion de los tres valores en la misma iteracion.
- Regla futura para evitarlo: todo artefacto regenerado debe dejar evidencia del antes, despues y publicado.
- Instruccion sugerida para proximos prompts: "Para artefactos descargables, reporta hash anterior, hash nuevo y hash de la descarga real."

## LL-012 - Docker/Windows bind mount y permisos al regenerar PDF

- Problema detectado: algunos flujos de regeneracion fallaban por permisos o comportamiento del bind mount en Windows.
- Causa raiz: diferencias de permisos entre host, contenedor y escritura sobre archivos montados.
- Impacto/riesgo: regeneraciones fallidas, artefactos stale y perdida de tiempo en diagnostico.
- Como se corrigio: se ejecuto el pipeline dentro del contenedor con el montaje correcto y permisos adecuados para escribir en el workspace.
- Validacion que lo confirmo: regeneracion efectiva de los PDFs y presencia de los archivos actualizados.
- Regla futura para evitarlo: cuando un artefacto depende de Docker en Windows, validar temprano mount, usuario y escritura efectiva.
- Instruccion sugerida para proximos prompts: "Si regeneras archivos con Docker en Windows, contempla permisos y bind mount como hipotesis primaria."

## LL-013 - `pytest` durante arranque de contenedor puede fallar

- Problema detectado: correr tests demasiado pronto podia fallar aunque la app estuviera bien.
- Causa raiz: el contenedor aun no habia llegado a estado `healthy`.
- Impacto/riesgo: diagnosticos falsos y reintentos innecesarios sobre codigo correcto.
- Como se corrigio: se tomo `docker compose ps` y el estado `healthy` como precondicion antes de `pytest`.
- Validacion que lo confirmo: ejecuciones estables de la suite luego de esperar el runtime sano.
- Regla futura para evitarlo: no interpretar un fallo temprano de tests como bug si el runtime aun no termino de arrancar.
- Instruccion sugerida para proximos prompts: "Si usas Docker Compose, espera `healthy` antes de lanzar `pytest` o validaciones dependientes del contenedor."

## LL-014 - Prompt IDs externos entre Franco y ChatGPT

- Problema detectado: existia riesgo de tratar Prompt IDs como parte del prompt ejecutable de Codex.
- Causa raiz: mezclar trazabilidad humana con instrucciones operativas de la herramienta.
- Impacto/riesgo: prompts ruidosos, mala interpretacion del alcance y documentacion confusa.
- Como se corrigio: se documento explicitamente que los Prompt IDs son externos y solo sirven como referencia.
- Validacion que lo confirmo: alineacion de `AGENTS.md`, docs operativas y manuales.
- Regla futura para evitarlo: separar identificadores de trazabilidad humana de las instrucciones ejecutables.
- Instruccion sugerida para proximos prompts: "Si hay Prompt ID, tratelo como referencia externa y no lo mezcles con el bloque ejecutable para Codex."

## LL-015 - No inventar timestamps historicos

- Problema detectado: algunos logs necesitaban backfill y no siempre existia la hora exacta verificable.
- Causa raiz: intentar convertir bitacoras historicas en registros exactos sin evidencia suficiente.
- Impacto/riesgo: auditoria falsa y confianza reducida en la documentacion.
- Como se corrigio: se dejo la regla de escribir `timestamp exacto no reconstruido con certeza` cuando faltara evidencia.
- Validacion que lo confirmo: reglas persistentes en `AGENTS.md` y trazabilidad mas consistente en docs de desarrollo.
- Regla futura para evitarlo: si no hay certeza, documentar el hueco; no fabricar precision.
- Instruccion sugerida para proximos prompts: "No reconstruyas horas historicas por aproximacion; deja explicitamente la falta de certeza."

## LL-016 - No meter cambios nuevos en un PR ya limpio salvo bloqueo real

- Problema detectado: un PR cercano a merge puede tentarte a incluir ajustes adicionales "aprovechando el viaje".
- Causa raiz: mezclar mejora opcional con correccion realmente necesaria.
- Impacto/riesgo: expansion de alcance, nueva superficie de review y retraso de cierre.
- Como se corrigio: se limito cada PR a fixes bloqueantes del mismo alcance.
- Validacion que lo confirmo: PRs #9 y #10 cerraron con ajustes puntuales ligados al hallazgo real.
- Regla futura para evitarlo: si el PR ya esta limpio, no agregar cambios no bloqueantes.
- Instruccion sugerida para proximos prompts: "Si el review esta limpio, agrega cambios solo si corrigen un bloqueo real del mismo alcance."

## LL-017 - Re-review cuando cambia el commit revisado

- Problema detectado: una revision aprobada deja de cubrir commits nuevos.
- Causa raiz: asumir que el review previo sigue siendo suficiente tras modificar el diff.
- Impacto/riesgo: mergear cambios nuevos sin revisarlos con el mismo criterio.
- Como se corrigio: se pidio `@codex review` nuevamente despues de corregir hallazgos o ajustar artefactos.
- Validacion que lo confirmo: los re-reviews detectaron y luego liberaron issues reales sobre PDFs y trazabilidad.
- Regla futura para evitarlo: cada cambio relevante sobre el commit revisado exige una nueva revision del mismo PR.
- Instruccion sugerida para proximos prompts: "Si cambia el diff despues de una review, publica re-review antes de mergear."

## LL-018 - Mantener fixes del mismo alcance dentro del PR abierto

- Problema detectado: abrir un PR nuevo por cada correccion menor fragmenta la trazabilidad.
- Causa raiz: tratar cada hallazgo post-review como trabajo independiente en lugar de cierre del mismo alcance.
- Impacto/riesgo: dispersion de contexto, historial menos claro y mas costo de coordinacion.
- Como se corrigio: los fixes de contraste, paginacion y hashes se mantuvieron dentro de PR #10 mientras siguieran siendo del mismo scope.
- Validacion que lo confirmo: el historial del PR quedo coherente y el cierre fue auditable.
- Regla futura para evitarlo: si el hallazgo corrige el mismo entregable, mantenerlo en la misma rama y PR.
- Instruccion sugerida para proximos prompts: "No abras un PR nuevo para un fix menor del mismo alcance; corrige en la rama abierta y vuelve a pedir review."

## LL-019 - Un test que codifica el contrato defectuoso pasa mientras el bug existe

- Problema detectado: el formulario plano de edicion destruia silenciosamente todas las secciones que solo existen en schema 2 (certificaciones, proyectos, idiomas, links, headline, location) al guardar un CV estructurado, y el CV seguia apareciendo como estructurado porque el payload vacio revalidaba como valido.
- Causa raiz: los dos tests que cubrian esa ruta afirmaban literalmente el comportamiento destructivo (`test_update_structured_cv_regenerates_payload_from_legacy_fields` esperaba `metadata.source == "legacy_edit"`). Ademas construian la fila con `_mark_cv_as_structured`, que deriva el payload de los campos legacy y por lo tanto ya dejaba vacias las secciones solo-estructuradas antes de editar. El test era verde y no podia detectar la perdida: no existia ningun caso con contenido exclusivo de schema 2 en la ruta legacy.
- Impacto/riesgo: perdida irreversible de datos del usuario alcanzable desde el boton principal del detalle, con el CV aun etiquetado como estructurado y sin warning. La suite completa en verde no cubria el escenario.
- Como se corrigio: se elimino el contrato destructivo en tres capas: la escritura (`_build_structured_columns_for_legacy_update` lanza `StructuredCVLegacyUpdateError` para filas estructuradas, antes de abrir conexion, en lugar de regenerar o anular), las rutas (`cvs_edit` y `cvs_update` redirigen con mensaje en espanol) y la vista (el boton "Editar" apunta al editor estructurado cuando `is_structured`). Se reescribieron los dos tests para construir el CV con `create_structured_cv` y contenido exclusivo de schema 2, y comparar seccion por seccion antes y despues.
- Validacion que lo confirmo: `assertRaises(StructuredCVLegacyUpdateError)` mas igualdad de `sections` antes/despues incluyendo `headline`, `location`, `certifications`, `projects`, `languages`, `links`, `additional_info`, `contact.links` y `metadata.source`. Suite enfocada `80 passed`, suite completa `198 passed`. Prueba HTTP end-to-end: `POST /cvs/1/edit` devolvio 303 sin escribir y el export schema 2 posterior conservo el titulo y las cinco secciones.
- Regla futura para evitarlo: un test de ruta destructiva debe construir el fixture con el metodo de escritura real del dominio (por ejemplo `create_structured_cv` con contenido exclusivo del schema nuevo), nunca con un helper que derive el estado desde la forma vieja. Si un test afirma un comportamiento que un usuario perderia datos por sufrir, ese test esta codificando el bug.
- Instruccion sugerida para proximos prompts: "Antes de confiar en un test verde de migracion de datos, verifica que el fixture contiene datos que SOLO existen en el formato nuevo."

## LL-020 - Un limite de longitud sin tope en el sufijo rompe el round-trip

- Problema detectado: un CV exportado con un titulo de 110 a 120 caracteres no podia reimportarse, porque `_build_imported_title` agregaba el sufijo `(importado)` sin respetar `FIELD_LIMITS["title"] = 120`.
- Causa raiz: la logica de sufijo estaba duplicada. `build_duplicate_title` si truncaba la base para dejar lugar al sufijo; `_build_imported_title` no. El contrato "lo que exporto se puede importar" no estaba verificado en ninguna prueba.
- Impacto/riesgo: perdida funcional en round-trip y mensajes de error que apuntan al JSON del usuario cuando el problema es del propio importador. Se agrava con cualquier sufijo agregado por el sistema.
- Como se corrigio: `IMPORTED_TITLE_SUFFIX` mas truncado de la base y `rstrip`, con guarda para base vacia y disponible menor o igual a cero. Se cubrieron 109, 110, 119 y 120 caracteres en schema 1 y schema 2.
- Validacion que lo confirmo: import HTTP con titulo de 120 caracteres responde 303 en ambos esquemas y el titulo resultante queda en 120 conservando `(importado)`.
- Regla futura para evitarlo: todo sufijo o prefijo agregado por el sistema debe respectar el mismo `FIELD_LIMITS` del campo que modifica, y la prueba de round-trip debe usar el valor limite exacto.
- Instruccion sugerida para proximos prompts: "Si el sistema agrega texto a un campo persistido, verifica el limite DESPUES de agregar, no antes."

## LL-021 - La referencia de una prueba de compatibilidad debe salir del baseline

- Problema detectado: la suite afirmaba que el TEX legacy quedaba intacto, pero ningun test lo comparaba contra el codigo anterior a la feature. Una regresion en las cuatro plantillas habria pasado inadvertida.
- Causa raiz: los tests existentes comparan un CV legacy contra variantes de fallback generadas dentro de la misma corrida, es decir con el mismo `_build_cv_context` y las mismas plantillas modificadas. Ese tipo de comparacion no puede detectar una regresion introducida por el propio diff.
- Impacto/riesgo: la garantia de compatibilidad legacy era una afirmacion sin respaldo mecanico, justamente en el punto mas sensible de una migracion de formato de datos.
- Como se corrigio: se extrajo el arbol de `a28d1fd` con `git archive`, se ejecuto el MISMO generador dentro de la imagen contra ese arbol y contra el workspace vigente, y se guardo la salida del baseline como fixture en `tests/fixtures/legacy_tex_a28d1fd`. La prueba `tests/test_legacy_tex_compatibility.py` reconstruye el mismo CV ficticio y exige identidad byte a byte en las cuatro plantillas. Se documento explicitamente que el nivel comprobado es identidad byte a byte y no solo equivalencia textual.
- Validacion que lo confirmo: las cuatro plantillas coinciden en longitud y SHA256 entre `a28d1fd` y el codigo vigente. Y el guard se provoco: al adulterar el fixture la prueba fallo indicando la linea exacta de la diferencia. Una prueba de identidad que nunca se hizo fallar no demuestra nada.
- Regla futura para evitarlo: una prueba de compatibilidad con una version anterior debe generar su referencia desde esa version anterior, nunca desde el codigo bajo prueba. Y antes de confiar en ella, hay que verificar que falla cuando el resultado esperado se altera.
- Instruccion sugerida para proximos prompts: "Si la garantia es 'no cambia el comportamiento anterior', genera el golden fixture desde el commit base y demuestra que el test detecta una diferencia."

## LL-022 - Declarar la politica de finales de linea en vez de normalizar el historico

- Problema detectado: alrededor de 79 archivos aparecian como modificados por unicamente CRLF porque HEAD guardaba LF y el working tree tenia CRLF, sin `.gitattributes` y con `core.autocrlf` sin definir. Un `git add` corriente almacenaba CRLF y producia commits donde cada archivo se leia como reescritura completa.
- Causa raiz: la politica de EOL nunca estuvo declarada, de modo que cada parte del equipo y cada herramienta decide por su cuenta. Cuando WSL y Windows comparten el repositorio, eso se traduce en ruido permanente y en commits ilegibles.
- Impacto/riesgo: reviews que parecen masivos y no lo son, riesgo de versionar CRLF por accidente y dificultad para distinguir un cambio real de un cambio de terminador de linea.
- Como se corrigio: se agrego un `.gitattributes` minimo con `* text=auto eol=lf` y declaracion explicita de binarios. No se ejecuto `git add --renormalize` ni se modifico la configuracion global. El indice de HEAD ya contenia todo archivo de texto en LF, con lo que la politica es compatible con el historial existente y no produce ningun cambio colateral.
- Validacion que lo confirmo: despues de agregar el archivo, `git status --short` sigue listando solo los archivos con cambio real mas el propio `.gitattributes`, y los 79 archivos con diferencias solo-CRLF siguen byte-identicos a `a28d1fd`. Setenta y dos de ellos permanecen limpios en el working tree; los siete restantes son precisamente los que recibieron cambios de contenido reales en esta etapa.
- Regla futura para evitarlo: al agregar contenido en este repositorio, agregar tambien las rutas en la misma operacion y verificar con `git diff --ignore-cr-at-eol` que el diff es real. La normalizacion historica de los archivos ya presentes es una decision aparte y debe hacerse de forma explicita, nunca como efecto secundario de un commit de funcionalidad.
- Instruccion sugerida para proximos prompts: "Antes de commitear, confirma que `git diff --ignore-cr-at-eol` muestra solo cambios reales y que ningun archivo se incorpore solo por CRLF."
