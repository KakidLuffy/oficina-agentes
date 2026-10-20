#!/usr/bin/env python3
"""
Oficina de agentes en la nube (PAPER TRADING: dinero ficticio, no toca ningun exchange).

Cada ejecucion hace UN paso: descarga precios reales de BTC/EUR, deja que cada agente
decida con las velas de 1 hora ya cerradas y guarda todo en la carpeta "datos/".
GitHub Actions lo ejecuta cada hora (ver agentes.yml). No necesita claves ni librerias extra.

Uso:
  python agentes_nube.py            -> un paso con precios reales
  python agentes_nube.py --demo 120 -> prueba con precios inventados (120 velas), sin internet
"""
import csv
import json
import os
import random
import sys
import urllib.request
from datetime import datetime, timezone

START = 50.0          # euros ficticios por agente
FEE = 0.0025          # comision 0,25 % por operacion (revisa la de tu exchange: con ordenes a mercado puede ser mayor)
SLIP = 0.0005         # deslizamiento: cada compra paga un 0,05 % mas y cada venta recibe un 0,05 % menos
PERDIDA_DIA = 2.0     # si un agente pierde esto (EUR) en un dia, no vuelve a comprar ese dia
STOP = START * 0.7    # el responsable de riesgo apaga al agente que baja de aqui
DATOS = "datos"
ESTADO = os.path.join(DATOS, "estado.json")
HISTORIAL = os.path.join(DATOS, "historial_v2.csv")   # v2: 6 agentes. El historial.csv antiguo (4 agentes) se conserva sin tocar.
OPERACIONES = os.path.join(DATOS, "operaciones.csv")
RESUMEN = os.path.join(DATOS, "resumen.md")


# ---------------- estrategias ----------------
def media(lista):
    return sum(lista) / len(lista)


def cruce(p, a, b):
    if len(p) < b + 1:
        return None
    ca, cb = media(p[-a:]), media(p[-b:])
    pa, pb = media(p[-a - 1:-1]), media(p[-b - 1:-1])
    if pa <= pb and ca > cb:
        return "b"
    if pa >= pb and ca < cb:
        return "s"
    return None


def momentum(p):
    if len(p) < 14:
        return None
    r = p[-1] / p[-13] - 1
    return "b" if r > 0.012 else ("s" if r < -0.012 else None)


def rebote(p):
    if len(p) < 21:
        return None
    m, x = media(p[-20:]), p[-1]
    return "b" if x < m * 0.985 else ("s" if x > m else None)


def filtro(decidir, n=200):
    """Filtro de mercado: solo deja pasar las COMPRAS si el precio esta por encima de su media de n velas."""
    def f(p):
        senal = decidir(p)
        if senal == "b" and (len(p) < n or p[-1] <= media(p[-n:])):
            return None
        return senal
    return f


def _votos(p):
    """Reglas de tendencia a favor de estar comprado: cruce 10/30, cruce 5/20 y momentum de 12 velas."""
    return (media(p[-10:]) > media(p[-30:])) + (media(p[-5:]) > media(p[-20:])) + (p[-1] > p[-13])


def consenso(p):
    """Consenso 2 de 3: compra cuando al menos 2 de las 3 reglas de tendencia coinciden; vende cuando dejan de coincidir."""
    if len(p) < 32:
        return None
    ahora, antes = _votos(p) >= 2, _votos(p[:-1]) >= 2
    if ahora and not antes:
        return "b"
    if antes and not ahora:
        return "s"
    return None


AGENTES = [
    ("Cruce 10/30", lambda p: cruce(p, 10, 30)),
    ("Cruce 5/20", lambda p: cruce(p, 5, 20)),
    ("Momentum", momentum),
    ("Rebote", rebote),
    ("Cruce 10/30 + filtro", filtro(lambda p: cruce(p, 10, 30))),
    ("Consenso 2 de 3", consenso),
]
DECIDIR = dict(AGENTES)
MIN_CERRADAS = 30   # criterio acordado: al menos 30 operaciones cerradas...
MIN_DIAS = 21       # ...y 3 semanas de simulacion, antes de fiarse de un agente


# ---------------- precios ----------------
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "oficina-agentes/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def velas_kraken():
    d = get_json("https://api.kraken.com/0/public/OHLC?pair=XBTEUR&interval=60")
    if d.get("error"):
        raise RuntimeError(d["error"])
    clave = [k for k in d["result"] if k != "last"][0]
    return [(int(v[0]), float(v[4])) for v in d["result"][clave]]


def velas_coinbase():
    d = get_json("https://api.exchange.coinbase.com/products/BTC-EUR/candles?granularity=3600")
    return sorted((int(v[0]), float(v[4])) for v in d)


def velas_demo(n):
    random.seed(7)
    precio, t, salida = 60000.0, 1_700_000_000, []
    for _ in range(n):
        precio *= 1 + random.gauss(0, 0.007)
        salida.append((t, precio))
        t += 3600
    return salida


def obtener_velas(demo):
    if demo:
        return velas_demo(demo), "demo"
    try:
        return velas_kraken(), "Kraken"
    except Exception as e1:
        print("Kraken fallo:", e1)
        return velas_coinbase(), "Coinbase"


# ---------------- estado ----------------
def agente_nuevo(nombre, precio, inicio):
    return {"nombre": nombre, "efectivo": START, "btc": 0.0, "apagado": False, "operaciones": 0,
            "dia": None, "eq_dia": START, "inicio": inicio, "precio_inicio": precio,
            "pico": START, "caida_max": 0.0, "cerradas": 0, "ganadoras": 0, "coste_entrada": 0.0}


def migrar(estado, precio):
    """Pone al dia un estado antiguo sin perder nada: rellena campos nuevos y anade los agentes que falten (empiezan ahora)."""
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    existentes = {a["nombre"] for a in estado["agentes"]}
    for n, _ in AGENTES:
        if n not in existentes:
            estado["agentes"].append(agente_nuevo(n, precio, ahora))
            print(f"Agente nuevo incorporado: {n} (empieza ahora con {START} EUR ficticios).")
    for a in estado["agentes"]:
        a.setdefault("inicio", estado["inicio"])
        a.setdefault("precio_inicio", estado["precio_inicio"])
        a.setdefault("pico", max(START, equity(a, precio)))
        a.setdefault("caida_max", 0.0)
        a.setdefault("cerradas", 0)
        a.setdefault("ganadoras", 0)
        a.setdefault("coste_entrada", 0.0)
    estado["agentes"] = [a for a in estado["agentes"] if a["nombre"] in DECIDIR]


def estado_nuevo(cerradas, precio):
    inicio = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ultima_vela": cerradas[-1][0],   # solo se actua sobre velas posteriores a esta
        "precio_inicio": precio,
        "fee": FEE,
        "slip": SLIP,
        "agentes": [agente_nuevo(n, precio, inicio) for n, _ in AGENTES],
    }


def anotar(archivo, cabecera, fila):
    nuevo = not os.path.exists(archivo)
    with open(archivo, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(cabecera)
        w.writerow(fila)


def parametros(estado):
    """Usa los costes guardados en el estado. Un estado antiguo sin operaciones adopta los costes actuales."""
    global FEE, SLIP
    if "slip" not in estado:
        if sum(a["operaciones"] for a in estado["agentes"]) == 0:
            estado["fee"], estado["slip"] = FEE, SLIP
            print("Estado antiguo sin operaciones: se aplican los costes nuevos (comision + deslizamiento).")
        else:
            estado["fee"], estado["slip"] = 0.0025, 0.0
            print("Aviso: este estado ya tiene operaciones con los costes antiguos; se mantienen. "
                  "Para aplicar los nuevos, borra la carpeta datos y empieza de nuevo.")
    FEE, SLIP = estado["fee"], estado["slip"]


def operar(a, tipo, precio, fecha):
    """Compra/vende todo. El precio ejecutado incluye el deslizamiento; ademas se paga la comision."""
    if tipo == "COMPRA":
        ejecutado = precio * (1 + SLIP)
        importe = a["efectivo"]
        a["coste_entrada"] = importe
        a["btc"] = importe * (1 - FEE) / ejecutado
        a["efectivo"] = 0.0
    else:
        ejecutado = precio * (1 - SLIP)
        importe = a["btc"] * ejecutado
        a["efectivo"] = importe * (1 - FEE)
        a["btc"] = 0.0
        a["cerradas"] += 1
        a["ganadoras"] += a["efectivo"] > a["coste_entrada"]
    a["operaciones"] += 1
    anotar(OPERACIONES, ["fecha_utc", "agente", "tipo", "precio_eur", "importe_eur"],
           [fecha, a["nombre"], tipo, round(ejecutado, 2), round(importe, 2)])
    print(f"{a['nombre']}: {tipo} a {ejecutado:.0f} EUR")


def equity(a, precio):
    return a["efectivo"] + a["btc"] * precio


def seguir_caida(a, precio):
    eq = equity(a, precio)
    a["pico"] = max(a["pico"], eq)
    a["caida_max"] = max(a["caida_max"], (a["pico"] - eq) / a["pico"] * 100)


def apagar_si_toca(a, precio, fecha):
    if not a["apagado"] and equity(a, precio) < STOP:
        if a["btc"] > 0:
            operar(a, "VENTA", precio, fecha)
        a["apagado"] = True
        print(f"RIESGO: {a['nombre']} apagado por superar el limite de perdida")


def paso(estado, velas):
    cerradas, precio = velas[:-1], velas[-1][1]   # la ultima vela aun esta en curso
    cierres = [c for _, c in cerradas]
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    nuevas = [i for i, (t, _) in enumerate(cerradas) if t > estado["ultima_vela"]]
    if len(nuevas) > 1:
        print(f"Aviso: {len(nuevas)} velas nuevas (la ejecucion anterior se retraso); se procesan todas en orden.")
    for i in nuevas:
        t, p = cerradas[i]
        fecha = datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="minutes")
        for a in estado["agentes"]:
            decidir = DECIDIR[a["nombre"]]
            if a["apagado"]:
                continue
            dia = t // 86400
            if a.get("dia") != dia:                      # nuevo dia: se anota con cuanto empieza
                a["dia"], a["eq_dia"] = dia, equity(a, p)
            senal = decidir(cierres[:i + 1])
            if senal == "b" and a["efectivo"] > 1:
                if a["eq_dia"] - equity(a, p) >= PERDIDA_DIA:
                    print(f"{a['nombre']}: compra bloqueada por el limite de perdida diaria")
                else:
                    operar(a, "COMPRA", p, fecha)
            elif senal == "s" and a["btc"] > 0:
                operar(a, "VENTA", p, fecha)
            seguir_caida(a, p)
            apagar_si_toca(a, p, fecha)
    if nuevas:
        estado["ultima_vela"] = cerradas[nuevas[-1]][0]
    for a in estado["agentes"]:
        seguir_caida(a, precio)
        apagar_si_toca(a, precio, ahora)
    return ahora, precio


def guardar(estado, ahora, precio, fuente):
    os.makedirs(DATOS, exist_ok=True)
    eqs = [equity(a, precio) for a in estado["agentes"]]
    mantener = START * (1 - FEE) * precio / (estado["precio_inicio"] * (1 + SLIP))
    anotar(HISTORIAL, ["fecha_utc", "precio_eur"] + [n for n, _ in AGENTES] + ["Comprar y mantener"],
           [ahora, round(precio, 2)] + [round(equity(next(a for a in estado["agentes"] if a["nombre"] == n), precio), 2)
                                        for n, _ in AGENTES] + [round(mantener, 2)])
    with open(ESTADO, "w") as f:
        json.dump(estado, f, indent=2)
    lineas = [
        "# Oficina de agentes (dinero ficticio)",
        "",
        f"Ultima actualizacion: {ahora} UTC · Precio BTC/EUR: {precio:.0f} ({fuente})",
        f"En marcha desde: {estado['inicio']} UTC",
        f"Costes simulados por operacion: comision {FEE * 100:.2f} % + deslizamiento {SLIP * 100:.2f} % · "
        f"limite de perdida diaria: {PERDIDA_DIA:.0f} EUR",
        "",
        "| Agente | Capital (EUR) | Resultado (EUR) | Dif. vs mantener | Operaciones | Ganadoras/cerradas | Caída máx. | Desde | Estado |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    pocas = []
    for a, e in zip(estado["agentes"], eqs):
        est = "Apagado por riesgo" if a["apagado"] else ("Con BTC" if a["btc"] > 0 else "En efectivo")
        hold = START * (1 - FEE) * precio / (a["precio_inicio"] * (1 + SLIP))
        dias = (datetime.now(timezone.utc) - datetime.fromisoformat(a["inicio"])).days
        aviso = " ⚠" if a["cerradas"] < MIN_CERRADAS or dias < MIN_DIAS else ""
        if aviso:
            pocas.append(a["nombre"])
        lineas.append(f"| {a['nombre']} | {e:.2f} | {e - START:+.2f} | {e - hold:+.2f} | {a['operaciones']} | "
                      f"{a['ganadoras']}/{a['cerradas']}{aviso} | {a['caida_max']:.1f} % | {a['inicio'][:10]} | {est} |")
    lineas.append(f"| Comprar y mantener | {mantener:.2f} | {mantener - START:+.2f} | – | 1 | – | – | {estado['inicio'][:10]} | Referencia |")
    if pocas:
        lineas += ["", f"⚠ Aún sin datos suficientes: se exigen al menos {MIN_CERRADAS} operaciones cerradas y {MIN_DIAS} días de simulación. Antes de eso, el resultado puede ser pura suerte."]
    lineas += ["", "Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.",
               "Estos resultados no garantizan beneficios futuros."]
    with open(RESUMEN, "w") as f:
        f.write("\n".join(lineas) + "\n")
    print("\n".join(lineas[4:]))


def main():
    demo = int(sys.argv[sys.argv.index("--demo") + 1]) if "--demo" in sys.argv else 0
    velas, fuente = obtener_velas(demo)
    os.makedirs(DATOS, exist_ok=True)
    precio = velas[-1][1]
    if os.path.exists(ESTADO):
        with open(ESTADO) as f:
            estado = json.load(f)
    else:
        estado = estado_nuevo(velas[:-1], precio)
        print("Primera ejecucion: los agentes empiezan ahora con", START, "EUR ficticios cada uno.")
    parametros(estado)
    migrar(estado, precio)
    ahora, precio = paso(estado, velas)
    guardar(estado, ahora, precio, fuente)


if __name__ == "__main__":
    main()
