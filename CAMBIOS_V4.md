# Versión 4 (propuesta, NO activa)

Preparada el 5-nov-2026 con los datos de la v3 (en marcha desde el 21-oct). **No se debe fusionar antes del
11-nov-2026 a las 12:38 (hora de Madrid)**, cuando la v3 cumple los 21 días de evaluación. Al fusionarla, `VERSION = 4`
hace que la siguiente ejecución archive la v3 en `datos/archivo_10eur_v3_<fecha>/` y empiece de cero.

| Cambio | Por qué (datos de la v3, a 5-nov) | Riesgo |
|---|---|---|
| Excluir EURC y otras monedas estables | 51 operaciones con EURC (vale siempre 1 €) y 0,46 € en costes, sin poder ganar nada | Ninguno |
| Retirar «Momentum rapido» y «Consenso 2 de 3» | Los que más operan: 288 y 165 operaciones; −29 % y −26 % | Con 15 días de datos puede ser mala racha, no mala regla |
| `min_horas = 6` en todos: no vender por señal antes de 6 h (stop y objetivo sí actúan) | Las 245 operaciones cerradas en menos de 6 h perdieron 7,16 € con ~20 % de aciertos; costes totales 10,57 € | Puede alargar operaciones perdedoras en los agentes sin stop |
| `espera_h = 6` en todos: no recomprar una moneda vendida hace menos de 6 h | Misma razón: menos compraventas | Puede perder alguna entrada buena |
| Nuevo agente «Rebalanceo semanal» (pedido por el usuario el 5-nov): cesta fija BTC, ETH, SOL, XRP y ADA a partes iguales; cada 7 días vende lo que no es de la cesta y rehace solo las posiciones desviadas más de un 35 % | Opera muy poco (5 operaciones en 15 días de prueba con precios inventados) y no persigue monedas de moda: en la v3, PUMP, ENA, ZEC y PEPE fueron las que más perdieron | Casi no cerrará operaciones: el criterio de 30 cierres no le sirve; hay que juzgarlo por días y frente a «Comprar y mantener» |
| Los agentes de señales solo compran monedas de su universo (top 20 por volumen); la cesta se descarga aparte | Que el rebalanceo no cambie lo que operan los demás | Ninguno |
| El workflow solo se ejecuta con push a `main` | Antes, un push a cualquier rama con cambios en `agentes_nube.py` lanzaba la simulación | Ninguno |

Lo que **no** cambia: costes simulados (0,40 % + deslizamiento), capital (10 € por agente), límite de 7 €, velas de 1 h,
criterio de evaluación (21 días y 30 operaciones cerradas, superando a «Comprar y mantener»).

Comprobado con `python -m unittest test_agentes` (9 pruebas; el aviso del director ya se publicó en main el 5-nov) y simulando 600 velas inventadas: los agentes de señales comunes
operan entre un 0 % y un 28 % menos. Con precios inventados no se puede saber si ganarán más; eso solo lo dirá la v4 en vivo.
