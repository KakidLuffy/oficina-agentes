#!/usr/bin/env python3
"""
DIRECTOR de la oficina (dinero ficticio, solo lee y resume; no opera ni cambia a los agentes).

Cada vez que termina la simulación o el laboratorio, el director:
  1. REVISA los datos (revisor): frescura, coherencia de cuentas, precios raros, límites.
  2. ESCRIBE el parte del día (datos/parte_director.json y .md) que muestra el panel.
  3. ANOTA en la memoria compartida (datos/memoria.jsonl y memoria.md) las decisiones y cambios.
  4. PREPARA las propuestas del laboratorio (datos/propuestas.md) para que las apruebes tú.

No usa claves ni servicios de pago. Uso:  python director.py [--datos datos]
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone

START = 50.0  # valor por defecto; se lee de estado.json (capital_inicial)
MAX_POS = 5
STOP = 35.0
MIN_DIAS, MIN_CIERRES = 21, 30
MAX_EVENTOS_MD = 40

REGLAS = [
    "Todo es una simulación con dinero ficticio: nunca se opera con dinero real ni se suben claves o contraseñas al repositorio.",
    f"Un agente solo es evaluable con al menos {MIN_DIAS} días de simulación y {MIN_CIERRES} operaciones cerradas.",
    "Un agente solo tiene ventaja si supera a «Comprar y mantener» de forma sostenida, después de costes.",
    "Las candidatas del laboratorio no operan solas: se añaden como agente nuevo solo si el usuario las aprueba.",
    "Un agente se apaga si pierde el 30 % de su capital inicial y no compra más ese día si pierde el 4 % en un día.",
]


def ahora():
    return datetime.now(timezone.utc)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_fecha(t):
    t = (t or "").strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


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


def num(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def euros(v, signo=False):
    s = f"{v:+.2f}" if signo else f"{v:.2f}"
    return s.replace(".", ",") + " €"


# ---------------- análisis ----------------
def capital_agente(a, precios):
    eq = num(a.get("efectivo"))
    for mon, q in (a.get("posiciones") or {}).items():
        eq += num(q) * num(precios.get(mon))
    return eq


def caida_maxima(serie):
    pico, dd = 0.0, 0.0
    for v in serie:
        pico = max(pico, v)
        if pico > 0:
            dd = max(dd, (pico - v) / pico * 100)
    return dd


def cierres_por_agente(ops):
    c = {}
    for o in ops:
        if (o.get("tipo") or "").upper().startswith("VENTA"):
            c[o.get("agente")] = c.get(o.get("agente"), 0) + 1
    return c


def revisar(estado, hist, ops, precios, ag, ref):
    """El revisor: devuelve una lista de problemas {nivel, texto}. Nivel: error | aviso."""
    p = []
    if not estado:
        return [{"nivel": "error", "texto": "No se puede leer estado.json: la simulación no ha guardado datos."}]
    if not hist:
        p.append({"nivel": "error", "texto": "El historial está vacío o no se puede leer."})
    else:
        ult = parse_fecha(hist[-1].get("fecha_utc"))
        if ult:
            h = (ref - ult).total_seconds() / 3600
            if h > 6:
                p.append({"nivel": "error", "texto": f"Los datos llevan {h:.0f} h sin actualizarse. Revisa la pestaña Actions de GitHub."})
            elif h > 3:
                p.append({"nivel": "aviso", "texto": f"Los datos llevan {h:.1f} h sin actualizarse (GitHub a veces se retrasa).".replace(".", ",")})
        nombres = [c for c in hist[-1].keys() if c not in ("fecha_utc", "precio_eur", "Comprar y mantener")]
        faltan = [a["nombre"] for a in ag if a["nombre"] not in nombres]
        if faltan:
            p.append({"nivel": "aviso", "texto": "Agentes sin columna en el historial: " + ", ".join(faltan) + "."})
        if len(hist) >= 2:
            a, b = num(hist[-2].get("precio_eur")), num(hist[-1].get("precio_eur"))
            if a > 0 and abs(b / a - 1) > 0.2:
                p.append({"nivel": "aviso", "texto": f"El precio de BTC saltó un {abs(b / a - 1) * 100:.0f} % entre las dos últimas lecturas."})
        suma_est = sum(x["eq"] for x in ag)
        suma_his = sum(num(hist[-1].get(x["nombre"])) for x in ag if hist[-1].get(x["nombre"]) not in (None, ""))
        if suma_his and abs(suma_est - suma_his) > 1.0:
            p.append({"nivel": "aviso", "texto": f"La suma de capitales del estado ({euros(suma_est)}) no coincide con el historial ({euros(suma_his)})."})
    malos = [m for m, v in precios.items() if num(v) <= 0]
    if malos:
        p.append({"nivel": "error", "texto": "Precios no válidos en: " + ", ".join(m.replace("EUR", "") for m in malos) + "."})
    for x in ag:
        if num(x["raw"].get("efectivo")) < -0.01:
            p.append({"nivel": "error", "texto": f"{x['nombre']} tiene efectivo negativo."})
        if len(x["raw"].get("posiciones") or {}) > MAX_POS:
            p.append({"nivel": "error", "texto": f"{x['nombre']} tiene más de {MAX_POS} monedas a la vez."})
    return p


def main():
    carpeta = sys.argv[sys.argv.index("--datos") + 1] if "--datos" in sys.argv else "datos"
    os.makedirs(carpeta, exist_ok=True)
    ref = ahora()
    estado = leer_json(os.path.join(carpeta, "estado.json"))
    global START, STOP
    try:
        START = float((estado or {}).get("capital_inicial") or START)
    except (TypeError, ValueError):
        pass
    STOP = START * 0.7
    hist = leer_csv(os.path.join(carpeta, "historial_v2.csv")) or leer_csv(os.path.join(carpeta, "historial.csv"))
    ops = leer_csv(os.path.join(carpeta, "operaciones.csv"))
    lab = leer_json(os.path.join(carpeta, "laboratorio.json"))
    prev = leer_json(os.path.join(carpeta, "director_estado.json"), {}) or {}
    eventos = []
    try:
        with open(os.path.join(carpeta, "memoria.jsonl"), encoding="utf-8") as f:
            eventos = [json.loads(l) for l in f if l.strip()]
    except (OSError, ValueError):
        eventos = []
    nuevos = []

    def anotar(tipo, texto, agente=""):
        nuevos.append({"fecha": iso(ref), "tipo": tipo, "agente": agente, "texto": texto})

    if not eventos:
        for r in REGLAS:
            nuevos.append({"fecha": iso(ref), "tipo": "regla", "agente": "", "texto": r})

    precios = (estado or {}).get("precios", {})
    ag = []
    for a in (estado or {}).get("agentes", []):
        eq = capital_agente(a, precios)
        ag.append({"nombre": a.get("nombre", "?"), "eq": eq, "res": eq - START, "apagado": bool(a.get("apagado")),
                   "pos": [m.replace("EUR", "") for m in (a.get("posiciones") or {}).keys()],
                   "ops": int(num(a.get("operaciones"))), "inicio": parse_fecha(a.get("inicio")), "raw": a})
    cierres = cierres_por_agente(ops)
    ult = hist[-1] if hist else {}
    hold = num(ult.get("Comprar y mantener"), None) if ult else None
    for x in ag:
        serie = [num(h.get(x["nombre"])) for h in hist if h.get(x["nombre"]) not in (None, "")]
        x["dd"] = caida_maxima(serie)
        x["dias"] = max(0.0, (ref - x["inicio"]).total_seconds() / 86400) if x["inicio"] else 0.0
        x["cierres"] = cierres.get(x["nombre"], 0)
        x["vs_mantener"] = (x["eq"] - hold) if hold is not None else None
        x["evaluable"] = x["dias"] >= MIN_DIAS and x["cierres"] >= MIN_CIERRES

    problemas = revisar(estado, hist, ops, precios, ag, ref)
    errores = [p for p in problemas if p["nivel"] == "error"]
    conocidos = {e["texto"] for e in eventos[-30:] if e.get("tipo") == "revision"}
    for p in problemas:
        if p["texto"] not in conocidos:
            anotar("revision", p["texto"])

    total = sum(x["eq"] for x in ag)
    base = START * len(ag)
    res_total = total - base
    lineas, alertas = [], []
    if ag:
        mejor, peor = max(ag, key=lambda x: x["res"]), min(ag, key=lambda x: x["res"])
        lineas.append("Fondo de " + euros(base) + " (" + euros(START) + " por agente): vale " + euros(total) + " (" + euros(res_total, True) + ").")
        lineas.append("Capital total " + euros(total) + " (" + euros(res_total, True) + ", " + f"{res_total / base * 100:+.2f}".replace(".", ",") + " %).")
        lineas.append(f"Mejor agente: {mejor['nombre']} ({euros(mejor['res'], True)}). Peor: {peor['nombre']} ({euros(peor['res'], True)}).")
        if hold is not None:
            sup = [x for x in ag if x["vs_mantener"] is not None and x["vs_mantener"] > 0]
            lineas.append(f"{len(sup)} de {len(ag)} agentes van por encima de «Comprar y mantener» ({euros(hold)}).")
        activos = [x for x in ag if x["pos"] and not x["apagado"]]
        lineas.append(f"{len(activos)} con monedas, {len([x for x in ag if not x['pos'] and not x['apagado']])} en efectivo, {len([x for x in ag if x['apagado']])} apagados.")
        hace24 = ref - timedelta(hours=24)
        n24 = sum(1 for o in ops if (parse_fecha(o.get("fecha_utc")) or ref - timedelta(days=9999)) >= hace24)
        lineas.append(f"Operaciones en las últimas 24 h: {n24}.")
    for x in ag:
        if x["apagado"]:
            alertas.append(f"{x['nombre']} está apagado por riesgo.")
        elif x["eq"] < STOP + 5:
            alertas.append(f"{x['nombre']} está cerca del límite de {STOP:.0f} € ({euros(x['eq'])}).")
        elif x["dd"] >= 10:
            alertas.append(f"{x['nombre']} acumula una caída máxima del " + f"{x['dd']:.1f}".replace(".", ",") + " %.")

    # cambios y memoria
    ap_prev = set(prev.get("apagados", []))
    ap_now = {x["nombre"] for x in ag if x["apagado"]}
    if prev:
        for n in sorted(ap_now - ap_prev):
            anotar("decision", f"{n} se apaga por riesgo (capital bajo {STOP:.0f} €).", n)
        for n in sorted(ap_prev - ap_now):
            anotar("decision", f"{n} vuelve a estar activo.", n)
        for x in ag:
            if x["evaluable"] and x["nombre"] not in set(prev.get("evaluables", [])):
                anotar("hito", f"{x['nombre']} ya es evaluable ({x['dias']:.0f} días y {x['cierres']} cierres). Resultado actual {euros(x['res'], True)}.", x["nombre"])
    elif ag:
        anotar("hito", f"El director empieza a vigilar la oficina con {len(ag)} agentes.")

    # laboratorio y propuestas
    estados_user = {}
    try:
        with open(os.path.join(carpeta, "aprobaciones.txt"), encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if ":" in l and not l.startswith("#"):
                    k, v = l.split(":", 1)
                    estados_user[v.strip().lower()] = k.strip().lower()
    except OSError:
        pass
    prop_md = ["# Propuestas del laboratorio", "",
               "Las candidatas **no operan solas**. Para añadir una como agente nuevo en simulación, dile a Claude su nombre. "
               "Si prefieres dejar constancia aquí, crea el archivo `datos/aprobaciones.txt` con líneas como `aprobar: Cruce 15/20` o `rechazar: Rebote 20 velas 1.0 %`.", ""]
    veredicto = None
    semanas = prev.get("semanas_candidatas", {})
    if lab:
        veredicto = lab.get("veredicto")
        if lab.get("generado") != prev.get("lab_generado"):
            nombres = [c["nombre"] for c in lab.get("candidatas", [])]
            anotar("laboratorio", f"Laboratorio del {lab.get('generado', '')[:10]}: veredicto {str(veredicto).upper()}; candidatas: {', '.join(nombres) if nombres else 'ninguna'}.")
            semanas = {n: semanas.get(n, 0) + 1 for n in nombres}
        prop_md += [f"Último laboratorio: {lab.get('generado', '')} · veredicto **{str(veredicto).upper()}** · {lab.get('probadas', 0)} variantes probadas (el azar aprobaría el {round(num(lab.get('tasa_azar')) * 100)} %).", ""]
        if lab.get("candidatas"):
            prop_md += ["| Candidata | Analista | Dif. examen (€) | Series aprobadas | Semanas seguidas | Estado |", "|---|---|---:|---:|---:|---|"]
            for c in lab["candidatas"]:
                est = {"aprobar": "Aprobada", "rechazar": "Rechazada"}.get(estados_user.get(c["nombre"].lower(), ""), "Pendiente")
                prop_md.append(f"| {c['nombre']} | {c['analista']} | {num(c['test_dif']):+.2f} | {c['ok']}/{c['total']} | {semanas.get(c['nombre'], 1)} | {est} |")
                if est != "Pendiente" and prev.get("estado_prop", {}).get(c["nombre"]) != est:
                    anotar("decision", f"Candidata «{c['nombre']}»: {est.lower()} por el usuario.")
            prop_md += ["", "Una candidata solo merece atención si se repite varias semanas seguidas."]
        else:
            prop_md.append("No hay candidatas esta semana.")
    else:
        prop_md.append("El laboratorio aún no ha trabajado.")
    with open(os.path.join(carpeta, "propuestas.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(prop_md) + "\n")

    # memoria
    if nuevos:
        with open(os.path.join(carpeta, "memoria.jsonl"), "a", encoding="utf-8") as f:
            for e in nuevos:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        eventos += nuevos
    md = ["# Memoria compartida de la oficina", "",
          "Aquí quedan las reglas y las decisiones. El director y el laboratorio la leen para no empezar de cero cada vez.", "", "## Reglas fijas", ""]
    md += [f"- {e['texto']}" for e in eventos if e.get("tipo") == "regla"]
    md += ["", "## Registro de decisiones y cambios (lo más reciente primero)", ""]
    for e in [e for e in eventos if e.get("tipo") != "regla"][::-1][:MAX_EVENTOS_MD]:
        md.append(f"- {e['fecha'][:16].replace('T', ' ')} · **{e['tipo']}** · {e['texto']}")
    with open(os.path.join(carpeta, "memoria.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    # parte
    progreso = [{"nombre": x["nombre"], "dias": round(x["dias"], 1), "cierres": x["cierres"], "evaluable": x["evaluable"]} for x in ag]
    if errores:
        titular = "Hay un problema con los datos: revisa antes de fiarte de las cifras."
    elif alertas:
        titular = "Hay avisos de riesgo."
    else:
        titular = "Todo en orden."
    parte = {"generado": iso(ref), "titular": titular, "lineas": lineas, "alertas": alertas,
             "revision": {"ok": not errores, "problemas": problemas}, "progreso": progreso,
             "laboratorio": veredicto, "min_dias": MIN_DIAS, "min_cierres": MIN_CIERRES}
    with open(os.path.join(carpeta, "parte_director.json"), "w", encoding="utf-8") as f:
        json.dump(parte, f, ensure_ascii=False, indent=1)
    pm = ["# Parte del director", "", f"Actualizado: {parte['generado']}", "", f"**{titular}**", ""]
    pm += [f"- {l}" for l in lineas]
    if alertas:
        pm += ["", "Avisos:"] + [f"- {a}" for a in alertas]
    pm += ["", "Revisión de datos: " + ("sin errores." if not errores else "CON ERRORES.")]
    pm += [f"- ({p['nivel']}) {p['texto']}" for p in problemas]
    pm += ["", f"Progreso hacia la evaluación ({MIN_DIAS} días y {MIN_CIERRES} cierres):"]
    pm += [f"- {p['nombre']}: {p['dias']} días, {p['cierres']} cierres{' ✔ evaluable' if p['evaluable'] else ''}" for p in progreso]
    if veredicto:
        pm += ["", f"Laboratorio: {str(veredicto).upper()} (ver propuestas.md)."]
    with open(os.path.join(carpeta, "parte_director.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(pm) + "\n")
    with open(os.path.join(carpeta, "director_estado.json"), "w", encoding="utf-8") as f:
        json.dump({"apagados": sorted(ap_now), "evaluables": [x["nombre"] for x in ag if x["evaluable"]],
                   "lab_generado": (lab or {}).get("generado"), "semanas_candidatas": semanas,
                   "estado_prop": {c["nombre"]: {"aprobar": "Aprobada", "rechazar": "Rechazada"}.get(estados_user.get(c["nombre"].lower(), ""), "Pendiente")
                                   for c in (lab or {}).get("candidatas", [])}, "actualizado": iso(ref)}, f, ensure_ascii=False, indent=1)
    print("\n".join(pm))


if __name__ == "__main__":
    main()
