# Oficina de agentes (dinero ficticio)

Ultima actualizacion: 2026-11-23T11:17:48+00:00 UTC · Precio BTC/EUR: 55866 (Kraken)
En marcha desde: 2026-11-11T23:09:56+00:00 UTC (11.5 dias)
Monedas vigiladas: las 20 de mayor volumen contra EUR (con datos en esta ejecucion: 20) · cada agente puede tener hasta 2 a la vez, 5.00 EUR en cada una · los agentes de senales solo compran XBT, ETH
Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). Todos los agentes son exploratorios: que alguno gane puede ser casualidad.
Costes simulados por operacion: comision 0.40 % + deslizamiento 0.05 % (0.3 % en monedas de poco volumen) · limite de perdida diaria: 0.40 EUR

| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Cruce 10/30 | 9.09 | -0.91 | -9.12 % | +0.71 | 18 | 0.38 | -0.53 | 2026-11-11 | Con ETH, XBT |
| Cruce 5/20 | 8.86 | -1.14 | -11.37 % | +0.48 | 32 | 0.68 | -0.45 | 2026-11-11 | Con ETH, XBT |
| Momentum | 8.91 | -1.09 | -10.86 % | +0.53 | 26 | 0.55 | -0.54 | 2026-11-11 | Con ETH, XBT |
| Rebote | 9.04 | -0.96 | -9.58 % | +0.66 | 26 | 0.55 | -0.41 | 2026-11-11 | En efectivo |
| Cruce 10/30 + filtro | 10.00 | +0.00 | +0.00 % | +1.62 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Cruce 3/8 rapido | 9.30 | -0.70 | -6.99 % | +0.92 | 13 | 0.29 | -0.41 | 2026-11-11 | Con XBT |
| Rebote rapido | 9.03 | -0.97 | -9.68 % | +0.65 | 36 | 0.78 | -0.19 | 2026-11-11 | En efectivo |
| Rebalanceo semanal | 8.59 | -1.41 | -14.11 % | +0.21 | 5 | 0.04 | -1.37 | 2026-11-11 | Con ADA, ETH, SOL, XBT, XRP |
| Tendencia H1 (diaria) | 10.00 | +0.00 | +0.00 % | +1.62 | 0 | 0.00 | +0.00 | 2026-11-11 | En efectivo |
| Comprar y mantener (solo BTC) | 8.38 | -1.62 | -16.17 % | 0.00 | 1 | 0.04 | -1.57 | 2026-11-11 | Referencia |
| Comprar y mantener (cesta) | 8.43 | -1.57 | -15.68 % | +0.05 | 2 | 0.04 | -1.52 | 2026-11-11 | Referencia: 2 monedas del inicio a partes iguales |
| Mantener la cesta del Rebalanceo | 8.59 | -1.41 | -14.11 % | +0.21 | 5 | 0.04 | -1.37 | 2026-11-11 | Referencia del Rebalanceo: sus 5 monedas sin rebalancear |

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
| Cruce 3/8 rapido | -7.20 % | 0 | 6 |
| Rebote rapido | -11.90 % | 7 | 11 |
| Rebalanceo semanal | -21.60 % | 0 | 0 |
| Tendencia H1 (diaria) | 0.00 % | 0 | 0 |
| Comprar y mantener | -23.70 % | 0 | 0 |

Caida maxima = lo que llego a perder cada agente desde su mejor momento. Una operacion cuenta cuando se cierra con su venta.

⚠ Aun sin datos suficientes (se exigen 30 operaciones cerradas y 21 dias): Cruce 10/30 (8 cerradas, 12 dias); Cruce 5/20 (15 cerradas, 12 dias); Momentum (12 cerradas, 12 dias); Rebote (13 cerradas, 12 dias); Cruce 10/30 + filtro (0 cerradas, 12 dias); Cruce 3/8 rapido (6 cerradas, 12 dias); Rebote rapido (18 cerradas, 12 dias); Rebalanceo semanal (0 cerradas, 12 dias); Tendencia H1 (diaria) (0 cerradas, 12 dias). Antes de eso, el resultado puede ser pura suerte. El 9-feb-2027 (90 dias) el que no llegue a 30 cerradas se declara «no evaluable con esta muestra» (CRITERIOS.md, seccion 5).

![Evolucion del capital](grafico.svg)

Aviso: solo hay 11.5 dias de datos; aun no hay base para concluir que una estrategia sea mejor.

Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.
Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.
Estos resultados no garantizan beneficios futuros.
