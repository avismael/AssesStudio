# 11 - Referencia de rutas Flask

| Campo | Valor |
|---|---|
| Estado | Verificado desde `app.app.url_map` y decorators |
| Versión | 1.1 |
| Fecha | 2026-08-16 |

No es una API pública. `Auth` indica sesión requerida; `Owner` indica validación de ownership/parent. `CSRF` aplica a mutaciones de formulario. GET/POST combinados solo mutan en POST. Salvo las excepciones indicadas, las rutas Teacher usan `teacher_required`; las rutas Admin usan `admin_required`, que incluye `teacher_required` y revalida cuenta activa.

## Operación

| Método | Ruta | Auth | Propósito |
|---|---|---|---|
| GET | `/health/live` | Pública | Liveness del proceso; no consulta DB |
| GET | `/health/ready` | Pública | Readiness mediante `SELECT 1`; no migra ni expone configuración |

## Estudiante y resultados

| Método | Ruta | Auth | Owner/rol | CSRF | Propósito |
|---|---|---|---|---|---|
| GET | `/` | Pública | - | - | Login o redirect al dashboard |
| POST | `/start` | Pública | Cuenta estudiante activa | Sí | Autenticar student |
| GET | `/student` | Student | `student_id` activo | - | Asignaciones y rules modal |
| POST | `/student/rules/acknowledge` | Student | Sesión student | Sí | Aceptar versión vigente |
| POST | `/student/exams/<int:assignment_id>/start` | Student | Assignment de su section | Sí | Start/resume, allocation y snapshot |
| GET, POST | `/student/password` | Student | Cuenta propia | En POST | Cambio de clave |
| POST | `/student/logout` | Student | Sesión propia | Sí | Cerrar sesión |
| GET | `/exam` | Student | Attempt en sesión y student owner | - | UI de intento en progreso |
| GET | `/api/listening-script/<question_id>` | Student | Attempt/question own in progress | - | Script TTS on demand, JSON no-store |
| POST | `/api/integrity-event` | Student | Attempt own in progress | No token | Evento JSON allowlisted |
| POST | `/submit` | Student | Attempt own in progress | Sí | Validar/calificar/enviar |
| GET | `/result/<attempt_id>` | Student o teacher activo | Student owner o teacher owner | - | Rama teacher revalida cuenta activa; timeline solo teacher |
| GET | `/report/<attempt_id>.pdf` | Student o teacher activo | Student owner o teacher owner | - | Rama teacher revalida cuenta activa; PDF sin answers |
| POST | `/teacher/results/<attempt_id>/penalties` | Teacher | Attempt owner, submitted | Sí | Penalización manual |
| POST | `/teacher/results/<attempt_id>/penalties/<int:penalty_id>/revoke` | Teacher | Attempt y penalty owner | Sí | Revocar penalización |

## Sesión docente y dashboard

| Método | Ruta | Auth/rol | Owner | CSRF | Propósito |
|---|---|---|---|---|---|
| GET, POST | `/teacher` | Pública en login; revalidación manual en dashboard | Result rows por current teacher | No en login | Sin decorador; autenticar o mostrar dashboard |
| POST | `/teacher/logout` | Condicional según sesión; sin lookup de cuenta | Sesión propia | Solo si `teacher_authenticated` | Sin decorador; siempre limpia sesión |
| GET, POST | `/teacher/account/password` | Teacher | Cuenta propia | En POST | Cambiar clave propia |
| GET, POST | `/teacher/setup` | Admin | Institucional | En POST | Settings, idioma y reglas |
| GET | `/teacher/export.csv` | Teacher | Attempts current teacher y filtros | - | CSV de resultados |
| GET | `/teacher/export.xlsx` | Teacher | Attempts current teacher y filtros | - | XLSX Results + Integrity Events |

**Gaps de seguridad conocidos:** el POST de login docente no verifica CSRF, a diferencia del login student; `/api/integrity-event` muta JSON sin token; y logout docente solo exige token cuando la marca de sesión teacher ya existe. Deben endurecerse sin confundir estas brechas con bypass de contraseña o cross-tenant ownership.

## Padrón compartido

| Método | Ruta | Auth | Scope | CSRF | Propósito |
|---|---|---|---|---|---|
| GET | `/teacher/students` | Teacher | Institucional | - | Lista/filtros de padrón |
| GET | `/teacher/students/import/template` | Teacher | Institucional | - | Plantilla CSV localizada |
| POST | `/teacher/students/import` | Teacher | Institucional | Sí | Importar filas válidas |
| POST | `/teacher/sections/new` | Teacher | Institucional | Sí | Crear section |
| POST | `/teacher/sections/<int:section_id>/edit` | Teacher | Institucional | Sí | Editar section |
| POST | `/teacher/sections/<int:section_id>/archive` | Teacher | Institucional | Sí | Archivar section vacía |
| POST | `/teacher/students/new` | Teacher | Institucional | Sí | Crear cuenta student |
| POST | `/teacher/students/<int:student_id>/edit` | Teacher | Institucional | Sí | Editar cuenta |
| POST | `/teacher/students/<int:student_id>/password` | Teacher | Institucional | Sí | Restablecer clave |
| POST | `/teacher/students/<int:student_id>/toggle` | Teacher | Institucional | Sí | Activar/desactivar |
| POST | `/teacher/students/<int:student_id>/archive` | Teacher | Institucional | Sí | Archivo lógico |

## Banco de preguntas

| Método | Ruta | Auth | Owner | CSRF | Propósito |
|---|---|---|---|---|---|
| GET | `/teacher/questions` | Teacher | `question_bank.teacher_id` | - | Lista/filtros |
| GET | `/teacher/questions/import/template` | Teacher | - | - | Plantilla CSV localizada |
| POST | `/teacher/questions/import` | Teacher | Inserts current teacher | Sí | Importar preguntas |
| GET, POST | `/teacher/questions/new` | Teacher | Inserts current teacher | En POST | Crear pregunta |
| GET, POST | `/teacher/questions/<qid>/edit` | Teacher | Question owner | En POST | Editar pregunta |
| POST | `/teacher/questions/<qid>/toggle` | Teacher | Question owner | Sí | Cambiar `is_active` |
| POST | `/teacher/questions/<qid>/duplicate` | Teacher | Source owner | Sí | Copia inactiva own |
| POST | `/teacher/questions/<qid>/archive` | Teacher | Question owner | Sí | Archivo lógico |
| POST | `/teacher/questions/bulk` | Teacher | UPDATE constrained by owner | Sí | Activate/deactivate/archive |

## Catálogo institucional

| Método | Ruta | Auth/rol | Scope | CSRF | Propósito |
|---|---|---|---|---|---|
| GET | `/teacher/catalog` | Teacher | Lectura institucional, counts own | - | Subjects/categories |
| POST | `/teacher/subjects/new` | Admin | Institucional | Sí | Crear subject |
| POST | `/teacher/subjects/<int:subject_id>/edit` | Admin | Institucional | Sí | Editar subject |
| POST | `/teacher/subjects/<int:subject_id>/archive` | Admin | Institucional | Sí | Archivar subject/categories/questions |
| POST | `/teacher/categories/new` | Admin | Institucional | Sí | Crear category |
| POST | `/teacher/categories/<int:category_id>/edit` | Admin | Institucional | Sí | Editar/mover category |
| POST | `/teacher/categories/<int:category_id>/archive` | Admin | Institucional | Sí | Archivar category/questions |

## Exámenes, versiones y asignaciones

Todas usan `teacher_required`; `exam_row()` exige `exams.teacher_id=current_teacher_id()` y las rutas nested validan parent/exam IDs.

| Método | Ruta | Owner | CSRF | Propósito |
|---|---|---|---|---|
| GET | `/teacher/exams` | Lista current teacher | - | Exam manager |
| POST | `/teacher/exams/new` | Inserta current teacher | Sí | Crear exam + version A |
| GET | `/teacher/exams/<int:exam_id>` | Exam owner | - | Detalle |
| POST | `/teacher/exams/<int:exam_id>/edit` | Exam owner | Sí | Editar |
| POST | `/teacher/exams/<int:exam_id>/publish` | Exam owner | Sí | Publicar/ocultar |
| POST | `/teacher/exams/<int:exam_id>/archive` | Exam owner | Sí | Archivar y desactivar assignments |
| POST | `/teacher/exams/<int:exam_id>/versions/new` | Exam owner | Sí | Crear version |
| POST | `/teacher/exams/<int:exam_id>/versions/<int:version_id>/edit` | Exam owner + version parent | Sí | Renombrar |
| POST | `/teacher/exams/<int:exam_id>/versions/<int:version_id>/duplicate` | Exam owner + version parent | Sí | Duplicar selección |
| POST | `/teacher/exams/<int:exam_id>/versions/<int:version_id>/archive` | Exam owner + version parent | Sí | Archivar con guards |
| POST | `/teacher/exams/<int:exam_id>/versions/<int:version_id>/restore` | Exam owner + version parent | Sí | Restaurar |
| GET | `/teacher/exams/<int:exam_id>/versions/<int:version_id>/questions` | Exam owner + version parent | - | Selector own/same subject |
| POST | `/teacher/exams/<int:exam_id>/versions/<int:version_id>/questions` | Exam owner + version parent | Sí | Reemplazar selección validada |
| POST | `/teacher/exams/<int:exam_id>/assign` | Exam owner | Sí | Upsert assignment por section |
| POST | `/teacher/exams/<int:exam_id>/assignments/<int:assignment_id>/remove` | Exam owner + assignment parent | Sí | Desactivar assignment |

## Administración de docentes

| Método | Ruta | Rol | CSRF | Propósito/guard |
|---|---|---|---|---|
| GET | `/teacher/users` | Admin | - | Lista cuentas |
| POST | `/teacher/users/new` | Admin | Sí | Crear teacher/admin |
| POST | `/teacher/users/<int:teacher_id>/edit` | Admin | Sí | Editar; conserva último admin activo |
| POST | `/teacher/users/<int:teacher_id>/password` | Admin | Sí | Restablecer hash |
| POST | `/teacher/users/<int:teacher_id>/toggle` | Admin | Sí | No self-disable ni último admin |

## Headers globales

Todas las respuestas reciben `nosniff`, frame deny, no-referrer, Permissions Policy y CSP. Paths `/exam`, `/student`, APIs de integridad/TTS y `/result/` reciben `Cache-Control: no-store`. El PDF `/report/` no entra en ese prefijo no-store actualmente; el download se genera en memoria y la política del proxy/browser debe revisarse.
