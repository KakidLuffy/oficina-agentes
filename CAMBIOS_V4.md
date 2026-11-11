# Versión 4

Preparada el 5-nov-2026 y **ajustada el 11-nov-2026** con los 21 días completos de la v3 (21-oct a 11-nov). Al fusionarla,
`VERSION = 4` hace que la siguiente ejecución archive la v3 en `datos/archivo_10eur_v3_<fecha>/` y empiece de cero.

## Ajustes del 11-nov (tras la evaluación a 21 días)

- **Se conservan los cambios de main del 11-nov**: el agente «Tendencia H1 (diaria)» y que los agentes de señales solo
  compren BTC y ETH (`PERMITIDAS`). En la v3, antes de costes, las operaciones cerradas perdieron 13,86 €, sobre todo en
  monedas pequeñas (PEPE −4,24, ZEC −2,26, PUMP −2,24, ENA −1,87); en BTC/ETH, 49 operaciones perdieron 0,40 € antes de costes.
- **«Comprar y mantener (cesta)» = BTC + ETH al 50 %**: la cesta de referencia usa las mismas monedas que pueden comprar.
- **`min_horas = 6` solo en la mitad** (Cruce 10/30, Momentum, Cruce 3/8 rápido); Cruce 5/20, Rebote, Cruce 10/30 + filtro
  y Rebote rápido quedan como comparación. Con 21 días el respaldo era débil: de las 295 operaciones cerradas en menos de
  6 h, 103 se cerraron por stop (que esta regla no toca), y las de 6 h o más perdían más por operación (−0,040 € frente a −0,031 €).
- **`espera_h` como en la v3** (solo en los rápidos): solo 47 de 508 recompras fueron en menos de 6 h.
- **Resumen con columna «Antes de costes (EUR)»**: para separar si pierde la regla o los costes.
- **Limitación conocida**: con solo 2 monedas y 2 € por compra, los agentes de señales tienen como mucho 4 € de 10 €
  invertidos; frente a «Comprar y mantener» (100 % invertido) ganarán en caídas y perderán en subidas por eso, no por acertar.

## Cambios preparados el 5-nov

| Cambio | Por qué (datos de la v3, actualizados a 8-nov) | Riesgo |
|---|---|---|
| Excluir EURC y otras monedas estables | 80 operaciones con EURC en la v3 (vale siempre 1 €) y 0,70 € en costes, sin poder ganar nada. Con solo BTC/ETH ya no se compran, pero queda como red de seguridad | Ninguno |
| Retirar «Momentum rapido» y «Consenso 2 de 3» | Los que más operan: 318 y 192 operaciones; −30 % y −29 % | Con 18 días de datos puede ser mala racha, no mala regla; «Momentum» (148 operaciones) pierde lo mismo (−31 %) y sigue |
| `min_horas = 6` (11-nov: solo en la mitad, ver arriba): no vender por señal antes de 6 h (stop y objetivo sí actúan) | Las 277 operaciones cerradas en menos de 6 h perdieron 8,13 € con ~19 % de aciertos; costes totales 11,65 €. Ojo: las de 6 h o más pierden más por operación (−0,040 € frente a −0,029 €); la razón es pagar menos costes, no que las cortas sean peores | Puede alargar operaciones perdedoras en los agentes sin stop |
| ~~`espera_h = 6` en todos~~ (11-nov: descartado, ver arriba): no recomprar una moneda vendida hace menos de 6 h | Misma razón: menos compraventas | Puede perder alguna entrada buena |
| Nuevo agente «Rebalanceo semanal» (pedido por el usuario el 5-nov): cesta fija BTC, ETH, SOL, XRP y ADA a partes iguales; cada 7 días vende lo que no es de la cesta y rehace solo las posiciones desviadas más de un 35 % | Opera muy poco (5 operaciones en 15 días de prueba con precios inventados) y no persigue monedas de moda: en la v3, PUMP, ENA, ZEC y PEPE fueron las que más perdieron | Casi no cerrará operaciones: el criterio de 30 cierres no le sirve; hay que juzgarlo por días y frente a «Comprar y mantener» |
| Referencia nueva «Comprar y mantener (cesta)»: al empezar, 10 € a partes iguales entre las monedas que operan los agentes, sin tocarlas | En la v3 solo se comparaba con BTC, pero los agentes operan sobre todo monedas pequeñas, que cayeron más: la comparación no era justa | Si una moneda deja de cotizar, se queda con su último precio |
| Costes pagados por agente en `resumen.md` y en el parte del director (la web ya los muestra desde el 5-nov) | Los costes (11,65 € a 8-nov) explican casi toda la diferencia con «Comprar y mantener»: hay que verlos en cada informe | Ninguno |
| Los agentes de señales solo compran monedas de su universo (top 20 por volumen); la cesta se descarga aparte | Que el rebalanceo no cambie lo que operan los demás | Ninguno |
| El workflow solo se ejecuta con push a `main` | Antes, un push a cualquier rama con cambios en `agentes_nube.py` lanzaba la simulación | Ninguno |

Lo que **no** cambia: costes simulados (0,40 % + deslizamiento), capital (10 € por agente), límite de 7 €, velas de 1 h,
criterio de evaluación (21 días y 30 operaciones cerradas, superando a «Comprar y mantener»).

Comprobado con `python -m unittest test_agentes` (14 pruebas el 11-nov; el aviso del director ya se publicó en main el 5-nov) y simulando 600 velas inventadas: los agentes de señales comunes
operan entre un 0 % y un 28 % menos. Con precios inventados no se puede saber si ganarán más; eso solo lo dirá la v4 en vivo.

## No incluido a propósito

- **Margen extra antes de vender**: el mínimo de 6 h ya ataca el mismo problema (vender por movimientos pequeños). Añadir
  otro parámetro sin datos sería ajustar a ciegas; se decidirá con lo que enseñe la v4.
- **Universo fijo para todos los agentes**: elegirlo mirando las 2 semanas de la v3 sería sobreajustar. Lo prueba solo el
  agente de rebalanceo, con la lista de respaldo que ya existía.
- **Agente con IA (LLM)**: experimento aparte después de la v4, evaluado solo en vivo.

## Pendiente del usuario: que la oficina trabaje cada 30 minutos de verdad

GitHub ejecuta el programa cada 1-5 h en vez de cada 30 min (7 rondas en 24 h el 6-nov), y al vigilante le pasa lo mismo.
La solución habitual es que un servicio externo gratuito (p. ej. cron-job.org) lance la ronda:

1. GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token. Repositorio: solo
   `oficina-agentes`. Permiso: **Actions: Read and write** (nada más). Caducidad: 90 días.
2. cron-job.org → Create cronjob. URL:
   `https://api.github.com/repos/KakidLuffy/oficina-agentes/actions/workflows/agentes.yml/dispatches`,
   cada 30 min, método **POST**, cuerpo `{"ref":"main"}`, cabeceras `Authorization: Bearer <token>`,
   `Accept: application/vnd.github+json` y `X-GitHub-Api-Version: 2022-11-28`.
3. Comprobar en la pestaña Actions que aparecen rondas `workflow_dispatch` cada 30 min.

El token solo lo debe ver el usuario: no se guarda en el repositorio ni se comparte.
