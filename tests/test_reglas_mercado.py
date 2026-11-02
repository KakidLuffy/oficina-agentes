import unittest
from tests.base import an, BaseDatos, velas, T0
import reglas_mercado as rm
import velas as vl_

KRAKEN_BTC = {"altname": "XBTEUR", "quote": "ZEUR", "ordermin": "0.00005", "costmin": "0.5", "lot_decimals": 8,
              "pair_decimals": 1, "cost_decimals": 5, "tick_size": "0.1", "status": "online"}


class Reglas(unittest.TestCase):
    def test_desde_kraken(self):
        r = rm.desde_kraken("XBTEUR", KRAKEN_BTC)
        self.assertEqual((r.ordermin, r.costmin, r.lot_decimals, r.pair_decimals, r.fuente), (0.00005, 0.5, 8, 1, "kraken"))

    def test_campos_ausentes_o_basura_usan_el_supuesto_y_lo_marcan(self):
        r = rm.desde_kraken("X", {"ordermin": "abc"})
        self.assertEqual(r.fuente, "supuesto")
        self.assertEqual(r.costmin, rm.GENERICA.costmin)

    def test_redondeo_siempre_hacia_abajo(self):
        self.assertEqual(rm.redondear_abajo(0.123456789, 4), 0.1234)
        self.assertEqual(rm.redondear_abajo(0.99999999, 2), 0.99)
        self.assertEqual(rm.redondear_abajo(5.0, 0), 5.0)

    def test_comprobacion_de_orden(self):
        r = rm.desde_kraken("XBTEUR", KRAKEN_BTC)
        self.assertIsNone(rm.motivo_invalida(r, 0.0001, 70000.0))                      # 0,0001 BTC = 7 EUR: valida
        self.assertIn("volumen minimo", rm.motivo_invalida(r, 0.00002, 70000.0))        # 2 EUR de BTC: por debajo del minimo
        r2 = rm.Regla("X", 0.0, 5.0, 8, 4, "kraken")
        self.assertIn("coste minimo", rm.motivo_invalida(r2, 1.0, 2.0))
        self.assertIn("no es positiva", rm.motivo_invalida(r, 0.0, 1.0))


class EnLaSimulacion(BaseDatos):
    def setUp(self):
        super().setUp()
        self.addCleanup(an.REGLAS.clear)

    def test_compra_por_debajo_del_minimo_se_rechaza_y_no_gasta_dinero(self):
        an.REGLAS[an.BTC] = rm.desde_kraken(an.BTC, KRAKEN_BTC)
        a = self.agente()
        ok = an.operar(a, "COMPRA", an.BTC, 70000.0, "2026-10-20T10:00+00:00", {an.BTC: 1e6})
        self.assertFalse(ok)
        self.assertEqual(a["efectivo"], an.START)
        self.assertEqual(a["posiciones"], {})
        self.assertEqual(an.COLA_OPS, [])

    def test_compra_valida_redondea_cantidad_y_el_sobrante_vuelve_al_efectivo(self):
        an.REGLAS["XEUR"] = rm.Regla("XEUR", 0.01, 0.5, 2, 4, "kraken")      # solo 2 decimales de cantidad
        a = self.agente()
        self.assertTrue(an.operar(a, "COMPRA", "XEUR", 3.0, "2026-10-20T10:00+00:00", {"XEUR": 1e6}))
        q = a["posiciones"]["XEUR"]
        self.assertEqual(q, round(q, 2))
        px = an.ejecucion.precio_compra(3.0, an.SLIP, an.SPREAD)
        gastado = an.START - a["efectivo"]
        self.assertAlmostEqual(gastado, q * px / (1 - an.FEE), places=9)
        self.assertLessEqual(gastado, an.SLOT + 1e-12)

    def test_sin_reglas_conocidas_se_usa_el_supuesto_generico(self):
        a = self.agente()
        self.assertTrue(an.operar(a, "COMPRA", an.BTC, 100.0, "2026-10-20T10:00+00:00", {an.BTC: 1e6}))   # 2 EUR >= 0,5 EUR

    def test_el_agente_no_intenta_comprar_lo_que_nunca_podra_ejecutar(self):
        an.REGLAS[an.BTC] = rm.desde_kraken(an.BTC, KRAKEN_BTC)
        v = {an.BTC: velas([100.0] * 39 + [103.0]) + [vl_.Vela(T0 + 3600 * 40, 70000.0, 70000.0, 70000.0, 70000.0, 1.0)]}
        est = an.estado_nuevo({an.BTC: v[an.BTC][:39]}, T0 + 3600 * 39)
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 40 + 600)
        for a in est["agentes"]:
            self.assertEqual(a["posiciones"], {})
        self.assertTrue(any("minimo" in r[5] for r in an.RECHAZOS))


if __name__ == "__main__":
    unittest.main()
