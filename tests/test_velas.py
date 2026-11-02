import math
import unittest
from tests.base import RAIZ  # noqa: F401
import velas as vl

H = 3600
T = 1_700_000_000 - (1_700_000_000 % H)


def v(i, c=100.0, o=None, h=None, lo=None, vol=1.0):
    o = c if o is None else o
    return vl.Vela(T + i * H, o, max(o, c) if h is None else h, min(o, c) if lo is None else lo, c, vol)


def tipos(inc):
    return [x["tipo"] for x in inc]


class Validar(unittest.TestCase):
    def test_serie_limpia_no_cambia(self):
        s = [v(i, 100 + i) for i in range(10)]
        out, inc = vl.validar(s, H, T + 10 * H)
        self.assertEqual(out, s)
        self.assertEqual(inc, [])

    def test_descarta_no_finitos_y_precios_no_positivos(self):
        s = [v(0), v(1, c=float("nan")), v(2, c=float("inf")), v(3, c=0.0), v(4, c=-5.0), v(5)]
        out, inc = vl.validar(s, H, T + 10 * H)
        self.assertEqual([x.ts for x in out], [T + 5 * H])     # tras los huecos solo queda la cola contigua
        self.assertIn("no_finito", tipos(inc))
        self.assertIn("precio_no_positivo", tipos(inc))

    def test_volumen_negativo(self):
        out, inc = vl.validar([v(0), v(1, vol=-1.0), v(2)], H, T + 5 * H)
        self.assertIn("volumen_negativo", tipos(inc))
        self.assertNotIn(T + H, [x.ts for x in out])

    def test_ohlc_incoherente(self):
        malo = vl.Vela(T + H, 100.0, 90.0, 95.0, 100.0, 1.0)    # maximo menor que apertura/cierre
        out, inc = vl.validar([v(0), malo, v(2)], H, T + 5 * H)
        self.assertIn("ohlc_incoherente", tipos(inc))
        self.assertNotIn(T + H, [x.ts for x in out])

    def test_duplicados_se_quedan_con_la_ultima(self):
        s = [v(0), v(1, 100.0), v(1, 101.0), v(2)]
        out, inc = vl.validar(s, H, T + 5 * H)
        self.assertEqual([x.c for x in out if x.ts == T + H], [101.0])
        self.assertIn("duplicada", tipos(inc))

    def test_desordenadas_se_ordenan_y_se_avisa(self):
        s = [v(2), v(0), v(1)]
        out, inc = vl.validar(s, H, T + 5 * H)
        self.assertEqual([x.ts for x in out], [T, T + H, T + 2 * H])
        self.assertIn("desordenada", tipos(inc))

    def test_marca_temporal_no_alineada(self):
        raro = vl.Vela(T + H + 17, 100.0, 100.0, 100.0, 100.0, 1.0)
        out, inc = vl.validar([v(0), raro, v(2)], H, T + 5 * H)
        self.assertIn("no_alineada", tipos(inc))
        self.assertNotIn(T + H + 17, [x.ts for x in out])

    def test_hueco_se_avisa_nunca_se_rellena_y_solo_se_usa_la_cola_contigua(self):
        s = [v(0), v(1), v(2), v(5), v(6), v(7)]               # faltan las velas 3 y 4
        out, inc = vl.validar(s, H, T + 10 * H)
        self.assertEqual([x.ts for x in out], [T + 5 * H, T + 6 * H, T + 7 * H])
        hueco = [x for x in inc if x["tipo"] == "hueco"][0]
        self.assertEqual(hueco["faltan"], 2)

    def test_vela_abierta_no_es_un_error(self):
        s = [v(0), v(1), v(2)]
        out, inc = vl.validar(s, H, T + 2 * H + 100)           # la ultima aun no ha cerrado
        self.assertEqual(len(out), 3)
        self.assertEqual(inc, [])

    def test_salto_anomalo_bloquea_compras_pero_conserva_datos(self):
        s = [v(0, 100.0), v(1, 100.0), v(2, 300.0)]
        out, inc = vl.validar(s, H, T + 5 * H)
        self.assertEqual(len(out), 3)
        self.assertIn("salto_anomalo", tipos(inc))
        self.assertTrue(vl.hay_bloqueo(inc))

    def test_lista_vacia(self):
        self.assertEqual(vl.validar([], H, T), ([], []))

    def test_desde_kraken_convierte_y_tolera_basura(self):
        f = [T, "100.0", "101.0", "99.0", "100.5", "100.2", "12.5", 7]
        x = vl.desde_kraken(f)
        self.assertEqual((x.ts, x.o, x.h, x.l, x.c, x.v), (T, 100.0, 101.0, 99.0, 100.5, 12.5))
        y = vl.desde_kraken([T, "x", "1", "1", "1", "1", "1", 1])
        self.assertTrue(math.isnan(y.o))


if __name__ == "__main__":
    unittest.main()
