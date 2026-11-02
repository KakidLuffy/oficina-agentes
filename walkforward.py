"""
Validacion walk-forward y regimenes de mercado (solo libreria estandar).

Walk-forward: en vez de UN corte entrenamiento/examen, se desliza una ventana: se elige con un tramo de entrenamiento y se examina en el tramo siguiente,
que no se ha usado para elegir; luego se avanza y se repite. Asi se ve si "elegir lo mejor del pasado" funciona de verdad una y otra vez, no una sola.

Regimen: tendencia con t-estadistico. z = ln(c[i]/c[i-W]) / (sigma_por_vela * sqrt(W)), con sigma de los ultimos W retornos logaritmicos (solo datos hasta i).
z > UMBRAL = alcista, z < -UMBRAL = bajista, en otro caso lateral. No depende de la escala de la vela.
"""
import math

VENTANA_REGIMEN = 60
UMBRAL_REGIMEN = 1.0
REGIMENES = ("alcista", "bajista", "lateral")


def pliegues(n, warm, entreno, prueba, paso=None):
    """[(ini_entreno, fin_entreno, ini_prueba, fin_prueba)] con indices de vela (fin exclusivo). Las pruebas son contiguas y no se solapan."""
    paso = paso or prueba
    if warm < 0 or entreno <= 0 or prueba <= 0 or paso <= 0:
        raise ValueError("parametros de walk-forward invalidos")
    out, ini = [], warm
    while ini + entreno + prueba <= n:
        out.append((ini, ini + entreno, ini + entreno, ini + entreno + prueba))
        ini += paso
    return out


def regimen(c, i, ventana=VENTANA_REGIMEN, umbral=UMBRAL_REGIMEN):
    """'alcista' | 'bajista' | 'lateral' en la vela i usando solo c[0..i]; None si no hay historia suficiente."""
    if i < ventana + 1:
        return None
    rets = [math.log(c[j] / c[j - 1]) for j in range(i - ventana + 1, i + 1)]
    media = sum(rets) / ventana
    sigma = math.sqrt(sum((r - media) ** 2 for r in rets) / (ventana - 1)) if ventana > 1 else 0.0
    total = math.log(c[i] / c[i - ventana])
    if sigma < 1e-12:
        return "lateral" if abs(total) < 1e-12 else ("alcista" if total > 0 else "bajista")
    z = total / (sigma * math.sqrt(ventana))
    return "alcista" if z > umbral else ("bajista" if z < -umbral else "lateral")


def regimenes(c, ventana=VENTANA_REGIMEN, umbral=UMBRAL_REGIMEN):
    return [regimen(c, i, ventana, umbral) for i in range(len(c))]


def por_regimen(curva, c, ini, regs):
    """Atribuye por regimen los retornos por vela de la estrategia (curva de capital que empieza en la vela 'ini')
    y de comprar y mantener. Devuelve {regimen: {velas, estrategia, hold}} con retornos simples sumados (fraccion)."""
    out = {r: {"velas": 0, "estrategia": 0.0, "hold": 0.0} for r in REGIMENES}
    for k in range(1, len(curva)):
        i = ini + k
        r = regs[i] if i < len(regs) else None
        if r is None or curva[k - 1] <= 0:
            continue
        out[r]["velas"] += 1
        out[r]["estrategia"] += curva[k] / curva[k - 1] - 1
        out[r]["hold"] += c[i] / c[i - 1] - 1
    return out
