# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-27T08:47:53+00:00 UTC · Precio BTC/EUR: 56268 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (15.4 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 9.08 | -0.92 | -9.16 % | +0.64 | 22 | 0.47 | -0.45 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 8.96 | -1.04 | -10.36 % | +0.52 | 40 | 0.84 | -0.19 | 2026-11-11 | Con ETH, XBT |
| Momentum | 9.08 | -0.92 | -9.17 % | +0.64 | 30 | 0.63 | -0.29 | 2026-11-11 | Con ETH, XBT |
| Rebote | 8.79 | -1.21 | -12.09 % | +0.35 | 30 | 0.63 | -0.58 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.56 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.53 | -0.47 | -4.71 % | +1.09 | 16 | 0.35 | -0.12 | 2026-11-11 | Con ETH, XBT |
| Rebote rapido | 8.85 | -1.15 | -11.54 % | +0.40 | 44 | 0.95 | -0.20 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.79 | -1.21 | -12.11 % | +0.35 | 5 | 0.04 | -1.17 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.56 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.44 | -1.56 | -15.56 % | 0.00 | 1 | 0.04 | -1.51 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.48 | -1.52 | -15.20 % | +0.04 | 2 | 0.04 | -1.47 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.79 | -1.21 | -12.11 % | +0.35 | 5 | 0.04 | -1.17 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-26 1538.65 frente a media de 100 dias 2080.13 (debajo: fuera); XBT cierre del 2026-11-26 55163.80 frente a media de 100 dias 68439.26 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -13.13 % | 0 | 10 |
| Cruce 5/20 | -12.20 % | 2 | 17 |
| Momentum | -12.09 % | 1 | 13 |
| Rebote | -14.30 % | 3 | 12 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -7.20 % | 1 | 6 |
| Rebote rapido | -12.70 % | 8 | 14 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (10 cerradas, 15 dias); Cruce 5/20 (19 cerradas, 15 dias); Momentum (14 cerradas, 15 dias); Rebote (15 cerradas, 15 dias); Cruce 10/30 + filtro (0 cerradas, 15 dias); Cruce 3/8 rapido (7 cerradas, 15 dias); Rebote rapido (22 cerradas, 15 dias); Rebalanceo semanal (0 cerradas, 15 dias); Tendencia H1 (diaria) (0 cerradas, 15 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 15.4 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
