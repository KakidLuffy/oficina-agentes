"""
Reglas del exchange para una moneda: volumen minimo (ordermin), coste minimo en EUR (costmin) y decimales (solo libreria estandar).
Salen de la lista de pares de Kraken (AssetPairs). Si un dato falta o no se puede leer se usa un SUPUESTO generico y la regla queda marcada
como fuente="supuesto" para que el resumen avise de que ese minimo no esta verificado.
"""
import math
from collections import namedtuple

Regla = namedtuple("Regla", "par ordermin costmin lot_decimals pair_decimals fuente")
GENERICA = Regla("*", 0.0, 0.5, 8, 8, "supuesto")      # 0,5 EUR de coste minimo es lo habitual en pares contra EUR; NO esta verificado


def _num(x, defecto):
    try:
        v = float(x)
        return v if math.isfinite(v) and v >= 0 else defecto
    except (TypeError, ValueError):
        return defecto


def desde_kraken(par, d):
    """d: entrada de AssetPairs de Kraken. Devuelve una Regla; si faltan los campos clave, la regla es un supuesto."""
    if not isinstance(d, dict) or "ordermin" not in d or "costmin" not in d:
        return GENERICA._replace(par=par)
    om, cm = _num(d.get("ordermin"), None), _num(d.get("costmin"), None)
    if om is None or cm is None:
        return GENERICA._replace(par=par)
    return Regla(par, om, cm, int(_num(d.get("lot_decimals"), 8)), int(_num(d.get("pair_decimals"), 8)), "kraken")


def redondear_abajo(x, decimales):
    f = 10 ** decimales
    return math.floor(x * f + 1e-9) / f


def motivo_invalida(regla, cantidad, precio):
    """None si la orden cumple los minimos; si no, el motivo (texto)."""
    if not cantidad > 0:
        return "la cantidad no es positiva"
    if cantidad < regla.ordermin:
        return f"por debajo del volumen minimo del exchange ({cantidad:.8g} < {regla.ordermin:g})"
    if cantidad * precio < regla.costmin:
        return f"por debajo del coste minimo del exchange ({cantidad * precio:.2f} EUR < {regla.costmin:g} EUR)"
    return None
