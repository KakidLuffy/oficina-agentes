import math
import random
import unittest

import metricas as m


def serie(n, mu=0.001, sd=0.01, seed=1):
    rng = random.Random(seed)
    v, out = 100.0, [100.0]
    for _ in range(n):
        v *= 1 + rng.gauss(mu, sd)
        out.append(v)
    return out


class Metricas(unittest.TestCase):
    def test_retornos_simples(self):
        for a, b in zip(m.retornos([100, 110, 99]), [0.1, 99 / 110 - 1]):
            self.assertAlmostEqual(a, b, places=12)

    def test_retornos_ignora_bases_no_positivas_y_vacios(self):
        self.assertEqual(m.retornos([0, 5, None, 6]), [])
        self.assertEqual(m.retornos([]), [])

    def test_muestra_pequena_es_no_estimable(self):
        r = m.retornos(serie(10))
        for f in (m.volatilidad, m.sharpe, m.sortino):
            self.assertEqual(f(r), m.NO_ESTIMABLE)
        self.assertEqual(m.ic_retorno_medio(r), m.NO_ESTIMABLE)
        self.assertEqual(m.factor_beneficio([1, -1, 2]), m.NO_ESTIMABLE)
        self.assertEqual(m.expectativa([1.0] * 5), m.NO_ESTIMABLE)
        self.assertEqual(m.porcentaje_acierto([1.0] * 5), m.NO_ESTIMABLE)

    def test_volatilidad_y_sharpe_valores_conocidos(self):
        r = [0.01, -0.01] * 20
        self.assertAlmostEqual(m.volatilidad(r), math.sqrt(sum(x * x for x in r) / 39), places=9)
        self.assertAlmostEqual(m.sharpe(r), 0.0, places=9)
        self.assertAlmostEqual(m.volatilidad(r, 365), m.volatilidad(r) * math.sqrt(365), places=9)

    def test_serie_constante_no_tiene_sharpe(self):
        self.assertEqual(m.sharpe([0.0] * 40), m.NO_ESTIMABLE)
        self.assertEqual(m.sortino([0.01] * 40), m.NO_ESTIMABLE)    # sin retornos negativos

    def test_sortino_penaliza_solo_las_caidas(self):
        r = [0.02, 0.02, -0.01] * 15
        self.assertGreater(m.sortino(r), m.sharpe(r))

    def test_caida_maxima(self):
        self.assertAlmostEqual(m.caida_maxima([100, 120, 90, 130, 117]), -25.0)
        self.assertEqual(m.caida_maxima([1, 2, 3]), 0.0)
        self.assertEqual(m.caida_maxima([]), 0.0)

    def test_factor_beneficio_expectativa_acierto(self):
        pnl = [3.0, 3.0, 3.0, 3.0, -2.0, -2.0, -2.0, 1.0, 1.0, -1.0]
        self.assertAlmostEqual(m.factor_beneficio(pnl), 14 / 7)
        self.assertAlmostEqual(m.expectativa(pnl), 7 / 10)
        self.assertAlmostEqual(m.porcentaje_acierto(pnl), 60.0)

    def test_factor_beneficio_sin_perdidas_no_estimable(self):
        self.assertEqual(m.factor_beneficio([1.0] * 12), m.NO_ESTIMABLE)

    def test_bootstrap_reproducible_y_contiene_la_media(self):
        r = m.retornos(serie(200))
        a, b = m.ic_retorno_medio(r), m.ic_retorno_medio(r)
        self.assertEqual(a, b)
        self.assertLess(a[0], sum(r) / len(r))
        self.assertGreater(a[1], sum(r) / len(r))

    def test_bootstrap_es_mas_estrecho_con_mas_datos(self):
        corto = m.ic_retorno_medio(m.retornos(serie(60, seed=3)))
        largo = m.ic_retorno_medio(m.retornos(serie(1200, seed=3)))
        self.assertLess(largo[1] - largo[0], corto[1] - corto[0])

    def test_ruido_puro_el_intervalo_incluye_cero(self):
        ic = m.ic_retorno_medio(m.retornos(serie(300, mu=0.0, seed=7)))
        self.assertLessEqual(ic[0], 0 + 1e-9 + 0.002)
        self.assertGreaterEqual(ic[1], 0 - 0.002)

    def test_resumen_y_formato(self):
        s = m.resumen(serie(100), [1.0, -0.5] * 8, 365)
        self.assertEqual(s["periodos"], 100)
        self.assertIsInstance(s["sharpe"], float)
        self.assertEqual(m.fmt(m.NO_ESTIMABLE), "NO ESTIMABLE")
        self.assertEqual(m.fmt((0.001, 0.002), 2, pct=True), "[0.10, 0.20]")
        self.assertEqual(m.fmt(1.234), "1.23")
        e = m.resumen([100, 101], [], None)
        self.assertEqual(e["sharpe"], m.NO_ESTIMABLE)


if __name__ == "__main__":
    unittest.main()
