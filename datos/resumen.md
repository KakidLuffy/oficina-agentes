# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-28T15:17:44+00:00 UTC · Precio BTC/EUR: 54266 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (16.7 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 8.78 | -1.22 | -12.25 % | +0.63 | 24 | 0.50 | -0.72 | 2026-11-11 | En efectivo |
| Cruce 5/20 | 8.61 | -1.39 | -13.86 % | +0.47 | 42 | 0.88 | -0.51 | 2026-11-11 | En efectivo |
| Momentum | 8.55 | -1.45 | -14.45 % | +0.41 | 34 | 0.71 | -0.73 | 2026-11-11 | En efectivo |
| Rebote | 8.77 | -1.23 | -12.28 % | +0.63 | 32 | 0.67 | -0.56 | 2026-11-11 | Con ETH, XBT |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.86 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.47 | -0.53 | -5.26 % | +1.33 | 18 | 0.39 | -0.13 | 2026-11-11 | En efectivo |
| Rebote rapido | 8.87 | -1.13 | -11.28 % | +0.73 | 48 | 1.03 | -0.10 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.45 | -1.55 | -15.48 % | +0.31 | 5 | 0.04 | -1.50 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.86 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.14 | -1.86 | -18.57 % | 0.00 | 1 | 0.04 | -1.81 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.14 | -1.86 | -18.56 % | +0.00 | 2 | 0.04 | -1.81 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.45 | -1.55 | -15.48 % | +0.31 | 5 | 0.04 | -1.50 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

Rebalanceo semanal frente a mantener sus mismas 5 monedas sin rebalancear: +0.00 EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC).

Regla de Tendencia H1 (diaria) (ultimo cierre diario): ETH cierre del 2026-11-27 1518.25 frente a media de 100 dias 2076.03 (debajo: fuera); XBT cierre del 2026-11-27 54720.60 frente a media de 100 dias 68393.00 (debajo: fuera).

Riesgo (calculado con el historial guardado):

| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |
|---|---:|---:|---:|
| Cruce 10/30 | -13.13 % | 0 | 12 |
| Cruce 5/20 | -14.00 % | 2 | 19 |
| Momentum | -14.59 % | 1 | 16 |
| Rebote | -14.30 % | 3 | 12 |
| Cruce 10/30 + filtro | 0.00 % | 0 | 0 |
| Cruce 3/8 rapido | -7.20 % | 1 | 8 |
| Rebote rapido | -12.70 % | 9 | 15 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (12 cerradas, 17 dias); Cruce 5/20 (21 cerradas, 17 dias); Momentum (17 cerradas, 17 dias); Rebote (15 cerradas, 17 dias); Cruce 10/30 + filtro (0 cerradas, 17 dias); Cruce 3/8 rapido (9 cerradas, 17 dias); Rebote rapido (24 cerradas, 17 dias); Rebalanceo semanal (0 cerradas, 17 dias); Tendencia H1 (diaria) (0 cerradas, 17 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 16.7 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
