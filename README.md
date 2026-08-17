# Assessment Studio

Plataforma institucional bilingüe de evaluaciones construida con Flask, Jinja y SQLite. Permite múltiples cuentas docentes, padrón compartido, bancos de preguntas reutilizables, exámenes con versiones, asignaciones por sección, un intento estable por estudiante, calificación automática, listening, revisión de integridad, penalizaciones manuales auditables y exportaciones PDF/CSV/XLSX.

## Estado actual

- **Implementado:** una institución lógica con docentes múltiples.
- **Compartido:** `students`, `sections`, `subjects` y `categories`.
- **Aislado por `teacher_id`:** `question_bank`, `exams`, `attempts` y sus resultados.
- **Garantías:** allocation estable, snapshot al iniciar, respuestas obligatorias y grading server-side.
- **Integridad:** la telemetría es un indicador, no una prueba; las penalizaciones son manuales, justificadas, revocables y no alteran la nota académica original.
- **No implementado:** SaaS multiinstitución, SSO, ventanas de examen, API pública o escalado horizontal.

La fuente de verdad completa está en [`docs/README.md`](docs/README.md). Las reglas obligatorias para cambios están en [`AGENTS.md`](AGENTS.md).

## Instalación local

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export TEACHER_ADMIN_NAME="Local Administrator"
export TEACHER_ADMIN_EMAIL="local-admin@example.invalid"
export TEACHER_ADMIN_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
flask --app app run --host 127.0.0.1 --port 5000
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:TEACHER_ADMIN_NAME = "Local Administrator"
$env:TEACHER_ADMIN_EMAIL = "local-admin@example.invalid"
$env:TEACHER_ADMIN_PASSWORD = python -c "import secrets; print(secrets.token_urlsafe(24))"
flask --app app run --host 127.0.0.1 --port 5000
```

Definir esas cuatro variables **antes del primer import/startup**: `init_db()` crea el primer administrador cuando `teachers` está vacía. Los ejemplos generan secretos nuevos en el shell actual; guardarlos en un gestor seguro si se necesita recuperar la cuenta y no publicarlos en el repositorio. Abrir `http://127.0.0.1:5000`.

Los fallbacks de código (`dev-change-this-secret-key`, `admin@assessment.local`, `ChangeMe123`) existen únicamente para desarrollo local aislado. No iniciar con esos valores en una red compartida ni en producción. `python app.py` enlaza `0.0.0.0`; el comando anterior usa loopback para evitar exposición accidental. El servidor incluido sigue siendo solo para desarrollo.

## Configuración

Consultar [`.env.example`](.env.example) y la [guía de desarrollo](docs/08-development-guide.md#configuración). La aplicación lee variables de entorno; no carga automáticamente un archivo `.env`.

Antes de usar datos reales, definir como mínimo:

```text
SECRET_KEY
TEACHER_ADMIN_NAME
TEACHER_ADMIN_EMAIL
TEACHER_ADMIN_PASSWORD
```

`DATABASE_PATH` permite cambiar la ubicación por defecto `data/results.db`.

## Datos demo

```bash
python seed.py
python seed.py --no-results
python seed.py --keep-settings
python seed.py --clean
```

El seed crea cuentas y contenido exclusivamente para desarrollo, modifica la DB elegida y escribe `static/audio/seed_three_beeps.wav` en el workspace desde el que se ejecuta. Imprime credenciales demo en el terminal. No ejecutarlo contra la DB/workspace actual solo para validar, ni reutilizarlo en producción. Detalles y validación aislada en la [guía de desarrollo](docs/08-development-guide.md#seed).

## Verificación

```bash
python -m py_compile app.py seed.py policy_defaults.py
node --check static/js/exam.js
node --check static/js/ui.js
node --check static/js/student_guard.js
pytest -q
```

La estrategia, matriz manual y gates están en [docs/09-quality-strategy.md](docs/09-quality-strategy.md).

## Documentación

- [Resumen ejecutivo](docs/00-executive-summary.md)
- [Producto, negocio y requisitos](docs/01-product-and-business.md)
- [Arquitectura y datos](docs/05-architecture.md)
- [Seguridad y privacidad](docs/07-security-privacy.md)
- [Operaciones](docs/10-operations-runbook.md)
- [Referencia completa de rutas](docs/11-api-route-reference.md)
- [Diagramas](docs/12-diagrams.md)
- [ADRs](docs/13-adrs.md) y [glosario, gobierno y roadmap](docs/14-glossary-governance-roadmap.md)
