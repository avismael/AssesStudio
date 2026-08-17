# Manual del administrador

[Volver al índice](README.md)

## Responsabilidad del rol

El administrador prepara la institución, gestiona cuentas docentes y mantiene el catálogo compartido. También puede trabajar como docente, pero únicamente puede abrir y editar directamente su propio banco de preguntas, exámenes y resultados. El rol `admin` **no** ofrece una vista global del contenido privado de otros docentes. No obstante, modificar o archivar el catálogo institucional sí puede producir efectos indirectos sobre preguntas de todos los propietarios, como se explica más adelante.

| Acción | Solo administrador | Administrador y docente |
|---|---:|---:|
| Crear, editar, activar o desactivar cuentas docentes | Sí | No |
| Configurar institución, idioma, reglas y límite de audio | Sí | No |
| Crear, editar o archivar asignaturas y categorías | Sí | No |
| Consultar el catálogo | No | Sí |
| Gestionar estudiantes y secciones institucionales | No | Sí |
| Crear preguntas, exámenes y versiones | No | Sí, cada uno en su espacio |
| Ver resultados o aplicar penalizaciones | No | Sí, solo si es propietario del intento |

## Preparación inicial y bootstrap

La instalación técnica debe ejecutar migraciones y luego `python bootstrap.py`. Antes del primer arranque, el responsable técnico debe definir `SECRET_KEY`, `DATABASE_URL`, `TEACHER_ADMIN_NAME`, `TEACHER_ADMIN_EMAIL` y `TEACHER_ADMIN_PASSWORD`. El bootstrap es idempotente: crea el catálogo `General`, la categoría `General`, la configuración base y la cuenta administradora si faltan.

1. Solicite al responsable técnico la URL institucional y las credenciales iniciales por un canal seguro.
2. Abra **Acceso docente** desde el portal estudiantil o ingrese en `/teacher`.
3. Inicie sesión con correo y contraseña.
4. Abra la opción de contraseña de su cuenta y cambie la clave inicial.
5. No use credenciales de demostración en producción.

Las contraseñas deben tener entre 8 y 128 caracteres, al menos una letra y un número. La aplicación almacena un hash, nunca el texto de la contraseña.

## Cuentas docentes

En **Docentes** puede crear cuentas `teacher` o `admin`, editar nombre, correo y rol, restablecer contraseñas y activar o desactivar cuentas.

1. Cree una cuenta individual por persona; no comparta usuarios.
2. Use un correo único y una contraseña temporal robusta.
3. Entregue la contraseña por un canal distinto al correo cuando sea posible.
4. Desactive cuentas que ya no deban ingresar; no reutilice una cuenta para otra persona.

La interfaz impide desactivar la propia cuenta y protege al último administrador activo. Antes de reducir privilegios o desactivar otro administrador, confirme que seguirá existiendo al menos uno activo.

## Catálogo institucional compartido

En **Asignaturas y categorías** todos los docentes pueden consultar el catálogo, pero solo un administrador puede modificarlo. Los conteos de preguntas que ve cada docente corresponden a su propio espacio.

- Una categoría pertenece a una asignatura.
- Los nombres se usan en las importaciones CSV y deben coincidir exactamente.
- Archivar una asignatura también archiva sus categorías y las preguntas asociadas de **todos los docentes**, no solo las del administrador actual.
- Archivar una categoría archiva las preguntas asociadas de **todos los docentes**.
- Cambiar una categoría de asignatura reasigna también las preguntas vinculadas, independientemente del docente propietario.
- Los intentos históricos conservan sus snapshots y siguen siendo consultables.

Antes de archivar o reasignar catálogo, revise el impacto con todos los docentes propietarios. Estas operaciones no permiten leer sus bancos o resultados, pero sí modifican la clasificación o disponibilidad de sus preguntas. Coordine también los cambios de nombre: el catálogo es compartido y afecta las opciones e importaciones de todo el equipo.

## Configuración institucional

En **Configuración** puede definir:

- nombre de la institución y descripción del portal;
- idioma global de la interfaz, español o inglés;
- límite de reproducciones de listening, entre 1 y 5;
- reglas de uso en español e inglés;
- versión de las reglas y aceptación obligatoria por sesión.

Si cambia el texto de las reglas, la aplicación incrementa automáticamente su versión. Las aceptaciones de una versión anterior dejan de ser suficientes y el estudiante deberá aceptar las reglas vigentes. El idioma de cada intento y el texto aceptado quedan guardados al iniciar el examen.

**Límite técnico del contador de listening:** el valor configurado controla un contador del navegador inicializado cada vez que se renderiza la página del examen. No se persiste en PostgreSQL ni se verifica en el servidor. Por tanto, no debe tratarse como un control de alta garantía. La institución debe presentarlo como una regla de uso y definir un procedimiento justo para fallos de audio, recargas accidentales o incidencias técnicas.

## Padrón institucional

Estudiantes y secciones son compartidos. Cualquier docente o administrador puede crearlos, editarlos, importar estudiantes, restablecer contraseñas y activar, desactivar o archivar registros. Por ello:

- acuerde una convención institucional para NIE, secciones y correos;
- evite duplicar estudiantes que ya existen para otra asignatura;
- no intente reutilizar el NIE o correo de un estudiante archivado: las restricciones de unicidad también incluyen registros archivados;
- comunique cambios de sección o estado a los docentes afectados;
- recuerde que una sección solo se archiva cuando no contiene estudiantes vigentes.

Consulte [Importación de estudiantes](importacion-estudiantes.md) para cargas masivas.

## Puesta en servicio

Antes de abrir el sistema:

1. Confirme que el catálogo y las cuentas están correctos.
2. Configure reglas, idioma institucional y límite de audio.
3. Pruebe un acceso de administrador, uno de docente y uno de estudiante.
4. Verifique inicio, reanudación, envío, resultado, PDF y exportaciones.
5. Compruebe que el servicio usa HTTPS y cookies seguras.
6. Confirme que existe un respaldo restaurable de PostgreSQL y de los audios.

## Seguridad, respaldo y escalamiento

La interfaz administrativa no crea respaldos. Un volumen persistente tampoco es un respaldo. El responsable técnico debe respaldar de forma coordinada PostgreSQL, `static/audio/`, configuración y versión desplegada; cifrar las copias y ensayar restauraciones aisladas.

Escale inmediatamente al responsable técnico:

- pérdida o exposición de credenciales, datos, reportes o audios;
- indisponibilidad, errores de base de datos o falta de espacio;
- necesidad de restaurar, migrar o cambiar secretos;
- sospecha de acceso no autorizado;
- cambios de TLS, proxy, almacenamiento o retención.

No borre intentos, telemetría ni penalizaciones durante una investigación. Preserve el estado y siga el procedimiento institucional. Los audios subidos se sirven actualmente desde `static/audio`; si son confidenciales, el equipo técnico debe implantar almacenamiento privado antes de usarlos.

## Problemas frecuentes

| Problema | Acción |
|---|---|
| No puede desactivar una cuenta admin | Compruebe que no sea su propia cuenta ni el último admin activo. |
| Un docente no ve resultados ajenos | Es correcto: no existe bypass global para administradores. |
| Una importación no encuentra asignatura/categoría | Revise nombre exacto, ID y estado no archivado. |
| Cambió una regla y reaparece el aviso | Es correcto: la nueva versión requiere otra aceptación. |
| Se perdió una contraseña | Restablézcala; no puede recuperarse el valor anterior. |
