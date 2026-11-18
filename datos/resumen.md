# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-18T15:17:47+00:00 UTC · Precio BTC/EUR: 57907 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (6.7 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 9.39 | -0.61 | -6.15 % | +0.70 | 10 | 0.22 | -0.39 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 9.13 | -0.87 | -8.66 % | +0.44 | 20 | 0.44 | -0.43 | 2026-11-11 | En efectivo |
| Momentum | 9.26 | -0.74 | -7.44 % | +0.57 | 15 | 0.33 | -0.42 | 2026-11-11 | Con XBT |
| Rebote | 9.31 | -0.69 | -6.86 % | +0.62 | 15 | 0.32 | -0.36 | 2026-11-11 | Con ETH |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.31 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.42 | -0.58 | -5.79 % | +0.73 | 10 | 0.22 | -0.36 | 2026-11-11 | En efectivo |
| Rebote rapido | 9.59 | -0.41 | -4.05 % | +0.91 | 17 | 0.38 | -0.03 | 2026-11-11 | Con ETH |
| Rebalanceo semanal | 8.89 | -1.11 | -11.08 % | +0.20 | 5 | 0.04 | -1.06 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.31 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.69 | -1.31 | -13.11 % | 0.00 | 1 | 0.04 | -1.27 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.71 | -1.29 | -12.95 % | +0.02 | 2 | 0.04 | -1.25 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.89 | -1.11 | -11.08 % | +0.20 | 5 | 0.04 | -1.06 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-17 1658.73 frente a media de 100 dias 2087.24 (debajo: fuera); XBT cierre del 2026-11-17 59026.10 frente a media de 100 dias 68400.95 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -7.26 % | 0 | 4 |
| Cruce 5/20 | -8.70 % | 0 | 10 |
| Momentum | -8.09 % | 0 | 7 |
| Rebote | -11.70 % | 3 | 4 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -5.80 % | 0 | 5 |
| Rebote rapido | -4.30 % | 4 | 4 |
| Rebalanceo semanal | -16.10 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -15.00 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (4 cerradas, 7 dias); Cruce 5/20 (10 cerradas, 7 dias); Momentum (7 cerradas, 7 dias); Rebote (7 cerradas, 7 dias); Cruce 10/30 + filtro (0 cerradas, 7 dias); Cruce 3/8 rapido (5 cerradas, 7 dias); Rebote rapido (8 cerradas, 7 dias); Rebalanceo semanal (0 cerradas, 7 dias); Tendencia H1 (diaria) (0 cerradas, 7 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 6.7 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
