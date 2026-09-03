# Manuales de usuario de Assessment Studio

## Alcance y vigencia

Esta suite está dirigida a administradores institucionales, docentes, estudiantes y personal de apoyo que usa la aplicación. Describe el comportamiento implementado y verificado en el código al **16 de agosto de 2026**. Si la interfaz cambia, debe revisarse esta documentación; ante una diferencia, prevalece la aplicación desplegada y su configuración institucional.

Assessment Studio tiene tres roles reales: `admin`, `teacher` y estudiante. Un administrador también dispone de las funciones docentes sobre su propio contenido, pero no obtiene una vista global para abrir o editar directamente bancos, exámenes o resultados de otros docentes. Las secciones y los estudiantes son institucionales y los administra solo el rol `admin`; las asignaturas y categorías pertenecen a cada docente.

## Navegación rápida

| Necesidad | Documento |
|---|---|
| Administrar la institución y cuentas docentes | [Manual del administrador](manual-administrador.md) |
| Preparar y calificar evaluaciones | [Manual del docente](manual-docente.md) |
| Ingresar, resolver y consultar resultados | [Manual del estudiante](manual-estudiante.md) |
| Importar el padrón estudiantil | [Importación de estudiantes](importacion-estudiantes.md) |
| Importar los siete tipos de pregunta | [Importación de preguntas](importacion-preguntas.md) |
| Usar GPT, Gemini u otra IA de forma responsable | [Guía de IA generativa](inteligencia-artificial-generativa.md) |
| Preparar fuentes y contexto antes de solicitar contenido | [Ficha de fuentes y contexto](ficha-fuentes-contexto.md) |
| Descargar archivos listos para probar | [Ejemplos CSV](examples/README.md) |

## Principios comunes

- Las cuentas, permisos y autorizaciones se validan en el servidor.
- El padrón, las secciones y los estudiantes son institucionales y los administra el rol `admin`.
- Las asignaturas y categorías son propias de cada docente.
- Cada docente solo administra su banco, exámenes e intentos.
- Las claves correctas y los guiones de listening no aparecen en el HTML inicial del examen.
- La telemetría de integridad es un indicador técnico, no una prueba automática de conducta indebida.
- Archivar oculta registros de la gestión habitual, pero conserva la compatibilidad con intentos e informes históricos.
- Las contraseñas no se pueden recuperar: solo se muestran al crearlas y luego se restablecen.

## Soporte

El estudiante debe acudir a su docente para restablecer su contraseña o resolver una asignación. El docente debe escalar al administrador los cambios de catálogo o configuración. El administrador debe escalar al responsable técnico los respaldos, restauraciones, incidentes, secretos, TLS y cambios de infraestructura.
