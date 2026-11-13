#!/usr/bin/env python3
"""
SALA ABIERTA (dinero ficticio, no opera en ningún exchange). Reglas en CRITERIOS.md, secciones 7 y 7.1.

Simulación aparte de la oficina principal (no la toca): 2 agentes con las ideas «POSIBLE» del laboratorio v2 que pueden
comprar TODAS las monedas de la oficina (las 20 de mayor volumen contra el euro en Kraken, más BTC y ETH). Las señales
son las funciones de laboratorio.py, sin retocar, sobre velas de 4 h de Kraken. Cada ejecución procesa las velas
cerradas desde la anterior y guarda todo en datos_sala/, con el mismo formato que datos/ para que el panel lo muestre.

Uso:
  python sala_abierta.py                    -> precios reales de Kraken
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

import agentes_nube as of        # oficina principal: lista de monedas, llamadas a Kraken y costes (solo se LEE)
import laboratorio as lab

START = 10.0                     # euros ficticios por agente
COMPRA = 2.5                     # euros por compra (hasta 4 monedas a la vez)
MAX_POS = 4
FEE = of.FEE                     # comisión 0,40 %, como la oficina principal
SLIP, SLIP_POCO, VOLUMEN_ALTO = of.SLIP, of.SLIP_POCO_VOLUMEN, of.VOLUMEN_ALTO
STOP = START * 0.7               # apagado por riesgo, como en la oficina principal
VELA = 4 * 3600                  # velas de 4 h (Kraken no da 6 h; ver CRITERIOS 7.1)
MIN_DIAS, MIN_CERRADAS = 90, 30  # CRITERIOS 7: no se juzga antes
VERSION = "sala-7.1"
BTC = "XBTEUR"
AGENTES = [
    ("Sala: Cruce 10/80 + filtro", lab.con_filtro(lab.cruce(10, 80))),
    ("Sala: Ruptura 40/20 + filtro", lab.con_filtro(lab.ruptura(40, 20))),
]
REF_BTC = "Comprar y mantener"            # mismos nombres de columna que la oficina principal (los entiende el panel)
REF_CESTA = "Comprar y mantener (cesta)"
CAB_OPS = ["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"]


# ---------------- datos ----------------
def velas_kraken(par):
    res = of.kraken(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval={VELA // 60}")
    clave = [k for k in res if k != "last"][0]
    return [(int(v[0]), float(v[4])) for v in res[clave]]


def velas_demo(n, k, fin):
    random.seed(101 + 17 * k)
    p, out = 100.0 * (k + 1), []
    for i in range(n):
        p *= 1 + random.gauss(0.0004 * (1 if (i // 120) % 2 else -1), 0.02)
        out.append((fin - (n - i) * VELA, p))
    return out


def obtener(demo, tenidas=()):
    """Devuelve (velas {par: [(apertura, cierre)]}, volúmenes {par: EUR}, orden [pares], ahora)."""
    ahora = int(time.time())
    if demo:
        fin = ahora // VELA * VELA
        nombres = [BTC, "ETHEUR"] + [f"DEMO{k}EUR" for k in range(2, 20)]
        vol = {p: (500_000 if k % 3 else 20_000) for k, p in enumerate(nombres)}
        return {p: velas_demo(demo, k, fin) for k, p in enumerate(nombres)}, vol, nombres, ahora
    uni = of.universo_kraken()
    vol = dict(uni)
    orden = [p for p, _ in uni] + [p for p in tenidas if p not in vol]
    velas = {}
    for par in orden:
        try:
            velas[par] = velas_kraken(par)
        except Exception as e:
            print(f"{par}: sin datos esta vez ({e})")
        time.sleep(of.PAUSA_API)
    return velas, vol, [p for p in orden if p in velas], ahora


# ---------------- simulación ----------------
def slip(par, volumenes):
    return SLIP if par == BTC or volumenes.get(par, 0) >= VOLUMEN_ALTO else max(SLIP, SLIP_POCO)


def equity(a, precios):
    return a["efectivo"] + sum(u * precios[s] for s, u in a["posiciones"].items())


def anotar(ruta, cab, fila):
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(cab)
        if fila is not None:
            w.writerow(fila)


def operar(a, tipo, par, precio, fecha, motivo, ops_csv, volumenes):
    sl = slip(par, volumenes)
    if tipo == "COMPRA":
        ejecutado = precio * (1 + sl)
        importe = min(a["efectivo"], COMPRA)
        a["posiciones"][par] = importe * (1 - FEE) / ejecutado
        a["efectivo"] -= importe
        coste = importe - a["posiciones"][par] * precio
    else:
        unidades = a["posiciones"].pop(par)
        ejecutado = precio * (1 - sl)
        importe = unidades * ejecutado * (1 - FEE)
        a["efectivo"] += importe
        coste = unidades * precio - importe
        a["cerradas"] = a.get("cerradas", 0) + 1
    a["operaciones"] += 1
    anotar(ops_csv, CAB_OPS, [fecha, a["nombre"], par, tipo, round(ejecutado, 6), round(importe, 4), motivo, round(coste, 5)])
    print(f"{a['nombre']}: {tipo} {par} a {ejecutado:.6g} EUR ({motivo})")


def estado_nuevo(velas, volumenes, ahora):
    ultimas = {p: [t for t, _ in v if t + VELA <= ahora][-1] for p, v in velas.items() if v}
    precios = {p: v[-1][1] for p, v in velas.items() if v}
    cesta = {p: (START / len(precios)) * (1 - FEE) / (x * (1 + slip(p, volumenes))) for p, x in precios.items()}
    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"version": VERSION, "capital_inicial": START, "fee": FEE, "slip": SLIP, "min_dias": MIN_DIAS,
            "min_cerradas": MIN_CERRADAS, "inicio": inicio, "precio_inicio": precios[BTC], "ultima_vela": ultimas,
            "precios": precios, "cesta": cesta,
            "agentes": [{"nombre": n, "efectivo": START, "posiciones": {}, "operaciones": 0, "cerradas": 0,
                         "apagado": False, "inicio": inicio, "precio_inicio": precios[BTC]} for n, _ in AGENTES]}


def apagar_si_toca(a, precios, fecha, ops_csv, volumenes):
    if not a["apagado"] and equity(a, precios) < STOP:
        for par in list(a["posiciones"]):
            operar(a, "VENTA", par, precios[par], fecha, "apagado por riesgo", ops_csv, volumenes)
        a["apagado"] = True
        print(f"RIESGO: {a['nombre']} apagado (capital bajo {STOP:.0f} €)")


def paso(estado, velas, volumenes, orden, ahora, ops_csv):
    decidir = dict(AGENTES)
    series, nuevas = {}, []
    for par, v in velas.items():
        cer = [(t, c) for t, c in v if t + VELA <= ahora]
        if not cer:
            continue
        series[par] = lab.Serie([c for _, c in cer], [t for t, _ in cer])
        ult = estado["ultima_vela"].get(par)
        if ult is None:                                  # moneda nueva en la lista: solo cuenta desde ahora
            estado["ultima_vela"][par] = cer[-1][0]
            continue
        nuevas += [(t, par, i) for i, (t, _) in enumerate(cer) if t > ult]
    rango = {p: k for k, p in enumerate(orden)}
    precios = estado["precios"]
    for t in sorted({x[0] for x in nuevas}):
        fecha = datetime.fromtimestamp(t + VELA, timezone.utc).isoformat(timespec="minutes")   # al cerrar la vela
        lote = sorted((x for x in nuevas if x[0] == t), key=lambda x: rango.get(x[1], 10 ** 6))
        for _, par, i in lote:
            precios[par] = series[par][i]
            estado["ultima_vela"][par] = t
        for a in estado["agentes"]:
            if a["apagado"]:
                continue
            fn = decidir[a["nombre"]]
            senales = {par: fn(series[par], i, 1.0) for _, par, i in lote}
            for _, par, _ in lote:                       # primero se vende...
                if par in a["posiciones"] and senales[par] == "s":
                    operar(a, "VENTA", par, precios[par], fecha, "señal vendedora", ops_csv, volumenes)
            for _, par, _ in lote:                       # ...y luego se compra, por orden de volumen
                if senales[par] == "b" and par not in a["posiciones"]:
                    if len(a["posiciones"]) >= MAX_POS or a["efectivo"] < COMPRA * 0.5:
                        break
                    operar(a, "COMPRA", par, precios[par], fecha, "señal compradora", ops_csv, volumenes)
            apagar_si_toca(a, precios, fecha, ops_csv, volumenes)
    for par, v in velas.items():                         # precio actual (la última vela puede seguir abierta)
        if v:
            precios[par] = v[-1][1]
    ahora_txt = datetime.now(timezone.utc).isoformat(timespec="minutes")
    for a in estado["agentes"]:
        apagar_si_toca(a, precios, ahora_txt, ops_csv, volumenes)


def valor_cesta(estado, precios):
    return sum(u * precios.get(p, 0.0) for p, u in estado["cesta"].items())


def valor_btc(estado, precios):
    return START * (1 - FEE) * precios[BTC] / (estado["precio_inicio"] * (1 + SLIP))


def corto(par):
    return "BTC" if par == BTC else (par[:-3] if par.endswith("EUR") else par)


def guardar(estado, carpeta):
    precios = estado["precios"]
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    eqs = [equity(a, precios) for a in estado["agentes"]]
    rb, rc = valor_btc(estado, precios), valor_cesta(estado, precios)
    anotar(os.path.join(carpeta, "historial_v2.csv"),
           ["fecha_utc", "precio_eur"] + [n for n, _ in AGENTES] + [REF_BTC, REF_CESTA],
           [ahora, round(precios[BTC], 2)] + [round(e, 4) for e in eqs] + [round(rb, 4), round(rc, 4)])
    anotar(os.path.join(carpeta, "operaciones.csv"), CAB_OPS, None)      # que exista aunque no haya operaciones
    with open(os.path.join(carpeta, "estado.json"), "w") as f:
        json.dump(estado, f, indent=2)
    dias = (datetime.fromisoformat(ahora) - datetime.fromisoformat(estado["inicio"])).total_seconds() / 86400
    l = ["# Sala abierta (dinero ficticio)", "",
         f"Actualizado: {ahora} UTC · en marcha desde {estado['inicio']} ({dias:.1f} días) · reglas: CRITERIOS.md, secciones 7 y 7.1",
         "Simulación aparte de la oficina principal. 2 agentes con las ideas «POSIBLE» del laboratorio v2 que pueden comprar "
         f"todas las monedas de la oficina ({len(precios)} con precio ahora), con velas de 4 h de Kraken; 2,50 € por compra, "
         f"hasta 4 a la vez. Costes: comisión {FEE * 100:.2f} % + deslizamiento {SLIP * 100:.2f} % "
         f"({SLIP_POCO * 100:.1f} % en monedas de poco volumen). Se ve en el panel, botón «Sala abierta».",
         "", "| Agente | Capital (EUR) | Resultado | Dif. vs mantener la cesta | Operaciones (cerradas) | Estado |",
         "|---|---:|---:|---:|---:|---|"]
    for a, e in zip(estado["agentes"], eqs):
        est = "Apagado por riesgo" if a["apagado"] else (
            "Con " + ", ".join(sorted(corto(p) for p in a["posiciones"])) if a["posiciones"] else "En efectivo")
        l.append(f"| {a['nombre']} | {e:.2f} | {(e / START - 1) * 100:+.2f} % | {e - rc:+.2f} € | "
                 f"{a['operaciones']} ({a.get('cerradas', 0)}) | {est} |")
    l.append(f"| Mantener la cesta inicial a partes iguales | {rc:.2f} | {(rc / START - 1) * 100:+.2f} % | 0.00 € | {len(estado['cesta'])} | Referencia |")
    l.append(f"| Mantener BTC | {rb:.2f} | {(rb / START - 1) * 100:+.2f} % | {rb - rc:+.2f} € | 1 | Referencia |")
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
    ruta = os.path.join(carpeta, "estado.json")
    estado = None
    if os.path.exists(ruta):
        with open(ruta) as f:
            estado = json.load(f)
        if estado.get("version") != VERSION:
            raise SystemExit("datos_sala es de otra versión de la sala: bórralo a mano antes de seguir.")
    tenidas = sorted({p for a in (estado or {}).get("agentes", []) for p in a["posiciones"]})
    velas, volumenes, orden, ahora = obtener(demo, tenidas)
    if BTC not in velas:
        raise SystemExit("Kraken no dio BTC: no se hace nada esta vez.")
    if estado is None:
        estado = estado_nuevo(velas, volumenes, ahora)
        print(f"Primera ejecución: {len(AGENTES)} agentes empiezan con {START} € ficticios cada uno.")
    paso(estado, velas, volumenes, orden, ahora, os.path.join(carpeta, "operaciones.csv"))
    guardar(estado, carpeta)


if __name__ == "__main__":
    main()
