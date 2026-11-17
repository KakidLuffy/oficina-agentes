# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-17T03:17:44+00:00 UTC · Precio BTC/EUR: 58735 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (5.2 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 9.76 | -0.24 | -2.44 % | +0.94 | 6 | 0.13 | -0.11 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 9.57 | -0.43 | -4.33 % | +0.75 | 12 | 0.26 | -0.17 | 2026-11-11 | Con ETH, XBT |
| Momentum | 9.51 | -0.49 | -4.89 % | +0.70 | 11 | 0.24 | -0.25 | 2026-11-11 | Con XBT |
| Rebote | 9.23 | -0.77 | -7.73 % | +0.41 | 8 | 0.17 | -0.60 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.19 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.88 | -0.12 | -1.20 % | +1.07 | 2 | 0.04 | -0.08 | 2026-11-11 | En efectivo |
| Rebote rapido | 9.57 | -0.43 | -4.34 % | +0.75 | 12 | 0.27 | -0.17 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.86 | -1.14 | -11.36 % | +0.05 | 5 | 0.04 | -1.09 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.19 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.81 | -1.19 | -11.86 % | 0.00 | 1 | 0.04 | -1.14 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.87 | -1.13 | -11.28 % | +0.06 | 2 | 0.04 | -1.08 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.86 | -1.14 | -11.36 % | +0.05 | 5 | 0.04 | -1.09 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-16 1655.10 frente a media de 100 dias 2087.18 (debajo: fuera); XBT cierre del 2026-11-16 58976.20 frente a media de 100 dias 68372.07 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -3.08 % | 0 | 2 |
| Cruce 5/20 | -4.50 % | 0 | 5 |
| Momentum | -5.00 % | 0 | 5 |
| Rebote | -11.70 % | 0 | 4 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -1.30 % | 0 | 1 |
| Rebote rapido | -4.30 % | 2 | 4 |
| Rebalanceo semanal | -16.10 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -15.00 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (2 cerradas, 5 dias); Cruce 5/20 (5 cerradas, 5 dias); Momentum (5 cerradas, 5 dias); Rebote (4 cerradas, 5 dias); Cruce 10/30 + filtro (0 cerradas, 5 dias); Cruce 3/8 rapido (1 cerradas, 5 dias); Rebote rapido (6 cerradas, 5 dias); Rebalanceo semanal (0 cerradas, 5 dias); Tendencia H1 (diaria) (0 cerradas, 5 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 5.2 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
