# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-21T21:17:45+00:00 UTC · Precio BTC/EUR: 55113 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (9.9 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 8.93 | -1.07 | -10.69 % | +0.66 | 18 | 0.38 | -0.68 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 9.11 | -0.89 | -8.93 % | +0.84 | 26 | 0.56 | -0.34 | 2026-11-11 | Con ETH, XBT |
| Momentum | 9.07 | -0.93 | -9.26 % | +0.80 | 22 | 0.47 | -0.46 | 2026-11-11 | Con ETH, XBT |
| Rebote | 9.04 | -0.96 | -9.58 % | +0.77 | 26 | 0.55 | -0.41 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.73 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.42 | -0.58 | -5.79 % | +1.15 | 10 | 0.22 | -0.36 | 2026-11-11 | En efectivo |
| Rebote rapido | 9.00 | -1.00 | -10.00 % | +0.73 | 34 | 0.74 | -0.26 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.46 | -1.54 | -15.35 % | +0.19 | 5 | 0.04 | -1.49 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.73 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.27 | -1.73 | -17.30 % | 0.00 | 1 | 0.04 | -1.68 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.29 | -1.71 | -17.11 % | +0.02 | 2 | 0.04 | -1.67 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.46 | -1.54 | -15.35 % | +0.19 | 5 | 0.04 | -1.49 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-20 1478.54 frente a media de 100 dias 2085.42 (debajo: fuera); XBT cierre del 2026-11-20 53687.60 frente a media de 100 dias 68422.30 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -11.44 % | 0 | 8 |
| Cruce 5/20 | -11.10 % | 0 | 12 |
| Momentum | -10.89 % | 0 | 10 |
| Rebote | -13.40 % | 3 | 10 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -5.80 % | 0 | 5 |
| Rebote rapido | -11.90 % | 6 | 11 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (8 cerradas, 10 dias); Cruce 5/20 (12 cerradas, 10 dias); Momentum (10 cerradas, 10 dias); Rebote (13 cerradas, 10 dias); Cruce 10/30 + filtro (0 cerradas, 10 dias); Cruce 3/8 rapido (5 cerradas, 10 dias); Rebote rapido (17 cerradas, 10 dias); Rebalanceo semanal (0 cerradas, 10 dias); Tendencia H1 (diaria) (0 cerradas, 10 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 9.9 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
