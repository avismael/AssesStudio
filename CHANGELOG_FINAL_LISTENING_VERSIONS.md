# Final refinements — Listening sources & version archive

## Listening questions
- Each Listening question can use either a prerecorded audio file or browser speech synthesis (TTS).
- Browser-voice mode requires a script and supports Auto, en-US, es-MX, and es-ES language hints.
- The TTS script is not rendered in the initial exam HTML. It is requested from an authenticated, no-cache endpoint only when Play is pressed.
- Question-bank CSV import now accepts `FuenteAudio` and `IdiomaVoz` columns. A Listening row is usable only when its selected source is actually available.
- Existing Listening questions remain backward compatible: audio questions continue as audio; script-only legacy questions are treated as browser voice.

## Exam versions
- Active exam versions now have an Archive action with SweetAlert/native confirmation.
- Archived versions appear in a separate section and can be restored.
- Historical attempts remain intact because attempts already store the question snapshot and version name.
- A fixed version used by an active section assignment cannot be archived until that assignment is changed/removed.
- A published exam with active assignments cannot be left without at least one usable active version.
