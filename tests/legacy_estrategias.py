"""Copia LITERAL de las estrategias de la simulacion antes de unificarlas (main f383ff8). Solo sirve de referencia en las pruebas de equivalencia."""
# ---------------- estrategias ----------------
def media(lista):
    return sum(lista) / len(lista)


def cruce(p, a, b, hueco=0.0):
    """Cruce de medias. 'hueco' exige una senal de compra mas fuerte: la media rapida debe superar a la lenta en ese %."""
    if len(p) < b + 1:
        return None
    ca, cb = media(p[-a:]), media(p[-b:])
    pa, pb = media(p[-a - 1:-1]), media(p[-b - 1:-1])
    if pa <= pb and ca > cb * (1 + hueco):
        return "b"
    if pa >= pb and ca < cb:
        return "s"
    return None


def momentum(p):
    if len(p) < 14:
        return None
    r = p[-1] / p[-13] - 1
    return "b" if r > 0.012 else ("s" if r < -0.012 else None)


def rebote(p):
    if len(p) < 21:
        return None
    m, x = media(p[-20:]), p[-1]
    return "b" if x < m * 0.985 else ("s" if x > m else None)


def filtro(decidir, n=200):
    """Filtro de mercado: solo deja pasar las COMPRAS si el precio esta por encima de su media de n velas."""
    def f(p):
        senal = decidir(p)
        if senal == "b" and (len(p) < n or p[-1] <= media(p[-n:])):
            return None
        return senal
    return f


def _votos(p):
    """Reglas de tendencia a favor de estar comprado: cruce 10/30, cruce 5/20 y momentum de 12 velas."""
    return (media(p[-10:]) > media(p[-30:])) + (media(p[-5:]) > media(p[-20:])) + (p[-1] > p[-13])


def consenso(p):
    """Consenso 2 de 3: compra cuando al menos 2 de las 3 reglas de tendencia coinciden; vende cuando dejan de coincidir."""
    if len(p) < 32:
        return None
    ahora, antes = _votos(p) >= 2, _votos(p[:-1]) >= 2
    if ahora and not antes:
        return "b"
    if antes and not ahora:
        return "s"
    return None


def momentum_rapido(p):
    """Momentum de corto plazo: mira las ultimas 6 horas y solo reacciona a movimientos del 1 %."""
    if len(p) < 8:
        return None
    r = p[-1] / p[-7] - 1
    return "b" if r > 0.010 else ("s" if r < -0.010 else None)


def rebote_rapido(p):
    """Rebote de corto plazo: compra si el precio cae un 1,2 % bajo su media de 8 velas; vende al volver a la media."""
    if len(p) < 9:
        return None
    m, x = media(p[-8:]), p[-1]
    return "b" if x < m * 0.988 else ("s" if x > m else None)


AGENTES = [
    ("Cruce 10/30", lambda p: cruce(p, 10, 30)),
    ("Cruce 5/20", lambda p: cruce(p, 5, 20)),
    ("Momentum", momentum),
    ("Rebote", rebote),
    ("Cruce 10/30 + filtro", filtro(lambda p: cruce(p, 10, 30))),
    ("Consenso 2 de 3", consenso),
    # agentes rapidos: senales de pocas horas, para que operen varias veces al dia
    ("Cruce 3/8 rapido", filtro(lambda p: cruce(p, 3, 8, 0.002), 48)),
    ("Momentum rapido", momentum_rapido),
    ("Rebote rapido", rebote_rapido),
]
DECIDIR = dict(AGENTES)
# Reglas de salida y de entrada propias de los agentes rapidos (los 6 originales no llevan ninguna: se mantienen tal cual):
#   espera_h: horas sin volver a comprar una moneda tras venderla · stop / objetivo: venta automatica al perder / ganar ese %
#   solo_liquidas: no compra monedas de poco volumen (donde el deslizamiento real es mayor)
OPCIONES = {n: {"espera_h": 6, "stop": 0.015, "objetivo": 0.03, "solo_liquidas": True}
            for n in ("Cruce 3/8 rapido", "Momentum rapido", "Rebote rapido")}


