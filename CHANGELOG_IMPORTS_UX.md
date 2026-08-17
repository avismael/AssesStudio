# Assessment Studio — UX + CSV Import Update

## Cambios

- Eliminada la barra flotante del selector de preguntas de una versión.
- Barra superior estática con seleccionar todo, contador total y guardar.
- Preguntas listening sin audio quedan bloqueadas para selección.
- Navegación añadida al reporte de resultados.
- Crear asignatura y crear categoría ahora usan modales.
- Importación masiva de estudiantes por CSV.
- Generación opcional de correo `NIE@dominio` o uso de correo personalizado del CSV.
- Contraseña temporal de lote automática o definida por docente.
- Importación de banco de preguntas por CSV con los 7 tipos soportados.
- Plantillas CSV descargables desde la UI y disponibles en `examples/`.

## CSV estudiantes

`NIE,Nombre,Apellido,Correo`

## CSV preguntas

`Asignatura,Categoria,Tipo,Pregunta,Opciones,Respuesta,Pares,Orden,Tolerancia,SensibleMayusculas,Script,Audio`
