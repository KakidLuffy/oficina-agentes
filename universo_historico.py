"""
Universo "punto en el tiempo" (solo libreria estandar) para reducir el SESGO DE SUPERVIVENCIA del laboratorio.

El laboratorio prueba monedas que existen HOY. Una lista fija elegida ahora favorece a las que sobrevivieron y subieron, y deja fuera las que cayeron o
desaparecieron. Para acercarse a lo que se habria podido operar de verdad, aqui cada moneda solo se considera operable en una vela concreta si
estaba entre las TOP-N de volumen (suma de los ultimos 'ventana' volumenes, usando solo datos hasta esa vela) del conjunto de monedas con datos.

LIMITES (se repiten en el informe): (1) Kraken no ofrece historial de monedas ya deslistadas, asi que las que murieron NO pueden incluirse;
el sesgo se reduce, no se elimina. (2) El conjunto es el de las monedas que estan disponibles hoy.
"""
import math


def _vol(x):
    return x if isinstance(x, (int, float)) and math.isfinite(x) and x > 0 else 0.0


def membresia(datos, n, ventana):
    """datos: {moneda: [(ts, volumen_eur)]} (cada lista ordenada por ts; las monedas pueden empezar en momentos distintos).
    Devuelve {moneda: [bool]} alineada con la lista de cada moneda: True si en ese ts la moneda estaba en el top-n por volumen
    acumulado de las ultimas 'ventana' velas. Una moneda con menos de 'ventana' velas de historia aun no es miembro."""
    acum = {}                                                  # moneda -> {ts: suma movil de volumen y numero de velas}
    for m, lista in datos.items():
        d, ventana_v = {}, []
        for k, (ts, v) in enumerate(lista):
            ventana_v.append(_vol(v))
            if len(ventana_v) > ventana:
                ventana_v.pop(0)
            if len(ventana_v) == ventana:
                d[ts] = sum(ventana_v)
        acum[m] = d
    todos_ts = sorted({ts for lista in datos.values() for ts, _ in lista})
    top = {}
    for ts in todos_ts:
        puntuaciones = sorted(((d[ts], m) for m, d in acum.items() if ts in d), key=lambda x: (-x[0], x[1]))
        top[ts] = {m for _, m in puntuaciones[:n]}
    return {m: [m in top[ts] for ts, _ in lista] for m, lista in datos.items()}
