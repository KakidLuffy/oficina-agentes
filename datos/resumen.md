# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-23T20:17:45+00:00 UTC · Precio BTC/EUR: 56289 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (11.9 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 9.18 | -0.82 | -8.18 % | +0.74 | 18 | 0.38 | -0.43 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 8.95 | -1.05 | -10.50 % | +0.50 | 32 | 0.68 | -0.37 | 2026-11-11 | Con ETH, XBT |
| Momentum | 9.01 | -0.99 | -9.94 % | +0.56 | 26 | 0.55 | -0.44 | 2026-11-11 | Con ETH, XBT |
| Rebote | 9.04 | -0.96 | -9.58 % | +0.60 | 26 | 0.55 | -0.41 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.55 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.50 | -0.50 | -5.01 % | +1.05 | 14 | 0.31 | -0.19 | 2026-11-11 | En efectivo |
| Rebote rapido | 9.01 | -0.99 | -9.88 % | +0.57 | 38 | 0.82 | -0.17 | 2026-11-11 | Con ETH, XBT |
| Rebalanceo semanal | 8.73 | -1.27 | -12.74 % | +0.28 | 5 | 0.04 | -1.23 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.55 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.45 | -1.55 | -15.53 % | 0.00 | 1 | 0.04 | -1.51 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.52 | -1.48 | -14.83 % | +0.07 | 2 | 0.04 | -1.44 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.73 | -1.27 | -12.74 % | +0.28 | 5 | 0.04 | -1.23 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-22 1569.28 frente a media de 100 dias 2083.87 (debajo: fuera); XBT cierre del 2026-11-22 55803.40 frente a media de 100 dias 68434.54 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -13.13 % | 0 | 8 |
| Cruce 5/20 | -11.80 % | 1 | 14 |
| Momentum | -12.09 % | 1 | 11 |
| Rebote | -13.40 % | 3 | 10 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -7.20 % | 1 | 6 |
| Rebote rapido | -11.90 % | 7 | 11 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (8 cerradas, 12 dias); Cruce 5/20 (15 cerradas, 12 dias); Momentum (12 cerradas, 12 dias); Rebote (13 cerradas, 12 dias); Cruce 10/30 + filtro (0 cerradas, 12 dias); Cruce 3/8 rapido (7 cerradas, 12 dias); Rebote rapido (18 cerradas, 12 dias); Rebalanceo semanal (0 cerradas, 12 dias); Tendencia H1 (diaria) (0 cerradas, 12 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 11.9 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
