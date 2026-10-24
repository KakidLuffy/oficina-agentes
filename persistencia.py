"""
Escritura segura de archivos (solo libreria estandar).

- escribir_atomico: escribe en un temporal de la misma carpeta, lo sincroniza con el disco y lo renombra.
  Un corte a mitad nunca deja un archivo a medias: o queda el antiguo o queda el nuevo.
- Transaccion: varios archivos que deben cambiar a la vez (estado, historial, operaciones).
  1) cada contenido nuevo se guarda en datos/.tx/N.tmp   2) se escribe el diario (journal.json) con sus huellas SHA-256
  3) se renombra cada temporal a su destino   4) se borra la carpeta .tx.
  Si el proceso muere despues del paso 2, recuperar() termina el trabajo (el diario garantiza que los temporales son
  completos); si muere antes, recuperar() descarta lo pendiente y los archivos antiguos siguen intactos.
"""
import hashlib
import json
import os
import shutil
import tempfile

CARPETA_TX = ".tx"
DIARIO = "journal.json"


def _sincronizar_carpeta(carpeta):
    try:
        fd = os.open(carpeta, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass                      # no todos los sistemas permiten sincronizar carpetas


def escribir_atomico(ruta, texto):
    carpeta = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(carpeta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=carpeta, suffix=".tmp", prefix=".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ruta)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    _sincronizar_carpeta(carpeta)


def escribir_json(ruta, obj, **kw):
    kw.setdefault("indent", 2)
    kw.setdefault("ensure_ascii", False)
    escribir_atomico(ruta, json.dumps(obj, **kw) + "\n")


def _sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class Transaccion:
    def __init__(self, carpeta):
        self.carpeta = carpeta
        self.dir = os.path.join(carpeta, CARPETA_TX)
        self.items = []           # [(destino, contenido)]

    def poner(self, destino, contenido):
        self.items.append((destino, contenido))

    def preparar(self):
        """Pasos 1 y 2: temporales completos + diario. Despues de esto la transaccion es recuperable."""
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir)
        entradas = []
        for i, (destino, contenido) in enumerate(self.items):
            tmp = os.path.join(self.dir, f"{i}.tmp")
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(contenido)
                f.flush()
                os.fsync(f.fileno())
            entradas.append({"tmp": f"{i}.tmp", "destino": os.path.relpath(destino, self.carpeta), "sha256": _sha(contenido)})
        escribir_atomico(os.path.join(self.dir, DIARIO), json.dumps({"entradas": entradas}, indent=1))

    def confirmar(self):
        self.preparar()
        recuperar(self.carpeta)


def _leer(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return f.read()


def recuperar(carpeta):
    """Devuelve 'nada', 'completada' o 'descartada'."""
    d = os.path.join(carpeta, CARPETA_TX)
    if not os.path.isdir(d):
        return "nada"
    try:
        diario = json.loads(_leer(os.path.join(d, DIARIO)))
        entradas = diario["entradas"]
    except (OSError, ValueError, KeyError):
        shutil.rmtree(d, ignore_errors=True)
        return "descartada"
    pendientes = []
    for e in entradas:
        destino = os.path.join(carpeta, e["destino"])
        tmp = os.path.join(d, e["tmp"])
        if os.path.exists(tmp):
            if _sha(_leer(tmp)) != e["sha256"]:
                shutil.rmtree(d, ignore_errors=True)
                return "descartada"
            pendientes.append((tmp, destino))
        elif not os.path.exists(destino) or _sha(_leer(destino)) != e["sha256"]:
            shutil.rmtree(d, ignore_errors=True)       # ni temporal ni destino correcto: no se puede completar
            return "descartada"
    for tmp, destino in pendientes:
        os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
        os.replace(tmp, destino)
    _sincronizar_carpeta(carpeta)
    shutil.rmtree(d, ignore_errors=True)
    return "completada"
