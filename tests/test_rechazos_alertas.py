import csv
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import agentes_nube as an
from tests.base import RAIZ

HAY_BASH = shutil.which("bash") and shutil.which("jq")


class RechazosPersistentes(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.viejo = an.DATOS
        an.DATOS = self.t.name
        self.addCleanup(setattr, an, "DATOS", self.viejo)
        an.RECHAZOS.clear()
        self.addCleanup(an.RECHAZOS.clear)

    def test_categorias(self):
        c = an.categoria_rechazo
        self.assertEqual(c("por debajo del coste minimo del exchange (1.00 EUR < 5 EUR)"), "minimo_coste")
        self.assertEqual(c("por debajo del volumen minimo del exchange (0.1 < 1)"), "minimo_volumen")
        self.assertEqual(c("efectivo insuficiente"), "efectivo_insuficiente")
        self.assertEqual(c("caducada: sin precio de ejecucion en 6 horas"), "caducada")
        self.assertEqual(c("algo nuevo"), "otro")

    def test_no_se_repite_la_misma_decision(self):
        an.RECHAZOS.append(("2026-01-01T00:00:00+00:00", "A", "BTCEUR", "COMPRA", "cruce", "efectivo insuficiente"))
        filas = an.rechazos_nuevos("2026-01-01T01:00:00+00:00")
        self.assertEqual(len(filas), 1)
        self.assertEqual(len(filas[0]), len(an.CAB_RECHAZOS))
        with open(an.ruta_rechazos(), "w", newline="") as f:
            csv.writer(f).writerows([an.CAB_RECHAZOS] + filas)
        self.assertEqual(an.rechazos_nuevos("2026-01-01T02:00:00+00:00"), [])          # el reintento horario no duplica
        an.RECHAZOS.append(("2026-01-01T01:00:00+00:00", "A", "BTCEUR", "COMPRA", "cruce", "efectivo insuficiente"))
        self.assertEqual(len(an.rechazos_nuevos("2026-01-01T02:00:00+00:00")), 1)       # otra vela = otra decision

    def test_dos_rechazos_iguales_en_la_misma_pasada_se_anotan_una_vez(self):
        fila = ("2026-01-01T00:00:00+00:00", "A", "BTCEUR", "VENTA", "x", "ya no hay posicion que vender")
        an.RECHAZOS.extend([fila, fila])
        self.assertEqual(len(an.rechazos_nuevos("ahora")), 1)

    def test_el_archivo_forma_parte_de_lo_que_se_archiva(self):
        import inspect
        self.assertIn("ruta_rechazos()", inspect.getsource(an.archivar))


@unittest.skipUnless(HAY_BASH, "hace falta bash y jq")
class AlertasSinDuplicados(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.log = os.path.join(self.t.name, "llamadas.log")
        gh = os.path.join(self.t.name, "gh")
        with open(gh, "w") as f:
            f.write('#!/usr/bin/env bash\necho "$@" >> "$LOG"\n'
                    'if [ "$1 $2" = "issue list" ]; then cat "$ISSUES"; fi\n')
        os.chmod(gh, os.stat(gh).st_mode | stat.S_IEXEC)

    def correr(self, accion, abiertos):
        issues = os.path.join(self.t.name, "issues.json")
        with open(issues, "w") as f:
            json.dump(abiertos, f)
        env = dict(os.environ, PATH=self.t.name + os.pathsep + os.environ["PATH"], LOG=self.log, ISSUES=issues)
        r = subprocess.run(["bash", os.path.join(RAIZ, "scripts", "alerta_fallo.sh"), accion, "Fallo X", "http://run/1"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return open(self.log).read() if os.path.exists(self.log) else ""

    def test_abre_una_alerta_si_no_hay(self):
        self.assertIn("issue create", self.correr("abrir", []))

    def test_no_duplica_si_ya_hay_una_abierta(self):
        self.assertNotIn("issue create", self.correr("abrir", [{"number": 7, "title": "Fallo X"}]))

    def test_un_issue_de_otro_titulo_no_cuenta(self):
        self.assertIn("issue create", self.correr("abrir", [{"number": 7, "title": "Otra cosa"}]))

    def test_cierra_al_recuperarse(self):
        log = self.correr("cerrar", [{"number": 7, "title": "Fallo X"}])
        self.assertIn("issue close 7", log)

    def test_cerrar_sin_alerta_no_hace_nada(self):
        self.assertNotIn("issue close", self.correr("cerrar", []))

    def test_titulo_con_comillas_no_rompe_el_filtro(self):
        env = dict(os.environ, PATH=self.t.name + os.pathsep + os.environ["PATH"], LOG=self.log,
                   ISSUES=os.path.join(self.t.name, "i.json"))
        open(env["ISSUES"], "w").write("[]")
        r = subprocess.run(["bash", os.path.join(RAIZ, "scripts", "alerta_fallo.sh"), "abrir", 'Fallo "raro" $(x)', "u"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class FlujosConAlerta(unittest.TestCase):
    def test_todos_los_flujos_tienen_alerta_y_solo_ella_escribe_issues(self):
        d = os.path.join(RAIZ, ".github", "workflows")
        for f in os.listdir(d):
            t = open(os.path.join(d, f), encoding="utf-8").read()
            self.assertIn("alerta_fallo.sh abrir", t, f)
            self.assertIn("alerta_fallo.sh cerrar", t, f)
            self.assertEqual(t.count("issues: write"), 1, f)
            self.assertNotIn("issues: write", t.split("\njobs:")[0], f)                  # nunca como permiso global


if __name__ == "__main__":
    unittest.main()
