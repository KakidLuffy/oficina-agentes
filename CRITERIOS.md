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

## 4. Laboratorio v2 (registrado el 12-nov-2026, ANTES de ejecutarlo con datos reales)

El laboratorio v1 usaba las 720 velas que da Kraken: unos 2 años en velas diarias, pero solo unos 120 días en velas de
4 h, y un único examen con el último 40 %. Con eso no se puede concluir nada. La v2 cambia el examen así, y nada de esto
se retoca después de ver resultados (cualquier ajuste posterior es una hipótesis nueva):

- **Datos**: velas de Coinbase (pares en EUR) desde que existe cada moneda, con 2 duraciones: **1 día y 6 h** (Coinbase
  no ofrece 4 h). Las mismas 12 monedas que antes; las que Coinbase no tenga en EUR se omiten y se dice cuáles.
- **Mismas variantes** que el v1 (101), con los mismos costes que en vivo (comisión 0,40 % + deslizamiento 0,05 %).
- **Examen por años naturales, en ventanas que avanzan**: se elige con el año Y−1 (entrenamiento) y se examina con el año Y.
  Así para cada año desde que hay datos. El año en curso cuenta si tiene al menos la mitad de sus velas.
  Una serie entra en un año si tiene al menos el 75 % de las velas del año de entrenamiento y el 50 % de las del examen.
  Un año necesita al menos 3 series para contar.
- **Una variante aprueba una serie en un año de examen** si cumple las tres cosas:
  1. hace **al menos 2 operaciones en ese año**;
  2. su resultado supera al de **mantener con la misma exposición media** (si estuvo dentro el 30 % del tiempo, se compara
     con el 30 % del resultado de comprar y mantener). Es la versión, para estrategias de una sola moneda, de la
     «cesta al 50 %» con la que se midió a H1;
  3. su **caída máxima** en ese año no es mayor que la de comprar y mantener.
- **Aprueba el año** si aprueba al menos el 60 % de las series de ese año.
- **Velas de 1 día y de 6 h se evalúan por separado**, cada una con su veredicto.
- **Es candidata** una variante que, en una duración de vela: aprueba **al menos el 60 % de los años de examen**, su
  resultado medio en el examen es **positivo** (gana dinero, no solo pierde menos) y estuvo **al menos una vez** entre las
  12 mejores del entrenamiento.
- **Control del azar**: con la tasa de aprobado de todas las variantes en todos los años se calcula cuántas variantes
  serían candidatas por pura casualidad (binomial). El veredicto es **POSIBLE** solo si hay al menos 2 candidatas y son
  más del doble de las esperadas por azar más una; si hay candidatas pero no tantas, **RUIDO**; si no hay, **NINGUNA**.
- Una candidata, como antes, **no opera sola**: se propone, y antes de entrar en simulación hay que registrarla aquí como
  hipótesis nueva.

## Registro de resultados

- **11-nov-2026, prueba histórica de H1: NO PASA** (`datos/backtest_h1.md`). Con datos de Coinbase desde el 2-sep-2017, H1 se apagó por su propia regla del −15 % el 30-dic-2017, a los 4 meses. Hasta ese día ganó un +65,4 %, frente al +72,4 % de la cesta al 50 %, y su caída máxima fue mayor (−19,3 % frente a −17,6 %). Las medias de 50, 150 y 200 días tampoco superan a la cesta. Sin la regla del −15 % (dato solo informativo) habría ganado un +328 %, frente al +525 % de la cesta al 50 %, aunque con menos caída (−43 % frente a −69 %). **Conforme a la sección 2, H1 queda descartada como hipótesis principal.** La v5 sigue en marcha como exploración. Una variante de H1 sin la regla del −15 % sería una hipótesis NUEVA y contaría como una comparación más.
