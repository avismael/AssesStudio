# 12 - Catálogo de diagramas

| Campo | Valor |
|---|---|
| Estado | Implementado/recomendado según cada leyenda |
| Versión | 1.0 |
| Fecha | 2026-08-16 |

Los IDs y labels evitan caracteres Mermaid ambiguos. Diagramas adicionales: [contexto y módulos](05-architecture.md), [ER](06-data-model.md), [UX](04-ux-design-system.md), [deploy/restore](10-operations-runbook.md) y [threat boundaries](07-security-privacy.md).

## Inventario

| ID | Diagrama | Tipo | Estado descrito |
|---|---|---|---|
| D01 | Contexto | Flowchart | Implementado |
| D02 | Contenedores y módulos | Flowchart | Implementado |
| D03 | Datos ER principal | ER | Implementado; relaciones principales completas |
| D04 | Login docente | Sequence | Implementado |
| D05 | Login estudiante y reglas | Sequence | Implementado |
| D06 | Asignación, allocation y snapshot | Sequence | Implementado |
| D07 | Navegación, validación y submit | Flowchart | Implementado |
| D08 | Integridad y penalización | Sequence | Implementado |
| D09 | Resultado y exports | Flowchart | Implementado |
| D10 | Topología de despliegue | Flowchart | Recomendado |
| D11 | CI/calidad | Flowchart | Recomendado como workflow; comandos implementados |
| D12 | Incidente y restore | Flowchart | Recomendado |
| D13 | Estado del attempt | State | Implementado |
| D14 | Estado de exam/version | State | Implementado |
| D15 | Preparación docente | Sequence | Implementado |
| D16 | Resolución estudiante | Sequence | Implementado |

## D01 - Contexto

```mermaid
flowchart LR
    Student[Estudiante] --> App[Assessment Studio]
    Teacher[Docente] --> App
    Admin[Administrador] --> App
    App --> DB[(SQLite)]
    App --> Audio[(Audio local)]
    Student -. Voz TTS local .-> Speech[Web Speech API]
```

## D02 - Contenedores y módulos

```mermaid
flowchart TB
    Browser[Browser] --> Templates[Jinja HTML]
    Browser --> JS[JavaScript vanilla]
    Browser --> CSS[CSS responsive]
    Templates --> Flask[Flask app.py]
    JS --> Flask
    Flask --> Auth[Auth session CSRF ownership]
    Flask --> Exam[Exam allocation snapshot grading]
    Flask --> Import[CSV import]
    Flask --> Export[PDF CSV XLSX]
    Auth --> DB[(SQLite)]
    Exam --> DB
    Import --> DB
    Export --> DB
    Exam --> Files[(Audio files)]
```

## D03 - Datos

```mermaid
erDiagram
    TEACHERS ||--o{ EXAMS : owns
    TEACHERS ||--o{ QUESTION_BANK : owns
    TEACHERS ||--o{ ATTEMPTS : owns
    TEACHERS ||--o{ ATTEMPT_PENALTIES : applies
    SECTIONS ||--o{ STUDENTS : includes
    SUBJECTS ||--o{ CATEGORIES : includes
    SUBJECTS ||--o{ QUESTION_BANK : classifies
    CATEGORIES ||--o{ QUESTION_BANK : classifies
    SUBJECTS ||--o{ EXAMS : classifies
    EXAMS ||--o{ EXAM_VERSIONS : has
    EXAM_VERSIONS ||--o{ EXAM_VERSION_QUESTIONS : selects
    QUESTION_BANK ||--o{ EXAM_VERSION_QUESTIONS : reused
    EXAMS ||--o{ EXAM_ASSIGNMENTS : assigned
    SECTIONS ||--o{ EXAM_ASSIGNMENTS : receives
    EXAM_ASSIGNMENTS ||--o{ STUDENT_EXAM_ALLOCATIONS : fixes
    STUDENTS ||--o{ STUDENT_EXAM_ALLOCATIONS : receives
    EXAM_VERSIONS ||--o{ STUDENT_EXAM_ALLOCATIONS : selected
    STUDENTS ||--o{ ATTEMPTS : starts
    EXAM_ASSIGNMENTS ||--o{ ATTEMPTS : starts
    ATTEMPTS ||--o{ INTEGRITY_EVENTS : logs
    ATTEMPTS ||--o{ ATTEMPT_PENALTIES : adjusts
```

## D04 - Login docente

```mermaid
sequenceDiagram
    participant T as Teacher
    participant F as Flask
    participant D as SQLite
    T->>F: POST teacher email password
    F->>D: SELECT teacher by email
    D-->>F: account hash role active
    F->>F: check_password_hash
    alt Valid and active
        F->>D: UPDATE last_login_at
        F->>F: clear session and set teacher identity
        F-->>T: redirect teacher dashboard
    else Invalid
        F-->>T: generic login error
    end
```

## D05 - Login estudiante y reglas

```mermaid
sequenceDiagram
    participant S as Student
    participant F as Flask
    participant D as SQLite
    S->>F: POST start with CSRF
    F->>D: active student and section by email
    F->>F: verify password
    alt Must change password
        F-->>S: redirect student password
        S->>F: POST new password with CSRF
        F->>D: update hash and flag
    end
    F-->>S: student dashboard
    F->>D: read current rules
    alt Acknowledgment required
        F-->>S: blocking rules dialog
        S->>F: POST rules version and acceptance
        F->>F: snapshot acceptance in session
    end
```

## D06 - Asignación, allocation y snapshot

```mermaid
sequenceDiagram
    participant S as Student
    participant F as Flask
    participant D as SQLite
    S->>F: POST start assignment
    F->>D: validate rules student section exam
    F->>D: find prior attempt
    alt Prior attempt
        D-->>F: same attempt and version
    else New attempt
        F->>D: find allocation
        alt No allocation and random mode
            F->>D: count allocations by usable version
            F->>F: choose among least used
            F->>D: insert stable allocation
        else Fixed mode
            F->>D: validate fixed version
        end
        F->>D: read version questions with answers
        F->>D: insert attempt snapshots and owner
    end
    F-->>S: redirect exam
```

Compatibilidad legacy en este ciclo: si una pregunta listening no tiene `listening_source`, `audio` selecciona archivo; si solo tiene `script`, se conserva como TTS y el guion se obtiene on demand mediante el endpoint autenticado.

## D07 - Respuestas y envío

```mermaid
flowchart TD
    Current[Pregunta actual] --> Input[Capturar respuesta]
    Input --> Forward{Avanzar hacia delante}
    Forward --> ValidateClient[Validar estructura cliente]
    ValidateClient -->|Invalida| Error[Error foco y misma pregunta]
    Error --> Input
    ValidateClient -->|Valida| Next[Mostrar y enfocar siguiente]
    Next --> Complete{Todas validas}
    Complete -->|No| Current
    Complete -->|Si| Review[Modal de revision]
    Review --> Submit[POST submit con CSRF]
    Submit --> ValidateServer{Validacion server snapshot}
    ValidateServer -->|Invalida| Draft[Guardar draft y seguir in progress]
    Draft --> Current
    ValidateServer -->|Valida| Grade[Calificar y marcar submitted]
    Grade --> Result[Resultado]
```

## D08 - Integridad y penalización

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as Flask
    participant D as SQLite
    participant T as Owner teacher
    B->>F: POST integrity event JSON
    F->>D: validate own in progress attempt
    F->>D: increment counter and insert event
    T->>F: GET result
    F->>D: fetch owned attempt and timeline
    F-->>T: contextual review and raw details
    Note over T,F: Telemetry is an indicator not proof
    opt Manual decision
        T->>F: POST penalty points reason CSRF
        F->>D: validate owner submitted and cap
        F->>D: insert auditable penalty
    end
    opt Revoke
        T->>F: POST revoke CSRF
        F->>D: mark inactive actor and time
    end
```

## D09 - Resultados y exportaciones

```mermaid
flowchart LR
    Filters[Filtros docente] --> Query[Query submitted con teacher_id]
    Query --> Dashboard[Dashboard y KPIs]
    Query --> CSV[CSV filtrado]
    Query --> XLSX[XLSX Results]
    XLSX --> Events[Integrity Events por attempt IDs]
    Attempt[Attempt autorizado] --> Result[Vista resultado]
    Attempt --> PDF[PDF en idioma snapshot]
    Result --> Penalty[Proyeccion de nota ajustada]
    PDF --> Penalty
```

## D10 - Despliegue recomendado

```mermaid
flowchart LR
    Browser -->|TLS| Proxy[Reverse proxy]
    Proxy --> WSGI[WSGI server]
    WSGI --> App[Flask]
    App --> DB[(SQLite volume)]
    App --> Audio[(Audio volume)]
    DB --> Backup[Encrypted backup]
    Audio --> Backup
    Monitor[Monitoring] --> Proxy
    Monitor --> WSGI
```

## D11 - CI y calidad

```mermaid
flowchart TD
    Change[Cambio] --> Compile[py_compile]
    Change --> JSCheck[node check por archivo]
    Compile --> Tests[pytest q]
    JSCheck --> Tests
    Tests --> Docs[Check links and Mermaid fences]
    Docs --> Security[Review CSRF role ownership snapshots]
    Security --> Manual[Manual browser responsive i18n]
    Manual --> Gate{Release gates}
    Gate -->|Pass| Release[Release candidate]
    Gate -->|Fail| Fix[Corregir]
    Fix --> Compile
```

No existe configuración CI en el repositorio; este workflow es **recomendado** y usa comandos locales reales.

## D12 - Incidente y restore

```mermaid
flowchart TD
    Detect[Detectar] --> Contain[Contener]
    Contain --> Preserve[Preservar DB audio logs]
    Preserve --> Assess[Evaluar alcance y datos]
    Assess --> Select[Elegir backup compatible]
    Select --> Restore[Restaurar DB y audio aislados]
    Restore --> Verify[Integrity foreign keys smoke tests]
    Verify -->|Fail| Select
    Verify -->|Pass| Reopen[Reabrir servicio]
    Reopen --> Notify[Notificar si aplica]
    Notify --> Postmortem[Postmortem y acciones]
```

## D13 - Estado de attempt

```mermaid
stateDiagram-v2
    [*] --> NotStarted
    NotStarted --> InProgress: start valid and snapshot
    InProgress --> InProgress: refresh resume draft invalid submit
    InProgress --> Submitted: valid server submission
    Submitted --> Submitted: view result report penalty projection
    Submitted --> [*]
```

No existe estado cancelado/expirado. Una asignación desactivada después del start sigue visible por el intento existente en portal según la consulta implementada.

## D14 - Estado de exam y version

```mermaid
stateDiagram-v2
    [*] --> DraftExam: create with version A
    DraftExam --> PublishedExam: usable active version
    PublishedExam --> DraftExam: unpublish
    DraftExam --> ArchivedExam: archive
    PublishedExam --> ArchivedExam: archive and disable assignments
    state Version {
        [*] --> ActiveVersion
        ActiveVersion --> ArchivedVersion: guards pass
        ArchivedVersion --> ActiveVersion: restore
    }
```

No hay restore de examen archivado en la UI actual; sí existe restore de version.

## D15 - Preparación docente

```mermaid
sequenceDiagram
    participant T as Teacher
    participant F as Flask
    participant D as SQLite
    T->>F: create or import own questions
    F->>D: insert with teacher_id
    T->>F: create exam
    F->>D: insert exam and version A
    T->>F: select questions for version
    F->>D: validate owner subject and listening source
    T->>F: assign section mode
    F->>D: upsert assignment
    T->>F: publish
    F->>D: require usable active version
```

## D16 - Resolución estudiante

```mermaid
sequenceDiagram
    participant S as Student
    participant B as Browser JS
    participant F as Flask
    participant D as SQLite
    S->>F: authenticate and acknowledge rules
    S->>F: start assignment
    F->>D: allocate and snapshot
    F-->>B: clean question payload
    S->>B: answer and navigate
    B->>F: integrity signals
    B->>F: submit all answers with CSRF
    F->>D: validate snapshot and grade
    F-->>S: result and optional PDF
```
