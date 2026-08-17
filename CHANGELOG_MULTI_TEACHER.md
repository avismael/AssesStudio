# Multi-Teacher + Exam UX Update

## Added
- Teacher accounts with email/password.
- Administrator role for teacher-account management.
- Teacher ownership on question bank, exams and attempts/results.
- Teacher account self-service password change.
- Development seed with one admin and three subject teachers.
- OpenCode-ready `AGENTS.md` and complete `docs/` package.

## Changed
- Teacher login no longer uses the shared PIN as the normal authentication flow.
- Existing unowned assessment data is backfilled to the bootstrap teacher during migration.
- Student/section roster remains institutional/shared.
- Subject/category catalog remains institutional/shared and administrator-managed.
- Exam Next/Previous navigation scrolls to the newly displayed question instead of page top.
- Exam sidebar is reduced to progress, compact navigation and integrity state.

## Compatibility
- Database changes are additive.
- Back up `data/results.db` before upgrading an existing installation.
