# 01 - Producto y negocio

| Campo | Valor |
|---|---|
| Estado | Hechos implementados y opciones recomendadas claramente separados |
| Versión | 1.0 |
| Fecha | 2026-08-16 |

## Contexto y objetivos

Assessment Studio apoya evaluaciones institucionales desde la preparación hasta el reporte. Su objetivo es ofrecer control docente, continuidad histórica y una experiencia estudiantil simple en una instalación administrada por una institución.

### Objetivos implementados

- Compartir secciones, estudiantes, asignaturas y categorías dentro de una institución.
- Aislar preguntas, exámenes e intentos por `teacher_id`.
- Reutilizar preguntas y combinarlas en versiones independientes.
- Mantener versión y preguntas estables durante un intento.
- Automatizar calificación y generar reportes sin revelar la clave.
- Registrar señales de integridad y preservar la revisión humana.

### No objetivos actuales

- Ser una plataforma de aprendizaje completa o un LMS.
- Sustituir procesos disciplinarios institucionales.
- Garantizar prevención absoluta de fraude en navegador.
- Proveer aislamiento entre instituciones.
- Brindar disponibilidad de misión crítica o escalado horizontal.

## Segmentos objetivo

Las valoraciones de ajuste siguientes son **Supuesto, no validado**: no provienen de entrevistas, ventas, pilotos ni métricas de adopción.

| Segmento | Ajuste actual | Necesidades pendientes |
|---|---|---|
| Centro educativo pequeño, una sede | Alto, supuesto no validado | Procedimientos operativos y respaldo |
| Departamento académico con varios docentes | Alto, supuesto no validado | Permisos opcionales por sección |
| Institución con TI local | Medio-alto, supuesto no validado | Servidor WSGI, TLS, monitoreo |
| Red de instituciones/SaaS | Bajo, supuesto no validado | `institution_id`, base de datos de servidor, aislamiento y facturación |
| Evaluación de alto impacto regulada | Bajo, supuesto no validado | Proctoring especializado, controles legales y auditoría formal |

## Modelo de negocio

Estas son **opciones recomendadas**, no capacidades de cobro implementadas:

| Opción | Propuesta | Ventaja | Riesgo/coste |
|---|---|---|---|
| Licencia anual por institución | Instalación y soporte para una sede | Se alinea con el modelo actual | Ingresos y soporte dependen de renovaciones |
| Suscripción por estudiante activo | Precio por volumen | Escala con uso | Requiere medición, facturación y multiinstitución |
| Servicio gestionado | Hosting, respaldo y actualizaciones | Reduce carga de TI escolar | Exige seguridad operativa y SLA |
| Código + soporte profesional | Uso local con contrato de soporte | Menor barrera de entrada | Ingresos menos predecibles |

**Supuesto a validar:** la institución valora más la trazabilidad, el control local y la facilidad de adopción que integraciones extensas con LMS.

## Métricas de valor y KPIs

Ninguna de estas métricas se persiste como analítica de negocio dedicada; algunas pueden calcularse desde datos existentes.

| KPI | Definición | Fuente posible | Estado |
|---|---|---|---|
| Docentes activos mensuales | Docentes con `last_login_at` en el periodo | `teachers` | Calculable, no mostrado |
| Tasa de publicación | Exámenes publicados / exámenes no archivados | `exams` | Calculable |
| Tasa de finalización | Intentos enviados / asignaciones disponibles | `attempts`, `exam_assignments` | Parcialmente mostrada por estudiante |
| Tiempo de preparación | Creación a publicación | timestamps de `exams` | Aproximación; no instrumentado |
| Reutilización de preguntas | Preguntas usadas en más de una versión | `exam_version_questions` | Calculable |
| Éxito de importación | Filas válidas / filas procesadas | Resumen de importación | Solo sesión/UI, no histórico |
| Incidencias de soporte | Tickets por periodo | Sistema externo | No implementado |
| Recuperación verificada | Restauraciones de prueba exitosas | Registro operativo | Recomendado |
| Satisfacción de usuario | Encuesta periódica | Herramienta externa | Supuesto/recomendado |

Las cifras de desempeño académico no deben usarse como único indicador de calidad del producto: dependen del diseño de cada evaluación y de su contexto pedagógico.

## Riesgos de adopción

- Resistencia al cambio desde hojas de cálculo o formularios existentes.
- Confusión entre telemetría técnica y prueba de conducta indebida.
- Carga de mantener padrón, credenciales y catálogo institucional.
- Dependencia de voces TTS del navegador y compatibilidad del dispositivo.
- Calidad variable de preguntas y equivalencia entre versiones.
- Expectativas de concurrencia superiores a SQLite.
- Falta de integración con identidad institucional o LMS.

## Impulsores de coste

| Coste | Variable principal |
|---|---|
| Infraestructura | Usuarios concurrentes, almacenamiento de audio, respaldos |
| Operación | Monitoreo, actualizaciones, pruebas de restauración |
| Soporte | Gestión de cuentas, navegadores, importaciones y capacitación |
| Cumplimiento | Evaluaciones de privacidad, contratos y retención |
| Evolución | Multiinstitución, SSO, PostgreSQL, auditoría y accesibilidad formal |

## Consideraciones de cumplimiento

**Recomendado:** antes de producción, identificar legislación local aplicable a datos estudiantiles, base jurídica del tratamiento, responsables/encargados, plazos de retención, derechos de acceso/corrección, notificación de incidentes y reglas sobre decisiones académicas. No se afirma cumplimiento automático con GDPR, FERPA u otra norma.

La institución debe informar qué telemetría se recopila, con qué propósito y por cuánto tiempo. Una penalización requiere criterio humano, motivo visible en el historial y posibilidad de revisión institucional.

## Restricciones contractuales sugeridas

- No prometer detección infalible de fraude.
- Definir alcance de soporte y navegadores compatibles.
- Definir propiedad, ubicación, respaldo y eliminación de datos.
- Declarar límites de capacidad acordes con SQLite.
- Establecer procedimiento de exportación al terminar el servicio.
- Separar SLA recomendado de la disponibilidad real de una instalación local.
