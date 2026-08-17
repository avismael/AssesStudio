# 08 - Guía de desarrollo

| Campo | Valor |
|---|---|
| Estado | Implementado/verificado contra archivos del repositorio |
| Versión | 1.0 |
| Fecha | 2026-08-16 |

## Requisitos

- Python 3 compatible con Flask 3.
- Node.js solo para `node --check` de JavaScript.
- Dependencias de `requirements.txt`: `Flask>=3.0,<4`, `openpyxl>=3.1,<4`, `reportlab>=4.0,<5`, `pytest>=8.0,<9`.
- SQLite incluido en Python.

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

También existen `run_linux_mac.sh` y `run_windows.bat`; ambos crean `.venv` si falta, instalan requisitos y ejecutan `python app.py`.

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
| `DATABASE_PATH` | `data/results.db` | Ruta SQLite alternativa |

Ejemplo seguro para una DB temporal:

```bash
export DATABASE_PATH=/tmp/assessment-studio-dev.db
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export TEACHER_ADMIN_NAME="Local Administrator"
export TEACHER_ADMIN_EMAIL="local-admin@example.invalid"
export TEACHER_ADMIN_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
flask --app app run --host 127.0.0.1 --port 5000
```

Estas variables deben existir antes del primer import/startup porque `init_db()` puede crear el bootstrap admin durante el import. No usar credenciales demo, placeholders ni defaults públicos con datos reales. `python app.py` enlaza `0.0.0.0`; limitar a `127.0.0.1` en desarrollo aislado evita exposición accidental.

## Inicialización y migraciones

Importar/ejecutar `app.py` llama `init_db()` automáticamente. La función:

1. Crea directorios DB/audio.
2. Crea tablas ausentes.
3. Inspecciona columnas con `PRAGMA table_info`.
4. Añade columnas mediante `ALTER TABLE ... ADD COLUMN`.
5. Crea bootstrap admin si no hay docentes.
6. Backfillea ownership legacy al primer docente.
7. Migra algunos campos legacy y crea índices/settings.

Para añadir una migración:

1. Definir el DDL de instalación nueva en `init_db()`.
2. Añadir comprobación de columna/índice para instalaciones existentes.
3. Mantener `seed.py:ensure_schema()` en paridad.
4. Añadir prueba de esquema y migración sobre DB legacy representativa.
5. Actualizar [modelo de datos](06-data-model.md), ADR si cambia una frontera y changelog.
6. Evitar DROP/recreate sin plan explícito y respaldo.

## Seed

```bash
python seed.py
python seed.py --no-results
python seed.py --keep-settings
python seed.py --clean
```

- Crea cuatro docentes demo, tres subjects, nueve categories, 19 questions, tres sections, 15 students, tres exams con dos versions y assignments.
- Sin `--no-results`, crea 15 attempts demo y eventos.
- Es reejecutable para filas seed; `--clean` elimina datos generados y conserva catálogo/secciones.
- Imprime credenciales demo intencionales al terminal. Ver [README raíz](../README.md#datos-demo), no reutilizarlas en producción.
- Siempre modifica `DATABASE_PATH` (o `data/results.db` por default), recrea passwords/cuentas seed y escribe `static/audio/seed_three_beeps.wav`; `--no-results` no lo convierte en check read-only.

Para validar el seed sin tocar la DB ni el audio del workspace actual, ejecutar desde una copia temporal. El `DATABASE_PATH` separado aísla SQLite y la copia aísla el `AUDIO_DIR`, que no tiene variable de entorno propia:

```bash
tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT
cp -a . "$tmp_root/qquizz"
(
  cd "$tmp_root/qquizz"
  DATABASE_PATH="$tmp_root/seed-validation.db" python seed.py --no-results
)
```

No ejecutar seed contra una DB de producción ni contra el workspace/default DB solo para validación.

## Ejecución

```bash
python app.py
```

Abrir `http://127.0.0.1:5000`. El servidor incluido es de desarrollo; producción requiere WSGI y proxy.

## Estructura

```text
app.py                 rutas, esquema, auth, dominio, import/export
policy_defaults.py     reglas canónicas dependency-free
seed.py                fixtures y schema bootstrap alternativo
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
pytest -q
```

Opcional, únicamente con aislamiento completo de DB y workspace/audio:

```bash
tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT
cp -a . "$tmp_root/qquizz"
(cd "$tmp_root/qquizz" && DATABASE_PATH="$tmp_root/seed-validation.db" python seed.py --no-results)
```

El resultado de la verificación de esta edición se registra en [09 - Calidad](09-quality-strategy.md#resultado-de-la-verificación-documental).

## Debugging

- Usar `DATABASE_PATH` separada para pruebas manuales destructivas.
- Trazar route -> helper -> SQL -> template/JS.
- Comprobar sesión, CSRF, estado/archivo y ownership antes de alterar lógica.
- Para esquema: `PRAGMA table_info`, `PRAGMA index_list`, `PRAGMA foreign_key_check`.
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
