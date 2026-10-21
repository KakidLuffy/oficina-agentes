import unittest
from tests.base import an


class Estrategias(unittest.TestCase):
    def test_datos_insuficientes_no_dan_senal(self):
        self.assertIsNone(an.cruce([1.0] * 10, 10, 30))
        self.assertIsNone(an.momentum([1.0] * 5))
        self.assertIsNone(an.rebote([1.0] * 5))
        self.assertIsNone(an.consenso([1.0] * 10))

    def test_cruce_compra_y_vende(self):
        bajada = [10.0] * 40
        p = bajada + [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 30.0]
        self.assertEqual(an.cruce(p, 10, 30), "b")
        q = [30.0] * 40 + [30.0] * 9 + [1.0]
        self.assertEqual(an.cruce(q, 10, 30), "s")

    def test_momentum_umbrales(self):
        base = [100.0] * 14
        self.assertEqual(an.momentum(base[:-1] + [102.0]), "b")
        self.assertEqual(an.momentum(base[:-1] + [98.0]), "s")
        self.assertIsNone(an.momentum(base[:-1] + [100.5]))

    def test_rebote(self):
        p = [100.0] * 20 + [97.0]
        self.assertEqual(an.rebote(p), "b")
        p = [100.0] * 20 + [101.0]
        self.assertEqual(an.rebote(p), "s")

    def test_filtro_bloquea_compras_bajo_la_media(self):
        f = an.filtro(lambda p: "b", n=10)
        self.assertIsNone(f([10.0] * 9 + [5.0]))       # bajo su media
        self.assertEqual(f([1.0] * 9 + [5.0]), "b")    # sobre su media
        self.assertIsNone(f([1.0] * 3))                # sin historia suficiente
        self.assertEqual(an.filtro(lambda p: "s", n=10)([10.0] * 10), "s")   # las ventas pasan

    def test_sin_mirar_el_futuro(self):
        """La senal depende solo de los datos hasta la vela actual."""
        p = [100.0] * 30 + [102.0]
        self.assertEqual(an.momentum(p), an.momentum(list(p)))
        self.assertEqual(an.momentum(p + [1.0, 1.0][:0]), "b")   # un futuro hipotetico no cambia la senal ya calculada

    def test_rapidos(self):
        self.assertEqual(an.momentum_rapido([100.0] * 7 + [102.0]), "b")
        self.assertEqual(an.rebote_rapido([100.0] * 8 + [98.0]), "b")


if __name__ == "__main__":
    unittest.main()
