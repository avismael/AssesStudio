# Assessment Studio

Plataforma institucional bilingüe de evaluaciones construida con Flask, Jinja y PostgreSQL. Permite múltiples cuentas docentes, catálogo por docente, padrón institucional administrado por el admin, bancos de preguntas reutilizables, exámenes con versiones, asignaciones por sección, un intento estable por estudiante, calificación automática, listening, revisión de integridad, penalizaciones manuales auditables y exportaciones PDF/CSV/XLSX.

## Estado actual

- **Implementado:** una institución lógica con docentes múltiples.
- **Compartido:** `students` y `sections`.
- **Propio por docente:** `subjects`, `categories`, `question_bank`, `exams`, `attempts` y sus resultados.
- **Garantías:** allocation estable, snapshot al iniciar, respuestas obligatorias y grading server-side.
- **Integridad:** la telemetría es un indicador, no una prueba; las penalizaciones son manuales, justificadas, revocables y no alteran la nota académica original.
- **No implementado:** SaaS multiinstitución, SSO, ventanas de examen, API pública o escalado horizontal.

La fuente de verdad completa está en [`docs/README.md`](docs/README.md). Los manuales de uso en español y ejemplos CSV están en [`userdirections/README.md`](userdirections/README.md). Las reglas obligatorias para cambios están en [`AGENTS.md`](AGENTS.md).

## Inicio con Docker

```bash
cp .env.example .env
# Reemplazar todos los secretos/credenciales placeholder de .env
docker compose up -d --build --wait
```

Abrir `http://127.0.0.1:5000`. `.env.example` desactiva `SESSION_COOKIE_SECURE` únicamente para este HTTP local; producción debe usar TLS y valor `1`. Compose ejecuta migraciones Alembic y el bootstrap idempotente antes de Gunicorn. PostgreSQL no publica puerto; `postgres_data` y `uploaded_audio` son volúmenes persistentes. Un volumen NO es un backup.

Para desarrollo local, `compose.override.yaml` monta el código fuente dentro del contenedor y activa `gunicorn --reload`, así que los cambios en la app se reflejan sin reconstruir la imagen.

### Cómo ejecutar

1. Crear y completar el archivo de variables de entorno:

```bash
cp .env.example .env
```

2. Levantar la base y la app:

```bash
docker compose up -d --build
```

3. Ver los logs de la app cuando haga falta:

```bash
docker compose logs -f app
```

4. Detener el entorno:

```bash
docker compose down
```

Con el override de desarrollo activo, los cambios del código se recargan automáticamente sin reconstruir la imagen.

### Implementación Docker

- `Dockerfile`: construye la imagen de la app con Python 3.13 slim, instala dependencias y deja listo el contenedor para producción.
- `compose.yaml`: levanta `db` (PostgreSQL 17) y `app`, con red interna para la base y volúmenes persistentes para datos y audio.
- `docker-entrypoint.sh`: espera a que la base esté lista, ejecuta `alembic upgrade head`, luego `python bootstrap.py` y finalmente arranca `gunicorn`.
- Variables obligatorias: `DATABASE_URL`, `SECRET_KEY`, `TEACHER_ADMIN_EMAIL` y `TEACHER_ADMIN_PASSWORD`.
- Variables recomendadas: `POSTGRES_PASSWORD`, `TEACHER_ADMIN_NAME`, `INSTITUTION_NAME`, `APP_HOST_PORT`, `GUNICORN_WORKERS`, `GUNICORN_THREADS`.

Si querés operar en local con Docker, ese es el flujo soportado por el repositorio.

## Instalación local

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export DATABASE_URL=postgresql://assessment:password@127.0.0.1:5432/assessment
alembic upgrade head
python bootstrap.py
flask --app app run --host 127.0.0.1 --port 5000
```

`app.py` no crea esquema al importarse. Ejecutar primero `alembic upgrade head` y después `python bootstrap.py`; el bootstrap usa un advisory lock y solo crea defaults/admin si faltan.

## Configuración

Consultar [`.env.example`](.env.example) y la [guía de desarrollo](docs/08-development-guide.md#configuración). La aplicación lee variables de entorno; no carga automáticamente un archivo `.env`.

Antes de usar datos reales, definir como mínimo:

```text
SECRET_KEY
DATABASE_URL
TEACHER_ADMIN_NAME
TEACHER_ADMIN_EMAIL
TEACHER_ADMIN_PASSWORD
```

`DATABASE_URL` es obligatorio y PostgreSQL es el único runtime soportado. Si la contraseña contiene caracteres reservados de URI, usar su valor percent-encoded en `DATABASE_URL`; `POSTGRES_PASSWORD` conserva el valor raw. Consultar pool y Gunicorn en [Operaciones](docs/10-operations-runbook.md).

## Datos demo

```bash
python seed.py --confirm-development-database
python seed.py --confirm-development-database --no-results
python seed.py --confirm-development-database --keep-settings
python seed.py --confirm-development-database --clean
```

El seed exige confirmación explícita, una base ya migrada y escribe bajo `AUDIO_DIR`. No crea esquema. Imprime credenciales demo; nunca ejecutarlo contra producción. Detalles en la [guía de desarrollo](docs/08-development-guide.md#seed).

## Verificación

```bash
python -m py_compile app.py seed.py policy_defaults.py
node --check static/js/exam.js
node --check static/js/ui.js
node --check static/js/student_guard.js
TEST_DATABASE_URL=postgresql://.../assessment_test pytest -q
```

La estrategia, matriz manual y gates están en [docs/09-quality-strategy.md](docs/09-quality-strategy.md).

## Documentación

- [Manuales de usuario y ejemplos de importación](userdirections/README.md)
- [Documento maestro de la aplicación](docs/15-documento-de-la-aplicacion.md)
- [Resumen ejecutivo](docs/00-executive-summary.md)
- [Producto, negocio y requisitos](docs/01-product-and-business.md)
- [Arquitectura y datos](docs/05-architecture.md)
- [Seguridad y privacidad](docs/07-security-privacy.md)
- [Operaciones](docs/10-operations-runbook.md)
- [Referencia completa de rutas](docs/11-api-route-reference.md)
- [Diagramas](docs/12-diagrams.md)
- [ADRs](docs/13-adrs.md) y [glosario, gobierno y roadmap](docs/14-glossary-governance-roadmap.md)
