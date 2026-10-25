"""
Archivado completo y verificable de una simulacion anterior (solo libreria estandar).

Pasos: 1) se COPIAN los archivos a una carpeta nueva (nunca se sobrescribe un archivo anterior)
       2) se comprueba que cada copia tiene la misma huella SHA-256 que el original
       3) se escribe MANIFIESTO.json (archivos, tamanos, huellas, filas, motivo, version, capital, fecha)
       4) solo entonces se borran los originales de la simulacion.
Si algo falla antes del paso 4, los originales siguen intactos y la carpeta a medias se marca como INCOMPLETA.
"""
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone

import persistencia as ps


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def filas_csv(ruta):
    if not ruta.endswith(".csv"):
        return None
    with open(ruta, "rb") as f:
        return max(0, sum(1 for _ in f) - 1)


def carpeta_libre(base, etiqueta, ahora):
    nombre = f"archivo_{etiqueta}_{ahora:%Y%m%d}"
    destino, n = os.path.join(base, nombre), 2
    while os.path.exists(destino):
        destino = os.path.join(base, f"{nombre}_{n}")
        n += 1
    return destino


def archivar(base, etiqueta, mover, copiar=(), meta=None, ahora=None):
    """mover: archivos de la simulacion (se borran tras verificar). copiar: archivos de contexto (se dejan en su sitio).
    Devuelve la carpeta creada, o None si no habia nada que archivar."""
    ahora = ahora or datetime.now(timezone.utc)
    existentes = [r for r in mover if os.path.exists(r)]
    if not existentes:
        return None
    destino = carpeta_libre(base, etiqueta, ahora)
    os.makedirs(destino)
    try:
        registro = []
        for ruta in list(existentes) + [c for c in copiar if os.path.exists(c)]:
            copia = os.path.join(destino, os.path.basename(ruta))
            shutil.copy2(ruta, copia)
            h = sha256(ruta)
            if sha256(copia) != h:
                raise OSError(f"la copia de {ruta} no coincide con el original")
            registro.append({"archivo": os.path.basename(ruta), "bytes": os.path.getsize(ruta), "sha256": h,
                             "filas": filas_csv(ruta), "tipo": "simulacion" if ruta in existentes else "contexto"})
        manifiesto = {"etiqueta": etiqueta, "archivado_utc": ahora.isoformat(timespec="seconds"),
                      "meta": meta or {}, "archivos": registro, "completo": True}
        ps.escribir_json(os.path.join(destino, "MANIFIESTO.json"), manifiesto)
    except BaseException:
        try:
            ps.escribir_atomico(os.path.join(destino, "INCOMPLETO.txt"), "Archivado interrumpido: los originales NO se borraron.\n")
        except OSError:
            pass
        raise
    for ruta in existentes:
        os.remove(ruta)
    return destino


def verificar(carpeta):
    """Comprueba un archivo ya hecho. Devuelve lista de problemas (vacia = correcto)."""
    try:
        with open(os.path.join(carpeta, "MANIFIESTO.json"), encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError) as e:
        return [f"manifiesto ilegible: {e}"]
    problemas = []
    for a in m.get("archivos", []):
        r = os.path.join(carpeta, a["archivo"])
        if not os.path.exists(r):
            problemas.append(f"falta {a['archivo']}")
        elif sha256(r) != a["sha256"]:
            problemas.append(f"huella distinta en {a['archivo']}")
    return problemas
