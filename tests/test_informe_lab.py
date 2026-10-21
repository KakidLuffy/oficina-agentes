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
            m = informe.metricas(h, o, ["A"])["A"]
            self.assertEqual((m.ganadoras, m.perdedoras, m.neutras), (1, 1, 0))
            self.assertAlmostEqual(m.caida, -10.0)

    def escribir_ops(self, d, filas):
        o = os.path.join(d, "o.csv")
        with open(o, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"])
            for i, (tipo, imp) in enumerate(filas):
                w.writerow([f"2026-01-01T{i:02d}:00", "A", "X", tipo, 1, imp, "", 0])
        h = os.path.join(d, "h.csv")
        open(h, "w").write("fecha_utc,A\nt1,10\n")
        return h, o

    def test_diferencias_pequenas_se_clasifican_bien_con_precision_completa(self):
        with tempfile.TemporaryDirectory() as d:
            # con 2 decimales las dos serian 2.00 (empate/perdida); con 8 decimales la venta gana 0,003 EUR
            h, o = self.escribir_ops(d, [("COMPRA", "2.00100000"), ("VENTA", "2.00400000")])
            m = informe.metricas(h, o, ["A"])["A"]
            self.assertEqual((m.ganadoras, m.perdedoras, m.neutras), (1, 0, 0))

    def test_igualdad_exacta_es_neutra_no_perdedora(self):
        with tempfile.TemporaryDirectory() as d:
            h, o = self.escribir_ops(d, [("COMPRA", "2.00"), ("VENTA", "2.00")])
            m = informe.metricas(h, o, ["A"])["A"]
            self.assertEqual((m.ganadoras, m.perdedoras, m.neutras, m.cerradas), (0, 0, 1, 1))

    def test_importe_ilegible_se_ignora_sin_romper(self):
        with tempfile.TemporaryDirectory() as d:
            h, o = self.escribir_ops(d, [("COMPRA", "abc"), ("COMPRA", "2.0"), ("VENTA", "1.5")])
            m = informe.metricas(h, o, ["A"])["A"]
            self.assertEqual((m.ganadoras, m.perdedoras), (0, 1))

    def test_grafico_y_metricas_toleran_columnas_vacias_de_agentes_nuevos(self):
        with tempfile.TemporaryDirectory() as d:
            h = os.path.join(d, "h.csv")
            open(h, "w").write("fecha_utc,A,B,Comprar y mantener\n2026-01-01T00:00,10,,10\n2026-01-01T01:00,10.5,,10.1\n2026-01-01T02:00,10.2,10,10.2\n")
            o = os.path.join(d, "o.csv")
            open(o, "w").write(",".join(["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"]) + "\n")
            m = informe.metricas(h, o, ["A", "B"])
            self.assertEqual(m["B"].caida, 0.0)                 # una sola observacion real
            svg = os.path.join(d, "g.svg")
            self.assertTrue(informe.grafico_svg(h, svg, ["A", "B"]))
            txt = open(svg).read()
            self.assertEqual(txt.count("<polyline"), 3)         # A, B (un punto) y Comprar y mantener: sin romper
            self.assertNotIn("nan", txt.lower())

    def test_decimal_no_acumula_error_de_coma_flotante(self):
        self.assertTrue(informe.dec("0.1") + informe.dec("0.2") == informe.dec("0.3"))


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
