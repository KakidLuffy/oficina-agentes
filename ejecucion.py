"""
Modelo de ejecucion y simulador historico UNICOS (solo libreria estandar). La simulacion en vivo y el laboratorio
(y la comparacion) ejecutan las ordenes con estas mismas reglas.

Regla de tiempo: una senal se calcula con el CIERRE de la vela i (ya conocido) y la orden se ejecuta al PRECIO DE APERTURA
de la vela i+1 (el primer precio al que se podia operar despues de decidir). Nunca al cierre usado para decidir.

Regla de costes (el modelo se amplia en la mejora de costes compartidos): precio de compra = apertura x (1 + spread/2 + deslizamiento),
precio de venta = apertura x (1 - spread/2 - deslizamiento), y comision sobre el importe en ambas patas.

Limitaciones conocidas (se documentan en el informe): en un mercado 24/7 la apertura de la vela i+1 casi coincide con el cierre de i, asi
que el cambio de regla corrige sobre todo el "operar al precio con el que se decide, sin horquilla"; el retraso real entre
la decision y la orden (minutos) no se modela como movimiento adverso porque no es predecible a partir de velas de 1 hora.
"""
import costes as _co

FEE, SLIP, SPREAD = _co.BASE.fee, _co.BASE.slip, _co.BASE.spread   # ver costes.py (modelo unico de costes)
START = 10.0
STOP_FRAC = 0.7


def precio_compra(apertura, slip=SLIP, spread=SPREAD):
    return apertura * (1 + spread / 2 + slip)


def precio_venta(apertura, slip=SLIP, spread=SPREAD):
    return apertura * (1 - spread / 2 - slip)


def simular(c, o, ini, fin, s, fn, opc=None, fee=FEE, slip=SLIP, spread=SPREAD, start=START, costes=None, permitido=None, curva=None):
    """Opera las velas ini..fin-1 con una posicion como maximo.
    c: cierres, o: aperturas (misma longitud), fn(c, i, s) -> 'b'|'s'|None, opc: {stop, objetivo, espera} o None.
    permitido(i) -> bool (opcional): si es False en la vela i, las COMPRAS decididas en i se ignoran (la moneda no estaba en el universo operable en esa fecha);
    las ventas siempre estan permitidas.
    curva (lista, opcional): se rellena con el capital al cierre de cada vela ini..fin-1 (tras apagarse, el capital se mantiene).
    Devuelve (resultado_eur, operaciones, resultado_de_mantener_eur, caida_maxima_pct)."""
    if costes is not None:                                         # un objeto Costes (costes.py) manda sobre fee/slip/spread sueltos
        fee, slip, spread = costes.fee, costes.slip, costes.spread
    stop_nivel = start * STOP_FRAC
    cash, unidades, ops, apagado = start, 0.0, 0, False
    entrada, libre, pend = 0.0, ini, None
    pico, caida = start, 0.0
    if opc:
        stop, obj, esp = opc["stop"] * s, opc["objetivo"] * s, opc["espera"]
    for i in range(ini, fin):
        if pend and not apagado:                                   # 1) se ejecuta lo decidido en la vela anterior, a la apertura de esta
            if pend == "b" and unidades == 0 and cash > 1 and i >= libre:
                entrada = precio_compra(o[i], slip, spread)
                unidades, cash, ops = cash * (1 - fee) / entrada, 0.0, ops + 1
            elif pend == "s" and unidades > 0:
                cash, unidades, ops = unidades * precio_venta(o[i], slip, spread) * (1 - fee), 0.0, ops + 1
                if opc:
                    libre = i + esp
        pend = None
        p = c[i]
        eq = cash + unidades * p                                   # 2) se valora al cierre
        if curva is not None:
            curva.append(eq)
        pico = max(pico, eq)
        caida = max(caida, (pico - eq) / pico * 100)
        if eq < stop_nivel:                                        # apagado por riesgo: salida inmediata al precio actual
            cash, unidades, apagado = unidades * precio_venta(p, slip, spread) * (1 - fee) + cash, 0.0, True
            if curva is not None:                                  # el resto de velas conserva el capital final
                curva[-1] = cash
                curva.extend([cash] * (fin - 1 - i))
            break
        senal = fn(c, i, s)                                        # 3) se decide con el cierre de esta vela (se ejecutara en la siguiente)
        if opc and unidades > 0:
            cambio = p / entrada - 1
            if cambio <= -stop or cambio >= obj:
                senal = "s"
        if senal == "b" and permitido is not None and not permitido(i):
            senal = None                                           # fuera del universo operable en esa fecha
        if (senal == "b" and unidades == 0 and cash > 1 and i >= libre) or (senal == "s" and unidades > 0):
            pend = senal
    final = cash + unidades * c[fin - 1]
    base = o[min(ini + 1, len(o) - 1)]
    mantener = start * (1 - fee) * c[fin - 1] / precio_compra(base, slip, spread)
    return final - start, ops, mantener - start, caida
