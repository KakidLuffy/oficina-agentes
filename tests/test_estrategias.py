import random
import unittest
from tests.base import an, RAIZ  # noqa: F401
import estrategias as es
from tests import legacy_estrategias as old


def ult(nombre, precios):
    """Senal de un agente en vivo sobre la ultima vela de 'precios'."""
    return dict(es.AGENTES_VIVOS)[nombre](es.Serie(precios), len(precios) - 1, 1.0)


class Estrategias(unittest.TestCase):
    def test_datos_insuficientes_no_dan_senal(self):
        for nombre, f in es.AGENTES_VIVOS:
            self.assertIsNone(f(es.Serie([1.0] * 5), 4, 1.0), nombre)

    def test_cruce_compra_y_vende(self):
        self.assertEqual(ult("Cruce 10/30", [10.0] * 49 + [30.0]), "b")
        self.assertEqual(ult("Cruce 10/30", [30.0] * 49 + [1.0]), "s")

    def test_momentum_umbrales(self):
        base = [100.0] * 14
        self.assertEqual(ult("Momentum", base[:-1] + [102.0]), "b")
        self.assertEqual(ult("Momentum", base[:-1] + [98.0]), "s")
        self.assertIsNone(ult("Momentum", base[:-1] + [100.5]))

    def test_rebote(self):
        self.assertEqual(ult("Rebote", [100.0] * 20 + [97.0]), "b")
        self.assertEqual(ult("Rebote", [100.0] * 20 + [101.0]), "s")

    def test_filtro_bloquea_compras_bajo_la_media(self):
        f = es.con_filtro(lambda c, i, s: "b", n=10)
        self.assertIsNone(f(es.Serie([10.0] * 14 + [5.0]), 14, 1.0))
        self.assertEqual(f(es.Serie([1.0] * 14 + [5.0]), 14, 1.0), "b")
        self.assertIsNone(f(es.Serie([1.0] * 3), 2, 1.0))
        self.assertEqual(es.con_filtro(lambda c, i, s: "s", n=10)(es.Serie([10.0] * 15), 14, 1.0), "s")

    def test_rapidos(self):
        self.assertEqual(ult("Momentum rapido", [100.0] * 7 + [102.0]), "b")
        self.assertEqual(ult("Rebote rapido", [100.0] * 8 + [98.0]), "b")

    def test_funcionan_con_lista_simple_y_con_serie(self):
        r = random.Random(3)
        p = [100.0]
        for _ in range(120):
            p.append(p[-1] * (1 + r.gauss(0, 0.01)))
        f = es.cruce(5, 20)
        s = es.Serie(p)
        self.assertEqual([f(p, i, 1.0) for i in range(len(p))], [f(s, i, 1.0) for i in range(len(p))])


def serie_aleatoria(semilla, n=260, vol=0.01, deriva=0.0):
    r = random.Random(semilla)
    p = [100.0]
    for _ in range(n - 1):
        p.append(p[-1] * (1 + r.gauss(deriva, vol)))
    return p


NOMBRES_VIEJOS = {n: f for n, f in old.AGENTES}


class EquivalenciaConLaVersionAnterior(unittest.TestCase):
    """El modulo unico debe dar las MISMAS senales que las funciones antiguas de la simulacion
    (salvo en las primeras velas de la serie, donde el codigo antiguo exigia una vela de mas)."""

    def test_mismas_senales_en_todas_las_velas_tras_el_arranque(self):
        casos = [(1, 0.01, 0.0), (2, 0.02, 0.001), (3, 0.005, -0.001), (4, 0.03, 0.0), (5, 0.012, 0.0005)]
        for semilla, vol, deriva in casos:
            p = serie_aleatoria(semilla, 300, vol, deriva)
            s = es.Serie(p)
            for nombre, nuevo in es.AGENTES_VIVOS:
                viejo = NOMBRES_VIEJOS[nombre]
                distintas = [i for i in range(40, len(p)) if nuevo(s, i, 1.0) != viejo(p[:i + 1])]
                self.assertEqual(distintas, [], f"{nombre} (semilla {semilla}) difiere en {distintas[:5]}")

    def test_hay_senales_de_los_dos_tipos(self):          # la prueba anterior no seria util si nunca hubiera senales
        p = serie_aleatoria(11, 600, 0.02)
        s = es.Serie(p)
        for nombre, f in es.AGENTES_VIVOS:
            vistas = {f(s, i, 1.0) for i in range(40, len(p))}
            self.assertTrue({"b", "s"} <= vistas or nombre == "Cruce 10/30 + filtro", nombre)


class SinMirarElFuturo(unittest.TestCase):
    def test_la_senal_en_i_no_cambia_si_se_anaden_o_cambian_velas_posteriores(self):
        p = serie_aleatoria(7, 300, 0.015)
        futuro = p[:200] + [x * 5 for x in p[200:]]          # el futuro cambia por completo
        for nombre, f in es.AGENTES_VIVOS:
            a, b = es.Serie(p), es.Serie(futuro)
            for i in range(30, 200):
                self.assertEqual(f(a, i, 1.0), f(b, i, 1.0), f"{nombre} mira el futuro en i={i}")
        for f in (es.cruce(5, 20), es.momentum(12, .012), es.rebote(20, .015), es.ruptura(20, 10),
                  es.con_volatilidad(es.cruce(5, 20), 0.5), es.consenso):
            a, b = es.Serie(p), es.Serie(futuro)
            for i in range(30, 200):
                self.assertEqual(f(a, i, 1.0), f(b, i, 1.0))

    def test_laboratorio_y_comparacion_usan_el_mismo_codigo(self):
        import laboratorio
        import comparar_estrategias as ce
        self.assertIs(laboratorio.Serie, es.Serie)
        self.assertIs(ce.media, es.media)
        self.assertIs(an.estrategias, es)
        self.assertIs(an.AGENTES, es.AGENTES_VIVOS)


if __name__ == "__main__":
    unittest.main()
