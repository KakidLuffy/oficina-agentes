"""
Extras del resumen (solo libreria estandar de Python): grafico SVG y metricas de riesgo.
Lee datos/historial.csv y datos/operaciones.csv; no modifica el estado de la simulacion.
"""
import csv
import os

COLORES = ["#2563eb", "#16a34a", "#f59e0b", "#a855f7", "#6b7280"]   # 4 agentes + Comprar y mantener


def leer_csv(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, newline="") as f:
        return list(csv.DictReader(f))


def caida_maxima(valores):
    """Mayor caida (en %) desde un maximo anterior hasta un minimo posterior."""
    pico, peor = None, 0.0
    for v in valores:
        pico = v if pico is None else max(pico, v)
        if pico > 0:
            peor = min(peor, v / pico - 1)
    return peor * 100


def metricas(historial_csv, operaciones_csv, nombres):
    """Devuelve {nombre: (caida_maxima_pct, ganadoras, perdedoras)}."""
    hist, ops = leer_csv(historial_csv), leer_csv(operaciones_csv)
    salida = {}
    for n in nombres:
        serie = [float(f[n]) for f in hist if f.get(n)]
        gan = per = 0
        compras = {}                                   # importe de la ultima compra abierta de cada moneda
        for o in sorted((o for o in ops if o["agente"] == n), key=lambda o: o["fecha_utc"]):
            moneda = o.get("moneda", "BTC")
            if o["tipo"] == "COMPRA":
                compras[moneda] = float(o["importe_eur"])
            elif o["tipo"] == "VENTA" and compras.get(moneda):
                if float(o["importe_eur"]) > compras[moneda]:
                    gan += 1
                else:
                    per += 1
                compras.pop(moneda)
        salida[n] = (caida_maxima(serie) if serie else 0.0, gan, per)
    return salida


def grafico_svg(historial_csv, ruta_svg, nombres):
    """Dibuja la evolucion del capital de cada agente y de 'Comprar y mantener'."""
    hist = leer_csv(historial_csv)
    if len(hist) < 2:
        return False
    cols = list(nombres) + ["Comprar y mantener"]
    series = {c: [float(f[c]) for f in hist] for c in cols}
    todos = [v for s in series.values() for v in s]
    lo, hi = min(todos), max(todos)
    if hi - lo < 0.5:                       # evita un eje plano si casi no hay movimiento
        centro = (hi + lo) / 2
        lo, hi = centro - 0.25, centro + 0.25
    ancho, alto, mi, md, ms, mb = 760, 360, 60, 150, 20, 40
    n = len(hist)

    def x(i):
        return mi + (ancho - mi - md) * (i / (n - 1))

    def y(v):
        return ms + (alto - ms - mb) * (1 - (v - lo) / (hi - lo))

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" '
         f'font-family="sans-serif" font-size="12">',
         f'<rect width="{ancho}" height="{alto}" fill="white"/>']
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        p.append(f'<line x1="{mi}" x2="{ancho - md}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e5e7eb"/>')
        p.append(f'<text x="{mi - 6}" y="{y(v) + 4:.1f}" text-anchor="end" fill="#374151">{v:.2f}</text>')
    p.append(f'<text x="{mi}" y="{alto - 10}" fill="#374151">{hist[0]["fecha_utc"][:16]}</text>')
    p.append(f'<text x="{ancho - md}" y="{alto - 10}" text-anchor="end" fill="#374151">{hist[-1]["fecha_utc"][:16]}</text>')
    p.append(f'<text x="{mi}" y="14" fill="#111827" font-weight="bold">Capital en EUR (dinero ficticio)</text>')
    for k, c in enumerate(cols):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(series[c]))
        dash = ' stroke-dasharray="5 4"' if c == "Comprar y mantener" else ""
        p.append(f'<polyline points="{pts}" fill="none" stroke="{COLORES[k]}" stroke-width="2"{dash}/>')
        ly = ms + 18 * k + 10
        p.append(f'<line x1="{ancho - md + 14}" x2="{ancho - md + 34}" y1="{ly}" y2="{ly}" stroke="{COLORES[k]}" '
                 f'stroke-width="2"{dash}/>')
        p.append(f'<text x="{ancho - md + 40}" y="{ly + 4}" fill="#111827">{c}</text>')
    p.append("</svg>")
    with open(ruta_svg, "w") as f:
        f.write("\n".join(p))
    return True
