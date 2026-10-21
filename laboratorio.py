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
import universo_historico as uh
import velas as vl
import walkforward as wf
import persistencia as ps

ce.FEE = 0.004                  # mismos costes que la simulacion en vivo (comision Kraken Pro 0,40 % + deslizamiento 0,05 %)
START, FEE, SLIP = ce.START, ce.FEE, ce.SLIP
WARM = 200                      # velas de calentamiento (el filtro de tendencia usa 200)
ENTRENO_VELAS = 200             # walk-forward: se elige con 200 velas...
PRUEBA_VELAS = 80               # ...y se examina en las 80 siguientes (que no se han usado para elegir); luego se desliza la ventana
MIN_OPS_EXAMEN = 4
FRACCION_SERIES = 0.6           # debe aprobar en al menos el 60 % de las series
N_CANDIDATAS = 12               # cuántas variantes (las mejores en entrenamiento) pasan al examen
PARES = [("BTC", "XBTEUR"), ("ETH", "ETHEUR"), ("SOL", "SOLEUR"), ("XRP", "XRPEUR"), ("ADA", "ADAEUR"), ("DOGE", "DOGEEUR"),
         ("LINK", "LINKEUR"), ("DOT", "DOTEUR"), ("LTC", "LTCEUR"), ("AVAX", "AVAXEUR"), ("ATOM", "ATOMEUR"), ("TRX", "TRXEUR"),
         ("BCH", "BCHEUR"), ("XLM", "XLMEUR"), ("UNI", "UNIEUR"), ("NEAR", "NEAREUR")]
N_TOP = 10                      # universo punto en el tiempo: solo se opera una moneda mientras esta entre las N de mayor volumen (de las PARES)
VENTANA_VOLUMEN_DIAS = 30       # el volumen se mide con los ultimos 30 dias (solo datos hasta cada vela)
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
def simular2(c, ini, fin, s, fn, opc, costes=None, permitido=None):
    """Simulador unico (ejecucion.py): senal con el cierre de la vela i, orden a la apertura de i+1, con comision, horquilla y deslizamiento.
    'costes' (costes.py) permite repetir la prueba con otro escenario (por defecto, el base)."""
    return ej.simular(c, c.o, ini, fin, s, fn, opc, FEE, SLIP, ej.SPREAD, START, costes, permitido)


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
    escala_vol = 10 ** random.uniform(1, 3)               # cada moneda negocia un volumen distinto
    p, out = 100.0, []
    t0 = 1_700_000_000 - (1_700_000_000 % (minutos * 60))
    for k in range(720):
        antes = p
        p *= 1 + random.gauss(0.0001, 0.012 * math.sqrt(minutos / 60) ** 0.7)
        out.append(vl.Vela(t0 + k * minutos * 60, antes, max(antes, p), min(antes, p), p, escala_vol * math.exp(random.gauss(0, 0.5))))
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
            if len(c) >= WARM + ENTRENO_VELAS + PRUEBA_VELAS:
                series.append({"moneda": sym, "vela": nom, "minutos": minutos, "c": Serie(c, [x.ts for x in velas_], [x.o for x in velas_], [x.v * x.c for x in velas_])})
    for minutos in {s["minutos"] for s in series}:      # universo punto en el tiempo, por duracion de vela (ver universo_historico.py)
        grupo = [s for s in series if s["minutos"] == minutos]
        ventana = max(2, int(VENTANA_VOLUMEN_DIAS * 1440 / minutos))
        m = uh.membresia({s["moneda"]: list(zip(s["c"].ts, s["c"].vol)) for s in grupo}, N_TOP, ventana)
        for s in grupo:
            s["miembro"] = m[s["moneda"]]
    for s in series:                                    # BTC de la misma duracion de vela, como referencia
        ref = [x for x in series if x["moneda"] == "BTC" and x["minutos"] == s["minutos"]]
        s["c"].ref = ref[0]["c"] if ref else None
        s["c"].ref_idx = alinear(s["c"], s["c"].ref) if ref else None
    return series


# ---------------- examen walk-forward ----------------
def evaluar_pliegues(series, fn, opc=None, costes=None, pit=True):
    """Walk-forward: para cada serie y cada pliegue (entrenamiento -> prueba siguiente). Devuelve {pliegue: [resultado por serie]}.
    pit=True: solo se compra mientras la moneda esta en el top-N de volumen EN ESA FECHA (universo punto en el tiempo);
    pit=False: lista fija de monedas actuales (la forma antigua, con sesgo de supervivencia)."""
    por_pliegue = {}
    for s in series:
        c, n, esc = s["c"], len(s["c"]), math.sqrt(s["minutos"] / 60)
        perm = (lambda i, m=s["miembro"]: m[i]) if pit and s.get("miembro") else None
        for k, (i0, i1, j0, j1) in enumerate(wf.pliegues(n, WARM, ENTRENO_VELAS, PRUEBA_VELAS)):
            r1, _, h1, _ = simular2(c, i0, i1, esc, fn, opc, costes, perm)
            r2, o2, h2, dd = simular2(c, j0, j1, esc, fn, opc, costes, perm)
            por_pliegue.setdefault(k, []).append({"train_dif": r1 - h1, "test_res": r2, "test_dif": r2 - h2, "test_ops": o2, "dd": dd})
    return por_pliegue


def aprueba(r):
    return r["test_res"] > 0 and r["test_dif"] > 0 and r["test_ops"] >= MIN_OPS_EXAMEN


def _media(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def resumir(por_pliegue):
    """Agrega los resultados por pliegue: medias por pliegue y totales de series aprobadas."""
    ks = sorted(por_pliegue)
    tr = [_media(x["train_dif"] for x in por_pliegue[k]) for k in ks]
    te = [_media(x["test_dif"] for x in por_pliegue[k]) for k in ks]
    todos = [x for k in ks for x in por_pliegue[k]]
    ok = sum(aprueba(x) for x in todos)
    return {"pliegues": len(ks), "fold_train": tr, "fold_test": te, "train_dif": _media(tr), "test_dif": _media(te),
            "test_res": _media(x["test_res"] for x in todos), "ops": _media(x["test_ops"] for x in todos),
            "dd": max((x["dd"] for x in todos), default=0.0), "ok": ok, "total": len(todos),
            "folds_positivos": sum(1 for v in te if v > 0)}


def es_candidata(r):
    """Pasa el examen: gana dinero y supera a mantener en >=60 % de (pliegue, serie), en promedio fuera de muestra y en >=60 % de los pliegues."""
    return (r["total"] > 0 and r["ok"] >= math.ceil(FRACCION_SERIES * r["total"]) and r["test_dif"] > 0
            and r["folds_positivos"] >= math.ceil(FRACCION_SERIES * r["pliegues"]))


def por_regimen_fuera_de_muestra(series, fn, opc, pit=True):
    """Para una variante: dif. (estrategia - mantener) en EUR por regimen de mercado, en el tramo fuera de muestra de cada serie
    (desde el inicio de la primera prueba hasta el final), promediada por serie. Tambien devuelve el reparto de velas por regimen."""
    acum = {r: {"velas": 0, "dif": 0.0, "hold": 0.0} for r in wf.REGIMENES}
    usadas = 0
    for s in series:
        c, n, esc = s["c"], len(s["c"]), math.sqrt(s["minutos"] / 60)
        pl = wf.pliegues(n, WARM, ENTRENO_VELAS, PRUEBA_VELAS)
        if not pl:
            continue
        ini, fin = pl[0][2], pl[-1][3]
        perm = (lambda i, m=s["miembro"]: m[i]) if pit and s.get("miembro") else None
        curva = []
        ej.simular(c, c.o, ini, fin, esc, fn, opc, FEE, SLIP, ej.SPREAD, START, None, perm, curva)
        regs = s.setdefault("regimenes", wf.regimenes(list(c)))
        r = wf.por_regimen(curva, c, ini, regs)
        usadas += 1
        for nombre, d in r.items():
            acum[nombre]["velas"] += d["velas"]
            acum[nombre]["dif"] += (d["estrategia"] - d["hold"]) * START
            acum[nombre]["hold"] += d["hold"] * START
    return {nombre: {"velas": d["velas"], "dif": d["dif"] / usadas if usadas else 0.0, "hold": d["hold"] / usadas if usadas else 0.0}
            for nombre, d in acum.items()}


def calcular(series, todas):
    """Todo el analisis (sin escribir archivos): filas por variante, seleccion por pliegue, sesgo, estres y regimenes."""
    filas = []
    for analista, nombre, fn, opc in todas:
        r = resumir(evaluar_pliegues(series, fn, opc))
        rf = resumir(evaluar_pliegues(series, fn, opc, pit=False))      # lista fija de monedas actuales (sesgo de supervivencia)
        filas.append({"analista": analista, "nombre": nombre, **r, "pasa": es_candidata(r),
                      "test_dif_fija": rf["test_dif"], "pasa_fija": es_candidata(rf)})
    probadas = len(filas)
    npl = max((f["pliegues"] for f in filas), default=0)
    # Seleccion por pliegue: se elige con el entrenamiento del pliegue y se mira que paso en SU prueba (fuera de muestra)
    sel_oos, todas_oos, veces = [], [], {f["nombre"]: 0 for f in filas}
    for k in range(npl):
        validas = [f for f in filas if len(f["fold_train"]) > k]
        top = sorted(validas, key=lambda f: f["fold_train"][k], reverse=True)[:N_CANDIDATAS]
        for f in top:
            veces[f["nombre"]] += 1
        sel_oos.append(_media(f["fold_test"][k] for f in top))
        todas_oos.append(_media(f["fold_test"][k] for f in validas))
    for f in filas:
        f["veces_elegida"] = veces[f["nombre"]]
    metodo = {"pliegues": npl, "oos_seleccion": _media(sel_oos), "oos_todas": _media(todas_oos),
              "ventaja": _media(sel_oos) - _media(todas_oos), "por_pliegue_seleccion": [round(x, 3) for x in sel_oos],
              "por_pliegue_todas": [round(x, 3) for x in todas_oos]}
    sesgo = {"dif_pit": _media(f["test_dif"] for f in filas), "dif_fija": _media(f["test_dif_fija"] for f in filas),
             "pasan_pit": sum(1 for f in filas if f["pasa"]), "pasan_fija": sum(1 for f in filas if f["pasa_fija"])}
    azar = sum(1 for f in filas if f["pasa"]) / probadas if probadas else 0.0       # aprobaria cualquiera, elegida al azar
    elegidas = sorted(filas, key=lambda f: f["train_dif"], reverse=True)[:N_CANDIDATAS]
    por_nombre = {nombre: (fn, opc) for _, nombre, fn, opc in todas}
    for f in elegidas:
        fn, opc = por_nombre[f["nombre"]]
        rs = resumir(evaluar_pliegues(series, fn, opc, costes_mod.ESTRES))      # estres: comision taker 0,80 % y horquilla/deslizamiento x2
        f["test_dif_estres"] = rs["test_dif"]
        f["aguanta_estres"] = rs["test_dif"] > 0
        f["regimenes"] = por_regimen_fuera_de_muestra(series, fn, opc)
    return {"filas": filas, "elegidas": elegidas, "probadas": probadas, "azar": azar, "sesgo": sesgo, "metodo": metodo}


def veredicto_de(candidatas, elegidas, azar):
    tasa = len(candidatas) / len(elegidas) if elegidas else 0.0
    if not candidatas:
        return "ninguna", "Ninguna de las mejores variantes del entrenamiento aprueba el examen walk-forward. No hay candidatas esta semana."
    if tasa > azar + 0.25 and len(candidatas) >= 2:
        return "posible", (f"{len(candidatas)} de {len(elegidas)} variantes elegidas con el entrenamiento aprueban el examen, "
                           f"claramente por encima de lo que daria el azar ({azar * 100:.0f} %). Son candidatas para probar en simulacion.")
    return "ruido", (f"{len(candidatas)} de {len(elegidas)} variantes aprueban el examen, pero el azar ya aprobaria el {azar * 100:.0f} % de las variantes. "
                     "No se distingue de la casualidad: tomar solo como pista.")


def main():
    es_demo = "--demo" in sys.argv
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "."
    os.makedirs(out, exist_ok=True)
    series = cargar_series(es_demo)
    if len(series) < 4:
        print("Datos insuficientes: no se actualiza el laboratorio.")
        sys.exit(0)
    todas = variantes()
    calc = calcular(series, todas)
    filas, elegidas, probadas, azar, sesgo, metodo = (calc[k] for k in ("filas", "elegidas", "probadas", "azar", "sesgo", "metodo"))
    candidatas = [f for f in elegidas if f["pasa"]]
    veredicto, txt = veredicto_de(candidatas, elegidas, azar)
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
    plano = lambda f: {k: (round(v, 2) if isinstance(v, float) else v) for k, v in f.items() if k not in ("fold_train", "fold_test", "regimenes")}
    datos = {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": "demo" if es_demo else "Kraken",
        "series": [f"{s['moneda']} {s['vela']}" for s in series],
        "walk_forward": {"entreno_velas": ENTRENO_VELAS, "prueba_velas": PRUEBA_VELAS, **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in metodo.items()}},
        "sesgo_supervivencia": {k: round(v, 3) if isinstance(v, float) else v for k, v in sesgo.items()},
        "universo": {"monedas": [p for p, _ in PARES], "top_n": N_TOP, "ventana_dias": VENTANA_VOLUMEN_DIAS},
        "probadas": probadas, "tasa_azar": round(azar, 3), "veredicto": veredicto, "texto": txt,
        "criterio": f"walk-forward ({metodo['pliegues']} pliegues: se elige con {ENTRENO_VELAS} velas y se examina en las {PRUEBA_VELAS} siguientes), "
                    f"≥{MIN_OPS_EXAMEN} operaciones, gana dinero y supera a comprar y mantener en ≥{int(FRACCION_SERIES * 100)} % de las pruebas y de los pliegues",
        "analistas": list(analistas.values()),
        "familias": {n: {"variantes": d["n"], "dif_media_examen": round(d["dif"] / d["n"], 2), "aprueban": d["pasan"]} for n, d in fam.items()},
        "candidatas": [plano(f) for f in candidatas],
        "mejores_entreno": [plano(f) for f in elegidas],
        "regimenes": {f["nombre"]: {r: {k: round(v, 3) for k, v in d.items()} for r, d in f["regimenes"].items()} for f in elegidas},
    }
    ps.escribir_json(os.path.join(out, "laboratorio.json"), datos, indent=1)
    md = ["# Laboratorio de estrategias", "",
          f"Actualizado: {datos['generado']} · datos: {datos['fuente']} · {len(series)} series ({', '.join(datos['series'])})", "",
          f"**Veredicto: {veredicto.upper()}.** {txt}", "",
          f"Variantes probadas: {probadas}. Criterio: {datos['criterio']}.", "",
          "| Variante | Analista | Dif. entrenamiento (€) | Dif. fuera de muestra (€) | Dif. con costes duros (€) | Pruebas aprobadas | Pliegues positivos | Aprueba |",
          "|---|---|---:|---:|---:|---:|---:|:-:|"]
    for f in elegidas:
        md.append(f"| {f['nombre']} | {f['analista']} | {f['train_dif']:+.2f} | {f['test_dif']:+.2f} | {f['test_dif_estres']:+.2f} | "
                  f"{f['ok']}/{f['total']} | {f['folds_positivos']}/{f['pliegues']} | {'✔' if f['pasa'] else '✘'} |")
    md += ["", "## ¿Sirve elegir lo mejor del pasado? (walk-forward)", "",
           f"Se repite {metodo['pliegues']} veces: se elige con {ENTRENO_VELAS} velas y se mide en las {PRUEBA_VELAS} siguientes. "
           f"Las {N_CANDIDATAS} variantes elegidas en cada pliegue rindieron fuera de muestra **{metodo['oos_seleccion']:+.2f} €** de media frente a comprar y mantener, "
           f"y el conjunto de las {probadas} variantes **{metodo['oos_todas']:+.2f} €**. Ventaja de elegir: **{metodo['ventaja']:+.2f} €**. "
           "Si la ventaja es cercana a cero o negativa, escoger por el pasado no aporta nada.", "",
           "| Pliegue | Elegidas (€) | Todas las variantes (€) |", "|---:|---:|---:|"]
    for k, (a, b) in enumerate(zip(metodo["por_pliegue_seleccion"], metodo["por_pliegue_todas"]), 1):
        md.append(f"| {k} | {a:+.2f} | {b:+.2f} |")
    md += ["", "## Resultados por régimen de mercado (fuera de muestra)", "",
           "Régimen = tendencia de las últimas 60 velas medida en unidades de su propia volatilidad (alcista, bajista o lateral). "
           "Cada celda: diferencia frente a comprar y mantener en € (media por serie) y, entre paréntesis, nº de velas de ese régimen.", "",
           "| Variante | Alcista | Bajista | Lateral |", "|---|---:|---:|---:|"]
    for f in elegidas:
        r = f["regimenes"]
        md.append(f"| {f['nombre']} | " + " | ".join(f"{r[x]['dif']:+.2f} ({r[x]['velas']})" for x in wf.REGIMENES) + " |")
    md += ["", "Una estrategia que solo gana en un régimen (p. ej. solo en tendencia alcista) puede dejar de funcionar cuando cambie el mercado; "
           "con la muestra disponible no se puede saber si los regímenes futuros se parecerán a estos.", ""]
    md += ["## Sesgo de supervivencia", "",
           f"Se prueban solo monedas que existen hoy ({len(PARES)} en total), lo que favorece a las que sobrevivieron. Para reducirlo, cada moneda solo se opera "
           f"mientras estaba entre las {N_TOP} de mayor volumen (últimos {VENTANA_VOLUMEN_DIAS} días, usando solo datos hasta esa fecha). "
           f"Resultado medio de las {probadas} variantes fuera de muestra: **{sesgo['dif_pit']:+.2f} €** con universo punto en el tiempo frente a "
           f"**{sesgo['dif_fija']:+.2f} €** con la lista fija de hoy ({sesgo['pasan_pit']} frente a {sesgo['pasan_fija']} variantes que aprueban). "
           "Kraken no publica el historial de monedas ya deslistadas, así que las que murieron **no se pueden incluir**: el sesgo se reduce, no se elimina. "
           "Tómese todo resultado favorable como optimista.", ""]
    md += ["«Costes duros» = comisión taker 0,80 % (órdenes a mercado) y horquilla y deslizamiento duplicados. Una variante que solo gana con los costes base es frágil.", "",
           "Resultado medio por familia fuera de muestra (frente a comprar y mantener, tras costes):", "",
           "| Familia | Variantes | Dif. media (€) | Operaciones medias | Aprueban |", "|---|---:|---:|---:|---:|"]
    for nom, d in fam.items():
        md.append(f"| {nom} | {d['n']} | {d['dif'] / d['n']:+.2f} | {d['ops'] / d['n']:.0f} | {d['pasan']} |")
    md += ["", "Las candidatas NO operan solas: solo se proponen. Para dudar de ellas: probar tantas variantes hace que algunas "
           "salgan bien por azar, y el historial pasado no garantiza el futuro. Antes de confiar, deben aguantar semanas en simulación.", ""]
    ps.escribir_atomico(os.path.join(out, "laboratorio.md"), "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
