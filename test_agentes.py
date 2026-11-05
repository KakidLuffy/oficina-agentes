"""Pruebas de las reglas v4 de agentes_nube.py (sin internet):  python -m unittest test_agentes"""
import contextlib
import csv
import io
import os
import tempfile
import unittest

import agentes_nube as a


def simular(precios_btc, precios_x, nombre="Rebote"):
    """Recorre velas de 1 h de BTC y de una moneda XEUR y devuelve las operaciones del agente `nombre`."""
    t0 = 1_700_000_000
    velas = {a.BTC: [(t0 + i * 3600, p) for i, p in enumerate(precios_btc)],
             "XEUR": [(t0 + i * 3600, p) for i, p in enumerate(precios_x)]}
    vol = {p: 1e6 for p in velas}
    ini = {p: v[:25] for p, v in velas.items()}
    est = a.estado_nuevo(ini, ini[a.BTC][-1][0] + 3600)
    a.parametros(est)
    a.asegurar_operaciones()
    with contextlib.redirect_stdout(io.StringIO()):
        a.paso(est, velas, vol, [a.BTC, "XEUR"], velas[a.BTC][-1][0] + 3600)
    with open(a.OPERACIONES, newline="") as f:
        return [r for r in csv.DictReader(f) if r["agente"] == nombre and r["moneda"] == "XEUR"]


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
        self.assertEqual(len(nombres), 7)
        self.assertTrue(all(a.OPCIONES[n]["min_horas"] == 6 for n in nombres))

    def test_monedas_estables_excluidas(self):
        for base in ("EURC", "USDC", "USDT", "EURCV", "USDE"):
            self.assertIn(base, a.EXCLUIR_BASES)

    def test_no_vende_por_senal_antes_de_6_horas(self):
        # Rebote compra al caer un 1,5 % bajo su media de 20 velas y vende al volver por encima de la media.
        x = [100.0] * 30 + [98.0] + [101.0] * 10        # senal vendedora ya 1 h despues de comprar
        ops = simular([60000.0] * len(x), x)
        self.assertEqual([o["tipo"] for o in ops][:2], ["COMPRA", "VENTA"])
        horas = (a.datetime.fromisoformat(ops[1]["fecha_utc"]) - a.datetime.fromisoformat(ops[0]["fecha_utc"])).total_seconds() / 3600
        self.assertEqual(horas, 6)                       # en v3 habria vendido a la hora

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


if __name__ == "__main__":
    unittest.main()
