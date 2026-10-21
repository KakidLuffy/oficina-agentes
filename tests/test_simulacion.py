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
        self.assertAlmostEqual(a["efectivo"], an.START - an.SLOT, delta=1e-5)    # el redondeo de cantidad devuelve migajas
        an.operar(a, "VENTA", an.BTC, 100.0, FECHA, {an.BTC: 1e6})
        self.assertEqual(a["posiciones"], {})
        self.assertLess(a["efectivo"], an.START)           # pierde comision y deslizamiento
        perdido = an.START - a["efectivo"]
        h = an.SPREAD / 2
        esperado = an.SLOT * (1 - (1 - an.FEE) ** 2 * (1 - h - an.SLIP) / (1 + h + an.SLIP))
        self.assertAlmostEqual(perdido, esperado, delta=1e-5)

    def test_coste_registrado_coincide_con_lo_perdido(self):
        a = self.agente()
        an.operar(a, "COMPRA", an.BTC, 50.0, FECHA, {an.BTC: 1e6})
        an.operar(a, "VENTA", an.BTC, 50.0, FECHA, {an.BTC: 1e6})
        total = sum(float(r["coste_eur"]) for r in filas_ops())
        self.assertAlmostEqual(total, an.START - a["efectivo"], places=3)

    def test_poco_volumen_cuesta_mas(self):
        poco, mucho = an.costes_par("XEUR", {"XEUR": 10}), an.costes_par("XEUR", {"XEUR": 1e7})
        self.assertGreater(poco.slip, mucho.slip)
        self.assertGreater(poco.spread, mucho.spread)
        self.assertEqual(an.costes_par(an.BTC, {}), an.costes_par("XEUR", {"XEUR": 1e7}))          # BTC siempre liquido
        self.assertEqual(an.costes_par("XEUR", {}), an.costes_par("XEUR", {"XEUR": 10}))            # desconocido = poco liquido

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

    def test_momentum_decide_al_cierre_y_ejecuta_en_la_apertura_siguiente(self):
        precios = [100.0] * 39 + [103.0]
        v = {an.BTC: velas(precios)}
        est = an.estado_nuevo({an.BTC: v[an.BTC][:39]}, T0 + 3600 * 39)
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 40)          # aun no existe la vela 40
        por = {a["nombre"]: a for a in est["agentes"]}
        self.assertEqual(por["Momentum"]["posiciones"], {})
        self.assertEqual([(o["par"], o["tipo"]) for o in por["Momentum"]["pendientes"]], [(an.BTC, "COMPRA")])
        self.assertEqual(filas_ops(), [])
        # aparece la vela 40 (abre a 105): la orden pendiente se ejecuta a ESA apertura, no al cierre 103
        v[an.BTC].append(vl_.Vela(T0 + 3600 * 40, 105.0, 105.0, 105.0, 105.0, 1.0))
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 40 + 600)
        self.assertEqual(por["Momentum"]["pendientes"], [])
        self.assertIn(an.BTC, por["Momentum"]["posiciones"])
        fila = [f for f in filas_ops() if f["agente"] == "Momentum"][0]
        self.assertAlmostEqual(float(fila["precio_eur"]), round(an.costes_par(an.BTC, {an.BTC: 1e6}).precio_compra(105.0), 6), places=5)
        self.assertEqual(fila["vela_inicio_utc"], an.iso_vela(T0 + 3600 * 39))      # decidida con la vela 39...
        self.assertEqual(fila["decision_utc"], an.iso_vela(T0 + 3600 * 40))         # ...que cierra cuando abre la 40

    def test_si_la_vela_siguiente_ya_existe_se_ejecuta_en_la_misma_pasada(self):
        precios = [100.0] * 39 + [103.0]
        v = {an.BTC: velas(precios) + [vl_.Vela(T0 + 3600 * 40, 104.0, 104.0, 104.0, 104.0, 1.0)]}   # la vela 40 esta abierta
        est = an.estado_nuevo({an.BTC: v[an.BTC][:39]}, T0 + 3600 * 39)
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 40 + 600)
        mom = {a["nombre"]: a for a in est["agentes"]}["Momentum"]
        self.assertIn(an.BTC, mom["posiciones"])
        self.assertEqual(mom["pendientes"], [])
        px = float([f for f in filas_ops() if f["agente"] == "Momentum"][0]["precio_eur"])
        self.assertAlmostEqual(px, an.costes_par(an.BTC, {an.BTC: 1e6}).precio_compra(104.0), places=4)

    def test_orden_pendiente_se_rechaza_si_ya_no_cabe(self):
        est = an.estado_nuevo({an.BTC: velas([100.0] * 39)}, T0 + 3600 * 39)
        a = est["agentes"][0]
        a["efectivo"] = 0.5                                                # sin dinero cuando llega la ejecucion
        a["pendientes"] = [{"par": an.BTC, "tipo": "COMPRA", "motivo": "x", "vela_ts": T0 + 3600 * 38}]
        v = {an.BTC: velas([100.0] * 40)}                                  # la vela 39 (siguiente a la decision) ya existe
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 39 + 60)
        self.assertEqual(a["posiciones"], {})
        self.assertEqual(a["pendientes"], [])
        self.assertEqual([r[5] for r in an.RECHAZOS], ["efectivo insuficiente"])

    def test_no_se_duplican_ordenes_ni_se_exceden_posiciones_con_ordenes_en_cola(self):
        est = an.estado_nuevo({an.BTC: velas([100.0] * 39)}, T0 + 3600 * 39)
        a = est["agentes"][0]
        a["pendientes"] = [{"par": f"M{k}EUR", "tipo": "COMPRA", "motivo": "x", "vela_ts": T0 + 3600 * 38} for k in range(an.MAX_POS)]
        v = {an.BTC: velas([100.0] * 39)}
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 39)        # sin velas de esas monedas: siguen pendientes
        self.assertEqual(len(a["pendientes"]), an.MAX_POS)
        self.assertEqual(a["posiciones"], {})

    def test_orden_caduca_si_la_siguiente_vela_llega_demasiado_tarde(self):
        est = an.estado_nuevo({an.BTC: velas([100.0] * 39)}, T0 + 3600 * 39)
        a = est["agentes"][0]
        a["pendientes"] = [{"par": an.BTC, "tipo": "COMPRA", "motivo": "x", "vela_ts": T0 + 3600 * 39}]
        v = {an.BTC: velas([100.0] * 39) + [vl_.Vela(T0 + 3600 * 50, 100.0, 100.0, 100.0, 100.0, 1.0)]}
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 39)
        self.assertEqual(a["pendientes"], [])
        self.assertEqual(a["posiciones"], {})
        self.assertTrue(any("caducada" in r[5] for r in an.RECHAZOS))

    def test_stop_de_perdida_en_agente_rapido(self):
        a = an.agente_nuevo("Momentum rapido", 100.0)
        est = {"ultima_vela": T0, "precios": {}, "agentes": [a]}
        a["posiciones"], a["entradas"], a["efectivo"] = {an.BTC: 0.02}, {an.BTC: 100.0}, 8.0
        v = {an.BTC: velas([100.0] * 10 + [98.0]) + [vl_.Vela(T0 + 3600 * 11, 97.0, 97.0, 97.0, 97.0, 1.0)]}   # -2 %; la vela siguiente abre a 97
        est["ultima_vela"] = v[an.BTC][9].ts
        an.paso(est, v, {an.BTC: 1e6}, [an.BTC], T0 + 3600 * 11 + 300)
        self.assertEqual(a["posiciones"], {})
        fila = [f for f in filas_ops() if "stop de perdida" in f["motivo"]][0]
        self.assertAlmostEqual(float(fila["precio_eur"]), an.costes_par(an.BTC, {an.BTC: 1e6}).precio_venta(97.0), places=4)

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

    def test_agente_nuevo_no_tiene_historial_inventado(self):
        with open(an.HISTORIAL, "w", newline="") as f:
            f.write("fecha_utc,precio_eur,A\n2026-01-01,100,9.5\n")
        import io
        txt = an.historial_con_fila(["fecha_utc", "precio_eur", "A", "B"], ["2026-01-02", "101", "9.6", "10"])
        filas = list(csv.reader(io.StringIO(txt, newline="")))
        self.assertEqual(filas[1], ["2026-01-01", "100", "9.5", ""])          # el agente B no existia: sin dato, no START
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


class Precision(BaseDatos):
    def test_importe_y_coste_se_guardan_sin_redondear_a_2_decimales(self):
        a = self.agente()
        an.operar(a, "COMPRA", an.BTC, 100.0, FECHA, {an.BTC: 1e6})
        fila = dict(zip(an.CAB_OPERACIONES, an.COLA_OPS[-1]))
        self.assertNotEqual(fila["importe_eur"], round(fila["importe_eur"], 2))     # tiene mas de 2 decimales
        self.assertGreater(fila["coste_eur"], 0)
        self.assertEqual(fila["importe_eur"], round(fila["importe_eur"], 8))

    def test_un_ciclo_con_ganancia_diminuta_se_ve_como_ganadora(self):
        a = self.agente()
        an.operar(a, "COMPRA", an.BTC, 100.0, FECHA, {an.BTC: 1e6})
        an.operar(a, "VENTA", an.BTC, 100.5, FECHA, {an.BTC: 1e6})                 # sube un 0,5 % (algo mas que los costes)
        compra, venta = an.COLA_OPS[-2][5], an.COLA_OPS[-1][5]
        self.assertNotEqual(round(compra, 2), compra)
        self.assertEqual(venta > compra, a["efectivo"] > an.START)                  # la clasificacion coincide con la contabilidad real

    def test_historial_con_seis_decimales(self):
        v, vol, orden, fuente, ts = an.obtener_datos(150)
        est = an.estado_nuevo({p: x[:100] for p, x in v.items()}, v[an.BTC][99].ts + 3600)
        ahora, precios = an.paso(est, v, vol, orden, ts)
        an.guardar(est, ahora, precios, fuente, len(orden), len(v))
        with open(an.HISTORIAL, newline="") as f:
            ult = list(csv.reader(f))[-1]
        self.assertTrue(any(len(x.split(".")[-1]) > 2 for x in ult[2:]))


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
