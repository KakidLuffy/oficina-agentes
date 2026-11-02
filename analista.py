#!/usr/bin/env python3
"""
Analista experimental (SOLO LECTURA + PROPUESTAS). Examina los resultados guardados y redacta hipotesis, inconsistencias,
experimentos y riesgos como PROPUESTAS PENDIENTES DE REVISION. No decide nada.

Garantias tecnicas (comprobadas en tests/test_analista.py):
  - Lee unicamente una lista cerrada de archivos de datos, abiertos en modo lectura.
  - Escribe unicamente propuestas_analista.json / .md en la carpeta de salida, y solo AÑADE propuestas nuevas: nunca borra ni
    modifica una propuesta ya existente (ni su estado de revision) ni ningun resultado historico.
  - No importa el simulador, la ejecucion, las estrategias ni la persistencia transaccional: no tiene forma de operar, activar
    estrategias, cambiar limites de riesgo, mover fondos ni habilitar trading real.
  - Es determinista y no usa red ni claves. Un analista basado en un modelo de lenguaje debe entregar su salida con el MISMO esquema
    y pasar por validar_propuestas(); lo que no encaje (acciones, parametros, ordenes) se rechaza.
  - Una propuesta nunca se da por buena: la validacion es cuantitativa e independiente (laboratorio walk-forward / simulacion en vivo).

Uso: python analista.py [--datos datos] [--out datos]
"""
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

LEIBLES = ("estado.json", "laboratorio.json", "operaciones.csv", "historial_v2.csv", "decisiones_rechazadas.csv",
           "incidencias_datos.csv", "parte_director.json")
SALIDA_JSON, SALIDA_MD = "propuestas_analista.json", "propuestas_analista.md"
TIPOS = ("hipotesis", "inconsistencia", "experimento", "riesgo", "informe")
ESTADOS = ("pendiente_de_revision", "aceptada_para_probar", "descartada")
CAMPOS = {"id", "tipo", "titulo", "detalle", "evidencia", "validacion_requerida", "estado", "creada"}
# Frases que ordenan ACTUAR. Es una barrera adicional y heuristica: la garantia real es estructural (el esquema no tiene campos de accion,
# los estados no incluyen «aplicada» y este modulo no puede importar nada que opere). «Comprar y mantener» o «ordenes rechazadas» son texto normal.
PROHIBIDO = ("trading real", "transferir fondos", "retirar fondos", "retirada de fondos", "activar la estrategia", "activar el agente",
             "desactivar el limite", "cambiar el limite", "modificar el limite", "subir el limite", "ejecutar la orden", "enviar la orden",
             "colocar la orden", "abrir una posicion real", "sobrescribir", "borrar el historial")
MIN_CERRADAS, MIN_DIAS = 30, 21


# ---------------- lectura (solo consulta) ----------------
class Lector:
    """Unico punto de acceso a los datos: lista cerrada, modo lectura, y nunca escribe."""
    def __init__(self, carpeta):
        self.carpeta = carpeta

    def _ruta(self, nombre):
        if nombre not in LEIBLES:
            raise PermissionError(f"el analista no puede leer {nombre}")
        return os.path.join(self.carpeta, nombre)

    def json(self, nombre):
        try:
            with open(self._ruta(nombre), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def csv(self, nombre):
        try:
            with open(self._ruta(nombre), newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except (OSError, csv.Error):
            return []


def _num(x, defecto=0.0):
    try:
        v = float(x)
        return v if v == v and abs(v) != float("inf") else defecto
    except (TypeError, ValueError):
        return defecto


def _id(tipo, clave):
    return tipo[:3] + "-" + hashlib.sha256(f"{tipo}|{clave}".encode()).hexdigest()[:10]


def propuesta(tipo, clave, titulo, detalle, evidencia, validacion, ahora):
    return {"id": _id(tipo, clave), "tipo": tipo, "titulo": titulo, "detalle": detalle, "evidencia": list(evidencia),
            "validacion_requerida": validacion, "estado": "pendiente_de_revision", "creada": ahora}


# ---------------- analisis ----------------
def cerradas_por_agente(ops):
    abiertas, cerradas = {}, {}
    for o in sorted(ops, key=lambda o: o.get("fecha_utc", "")):
        ag, par = o.get("agente", ""), o.get("moneda", "")
        if o.get("tipo") == "COMPRA":
            abiertas[(ag, par)] = _num(o.get("importe_eur"))
        elif o.get("tipo") == "VENTA" and (ag, par) in abiertas:
            cerradas.setdefault(ag, []).append(_num(o.get("importe_eur")) - abiertas.pop((ag, par)))
    return cerradas


def analizar(datos, ahora):
    estado, lab = datos.json("estado.json"), datos.json("laboratorio.json")
    ops, rech = datos.csv("operaciones.csv"), datos.csv("decisiones_rechazadas.csv")
    inc = datos.csv("incidencias_datos.csv")
    out = []

    # 1. Inconsistencias entre archivos
    if estado and ops:
        for a in estado.get("agentes", []):
            n = sum(1 for o in ops if o.get("agente") == a.get("nombre"))
            if _num(a.get("operaciones")) != n and n:
                out.append(propuesta("inconsistencia", f"ops|{a.get('nombre')}", f"Contador de operaciones distinto en {a.get('nombre')}",
                                     f"estado.json dice {a.get('operaciones')} operaciones y operaciones.csv tiene {n} filas de ese agente.",
                                     ["estado.json", "operaciones.csv"], "Revisar a mano; ejecutar verificar_salida.py y los tests de contabilidad.", ahora))

    # 2. Decisiones rechazadas: patrones
    if rech:
        por_cat = {}
        for r in rech:
            por_cat[r.get("categoria", "otro")] = por_cat.get(r.get("categoria", "otro"), 0) + 1
        cat, n = max(por_cat.items(), key=lambda kv: kv[1])
        if n >= 5 and n / len(rech) >= 0.5:
            out.append(propuesta("hipotesis", f"rechazos|{cat}", f"La mayoria de las ordenes rechazadas lo son por «{cat}»",
                                 f"{n} de {len(rech)} decisiones rechazadas ({n / len(rech) * 100:.0f} %). Si la causa son los minimos del exchange, "
                                 "el capital por posicion puede ser demasiado pequeño para algunas monedas: hipotesis, no conclusion.",
                                 ["decisiones_rechazadas.csv"],
                                 "Medirlo con el simulador (mas capital o menos posiciones) ANTES de proponer cambios; el cambio de capital es decision del usuario.", ahora))

    # 3. Resultados de agentes frente a la regla de confianza
    cerr = cerradas_por_agente(ops)
    if estado:
        for a in estado.get("agentes", []):
            nom = a.get("nombre")
            try:
                dias = (datetime.fromisoformat(ahora.replace("Z", "+00:00")) - datetime.fromisoformat(a.get("inicio", "").replace("Z", "+00:00"))).total_seconds() / 86400
            except ValueError:
                dias = 0
            k = len(cerr.get(nom, []))
            if dias < MIN_DIAS or k < MIN_CERRADAS:
                continue
            gan = sum(1 for v in cerr[nom] if v > 0)
            out.append(propuesta("informe", f"confianza|{nom}", f"{nom} ya supera el minimo de datos para evaluarse",
                                 f"{dias:.0f} dias y {k} operaciones cerradas ({gan} ganadoras). Cumplir el minimo NO significa que la estrategia sirva: "
                                 "falta compararla con Comprar y mantener de forma sostenida y con intervalos de confianza.",
                                 ["estado.json", "operaciones.csv"], "Comparar con Comprar y mantener y metricas con IC (metricas.py) durante varias semanas.", ahora))

    # 4. Costes frente a resultado
    coste = sum(_num(o.get("coste_eur")) for o in ops)
    if estado and ops and coste > 0:
        out.append(propuesta("riesgo", "costes", "Los costes de operar pueden pesar mas que cualquier ventaja",
                             f"Las {len(ops)} operaciones registradas suman {coste:.2f} EUR de comisiones. Con muchas operaciones pequeñas el coste se come la ventaja de la estrategia.",
                             ["operaciones.csv"], "Comparar el resultado bruto y el neto con costes duros (laboratorio, columna de estres).", ahora))

    # 5. Laboratorio
    if lab:
        v, azar = lab.get("veredicto"), _num(lab.get("tasa_azar"))
        if v in ("ruido", "ninguna"):
            out.append(propuesta("hipotesis", f"lab|{v}", "El laboratorio no distingue sus candidatas del azar",
                                 f"Veredicto «{v}» con tasa de azar {azar * 100:.0f} %. Lo prudente es no incorporar estrategias nuevas con estos datos.",
                                 ["laboratorio.json"], "Repetir el laboratorio con mas historial; solo cambiar algo si las candidatas superan claramente al azar.", ahora))
        wf = lab.get("walk_forward") or {}
        if wf and _num(wf.get("ventaja")) <= 0:
            out.append(propuesta("hipotesis", "wf|sin_ventaja", "Elegir la mejor variante del pasado no mejora fuera de muestra",
                                 f"En {wf.get('pliegues')} pliegues walk-forward la ventaja de elegir fue {_num(wf.get('ventaja')):+.2f} EUR frente a la media de todas las variantes.",
                                 ["laboratorio.json"], "No promover variantes por su rendimiento pasado; exigir persistencia en simulacion en vivo.", ahora))
        sg = lab.get("sesgo_supervivencia") or {}
        if sg and _num(sg.get("dif_fija")) > _num(sg.get("dif_pit")):
            out.append(propuesta("riesgo", "sesgo", "Los resultados con la lista fija de monedas son mas optimistas",
                                 f"Dif. media {_num(sg.get('dif_fija')):+.2f} EUR con lista fija frente a {_num(sg.get('dif_pit')):+.2f} EUR con universo punto en el tiempo. "
                                 "Ademas, las monedas ya deslistadas no se pueden incluir: el sesgo no desaparece.",
                                 ["laboratorio.json"], "Tratar todo resultado favorable como optimista.", ahora))
        reg = lab.get("regimenes") or {}
        sola = [n for n, r in reg.items() if isinstance(r, dict) and sum(1 for x in r.values() if _num(x.get("dif")) > 0) == 1]
        if sola:
            out.append(propuesta("experimento", "regimen|" + ",".join(sorted(sola)), "Variantes que solo ganan en un tipo de mercado",
                                 f"{len(sola)} de las variantes elegidas ganan frente a mantener en un unico regimen (alcista, bajista o lateral). "
                                 "Hipotesis: dependen de que el mercado se parezca al de la muestra.",
                                 ["laboratorio.json"], "Probar en otro periodo y comprobar que el resultado por regimen se mantiene.", ahora))

    # 6. Calidad de datos
    if len(inc) >= 10:
        por_par = {}
        for r in inc:
            por_par[r.get("par", "")] = por_par.get(r.get("par", ""), 0) + 1
        par, n = max(por_par.items(), key=lambda kv: kv[1])
        out.append(propuesta("inconsistencia", f"datos|{par}", f"Muchas incidencias de datos de velas en {par}",
                             f"{n} de {len(inc)} incidencias corresponden a {par}. Datos de mala calidad producen señales falsas.",
                             ["incidencias_datos.csv"], "Revisar la moneda; valorar excluirla del universo tras comprobarlo.", ahora))
    return out


# ---------------- validacion de propuestas (tambien para las de un modelo de lenguaje) ----------------
def validar_propuestas(lista):
    """Devuelve (aceptadas, rechazadas[(propuesta, motivo)]). Solo pasan propuestas con el esquema exacto, tipo y estado validos,
    SIN acciones: cualquier texto que ordene operar, activar, mover fondos o tocar limites se rechaza."""
    ok, mal = [], []
    for p in lista if isinstance(lista, list) else []:
        if not isinstance(p, dict) or set(p) != CAMPOS:
            mal.append((p, "esquema distinto del permitido"))
        elif p["tipo"] not in TIPOS or p["estado"] not in ESTADOS:
            mal.append((p, "tipo o estado no permitido"))
        elif not all(isinstance(p[k], str) and p[k].strip() for k in ("id", "titulo", "detalle", "validacion_requerida", "creada")) or not isinstance(p["evidencia"], list):
            mal.append((p, "campos vacios o de tipo incorrecto"))
        elif any(w in " ".join([p["titulo"], p["detalle"], p["validacion_requerida"]]).lower() for w in PROHIBIDO):
            mal.append((p, "contiene una accion prohibida para el analista"))
        else:
            ok.append(p)
    return ok, mal


def combinar(existentes, nuevas):
    """Anade las nuevas por id; las que ya existian (y su estado de revision) NO se tocan."""
    ids = {p["id"] for p in existentes}
    return list(existentes) + [p for p in nuevas if p["id"] not in ids]


def texto_md(props, ahora):
    md = ["# Propuestas del analista (experimental)", "",
          f"Actualizado: {ahora}. Son **hipotesis pendientes de revision**: el analista no activa estrategias, no cambia limites ni opera. "
          "Cada una debe validarse con procedimientos cuantitativos independientes antes de actuar.", ""]
    for estado in ESTADOS:
        sel = [p for p in props if p["estado"] == estado]
        if not sel:
            continue
        md += [f"## {estado.replace('_', ' ').capitalize()} ({len(sel)})", ""]
        for p in sel:
            md += [f"### [{p['tipo']}] {p['titulo']}  `{p['id']}`", "", p["detalle"], "",
                   f"- Evidencia: {', '.join(p['evidencia'])}", f"- Validacion requerida: {p['validacion_requerida']}", ""]
    if not props:
        md.append("No hay propuestas.")
    return "\n".join(md) + "\n"


def escribir_salida(carpeta, props, ahora):
    """Unico lugar donde se escribe: dos archivos propios, de forma atomica."""
    os.makedirs(carpeta, exist_ok=True)
    for nombre, contenido in ((SALIDA_JSON, json.dumps({"generado": ahora, "propuestas": props}, indent=1, ensure_ascii=False) + "\n"),
                              (SALIDA_MD, texto_md(props, ahora))):
        ruta = os.path.join(carpeta, nombre)
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(contenido)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ruta)


def main():
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    carpeta, out = arg("--datos", "datos"), arg("--out", arg("--datos", "datos"))
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nuevas, rechazadas = validar_propuestas(analizar(Lector(carpeta), ahora))
    previo = {}
    try:
        with open(os.path.join(out, SALIDA_JSON), encoding="utf-8") as f:
            previo = json.load(f)
    except (OSError, ValueError):
        pass
    existentes, _ = validar_propuestas(previo.get("propuestas", []))
    props = combinar(existentes, nuevas)
    escribir_salida(out, props, ahora)
    print(f"Propuestas: {len(props)} ({len(props) - len(existentes)} nuevas, {len(rechazadas)} rechazadas por el validador). Ninguna se aplica sola.")


if __name__ == "__main__":
    main()
