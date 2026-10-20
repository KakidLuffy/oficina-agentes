# Oficina de agentes (simulación con dinero ficticio)

Este proyecto **no usa dinero real ni se conecta a ningún exchange**. Cuatro "agentes" empiezan con 50 € ficticios cada uno
y deciden comprar o vender las 20 monedas de mayor volumen contra EUR en Kraken (sin stablecoins ni monedas fiat), con precios reales. La lista se actualiza sola en cada ejecución. Sirve para ver, sin riesgo,
si alguna estrategia automática se comporta mejor que simplemente comprar y mantener.

## Cómo funciona
GitHub Actions ejecuta `agentes_nube.py` cada hora (a veces con retraso: GitHub no garantiza la hora exacta).
Cada paso mira las velas de 1 hora ya cerradas, deja decidir a cada agente y guarda todo en la carpeta `datos/`.
Cada agente puede tener hasta 5 monedas a la vez, con 10 € en cada una. Se restan una comisión del 0,25 % y un deslizamiento del 0,05 % en cada operación (0,3 % en monedas de poco volumen). "Comprar y mantener" sigue siendo solo BTC.

## Los agentes
- **Cruce 10/30 y Cruce 5/20:** compran cuando el precio medio reciente supera al de un periodo más largo (señal de subida) y venden cuando lo pierde.
- **Momentum:** compra tras una subida fuerte reciente y vende tras una bajada fuerte.
- **Rebote:** compra cuando el precio cae bastante por debajo de su media y vende al recuperarla.
- **Comprar y mantener:** no es un agente, es la referencia: compra al inicio y no vende.

## Seguridad simulada
Si un agente pierde 2 € en un día, no vuelve a comprar ese día. Si su capital baja de 35 €, se apaga.

## Qué hay en `datos/`
- `resumen.md`: estado actual, riesgo y gráfico (es lo primero que conviene mirar).
- `historial.csv`: capital de cada agente en cada ejecución.
- `operaciones.csv`: cada compra y venta.
- `grafico.svg`: evolución del capital.
- `estado.json`: memoria interna de la simulación (no editar).

`comparacion/` se genera a mano desde la pestaña Actions con el flujo "Comparar estrategias (historial)".

## Cómo interpretar los resultados
Una estrategia solo merecería atención si supera a "Comprar y mantener" de forma sostenida durante **varias semanas**
y en distintos tipos de mercado. Pocos días no demuestran nada, y los resultados pasados no garantizan beneficios futuros.
