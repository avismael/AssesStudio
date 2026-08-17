# 09 - Estrategia de calidad

| Campo | Valor |
|---|---|
| Estado | Cobertura actual verificada; ampliaciones recomendadas |
| Versión | 1.0 |
| Fecha | 2026-08-16 |

## Objetivos

- Proteger invariantes de seguridad, tenancy, unicidad y snapshot.
- Detectar regresiones de calificación, i18n, exports y UX crítica.
- Validar compatibilidad de schema y seed.
- Separar checks rápidos, integración y exploración manual.

## Pirámide

| Nivel | Actual | Ejemplos |
|---|---|---|
| Estático | Implementado | `py_compile`, `node --check`, inspección de keys/iconos |
| Unitario | Implementado | scoring, validación required, formatting de integridad |
| Integración Flask/SQLite | Implementado | login, start, submit, roles, penalties, exports |
| Render/contrato HTML | Implementado | nav móvil, sprite, tablas responsivas, privacidad timeline |
| E2E browser | No implementado | Recomendado con Playwright/Selenium |
| Accesibilidad automatizada | No implementado | Recomendado con axe en E2E |
| Carga/concurrencia | No implementado | Recomendado antes de ampliar uso |

## Capacidades automatizadas actuales

`tests/test_core.py` usa DB temporal y Flask test client. Cubre:

- catálogo/schema/defaults;
- scoring short/numeric y ocultamiento de answers;
- auth student, cambio obligatorio y rules acknowledgment;
- intento único y snapshots de policy/language;
- CSV de estudiantes/preguntas y listening incompleto;
- TTS sin script en payload inicial;
- version archive/restore routes;
- dashboard tenancy y estadísticas;
- navegación móvil y tablas semánticas responsive;
- sprite Phosphor/licencia/sin dependencia remota;
- traducciones literales y login bilingüe;
- Setup admin-only;
- validación required por tipo, CSRF/ownership y draft inválido;
- penalizaciones owner/cap/revocación y valores CSV/XLSX/PDF;
- presentación bilingüe/timeline de integridad y privacidad student;
- estructura no-skip en `exam.js`.

No se fija aquí un conteo de tests porque cambia con frecuencia. La fuente estable es `pytest -q` en el commit/working tree evaluado.

## Vacíos prioritarios

1. Nested-route IDOR negativo para cada operación de exam/version/assignment/question.
2. Login throttling/cookie flags y seguridad de sesión en entorno de producción.
3. Race real de dos starts simultáneos y lock/concurrency SQLite.
4. HTML completo sin answer/script para cada tipo.
5. CSV formula injection y validación MIME/audio.
6. Migrations desde fixtures legacy y paridad DDL app/seed.
7. E2E de modales, focus trap, navegación, localStorage y fullscreen.
8. Accessibility con lector de pantalla/axe y contraste.
9. PDF multilenguaje con caracteres no ASCII y textos largos.
10. Backup/restore automatizado y `foreign_key_check`.

## Matriz manual

| Área | Desktop | Tablet | Phone | ES | EN | Seguridad |
|---|---:|---:|---:|---:|---:|---:|
| Login admin/teacher/student | X | X | X | X | X | credenciales inválidas/inactivo |
| Dashboard docente | X | X | X | X | X | aislamiento teacher |
| Padrón/importación | X | X | X | X | X | duplicados/CSV inválido |
| Banco/editor/listening | X | X | X | X | X | upload inválido/script no expuesto |
| Exam/version/assignment | X | X | X | X | X | nested ownership |
| Rules/start/resume | X | X | X | X | X | bypass directo/race |
| Preguntas y navegación | X | X | X | X | X | no-skip/draft/refresh |
| Submit/result/PDF | X | X | X | X | X | ownership/single attempt |
| Integridad/penalty | X | X | X | X | X | student no ve raw; manual only |
| Exports | X | N/A | N/A | X | X | filtros y tenant en ambas hojas |

## Planes específicos

### Browser y responsive

- Chrome/Chromium, Firefox y Safari/WebKit recientes según población real.
- 100% de zoom; 320px, 430px, 768px, 1119px, 1120px y desktop amplio.
- Teclado, touch, orientación y viewport con teclado virtual.
- Verificar que modales mantienen footer alcanzable y tablas no pierden acciones.

### Accesibilidad

- Orden de headings/landmarks y skip link.
- Navegación completa por teclado, Escape y retorno de foco.
- Labels, nombres accesibles, estados de error y live regions.
- Contraste en todos los status chips.
- `prefers-reduced-motion` y zoom 200% como prueba adicional recomendada.
- Lector de pantalla para login, dashboard, examen, modal rules y resultado.

### i18n

- Ejecutar prueba de keys literales.
- Alternar global ES/EN y confirmar templates, flashes, JS, CSV y PDF.
- Iniciar en EN, cambiar global a ES y confirmar exam/PDF snapshot EN.
- Probar textos largos de reglas y nombres con acentos.

### Seguridad

- Matriz actor x route x owner/not-owner.
- CSRF faltante/incorrecto en cada POST de formulario.
- IDs manipulados, account inactive, archived parents y status inválidos.
- XSS payloads en nombres, prompts, motivos, CSV y settings.
- Uploads con extensión/MIME/tamaño inesperado.
- Exports sin registros de otro docente.
- Confirmar que telemetría no cambia nota.

## Gates de release

| Gate | Criterio |
|---|---|
| Compilación | `py_compile` y tres `node --check` pasan |
| Tests | `pytest -q` pasa sin fallos |
| Invariantes | Sin answer/script, one attempt, allocation/snapshot estable, tenancy |
| Datos | Migración aditiva probada; backup previo definido |
| UX | Matriz manual del área afectada en tres viewports |
| Seguridad | Review de método, CSRF, rol, ownership y datos sensibles |
| Docs | Ruta/schema/comportamiento/changelog actualizados |
| Operación | Configuración, rollback y health check definidos |

## Severidad de defectos

| Nivel | Definición | Ejemplos | Gate |
|---|---|---|---|
| S0 crítica | Fuga/alteración masiva o acceso arbitrario | answer keys, tenant bypass, RCE | Bloquea release; incidente |
| S1 alta | Pérdida de intento/datos o auth bypass acotado | repetir intento, snapshot roto | Bloquea release |
| S2 media | Función central incorrecta con workaround | export parcial, modal inaccesible | Corregir antes o aceptar formalmente |
| S3 baja | Defecto cosmético/documental | copy, spacing menor | Puede planificarse |

## Trazabilidad

| Riesgo | Requisitos | Casos | Pruebas actuales |
|---|---|---|---|
| Credenciales/auth | FR-001..003 | UC-A01..A03, UC-S01..S02 | password policy/login/setup role |
| Tenancy/IDOR | FR-005, FR-021..024 | UC-Q/E/I/O | dashboard, penalties, result privacy, exports; nested gaps |
| Intento/snapshot | FR-011..015 | UC-S03..S05 | unique index, login/start, rules snapshot |
| Validación/grading | FR-016..018 | UC-S06..S08 | answer hidden, parametrized required, submit |
| Integridad/equidad | FR-019..022 | UC-I01..I03 | event presentation, owner-only, penalty audit |
| UI responsive | NFR-UX/A11Y | todas las journeys | nav/table markup; falta E2E/axe |
| Operación/datos | NFR-REL/OPS | UC-O | schema tests; falta restore/concurrency |

## Resultado de la verificación documental

Ejecución del 2026-08-16 sobre el working tree documentado:

- `python -m py_compile app.py seed.py policy_defaults.py`: pass.
- `node --check static/js/exam.js`: pass.
- `node --check static/js/ui.js`: pass.
- `node --check static/js/student_guard.js`: pass.
- `pytest -q`: pass; consultar la salida del run para el conteo vigente.
- Seed aislado desde copia `mktemp`, con `DATABASE_PATH` temporal y audio escrito solo dentro de la copia: pass; SHA-256 normalizado del workspace completo idéntico antes/después. Ver el [comando seguro exacto](08-development-guide.md#seed).
- Checker Python de documentación: 23 archivos Markdown y 28 bloques Mermaid; destinos relativos, anchors, fences y tipos de bloque válidos.
- `mermaid-cli`: no estaba instalado; no se añadió la dependencia. Se realizó validación estructural y revisión de sintaxis obvia.
