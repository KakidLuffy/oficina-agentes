import csv
import unittest
from tests.base import an, BaseDatos


class VariasHoras(BaseDatos):
    """Simula horas consecutivas con velas sinteticas (como las ejecuciones horarias reales) y comprueba la contabilidad."""

    def test_contabilidad_coherente_y_ejecucion_posterior_a_la_decision(self):
        v, vol, orden, fuente, _ = an._descargar(220)
        n0 = 150
        est = an.estado_nuevo({p: x[:n0] for p, x in v.items()}, v[an.BTC][n0 - 1].ts + 3600)
        for k in range(n0, 219):
            corte = {p: x[:k + 1] for p, x in v.items()}
            ahora, precios = an.paso(est, corte, vol, orden, corte[an.BTC][-1].ts + 900)
            an.guardar(est, ahora, precios, fuente, len(orden), len(corte))
        with open(an.OPERACIONES, newline="") as f:
            ops = list(csv.DictReader(f))
        self.assertGreater(len(ops), 50)
        for o in ops:
            self.assertGreater(o["decision_utc"], o["vela_inicio_utc"]) if o["motivo"] != "apagado por riesgo" else None
        for a in est["agentes"]:
            self.assertGreaterEqual(a["efectivo"], -1e-9)
            flujo = sum((-float(o["importe_eur"]) if o["tipo"] == "COMPRA" else float(o["importe_eur"]))
                        for o in ops if o["agente"] == a["nombre"])
            self.assertAlmostEqual(a["efectivo"], an.START + flujo, delta=0.05 * max(1, a["operaciones"]))
            self.assertLessEqual(len(a["posiciones"]), an.MAX_POS)

    def test_repetir_la_misma_ejecucion_no_duplica_operaciones(self):
        v, vol, orden, fuente, _ = an._descargar(220)
        n0 = 150
        est = an.estado_nuevo({p: x[:n0] for p, x in v.items()}, v[an.BTC][n0 - 1].ts + 3600)
        corte = {p: x[:200] for p, x in v.items()}
        ts = corte[an.BTC][-1].ts + 900
        ahora, precios = an.paso(est, corte, vol, orden, ts)
        an.guardar(est, ahora, precios, fuente, len(orden), len(corte))
        n1 = len(open(an.OPERACIONES).read().splitlines())
        ahora, precios = an.paso(est, corte, vol, orden, ts)
        an.guardar(est, ahora, precios, fuente, len(orden), len(corte))
        self.assertEqual(len(open(an.OPERACIONES).read().splitlines()), n1)


if __name__ == "__main__":
    unittest.main()
