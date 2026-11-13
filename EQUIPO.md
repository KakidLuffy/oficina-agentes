# Carta del equipo

Esta oficina es una **simulación con dinero ficticio**. Este documento dice quién hace qué y qué está permitido.

## Quién trabaja aquí

| Sector | Quién | Qué hace |
|---|---|---|
| Ejecución | Los 9 agentes de trading | Operan con 10 € ficticios cada uno (90 € en total; 2 de ellos son «rápidos» y operan varias veces al día, «Rebalanceo semanal» reparte su dinero entre 5 monedas, y «Tendencia H1» solo opera BTC y ETH con velas diarias y reglas de riesgo más estrictas), con precios reales de Kraken. Máximo 9 agentes (CRITERIOS.md). |
| Sala abierta | 2 agentes aparte | Simulación separada (`sala_abierta.py`, `datos_sala/`): las 2 ideas «POSIBLE» del laboratorio v2, que pueden comprar cualquiera de las 12 monedas del laboratorio. Exploratoria (CRITERIOS.md, sección 7). |
| Análisis | Los 6 analistas del laboratorio | Cada lunes prueban 101 variantes de estrategias con años de historia de Coinbase y las examinan año a año, con datos que no usaron para elegirlas (CRITERIOS.md, sección 4). |
| Dirección | El director | Revisa los datos, escribe el parte, anota decisiones en la memoria y prepara las propuestas. Solo lee y resume. |
| Riesgo | El vigilante (en el panel) | Avisa si un agente cae de golpe o se acerca al límite de pérdida. Solo avisa. |

## Qué puede hacer cada uno por su cuenta

- Los agentes compran y venden dinero ficticio dentro de los límites: los de señales solo compran BTC y ETH (desde el 11-nov-2026), 5 € por compra y como mucho 2 monedas a la vez; 0,40 € de pérdida diaria; apagado bajo 7 €. «Rebalanceo semanal» compra su cesta fija de 5 monedas.
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
