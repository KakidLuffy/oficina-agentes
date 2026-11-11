"""Prueba historica de "Tendencia H1 (diaria)" con las MISMAS reglas que el agente en vivo (agentes_nube.paso_h1).

Criterios fijados de antemano en CRITERIOS.md (registrados antes de ejecutar esta prueba). Dinero FICTICIO.

Uso:  python backtest_h1.py --out datos           (descarga velas diarias de Coinbase; en GitHub Actions)
      python backtest_h1.py --demo --out /tmp/x   (precios inventados, para probar el codigo sin internet)
"""
import json
import os
import random
import sys
import time
import urllib.request
from datetime import datetime, timezone

# --- reglas (copiadas de agentes_nube.py; test_agentes comprueba que coinciden) ---
START = 10.0
FEE, SLIP = 0.004, 0.0005
H1_SMA = 100
H1_MAX_ACTIVO = 0.25
H1_RIESGO_OP = 0.02
H1_PARADA_MES = 0.06
H1_PARADA_PICO = 0.15
PARES = {"XBTEUR": "BTC-EUR", "ETHEUR": "ETH-EUR"}
VECINAS = (50, 150, 200)            # solo para ver si el resultado es robusto, NUNCA para elegir otra media


# ---------------- datos ----------------
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "oficina-agentes-backtest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def diarias_coinbase(producto):
    """Todas las velas diarias disponibles: {dia_ts: (apertura, minimo, cierre)}. Coinbase da 300 por peticion."""
    fin = int(time.time()) // 86400 * 86400            # solo dias ya cerrados
    velas, vacias = {}, 0
    while vacias < 2 and fin > 1_420_070_400:          # hasta 2015
        ini = fin - 300 * 86400
        d = get_json(f"https://api.exchange.coinbase.com/products/{producto}/candles?granularity=86400"
                     f"&start={datetime.fromtimestamp(ini, timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
                     f"&end={datetime.fromtimestamp(fin - 1, timezone.utc):%Y-%m-%dT%H:%M:%SZ}")
        if not d:
            vacias += 1
        for t, lo, hi, op, cl, vol in d:
            if int(t) + 86400 <= int(time.time()):
                velas[int(t)] = (float(op), float(lo), float(cl))
        fin = ini
        time.sleep(0.4)
    return velas


def diarias_demo(n=2600):
    random.seed(11)
    out = {}
    for k, par in enumerate(PARES):
        p, v = 3000.0 * (k + 1), {}
        for i in range(n):
            t = 1_500_000_000 // 86400 * 86400 + i * 86400
            op = p
            p *= 1 + random.gauss(0.0006, 0.035 + 0.01 * k)
            v[t] = (op, min(op, p) * (1 - abs(random.gauss(0, 0.015))), p)
        out[par] = v
    return out


# ---------------- simulacion ----------------
def simular(datos, sma_n=H1_SMA, fechas=None, parada_pico=H1_PARADA_PICO):
    """Recorre los dias comunes en orden. Devuelve curva de capital, operaciones y si se apago."""
    dias = fechas or sorted(set.intersection(*(set(v) for v in datos.values())))
    cierres = {p: [] for p in datos}
    ef, pos, entrada, stop = START, {}, {}, {}
    pico, mes, eq_mes, apagado = START, None, START, None
    curva, ops, costes = [], [], 0.0
    importe = START * H1_MAX_ACTIVO
    riesgo_pct = START * H1_RIESGO_OP / importe        # 0,20 EUR sobre 2,50 EUR -> stop al -8 %

    def vender(par, precio, t, motivo):
        nonlocal ef, costes
        u = pos.pop(par)
        ejec = precio * (1 - SLIP)
        cobro = u * ejec * (1 - FEE)
        costes += u * precio - cobro
        ef += cobro
        ops.append({"t": t, "par": par, "tipo": "VENTA", "precio": ejec, "eur": cobro, "motivo": motivo,
                    "ganancia": cobro - entrada.pop(par)})
        stop.pop(par, None)

    for t in dias:
        o = {p: datos[p][t] for p in datos}            # (apertura, minimo, cierre)
        for p in datos:
            cierres[p].append(o[p][2])
        if apagado is None:
            for par in list(pos):                      # 1) stop: se mira el minimo del dia
                if o[par][1] <= stop[par]:
                    vender(par, min(stop[par], o[par][0]), t, "stop")
            eq = ef + sum(u * o[p][2] for p, u in pos.items())
            pico = max(pico, eq)
            if parada_pico and eq <= pico * (1 - parada_pico):   # 2) -15 % desde el maximo: se apaga
                for par in list(pos):
                    vender(par, o[par][2], t, "apagado -15 %")
                apagado = t
            else:
                m = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m")
                if m != mes:
                    mes, eq_mes = m, eq
                pausa = eq <= eq_mes * (1 - H1_PARADA_MES)   # 3) mes con -6 %
                for par in PARES:                      # 4) la regla, al cierre del dia
                    c = cierres[par]
                    if len(c) < sma_n + 1:
                        continue
                    sma = sum(c[-sma_n:]) / sma_n
                    if par in pos and c[-1] < sma:
                        vender(par, c[-1], t, "cierre bajo la media")
                    elif par not in pos and c[-1] > sma and not pausa and ef >= importe * 0.5:
                        imp = min(ef, importe)
                        ejec = c[-1] * (1 + SLIP)
                        pos[par] = imp * (1 - FEE) / ejec
                        costes += imp - pos[par] * c[-1]
                        ef -= imp
                        entrada[par] = imp
                        stop[par] = ejec * (1 - riesgo_pct)
                        ops.append({"t": t, "par": par, "tipo": "COMPRA", "precio": ejec, "eur": imp})
        eq = ef + sum(u * o[p][2] for p, u in pos.items())
        curva.append((t, eq, len(pos)))
    return {"curva": curva, "ops": ops, "costes": costes, "apagado": apagado}


def cesta(datos, dias, fraccion):
    """Compra el primer dia `fraccion` del capital, a partes iguales en BTC y ETH, y no toca nada."""
    t0 = dias[0]
    parte = START * fraccion / len(datos)
    u = {p: parte * (1 - FEE) / (datos[p][t0][2] * (1 + SLIP)) for p in datos}
    ef = START - START * fraccion
    return [(t, ef + sum(u[p] * datos[p][t][2] for p in datos)) for t in dias]


# ---------------- metricas ----------------
def caida_max(valores):
    pico, peor = valores[0], 0.0
    for v in valores:
        pico = max(pico, v)
        peor = min(peor, v / pico - 1)
    return peor


def por_anio(curva):
    """Rentabilidad de cada ano natural COMPLETO (del ultimo dia del ano anterior al ultimo de este)."""
    fin_anio = {}
    for t, v, *_ in curva:
        fin_anio[datetime.fromtimestamp(t, timezone.utc).year] = (t, v)
    anios = sorted(fin_anio)
    res = {}
    for a, b in zip(anios, anios[1:]):
        tb = datetime.fromtimestamp(fin_anio[b][0], timezone.utc)
        if tb.month == 12 and tb.day == 31:
            res[b] = fin_anio[b][1] / fin_anio[a][1] - 1
    return res


def evaluar(datos):
    dias_com = sorted(set.intersection(*(set(v) for v in datos.values())))
    inicio = dias_com[H1_SMA]                           # primer dia con media de 100 calculable: aqui empieza todo
    dias = [t for t in dias_com if t >= inicio]
    warm = [t for t in dias_com if t < inicio]

    def correr(n, parada_pico=H1_PARADA_PICO):
        r = simular(datos, n, warm[-n:] + dias if n <= len(warm) else dias_com, parada_pico)
        r["curva"] = [c for c in r["curva"] if c[0] >= inicio]
        corte = r["apagado"] or dias[-1]               # si se apaga, la comparacion termina ese dia
        r["curva_cmp"] = [c for c in r["curva"] if c[0] <= corte]
        return r

    h1 = correr(H1_SMA)
    corte = h1["curva_cmp"][-1][0]
    d_cmp = [t for t in dias if t <= corte]
    c50, c100 = cesta(datos, d_cmp, 0.5), cesta(datos, d_cmp, 1.0)
    btc = [(t, START * (1 - FEE) * datos["XBTEUR"][t][2] / (datos["XBTEUR"][d_cmp[0]][2] * (1 + SLIP))) for t in d_cmp]

    def resumen(curva):
        vals = [v for _, v, *_ in curva]
        return {"final": vals[-1], "rent": vals[-1] / START - 1, "caida_max": caida_max(vals), "anios": por_anio(curva)}

    R = {"H1": resumen(h1["curva_cmp"]), "Cesta 50 %": resumen(c50), "Cesta 100 %": resumen(c100),
         "Solo BTC 100 %": resumen(btc)}
    cerr = [o for o in h1["ops"] if o["tipo"] == "VENTA" and o["t"] <= corte]
    R["H1"].update({"operaciones": len([o for o in h1["ops"] if o["t"] <= corte]), "cerradas": len(cerr),
                    "ganadoras": sum(o["ganancia"] > 0 for o in cerr), "costes": h1["costes"],
                    "stops": sum(o["motivo"] == "stop" for o in cerr),
                    "invertido_pct": sum(c[2] > 0 for c in h1["curva_cmp"]) / len(h1["curva_cmp"]),
                    "apagado": h1["apagado"]})
    anios_h1, anios_c = R["H1"]["anios"], R["Cesta 50 %"]["anios"]
    comunes = sorted(set(anios_h1) & set(anios_c))
    gana = [a for a in comunes if anios_h1[a] > anios_c[a]]
    c1 = R["H1"]["rent"] > R["Cesta 50 %"]["rent"]
    c2 = bool(comunes) and len(gana) >= len(comunes) / 2
    c3 = R["H1"]["caida_max"] > R["Cesta 50 %"]["caida_max"]     # caidas negativas: mayor = menos profunda
    vec = {}
    for n in VECINAS:
        r = correr(n)
        t_fin = r["curva_cmp"][-1][0]
        ref = cesta(datos, [t for t in dias if t <= t_fin], 0.5)
        vec[n] = {"rent": r["curva_cmp"][-1][1] / START - 1, "cesta50": ref[-1][1] / START - 1,
                  "supera": r["curva_cmp"][-1][1] > ref[-1][1], "apagado": r["apagado"]}
    robusto = sum(v["supera"] for v in vec.values()) >= 2
    sin = correr(H1_SMA, 0)                             # SOLO INFORMATIVO: que habria pasado sin la regla del -15 %
    c50_todo = cesta(datos, dias, 0.5)
    sin_apagado = {"rent": sin["curva"][-1][1] / START - 1, "caida_max": caida_max([c[1] for c in sin["curva"]]),
                   "cesta50": c50_todo[-1][1] / START - 1, "cesta50_caida": caida_max([v for _, v in c50_todo])}
    return {"inicio": inicio, "fin": dias[-1], "corte": corte, "R": R, "anios_comunes": comunes, "anios_gana": gana,
            "c1": c1, "c2": c2, "c3": c3, "robusto": robusto, "vecinas": vec,
            "pasa": c1 and c2 and c3 and robusto, "sin_apagado": sin_apagado}


def fecha(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def informe(ev, fuente):
    R = ev["R"]
    si = lambda b: "SÍ" if b else "NO"
    L = ["# Prueba histórica de «Tendencia H1 (diaria)»", "",
         f"Generado: {datetime.now(timezone.utc).isoformat(timespec='minutes')} UTC · Datos: {fuente} · "
         f"Periodo: {fecha(ev['inicio'])} a {fecha(ev['fin'])}"
         + (f" · **H1 se apagó el {fecha(ev['corte'])}** (regla −15 %): la comparación termina ese día" if R["H1"]["apagado"] else ""),
         "", "Mismas reglas y costes que el agente en vivo. Criterios fijados de antemano en `CRITERIOS.md`. Dinero ficticio.", "",
         f"## Veredicto: **{'PASA' if ev['pasa'] else 'NO PASA'}**", "",
         f"1. ¿Rentabilidad total mayor que la cesta al 50 %? **{si(ev['c1'])}** "
         f"({R['H1']['rent'] * 100:+.1f} % frente a {R['Cesta 50 %']['rent'] * 100:+.1f} %)",
         f"2. ¿Gana a la cesta al 50 % en al menos la mitad de los años completos? **{si(ev['c2'])}** "
         f"({len(ev['anios_gana'])} de {len(ev['anios_comunes'])})",
         f"3. ¿Caída máxima menor que la de la cesta al 50 %? **{si(ev['c3'])}** "
         f"({R['H1']['caida_max'] * 100:.1f} % frente a {R['Cesta 50 %']['caida_max'] * 100:.1f} %)",
         f"4. ¿Robusto (al menos 2 de las medias 50/150/200 también superan a la cesta al 50 %)? **{si(ev['robusto'])}**",
         "", "## Resultado", "",
         "| | Capital final (EUR) | Rentabilidad | Caída máxima |", "|---|---:|---:|---:|"]
    for k, v in R.items():
        L.append(f"| {k} | {v['final']:.2f} | {v['rent'] * 100:+.1f} % | {v['caida_max'] * 100:.1f} % |")
    h = R["H1"]
    L += ["", f"H1: {h['operaciones']} operaciones, {h['cerradas']} cerradas, {h['ganadoras']} ganadoras "
          f"({(h['ganadoras'] / h['cerradas'] * 100) if h['cerradas'] else 0:.0f} %), {h['stops']} por stop, "
          f"costes {h['costes']:.2f} EUR, con alguna posición abierta el {h['invertido_pct'] * 100:.0f} % de los días.",
          "", "## Por año natural completo", "", "| Año | H1 | Cesta 50 % | Cesta 100 % | Solo BTC |", "|---|---:|---:|---:|---:|"]
    for a in ev["anios_comunes"]:
        L.append(f"| {a} | {R['H1']['anios'][a] * 100:+.1f} % | {R['Cesta 50 %']['anios'][a] * 100:+.1f} % | "
                 f"{R['Cesta 100 %']['anios'].get(a, 0) * 100:+.1f} % | {R['Solo BTC 100 %']['anios'].get(a, 0) * 100:+.1f} % |")
    L += ["", "## Robustez (solo informativo: no se elige otra media)", "", "| Media | H1 | Cesta 50 % | ¿Supera? |", "|---:|---:|---:|---|"]
    for n, v in ev["vecinas"].items():
        L.append(f"| {n} días | {v['rent'] * 100:+.1f} % | {v['cesta50'] * 100:+.1f} % | {si(v['supera'])}"
                 + (f" (apagada el {fecha(v['apagado'])})" if v["apagado"] else "") + " |")
    s = ev["sin_apagado"]
    L += ["", f"Solo informativo (no cuenta para el veredicto): sin la regla del −15 %, en todo el periodo H1 habría hecho "
          f"{s['rent'] * 100:+.1f} % (caída máx. {s['caida_max'] * 100:.1f} %) frente a {s['cesta50'] * 100:+.1f} % "
          f"(caída máx. {s['cesta50_caida'] * 100:.1f} %) de la cesta al 50 %."]
    L += ["", "Limitaciones: el stop se comprueba con el mínimo diario (en vivo, con el precio de cada ronda); las compras y "
          "ventas se hacen al cierre del día; el pasado no garantiza el futuro, y las medias móviles en cripto llevan años "
          "estudiándose, así que la regla pudo elegirse sabiendo que funcionó."]
    return "\n".join(L) + "\n"


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "datos"
    if "--demo" in sys.argv:
        datos, fuente = diarias_demo(), "precios inventados (demo)"
    else:
        datos, fuente = {p: diarias_coinbase(prod) for p, prod in PARES.items()}, "Coinbase (BTC-EUR, ETH-EUR, velas diarias)"
        for p, v in datos.items():
            print(f"{p}: {len(v)} velas diarias desde {fecha(min(v))}")
    ev = evaluar(datos)
    os.makedirs(out, exist_ok=True)
    texto = informe(ev, fuente)
    with open(os.path.join(out, "backtest_h1.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    with open(os.path.join(out, "backtest_h1.json"), "w") as f:
        json.dump({k: v for k, v in ev.items()}, f, indent=1, default=str)
    print(texto)


if __name__ == "__main__":
    main()
