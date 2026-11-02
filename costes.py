"""
Modelo de costes UNICO (solo libreria estandar): lo usan la simulacion en vivo, el laboratorio y la comparacion.

Tres componentes por operacion:
  fee     comision sobre el importe: 0,40 % (Kraken Pro, nivel mas bajo, orden "maker") o 0,80 % (orden "taker")
  spread  horquilla compra-venta total; cada orden paga la mitad
  slip    deslizamiento: lo que el precio se mueve en contra por el tamano/velocidad de la orden
El spread y el deslizamiento dependen de la LIQUIDEZ (volumen en 24 h): mas caros en monedas con poco volumen.

IMPORTANTE: la horquilla y el deslizamiento son SUPUESTOS DE DISENO, no medidos. Con ordenes que se ejecutan "a mercado" (como supone la
simulacion: se entra a la apertura siguiente) la comision real seria la taker (0,80 %), asi que el escenario ESTRES la usa.
"""
import math
from collections import namedtuple

FACTOR_SPREAD = {"alta": 1.0, "media": 2.5, "baja": 6.25}
FACTOR_SLIP = {"alta": 1.0, "media": 2.0, "baja": 6.0}
VOLUMEN_ALTO = 1_000_000      # EUR en 24 h: a partir de aqui, liquidez alta
VOLUMEN_MEDIO = 100_000       # entre este y el anterior, media; por debajo (o desconocido), baja


class Costes(namedtuple("Costes", "fee slip spread")):
    __slots__ = ()

    def __new__(cls, fee, slip, spread):
        for n, v, tope in (("fee", fee, 0.05), ("slip", slip, 0.05), ("spread", spread, 0.05)):
            if not (isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= tope):
                raise ValueError(f"coste '{n}' invalido: {v!r}")
        return super().__new__(cls, float(fee), float(slip), float(spread))

    def precio_compra(self, apertura):
        return apertura * (1 + self.spread / 2 + self.slip)

    def precio_venta(self, apertura):
        return apertura * (1 - self.spread / 2 - self.slip)

    def coste_ida_y_vuelta(self):
        """Fraccion del capital que se pierde al comprar y vender al mismo precio de referencia."""
        return 1 - (1 - self.fee) ** 2 * self.precio_venta(1.0) / self.precio_compra(1.0)

    def escalar(self, fee=1.0, slip=1.0, spread=1.0):
        return Costes(self.fee * fee, self.slip * slip, self.spread * spread)


BASE = Costes(0.004, 0.0005, 0.0008)                       # lo acordado: comision 0,40 %, y supuestos para el resto (monedas liquidas)
ESTRES = Costes(0.008, BASE.slip * 2, BASE.spread * 2)     # taker 0,80 % + horquilla y deslizamiento x2


def nivel(volumen_eur):
    if not isinstance(volumen_eur, (int, float)) or not math.isfinite(volumen_eur):
        return "baja"
    return "alta" if volumen_eur >= VOLUMEN_ALTO else ("media" if volumen_eur >= VOLUMEN_MEDIO else "baja")


def por_liquidez(volumen_eur, base=BASE, es_btc=False):
    """Costes de una moneda segun su volumen de 24 h. BTC se considera siempre liquido; volumen desconocido = poco liquido."""
    n = "alta" if es_btc else nivel(volumen_eur)
    return base.escalar(1.0, FACTOR_SLIP[n], FACTOR_SPREAD[n])
