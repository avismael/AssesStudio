# Importación de preguntas

[Volver al índice](README.md) | [Ejemplo con todos los tipos](examples/preguntas_todos_los_tipos.csv)

## Encabezado español exacto

Todos los ejemplos usan estas 14 columnas, en este orden:

```text
Asignatura,Categoria,Tipo,Pregunta,Opciones,Respuesta,Pares,Orden,Tolerancia,SensibleMayusculas,Script,Audio,FuenteAudio,IdiomaVoz
```

Solo `Tipo` y `Pregunta` son columnas globalmente obligatorias, pero cada tipo requiere datos adicionales. Se admiten UTF-8 con o sin BOM y `latin-1`; el delimitador puede ser coma o punto y coma. Use comillas CSV cuando una celda contenga el delimitador. `|`, `=>` y `=` tienen significado interno y no deben sustituirse por comas.

## Encabezados alternativos

| Español | Aliases reconocidos |
|---|---|
| `Asignatura` | `Subject` |
| `Categoria` | `Category` |
| `Tipo` | `Type` |
| `Pregunta` | `Question`, `Prompt` |
| `Opciones` | `Options`, `Choices` |
| `Respuesta` | `Answer`, `Correcta`, `Correct` |
| `Pares` | `Pairs`, `Matching` |
| `Orden` | `Order`, `Sequence` |
| `Tolerancia` | `Tolerance` |
| `SensibleMayusculas` | `CaseSensitive`, `Case_sensitive` |
| `Script` | `Guion` |
| `Audio` | `Audio_file`, `Archivo_audio` |
| `FuenteAudio` | `AudioSource`, `ListeningSource`, `Listening_source` |
| `IdiomaVoz` | `VoiceLanguage`, `SpeechLanguage`, `TTSLang` |

Los encabezados y tipos se normalizan sin acentos y sin distinguir mayúsculas. Los nombres de asignatura y categoría, en cambio, se resuelven por **nombre exacto actual** o ID numérico y deben estar activos.

## Asignatura y categoría

- Si ambas celdas tienen valor, deben identificar una asignatura y una categoría perteneciente a ella.
- Si están vacías, el formulario puede aportar valores predeterminados.
- Si solo se elige categoría predeterminada, la aplicación deriva su asignatura.
- Un valor del CSV prevalece sobre el valor predeterminado.
- Los ejemplos usan `General` y `General`, creados por el bootstrap en una base nueva.

## Tipos y aliases

| Tipo canónico | Aliases de `Tipo` |
|---|---|
| `multiple_choice` | `opcion_multiple`, `opcion`, `mcq` |
| `true_false` | `verdadero_falso`, `vf` |
| `short_answer` | `respuesta_corta` |
| `numeric` | `numeric_answer`, `numerica`, `respuesta_numerica` |
| `order` | `ordering`, `ordenar`, `put_in_order` |
| `matching` | `relacionar`, `match` |
| `listening` | `audio`, `audio_listening` |

## Formato exacto por tipo

### `multiple_choice`

- `Opciones`: al menos dos textos separados por `|`.
- `Respuesta`: texto de una opción, comparado sin distinguir mayúsculas, o número de posición desde 1.
- Ejemplo: `Rojo|Verde|Azul` y `2` o `Verde`.

### `true_false`

- `Respuesta` verdadera: `true`, `verdadero`, `1`, `yes`, `si`.
- `Respuesta` falsa: `false`, `falso`, `0`, `no`.
- La normalización ignora mayúsculas y acentos.

### `short_answer`

- `Respuesta`: una o más respuestas aceptadas separadas por `|`.
- `SensibleMayusculas`: se activa con `1`, `true`, `yes`, `si`, `s`, `x` o `verdadero`; cualquier otro valor queda desactivado.
- Sin sensibilidad, se normalizan espacios y capitalización al calificar. Con sensibilidad, la capitalización sí importa.

### `numeric`

- `Respuesta`: use un número finito en notación decimal.
- `Tolerancia`: número no negativo; vacío equivale a `0` y un valor negativo se convierte en `0`.
- Se acepta punto o coma decimal en la importación. Si usa coma decimal en un CSV delimitado por comas, cite la celda: `"3,14"`.

**Caveat actual:** el importador usa la conversión `float()` y no rechaza expresamente literales no finitos como `NaN` o `Infinity`. Esos valores no son respuestas numéricas utilizables y la validación del intento estudiantil sí los rechaza. No los importe; revise que respuesta y tolerancia sean decimales finitos.

### `order`

- `Orden`: al menos dos elementos, ya colocados en la secuencia correcta, separados por `|`.
- Si `Orden` está vacío, se usa `Opciones` como alternativa.
- La aplicación asigna IDs internos y mezcla la presentación al estudiante.

### `matching`

- `Pares`: al menos dos pares separados por `|`.
- Cada par usa `izquierda=>derecha`; también se acepta `izquierda=derecha`.
- Partes sin separador o con un lado vacío se ignoran; deben quedar al menos dos pares válidos.

### `listening`

- `Opciones` y `Respuesta`: mismas reglas que opción múltiple.
- `FuenteAudio`: `tts`, `voz`, `script` o `browser_voice` seleccionan voz del navegador; `audio`, `archivo` o `file` seleccionan archivo.
- TTS requiere `Script` no vacío. `IdiomaVoz` válido: `auto`, `en-US`, `es-MX`, `es-ES`; otro valor se convierte en `auto`.
- Audio requiere que el nombre de `Audio` ya exista físicamente en `static/audio`. El CSV no sube archivos.
- Si `FuenteAudio` está vacía, se elige archivo si existe, TTS si hay script y, si no hay ninguno, audio incompleto.
- Si la fuente seleccionada falta, la fila puede importarse, pero se cuenta en la advertencia **Listening sin fuente** y no podrá agregarse a una versión hasta corregirla.

El ejemplo listening incluido usa TTS, guion no vacío y `es-MX`, por lo que no depende de un archivo externo.

## Procedimiento

> **Advertencia importante sobre revisión:** la importación crea preguntas con `is_active=0` y no las adjunta ni publica automáticamente. Sin embargo, el selector de versiones lista y acepta actualmente preguntas inactivas siempre que sean propias, de la misma asignatura, no estén archivadas y tengan una fuente listening utilizable. `is_active=0` **no es una barrera técnica de aprobación**. La revisión humana debe completarse antes de seleccionar una pregunta. Activarla es una acción de estado/gestión, no una garantía de seguridad.

1. Revise o cree el catálogo con el administrador.
2. Abra **Banco de preguntas** y pulse **Importar CSV**.
3. Seleccione el archivo.
4. Si las celdas de catálogo están vacías, elija asignatura y categoría predeterminadas coherentes.
5. Importe y revise las advertencias de filas omitidas y listening sin fuente.
6. Filtre, abra y revise cada pregunta importada.
7. Corrija o archive cualquier pregunta no aprobada antes de abrir el selector de versiones.
8. Use la activación como estado de gestión si corresponde.
9. Seleccione manualmente en **Exámenes** solo las preguntas ya aprobadas por una persona responsable.

Todas las preguntas importadas quedan en el banco del docente actual con `is_active=0`. No se incorporan a versiones ni se publican de forma automática durante la importación. No obstante, una acción posterior de selección puede incorporarlas aunque sigan inactivas; por eso el proceso humano, y no `is_active`, es el control de aprobación vigente.

## Filas omitidas y seguridad

Se omite una fila por catálogo inexistente, tipo inválido, pregunta menor de tres caracteres, opciones/respuesta incompatibles, número inválido o estructura insuficiente. Las demás filas siguen procesándose y la interfaz muestra hasta cuatro detalles de error.

No incluya fórmulas. La aplicación no neutraliza texto no confiable que comience con `=`, `+`, `-` o `@`; podría ejecutarse al abrir archivos en una hoja de cálculo. Un número negativo simple puede ser pedagógicamente válido, pero debe comprobarse como número y no como fórmula. Tampoco coloque datos personales, credenciales, claves confidenciales o contenido sin autorización.

## Ejemplos individuales

- [Opción múltiple](examples/preguntas_multiple_choice.csv)
- [Verdadero/falso](examples/preguntas_true_false.csv)
- [Respuesta corta](examples/preguntas_short_answer.csv)
- [Numérica](examples/preguntas_numeric.csv)
- [Orden](examples/preguntas_order.csv)
- [Relación](examples/preguntas_matching.csv)
- [Listening TTS](examples/preguntas_listening.csv)
