# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-26T09:17:47+00:00 UTC · Precio BTC/EUR: 55420 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (14.4 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 8.93 | -1.07 | -10.71 % | +0.61 | 22 | 0.47 | -0.61 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 8.94 | -1.06 | -10.65 % | +0.62 | 36 | 0.76 | -0.30 | 2026-11-11 | Con ETH, XBT |
| Momentum | 8.93 | -1.07 | -10.68 % | +0.62 | 30 | 0.63 | -0.44 | 2026-11-11 | Con ETH, XBT |
| Rebote | 8.79 | -1.21 | -12.09 % | +0.48 | 30 | 0.63 | -0.58 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.68 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.50 | -0.50 | -5.01 % | +1.18 | 14 | 0.31 | -0.19 | 2026-11-11 | En efectivo |
| Rebote rapido | 8.85 | -1.15 | -11.54 % | +0.53 | 44 | 0.95 | -0.20 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.58 | -1.42 | -14.21 % | +0.26 | 5 | 0.04 | -1.38 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.68 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.32 | -1.68 | -16.84 % | 0.00 | 1 | 0.04 | -1.64 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.34 | -1.66 | -16.63 % | +0.02 | 2 | 0.04 | -1.62 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.58 | -1.42 | -14.21 % | +0.26 | 5 | 0.04 | -1.38 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-25 1541.46 frente a media de 100 dias 2081.30 (debajo: fuera); XBT cierre del 2026-11-25 55042.40 frente a media de 100 dias 68446.43 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -13.13 % | 0 | 10 |
| Cruce 5/20 | -11.80 % | 1 | 16 |
| Momentum | -12.09 % | 1 | 13 |
| Rebote | -14.30 % | 3 | 12 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -7.20 % | 1 | 6 |
| Rebote rapido | -12.70 % | 8 | 14 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (10 cerradas, 14 dias); Cruce 5/20 (17 cerradas, 14 dias); Momentum (14 cerradas, 14 dias); Rebote (15 cerradas, 14 dias); Cruce 10/30 + filtro (0 cerradas, 14 dias); Cruce 3/8 rapido (7 cerradas, 14 dias); Rebote rapido (22 cerradas, 14 dias); Rebalanceo semanal (0 cerradas, 14 dias); Tendencia H1 (diaria) (0 cerradas, 14 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 14.4 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
