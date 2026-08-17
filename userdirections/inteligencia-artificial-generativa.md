# Uso responsable de IA generativa

[Volver al índice](README.md) | [Ficha de fuentes y contexto](ficha-fuentes-contexto.md)

## Alcance real

Assessment Studio no integra GPT, Gemini, RAG ni generación automática. Un docente puede usar herramientas externas para preparar borradores y luego importar un CSV, bajo la política de su institución.

Una IA generativa **no garantiza exactitud, actualidad, ausencia de sesgos, originalidad ni adecuación pedagógica**. La revisión humana experta es obligatoria. El docente conserva la responsabilidad sobre fuentes, contenido, respuestas, distractores, accesibilidad y uso final.

## Privacidad y derechos

No cargue en modelos de terceros:

- datos personales o académicos de estudiantes;
- nombres, correos, NIE, respuestas, notas o telemetría;
- credenciales, secretos, cookies o configuración;
- claves de respuesta no publicadas o exámenes confidenciales;
- materiales reservados de la institución;
- contenido protegido por derechos de autor sin autorización.

Use fuentes autorizadas y compruebe las condiciones del proveedor, retención, entrenamiento con entradas, ubicación de datos y contrato institucional. Anonimizar no siempre elimina el riesgo de reidentificación.

## Flujo seguro en dos pasadas

### Primera pasada: contenido y revisión

1. Defina objetivo de aprendizaje, audiencia, nivel, idioma, dificultad y mezcla de tipos.
2. Complete la [ficha de fuentes y contexto](ficha-fuentes-contexto.md).
3. Proporcione solo extractos autorizados con título, versión/fecha y página o sección.
4. Ordene usar exclusivamente esas fuentes y marcar cualquier dato no sustentado.
5. Exija trazabilidad fuera del CSV: fuente y página por pregunta.
6. Valide cada afirmación y respuesta contra la fuente.
7. Revise distractores: plausibles, inequívocamente incorrectos y sin pistas formales.
8. Revise edad, idioma, accesibilidad, neutralidad cultural, ambigüedad y sesgos.
9. Apruebe o rechace cada pregunta antes de continuar.

### Segunda pasada: conversión a CSV

Convierta únicamente el contenido aprobado. Valide encabezados, delimitadores internos, comillas y reglas por tipo.

> **Advertencia importante:** la importación deja las preguntas con `is_active=0` y no las adjunta ni publica automáticamente, pero ese estado no es una barrera técnica de revisión. Las rutas actuales permiten seleccionar en una versión una pregunta inactiva no archivada. La revisión humana debe ocurrir **antes de la selección**. La activación es un estado de gestión, no una garantía de seguridad, calidad o aprobación.

El CSV no es adecuado para conservar citas extensas. Mantenga la matriz de trazabilidad en un documento institucional separado.

## Plantilla 1: generación basada en fuentes

```text
Actúa como asistente de diseño de evaluación. No inventes información y no uses conocimiento externo.

CONTEXTO
- Asignatura: [ASIGNATURA]
- Tema: [TEMA]
- Grado/edad: [GRADO_EDAD]
- Idioma y variante: [IDIOMA]
- Objetivos de aprendizaje: [OBJETIVOS]
- Dificultad: [DIFICULTAD]
- Mezcla solicitada: [CANTIDAD_Y_TIPOS]
- Terminología obligatoria: [TERMINOLOGIA]
- Exclusiones: [EXCLUSIONES]
- Riesgos conocidos: [RIESGOS]

FUENTES AUTORIZADAS
[FUENTE_1: título, autor/institución, versión/fecha, página/sección]
[EXTRACTO_AUTORIZADO_1]
[FUENTE_2...]

INSTRUCCIONES ESTRICTAS
1. Usa únicamente las fuentes autorizadas anteriores.
2. Si una respuesta no está sustentada de forma explícita, escribe NO SUSTENTADA y no generes esa pregunta.
3. Genera primero una tabla de revisión, NO CSV, con: ID, tipo, enunciado, opciones/estructura, respuesta propuesta, explicación, objetivo, fuente exacta y página/sección.
4. No incluyas datos personales ni materiales fuera de las fuentes.
5. Evita pistas gramaticales, dobles negaciones, absolutos injustificados, estereotipos y ambigüedad.
6. Ajusta lenguaje, longitud y carga cognitiva a [GRADO_EDAD].
7. Para cada distractor, explica por qué es plausible pero incorrecto según la fuente.
8. No declares que el contenido está aprobado; termina con PENDIENTE DE REVISIÓN HUMANA.
```

## Plantilla 2: conversión del contenido aprobado a CSV

```text
Convierte SOLO las preguntas aprobadas incluidas abajo a CSV UTF-8.

CONTENIDO APROBADO
[PEGAR_SOLO_PREGUNTAS_APROBADAS_SIN_DATOS_PERSONALES]

SALIDA ESTRICTA
1. Devuelve únicamente CSV dentro de un bloque de código, sin explicación antes ni después.
2. Usa exactamente este encabezado y orden:
Asignatura,Categoria,Tipo,Pregunta,Opciones,Respuesta,Pares,Orden,Tolerancia,SensibleMayusculas,Script,Audio,FuenteAudio,IdiomaVoz
3. Usa Asignatura=[ASIGNATURA_EXISTENTE] y Categoria=[CATEGORIA_EXISTENTE].
4. Tipos permitidos: multiple_choice,true_false,short_answer,numeric,order,matching,listening.
5. Separa opciones, respuestas aceptadas y orden con |. Usa izquierda=>derecha para pares.
6. multiple_choice/listening: al menos 2 opciones; Respuesta debe coincidir con el texto de una opción o ser su posición desde 1.
7. true_false: Respuesta es verdadero o falso.
8. short_answer: Respuesta contiene alternativas con |; SensibleMayusculas es si o no.
9. numeric: Respuesta y Tolerancia son números; usa punto decimal para evitar conflicto con la coma CSV.
10. order: coloca la secuencia correcta en Orden.
11. matching: coloca al menos dos pares en Pares.
12. listening: usa FuenteAudio=tts, Script no vacío, Audio vacío e IdiomaVoz en auto/en-US/es-MX/es-ES.
13. Escapa las comillas duplicándolas y cita toda celda que contenga coma, comillas o salto de línea.
14. No agregues citas al CSV, no inventes preguntas y no uses fórmulas ni texto no numérico que comience con =,+,-,@.
```

## Plantilla 3: auditoría factual y de citas

```text
Audita el siguiente borrador contra EXCLUSIVAMENTE las fuentes autorizadas. No reescribas todavía.

BORRADOR
[BORRADOR_CON_IDS]

FUENTES AUTORIZADAS
[TITULO_VERSION_PAGINA_Y_EXTRACTOS]

Devuelve una tabla con estas columnas exactas:
ID | afirmación evaluada | veredicto (sustentada/parcial/no sustentada/contradicha) | fuente | página/sección | cita breve | problema | corrección propuesta

Reglas:
- Verifica enunciado, respuesta y cada distractor por separado.
- No completes lagunas con conocimiento externo.
- Marca páginas o versiones ausentes.
- Detecta más de una respuesta defendible, datos desactualizados y precisión falsa.
- Si no puedes verificar algo, clasifícalo como no sustentado.
- Termina con una lista de preguntas que deben rechazarse o volver a revisión humana.
```

## Plantilla 4: auditoría de sesgo, equidad y accesibilidad

```text
Realiza una auditoría crítica del contenido siguiente para [GRADO_EDAD], [IDIOMA_VARIANTE] y [CONTEXTO_INSTITUCIONAL]. No cambies hechos ni claves de respuesta.

CONTENIDO
[PREGUNTAS_CON_IDS]

REVISA
- estereotipos, representación y supuestos culturales o socioeconómicos;
- nombres, contextos o conocimientos periféricos que generen ventaja irrelevante;
- lenguaje discriminatorio, sensible o innecesariamente personal;
- ambigüedad, dobles negaciones y más de una respuesta razonable;
- nivel lector, longitud, vocabulario y carga cognitiva;
- dependencia innecesaria de visión, audición, color, motricidad o tecnología;
- distractores humillantes, absurdos, desiguales en longitud o con pistas;
- adecuación de listening y alternativas equivalentes según la política institucional.

Devuelve una tabla:
ID | riesgo | severidad (alta/media/baja) | población potencialmente afectada | evidencia textual | recomendación | requiere decisión humana (sí/no)

No declares ausencia total de sesgo. No apruebes automáticamente. Finaliza con PENDIENTE DE REVISIÓN HUMANA Y DE ACCESIBILIDAD.
```

## Lista de aprobación humana

- [ ] Cada afirmación y respuesta coincide con una fuente autorizada vigente.
- [ ] La trazabilidad externa conserva título, versión y página/sección.
- [ ] Solo existe una respuesta defendible o la rúbrica contempla alternativas.
- [ ] Los distractores son plausibles, incorrectos y no dan pistas.
- [ ] El nivel, idioma y extensión son adecuados.
- [ ] Se revisaron accesibilidad, sesgo, cultura y ambigüedad.
- [ ] No hay PII, credenciales, claves confidenciales ni contenido no autorizado.
- [ ] El CSV pasa la guía de formato y una apertura segura como texto.
- [ ] La pregunta importada fue revisada y aprobada antes de seleccionarla para una versión, con independencia de su estado activo/inactivo.
