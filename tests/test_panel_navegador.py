"""Pruebas del panel en un navegador real (Chromium via Playwright). Se omiten si no hay navegador.
Comprueban: datos normales, archivos vacios, columnas en blanco, datos maliciosos (no se ejecuta nada), ?base= manipulado y que no se pide nada a terceros."""
import functools
import http.server
import json
import os
import shutil
import tempfile
import threading
import unittest

from tests.base import RAIZ

try:
    from playwright.sync_api import sync_playwright
except ImportError:            # pragma: no cover
    sync_playwright = None

NAVEGADOR = next((p for p in ("/opt/pw-browsers/chromium", shutil.which("chromium") or "", shutil.which("chromium-browser") or "") if p and os.path.exists(p)), None)
XSS = '<img src=x onerror="window.__pwned=1">'
XSS2 = '"><svg onload="window.__pwned=1">'
CAB_OPS = "fecha_utc,agente,tipo,moneda,precio_eur,unidades,importe_eur,coste_eur,motivo,vela_inicio_utc,decision_utc\n"


def escribir(d, nombre, txt):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, nombre), "w", encoding="utf-8") as f:
        f.write(txt if isinstance(txt, str) else json.dumps(txt))


def estado(nombres, par="XBTEUR"):
    ag = [{"nombre": n, "efectivo": 10.0, "posiciones": {}, "operaciones": 1, "apagado": False, "inicio": "2026-10-01T00:00:00+00:00",
           "precio_inicio": 50000.0, "pendientes": []} for n in nombres]
    return {"capital_inicial": 10.0, "fee": 0.004, "slip": 0.0005, "inicio": "2026-10-01T00:00:00+00:00", "precio_inicio": 50000.0,
            "precios": {par: 51000.0}, "agentes": ag, "version": 4}


@unittest.skipUnless(sync_playwright and NAVEGADOR, "hace falta Playwright y Chromium")
class PanelEnNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.TemporaryDirectory()
        cls.raiz = cls.t.name
        shutil.copy(os.path.join(RAIZ, "index.html"), cls.raiz)
        for f in os.listdir(RAIZ):
            if f.startswith("icon-") or f == "manifest.json":
                shutil.copy(os.path.join(RAIZ, f), cls.raiz)
        class Silencioso(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a, **k):
                pass
        h = functools.partial(Silencioso, directory=cls.raiz)
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"
        cls.pw = sync_playwright().start()
        cls.nav = cls.pw.chromium.launch(executable_path=NAVEGADOR, args=["--no-sandbox"])

    @classmethod
    def tearDownClass(cls):
        cls.nav.close()
        cls.pw.stop()
        cls.srv.shutdown()
        cls.t.cleanup()

    def abrir(self, carpeta, base=None):
        pag = self.nav.new_page()
        self.addCleanup(pag.close)
        self.errores, self.externas = [], []
        pag.on("pageerror", lambda e: self.errores.append(str(e)))
        pag.on("request", lambda r: self.externas.append(r.url) if not r.url.startswith(self.url) else None)
        pag.goto(f"{self.url}/index.html?base={base if base is not None else '/' + carpeta + '/'}")
        pag.wait_for_timeout(1500)
        return pag

    def sin_ejecucion(self, pag):
        self.assertIsNone(pag.evaluate("window.__pwned"), "se ejecuto codigo procedente de los datos")
        self.assertEqual(pag.evaluate("document.querySelectorAll('[onerror],[onload]').length"), 0)

    def test_datos_normales(self):
        d = os.path.join(self.raiz, "normal")
        escribir(d, "estado.json", estado(["A", "B"]))
        escribir(d, "historial_v2.csv", "fecha_utc,precio_eur,A,B,Comprar y mantener\n2026-10-01T00:00,50000,10,10,10\n2026-10-01T01:00,51000,10.2,9.9,10.2\n")
        escribir(d, "operaciones.csv", CAB_OPS + "2026-10-01T01:00:00+00:00,A,COMPRA,XBTEUR,51000,0.0001,5.1,0.02,cruce,,\n")
        pag = self.abrir("normal")
        self.assertEqual(self.errores, [])
        self.assertIn("A", pag.inner_text("body"))
        self.assertEqual(self.externas, [])

    def test_archivos_vacios_muestran_error_sin_romperse(self):
        d = os.path.join(self.raiz, "vacio")
        escribir(d, "estado.json", "{}")
        escribir(d, "historial_v2.csv", "")
        escribir(d, "operaciones.csv", "")
        pag = self.abrir("vacio")
        self.assertEqual(self.errores, [])
        self.assertIn("estado.json", pag.inner_text("body"))

    def test_estado_roto_y_sin_historial(self):
        d = os.path.join(self.raiz, "roto")
        escribir(d, "estado.json", "{roto")
        pag = self.abrir("roto")
        self.assertEqual(self.errores, [])
        self.assertTrue(pag.inner_text("body").strip())

    def test_columnas_nuevas_en_blanco_en_el_historial(self):
        d = os.path.join(self.raiz, "blancos")
        escribir(d, "estado.json", estado(["A", "Nuevo"]))
        escribir(d, "historial_v2.csv", "fecha_utc,precio_eur,A,Nuevo,Comprar y mantener\n2026-10-01T00:00,50000,10,,10\n2026-10-01T01:00,51000,10.2,,10.2\n2026-10-01T02:00,51000,10.3,10,10.2\n")
        escribir(d, "operaciones.csv", CAB_OPS)
        pag = self.abrir("blancos")
        self.assertEqual(self.errores, [])
        self.assertNotIn("NaN", pag.inner_text("body"))

    def test_datos_maliciosos_no_ejecutan_nada(self):
        d = os.path.join(self.raiz, "malo")
        est = estado([XSS, "B"], par=XSS2)
        est["agentes"][1]["posiciones"] = {XSS2: 1.0}
        escribir(d, "estado.json", est)
        escribir(d, "historial_v2.csv", f'fecha_utc,precio_eur,"{XSS}",B,Comprar y mantener\n2026-10-01T00:00,50000,10,10,10\n2026-10-01T01:00,51000,10.2,9.9,10.2\n')
        escribir(d, "operaciones.csv", CAB_OPS + f'2026-10-01T01:00:00+00:00,"{XSS}",COMPRA,"{XSS2}",51000,0.0001,5.1,0.02,"cruce, {XSS}",,\n')
        escribir(d, "laboratorio.json", {"veredicto": XSS, "texto": XSS, "criterio": XSS2, "fuente": XSS, "generado": XSS, "probadas": XSS, "tasa_azar": XSS,
                                        "series": XSS, "mejores_entreno": [{"nombre": XSS, "train_dif": XSS, "test_dif": None, "ok": XSS, "total": XSS, "pasa": True}]})
        escribir(d, "parte_director.json", {"titular": XSS, "lineas": [XSS], "alertas": [XSS2], "generado": XSS, "min_dias": XSS,
                                           "progreso": [{"nombre": XSS, "dias": XSS, "cierres": XSS, "evaluable": True}], "revision": {"problemas": [{"nivel": XSS, "texto": XSS}]}})
        pag = self.abrir("malo")
        for vista in ("lab", "sala"):
            pag.evaluate("(v) => { var b = document.querySelector('[data-view=\"' + v + '\"]'); if (b) b.click(); }", vista)
            pag.wait_for_timeout(300)
        pag.wait_for_timeout(500)
        self.sin_ejecucion(pag)
        self.assertEqual(self.externas, [])

    def test_base_manipulada_no_se_obedece(self):
        for base in ("https://evil.example/datos/", "//evil.example/x/", "javascript:alert(1)", "/..%2f..%2fetc/"):
            self.abrir("normal", base=base)
            self.assertFalse([u for u in self.externas if "evil.example" in u], base)

    def test_no_hay_peticiones_a_tipografias_de_terceros(self):
        with open(os.path.join(RAIZ, "index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("fonts.gstatic.com", html)
        self.assertIn("Content-Security-Policy", html)


if __name__ == "__main__":
    unittest.main()
