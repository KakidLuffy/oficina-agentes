# Informe final de implementación — 20 mejoras de la auditoría

Fecha: 2026-10-22 · Rama: `mejoras-crypto` (21 commits propios sobre `main` f383ff8; **no subida a GitHub y sin fusionar**) · Todo es **simulación con dinero ficticio**.

## A. Resumen ejecutivo

**Estado global: PARCIAL.** Las 20 mejoras están revisadas y las aplicables están implementadas y probadas con datos sintéticos, en un navegador real (panel) y con una batería de **228 pruebas automáticas (228 correctas, 0 fallidas, 0 omitidas)**, incluidos los 20 escenarios de validación global. Se declara PARCIAL, y no completado, porque hay validaciones que **solo se pueden hacer fuera de este entorno** y todavía no se han hecho:

1. Nunca se ha ejecutado contra **datos reales de Kraken** (la API no es accesible desde aquí): validación de velas, mínimos del exchange y costes se probaron con datos sintéticos.
2. Los **workflows de GitHub Actions** (reintentos, alertas por Issues, publicación) solo se pueden probar dentro de GitHub; aquí se probaron sus scripts con un `gh` simulado y se validó la sintaxis YAML.
3. El **adaptador de exchange de solo lectura** está diseñado, no implementado (no hay necesidad concreta ni autorización del usuario: es lo que pide el enunciado).

Lo que cambia para el usuario: la simulación pasa a la **versión 4** (decisión con el cierre de la vela, ejecución a la apertura de la siguiente, costes más prudentes, mínimos del exchange, datos validados). **Al fusionar a `main`, la primera ejecución archiva la simulación v3 con manifiesto y huellas y empieza de nuevo con 10 € por agente.** Ningún cambio se ha desplegado.

No se ha demostrado que ninguna estrategia gane dinero; el laboratorio en datos sintéticos dice «NINGUNA», que es lo esperable en datos aleatorios.

## B. Mejoras implementadas

| ID | Descripción | Estado | Archivos principales | Pruebas | Resultado |
|---|---|---|---|---|---|
| CRYPTO-015 | Batería de pruebas automáticas | VALIDADA | `tests/` | 228 en total | Todas correctas; se ejecutan antes de cada paso de la simulación |
| CRYPTO-018 | Persistencia atómica (todo o nada) | VALIDADA | `persistencia.py` | `test_persistencia`, esc. 12 | Cortes simulados en 11 puntos de escritura: siempre queda o todo lo antiguo o todo lo nuevo |
| CRYPTO-011 | Archivo verificable con manifiesto y SHA-256 | VALIDADA | `archivado.py` | `test_archivado` | Copia, verifica y solo entonces borra; nunca colisiona |
| CRYPTO-017 | Robustez de GitHub Actions | IMPLEMENTADA | 5 workflows, `scripts/`, `verificar_salida.py` | `test_workflows`, esc. 19 | Acciones fijadas por SHA, permisos mínimos, reintentos sin `--force`; **falta ver una ejecución real** |
| CRYPTO-008 | Validación de velas | VALIDADA* | `velas.py` | `test_velas`, esc. 4 | Descarta NaN, ≤0, OHLC incoherente, duplicadas, mal alineadas; salto >40 % bloquea compras. *Sin datos reales de Kraken |
| CRYPTO-009 | Alineación de marcas temporales | VALIDADA | `laboratorio.py`, `estrategias.py` | `test_informe_lab`, esc. 15 | Series emparejadas por marca de tiempo, no por posición |
| CRYPTO-005 | Columnas `vela_inicio_utc` / `decision_utc` | VALIDADA | `agentes_nube.py`, `verificar_salida.py` | `test_simulacion`, esc. 5–6 | Migración atómica que solo deriva valores ciertos |
| CRYPTO-013 | Estrategias unificadas | VALIDADA | `estrategias.py` | `test_estrategias` | Equivalencia exacta con las estrategias antiguas y sin mirar el futuro |
| CRYPTO-002 | Ejecución en la apertura de la vela siguiente | VALIDADA* | `ejecucion.py`, `agentes_nube.py` | `test_ejecucion`, `test_e2e_horas`, esc. 5–6 | Contabilidad conservada en 149 h sintéticas. *Sin Kraken real |
| CRYPTO-006 | Mínimos y decimales del exchange | IMPLEMENTADA | `reglas_mercado.py` | `test_reglas_mercado`, esc. 3 | Valores reales sin verificar desde aquí (fuente «supuesto» marcada) |
| CRYPTO-001 | Posiciones fuera del universo | VALIDADA | `agentes_nube.py` | `test_fuera_universo`, esc. 7–8 | No se cierran ni se inventa ganancia; valoración conservadora y alerta |
| CRYPTO-007 | Modelo de costes compartido | VALIDADA* | `costes.py` | `test_costes`, esc. 10–11 | *Horquilla y deslizamiento son supuestos de diseño, no medidos |
| CRYPTO-012 | Precisión decimal | VALIDADA | `agentes_nube.py`, `informe.py`, `index.html` | `test_simulacion`, `test_informe_lab` | Empates exactos como «neutras» |
| CRYPTO-010 | Sin historial inventado | VALIDADA | `agentes_nube.py`, `informe.py`, `index.html` | `test_simulacion`, `test_panel_navegador` | Columnas nuevas vacías; el panel no muestra «NaN» |
| CRYPTO-004 | Sesgo de supervivencia | IMPLEMENTADA | `universo_historico.py`, `laboratorio.py` | `test_universo_historico` | Reduce, **no elimina** (Kraken no da monedas deslistadas) |
| CRYPTO-003 | Walk-forward y regímenes | VALIDADA | `walkforward.py`, `laboratorio.py` | `test_walkforward`, esc. 16–18 | Pliegues sin solape; un pliegue no cambia si desaparece el futuro |
| CRYPTO-014 | Métricas avanzadas | VALIDADA | `metricas.py` | `test_metricas` | IC por bootstrap de bloques reproducible; «NO ESTIMABLE» si la muestra no alcanza |
| CRYPTO-016 | Decisiones rechazadas y alertas | VALIDADA* | `agentes_nube.py`, `scripts/alerta_fallo.sh` | `test_rechazos_alertas`, esc. 3, 19 | *El envío real del Issue solo se prueba en GitHub |
| CRYPTO-019 | Seguridad del panel | VALIDADA | `index.html` | `test_panel_navegador` (Chromium) | Datos vacíos y maliciosos no ejecutan nada (comprobado también por mutación) |
| CRYPTO-020 | Analista de IA que solo propone | IMPLEMENTADA | `analista.py`, `exchange_lectura.py` | `test_analista`, esc. 20 | Técnicamente incapaz de operar (ver sección I) |
| CRYPTO-020b | Adaptador de exchange de solo lectura | NO APLICABLE por ahora | `ADAPTADOR_EXCHANGE_SOLO_LECTURA.md` | `test_analista` | Solo diseño y guardas; no hay necesidad ni autorización |

Detalle por mejora (cambio, pruebas, riesgos): `IMPLEMENTACION_MEJORAS_CRYPTO.md`.

## C. Mejoras incompletas

| Qué falta | Por qué | Dependencia |
|---|---|---|
| Probar velas, mínimos y costes con **Kraken real** | La API no es accesible desde el entorno de trabajo | Ejecutar `python agentes_nube.py` o el workflow en GitHub y **revisar la primera ejecución** (resumen y `reglas_mercado.json`) |
| Ver los workflows funcionando (reintentos, alertas, publicación) | Solo se ejecutan dentro de GitHub; la rama no está subida | Autorización del usuario para subir la rama y lanzar una ejecución manual |
| Tipografías propias en el panel | No se pudieron descargar los ficheros (sin acceso al registro de paquetes) | Guardar `.woff2` de licencia libre en el repositorio; mientras, se usan las del dispositivo |
| Adaptador de exchange de solo lectura | El enunciado exige necesidad concreta y autorización | Decisión del usuario |
| Sesgo de supervivencia total | Kraken no publica el historial de monedas deslistadas | Otra fuente de datos (probablemente de pago): fuera de la regla «solo gratis» |
| Archivos antiguos sin manifiesto (`datos/archivo_50eur_…`, `archivo_10eur_v1_…`) | Son anteriores a la mejora y no se han modificado | Opcional: generar manifiestos retroactivos |

## D. Errores corregidos

| Error | Solución | Evidencia |
|---|---|---|
| Las órdenes se ejecutaban al precio del cierre con el que se decidía (ventaja imposible en la realidad) | Decisión con el cierre, ejecución a la apertura de la vela siguiente con horquilla y deslizamiento (mejora 9) | `test_ejecucion`, esc. 5–6 (precio ≥ 120 con cierre 100) |
| Una moneda sin precio se valoraba a 0 € (o con ganancia inventada) | Marca «sin cotización», valoración `min(último precio, entrada)`, alerta diaria (mejora 11) | `test_fuera_universo`, esc. 7–8 |
| Las posiciones de monedas que salían del ranking dejaban de vigilarse | El universo incluye las monedas en cartera | `test_fuera_universo` |
| Órdenes por debajo de los mínimos del exchange se «ejecutaban» | Redondeo y mínimos por moneda; se rechazan y se anotan (mejora 10) | `test_reglas_mercado`, esc. 3 |
| Los rechazos solo se imprimían y se perdían | Registro persistente y deduplicado en la misma transacción (mejora 18) | `test_rechazos_alertas` |
| **Las compras que no cumplían mínimos se descartaban sin anotarse** (hallado en la validación global) | Ahora se anotan en `RECHAZOS` antes de descartar | esc. 3 (parte «flujo real»): la prueba falló antes de la corrección y pasa después |
| Historial de agentes nuevos rellenado con el capital inicial (línea plana inventada) | Columnas vacías; gráfico tolerante (mejora 14) | `test_simulacion`, `test_panel_navegador` |
| Empates de importes contados como ganancia o pérdida por coma flotante | Aritmética `Decimal`; las igualdades son «neutras» (mejora 13) | `test_informe_lab` |
| Escritura no atómica: un corte dejaba estado, historial y operaciones desincronizados | Transacción con diario y recuperación al arrancar (mejora 2) | esc. 12: cortes en 11 puntos, siempre todo-o-nada |
| Series del laboratorio emparejadas por posición, no por marca temporal | Alineación por timestamp (mejora 6) | esc. 15 |
| Panel: texto sin escapar en 3 sitios, `?base=` manipulable, CSV con comas descuadrado, excepciones con archivos vacíos, Google Fonts | Ver mejora 19 | `test_panel_navegador` (incluye mutación: con `esc` anulado, la prueba falla) |
| `__pycache__` subido al repositorio | `.gitignore` y borrado del índice | commit 829fd9c |
| Prueba de costes duros no determinista (apagado por riesgo según la trayectoria) | Series y parámetros fijos | commits 37cddf3, 2ae7164 |
| Escenario 10 inicial fallaba por apagado por riesgo (resultado dependiente de la trayectoria) | **Se corrigió la prueba, no el código**: con volatilidad moderada el efecto del coste es monótono. Anotado aquí por transparencia | `tests/test_validacion_global.py` |

## E. Arquitectura final

```
                         GitHub Actions (cada hora)
                                   │
   Kraken (público) ──► agentes_nube.py ──► velas.py (valida) ──► estrategias.py (señal al cierre i)
                              │                                          │
                              │            ejecucion.py + costes.py + reglas_mercado.py
                              │            (orden pendiente → apertura de i+1, mínimos, costes)
                              ▼
                   persistencia.py (transacción atómica)
          estado.json · historial_v2.csv · operaciones.csv · decisiones_rechazadas.csv
          incidencias_datos.csv · reglas_mercado.json · resumen.md (informe.py + metricas.py)
                              │
                 verificar_salida.py ──(falla)──► NO se publica ──► alerta_fallo.sh (Issue único)
                              │
                       guardar_datos.sh (reintentos, sin --force)
                              ▼
   datos/ en el repositorio ──► index.html (CSP, escapado, sin terceros) / director.py (lee y resume)

   Laboratorio (lunes, manual):  los MISMOS estrategias.py + ejecucion.py + costes.py
        universo_historico.py (top-N a la fecha) · walkforward.py (pliegues, regímenes) · metricas.py
        → laboratorio.json / .md → director.py → propuestas.md

   Analista (solo manual):  Lector de lista cerrada ──► analista.py ──► propuestas_analista.json/.md
        (sin importar nada que opere; solo añade propuestas «pendientes de revisión»)
   exchange_lectura.py: contrato sin métodos de órdenes (no conectado a nada)
```

Separación clave: **la simulación y el laboratorio comparten código** (una sola definición de estrategias, simulador y costes), de modo que sus resultados son comparables.

## F. Pruebas

| Concepto | Resultado |
|---|---|
| Pruebas ejecutadas | **228** |
| Aprobadas | 228 |
| Fallidas | 0 |
| Omitidas | 0 (las 7 de navegador se ejecutan porque hay Chromium; se omitirían sin él) |
| Duración | ≈ 58 s |
| Comando | `python3 -m unittest discover -s tests -t .` |

Por área: estrategias y equivalencia (11), ejecución (9), costes (10), reglas del exchange (4), simulación (8+), fuera de universo (7), e2e de horas (2), persistencia (5), archivado, workflows, velas (12), universo histórico (9), walk-forward (11), métricas (13), laboratorio e informe (15), rechazos y alertas (11), analista y exchange (19), panel en Chromium (7) y **validación global (21: un escenario por caso)**.

**Los 20 escenarios de la validación global** (`tests/test_validacion_global.py`, nombres `esc01`…`esc20`): 1 agente recién creado · 2 primera operación · 3 rechazo por mínimos · 4 rechazo por datos inválidos · 5 señal al cierre · 6 ejecución en la vela posterior · 7 posición fuera del universo · 8 posición sin cotización · 9 caída del mercado · 10 aumento de spread · 11 comisión elevada · 12 interrupción de escritura · 13 recuperación tras reinicio · 14 historial vacío · 15 marcas de tiempo distintas · 16 fuera de muestra · 17 mercado bajista · 18 mercado lateral · 19 error de Actions · 20 propuesta de IA sin autorización. **Todos correctos.**

Límite de las pruebas: son sintéticas. No sustituyen a una validación con datos reales de Kraken ni a una ejecución en GitHub.

## G. Rendimiento

| Medida | `main` (antes) | `mejoras-crypto` (después) |
|---|---|---|
| Un paso de la simulación (`--demo 220`) | ≈ 0,06–0,10 s | ≈ 0,08–0,10 s |
| Laboratorio completo en demo | ≈ 1,1 s | ≈ 14–29 s (varía con la carga de la máquina) |
| Batería de pruebas | 28 pruebas | 228 pruebas, ≈ 58 s |

El laboratorio es más lento porque ahora hace walk-forward (varios pliegues), evalúa cada variante dos veces (universo punto en el tiempo y lista fija), usa 16 monedas y calcula intervalos bootstrap. Con datos reales el tiempo lo domina la descarga (pausas de 1,2 s por serie); el workflow semanal tiene un límite de 20 min. Son mediciones de un solo equipo y sin repetir suficientes veces para un benchmark formal.

## H. Riesgos residuales

1. **Mínimos del exchange frente a 2 € por posición:** es probable que algunas monedas (BTC incluido) no sean operables con ese tamaño y que muchas señales queden rechazadas. Sin verificar con Kraken real. Es una **decisión del usuario** (más capital por agente o menos posiciones); no se cambió por mi cuenta.
2. **Costes supuestos:** horquilla y deslizamiento por nivel de liquidez son hipótesis de diseño, no medidas.
3. **Primera ejecución real sin ver:** puede revelar diferencias de formato en los datos de Kraken.
4. **Workflows sin probar en GitHub** (incluida la alerta por Issues; si GitHub Actions no arranca, no hay alerta).
5. **Sesgo de supervivencia** reducido, no eliminado; las monedas muertas no se pueden incluir.
6. **Poca muestra:** con pocas semanas, Sharpe/Sortino y los resultados por régimen son muy inestables; el propio informe lo marca («NO ESTIMABLE», IC).
7. **Panel:** el CSP en `<meta>` no impide que otro sitio incruste el panel en un `iframe` (GitHub Pages no permite cabeceras HTTP propias). Tipografías sin ficheros propios.
8. **Fusionar a `main` cambia los formatos de datos** y archiva la simulación v3; no es reversible salvo recuperando el archivo.
9. **El repositorio es público:** nada sensible en él (no hay claves); conviene revocar el acceso de la aplicación de GitHub concedido para esta sesión.

## I. Seguridad

Mecanismos de separación entre simulación y operaciones reales, con la evidencia que los respalda:

| Mecanismo | Evidencia |
|---|---|
| No existe código que opere en un exchange: ningún acceso a rutas privadas, órdenes, retiradas ni claves en los `.py`; ningún `secrets.` en los workflows | `test_no_existen_ejecuciones_financieras_reales` (barrido de todo el código) |
| La simulación solo usa datos **públicos** de mercado y escribe solo en `datos/` | Lectura del código; `exchange_lectura.comprobar_ruta_publica` rechaza rutas no públicas |
| El analista de IA **no puede** operar: no importa simulador, ejecución, estrategias, persistencia ni módulos de red; lee una lista cerrada de 7 archivos; solo una función escribe y solo 2 archivos propios; solo añade propuestas y no pisa su estado; los estados posibles no incluyen «aplicada» | `tests/test_analista.py` (análisis AST de importaciones y escrituras), esc. 20 |
| Una propuesta de IA no activa nada: el validador rechaza esquemas con campos de acción, estados no permitidos y frases que ordenan activar, mover fondos o tocar límites | esc. 20 |
| El simulador, el director y el laboratorio no importan al analista ni al adaptador | `test_ningun_modulo_del_sistema_importa_el_adaptador`, `test_no_hay_modulo_que_importe_al_analista…` |
| Un adaptador futuro solo admitiría credenciales de «consulta» | `exchange_lectura.comprobar_permisos` (probado) |
| Permisos mínimos en Actions: `contents: read` por defecto, `issues: write` solo en el trabajo de alerta, acciones fijadas por SHA, nunca `--force` | `test_workflows`, `test_rechazos_alertas` |
| Datos corruptos no se publican | esc. 19 (`verificar_salida.py` sale con código 1) |
| Panel resistente a datos manipulados | `test_panel_navegador` |
| Reglas del usuario respetadas: solo dinero ficticio, sin claves en el repositorio, sin garantía de beneficios | Revisión del código y de los textos de los informes |

Limitación honesta: la separación se apoya en estos controles de código y pruebas; **no** en un aislamiento a nivel de sistema operativo.

## J. Recomendaciones (sin implementar)

1. Subir la rama a GitHub como *pull request* y lanzar manualmente una ejecución para revisar la primera pasada con datos reales **antes** de fusionar.
2. Decidir el capital por agente / número de posiciones a la vista de `reglas_mercado.json` y de las decisiones rechazadas.
3. Medir horquilla y deslizamiento reales con datos de libro de órdenes públicos para sustituir los supuestos.
4. Dejar la simulación correr ≥ 21 días y ≥ 30 operaciones cerradas por agente antes de sacar conclusiones.
5. Guardar tipografías `.woff2` libres en el repositorio.
6. Generar manifiestos retroactivos para los archivos antiguos.
7. Valorar un analista basado en un modelo de lenguaje solo si pasa por `validar_propuestas` y se mantiene sin acceso a escritura.
8. Revocar el acceso de la aplicación de GitHub concedido a esta sesión cuando termine la revisión.
