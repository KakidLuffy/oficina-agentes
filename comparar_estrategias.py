#!/usr/bin/env python3
"""
Compara estrategias y duraciones de vela sobre el HISTORIAL REAL de BTC/EUR (dinero ficticio).

Para cada combinacion estrategia x duracion de vela calcula:
  - el resultado con 50 EUR y comision del 0,25 %,
  - cuanto mejora o empeora frente a simplemente comprar y mantener,
  - lo mismo en la primera y en la segunda mitad del periodo, por separado.

Una combinacion solo es interesante si supera a "comprar y mantener" en las dos mitades.
Aun asi, al probar muchas combinaciones algunas saldran bien por casualidad:
hay que confirmarlas despues con la simulacion en vivo.

Uso:
  python comparar_estrategias.py              -> descarga precios reales de Kraken
  python comparar_estrategias.py --demo       -> precios inventados, sin internet
  python comparar_estrategias.py --out carpeta -> donde guardar comparacion.md y .csv
"""
import csv
import json
import math
import os
import random
import sys
import urllib.request

START = 50.0
FEE = 0.0025
STOP = START * 0.7
WARM = 50   # velas de calentamiento antes de empezar a operar
INTERVALOS = [(15, "15 minutos"), (60, "1 hora"), (240, "4 horas"), (1440, "1 día")]


# ---------------- estrategias: f(cierres, i, escala) -> "b" | "s" | None ----------------
def media(c, i, n):
    w = c[max(0, i - n + 1):i + 1]
    return sum(w) / len(w)


def cruce(a, b):
    def f(c, i, s):
        if i < b:
            return None
        ca, cb, pa, pb = media(c, i, a), media(c, i, b), media(c, i - 1, a), media(c, i - 1, b)
        if pa <= pb and ca > cb:
            return "b"
        if pa >= pb and ca < cb:
            return "s"
        return None
    return f


def momentum(c, i, s):
    if i < 12:
        return None
    r, t = c[i] / c[i - 12] - 1, 0.012 * s
    return "b" if r > t else ("s" if r < -t else None)


def rebote(c, i, s):
    if i < 20:
        return None
    m = media(c, i, 20)
    return "b" if c[i] < m * (1 - 0.015 * s) else ("s" if c[i] > m else None)


def ruptura(c, i, s):
    """Compra al superar el maximo de las ultimas 20 velas, vende al perder el minimo de las ultimas 10."""
    if i < 20:
        return None
    if c[i] > max(c[i - 20:i]):
        return "b"
    if c[i] < min(c[i - 10:i]):
        return "s"
    return None


ESTRATEGIAS = [
    ("Cruce 5/20", cruce(5, 20)),
    ("Cruce 10/30", cruce(10, 30)),
    ("Cruce 20/50", cruce(20, 50)),
    ("Momentum", momentum),
    ("Rebote", rebote),
    ("Ruptura 20/10", ruptura),
]


# ---------------- simulacion ----------------
def simular(c, ini, fin, s, fn):
    """Opera de la vela ini a la fin-1. Devuelve (resultado, operaciones, resultado de mantener)."""
    cash, btc, ops, apagado = START, 0.0, 0, False
    for i in range(ini, fin):
        p = c[i]
        if apagado:
            break
        senal = fn(c, i, s)
        if senal == "b" and cash > 1:
            btc, cash, ops = cash * (1 - FEE) / p, 0.0, ops + 1
        elif senal == "s" and btc > 0:
            cash, btc, ops = btc * p * (1 - FEE), 0.0, ops + 1
        if cash + btc * p < STOP:
            cash, btc, apagado = btc * p * (1 - FEE) + cash, 0.0, True
    final = cash + btc * c[fin - 1]
    mantener = START * (1 - FEE) * c[fin - 1] / c[ini]
    return final - START, ops, mantener - START


# ---------------- datos ----------------
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "oficina-agentes/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def cierres_kraken(minutos):
    d = get_json(f"https://api.kraken.com/0/public/OHLC?pair=XBTEUR&interval={minutos}")
    if d.get("error"):
        raise RuntimeError(d["error"])
    k = [x for x in d["result"] if x != "last"][0]
    return [float(v[4]) for v in d["result"][k][:-1]]   # sin la vela en curso


def cierres_coinbase(minutos):
    if minutos not in (15, 60, 1440):
        raise RuntimeError("Coinbase no ofrece esta duracion")
    d = get_json(f"https://api.exchange.coinbase.com/products/BTC-EUR/candles?granularity={minutos * 60}")
    return [float(v[4]) for v in sorted(d, key=lambda v: v[0])][:-1]


def cierres_demo(minutos):
    random.seed(minutos)
    p, out = 60000.0, []
    for _ in range(720):
        p *= 1 + random.gauss(0, 0.007 * math.sqrt(minutos / 60))
        out.append(p)
    return out


def obtener(minutos, demo):
    if demo:
        return cierres_demo(minutos), "demo"
    try:
        return cierres_kraken(minutos), "Kraken"
    except Exception as e1:
        try:
            return cierres_coinbase(minutos), "Coinbase"
        except Exception as e2:
            print(f"  No se pudo descargar velas de {minutos} min (Kraken: {e1}; Coinbase: {e2})")
            return None, None


# ---------------- informe ----------------
def f2(v):
    return f"{v:+.2f}"


def main():
    demo = "--demo" in sys.argv
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
    os.makedirs(out, exist_ok=True)
    md = ["# Comparación de estrategias sobre el historial real de BTC/EUR",
          "",
          f"Dinero ficticio: {START:.0f} € por combinación, comisión {FEE * 100:.2f} % por operación. "
          "Las cifras son en euros. \"Dif.\" es la diferencia frente a comprar y mantener durante el mismo periodo "
          "(positivo = mejor que mantener).",
          ""]
    filas, buenas = [], []
    for minutos, nombre in INTERVALOS:
        c, fuente = obtener(minutos, demo)
        if not c or len(c) < WARM + 40:
            md += [f"## Velas de {nombre}", "", "Sin datos suficientes.", ""]
            continue
        n, mid, s = len(c), (WARM + len(c)) // 2, math.sqrt(minutos / 60)
        dias = n * minutos / 1440
        md += [f"## Velas de {nombre} ({n} velas ≈ {dias:.0f} días, {fuente})", "",
               "| Estrategia | Resultado (€) | Operaciones | Dif. total | Dif. 1ª mitad | Dif. 2ª mitad |",
               "|---|---:|---:|---:|---:|---:|"]
        for nom, fn in ESTRATEGIAS:
            r, ops, hold = simular(c, WARM, n, s, fn)
            r1, _, h1 = simular(c, WARM, mid, s, fn)
            r2, _, h2 = simular(c, mid, n, s, fn)
            d, d1, d2 = r - hold, r1 - h1, r2 - h2
            ok = r > 0 and d > 0 and d1 > 0 and d2 > 0   # gana dinero Y supera a mantener, en todo y en las dos mitades
            md.append(f"| {nom}{' ✔' if ok else ''} | {f2(r)} | {ops} | {f2(d)} | {f2(d1)} | {f2(d2)} |")
            filas.append([nombre, nom, round(r, 2), ops, round(hold, 2), round(d, 2), round(d1, 2), round(d2, 2), ok])
            if ok:
                buenas.append(f"{nom} con velas de {nombre}")
        md +=[f"| *Comprar y mantener* | {f2(START * (1 - FEE) * c[-1] / c[WARM] - START)} | 1 | – | – | – |", ""]
    md += ["## Veredicto", ""]
    if buenas:
        md.append("Combinaciones que ganan dinero y además superan a comprar y mantener, en el total y en las dos mitades (✔): "
                  + "; ".join(buenas) + ".")
        md.append("")
        md.append("Cuidado: se han probado muchas combinaciones y algunas saldrán bien solo por azar. "
                  "Una candidata solo merece confianza si también aguanta semanas en la simulación en vivo.")
    else:
        md.append("Ninguna combinación gana dinero y supera a comprar y mantener a la vez en el total y en las dos mitades. "
                  "Con estos datos no hay una estrategia que justifique dinero real.")
    md += ["", "Notas: los periodos de cada duración son distintos (las velas cortas cubren pocos días), "
           "así que cada tabla se compara solo con comprar y mantener en su propio periodo. "
           "El historial pasado no garantiza resultados futuros."]
    texto = "\n".join(md) + "\n"
    with open(os.path.join(out, "comparacion.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    with open(os.path.join(out, "comparacion.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vela", "estrategia", "resultado_eur", "operaciones", "mantener_eur",
                    "dif_total", "dif_mitad1", "dif_mitad2", "supera_en_todo"])
        w.writerows(filas)
    print(texto)


if __name__ == "__main__":
    main()
