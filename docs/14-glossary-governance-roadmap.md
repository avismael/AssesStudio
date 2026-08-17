# 14 - Glosario, gobierno, configuración y roadmap

| Campo | Valor |
|---|---|
| Estado | Implementado y roadmap explícito |
| Versión | 1.0 |
| Fecha | 2026-08-16 |

## Glosario

| Término | Definición |
|---|---|
| Assessment Studio | Nombre del producto |
| Subject | Asignatura institucional compartida |
| Category | Unidad de clasificación dentro de un subject |
| Question bank | Preguntas reutilizables owned por docente |
| Exam | Evaluación owned con subject, publicación y versiones |
| Exam version | Selección nombrada/ordenada de preguntas |
| Assignment | Vínculo entre exam y section con modo fixed/random |
| Allocation | Version persistida para un student en un assignment |
| Attempt | Ejecución única con snapshot, answers y resultado |
| Snapshot | Copia histórica de preguntas/contexto al iniciar |
| Raw grade | `grade10` académica antes de penalizaciones |
| Adjusted grade | `max(0, raw grade - active penalties)` |
| Integrity event | Señal técnica del browser; indicador, no prueba |
| Penalty | Deducción manual, motivada, auditable y revocable |
| Owner | Teacher cuyo `teacher_id` controla el dato |
| Shared roster | Students/sections visibles y gestionables institucionalmente |
| Archive | Ocultamiento lógico que preserva historia |
| TTS | Text-to-Speech mediante Web Speech API del navegador |
| CSRF | Cross-Site Request Forgery; token en formularios de mutación |
| IDOR | Acceso inseguro a objetos por ID sin autorización |

## Referencia de settings

Todos se almacenan como TEXT en `app_settings`.

| Key | Default | Gestión | Uso |
|---|---|---|---|
| `institution_name` | `INSTITUTION_NAME` o `Your Institution` | Admin Setup | Branding visible/PDF |
| `assessment_title` | `General Assessment` | Sin campo actual en Setup | Compatibilidad/default fallback |
| `assessment_subtitle` | Texto default | Admin Setup | Login student |
| `listening_max_plays` | `2` | Admin Setup, 1-5 | Límite client-side por render |
| `current_subject_id` | `1` | Legacy/seed | Helpers legacy; no selector principal actual |
| `student_access_mode` | `accounts` | Migración/default | Modo actual único de cuentas |
| `ui_language` | `es` | Admin Setup | UI global `es`/`en` |
| `student_rules_es` | `policy_defaults.py` | Admin Setup | Reglas ES |
| `student_rules_en` | `policy_defaults.py` | Admin Setup | Reglas EN |
| `rules_version` | `1` | Admin Setup/auto bump | Acknowledgment y snapshot |
| `require_rules_acknowledgment` | `1` | Admin Setup | Gate por sesión |
| `rules_updated_at` | vacío | App al guardar | Trazabilidad básica |

Cambiar texto ES o EN hace auto-increment de `rules_version`. Aunque el formulario muestra versión editable, un cambio de texto usa la versión incrementada desde el valor persistido.

## Limitaciones conocidas

| Área | Limitación actual | Estado futuro |
|---|---|---|
| Instituciones | Una institución lógica; sin `institution_id` | Roadmap |
| Base | SQLite sin WAL/busy timeout explícito | Hardening/roadmap PostgreSQL |
| Servidor | `app.run` para desarrollo | Producción requiere WSGI/proxy |
| Auth | Sin rate limiting, MFA, SSO o recuperación autónoma | Roadmap |
| Login docente | POST sin token CSRF | Hardening recomendado |
| API integridad | POST JSON sin token CSRF; usa sesión/ownership/allowlist | Hardening recomendado |
| Logout docente | CSRF solo si la sesión ya marca teacher autenticado | Hardening recomendado |
| Resultado/PDF teacher | Ownership con sesión existente, sin revalidar cuenta activa | Hardening recomendado |
| Cookies | Flags productivos no configurados explícitamente | Hardening recomendado |
| Disponibilidad | Sin due dates/windows/time limits | Roadmap |
| Auditoría | Solo penalties y señales; no admin audit general | Roadmap |
| Integridad | Browser deterrence manipulable/falsos positivos | Limitación inherente |
| Audio | Extensión, no MIME/magic/antivirus; `static/audio` URL-addressable sin auth | Media privada y validación recomendadas |
| CSV | Sin mitigación explícita de formula injection | Hardening recomendado |
| i18n | Global, no preferencia individual; contenido no traducido | Roadmap opcional |
| Analytics | KPIs dashboard básicos, sin item analysis | Roadmap |
| QA | Sin E2E/axe/load/CI config | Roadmap de calidad |
| Health | Sin endpoint dedicado ni logs estructurados | Operación recomendada |
| Retención | Sin purge/anonymization/legal hold | Gobierno institucional |
| Schema parity | FKs/defaults difieren entre initializers | Corrección recomendada |

## Roadmap

Todo este apartado es **Roadmap**, no funcionalidad disponible.

### Fase 1 - Hardening

- Rate limiting/login throttling y cookies productivas.
- CSRF en login/API/logout según threat review y una política consistente.
- Revalidación de cuenta activa en resultado/PDF para sesiones teacher.
- Validación MIME/audio, cuotas y CSV formula safety.
- Alinear DDL `app.py`/`seed.py` y fixtures de migración.
- Logging estructurado, health/readiness y backup automation.
- E2E, accessibility y load tests.
- Auditoría de cambios administrativos.

### Fase 2 - Operación académica

- Availability windows, due dates y time limits server-side.
- Permisos teacher-to-section y periodos académicos.
- Bulk assignment y mejores workflows de catálogo.
- Política de retención/anonymization y exports administrativos.
- Recuperación segura de cuenta/SSO institucional.

### Fase 3 - Escala

- PostgreSQL con migración probada.
- Contenedores/release automation y observabilidad.
- `institution_id` transversal antes de SaaS multi-school.
- Endpoint autenticado/media privada u object storage con URLs firmadas para audio confidencial.
- API/integraciones LMS solo con contrato y auth formal.

### Fase 4 - Analítica

- Item difficulty/discrimination.
- Comparación de equivalencia entre versions.
- Distribuciones por section/category y longitudinales.
- Export/report governance para evitar inferencias injustas.

## Gobierno documental

### Propietarios

| Dominio | Owner recomendado | Revisor |
|---|---|---|
| Producto/negocio | Product owner o dirección académica | Docentes y compliance |
| UX/accesibilidad | Responsable UX | Usuarios y QA |
| Arquitectura/datos | Tech lead | Seguridad/operaciones |
| Seguridad/privacidad | Security/privacy owner | Dirección/TI |
| Operaciones | DevOps/IT owner | Tech lead |
| Rutas/calidad | Equipo de desarrollo | QA |

### Cadencia

- En cada cambio de comportamiento/schema/route/config: actualización en el mismo PR/change.
- Mensual durante desarrollo activo: links, roadmap y known limitations.
- Antes de release: matriz de cobertura, route map, data dictionary y runbook.
- Trimestral en producción: threat model, restore, retención y decisiones.

### Regla de actualización

1. Cambiar código y tests.
2. Actualizar documento fuente del dominio, route map y data model si aplica.
3. Añadir/actualizar ADR para decisiones mayores.
4. Actualizar changelog.
5. Validar links, Mermaid fences y comandos.
6. Cambiar fecha/versión solo cuando el contenido fue revisado.

No duplicar explicaciones completas en varios documentos: enlazar a la autoridad. El código prevalece si hay divergencia, pero la divergencia es un defecto documental que debe corregirse.

## Índice de cambios

- [Multi-Teacher + Exam UX](../CHANGELOG_MULTI_TEACHER.md)
- [Listening sources y version archive](../CHANGELOG_FINAL_LISTENING_VERSIONS.md)
- [Imports y UX](../CHANGELOG_IMPORTS_UX.md)
- [Required answers, rules y penalties](../CHANGELOG_REQUIRED_ANSWERS_RULES_PENALTIES.md)

Los changelogs son históricos y pueden estar en inglés. Esta suite describe el estado consolidado actual.

## Auditoría de la documentación anterior

La colección anterior cubría producto, arquitectura, schema, auth, lifecycle, seguridad, imports, desarrollo, roadmap, rutas, UI y cambios recientes, pero presentaba estos problemas:

- mayoría en inglés pese al contexto bilingüe;
- route map resumido, no verificable ruta por ruta;
- schema sin diccionario completo ni ER;
- ausencia de negocio, personas/casos completos, operaciones, threat model y gobierno;
- diagramas insuficientes;
- informe de fallos histórico que ya afirmaba resolución y duplicaba estado;
- behavior transversal repartido entre documentos sin matriz de cobertura.

Se reemplazaron los 14 documentos anteriores por esta estructura consolidada. Los changelogs raíz se preservaron como historia y se enlazan arriba.
