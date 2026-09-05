# 15 - Documento maestro de la aplicación

| Campo | Valor |
|---|---|
| Estado | Consolidado a partir de la implementación verificada |
| Versión | 1.0 |
| Fecha | 2026-09-02 |

## Propósito

Este documento reúne la vista ejecutiva, arquitectónica y operativa de Assessment Studio en una sola referencia de consulta. No reemplaza los documentos especializados; los organiza y los conecta.

## Alcance funcional

Assessment Studio es una plataforma institucional bilingüe para evaluar, corregir y reportar exámenes con:

- múltiples docentes y cuentas administrativas;
- padrón compartido de estudiantes, secciones, asignaturas y categorías;
- banco reutilizable de preguntas por docente;
- exámenes con versiones y asignaciones por sección;
- un intento estable por estudiante y asignación;
- calificación del lado del servidor;
- listening con audio subido o TTS del navegador;
- telemetría de integridad y penalizaciones manuales auditables;
- exportaciones PDF, CSV y XLSX.

## Arquitectura en una vista

```mermaid
flowchart LR
    Student[Estudiante] -->|HTTPS HTML| App[Assessment Studio]
    Teacher[Docente] -->|HTTPS HTML y exportaciones| App
    Admin[Administrador] -->|HTTPS configuracion| App
    App --> DB[(PostgreSQL)]
    App --> Audio[(static/audio)]
    Student -. TTS opcional .-> Speech[Web Speech API]
```

### Contenedores principales

```mermaid
flowchart TB
    subgraph Browser[Browser]
        Jinja[Jinja templates]
        ExamJS[static/js/exam.js]
        UIJS[static/js/ui.js]
        Guard[static/js/student_guard.js]
        CSS[static/css]
    end
    subgraph Flask[Proceso Flask]
        Routes[Rutas y vistas]
        Auth[Autenticacion y CSRF]
        Domain[Asignacion snapshot grading]
        Reports[PDF CSV XLSX]
        I18N[tr y settings]
    end
    Jinja --> Routes
    ExamJS --> Routes
    UIJS --> Routes
    Guard --> Jinja
    Routes --> Auth
    Routes --> Domain
    Routes --> Reports
    Routes --> I18N
    Auth --> DB[(PostgreSQL)]
    Domain --> DB
    Reports --> DB
```

## Modelo de información

Las entidades clave son:

| Dominio | Entidades |
|---|---|
| Identidad | `teachers`, `students`, `sections` |
| Catálogo por docente | `subjects`, `categories` |
| Autoría docente | `question_bank`, `exams`, `exam_versions`, `exam_version_questions` |
| Asignación y ejecución | `exam_assignments`, `student_exam_allocations`, `attempts` |
| Integridad y ajuste | `integrity_events`, `attempt_penalties` |
| Configuración | `app_settings` |

### Relación principal de datos

```mermaid
erDiagram
    TEACHERS ||--o{ QUESTION_BANK : owns
    TEACHERS ||--o{ EXAMS : owns
    TEACHERS ||--o{ ATTEMPTS : owns
    SECTIONS ||--o{ STUDENTS : contains
    SUBJECTS ||--o{ CATEGORIES : groups
    SUBJECTS ||--o{ QUESTION_BANK : classifies
    SUBJECTS ||--o{ EXAMS : classifies
    EXAMS ||--o{ EXAM_VERSIONS : has
    EXAM_VERSIONS ||--o{ EXAM_VERSION_QUESTIONS : selects
    QUESTION_BANK ||--o{ EXAM_VERSION_QUESTIONS : reused
    EXAMS ||--o{ EXAM_ASSIGNMENTS : assigned
    EXAM_ASSIGNMENTS ||--o{ STUDENT_EXAM_ALLOCATIONS : allocates
    STUDENTS ||--o{ ATTEMPTS : submits
    EXAM_ASSIGNMENTS ||--o{ ATTEMPTS : starts
    ATTEMPTS ||--o{ INTEGRITY_EVENTS : records
    ATTEMPTS ||--o{ ATTEMPT_PENALTIES : adjusts
```

## Flujos principales

### 1. Inicio de sesión docente

```mermaid
sequenceDiagram
    participant T as Docente
    participant F as Flask
    participant D as PostgreSQL
    T->>F: POST /teacher con credenciales
    F->>D: buscar cuenta por correo
    D-->>F: hash, rol, estado
    F->>F: validar hash y estado
    alt Credenciales validas
        F->>D: actualizar last_login_at
        F->>F: limpiar sesion y establecer identidad
        F-->>T: redireccion al panel
    else Credenciales invalidas
        F-->>T: error generico
    end
```

### 2. Inicio de sesión estudiantil y reglas

```mermaid
sequenceDiagram
    participant S as Estudiante
    participant F as Flask
    participant D as PostgreSQL
    S->>F: POST /start
    F->>D: buscar estudiante activo
    F->>F: validar clave
    alt Requiere cambio
        F-->>S: redireccion a cambio de clave
    else Ok
        F-->>S: panel estudiantil
    end
    F->>D: leer reglas vigentes
    alt Requiere aceptacion
        F-->>S: modal de reglas
        S->>F: POST /student/rules/acknowledge
    end
```

### 3. Asignación, allocation y snapshot

```mermaid
sequenceDiagram
    participant S as Estudiante
    participant F as Flask
    participant D as PostgreSQL
    S->>F: POST /student/exams/<assignment_id>/start
    F->>D: validar estudiante, seccion, publicacion y reglas
    F->>D: buscar intento previo
    alt Existe intento
        D-->>F: mismo intento y version
    else Primer inicio
        F->>D: elegir version estable o fija
        F->>D: leer preguntas y construir snapshot
        F->>D: insertar allocation e intento
    end
    F-->>S: redirect /exam
```

### 4. Resolución del examen y envío

```mermaid
flowchart TD
    Current[Pregunta actual] --> Input[Capturar respuesta]
    Input --> ValidateClient[Validacion cliente]
    ValidateClient -->|Invalida| Error[Corregir en la misma pantalla]
    ValidateClient -->|Valida| Next[Siguiente pregunta]
    Next --> Complete{Todas completas}
    Complete -->|No| Current
    Complete -->|Si| Review[Revision final]
    Review --> Submit[POST /submit]
    Submit --> ValidateServer{Validacion server snapshot}
    ValidateServer -->|Invalida| Draft[Guardar borrador y mantener in_progress]
    ValidateServer -->|Valida| Grade[Calificar y marcar submitted]
    Grade --> Result[Resultado]
```

### 5. Integridad y penalizaciones

```mermaid
sequenceDiagram
    participant B as Navegador
    participant F as Flask
    participant D as PostgreSQL
    participant T as Docente propietario
    B->>F: POST /api/integrity-event
    F->>D: validar intento propio en progreso
    F->>D: incrementar contador e insertar evento
    T->>F: ver resultado
    F->>D: leer intento y timeline
    opt Penalizacion manual
        T->>F: POST /teacher/results/<attempt_id>/penalties
        F->>D: validar owner y limite
        F->>D: registrar ajuste auditable
    end
```

### 6. Resultados y exportaciones

```mermaid
flowchart LR
    Filters[Filtros docente] --> Query[Consulta sobre submitted]
    Query --> Dashboard[Dashboard y KPIs]
    Query --> CSV[Exportacion CSV]
    Query --> XLSX[Exportacion XLSX]
    Query --> PDF[Reporte PDF del intento]
```

Los exportes imprimibles de exámenes preservan el snapshot, pero barajan de forma determinística opciones/ítems.

## Ciclo de vida del intento

```mermaid
stateDiagram-v2
    [*] --> in_progress: start
    in_progress --> in_progress: autosave / recovery
    in_progress --> submitted: submit valido
    in_progress --> in_progress: submit invalido
    submitted --> [*]
```

## Ciclo de vida de examen y versiones

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> published: publish
    published --> archived: archive
    archived --> published: restore
```

## Operación y despliegue

**Implementado:** Docker Compose levanta PostgreSQL 17 y la aplicación bajo Gunicorn. Las migraciones Alembic se ejecutan antes del arranque, luego corre `bootstrap.py` y finalmente Gunicorn.

**Recomendado:** TLS en reverse proxy, secretos fuera del repositorio, backups probados, monitoreo y restauración ensayada.

## Manuales de usuario

Los manuales vivos están en `userdirections/`:

- [Manual del administrador](../userdirections/manual-administrador.md)
- [Manual del docente](../userdirections/manual-docente.md)
- [Manual del estudiante](../userdirections/manual-estudiante.md)
- [Importación de estudiantes](../userdirections/importacion-estudiantes.md)
- [Importación de preguntas](../userdirections/importacion-preguntas.md)

## Documentación relacionada

| Tema | Documento |
|---|---|
| Resumen ejecutivo | [00-executive-summary.md](00-executive-summary.md) |
| Producto y negocio | [01-product-and-business.md](01-product-and-business.md) |
| Personas y casos de uso | [02-personas-journeys-use-cases.md](02-personas-journeys-use-cases.md) |
| Requisitos | [03-functional-requirements.md](03-functional-requirements.md) |
| UX / UI | [04-ux-design-system.md](04-ux-design-system.md) |
| Arquitectura técnica | [05-architecture.md](05-architecture.md) |
| Modelo de datos | [06-data-model.md](06-data-model.md) |
| Seguridad y privacidad | [07-security-privacy.md](07-security-privacy.md) |
| Desarrollo | [08-development-guide.md](08-development-guide.md) |
| Calidad | [09-quality-strategy.md](09-quality-strategy.md) |
| Operaciones | [10-operations-runbook.md](10-operations-runbook.md) |
| Rutas Flask | [11-api-route-reference.md](11-api-route-reference.md) |
| Diagramas | [12-diagrams.md](12-diagrams.md) |
| ADRs | [13-adrs.md](13-adrs.md) |
| Gobierno y roadmap | [14-glossary-governance-roadmap.md](14-glossary-governance-roadmap.md) |

## Lectura recomendada

1. `docs/README.md`
2. `docs/05-architecture.md`
3. `docs/06-data-model.md`
4. `docs/11-api-route-reference.md`
5. `userdirections/README.md`
