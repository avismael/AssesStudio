# 00 - Resumen ejecutivo

| Campo | Valor |
|---|---|
| Estado | Implementado, salvo apartados marcados |
| Versión | 1.0 |
| Fecha | 2026-08-16 |
| Fuentes | `AGENTS.md`, `app.py`, `README.md`, pruebas y vistas actuales |

## Síntesis

Assessment Studio es una aplicación institucional bilingüe para diseñar, asignar, resolver y calificar evaluaciones. Centraliza un padrón compartido de estudiantes y secciones, permite múltiples cuentas docentes y aísla por docente el banco de preguntas, los exámenes y los resultados.

**Implementado:** Flask sirve HTML Jinja y endpoints internos; PostgreSQL conserva configuración, contenido, asignaciones, snapshots, intentos, telemetría y penalizaciones. Psycopg usa pool acotado, Alembic versiona schema y Docker Compose opera app+DB con volúmenes separados. El navegador usa JavaScript vanilla para interacción y señales de integridad. No existe una API pública ni un servicio SaaS multiinstitución.

## Problema

Las evaluaciones gestionadas con archivos dispersos o formularios genéricos dificultan reutilizar preguntas, controlar versiones, asignar de forma estable, mantener trazabilidad histórica y separar el trabajo de varios docentes. Assessment Studio reúne ese ciclo sin depender de servicios externos para su función central.

## Propuesta de valor

- Reutilización de preguntas por asignatura y categoría.
- Múltiples exámenes y versiones con asignación fija o aleatoria balanceada.
- Un intento por estudiante y asignación, reforzado por índice único PostgreSQL y transacciones con locks de fila.
- Snapshot inmutable de preguntas, política, idioma y contexto al iniciar.
- Calificación automática de siete tipos de pregunta.
- Resultados filtrables, PDF y exportación CSV/XLSX.
- Telemetría de integridad como señal revisable, nunca como prueba concluyente.
- Penalizaciones manuales, justificadas, revocables y auditables sin alterar la nota académica original.

## Usuarios y partes interesadas

| Grupo | Interés principal |
|---|---|
| Administrador institucional | Cuentas docentes, catálogo compartido, idioma y reglas globales |
| Docente | Banco propio, exámenes, asignaciones, resultados y revisión de integridad |
| Estudiante | Acceso claro, intento estable, privacidad y resultado comprensible |
| Dirección académica | Consistencia, trazabilidad, adopción y métricas de uso |
| TI/operaciones | Seguridad, respaldo, disponibilidad y capacidad |
| Protección de datos/compliance | Minimización, retención, transparencia y atención de incidentes |

## Alcance actual

**Implementado:** una institución lógica, varias cuentas docentes, padrón y catálogo compartidos, autenticación por correo y contraseña, interfaz global español/inglés, banco de preguntas, exámenes/versiones/asignaciones, intentos, calificación, listening con archivo o TTS, telemetría, penalizaciones y exportaciones.

**Fuera de alcance actual:** multiinstitución real, inscripción docente-sección, ventanas de disponibilidad, recuperación autónoma de contraseñas, SSO, MFA, auditoría administrativa general, API pública, aplicación móvil nativa, pagos, colas de trabajo y alta disponibilidad.

## Principios del producto

1. La seguridad y autorización son decisiones del servidor.
2. El intento iniciado es históricamente estable.
3. La persona estudiante no recibe claves ni scripts de listening en el HTML inicial.
4. La telemetría orienta una revisión humana; no determina culpabilidad.
5. Los datos archivados siguen siendo compatibles con reportes históricos.
6. El diseño debe funcionar a 100% de zoom en teléfono, tableta y escritorio.
7. El software bilingüe mantiene identificadores técnicos en inglés y traduce la experiencia visible.

## Restricciones y riesgos ejecutivos

| Tema | Estado | Consecuencia |
|---|---|---|
| PostgreSQL + Gunicorn | Implementado | Workers concurrentes con pool acotado; requiere tuning y backup profesional |
| Sesiones Flask con cookie firmada | Implementado | Requiere `SECRET_KEY` robusta y TLS en producción |
| Archivos de audio locales | Implementado | Deben incluirse en respaldos y permisos del servidor |
| CDN de SweetAlert2 | Implementado | La confirmación usa `window.confirm` si no hay red; el CSP permite `cdn.jsdelivr.net` |
| Sin límites de login | Implementado como ausencia | Riesgo de fuerza bruta; se recomienda rate limiting |
| Sin `institution_id` | Implementado como modelo único | No operar varias instituciones aisladas en la misma base |
| Telemetría del navegador | Limitación inherente | Puede tener falsos positivos y no detecta dispositivos externos |

## Criterio de éxito

El producto tiene éxito cuando reduce el tiempo de preparación y revisión sin debilitar la equidad, conserva intentos reproducibles y permite a TI recuperar la operación desde un respaldo probado. Las métricas propuestas están en [Producto y negocio](01-product-and-business.md#métricas-de-valor-y-kpis).
