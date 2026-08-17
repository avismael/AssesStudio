# AGENTS.md — Assessment Studio

This file is the working contract for AI coding agents (including OpenCode) modifying this repository.

## Product
Assessment Studio is a bilingual Flask/SQLite assessment platform for teachers and students. It supports shared institutional rosters, multiple teacher accounts, reusable question banks, multiple exams per subject, versions per exam, section assignments, balanced random version allocation, one attempt per student, automatic grading, listening (uploaded audio or browser TTS), integrity event logging, PDF reports, and CSV/XLSX exports.

## Non-negotiable invariants
1. Never expose correct answers or listening scripts in the initial student exam HTML.
2. Never store plaintext passwords. Use Werkzeug password hashing.
3. One submitted/in-progress attempt per `(student_id, assignment_id)`.
4. Once a random version is allocated to a student, it must remain stable across refresh/login/reconnect.
5. Starting an exam creates a question snapshot. Later bank/version edits must not change that attempt.
6. Teacher-owned data must be scoped by `teacher_id` for question bank, exams, and results/attempts.
7. Students and sections are institutional/shared roster data.
8. Archived records must remain compatible with historical attempts and reports.
9. Student exam pages must retain the anti-copy/context-menu/devtools-shortcut protections and integrity telemetry.
10. CSV imports must validate rows and skip invalid/duplicate records rather than silently overwrite data.
11. UI must remain usable at 100% browser zoom and responsive on phone, tablet, and desktop.
12. Student question navigation must focus/scroll to the newly displayed question, never to page top.

## Architecture boundaries
- `app.py`: Flask routes, database initialization/migrations, auth, grading, exports.
- `templates/`: Jinja views. Keep business/security decisions server-side.
- `static/js/exam.js`: question interaction and exam telemetry only.
- `static/js/ui.js`: generic UI behavior, modals/alerts/navigation.
- `static/js/student_guard.js`: student portal/exam browser deterrence.
- `static/css/dashboard.css`: canonical premium token/system layer and dashboard/component styling.
- `static/css/style.css`: shared responsive layouts and legacy-compatible styles built alongside the token layer.
- `seed.py`: dependency-light development fixtures; must be safe to re-run.
- `docs/`: source-of-truth project documentation.

## Teacher tenancy model
- `teachers`: authenticated faculty/admin users.
- `question_bank.teacher_id`, `exams.teacher_id`, `attempts.teacher_id`: tenant ownership.
- A teacher may only read/write their own questions, exams, and results.
- `admin` can manage teacher accounts and the shared institutional catalog.
- `students` and `sections` are shared so the same learner can receive exams from different teachers.
- Subjects/categories are currently an institutional shared catalog. Treat changes to this choice as a schema/authorization migration, not a cosmetic change.

## Security rules
- All mutations use POST and CSRF verification.
- Authorization is checked on the server; hiding buttons is not authorization.
- Validate ownership again on nested routes such as versions and assignments.
- Do not trust IDs coming from forms/JS.
- Do not weaken one-attempt or exam-snapshot rules.
- Keep TTS script endpoint authenticated, attempt-scoped, question-scoped, and `no-store`.

## Database changes
Use additive migrations in `init_db()` and `ensure_column()` patterns. Existing installations must remain upgradeable. Before destructive schema changes, create an explicit migration plan in `docs/14-glossary-governance-roadmap.md` or a dedicated migration document.

## UI conventions
- Forms: 16px input text on mobile, comfortable padding, no clipped modal content.
- Modals: header + scrollable body + reachable footer actions; use dynamic viewport height.
- Destructive actions: SweetAlert confirmation with native confirm fallback.
- Mobile teacher navigation behaves like an app; desktop navigation may collapse.
- Exam sidebar is intentionally minimal: progress, compact navigation, integrity indicator.

## Local quality checks
Run before handing back changes:

```bash
python -m py_compile app.py seed.py policy_defaults.py
node --check static/js/exam.js
node --check static/js/ui.js
node --check static/js/student_guard.js
```

`seed.py` is mutating development tooling, not a read-only quality check. Never run it against the current/default database or a production workspace merely for validation. If seed validation is relevant, isolate both its database and its fixed `static/audio` output by running it from a temporary copy:

```bash
tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT
cp -a . "$tmp_root/qquizz"
(
  cd "$tmp_root/qquizz"
  DATABASE_PATH="$tmp_root/seed-validation.db" python seed.py --no-results
)
```

If dependencies are installed:

```bash
pytest -q
python app.py
```

Then manually test:
- admin login;
- teacher login and isolation;
- student login;
- assigned exam list;
- random/fixed version start;
- refresh/resume;
- next/previous question scrolling;
- submission and single-attempt enforcement;
- results filters/export;
- phone/tablet/desktop layouts.

## How to approach new work in OpenCode
1. Read `docs/README.md`, this file, and the relevant focused document.
2. Inspect existing route/schema before coding.
3. State the tables/routes/templates affected.
4. Make the smallest compatible change.
5. Add/adjust tests or static validation.
6. Update docs and changelog when behavior/schema changes.
