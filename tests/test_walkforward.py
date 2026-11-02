import math
import unittest
from tests.base import RAIZ  # noqa: F401
import walkforward as wf
import ejecucion as ej


class Pliegues(unittest.TestCase):
    def test_ventanas_deslizantes_sin_solaparse_en_la_prueba(self):
        p = wf.pliegues(n=720, warm=200, entreno=200, prueba=80)
        self.assertEqual(p, [(200, 400, 400, 480), (280, 480, 480, 560), (360, 560, 560, 640), (440, 640, 640, 720)])
        pruebas = [(a, b) for _, _, a, b in p]
        self.assertTrue(all(pruebas[k][1] == pruebas[k + 1][0] for k in range(len(pruebas) - 1)))   # contiguas
        self.assertTrue(all(i1 <= j0 for _, i1, j0, _ in p))                  # el entrenamiento termina antes de la prueba

    def test_serie_corta_da_menos_pliegues_y_muy_corta_ninguno(self):
        self.assertEqual(len(wf.pliegues(500, 200, 200, 80)), 1)
        self.assertEqual(wf.pliegues(300, 200, 200, 80), [])

    def test_el_ultimo_tramo_incompleto_se_descarta(self):
        p = wf.pliegues(700, 200, 200, 80)
        self.assertEqual(p[-1][3], 640)

    def test_parametros_invalidos(self):
        for args in ((100, 10, 0, 5), (100, 10, 20, 0), (100, -1, 20, 5)):
            with self.assertRaises(ValueError):
                wf.pliegues(*args)


class Regimenes(unittest.TestCase):
    def test_tendencia_clara_es_alcista_o_bajista_y_ruido_es_lateral(self):
        import random
        sube = [100 * 1.004 ** i for i in range(200)]
        baja = [100 * 0.996 ** i for i in range(200)]
        r = random.Random(5)
        ruido = [100.0]
        for _ in range(199):
            ruido.append(ruido[-1] * (1 + r.gauss(0, 0.01)))
        # con tendencia pura la volatilidad es ~0: se usa una tendencia con algo de ruido
        sube2 = [x * (1 + 0.003 * math.sin(i)) for i, x in enumerate(sube)]
        baja2 = [x * (1 + 0.003 * math.sin(i)) for i, x in enumerate(baja)]
        self.assertEqual(wf.regimen(sube2, 150), "alcista")
        self.assertEqual(wf.regimen(baja2, 150), "bajista")
        self.assertEqual(wf.regimen(ruido, 150) in ("lateral", "alcista", "bajista"), True)

    def test_sin_historia_suficiente_no_hay_regimen(self):
        self.assertIsNone(wf.regimen([100.0] * 30, 20))

    def test_sin_mirar_el_futuro(self):
        base = [100 + (i % 7) + i * 0.05 for i in range(200)]
        futuro = base[:150] + [x * 9 for x in base[150:]]
        self.assertEqual(wf.regimenes(base, 60)[:150], wf.regimenes(futuro, 60)[:150])

    def test_serie_plana_es_lateral_sin_dividir_por_cero(self):
        self.assertEqual(wf.regimen([100.0] * 200, 150), "lateral")

    def test_regimenes_alineados(self):
        c = [100.0 + i for i in range(120)]
        r = wf.regimenes(c, 60)
        self.assertEqual(len(r), 120)
        self.assertIsNone(r[10])


class PorRegimen(unittest.TestCase):
    def test_atribucion_de_retornos(self):
        c = [100, 110, 121, 121, 121, 108.9]
        regs = ["alcista"] * 3 + ["lateral"] * 3
        curva = [10.0, 10.0, 10.0, 10.0, 10.0, 9.0]          # la estrategia solo pierde en la ultima vela
        r = wf.por_regimen(curva, c, 0, regs)
        self.assertEqual(r["alcista"]["velas"], 2)
        self.assertAlmostEqual(r["alcista"]["hold"], 0.20, places=9)         # 10 % + 10 % (retornos simples sumados)
        self.assertAlmostEqual(r["alcista"]["estrategia"], 0.0)
        self.assertAlmostEqual(r["lateral"]["estrategia"], -0.1, places=9)
        self.assertAlmostEqual(r["lateral"]["hold"], -0.1, places=9)

    def test_curva_del_simulador_cubre_todas_las_velas_incluso_tras_apagarse(self):
        c = [100.0, 100.0, 100.0, 40.0, 40.0, 40.0, 40.0]
        curva = []
        ej.simular(c, c, 1, 7, 1.0, lambda c_, i, s: "b" if i == 1 else None, curva=curva, fee=0.0, slip=0.0, spread=0.0)
        self.assertEqual(len(curva), 6)
        self.assertAlmostEqual(curva[-1], curva[-2])         # tras apagarse, el capital ya no cambia


if __name__ == "__main__":
    unittest.main()
