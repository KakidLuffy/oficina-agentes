# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-25T04:14:51+00:00 UTC · Precio BTC/EUR: 54116 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (13.2 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 8.90 | -1.10 | -10.97 % | +0.78 | 20 | 0.43 | -0.67 | 2026-11-11 | En efectivo |
| Cruce 5/20 | 8.85 | -1.15 | -11.50 % | +0.73 | 34 | 0.72 | -0.43 | 2026-11-11 | En efectivo |
| Momentum | 8.85 | -1.15 | -11.50 % | +0.73 | 28 | 0.59 | -0.56 | 2026-11-11 | En efectivo |
| Rebote | 8.80 | -1.20 | -12.05 % | +0.67 | 28 | 0.59 | -0.61 | 2026-11-11 | Con ETH, XBT |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.88 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.50 | -0.50 | -5.01 % | +1.38 | 14 | 0.31 | -0.19 | 2026-11-11 | En efectivo |
| Rebote rapido | 8.78 | -1.22 | -12.18 % | +0.66 | 42 | 0.91 | -0.31 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.35 | -1.65 | -16.53 % | +0.23 | 5 | 0.04 | -1.61 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.88 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.12 | -1.88 | -18.79 % | 0.00 | 1 | 0.04 | -1.83 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.16 | -1.84 | -18.41 % | +0.04 | 2 | 0.04 | -1.80 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.35 | -1.65 | -16.53 % | +0.23 | 5 | 0.04 | -1.61 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-24 1531.06 frente a media de 100 dias 2082.39 (debajo: fuera); XBT cierre del 2026-11-24 54510.40 frente a media de 100 dias 68452.64 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -13.13 % | 0 | 10 |
| Cruce 5/20 | -11.80 % | 1 | 16 |
| Momentum | -12.09 % | 1 | 13 |
| Rebote | -13.40 % | 3 | 10 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -7.20 % | 1 | 6 |
| Rebote rapido | -12.20 % | 7 | 14 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (10 cerradas, 13 dias); Cruce 5/20 (17 cerradas, 13 dias); Momentum (14 cerradas, 13 dias); Rebote (13 cerradas, 13 dias); Cruce 10/30 + filtro (0 cerradas, 13 dias); Cruce 3/8 rapido (7 cerradas, 13 dias); Rebote rapido (21 cerradas, 13 dias); Rebalanceo semanal (0 cerradas, 13 dias); Tendencia H1 (diaria) (0 cerradas, 13 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 13.2 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
