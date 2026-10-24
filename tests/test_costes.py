import unittest
from tests.base import RAIZ  # noqa: F401
import costes as co


class Costes(unittest.TestCase):
    def test_base_es_maker_040(self):
        c = co.BASE
        self.assertEqual((c.fee, c.slip, c.spread), (0.004, 0.0005, 0.0008))

    def test_estres_es_taker_080_y_duplica_horquilla_y_deslizamiento(self):
        e = co.ESTRES
        self.assertEqual(e.fee, 0.008)
        self.assertAlmostEqual(e.slip, co.BASE.slip * 2)
        self.assertAlmostEqual(e.spread, co.BASE.spread * 2)
        self.assertGreater(e.coste_ida_y_vuelta(), co.BASE.coste_ida_y_vuelta())

    def test_horquilla_y_deslizamiento_crecen_al_bajar_la_liquidez(self):
        alta, media, baja = (co.por_liquidez(v) for v in (5_000_000, 300_000, 20_000))
        self.assertLess(alta.spread, media.spread)
        self.assertLess(media.spread, baja.spread)
        self.assertLess(alta.slip, media.slip)
        self.assertLess(media.slip, baja.slip)
        self.assertEqual(alta.fee, media.fee)                 # la comision no depende de la liquidez

    def test_volumen_desconocido_se_trata_como_poco_liquido(self):
        self.assertEqual(co.por_liquidez(None), co.por_liquidez(0))
        self.assertEqual(co.por_liquidez(float("nan")), co.por_liquidez(0))

    def test_btc_siempre_es_liquido(self):
        self.assertEqual(co.por_liquidez(0, es_btc=True), co.por_liquidez(10 ** 9))

    def test_umbrales(self):
        self.assertEqual(co.nivel(1_000_000), "alta")
        self.assertEqual(co.nivel(999_999), "media")
        self.assertEqual(co.nivel(100_000), "media")
        self.assertEqual(co.nivel(99_999), "baja")

    def test_precios_de_ejecucion(self):
        c = co.BASE
        self.assertAlmostEqual(c.precio_compra(100.0), 100.0 * (1 + c.spread / 2 + c.slip))
        self.assertAlmostEqual(c.precio_venta(100.0), 100.0 * (1 - c.spread / 2 - c.slip))

    def test_coste_ida_y_vuelta_coincide_con_la_formula_exacta(self):
        c = co.BASE
        directo = 1 - (1 - c.fee) ** 2 * c.precio_venta(1.0) / c.precio_compra(1.0)
        self.assertAlmostEqual(c.coste_ida_y_vuelta(), directo, places=12)

    def test_escalado(self):
        c = co.BASE.escalar(spread=3.0, slip=2.0)
        self.assertAlmostEqual(c.spread, co.BASE.spread * 3)
        self.assertAlmostEqual(c.slip, co.BASE.slip * 2)
        self.assertEqual(c.fee, co.BASE.fee)

    def test_valida_parametros(self):
        for kw in ({"fee": -0.1}, {"slip": float("nan")}, {"spread": 2.0}):
            with self.assertRaises(ValueError):
                co.Costes(**{"fee": 0.004, "slip": 0.0005, "spread": 0.0008, **kw})


if __name__ == "__main__":
    unittest.main()
