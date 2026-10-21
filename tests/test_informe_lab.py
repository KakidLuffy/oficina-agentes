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
