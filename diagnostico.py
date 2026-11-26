#!/usr/bin/env python3
"""
DIAGNÓSTICO de la señal (CRITERIOS.md, sección 8). Dinero ficticio. Solo mide: no opera ni cambia a los agentes.

Responde a dos preguntas que el parte no contestaba:
  1. ¿El agente pierde menos que el mercado porque su señal acierta, o solo porque estaba en efectivo?  (§8.1)
  2. ¿Lo hace mejor que un agente que hiciera las mismas operaciones pero entrando a una hora al azar?   (§8.2)

Escribe datos/diagnostico.json y datos/diagnostico.md, y guarda los precios de 1 h en datos/precios_1h.json.
Uso:  python diagnostico.py [--datos datos] [--sin-red]
"""
import csv
import json
import os
import random
import sys
import time
import urllib.request
from datetime import datetime, timezone

N_AZAR = 2000
SEMILLA = 20261126
HORA = 3600
REBALANCEO = "Rebalanceo semanal"
REF_CESTA = "Comprar y mantener (cesta)"
REF_BTC = "Comprar y mantener"
SIEMPRE = ("XBTEUR", "ETHEUR")


# ---------------- lectura ----------------
def ts(fecha):
    d = datetime.fromisoformat(fecha.strip().replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return int(d.timestamp())


def leer_json(ruta, defecto=None):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def leer_csv(ruta):
    try:
        with open(ruta, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


# ---------------- precios de 1 h (Kraken, con memoria) ----------------
def velas_kraken_1h(par):
    """Últimas 720 velas de 1 h de Kraken: {inicio de la vela: cierre}. La última puede seguir abierta."""
    url = f"https://api.kraken.com/0/public/OHLC?pair={par}&interval=60"
    for intento in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": "oficina-agentes/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        if not d.get("error"):
            res = d["result"]
            clave = [k for k in res if k != "last"][0]
            return {int(v[0]): float(v[4]) for v in res[clave]}
        if intento < 3 and any("Rate limit" in e or "Too many" in e for e in d["error"]):
            time.sleep(5 * (intento + 1))
            continue
        raise RuntimeError(d["error"])


def actualizar_precios(ruta, pares, descargar=velas_kraken_1h):
    """Mezcla lo descargado con lo guardado (Kraken solo da 30 días de velas de 1 h)."""
    guardado = leer_json(ruta, {}) or {}
    series = {p: {int(t): float(c) for t, c in guardado.get(p, {}).items()} for p in guardado}
    fallos = []
    for par in pares:
        if descargar is None:
            continue
        try:
            series.setdefault(par, {}).update(descargar(par))
        except Exception as e:                      # sin red o Kraken caído: se sigue con lo guardado
            fallos.append(f"{par}: {e}")
        time.sleep(1.1 if descargar is velas_kraken_1h else 0)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({p: {str(t): c for t, c in sorted(s.items())} for p, s in sorted(series.items())}, f, separators=(",", ":"))
    return series, fallos


# ---------------- operaciones ----------------
def ida_vuelta(ops, nombre):
    """Empareja cada compra con su venta (misma moneda, en orden). Las que siguen abiertas quedan con salida None."""
    abiertas, salida = {}, []
    for o in ops:
        if o.get("agente") != nombre:
            continue
        m, t = o["moneda"], ts(o["fecha_utc"])
        if o["tipo"].upper().startswith("COMPRA"):
            abiertas.setdefault(m, []).append((t, float(o["importe_eur"])))
        elif abiertas.get(m):
            t0, q = abiertas[m].pop(0)
            salida.append({"moneda": m, "entrada": t0, "salida": t, "importe": q})
    for m, lista in abiertas.items():
        for t0, q in lista:
            salida.append({"moneda": m, "entrada": t0, "salida": None, "importe": q})
    return sorted(salida, key=lambda x: x["entrada"])


def exposicion(viajes, inicio, fin, capital):
    """Euros invertidos (a precio de compra) × horas, entre capital inicial × horas del periodo (§8.1)."""
    total = max(fin - inicio, HORA)
    usado = sum(v["importe"] * max(0, min(v["salida"] or fin, fin) - max(v["entrada"], inicio)) for v in viajes)
    return usado / (capital * total)


def resultado_viaje(importe, p0, p1, fee, slip):
    """Compra a p0 y vende a p1 pagando comisión y deslizamiento en las dos patas (igual que agentes_nube.operar)."""
    return importe * ((1 - fee) ** 2 * (1 - slip) / (1 + slip) * p1 / p0 - 1)


def precio_en(serie, t, tolerancia=2 * HORA):
    """Cierre de la vela que empieza en t; si falta, el de la vela anterior más cercana (hasta 2 h antes)."""
    for k in range(0, tolerancia + 1, HORA):
        if t - k in serie:
            return serie[t - k]
    return None


# ---------------- comparación con entradas al azar (§8.2) ----------------
def comparar_azar(viajes, series, inicio, fin, fee, slip, n=N_AZAR, semilla=SEMILLA):
    """Devuelve (resultado real recalculado, lista de n resultados al azar, operaciones usadas, sin precio)."""
    usados, sin_precio, real = [], 0, 0.0
    ultimo = {p: max((t for t in s if t <= fin), default=None) for p, s in series.items()}
    for v in viajes:
        s = series.get(v["moneda"], {})
        t0 = v["entrada"] // HORA * HORA
        t1 = (v["salida"] // HORA * HORA) if v["salida"] else ultimo.get(v["moneda"])
        p0 = precio_en(s, t0)
        p1 = precio_en(s, t1) if t1 is not None else None
        if p0 is None or p1 is None or t1 < t0:
            sin_precio += 1
            continue
        horas = (t1 - t0) // HORA
        real += resultado_viaje(v["importe"], p0, p1, fee, slip)
        usados.append((v["moneda"], v["importe"], horas))
    huecos = {}
    for m, _, h in usados:                    # horas de entrada posibles para cada (moneda, duración)
        if (m, h) not in huecos:
            s = series[m]
            ini = inicio // HORA * HORA
            huecos[(m, h)] = [t for t in sorted(s) if t >= ini and t + h * HORA <= (ultimo[m] or 0) and t + h * HORA in s]
    rng = random.Random(semilla)
    azar = []
    for _ in range(n):
        r = 0.0
        for m, q, h in usados:
            op = huecos[(m, h)]
            if not op:
                continue
            t = op[rng.randrange(len(op))]
            r += resultado_viaje(q, series[m][t], series[m][t + h * HORA], fee, slip)
        azar.append(r)
    return real, azar, len(usados), sin_precio


def percentil(real, azar):
    if not azar:
        return None
    peor = sum(1 for x in azar if x < real - 1e-12)
    igual = sum(1 for x in azar if abs(x - real) <= 1e-12)
    return (peor + 0.5 * igual) / len(azar)


def cuantil(lista, q):
    s = sorted(lista)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))] if s else None


# ---------------- informe ----------------
def eur(v, signo=True):
    return (f"{v:+.2f}" if signo else f"{v:.2f}").replace(".", ",") + " €"


def pct(v):
    return f"{v * 100:.0f} %"


def diagnosticar(carpeta, descargar=velas_kraken_1h, ahora=None, n=N_AZAR):
    estado = leer_json(os.path.join(carpeta, "estado.json"))
    if not estado:
        raise SystemExit("No hay estado.json: nada que diagnosticar.")
    ops = leer_csv(os.path.join(carpeta, "operaciones.csv"))
    hist = leer_csv(os.path.join(carpeta, "historial_v2.csv"))
    capital = float(estado.get("capital_inicial", 10.0))
    fee, slip = float(estado.get("fee", 0.004)), float(estado.get("slip", 0.0005))
    inicio = ts(estado["inicio"])
    fin = int(ahora if ahora is not None else time.time())
    precios = estado.get("precios", {})
    agentes = estado.get("agentes", [])
    senal = [a for a in agentes if a.get("nombre") != REBALANCEO]
    nombres = {a["nombre"] for a in senal}
    pares = sorted(set(SIEMPRE) | {o["moneda"] for o in ops if o.get("agente") in nombres})
    series, fallos = actualizar_precios(os.path.join(carpeta, "precios_1h.json"), pares, descargar)

    ult = hist[-1] if hist else {}
    mercado = float(ult[REF_CESTA]) - capital if ult.get(REF_CESTA) not in (None, "") else None
    btc = float(ult[REF_BTC]) - capital if ult.get(REF_BTC) not in (None, "") else None

    filas = []
    for a in senal:
        eq = a.get("efectivo", 0.0) + sum(u * precios.get(p, 0.0) for p, u in (a.get("posiciones") or {}).items())
        res = eq - capital
        viajes = ida_vuelta(ops, a["nombre"])
        e = exposicion(viajes, inicio, fin, capital)
        fila = {"nombre": a["nombre"], "resultado": round(res, 4), "exposicion": round(e, 4),
                "operaciones": len(viajes), "cerradas": sum(1 for v in viajes if v["salida"])}
        if mercado is not None:
            fila["efecto_fuera"] = round(e * mercado - mercado, 4)
            fila["efecto_senal"] = round(res - e * mercado, 4)
        if viajes:
            real, azar, usados, sin_p = comparar_azar(viajes, series, inicio, fin, fee, slip, n=n)
            fila["azar"] = {"resultado_recalculado": round(real, 4), "percentil": percentil(real, azar),
                            "mediana": round(cuantil(azar, 0.5), 4), "p5": round(cuantil(azar, 0.05), 4),
                            "p95": round(cuantil(azar, 0.95), 4), "operaciones_usadas": usados, "sin_precio": sin_p}
        filas.append(fila)

    salida = {"generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "criterios": "CRITERIOS.md §8",
              "desde": estado["inicio"], "dias": round((fin - inicio) / 86400, 1), "n_azar": n, "semilla": SEMILLA,
              "mercado_cesta": None if mercado is None else round(mercado, 4),
              "mercado_btc": None if btc is None else round(btc, 4),
              "fallos_precios": fallos, "agentes": filas}
    with open(os.path.join(carpeta, "diagnostico.json"), "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    with open(os.path.join(carpeta, "diagnostico.md"), "w", encoding="utf-8") as f:
        f.write(informe_md(salida))
    return salida


def informe_md(d):
    m = d["mercado_cesta"]
    md = ["# Diagnóstico de la señal (dinero ficticio)", "",
          f"Actualizado: {d['generado']} · {d['dias']} días desde el inicio de la v5 · reglas: {d['criterios']}", ""]
    if m is not None:
        md += [f"Mercado («Comprar y mantener (cesta)», BTC y ETH a partes iguales): {eur(m)}.", ""]
    md += ["| Agente | Resultado | Tiempo invertido | Efecto de estar fuera | Efecto de la señal | "
           "Mejor que el azar | Azar: típico (5 %–95 %) | Cerradas |",
           "|---|---:|---:|---:|---:|---:|---|---:|"]
    for f in d["agentes"]:
        az = f.get("azar")
        p = pct(az["percentil"]) if az and az.get("percentil") is not None else "—"
        rango = f"{eur(az['mediana'])} ({eur(az['p5'])} a {eur(az['p95'])})" if az else "—"
        fuera = eur(f["efecto_fuera"]) if "efecto_fuera" in f else "—"
        senal = eur(f["efecto_senal"]) if "efecto_senal" in f else "—"
        md.append(f"| {f['nombre']} | {eur(f['resultado'])} | {pct(f['exposicion'])} | {fuera} | {senal} | {p} | {rango} | {f['cerradas']} |")
    md += ["",
           "Cómo leerlo:",
           "- **Efecto de estar fuera**: lo que se ahorra (o se pierde) por no estar invertido todo el tiempo. En un mercado que cae es positivo aunque la señal no sirva.",
           "- **Efecto de la señal**: resultado del agente menos el de mantener la cesta con su mismo tiempo invertido. Es lo que dice si la señal acierta.",
           f"- **Mejor que el azar**: qué parte de {d['n_azar']} agentes al azar, con las mismas operaciones (moneda, importe, duración y costes) pero entrando a una hora al azar, lo hacen peor. 50 % = como tirar una moneda.",
           "- El resultado de la comparación con el azar se recalcula con cierres de 1 h, así que puede diferir unos céntimos del resultado de la tabla.",
           "",
           "⚠ Con menos de 30 operaciones cerradas todo esto es orientativo. No es un criterio de aprobado: el umbral lo fija el usuario y se registrará en CRITERIOS.md antes de evaluar.",
           "El Rebalanceo semanal no aparece: está casi siempre invertido y se compara con su propia referencia (CRITERIOS.md §6)."]
    if d["fallos_precios"]:
        md += ["", "Precios no descargados esta vez (se usaron los guardados): " + "; ".join(d["fallos_precios"])]
    return "\n".join(md) + "\n"


def main():
    carpeta = sys.argv[sys.argv.index("--datos") + 1] if "--datos" in sys.argv else "datos"
    d = diagnosticar(carpeta, descargar=None if "--sin-red" in sys.argv else velas_kraken_1h)
    print(informe_md(d))


if __name__ == "__main__":
    main()
