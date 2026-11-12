#!/usr/bin/env python3
"""
LABORATORIO de estrategias v2 (dinero ficticio, no opera en ningún exchange). Reglas en CRITERIOS.md, sección 4.

Un grupo de "analistas" genera muchas variantes de estrategias y las examina de forma estricta:
  1. Datos largos: velas de Coinbase (EUR) desde que existe cada moneda, de 1 día y de 6 h.
  2. Examen por años que avanzan: se elige con el año Y-1 (entrenamiento) y se examina con el año Y, para cada año.
  3. Una variante aprueba una serie en un año si hace al menos 2 operaciones, supera a "mantener con su misma
     exposición media" y su caída máxima no es mayor que la de comprar y mantener. Aprueba el año si aprueba
     al menos el 60 % de las series.
  4. Candidata: aprueba al menos el 60 % de los años, gana dinero de media en el examen y estuvo alguna vez entre
     las 12 mejores del entrenamiento. Las velas de 1 día y de 6 h se juzgan por separado.
  5. Control del azar: cuántas variantes serían candidatas por pura casualidad (binomial con la tasa de aprobado).

Es un modo "propone, no ejecuta": las candidatas NO operan solas.

Uso:
  python laboratorio.py               -> descarga precios reales de Coinbase
  python laboratorio.py --demo        -> precios inventados, sin internet
  python laboratorio.py --out datos   -> carpeta donde guardar laboratorio.json y laboratorio.md
"""
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import comparar_estrategias as ce

ce.FEE = 0.004                  # mismos costes que la simulacion en vivo (comision Kraken Pro 0,40 % + deslizamiento 0,05 %)
START, FEE, SLIP = ce.START, ce.FEE, ce.SLIP
WARM = 200                      # velas de calentamiento (el filtro de tendencia usa 200)
MIN_OPS_ANUAL = 2               # operaciones minimas en cada año de examen
FRACCION_SERIES = 0.6           # aprueba el año si aprueba al menos el 60 % de las series
FRACCION_ANIOS = 0.6            # candidata si aprueba al menos el 60 % de los años de examen
COBERTURA_ENTRENO = 0.75        # una serie entra en un año si tiene el 75 % de las velas del año de entrenamiento
COBERTURA_EXAMEN = 0.5          # ... y el 50 % de las del año de examen (el año en curso cuenta si va por la mitad)
MIN_SERIES_ANIO = 3
N_CANDIDATAS = 12               # las mejores del entrenamiento de cada año
PARES = [("BTC", "BTC-EUR"), ("ETH", "ETH-EUR"), ("SOL", "SOL-EUR"), ("XRP", "XRP-EUR"), ("ADA", "ADA-EUR"), ("DOGE", "DOGE-EUR"),
         ("LINK", "LINK-EUR"), ("DOT", "DOT-EUR"), ("LTC", "LTC-EUR"), ("AVAX", "AVAX-EUR"), ("ATOM", "ATOM-EUR"), ("TRX", "TRX-EUR")]
VELAS = [(1440, "1 día"), (360, "6 h")]   # Coinbase no ofrece velas de 4 h


class Serie(list):
    """Lista de cierres con medias móviles precalculadas (para que el laboratorio sea rápido).
    `t` son los instantes de apertura de cada vela; `ref` es BTC alineado por fecha (para la fuerza relativa)."""
    def __init__(self, v, t=None):
        super().__init__(v)
        self.t = list(t) if t is not None else list(range(len(v)))
        self._sma = {}
        self.ref = None

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


# ---------------- familias de estrategias parametrizadas ----------------
def cruce(a, b):
    def f(c, i, s):
        sa, sb = c.sma(a), c.sma(b)
        if i < b:
            return None
        if sa[i - 1] <= sb[i - 1] and sa[i] > sb[i]:
            return "b"
        if sa[i - 1] >= sb[i - 1] and sa[i] < sb[i]:
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
        m = c.sma(n)[i]
        return "b" if c[i] < m * (1 - t * s) else ("s" if c[i] > m else None)
    return f


def ruptura(n, m):
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
    def f(c, i, s):
        senal = fn(c, i, s)
        if senal == "b" and (i < n or c[i] <= c.sma(n)[i]):
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
    """Fuerza relativa: compra si la moneda sube mas que BTC (margen) en n velas y sube de por si; vende si rinde menos que BTC."""
    def f(c, i, s):
        r = c.ref
        if r is None or i < n or len(r) <= i:
            return None
        rc, rb = c[i] / c[i - n] - 1, r[i] / r[i - n] - 1
        if rc > rb + margen * s and rc > 0:
            return "b"
        if rc < rb:
            return "s"
        return None
    return f


# salidas con stop y objetivo: (stop, objetivo, velas de espera tras vender), todo escalado a la duracion de la vela
SALIDA = {"stop": 0.015, "objetivo": 0.03, "espera": 3}


def variantes():
    """Devuelve [(analista, nombre, funcion, opciones)]."""
    v = []
    for a, nom, fn in _base():
        v.append((a, nom, fn, None))
    for a, b in ((5, 20), (10, 30), (10, 50)):
        for k in (0.5, 1.0):
            v.append(("Analista de volatilidad", f"Cruce {a}/{b} con volatilidad ≥{k:g}", con_volatilidad(cruce(a, b), k), None))
    v.append(("Analista de volatilidad", "Momentum 12 velas ±1,2 % con volatilidad ≥0,5", con_volatilidad(momentum(12, 0.012), 0.5), None))
    v.append(("Analista de volatilidad", "Momentum 12 velas ±1,2 % con volatilidad ≥1", con_volatilidad(momentum(12, 0.012), 1.0), None))
    for nom, fn in (("Cruce 5/20", cruce(5, 20)), ("Cruce 10/30", cruce(10, 30)), ("Cruce 10/30 + filtro", con_filtro(cruce(10, 30))),
                    ("Cruce 3/8", cruce(3, 8)), ("Momentum 12 velas ±1,2 %", momentum(12, 0.012)),
                    ("Rebote 20 velas 1,5 %", rebote(20, 0.015)), ("Ruptura 20/10", ruptura(20, 10)),
                    ("Ruptura 20/10 + filtro", con_filtro(ruptura(20, 10)))):
        v.append(("Analista de salidas", nom + " con stop 1,5 % y objetivo 3 %", fn, SALIDA))
    for n in (6, 12, 24):
        for m in (0.005, 0.01):
            v.append(("Analista de fuerza relativa", f"Fuerza relativa vs BTC {n} velas +{m * 100:.1f} %", relativa(n, m), None))
    return v


def _base():
    v = []
    for a in (3, 5, 8, 10, 15, 20):
        for b in (20, 30, 50, 80):
            if a < b:
                v.append(("Analista de tendencia", f"Cruce {a}/{b}", cruce(a, b)))
                v.append(("Analista de filtros", f"Cruce {a}/{b} + filtro", con_filtro(cruce(a, b))))
    for n in (6, 12, 24):
        for t in (0.008, 0.012, 0.02):
            v.append(("Analista de tendencia", f"Momentum {n} velas ±{t * 100:.1f} %", momentum(n, t)))
            v.append(("Analista de filtros", f"Momentum {n} velas ±{t * 100:.1f} % + filtro", con_filtro(momentum(n, t))))
    for n in (10, 20, 40):
        for t in (0.01, 0.015, 0.025):
            v.append(("Analista de rebote", f"Rebote {n} velas {t * 100:.1f} %", rebote(n, t)))
    for n, m in ((10, 5), (20, 10), (40, 20)):
        v.append(("Analista de tendencia", f"Ruptura {n}/{m}", ruptura(n, m)))
        v.append(("Analista de filtros", f"Ruptura {n}/{m} + filtro", con_filtro(ruptura(n, m))))
    return v




# ---------------- simulador ----------------
def simular(c, ini, fin, s, fn, opc=None):
    """Opera de la vela ini a la fin-1 empezando con START en efectivo. Con `opc`, añade stop, objetivo y espera.
    Devuelve dict: res, ops, hold (resultado de comprar y mantener), dd y dd_hold (caídas máximas en %),
    expo (fracción de velas con la moneda comprada)."""
    if opc:
        stop, obj, esp = opc["stop"] * s, opc["objetivo"] * s, opc["espera"]
    cash, mon, ops, entrada, libre = START, 0.0, 0, 0.0, ini
    pico, dd, dentro = START, 0.0, 0
    unidades = START * (1 - FEE) / (c[ini] * (1 + SLIP))
    pico_h, dd_h = START, 0.0
    for i in range(ini, fin):
        p = c[i]
        senal = fn(c, i, s)
        if opc and mon > 0:
            cambio = p / entrada - 1
            if cambio <= -stop or cambio >= obj:
                senal = "s"
        if senal == "b" and mon == 0 and cash > 1 and i >= libre:
            entrada = p * (1 + SLIP)
            mon, cash, ops = cash * (1 - FEE) / entrada, 0.0, ops + 1
        elif senal == "s" and mon > 0:
            cash, mon, ops = mon * p * (1 - SLIP) * (1 - FEE), 0.0, ops + 1
            if opc:
                libre = i + esp
        if mon > 0:
            dentro += 1
        eq = cash + mon * p
        pico = max(pico, eq)
        dd = max(dd, (pico - eq) / pico * 100)
        eh = unidades * p
        pico_h = max(pico_h, eh)
        dd_h = max(dd_h, (pico_h - eh) / pico_h * 100)
        if eq < ce.STOP:                       # misma regla de apagado que comparar_estrategias
            cash, mon = mon * p * (1 - SLIP) * (1 - FEE) + cash, 0.0
            break
    final = cash + mon * c[fin - 1]
    hold = START * (1 - FEE) * c[fin - 1] / (c[ini] * (1 + SLIP)) - START
    return {"res": final - START, "ops": ops, "hold": hold, "dd": dd, "dd_hold": dd_h, "expo": dentro / max(1, fin - ini)}


def aprueba(r):
    """Una serie en un año de examen (CRITERIOS.md, sección 4)."""
    return (r["ops"] >= MIN_OPS_ANUAL
            and r["res"] > r["expo"] * r["hold"]       # supera a mantener con su misma exposición media
            and r["dd"] <= r["dd_hold"])               # sin caer más que comprar y mantener


# ---------------- datos ----------------
def descargar(producto, minutos):
    """Todas las velas cerradas de Coinbase desde que existe el par: (instantes, cierres). 300 velas por petición."""
    paso = minutos * 60
    ahora = int(time.time())
    fin = ahora // paso * paso
    velas, vacias = {}, 0
    while vacias < 2 and fin > 1_420_070_400:          # hasta 2015
        ini = fin - 300 * paso
        url = (f"https://api.exchange.coinbase.com/products/{producto}/candles?granularity={paso}"
               f"&start={datetime.fromtimestamp(ini, timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
               f"&end={datetime.fromtimestamp(fin - 1, timezone.utc):%Y-%m-%dT%H:%M:%SZ}")
        for intento in range(4):                       # Coinbase a veces pide ir más despacio (429)
            try:
                d = ce.get_json(url)
                break
            except urllib.error.HTTPError as e:
                if e.code == 404 or intento == 3:
                    raise
                time.sleep(3 * (intento + 1))
        if isinstance(d, dict):
            raise RuntimeError(d.get("message", d))
        vacias = vacias + 1 if not d else 0
        for x in d:
            if int(x[0]) + paso <= ahora:
                velas[int(x[0])] = float(x[4])
        fin = ini
        time.sleep(0.35)
    ts = sorted(velas)
    return ts, [velas[t] for t in ts]


def demo(sym, minutos):
    """Precios inventados con fases alcistas y bajistas, desde 2018 (1 día) o 2021 (6 h) hasta hoy."""
    random.seed(sum(map(ord, sym)) * 7 + minutos)
    paso = minutos * 60
    t0 = int(datetime(2018 if minutos >= 1440 else 2021, 1, 1, tzinfo=timezone.utc).timestamp())
    t0 += 86400 * 120 * (sum(map(ord, sym)) % 4)       # monedas que empiezan más tarde
    fin = int(time.time()) // paso * paso - paso
    p, ts, out, deriva = 100.0, [], [], 0.0
    vol = 0.03 * math.sqrt(minutos / 1440)
    for k, t in enumerate(range(t0, fin, paso)):
        if k % int(86400 * 90 / paso) == 0:
            deriva = random.gauss(0, 0.004) * minutos / 1440
        p *= 1 + random.gauss(deriva, vol)
        ts.append(t)
        out.append(max(p, 1e-6))
    return ts, out


def cargar_series(es_demo):
    series, faltan = [], []
    for sym, producto in PARES:
        for minutos, nom in VELAS:
            try:
                ts, c = demo(sym, minutos) if es_demo else descargar(producto, minutos)
            except Exception as e:
                print(f"  sin datos de {sym} {nom}: {e}")
                faltan.append(f"{sym} {nom}")
                continue
            if len(c) < WARM + 2 * 365 * 1440 // minutos // 2:
                print(f"  {sym} {nom}: historia demasiado corta ({len(c)} velas)")
                faltan.append(f"{sym} {nom}")
                continue
            series.append({"moneda": sym, "vela": nom, "minutos": minutos, "c": Serie(c, ts)})
            print(f"  {sym} {nom}: {len(c)} velas desde {datetime.fromtimestamp(ts[0], timezone.utc):%Y-%m-%d}")
    alinear_ref(series)
    return series, faltan


def alinear_ref(series):
    """Pone en cada serie el BTC de la misma duración de vela, alineado por fecha (las monedas empiezan en días distintos)."""
    for s in series:
        ref = [x for x in series if x["moneda"] == "BTC" and x["minutos"] == s["minutos"]]
        if not ref:
            continue
        r = ref[0]["c"]
        mapa, ultimo, alineado = dict(zip(r.t, r)), None, []
        for t in s["c"].t:
            ultimo = mapa.get(t, ultimo)
            alineado.append(ultimo if ultimo is not None else float("nan"))
        s["c"].ref = alineado


def tramos_anuales(serie, minutos):
    """{año: (ini, fin, fracción de velas presentes)} solo con velas posteriores al calentamiento."""
    por_anio, esperadas = {}, 365 * 1440 / minutos
    for i, t in enumerate(serie.t):
        if i < WARM:
            continue
        y = datetime.fromtimestamp(t, timezone.utc).year
        a = por_anio.setdefault(y, [i, i + 1])
        a[1] = i + 1
    return {y: (a, b, (b - a) / esperadas) for y, (a, b) in por_anio.items()}


# ---------------- examen ----------------
def examinar(series, todas, minutos):
    """Examen por años para una duración de vela. Devuelve el resumen (dict) de esa duración."""
    sel = [s for s in series if s["minutos"] == minutos]
    tramos = [(s, tramos_anuales(s["c"], minutos)) for s in sel]
    anios = sorted({y for _, tr in tramos for y in tr})
    pliegues = []                                       # (año de entrenamiento, año de examen, series que entran)
    for y in anios[1:]:
        dentro = [(s, tr[y - 1], tr[y]) for s, tr in tramos
                  if y - 1 in tr and y in tr and tr[y - 1][2] >= COBERTURA_ENTRENO and tr[y][2] >= COBERTURA_EXAMEN]
        if len(dentro) >= MIN_SERIES_ANIO:
            pliegues.append((y - 1, y, dentro))
    if not pliegues:
        return None
    cache = {}

    def sim(k, s, tramo, fn, opc):                     # cada (variante, serie, año) se simula una sola vez
        clave = (k, id(s), tramo[0])
        if clave not in cache:
            cache[clave] = simular(s["c"], tramo[0], tramo[1], math.sqrt(minutos / 60), fn, opc)
        return cache[clave]

    filas = []
    for k, (analista, nombre, fn, opc) in enumerate(todas):
        por_pliegue = []
        for ye, yx, dentro in pliegues:
            tr = [sim(k, s, a, fn, opc) for s, a, _ in dentro]
            ex = [sim(k, s, b, fn, opc) for s, _, b in dentro]
            ok = sum(aprueba(r) for r in ex)
            por_pliegue.append({
                "anio": yx, "series": len(ex), "ok": ok,
                "pasa": ok >= math.ceil(FRACCION_SERIES * len(ex)),
                "train_dif": sum(r["res"] - r["hold"] for r in tr) / len(tr),
                "test_res": sum(r["res"] for r in ex) / len(ex),
                "test_dif": sum(r["res"] - r["hold"] for r in ex) / len(ex),
                "test_dif_expo": sum(r["res"] - r["expo"] * r["hold"] for r in ex) / len(ex),
                "dd": max(r["dd"] for r in ex), "dd_hold": max(r["dd_hold"] for r in ex),
                "ops": sum(r["ops"] for r in ex) / len(ex),
            })
        n = len(por_pliegue)
        filas.append({"analista": analista, "nombre": nombre, "pp": por_pliegue,
                      "train_dif": sum(p["train_dif"] for p in por_pliegue) / n,
                      "test_res": sum(p["test_res"] for p in por_pliegue) / n,
                      "test_dif": sum(p["test_dif"] for p in por_pliegue) / n,
                      "test_dif_expo": sum(p["test_dif_expo"] for p in por_pliegue) / n,
                      "ops": sum(p["ops"] for p in por_pliegue) / n,
                      "dd": sum(p["dd"] for p in por_pliegue) / n, "dd_hold": sum(p["dd_hold"] for p in por_pliegue) / n,
                      "ok": sum(p["pasa"] for p in por_pliegue), "total": n, "elegida": 0, "ok_elegida": 0})
    for j in range(len(pliegues)):                     # las 12 mejores del entrenamiento de cada año
        for f in sorted(filas, key=lambda f: f["pp"][j]["train_dif"], reverse=True)[:N_CANDIDATAS]:
            f["elegida"] += 1
            f["ok_elegida"] += f["pp"][j]["pasa"]
    n_pl = len(pliegues)
    minimo = math.ceil(FRACCION_ANIOS * n_pl)
    for f in filas:
        f["pasa"] = f["ok"] >= minimo and f["test_res"] > 0 and f["elegida"] > 0
    azar = sum(f["ok"] for f in filas) / (len(filas) * n_pl)
    p_azar = sum(math.comb(n_pl, k) * azar ** k * (1 - azar) ** (n_pl - k) for k in range(minimo, n_pl + 1))
    esperadas = len(filas) * p_azar
    elegidas_total = sum(f["elegida"] for f in filas)
    tasa_sel = sum(f["ok_elegida"] for f in filas) / elegidas_total if elegidas_total else 0.0
    candidatas = sorted([f for f in filas if f["pasa"]], key=lambda f: f["test_dif_expo"], reverse=True)
    if not candidatas:
        veredicto = "ninguna"
    elif len(candidatas) >= 2 and len(candidatas) > 2 * esperadas + 1:
        veredicto = "posible"
    else:
        veredicto = "ruido"
    return {"minutos": minutos, "pliegues": [(a, b, len(d)) for a, b, d in pliegues], "filas": filas,
            "candidatas": candidatas, "azar": azar, "esperadas": esperadas, "tasa_sel": tasa_sel,
            "minimo": minimo, "veredicto": veredicto, "series": [f"{s['moneda']}" for s in sel]}


def texto_veredicto(r, nom):
    n, pl = len(r["candidatas"]), r["pliegues"]
    anios = f"{len(pl)} años de examen ({pl[0][1]}–{pl[-1][1]})"
    if r["veredicto"] == "ninguna":
        return f"Velas de {nom}: ninguna variante aprueba al menos {r['minimo']} de los {anios} ganando dinero de media."
    if r["veredicto"] == "posible":
        return (f"Velas de {nom}: {n} candidatas en {anios}, más del doble de las {r['esperadas']:.1f} que daría el azar. "
                "Son candidatas para registrar como hipótesis y probar en simulación.")
    return (f"Velas de {nom}: {n} candidata(s) en {anios}, pero el azar ya daría unas {r['esperadas']:.1f}. "
            "No se distingue de la casualidad: tomar solo como pista.")


def main():
    es_demo = "--demo" in sys.argv
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
    os.makedirs(out, exist_ok=True)
    series, faltan = cargar_series(es_demo)
    if len(series) < 4:
        print("Datos insuficientes: no se actualiza el laboratorio.")
        sys.exit(0)
    todas = variantes()
    por_vela = {}
    for minutos, nom in VELAS:
        r = examinar(series, todas, minutos)
        if r:
            r["nombre"] = nom
            por_vela[nom] = r
            print(f"Velas de {nom}: {len(r['pliegues'])} años de examen, veredicto {r['veredicto']}.")
    if not por_vela:
        print("No hay años de examen suficientes: no se actualiza el laboratorio.")
        sys.exit(0)
    orden = {"posible": 2, "ruido": 1, "ninguna": 0}
    veredicto = max((r["veredicto"] for r in por_vela.values()), key=orden.get)
    txt = " ".join(texto_veredicto(r, nom) for nom, r in por_vela.items())

    def limpia(f, nom):
        d = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in f.items() if k != "pp"}
        d["nombre"], d["variante"], d["vela"] = f"{f['nombre']} ({nom})", f["nombre"], nom
        d["anios"] = [{"anio": p["anio"], "pasa": p["pasa"], "ok": p["ok"], "series": p["series"],
                       "test_res": round(p["test_res"], 2), "test_dif_expo": round(p["test_dif_expo"], 2)} for p in f["pp"]]
        return d

    analistas, familias, candidatas, mejores = {}, {}, [], []
    for nom, r in por_vela.items():
        for f in r["filas"]:
            a = analistas.setdefault(f["analista"], {"nombre": f["analista"], "probadas": 0, "candidatas": 0})
            a["probadas"] += 1
            a["candidatas"] += 1 if f["pasa"] else 0
            d = familias.setdefault(f"{f['analista']} ({nom})", {"variantes": 0, "dif": 0.0, "dif_expo": 0.0, "ops": 0.0, "aprueban": 0})
            d["variantes"] += 1
            d["dif"] += f["test_dif"]
            d["dif_expo"] += f["test_dif_expo"]
            d["ops"] += f["ops"]
            d["aprueban"] += 1 if f["pasa"] else 0
        candidatas += [limpia(f, nom) for f in r["candidatas"]]
        mejores += [limpia(f, nom) for f in sorted(r["filas"], key=lambda f: f["train_dif"], reverse=True)[:N_CANDIDATAS]]
    probadas = sum(len(r["filas"]) for r in por_vela.values())
    azar = sum(r["azar"] * len(r["filas"]) for r in por_vela.values()) / probadas
    datos = {
        "version": 2,
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": "demo" if es_demo else "Coinbase",
        "series": [f"{s['moneda']} {s['vela']}" for s in series],
        "sin_datos": faltan,
        "probadas": probadas, "tasa_azar": round(azar, 3), "veredicto": veredicto, "texto": txt,
        "criterio": (f"examen año a año (se elige con el año anterior); una serie aprueba un año con ≥{MIN_OPS_ANUAL} operaciones, "
                     f"superando a mantener con la misma exposición y sin caer más que mantener; aprueba el año con ≥{int(FRACCION_SERIES * 100)} % "
                     f"de las series; candidata si aprueba ≥{int(FRACCION_ANIOS * 100)} % de los años y gana dinero de media. "
                     "Velas de 1 día y de 6 h por separado"),
        "por_vela": {nom: {"veredicto": r["veredicto"], "texto": texto_veredicto(r, nom), "variantes": len(r["filas"]),
                           "anios_examen": [b for _, b, _ in r["pliegues"]], "series_por_anio": [n for _, _, n in r["pliegues"]],
                           "tasa_azar": round(r["azar"], 3), "candidatas_por_azar": round(r["esperadas"], 2),
                           "tasa_aprobado_elegidas": round(r["tasa_sel"], 3), "candidatas": len(r["candidatas"])}
                     for nom, r in por_vela.items()},
        "analistas": list(analistas.values()),
        "familias": {n: {"variantes": d["variantes"], "dif_media_examen": round(d["dif"] / d["variantes"], 2),
                         "dif_media_misma_exposicion": round(d["dif_expo"] / d["variantes"], 2),
                         "operaciones_medias_anio": round(d["ops"] / d["variantes"], 1), "aprueban": d["aprueban"]}
                     for n, d in familias.items()},
        "candidatas": candidatas,
        "mejores_entreno": mejores,
    }
    with open(os.path.join(out, "laboratorio.json"), "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)

    md = ["# Laboratorio de estrategias (v2)", "",
          f"Actualizado: {datos['generado']} · datos: {datos['fuente']} · {len(series)} series ({', '.join(datos['series'])})", ""]
    if faltan:
        md += [f"Sin datos suficientes: {', '.join(faltan)}.", ""]
    md += [f"**Veredicto: {veredicto.upper()}.** {txt}", "",
           f"Variantes probadas: {len(todas)} en cada duración de vela. Criterio (CRITERIOS.md, sección 4): {datos['criterio']}.", ""]
    for nom, r in por_vela.items():
        pv = datos["por_vela"][nom]
        md += [f"## Velas de {nom}", "",
               f"Años de examen: {', '.join(f'{b} ({n} series)' for _, b, n in r['pliegues'])}. "
               f"Tasa de aprobado de un año cualquiera: {pv['tasa_azar'] * 100:.0f} %; de las elegidas por el entrenamiento: "
               f"{pv['tasa_aprobado_elegidas'] * 100:.0f} %. Candidatas esperadas por azar: {pv['candidatas_por_azar']:.1f}.", "",
               "Las mejores en el entrenamiento (medias por año de examen, en € sobre 50 € ficticios):", "",
               "| Variante | Analista | Dif. entreno vs mantener | Resultado examen | Examen vs mantener | Examen vs misma exposición | Caída máx. / mantener | Op./año | Años aprobados | Candidata |",
               "|---|---|---:|---:|---:|---:|---:|---:|---:|:-:|"]
        for f in sorted(r["filas"], key=lambda f: f["train_dif"], reverse=True)[:N_CANDIDATAS]:
            md.append(f"| {f['nombre']} | {f['analista']} | {f['train_dif']:+.2f} | {f['test_res']:+.2f} | {f['test_dif']:+.2f} | "
                      f"{f['test_dif_expo']:+.2f} | {f['dd']:.0f} % / {f['dd_hold']:.0f} % | {f['ops']:.0f} | {f['ok']}/{f['total']} | {'✔' if f['pasa'] else '✘'} |")
        if r["candidatas"]:
            md += ["", "Candidatas, año a año (✔ = aprueba ese año):", "",
                   "| Variante | " + " | ".join(str(b) for _, b, _ in r["pliegues"]) + " |",
                   "|---|" + "|".join(":-:" for _ in r["pliegues"]) + "|"]
            for f in r["candidatas"]:
                md.append(f"| {f['nombre']} | " + " | ".join(f"{'✔' if p['pasa'] else '✘'} {p['test_res']:+.1f}" for p in f["pp"]) + " |")
        md.append("")
    md += ["Resultado medio por familia en el examen (por año, tras costes):", "",
           "| Familia | Variantes | Vs mantener (€) | Vs misma exposición (€) | Op./año | Candidatas |", "|---|---:|---:|---:|---:|---:|"]
    for nom, d in datos["familias"].items():
        md.append(f"| {nom} | {d['variantes']} | {d['dif_media_examen']:+.2f} | {d['dif_media_misma_exposicion']:+.2f} | "
                  f"{d['operaciones_medias_anio']:.0f} | {d['aprueban']} |")
    md += ["", "«Misma exposición»: si una variante estuvo dentro el 30 % del tiempo, se compara con el 30 % del resultado de "
           "comprar y mantener. Las candidatas NO operan solas: solo se proponen. Probar tantas variantes hace que algunas "
           "salgan bien por azar, y el historial pasado no garantiza el futuro. Antes de confiar, deben registrarse como "
           "hipótesis en CRITERIOS.md y aguantar semanas en simulación.", ""]
    with open(os.path.join(out, "laboratorio.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
