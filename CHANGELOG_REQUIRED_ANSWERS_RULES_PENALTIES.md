# Required Answers, Rules, and Penalties

- Added canonical required-answer validation and CSRF/student ownership enforcement for submission.
- Added one guarded client navigation path with finite numeric, touched-order, and unique matching semantics.
- Completed literal Spanish translation coverage and localized dynamic JavaScript/CSV guidance.
- Restricted global Setup to administrators and simplified the public student login.
- Added configurable bilingual, versioned student rules with session acceptance and attempt snapshots.
- Added owner-only, reasoned, auditable, revocable grade-point penalties while preserving raw academic values.
- Added raw, penalty, and adjusted grade output to result pages, dashboards, PDF, CSV, and XLSX.
- Added regression tests for security, validation, i18n, policy lifecycle, snapshots, tenancy, penalties, exports, and no-skip structure.
- Fixed PDF report generation to load active penalty totals and reasons for the authorized attempt.
- Enforced contiguous forward navigation so dot and question-type jumps cannot pass unanswered intermediate questions.
- Policy text changes now auto-increment the current rules version and invalidate prior session acknowledgments.
- Shared dependency-free policy defaults now keep application initialization and development seeding synchronized.
