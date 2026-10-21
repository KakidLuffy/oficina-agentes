# Registro de implementación de las 20 mejoras

Rama de trabajo: `mejoras-crypto` (no se ha tocado `main`). Todo sigue siendo simulación con dinero ficticio; no existe código de operación real ni claves.

## Tabla de progreso

| # | ID | Mejora | Estado |
|---|---|---|---|
| 1 | CRYPTO-015 | Pruebas automáticas | VALIDADA |
| 2 | CRYPTO-018 | Persistencia atómica | VALIDADA |
| 3 | CRYPTO-011 | Archivo completo con manifiesto | VALIDADA |
| 4 | CRYPTO-017 | Robustez de GitHub Actions | IMPLEMENTADA (falta ver una ejecución real en GitHub) |
| 5 | CRYPTO-008 | Validación de velas | PENDIENTE |
| 6 | CRYPTO-009 | Alineación de marcas temporales | PENDIENTE |
| 7 | CRYPTO-005 | Columnas vela_inicio / decision_utc | PENDIENTE |
| 8 | CRYPTO-013 | Módulo único de estrategias | PENDIENTE |
| 9 | CRYPTO-002 | Ejecución en la vela siguiente | PENDIENTE |
| 10 | CRYPTO-006 | Mínimos y precisión del exchange | PENDIENTE |
| 11 | CRYPTO-001 | Posiciones fuera del universo | PENDIENTE |
| 12 | CRYPTO-007 | Modelo de costes compartido | PENDIENTE |
| 13 | CRYPTO-012 | Precisión decimal | PENDIENTE |
| 14 | CRYPTO-010 | Sin historial inventado | PENDIENTE |
| 15 | CRYPTO-004 | Sesgo de supervivencia | PENDIENTE |
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
