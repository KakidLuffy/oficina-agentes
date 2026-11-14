# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-14T14:33:35+00:00 UTC · Precio BTC/EUR: 60074 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (2.6 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 10.00 | +0.00 | +0.00 % | +0.99 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 5/20 | 9.92 | -0.08 | -0.83 % | +0.90 | 4 | 0.09 | +0.01 | 2026-11-11 | En efectivo |
| Momentum | 9.84 | -0.16 | -1.57 % | +0.83 | 4 | 0.09 | -0.07 | 2026-11-11 | En efectivo |
| Rebote | 9.44 | -0.56 | -5.64 % | +0.42 | 6 | 0.13 | -0.43 | 2026-11-11 | Con ETH, XBT |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +0.99 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 10.00 | +0.00 | +0.00 % | +0.99 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Rebote rapido | 9.89 | -0.11 | -1.10 % | +0.88 | 8 | 0.18 | +0.07 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 9.09 | -0.91 | -9.12 % | +0.07 | 5 | 0.04 | -0.87 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +0.99 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 9.01 | -0.99 | -9.85 % | 0.00 | 1 | 0.04 | -0.94 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 9.06 | -0.94 | -9.39 % | +0.05 | 2 | 0.04 | -0.89 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 9.09 | -0.91 | -9.12 % | +0.07 | 5 | 0.04 | -0.87 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-13 1750.49 frente a media de 100 dias 2087.53 (debajo: fuera); XBT cierre del 2026-11-13 61955.00 frente a media de 100 dias 68287.96 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | 0.00 % | 0 | 0 |
| Cruce 5/20 | -1.00 % | 0 | 2 |
| Momentum | -1.70 % | 0 | 2 |
| Rebote | -5.60 % | 0 | 2 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | 0.00 % | 0 | 0 |
| Rebote rapido | -1.90 % | 2 | 2 |
| Rebalanceo semanal | -9.10 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -9.90 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (0 cerradas, 3 dias); Cruce 5/20 (2 cerradas, 3 dias); Momentum (2 cerradas, 3 dias); Rebote (2 cerradas, 3 dias); Cruce 10/30 + filtro (0 cerradas, 3 dias); Cruce 3/8 rapido (0 cerradas, 3 dias); Rebote rapido (4 cerradas, 3 dias); Rebalanceo semanal (0 cerradas, 3 dias); Tendencia H1 (diaria) (0 cerradas, 3 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 2.6 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
