# Prueba histórica de «Tendencia H1 (diaria)»

Generado: 2026-11-11T23:15+00:00 UTC · Datos: Coinbase (BTC-EUR, ETH-EUR, velas diarias) · Periodo: 2017-09-02 a 2026-11-10 · **H1 se apagó el 2017-12-30** (regla −15 %): la comparación termina ese día

Mismas reglas y costes que el agente en vivo. Criterios fijados de antemano en `CRITERIOS.md`. Dinero ficticio.

## Veredicto: **NO PASA**

1. ¿Rentabilidad total mayor que la cesta al 50 %? **NO** (+65.4 % frente a +72.4 %)
2. ¿Gana a la cesta al 50 % en al menos la mitad de los años completos? **NO** (0 de 0)
3. ¿Caída máxima menor que la de la cesta al 50 %? **NO** (-19.3 % frente a -17.6 %)
4. ¿Robusto (al menos 2 de las medias 50/150/200 también superan a la cesta al 50 %)? **NO**

## Resultado

| | Capital final (EUR) | Rentabilidad | Caída máxima |
|---|---:|---:|---:|
| H1 | 16.54 | +65.4 % | -19.3 % |
| Cesta 50 % | 17.24 | +72.4 % | -17.6 % |
| Cesta 100 % | 24.49 | +144.9 % | -34.0 % |
| Solo BTC 100 % | 28.29 | +182.9 % | -33.6 % |

H1: 20 operaciones, 10 cerradas, 2 ganadoras (20 %), 6 por stop, costes 0.25 EUR, con alguna posición abierta el 80 % de los días.

## Por año natural completo

| Año | H1 | Cesta 50 % | Cesta 100 % | Solo BTC |
|---|---:|---:|---:|---:|

## Robustez (solo informativo: no se elige otra media)

| Media | H1 | Cesta 50 % | ¿Supera? |
|---:|---:|---:|---|
| 50 días | +62.5 % | +72.4 % | NO (apagada el 2017-12-30) |
| 150 días | +60.8 % | +72.4 % | NO (apagada el 2017-12-30) |
| 200 días | -8.8 % | +81.4 % | NO (apagada el 2017-12-22) |

Solo informativo (no cuenta para el veredicto): sin la regla del −15 %, en todo el periodo H1 habría hecho +328.5 % (caída máx. -42.9 %) frente a +524.5 % (caída máx. -69.0 %) de la cesta al 50 %.

Limitaciones: el stop se comprueba con el mínimo diario (en vivo, con el precio de cada ronda); las compras y ventas se hacen al cierre del día; el pasado no garantiza el futuro, y las medias móviles en cripto llevan años estudiándose, así que la regla pudo elegirse sabiendo que funcionó.
