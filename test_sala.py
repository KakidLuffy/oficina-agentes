"""Pruebas de la Sala abierta (CRITERIOS.md, sección 7). Sin internet: python -m unittest test_sala"""
import csv
import os
import tempfile
import unittest

import laboratorio as lab
import sala_abierta as s


class TestSala(unittest.TestCase):
    def preparar(self, n=420, corte=250):
        self.dir = tempfile.mkdtemp()
        self.ops = os.path.join(self.dir, "operaciones.csv")
        fin = 1_800_000_000 // s.VELA * s.VELA
        velas = {sym: s.velas_demo(n, k, fin) for k, (sym, _) in enumerate(s.PARES)}
        ahora = fin + 60
        inicio = {sym: v[:corte] for sym, v in velas.items()}
        estado = s.estado_nuevo(inicio, inicio["BTC"][-1][0] + s.VELA + 60)
        return estado, velas, ahora

    def leer_ops(self):
        if not os.path.exists(self.ops):
            return []
        with open(self.ops, newline="") as f:
            return list(csv.DictReader(f))

    def test_dos_agentes_y_reglas_del_laboratorio(self):
        self.assertEqual(len(s.AGENTES), 2)                       # CRITERIOS 7: como mucho 2 agentes en la sala
        self.assertEqual([n for n, _ in s.AGENTES], ["Sala: Cruce 10/80 + filtro", "Sala: Ruptura 40/20 + filtro"])
        self.assertEqual(s.PARES, lab.PARES)

    def test_opera_varias_monedas_sin_pasar_limites(self):
        estado, velas, ahora = self.preparar()
        s.paso(estado, velas, ahora, self.ops)
        ops = self.leer_ops()
        self.assertTrue(ops, "con 170 velas nuevas deberia haber operaciones")
        self.assertGreater(len({o["moneda"] for o in ops if o["tipo"] == "COMPRA"}), 2)   # no solo BTC y ETH
        for a in estado["agentes"]:
            self.assertLessEqual(len(a["posiciones"]), s.MAX_POS)
            self.assertGreaterEqual(a["efectivo"], -1e-9)
        for o in ops:
            if o["tipo"] == "COMPRA":
                self.assertLessEqual(float(o["importe_eur"]), s.COMPRA + 1e-9)

    def test_cada_compra_responde_a_la_senal_del_laboratorio(self):
        estado, velas, ahora = self.preparar()
        s.paso(estado, velas, ahora, self.ops)
        fn = dict(s.AGENTES)
        for o in self.leer_ops():
            if o["motivo"] not in ("señal compradora", "señal vendedora"):
                continue
            cer = [(t, c) for t, c in velas[o["moneda"]] if t + s.VELA <= ahora]
            serie = lab.Serie([c for _, c in cer], [t for t, _ in cer])
            cierre_ts = int(__import__("datetime").datetime.fromisoformat(o["fecha_utc"]).timestamp())
            i = [t for t, _ in cer].index(cierre_ts - s.VELA)
            esperado = "b" if o["tipo"] == "COMPRA" else "s"
            self.assertEqual(fn[o["agente"]](serie, i, 1.0), esperado)

    def test_no_repite_velas_ya_procesadas(self):
        estado, velas, ahora = self.preparar()
        s.paso(estado, velas, ahora, self.ops)
        n = len(self.leer_ops())
        s.paso(estado, velas, ahora + 60, self.ops)
        self.assertEqual(len(self.leer_ops()), n)

    def test_costes_mas_altos_fuera_de_btc_y_eth(self):
        self.assertEqual(s.slip("BTC"), 0.0005)
        self.assertEqual(s.slip("ETH"), 0.0005)
        self.assertEqual(s.slip("DOGE"), 0.003)

    def test_apagado_por_riesgo(self):
        estado, velas, ahora = self.preparar()
        a = estado["agentes"][0]
        a["efectivo"], a["posiciones"] = 4.0, {"BTC": 0.0}
        s.paso(estado, velas, ahora, self.ops)
        self.assertTrue(a["apagado"])

    def test_guardar_y_referencia(self):
        estado, velas, ahora = self.preparar()
        s.paso(estado, velas, ahora, self.ops)
        s.guardar(estado, self.dir)
        with open(os.path.join(self.dir, "resumen.md")) as f:
            txt = f.read()
        self.assertIn("Mantener a partes iguales", txt)
        self.assertIn("90 días", txt)
        self.assertAlmostEqual(sum(u * p for u, p in zip(estado["referencia"].values(),
                                                         [velas[k][249][1] for k in estado["referencia"]])),
                               s.START * (1 - s.FEE) / 1.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
