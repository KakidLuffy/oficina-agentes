#!/usr/bin/env python3
"""
SALA ABIERTA (dinero ficticio, no opera en ningún exchange). Reglas en CRITERIOS.md, sección 7.

Simulación aparte de la oficina principal (no la toca): 2 agentes con las ideas «POSIBLE» del laboratorio v2 en velas
de 6 h, que pueden comprar cualquiera de las 12 monedas del laboratorio. Las señales son las funciones de laboratorio.py,
sin retocar. Cada ejecución procesa las velas de 6 h cerradas desde la anterior y guarda todo en datos_sala/.

Uso:
  python sala_abierta.py                    -> precios reales de Coinbase
  python sala_abierta.py --demo 400         -> precios inventados (400 velas), sin internet
  python sala_abierta.py --datos carpeta    -> otra carpeta de datos (para pruebas)
"""
import csv
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

import comparar_estrategias as ce
import laboratorio as lab

START = 10.0                     # euros ficticios por agente
COMPRA = 2.5                     # euros por compra (hasta 4 monedas a la vez)
MAX_POS = 4
FEE = 0.004                      # comisión 0,40 %
SLIP_GRANDE = 0.0005             # deslizamiento 0,05 % en BTC y ETH...
SLIP_OTRAS = 0.003               # ...y 0,3 % en las demás
STOP = START * 0.7               # apagado por riesgo, como en la oficina principal
VELA = 6 * 3600                  # velas de 6 h
MIN_DIAS, MIN_CERRADAS = 90, 30  # CRITERIOS.md 7: no se juzga antes
PARES = lab.PARES                # las 12 monedas del laboratorio, en su orden
AGENTES = [
    ("Sala: Cruce 10/80 + filtro", lab.con_filtro(lab.cruce(10, 80))),
    ("Sala: Ruptura 40/20 + filtro", lab.con_filtro(lab.ruptura(40, 20))),
]
REFERENCIA = "Mantener las 12 a partes iguales"
CAB_OPS = ["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"]


# ---------------- datos ----------------
def velas_coinbase(producto):
    """Últimas 300 velas de 6 h de Coinbase: [(apertura, cierre)] de más antigua a más reciente."""
    d = ce.get_json(f"https://api.exchange.coinbase.com/products/{producto}/candles?granularity={VELA}")
    if isinstance(d, dict):
        raise RuntimeError(d.get("message", d))
    return sorted((int(x[0]), float(x[4])) for x in d)


def velas_demo(n, k, fin):
    random.seed(101 + 17 * k)
    p, out = 100.0 * (k + 1), []
    for i in range(n):
        p *= 1 + random.gauss(0.0004 * (1 if (i // 120) % 2 else -1), 0.02)
        out.append((fin - (n - i) * VELA, p))
    return out


def obtener(demo):
    ahora = int(time.time())
    if demo:
        fin = ahora // VELA * VELA
        return {sym: velas_demo(demo, k, fin) for k, (sym, _) in enumerate(PARES)}, ahora
    velas = {}
    for sym, producto in PARES:
        try:
            velas[sym] = velas_coinbase(producto)
        except Exception as e:
            print(f"{sym}: sin datos esta vez ({e})")
        time.sleep(0.35)
    return velas, ahora


# ---------------- simulación ----------------
def slip(sym):
    return SLIP_GRANDE if sym in ("BTC", "ETH") else SLIP_OTRAS


def equity(a, precios):
    return a["efectivo"] + sum(u * precios[s] for s, u in a["posiciones"].items())


def anotar(ruta, cab, fila):
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(cab)
        w.writerow(fila)


def operar(a, tipo, sym, precio, fecha, motivo, ops_csv):
    if tipo == "COMPRA":
        ejecutado = precio * (1 + slip(sym))
        importe = min(a["efectivo"], COMPRA)
        a["posiciones"][sym] = importe * (1 - FEE) / ejecutado
        a["efectivo"] -= importe
        coste = importe - a["posiciones"][sym] * precio
    else:
        unidades = a["posiciones"].pop(sym)
        ejecutado = precio * (1 - slip(sym))
        importe = unidades * ejecutado * (1 - FEE)
        a["efectivo"] += importe
        coste = unidades * precio - importe
        a["cerradas"] = a.get("cerradas", 0) + 1
    a["operaciones"] += 1
    anotar(ops_csv, CAB_OPS, [fecha, a["nombre"], sym, tipo, round(ejecutado, 6), round(importe, 4), motivo, round(coste, 5)])
    print(f"{a['nombre']}: {tipo} {sym} a {ejecutado:.6g} EUR ({motivo})")


def estado_nuevo(velas, ahora):
    ultimas = {s: [t for t, _ in v if t + VELA <= ahora][-1] for s, v in velas.items() if v}
    precios = {s: v[-1][1] for s, v in velas.items() if v}
    ref = {s: (START / len(precios)) * (1 - FEE) / (p * (1 + slip(s))) for s, p in precios.items()}
    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"inicio": inicio, "ultima_vela": ultimas, "precios": precios, "referencia": ref,
            "agentes": [{"nombre": n, "efectivo": START, "posiciones": {}, "operaciones": 0, "cerradas": 0,
                         "apagado": False, "pico": START, "caida_max": 0.0} for n, _ in AGENTES],
            "ref_pico": START, "ref_caida_max": 0.0}


def paso(estado, velas, ahora, ops_csv):
    decidir = dict(AGENTES)
    series, nuevas = {}, []
    for sym, v in velas.items():
        cer = [(t, c) for t, c in v if t + VELA <= ahora]
        if not cer:
            continue
        series[sym] = lab.Serie([c for _, c in cer], [t for t, _ in cer])
        ult = estado["ultima_vela"].get(sym)
        for i, (t, c) in enumerate(cer):
            if ult is None or t > ult:
                nuevas.append((t, sym, i))
        if ult is None:                                  # moneda que no tenía datos al empezar: solo desde ahora
            nuevas = [x for x in nuevas if x[1] != sym]
            estado["ultima_vela"][sym] = cer[-1][0]
    orden = {s: k for k, (s, _) in enumerate(PARES)}
    precios = estado["precios"]
    for t in sorted({x[0] for x in nuevas}):
        fecha = datetime.fromtimestamp(t + VELA, timezone.utc).isoformat(timespec="minutes")   # al cerrar la vela
        lote = sorted((x for x in nuevas if x[0] == t), key=lambda x: orden[x[1]])
        for _, sym, i in lote:
            precios[sym] = series[sym][i]
            estado["ultima_vela"][sym] = t
        for a in estado["agentes"]:
            if a["apagado"]:
                continue
            fn = decidir[a["nombre"]]
            senales = {sym: fn(series[sym], i, 1.0) for _, sym, i in lote}
            for _, sym, _ in lote:                       # primero se vende...
                if sym in a["posiciones"] and senales[sym] == "s":
                    operar(a, "VENTA", sym, precios[sym], fecha, "señal vendedora", ops_csv)
            for _, sym, _ in lote:                       # ...y luego se compra, por el orden de la lista
                if senales[sym] == "b" and sym not in a["posiciones"]:
                    if len(a["posiciones"]) >= MAX_POS or a["efectivo"] < COMPRA * 0.5:
                        break
                    operar(a, "COMPRA", sym, precios[sym], fecha, "señal compradora", ops_csv)
            if equity(a, precios) < STOP:
                for sym in list(a["posiciones"]):
                    operar(a, "VENTA", sym, precios[sym], fecha, "apagado por riesgo", ops_csv)
                a["apagado"] = True
                print(f"RIESGO: {a['nombre']} apagado (capital bajo {STOP:.0f} €)")
        medir(estado, precios)
    for sym, v in velas.items():                         # precio actual para valorar (la última vela puede seguir abierta)
        if v:
            precios[sym] = v[-1][1]
    medir(estado, precios)


def valor_ref(estado, precios):
    return sum(u * precios[s] for s, u in estado["referencia"].items())


def medir(estado, precios):
    """Caída máxima desde el mejor momento, de cada agente y de la referencia."""
    for a in estado["agentes"]:
        eq = equity(a, precios)
        a["pico"] = max(a["pico"], eq)
        a["caida_max"] = max(a["caida_max"], (a["pico"] - eq) / a["pico"] * 100)
    r = valor_ref(estado, precios)
    estado["ref_pico"] = max(estado["ref_pico"], r)
    estado["ref_caida_max"] = max(estado["ref_caida_max"], (estado["ref_pico"] - r) / estado["ref_pico"] * 100)


def guardar(estado, carpeta):
    precios = estado["precios"]
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    eqs = [equity(a, precios) for a in estado["agentes"]]
    ref = valor_ref(estado, precios)
    anotar(os.path.join(carpeta, "historial.csv"), ["fecha_utc"] + [n for n, _ in AGENTES] + [REFERENCIA],
           [ahora] + [round(e, 4) for e in eqs] + [round(ref, 4)])
    with open(os.path.join(carpeta, "estado.json"), "w") as f:
        json.dump(estado, f, indent=2)
    dias = (datetime.fromisoformat(ahora) - datetime.fromisoformat(estado["inicio"])).total_seconds() / 86400
    l = ["# Sala abierta (dinero ficticio)", "",
         f"Actualizado: {ahora} UTC · en marcha desde {estado['inicio']} ({dias:.1f} días) · reglas: CRITERIOS.md, sección 7",
         "Simulación aparte de la oficina principal. 2 agentes con las ideas «POSIBLE» del laboratorio v2 (velas de 6 h de "
         "Coinbase) que pueden comprar cualquiera de las 12 monedas del laboratorio; 2,50 € por compra, hasta 4 a la vez. "
         f"Costes: comisión {FEE * 100:.2f} % + deslizamiento {SLIP_GRANDE * 100:.2f} % (BTC, ETH) o {SLIP_OTRAS * 100:.1f} % (resto).",
         "", "| Agente | Capital (EUR) | Resultado | Dif. vs referencia | Caída máxima | Operaciones (cerradas) | Estado |",
         "|---|---:|---:|---:|---:|---:|---|"]
    for a, e in zip(estado["agentes"], eqs):
        est = "Apagado por riesgo" if a["apagado"] else (
            "Con " + ", ".join(sorted(a["posiciones"])) if a["posiciones"] else "En efectivo")
        l.append(f"| {a['nombre']} | {e:.2f} | {(e / START - 1) * 100:+.2f} % | {e - ref:+.2f} € | -{a['caida_max']:.2f} % | "
                 f"{a['operaciones']} ({a.get('cerradas', 0)}) | {est} |")
    l.append(f"| {REFERENCIA} (referencia) | {ref:.2f} | {(ref / START - 1) * 100:+.2f} % | 0.00 € | -{estado['ref_caida_max']:.2f} % | 12 | Referencia |")
    l += ["", f"⚠ No se juzga a ningún agente antes de {MIN_DIAS} días y {MIN_CERRADAS} operaciones cerradas. "
          "Es exploratoria: aunque gane, no se convierte en agente principal ni justifica dinero real.",
          "Estos resultados no garantizan beneficios futuros."]
    with open(os.path.join(carpeta, "resumen.md"), "w") as f:
        f.write("\n".join(l) + "\n")
    print("\n".join(l[5:]))


def main():
    demo = int(sys.argv[sys.argv.index("--demo") + 1]) if "--demo" in sys.argv else 0
    carpeta = sys.argv[sys.argv.index("--datos") + 1] if "--datos" in sys.argv else "datos_sala"
    os.makedirs(carpeta, exist_ok=True)
    velas, ahora = obtener(demo)
    if not velas:
        raise SystemExit("Sin datos de ninguna moneda: no se hace nada esta vez.")
    ruta = os.path.join(carpeta, "estado.json")
    if os.path.exists(ruta):
        with open(ruta) as f:
            estado = json.load(f)
    else:
        estado = estado_nuevo(velas, ahora)
        print(f"Primera ejecución: {len(AGENTES)} agentes empiezan con {START} € ficticios cada uno.")
    paso(estado, velas, ahora, os.path.join(carpeta, "operaciones.csv"))
    guardar(estado, carpeta)


if __name__ == "__main__":
    main()
