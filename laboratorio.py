#!/usr/bin/env python3
"""
LABORATORIO de estrategias (dinero ficticio, no opera en ningún exchange).

Un grupo de "analistas" genera muchas variantes de estrategias y las examina de forma estricta:
  1. Se elige con la PRIMERA parte del historial (entrenamiento) cuáles parecen mejores.
  2. Se las examina con la parte final, que no se ha usado para elegir (examen).
  3. Solo son "candidatas" las que, en el examen, ganan dinero Y superan a comprar y mantener
     en la mayoría de las series (varias monedas y duraciones de vela), con operaciones suficientes.
  4. Se calcula cuántas variantes aprobarían el examen por pura casualidad (tasa de azar).
     Si las candidatas no destacan sobre esa tasa, el veredicto es "ruido".

Es un modo "propone, no ejecuta": las candidatas NO operan solas. Aparecen en el panel y en el informe
para que, pasadas semanas, se decida si merece la pena añadirlas como agentes de simulación.

Uso:
  python laboratorio.py               -> descarga precios reales de Kraken
  python laboratorio.py --demo        -> precios inventados, sin internet
  python laboratorio.py --out datos   -> carpeta donde guardar laboratorio.json y laboratorio.md
"""
import json
import math
import os
import random
import sys
import time
import urllib.request
from datetime import datetime, timezone

import comparar_estrategias as ce
import costes as costes_mod
import ejecucion as ej
import estrategias
import velas as vl
import persistencia as ps

ce.FEE = 0.004                  # mismos costes que la simulacion en vivo (comision Kraken Pro 0,40 % + deslizamiento 0,05 %)
START, FEE, SLIP = ce.START, ce.FEE, ce.SLIP
WARM = 200                      # velas de calentamiento (el filtro de tendencia usa 200)
PARTE_ENTRENO = 0.6             # primer 60 % para elegir, último 40 % para el examen
MIN_OPS_EXAMEN = 4
FRACCION_SERIES = 0.6           # debe aprobar en al menos el 60 % de las series
N_CANDIDATAS = 12               # cuántas variantes (las mejores en entrenamiento) pasan al examen
PARES = [("BTC", "XBTEUR"), ("ETH", "ETHEUR"), ("SOL", "SOLEUR"), ("XRP", "XRPEUR"), ("ADA", "ADAEUR"), ("DOGE", "DOGEEUR"),
         ("LINK", "LINKEUR"), ("DOT", "DOTEUR"), ("LTC", "LTCEUR"), ("AVAX", "AVAXEUR"), ("ATOM", "ATOMEUR"), ("TRX", "TRXEUR")]
VELAS = [(240, "4 h"), (1440, "1 día")]


Serie, alinear = estrategias.Serie, estrategias.alinear
cruce, momentum, rebote, ruptura = estrategias.cruce, estrategias.momentum, estrategias.rebote, estrategias.ruptura
con_filtro, con_volatilidad, relativa = estrategias.con_filtro, estrategias.con_volatilidad, estrategias.relativa


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


# ---------------- simulador con stop, objetivo y espera ----------------
def simular2(c, ini, fin, s, fn, opc, costes=None):
    """Simulador unico (ejecucion.py): senal con el cierre de la vela i, orden a la apertura de i+1, con comision, horquilla y deslizamiento.
    'costes' (costes.py) permite repetir la prueba con otro escenario (por defecto, el base)."""
    return ej.simular(c, c.o, ini, fin, s, fn, opc, FEE, SLIP, ej.SPREAD, START, costes)


# ---------------- datos ----------------
def solo_cerradas(velas_, minutos, ahora_ts):
    """Quita la vela que aun no ha cerrado (por su marca temporal, no por 'la ultima de la lista')."""
    return [x for x in velas_ if x.ts + minutos * 60 <= ahora_ts]


def preparar(velas_, minutos, ahora_ts):
    """Valida y se queda con las velas cerradas. Devuelve (velas, incidencias)."""
    util, inc = vl.validar(velas_, minutos * 60, ahora_ts)
    return solo_cerradas(util, minutos, ahora_ts), inc


def descargar(par, minutos):
    """Devuelve las velas CERRADAS y validadas (lista de Vela) con sus marcas temporales."""
    d = ce.get_json(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval={minutos}")
    if d.get("error"):
        raise RuntimeError(d["error"])
    k = [x for x in d["result"] if x != "last"][0]
    crudas = [vl.desde_kraken(x) for x in d["result"][k]]
    util, inc = preparar(crudas, minutos, int(time.time()))
    if inc:
        tipos = sorted({i["tipo"] for i in inc})
        print(f"  {par} {minutos} min: incidencias en los datos ({', '.join(tipos)})")
    return util


def demo(par, minutos):
    random.seed(hash((par, minutos)) % 100000)
    p, out = 100.0, []
    t0 = 1_700_000_000 - (1_700_000_000 % (minutos * 60))
    for k in range(720):
        antes = p
        p *= 1 + random.gauss(0.0001, 0.012 * math.sqrt(minutos / 60) ** 0.7)
        out.append(vl.Vela(t0 + k * minutos * 60, antes, max(antes, p), min(antes, p), p, 1.0))
    return out


def cargar_series(es_demo):
    series = []
    for sym, par in PARES:
        for minutos, nom in VELAS:
            try:
                velas_ = demo(sym, minutos) if es_demo else descargar(par, minutos)
                c = [x.c for x in velas_]
                if not es_demo:
                    time.sleep(1.2)
            except Exception as e:
                print(f"  sin datos de {sym} {nom}: {e}")
                continue
            if len(c) >= WARM + 150:
                series.append({"moneda": sym, "vela": nom, "minutos": minutos, "c": Serie(c, [x.ts for x in velas_], [x.o for x in velas_])})
    for s in series:                                    # BTC de la misma duracion de vela, como referencia
        ref = [x for x in series if x["moneda"] == "BTC" and x["minutos"] == s["minutos"]]
        s["c"].ref = ref[0]["c"] if ref else None
        s["c"].ref_idx = alinear(s["c"], s["c"].ref) if ref else None
    return series


# ---------------- examen ----------------
def evaluar(series, fn, opc=None, costes=None):
    """Para cada serie: entrenamiento y examen (con los costes base o con el escenario 'costes'). Devuelve lista de dicts."""
    res = []
    for s in series:
        c, n, esc = s["c"], len(s["c"]), math.sqrt(s["minutos"] / 60)
        corte = WARM + int((n - WARM) * PARTE_ENTRENO)
        r1, o1, h1, _ = simular2(c, WARM, corte, esc, fn, opc, costes)
        r2, o2, h2, dd = simular2(c, corte, n, esc, fn, opc, costes)
        res.append({"train_dif": r1 - h1, "test_res": r2, "test_dif": r2 - h2, "test_ops": o2, "dd": dd})
    return res


def aprueba(r):
    return r["test_res"] > 0 and r["test_dif"] > 0 and r["test_ops"] >= MIN_OPS_EXAMEN


def main():
    es_demo = "--demo" in sys.argv
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
    os.makedirs(out, exist_ok=True)
    series = cargar_series(es_demo)
    if len(series) < 4:
        print("Datos insuficientes: no se actualiza el laboratorio.")
        sys.exit(0)
    todas = variantes()
    filas = []
    for analista, nombre, fn, opc in todas:
        r = evaluar(series, fn, opc)
        ok = sum(aprueba(x) for x in r)
        filas.append({
            "analista": analista, "nombre": nombre,
            "train_dif": sum(x["train_dif"] for x in r) / len(r),
            "test_dif": sum(x["test_dif"] for x in r) / len(r),
            "test_res": sum(x["test_res"] for x in r) / len(r),
            "ops": sum(x["test_ops"] for x in r) / len(r),
            "dd": max(x["dd"] for x in r),
            "ok": ok, "total": len(r),
            "pasa": ok >= math.ceil(FRACCION_SERIES * len(r)) and sum(x["test_dif"] for x in r) > 0,
        })
    probadas = len(filas)
    azar = sum(1 for f in filas if f["pasa"]) / probadas                      # aprobaría cualquiera, elegida al azar
    elegidas = sorted(filas, key=lambda f: f["train_dif"], reverse=True)[:N_CANDIDATAS]
    por_nombre = {nombre: (fn, opc) for _, nombre, fn, opc in todas}
    for f in elegidas:                              # prueba de estres: mismo examen con comision taker 0,80 % y horquilla/deslizamiento x2
        fn, opc = por_nombre[f["nombre"]]
        rs = evaluar(series, fn, opc, costes_mod.ESTRES)
        f["test_dif_estres"] = sum(x["test_dif"] for x in rs) / len(rs)
        f["aguanta_estres"] = f["test_dif_estres"] > 0
    candidatas = [f for f in elegidas if f["pasa"]]
    tasa_cand = len(candidatas) / len(elegidas)
    if not candidatas:
        veredicto = "ninguna"
        txt = "Ninguna de las mejores variantes del entrenamiento aprueba el examen. No hay candidatas esta semana."
    elif tasa_cand > azar + 0.25 and len(candidatas) >= 2:
        veredicto = "posible"
        txt = (f"{len(candidatas)} de {len(elegidas)} variantes elegidas con el entrenamiento aprueban el examen, "
               f"claramente por encima de lo que daría el azar ({azar * 100:.0f} %). Son candidatas para probar en simulación.")
    else:
        veredicto = "ruido"
        txt = (f"{len(candidatas)} de {len(elegidas)} variantes aprueban el examen, pero el azar ya aprobaría el {azar * 100:.0f} % de las variantes. "
               "No se distingue de la casualidad: tomar solo como pista.")
    analistas = {}
    for f in filas:
        a = analistas.setdefault(f["analista"], {"nombre": f["analista"], "probadas": 0, "candidatas": 0})
        a["probadas"] += 1
    for f in candidatas:
        analistas[f["analista"]]["candidatas"] += 1
    fam = {}
    for f in filas:
        d = fam.setdefault(f["analista"], {"n": 0, "dif": 0.0, "pasan": 0, "ops": 0.0})
        d["n"] += 1
        d["dif"] += f["test_dif"]
        d["ops"] += f["ops"]
        d["pasan"] += 1 if f["pasa"] else 0
    datos = {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": "demo" if es_demo else "Kraken",
        "series": [f"{s['moneda']} {s['vela']}" for s in series],
        "probadas": probadas, "tasa_azar": round(azar, 3), "veredicto": veredicto, "texto": txt,
        "criterio": f"examen en el último {int((1 - PARTE_ENTRENO) * 100)} % del historial, ≥{MIN_OPS_EXAMEN} operaciones, "
                    f"gana dinero y supera a comprar y mantener en ≥{int(FRACCION_SERIES * 100)} % de las series",
        "analistas": list(analistas.values()),
        "familias": {n: {"variantes": d["n"], "dif_media_examen": round(d["dif"] / d["n"], 2), "aprueban": d["pasan"]} for n, d in fam.items()},
        "candidatas": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in f.items()} for f in candidatas],
        "mejores_entreno": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in f.items()} for f in elegidas],
    }
    ps.escribir_json(os.path.join(out, "laboratorio.json"), datos, indent=1)
    md = ["# Laboratorio de estrategias", "",
          f"Actualizado: {datos['generado']} · datos: {datos['fuente']} · {len(series)} series ({', '.join(datos['series'])})", "",
          f"**Veredicto: {veredicto.upper()}.** {txt}", "",
          f"Variantes probadas: {probadas}. Criterio: {datos['criterio']}.", "",
          "| Variante | Analista | Dif. entrenamiento (€) | Dif. examen (€) | Dif. examen con costes duros (€) | Series aprobadas | Aprueba |",
          "|---|---|---:|---:|---:|---:|:-:|"]
    for f in elegidas:
        md.append(f"| {f['nombre']} | {f['analista']} | {f['train_dif']:+.2f} | {f['test_dif']:+.2f} | {f['test_dif_estres']:+.2f} | {f['ok']}/{f['total']} | {'✔' if f['pasa'] else '✘'} |")
    md += ["", "«Costes duros» = comisión taker 0,80 % (órdenes a mercado) y horquilla y deslizamiento duplicados. Una variante que solo gana con los costes base es frágil.", "",
           "Resultado medio por familia en el examen (frente a comprar y mantener, tras costes):", "",
           "| Familia | Variantes | Dif. media examen (€) | Operaciones medias | Aprueban |", "|---|---:|---:|---:|---:|"]
    for nom, d in fam.items():
        md.append(f"| {nom} | {d['n']} | {d['dif'] / d['n']:+.2f} | {d['ops'] / d['n']:.0f} | {d['pasan']} |")
    md += ["", "Las candidatas NO operan solas: solo se proponen. Para dudar de ellas: probar tantas variantes hace que algunas "
           "salgan bien por azar, y el historial pasado no garantiza el futuro. Antes de confiar, deben aguantar semanas en simulación.", ""]
    ps.escribir_atomico(os.path.join(out, "laboratorio.md"), "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
