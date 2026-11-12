"""Pruebas del laboratorio v2 (sin internet):  python -m unittest test_laboratorio"""
import contextlib
import io
import json
import os
import random
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

import comparar_estrategias as ce
import laboratorio as lab


def serie_diaria(precios, desde=(2019, 1, 1)):
    t0 = int(datetime(*desde, tzinfo=timezone.utc).timestamp())
    return lab.Serie(precios, [t0 + i * 86400 for i in range(len(precios))])


def paseo(n, semilla, deriva=0.0, vol=0.03):
    random.seed(semilla)
    p, out = 100.0, []
    for _ in range(n):
        p *= 1 + random.gauss(deriva, vol)
        out.append(p)
    return out


def oraculo(c, i, s):
    """Variante tramposa que mira el precio de mañana: debe aprobar casi siempre."""
    if i + 1 >= len(c):
        return None
    return "b" if c[i + 1] > c[i] * 1.01 else ("s" if c[i + 1] < c[i] else None)


class TestLaboratorio(unittest.TestCase):
    def test_simular_igual_que_comparar_estrategias(self):
        c = serie_diaria(paseo(900, 1))
        for fn in (lab.cruce(5, 20), lab.momentum(12, 0.012), lab.rebote(20, 0.015)):
            r = lab.simular(c, 250, 800, 1.0, fn)
            res, ops, hold, dd = ce.simular(c, 250, 800, 1.0, fn)
            self.assertAlmostEqual(r["res"], res, places=9)
            self.assertEqual(r["ops"], ops)
            self.assertAlmostEqual(r["hold"], hold, places=9)
            self.assertAlmostEqual(r["dd"], dd, places=9)
            self.assertTrue(0.0 <= r["expo"] <= 1.0)

    def test_exposicion_y_caida_de_mantener(self):
        c = serie_diaria([100.0] * 10 + [80.0] * 10)
        siempre = lambda c, i, s: "b"
        nunca = lambda c, i, s: None
        self.assertAlmostEqual(lab.simular(c, 0, 20, 1.0, siempre)["expo"], 1.0)
        r = lab.simular(c, 0, 20, 1.0, nunca)
        self.assertEqual(r["expo"], 0.0)
        self.assertAlmostEqual(r["dd_hold"], 20.0, delta=0.5)   # incluye el coste de la compra
        self.assertEqual(r["dd"], 0.0)

    def test_aprueba(self):
        base = {"ops": 2, "res": 1.0, "hold": 10.0, "expo": 0.05, "dd": 5.0, "dd_hold": 20.0}
        self.assertTrue(lab.aprueba(base))                                   # 1 > 0,05 x 10
        self.assertFalse(lab.aprueba({**base, "ops": 1}))                    # pocas operaciones
        self.assertFalse(lab.aprueba({**base, "expo": 0.5}))                 # no supera a la misma exposición
        self.assertFalse(lab.aprueba({**base, "dd": 25.0}))                  # cae más que mantener
        self.assertTrue(lab.aprueba({**base, "res": -1.0, "hold": -40.0, "expo": 0.5}))  # pierde menos con la misma exposición

    def test_tramos_por_anio_natural(self):
        c = serie_diaria(paseo(1000, 2), desde=(2019, 7, 1))
        tr = lab.tramos_anuales(c, 1440)
        self.assertEqual(sorted(tr), [2020, 2021, 2022])
        a, b, frac = tr[2020]
        self.assertEqual(datetime.fromtimestamp(c.t[a], timezone.utc).date().isoformat(), "2020-01-17")  # tras 200 velas
        self.assertEqual(datetime.fromtimestamp(c.t[b - 1], timezone.utc).date().isoformat(), "2020-12-31")
        self.assertAlmostEqual(tr[2021][2], 1.0)

    def series_prueba(self, n=8):
        return [{"moneda": f"M{k}", "vela": "1 día", "minutos": 1440, "c": serie_diaria(paseo(2600, 10 + k))} for k in range(n)]

    def test_oraculo_es_candidata_y_el_azar_no(self):
        series = self.series_prueba()
        todas = [("Tramposo", "Oráculo A", oraculo, None), ("Tramposo", "Oráculo B", oraculo, lab.SALIDA)]
        todas += [("Azar", f"Moneda al aire {k}", (lambda k: lambda c, i, s: random.Random(k * 100000 + i).choice("bs "))(k), None)
                  for k in range(20)]
        r = lab.examinar(series, todas, 1440)
        nombres = [f["nombre"] for f in r["candidatas"]]
        self.assertIn("Oráculo A", nombres)
        self.assertFalse(any(n.startswith("Moneda") for n in nombres))
        self.assertEqual(r["veredicto"], "posible")
        self.assertEqual([b for _, b, _ in r["pliegues"]], [2021, 2022, 2023, 2024, 2025])   # 2019 sin 75 % tras el calentamiento

    def test_nada_que_aprobar(self):
        series = self.series_prueba(4)
        nunca = [("Quieto", "Nunca compra", lambda c, i, s: None, None)]
        r = lab.examinar(series, nunca, 1440)
        self.assertEqual(r["veredicto"], "ninguna")              # 0 operaciones: no aprueba nunca

    def test_demo_completa(self):
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.argv", ["laboratorio.py", "--demo", "--out", d]):
            with contextlib.redirect_stdout(io.StringIO()):
                lab.main()
            with open(os.path.join(d, "laboratorio.json"), encoding="utf-8") as f:
                j = json.load(f)
        self.assertEqual(j["version"], 2)
        self.assertEqual(set(j["por_vela"]), {"1 día", "6 h"})
        for k in ("veredicto", "texto", "probadas", "tasa_azar", "criterio", "series", "analistas", "candidatas", "mejores_entreno"):
            self.assertIn(k, j)                                   # lo que leen index.html y director.py
        for x in j["mejores_entreno"]:
            for k in ("nombre", "analista", "train_dif", "test_dif", "ok", "total", "pasa"):
                self.assertIn(k, x)
        self.assertIn(j["veredicto"], ("ninguna", "ruido", "posible"))

    def test_fuerza_relativa_alineada_por_fecha(self):
        t0 = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp())
        btc = lab.Serie([1.0, 2.0, 3.0, 4.0], [t0 + i * 86400 for i in range(4)])
        otra = lab.Serie([9.0, 9.0, 9.0], [t0 + 2 * 86400, t0 + 3 * 86400, t0 + 4 * 86400])   # empieza 2 días después
        lab.alinear_ref([{"moneda": "BTC", "minutos": 1440, "c": btc}, {"moneda": "X", "minutos": 1440, "c": otra}])
        self.assertEqual(otra.ref, [3.0, 4.0, 4.0])              # el día sin vela de BTC usa la última conocida
        self.assertEqual(btc.ref, [1.0, 2.0, 3.0, 4.0])


    def test_descargar_pagina_hacia_atras(self):
        ahora = 1_800_000_000
        dia = ahora // 86400 * 86400
        pag1 = [[dia - k * 86400, 1, 2, 1, 100.0 + k, 5] for k in range(1, 301)]          # Coinbase: más reciente primero
        pag2 = [[dia - k * 86400, 1, 2, 1, 100.0 + k, 5] for k in range(301, 351)]
        with mock.patch.object(lab.ce, "get_json", side_effect=[pag1, pag2, [], []]) as g, \
             mock.patch.object(lab.time, "time", return_value=ahora), mock.patch.object(lab.time, "sleep"):
            ts, c = lab.descargar("BTC-EUR", 1440)
        self.assertEqual(len(ts), 350)
        self.assertEqual(ts, sorted(ts))
        self.assertEqual(c[-1], 101.0)                           # cierre más reciente al final
        self.assertIn("granularity=86400", g.call_args_list[0].args[0])


    def test_candidatas_casi_iguales_cuentan_como_una_idea(self):
        base = [1.0, -2.0, 3.0, 0.5, -1.0, 2.0]
        casi = [x * 1.1 + 0.01 for x in base]                    # la misma estrategia con otro parámetro
        otra = [0.2, 1.0, -0.5, 2.0, 1.5, -2.0]                   # una idea distinta
        fs = [{"nombre": "A", "vec": base}, {"nombre": "A'", "vec": casi}, {"nombre": "B", "vec": otra}]
        ideas = lab.agrupar_ideas(fs)
        self.assertEqual([[f["nombre"] for f in g] for g in ideas], [["A", "A'"], ["B"]])
        self.assertEqual(fs[1]["idea"], "A")


if __name__ == "__main__":
    unittest.main()
