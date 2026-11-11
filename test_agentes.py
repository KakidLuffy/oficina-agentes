"""Pruebas de las reglas v4 de agentes_nube.py (sin internet):  python -m unittest test_agentes"""
import contextlib
import csv
import io
import os
import tempfile
import unittest
from unittest import mock

import agentes_nube as a


X = "ETHEUR"   # moneda de prueba: desde el 11-nov los agentes de senales solo compran PERMITIDAS (BTC y ETH)


def simular(precios_btc, precios_x, nombre="Rebote"):
    """Recorre velas de 1 h de BTC y de ETH y devuelve las operaciones de ETH del agente `nombre`."""
    t0 = 1_700_000_000
    velas = {a.BTC: [(t0 + i * 3600, p) for i, p in enumerate(precios_btc)],
             X: [(t0 + i * 3600, p) for i, p in enumerate(precios_x)]}
    vol = {p: 1e6 for p in velas}
    ini = {p: v[:25] for p, v in velas.items()}
    est = a.estado_nuevo(ini, ini[a.BTC][-1][0] + 3600)
    a.parametros(est)
    a.asegurar_operaciones()
    with contextlib.redirect_stdout(io.StringIO()):
        a.paso(est, velas, {}, vol, [a.BTC, X], velas[a.BTC][-1][0] + 3600)
    with open(a.OPERACIONES, newline="") as f:
        return [r for r in csv.DictReader(f) if r["agente"] == nombre and r["moneda"] == X]


class TestV4(unittest.TestCase):
    def setUp(self):
        self.antes = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        os.makedirs(a.DATOS)

    def tearDown(self):
        os.chdir(self.antes)
        self.dir.cleanup()

    def test_version_y_agentes(self):
        self.assertEqual(a.VERSION, 4)
        nombres = [n for n, _ in a.AGENTES]
        self.assertNotIn("Momentum rapido", nombres)
        self.assertNotIn("Consenso 2 de 3", nombres)
        self.assertEqual(len(nombres), 9)
        self.assertIn(a.REBALANCEO, nombres)
        self.assertIn(a.H1, nombres)                                   # el agente de main (11-nov) se conserva
        self.assertEqual(a.PERMITIDAS, ("XBTEUR", "ETHEUR"))

    def test_min_horas_solo_en_la_mitad(self):
        con = {n for n in a.OPCIONES if a.OPCIONES[n].get("min_horas") == 6}
        self.assertEqual(con, {"Cruce 10/30", "Momentum", "Cruce 3/8 rapido"})
        for n in ("Cruce 5/20", "Rebote", "Cruce 10/30 + filtro", "Rebote rapido"):
            self.assertNotIn("min_horas", a.OPCIONES[n])               # grupo de comparacion
        con_espera = {n for n in a.OPCIONES if a.OPCIONES[n].get("espera_h")}
        self.assertEqual(con_espera, {"Cruce 3/8 rapido", "Rebote rapido"})   # como en la v3

    def test_monedas_estables_excluidas(self):
        for base in ("EURC", "USDC", "USDT", "EURCV", "USDE"):
            self.assertIn(base, a.EXCLUIR_BASES)

    def test_no_vende_por_senal_antes_de_6_horas(self):
        # Rebote compra al caer un 1,5 % bajo su media de 20 velas y vende al volver por encima de la media.
        x = [100.0] * 30 + [98.0] + [101.0] * 10        # senal vendedora ya 1 h despues de comprar
        with mock.patch.dict(a.OPCIONES, {"Rebote": {"min_horas": 6}}):
            ops = simular([60000.0] * len(x), x)
        self.assertEqual([o["tipo"] for o in ops][:2], ["COMPRA", "VENTA"])
        horas = (a.datetime.fromisoformat(ops[1]["fecha_utc"]) - a.datetime.fromisoformat(ops[0]["fecha_utc"])).total_seconds() / 3600
        self.assertEqual(horas, 6)                       # en v3 habria vendido a la hora

    def test_sin_min_horas_vende_a_la_hora(self):
        x = [100.0] * 30 + [98.0] + [101.0] * 10         # Rebote no lleva min_horas en la v4 (grupo de comparacion)
        ops = simular([60000.0] * len(x), x)
        horas = (a.datetime.fromisoformat(ops[1]["fecha_utc"]) - a.datetime.fromisoformat(ops[0]["fecha_utc"])).total_seconds() / 3600
        self.assertEqual(horas, 1)

    def test_no_compra_monedas_no_permitidas(self):
        t0 = 1_700_000_000
        x = [100.0] * 30 + [98.0] + [101.0] * 10
        velas = {a.BTC: [(t0 + i * 3600, 60000.0) for i in range(len(x))],
                 "XEUR": [(t0 + i * 3600, p) for i, p in enumerate(x)]}
        ini = {p: v[:25] for p, v in velas.items()}
        est = a.estado_nuevo(ini, ini[a.BTC][-1][0] + 3600)
        a.parametros(est)
        a.asegurar_operaciones()
        with contextlib.redirect_stdout(io.StringIO()):
            a.paso(est, velas, {}, {p: 1e6 for p in velas}, [a.BTC, "XEUR"], velas[a.BTC][-1][0] + 3600)
        with open(a.OPERACIONES, newline="") as f:
            self.assertFalse([r for r in csv.DictReader(f) if r["moneda"] == "XEUR"])

    def test_el_stop_actua_aunque_no_hayan_pasado_6_horas(self):
        x = [100.0] * 30 + [98.0] * 3 + [95.0] * 10     # Rebote rapido: stop del 1,5 %
        ops = simular([60000.0] * len(x), x, "Rebote rapido")
        ventas = [o for o in ops if o["tipo"] == "VENTA"]
        self.assertTrue(ventas and ventas[0]["motivo"].startswith("stop"))
        primera_compra = next(o for o in ops if o["tipo"] == "COMPRA")
        h = (a.datetime.fromisoformat(ventas[0]["fecha_utc"]) - a.datetime.fromisoformat(primera_compra["fecha_utc"])).total_seconds() / 3600
        self.assertLess(h, 6)

    def test_retenida(self):
        ag = {"compras": {"XEUR": "2026-11-01T10:00+00:00"}}
        op = {"min_horas": 6}
        self.assertTrue(a.retenida(ag, "XEUR", "2026-11-01T15:00+00:00", op))
        self.assertFalse(a.retenida(ag, "XEUR", "2026-11-01T16:00+00:00", op))
        self.assertFalse(a.retenida(ag, "YEUR", "2026-11-01T11:00+00:00", op))      # sin fecha de compra (estado v3)
        self.assertFalse(a.retenida(ag, "XEUR", "2026-11-01T11:00+00:00", {}))


class TestRebalanceo(unittest.TestCase):
    """Cesta inventada de 5 monedas: C1..C4 + BTC. 'OTRA' solo la pueden operar los agentes de senales."""
    def setUp(self):
        self.antes = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        os.makedirs(a.DATOS)
        self.cesta = [a.BTC, "C1EUR", "C2EUR", "C3EUR", "C4EUR"]

    def tearDown(self):
        os.chdir(self.antes)
        self.dir.cleanup()

    def correr(self, series, orden, horas):
        t0 = 1_700_000_000
        velas = {p: [(t0 + i * 3600, f(i)) for i in range(horas)] for p, f in series.items()}
        vol = {p: 1e6 for p in velas}
        ini = {p: v[:25] for p, v in velas.items()}
        est = a.estado_nuevo(ini, ini[a.BTC][-1][0] + 3600)
        est["cesta"] = self.cesta
        a.parametros(est)
        a.asegurar_operaciones()
        with contextlib.redirect_stdout(io.StringIO()):
            a.paso(est, velas, {}, vol, orden, velas[a.BTC][-1][0] + 3600)
        with open(a.OPERACIONES, newline="") as f:
            ops = list(csv.DictReader(f))
        ag = next(x for x in est["agentes"] if x["nombre"] == a.REBALANCEO)
        return [o for o in ops if o["agente"] == a.REBALANCEO], ops, ag, est

    def test_compra_la_cesta_a_partes_iguales_y_no_opera_hasta_la_semana(self):
        planas = {p: (lambda i: 100.0) for p in self.cesta}
        reb, _, ag, est = self.correr(planas, list(self.cesta), 25 + 24 * 6)     # menos de 7 dias
        self.assertEqual(sorted(o["moneda"] for o in reb), sorted(self.cesta))
        self.assertTrue(all(o["tipo"] == "COMPRA" for o in reb))
        valores = [u * est["precios"][p] for p, u in ag["posiciones"].items()]
        self.assertAlmostEqual(max(valores), min(valores), places=6)
        self.assertLess(ag["efectivo"], 0.01)

    def test_a_los_7_dias_solo_rehace_la_moneda_desviada(self):
        series = {p: (lambda i: 100.0) for p in self.cesta}
        series["C1EUR"] = lambda i: 100.0 if i < 60 else 200.0                    # C1 dobla su precio
        series["C2EUR"] = lambda i: 100.0 if i < 60 else 110.0                    # C2 +10 %: dentro de la banda
        reb, _, ag, _ = self.correr(series, list(self.cesta), 25 + 24 * 7 + 3)
        ventas = [o["moneda"] for o in reb if o["tipo"] == "VENTA"]
        self.assertEqual(ventas, ["C1EUR"])
        self.assertEqual(sum(o["tipo"] == "COMPRA" and o["moneda"] == "C1EUR" for o in reb), 2)
        self.assertEqual(ag["ultimo_rebalanceo"] - 1_700_000_000, (25 + 24 * 7) * 3600)   # primera vela procesada (25) + 7 dias

    def test_los_demas_agentes_no_operan_monedas_fuera_de_su_universo(self):
        series = {p: (lambda i: 100.0 + (i % 7) * 3) for p in self.cesta}         # oscila: los agentes de senales operan
        _, ops, _, _ = self.correr(series, [a.BTC], 25 + 72)                      # universo de senales: solo BTC
        otras = {o["moneda"] for o in ops if o["agente"] != a.REBALANCEO}
        self.assertEqual(otras - {a.BTC}, set())
        self.assertTrue(otras)


class TestReferenciaYCostes(unittest.TestCase):
    def setUp(self):
        self.antes = os.getcwd()
        self.dir = tempfile.TemporaryDirectory()
        os.chdir(self.dir.name)
        os.makedirs(a.DATOS)

    def tearDown(self):
        os.chdir(self.antes)
        self.dir.cleanup()

    def test_cesta_a_partes_iguales_con_costes(self):
        velas = {a.BTC: [(0, 60000.0)], "ETHEUR": [(0, 2000.0)], "YEUR": [(0, 50.0)], "FUERAEUR": [(0, 1.0)]}
        ref = a.referencia_cesta(velas, [a.BTC, "ETHEUR", "YEUR"])
        self.assertEqual(sorted(ref), sorted([a.BTC, "ETHEUR"]))             # solo las monedas que pueden comprar
        self.assertAlmostEqual(ref["ETHEUR"] * 2000.0, ref[a.BTC] * 60000.0)
        est = {"referencia_cesta": ref, "precios": {a.BTC: 60000.0, "ETHEUR": 2000.0}}
        self.assertAlmostEqual(a.valor_referencia(est, est["precios"]), a.START * (1 - a.FEE) / (1 + a.SLIP))
        # si una moneda no tiene precio en esta ronda, vale su ultimo precio conocido
        self.assertAlmostEqual(a.valor_referencia(est, {a.BTC: 60000.0, "ETHEUR": 4000.0}),
                               a.START / 2 * (1 - a.FEE) / (1 + a.SLIP) * 3)

    def test_resumen_e_historial_con_cesta_y_costes(self):
        t0 = 1_700_000_000
        x = [100.0] * 30 + [98.0] + [101.0] * 10
        velas = {a.BTC: [(t0 + i * 3600, 60000.0) for i in range(len(x))], "ETHEUR": [(t0 + i * 3600, p) for i, p in enumerate(x)]}
        ini = {p: v[:25] for p, v in velas.items()}
        est = a.estado_nuevo(ini, ini[a.BTC][-1][0] + 3600, [a.BTC, "ETHEUR"])
        a.parametros(est)
        a.asegurar_operaciones()
        with contextlib.redirect_stdout(io.StringIO()):
            ahora, precios = a.paso(est, velas, {}, {p: 1e6 for p in velas}, [a.BTC, "ETHEUR"], velas[a.BTC][-1][0] + 3600)
            a.guardar(est, ahora, precios, "prueba", 2, 2)
        with open(a.OPERACIONES, newline="") as f:
            ops = list(csv.DictReader(f))
        for ag in est["agentes"]:
            esperado = sum(float(o["coste_eur"]) for o in ops if o["agente"] == ag["nombre"])
            self.assertAlmostEqual(ag.get("costes", 0.0), esperado, places=3)
        self.assertTrue(any(ag.get("costes", 0) > 0 for ag in est["agentes"]))
        with open(a.HISTORIAL, newline="") as f:
            filas = list(csv.DictReader(f))
        self.assertIn(a.REF_CESTA, filas[-1])
        with open(a.RESUMEN, encoding="utf-8") as f:
            resumen = f.read()
        self.assertIn("Costes pagados (EUR)", resumen)
        self.assertIn("Antes de costes (EUR)", resumen)
        self.assertIn("| " + a.REF_CESTA + " |", resumen)


class TestDirector(unittest.TestCase):
    def test_aviso_de_limite_solo_cerca_del_limite(self):
        import director
        with open(director.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn('x["eq"] < STOP + 5', src)                 # con 10 EUR avisaba siempre (umbral 12 EUR)
        self.assertIn('x["eq"] < STOP + (START - STOP) * 0.25', src)  # con 10 EUR: avisa por debajo de 7,75 EUR


if __name__ == "__main__":
    unittest.main()
