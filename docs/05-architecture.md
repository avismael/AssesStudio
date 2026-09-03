# 05 - Arquitectura técnica

| Campo | Valor |
|---|---|
| Estado | Implementado con PostgreSQL, Alembic y Docker Compose |
| Versión | 2.0 |
| Fecha | 2026-08-16 |
| Decisiones | [ADRs](13-adrs.md) |

## Contexto del sistema

```mermaid
flowchart LR
    Student[Estudiante] -->|HTTPS HTML y formularios| System[Assessment Studio]
    Teacher[Docente] -->|HTTPS HTML y exportaciones| System
    Admin[Administrador] -->|HTTPS configuracion| System
    System --> DB[(PostgreSQL)]
    System --> Audio[(volumen uploaded_audio)]
    Browser[Web Speech API del navegador] -. TTS opcional .-> Student
```

Assessment Studio es un monolito server-rendered. No hay API pública, broker, worker ni servicio de identidad externo. El endpoint JSON de integridad y el endpoint TTS son interfaces internas de la misma aplicación.

## Contenedores y módulos

```mermaid
flowchart TB
    subgraph Browser[Browser]
        Jinja[HTML Jinja]
        ExamJS[exam.js]
        UIJS[ui.js]
        Guard[student_guard.js]
        CSS[style.css y dashboard.css]
    end
    subgraph Flask[Proceso Flask]
        Routes[Rutas app.py]
        Auth[Auth roles CSRF]
        Domain[Asignacion snapshot validacion grading]
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
    Auth --> PostgreSQL[(PostgreSQL)]
    Domain --> PostgreSQL
    Reports --> PostgreSQL
    Domain --> Files[(static audio)]
```

## Límites de responsabilidad

| Área | Responsabilidad |
|---|---|
| `app.py` | App Flask, defaults post-migración, sesiones, auth, autorización, validación, grading, import/export |
| `database.py` | Pool psycopg acotado, filas dict y frontera transaccional |
| `migrations/` | Esquema PostgreSQL versionado por Alembic |
| `policy_defaults.py` | Defaults de reglas compartidos por app y seed |
| `seed.py` | Fixtures de desarrollo reejecutables; verifica migración y nunca crea esquema |
| `templates/` | Presentación Jinja; no decide ownership ni respuesta correcta |
| `static/js/exam.js` | Interacción de pregunta, draft local, navegación y telemetría |
| `static/js/ui.js` | Navegación, modales, toasts, confirmaciones y formularios genéricos |
| `static/js/student_guard.js` | Disuasión básica fuera del examen |
| `static/css/` | Layout responsive, tokens y componentes |
| `tests/` | Regresiones unitarias/integración Flask/markup/export |

## Ciclo de request

1. El entrypoint ejecuta `alembic upgrade head` y `bootstrap.py` antes de iniciar Gunicorn; importar `app.py` no muta esquema.
2. La ruta obtiene sesión y, cuando corresponde, pasa por `teacher_required` o `admin_required`.
3. Las mutaciones de formularios llaman `verify_csrf()`, salvo los gaps actuales documentados abajo.
4. La ruta vuelve a resolver IDs y ownership en PostgreSQL.
5. Las reglas de negocio se ejecutan en servidor.
6. La respuesta renderiza Jinja, redirige, devuelve JSON o genera archivo.
7. `add_security_headers()` agrega headers y `no-store` a superficies sensibles.

## Autenticación, sesión y CSRF

Flask usa cookie de sesión firmada con `SECRET_KEY`, `HttpOnly`, `SameSite=Lax` y `Secure` por default. El login exitoso hace `session.clear()`, establece identidad/rol y genera token CSRF. Las contraseñas se verifican con Werkzeug. Las rutas decoradas con `teacher_required` vuelven a comprobar que la cuenta existe y está activa; `admin_required` incluye esa comprobación.

El dashboard `/teacher` revalida manualmente la cuenta activa. `GET /result/<attempt_id>` y `GET /report/<attempt_id>.pdf` permiten alternativamente al student owner o al teacher owner; la rama docente consulta `teachers.is_active` en cada lectura y limpia una sesión de una cuenta desactivada antes de denegar acceso.

El CSRF usa token aleatorio en sesión y comparación constante para formularios. La norma objetivo es POST+CSRF para toda mutación, pero el estado actual tiene tres excepciones explícitas: el POST de login `/teacher` no verifica token; `/api/integrity-event` acepta JSON sin token y valida sesión/attempt/student/estado/allowlist; `/teacher/logout` verifica CSRF solo cuando `teacher_authenticated` ya está en sesión y, sin esa marca, limpia la sesión sin token. Son gaps de hardening, no cumplimiento pleno de la norma.

## Tenancy docente y padrón compartido

`question_bank.teacher_id`, `exams.teacher_id` y `attempts.teacher_id` son los roots de ownership. Versiones, selecciones y asignaciones heredan ownership desde `exams`. Penalizaciones exigen que `attempts.teacher_id` y `attempt_penalties.teacher_id` coincidan con el docente actual.

`students` y `sections` son institucionales. `subjects` y `categories` pertenecen a cada docente. Solo admin gestiona el padrón; cada docente gestiona su propio catálogo y settings institucionales. Cambiar esta frontera requiere migración de autorización y datos.

## Ciclo de examen

```mermaid
sequenceDiagram
    participant S as Student
    participant F as Flask
    participant D as PostgreSQL
    S->>F: POST start assignment
    F->>D: validar estudiante seccion examen reglas
    F->>D: buscar intento existente
    alt Existe intento
        D-->>F: mismo attempt y version
    else Primer inicio
        F->>D: buscar allocation
        alt Sin allocation random
            F->>D: lock assignment y contar versiones
            F->>D: insertar allocation estable
        end
        F->>D: leer preguntas de version
        F->>D: insertar attempt con snapshots
    end
    F-->>S: redirect exam
```

### Asignación estable

`start_assigned_exam()` bloquea la fila de `exam_assignments` con `FOR UPDATE` durante el tramo corto de allocation y snapshot. `choose_assignment_version()` reutiliza una allocation existente; en random cuenta versiones usables, toma el mínimo y usa `secrets.choice()` entre empates. La serialización por assignment mantiene el balance y `UNIQUE(assignment_id, student_id)` fija la versión ante requests duplicadas.

### Snapshot

`questions_json` conserva pregunta, answer, datos, categoría, subject y listening source. `exam_version_name`, identidad del estudiante, título/asignatura, labels, idioma y `policy_*` preservan contexto. La vista elimina `answer` y, para TTS, `script`; el servidor conserva ambos para grading/reproducción autorizada.

La compatibilidad legacy de listening es intencional: si `data_json.listening_source` falta, una pregunta con `audio` usa archivo; una pregunta sin audio pero con `script` usa TTS. Una fila legacy script-only sigue siendo usable, se normaliza como TTS al crear/renderizar el snapshot y obtiene el guion solo mediante el endpoint autenticado.

### Frontera de audio

**Implementado:** los uploads se guardan con nombre aleatorio bajo `static/audio` y el HTML usa la URL estática correspondiente. Flask puede servir cualquier archivo de ese directorio sin auth si alguien conoce o descubre su URL; la autorización del intento no protege el fetch del archivo. El nombre aleatorio reduce descubrimiento casual, pero no es control de acceso. El endpoint TTS sí permanece autenticado, attempt/question-scoped y `no-store`.

**Recomendado:** para audio confidencial, mover archivos fuera de `static/` y servirlos mediante un endpoint autenticado, attempt/question-scoped, con autorización y headers de cache; alternativamente usar storage privado con URLs firmadas de corta duración. La implementación actual solo es apropiada para audio no confidencial o donde este riesgo sea aceptado explícitamente.

### Validación y grading

El cliente guía y bloquea saltos hacia delante. El servidor es canónico: `validate_required_answers()` valida contra snapshot; solo después `score_attempt()` califica. Submit bloquea el attempt con `FOR UPDATE`; en error guarda draft y conserva `in_progress`; en éxito el UPDATE exige `status='in_progress'`. Posts concurrentes posteriores son idempotentes y redirigen al mismo resultado.

## i18n

`ui_language` global está en `app_settings`. `get_ui_language()` usa el snapshot del intento para student exam/result y el global en otras rutas. `tr()` utiliza keys inglesas y diccionario español. El contenido académico no se traduce.

## Estadísticas

- Student: asignadas, disponibles, en progreso, completadas, completion rate, media ajustada y próximo examen.
- Teacher: resultados enviados, media académica/ajustada, clean/review, eventos agregados, distribución 0-59/60-79/80-100, exámenes, preguntas y padrón.
- Los filtros visibles calculan un resumen separado; KPIs principales usan todos los resultados del owner.

## Integridad y penalizaciones

`exam.js` registra visibility, blur, pagehide, intentos bloqueados y salida de fullscreen. El servidor bloquea el attempt, incrementa contadores mediante expresiones atómicas y añade `integrity_events` en la misma transacción. La vista docente empareja salida/retorno, humaniza tiempos y conserva payload técnico colapsado.

No existe regla automática de descuento. El owner aplica puntos positivos con motivo y límite a la nota ajustada disponible. La revocación marca actor/fecha. `grade10` queda intacta y la proyección es `max(0, grade10 - sum(active points))`.

## Reportes e importaciones

- PDF: ReportLab, intento individual, idioma snapshot, resumen, integridad y motivos activos; sin clave.
- CSV: resultados filtrados, columnas académicas, categorías/tipos e integridad.
- XLSX: hoja Results más Integrity Events, limitada a los attempt IDs filtrados.
- Import: CSV UTF-8 BOM/UTF-8/Latin-1, coma o punto y coma, aliases bilingües; procesamiento por fila.

## Dependencias

```mermaid
flowchart LR
    Flask --> Werkzeug[Werkzeug hashes y uploads]
    Flask --> Jinja[Jinja templates]
    App[app.py] --> Flask
    App --> Psycopg[psycopg 3 pool]
    Alembic --> PostgreSQL
    App --> Openpyxl[openpyxl XLSX]
    App --> ReportLab[ReportLab PDF]
    Seed[seed.py] --> Psycopg
    Tests[pytest] --> App
    Tests --> Openpyxl
```

## Runtime y despliegue

**Implementado:** `compose.yaml` ejecuta PostgreSQL 17 y la app bajo Gunicorn. El entrypoint migra y bootstrappea antes de workers; PostgreSQL no publica puerto. Los volúmenes nombrados `postgres_data` y `uploaded_audio` persisten datos y audio. `/health/live` comprueba proceso y `/health/ready` ejecuta solo `SELECT 1`.

**Recomendado:** terminar TLS en un reverse proxy, externalizar secretos, automatizar backups/restores y ejecutar pruebas de carga representativas. Los archivos de audio siguen siendo recursos estáticos URL-addressable; el volumen aporta persistencia, no confidencialidad ni backup. Consultar [Operaciones](10-operations-runbook.md).
