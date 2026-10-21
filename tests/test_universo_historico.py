import unittest
from tests.base import RAIZ  # noqa: F401
import universo_historico as uh
import ejecucion as ej


def serie_vol(valores, t0=0, paso=100):
    return [(t0 + paso * i, v) for i, v in enumerate(valores)]


class Membresia(unittest.TestCase):
    def test_top_n_por_volumen_reciente_en_cada_fecha(self):
        datos = {"A": serie_vol([10] * 10), "B": serie_vol([5] * 10), "C": serie_vol([1] * 10)}
        m = uh.membresia(datos, n=2, ventana=3)
        self.assertTrue(m["A"][9] and m["B"][9])
        self.assertFalse(m["C"][9])

    def test_el_ranking_cambia_con_el_tiempo(self):
        # C pasa de nada a lo mas negociado; A cae
        datos = {"A": serie_vol([10] * 10 + [1] * 10), "B": serie_vol([5] * 20), "C": serie_vol([1] * 10 + [50] * 10)}
        m = uh.membresia(datos, n=2, ventana=3)
        self.assertTrue(m["A"][9])
        self.assertFalse(m["C"][9])
        self.assertTrue(m["C"][19])
        self.assertFalse(m["A"][19])

    def test_sin_mirar_el_futuro(self):
        base = {"A": serie_vol([10] * 20), "B": serie_vol([5] * 20), "C": serie_vol([1] * 10 + [1] * 10)}
        futuro = {"A": serie_vol([10] * 20), "B": serie_vol([5] * 20), "C": serie_vol([1] * 10 + [1000] * 10)}
        a, b = uh.membresia(base, 2, 3), uh.membresia(futuro, 2, 3)
        for k in ("A", "B", "C"):
            self.assertEqual(a[k][:10], b[k][:10])            # lo que pasa despues de la vela 10 no cambia el pasado

    def test_moneda_sin_historia_suficiente_no_es_miembro(self):
        datos = {"A": serie_vol([10] * 10), "NUEVA": serie_vol([999] * 3, t0=700)}
        m = uh.membresia(datos, n=2, ventana=5)
        self.assertEqual(m["NUEVA"], [False, False, False])  # no hay 5 velas todavia: no se puede saber si estaba en el top

    def test_alineacion_por_marca_temporal_entre_monedas_con_distinto_inicio(self):
        datos = {"A": serie_vol([10] * 10, t0=0), "B": serie_vol([5] * 10, t0=300)}     # B empieza 3 velas despues
        m = uh.membresia(datos, n=1, ventana=2)
        self.assertEqual(len(m["A"]), 10)
        self.assertEqual(len(m["B"]), 10)
        self.assertFalse(any(m["B"][:7]))                     # mientras A cotiza (hasta ts 900), A esta siempre por delante de B
        self.assertTrue(all(m["B"][7:]))                      # cuando A ya no tiene datos (ts 1000+), B es la unica y entra

    def test_volumen_invalido_cuenta_cero(self):
        datos = {"A": serie_vol([float("nan")] * 6), "B": serie_vol([1] * 6)}
        m = uh.membresia(datos, n=1, ventana=2)
        self.assertTrue(m["B"][5])
        self.assertFalse(m["A"][5])

    def test_n_mayor_que_el_numero_de_monedas_incluye_a_todas(self):
        datos = {"A": serie_vol([1] * 6), "B": serie_vol([2] * 6)}
        m = uh.membresia(datos, n=10, ventana=2)
        self.assertTrue(m["A"][5] and m["B"][5])


class SimuladorConMembresia(unittest.TestCase):
    def test_no_abre_compras_fuera_del_top_pero_si_puede_vender(self):
        c = [100.0] * 12
        senales = {1: "b", 5: "s", 7: "b"}
        permitido = lambda i: i < 6                           # fuera del universo a partir de la vela 6
        r, ops, _, _ = ej.simular(c, c, 1, 12, 1.0, lambda c_, i, s: senales.get(i), permitido=permitido)
        self.assertEqual(ops, 2)                              # compra (i=1->2), vende (5->6); la compra de i=7 se ignora

    def test_si_esta_en_cartera_cuando_sale_del_top_puede_vender(self):
        c = [100.0] * 12
        senales = {1: "b", 8: "s"}
        permitido = lambda i: i < 4
        r, ops, _, _ = ej.simular(c, c, 1, 12, 1.0, lambda c_, i, s: senales.get(i), permitido=permitido)
        self.assertEqual(ops, 2)


if __name__ == "__main__":
    unittest.main()
