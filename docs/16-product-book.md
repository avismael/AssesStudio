# 16 - Product book

| Campo | Valor |
|---|---|
| Estado | Consolidado a partir de la implementación verificada |
| Versión | 1.0 |
| Fecha | 2026-09-05 |

## Propósito

Este documento resume el producto, su arquitectura funcional y la pila técnica que lo sostiene. Es la puerta de entrada para entender qué es Assessment Studio, por qué está organizado así y qué documentos amplían cada tema.

## Resumen del producto

Assessment Studio es una plataforma institucional para gestionar evaluaciones con tres perfiles operativos:

- **Administrador**: mantiene el padrón institucional, secciones y cuentas docentes.
- **Docente**: administra su catálogo, crea exámenes, asigna versiones por sección, revisa resultados y exporta reportes.
- **Estudiante**: inicia sesión, resuelve exámenes, conserva progreso y consulta resultados.

El producto combina flujo docente y experiencia estudiantil en una misma aplicación web server-rendered, con reglas de negocio aplicadas en servidor y persistencia transaccional en PostgreSQL.

## Qué resuelve

| Necesidad | Respuesta del sistema |
|---|---|
| Un solo intento estable por estudiante y asignación | La versión se asigna de forma persistente y el intento conserva snapshot histórico |
| Exámenes reutilizables con variantes | Banco por docente, versiones de examen y preguntas seleccionadas por versión |
| Evaluación controlada | Validación y calificación del lado del servidor |
| Seguimiento de integridad | Eventos técnicos, revisión docente y penalizaciones auditables |
| Reportes operativos | Exportaciones PDF, CSV y XLSX |

## Pila tecnológica

| Capa | Tecnología | Uso |
|---|---|---|
| Web backend | Flask | App principal, rutas, sesión, auth, validación y renderizado |
| Vistas | Jinja | HTML server-rendered |
| Persistencia | PostgreSQL 17 | Datos institucionales, snapshots, resultados y auditoría |
| Acceso a DB | psycopg 3 / pool | Conexión y pool transaccional |
| Migraciones | Alembic | Evolución del esquema |
| Frontend | JavaScript vanilla | Navegación, autosave, interacción del examen |
| Estilos | CSS | Sistema visual y layout responsive |
| Runtime | Gunicorn | Servidor WSGI |
| Orquestación | Docker Compose | App + base + arranque reproducible |
| Exportación XLSX | openpyxl | Reportes Excel |
| Exportación PDF | reportlab | Reportes PDF |

## Arquitectura

El patrón usado es un **monolito modular server-rendered** con **slices por dominio**. La aplicación central vive en `app.py`, las áreas funcionales se separan en módulos bajo `routes/`, y la UI se compone con plantillas compartidas y helpers comunes.

### Por qué este patrón

- El negocio necesita consistencia transaccional entre asignación, snapshot, grading e integridad.
- Un microservicio fragmentaría una unidad de datos que debe resolverse en una sola base y una sola transacción.
- La separación por módulos de ruta da orden sin introducir la complejidad de una arquitectura distribuida.
- No se eligió Blueprints como frontera principal porque el límite real del sistema es funcional y transaccional, no el framework de routing.

### Organización práctica

| Zona | Rol |
|---|---|
| `app.py` | Núcleo de la aplicación, helpers, auth, reglas, grading e import/export |
| `routes/teacher_*.py` | Slices funcionales de docente y admin |
| `templates/` | Presentación Jinja y componentes compartidos |
| `static/js/` | Interacción del examen y utilidades de UI |
| `static/css/` | Sistema visual y estilos |
| `migrations/` | Esquema oficial |
| `seed.py` | Fixtures de desarrollo |

## Capacidades del producto

- Autenticación de estudiantes, docentes y admin.
- Gestión de secciones y padrón institucional.
- Banco de preguntas por docente.
- Exámenes con versiones y asignaciones por sección.
- Un intento estable por `(student_id, assignment_id)`.
- Snapshot histórico al iniciar el examen.
- Corrección automática y reporte de resultados.
- Listening con audio local o TTS del navegador.
- Telemetría de integridad y penalizaciones manuales.
- Exportación de resultados y reportes imprimibles.

## Documentación relacionada

- [05 - Arquitectura técnica](05-architecture.md)
- [06 - Modelo y diccionario de datos](06-data-model.md)
- [11 - Referencia de rutas Flask](11-api-route-reference.md)
- [12 - Catálogo de diagramas](12-diagrams.md)
- [15 - Documento maestro de la aplicación](15-documento-de-la-aplicacion.md)
