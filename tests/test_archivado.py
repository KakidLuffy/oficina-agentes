import os
import tempfile
import unittest
from datetime import datetime, timezone
from tests.base import RAIZ  # noqa: F401
import archivado as ar


class Archivado(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.d = self.t.name
        self.a = os.path.join(self.d, "estado.json")
        self.b = os.path.join(self.d, "operaciones.csv")
        self.c = os.path.join(self.d, "director_estado.json")
        open(self.a, "w").write("{}")
        open(self.b, "w").write("h\n1\n2\n")
        open(self.c, "w").write("{}")
        self.ahora = datetime(2026, 10, 22, tzinfo=timezone.utc)

    def test_archiva_verifica_y_borra_originales(self):
        dest = ar.archivar(self.d, "x", [self.a, self.b], [self.c], {"capital": 10}, self.ahora)
        self.assertEqual(ar.verificar(dest), [])
        self.assertFalse(os.path.exists(self.a))
        self.assertTrue(os.path.exists(self.c))                       # contexto: se copia, no se mueve
        self.assertTrue(os.path.exists(os.path.join(dest, "director_estado.json")))
        import json
        m = json.load(open(os.path.join(dest, "MANIFIESTO.json")))
        self.assertEqual({x["archivo"]: x["filas"] for x in m["archivos"] if x["tipo"] == "simulacion"}["operaciones.csv"], 2)
        self.assertEqual(m["meta"]["capital"], 10)

    def test_nunca_sobrescribe_un_archivo_anterior(self):
        d1 = ar.archivar(self.d, "x", [self.a], [], None, self.ahora)
        open(self.a, "w").write("{}")
        d2 = ar.archivar(self.d, "x", [self.a], [], None, self.ahora)
        self.assertNotEqual(d1, d2)
        self.assertTrue(os.path.isdir(d1) and os.path.isdir(d2))

    def test_sin_archivos_no_hace_nada(self):
        os.remove(self.a), os.remove(self.b)
        self.assertIsNone(ar.archivar(self.d, "x", [self.a, self.b], [], None, self.ahora))

    def test_fallo_de_copia_deja_los_originales(self):
        original = ar.shutil.copy2

        def falla(*a, **k):
            raise OSError("disco lleno")
        ar.shutil.copy2 = falla
        try:
            with self.assertRaises(OSError):
                ar.archivar(self.d, "x", [self.a, self.b], [], None, self.ahora)
        finally:
            ar.shutil.copy2 = original
        self.assertTrue(os.path.exists(self.a) and os.path.exists(self.b))

    def test_verificar_detecta_manipulacion(self):
        dest = ar.archivar(self.d, "x", [self.a], [], None, self.ahora)
        open(os.path.join(dest, "estado.json"), "w").write("cambiado")
        self.assertTrue(ar.verificar(dest))


if __name__ == "__main__":
    unittest.main()
