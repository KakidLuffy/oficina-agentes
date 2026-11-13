"""Pruebas de la Sala abierta (CRITERIOS.md, secciones 7 y 7.1). Sin internet: python -m unittest test_sala"""
import csv
import json
import os
import tempfile
import unittest
from datetime import datetime

import laboratorio as lab
import sala_abierta as s


class TestSala(unittest.TestCase):
    def preparar(self, n=420, corte=250):
        self.dir = tempfile.mkdtemp()
        self.ops = os.path.join(self.dir, "operaciones.csv")
        fin = 1_800_000_000 // s.VELA * s.VELA
        nombres = [s.BTC, "ETHEUR"] + [f"DEMO{k}EUR" for k in range(2, 20)]
        self.vol = {p: (500_000 if k % 3 else 20_000) for k, p in enumerate(nombres)}
        velas = {p: s.velas_demo(n, k, fin) for k, p in enumerate(nombres)}
        inicio = {p: v[:corte] for p, v in velas.items()}
        estado = s.estado_nuevo(inicio, self.vol, inicio[s.BTC][-1][0] + s.VELA + 60)
        return estado, velas, nombres, fin + 60

    def leer_ops(self):
        if not os.path.exists(self.ops):
            return []
        with open(self.ops, newline="") as f:
            return list(csv.DictReader(f))

    def test_dos_agentes_con_reglas_del_laboratorio(self):
        self.assertEqual([n for n, _ in s.AGENTES], ["Sala: Cruce 10/80 + filtro", "Sala: Ruptura 40/20 + filtro"])
        self.assertEqual(s.VELA, 4 * 3600)                       # CRITERIOS 7.1

    def test_compra_monedas_de_toda_la_lista(self):
        estado, velas, orden, ahora = self.preparar()
        s.paso(estado, velas, self.vol, orden, ahora, self.ops)
        compradas = {o["moneda"] for o in self.leer_ops() if o["tipo"] == "COMPRA"}
        self.assertGreater(len(compradas - {s.BTC, "ETHEUR"}), 2)   # no solo BTC y ETH
        for a in estado["agentes"]:
            self.assertLessEqual(len(a["posiciones"]), s.MAX_POS)
            self.assertGreaterEqual(a["efectivo"], -1e-9)

    def test_cada_operacion_responde_a_la_senal_del_laboratorio(self):
        estado, velas, orden, ahora = self.preparar()
        s.paso(estado, velas, self.vol, orden, ahora, self.ops)
        fn = dict(s.AGENTES)
        revisadas = 0
        for o in self.leer_ops():
            if o["motivo"] not in ("señal compradora", "señal vendedora"):
                continue
            cer = [(t, c) for t, c in velas[o["moneda"]] if t + s.VELA <= ahora]
            serie = lab.Serie([c for _, c in cer], [t for t, _ in cer])
            i = [t for t, _ in cer].index(int(datetime.fromisoformat(o["fecha_utc"]).timestamp()) - s.VELA)
            self.assertEqual(fn[o["agente"]](serie, i, 1.0), "b" if o["tipo"] == "COMPRA" else "s")
            revisadas += 1
        self.assertGreater(revisadas, 0)

    def test_deslizamiento_segun_volumen_como_la_oficina(self):
        self.assertEqual(s.slip(s.BTC, {}), 0.0005)
        self.assertEqual(s.slip("DEMO2EUR", {"DEMO2EUR": 500_000}), 0.0005)
        self.assertEqual(s.slip("DEMO3EUR", {"DEMO3EUR": 20_000}), 0.003)

    def test_no_repite_velas(self):
        estado, velas, orden, ahora = self.preparar()
        s.paso(estado, velas, self.vol, orden, ahora, self.ops)
        n = len(self.leer_ops())
        s.paso(estado, velas, self.vol, orden, ahora + 60, self.ops)
        self.assertEqual(len(self.leer_ops()), n)

    def test_moneda_nueva_en_la_lista_solo_cuenta_desde_ahora(self):
        estado, velas, orden, ahora = self.preparar()
        velas["NUEVAEUR"] = s.velas_demo(420, 30, ahora - 60)
        s.paso(estado, velas, self.vol, orden + ["NUEVAEUR"], ahora, self.ops)
        self.assertNotIn("NUEVAEUR", {o["moneda"] for o in self.leer_ops()})
        self.assertIn("NUEVAEUR", estado["ultima_vela"])

    def test_apagado_por_riesgo(self):
        estado, velas, orden, ahora = self.preparar()
        a = estado["agentes"][0]
        a["efectivo"] = 4.0
        s.paso(estado, velas, self.vol, orden, ahora, self.ops)
        self.assertTrue(a["apagado"])

    def test_formato_que_entiende_el_panel(self):
        estado, velas, orden, ahora = self.preparar()
        s.paso(estado, velas, self.vol, orden, ahora, self.ops)
        s.guardar(estado, self.dir)
        with open(os.path.join(self.dir, "estado.json")) as fh:
            e = json.load(fh)
        for k in ("capital_inicial", "fee", "slip", "precios", "precio_inicio", "inicio", "agentes"):
            self.assertIn(k, e)
        self.assertIn(s.BTC, e["precios"])
        for a in e["agentes"]:
            for k in ("nombre", "operaciones", "posiciones", "apagado", "inicio", "precio_inicio"):
                self.assertIn(k, a)
        with open(os.path.join(self.dir, "historial_v2.csv")) as fh:
            cab = fh.readline().strip().split(",")
        self.assertEqual(cab[:2], ["fecha_utc", "precio_eur"])
        self.assertIn("Comprar y mantener", cab)
        self.assertIn("Comprar y mantener (cesta)", cab)
        with open(os.path.join(self.dir, "operaciones.csv")) as fh:
            self.assertEqual(fh.readline().strip().split(","), s.CAB_OPS)

    def test_cesta_de_referencia_vale_el_capital_al_empezar(self):
        estado, velas, orden, ahora = self.preparar()
        self.assertAlmostEqual(s.valor_cesta(estado, estado["precios"]), s.START, delta=0.1)


if __name__ == "__main__":
    unittest.main()
