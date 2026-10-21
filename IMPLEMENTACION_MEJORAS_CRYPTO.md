# Registro de implementación de las 20 mejoras

Rama de trabajo: `mejoras-crypto` (no se ha tocado `main`). Todo sigue siendo simulación con dinero ficticio; no existe código de operación real ni claves.

## Tabla de progreso

| # | ID | Mejora | Estado |
|---|---|---|---|
| 1 | CRYPTO-015 | Pruebas automáticas | EN CURSO |
| 2 | CRYPTO-018 | Persistencia atómica | PENDIENTE |
| 3 | CRYPTO-011 | Archivo completo con manifiesto | PENDIENTE |
| 4 | CRYPTO-017 | Robustez de GitHub Actions | PENDIENTE |
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
