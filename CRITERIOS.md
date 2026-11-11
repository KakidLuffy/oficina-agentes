# Criterios fijados de antemano (registrados el 11-nov-2026, ANTES de la prueba histórica de H1)

Este archivo se escribe y se sube a GitHub **antes** de ejecutar `backtest_h1.py`. La fecha del commit lo demuestra. Si
después se cambia un criterio, se anota aquí con su fecha y el motivo, y ese cambio cuenta como una hipótesis nueva.

Todo es con dinero **ficticio**. Que una estrategia pase estos criterios no la convierte en apta para dinero real.

## 1. Prueba histórica de «Tendencia H1 (diaria)» (`backtest_h1.py`)

- **Reglas**: exactamente las del agente en vivo, sin retocar nada.
  - Solo BTC y ETH, con velas diarias.
  - Compra cuando el cierre supera la media de 100 días y vende cuando cierra por debajo.
  - Cada compra es del 25 % del capital inicial.
  - Stop al −8 % del precio de entrada (equivale a perder el 2 % del capital).
  - Si en el mes la cuenta va un 6 % abajo, no hay compras nuevas.
  - Si cae un 15 % desde su máximo, se apaga.
- **Costes**: los mismos que en vivo, comisión del 0,40 % y deslizamiento del 0,05 % por operación.
- **Datos**: velas diarias BTC-EUR y ETH-EUR de Coinbase, desde que existen las dos monedas.
- **Referencia principal**: «Cesta al 50 %», que es comprar al principio un 25 % en BTC y un 25 % en ETH y mantenerlos, con el resto en efectivo. Tiene la misma exposición máxima que H1, así que la comparación es justa.

**H1 pasa la prueba histórica solo si cumple LAS TRES condiciones:**

1. Rentabilidad total tras costes **mayor** que la de la cesta al 50 % en el periodo completo.
2. Gana a la cesta al 50 % en **al menos la mitad** de los años naturales completos.
3. Su caída máxima es **menor** que la de la cesta al 50 %.

Además:

- Si se apaga por la regla del −15 %, la prueba se da por terminada en ese momento y la comparación se hace hasta ese día. Una regla de riesgo no se ignora a posteriori.
- Las medias de 50, 150 y 200 días se calculan **solo para ver si el resultado es robusto**. No sirven para elegir otra media. Si H1 solo funciona con la media de 100 días y no con sus vecinas, se considera frágil y no pasa. Precisado el 11-nov, antes de ejecutar la prueba: «funciona con sus vecinas» quiere decir que **al menos 2 de las 3** (50, 150 y 200) superan también a la cesta al 50 % en rentabilidad total.

## 2. Simulación en vivo v5 (desde el 11-nov-2026)

- **Si H1 NO pasa la prueba histórica**, se descarta como hipótesis principal. La v5 sigue en marcha, pero su resultado a los 21 días no puede rescatar a H1.
- **Si H1 pasa la prueba histórica**, los 21 días de la v5 son solo una comprobación de que el código funciona en vivo. Con una señal diaria, 21 días dan muy pocas operaciones. Para un veredicto en vivo hacen falta **al menos 90 días** o 30 operaciones cerradas, lo que llegue más tarde.
- Los demás agentes son exploratorios. Ninguno puede convertirse en principal por haber ganado en vivo. Si alguno destaca, se registra aquí como hipótesis nueva y se prueba primero con datos históricos.

## 3. Reglas de la oficina

- **No se retocan parámetros después de ver resultados.** Cualquier variante es una hipótesis nueva y cuenta como una comparación más.
- **Máximo 9 agentes.** Para añadir uno hay que retirar otro antes. Hay una prueba en `test_agentes.py` que lo vigila.
- **Cambiar reglas en vivo reinicia el reloj** (`VERSION`). Solo se cambia algo cuando se ha cumplido un plazo de evaluación o si hay un fallo de código.

## Registro de resultados

- **11-nov-2026, prueba histórica de H1: NO PASA** (`datos/backtest_h1.md`). Con datos de Coinbase desde el 2-sep-2017, H1 se apagó por su propia regla del −15 % el 30-dic-2017, a los 4 meses. Hasta ese día ganó un +65,4 %, frente al +72,4 % de la cesta al 50 %, y su caída máxima fue mayor (−19,3 % frente a −17,6 %). Las medias de 50, 150 y 200 días tampoco superan a la cesta. Sin la regla del −15 % (dato solo informativo) habría ganado un +328 %, frente al +525 % de la cesta al 50 %, aunque con menos caída (−43 % frente a −69 %). **Conforme a la sección 2, H1 queda descartada como hipótesis principal.** La v5 sigue en marcha como exploración. Una variante de H1 sin la regla del −15 % sería una hipótesis NUEVA y contaría como una comparación más.
