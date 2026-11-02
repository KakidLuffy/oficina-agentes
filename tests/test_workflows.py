import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from tests.base import RAIZ
import verificar_salida as vs

HAY_GIT = shutil.which("git") and shutil.which("bash")


class Verificar(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.d = self.t.name

    def escribir(self, n, txt):
        open(os.path.join(self.d, n), "w").write(txt)

    def bueno(self):
        self.escribir("estado.json", json.dumps({"agentes": [{"nombre": "A", "efectivo": 5, "posiciones": {"X": 1.0}}]}))
        self.escribir("operaciones.csv", ",".join(vs.CAB_OPS) + "\n")
        self.escribir("historial_v2.csv", "a,b\n1,2\n")

    def test_datos_correctos(self):
        self.bueno()
        self.assertEqual(vs.comprobar(self.d), [])

    def test_detecta_json_roto_efectivo_negativo_y_tx_pendiente(self):
        self.bueno()
        self.escribir("estado.json", "{roto")
        self.assertTrue(vs.comprobar(self.d))
        self.bueno()
        self.escribir("estado.json", json.dumps({"agentes": [{"nombre": "A", "efectivo": -3, "posiciones": {}}]}))
        self.assertTrue(any("negativo" in p for p in vs.comprobar(self.d)))
        self.bueno()
        os.makedirs(os.path.join(self.d, ".tx"))
        self.assertTrue(any(".tx" in p for p in vs.comprobar(self.d)))

    def test_detecta_filas_desiguales_y_cabecera_mala(self):
        self.bueno()
        self.escribir("historial_v2.csv", "a,b\n1\n")
        self.assertTrue(vs.comprobar(self.d))
        self.bueno()
        self.escribir("operaciones.csv", "x,y\n")
        self.assertTrue(vs.comprobar(self.d))


class FlujosDeTrabajo(unittest.TestCase):
    def flujos(self):
        d = os.path.join(RAIZ, ".github", "workflows")
        return {f: open(os.path.join(d, f), encoding="utf-8").read() for f in os.listdir(d) if f.endswith(".yml")}

    def test_acciones_fijadas_por_sha_completo(self):
        for f, t in self.flujos().items():
            for m in re.finditer(r"uses:\s*(\S+)", t):
                self.assertRegex(m.group(1), r"@[0-9a-f]{40}$", f"{f}: {m.group(1)} no esta fijada por SHA")

    def test_permisos_minimos_por_defecto(self):
        for f, t in self.flujos().items():
            self.assertRegex(t, r"(?m)^permissions:\n  contents: read", f)

    def test_ningun_flujo_fuerza_el_push(self):
        for f, t in self.flujos().items():
            self.assertNotIn("--force", t, f)
            self.assertNotIn("push -f", t, f)
        self.assertNotIn("--force", open(os.path.join(RAIZ, "scripts", "guardar_datos.sh")).read().replace("NUNCA usa --force", ""))

    def test_la_simulacion_solo_se_lanza_por_push_en_main(self):
        self.assertIn("branches: [main]", self.flujos()["agentes.yml"])


@unittest.skipUnless(HAY_GIT, "hace falta git y bash")
class GuardarDatos(unittest.TestCase):
    def git(self, cwd, *a):
        return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True,
                              env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                                   "GIT_COMMITTER_EMAIL": "t@t"})

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        b = self.t.name
        self.remoto = os.path.join(b, "remoto.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.remoto], check=True)
        self.a, self.b = os.path.join(b, "a"), os.path.join(b, "b")
        for c in (self.a, self.b):
            subprocess.run(["git", "clone", "-q", self.remoto, c], check=True, capture_output=True)
        open(os.path.join(self.a, "base.txt"), "w").write("x")
        self.git(self.a, "checkout", "-q", "-B", "main")
        self.git(self.a, "add", ".")
        self.git(self.a, "commit", "-qm", "base")
        self.git(self.a, "push", "-q", "origin", "main")
        self.git(self.b, "pull", "-q", "origin", "main")
        self.git(self.b, "checkout", "-q", "-B", "main", "origin/main")

    def guardar(self, cwd, msg, *rutas):
        return subprocess.run(["bash", os.path.join(RAIZ, "scripts", "guardar_datos.sh"), msg, *rutas], cwd=cwd, text=True,
                              capture_output=True, env={**os.environ, "GITHUB_REF_NAME": "main",
                                                        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t"})

    def test_sin_cambios_no_hace_commit(self):
        r = self.guardar(self.a, "m", "base.txt")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Sin cambios", r.stdout)

    def test_se_adelantan_otros_y_se_integra_sin_forzar(self):
        os.makedirs(os.path.join(self.b, "datos"))
        open(os.path.join(self.b, "datos", "uno.txt"), "w").write("1")
        self.assertEqual(self.guardar(self.b, "uno", "datos").returncode, 0)
        os.makedirs(os.path.join(self.a, "datos"))
        open(os.path.join(self.a, "datos", "dos.txt"), "w").write("2")
        r = self.guardar(self.a, "dos", "datos")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.git(self.b, "pull", "-q", "origin", "main")
        self.assertTrue(os.path.exists(os.path.join(self.b, "datos", "dos.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.b, "datos", "uno.txt")))


if __name__ == "__main__":
    unittest.main()
