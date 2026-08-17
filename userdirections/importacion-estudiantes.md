# Importación masiva de estudiantes

[Volver al índice](README.md) | [Archivo de ejemplo](examples/estudiantes_importacion.csv)

## Encabezados y aliases

La plantilla española usa:

```text
NIE,Nombre,Apellido,Correo
```

| Dato | Encabezados reconocidos | Obligatorio |
|---|---|---|
| Identificador | `NIE`, `Student ID`, `student_code` | Sí |
| Nombre | `Nombre`, `First name` o `first_name` | Sí |
| Apellido | `Apellido`, `Last name` o `last_name` | Sí |
| Correo | `Correo`, `Email`, `correo_electronico` | Sí, salvo generación automática |

Los encabezados se normalizan sin distinguir mayúsculas, acentos ni separadores comunes. Use la plantilla para evitar ambigüedades.

## Preparar el archivo

- Use `.csv`, preferentemente UTF-8 con o sin BOM. También se admite `latin-1`.
- Se detectan coma `,` y punto y coma `;`.
- Incluya una fila de encabezados y una fila por estudiante.
- NIE, nombre y apellido no pueden quedar vacíos.
- El NIE y el correo deben ser únicos globalmente, incluidos los estudiantes archivados. No pueden reutilizarse después de archivar una cuenta.
- Evite espacios o símbolos en el NIE si generará correos. La parte local conserva únicamente letras ASCII, números y `._+-`.

La aplicación no neutraliza fórmulas de hoja de cálculo. No use texto no confiable que comience con `=`, `+`, `-` o `@`. Revise especialmente datos copiados desde Excel/Sheets antes de subirlos. El CSV es información, no un lugar para fórmulas.

## Correo generado o correo del archivo

### Generar correo desde NIE

Active **Generar correo desde NIE** y escriba un dominio válido, por ejemplo `clases.edu`. La aplicación crea `NIE@dominio`; la columna `Correo` puede estar vacía. Si al limpiar el NIE no queda una parte local válida, la fila se omite.

### Usar Correo

Desactive la generación automática. El archivo debe contener la columna `Correo`, `Email` o `correo_electronico`, y cada fila debe aportar un correo válido. Los correos se normalizan a minúsculas.

## Sección y contraseñas

Toda la carga se asigna a una única sección activa seleccionada en el formulario. Cree la sección antes de importar.

Puede:

- generar una contraseña temporal segura para todo el lote; o
- escribir una contraseña temporal común de 8 a 128 caracteres con al menos una letra y un número.

La contraseña del lote se muestra una sola vez después de importar. Guárdela y distribúyala por un canal seguro. La opción **Exigir cambio de contraseña** marca todas las cuentas importadas para que definan una clave personal en el siguiente ingreso; se recomienda mantenerla activa.

## Procedimiento

1. Abra **Estudiantes y secciones**.
2. Cree o confirme la sección de destino.
3. Pulse **Importar estudiantes**.
4. Seleccione el CSV.
5. Elija la sección.
6. Configure generación de correo o uso de `Correo`.
7. Elija la contraseña de lote y la exigencia de cambio.
8. Pulse **Importar estudiantes ahora**.
9. Revise cantidad importada, omitida y hasta ocho mensajes de fila.
10. Entregue las credenciales temporales de forma segura.

## Validación, filas omitidas y duplicados

Cada fila se procesa por separado. Una fila inválida o duplicada se omite y las demás continúan. No se actualizan ni sobrescriben registros existentes.

La comprobación previa de la importación busca duplicados no archivados. Sin embargo, PostgreSQL mantiene restricciones únicas globales sobre NIE y correo, también para registros archivados. Si una fila coincide con un registro archivado, la inserción falla de forma controlada y esa fila se informa como **conflicto de datos**. Archivar no libera el identificador ni el correo.

Se omiten filas por:

- NIE, nombre o apellido ausente;
- correo inválido o imposible de generar;
- NIE o correo ya registrado;
- conflicto de integridad de datos, incluido NIE o correo perteneciente a un registro archivado.

Si ninguna fila es válida, no se muestra una contraseña utilizable y la importación informa el fallo.

## Solución de problemas

| Mensaje o síntoma | Corrección |
|---|---|
| Faltan columnas obligatorias | Use `NIE,Nombre,Apellido,Correo` o aliases reconocidos. |
| Se exige Correo | Agregue la columna o active generación desde NIE. |
| Dominio inválido | Escriba solo un dominio válido, sin `@` inicial. |
| Contraseña inválida | Use al menos 8 caracteres, una letra y un número. |
| Sección inválida | Seleccione una sección activa. |
| NIE o correo ya registrado/conflicto de datos | Busque también entre registros archivados. Restaure o corrija el registro institucional; no reutilice NIE ni correo. |
| Caracteres dañados | Exporte como CSV UTF-8; no cambie manualmente la codificación. |
| Columnas desplazadas | Cite con comillas cualquier celda que contenga el delimitador. |
