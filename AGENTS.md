# AGENTS.md — Assessment Studio

Compact working rules for OpenCode sessions in this repo.

## Read first
- `docs/README.md` is the technical source of truth; `docs/11-api-route-reference.md` is the route source of truth.
- `README.md` is the short operational entrypoint; `userdirections/README.md` covers user-facing manuals.
- This repo does **not** auto-load `.env`; export vars yourself or use Docker Compose.

## Must-not-break behavior
- Multi-teacher Flask/Jinja/PostgreSQL app.
- `students` and `sections` are shared institutional data; `subjects`, `categories`, `question_bank`, `exams`, `attempts`, and results are teacher-scoped.
- One submitted/in-progress attempt per `(student_id, assignment_id)`.
- Random exam version allocation stays stable across refresh/login/reconnect.
- Starting an exam creates a snapshot; later bank/version edits must not change that attempt.
- Never expose correct answers or listening scripts in the initial student exam HTML.
- Passwords stay hashed; mutations stay POST + CSRF; ownership checks stay server-side.

## Repo structure
- `app.py`: routes, auth, grading, exports, runtime bootstrap.
- `database.py`: psycopg pool and transaction boundary.
- `migrations/`: Alembic schema.
- `templates/`: server-rendered UI; keep business/security decisions here.
- `static/js/exam.js`: exam interaction/telemetry only.
- `static/js/ui.js`: shared UI helpers.
- `static/js/student_guard.js`: student-browser deterrence.
- `static/css/dashboard.css`: canonical design tokens/system layer.
- `seed.py`: destructive dev fixture loader; never use on a real DB.
- `tests/`: `test_core.py`, `test_postgres_concurrency.py`, `test_user_manuals.py`.

## Setup quirks
- `app.py` does not create schema on import.
- Required order: `alembic upgrade head` -> `python bootstrap.py` -> run app.
- Docker Compose already runs migrations + bootstrap in `docker-entrypoint.sh`.
- `DATABASE_URL` is mandatory and PostgreSQL is the only supported runtime.
- Test runs require `TEST_DATABASE_URL`; `tests/conftest.py` drops and recreates `public`, so never point it at a live DB.
- `seed.py` requires `--confirm-development-database`, writes under `AUDIO_DIR`, and is destructive.

## Commands worth remembering
```bash
python -m py_compile app.py seed.py policy_defaults.py
node --check static/js/exam.js
node --check static/js/ui.js
node --check static/js/student_guard.js
TEST_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/assessment_test pytest -q
flask --app app run --host 127.0.0.1 --port 5000
cp .env.example .env && docker compose up -d --build --wait
```

## Change hygiene
- Inspect the smallest set of routes/tables/templates/JS/CSS that the request touches.
- Make the smallest compatible change; keep server-side checks.
- Add or adjust tests/static checks when behavior changes.
- Update docs when schema or user-visible behavior changes.
