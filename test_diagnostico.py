"""Pruebas del diagnóstico de la señal (CRITERIOS.md §8). Sin internet:  python -m unittest test_diagnostico"""
import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

import diagnostico as d

T0 = 1_800_000_000 // 3600 * 3600
H = 3600


def fecha(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="minutes")


def carpeta(ops, serie, horas=200, capital=10.0, posiciones=None, efectivo=10.0, cesta=9.0):
    """Prepara una carpeta de datos con un agente de señales y otro de rebalanceo."""
    dir_ = tempfile.mkdtemp()
    est = {"capital_inicial": capital, "fee": 0.004, "slip": 0.0005, "inicio": fecha(T0),
           "precios": {"XBTEUR": serie[T0 + (horas - 1) * H], "ETHEUR": 1000.0},
           "agentes": [{"nombre": "Prueba", "efectivo": efectivo, "posiciones": posiciones or {}},
                       {"nombre": d.REBALANCEO, "efectivo": 10.0, "posiciones": {}}]}
    with open(os.path.join(dir_, "estado.json"), "w") as f:
        json.dump(est, f)
    with open(os.path.join(dir_, "operaciones.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"])
        for t, tipo, q in ops:
            w.writerow([fecha(t), "Prueba", "XBTEUR", tipo, serie[t], q, "", 0.0])
    with open(os.path.join(dir_, "historial_v2.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fecha_utc", "precio_eur", "Prueba", "Comprar y mantener", "Comprar y mantener (cesta)"])
        w.writerow([fecha(T0 + horas * H), 1, 10, 9.0, cesta])
    return dir_


def descargar_de(series):
    return lambda par: series.get(par, {T0 + i * H: 1000.0 for i in range(200)})


class TestDiagnostico(unittest.TestCase):
    def test_coste_igual_que_la_simulacion(self):
        # agentes_nube.operar: compra importe*(1-fee)/(p0*(1+slip)) unidades; vende unidades*p1*(1-slip)*(1-fee)
        q, p0, p1, fee, slip = 5.0, 100.0, 110.0, 0.004, 0.0005
        unidades = q * (1 - fee) / (p0 * (1 + slip))
        cobrado = unidades * p1 * (1 - slip) * (1 - fee)
        self.assertAlmostEqual(d.resultado_viaje(q, p0, p1, fee, slip), cobrado - q, places=12)

    def test_empareja_compras_y_ventas_y_deja_abiertas(self):
        ops = [{"agente": "A", "moneda": "X", "tipo": "COMPRA", "fecha_utc": fecha(T0), "importe_eur": "5"},
               {"agente": "B", "moneda": "X", "tipo": "COMPRA", "fecha_utc": fecha(T0), "importe_eur": "5"},
               {"agente": "A", "moneda": "X", "tipo": "VENTA", "fecha_utc": fecha(T0 + 3 * H), "importe_eur": "5.1"},
               {"agente": "A", "moneda": "Y", "tipo": "COMPRA", "fecha_utc": fecha(T0 + 4 * H), "importe_eur": "2"}]
        v = d.ida_vuelta(ops, "A")
        self.assertEqual(len(v), 2)
        self.assertEqual((v[0]["entrada"], v[0]["salida"], v[0]["importe"]), (T0, T0 + 3 * H, 5.0))
        self.assertIsNone(v[1]["salida"])

    def test_exposicion(self):
        viajes = [{"entrada": T0, "salida": T0 + 50 * H, "importe": 5.0}]
        self.assertAlmostEqual(d.exposicion(viajes, T0, T0 + 100 * H, 10.0), 0.25)
        abierta = [{"entrada": T0 + 50 * H, "salida": None, "importe": 10.0}]
        self.assertAlmostEqual(d.exposicion(abierta, T0, T0 + 100 * H, 10.0), 0.5)

    def test_efectos_suman_la_diferencia_con_el_mercado(self):
        serie = {T0 + i * H: 100.0 for i in range(200)}
        dir_ = carpeta([(T0 + 10 * H, "COMPRA", 5.0), (T0 + 60 * H, "VENTA", 5.0)], serie, efectivo=9.7, cesta=8.5)
        r = d.diagnosticar(dir_, descargar=descargar_de({"XBTEUR": serie}), ahora=T0 + 200 * H, n=50)
        f = r["agentes"][0]
        self.assertEqual([a["nombre"] for a in r["agentes"]], ["Prueba"])   # el Rebalanceo queda fuera (§8.1)
        self.assertAlmostEqual(f["efecto_fuera"] + f["efecto_senal"], f["resultado"] - r["mercado_cesta"], places=3)
        self.assertGreater(f["efecto_fuera"], 0)          # mercado cayendo + poco tiempo invertido

    def test_entrar_en_el_suelo_supera_al_azar_y_en_el_techo_no(self):
        # baja 100 h y luego sube 100 h
        serie = {T0 + i * H: 100.0 - i * 0.3 if i < 100 else 70.0 + (i - 100) * 0.3 for i in range(200)}
        bien = carpeta([(T0 + 100 * H, "COMPRA", 5.0), (T0 + 190 * H, "VENTA", 5.0)], serie)
        mal = carpeta([(T0 + 5 * H, "COMPRA", 5.0), (T0 + 95 * H, "VENTA", 5.0)], serie)
        kw = dict(ahora=T0 + 200 * H, n=500)
        pb = d.diagnosticar(bien, descargar=descargar_de({"XBTEUR": serie}), **kw)["agentes"][0]["azar"]["percentil"]
        pm = d.diagnosticar(mal, descargar=descargar_de({"XBTEUR": serie}), **kw)["agentes"][0]["azar"]["percentil"]
        self.assertGreater(pb, 0.9)
        self.assertLess(pm, 0.1)

    def test_precio_plano_da_el_50(self):
        serie = {T0 + i * H: 100.0 for i in range(200)}
        dir_ = carpeta([(T0 + 10 * H, "COMPRA", 5.0), (T0 + 20 * H, "VENTA", 5.0)], serie)
        az = d.diagnosticar(dir_, descargar=descargar_de({"XBTEUR": serie}), ahora=T0 + 200 * H, n=100)["agentes"][0]["azar"]
        self.assertAlmostEqual(az["percentil"], 0.5)

    def test_reproducible_y_guarda_precios_sin_red(self):
        serie = {T0 + i * H: 100.0 + (i % 7) for i in range(200)}
        ops = [(T0 + 10 * H, "COMPRA", 5.0), (T0 + 30 * H, "VENTA", 5.0), (T0 + 150 * H, "COMPRA", 5.0)]
        dir_ = carpeta(ops, serie)
        a = d.diagnosticar(dir_, descargar=descargar_de({"XBTEUR": serie}), ahora=T0 + 200 * H, n=200)
        b = d.diagnosticar(dir_, descargar=None, ahora=T0 + 200 * H, n=200)      # sin red: usa precios_1h.json
        self.assertEqual(a["agentes"][0]["azar"], b["agentes"][0]["azar"])
        self.assertEqual(a["agentes"][0]["azar"]["operaciones_usadas"], 2)       # la abierta cuenta hasta ahora
        self.assertTrue(os.path.exists(os.path.join(dir_, "diagnostico.md")))

    def test_fallo_de_kraken_no_rompe(self):
        serie = {T0 + i * H: 100.0 for i in range(200)}
        dir_ = carpeta([(T0 + 10 * H, "COMPRA", 5.0)], serie)

        def roto(par):
            raise OSError("sin red")
        r = d.diagnosticar(dir_, descargar=roto, ahora=T0 + 200 * H, n=10)
        self.assertTrue(r["fallos_precios"])
        self.assertEqual(r["agentes"][0]["azar"]["sin_precio"], 1)

    def test_parte_del_director_resume_el_diagnostico(self):
        import director
        diag = {"n_azar": 2000, "agentes": [
            {"nombre": "A", "operaciones": 4, "efecto_senal": -0.4, "azar": {"percentil": 0.67}},
            {"nombre": "B", "operaciones": 6, "efecto_senal": 0.2, "azar": {"percentil": 0.3}},
            {"nombre": "C", "operaciones": 0, "efecto_senal": 0.0}]}
        l = director.lineas_diagnostico(diag)
        self.assertIn("positivo en 1 de 2", l[0])
        self.assertIn("1 de 2 lo hacen mejor que la mitad", l[1])
        viejo = {"generado": "2020-01-01T00:00:00Z"}
        self.assertIsNone(director.diagnostico_fresco(viejo, director.ahora()))


if __name__ == "__main__":
    unittest.main()
