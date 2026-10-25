import ast
import csv
import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest

import analista as an
import exchange_lectura as ex
from tests.base import RAIZ

AHORA = "2026-10-21T22:00:00Z"
MODULOS_QUE_OPERAN = {"agentes_nube", "ejecucion", "estrategias", "persistencia", "archivado", "reglas_mercado", "costes", "velas",
                      "laboratorio", "director", "comparar_estrategias", "urllib", "socket", "subprocess", "requests", "http", "ssl", "os.system"}


def huellas(carpeta):
    out = {}
    for r, _, fs in os.walk(carpeta):
        for f in fs:
            p = os.path.join(r, f)
            out[os.path.relpath(p, carpeta)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def datos_de_prueba(d, rechazos=None, lab=None, ops=None, agentes=None):
    os.makedirs(d, exist_ok=True)
    json.dump({"agentes": agentes if agentes is not None else [{"nombre": "A", "operaciones": 2, "inicio": "2026-10-01T00:00:00+00:00", "efectivo": 10}]},
              open(os.path.join(d, "estado.json"), "w"))
    json.dump(lab or {"veredicto": "ruido", "tasa_azar": 0.3}, open(os.path.join(d, "laboratorio.json"), "w"))
    with open(os.path.join(d, "operaciones.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fecha_utc", "agente", "moneda", "tipo", "precio_eur", "importe_eur", "motivo", "coste_eur"])
        w.writerows(ops if ops is not None else [["2026-10-02T00:00", "A", "XBTEUR", "COMPRA", 1, 2.0, "", 0.01], ["2026-10-03T00:00", "A", "XBTEUR", "VENTA", 1, 2.1, "", 0.01]])
    if rechazos:
        with open(os.path.join(d, "decisiones_rechazadas.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["fecha_utc", "registrado_utc", "agente", "par", "tipo", "motivo_decision", "categoria", "razon"])
            w.writerows(rechazos)


class Incapacidad(unittest.TestCase):
    """El analista no puede operar: lo garantiza su codigo, no solo su buena fe."""
    def setUp(self):
        self.src = open(os.path.join(RAIZ, "analista.py"), encoding="utf-8").read()
        self.tree = ast.parse(self.src)

    def test_no_importa_nada_que_opere_o_use_la_red(self):
        for n in ast.walk(self.tree):
            nombres = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] if isinstance(n, ast.ImportFrom) else []
            for nombre in nombres:
                self.assertNotIn(nombre.split(".")[0], MODULOS_QUE_OPERAN, nombre)

    def test_solo_una_funcion_escribe_archivos(self):
        for f in [n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)]:
            escribe = any(isinstance(c, ast.Call) and getattr(c.func, "id", "") == "open" and len(c.args) > 1 and
                          isinstance(c.args[1], ast.Constant) and "w" in str(c.args[1].value) for c in ast.walk(f))
            self.assertEqual(escribe, f.name == "escribir_salida", f.name)

    def test_el_lector_solo_abre_la_lista_cerrada(self):
        l = an.Lector("datos")
        for malo in ("../agentes_nube.py", "estado.json/../x", "reglas_mercado.json", "/etc/passwd"):
            with self.assertRaises(PermissionError):
                l._ruta(malo)

    def test_no_hay_modulo_que_importe_al_analista_desde_el_simulador(self):
        for f in ("agentes_nube.py", "ejecucion.py", "director.py", "laboratorio.py"):
            self.assertNotIn("import analista", open(os.path.join(RAIZ, f), encoding="utf-8").read())

    def test_los_estados_posibles_no_incluyen_aplicar(self):
        self.assertEqual(set(an.ESTADOS), {"pendiente_de_revision", "aceptada_para_probar", "descartada"})


class Ejecucion(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.datos = os.path.join(self.t.name, "datos")
        self.out = os.path.join(self.t.name, "salida")

    def correr(self, out=None):
        import sys
        viejo = sys.argv
        sys.argv = ["analista.py", "--datos", self.datos, "--out", out or self.out]
        try:
            an.main()
        finally:
            sys.argv = viejo

    def test_no_modifica_ningun_dato_y_funciona_con_datos_de_solo_lectura(self):
        datos_de_prueba(self.datos, rechazos=[[f"2026-10-0{i}", "x", "A", "XBTEUR", "COMPRA", "c", "minimo_coste", "por debajo del coste minimo"] for i in range(1, 8)])
        antes = huellas(self.datos)
        for r, ds, fs in os.walk(self.datos):
            for n in fs:
                os.chmod(os.path.join(r, n), stat.S_IREAD)
            os.chmod(r, stat.S_IREAD | stat.S_IEXEC)
        self.addCleanup(lambda: [os.chmod(r, 0o755) for r, _, _ in os.walk(self.datos)])
        self.correr()
        self.assertEqual(huellas(self.datos), antes)
        self.assertEqual(sorted(os.listdir(self.out)), [an.SALIDA_JSON, an.SALIDA_MD])

    def test_las_propuestas_quedan_pendientes_y_con_evidencia(self):
        datos_de_prueba(self.datos, rechazos=[[f"2026-10-0{i}", "x", "A", "XBTEUR", "COMPRA", "c", "minimo_coste", "por debajo del coste minimo"] for i in range(1, 8)])
        self.correr()
        props = json.load(open(os.path.join(self.out, an.SALIDA_JSON)))["propuestas"]
        self.assertTrue(props)
        for p in props:
            self.assertEqual(p["estado"], "pendiente_de_revision")
            self.assertTrue(p["evidencia"] and p["validacion_requerida"])
        self.assertTrue(any("minimo_coste" in p["titulo"] for p in props))

    def test_repetir_no_duplica_ni_pisa_la_revision_humana(self):
        datos_de_prueba(self.datos)
        self.correr()
        ruta = os.path.join(self.out, an.SALIDA_JSON)
        d = json.load(open(ruta))
        d["propuestas"][0]["estado"] = "descartada"
        json.dump(d, open(ruta, "w"))
        n = len(d["propuestas"])
        self.correr()
        d2 = json.load(open(ruta))
        self.assertEqual(len(d2["propuestas"]), n)
        self.assertEqual(d2["propuestas"][0]["estado"], "descartada")

    def test_inconsistencia_de_contadores(self):
        datos_de_prueba(self.datos, agentes=[{"nombre": "A", "operaciones": 9, "inicio": "2026-10-01T00:00:00+00:00"}])
        self.correr()
        props = json.load(open(os.path.join(self.out, an.SALIDA_JSON)))["propuestas"]
        self.assertTrue(any(p["tipo"] == "inconsistencia" for p in props))

    def test_sin_datos_no_falla(self):
        os.makedirs(self.datos)
        self.correr()
        self.assertEqual(json.load(open(os.path.join(self.out, an.SALIDA_JSON)))["propuestas"], [])

    def test_archivos_corruptos_no_rompen_al_analista(self):
        os.makedirs(self.datos)
        open(os.path.join(self.datos, "estado.json"), "w").write("{roto")
        open(os.path.join(self.datos, "operaciones.csv"), "w").write('a,b\n"x')
        self.correr()


class Validador(unittest.TestCase):
    def base(self, **k):
        p = {"id": "x-1", "tipo": "hipotesis", "titulo": "Las ordenes rechazadas", "detalle": "Comparar con Comprar y mantener",
             "evidencia": ["a.csv"], "validacion_requerida": "Repetir el laboratorio", "estado": "pendiente_de_revision", "creada": AHORA}
        p.update(k)
        return p

    def test_acepta_texto_normal(self):
        ok, mal = an.validar_propuestas([self.base()])
        self.assertEqual((len(ok), len(mal)), (1, 0))

    def test_rechaza_campos_de_accion_y_estados_no_permitidos(self):
        for p in (dict(self.base(), accion="comprar BTC"), self.base(estado="aplicada"), self.base(tipo="orden"),
                  self.base(detalle="Habilitar trading real en Kraken"), self.base(detalle="Hay que transferir fondos a la cuenta"),
                  self.base(validacion_requerida="Activar la estrategia X ya"), self.base(detalle="Cambiar el limite de perdida a 50 %"),
                  self.base(titulo=""), self.base(evidencia="a.csv"), "texto", None):
            ok, mal = an.validar_propuestas([p])
            self.assertEqual((len(ok), len(mal)), (0, 1), p)

    def test_combinar_no_toca_existentes(self):
        a = self.base(id="a", estado="aceptada_para_probar")
        nuevo = an.combinar([a], [dict(a, estado="pendiente_de_revision"), self.base(id="b")])
        self.assertEqual([p["id"] for p in nuevo], ["a", "b"])
        self.assertEqual(nuevo[0]["estado"], "aceptada_para_probar")


class FlujoDelAnalista(unittest.TestCase):
    def test_solo_manual_y_solo_publica_sus_dos_archivos(self):
        with open(os.path.join(RAIZ, ".github", "workflows", "analista.yml"), encoding="utf-8") as f:
            t = f.read()
        self.assertIn("workflow_dispatch", t)
        self.assertNotIn("schedule:", t)
        self.assertNotIn("push:", t)
        self.assertIn("datos/propuestas_analista.json datos/propuestas_analista.md", t)
        self.assertNotIn("guardar_datos.sh \"Propuestas del analista (pendientes de revisión)\" datos\n", t)      # nunca la carpeta entera


class AdaptadorDeExchange(unittest.TestCase):
    def test_solo_permisos_de_consulta(self):
        self.assertTrue(ex.comprobar_permisos(["consulta"]))
        for malo in (["consulta", "trading"], ["retirada"], [], ["Orden"], ["fondos"]):
            with self.assertRaises(ex.PermisoDenegado):
                ex.comprobar_permisos(malo)

    def test_solo_rutas_publicas(self):
        self.assertTrue(ex.comprobar_ruta_publica("/0/public/OHLC"))
        for malo in ("/0/private/AddOrder", "/0/private/Withdraw", "/0/public/../private/Balance", "OHLC"):
            with self.assertRaises(ex.PermisoDenegado):
                ex.comprobar_ruta_publica(malo)

    def test_la_interfaz_no_tiene_metodos_de_ejecucion(self):
        prohibidos = ("order", "orden", "buy", "sell", "withdraw", "retir", "transfer", "cancel", "trade", "comprar", "vender")
        for n in dir(ex.ExchangeLectura):
            self.assertFalse(any(w in n.lower() for w in prohibidos), n)

    def test_ningun_modulo_del_sistema_importa_el_adaptador(self):
        for f in os.listdir(RAIZ):
            if f.endswith(".py") and f != "exchange_lectura.py":
                self.assertNotIn("exchange_lectura", open(os.path.join(RAIZ, f), encoding="utf-8").read(), f)


if __name__ == "__main__":
    unittest.main()
