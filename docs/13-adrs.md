# 13 - Registros de decisiones arquitectónicas

| Campo | Valor |
|---|---|
| Estado | Aceptado, refleja arquitectura actual |
| Versión | 1.0 |
| Fecha | 2026-08-16 |

## ADR-001 - Monolito Flask con SQLite

**Estado:** Superseded por ADR-011. Flask/Jinja monolítico permanece; SQLite no.

**Contexto:** se requiere una aplicación local/institucional simple, server-rendered y con pocas dependencias operativas.

**Decisión:** mantener Flask/Jinja/JavaScript vanilla y SQLite en un único servicio.

**Consecuencias:** despliegue y backup simples; cambios rápidos en `app.py`. A cambio, `app.py` concentra responsabilidades, SQLite limita concurrencia de escritura y no hay escalado horizontal directo.

**Alternativa futura:** PostgreSQL y módulos/services separados cuando capacidad, testabilidad o multiinstitución lo justifiquen.

## ADR-002 - Tenancy docente con padrón institucional compartido

**Estado:** Aceptado.

**Decisión:** `question_bank`, `exams` y `attempts` tienen `teacher_id`; `students`, `sections`, `subjects` y `categories` son compartidos. Admin gestiona catálogo/settings, pero no obtiene bypass de resultados owned.

**Consecuencias:** el mismo estudiante recibe exámenes de varios docentes y se evita duplicar catálogo. Todos los docentes pueden gestionar el padrón compartido. Un SaaS necesita `institution_id` antes de varias escuelas.

## ADR-003 - Snapshot de preguntas al iniciar

**Estado:** Aceptado.

**Decisión:** copiar preguntas completas, incluida respuesta server-side, a `attempts.questions_json` al start.

**Consecuencias:** edición posterior no cambia intento; grading reproducible. Aumenta tamaño de DB y duplica contenido sensible, por lo que backup/authorization son críticos.

## ADR-004 - Asignación de versión estable y balanceada

**Estado:** Aceptado.

**Decisión:** persistir allocation por student/assignment; para random elegir con `secrets.choice` entre versiones usables de menor conteo.

**Consecuencias:** estabilidad ante refresh y distribución uniforme por assignment. PostgreSQL serializa el tramo de asignación con `FOR UPDATE`; unique evita doble allocation persistida.

## ADR-005 - Validación de respuestas canónica en servidor

**Estado:** Aceptado.

**Decisión:** cliente guía navegación; servidor repite validación estructural contra snapshot antes de grading.

**Consecuencias:** requests manipulados no saltan preguntas. Cliente y servidor duplican reglas, por lo que las pruebas parametrizadas deben mantener paridad.

## ADR-006 - Penalizaciones manuales, no automáticas

**Estado:** Aceptado.

**Decisión:** separar telemetría de decisión académica. Solo owner aplica puntos positivos con motivo; puede revocar; raw grade no cambia.

**Consecuencias:** mayor equidad/auditoría y posibilidad de apelación. Requiere capacitación y política institucional; no elimina sesgo humano.

## ADR-007 - Iconos SVG locales Phosphor

**Estado:** Aceptado.

**Decisión:** sprite local, macro Jinja y licencia MIT vendorizada desde `@phosphor-icons/core 2.1.1`.

**Consecuencias:** funcionamiento offline, consistencia y sin tracking/CDN de iconos. Cada icono nuevo requiere añadir símbolo y mantener atribución.

## ADR-008 - CSS tokenizado en tres capas

**Estado:** Aceptado.

**Decisión:** primitives -> semantic -> component en `dashboard.css`, con aliases legacy para `style.css`.

**Consecuencias:** evolución visual coherente y breakpoints centralizados. La coexistencia con CSS legacy contiene duplicación; nuevas reglas deben preferir tokens semánticos.

## ADR-009 - Idioma institucional global y snapshot por intento

**Estado:** Aceptado.

**Decisión:** admin selecciona `es`/`en` global. Cada attempt guarda `ui_language`, `policy_version`, `policy_accepted_at` y texto localizado.

**Consecuencias:** experiencia institucional consistente e historia estable. No soporta preferencia individual ni contenido académico bilingüe paralelo.

## ADR-010 - Migraciones aditivas in-process

**Estado:** Superseded por ADR-011.

**Decisión:** `init_db()` crea y añade columnas/índices al startup; no hay migration framework.

**Consecuencias:** upgrades simples y legacy preservado. No existe historial versionado ni rollback; FKs no pueden añadirse retroactivamente con el patrón actual. Una evolución destructiva requiere herramienta/plan dedicado.

## ADR-011 - PostgreSQL canónico y migraciones Alembic

**Estado:** Aceptado e implementado.

**Contexto:** SQLite y DDL al importar limitaban concurrencia, hacían carreras de startup posibles y duplicaban schema entre app/seed. La migración parte de una base PostgreSQL vacía; no se requiere importar SQLite.

**Decisión:** PostgreSQL es el único runtime. `database.py` expone psycopg 3 con pool acotado y filas dict. Alembic es la única autoridad DDL. El entrypoint ejecuta migraciones antes de Gunicorn y `bootstrap.py` crea defaults/admin bajo advisory lock. `seed.py` exige una revisión actual y no crea schema.

**Consecuencias:** transacciones/locks e índices soportan workers concurrentes; hay historial versionado y una frontera de conexiones explícita. PostgreSQL pasa a ser dependencia operativa obligatoria. Los timestamps y JSON snapshot siguen en TEXT para preservar comportamiento; JSONB/timestamptz serían migraciones futuras, no cambios cosméticos.

## ADR-012 - Contenedores y persistencia separada

**Estado:** Aceptado e implementado.

**Decisión:** `compose.yaml` ejecuta app+PostgreSQL, sin puerto público de DB, con healthchecks y volúmenes nombrados `postgres_data`/`uploaded_audio`. Gunicorn se ajusta por entorno.

**Consecuencias:** recrear contenedores conserva DB/audio y el arranque es reproducible. Los volúmenes NO son backup; operación debe usar `pg_dump` y copia externa/verificada del audio. El audio continúa siendo estático URL-addressable hasta una decisión separada de media privada.

## Gobierno de ADRs

Crear un ADR cuando cambien fronteras de tenancy, persistencia, identidad, seguridad, snapshot, grading, i18n o despliegue. No reescribir una decisión histórica: marcarla superseded y enlazar el ADR nuevo. Cambios puramente visuales dentro del sistema vigente no necesitan ADR.
