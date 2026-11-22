# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-22T23:47:44+00:00 UTC · Precio BTC/EUR: 55747 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (11.0 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 9.07 | -0.93 | -9.29 % | +0.71 | 18 | 0.38 | -0.54 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 8.92 | -1.08 | -10.78 % | +0.56 | 30 | 0.64 | -0.44 | 2026-11-11 | Con ETH, XBT |
| Momentum | 8.90 | -1.10 | -11.03 % | +0.53 | 26 | 0.55 | -0.55 | 2026-11-11 | Con ETH, XBT |
| Rebote | 9.04 | -0.96 | -9.58 % | +0.68 | 26 | 0.55 | -0.41 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.63 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.34 | -0.66 | -6.59 % | +0.98 | 12 | 0.26 | -0.40 | 2026-11-11 | En efectivo |
| Rebote rapido | 9.03 | -0.97 | -9.68 % | +0.67 | 36 | 0.78 | -0.19 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.50 | -1.50 | -14.99 % | +0.14 | 5 | 0.04 | -1.45 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.63 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.37 | -1.63 | -16.35 % | 0.00 | 1 | 0.04 | -1.59 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.42 | -1.58 | -15.85 % | +0.05 | 2 | 0.04 | -1.54 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.50 | -1.50 | -14.99 % | +0.14 | 5 | 0.04 | -1.45 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-21 1536.41 frente a media de 100 dias 2084.44 (debajo: fuera); XBT cierre del 2026-11-21 54887.20 frente a media de 100 dias 68421.11 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -13.13 % | 0 | 8 |
| Cruce 5/20 | -11.60 % | 1 | 13 |
| Momentum | -11.99 % | 1 | 11 |
| Rebote | -13.40 % | 3 | 10 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -6.60 % | 0 | 6 |
| Rebote rapido | -11.90 % | 7 | 11 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (8 cerradas, 11 dias); Cruce 5/20 (14 cerradas, 11 dias); Momentum (12 cerradas, 11 dias); Rebote (13 cerradas, 11 dias); Cruce 10/30 + filtro (0 cerradas, 11 dias); Cruce 3/8 rapido (6 cerradas, 11 dias); Rebote rapido (18 cerradas, 11 dias); Rebalanceo semanal (0 cerradas, 11 dias); Tendencia H1 (diaria) (0 cerradas, 11 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 11.0 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
