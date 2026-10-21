"""Utilidades comunes de las pruebas: carpeta temporal de datos y velas sinteticas."""
import os
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import agentes_nube as an  # noqa: E402

T0 = 1_700_000_000 - (1_700_000_000 % 3600)


def velas(precios, par=None, t0=T0):
    """Lista [(ts, cierre)] con una vela por hora."""
    return [(t0 + 3600 * i, float(p)) for i, p in enumerate(precios)]


class BaseDatos(unittest.TestCase):
    """Redirige todos los archivos de datos a una carpeta temporal y restaura los parametros globales."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        d = self.tmp.name
        self._orig = {k: getattr(an, k) for k in ("DATOS", "ESTADO", "HISTORIAL", "OPERACIONES", "RESUMEN", "GRAFICO", "FEE", "SLIP")}
        an.DATOS = d
        an.ESTADO = os.path.join(d, "estado.json")
        an.HISTORIAL = os.path.join(d, "historial_v2.csv")
        an.OPERACIONES = os.path.join(d, "operaciones.csv")
        an.RESUMEN = os.path.join(d, "resumen.md")
        an.GRAFICO = os.path.join(d, "grafico.svg")
        self.addCleanup(self._restaurar)
        an.asegurar_operaciones()

    def _restaurar(self):
        for k, v in self._orig.items():
            setattr(an, k, v)

    def agente(self, nombre="Cruce 10/30"):
        return an.agente_nuevo(nombre, 100.0)
