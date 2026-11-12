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

START = 10.0          # euros ficticios por agente (9 agentes = 90 EUR en total)
VERSION = 5           # si cambian las reglas o los costes, sube este numero: la simulacion anterior se archiva y empieza de cero
FEE = 0.004           # comision 0,40 % por operacion: tarifa "maker" de Kraken Pro en el nivel mas bajo (con ordenes a mercado seria "taker", 0,80 %)
SLIP = 0.0005         # deslizamiento: cada compra paga un 0,05 % mas y cada venta recibe un 0,05 % menos
PERDIDA_DIA = START * 0.04   # si un agente pierde esto (EUR, el 4 % de su capital) en un dia, no vuelve a comprar ese dia
STOP = START * 0.7    # el responsable de riesgo apaga al agente que baja de aqui
TOP_MONEDAS = 20      # cuantas monedas se vigilan: las de mayor volumen en 24 h (cambia este numero si quieres mas o menos)
MAX_POS = 2           # maximo de monedas a la vez (v5: solo se compran BTC y ETH, asi que 2 compras de 5 EUR = 100 %
                      # invertible; con 5 de 2 EUR los agentes nunca pasaban del 40 % y la comparacion con
                      # "Comprar y mantener" premiaba estar en efectivo en las caidas)
SLOT = START / MAX_POS                  # euros ficticios que se invierten en cada compra
SLIP_POCO_VOLUMEN = 0.003               # deslizamiento (0,3 %) en monedas con poco volumen diario
VOLUMEN_ALTO = 100_000                  # EUR de volumen en 24 h a partir del cual se usa el deslizamiento normal
PAUSA_API = 1.1                         # segundos entre peticiones a Kraken (para no pasar su limite)
HISTORIA_HORAS = 220                    # velas de 1 hora que se descargan por moneda (el filtro de tendencia necesita 200)
MIN_CERRADAS = 30                       # criterio acordado: al menos 30 operaciones cerradas...
MIN_DIAS = 21                           # ...y 3 semanas de simulacion antes de fiarse de un agente
# Desde el 11-nov-2026 los agentes solo COMPRAN estas monedas (mas liquidas: menos deslizamiento y menos
# operaciones). Las posiciones que ya tenian en otras monedas se venden con su regla normal, sin forzar.
PERMITIDAS = ("XBTEUR", "ETHEUR")
BTC = "XBTEUR"                          # moneda de referencia para 'Comprar y mantener' y la columna precio_eur
# Stablecoins y monedas fiat: su precio casi no se mueve, asi que no tiene sentido operarlas
# v4: faltaba EURC (euro estable de Circle): en la v3 (21 dias) los agentes hicieron 80 operaciones con ella pagando 0,70 EUR en costes.
EXCLUIR_BASES = {"USDT", "USDC", "DAI", "PYUSD", "TUSD", "EURT", "EURR", "EURQ", "USDG", "RLUSD", "USDD", "USDQ",
                 "EURC", "EUROC", "EURCV", "EURI", "EURE", "EURAU", "USDE", "USDS", "FDUSD", "USD1",
                 "USD", "GBP", "AUD", "CAD", "CHF", "JPY", "EUR"}
# Lista de emergencia: solo se usa si Kraken no da los volumenes
RESPALDO = ["XBTEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "DOGEEUR", "DOTEUR", "LINKEUR", "LTCEUR", "AVAXEUR",
            "TRXEUR", "ATOMEUR", "XLMEUR", "BCHEUR", "UNIEUR", "NEAREUR", "AAVEEUR", "ETCEUR", "ALGOEUR", "FILEUR"]
# Agente "Rebalanceo semanal" (v4): cesta FIJA de 5 monedas grandes (las 5 primeras de la lista de respaldo, que ya existia
# antes de ver resultados) a partes iguales. Cada 7 dias vende lo que no es de la cesta y rehace solo las posiciones que se
# hayan apartado mas de un DESVIO_MAX de su peso: opera muy poco a proposito. No opera ninguna otra moneda.
REBALANCEO = "Rebalanceo semanal"
CESTA = RESPALDO[:5]                    # XBT, ETH, SOL, XRP, ADA
REBALANCEO_DIAS = 7
DESVIO_MAX = 0.35
# Referencia "Comprar y mantener (cesta)" (v4): al empezar se reparten START EUR a partes iguales entre las monedas que
# pueden comprar los agentes de senales (PERMITIDAS: BTC y ETH) y se mantienen sin tocar. Es una comparacion mas justa
# que solo BTC: en la v3 los agentes operaban sobre todo monedas pequenas, que cayeron mas que BTC.
REF_CESTA = "Comprar y mantener (cesta)"
REF_REBALANCEO = "Mantener la cesta del Rebalanceo"
REVISION_CALENDARIO = "9-feb-2027"     # CRITERIOS.md, seccion 5: revision a los 90 dias de la v5
_VOLUMENES_TODOS = {}                   # volumen 24 h (EUR) de todos los pares EUR, para el deslizamiento de la cesta
# Agente "Tendencia H1 (diaria)": hipotesis H1 y reglas de riesgo selladas de JANUS Crypto (v1, 27-oct-2026),
# reconstruidas desde su documentacion. Solo BTC y ETH, velas DIARIAS, solo largos, sin apalancamiento.
H1 = "Tendencia H1 (diaria)"
# Agente PRINCIPAL elegido de antemano (11-nov-2026, antes de ver resultados de la v5): el veredicto de la v5 se basa
# solo en el. Los demas son exploratorios: con 9 agentes, que alguno gane puede ser casualidad.
AGENTE_PRINCIPAL = None   # era H1; el 11-nov no paso la prueba historica (CRITERIOS.md): la v5 es exploratoria
H1_PARES = ("XBTEUR", "ETHEUR")
H1_SMA = 100                            # dentro si el cierre diario esta por encima de su media de 100 dias
H1_MAX_ACTIVO = 0.25                    # maximo 25 % del capital por activo (50 % en total con 2 activos)
H1_RIESGO_OP = 0.02                     # perdida maxima por operacion: 2 % del capital, con stop obligatorio
H1_PARADA_MES = 0.06                    # si el mes va un 6 % abajo, no abre posiciones nuevas hasta el mes siguiente
H1_PARADA_PICO = 0.15                   # caida del 15 % desde su maximo: cierra todo y se apaga (revision humana)
DATOS = "datos"
ESTADO = os.path.join(DATOS, "estado.json")
HISTORIAL = os.path.join(DATOS, "historial_v2.csv")   # v2: 6 agentes. El historial.csv antiguo (4 agentes) se conserva sin tocar
OPERACIONES = os.path.join(DATOS, "operaciones.csv")
CAB_OPERACIONES = ["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"]
RESUMEN = os.path.join(DATOS, "resumen.md")
GRAFICO = os.path.join(DATOS, "grafico.svg")


# ---------------- estrategias ----------------
def media(lista):
    return sum(lista) / len(lista)


def cruce(p, a, b, hueco=0.0):
    """Cruce de medias. 'hueco' exige una senal de compra mas fuerte: la media rapida debe superar a la lenta en ese %."""
    if len(p) < b + 1:
        return None
    ca, cb = media(p[-a:]), media(p[-b:])
    pa, pb = media(p[-a - 1:-1]), media(p[-b - 1:-1])
    if pa <= pb and ca > cb * (1 + hueco):
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
    """Momentum de corto plazo: mira las ultimas 6 horas y solo reacciona a movimientos del 1 %."""
    if len(p) < 8:
        return None
    r = p[-1] / p[-7] - 1
    return "b" if r > 0.010 else ("s" if r < -0.010 else None)


def rebote_rapido(p):
    """Rebote de corto plazo: compra si el precio cae un 1,2 % bajo su media de 8 velas; vende al volver a la media."""
    if len(p) < 9:
        return None
    m, x = media(p[-8:]), p[-1]
    return "b" if x < m * 0.988 else ("s" if x > m else None)


AGENTES = [
    ("Cruce 10/30", lambda p: cruce(p, 10, 30)),
    ("Cruce 5/20", lambda p: cruce(p, 5, 20)),
    ("Momentum", momentum),
    ("Rebote", rebote),
    ("Cruce 10/30 + filtro", filtro(lambda p: cruce(p, 10, 30))),
    # agentes rapidos: senales de pocas horas, para que operen varias veces al dia
    ("Cruce 3/8 rapido", filtro(lambda p: cruce(p, 3, 8, 0.002), 48)),
    ("Rebote rapido", rebote_rapido),
    (REBALANCEO, lambda p: None),       # no usa senales: ver rebalancear()
    # agente de velas diarias con reglas propias de riesgo (ver paso_h1); no usa la decision por hora
    (H1, None),
]
DECIDIR = dict(AGENTES)
# Reglas de salida y de entrada:
#   espera_h: horas sin volver a comprar una moneda tras venderla · stop / objetivo: venta automatica al perder / ganar ese %
#   solo_liquidas: no compra monedas de poco volumen (donde el deslizamiento real es mayor)
#   min_horas (v4, EXPERIMENTO en la mitad de los agentes): no se vende por senal antes de ese tiempo desde la compra
#   (stop y objetivo si actuan). En la v3 (21 dias) las 295 operaciones cerradas en menos de 6 h perdieron 9,09 EUR, pero las
#   de 6 h o mas perdieron mas por operacion (-0,040 frente a -0,031 EUR): no esta claro que ayude, por eso solo se aplica a
#   CON_MIN_HORAS y el resto sirve de comparacion. espera_h se queda como en la v3 (solo en los rapidos): en la v3 solo
#   47 de 508 recompras fueron en menos de 6 h, asi que extenderla a todos casi no cambiaria nada.
# v4 retira "Momentum rapido" (318 operaciones, 2,77 EUR en costes, -30 %) y "Consenso 2 de 3" (196 operaciones, -31 %):
# menos agentes = menos comparaciones y menos riesgo de que uno "gane" por casualidad.
MIN_HORAS = 6
ESPERA_H = 6
CON_MIN_HORAS = ("Cruce 10/30", "Momentum", "Cruce 3/8 rapido")   # sin ella (comparacion): Cruce 5/20, Rebote,
                                                                  # Cruce 10/30 + filtro, Rebote rapido
OPCIONES = {n: ({"min_horas": MIN_HORAS} if n in CON_MIN_HORAS else {}) for n, _ in AGENTES}
for _n in ("Cruce 3/8 rapido", "Rebote rapido"):
    OPCIONES[_n].update({"espera_h": ESPERA_H, "stop": 0.015, "objetivo": 0.03, "solo_liquidas": True})


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
    _VOLUMENES_TODOS.update({pares[c]: v for c, v in volumenes.items() if c in pares})
    disponibles = set(pares.values())
    if volumenes:
        salida = sorted(((pares[c], volumenes.get(c, 0.0)) for c in pares), key=lambda x: (-x[1], x[0]))
        salida = salida[:TOP_MONEDAS]
    else:
        print("Sin volumenes: se usa la lista de respaldo.")
        salida = [(p, 0.0) for p in RESPALDO if p in disponibles][:TOP_MONEDAS]
    for par in reversed(PERMITIDAS):                     # BTC y ETH siempre se descargan
        if par not in [p for p, _ in salida] and (par in disponibles or par == BTC):
            salida.insert(0, (par, 0.0))
    return salida


def velas_kraken(par):
    desde = int(time.time()) - HISTORIA_HORAS * 3600
    res = kraken(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=60&since={desde}")
    clave = [k for k in res if k != "last"][0]
    return [(int(v[0]), float(v[4])) for v in res[clave]]


def velas_coinbase():
    d = get_json("https://api.exchange.coinbase.com/products/BTC-EUR/candles?granularity=3600")
    return sorted((int(v[0]), float(v[4])) for v in d)


def velas_diarias_kraken(par):
    """Ultimas 720 velas diarias (Kraken no da mas); H1 necesita 101."""
    res = kraken(f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=1440")
    clave = [k for k in res if k != "last"][0]
    return [(int(v[0]), float(v[4])) for v in res[clave]]


def velas_demo(n, k, paso_s=3600, fin=None):
    random.seed(7 + 13 * k + (0 if paso_s == 3600 else 1000))
    precio, salida = 60000.0 / (k + 1), []
    t = (fin - n * paso_s) if fin else 1_700_000_000
    for _ in range(n):
        precio *= 1 + random.gauss(0, (0.007 + 0.002 * k) * (1 if paso_s == 3600 else 4))
        salida.append((t, precio))
        t += paso_s
    return salida


def pares_referencia():
    """Monedas de la referencia en cesta ya guardada (hay que seguir descargandolas aunque salgan del top)."""
    try:
        with open(ESTADO) as f:
            return list(json.load(f).get("referencia_cesta", {}))
    except (OSError, ValueError):
        return []


def obtener_datos(demo, extra=()):
    """Devuelve (velas {par: [(ts, cierre)]}, diarias {par: [(ts, cierre)]}, volumenes {par: EUR}, orden [pares],
    fuente, ahora_ts)."""
    if demo:
        nombres = [BTC, "ETHEUR"] + [f"DEMO{k}EUR" for k in range(2, 8)]
        velas = {p: velas_demo(demo, k) for k, p in enumerate(nombres)}
        vol = {p: (500_000 if k % 3 else 20_000) for k, p in enumerate(nombres)}
        ahora_ts = velas[BTC][-1][0] + 1800
        dia_fin = ahora_ts // 86400 * 86400 + 86400
        diarias = {p: velas_demo(200, k, 86400, dia_fin) for k, p in enumerate(nombres[:2])}
        return velas, diarias, vol, nombres, "demo", ahora_ts
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
    vol = {p: v for p, v in uni}
    for par in list(dict.fromkeys(list(CESTA) + list(extra))):   # cesta del rebalanceo y de la referencia, aunque no esten en el top
        if par not in velas:
            try:
                v = velas_kraken(par)
                if v:
                    velas[par] = v
                    vol[par] = _VOLUMENES_TODOS.get(par, 0.0)
            except Exception as e:
                print(f"{par} (cesta o referencia): sin datos esta vez ({e})")
            time.sleep(PAUSA_API)
    if BTC not in velas:
        print("Kraken no dio BTC; se usa Coinbase para BTC")
        velas[BTC], fuente = velas_coinbase(), "Coinbase (BTC) + Kraken"
    print(f"Se descargaron velas de {len(velas)} de {len(uni)} monedas.")
    orden = [p for p, _ in uni if p in velas]          # solo estas las operan los agentes de senales
    diarias = {}
    for par in H1_PARES:                                  # velas diarias solo para el agente H1
        try:
            diarias[par] = velas_diarias_kraken(par)
        except Exception as e:
            print(f"{par} (diarias): sin datos esta vez ({e})")
        time.sleep(PAUSA_API)
    return velas, diarias, vol, orden, fuente, int(time.time())


# ---------------- estado ----------------
def agente_nuevo(nombre, precio_btc):
    return {"nombre": nombre, "efectivo": START, "posiciones": {}, "apagado": False, "operaciones": 0,
            "dia": None, "eq_dia": START,
            "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"), "precio_inicio": precio_btc}


def referencia_cesta(velas, orden):
    """Unidades de cada moneda compradas al empezar, START EUR a partes iguales, con los mismos costes que los agentes."""
    pares = [p for p in (orden or list(velas)) if p in velas and p in PERMITIDAS]   # las mismas que pueden comprar
    if not pares:
        return {}
    parte = START / len(pares)
    return {p: parte * (1 - FEE) / (velas[p][-1][1] * (1 + SLIP)) for p in pares}


def referencia_rebalanceo(cesta, precios):
    """Las mismas monedas que el Rebalanceo, a partes iguales y SIN rebalancear (su referencia justa)."""
    pares = [p for p in cesta if precios.get(p)]
    if not pares:
        return {}
    parte = START / len(pares)
    return {p: parte * (1 - FEE) / (precios[p] * (1 + SLIP)) for p in pares}


def migrar_referencia_rebalanceo(estado):
    """Estados que no la tenian (v5 hasta el 12-nov): se reconstruye con las primeras compras del Rebalanceo,
    que son justo la cesta a partes iguales; si aun no compro, con los precios de ahora."""
    if "referencia_rebalanceo" in estado:
        return
    filas = []
    if os.path.exists(OPERACIONES):
        with open(OPERACIONES, newline="") as f:
            filas = [r for r in csv.DictReader(f) if r.get("agente") == REBALANCEO and r.get("tipo") == "COMPRA"]
    if filas:
        primera = min(r["fecha_utc"] for r in filas)
        ref = {}
        for r in filas:
            if r["fecha_utc"] == primera:
                ref[r["moneda"]] = ref.get(r["moneda"], 0.0) + float(r["importe_eur"]) * (1 - FEE) / float(r["precio_eur"])
        estado["referencia_rebalanceo"], estado["referencia_rebalanceo_desde"] = ref, primera
    else:
        estado["referencia_rebalanceo"] = referencia_rebalanceo(estado.get("cesta", []), estado.get("precios", {}))
        estado["referencia_rebalanceo_desde"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


def valor_referencia(estado, precios):
    ref = estado.get("referencia_cesta") or {}
    return sum(u * precios.get(p, estado["precios"].get(p, 0.0)) for p, u in ref.items()) if ref else None


def estado_nuevo(velas, ahora_ts, orden=None):
    cerradas = [c for c in velas[BTC] if c[0] + 3600 <= ahora_ts]
    return {
        "version": VERSION,
        "capital_inicial": START,          # si se cambia START, la simulacion archiva la anterior y empieza de cero
        "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ultima_vela": cerradas[-1][0],   # solo se actua sobre velas posteriores a esta
        "precio_inicio": velas[BTC][-1][1],
        "fee": FEE,
        "slip": SLIP,
        "precios": {p: v[-1][1] for p, v in velas.items()},
        "agentes": [agente_nuevo(n, velas[BTC][-1][1]) for n, _ in AGENTES],
        "cesta": cesta_para(velas),
        "referencia_cesta": referencia_cesta(velas, orden),
        "referencia_rebalanceo": referencia_rebalanceo(cesta_para(velas), {p: v[-1][1] for p, v in velas.items()}),
        "referencia_rebalanceo_desde": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def cesta_para(velas):
    """La cesta fija; con precios inventados (--demo) usa las 5 primeras monedas de la prueba."""
    if any(p.startswith("DEMO") for p in velas):
        return sorted(velas, key=lambda p: (p != BTC, p))[:len(CESTA)]
    return list(CESTA)


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


def operar(a, tipo, par, precio, fecha, volumenes, motivo="", importe_compra=None):
    """Compra un 'slot' (o `importe_compra` EUR) o vende toda la moneda. El precio ejecutado incluye el deslizamiento y se paga la comision."""
    slip = deslizamiento(par, volumenes)
    if tipo == "COMPRA":
        ejecutado = precio * (1 + slip)
        importe = min(a["efectivo"], SLOT if importe_compra is None else importe_compra)
        a["posiciones"][par] = importe * (1 - FEE) / ejecutado
        a["efectivo"] -= importe
        a.setdefault("entradas", {})[par] = ejecutado
        a.setdefault("compras", {})[par] = fecha
        coste = importe - a["posiciones"][par] * precio                 # comision + deslizamiento pagados al comprar
    else:
        unidades = a["posiciones"].pop(par)
        ejecutado = precio * (1 - slip)
        importe = unidades * ejecutado * (1 - FEE)    # lo que realmente se cobra, ya sin comision
        a["efectivo"] += importe
        a.setdefault("entradas", {}).pop(par, None)
        a.setdefault("compras", {}).pop(par, None)
        a.setdefault("stops", {}).pop(par, None)
        a.setdefault("ultima_venta", {})[par] = fecha
        coste = unidades * precio - importe                              # comision + deslizamiento pagados al vender
    a["operaciones"] += 1
    a["costes"] = a.get("costes", 0.0) + coste
    anotar(OPERACIONES, CAB_OPERACIONES,
           [fecha, a["nombre"], par, tipo, round(ejecutado, 6), round(importe, 2), motivo, round(coste, 4)])
    print(f"{a['nombre']}: {tipo} {par} a {ejecutado:.6g} EUR ({motivo})")


def equity(a, precios):
    return a["efectivo"] + sum(u * precios.get(p, 0.0) for p, u in a["posiciones"].items())


def apagar_si_toca(a, precios, fecha, volumenes):
    if not a["apagado"] and equity(a, precios) < STOP:
        for par in list(a["posiciones"]):
            operar(a, "VENTA", par, precios[par], fecha, volumenes, "apagado por riesgo")
        a["apagado"] = True
        print(f"RIESGO: {a['nombre']} apagado por superar el limite de perdida")


def horas_desde(desde, fecha):
    return (datetime.fromisoformat(fecha) - datetime.fromisoformat(desde)).total_seconds() / 3600


def retenida(a, par, fecha, op):
    """True si la moneda se compro hace menos de op['min_horas']: la senal vendedora se ignora (el stop no)."""
    comprada = a.get("compras", {}).get(par)
    return bool(op.get("min_horas") and comprada and horas_desde(comprada, fecha) < op["min_horas"])


def rebalancear(a, t, fecha, precios, volumenes, cesta):
    """Cada REBALANCEO_DIAS: vende lo que no es de la cesta, rehace las posiciones desviadas y compra lo que falte a partes iguales."""
    if a.get("ultimo_rebalanceo") is not None and t - a["ultimo_rebalanceo"] < REBALANCEO_DIAS * 86400:
        return False
    if a["eq_dia"] - equity(a, precios) >= PERDIDA_DIA:
        return False                                     # mismo limite de perdida diaria que el resto: se aplaza
    objetivo = equity(a, precios) / len(cesta)
    for par in list(a["posiciones"]):
        if par not in cesta:
            operar(a, "VENTA", par, precios[par], fecha, volumenes, "rebalanceo: fuera de la cesta")
        elif abs(a["posiciones"][par] * precios[par] / objetivo - 1) > DESVIO_MAX:
            operar(a, "VENTA", par, precios[par], fecha, volumenes, "rebalanceo: peso desviado")
    for par in cesta:
        if par not in a["posiciones"] and a["efectivo"] >= objetivo * 0.5:
            operar(a, "COMPRA", par, precios[par], fecha, volumenes, "rebalanceo", importe_compra=objetivo)
    a["ultimo_rebalanceo"] = t
    return True


def paso_h1(a, diarias, precios, ahora_ts, fecha, volumenes):
    """Hipotesis H1 con las reglas de riesgo de JANUS Crypto. Decide una vez por vela diaria cerrada; el stop
    se vigila en cada ejecucion con el precio actual."""
    if a["apagado"]:
        return
    for par, d in diarias.items():                       # precio actual de BTC/ETH (la vela diaria abierta)
        if d:
            precios[par] = d[-1][1]
    for par in list(a["posiciones"]):                    # 1) stop obligatorio de cada posicion
        stop = a.get("stops", {}).get(par)
        if stop and precios.get(par, stop) <= stop:
            operar(a, "VENTA", par, precios[par], fecha, volumenes, "stop (2 % del capital)")
    eq = equity(a, precios)
    a["pico"] = max(a.get("pico", START), eq)
    if eq <= a["pico"] * (1 - H1_PARADA_PICO):           # 2) caida del 15 % desde el maximo: se apaga
        for par in list(a["posiciones"]):
            operar(a, "VENTA", par, precios[par], fecha, volumenes, "caida del 15 % desde el maximo")
        a["apagado"] = True
        print(f"RIESGO: {a['nombre']} apagado (caida del 15 % desde su maximo): necesita revision humana")
        return
    mes = fecha[:7]
    if a.get("mes") != mes:
        a["mes"], a["eq_mes"] = mes, eq
    pausa_mes = eq <= a["eq_mes"] * (1 - H1_PARADA_MES)  # 3) mes con -6 %: no abre posiciones nuevas
    importe = START * H1_MAX_ACTIVO
    for par in H1_PARES:                                 # 4) la regla H1, una vez por cada cierre diario
        cer = [(t, c) for t, c in diarias.get(par, []) if t + 86400 <= ahora_ts]
        if len(cer) < H1_SMA + 1:
            continue
        t_ult = cer[-1][0]
        cierre, sma = cer[-1][1], media([c for _, c in cer[-H1_SMA:]])
        a.setdefault("h1_ultimo", {})[par] = {      # para poder revisar la regla sin descargar velas (solo informativo)
            "dia": datetime.fromtimestamp(t_ult, timezone.utc).strftime("%Y-%m-%d"),
            "cierre": round(cierre, 2), f"media{H1_SMA}": round(sma, 2), "encima": cierre > sma}
        vistas = a.setdefault("ultima_diaria", {})
        if vistas.get(par) == t_ult:
            continue
        vistas[par] = t_ult
        if par in a["posiciones"] and cierre < sma:
            operar(a, "VENTA", par, precios[par], fecha, volumenes, f"cierre diario bajo la media de {H1_SMA} dias")
        elif par not in a["posiciones"] and cierre > sma:
            if pausa_mes:
                print(f"{a['nombre']}: compra de {par} bloqueada (perdida del mes >= {H1_PARADA_MES * 100:.0f} %)")
            elif a["efectivo"] >= importe * 0.5:
                operar(a, "COMPRA", par, precios[par], fecha, volumenes,
                       f"cierre diario sobre la media de {H1_SMA} dias", importe_compra=importe)
                riesgo_pct = START * H1_RIESGO_OP / importe   # 0,20 EUR sobre 2,50 EUR -> stop al -8 %
                a.setdefault("stops", {})[par] = a["entradas"][par] * (1 - riesgo_pct)


def paso(estado, velas, diarias, volumenes, orden, ahora_ts):
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
    universo = set(orden)
    cesta = estado.setdefault("cesta", cesta_para(velas))
    for t in tiempos:
        fecha = datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="minutes")
        pares_t = sorted(cerr_por_t[t], key=lambda p: rango.get(p, 10 ** 6))
        for par in pares_t:
            precios[par] = cierres[par][indice[(par, t)]]
        for a in estado["agentes"]:
            decidir = DECIDIR.get(a["nombre"])
            if a["apagado"] or decidir is None:
                continue
            dia = t // 86400
            if a.get("dia") != dia:                      # nuevo dia: se anota con cuanto empieza
                a["dia"], a["eq_dia"] = dia, equity(a, precios)
            if a["nombre"] == REBALANCEO:
                if all(par in pares_t for par in cesta):     # solo con precio de esta hora en TODA la cesta
                    rebalancear(a, t, fecha, precios, volumenes, cesta)
                apagar_si_toca(a, precios, fecha, volumenes)
                continue
            op = OPCIONES.get(a["nombre"], {})
            pares_t_ag = [par for par in pares_t if par in universo]   # la cesta del rebalanceo no entra si no esta en el top
            senales = {par: decidir(cierres[par][:indice[(par, t)] + 1])
                       for par in pares_t if par in universo or par in a["posiciones"]}
            for par in pares_t:                          # primero se vende (stop y objetivo, y luego la senal vendedora)...
                if par not in a["posiciones"]:
                    continue
                entrada = a.get("entradas", {}).get(par)
                cambio = precios[par] / entrada - 1 if entrada else 0.0
                if op.get("stop") and entrada and cambio <= -op["stop"]:
                    operar(a, "VENTA", par, precios[par], fecha, volumenes, f"stop de perdida ({cambio * 100:.1f} %)")
                elif op.get("objetivo") and entrada and cambio >= op["objetivo"]:
                    operar(a, "VENTA", par, precios[par], fecha, volumenes, f"objetivo de ganancia ({cambio * 100:+.1f} %)")
                elif senales.get(par) == "s" and not retenida(a, par, fecha, op):
                    operar(a, "VENTA", par, precios[par], fecha, volumenes, "senal vendedora")
            bloqueado = a["eq_dia"] - equity(a, precios) >= PERDIDA_DIA
            for par in pares_t_ag:                       # ...y luego se compra, por orden de volumen
                if senales[par] == "b" and par not in a["posiciones"] and par in PERMITIDAS:
                    if len(a["posiciones"]) >= MAX_POS or a["efectivo"] < SLOT * 0.5:
                        break
                    if bloqueado:
                        print(f"{a['nombre']}: compra bloqueada por el limite de perdida diaria")
                        break
                    if op.get("solo_liquidas") and par != BTC and volumenes.get(par, 0) < VOLUMEN_ALTO:
                        continue                         # moneda de poco volumen: no se opera
                    uv = a.get("ultima_venta", {}).get(par)
                    if op.get("espera_h") and uv and (datetime.fromisoformat(fecha) - datetime.fromisoformat(uv)).total_seconds() < op["espera_h"] * 3600:
                        continue                         # vendida hace poco: se espera antes de volver a entrar
                    operar(a, "COMPRA", par, precios[par], fecha, volumenes, "senal compradora")
            apagar_si_toca(a, precios, fecha, volumenes)
    if tiempos:
        estado["ultima_vela"] = tiempos[-1]
    for par, v in velas.items():                        # precio actual (la ultima vela puede seguir abierta)
        precios[par] = v[-1][1]
    for a in estado["agentes"]:
        if a["nombre"] == H1:
            paso_h1(a, diarias, precios, ahora_ts, ahora, volumenes)
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
    cesta_ref = valor_referencia(estado, precios)
    cab_hist = ["fecha_utc", "precio_eur"] + [n for n, _ in AGENTES] + ["Comprar y mantener"] + ([REF_CESTA] if cesta_ref is not None else [])
    ajustar_historial(cab_hist)
    anotar(HISTORIAL, cab_hist,
           [ahora, round(precio, 2)] + [round(eq_por_nombre[n], 2) for n, _ in AGENTES] + [round(mantener, 2)]
           + ([round(cesta_ref, 2)] if cesta_ref is not None else []))
    with open(ESTADO, "w") as f:
        json.dump(estado, f, indent=2)
    dias = (datetime.fromisoformat(ahora) - datetime.fromisoformat(estado["inicio"])).total_seconds() / 86400
    lineas = [
        "# Oficina de agentes (dinero ficticio)",
        "",
        f"Ultima actualizacion: {ahora} UTC · Precio BTC/EUR: {precio:.0f} ({fuente})",
        f"En marcha desde: {estado['inicio']} UTC ({dias:.1f} dias)",
        f"Monedas vigiladas: las {n_monedas} de mayor volumen contra EUR (con datos en esta ejecucion: {n_con_datos}) · "
        f"cada agente puede tener hasta {MAX_POS} a la vez, {SLOT:.2f} EUR en cada una · "
        f"los agentes de senales solo compran {', '.join(nombre_corto(p) for p in PERMITIDAS)}",
        (f"Agente principal (elegido antes de empezar; el veredicto se basa solo en el): {AGENTE_PRINCIPAL}. "
         "Los demas son exploratorios." if AGENTE_PRINCIPAL else
         "Sin agente principal: Tendencia H1 no paso la prueba historica (ver CRITERIOS.md y backtest_h1.md). "
         "Todos los agentes son exploratorios: que alguno gane puede ser casualidad."),
        f"Costes simulados por operacion: comision {FEE * 100:.2f} % + deslizamiento {SLIP * 100:.2f} % "
        f"({SLIP_POCO_VOLUMEN * 100:.1f} % en monedas de poco volumen) · limite de perdida diaria: {PERDIDA_DIA:.2f} EUR",
        "",
        "| Agente | Capital (EUR) | Resultado (EUR) | Resultado (%) | Dif. vs Comprar y mantener (EUR, desde su inicio) | Operaciones | Costes pagados (EUR) | Antes de costes (EUR) | Desde | Estado |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
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
                      f"{a['operaciones']} | {a.get('costes', 0.0):.2f} | {e - START + a.get('costes', 0.0):+.2f} | {a['inicio'][:10]} | {est} |")
    lineas.append(f"| Comprar y mantener (solo BTC) | {mantener:.2f} | {mantener - START:+.2f} | {(mantener / START - 1) * 100:+.2f} % | 0.00 | 1 | "
                  f"{START - START * (1 - FEE) / (1 + SLIP):.2f} | {mantener - START * (1 - FEE) / (1 + SLIP):+.2f} | {estado['inicio'][:10]} | Referencia |")
    if cesta_ref is not None:
        n_ref = len(estado["referencia_cesta"])
        lineas.append(f"| {REF_CESTA} | {cesta_ref:.2f} | {cesta_ref - START:+.2f} | {(cesta_ref / START - 1) * 100:+.2f} % | "
                      f"{cesta_ref - mantener:+.2f} | {n_ref} | {START - START * (1 - FEE) / (1 + SLIP):.2f} | "
                      f"{cesta_ref - START * (1 - FEE) / (1 + SLIP):+.2f} | {estado['inicio'][:10]} | "
                      f"Referencia: {n_ref} monedas del inicio a partes iguales |")
    ref_reb = estado.get("referencia_rebalanceo") or {}
    if ref_reb:
        val = sum(u * precios.get(p, estado["precios"].get(p, 0.0)) for p, u in ref_reb.items())
        lineas.append(f"| {REF_REBALANCEO} | {val:.2f} | {val - START:+.2f} | {(val / START - 1) * 100:+.2f} % | "
                      f"{val - mantener:+.2f} | {len(ref_reb)} | {START - START * (1 - FEE) / (1 + SLIP):.2f} | "
                      f"{val - START * (1 - FEE) / (1 + SLIP):+.2f} | {estado.get('referencia_rebalanceo_desde', estado['inicio'])[:10]} | "
                      f"Referencia del Rebalanceo: sus {len(ref_reb)} monedas sin rebalancear |")
        lineas += ["", f"{REBALANCEO} frente a mantener sus mismas {len(ref_reb)} monedas sin rebalancear: "
                   f"{eq_por_nombre[REBALANCEO] - val:+.2f} EUR (la columna «Dif. vs Comprar y mantener» lo compara solo con BTC)."]
    h1 = next((a for a in estado["agentes"] if a["nombre"] == H1), None)
    if h1 and h1.get("h1_ultimo"):
        partes = [f"{nombre_corto(p)} cierre del {d['dia']} {d['cierre']:.2f} frente a media de {H1_SMA} dias {d[f'media{H1_SMA}']:.2f} "
                  f"({'encima: dentro' if d['encima'] else 'debajo: fuera'})" for p, d in sorted(h1["h1_ultimo"].items())]
        lineas += ["", f"Regla de {H1} (ultimo cierre diario): " + "; ".join(partes) + "."]
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
                       + "; ".join(pocos) + ". Antes de eso, el resultado puede ser pura suerte. "
                       f"El {REVISION_CALENDARIO} (90 dias) el que no llegue a {MIN_CERRADAS} cerradas se declara "
                       "«no evaluable con esta muestra» (CRITERIOS.md, seccion 5)."]
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


def archivar(etiqueta):
    """Guarda los archivos de la simulacion anterior en datos/archivo_<etiqueta>_<fecha>/ y deja datos/ listo para empezar."""
    destino = os.path.join(DATOS, f"archivo_{etiqueta}_{datetime.now(timezone.utc):%Y%m%d}")
    os.makedirs(destino, exist_ok=True)
    for ruta in (ESTADO, HISTORIAL, OPERACIONES, RESUMEN, GRAFICO):
        if os.path.exists(ruta):
            shutil.move(ruta, os.path.join(destino, os.path.basename(ruta)))


def main():
    demo = int(sys.argv[sys.argv.index("--demo") + 1]) if "--demo" in sys.argv else 0
    velas, diarias, volumenes, orden, fuente, ahora_ts = obtener_datos(demo, pares_referencia())
    os.makedirs(DATOS, exist_ok=True)
    if os.path.exists(ESTADO):
        with open(ESTADO) as f:
            estado = json.load(f)
        cap_ant, ver_ant = estado.get("capital_inicial", 50.0), estado.get("version", 1)
        if cap_ant != START or ver_ant != VERSION:
            archivar(f"{cap_ant:g}eur" if cap_ant != START else f"{cap_ant:g}eur_v{ver_ant}")
            estado = estado_nuevo(velas, ahora_ts, orden)
            print("Cambio de capital o de reglas: simulacion anterior archivada; los agentes empiezan ahora con", START, "EUR ficticios cada uno.")
        else:
            migrar(estado, velas)
    else:
        estado = estado_nuevo(velas, ahora_ts, orden)
        print("Primera ejecucion: los agentes empiezan ahora con", START, "EUR ficticios cada uno.")
    parametros(estado)
    migrar_referencia_rebalanceo(estado)
    asegurar_operaciones()                    # antes de operar, para que el archivo tenga la cabecera nueva
    ahora, precios = paso(estado, velas, diarias, volumenes, orden, ahora_ts)
    guardar(estado, ahora, precios, fuente, len(orden), len(velas))


if __name__ == "__main__":
    main()
