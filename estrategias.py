"""
Estrategias UNICAS (solo libreria estandar). La simulacion en vivo, el laboratorio y la comparacion historica usan
exactamente estas funciones: lo que se prueba en el laboratorio es lo que opera en la simulacion.

Convencion: cada estrategia es f(c, i, s) -> "b" (comprar) | "s" (vender) | None
  c: cierres (lista o Serie), i: indice de la ultima vela CERRADA que se puede mirar, s: escala de la duracion de vela
  (1 para velas de 1 hora; los umbrales de movimiento se multiplican por ella).
Una estrategia SOLO puede mirar c[0..i]: nunca c[i+1:] (comprobado por tests/test_estrategias_unicas.py).
"""
from math import sqrt


class Serie(list):
    """Lista de cierres con medias moviles precalculadas (cada media en i solo usa c[0..i])."""

    def __init__(self, v, ts=None, o=None, vol=None):
        super().__init__(v)
        self._sma = {}
        # aperturas de cada vela (para ejecutar al precio de apertura de la vela siguiente). Si no se dan, se aproxima
        # con el cierre anterior (en un mercado 24/7 la apertura casi coincide con el cierre previo).
        self.o = list(o) if o is not None else ([v[0]] + list(v[:-1]) if len(v) else [])
        self.ts = list(ts) if ts is not None else list(range(len(v)))   # marca temporal (s) de cada vela
        self.vol = list(vol) if vol is not None else [0.0] * len(v)     # volumen en EUR de cada vela (para el universo punto en el tiempo)
        self.ref = None          # serie de BTC con la misma duracion de vela (para la fuerza relativa)
        self.ref_idx = None      # para cada vela: indice de la vela de BTC con la MISMA marca temporal (o None)

    def sma(self, n):
        if n not in self._sma:
            acum, out, t = [0.0], [], 0.0
            for i, x in enumerate(self):
                t += x
                acum.append(t)
                k = max(0, i - n + 1)
                out.append((acum[i + 1] - acum[k]) / (i + 1 - k))
            self._sma[n] = out
        return self._sma[n]


def media(c, i, n):
    """Media de las n velas que terminan en i (con menos velas al principio de la serie)."""
    if hasattr(c, "sma"):
        return c.sma(n)[i]
    w = c[max(0, i - n + 1):i + 1]
    return sum(w) / len(w)


def alinear(serie, ref):
    """Para cada vela de 'serie', el indice de la vela de 'ref' con la misma marca temporal (None si no existe)."""
    pos = {t: k for k, t in enumerate(ref.ts)}
    return [pos.get(t) for t in serie.ts]


# ---------------- familias parametrizadas ----------------
def cruce(a, b, hueco=0.0):
    """Cruce de medias a/b. 'hueco' exige una senal de compra mas fuerte: la media rapida debe superar a la lenta en ese %."""
    def f(c, i, s):
        if i < b:
            return None
        ca, cb, pa, pb = media(c, i, a), media(c, i, b), media(c, i - 1, a), media(c, i - 1, b)
        if pa <= pb and ca > cb * (1 + hueco):
            return "b"
        if pa >= pb and ca < cb:
            return "s"
        return None
    return f


def momentum(n, t):
    def f(c, i, s):
        if i < n:
            return None
        r, u = c[i] / c[i - n] - 1, t * s
        return "b" if r > u else ("s" if r < -u else None)
    return f


def rebote(n, t):
    def f(c, i, s):
        if i < n:
            return None
        m = media(c, i, n)
        return "b" if c[i] < m * (1 - t * s) else ("s" if c[i] > m else None)
    return f


def ruptura(n, m):
    """Compra al superar el maximo de las ultimas n velas, vende al perder el minimo de las ultimas m."""
    def f(c, i, s):
        if i < n:
            return None
        if c[i] > max(c[i - n:i]):
            return "b"
        if c[i] < min(c[i - m:i]):
            return "s"
        return None
    return f


def con_filtro(fn, n=200):
    """Filtro de mercado: solo deja pasar las COMPRAS si el precio esta por encima de su media de n velas."""
    def f(c, i, s):
        senal = fn(c, i, s)
        if senal == "b" and (i < n or c[i] <= media(c, i, n)):
            return None
        return senal
    return f


def con_volatilidad(fn, k, n=14):
    """Solo deja pasar las COMPRAS si el mercado se mueve lo bastante: movimiento medio por vela >= k x 0,4 % (escalado a la vela)."""
    def f(c, i, s):
        senal = fn(c, i, s)
        if senal == "b":
            if i < n + 1:
                return None
            mov = sum(abs(c[j] / c[j - 1] - 1) for j in range(i - n + 1, i + 1)) / n
            if mov < k * 0.004 * s:
                return None
        return senal
    return f


def relativa(n, margen):
    """Fuerza relativa: compra si la moneda sube mas que BTC (margen) en n velas y sube de por si; vende si rinde menos que BTC.
    BTC se busca por MARCA TEMPORAL (no por posicion): dos series pueden empezar o acabar en momentos distintos."""
    def f(c, i, s):
        r = c.ref
        if r is None or c.ref_idx is None or i < n:
            return None
        ia, ib = c.ref_idx[i], c.ref_idx[i - n]
        if ia is None or ib is None:
            return None
        rc, rb = c[i] / c[i - n] - 1, r[ia] / r[ib] - 1
        if rc > rb + margen * s and rc > 0:
            return "b"
        if rc < rb:
            return "s"
        return None
    return f


def _votos(c, i):
    """Votos de tendencia a favor de estar comprado: cruce 10/30, cruce 5/20 y momentum de 12 velas."""
    return (media(c, i, 10) > media(c, i, 30)) + (media(c, i, 5) > media(c, i, 20)) + (c[i] > c[i - 12])


def consenso(c, i, s):
    """Consenso 2 de 3: compra cuando al menos 2 de las 3 reglas de tendencia coinciden; vende cuando dejan de coincidir."""
    if i < 31:
        return None
    ahora, antes = _votos(c, i) >= 2, _votos(c, i - 1) >= 2
    if ahora and not antes:
        return "b"
    if antes and not ahora:
        return "s"
    return None


# ---------------- los agentes de la simulacion en vivo ----------------
AGENTES_VIVOS = [
    ("Cruce 10/30", cruce(10, 30)),
    ("Cruce 5/20", cruce(5, 20)),
    ("Momentum", momentum(12, 0.012)),
    ("Rebote", rebote(20, 0.015)),
    ("Cruce 10/30 + filtro", con_filtro(cruce(10, 30))),
    ("Consenso 2 de 3", consenso),
    # agentes rapidos: senales de pocas horas, para que operen varias veces al dia
    ("Cruce 3/8 rapido", con_filtro(cruce(3, 8, 0.002), 48)),
    ("Momentum rapido", momentum(6, 0.010)),
    ("Rebote rapido", rebote(8, 0.012)),
]
# Reglas de salida y de entrada propias de los agentes rapidos (los 6 originales no llevan ninguna):
#   espera_h: horas sin volver a comprar una moneda tras venderla · stop / objetivo: venta automatica al perder / ganar ese %
#   solo_liquidas: no compra monedas de poco volumen (donde el deslizamiento real es mayor)
OPCIONES_VIVOS = {n: {"espera_h": 6, "stop": 0.015, "objetivo": 0.03, "solo_liquidas": True}
                  for n in ("Cruce 3/8 rapido", "Momentum rapido", "Rebote rapido")}


def escala(minutos):
    """Escala de umbrales para velas de otra duracion (1 para 1 hora)."""
    return sqrt(minutos / 60)
