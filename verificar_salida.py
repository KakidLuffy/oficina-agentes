#!/usr/bin/env python3
"""Comprueba que los datos generados son coherentes antes de publicarlos. Sale con codigo 1 si algo falla.
Uso: python verificar_salida.py [carpeta_datos]"""
import csv
import json
import os
import sys

CAB_OPS = ["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"]


def comprobar(datos="datos"):
    problemas = []
    if os.path.exists(os.path.join(datos, ".tx")):
        problemas.append("queda una transaccion pendiente (.tx)")
    ruta = os.path.join(datos, "estado.json")
    if not os.path.exists(ruta):
        return problemas + ["falta estado.json"]
    try:
        with open(ruta, encoding="utf-8") as f:
            e = json.load(f)
    except ValueError as ex:
        return problemas + [f"estado.json no es JSON valido: {ex}"]
    for a in e.get("agentes", []):
        if a.get("efectivo", 0) < -1e-6:
            problemas.append(f"{a.get('nombre')}: efectivo negativo")
        for par, u in a.get("posiciones", {}).items():
            if not u > 0:
                problemas.append(f"{a.get('nombre')}: posicion no positiva en {par}")
    for nombre, cab in (("operaciones.csv", CAB_OPS), ("historial_v2.csv", None)):
        r = os.path.join(datos, nombre)
        if not os.path.exists(r):
            problemas.append(f"falta {nombre}")
            continue
        with open(r, newline="", encoding="utf-8") as f:
            filas = list(csv.reader(f))
        if not filas:
            problemas.append(f"{nombre} vacio")
        elif cab and filas[0] != cab:
            problemas.append(f"{nombre}: cabecera inesperada")
        elif any(len(x) != len(filas[0]) for x in filas[1:]):
            problemas.append(f"{nombre}: filas con numero de columnas distinto")
    return problemas


if __name__ == "__main__":
    p = comprobar(sys.argv[1] if len(sys.argv) > 1 else "datos")
    for x in p:
        print("ERROR:", x)
    print("Datos coherentes." if not p else f"{len(p)} problema(s).")
    sys.exit(1 if p else 0)
