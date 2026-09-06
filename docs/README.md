# Assessment Studio - Fuente de verdad documental

| Campo | Valor |
|---|---|
| Estado | Implementado, con recomendaciones y roadmap identificados explícitamente |
| Versión documental | 2.0 |
| Fecha de verificación | 2026-08-16 |
| Autoridad técnica | `app.py`, `database.py`, `migrations/`, `seed.py`, `compose.yaml`, `templates/`, `static/`, `tests/` |

Esta carpeta describe el producto realmente implementado. Las etiquetas **Implementado**, **Recomendado**, **Supuesto** y **Roadmap** separan hechos comprobados de decisiones futuras. Ante una discrepancia, prevalece el código y debe corregirse la documentación en el mismo cambio.

## Rutas de lectura

| Audiencia | Recorrido recomendado |
|---|---|
| Dirección e institución | [Resumen ejecutivo](00-executive-summary.md) -> [Producto y negocio](01-product-and-business.md) -> [Roadmap y gobierno](14-glossary-governance-roadmap.md) |
| Producto y UX | [Personas y casos de uso](02-personas-journeys-use-cases.md) -> [Requisitos](03-functional-requirements.md) -> [Diseño UX/UI](04-ux-design-system.md) |
| Arquitectura y seguridad | [Arquitectura](05-architecture.md) -> [Datos](06-data-model.md) -> [Seguridad](07-security-privacy.md) -> [ADRs](13-adrs.md) |
| Desarrollo y QA | [Guía de desarrollo](08-development-guide.md) -> [Calidad](09-quality-strategy.md) -> [Referencia de rutas](11-api-route-reference.md) |
| Operaciones | [Runbook](10-operations-runbook.md) -> [Diagramas](12-diagrams.md) -> [Seguridad](07-security-privacy.md) |
| Paquete documental premium | [16 - Product book](16-product-book.md) -> [17 - Casos de uso](17-use-cases.md) -> [18 - Diagramas UML](18-uml-diagrams.md) -> [19 - ER y modelo de datos](19-erd.md) |
| Usuarios finales | [Manuales por rol e importaciones](../userdirections/README.md) |
| Documento maestro | [Documento de la aplicación](15-documento-de-la-aplicacion.md) -> [Manuales](../userdirections/README.md) |

## Índice maestro

1. [00 - Resumen ejecutivo](00-executive-summary.md)
2. [01 - Producto y negocio](01-product-and-business.md)
3. [02 - Personas, jornadas y casos de uso](02-personas-journeys-use-cases.md)
4. [03 - Requisitos funcionales y no funcionales](03-functional-requirements.md)
5. [04 - Arquitectura de información y sistema de diseño](04-ux-design-system.md)
6. [05 - Arquitectura técnica](05-architecture.md)
7. [06 - Modelo y diccionario de datos](06-data-model.md)
8. [07 - Seguridad y privacidad](07-security-privacy.md)
9. [08 - Guía de desarrollo](08-development-guide.md)
10. [09 - Estrategia de calidad](09-quality-strategy.md)
11. [10 - Operaciones y despliegue](10-operations-runbook.md)
12. [11 - Referencia de rutas Flask](11-api-route-reference.md)
13. [12 - Catálogo de diagramas](12-diagrams.md)
14. [13 - Registros de decisiones arquitectónicas](13-adrs.md)
15. [14 - Glosario, gobierno y roadmap](14-glossary-governance-roadmap.md)
16. [15 - Documento maestro de la aplicación](15-documento-de-la-aplicacion.md)
17. [16 - Product book](16-product-book.md)
18. [17 - Casos de uso](17-use-cases.md)
19. [18 - Diagramas UML](18-uml-diagrams.md)
20. [19 - ER y modelo de datos](19-erd.md)

Los procedimientos de uso están en [Manuales de usuario](../userdirections/README.md), sin duplicar la referencia técnica. También son normativos [AGENTS.md](../AGENTS.md), para invariantes de modificación, y [README.md](../README.md), como entrada operativa breve. Los changelogs históricos se enlazan desde el [índice de cambios](14-glossary-governance-roadmap.md#índice-de-cambios).

## Matriz de cobertura

| Dominio solicitado | Documento principal | Complementos |
|---|---|---|
| Ejecutivo, producto y negocio | [00](00-executive-summary.md), [01](01-product-and-business.md) | [03](03-functional-requirements.md) |
| Personas, jornadas y casos de uso | [02](02-personas-journeys-use-cases.md) | [11](11-api-route-reference.md) |
| Diseño UI/UX | [04](04-ux-design-system.md) | [12](12-diagrams.md) |
| Arquitectura | [05](05-architecture.md), [13](13-adrs.md) | [12](12-diagrams.md) |
| Datos | [06](06-data-model.md) | [10](10-operations-runbook.md) |
| Flujos y diagramas | [12](12-diagrams.md) | [05](05-architecture.md), [06](06-data-model.md) |
| Desarrollo | [08](08-development-guide.md) | [09](09-quality-strategy.md) |
| Calidad | [09](09-quality-strategy.md) | [03](03-functional-requirements.md) |
| Seguridad y privacidad | [07](07-security-privacy.md) | [10](10-operations-runbook.md) |
| Operaciones | [10](10-operations-runbook.md) | [07](07-security-privacy.md) |
| Rutas, configuración y referencia | [11](11-api-route-reference.md), [14](14-glossary-governance-roadmap.md) | [08](08-development-guide.md) |
| Documento maestro de la aplicación | [15](15-documento-de-la-aplicacion.md) | [05](05-architecture.md), [06](06-data-model.md), [11](11-api-route-reference.md), [12](12-diagrams.md), [../userdirections/README.md](../userdirections/README.md) |
| Paquete documental premium | [16](16-product-book.md), [17](17-use-cases.md), [18](18-uml-diagrams.md), [19](19-erd.md) | [05](05-architecture.md), [06](06-data-model.md), [11](11-api-route-reference.md), [12](12-diagrams.md) |

## Convención de estado

- **Implementado**: comportamiento comprobado en el código actual.
- **Recomendado**: práctica necesaria para operación profesional, no automatizada por el repositorio.
- **Supuesto**: hipótesis de producto o negocio que requiere validación institucional.
- **Roadmap**: capacidad futura; no debe comunicarse como disponible.
