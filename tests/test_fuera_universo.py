import unittest
from tests.base import an, BaseDatos, velas, T0
import velas as vl_


def asset_pairs(n):
    return {f"C{k}EUR": {"altname": f"C{k}EUR", "quote": "ZEUR", "status": "online", "ordermin": "0.001", "costmin": "0.5",
                         "lot_decimals": 8, "pair_decimals": 4} for k in range(n)}


class Universo(BaseDatos):
    def setUp(self):
        super().setUp()
        self.orig = (an.kraken, an.time.sleep)
        self.addCleanup(self._rest)
        an.time.sleep = lambda s: None

    def _rest(self):
        an.kraken, an.time.sleep = self.orig

    def falso_kraken(self, n=30):
        def f(url):
            if "AssetPairs" in url:
                return asset_pairs(n)
            return {f"C{k}EUR": {"v": ["0", str(1000 - k)], "c": ["1.0"]} for k in range(n)}     # C0 el de mas volumen
        an.kraken = f

    def test_universo_normal_son_las_top_n(self):
        self.falso_kraken()
        uni = [p for p, _ in an.universo_kraken()]
        self.assertEqual(len([p for p in uni if p != an.BTC]), an.TOP_MONEDAS)
        self.assertNotIn("C25EUR", uni)

    def test_una_moneda_en_cartera_se_sigue_vigilando_aunque_salga_del_ranking(self):
        self.falso_kraken()
        uni = dict(an.universo_kraken(extra={"C25EUR"}))
        self.assertIn("C25EUR", uni)
        self.assertGreater(uni["C25EUR"], 0)                    # con su volumen real, no 0

    def test_extra_inexistente_se_ignora_sin_romper(self):
        self.falso_kraken()
        uni = dict(an.universo_kraken(extra={"NOEXISTEEUR"}))
        self.assertIn("NOEXISTEEUR", uni)                        # se intenta descargar; si falla se tratara como sin cotizacion

    def test_pares_en_cartera(self):
        est = an.estado_nuevo({an.BTC: velas([100.0] * 40)}, T0 + 3600 * 40)
        est["agentes"][0]["posiciones"] = {"AEUR": 1.0}
        est["agentes"][1]["pendientes"] = [{"par": "BEUR", "tipo": "VENTA", "motivo": "", "vela_ts": T0}]
        self.assertEqual(an.pares_en_cartera(est), {"AEUR", "BEUR"})


class SinCotizacion(BaseDatos):
    def estado(self):
        v = {an.BTC: velas([100.0] * 50), "OUTEUR": velas([10.0] * 50)}
        est = an.estado_nuevo(v, T0 + 3600 * 50)
        a = est["agentes"][0]
        a["efectivo"], a["posiciones"], a["entradas"] = 8.0, {"OUTEUR": 0.2}, {"OUTEUR": 10.0}
        est["precios"]["OUTEUR"] = 14.0                        # ultimo precio conocido: sube un 40 %
        return est, a

    def test_posicion_sin_datos_no_se_cierra_ni_se_inventa_ganancia(self):
        est, a = self.estado()
        v = {an.BTC: velas([100.0] * 52)}                      # llegan velas nuevas de BTC; de OUTEUR ninguna
        ahora, precios = an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 52)
        self.assertIn("OUTEUR", a["posiciones"])                # no se ha cerrado nada
        self.assertEqual(a["operaciones"], 0)
        self.assertIn("OUTEUR", a["sin_cotizacion"])
        # valoracion conservadora: nunca por encima del precio de entrada mientras no hay cotizacion
        self.assertAlmostEqual(an.equity(a, precios), 8.0 + 0.2 * 10.0)

    def test_valor_conservador_si_ni_siquiera_hay_ultimo_precio(self):
        est, a = self.estado()
        est["precios"].pop("OUTEUR")
        self.assertAlmostEqual(an.equity(a, est["precios"]), 8.0 + 0.2 * 10.0)       # a coste, no a cero

    def test_si_vuelve_la_cotizacion_se_quita_la_marca_y_se_valora_a_mercado(self):
        est, a = self.estado()
        v = {an.BTC: velas([100.0] * 52)}
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 52)
        self.assertIn("OUTEUR", a["sin_cotizacion"])
        v = {an.BTC: velas([100.0] * 54), "OUTEUR": velas([13.0] * 54)}
        ahora, precios = an.paso(est, v, {an.BTC: 1e6, "OUTEUR": 1e6}, [an.BTC, "OUTEUR"], T0 + 3600 * 54)
        self.assertNotIn("OUTEUR", a.get("sin_cotizacion", {}))
        self.assertAlmostEqual(an.equity(a, precios), 8.0 + 0.2 * 13.0)

    def test_se_registra_incidencia_de_alerta(self):
        est, a = self.estado()
        an.paso(est, {an.BTC: velas([100.0] * 52)}, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 52)
        self.assertTrue(any(p == "OUTEUR" and i["tipo"] == "sin_cotizacion" for p, i in an.INCIDENCIAS))

    def test_orden_pendiente_de_una_moneda_sin_velas_caduca(self):
        est, a = self.estado()
        a["pendientes"] = [{"par": "OUTEUR", "tipo": "VENTA", "motivo": "x", "vela_ts": T0 + 3600 * 40}]
        an.paso(est, {an.BTC: velas([100.0] * 52)}, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 52)
        self.assertEqual(a["pendientes"], [])
        self.assertTrue(any("caducada" in r[5] for r in an.RECHAZOS))


if __name__ == "__main__":
    unittest.main()
