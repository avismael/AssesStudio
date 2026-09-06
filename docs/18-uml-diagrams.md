# 18 - Diagramas UML

| Campo | Valor |
|---|---|
| Estado | Consolidado a partir de la implementación verificada |
| Versión | 1.0 |
| Fecha | 2026-09-05 |

## Propósito

Este documento concentra los diagramas UML más útiles para entender el sistema operativo: contexto, componentes y secuencias clave. Evita forzar un diagrama de clases donde no aporta valor real.

## Diagrama de contexto

```mermaid
flowchart LR
    Student[Estudiante] -->|HTTPS HTML + formularios| App[Assessment Studio]
    Teacher[Docente] -->|HTTPS HTML + exportaciones| App
    Admin[Administrador] -->|HTTPS HTML| App
    App --> DB[(PostgreSQL 17)]
    App --> Audio[(uploaded_audio)]
    Browser[Browser JS] -. TTS opcional .-> Speech[Web Speech API]
```

## Diagrama de componentes

```mermaid
flowchart TB
    subgraph Browser[Browser]
        Jinja[Jinja HTML]
        ExamJS[static/js/exam.js]
        UIJS[static/js/ui.js]
        Guard[static/js/student_guard.js]
        CSS[static/css]
    end

    subgraph FlaskApp[Flask modular monolith]
        Core[app.py core]
        Routes[routes/teacher_*.py]
        Domain[Asignacion snapshot grading]
        Auth[Sesion auth CSRF ownership]
        Export[openpyxl y reportlab]
    end

    subgraph Infra[Infraestructura]
        WSGI[Gunicorn]
        Compose[Docker Compose]
        DB[(PostgreSQL 17 + psycopg 3/pool)]
        Mig[Alembic]
    end

    Jinja --> Core
    ExamJS --> Core
    UIJS --> Core
    Guard --> Jinja
    Core --> Auth --> DB
    Routes --> Auth
    Core --> Domain --> DB
    Core --> Export --> DB
    Compose --> WSGI
    Compose --> DB
    WSGI --> FlaskApp
    Mig --> DB
```

## Secuencia: inicio de asignación y snapshot

```mermaid
sequenceDiagram
    participant S as Estudiante
    participant F as Flask
    participant D as PostgreSQL

    S->>F: POST /student/exams/<assignment_id>/start
    F->>D: validar estudiante, seccion, reglas y assignment
    F->>D: buscar intento previo
    alt Existe intento
        D-->>F: mismo attempt y misma version
    else Primer inicio
        F->>D: elegir o reusar version estable
        F->>D: insertar allocation persistente
        F->>D: construir snapshot del attempt
    end
    F-->>S: redirect /exam
```

## Secuencia: revisión docente y exportación

```mermaid
sequenceDiagram
    participant T as Docente
    participant F as Flask
    participant D as PostgreSQL

    T->>F: GET /teacher/results/<attempt_id>
    F->>D: validar ownership y cargar attempt
    F->>D: cargar integrity_events y penalties
    F-->>T: vista de resultado
    opt Exportacion PDF
        T->>F: GET /report/<attempt_id>.pdf
        F->>D: reconstruir payload sin respuestas correctas
        F-->>T: PDF
    end
```

## Secuencia: envío del intento

```mermaid
sequenceDiagram
    participant S as Estudiante
    participant B as Navegador
    participant F as Flask
    participant D as PostgreSQL

    S->>B: completa respuestas
    B->>F: POST /submit con CSRF
    F->>D: validar snapshot y requerimientos
    alt Invalido
        F->>D: guardar draft y mantener in_progress
        F-->>B: error de validacion
    else Valido
        F->>D: calificar y cerrar attempt
        F-->>B: resultado
    end
```

## Lectura recomendada

- [05 - Arquitectura técnica](05-architecture.md)
- [11 - Referencia de rutas Flask](11-api-route-reference.md)
- [12 - Catálogo de diagramas](12-diagrams.md)
