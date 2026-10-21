# Registro de implementación de las 20 mejoras

Rama de trabajo: `mejoras-crypto` (no se ha tocado `main`). Todo sigue siendo simulación con dinero ficticio; no existe código de operación real ni claves.

## Tabla de progreso

| # | ID | Mejora | Estado |
|---|---|---|---|
| 1 | CRYPTO-015 | Pruebas automáticas | VALIDADA |
| 2 | CRYPTO-018 | Persistencia atómica | VALIDADA |
| 3 | CRYPTO-011 | Archivo completo con manifiesto | VALIDADA |
| 4 | CRYPTO-017 | Robustez de GitHub Actions | IMPLEMENTADA (falta ver una ejecución real en GitHub) |
| 5 | CRYPTO-008 | Validación de velas | VALIDADA (datos reales de Kraken sin probar: la API no es accesible desde aquí) |
| 6 | CRYPTO-009 | Alineación de marcas temporales | VALIDADA |
| 7 | CRYPTO-005 | Columnas vela_inicio / decision_utc | VALIDADA |
| 8 | CRYPTO-013 | Módulo único de estrategias | VALIDADA |
| 9 | CRYPTO-002 | Ejecución en la vela siguiente | VALIDADA (con datos sintéticos; falta una pasada con Kraken real) |
| 10 | CRYPTO-006 | Mínimos y precisión del exchange | IMPLEMENTADA (valores reales de Kraken sin verificar desde aquí) |
| 11 | CRYPTO-001 | Posiciones fuera del universo | VALIDADA |
| 12 | CRYPTO-007 | Modelo de costes compartido | VALIDADA (horquilla y deslizamiento son supuestos, no medidos) |
| 13 | CRYPTO-012 | Precisión decimal | VALIDADA |
| 14 | CRYPTO-010 | Sin historial inventado | VALIDADA (panel: comprobación visual pendiente en etapa 6) |
| 15 | CRYPTO-004 | Sesgo de supervivencia | IMPLEMENTADA (reduce, no elimina) |
| 16 | CRYPTO-003 | Walk-forward y regímenes | PENDIENTE |
| 17 | CRYPTO-014 | Métricas avanzadas | PENDIENTE |
| 18 | CRYPTO-016 | Decisiones rechazadas + alertas | PENDIENTE |
| 19 | CRYPTO-019 | Seguridad del panel | PENDIENTE |
| 20 | CRYPTO-020 | Analista de IA (solo propuestas) | PENDIENTE |

## Preparación (2026-10-22)
- Rama `mejoras-crypto` creada desde `main` (f383ff8). Copia de `datos/` guardada fuera del repositorio como línea base.
- Comprobado: ninguna referencia a claves, órdenes reales ni saldos en los `.py`.
- Línea base: sintaxis OK en los 5 módulos; modo `--demo` funciona.

## Mejora 1 — CRYPTO-015 Pruebas automáticas
- **Archivos:** `tests/base.py`, `tests/test_estrategias.py`, `tests/test_simulacion.py`, `tests/test_informe_lab.py`.
- **Cambio:** batería con `unittest` (solo librería estándar, sin red). Se ejecuta con `python3 -m unittest discover -s tests -t .`.
- **Cubre:** señales de las estrategias, coste ida y vuelta, coste registrado = dinero perdido, deslizamiento por volumen, apagado por riesgo, no actuar sobre vela abierta, catch-up de velas, idempotencia, stop de pérdida, archivar, migrar, ajustar historial, ciclo completo en demo, métricas del informe, variantes del laboratorio.
- **Resultado:** 28 pruebas, todas correctas.
- **Limitación conocida:** una prueba documenta que `equity` valora a 0 una moneda sin precio (se corrige en CRYPTO-001).

## Mejora 2 — CRYPTO-018 Persistencia atómica
- **Archivos:** `persistencia.py` (nuevo), `agentes_nube.py`, `informe.py`, `director.py`, `laboratorio.py`, `comparar_estrategias.py`, `tests/test_persistencia.py`, `tests/test_simulacion.py`.
- **Cambio:** `escribir_atomico` (temporal + fsync + `os.replace`) para todos los archivos generados. Estado, historial y operaciones se guardan en una **transacción** con diario (`datos/.tx/journal.json` con huellas SHA-256): si el proceso muere antes del diario no cambia nada; si muere después, `recuperar()` termina la escritura al arrancar. Las operaciones de una ejecución se acumulan en `COLA_OPS` y se escriben junto con el estado (antes se añadían a `operaciones.csv` al vuelo, y un corte podía duplicarlas al repetir).
- **Pruebas:** 10 nuevas (escritura atómica, fallo de `replace`, transacción, recuperación completada/descartada, hash corrupto, cortes antes/después del diario sin duplicados). Total 38 correctas. Ejecución real en modo demo de simulación, director y laboratorio sin errores ni temporales sobrantes.
- **Riesgo residual:** `resumen.md` y `grafico.svg` son derivados y se escriben aparte (atómicos, pero no dentro de la transacción; se regeneran en la siguiente ejecución). Los CSV se reescriben enteros en cada paso (coste lineal; irrelevante con este volumen).

## Mejora 3 — CRYPTO-011 Archivo completo con manifiesto
- **Archivos:** `archivado.py` (nuevo), `agentes_nube.py`, `tests/test_archivado.py`.
- **Cambio:** el archivado ya no *mueve* sin comprobar: copia → compara SHA-256 de cada copia → escribe `MANIFIESTO.json` (archivos, bytes, huella, filas de los CSV, motivo, versión y capital anterior/nuevo, fecha) → solo entonces borra los originales de la simulación. Si algo falla, los originales quedan y la carpeta se marca `INCOMPLETO.txt`. Nunca sobrescribe un archivo previo (sufijo `_2`, `_3`…). Además **copia** como contexto `director_estado.json`, `parte_director.json`, `laboratorio.json`, `memoria.jsonl`, `propuestas.md` (no se borran: el director y el laboratorio siguen vivos). `verificar()` detecta archivos faltantes o manipulados.
- **Pruebas:** 5 nuevas (archivar+verificar, no sobrescribir, sin archivos, fallo de copia conserva originales, manipulación detectada) + comprobación del manifiesto en el test de `archivar`. Prueba real en demo: cambio de versión → archivo con manifiesto, `verificar` = sin problemas. Total 43 correctas.
- **Nota:** los archivos antiguos ya existentes (`archivo_50eur_*`, `archivo_10eur_v1_*`) no tienen manifiesto; se podría generar uno retroactivo (no se hace para no tocar históricos sin autorización).

## Mejora 4 — CRYPTO-017 Robustez de GitHub Actions
- **Archivos:** `.github/workflows/{agentes,director,laboratorio,comparar}.yml`, `scripts/guardar_datos.sh`, `scripts/reintentar.sh`, `verificar_salida.py`, `requirements.txt`, `tests/test_workflows.py`.
- **Cambios:**
  - Acciones fijadas por SHA completo (`actions/checkout` v4.3.1 = `34e1148…`, `actions/setup-python` v5.6.0 = `a26af69…`; SHAs leídos de los repositorios oficiales con `git ls-remote`, no inventados).
  - Permisos: `contents: read` por defecto y `contents: write` solo en el trabajo que publica.
  - `guardar_datos.sh`: commit + `pull --rebase` + `push` con hasta 5 reintentos y espera creciente; en conflicto hace `rebase --abort` y reintenta; **nunca** `--force`; si agota los intentos falla en rojo (visible) en vez de perder datos en silencio.
  - `reintentar.sh`: hasta 3 intentos para fallos de red de la simulación y el laboratorio (repetir es seguro gracias a la mejora 2).
  - La simulación horaria ahora ejecuta antes las pruebas automáticas y después `verificar_salida.py` (JSON válido, efectivo no negativo, posiciones positivas, cabeceras/columnas CSV, sin transacción pendiente); si algo falla, **no se publica**.
  - El disparador `push` de la simulación se limita a `branches: [main]` (una rama de pruebas no puede lanzarla).
  - `requirements.txt` documenta que solo se usa la librería estándar.
- **Pruebas:** 9 nuevas (verificador, acciones fijadas, permisos, sin `--force`, solo `main`, y dos pruebas reales de `guardar_datos.sh` con un remoto git local: sin cambios y adelantamiento de otro proceso). Total 52 correctas. YAML de los 4 flujos validado.
- **Pendiente / riesgos:** los flujos solo se pueden probar de verdad dentro de GitHub (ejecutar a mano tras fusionar). Si una prueba unitaria fallara, la simulación horaria se detendría hasta arreglarla (intencionado: mejor parar que operar con código roto, pero hay que mirar las alertas). El caso de conflicto en el mismo archivo tras 5 intentos no se prueba automáticamente (tardaría ~75 s).
- **Detección de fallos:** un flujo fallido ya deja el trabajo en rojo; la alerta deduplicada por Issue se hará en la mejora 18.

## Mejora 5 — CRYPTO-008 Validación de velas
- **Archivos:** `velas.py` (nuevo), `agentes_nube.py`, `tests/test_velas.py`, `tests/test_simulacion.py`, `tests/base.py`.
- **Cambio:** las velas pasan de `(ts, cierre)` a `Vela(ts, o, h, l, c, v)` (necesario también para la mejora 9). `validar()` aplica una política explícita: **descarta** NaN/inf, precios ≤ 0, volumen negativo, OHLC incoherente y marcas no alineadas; **duplicadas** → gana la última; **desordenadas** → se ordenan; **huecos** → nunca se rellenan y las señales usan solo la cola contigua posterior; **salto anómalo** (>40 % entre cierres) → se conserva el dato pero se bloquean compras nuevas en ese par en esa ejecución (las posiciones abiertas siguen valoradas y las ventas permitidas); **vela abierta** → no es error. Incidencias registradas (sin repetirse cada hora) en `datos/incidencias_datos.csv` dentro de la transacción. Un par sin ninguna vela utilizable se ignora y se avisa.
- **Pruebas:** 12 de `velas.py` + 3 de integración (bloqueo de compras, registro único, par inutilizable). Total 67 correctas; ejecución demo de extremo a extremo y `verificar_salida.py` correcto.
- **Riesgos:** (1) en Kraken los pares poco líquidos omiten velas sin operaciones; esos huecos reales recortan la serie utilizable (conservador; es el comportamiento deseado). (2) No se pudo probar con respuestas reales de Kraken (sin acceso), solo con el formato documentado `[time, open, high, low, close, vwap, volume, count]`; la primera ejecución real debe revisarse. (3) El umbral del 40 % es una decisión de diseño, ajustable en `velas.SALTO_MAX`.

## Mejora 6 — CRYPTO-009 Alineación de marcas temporales (laboratorio)
- **Archivos:** `laboratorio.py`, `tests/test_informe_lab.py`.
- **Problema:** `descargar()` devolvía solo cierres y quitaba "la última vela" a ciegas; la fuerza relativa comparaba cada moneda con BTC **por posición en la lista**, de modo que si una serie empezaba/terminaba en otra hora se comparaba con el BTC equivocado.
- **Cambio:** `descargar()` devuelve velas con marca temporal, ya validadas (mejora 5) y solo las **cerradas por su marca** (`solo_cerradas`); `Serie` guarda `ts`; `alinear()` calcula para cada vela el índice de BTC con la **misma marca temporal** (`ref_idx`); `relativa()` no emite señal si falta la hora común. El modo demo genera marcas alineadas.
- **Pruebas:** 4 nuevas (alineación con desfase, relativa con BTC de la misma hora y sin hora común, vela abierta, demo). Ejecución completa del laboratorio demo correcta.
- **Efecto esperado:** el veredicto del laboratorio puede cambiar en la familia de fuerza relativa al recalcularse con la alineación correcta (no se ha ejecutado con datos reales: sin acceso a Kraken desde aquí).

## Mejora 7 — CRYPTO-005 Columnas `vela_inicio_utc` y `decision_utc`
- **Archivos:** `agentes_nube.py`, `verificar_salida.py`, `tests/test_simulacion.py`, `.gitignore`.
- **Problema:** `fecha_utc` era el inicio de la vela, pero la decisión solo puede conocerse al cierre (una hora después): la hora anotada parecía anterior a la decisión. Las ventas por apagado de riesgo llevaban la hora real, mezclando dos significados.
- **Cambio:** se añaden dos columnas al final (`vela_inicio_utc`, `decision_utc`); `fecha_utc` se conserva con su significado para no romper el panel, director e informes (todos leen por nombre de columna). Las ventas por apagado registran la vela cuyo precio se usó y la hora real como decisión. Migración automática y atómica de `operaciones.csv` de 8 columnas a 10: se **deriva solo lo cierto** (operaciones normales: vela = fecha, decisión = +1 h); en las antiguas de apagado la vela queda vacía (desconocida) y no se inventa. Probado sobre una copia de las 37 operaciones reales actuales: se conservan todas.
- **Higiene:** había colado `__pycache__` en dos commits míos; se quita del índice y se añade `.gitignore`.
- **Pruebas:** 4 nuevas (normal, apagado, migración que no inventa, cabecera del verificador). Total 75 correctas.

## Mejora 8 — CRYPTO-013 Módulo único de estrategias
- **Archivos:** `estrategias.py` (nuevo), `agentes_nube.py`, `laboratorio.py`, `comparar_estrategias.py`, `tests/test_estrategias.py`, `tests/legacy_estrategias.py`.
- **Problema:** la simulación, el laboratorio y la comparación tenían **tres copias** de las estrategias con diferencias sutiles (p. ej. umbrales de datos mínimos), así que lo "probado" en el laboratorio no era exactamente lo que operaba.
- **Cambio:** un único módulo con `Serie`, las familias (cruce con hueco, momentum, rebote, ruptura, filtro, volatilidad, fuerza relativa, consenso), la definición de los 9 agentes en vivo y sus reglas rápidas. La simulación construye una `Serie` por moneda e invoca `decidir(serie, i, 1.0)`; el laboratorio y la comparación importan las mismas funciones.
- **Garantías (pruebas):** (1) **equivalencia**: copia literal de las funciones antiguas (`tests/legacy_estrategias.py`, de `main`) frente a las nuevas, 9 agentes × 5 series aleatorias × todas las velas desde la 40ª → 0 diferencias; (2) **sin mirar el futuro**: cambiar por completo las velas posteriores a `i` no altera la señal en `i` (agentes y familias); (3) laboratorio/comparación usan los mismos objetos. Ejecución completa de simulación, laboratorio, comparación y director en demo sin errores.
- **Diferencia reconocida:** en las primeras velas de una serie (índice < 40) el código antiguo exigía una vela más de historial en momentum/filtro; irrelevante con 220 velas de historia.

## Mejora 9 — CRYPTO-002 Ejecución en la vela siguiente, con horquilla
- **Archivos:** `ejecucion.py` (nuevo), `agentes_nube.py`, `laboratorio.py`, `comparar_estrategias.py`, `estrategias.py`, `tests/test_ejecucion.py`, `tests/test_simulacion.py`, `tests/test_e2e_horas.py`.
- **Problema:** las órdenes se ejecutaban al **cierre de la vela que se había usado para decidir** y sin horquilla compra-venta; el laboratorio tenía su propio simulador (otra copia con las mismas hipótesis optimistas).
- **Cambio (un solo modelo):** la señal se calcula con el cierre de la vela *i*; la orden se ejecuta al **precio de apertura de la vela *i+1*** con `apertura × (1 ± (horquilla/2 + deslizamiento))` y comisión. `ejecucion.simular()` es el único simulador histórico (el laboratorio y la comparación delegan en él; "comprar y mantener" entra en la primera vela en que la estrategia también podría). En vivo: las decisiones generan **órdenes pendientes** (`pendientes` en el estado) que se ejecutan en cuanto existe la vela siguiente (normalmente en la misma pasada, porque su apertura ya es un hecho; si no, en la siguiente); se **revalidan al ejecutar** (efectivo, máximo de posiciones, duplicados, agente apagado, datos anómalos) y las no ejecutadas se anotan en `RECHAZOS` (se persistirán en la mejora 18); caducan tras 6 h sin precio. El apagado por riesgo sigue siendo inmediato al último precio (salida de emergencia, con los mismos costes).
- **Horquilla:** `SPREAD = 0,08 %` total (0,04 % por lado) en monedas líquidas — **supuesto de diseño, no medido**; se sustituirá por una estimación por liquidez en la mejora 12. El estado guarda `spread` para que cada simulación sea reproducible.
- **Versión:** `VERSION = 4`. Al fusionar esta rama, la simulación en vivo detectará el cambio de reglas, **archivará con manifiesto** la actual (v3) y empezará de cero con 10 € por agente (mismo mecanismo ya usado antes). Los datos antiguos no se pierden.
- **Pruebas (92 en total, +13):** ejecución en la apertura siguiente (con apertura distinta del cierre), decisión de la última vela no ejecutada, costes de ida y vuelta, stop decidido al cierre y vendido en la apertura siguiente, "mantener" coherente, apagado, sin mirar el futuro; en vivo: pendiente → ejecución posterior, ejecución en la misma pasada, rechazo por efectivo, caducidad, sin duplicados ni exceso de posiciones; 149 horas consecutivas sintéticas (642 operaciones) con contabilidad conservada (efectivo = capital + flujos) y repetición idempotente.
- **Limitación honesta:** en un mercado 24/7 la apertura de la vela *i+1* casi coincide con el cierre de *i*, por lo que este cambio **no** introduce un castigo grande por sí mismo; lo que aporta es que ya no se opera al mismo precio con el que se decide y que se paga la horquilla. El retraso real entre decisión y orden (la ejecución horaria corre ~17 min después de abrir la vela) **no se modela**; en la mejora 12 se añadirá un análisis de sensibilidad (costes ×2) para ver cuánto aguanta cada estrategia.

## Mejora 10 — CRYPTO-006 Mínimos y precisión del exchange
- **Archivos:** `reglas_mercado.py` (nuevo), `agentes_nube.py`, `tests/test_reglas_mercado.py`, `tests/base.py`.
- **Cambio:** las reglas (`ordermin`, `costmin`, `lot_decimals`, `pair_decimals`) se leen de `AssetPairs` de Kraken (la misma llamada que ya se hacía para el universo) y se guardan en `datos/reglas_mercado.json`. Cada orden pasa por `preparar_orden`: la cantidad se **redondea hacia abajo** a los decimales permitidos (lo no gastado vuelve al efectivo), y si queda por debajo del volumen mínimo o del coste mínimo **se rechaza** (se anota en `RECHAZOS`, no gasta dinero). El agente **no pide** compras que sabe que no cumplirán los mínimos. Las ventas también se comprueban. Si una moneda no trae reglas (o falla la lectura) se usa un **supuesto genérico marcado `supuesto`** (0,5 € de coste mínimo) y el `resumen.md` avisa de que ese mínimo no está verificado.
- **Hallazgo importante (a verificar en la primera ejecución real):** con trozos de **2 €** (`SLOT = 10 € / 5`), monedas caras como BTC (volumen mínimo típico del orden de 0,00005 BTC ≈ 3–4 € a precios actuales) probablemente **no cumplan el mínimo** y dejen de operarse. No lo he podido comprobar porque Kraken no es accesible desde este entorno; los valores de los tests son ilustrativos. Si se confirma, las opciones son: subir el capital por agente, reducir `MAX_POS` (trozos más grandes) o aceptar que solo se operan monedas baratas. **Es una decisión tuya** (no la tomo yo).
- **Pruebas (+8):** lectura de reglas, campos ausentes → supuesto marcado, redondeo hacia abajo, comprobación de mínimos, rechazo sin gastar dinero, redondeo de cantidad con devolución del sobrante, supuesto genérico, el agente no intenta lo inejecutable. Total 100 correctas; 149 horas sintéticas siguen con contabilidad conservada.

## Mejora 11 — CRYPTO-001 Posiciones fuera del universo
- **Archivos:** `agentes_nube.py`, `tests/test_fuera_universo.py`.
- **Problema:** el universo son las 20 monedas de mayor volumen *de cada ejecución*. Una moneda comprada que salía del ranking dejaba de descargarse: nunca se volvía a actualizar su precio, ninguna señal podía venderla (posición "zombi") y, si faltaba su precio, `equity` la valoraba a **0 €**.
- **Cambio:** (1) el universo descargado es **ranking ∪ monedas en cartera** (incluidas ventas pendientes), leídas del estado antes de descargar; (2) si de una moneda en cartera siguen sin llegar velas, la posición queda marcada **`sin_cotizacion`**, **no se cierra** ni se inventa un precio, se valora **de forma conservadora** (nunca por encima de su precio de entrada y nunca a 0), se registra una incidencia de alerta (una fila por día) y el `resumen.md` la muestra con aviso; al volver la cotización la marca se quita y se valora a mercado; (3) el apagado por riesgo no intenta vender lo que no cotiza; (4) las órdenes pendientes de una moneda sin velas caducan a las 6 h.
- **Pruebas (+9, 109 en total):** el ranking sigue siendo top-N; una moneda fuera del ranking se vigila con su volumen real; extra inexistente no rompe; detección de monedas en cartera; posición sin datos (no se cierra, valoración conservadora, alerta); sin último precio → a coste, no a 0; recuperación; incidencia; caducidad.
- **Pendiente/decisión:** qué hacer con una moneda deslistada de verdad (venderla a mano, darla por perdida tras N días) queda como **decisión humana**: el sistema solo avisa. No se ha tocado `director.py` para que alerte de esto (se cubre en la mejora 18).

## Mejora 12 — CRYPTO-007 Modelo de costes compartido
- **Archivos:** `costes.py` (nuevo), `ejecucion.py`, `agentes_nube.py`, `laboratorio.py`, `tests/test_costes.py`, `tests/test_ejecucion.py`, `tests/test_simulacion.py`.
- **Problema:** los costes estaban repartidos en constantes sueltas (`FEE`, `SLIP`, `SLIP_POCO_VOLUMEN`) copiadas entre simulación, laboratorio y comparación, sin horquilla variable ni escenario duro.
- **Cambio:** un único objeto `Costes(fee, slip, spread)` validado (rechaza negativos, NaN, valores absurdos) con `precio_compra/venta` y `coste_ida_y_vuelta`. Escenario **BASE** (lo acordado: comisión 0,40 %, deslizamiento 0,05 %, horquilla 0,08 % en monedas líquidas) y **ESTRÉS** (comisión *taker* 0,80 %, horquilla y deslizamiento ×2). Horquilla y deslizamiento **variables por liquidez** (volumen 24 h): alta ≥ 1 M €, media ≥ 100 k €, baja < 100 k € o desconocido (horquilla ×1 / ×2,5 / ×6,25; deslizamiento ×1 / ×2 / ×6); BTC siempre líquido. La simulación en vivo usa `costes_par()` en cada orden y el estado guarda los parámetros base; el laboratorio repite el examen de las 12 variantes elegidas con el escenario de estrés y lo muestra en una columna nueva («Dif. examen con costes duros»), así se ve qué variantes solo ganan con costes optimistas.
- **Honestidad sobre los supuestos:** la horquilla y el deslizamiento **no están medidos** (no hay libro de órdenes en las velas); son hipótesis prudentes. La comisión del 0,40 % es la de órdenes *maker*; como la simulación entra "a mercado" a la apertura siguiente, la real sería *taker* (0,80 %) → por eso existe el escenario de estrés. La base se deja en 0,40 % porque es lo que acordaste; **te recomiendo mirar siempre la columna de costes duros**.
- **Pruebas (+12, 121 en total):** valores base/estrés, escalado por liquidez, volumen desconocido, BTC, umbrales, precios de ejecución, coste de ida y vuelta = fórmula exacta, validación de parámetros; los costes duros nunca mejoran el resultado (6 series sin apagado por riesgo, mismas operaciones; con apagado las rutas pueden divergir y no se comparan); `costes` suelto y objeto equivalentes. Laboratorio demo completo con la columna nueva.

## Mejora 13 — CRYPTO-012 Precisión decimal
- **Archivos:** `agentes_nube.py`, `informe.py`, `index.html`, `tests/test_simulacion.py`, `tests/test_informe_lab.py`.
- **Problema:** `importe_eur` se guardaba redondeado a **2 decimales** y las operaciones ganadoras/perdedoras se clasificaban comparando esos importes: con trozos de 2 €, un redondeo de 0,01 € es el 0,5 % del importe, del tamaño de los costes. Además, una igualdad (empate) contaba como **perdedora**.
- **Cambio:** importe y coste se guardan con **8 decimales** y el precio con 10 cifras significativas; el historial con 6 decimales (antes 2). `informe.metricas` compara con **`Decimal` exacto** leído del texto del CSV (sin error de coma flotante) y devuelve `Metrica(caida, ganadoras, perdedoras, neutras)`; igualdad exacta = **neutra** (cerrada, ni ganadora ni perdedora). Importes ilegibles se ignoran sin romper. El panel (`index.html`) aplica la misma regla (ganadora / perdedora / neutra). Los CSV antiguos con 2 decimales siguen leyéndose (sus empates aparentes ahora salen neutros en vez de perdedores).
- **Pruebas (+7):** importe y coste con >2 decimales; una ganancia diminuta se clasifica como ganadora y coincide con la contabilidad; historial con 6 decimales; diferencia de 0,003 € bien clasificada; igualdad exacta neutra; importe ilegible; `0,1 + 0,2 = 0,3` con Decimal. Sintaxis JS del panel validada con `node --check`.
- **Límite:** el estado interno sigue en coma flotante de 64 bits (error ~1e-16, irrelevante a este tamaño); lo que se corrige es el redondeo *visible* y la clasificación.

## Mejora 14 — CRYPTO-010 Sin historial inventado para agentes nuevos
- **Archivos:** `agentes_nube.py`, `informe.py`, `index.html`, `tests/test_simulacion.py`, `tests/test_informe_lab.py`.
- **Problema:** al añadir un agente, `ajustar_historial` rellenaba sus columnas en las filas anteriores con el capital inicial: una **línea plana de 10 € inventada** durante semanas en las que el agente no existía (con efecto en gráficos, caída máxima y comparaciones).
- **Cambio:** las columnas del agente nuevo quedan **vacías** en las filas anteriores. `informe.grafico_svg` dibuja solo los puntos reales (sin romper si una serie tiene huecos), `informe.metricas` ya ignoraba vacíos, el director ya trataba los vacíos como "sin dato", y el panel ya filtraba valores no numéricos (`isFinite`). Corregido de paso un texto fijo del gráfico del panel ("50 € (capital inicial)") que ahora usa el capital real del estado.
- **Pruebas:** historial con columna nueva vacía (no `START`); gráfico y métricas con columnas vacías sin NaN. Total 129 correctas.
- **Pendiente:** verificar visualmente el panel con una columna vacía (se hará en la etapa 6 junto a la seguridad del panel).

## Mejora 15 — CRYPTO-004 Sesgo de supervivencia
- **Archivos:** `universo_historico.py` (nuevo), `ejecucion.py`, `estrategias.py`, `laboratorio.py`, `tests/test_universo_historico.py`, `tests/test_informe_lab.py`.
- **Problema:** el laboratorio probaba una lista fija de 12 monedas **que existen hoy**: las que murieron o cayeron no están, así que el historial es más amable que la realidad.
- **Cambio:** universo "punto en el tiempo": cada moneda solo se puede **comprar** mientras estaba entre las **10 de mayor volumen** (de las 16 candidatas; suma de los últimos 30 días con datos solo hasta esa vela, sin mirar el futuro; una moneda sin 30 días de historia aún no cuenta; las ventas siempre se permiten). El simulador acepta `permitido(i)`. Cada variante se evalúa **dos veces** (punto en el tiempo y lista fija) y el informe publica la diferencia media y cuántas variantes aprueban en cada caso (sección «Sesgo de supervivencia» de `laboratorio.md`, y `sesgo_supervivencia` en el JSON). Se amplía la lista de 12 a 16 monedas (BCH, XLM, UNI, NEAR).
- **Pruebas (+11, 140 en total):** top-N por volumen, ranking cambiante, sin mirar el futuro, monedas sin historia suficiente, alineación por marca temporal con inicios distintos, volumen inválido, N mayor que el número de monedas, simulador con membresía (no compra fuera, sí vende), integración en el laboratorio demo (membresía alineada y variable; reduce operaciones).
- **Límite que no se puede arreglar con datos gratuitos:** Kraken no ofrece historial de monedas deslistadas; **las que murieron no pueden incluirse**. El informe lo dice explícitamente y pide tomar los resultados favorables como optimistas.
