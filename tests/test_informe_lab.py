import csv
import os
import tempfile
import unittest
from tests.base import RAIZ  # noqa: F401
import informe
import laboratorio


class Informe(unittest.TestCase):
    def test_caida_maxima(self):
        self.assertAlmostEqual(informe.caida_maxima([10, 12, 9, 11]), -25.0)
        self.assertEqual(informe.caida_maxima([1, 2, 3]), 0.0)
        self.assertEqual(informe.caida_maxima([]), 0.0)

    def test_metricas_ganadoras_y_perdedoras(self):
        with tempfile.TemporaryDirectory() as d:
            h, o = os.path.join(d, "h.csv"), os.path.join(d, "o.csv")
            open(h, "w").write("fecha_utc,A\nt1,10\nt2,9\n")
            with open(o, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"])
                w.writerows([["1", "A", "X", "COMPRA", 1, 2, "", 0], ["2", "A", "X", "VENTA", 1, 2.5, "", 0],
                             ["3", "A", "X", "COMPRA", 1, 2, "", 0], ["4", "A", "X", "VENTA", 1, 1.5, "", 0]])
            cm, g, p = informe.metricas(h, o, ["A"])["A"]
            self.assertEqual((g, p), (1, 1))
            self.assertAlmostEqual(cm, -10.0)


class Laboratorio(unittest.TestCase):
    def test_variantes_no_vacias_y_con_nombre_unico(self):
        v = laboratorio.variantes()
        self.assertGreater(len(v), 50)
        nombres = [x[1] for x in v]
        self.assertEqual(len(nombres), len(set(map(str, nombres))))


if __name__ == "__main__":
    unittest.main()


class AlineacionTemporal(unittest.TestCase):
    H = 3600
    T = 1_700_000_000 - (1_700_000_000 % 3600)

    def serie(self, cierres, desde):
        return laboratorio.Serie(cierres, [self.T + (desde + k) * self.H for k in range(len(cierres))])

    def test_alinear_por_marca_temporal_y_no_por_posicion(self):
        btc = self.serie([100.0 + k for k in range(50)], 0)
        moneda = self.serie([10.0] * 40, 10)               # empieza 10 horas despues
        idx = laboratorio.alinear(moneda, btc)
        self.assertEqual(idx[0], 10)
        self.assertEqual(idx[-1], 49)
        sin_par = self.serie([1.0] * 3, 80)
        self.assertEqual(laboratorio.alinear(sin_par, btc), [None, None, None])

    def test_relativa_usa_el_btc_de_la_misma_hora(self):
        # BTC sube 1 por vela; la moneda empieza mas tarde. Con alineacion por posicion se compararia con el BTC equivocado.
        btc = self.serie([100.0 + k for k in range(60)], 0)
        moneda = self.serie([10.0 * (1.03 ** k) for k in range(40)], 20)
        moneda.ref, moneda.ref_idx = btc, laboratorio.alinear(moneda, btc)
        f = laboratorio.relativa(6, 0.0)
        self.assertEqual(f(moneda, 20, 1.0), "b")           # sube 19 % vs BTC ~6 %
        moneda.ref_idx = [None] * len(moneda)
        self.assertIsNone(f(moneda, 20, 1.0))                # sin hora comun: no hay senal

    def test_solo_cerradas_quita_la_vela_abierta_por_marca_temporal(self):
        import velas as vl
        v = [vl.Vela(self.T + k * self.H, 1, 1, 1, 1, 1) for k in range(5)]
        ahora = self.T + 4 * self.H + 100                     # la ultima aun no ha cerrado
        self.assertEqual(len(laboratorio.solo_cerradas(v, 60, ahora)), 4)
        self.assertEqual(len(laboratorio.solo_cerradas(v, 60, self.T + 5 * self.H)), 5)   # todas cerradas: no se pierde ninguna

    def test_demo_produce_marcas_alineadas_entre_monedas(self):
        a, b = laboratorio.demo("BTC", 240), laboratorio.demo("ETH", 240)
        self.assertEqual([x.ts for x in a], [x.ts for x in b])
