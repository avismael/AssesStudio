# PostgreSQL + Docker migration

Date: 2026-08-16

## Implemented

- Replaced SQLite runtime access with psycopg 3 dict rows and a bounded per-process connection pool.
- Added Alembic revision `20260816_0001` as the only schema authority; importing `app.py` no longer mutates schema.
- Added post-migration, advisory-lock-protected defaults/admin bootstrap.
- Ported application and seed SQL to PostgreSQL placeholders/dialect, `citext`, `RETURNING`, `GREATEST`, PostgreSQL metadata, and psycopg exceptions.
- Serialized allocation/snapshot creation with an assignment row lock, submit with an attempt row lock and conditional state transition, and integrity updates with an attempt row lock plus atomic counters.
- Ported `seed.py` to PostgreSQL. It verifies Alembic, requires explicit development confirmation, honors `AUDIO_DIR`, and remains re-runnable.
- Added production Dockerfile, entrypoint, Compose app/PostgreSQL services, private DB networking, healthchecks, Gunicorn tuning, and named DB/audio volumes.
- Added `/health/live` and `/health/ready`; readiness performs only `SELECT 1`.
- Ported tests to a safety-checked PostgreSQL test database and added real threaded allocation/start and submit concurrency coverage.
- Required an explicit percent-encoded `DATABASE_URL`, made the app port loopback-only by default, and configured secure session-cookie defaults with a documented local HTTP override.
- Revalidated active teacher accounts on result/PDF reads, required canonical ownership/assignment links in the fresh schema, and made demo-attempt cleanup penalty-safe.
- Added a bounded migration retry for PostgreSQL's fresh-volume initialization transition before Gunicorn starts.

## Migration boundary

This release intentionally starts from a new empty PostgreSQL database. No SQLite data migration utility is included. Run `alembic upgrade head` followed by `python bootstrap.py`, or use the Docker entrypoint.

## Verification

- Static Python and JavaScript checks passed.
- PostgreSQL test suite: 66 passed.
- Full seed ran twice with dependent penalties against an isolated migrated PostgreSQL database and `--clean` removed the demo graph safely.
- Docker image/Compose startup and healthchecks passed.
- Database and audio markers survived forced container recreation through the two named volumes.
