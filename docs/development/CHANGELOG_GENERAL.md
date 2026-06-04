# Changelog General

## 0.4.2 - 2026-06-04

### Cambiado

- `docker-compose.yml` publica el puerto HTTP sobre `127.0.0.1` por defecto mediante `APP_HOST_BIND`.
- La importacion JSON ahora se lee por chunks con limite temprano de `512 KB`.
- El duplicado de CV reutiliza validaciones y recorta el titulo para cerrar con `(copia)` sin exceder el maximo.
- Los errores de compilacion PDF separan mensaje seguro para UI y detalle tecnico para logs.
- Se actualizaron README, docs operativas y modulo CV Builder para reflejar el baseline endurecido.

### Validado

- `pytest` cubriendo lectura limitada de import JSON, duplicado con titulo largo y mensaje PDF seguro.
- Build y arranque Docker manteniendo `/data`, exportaciones y compilacion PDF.

### No incluido en esta version

- Etapa 4.
- Cartas de presentacion.
- Tracker de postulaciones.
- ATS Basic Check funcional.
- IA.

## 0.4.1 - 2026-06-03

### Cambiado

- Plantillas LaTeX actualizadas con `cmap`, `lmodern`, `glyphtounicode` y `pdfgentounicode=1`.
- Dockerfile actualizado con `lmodern` y `poppler-utils`.
- Tests de LaTeX actualizados para verificar el bloque de mapeo Unicode en todas las plantillas.
- Documentacion actualizada con la validacion de extraccion de texto PDF.

### Validado

- PDFs generados correctamente con `classic`, `modern`, `compact` y `tech`.
- Extraccion con `pdftotext` preservando `Perfil`, acentos, `ñ`, `ü` y signos comunes en espanol.

### No incluido en esta version

- Cartas de presentacion.
- Tracker de postulaciones.
- ATS Basic Check funcional.
- IA.

## 0.4.0 - 2026-06-03

### Agregado

- Export Engine para CVs.
- Descarga de TEX generado desde CV guardado.
- Generacion y descarga de PDF desde TEX.
- Exportacion de CV a JSON.
- Importacion de CV desde JSON creando un nuevo registro seguro.
- Persistencia de artefactos en `/data/exports`.
- Directorios de exportacion creados automaticamente.
- Compilacion PDF en directorio temporal controlado bajo `/data/exports/_tmp`.
- Tests basicos para `export_service` y `pdf_service`.
- Controles HTML simples para exportar e importar desde el modulo CVs.

### Cambiado

- Version del proyecto actualizada a `0.4.0`.
- Dockerfile actualizado con TeX Live para compilar las plantillas actuales con `pdflatex`.
- Vista TEX actualizada con acciones de descarga TEX y generacion PDF.
- Nombres de archivo exportados reforzados con sanitizacion y timestamp con microsegundos para evitar colisiones.

### No incluido en esta version

- Cartas de presentacion.
- Tracker de postulaciones.
- ATS Basic Check.
- IA.
- Login.
- PostgreSQL.
- Deploy cloud.

## 0.3.0 - 2026-06-02

### Agregado

- Estructura `app/latex_templates/cv/`.
- Plantillas LaTeX propias:
  - `classic.tex`
  - `modern.tex`
  - `compact.tex`
  - `tech.tex`
- Servicio `app/services/latex_service.py`.
- Sanitizador `app/validations/latex_sanitizer.py`.
- Previsualizacion de contenido `.tex` desde un CV guardado.
- Manejo de secciones vacias.
- Soporte para caracteres comunes en espanol mediante UTF-8.
- Tests basicos de sanitizacion.
- Documentacion especifica de plantillas LaTeX.
- ADR de rendering LaTeX.

### Cambiado

- Version del proyecto actualizada a `0.3.0`.
- Detalle de CV actualizado con accion `Ver TEX`.
- Dependencias del contenedor actualizadas para incluir `pytest` y permitir la validacion con `python -m pytest` dentro de Docker.
- Imagen Docker actualizada para copiar `tests/` y ejecutar la suite dentro del contenedor.

### No incluido en esta version

- Compilacion PDF final.
- Descarga PDF.
- Export TEX.
- Export JSON.
- Import JSON.
- Cartas de presentacion.
- Tracker de postulaciones.
- ATS Basic Check.
- IA.

## 0.2.0 - 2026-06-02

### Agregado

- Modulo CV Builder Core.
- Modelo base `CV`.
- Schema `CVFormData`.
- Tabla SQLite `cvs`.
- CRUD basico de CVs:
  - Crear CV.
  - Listar CVs.
  - Ver detalle.
  - Editar CV.
  - Duplicar CV.
  - Eliminar logicamente con confirmacion.
- Formularios HTML simples.
- Navegacion desde dashboard y header hacia CVs.
- Validaciones centralizadas para campos requeridos, email y longitudes.
- Documentacion especifica del modulo.

### Cambiado

- Version del proyecto actualizada a `0.2.0`.
- Dashboard actualizado para marcar CVs como modulo activo.

### No incluido en esta version

- LaTeX.
- Generacion PDF.
- Export TEX.
- Export JSON.
- Cartas de presentacion.
- Tracker de postulaciones.
- ATS Basic Check.
- IA.

## 0.1.0 - 2026-06-02

### Agregado

- Base minima FastAPI.
- Dashboard Jinja2 con estado `MVP base funcionando`.
- Archivos estaticos CSS y JavaScript.
- Inicializacion tecnica de SQLite en `/data/app.db`.
- Dockerfile y Docker Compose con servicio `app`.
- Persistencia local mediante `./data:/data`.
- Documentacion inicial de desarrollo.
- ADRs iniciales para stack y portabilidad Docker.

### No incluido en esta version

- CV Builder.
- Plantillas LaTeX.
- Export PDF/TEX/JSON.
- Cartas de presentacion.
- Tracker de postulaciones.
- ATS Basic Check.
- IA.
