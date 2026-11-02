"""VALIDACION GLOBAL: un escenario de integracion por cada uno de los 20 casos del enunciado (datos ficticios/sinteticos).
Cada prueba lleva el numero del escenario en su nombre (esc01 ... esc20)."""
import copy
import csv
import hashlib
import json
import math
import os
import random
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

import analista
import costes as costes_mod
import ejecucion as ej
import estrategias as es
import informe
import laboratorio as lab
import metricas
import persistencia as ps
import reglas_mercado as rm
import velas as vl
import verificar_salida
import walkforward as wf
from tests.base import RAIZ, an, BaseDatos, velas, T0

FECHA = "2026-10-20T10:00+00:00"
BTC = an.BTC


def forzar(nombre_agente, senal):
    """Todos los agentes devuelven None salvo el indicado, que devuelve siempre 'senal'."""
    return {n: ((lambda s, i, _x, sg=senal: sg) if n == nombre_agente else (lambda s, i, _x: None)) for n in an.DECIDIR}


def filas_csv(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def v(ts_idx, o, c=None):
    c = o if c is None else c
    return vl.Vela(T0 + 3600 * ts_idx, o, max(o, c), min(o, c), c, 1.0)


class Esc01a09(BaseDatos):
    def test_esc01_agente_recien_creado(self):
        a = an.agente_nuevo("Cruce 10/30", 100.0)
        self.assertEqual((a["efectivo"], a["posiciones"], a["operaciones"], a["apagado"], a["pendientes"]), (an.START, {}, 0, False, []))
        est = an.estado_nuevo({BTC: velas([100.0] * 60)}, T0 + 3600 * 60)
        self.assertEqual(len(est["agentes"]), len(an.AGENTES))
        self.assertTrue(all(x["efectivo"] == an.START and not x["posiciones"] for x in est["agentes"]))
        self.assertEqual(an.equity(est["agentes"][0], est["precios"]), an.START)

    def test_esc02_primera_operacion_simulada(self):
        a = self.agente()
        self.assertTrue(an.operar(a, "COMPRA", BTC, 100.0, FECHA, {BTC: 1e6}, "senal compradora"))
        self.assertEqual(a["operaciones"], 1)
        self.assertGreater(a["posiciones"][BTC], 0)
        self.assertAlmostEqual(a["efectivo"], an.START - an.SLOT, delta=1e-5)
        fila = dict(zip(an.CAB_OPERACIONES, an.COLA_OPS[0]))
        self.assertEqual((fila["tipo"], fila["moneda"]), ("COMPRA", BTC))
        self.assertGreater(float(fila["coste_eur"]), 0)

    def test_esc03_compra_rechazada_por_minimos(self):
        an.REGLAS[BTC] = rm.Regla(BTC, 0.0, 50.0, 8, 8, "kraken")            # coste minimo 50 EUR > slot de 2 EUR
        a = self.agente()
        self.assertFalse(an.operar(a, "COMPRA", BTC, 100.0, FECHA, {BTC: 1e6}, "senal compradora"))
        self.assertEqual((a["efectivo"], a["posiciones"], a["operaciones"]), (an.START, {}, 0))
        self.assertEqual(an.categoria_rechazo(an.RECHAZOS[0][5]), "minimo_coste")
        # y en el flujo real: la senal no genera orden pendiente y el rechazo queda anotado (error corregido durante esta validacion)
        est = an.estado_nuevo({BTC: velas([100.0] * 60)}, T0 + 3600 * 60)
        with mock.patch.dict(an.DECIDIR, forzar("Rebote", "b")):
            an.paso(est, {BTC: velas([100.0] * 62)}, {BTC: 1e6}, [BTC], T0 + 3600 * 61 + 60)
        ag = next(x for x in est["agentes"] if x["nombre"] == "Rebote")
        self.assertEqual((ag["posiciones"], ag["pendientes"]), ({}, []))
        self.assertTrue(any(r[1] == "Rebote" and "coste minimo" in r[5] for r in an.RECHAZOS))
        self.assertTrue(an.rechazos_nuevos("ahora"))

    def test_esc04_compra_rechazada_por_datos_invalidos(self):
        malas = velas([100.0] * 60) + [vl.Vela(T0 + 3600 * 60, math.nan, math.nan, math.nan, math.nan, 1.0)]
        limpias = an.validar_todo({BTC: malas}, T0 + 3600 * 62)
        self.assertEqual(len(limpias[BTC]), 60)                                      # la vela con NaN se descarta
        self.assertTrue(any(i["tipo"] == "no_finito" for _, i in an.INCIDENCIAS))
        salto = velas([100.0] * 60 + [200.0] * 3)                                    # +100 % en una vela: dato anomalo
        an.validar_todo({BTC: salto}, T0 + 3600 * 64)
        self.assertIn(BTC, an.BLOQUEADOS)
        est = an.estado_nuevo({BTC: velas([100.0] * 60)}, T0 + 3600 * 60)
        with mock.patch.dict(an.DECIDIR, forzar("Rebote", "b")):
            an.paso(est, {BTC: salto}, {BTC: 1e6}, [BTC], T0 + 3600 * 64)
        ag = next(x for x in est["agentes"] if x["nombre"] == "Rebote")
        self.assertEqual((ag["posiciones"], ag["pendientes"], ag["operaciones"]), ({}, [], 0))   # no se abre posicion con datos anomalos

    def _senal_y_ejecucion(self):
        est = an.estado_nuevo({BTC: velas([100.0] * 60)}, T0 + 3600 * 60)
        nuevas = velas([100.0] * 60) + [v(60, 100.0), v(61, 120.0)]                  # la vela 61 abre un 20 % mas alto
        with mock.patch.dict(an.DECIDIR, forzar("Rebote", "b")):
            an.paso(est, {BTC: nuevas}, {BTC: 1e6}, [BTC], T0 + 3600 * 61 + 60)
        return est, [dict(zip(an.CAB_OPERACIONES, map(str, r))) for r in an.COLA_OPS if r[1] == "Rebote"]

    def test_esc05_senal_generada_al_cierre_de_una_vela(self):
        est, ops = self._senal_y_ejecucion()
        self.assertTrue(ops)
        self.assertEqual(ops[0]["vela_inicio_utc"], an.iso_vela(T0 + 3600 * 60))     # decidida con el cierre de la vela 60

    def test_esc06_ejecucion_en_la_vela_posterior(self):
        est, ops = self._senal_y_ejecucion()
        self.assertGreater(ops[0]["decision_utc"], ops[0]["vela_inicio_utc"])
        self.assertGreaterEqual(float(ops[0]["precio_eur"]), 120.0)                  # al precio de apertura de la vela siguiente, no al cierre (100)

    def _estado_con_posicion_ajena(self):
        est = an.estado_nuevo({BTC: velas([100.0] * 60)}, T0 + 3600 * 60)
        a = est["agentes"][0]
        a["efectivo"], a["posiciones"], a["entradas"] = 8.0, {"OUTEUR": 0.2}, {"OUTEUR": 10.0}
        est["precios"]["OUTEUR"] = 14.0
        return est, a

    def test_esc07_posicion_que_sale_del_universo(self):
        est, a = self._estado_con_posicion_ajena()
        self.assertIn("OUTEUR", an.pares_en_cartera(est))                            # se sigue vigilando aunque salga del ranking
        an.paso(est, {BTC: velas([100.0] * 62), "OUTEUR": velas([14.0] * 62)}, {BTC: 1e6, "OUTEUR": 1e6}, [BTC], T0 + 3600 * 62)
        self.assertNotIn("OUTEUR", a.get("sin_cotizacion", {}))                      # con datos, se valora a mercado
        self.assertAlmostEqual(an.equity(a, est["precios"]), 8.0 + 0.2 * 14.0)

    def test_esc08_posicion_sin_cotizacion(self):
        est, a = self._estado_con_posicion_ajena()
        ahora, precios = an.paso(est, {BTC: velas([100.0] * 62)}, {BTC: 1e6}, [BTC], T0 + 3600 * 62)
        self.assertIn("OUTEUR", a["posiciones"])                                     # no se cierra ni se inventa ganancia
        self.assertIn("OUTEUR", a["sin_cotizacion"])
        self.assertLessEqual(an.equity(a, precios), 8.0 + 0.2 * 10.0 + 1e-9)         # valoracion conservadora
        self.assertTrue(any(i["tipo"] == "sin_cotizacion" for _, i in an.INCIDENCIAS))

    def test_esc09_caida_del_mercado(self):
        a = self.agente()
        an.operar(a, "COMPRA", BTC, 100.0, FECHA, {BTC: 1e6})
        a["efectivo"] = 0.0
        an.apagar_si_toca(a, {BTC: 100.0 * 0.5}, FECHA, {BTC: 1e6}, None)           # el valor de la posicion cae por debajo del stop
        self.assertTrue(a["apagado"])
        self.assertEqual(a["posiciones"], {})
        self.assertGreater(a["efectivo"], 0)
        c = [100.0] * 20 + [100.0 - 3 * k for k in range(20)] + [40.0] * 10          # desplome del 60 %
        r, ops, hold, dd = ej.simular(c, c, 5, len(c), 1.0, lambda c_, i, s: "b" if i == 6 else None)
        self.assertGreater(dd, 25)
        self.assertGreater(r, -ej.START * 0.4)                                       # el apagado por riesgo limita la perdida


class Esc10a11Costes(unittest.TestCase):
    def serie(self):
        r, c = random.Random(3), [100.0]
        for _ in range(600):
            c.append(c[-1] * (1 + r.gauss(0, 0.005)))    # volatilidad moderada: sin apagado por riesgo, cuyo disparo depende de la trayectoria
        return c

    def resultado(self, fee, slip, spread):
        c = self.serie()
        return ej.simular(c, c, 50, len(c), 1.0, es.cruce(5, 20), None, fee, slip, spread, 10.0)

    def test_esc10_aumento_de_spread(self):
        r1, ops1, _, _ = self.resultado(0.004, 0.0005, 0.0008)
        r2, _, _, _ = self.resultado(0.004, 0.0005, 0.0016)
        r3, _, _, _ = self.resultado(0.004, 0.0005, 0.0064)
        self.assertGreater(ops1, 10)
        self.assertGreater(r1, r2)
        self.assertGreater(r2, r3)
        self.assertGreater(costes_mod.por_liquidez(1000.0).spread, costes_mod.por_liquidez(1e9).spread)     # menos liquidez = mas horquilla

    def test_esc11_comision_elevada(self):
        r1, _, _, _ = self.resultado(0.004, 0.0005, 0.0008)
        r2, _, _, _ = self.resultado(0.008, 0.0005, 0.0008)
        self.assertGreater(r1, r2)
        e = costes_mod.ESTRES
        self.assertGreater(e.fee, costes_mod.BASE.fee)
        self.assertGreater(e.coste_ida_y_vuelta(), costes_mod.BASE.coste_ida_y_vuelta())


class Esc12a14Persistencia(BaseDatos):
    def _horas(self, hasta, est=None, desde=None):
        v_, vol, orden, fuente, _ = an._descargar(220)
        n0 = 150
        if est is None:
            est = an.estado_nuevo({p: x[:n0] for p, x in v_.items()}, v_[BTC][n0 - 1].ts + 3600)
        for k in range(desde or n0, hasta):
            corte = {p: x[:k + 1] for p, x in v_.items()}
            ahora, precios = an.paso(est, corte, vol, orden, corte[BTC][-1].ts + 900)
            an.guardar(est, ahora, precios, fuente, len(orden), len(corte))
        return est, (v_, vol, orden, fuente)

    def instantanea(self):
        out = {}
        for n in ("estado.json", "historial_v2.csv", "operaciones.csv"):
            with open(os.path.join(an.DATOS, n), "rb") as f:
                out[n] = hashlib.sha256(f.read()).hexdigest()
        return out

    def test_esc12_interrupcion_de_escritura_todo_o_nada(self):
        est, (v_, vol, orden, fuente) = self._horas(190)
        otra = tempfile.TemporaryDirectory()
        self.addCleanup(otra.cleanup)
        base = os.path.join(otra.name, "base")                                     # fuera de la carpeta de datos
        shutil.copytree(an.DATOS, base)
        k = 190
        corte = {p: x[:k + 1] for p, x in v_.items()}
        est1 = copy.deepcopy(est)
        ahora, precios = an.paso(est1, corte, vol, orden, corte[BTC][-1].ts + 900)
        cola, rech, inc = list(an.COLA_OPS), list(an.RECHAZOS), list(an.INCIDENCIAS)
        # resultado esperado sin fallo
        an.guardar(copy.deepcopy(est1), ahora, precios, fuente, len(orden), len(corte))
        nuevo = self.instantanea()
        antiguo = {}
        shutil.rmtree(an.DATOS)
        shutil.copytree(base, an.DATOS)
        antiguo = self.instantanea()
        self.assertNotEqual(antiguo, nuevo)
        resultados = set()
        for fallo_en in range(1, 12):
            shutil.rmtree(an.DATOS)
            shutil.copytree(base, an.DATOS)
            an.COLA_OPS[:], an.RECHAZOS[:], an.INCIDENCIAS[:] = cola, rech, inc
            llamadas = {"n": 0}
            real = ps.os.replace

            def replace_roto(a, b, _real=real, _n=fallo_en):
                llamadas["n"] += 1
                if llamadas["n"] == _n:
                    raise OSError("corte de energia simulado")
                return _real(a, b)
            with mock.patch.object(ps.os, "replace", replace_roto):
                try:
                    an.guardar(copy.deepcopy(est1), ahora, precios, fuente, len(orden), len(corte))
                    fallo = False
                except OSError:
                    fallo = True
            ps.recuperar(an.DATOS)                                                # lo que hace main() al arrancar
            self.assertEqual(verificar_salida.comprobar(an.DATOS), [], f"fallo en la escritura {fallo_en}")
            instante = self.instantanea()
            self.assertIn(instante, (antiguo, nuevo), f"escritura a medias tras fallar en la llamada {fallo_en} (fallo={fallo})")
            resultados.add("nuevo" if instante == nuevo else "antiguo")
        self.assertEqual(resultados, {"antiguo", "nuevo"})                          # se probaron cortes antes y despues del punto de no retorno

    def test_esc13_recuperacion_tras_reinicio(self):
        est_a, _ = self._horas(200)                                              # ejecucion continua
        ops_a = filas_csv(an.OPERACIONES)
        ef_a = {x["nombre"]: (round(x["efectivo"], 6), sorted(x["posiciones"])) for x in est_a["agentes"]}
        shutil.rmtree(an.DATOS)
        os.makedirs(an.DATOS)
        an.asegurar_operaciones()
        an.COLA_OPS.clear()
        est_b, ctx = self._horas(175)                                            # se detiene en la hora 175...
        with open(an.ESTADO, encoding="utf-8") as f:                             # ..."reinicio": se recarga todo desde disco
            recargado = json.load(f)
        an.COLA_OPS.clear()
        an.RECHAZOS.clear()
        est_c, _ = self._horas(200, est=recargado, desde=175)
        ops_b = filas_csv(an.OPERACIONES)
        clave = lambda o: (o["fecha_utc"], o["agente"], o["moneda"], o["tipo"], o["precio_eur"], o["importe_eur"])
        self.assertEqual([clave(o) for o in ops_b], [clave(o) for o in ops_a])
        self.assertEqual({x["nombre"]: (round(x["efectivo"], 6), sorted(x["posiciones"])) for x in est_c["agentes"]}, ef_a)

    def test_esc14_historial_vacio(self):
        h, o = os.path.join(self.tmp.name, "no_h.csv"), os.path.join(self.tmp.name, "no_o.csv")
        m = informe.metricas(h, o, ["A"])
        self.assertEqual((m["A"].caida, m["A"].cerradas), (0.0, 0))
        self.assertFalse(informe.grafico_svg(h, os.path.join(self.tmp.name, "g.svg"), ["A"]))
        s = metricas.resumen([], [])
        self.assertTrue(all(s[k] == metricas.NO_ESTIMABLE for k in ("volatilidad", "sharpe", "sortino", "factor_beneficio", "expectativa", "ic_retorno_medio")))
        # el primer guardado con historial inexistente crea cabecera + 1 fila
        est = an.estado_nuevo({BTC: velas([100.0] * 60)}, T0 + 3600 * 60)
        an.guardar(est, "2026-10-20T10:00:00+00:00", est["precios"], "demo", 1, 1)
        self.assertEqual(len(filas_csv(an.HISTORIAL)), 1)


class Esc15a18Validacion(unittest.TestCase):
    def test_esc15_series_con_timestamps_distintos(self):
        raro = vl.Vela(T0 + 3600 + 17, 100.0, 100.0, 100.0, 100.0, 1.0)
        util, inc = vl.validar([v(0, 100.0), raro, v(2, 100.0)], 3600, T0 + 9 * 3600)
        self.assertNotIn(T0 + 3600 + 17, [x.ts for x in util])
        self.assertIn("no_alineada", [i["tipo"] for i in inc])
        corta = es.Serie([1.0, 2.0, 3.0], [T0 + 3600 * 2, T0 + 3600 * 3, T0 + 3600 * 4])
        larga = es.Serie([1.0] * 6, [T0 + 3600 * k for k in range(6)])
        self.assertEqual(es.alinear(corta, larga), [2, 3, 4])                        # cada vela se empareja por su marca de tiempo, no por su posicion
        sin = es.Serie([1.0], [T0 + 3600 * 40])
        self.assertEqual(es.alinear(sin, larga), [None])

    @classmethod
    def series_demo(cls):
        return lab.cargar_series(True)

    def test_esc16_backtesting_fuera_de_muestra(self):
        series = [s for s in self.series_demo() if s["minutos"] == 240][:3]
        n = len(series[0]["c"])
        pl = wf.pliegues(n, lab.WARM, lab.ENTRENO_VELAS, lab.PRUEBA_VELAS)
        self.assertGreaterEqual(len(pl), 2)
        for (i0, i1, j0, j1), (k0, k1, l0, l1) in zip(pl, pl[1:]):
            self.assertEqual(j1, l0)                                                 # pruebas contiguas
            self.assertLessEqual(i1, j0)                                             # se examina solo despues de entrenar
        fn = es.cruce(5, 20)
        completo = lab.evaluar_pliegues(series, fn)
        corte = pl[0][3]                                                             # se corta el futuro tras la primera prueba
        recortadas = [{**s, "c": es.Serie(list(s["c"])[:corte], s["c"].ts[:corte], s["c"].o[:corte], s["c"].vol[:corte]), "miembro": s["miembro"][:corte]} for s in series]
        recortado = lab.evaluar_pliegues(recortadas, fn)
        self.assertEqual(recortado[0], completo[0])                                  # el pliegue 1 no cambia si desaparece el futuro: sin mirar adelante

    def test_esc17_mercado_bajista(self):
        rng = random.Random(5)
        c = [100.0]
        for _ in range(500):
            c.append(c[-1] * math.exp(-0.004 + rng.gauss(0, 0.003)))
        regs = wf.regimenes(c)
        self.assertEqual(regs[-1], "bajista")
        self.assertGreater(sum(1 for r in regs if r == "bajista"), 0.8 * len(c) - 61)
        curva = []
        r, ops, hold, _ = ej.simular(c, c, 70, len(c), 1.0, es.con_filtro(es.cruce(5, 20)), None, 0.004, 0.0005, 0.0008, 10.0, None, None, curva)
        self.assertLess(hold, 0)                                                     # mantener pierde en un mercado bajista
        self.assertGreater(r, hold)                                                  # la estrategia con filtro pierde menos
        pr = wf.por_regimen(curva, c, 70, regs)
        self.assertGreater(pr["bajista"]["velas"], 0)
        self.assertEqual(pr["alcista"]["velas"], 0)

    def test_esc18_mercado_lateral(self):
        c = [100.0 * (1 + 0.01 * math.sin(2 * math.pi * i / 20)) for i in range(400)]
        regs = wf.regimenes(c)
        self.assertTrue(all(r == "lateral" for r in regs[61:]))
        curva = []
        r, ops, hold, _ = ej.simular(c, c, 70, len(c), 1.0, es.cruce(5, 20), None, 0.004, 0.0005, 0.0008, 10.0, None, None, curva)
        self.assertLess(r, 0.5)                                                      # sin tendencia, los costes de operar restan
        self.assertEqual(wf.por_regimen(curva, c, 70, regs)["lateral"]["velas"], len(curva) - 1)


class Esc19a20Seguridad(unittest.TestCase):
    def test_esc19_error_de_github_actions(self):
        with tempfile.TemporaryDirectory() as d:
            datos = os.path.join(d, "datos")
            os.makedirs(datos)
            open(os.path.join(datos, "estado.json"), "w").write("{roto")
            r = subprocess.run(["python3", os.path.join(RAIZ, "verificar_salida.py"), datos], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)                                        # datos corruptos: el paso falla y el flujo NO publica
            gh = os.path.join(d, "gh")
            open(gh, "w").write('#!/usr/bin/env bash\necho "$@" >> "$LOG"\nif [ "$1 $2" = "issue list" ]; then cat "$ISSUES"; fi\n')
            os.chmod(gh, os.stat(gh).st_mode | stat.S_IEXEC)
            env = dict(os.environ, PATH=d + os.pathsep + os.environ["PATH"], LOG=os.path.join(d, "log"), ISSUES=os.path.join(d, "i.json"))
            for abiertos in ([], [{"number": 3, "title": "Fallo X"}]):                # primer fallo abre; el segundo no duplica
                json.dump(abiertos, open(env["ISSUES"], "w"))
                subprocess.run(["bash", os.path.join(RAIZ, "scripts", "alerta_fallo.sh"), "abrir", "Fallo X", "u"], env=env, check=True, capture_output=True)
            self.assertEqual(open(env["LOG"]).read().count("issue create"), 1)
        t = open(os.path.join(RAIZ, ".github", "workflows", "agentes.yml"), encoding="utf-8").read()
        self.assertLess(t.index("unittest discover"), t.index("reintentar.sh python agentes_nube.py"))      # pruebas antes de tocar datos
        self.assertLess(t.index("verificar_salida.py"), t.index("guardar_datos.sh"))                 # verificar antes de publicar
        self.assertNotIn("--force", open(os.path.join(RAIZ, "scripts", "guardar_datos.sh")).read().replace("NUNCA usa --force", "").replace("sin forzar", ""))

    def test_esc20_propuesta_de_ia_sin_autorizacion_de_activacion(self):
        with tempfile.TemporaryDirectory() as d:
            datos = os.path.join(d, "datos")
            os.makedirs(datos)
            json.dump({"agentes": [{"nombre": "A", "operaciones": 9, "inicio": "2026-01-01T00:00:00+00:00"}]}, open(os.path.join(datos, "estado.json"), "w"))
            json.dump({"veredicto": "ruido", "tasa_azar": 0.4}, open(os.path.join(datos, "laboratorio.json"), "w"))
            antes = {n: open(os.path.join(datos, n), "rb").read() for n in os.listdir(datos)}
            agentes_antes = [n for n, _ in an.AGENTES]
            props, mal = analista.validar_propuestas(analista.analizar(analista.Lector(datos), "2026-10-21T00:00:00Z"))
            self.assertTrue(props and not mal)
            self.assertTrue(all(p["estado"] == "pendiente_de_revision" for p in props))
            intento = dict(props[0], estado="aplicada")                                           # una IA intenta marcar la propuesta como aplicada
            intento2 = dict(props[0], detalle="Activar la estrategia Momentum rapido con dinero real")
            self.assertEqual(len(analista.validar_propuestas([intento, intento2])[1]), 2)
            self.assertEqual({n: open(os.path.join(datos, n), "rb").read() for n in os.listdir(datos)}, antes)
            self.assertEqual([n for n, _ in an.AGENTES], agentes_antes)                           # no se ha activado ni quitado ninguna estrategia

    def test_no_existen_ejecuciones_financieras_reales(self):
        prohibido = re.compile(r"AddOrder|CancelOrder|/0/private|Withdraw|WithdrawFunds|API-Sign|API-Key|KRAKEN_API|api_secret|ccxt", re.I)
        for f in sorted(os.listdir(RAIZ)):
            if f.endswith(".py") and f != "test_validacion_global.py":
                with open(os.path.join(RAIZ, f), encoding="utf-8") as fh:
                    for n, linea in enumerate(fh, 1):
                        if prohibido.search(linea) and "PermisoDenegado" not in linea and "ruta" not in linea.lower():
                            self.fail(f"{f}:{n}: {linea.strip()}")
        for f in os.listdir(os.path.join(RAIZ, ".github", "workflows")):
            with open(os.path.join(RAIZ, ".github", "workflows", f), encoding="utf-8") as fh:
                self.assertNotRegex(fh.read(), r"secrets\.")


if __name__ == "__main__":
    unittest.main()
