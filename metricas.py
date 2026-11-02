"""
Metricas de rendimiento y riesgo (solo libreria estandar). Funciones puras, sin leer ni escribir archivos.

Principio: con pocos datos una cifra es ruido. Si la muestra no llega al minimo, se devuelve NO_ESTIMABLE
(en vez de un numero enganoso) y los intervalos de confianza usan bootstrap por bloques con semilla fija (reproducible).
"""
import math
import random

NO_ESTIMABLE = "NO ESTIMABLE"
MIN_RETORNOS = 30        # periodos minimos para volatilidad / Sharpe / Sortino
MIN_OPERACIONES = 10     # operaciones cerradas minimas para factor de beneficio / expectativa / % acierto
SEMILLA = 12345
REMUESTREOS = 1000


def retornos(curva):
    """Retornos simples entre valores consecutivos de una curva de capital (se saltan tramos no positivos)."""
    out = []
    for a, b in zip(curva, curva[1:]):
        if a is not None and b is not None and a > 0:
            out.append(b / a - 1)
    return out


def _media(x):
    return sum(x) / len(x)


def _desv(x):
    m = _media(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def volatilidad(r, periodos_anio=None):
    """Desviacion tipica de los retornos (anualizada si se indica periodos_anio)."""
    if len(r) < MIN_RETORNOS:
        return NO_ESTIMABLE
    d = _desv(r)
    return d * math.sqrt(periodos_anio) if periodos_anio else d


def sharpe(r, periodos_anio=None):
    """Media / desviacion tipica (tasa libre de riesgo = 0). Sin volatilidad -> NO ESTIMABLE."""
    if len(r) < MIN_RETORNOS:
        return NO_ESTIMABLE
    d = _desv(r)
    if d == 0:
        return NO_ESTIMABLE
    v = _media(r) / d
    return v * math.sqrt(periodos_anio) if periodos_anio else v


def sortino(r, periodos_anio=None):
    """Media / desviacion de los retornos negativos (objetivo 0). Sin retornos negativos -> NO ESTIMABLE."""
    if len(r) < MIN_RETORNOS:
        return NO_ESTIMABLE
    neg = [min(v, 0.0) for v in r]
    d = math.sqrt(sum(v * v for v in neg) / len(r))
    if d == 0 or sum(1 for v in r if v < 0) < 2:
        return NO_ESTIMABLE
    v = _media(r) / d
    return v * math.sqrt(periodos_anio) if periodos_anio else v


def caida_maxima(curva):
    """Mayor caida desde un maximo anterior, en % (valor negativo o 0)."""
    pico, peor = None, 0.0
    for v in curva:
        if v is None:
            continue
        pico = v if pico is None else max(pico, v)
        if pico > 0:
            peor = min(peor, v / pico - 1)
    return peor * 100


def factor_beneficio(pnl):
    """Suma de ganancias / suma de perdidas (en valor absoluto). Sin perdidas -> NO ESTIMABLE."""
    if len(pnl) < MIN_OPERACIONES:
        return NO_ESTIMABLE
    g = sum(v for v in pnl if v > 0)
    p = -sum(v for v in pnl if v < 0)
    return g / p if p > 0 else NO_ESTIMABLE


def expectativa(pnl):
    """Ganancia media por operacion cerrada (en la unidad de pnl)."""
    return _media(pnl) if len(pnl) >= MIN_OPERACIONES else NO_ESTIMABLE


def porcentaje_acierto(pnl):
    """% de operaciones ganadoras sobre las cerradas (las neutras cuentan en el total)."""
    return 100 * sum(1 for v in pnl if v > 0) / len(pnl) if len(pnl) >= MIN_OPERACIONES else NO_ESTIMABLE


def _bloques(x, largo, rng):
    n = len(x)
    out = []
    while len(out) < n:
        i = rng.randrange(n)
        out.extend(x[(i + k) % n] for k in range(largo))
    return out[:n]


def intervalo_bootstrap(datos, estadistico, minimo, nivel=0.95, largo_bloque=None, remuestreos=REMUESTREOS, semilla=SEMILLA):
    """Intervalo de confianza por bootstrap de BLOQUES (conserva la dependencia entre periodos consecutivos).
    Devuelve (inferior, superior) o NO_ESTIMABLE si hay menos de 'minimo' datos o el estadistico no se puede calcular."""
    n = len(datos)
    if n < minimo:
        return NO_ESTIMABLE
    largo = largo_bloque or max(1, round(n ** (1 / 3)))
    rng = random.Random(semilla)
    vals = []
    for _ in range(remuestreos):
        v = estadistico(_bloques(list(datos), largo, rng))
        if isinstance(v, (int, float)) and math.isfinite(v):
            vals.append(v)
    if len(vals) < remuestreos * 0.8:
        return NO_ESTIMABLE
    vals.sort()
    a = (1 - nivel) / 2
    return vals[int(a * (len(vals) - 1))], vals[int((1 - a) * (len(vals) - 1))]


def ic_retorno_medio(r):
    """IC 95 % del retorno medio por periodo. Si el intervalo incluye 0, no se distingue de la casualidad."""
    return intervalo_bootstrap(r, _media, MIN_RETORNOS)


def ic_expectativa(pnl):
    return intervalo_bootstrap(pnl, _media, MIN_OPERACIONES)


def resumen(curva, pnl, periodos_anio=None):
    """Todas las metricas de un agente (curva de capital y lista de ganancias por operacion cerrada)."""
    r = retornos(curva)
    return {"periodos": len(r), "operaciones": len(pnl), "caida_max_pct": caida_maxima(curva),
            "volatilidad": volatilidad(r, periodos_anio), "sharpe": sharpe(r, periodos_anio), "sortino": sortino(r, periodos_anio),
            "factor_beneficio": factor_beneficio(pnl), "expectativa": expectativa(pnl), "acierto_pct": porcentaje_acierto(pnl),
            "ic_retorno_medio": ic_retorno_medio(r), "ic_expectativa": ic_expectativa(pnl)}


def fmt(v, dec=2, pct=False):
    """Texto de una metrica: numero, intervalo (a, b) o NO ESTIMABLE."""
    if v == NO_ESTIMABLE or v is None:
        return NO_ESTIMABLE
    if isinstance(v, tuple):
        k = 100 if pct else 1
        return f"[{v[0] * k:.{dec}f}, {v[1] * k:.{dec}f}]"
    return f"{v:.{dec}f}" + (" %" if pct else "")
