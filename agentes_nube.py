#!/usr/bin/env python3
"""
Oficina de agentes en la nube (PAPER TRADING: dinero ficticio, no toca ningun exchange).

Cada ejecucion hace UN paso: pide a Kraken la lista de pares contra EUR, se queda con las TOP_MONEDAS de mayor
volumen (sin stablecoins ni monedas fiat), descarga sus precios reales, deja que cada agente decida con las velas
de 1 hora ya cerradas y guarda todo en la carpeta "datos/". Cada agente reparte sus 10 EUR ficticios en hasta
5 monedas a la vez. GitHub Actions lo ejecuta cada hora (ver agentes.yml). No necesita claves ni librerias extra.

Uso:
  python agentes_nube.py            -> un paso con precios reales
  python agentes_nube.py --demo 120 -> prueba con precios inventados (120 velas, 8 monedas), sin internet
"""
import csv
import json
import os
import random
import sys
import time
import shutil
import urllib.request
from datetime import datetime, timezone

import informe

START = 10.0          # euros ficticios por agente (6 agentes = 60 EUR en total)
FEE = 0.0025          # comision 0,25 % por operacion (revisa la de tu exchange: con ordenes a mercado puede ser mayor)
SLIP = 0.0005         # deslizamiento: cada compra paga un 0,05 % mas y cada venta recibe un 0,05 % menos
PERDIDA_DIA = START * 0.04   # si un agente pierde esto (EUR, el 4 % de su capital) en un dia, no vuelve a comprar ese dia
STOP = START * 0.7    # el responsable de riesgo apaga al agente que baja de aqui
TOP_MONEDAS = 20      # cuantas monedas se vigilan: las de mayor volumen en 24 h (cambia este numero si quieres mas o menos)
MAX_POS = 5           # maximo de monedas que un agente puede tener a la vez
SLOT = START / MAX_POS                  # euros ficticios que se invierten en cada compra
SLIP_POCO_VOLUMEN = 0.003               # deslizamiento (0,3 %) en monedas con poco volumen diario
VOLUMEN_ALTO = 100_000                  # EUR de volumen en 24 h a partir del cual se usa el deslizamiento normal
PAUSA_API = 1.1                         # segundos entre peticiones a Kraken (para no pasar su limite)
HISTORIA_HORAS = 220                    # velas de 1 hora que se descargan por moneda (el filtro de tendencia necesita 200)
MIN_CERRADAS = 30                       # criterio acordado: al menos 30 operaciones cerradas...
MIN_DIAS = 21                           # ...y 3 semanas de simulacion antes de fiarse de un agente
BTC = "XBTEUR"                          # moneda de referencia para 'Comprar y mantener' y la columna precio_eur
# Stablecoins y monedas fiat: su precio casi no se mueve, asi que no tiene sentido operarlas
EXCLUIR_BASES = {"USDT", "USDC", "DAI", "PYUSD", "TUSD", "EURT", "EURR", "EURQ", "USDG", "RLUSD", "USDD", "USDQ",
                 "USD", "GBP", "AUD", "CAD", "CHF", "JPY", "EUR"}
# Lista de emergencia: solo se usa si Kraken no da los volumenes
RESPALDO = ["XBTEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "DOGEEUR", "DOTEUR", "LINKEUR", "LTCEUR", "AVAXEUR",
            "TRXEUR", "ATOMEUR", "XLMEUR", "BCHEUR", "UNIEUR", "NEAREUR", "AAVEEUR", "ETCEUR", "ALGOEUR", "FILEUR"]
DATOS = "datos"
ESTADO = os.path.join(DATOS, "estado.json")
HISTORIAL = os.path.join(DATOS, "historial_v2.csv")   # v2: 6 agentes. El historial.csv antiguo (4 agentes) se conserva sin tocar
OPERACIONES = os.path.join(DATOS, "operaciones.csv")
CAB_OPERACIONES = ["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur"]
RESUMEN = os.path.join(DATOS, "resumen.md")
GRAFICO = os.path.join(DATOS, "grafico.svg")


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


def momentum_rapido(p):
    """Momentum de corto plazo: mira solo las ultimas 4 velas (4 horas) y reacciona a movimientos del 0,6 %."""
    if len(p) < 6:
        return None
    r = p[-1] / p[-5] - 1
    return "b" if r > 0.006 else ("s" if r < -0.006 else None)


def rebote_rapido(p):
    """Rebote de corto plazo: compra si el precio cae un 0,8 % bajo su media de 8 velas; vende al volver a la media."""
    if len(p) < 9:
        return None
    m, x = media(p[-8:]), p[-1]
    return "b" if x < m * 0.992 else ("s" if x > m else None)


AGENTES = [
    ("Cruce 10/30", lambda p: cruce(p, 10, 30)),
    ("Cruce 5/20", lambda p: cruce(p, 5, 20)),
    ("Momentum", momentum),
    ("Rebote", rebote),
    ("Cruce 10/30 + filtro", filtro(lambda p: cruce(p, 10, 30))),
    ("Consenso 2 de 3", consenso),
    # agentes rapidos: senales de pocas horas, para que operen varias veces al dia
    ("Cruce 3/8 rapido", lambda p: cruce(p, 3, 8)),
    ("Momentum rapido", momentum_rapido),
    ("Rebote rapido", rebote_rapido),
]
DECIDIR = dict(AGENTES)


# ---------------- precios ----------------
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "oficina-agentes/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def kraken(url):
    """Llama a Kraken; si responde 'demasiadas peticiones' espera y reintenta."""
    for intento in range(4):
        d = get_json(url)
        err = d.get("error")
        if not err:
            return d["result"]
        if any("Rate limit" in e or "Too many" in e for e in err) and intento < 3:
            print("Kraken pide ir mas despacio; espero", 5 * (intento + 1), "s")
            time.sleep(5 * (intento + 1))
            continue
        raise RuntimeError(err)


def universo_kraken():
    """Las TOP_MONEDAS de mayor volumen entre los pares contra EUR en linea (sin stablecoins ni fiat).
    Devuelve [(par, volumen_24h_EUR)] ordenado de mayor a menor volumen."""
    res = kraken("https://api.kraken.com/0/public/AssetPairs")
    pares = {}
    for clave, v in res.items():
        if v.get("quote") not in ("ZEUR", "EUR"):
            continue
        if v.get("status", "online") != "online" or v.get("aclass_base", "currency") != "currency":
            continue
        if ".d" in clave or "." in v.get("altname", "."):
            continue
        alt = v["altname"]
        base = alt[:-3] if alt.endswith("EUR") else alt
        if base.upper() in EXCLUIR_BASES:
            continue
        pares[clave] = alt
    volumenes = {}
    try:
        lista = list(pares)
        for i in range(0, len(lista), 80):                   # por trozos, para no hacer una URL demasiado larga
            tick = kraken("https://api.kraken.com/0/public/Ticker?pair=" + ",".join(lista[i:i + 80]))
            for clave, t in tick.items():
                volumenes[clave] = float(t["v"][1]) * float(t["c"][0])
            time.sleep(PAUSA_API)
    except Exception as e:
        print("No se pudo leer el volumen de las monedas:", e)
    disponibles = set(pares.values())
    if volumenes:
        salida = sorted(((pares[c], volumenes.get(c, 0.0)) for c in pares), key=lambda x: (-x[1], x[0]))
        salida = salida[:TOP_MONEDAS]
    else:
        print("Sin volumenes: se usa la lista de respaldo.")
        salida = [(p, 0.0) for p in RESPALDO if p in disponibles][:TOP_MONEDAS]
    if BTC not in [p for p, _ in salida]:
        salida.insert(0, (BTC, 0.0))
    return salida


def velas_kraken(par):
    desde = int(time.time()) - HISTORIA_HORAS * 3600
    res = kraken(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=60&since={desde}")
    clave = [k for k in res if k != "last"][0]
    return [(int(v[0]), float(v[4])) for v in res[clave]]


def velas_coinbase():
    d = get_json("https://api.exchange.coinbase.com/products/BTC-EUR/candles?granularity=3600")
    return sorted((int(v[0]), float(v[4])) for v in d)


def velas_demo(n, k):
    random.seed(7 + 13 * k)
    precio, t, salida = 60000.0 / (k + 1), 1_700_000_000, []
    for _ in range(n):
        precio *= 1 + random.gauss(0, 0.007 + 0.002 * k)
        salida.append((t, precio))
        t += 3600
    return salida


def obtener_datos(demo):
    """Devuelve (velas {par: [(ts, cierre)]}, volumenes {par: EUR}, orden [pares], fuente, ahora_ts)."""
    if demo:
        nombres = [BTC] + [f"DEMO{k}EUR" for k in range(1, 8)]
        velas = {p: velas_demo(demo, k) for k, p in enumerate(nombres)}
        vol = {p: (500_000 if k % 3 else 20_000) for k, p in enumerate(nombres)}
        return velas, vol, nombres, "demo", velas[BTC][-1][0] + 1800
    uni = universo_kraken()
    print(f"Se vigilan {len(uni)} monedas (las de mayor volumen contra EUR en Kraken): "
          + ", ".join(p for p, _ in uni))
    velas, fuente = {}, "Kraken"
    for par, _ in uni:
        try:
            v = velas_kraken(par)
            if v:
                velas[par] = v
        except Exception as e:
            print(f"{par}: sin datos esta vez ({e})")
        time.sleep(PAUSA_API)
    if BTC not in velas:
        print("Kraken no dio BTC; se usa Coinbase para BTC")
        velas[BTC], fuente = velas_coinbase(), "Coinbase (BTC) + Kraken"
    print(f"Se descargaron velas de {len(velas)} de {len(uni)} monedas.")
    orden = [p for p, _ in uni if p in velas]
    return velas, {p: v for p, v in uni}, orden, fuente, int(time.time())


# ---------------- estado ----------------
def agente_nuevo(nombre, precio_btc):
    return {"nombre": nombre, "efectivo": START, "posiciones": {}, "apagado": False, "operaciones": 0,
            "dia": None, "eq_dia": START,
            "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"), "precio_inicio": precio_btc}


def estado_nuevo(velas, ahora_ts):
    cerradas = [c for c in velas[BTC] if c[0] + 3600 <= ahora_ts]
    return {
        "capital_inicial": START,          # si se cambia START, la simulacion archiva la anterior y empieza de cero
        "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ultima_vela": cerradas[-1][0],   # solo se actua sobre velas posteriores a esta
        "precio_inicio": velas[BTC][-1][1],
        "fee": FEE,
        "slip": SLIP,
        "precios": {p: v[-1][1] for p, v in velas.items()},
        "agentes": [agente_nuevo(n, velas[BTC][-1][1]) for n, _ in AGENTES],
    }


def migrar(estado, velas):
    """Estados antiguos (solo BTC, campo 'btc') pasan al formato con varias monedas."""
    for a in estado["agentes"]:
        if "posiciones" not in a:
            a["posiciones"] = {BTC: a["btc"]} if a.get("btc", 0) > 0 else {}
            a.pop("btc", None)
    estado.setdefault("precios", {})
    estado["precios"].setdefault(BTC, estado.get("precio_inicio", velas[BTC][-1][1]))
    # agentes nuevos: se anaden al final y empiezan ahora con START; los que ya existian conservan todo
    existentes = {a["nombre"] for a in estado["agentes"]}
    for n, _ in AGENTES:
        if n not in existentes:
            estado["agentes"].append(agente_nuevo(n, velas[BTC][-1][1]))
            print(f"Agente nuevo incorporado: {n} (empieza ahora con {START} EUR ficticios).")
    for a in estado["agentes"]:
        a.setdefault("inicio", estado["inicio"])
        a.setdefault("precio_inicio", estado["precio_inicio"])


def anotar(archivo, cabecera, fila):
    nuevo = not os.path.exists(archivo)
    with open(archivo, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(cabecera)
        w.writerow(fila)


def asegurar_operaciones():
    """Crea operaciones.csv con su cabecera aunque aun no haya operaciones. Si el archivo es de la version
    antigua (sin columna 'moneda') y solo tiene la cabecera, se renueva con la cabecera nueva."""
    if os.path.exists(OPERACIONES):
        with open(OPERACIONES, newline="") as f:
            filas = list(csv.reader(f))
        if len(filas) <= 1 and (not filas or filas[0] != CAB_OPERACIONES):
            os.remove(OPERACIONES)
    if not os.path.exists(OPERACIONES):
        with open(OPERACIONES, "w", newline="") as f:
            csv.writer(f).writerow(CAB_OPERACIONES)


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


def deslizamiento(par, volumenes):
    """0,05 % en monedas con volumen alto; 0,3 % en las de poco volumen o con volumen desconocido."""
    return SLIP if volumenes.get(par, 0) >= VOLUMEN_ALTO or par == BTC else max(SLIP, SLIP_POCO_VOLUMEN)


def operar(a, tipo, par, precio, fecha, volumenes):
    """Compra un 'slot' o vende toda la moneda. El precio ejecutado incluye el deslizamiento y se paga la comision."""
    slip = deslizamiento(par, volumenes)
    if tipo == "COMPRA":
        ejecutado = precio * (1 + slip)
        importe = min(a["efectivo"], SLOT)
        a["posiciones"][par] = importe * (1 - FEE) / ejecutado
        a["efectivo"] -= importe
    else:
        ejecutado = precio * (1 - slip)
        importe = a["posiciones"].pop(par) * ejecutado * (1 - FEE)    # lo que realmente se cobra, ya sin comision
        a["efectivo"] += importe
    a["operaciones"] += 1
    anotar(OPERACIONES, CAB_OPERACIONES,
           [fecha, a["nombre"], par, tipo, round(ejecutado, 6), round(importe, 2)])
    print(f"{a['nombre']}: {tipo} {par} a {ejecutado:.6g} EUR")


def equity(a, precios):
    return a["efectivo"] + sum(u * precios.get(p, 0.0) for p, u in a["posiciones"].items())


def apagar_si_toca(a, precios, fecha, volumenes):
    if not a["apagado"] and equity(a, precios) < STOP:
        for par in list(a["posiciones"]):
            operar(a, "VENTA", par, precios[par], fecha, volumenes)
        a["apagado"] = True
        print(f"RIESGO: {a['nombre']} apagado por superar el limite de perdida")


def paso(estado, velas, volumenes, orden, ahora_ts):
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cierres, indice, cerr_por_t = {}, {}, {}
    for par, v in velas.items():
        cer = [c for c in v if c[0] + 3600 <= ahora_ts]          # solo velas ya cerradas
        cierres[par] = [c for _, c in cer]
        for i, (t, _) in enumerate(cer):
            indice[(par, t)] = i
            if t > estado["ultima_vela"]:
                cerr_por_t.setdefault(t, []).append(par)
    tiempos = sorted(cerr_por_t)
    if len(tiempos) > 1:
        print(f"Aviso: {len(tiempos)} velas nuevas (la ejecucion anterior se retraso); se procesan todas en orden.")
    precios = estado["precios"]
    rango = {p: i for i, p in enumerate(orden)}
    for t in tiempos:
        fecha = datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="minutes")
        pares_t = sorted(cerr_por_t[t], key=lambda p: rango.get(p, 10 ** 6))
        for par in pares_t:
            precios[par] = cierres[par][indice[(par, t)]]
        for a in estado["agentes"]:
            decidir = DECIDIR[a["nombre"]]
            if a["apagado"]:
                continue
            dia = t // 86400
            if a.get("dia") != dia:                      # nuevo dia: se anota con cuanto empieza
                a["dia"], a["eq_dia"] = dia, equity(a, precios)
            senales = {par: decidir(cierres[par][:indice[(par, t)] + 1]) for par in pares_t}
            for par in pares_t:                          # primero se vende...
                if senales[par] == "s" and par in a["posiciones"]:
                    operar(a, "VENTA", par, precios[par], fecha, volumenes)
            bloqueado = a["eq_dia"] - equity(a, precios) >= PERDIDA_DIA
            for par in pares_t:                          # ...y luego se compra, por orden de volumen
                if senales[par] == "b" and par not in a["posiciones"]:
                    if len(a["posiciones"]) >= MAX_POS or a["efectivo"] < SLOT * 0.5:
                        break
                    if bloqueado:
                        print(f"{a['nombre']}: compra bloqueada por el limite de perdida diaria")
                        break
                    operar(a, "COMPRA", par, precios[par], fecha, volumenes)
            apagar_si_toca(a, precios, fecha, volumenes)
    if tiempos:
        estado["ultima_vela"] = tiempos[-1]
    for par, v in velas.items():                        # precio actual (la ultima vela puede seguir abierta)
        precios[par] = v[-1][1]
    for a in estado["agentes"]:
        apagar_si_toca(a, precios, ahora, volumenes)
    return ahora, precios


def nombre_corto(par):
    return par[:-3] if par.endswith("EUR") else par


def ajustar_historial(cabecera):
    """Si se anadieron agentes, reescribe el historial con las columnas nuevas (las filas viejas las rellenan con START)."""
    if not os.path.exists(HISTORIAL):
        return
    with open(HISTORIAL, newline="") as f:
        filas = list(csv.reader(f))
    if not filas or filas[0] == cabecera:
        return
    viejas = filas[0]
    nuevas = []
    for fila in filas[1:]:
        d = dict(zip(viejas, fila))
        nuevas.append([d.get(c, str(START)) for c in cabecera])
    with open(HISTORIAL, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        w.writerows(nuevas)
    print("Historial ampliado con las columnas de los agentes nuevos.")


def guardar(estado, ahora, precios, fuente, n_monedas, n_con_datos):
    os.makedirs(DATOS, exist_ok=True)
    asegurar_operaciones()
    precio = precios[BTC]
    eqs = [equity(a, precios) for a in estado["agentes"]]
    mantener = START * (1 - FEE) * precio / (estado["precio_inicio"] * (1 + SLIP))
    eq_por_nombre = {a["nombre"]: e for a, e in zip(estado["agentes"], eqs)}
    cab_hist = ["fecha_utc", "precio_eur"] + [n for n, _ in AGENTES] + ["Comprar y mantener"]
    ajustar_historial(cab_hist)
    anotar(HISTORIAL, cab_hist,
           [ahora, round(precio, 2)] + [round(eq_por_nombre[n], 2) for n, _ in AGENTES] + [round(mantener, 2)])
    with open(ESTADO, "w") as f:
        json.dump(estado, f, indent=2)
    dias = (datetime.fromisoformat(ahora) - datetime.fromisoformat(estado["inicio"])).total_seconds() / 86400
    lineas = [
        "# Oficina de agentes (dinero ficticio)",
        "",
        f"Ultima actualizacion: {ahora} UTC · Precio BTC/EUR: {precio:.0f} ({fuente})",
        f"En marcha desde: {estado['inicio']} UTC ({dias:.1f} dias)",
        f"Monedas vigiladas: las {n_monedas} de mayor volumen contra EUR (con datos en esta ejecucion: {n_con_datos}) · "
        f"cada agente puede tener hasta {MAX_POS} a la vez, {SLOT:.2f} EUR en cada una",
        f"Costes simulados por operacion: comision {FEE * 100:.2f} % + deslizamiento {SLIP * 100:.2f} % "
        f"({SLIP_POCO_VOLUMEN * 100:.1f} % en monedas de poco volumen) · limite de perdida diaria: {PERDIDA_DIA:.2f} EUR",
        "",
        "| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Desde | Estado |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for a, e in zip(estado["agentes"], eqs):
        if a["apagado"]:
            est = "Apagado por riesgo"
        elif a["posiciones"]:
            est = "Con " + ", ".join(nombre_corto(p) for p in sorted(a["posiciones"]))
        else:
            est = "En efectivo"
        hold_a = START * (1 - FEE) * precio / (a["precio_inicio"] * (1 + SLIP))   # mantener BTC desde que empezo ESTE agente
        lineas.append(f"| {a['nombre']} | {e:.2f} | {e - START:+.2f} | {(e / START - 1) * 100:+.2f} % | {e - hold_a:+.2f} | "
                      f"{a['operaciones']} | {a['inicio'][:10]} | {est} |")
    lineas.append(f"| Comprar y mantener (solo BTC) | {mantener:.2f} | {mantener - START:+.2f} | {(mantener / START - 1) * 100:+.2f} % | 0.00 | 1 | {estado['inicio'][:10]} | Referencia |")
    nombres = [n for n, _ in AGENTES]
    try:
        met = informe.metricas(HISTORIAL, OPERACIONES, nombres + ["Comprar y mantener"])
        lineas += ["", "Riesgo (calculado con el historial guardado):", "",
                   "| Agente | Caida maxima | Operaciones ganadoras | Operaciones perdedoras |",
                   "|---|---:|---:|---:|"]
        for n in nombres + ["Comprar y mantener"]:
            cm, g, pe = met[n]
            lineas.append(f"| {n} | {cm:.2f} % | {g} | {pe} |")
        lineas += ["", "Caida maxima = lo que llego a perder cada agente desde su mejor momento. "
                   "Una operacion cuenta cuando se cierra con su venta."]
        pocos = []
        for a in estado["agentes"]:
            cerradas = met[a["nombre"]][1] + met[a["nombre"]][2]
            dias_a = (datetime.fromisoformat(ahora) - datetime.fromisoformat(a["inicio"])).total_seconds() / 86400
            if cerradas < MIN_CERRADAS or dias_a < MIN_DIAS:
                pocos.append(f"{a['nombre']} ({cerradas} cerradas, {dias_a:.0f} dias)")
        if pocos:
            lineas += ["", f"⚠ Aun sin datos suficientes (se exigen {MIN_CERRADAS} operaciones cerradas y {MIN_DIAS} dias): "
                       + "; ".join(pocos) + ". Antes de eso, el resultado puede ser pura suerte."]
        if informe.grafico_svg(HISTORIAL, GRAFICO, [n for n, _ in AGENTES[:4]]):   # el grafico conserva sus 4 colores originales
            lineas += ["", "![Evolucion del capital](grafico.svg)"]
    except Exception as e:                      # los extras nunca deben romper la simulacion
        print("Aviso: no se pudieron calcular los extras del resumen:", e)
    if dias < 28:
        lineas += ["", f"Aviso: solo hay {dias:.1f} dias de datos; aun no hay base para concluir que una estrategia sea mejor."]
    lineas += ["", "Una estrategia solo merece dinero real si supera de forma sostenida a 'Comprar y mantener' durante semanas.",
               "Probar muchas monedas y estrategias aumenta la probabilidad de que alguna parezca buena solo por casualidad.",
               "Estos resultados no garantizan beneficios futuros."]
    with open(RESUMEN, "w") as f:
        f.write("\n".join(lineas) + "\n")
    print("\n".join(lineas[4:]))


def archivar(capital_antiguo):
    """Guarda los archivos de la simulacion anterior en datos/archivo_<capital>eur_<fecha>/ y deja datos/ listo para empezar."""
    destino = os.path.join(DATOS, f"archivo_{capital_antiguo:g}eur_{datetime.now(timezone.utc):%Y%m%d}")
    os.makedirs(destino, exist_ok=True)
    for ruta in (ESTADO, HISTORIAL, OPERACIONES, RESUMEN, GRAFICO):
        if os.path.exists(ruta):
            shutil.move(ruta, os.path.join(destino, os.path.basename(ruta)))


def main():
    demo = int(sys.argv[sys.argv.index("--demo") + 1]) if "--demo" in sys.argv else 0
    velas, volumenes, orden, fuente, ahora_ts = obtener_datos(demo)
    os.makedirs(DATOS, exist_ok=True)
    if os.path.exists(ESTADO):
        with open(ESTADO) as f:
            estado = json.load(f)
        if estado.get("capital_inicial", 50.0) != START:      # cambio de capital: se archiva la simulacion anterior
            archivar(estado.get("capital_inicial", 50.0))
            estado = estado_nuevo(velas, ahora_ts)
            print("Cambio de capital: simulacion anterior archivada; los agentes empiezan ahora con", START, "EUR ficticios cada uno.")
        else:
            migrar(estado, velas)
    else:
        estado = estado_nuevo(velas, ahora_ts)
        print("Primera ejecucion: los agentes empiezan ahora con", START, "EUR ficticios cada uno.")
    parametros(estado)
    asegurar_operaciones()                    # antes de operar, para que el archivo tenga la cabecera nueva
    ahora, precios = paso(estado, velas, volumenes, orden, ahora_ts)
    guardar(estado, ahora, precios, fuente, len(orden), len(velas))


if __name__ == "__main__":
    main()
