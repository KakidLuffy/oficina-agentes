import csv
import json
import os
import unittest
import velas as vl_
from tests.base import an, BaseDatos, velas, T0


FECHA = "2026-10-20T10:00+00:00"


def filas_ops():
    """Operaciones ya guardadas en disco + las pendientes de esta ejecucion."""
    with open(an.OPERACIONES, newline="") as f:
        return list(csv.DictReader(f)) + [dict(zip(an.CAB_OPERACIONES, map(str, r))) for r in an.COLA_OPS]


class Operar(BaseDatos):
    def test_ida_y_vuelta_cuesta_comisiones_y_nunca_crea_dinero(self):
        a = self.agente()
        an.operar(a, "COMPRA", an.BTC, 100.0, FECHA, {an.BTC: 1e6})
        self.assertAlmostEqual(a["efectivo"], an.START - an.SLOT)
        an.operar(a, "VENTA", an.BTC, 100.0, FECHA, {an.BTC: 1e6})
        self.assertEqual(a["posiciones"], {})
        self.assertLess(a["efectivo"], an.START)           # pierde comision y deslizamiento
        perdido = an.START - a["efectivo"]
        esperado = an.SLOT * (1 - (1 - an.FEE) ** 2 * (1 - an.SLIP) / (1 + an.SLIP))
        self.assertAlmostEqual(perdido, esperado, places=9)

    def test_coste_registrado_coincide_con_lo_perdido(self):
        a = self.agente()
        an.operar(a, "COMPRA", an.BTC, 50.0, FECHA, {an.BTC: 1e6})
        an.operar(a, "VENTA", an.BTC, 50.0, FECHA, {an.BTC: 1e6})
        total = sum(float(r["coste_eur"]) for r in filas_ops())
        self.assertAlmostEqual(total, an.START - a["efectivo"], places=3)

    def test_poco_volumen_desliza_mas(self):
        self.assertEqual(an.deslizamiento("XEUR", {"XEUR": 10}), an.SLIP_POCO_VOLUMEN)
        self.assertEqual(an.deslizamiento("XEUR", {"XEUR": 1e6}), an.SLIP)
        self.assertEqual(an.deslizamiento(an.BTC, {}), an.SLIP)
        self.assertEqual(an.deslizamiento("XEUR", {}), an.SLIP_POCO_VOLUMEN)

    def test_compra_no_supera_efectivo(self):
        a = self.agente()
        a["efectivo"] = 0.5
        an.operar(a, "COMPRA", an.BTC, 100.0, FECHA, {an.BTC: 1e6})
        self.assertGreaterEqual(a["efectivo"], 0)

    def test_equity(self):
        a = self.agente()
        a["efectivo"], a["posiciones"] = 3.0, {"AEUR": 2.0}
        self.assertEqual(an.equity(a, {"AEUR": 4.0}), 11.0)
        self.assertEqual(an.equity(a, {}), 3.0)   # sin precio: valora a 0 (se corrige en CRYPTO-001)


class Apagado(BaseDatos):
    def test_apaga_y_vende_por_debajo_del_stop(self):
        a = self.agente()
        a["efectivo"], a["posiciones"] = 0.0, {an.BTC: 0.1}
        an.apagar_si_toca(a, {an.BTC: 10.0}, FECHA, {an.BTC: 1e6})   # equity 1 < 7
        self.assertTrue(a["apagado"])
        self.assertEqual(a["posiciones"], {})

    def test_no_apaga_si_esta_por_encima(self):
        a = self.agente()
        an.apagar_si_toca(a, {an.BTC: 10.0}, FECHA, {})
        self.assertFalse(a["apagado"])


class Paso(BaseDatos):
    def estado(self, v):
        return an.estado_nuevo(v, T0 + 3600 * 40)

    def test_no_actua_sobre_vela_abierta(self):
        precios = [100.0] * 40
        v = {an.BTC: velas(precios)}
        est = self.estado(v)
        # aparece una vela nueva pero aun no ha cerrado (ahora_ts dentro de ella)
        v[an.BTC].append(vl_.Vela(T0 + 3600 * 40, 500.0, 500.0, 500.0, 500.0, 1.0))
        ahora_ts = T0 + 3600 * 40 + 100
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], ahora_ts)
        self.assertEqual(est["ultima_vela"], T0 + 3600 * 39)
        self.assertEqual(sum(a["operaciones"] for a in est["agentes"]), 0)

    def test_procesa_velas_pendientes_en_orden(self):
        precios = [100.0] * 40
        v = {an.BTC: velas(precios)}
        est = self.estado(v)
        for k in range(40, 45):
            v[an.BTC].append(vl_.Vela(T0 + 3600 * k, 100.0, 100.0, 100.0, 100.0, 1.0))
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 45)
        self.assertEqual(est["ultima_vela"], T0 + 3600 * 44)

    def test_idempotente_si_no_hay_velas_nuevas(self):
        v = {an.BTC: velas([100.0] * 40)}
        est = self.estado(v)
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 40)
        antes = json.dumps(est, sort_keys=True)
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 40)
        self.assertEqual(antes, json.dumps(est, sort_keys=True))

    def test_momentum_compra_tras_subida_y_registra_operacion(self):
        precios = [100.0] * 39 + [103.0]
        v = {an.BTC: velas(precios)}
        est = an.estado_nuevo({an.BTC: v[an.BTC][:39]}, T0 + 3600 * 39)
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 40)
        por = {a["nombre"]: a for a in est["agentes"]}
        self.assertIn(an.BTC, por["Momentum"]["posiciones"])
        self.assertTrue(any(r["agente"] == "Momentum" and r["tipo"] == "COMPRA" for r in filas_ops()))

    def test_stop_de_perdida_en_agente_rapido(self):
        a = next(x for x in [an.agente_nuevo("Momentum rapido", 100.0)])
        est = {"ultima_vela": T0, "precios": {}, "agentes": [a]}
        a["posiciones"], a["entradas"], a["efectivo"] = {an.BTC: 0.02}, {an.BTC: 100.0}, 8.0
        v = {an.BTC: velas([100.0] * 10 + [98.0])}      # -2 % desde la entrada
        est["ultima_vela"] = v[an.BTC][9][0]
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 11)
        self.assertEqual(a["posiciones"], {})
        self.assertTrue(any("stop de perdida" in r["motivo"] for r in filas_ops()))

    def test_limite_de_posiciones(self):
        a = self.agente("Momentum")
        for i in range(an.MAX_POS):
            a["posiciones"][f"M{i}EUR"] = 1.0
        self.assertEqual(len(a["posiciones"]), an.MAX_POS)


class Persistencia(BaseDatos):
    def test_archivar_mueve_solo_archivos_de_la_simulacion(self):
        for r in (an.ESTADO, an.HISTORIAL, an.RESUMEN, an.GRAFICO):
            open(r, "w").write("x")
        otro = os.path.join(an.DATOS, "laboratorio.json")
        open(otro, "w").write("{}")
        an.archivar("prueba")
        self.assertTrue(os.path.exists(otro))
        self.assertFalse(os.path.exists(an.ESTADO))
        carpetas = [d for d in os.listdir(an.DATOS) if d.startswith("archivo_prueba")]
        self.assertEqual(len(carpetas), 1)
        self.assertTrue(os.path.exists(os.path.join(an.DATOS, carpetas[0], "estado.json")))
        self.assertTrue(os.path.exists(os.path.join(an.DATOS, carpetas[0], "MANIFIESTO.json")))

    def test_ajustar_historial_rellena_columnas_nuevas(self):
        with open(an.HISTORIAL, "w", newline="") as f:
            f.write("fecha_utc,precio_eur,A\n2026-01-01,100,9.5\n")
        import io
        txt = an.historial_con_fila(["fecha_utc", "precio_eur", "A", "B"], ["2026-01-02", "101", "9.6", "10"])
        filas = list(csv.reader(io.StringIO(txt, newline="")))
        self.assertEqual(filas[1], ["2026-01-01", "100", "9.5", str(an.START)])
        self.assertEqual(filas[2], ["2026-01-02", "101", "9.6", "10"])

    def test_migrar_estado_antiguo_y_agentes_nuevos(self):
        v = {an.BTC: velas([100.0] * 40)}
        est = an.estado_nuevo(v, T0 + 3600 * 40)
        est["agentes"] = est["agentes"][:2]
        est["agentes"][0]["btc"] = 0.5
        del est["agentes"][0]["posiciones"]
        an.migrar(est, v)
        self.assertEqual(est["agentes"][0]["posiciones"], {an.BTC: 0.5})
        self.assertEqual(len(est["agentes"]), len(an.AGENTES))

    def test_parametros_estado_antiguo(self):
        v = {an.BTC: velas([100.0] * 40)}
        est = an.estado_nuevo(v, T0 + 3600 * 40)
        del est["slip"]
        est["agentes"][0]["operaciones"] = 3
        an.parametros(est)
        self.assertEqual((est["fee"], est["slip"]), (0.0025, 0.0))

    def test_ciclo_completo_en_demo(self):
        v, vol, orden, fuente, ts = an.obtener_datos(150)
        est = an.estado_nuevo({p: x[:100] for p, x in v.items()}, v[an.BTC][99].ts + 3600)
        ahora, precios = an.paso(est, v, vol, orden, ts)
        an.guardar(est, ahora, precios, fuente, len(orden), len(v))
        for r in (an.ESTADO, an.HISTORIAL, an.OPERACIONES, an.RESUMEN):
            self.assertTrue(os.path.exists(r), r)
        json.load(open(an.ESTADO, encoding="utf-8"))
        for a in est["agentes"]:
            self.assertGreaterEqual(a["efectivo"], -1e-9)


class MarcasTemporales(BaseDatos):
    def test_operacion_normal_lleva_vela_y_decision(self):
        a = self.agente()
        an.operar(a, "COMPRA", an.BTC, 100.0, "2026-10-20T10:00+00:00", {an.BTC: 1e6})
        fila = dict(zip(an.CAB_OPERACIONES, an.COLA_OPS[-1]))
        self.assertEqual(fila["vela_inicio_utc"], "2026-10-20T10:00+00:00")
        self.assertEqual(fila["decision_utc"], "2026-10-20T11:00+00:00")     # la vela cierra una hora despues
        self.assertEqual(fila["fecha_utc"], fila["vela_inicio_utc"])          # compatibilidad

    def test_apagado_por_riesgo_usa_la_hora_real_de_ejecucion(self):
        a = self.agente()
        a["efectivo"], a["posiciones"] = 0.0, {an.BTC: 0.1}
        an.apagar_si_toca(a, {an.BTC: 10.0}, "2026-10-20T10:07:33+00:00", {an.BTC: 1e6}, {an.BTC: "2026-10-20T10:00+00:00"})
        fila = dict(zip(an.CAB_OPERACIONES, an.COLA_OPS[-1]))
        self.assertEqual(fila["vela_inicio_utc"], "2026-10-20T10:00+00:00")
        self.assertEqual(fila["decision_utc"], "2026-10-20T10:07:33+00:00")

    def test_migracion_de_operaciones_antiguas_solo_deriva_lo_cierto(self):
        os.remove(an.OPERACIONES)
        viejo = (",".join(an.CAB_OPERACIONES_V1) + "\n"
                 "2026-10-20T10:00+00:00,A,BTCEUR,COMPRA,1,2,senal compradora,0.01\n"
                 "2026-10-20T10:07:33+00:00,A,BTCEUR,VENTA,1,2,apagado por riesgo,0.01\n")
        open(an.OPERACIONES, "w", newline="").write(viejo)
        an.asegurar_operaciones()
        with open(an.OPERACIONES, newline="") as f:
            filas = list(csv.DictReader(f))
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0]["vela_inicio_utc"], "2026-10-20T10:00+00:00")
        self.assertEqual(filas[0]["decision_utc"], "2026-10-20T11:00+00:00")
        self.assertEqual(filas[1]["vela_inicio_utc"], "")                       # desconocida: no se inventa
        self.assertEqual(filas[1]["decision_utc"], "2026-10-20T10:07:33+00:00")
        self.assertEqual(filas[0]["precio_eur"], "1")                          # el resto no cambia

    def test_cabecera_del_verificador_coincide(self):
        import verificar_salida
        self.assertEqual(verificar_salida.CAB_OPS, an.CAB_OPERACIONES)


class CortesDeEjecucion(BaseDatos):
    """Simula que el proceso muere en distintos momentos de guardar()."""

    def preparar(self):
        v, vol, orden, fuente, ts = an.obtener_datos(150)
        est = an.estado_nuevo({p: x[:100] for p, x in v.items()}, v[an.BTC][99].ts + 3600)
        ahora, precios = an.paso(est, v, vol, orden, ts)
        return est, ahora, precios, fuente, orden, v

    def contar_ops(self):
        with open(an.OPERACIONES, newline="") as f:
            return len(list(csv.reader(f))) - 1

    def test_corte_antes_del_diario_no_cambia_nada(self):
        est, ahora, precios, fuente, orden, v = self.preparar()
        original = an.ps.Transaccion.preparar

        def muere(self):
            raise KeyboardInterrupt("corte")
        an.ps.Transaccion.preparar = muere
        try:
            with self.assertRaises(KeyboardInterrupt):
                an.guardar(est, ahora, precios, fuente, len(orden), len(v))
        finally:
            an.ps.Transaccion.preparar = original
        self.assertFalse(os.path.exists(an.ESTADO))
        self.assertEqual(self.contar_ops(), 0)

    def test_corte_tras_el_diario_se_completa_y_sin_duplicados(self):
        est, ahora, precios, fuente, orden, v = self.preparar()
        n_ops = len(an.COLA_OPS)
        self.assertGreater(n_ops, 0)
        original = an.ps.recuperar

        def muere(carpeta):
            raise KeyboardInterrupt("corte tras el diario")
        an.ps.recuperar = muere
        try:
            with self.assertRaises(KeyboardInterrupt):
                an.guardar(est, ahora, precios, fuente, len(orden), len(v))
        finally:
            an.ps.recuperar = original
        self.assertEqual(an.ps.recuperar(an.DATOS), "completada")
        self.assertEqual(self.contar_ops(), n_ops)
        guardado = json.load(open(an.ESTADO, encoding="utf-8"))
        self.assertEqual(guardado["ultima_vela"], est["ultima_vela"])
        self.assertEqual(an.ps.recuperar(an.DATOS), "nada")


class ValidacionIntegrada(BaseDatos):
    def datos_con_salto(self):
        base = velas([100.0] * 60)
        v = {an.BTC: base, "SALTOEUR": velas([100.0] * 55 + [100.0, 100.0, 100.0, 100.0, 300.0])}
        return v

    def test_salto_anomalo_bloquea_compras_en_ese_par(self):
        v = an.validar_todo(self.datos_con_salto(), T0 + 3600 * 60)
        self.assertIn("SALTOEUR", an.BLOQUEADOS)
        self.assertNotIn(an.BTC, an.BLOQUEADOS)
        est = an.estado_nuevo({p: x[:55] for p, x in v.items()}, T0 + 3600 * 55)
        an.paso(est, v, {an.BTC: 1e6, "SALTOEUR": 1e6}, [an.BTC, "SALTOEUR"], T0 + 3600 * 60)
        for a in est["agentes"]:
            self.assertNotIn("SALTOEUR", a["posiciones"])

    def test_incidencias_se_registran_una_sola_vez(self):
        v = an.validar_todo(self.datos_con_salto(), T0 + 3600 * 60)
        est = an.estado_nuevo({p: x[:55] for p, x in v.items()}, T0 + 3600 * 55)
        ahora, precios = an.paso(est, v, {an.BTC: 1e6, "SALTOEUR": 1e6}, [an.BTC, "SALTOEUR"], T0 + 3600 * 60)
        an.guardar(est, ahora, precios, "demo", 2, 2)
        n1 = len(open(an.ruta_incidencias()).read().splitlines())
        self.assertEqual(n1, 2)                                  # cabecera + salto
        an.validar_todo(self.datos_con_salto(), T0 + 3600 * 60)
        an.guardar(est, ahora, precios, "demo", 2, 2)
        self.assertEqual(len(open(an.ruta_incidencias()).read().splitlines()), n1)

    def test_par_sin_velas_utilizables_se_ignora(self):
        malas = [vl_.Vela(T0 + 3600 * i, float("nan"), 1.0, 1.0, 1.0, 1.0) for i in range(5)]
        v = an.validar_todo({an.BTC: velas([100.0] * 10), "MALOEUR": malas}, T0 + 3600 * 10)
        self.assertNotIn("MALOEUR", v)
        self.assertIn(an.BTC, v)


if __name__ == "__main__":
    unittest.main()
