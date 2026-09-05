# 03 - Requisitos funcionales y no funcionales

| Campo | Valor |
|---|---|
| Estado | Implementado salvo etiqueta explícita |
| Versión | 1.0 |
| Fecha | 2026-08-16 |

## Roles y permisos

| Capacidad | Admin | Teacher | Student |
|---|---:|---:|---:|
| Gestionar docentes | Sí | No | No |
| Configuración institucional y reglas | Sí | No | No |
| Crear/editar catálogo compartido | Sí | Solo lectura | No |
| Gestionar padrón compartido | Sí | Sí | No |
| Gestionar banco/exámenes propios | Sí, como owner | Sí | No |
| Ver resultados propios del docente | Sí, sin bypass global | Sí | Solo intentos propios |
| Aplicar penalización | Solo si es owner | Solo si es owner | No |
| Resolver examen | No | No | Sí |

Un administrador no obtiene acceso transversal a contenido de otros docentes. Su rol agrega administración institucional, no un bypass de tenancy.

## Requisitos funcionales

| ID | Requisito | Estado | Evidencia principal |
|---|---|---|---|
| FR-001 | Autenticar docentes y estudiantes con correo/contraseña hasheada | Implementado | `/teacher`, `/start`, Werkzeug |
| FR-002 | Forzar cambio de clave estudiantil cuando corresponda | Implementado | `/student/password`, `must_change_password` |
| FR-003 | Mantener roles `admin` y `teacher` | Implementado | `teachers.role`, decoradores |
| FR-004 | Compartir padrón, secciones y catálogo en una institución | Implementado | consultas sin `teacher_id` por diseño |
| FR-005 | Aislar banco, exámenes e intentos por `teacher_id` | Implementado | ownership en rutas y filtros |
| FR-006 | Gestionar siete tipos de pregunta | Implementado | `TYPE_LABELS`, formularios, scoring |
| FR-007 | Importar estudiantes y preguntas desde CSV bilingüe | Implementado | rutas `/import`, alias de headers |
| FR-008 | Omitir filas inválidas/duplicadas sin sobrescribir | Implementado | loops de importación y resumen |
| FR-009 | Crear varios exámenes y versiones por asignatura | Implementado | tablas y rutas de exámenes |
| FR-010 | Asignar examen a sección en modo fijo o aleatorio balanceado | Implementado | `exam_assignments`, `choose_assignment_version()` |
| FR-011 | Mantener la asignación de versión estable | Implementado | `student_exam_allocations` unique |
| FR-012 | Limitar a un intento por estudiante/asignación | Implementado | índice parcial y recuperación de intento |
| FR-013 | Crear snapshot completo al iniciar | Implementado | `attempts.questions_json` y contexto |
| FR-014 | Exigir aceptación de reglas vigentes por sesión | Implementado | `rules_acknowledged()` y rutas |
| FR-015 | Capturar idioma, versión y texto de política en intento | Implementado | campos `policy_*`, `ui_language` |
| FR-016 | No exponer respuesta correcta ni script TTS en HTML inicial | Implementado | `clean_question()`, endpoint TTS |
| FR-017 | Exigir respuesta estructuralmente válida para avanzar/enviar | Implementado | `exam.js`, `validate_required_answers()` |
| FR-018 | Calificar siempre en servidor contra snapshot | Implementado | `score_attempt()` después de validación |
| FR-019 | Registrar señales de integridad permitidas | Implementado | API, contadores y `integrity_events` |
| FR-020 | Tratar telemetría como indicador y nunca penalizar automáticamente | Implementado | flujo manual separado |
| FR-021 | Aplicar penalización manual con motivo, owner y revocación | Implementado | `attempt_penalties` y rutas |
| FR-022 | Preservar nota académica original | Implementado | proyección `adjusted_grade10()` |
| FR-023 | Filtrar resultados y exportar CSV/XLSX | Implementado | `result_filter_values()`, export routes |
| FR-024 | Generar PDF por intento sin clave | Implementado | `/report/<attempt_id>.pdf` |
| FR-025 | Archivar sin romper intentos históricos | Implementado | flags y snapshots |
| FR-026 | Mostrar dashboards con estadísticas derivadas | Implementado | `student_dashboard_stats()`, `teacher_dashboard_stats()` |

**Compatibilidad listening legacy:** para preguntas existentes sin `data_json.listening_source`, la presencia de `audio` mantiene reproducción por archivo; una fila script-only se interpreta como TTS. Esta fallback es comportamiento soportado y debe preservarse en migraciones, snapshots y edición.

## Comportamiento bilingüe

**Implementado:** `app_settings.ui_language` selecciona globalmente `es` o `en`. `tr()` traduce claves literales y Jinja recibe `t()`. Plantillas CSV, mensajes JS y reportes PDF se localizan. El texto creado por usuarios no se traduce.

Al iniciar un intento, `ui_language` queda en snapshot. El examen y su PDF usan ese idioma aunque la configuración global cambie. Las reglas se almacenan en español e inglés; el intento conserva el texto localizado aceptado.

**Limitación:** el catálogo y las preguntas no poseen campos bilingües paralelos. Una misma pregunta no cambia de idioma automáticamente.

## Reglas de validación de respuesta

| Tipo | Validez estructural | Calificación |
|---|---|---|
| `multiple_choice`, `true_false`, `listening` | Valor no vacío incluido en choices del snapshot | Igualdad con `answer` |
| `short_answer` | Texto no blanco | Normalización de espacios/case o exacta si `case_sensitive` |
| `numeric` | Número finito, admite coma decimal | Diferencia <= tolerancia |
| `order` | Marcada como tocada y permutación completa sin duplicados | Lista idéntica al orden correcto |
| `matching` | Todos los lados, opciones permitidas y sin repetir | Mapa idéntico a `answer` |

Los exports imprimibles (`PDF`, `Markdown`, `DOCX`) preservan el contenido del snapshot, pero barajan de forma determinística las opciones/ítems de cada pregunta para no revelar el orden original.

## Requisitos no funcionales

| ID | Requisito | Estado/medida actual |
|---|---|---|
| NFR-SEC-01 | Contraseñas nunca en texto plano | Implementado con hashes Werkzeug/PBKDF2 compatible en seed |
| NFR-SEC-02 | Mutaciones con POST+CSRF | Norma objetivo; gaps actuales en login teacher, API JSON de telemetría y logout teacher condicional |
| NFR-SEC-03 | Autorización server-side e aislamiento | Implementado; requiere regresión continua |
| NFR-SEC-04 | No cachear superficies estudiantiles sensibles | Implementado con `Cache-Control: no-store` en rutas relevantes |
| NFR-UX-01 | Responsive a 100% de zoom | Implementado por CSS; requiere matriz manual |
| NFR-UX-02 | Inputs móviles >=16px | Implementado bajo 768px |
| NFR-UX-03 | Navegación enfoca pregunta, no top | Implementado con `scrollIntoView()` y foco de heading |
| NFR-A11Y-01 | Teclado, foco visible, reduced motion y semántica | Parcialmente implementado; auditoría WCAG formal recomendada |
| NFR-PERF-01 | Respuesta adecuada para institución pequeña | Supuesto; no existe benchmark ni SLA |
| NFR-REL-01 | Migraciones aditivas | Implementado con creación/`ALTER TABLE` condicional |
| NFR-REL-02 | Seed reejecutable sin borrar datos reales | Implementado para IDs/prefijos demo; revisar antes de producción |
| NFR-OPS-01 | Recuperación por respaldo | Recomendado; no automatizado |
| NFR-COMP-01 | Retención y privacidad institucional | Recomendado; no automatizado |

## Invariantes de aceptación

1. No se entrega `answer` ni `script` TTS en el HTML inicial del examen.
2. No existe más de un intento con `assignment_id` para el mismo estudiante.
3. Una asignación aleatoria existente no cambia por refresh, login o reconexión.
4. La edición del banco o versión no altera `questions_json` iniciado.
5. Toda lectura/escritura docente de contenido propio aplica `teacher_id` o parent ownership.
6. Los archivos y reportes no incluyen datos de otro docente.
7. Las penalizaciones son manuales, justificadas, revocables y no cambian `grade10`.
8. La telemetría se comunica como indicador, no como prueba.

## Matriz de trazabilidad resumida

| Requisitos | Casos de uso | Pruebas existentes |
|---|---|---|
| FR-001..005 | UC-A01..A05, UC-S01 | login, setup role, dashboard tenancy, penalty cross-teacher |
| FR-006..008 | UC-R03, UC-Q01..Q03 | scoring, CSV multi-type, listening source, clone |
| FR-009..013 | UC-E01..E05, UC-S05 | schema, route archive/restore, one-attempt, login/start |
| FR-014..018 | UC-S03, UC-S06..S08 | policy lifecycle, language snapshot, required validation, no-skip |
| FR-019..022 | UC-I01..I03 | event presentation, owner-only rendering, penalties |
| FR-023..026 | UC-O01..O02 | export values, PDF, dashboard stats |

La cobertura detallada y los vacíos están en [09 - Estrategia de calidad](09-quality-strategy.md).
