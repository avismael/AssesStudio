# Manual del docente

[Volver al índice](README.md)

## Acceso y alcance

Abra **Acceso docente** o `/teacher` e ingrese con su correo y contraseña. Puede cambiar su propia clave desde la cuenta docente. Si no puede ingresar, solicite al administrador que confirme el estado de la cuenta o restablezca la contraseña.

Su banco de preguntas, exámenes, intentos, resultados, exportaciones y penalizaciones están aislados por docente. El rol administrador no puede usar su privilegio para entrar en el contenido de otro docente. El padrón, las secciones y el catálogo sí son institucionales y compartidos.

## Estudiantes y secciones

En **Estudiantes y secciones** puede buscar y filtrar, crear secciones, agregar estudiantes, editar cuentas, restablecer claves y activar, desactivar o archivar.

- Coordine cambios porque el padrón afecta a todos los docentes.
- El correo es el usuario de acceso y debe ser único, incluso respecto de cuentas archivadas.
- El NIE tampoco puede reutilizarse después de archivar un estudiante.
- Una contraseña temporal se muestra una sola vez.
- Es recomendable exigir cambio de contraseña en el siguiente ingreso.
- Una cuenta inactiva o archivada no puede iniciar sesión.
- Los registros archivados desaparecen de la gestión normal, pero la historia se conserva.

Para cargas masivas use [Importación de estudiantes](importacion-estudiantes.md).

## Banco de preguntas

Cada pregunta pertenece a una asignatura y categoría existentes. Las preguntas se crean en el banco y luego se agregan a las versiones de un examen. Crear o importar una pregunta no la incorpora automáticamente a una evaluación.

### Los siete tipos

| Tipo | Cómo se configura | Cómo responde el estudiante |
|---|---|---|
| Opción múltiple (`multiple_choice`) | Dos o más opciones y una correcta | Selecciona una opción. |
| Verdadero/falso (`true_false`) | Define verdadero o falso | Selecciona una de las dos opciones. |
| Respuesta corta (`short_answer`) | Una o más respuestas aceptadas; sensibilidad opcional | Escribe texto no vacío. |
| Numérica (`numeric`) | Valor correcto y tolerancia no negativa | Escribe un número, con punto o coma decimal. |
| Orden (`order`) | Dos o más elementos en el orden correcto | Reordena todos los elementos. |
| Relación (`matching`) | Dos o más pares izquierda/derecha | Selecciona una correspondencia única para cada elemento. |
| Comprensión auditiva (`listening`) | Opciones, respuesta y fuente de audio o TTS | Reproduce dentro del límite y selecciona una opción. |

En respuesta corta, la capitalización se ignora por defecto; active sensibilidad solo cuando tenga valor pedagógico. En numérica, una respuesta es correcta cuando su diferencia con el valor esperado no supera la tolerancia.

Para listening puede subir WAV, MP3, M4A, OGG o AAC, o seleccionar voz del navegador (TTS) y escribir un guion. La voz disponible y su calidad dependen del navegador y dispositivo. Pruebe siempre el idioma y el contenido. El guion TTS no se incluye en el HTML inicial, pero llega al navegador autorizado al reproducir.

**El límite de reproducciones es solo una disuasión del navegador.** El contador se crea al renderizar la página y no se persiste ni se valida en el servidor. No lo use como evidencia de cuántas veces se escuchó un contenido ni como control de alta garantía. Ante fallos de audio, recargas o problemas de accesibilidad, recopile contexto y aplique una solución académica justa.

Puede editar, duplicar o archivar preguntas propias. Una copia y toda pregunta importada quedan inicialmente con `is_active=0`.

> **Advertencia importante:** `is_active=0` no es una barrera técnica de aprobación. La pantalla y la ruta de selección de versiones aceptan actualmente preguntas inactivas que no estén archivadas. La importación no adjunta ni publica preguntas por sí sola, pero un docente puede seleccionar una importada sin activarla. Revise el contenido **antes de seleccionarlo**. Activar es una acción de estado/gestión, no una garantía de seguridad ni de revisión.

Consulte [Importación de preguntas](importacion-preguntas.md).

## Exámenes, versiones y asignaciones

1. En **Exámenes**, cree un examen con asignatura, título y descripción. Se crea como borrador con una versión A.
2. Abra el examen y edite la selección de cada versión. Solo aparecen preguntas propias, de la misma asignatura y utilizables.
3. Cree, renombre o duplique versiones según sea necesario.
4. Asigne el examen a una sección en modo fijo o aleatorio.
5. Publique el examen cuando al menos una versión activa tenga preguntas.

El modo fijo entrega la versión elegida. El modo aleatorio distribuye de forma balanceada entre versiones utilizables. Una vez asignada una versión a un estudiante, permanece estable al actualizar, reconectar o reanudar.

Al iniciar, la aplicación crea un snapshot de las preguntas. Los cambios posteriores en banco o versión no alteran ese intento. Solo existe un intento por estudiante y asignación; un intento en progreso se reanuda y uno enviado abre el resultado.

No archive la última versión utilizable de un examen publicado ni una versión fija aún vinculada. Las versiones archivadas conservan relaciones históricas y pueden restaurarse. Archivar un examen desactiva sus asignaciones y lo oculta sin romper resultados previos.

## Intentos, resultados e integridad

El panel muestra únicamente resultados de sus exámenes. Puede filtrar por estudiante/correo, sección, asignatura, examen, versión, estado de integridad y fechas. Abra **Ver** para consultar resultado, desglose, resumen de integridad y línea temporal técnica.

La telemetría registra señales permitidas, como cambios de foco o visibilidad, tiempo fuera, salida de pantalla completa y acciones bloqueadas de menú contextual, copiar, cortar, pegar o atajos. Estas señales pueden tener causas legítimas de accesibilidad, notificaciones o fallos del dispositivo. **No son prueba de fraude y nunca descuentan puntos automáticamente.** Revise contexto, escuche al estudiante y aplique la política institucional.

## Penalizaciones

Solo el docente propietario de un intento enviado puede aplicar una penalización. Debe indicar puntos positivos y un motivo concreto. La deducción no puede superar la nota ajustada disponible.

- La nota académica original permanece intacta.
- La nota final ajustada resta penalizaciones activas y nunca baja de cero.
- Cada acción registra docente, fecha y motivo.
- Una penalización puede revocarse; el historial permanece visible.

Use este mecanismo únicamente después de una revisión humana y con un procedimiento de apelación institucional.

## Exportaciones e informes

- **CSV** y **Excel** respetan los filtros activos y solo incluyen sus resultados.
- Excel incluye resultados y eventos de integridad.
- Cada intento ofrece un PDF descargable y una vista imprimible.
- El PDF del estudiante contiene el resumen, no la clave de respuestas.

Trate estos archivos como datos personales y académicos: descárguelos solo en equipos autorizados, no los envíe a servicios externos sin autorización y elimínelos conforme a la política de retención.

## Solución de problemas

| Problema | Comprobación |
|---|---|
| No aparece una pregunta al editar versión | Debe ser propia, de la misma asignatura, no archivada y, si es listening, tener fuente válida. El estado inactivo no la excluye actualmente. |
| No se puede publicar | Confirme que exista una versión activa con preguntas. |
| Un estudiante no ve el examen | Revise cuenta/sección activa, asignación activa, publicación y versión utilizable. |
| El estudiante vuelve al mismo intento | Es el comportamiento correcto: un intento estable por asignación. |
| Un cambio del banco no aparece en un intento iniciado | Es correcto: el intento usa su snapshot. |
| TTS no reproduce | Pruebe navegador compatible, volumen, idioma y guion; no cambie a audio si no existe el archivo. |
| Una fila CSV se omitió | Revise el resumen y la guía de importación correspondiente. |
| Un evento de integridad parece incorrecto | Trátelo como señal técnica, recopile contexto y no penalice automáticamente. |
