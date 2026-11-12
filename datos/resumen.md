# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-12T18:51:53+00:00 UTC · Precio BTC/EUR: 64760 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (0.8 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 10.00 | +0.00 | +0.00 % | +0.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 5/20 | 10.00 | +0.00 | +0.00 % | +0.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Momentum | 10.00 | +0.00 | +0.00 % | +0.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Rebote | 9.90 | -0.10 | -0.96 % | +0.19 | 2 | 0.04 | -0.05 | 2026-11-11 | Con ETH, XBT |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +0.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 10.00 | +0.00 | +0.00 % | +0.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Rebote rapido | 9.99 | -0.01 | -0.13 % | +0.27 | 1 | 0.02 | +0.01 | 2026-11-11 | Con XBT |
| Rebalanceo semanal | 9.75 | -0.25 | -2.46 % | +0.04 | 5 | 0.04 | -0.20 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +0.28 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 9.72 | -0.28 | -2.82 % | 0.00 | 1 | 0.04 | -0.24 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 9.77 | -0.23 | -2.29 % | +0.05 | 2 | 0.04 | -0.18 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | 0.00 % | 0 | 0 |
| Cruce 5/20 | 0.00 % | 0 | 0 |
| Momentum | 0.00 % | 0 | 0 |
| Rebote | -1.00 % | 0 | 0 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | 0.00 % | 0 | 0 |
| Rebote rapido | -0.10 % | 0 | 0 |
| Rebalanceo semanal | -2.70 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -2.80 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (0 cerradas, 1 dias); Cruce 5/20 (0 cerradas, 1 dias); Momentum (0 cerradas, 1 dias); Rebote (0 cerradas, 1 dias); Cruce 10/30 + filtro (0 cerradas, 1 dias); Cruce 3/8 rapido (0 cerradas, 1 dias); Rebote rapido (0 cerradas, 1 dias); Rebalanceo semanal (0 cerradas, 1 dias); Tendencia H1 (diaria) (0 cerradas, 1 dias). Antes de eso, el resultado puede ser pura suerte.

![Evolucion del capital](grafico.svg)

Aviso: solo hay 0.8 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
