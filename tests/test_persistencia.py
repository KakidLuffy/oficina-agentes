import json
import os
import tempfile
import unittest
from tests.base import RAIZ  # noqa: F401
import persistencia as ps


class Atomico(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.d = self.t.name

    def leer(self, n):
        with open(os.path.join(self.d, n), encoding="utf-8") as f:
            return f.read()

    def test_escribir_atomico_crea_y_reemplaza(self):
        r = os.path.join(self.d, "a.txt")
        ps.escribir_atomico(r, "uno")
        ps.escribir_atomico(r, "dos")
        self.assertEqual(self.leer("a.txt"), "dos")
        self.assertEqual([f for f in os.listdir(self.d) if f.endswith(".tmp")], [])

    def test_fallo_al_escribir_no_corrompe_el_original(self):
        r = os.path.join(self.d, "a.txt")
        ps.escribir_atomico(r, "bueno")
        original = ps.os.replace

        def falla(*a, **k):
            raise OSError("disco lleno")
        ps.os.replace = falla
        try:
            with self.assertRaises(OSError):
                ps.escribir_atomico(r, "malo")
        finally:
            ps.os.replace = original
        self.assertEqual(self.leer("a.txt"), "bueno")
        self.assertEqual([f for f in os.listdir(self.d) if f.endswith(".tmp")], [])

    def test_transaccion_confirmada_escribe_todo(self):
        tx = ps.Transaccion(self.d)
        tx.poner(os.path.join(self.d, "a"), "1")
        tx.poner(os.path.join(self.d, "b"), "2")
        tx.confirmar()
        self.assertEqual((self.leer("a"), self.leer("b")), ("1", "2"))
        self.assertFalse(os.path.exists(os.path.join(self.d, ps.CARPETA_TX)))

    def test_recuperar_termina_una_transaccion_interrumpida_tras_el_diario(self):
        a, b = os.path.join(self.d, "a"), os.path.join(self.d, "b")
        ps.escribir_atomico(a, "viejo-a")
        ps.escribir_atomico(b, "viejo-b")
        tx = ps.Transaccion(self.d)
        tx.poner(a, "nuevo-a")
        tx.poner(b, "nuevo-b")
        tx.preparar()                                   # diario escrito, nada aplicado aun
        os.replace(os.path.join(self.d, ps.CARPETA_TX, "0.tmp"), a)   # se aplico solo la mitad
        self.assertEqual(ps.recuperar(self.d), "completada")
        self.assertEqual((self.leer("a"), self.leer("b")), ("nuevo-a", "nuevo-b"))
        self.assertFalse(os.path.exists(os.path.join(self.d, ps.CARPETA_TX)))

    def test_recuperar_descarta_transaccion_sin_diario(self):
        a = os.path.join(self.d, "a")
        ps.escribir_atomico(a, "viejo")
        carpeta = os.path.join(self.d, ps.CARPETA_TX)
        os.makedirs(carpeta)
        open(os.path.join(carpeta, "0.tmp"), "w").write("a medias")
        self.assertEqual(ps.recuperar(self.d), "descartada")
        self.assertEqual(self.leer("a"), "viejo")
        self.assertFalse(os.path.exists(carpeta))

    def test_recuperar_descarta_si_falta_un_temporal_o_no_coincide_el_hash(self):
        a = os.path.join(self.d, "a")
        ps.escribir_atomico(a, "viejo")
        tx = ps.Transaccion(self.d)
        tx.poner(a, "nuevo")
        tx.preparar()
        open(os.path.join(self.d, ps.CARPETA_TX, "0.tmp"), "w").write("corrupto")
        self.assertEqual(ps.recuperar(self.d), "descartada")
        self.assertEqual(self.leer("a"), "viejo")

    def test_recuperar_sin_nada_pendiente(self):
        self.assertEqual(ps.recuperar(self.d), "nada")

    def test_json_atomico(self):
        r = os.path.join(self.d, "e.json")
        ps.escribir_json(r, {"x": 1, "ñ": "é"})
        self.assertEqual(json.load(open(r, encoding="utf-8")), {"x": 1, "ñ": "é"})


if __name__ == "__main__":
    unittest.main()
