# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-21T05:17:43+00:00 UTC · Precio BTC/EUR: 51455 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (9.3 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 8.94 | -1.06 | -10.59 % | +1.22 | 16 | 0.34 | -0.71 | 2026-11-11 | En efectivo |
| Cruce 5/20 | 8.91 | -1.09 | -10.86 % | +1.19 | 24 | 0.52 | -0.57 | 2026-11-11 | En efectivo |
| Momentum | 8.99 | -1.01 | -10.11 % | +1.27 | 20 | 0.43 | -0.58 | 2026-11-11 | En efectivo |
| Rebote | 8.75 | -1.25 | -12.50 % | +1.03 | 24 | 0.51 | -0.74 | 2026-11-11 | Con ETH, XBT |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +2.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.42 | -0.58 | -5.79 % | +1.70 | 10 | 0.22 | -0.36 | 2026-11-11 | En efectivo |
| Rebote rapido | 8.92 | -1.08 | -10.80 % | +1.20 | 32 | 0.69 | -0.39 | 2026-11-11 | Con ETH, XBT |
| Rebalanceo semanal | 7.94 | -2.06 | -20.62 % | +0.22 | 5 | 0.04 | -2.02 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +2.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 7.72 | -2.28 | -22.79 % | 0.00 | 1 | 0.04 | -2.23 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 7.73 | -2.27 | -22.68 % | +0.01 | 2 | 0.04 | -2.22 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 7.94 | -2.06 | -20.62 % | +0.22 | 5 | 0.04 | -2.02 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-20 1478.54 frente a media de 100 dias 2085.42 (debajo: fuera); XBT cierre del 2026-11-20 53687.60 frente a media de 100 dias 68422.30 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -11.04 % | 0 | 8 |
| Cruce 5/20 | -11.10 % | 0 | 12 |
| Momentum | -10.19 % | 0 | 10 |
| Rebote | -13.30 % | 3 | 8 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -5.80 % | 0 | 5 |
| Rebote rapido | -11.60 % | 5 | 10 |
| Rebalanceo semanal | -21.20 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.40 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (8 cerradas, 9 dias); Cruce 5/20 (12 cerradas, 9 dias); Momentum (10 cerradas, 9 dias); Rebote (11 cerradas, 9 dias); Cruce 10/30 + filtro (0 cerradas, 9 dias); Cruce 3/8 rapido (5 cerradas, 9 dias); Rebote rapido (15 cerradas, 9 dias); Rebalanceo semanal (0 cerradas, 9 dias); Tendencia H1 (diaria) (0 cerradas, 9 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 9.3 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
