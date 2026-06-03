# Changelog General

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
