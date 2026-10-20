# Carta del equipo

Esta oficina es una **simulación con dinero ficticio**. Este documento dice quién hace qué y qué está permitido.

## Quién trabaja aquí

| Sector | Quién | Qué hace |
|---|---|---|
| Ejecución | Los 9 agentes de trading | Operan con 10 € ficticios cada uno (90 € en total; 3 de ellos son «rápidos» y operan varias veces al día), con precios reales de Kraken. |
| Análisis | Los 3 analistas del laboratorio | Cada lunes prueban variantes de estrategias y las examinan en datos que no usaron para elegirlas. |
| Dirección | El director | Revisa los datos, escribe el parte, anota decisiones en la memoria y prepara las propuestas. Solo lee y resume. |
| Riesgo | El vigilante (en el panel) | Avisa si un agente cae de golpe o se acerca al límite de pérdida. Solo avisa. |

## Qué puede hacer cada uno por su cuenta

- Los agentes compran y venden dinero ficticio dentro de los límites: 2 € por moneda, hasta 5 monedas a la vez, 0,40 € de pérdida diaria, apagado bajo 7 €.
- El laboratorio y el director escriben solo en la carpeta `datos/`.

## Qué necesita tu aprobación

- Añadir una candidata del laboratorio como agente nuevo.
- Cambiar los límites de riesgo, las monedas o las comisiones simuladas.
- Cualquier cambio en los programas del repositorio.

## Qué está prohibido

- Operar con dinero real o conectarse a un exchange con claves.
- Subir claves, contraseñas o datos personales al repositorio (es público).
- Presentar un resultado de simulación como garantía de beneficios.

## Dónde está cada cosa

- `datos/parte_director.md`: el parte del día. `datos/memoria.md`: reglas y registro de decisiones. `datos/propuestas.md`: candidatas del laboratorio.
- Criterio para fiarse de un agente: al menos 21 días y 30 operaciones cerradas, y superar a «Comprar y mantener» de forma sostenida.
