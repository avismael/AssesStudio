# AGENTS.md — Assessment Studio

Working contract for AI coding agents modifying this repository. Source of truth for product behavior is `docs/README.md`; for routes it is `docs/11-api-route-reference.md`.

## Product
Bilingual Flask + Jinja + PostgreSQL assessment platform: multiple teacher accounts, shared institutional rosters (`students`, `sections`, `subjects`, `categories`), reusable question banks, exams with versions, section assignments, stable random version allocation, one attempt per student, server-side grading, listening (uploaded audio or browser TTS), integrity telemetry, and PDF/CSV/XLSX export.

## Critical gotchas (easy to get wrong)
- **No `.env` auto-loading.** The app reads env vars only; it never loads `.env` (no python-dotenv). Export vars yourself or run via Docker Compose, which injects them.
- **Schema is never created on import.** `app.py` does not build schema. Order is mandatory: `alembic upgrade head` → `python bootstrap.py` (creates defaults/admin, idempotent, advisory-locked) → run. Docker Compose does this automatically in the entrypoint.
- **Tests need an isolated, disposable DB.** `pytest` via `tests/conftest.py` requires `TEST_DATABASE_URL`, enforces a `test_/_test/_test_` name boundary, and **drops & recreates `public` schema** on every run. Never point it at an application database.
- **`seed.py` is destructive dev tooling.** It requires `--confirm-development-database`, writes under `AUDIO_DIR`, and must never run against production. Never run it on the default/current database for validation; isolate DB and `AUDIO_DIR` (see README) instead.
- **PostgreSQL is the only supported runtime.** `DATABASE_URL` is mandatory; URL-encode URI credentials (raw password goes in `POSTGRES_PASSWORD`).

## Non-negotiable invariants
1. Never expose correct answers or listening scripts in the initial student exam HTML.
2. Never store plaintext passwords; use Werkzeug hashing.
3. One submitted/in-progress attempt per `(student_id, assignment_id)`.
4. A random version allocated to a student stays stable across refresh/login/reconnect.
5. Starting an exam creates a question snapshot; later bank/version edits must not alter that attempt.
6. Teacher-owned data (`question_bank`, `exams`, `attempts`) is scoped by `teacher_id`.
7. `students` and `sections` are shared institutional roster data, usable across teachers.
8. Archived records stay compatible with historical attempts and reports.
9. Student exam pages keep anti-copy/context-menu/devtools defenses and integrity telemetry.
10. CSV imports validate rows and skip invalid/duplicate records; never silently overwrite.
11. UI stays usable at 100% zoom and responsive on phone/tablet/desktop.
12. Student question navigation focuses/scrolls to the new question, never page top.

## Architecture boundaries
- `app.py`: Flask routes, runtime bootstrap (`bootstrap_runtime_data`), auth, grading, exports.
- `database.py`: psycopg pool and connection/transaction boundary.
- `migrations/`: versioned PostgreSQL schema via Alembic (`script_location = migrations`).
- `templates/`: Jinja views. Keep business/security decisions server-side.
- `static/js/exam.js`: question interaction and exam telemetry only.
- `static/js/ui.js`: generic UI (modals/alerts/navigation).
- `static/js/student_guard.js`: student portal/exam browser deterrence.
- `static/css/dashboard.css`: canonical token/system layer. `static/css/style.css`: shared responsive/legacy.
- `seed.py`: dependency-light fixtures; safe to re-run behind explicit confirmation.
- `tests/`: `test_core.py` (main suite), `test_postgres_concurrency.py` (allocation isolation), `test_user_manuals.py` (docs/CSV examples).

## Teacher tenancy model
- `teachers`: authenticated faculty/admin. `admin` manages teacher accounts and the shared catalog.
- A teacher may only read/write their own questions, exams, and results; re-validate ownership on nested routes (versions, assignments).
- Subjects/categories are an institutional shared catalog — changing this is a schema/authorization migration, not cosmetic.

## Security rules
- All mutations use POST + CSRF verification. Server-side authorization, not hidden buttons.
- Do not trust IDs from forms/JS; do not weaken one-attempt or snapshot rules.
- TTS script endpoint stays authenticated, attempt-scoped, question-scoped, and `no-store`.

## Database changes
Use versioned Alembic migrations. Runtime code and `seed.py` must never create/mutate schema. Plan destructive schema changes in `docs/14-glossary-governance-roadmap.md` or a dedicated migration doc.

## UI conventions
- Forms: 16px input text on mobile, comfortable padding, no clipped modal content.
- Modals: header + scrollable body + reachable footer; dynamic viewport height.
- Destructive actions: SweetAlert confirmation with native `confirm` fallback.
- Exam sidebar is intentionally minimal: progress, compact navigation, integrity indicator.

## Local quality checks
Run before handing back changes (these verify without a DB):
```bash
python -m py_compile app.py seed.py policy_defaults.py
node --check static/js/exam.js
node --check static/js/ui.js
node --check static/js/student_guard.js
```
With dependencies installed, run the full suite against an isolated DB:
```bash
TEST_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/assessment_test pytest -q
```
Local dev server (after `alembic upgrade head` and `bootstrap.py`):
```bash
flask --app app run --host 127.0.0.1 --port 5000
```
Docker (injects env, runs migrations + bootstrap, then Gunicorn; PostgreSQL port not published):
```bash
cp .env.example .env   # fill all secrets; local example disables SESSION_COOKIE_SECURE
docker compose up -d --build --wait
```

## Approach to new work
1. Read `docs/README.md`, this file, and the relevant focused doc; inspect existing route/schema first.
2. State affected tables/routes/templates/JS/CSS.
3. Make the smallest compatible change; keep server-side checks.
4. Add/adjust tests or static validation; update docs/changelog when schema or behavior changes.
5. Do not rewrite unrelated working areas.
