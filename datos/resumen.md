# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-18T08:17:53+00:00 UTC · Precio BTC/EUR: 58827 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (6.4 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 9.55 | -0.45 | -4.47 % | +0.73 | 10 | 0.22 | -0.23 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 9.27 | -0.73 | -7.33 % | +0.44 | 18 | 0.39 | -0.34 | 2026-11-11 | Con ETH, XBT |
| Momentum | 9.44 | -0.56 | -5.62 % | +0.61 | 14 | 0.31 | -0.26 | 2026-11-11 | Con ETH, XBT |
| Rebote | 9.34 | -0.66 | -6.56 % | +0.52 | 14 | 0.30 | -0.35 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.17 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.53 | -0.47 | -4.68 % | +0.70 | 8 | 0.18 | -0.29 | 2026-11-11 | Con ETH, XBT |
| Rebote rapido | 9.62 | -0.38 | -3.75 % | +0.80 | 16 | 0.36 | -0.02 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 9.02 | -0.98 | -9.77 % | +0.20 | 5 | 0.04 | -0.93 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.17 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.83 | -1.17 | -11.73 % | 0.00 | 1 | 0.04 | -1.13 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.86 | -1.14 | -11.38 % | +0.03 | 2 | 0.04 | -1.09 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 9.02 | -0.98 | -9.77 % | +0.20 | 5 | 0.04 | -0.93 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-17 1658.73 frente a media de 100 dias 2087.24 (debajo: fuera); XBT cierre del 2026-11-17 59026.10 frente a media de 100 dias 68400.95 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -4.98 % | 0 | 4 |
| Cruce 5/20 | -8.00 % | 0 | 8 |
| Momentum | -6.09 % | 0 | 6 |
| Rebote | -11.70 % | 3 | 4 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -4.70 % | 0 | 3 |
| Rebote rapido | -4.30 % | 4 | 4 |
| Rebalanceo semanal | -16.10 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -15.00 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (4 cerradas, 6 dias); Cruce 5/20 (8 cerradas, 6 dias); Momentum (6 cerradas, 6 dias); Rebote (7 cerradas, 6 dias); Cruce 10/30 + filtro (0 cerradas, 6 dias); Cruce 3/8 rapido (3 cerradas, 6 dias); Rebote rapido (8 cerradas, 6 dias); Rebalanceo semanal (0 cerradas, 6 dias); Tendencia H1 (diaria) (0 cerradas, 6 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 6.4 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
