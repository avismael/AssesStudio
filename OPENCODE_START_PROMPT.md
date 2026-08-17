# OpenCode starter prompt

Paste the following when opening this repository in OpenCode:

```text
We are continuing development of Assessment Studio, a multi-teacher Flask/SQLite assessment platform.

Before changing code, read AGENTS.md and docs/README.md, then inspect the files relevant to the request. The documented invariants are mandatory: teacher-owned content/results must be scoped by teacher_id; shared students/sections must remain usable across teachers; one attempt per student+assignment; persistent random version allocation; exam question snapshots; secure password hashes; POST+CSRF mutations; and student exam integrity protections.

For every change:
1. Identify affected routes, tables, templates, JS and CSS.
2. Preserve existing SQLite databases with additive migrations.
3. Keep server-side authorization checks even if UI buttons are hidden.
4. Maintain mobile/tablet/desktop behavior at 100% zoom.
5. Run the validation commands in AGENTS.md.
6. Update documentation when schema/behavior changes.

Do not rewrite unrelated working areas. Prefer small, reversible changes.

Current task:
[WRITE THE TASK HERE]
```
