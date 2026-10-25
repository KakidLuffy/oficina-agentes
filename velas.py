"""
Validacion de velas (solo libreria estandar).

Politica (documentada y comprobada por tests/test_velas.py):
  - Cada incidencia se registra (tipo, nivel, detalle) y se muestra; nunca se corrige "inventando" datos.
  - DESCARTAN la vela: valores no finitos (NaN/inf), precios <= 0, volumen negativo, OHLC incoherente
    (maximo < apertura/cierre/minimo o minimo > apertura/cierre), marca temporal no alineada con el intervalo.
  - DUPLICADAS: se conserva la ultima recibida. DESORDENADAS: se ordenan y se avisa.
  - HUECOS (faltan velas): jamas se rellenan. Las senales solo usan la COLA CONTIGUA posterior al ultimo hueco
    (las medias no deben mezclar horas que no son consecutivas). Una posicion abierta sigue valorandose con el ultimo cierre.
  - SALTO ANOMALO (cierre a cierre > SALTO_MAX): se conserva el dato pero se marca BLOQUEO: no se abren compras
    nuevas en ese par durante esta ejecucion (las ventas siguen permitidas).
  - VELA ABIERTA (ts + intervalo > ahora): no es error; quien decide solo actua sobre velas cerradas.
"""
import math
from collections import namedtuple

Vela = namedtuple("Vela", "ts o h l c v")
SALTO_MAX = 0.40          # 40 % entre dos cierres consecutivos se considera anomalo
TOL = 1e-9


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def desde_kraken(fila):
    """Fila OHLC de Kraken: [time, open, high, low, close, vwap, volume, count]."""
    try:
        ts = int(fila[0])
    except (TypeError, ValueError):
        ts = -1
    return Vela(ts, _num(fila[1]), _num(fila[2]), _num(fila[3]), _num(fila[4]), _num(fila[6]) if len(fila) > 6 else 0.0)


def _inc(tipo, ts, nivel="aviso", **extra):
    d = {"tipo": tipo, "ts": ts, "nivel": nivel}
    d.update(extra)
    return d


def validar(velas, intervalo, ahora_ts=None):
    """Devuelve (velas_utilizables, incidencias). Las utilizables estan ordenadas, sin duplicados y son contiguas hasta el final."""
    inc, buenas = [], []
    for x in velas:
        vals = (x.o, x.h, x.l, x.c, x.v)
        if x.ts < 0 or not all(math.isfinite(a) for a in vals):
            inc.append(_inc("no_finito", x.ts, "descartada"))
        elif min(x.o, x.h, x.l, x.c) <= 0:
            inc.append(_inc("precio_no_positivo", x.ts, "descartada"))
        elif x.v < 0:
            inc.append(_inc("volumen_negativo", x.ts, "descartada"))
        elif x.h < max(x.o, x.c, x.l) * (1 - TOL) or x.l > min(x.o, x.c, x.h) * (1 + TOL):
            inc.append(_inc("ohlc_incoherente", x.ts, "descartada"))
        elif x.ts % intervalo != 0:
            inc.append(_inc("no_alineada", x.ts, "descartada"))
        else:
            buenas.append(x)
    if any(b.ts < a.ts for a, b in zip(buenas, buenas[1:])):
        inc.append(_inc("desordenada", None))
    ultimas = {}
    for x in buenas:                                     # duplicadas: gana la ultima recibida
        if x.ts in ultimas:
            inc.append(_inc("duplicada", x.ts))
        ultimas[x.ts] = x
    orden = [ultimas[t] for t in sorted(ultimas)]
    inicio = 0
    for i in range(1, len(orden)):                        # huecos: se parte por el ultimo
        falta = (orden[i].ts - orden[i - 1].ts) // intervalo - 1
        if falta > 0:
            inc.append(_inc("hueco", orden[i - 1].ts, faltan=falta))
            inicio = i
    util = orden[inicio:]
    for a, b in zip(util, util[1:]):
        if abs(b.c / a.c - 1) > SALTO_MAX:
            inc.append(_inc("salto_anomalo", b.ts, "bloqueo", variacion=round(b.c / a.c - 1, 4)))
    return util, inc


def hay_bloqueo(incidencias):
    return any(i["nivel"] == "bloqueo" for i in incidencias)
