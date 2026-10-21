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
import bisect
import random
import re
import sys
import time
import io
import urllib.request
from datetime import datetime, timedelta, timezone

import archivado
import ejecucion
import estrategias
import informe
import velas as vl
import persistencia as ps
import reglas_mercado as rm

START = 10.0          # euros ficticios por agente (6 agentes = 60 EUR en total)
VERSION = 4           # si cambian las reglas o los costes, sube este numero: la simulacion anterior se archiva y empieza de cero
FEE = 0.004           # comision 0,40 % por operacion: tarifa "maker" de Kraken Pro en el nivel mas bajo (con ordenes a mercado seria "taker", 0,80 %)
SPREAD = ejecucion.SPREAD   # horquilla compra-venta total (0,08 %): cada orden paga la mitad por su lado
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
# fecha_utc = INICIO de la vela sobre la que se decidio (se conserva por compatibilidad con el panel y los informes).
# vela_inicio_utc = lo mismo, explicito. decision_utc = momento en que esa vela cerro y la senal pudo conocerse
# (para una venta por apagado de riesgo, el momento real de la ejecucion).
CAB_OPERACIONES_V1 = ["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"]
CAB_OPERACIONES = CAB_OPERACIONES_V1 + ["vela_inicio_utc", "decision_utc"]
RESUMEN = os.path.join(DATOS, "resumen.md")
GRAFICO = os.path.join(DATOS, "grafico.svg")


# ---------------- estrategias (modulo unico, compartido con el laboratorio) ----------------
AGENTES = estrategias.AGENTES_VIVOS
DECIDIR = dict(AGENTES)
OPCIONES = estrategias.OPCIONES_VIVOS


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


REGLAS = {}      # {par: reglas_mercado.Regla} leidas de AssetPairs de Kraken


def regla(par):
    return REGLAS.get(par) or rm.GENERICA._replace(par=par)


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
        REGLAS[alt] = rm.desde_kraken(alt, v)
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
    return [vl.desde_kraken(v) for v in res[clave]]


def velas_coinbase():
    """Coinbase devuelve [time, low, high, open, close, volume]."""
    d = get_json("https://api.exchange.coinbase.com/products/BTC-EUR/candles?granularity=3600")
    return sorted((vl.Vela(int(v[0]), vl._num(v[3]), vl._num(v[2]), vl._num(v[1]), vl._num(v[4]), vl._num(v[5])) for v in d),
                  key=lambda x: x.ts)


def velas_demo(n, k):
    random.seed(7 + 13 * k)
    precio, t, salida = 60000.0 / (k + 1), 1_700_000_000 - (1_700_000_000 % 3600), []
    for _ in range(n):
        antes = precio
        precio *= 1 + random.gauss(0, 0.007 + 0.002 * k)
        salida.append(vl.Vela(t, antes, max(antes, precio), min(antes, precio), precio, 1.0))
        t += 3600
    return salida


INCIDENCIAS = []         # [(par, incidencia)] de esta ejecucion (ver velas.py)
BLOQUEADOS = set()       # pares con salto anomalo: no se abren compras nuevas en esta ejecucion


def validar_todo(velas, ahora_ts):
    """Valida cada par; descarta los pares sin datos utilizables y anota incidencias y bloqueos."""
    INCIDENCIAS.clear()
    BLOQUEADOS.clear()
    limpias = {}
    for par, lista in velas.items():
        util, inc = vl.validar(lista, 3600, ahora_ts)
        INCIDENCIAS.extend((par, i) for i in inc)
        if vl.hay_bloqueo(inc):
            BLOQUEADOS.add(par)
        if util:
            limpias[par] = util
        else:
            print(f"{par}: ninguna vela utilizable tras la validacion; se ignora en esta ejecucion.")
    if INCIDENCIAS:
        resumen = {}
        for _, i in INCIDENCIAS:
            resumen[i["tipo"]] = resumen.get(i["tipo"], 0) + 1
        print("Incidencias en los datos de velas:", ", ".join(f"{k} x{n}" for k, n in sorted(resumen.items())))
    return limpias


def obtener_datos(demo):
    """Devuelve (velas {par: [Vela]}, volumenes {par: EUR}, orden [pares], fuente, ahora_ts). Las velas ya estan validadas."""
    velas, volumenes, orden, fuente, ahora_ts = _descargar(demo)
    velas = validar_todo(velas, ahora_ts)
    orden = [p for p in orden if p in velas]
    return velas, volumenes, orden, fuente, ahora_ts


def _descargar(demo):
    if demo:
        nombres = [BTC] + [f"DEMO{k}EUR" for k in range(1, 8)]
        velas = {p: velas_demo(demo, k) for k, p in enumerate(nombres)}
        vol = {p: (500_000 if k % 3 else 20_000) for k, p in enumerate(nombres)}
        return velas, vol, nombres, "demo", velas[BTC][-1].ts + 1800
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
    return {"nombre": nombre, "efectivo": START, "posiciones": {}, "pendientes": [], "apagado": False, "operaciones": 0,
            "dia": None, "eq_dia": START,
            "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"), "precio_inicio": precio_btc}


def estado_nuevo(velas, ahora_ts):
    cerradas = [c for c in velas[BTC] if c.ts + 3600 <= ahora_ts]
    return {
        "version": VERSION,
        "capital_inicial": START,          # si se cambia START, la simulacion archiva la anterior y empieza de cero
        "inicio": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ultima_vela": cerradas[-1].ts,   # solo se actua sobre velas posteriores a esta
        "precio_inicio": velas[BTC][-1].c,
        "fee": FEE,
        "slip": SLIP,
        "spread": SPREAD,
        "precios": {p: v[-1].c for p, v in velas.items()},
        "agentes": [agente_nuevo(n, velas[BTC][-1].c) for n, _ in AGENTES],
    }


def migrar(estado, velas):
    """Estados antiguos (solo BTC, campo 'btc') pasan al formato con varias monedas."""
    for a in estado["agentes"]:
        if "posiciones" not in a:
            a["posiciones"] = {BTC: a["btc"]} if a.get("btc", 0) > 0 else {}
            a.pop("btc", None)
    estado.setdefault("precios", {})
    estado["precios"].setdefault(BTC, estado.get("precio_inicio", velas[BTC][-1].c))
    # agentes nuevos: se anaden al final y empiezan ahora con START; los que ya existian conservan todo
    existentes = {a["nombre"] for a in estado["agentes"]}
    for n, _ in AGENTES:
        if n not in existentes:
            estado["agentes"].append(agente_nuevo(n, velas[BTC][-1].c))
            print(f"Agente nuevo incorporado: {n} (empieza ahora con {START} EUR ficticios).")
    for a in estado["agentes"]:
        a.setdefault("inicio", estado["inicio"])
        a.setdefault("precio_inicio", estado["precio_inicio"])


COLA_OPS = []        # operaciones de esta ejecucion; se escriben junto con el estado y el historial en una sola transaccion


def texto_csv(filas):
    b = io.StringIO()
    csv.writer(b).writerows(filas)
    return b.getvalue()


def leer_texto(ruta):
    if not os.path.exists(ruta):
        return ""
    with open(ruta, encoding="utf-8", newline="") as f:
        return f.read()


def iso_vela(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="minutes")


def fin_de_vela(fecha):
    """Momento en que cierra la vela que empieza en 'fecha' (texto ISO a minutos)."""
    return (datetime.fromisoformat(fecha) + timedelta(hours=1)).isoformat(timespec="minutes")


def migrar_operaciones(filas):
    """Pasa las filas del formato de 8 columnas al de 10. Solo se rellena lo que se puede DERIVAR con certeza:
    las operaciones normales llevan como fecha el inicio de su vela; las de 'apagado por riesgo' llevan la hora real
    de ejecucion (con segundos), asi que de ellas se desconoce la vela y su decision es esa hora."""
    nuevas = [CAB_OPERACIONES]
    for f in filas[1:]:
        f = list(f) + [""] * (len(CAB_OPERACIONES_V1) - len(f))
        fecha = f[0]
        if not re.search(r"T\d\d:\d\d:\d\d", fecha):                 # sin segundos: inicio de vela
            try:
                nuevas.append(f[:8] + [fecha, fin_de_vela(fecha)])
                continue
            except ValueError:
                pass
        nuevas.append(f[:8] + ["", fecha])
    return nuevas


def asegurar_operaciones():
    """Crea operaciones.csv con su cabecera aunque aun no haya operaciones. Si el archivo es de una version
    anterior: sin operaciones se renueva; con operaciones se amplian las columnas conservando todas las filas."""
    if os.path.exists(OPERACIONES):
        with open(OPERACIONES, newline="", encoding="utf-8") as f:
            filas = list(csv.reader(f))
        if len(filas) <= 1 and (not filas or filas[0] != CAB_OPERACIONES):
            os.remove(OPERACIONES)
        elif filas and filas[0] == CAB_OPERACIONES_V1:
            ps.escribir_atomico(OPERACIONES, texto_csv(migrar_operaciones(filas)))
            print("operaciones.csv ampliado con las columnas vela_inicio_utc y decision_utc.")
    if not os.path.exists(OPERACIONES):
        ps.escribir_atomico(OPERACIONES, texto_csv([CAB_OPERACIONES]))


def parametros(estado):
    """Usa los costes guardados en el estado. Un estado antiguo sin operaciones adopta los costes actuales."""
    global FEE, SLIP, SPREAD
    estado.setdefault("spread", SPREAD if sum(a["operaciones"] for a in estado["agentes"]) == 0 else 0.0)
    if "slip" not in estado:
        if sum(a["operaciones"] for a in estado["agentes"]) == 0:
            estado["fee"], estado["slip"] = FEE, SLIP
            print("Estado antiguo sin operaciones: se aplican los costes nuevos (comision + deslizamiento).")
        else:
            estado["fee"], estado["slip"] = 0.0025, 0.0
            print("Aviso: este estado ya tiene operaciones con los costes antiguos; se mantienen. "
                  "Para aplicar los nuevos, borra la carpeta datos y empieza de nuevo.")
    FEE, SLIP, SPREAD = estado["fee"], estado["slip"], estado["spread"]


def deslizamiento(par, volumenes):
    """0,05 % en monedas con volumen alto; 0,3 % en las de poco volumen o con volumen desconocido."""
    return SLIP if volumenes.get(par, 0) >= VOLUMEN_ALTO or par == BTC else max(SLIP, SLIP_POCO_VOLUMEN)


RECHAZOS = []        # decisiones que no llegaron a ejecutarse en esta ejecucion: (fecha, agente, par, tipo, motivo, razon)


def preparar_orden(a, tipo, par, precio, volumenes):
    """Calcula la orden con costes, redondeo y minimos del exchange. Devuelve (datos, None) o (None, motivo_de_rechazo).
    'precio' es el precio de referencia (apertura de la vela de ejecucion)."""
    slip = deslizamiento(par, volumenes)
    r = regla(par)
    if tipo == "COMPRA":
        ejecutado = ejecucion.precio_compra(precio, slip, SPREAD)
        importe = min(a["efectivo"], SLOT)
        q = rm.redondear_abajo(importe * (1 - FEE) / ejecutado, r.lot_decimals)     # el exchange solo admite ciertos decimales
        motivo = rm.motivo_invalida(r, q, ejecutado)
        if motivo:
            return None, motivo
        return {"ejecutado": ejecutado, "unidades": q, "importe": q * ejecutado / (1 - FEE)}, None   # lo no gastado por el redondeo queda en efectivo
    unidades = a["posiciones"][par]
    ejecutado = ejecucion.precio_venta(precio, slip, SPREAD)
    motivo = rm.motivo_invalida(r, unidades, ejecutado)
    if motivo:
        return None, motivo
    return {"ejecutado": ejecutado, "unidades": unidades, "importe": unidades * ejecutado * (1 - FEE)}, None


def operar(a, tipo, par, precio, fecha, volumenes, motivo="", vela_inicio=None, decision=None):
    """Compra un 'slot' o vende toda la moneda. El precio ejecutado incluye horquilla y deslizamiento; se paga la comision y se
    respetan los minimos y decimales del exchange. Devuelve True si se ejecuta; False (y anota el rechazo) si no cumple los minimos."""
    datos, razon = preparar_orden(a, tipo, par, precio, volumenes)
    if razon:
        RECHAZOS.append((fecha, a["nombre"], par, tipo, motivo, razon))
        print(f"{a['nombre']}: orden de {tipo} {par} no ejecutada ({razon})")
        return False
    ejecutado, importe = datos["ejecutado"], datos["importe"]
    if tipo == "COMPRA":
        a["posiciones"][par] = datos["unidades"]
        a["efectivo"] -= importe
        a.setdefault("entradas", {})[par] = ejecutado
        coste = importe - datos["unidades"] * precio                    # comision + horquilla + deslizamiento pagados al comprar
    else:
        unidades = a["posiciones"].pop(par)
        a["efectivo"] += importe
        a.setdefault("entradas", {}).pop(par, None)
        a.setdefault("ultima_venta", {})[par] = fecha
        coste = unidades * precio - importe                              # comision + horquilla + deslizamiento pagados al vender
    a["operaciones"] += 1
    if vela_inicio is None:                                           # caso normal: 'fecha' es el inicio de la vela decisoria
        vela_inicio = fecha
    if decision is None:
        decision = fin_de_vela(fecha)
    COLA_OPS.append([fecha, a["nombre"], par, tipo, round(ejecutado, regla(par).pair_decimals if regla(par).fuente == "kraken" else 6),
                     round(importe, 2), motivo, round(coste, 4), vela_inicio, decision])
    print(f"{a['nombre']}: {tipo} {par} a {ejecutado:.6g} EUR ({motivo})")
    return True


def equity(a, precios):
    return a["efectivo"] + sum(u * precios.get(p, 0.0) for p, u in a["posiciones"].items())


def apagar_si_toca(a, precios, fecha, volumenes, ultima=None):
    """'ultima' {par: inicio de la ultima vela} se usa cuando 'fecha' es la hora real de ejecucion y no el inicio de una vela."""
    if not a["apagado"] and equity(a, precios) < STOP:
        for par in list(a["posiciones"]):
            if ultima is None:
                operar(a, "VENTA", par, precios[par], fecha, volumenes, "apagado por riesgo")
            else:
                operar(a, "VENTA", par, precios[par], fecha, volumenes, "apagado por riesgo",
                       vela_inicio=ultima.get(par, ""), decision=fecha)
        a["apagado"] = True
        print(f"RIESGO: {a['nombre']} apagado por superar el limite de perdida")


MAX_ESPERA_ORDEN = 6 * 3600       # una orden que no encuentra precio de ejecucion en 6 horas se anula (moneda sin operaciones)


def rechazar(a, o, razon):
    RECHAZOS.append((iso_vela(o["vela_ts"]), a["nombre"], o["par"], o["tipo"], o["motivo"], razon))
    print(f"{a['nombre']}: orden de {o['tipo']} {o['par']} no ejecutada ({razon})")


def ejecutar_pendientes(a, aperturas, volumenes):
    """Ejecuta las ordenes decididas con el cierre de una vela a la APERTURA de la siguiente vela con precio (ejecucion.py).
    Si esa apertura aun no existe (la vela siguiente no ha empezado a negociarse), la orden queda pendiente en el estado."""
    resto = []
    for o in a.get("pendientes", []):
        tss = aperturas.get(o["par"], ([], {}))
        k = bisect.bisect_right(tss[0], o["vela_ts"])
        if k >= len(tss[0]):
            resto.append(o)                                          # aun no hay vela posterior
            continue
        ts_exec = tss[0][k]
        if ts_exec - o["vela_ts"] > MAX_ESPERA_ORDEN:
            rechazar(a, o, "caducada: sin precio de ejecucion en 6 horas")
            continue
        px = tss[1][ts_exec]
        par, tipo = o["par"], o["tipo"]
        if a["apagado"]:
            rechazar(a, o, "agente apagado por riesgo")
        elif tipo == "COMPRA":
            if par in a["posiciones"]:
                rechazar(a, o, "ya hay posicion en esa moneda")
            elif len(a["posiciones"]) >= MAX_POS:
                rechazar(a, o, "maximo de posiciones alcanzado")
            elif a["efectivo"] < SLOT * 0.5:
                rechazar(a, o, "efectivo insuficiente")
            elif par in BLOQUEADOS:
                rechazar(a, o, "datos anomalos en esa moneda")
            else:
                fecha = iso_vela(o["vela_ts"])
                operar(a, "COMPRA", par, px, fecha, volumenes, o["motivo"])
        else:
            if par not in a["posiciones"]:
                rechazar(a, o, "ya no hay posicion que vender")
            else:
                fecha = iso_vela(o["vela_ts"])
                operar(a, "VENTA", par, px, fecha, volumenes, o["motivo"])
    a["pendientes"] = resto


def paso(estado, velas, volumenes, orden, ahora_ts):
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    RECHAZOS.clear()
    cierres, indice, cerr_por_t, series, aperturas = {}, {}, {}, {}, {}
    for par, v in velas.items():
        cer = [c for c in v if c.ts + 3600 <= ahora_ts]          # solo velas ya cerradas
        cierres[par] = [c.c for c in cer]
        series[par] = estrategias.Serie(cierres[par])       # medias precalculadas; la senal en i solo mira hasta i
        aperturas[par] = ([c.ts for c in v], {c.ts: c.o for c in v})    # TODAS las velas (tambien la abierta): su apertura ya es un hecho
        for i, x in enumerate(cer):
            t = x.ts
            indice[(par, t)] = i
            if t > estado["ultima_vela"]:
                cerr_por_t.setdefault(t, []).append(par)
    tiempos = sorted(cerr_por_t)
    if len(tiempos) > 1:
        print(f"Aviso: {len(tiempos)} velas nuevas (la ejecucion anterior se retraso); se procesan todas en orden.")
    precios = estado["precios"]
    rango = {p: i for i, p in enumerate(orden)}
    for a in estado["agentes"]:                          # ordenes que quedaron pendientes de una ejecucion anterior
        a.setdefault("pendientes", [])
        ejecutar_pendientes(a, aperturas, volumenes)
    for t in tiempos:
        fecha = iso_vela(t)
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
            op = OPCIONES.get(a["nombre"], {})
            senales = {par: decidir(series[par], indice[(par, t)], 1.0) for par in pares_t}
            nuevas = a.setdefault("pendientes", [])
            en_cola = {(o["par"], o["tipo"]) for o in nuevas}

            def pedir(par, tipo, motivo):
                if (par, tipo) not in en_cola:
                    nuevas.append({"par": par, "tipo": tipo, "motivo": motivo, "vela_ts": t})
                    en_cola.add((par, tipo))
            for par in pares_t:                          # primero se decide vender (stop y objetivo, y luego la senal vendedora)...
                if par not in a["posiciones"]:
                    continue
                entrada = a.get("entradas", {}).get(par)
                cambio = precios[par] / entrada - 1 if entrada else 0.0
                if op.get("stop") and entrada and cambio <= -op["stop"]:
                    pedir(par, "VENTA", f"stop de perdida ({cambio * 100:.1f} %)")
                elif op.get("objetivo") and entrada and cambio >= op["objetivo"]:
                    pedir(par, "VENTA", f"objetivo de ganancia ({cambio * 100:+.1f} %)")
                elif senales[par] == "s":
                    pedir(par, "VENTA", "senal vendedora")
            bloqueado = a["eq_dia"] - equity(a, precios) >= PERDIDA_DIA
            compras = sum(1 for o in nuevas if o["tipo"] == "COMPRA")
            for par in pares_t:                          # ...y luego se decide comprar, por orden de volumen
                if senales[par] == "b" and par not in a["posiciones"] and (par, "COMPRA") not in en_cola:
                    if par in BLOQUEADOS:
                        continue                         # salto anomalo en los datos: no se abre posicion nueva
                    if len(a["posiciones"]) + compras >= MAX_POS or a["efectivo"] - compras * SLOT < SLOT * 0.5:
                        break
                    if bloqueado:
                        print(f"{a['nombre']}: compra bloqueada por el limite de perdida diaria")
                        break
                    if op.get("solo_liquidas") and par != BTC and volumenes.get(par, 0) < VOLUMEN_ALTO:
                        continue                         # moneda de poco volumen: no se opera
                    uv = a.get("ultima_venta", {}).get(par)
                    if op.get("espera_h") and uv and (datetime.fromisoformat(fecha) - datetime.fromisoformat(uv)).total_seconds() < op["espera_h"] * 3600:
                        continue                         # vendida hace poco: se espera antes de volver a entrar
                    if preparar_orden(a, "COMPRA", par, precios[par], volumenes)[1]:
                        continue                         # no cumple los minimos del exchange con un slot tan pequeno: ni se intenta
                    pedir(par, "COMPRA", "senal compradora")
                    compras += 1
            ejecutar_pendientes(a, aperturas, volumenes)  # a la apertura de la vela siguiente, si ya existe
            apagar_si_toca(a, precios, fecha, volumenes)
    if tiempos:
        estado["ultima_vela"] = tiempos[-1]
    for par, v in velas.items():                        # precio actual (la ultima vela puede seguir abierta)
        precios[par] = v[-1].c
    ultima = {par: iso_vela(v[-1].ts) for par, v in velas.items()}
    for a in estado["agentes"]:
        apagar_si_toca(a, precios, ahora, volumenes, ultima)
    return ahora, precios


def nombre_corto(par):
    return par[:-3] if par.endswith("EUR") else par


CAB_INCIDENCIAS = ["fecha_utc", "par", "tipo", "nivel", "vela_ts", "detalle"]


def ruta_incidencias():
    return os.path.join(DATOS, "incidencias_datos.csv")


def incidencias_nuevas(ahora):
    """Filas de incidencias aun no registradas (la misma vela con el mismo problema se descarga cada hora: no se repite)."""
    vistas = set()
    if os.path.exists(ruta_incidencias()):
        with open(ruta_incidencias(), newline="", encoding="utf-8") as f:
            vistas = {(r["par"], r["tipo"], r["vela_ts"]) for r in csv.DictReader(f)}
    filas = []
    for par, i in INCIDENCIAS:
        clave = (par, i["tipo"], str(i["ts"]))
        if clave in vistas:
            continue
        vistas.add(clave)
        extra = {k: v for k, v in i.items() if k not in ("tipo", "ts", "nivel")}
        filas.append([ahora, par, i["tipo"], i["nivel"], i["ts"], json.dumps(extra, ensure_ascii=False) if extra else ""])
    return filas


def historial_con_fila(cabecera, fila):
    """Texto completo del historial con la fila nueva. Si se anadieron agentes, las filas viejas se rellenan con START."""
    filas = list(csv.reader(io.StringIO(leer_texto(HISTORIAL), newline="")))
    if not filas:
        filas = [cabecera]
    elif filas[0] != cabecera:
        viejas = filas[0]
        filas = [cabecera] + [[dict(zip(viejas, f)).get(c, str(START)) for c in cabecera] for f in filas[1:]]
        print("Historial ampliado con las columnas de los agentes nuevos.")
    filas.append(fila)
    return texto_csv(filas)


def guardar(estado, ahora, precios, fuente, n_monedas, n_con_datos):
    os.makedirs(DATOS, exist_ok=True)
    asegurar_operaciones()
    precio = precios[BTC]
    eqs = [equity(a, precios) for a in estado["agentes"]]
    mantener = START * (1 - FEE) * precio / ejecucion.precio_compra(estado["precio_inicio"], SLIP, SPREAD)
    eq_por_nombre = {a["nombre"]: e for a, e in zip(estado["agentes"], eqs)}
    cab_hist = ["fecha_utc", "precio_eur"] + [n for n, _ in AGENTES] + ["Comprar y mantener"]
    fila = [ahora, round(precio, 2)] + [round(eq_por_nombre[n], 2) for n, _ in AGENTES] + [round(mantener, 2)]
    tx = ps.Transaccion(DATOS)                    # estado + historial + operaciones cambian juntos o no cambian
    ops = leer_texto(OPERACIONES) or texto_csv([CAB_OPERACIONES])
    tx.poner(OPERACIONES, ops + texto_csv(COLA_OPS))
    tx.poner(HISTORIAL, historial_con_fila(cab_hist, fila))
    tx.poner(ESTADO, json.dumps(estado, indent=2))
    if REGLAS:
        vigiladas = {p: REGLAS[p]._asdict() for p in sorted(set(estado["precios"]) | set(p for a in estado["agentes"] for p in a["posiciones"])) if p in REGLAS}
        tx.poner(os.path.join(DATOS, "reglas_mercado.json"), json.dumps({"generado": ahora, "reglas": vigiladas}, indent=1, ensure_ascii=False) + "\n")
    nuevas = incidencias_nuevas(ahora)
    if nuevas:
        previo = leer_texto(ruta_incidencias()) or texto_csv([CAB_INCIDENCIAS])
        tx.poner(ruta_incidencias(), previo + texto_csv(nuevas))
    tx.confirmar()
    COLA_OPS.clear()
    dias = (datetime.fromisoformat(ahora) - datetime.fromisoformat(estado["inicio"])).total_seconds() / 86400
    lineas = [
        "# Oficina de agentes (dinero ficticio)",
        "",
        f"Ultima actualizacion: {ahora} UTC · Precio BTC/EUR: {precio:.0f} ({fuente})",
        f"En marcha desde: {estado['inicio']} UTC ({dias:.1f} dias)",
        f"Monedas vigiladas: las {n_monedas} de mayor volumen contra EUR (con datos en esta ejecucion: {n_con_datos}) · "
        f"cada agente puede tener hasta {MAX_POS} a la vez, {SLOT:.2f} EUR en cada una",
        f"Costes simulados por operacion: comision {FEE * 100:.2f} % + horquilla {SPREAD * 100:.2f} % + deslizamiento {SLIP * 100:.2f} % "
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
        hold_a = START * (1 - FEE) * precio / ejecucion.precio_compra(a["precio_inicio"], SLIP, SPREAD)   # mantener BTC desde que empezo ESTE agente
        lineas.append(f"| {a['nombre']} | {e:.2f} | {e - START:+.2f} | {(e / START - 1) * 100:+.2f} % | {e - hold_a:+.2f} | "
                      f"{a['operaciones']} | {a['inicio'][:10]} | {est} |")
    lineas.append(f"| Comprar y mantener (solo BTC) | {mantener:.2f} | {mantener - START:+.2f} | {(mantener / START - 1) * 100:+.2f} % | 0.00 | 1 | {estado['inicio'][:10]} | Referencia |")
    nombres = [n for n, _ in AGENTES]
    sin_verificar = [p for p in estado["precios"] if regla(p).fuente != "kraken"]
    if sin_verificar:
        lineas += ["", f"⚠ Minimos del exchange NO verificados para {len(sin_verificar)} moneda(s) (se usa un supuesto de 0,5 EUR de coste minimo): "
                   + ", ".join(nombre_corto(p) for p in sin_verificar[:10]) + ("…" if len(sin_verificar) > 10 else "") + "."]
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
    ps.escribir_atomico(RESUMEN, "\n".join(lineas) + "\n")
    print("\n".join(lineas[4:]))


CONTEXTO = ("director_estado.json", "parte_director.json", "laboratorio.json", "memoria.jsonl", "propuestas.md")


def archivar(etiqueta, meta=None):
    """Archivo verificable (con manifiesto y huellas) de la simulacion anterior en datos/archivo_<etiqueta>_<fecha>/.
    Los archivos del director y del laboratorio se COPIAN como contexto; los de la simulacion se borran solo tras verificar."""
    mover = [ESTADO, HISTORIAL, OPERACIONES, RESUMEN, GRAFICO]
    contexto = [os.path.join(DATOS, c) for c in CONTEXTO]
    return archivado.archivar(DATOS, etiqueta, mover, contexto, meta)


def main():
    demo = int(sys.argv[sys.argv.index("--demo") + 1]) if "--demo" in sys.argv else 0
    os.makedirs(DATOS, exist_ok=True)
    rec = ps.recuperar(DATOS)
    if rec != "nada":
        print(f"Se encontro una escritura interrumpida de la ejecucion anterior: {rec}.")
    velas, volumenes, orden, fuente, ahora_ts = obtener_datos(demo)
    if os.path.exists(ESTADO):
        with open(ESTADO) as f:
            estado = json.load(f)
        cap_ant, ver_ant = estado.get("capital_inicial", 50.0), estado.get("version", 1)
        if cap_ant != START or ver_ant != VERSION:
            archivar(f"{cap_ant:g}eur" if cap_ant != START else f"{cap_ant:g}eur_v{ver_ant}",
                     {"motivo": "cambio de capital o de reglas", "capital_anterior": cap_ant, "version_anterior": ver_ant,
                      "capital_nuevo": START, "version_nueva": VERSION})
            estado = estado_nuevo(velas, ahora_ts)
            print("Cambio de capital o de reglas: simulacion anterior archivada; los agentes empiezan ahora con", START, "EUR ficticios cada uno.")
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
