import unittest
from tests.base import RAIZ  # noqa: F401
import ejecucion as ej


def siempre(senales):
    """Estrategia de prueba: devuelve la senal indicada para cada indice."""
    return lambda c, i, s: senales.get(i)


class Simulador(unittest.TestCase):
    def test_compra_se_ejecuta_a_la_apertura_siguiente_no_al_cierre_de_decision(self):
        c = [100.0, 100.0, 100.0, 100.0, 100.0]
        o = [100.0, 100.0, 110.0, 100.0, 100.0]          # la vela 2 abre mucho mas alto
        # decide comprar en i=1 -> ejecuta a o[2]=110, no a c[1]=100
        r, ops, _, _ = ej.simular(c, o, 1, 5, 1.0, siempre({1: "b"}), fee=0.0, slip=0.0, spread=0.0, start=10.0)
        self.assertEqual(ops, 1)
        self.assertAlmostEqual(r, 10.0 / 110.0 * 100.0 - 10.0, places=9)     # unidades compradas a 110, valoradas a 100

    def test_la_decision_de_la_ultima_vela_no_se_ejecuta(self):
        c = [100.0] * 5
        r, ops, _, _ = ej.simular(c, c, 1, 5, 1.0, siempre({4: "b"}))
        self.assertEqual(ops, 0)
        self.assertEqual(r, 0.0)

    def test_ida_y_vuelta_con_costes(self):
        c = [100.0] * 8
        r, ops, _, _ = ej.simular(c, c, 1, 8, 1.0, siempre({1: "b", 3: "s"}))
        esperado = 10.0 * (1 - ej.FEE) / ej.precio_compra(100.0) * ej.precio_venta(100.0) * (1 - ej.FEE) - 10.0
        self.assertEqual(ops, 2)
        self.assertAlmostEqual(r, esperado, places=9)
        self.assertLess(r, 0)

    def test_stop_decidido_al_cierre_sale_en_la_apertura_siguiente(self):
        c = [100.0, 100.0, 100.0, 97.0, 97.0, 97.0, 97.0]
        o = [100.0, 100.0, 100.0, 100.0, 96.0, 97.0, 97.0]
        opc = {"stop": 0.02, "objetivo": 0.5, "espera": 1}
        r, ops, _, _ = ej.simular(c, o, 1, 7, 1.0, siempre({1: "b"}), opc, fee=0.0, slip=0.0, spread=0.0)
        self.assertEqual(ops, 2)                          # compra a o[2]=100; en i=3 cae 3 % -> vende a o[4]=96
        self.assertAlmostEqual(r, 10.0 * 96.0 / 100.0 - 10.0, places=9)

    def test_mantener_entra_en_la_misma_vela_que_podria_entrar_la_estrategia(self):
        c = [100.0, 100.0, 120.0, 120.0]
        o = [100.0, 100.0, 100.0, 120.0]
        _, _, m, _ = ej.simular(c, o, 0, 4, 1.0, siempre({}), fee=0.0, slip=0.0, spread=0.0)
        self.assertAlmostEqual(m, 10.0 * 120.0 / 100.0 - 10.0, places=9)     # entra a o[1]=100

    def test_apagado_por_riesgo(self):
        c = [100.0, 100.0, 100.0, 50.0, 50.0, 50.0]
        r, ops, _, dd = ej.simular(c, c, 1, 6, 1.0, siempre({1: "b"}), fee=0.0, slip=0.0, spread=0.0)
        self.assertEqual(ops, 1)
        self.assertGreater(dd, 40)
        self.assertAlmostEqual(r, 10.0 * 50.0 / 100.0 - 10.0, places=9)      # vendio al precio actual al apagarse

    def test_sin_mirar_el_futuro(self):
        import random
        import estrategias as es
        r = random.Random(1)
        c = [100.0]
        for _ in range(300):
            c.append(c[-1] * (1 + r.gauss(0, 0.01)))
        o = [c[0]] + c[:-1]
        base = ej.simular(c, o, 40, 200, 1.0, es.cruce(5, 20))
        c2, o2 = c[:200] + [x * 3 for x in c[200:]], o[:200] + [x * 3 for x in o[200:]]
        self.assertEqual(base, ej.simular(c2, o2, 40, 200, 1.0, es.cruce(5, 20)))
        self.assertGreater(base[1], 0)


class EscenariosDeCostes(unittest.TestCase):
    def test_los_costes_duros_nunca_mejoran_el_resultado(self):
        import math
        import costes as co
        import estrategias as es
        for periodo in (12, 15, 20, 30):                            # ondas lentas: pocas operaciones, sin apagado por riesgo
            c = [100.0 * (1 + 0.08 * math.sin(i / periodo)) for i in range(400)]
            o = [c[0]] + c[:-1]
            base = ej.simular(c, o, 50, 400, 1.0, es.cruce(5, 20), costes=co.BASE)
            duro = ej.simular(c, o, 50, 400, 1.0, es.cruce(5, 20), costes=co.ESTRES)
            self.assertGreater(base[1], 1)
            self.assertLess(base[1], 40)
            self.assertEqual(base[1], duro[1])                      # mismas operaciones
            self.assertLessEqual(duro[0], base[0] + 1e-9)
            self.assertLessEqual(duro[2], base[2] + 1e-9)           # y tambien "mantener" sale peor

    def test_costes_sueltos_y_objeto_dan_lo_mismo(self):
        import costes as co
        c = [100.0 + (i % 7) for i in range(60)]
        a = ej.simular(c, c, 5, 60, 1.0, lambda c_, i, s: "b" if i % 10 == 0 else ("s" if i % 10 == 5 else None))
        b = ej.simular(c, c, 5, 60, 1.0, lambda c_, i, s: "b" if i % 10 == 0 else ("s" if i % 10 == 5 else None), costes=co.BASE)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
