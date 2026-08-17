# 08 - Guía de desarrollo

| Campo | Valor |
|---|---|
| Estado | Implementado/verificado contra archivos del repositorio |
| Versión | 2.0 |
| Fecha | 2026-08-16 |

## Requisitos

- Python 3 compatible con Flask 3.
- Node.js solo para `node --check` de JavaScript.
- Dependencias de `requirements.txt`, incluidas Flask, psycopg 3/pool, Alembic, SQLAlchemy solo para migraciones, Gunicorn, exports y pytest.
- PostgreSQL 17 recomendado; Docker Engine + Compose simplifican el entorno local.

## Instalación local

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

`run_linux_mac.sh` y `run_windows.bat` requieren `DATABASE_URL`; instalan dependencias, ejecutan Alembic/bootstrap y arrancan el servidor Flask de desarrollo. No aprovisionan PostgreSQL. Preferir Compose para el runtime completo.

## Configuración

Exportar variables desde un entorno seguro; la aplicación no carga `.env` por sí sola y no depende de `python-dotenv`.

| Variable | Default de código | Uso |
|---|---|---|
| `SECRET_KEY` | `dev-change-this-secret-key` | Firma de sesión; cambiar en producción |
| `INSTITUTION_NAME` | `Your Institution` | Default inicial de settings |
| `PORT` | `5000` | Puerto de `app.run` |
| `FLASK_DEBUG` | distinto de `1` | Debug solo si vale `1` |
| `TEACHER_ADMIN_NAME` | `Administrator` | Bootstrap cuando `teachers` está vacía |
| `TEACHER_ADMIN_EMAIL` | `admin@assessment.local` | Login bootstrap |
| `TEACHER_ADMIN_PASSWORD` | `ChangeMe123` | Clave bootstrap de desarrollo |
| `DATABASE_URL` | obligatorio | DSN PostgreSQL canónico |
| `AUDIO_DIR` | `static/audio` | Directorio de uploads; `/app/static/audio` en Compose |
| `SESSION_COOKIE_SECURE` | `1` | Cookie solo HTTPS; usar `0` únicamente en HTTP local aislado |
| `SESSION_COOKIE_SAMESITE` | `Lax` | `Lax`, `Strict` o `None`; `None` requiere cookie segura |
| `DB_POOL_MIN_SIZE` / `DB_POOL_MAX_SIZE` | `1` / `10` | Pool psycopg acotado por proceso |
| `DB_POOL_TIMEOUT` | `10` | Espera máxima por conexión |
| `GUNICORN_WORKERS` / `GUNICORN_THREADS` | `2` / `4` | Concurrencia del contenedor |
| `GUNICORN_TIMEOUT` | `60` | Timeout de worker |

Ejemplo seguro para una DB temporal:

```bash
export DATABASE_URL=postgresql://assessment:password@127.0.0.1:5432/assessment_dev
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export SESSION_COOKIE_SECURE=0  # solo para este servidor HTTP local
export TEACHER_ADMIN_NAME="Local Administrator"
export TEACHER_ADMIN_EMAIL="local-admin@example.invalid"
export TEACHER_ADMIN_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
alembic upgrade head
python bootstrap.py
flask --app app run --host 127.0.0.1 --port 5000
```

Importar `app.py` no crea esquema ni defaults. `bootstrap.py` debe ejecutarse después de la migración. No usar credenciales demo, placeholders ni defaults públicos con datos reales.

`POSTGRES_PASSWORD` es texto raw para PostgreSQL. Si la contraseña contiene caracteres reservados como `@`, `:`, `/`, `%`, `#` o `?`, percent-encodearla al construir `DATABASE_URL`; no interpolar el valor raw dentro de una URI. Compose exige `DATABASE_URL` explícita para evitar esa ambigüedad.

## Inicialización y migraciones

El esquema se gestiona exclusivamente con Alembic:

```bash
alembic current
alembic upgrade head
alembic downgrade -1  # solo si el downgrade fue probado y es seguro
python bootstrap.py
```

El entrypoint de Docker ejecuta upgrade y bootstrap una sola vez antes de Gunicorn. Readiness nunca migra.

Para añadir una migración:

1. Crear una revisión bajo `migrations/versions/`.
2. Definir upgrade y downgrade explícitos; probar ambos cuando el downgrade sea viable.
3. Mantener `seed.py` como consumidor del esquema, nunca como initializer.
4. Añadir prueba sobre una base PostgreSQL vacía y, para revisiones futuras, desde la revisión anterior.
5. Actualizar [modelo de datos](06-data-model.md), ADR si cambia una frontera y changelog.
6. Evitar DROP/recreate sin plan explícito y respaldo.

## Seed

```bash
python seed.py --confirm-development-database
python seed.py --confirm-development-database --no-results
python seed.py --confirm-development-database --keep-settings
python seed.py --confirm-development-database --clean
```

- Crea cuatro docentes demo, tres subjects, nueve categories, 19 questions, tres sections, 15 students, tres exams con dos versions y assignments.
- Sin `--no-results`, crea 15 attempts demo y eventos.
- Es reejecutable para filas seed; `--clean` elimina datos generados y conserva catálogo/secciones.
- Imprime credenciales demo intencionales al terminal. Ver [README raíz](../README.md#datos-demo), no reutilizarlas en producción.
- Requiere `DATABASE_URL`, revisión Alembic actual y confirmación explícita; recrea passwords/cuentas seed y escribe en `AUDIO_DIR`. `--no-results` no lo convierte en check read-only.

Para validar el seed, usar una base PostgreSQL dedicada cuyo nombre indique test y un directorio de audio temporal:

```bash
tmp_audio="$(mktemp -d)"
DATABASE_URL=postgresql://assessment:password@127.0.0.1:5432/assessment_seed_test alembic upgrade head
DATABASE_URL=postgresql://assessment:password@127.0.0.1:5432/assessment_seed_test \
  AUDIO_DIR="$tmp_audio" python seed.py --confirm-development-database --no-results
```

No ejecutar seed contra una DB de producción ni contra el workspace/default DB solo para validación.

## Ejecución

```bash
python app.py
```

Abrir `http://127.0.0.1:5000`. El servidor incluido es de desarrollo; producción requiere WSGI y proxy.

## Estructura

```text
app.py                 rutas, bootstrap de defaults, auth, dominio, import/export
database.py            pool psycopg y transacciones
migrations/            esquema PostgreSQL versionado
policy_defaults.py     reglas canónicas dependency-free
seed.py                fixtures de desarrollo; requiere schema Alembic actual
templates/             vistas Jinja
static/css/             diseño responsive y tokens
static/js/exam.js       interacción del examen y telemetría
static/js/ui.js         UI genérica
static/js/student_guard.js disuasión del portal
static/icons/           sprite Phosphor y licencia
static/audio/           uploads y audio demo
tests/                  pytest
examples/               plantillas CSV estáticas
docs/                   fuente de verdad
```

## Convenciones de código

- Mantener decisiones de negocio/seguridad en servidor.
- Usar SQL parametrizado; allowlist para fragmentos inevitables.
- Resolver owner por `teacher_id` o parent owned antes de usar IDs.
- Todas las mutaciones de formularios: POST+CSRF.
- Migraciones aditivas y compatibles.
- Archivar antes que borrar datos históricos.
- No añadir compatibilidad legacy especulativa.
- Mantener comentarios breves solo para decisiones no obvias.

## Workflow i18n

1. Escribir key visible en inglés, idioma fuente técnico.
2. Añadir traducción profesional neutral a `TRANSLATIONS_ES`.
3. En Jinja usar `t('Key')`; en Python `tr()`/`flash_ui()`.
4. En JS dinámico, ampliar `exam_js_strings()` o `AS_UI_I18N`.
5. No traducir route/table/column/question type identifiers.
6. Ejecutar prueba de keys literales y probar `ui_language=es/en`.
7. Si el texto pertenece al intento, confirmar snapshot y no solo global setting.

## Añadir un tipo de pregunta

1. Agregar key a `TYPE_LABELS` y aliases CSV.
2. Definir schema JSON de datos/respuesta.
3. Implementar validación de formulario/import.
4. Limpiar payload student en `clean_question()`.
5. Renderizar control en `exam.html` sin answer.
6. Implementar validez cliente y draft en `exam.js`.
7. Implementar validez server en `validate_required_answers()`.
8. Implementar grading en `score_attempt()`.
9. Actualizar exports, i18n, seed, pruebas y documentación.

La validación cliente mejora UX; nunca sustituye la server-canonical.

## Añadir un icono

1. Confirmar que la UI realmente necesita el símbolo.
2. Obtener path de `@phosphor-icons/core 2.1.1` compatible con licencia MIT.
3. Añadir `<symbol id="ph-official-name">` al sprite local.
4. Usar `icon('official-name')`.
5. Mantener `aria-hidden` o `aria-label` según semántica.
6. Ejecutar pruebas de sprite/licencia y dependencia remota.

## Pruebas y checks

```bash
python -m py_compile app.py seed.py policy_defaults.py
node --check static/js/exam.js
node --check static/js/ui.js
node --check static/js/student_guard.js
TEST_DATABASE_URL=postgresql://assessment:password@127.0.0.1:5432/assessment_test pytest -q
```

El `conftest.py` falla antes de importar la app si falta `TEST_DATABASE_URL` o si el nombre no usa un límite explícito `test_`/`_test`. Al iniciar, recrea únicamente el schema `public` de esa base dedicada y ejecuta Alembic/bootstrap.

El resultado de la verificación de esta edición se registra en [09 - Calidad](09-quality-strategy.md#resultado-de-la-verificación-documental).

## Debugging

- Usar base/usuario PostgreSQL separados para pruebas manuales destructivas.
- Trazar route -> helper -> SQL -> template/JS.
- Comprobar sesión, CSRF, estado/archivo y ownership antes de alterar lógica.
- Para esquema: `alembic current`, `\d`/catálogo `information_schema`, `pg_indexes` y consultas de FKs en `pg_catalog`.
- Para i18n: alternar globalmente desde Setup y probar intento ya iniciado.
- Para drafts: revisar `AS_SERVER_DRAFT` y key `assessment-studio:<attempt_id>` en localStorage.

## Contribución y definición de terminado

1. Leer `AGENTS.md` y documentos de dominio.
2. Identificar rutas/tablas/templates/JS afectados.
3. Implementar el cambio mínimo compatible.
4. Añadir prueba positiva y negativa, especialmente ownership.
5. Ejecutar checks y matriz manual relevante.
6. Actualizar docs/changelog en el mismo cambio.
7. Confirmar que no se exponen answer/script y no se debilitan snapshots/unicidad.
8. Documentar migración, rollback y operación si aplica.

Un cambio no está terminado si solo funciona visualmente pero la autorización, migración o regresión histórica no están verificadas.
