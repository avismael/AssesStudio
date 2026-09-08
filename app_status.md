# Application Health Check

**Snapshot date:** 2026-09-07

## Overall Status
Healthy: core teacher, student, and exam flows are implemented and covered by tests.

## What Is Working
- Teacher/admin flows
- Student exam rendering with hidden answers/scripts
- Exam versioning and attempt snapshots
- Concurrent submit protection
- Local, self-hosted UI assets

## Key Capabilities
- Teacher/admin authentication and account management
- Teacher setup and application settings
- Subjects, categories, and question bank management
- Exam creation, versioning, archive/restore, and export routes
- Student exam start/submit flow with attempt tracking
- Listening questions with audio/TTS support
- CSV import paths for students and questions
- Integrity-event telemetry in the student exam UI

## Architecture
- Backend: Flask application in `app.py`
- Database: PostgreSQL via a shared connection layer in `database.py`
- UI: server-rendered templates under `templates/`
- Frontend behavior: `static/js/exam.js`, `static/js/ui.js`, `static/js/student_guard.js`
- Canonical styling: `static/css/dashboard.css`

## Security / Integrity
- Passwords are hashed.
- Mutations are POST + CSRF protected.
- Ownership checks are server-side.
- Student exam HTML does not expose correct answers or listening scripts initially.
- One submitted/in-progress attempt per `(student_id, assignment_id)` is enforced.
- Random exam version allocation is intended to remain stable across refresh/login/reconnect.

## Verified Signals
Relevant coverage includes:
- exam payload hides answers
- schema and route existence checks
- concurrent submit idempotency
- listening-question editor preview behavior
- local asset usage checks

## Operational Notes
- `DATABASE_URL` is required.
- Tests require `TEST_DATABASE_URL`.
- The app does not create schema on import.
- Expected setup order: migrations -> bootstrap -> run app.

## Watchouts
- Some route helpers in `app.py` have limited direct test coverage.
- Update this file after schema, security, or route changes.
