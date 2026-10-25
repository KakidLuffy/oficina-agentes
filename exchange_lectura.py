"""
Contrato de un adaptador de exchange de SOLO LECTURA (diseño; sin conexion, sin claves, sin red).

No se implementa ninguna conexion a una cuenta: eso exige una necesidad concreta y que el usuario autorice la configuracion
(ver ADAPTADOR_EXCHANGE_SOLO_LECTURA.md). Este modulo fija lo que un adaptador futuro PUEDE hacer y, sobre todo, lo que NO:
  - sus metodos son de consulta (datos de mercado y, si el usuario lo autoriza algun dia, saldos propios);
  - no existe ningun metodo para crear, modificar o cancelar ordenes, ni para retirar o transferir fondos;
  - no acepta credenciales con permisos de trading ni de retirada: el adaptador exige declarar permisos y rechaza cualquiera que no sea «consulta».
"""
import abc

PERMISOS_ADMITIDOS = frozenset({"consulta"})
PERMISOS_PROHIBIDOS = frozenset({"trading", "orden", "retirada", "transferencia", "fondos", "ordenes"})
PREFIJOS_PUBLICOS = ("/0/public/",)


class PermisoDenegado(Exception):
    pass


def comprobar_permisos(permisos):
    """Una credencial solo es aceptable si sus permisos son exclusivamente de consulta."""
    p = {str(x).strip().lower() for x in permisos}
    if not p or not p <= PERMISOS_ADMITIDOS or p & PERMISOS_PROHIBIDOS:
        raise PermisoDenegado(f"permisos no admitidos: {sorted(p - PERMISOS_ADMITIDOS) or 'ninguno declarado'}; solo se admite «consulta»")
    return True


def comprobar_ruta_publica(ruta):
    """Un adaptador de datos de mercado solo puede llamar a rutas publicas del exchange (sin firma ni claves)."""
    if not any(ruta.startswith(p) for p in PREFIJOS_PUBLICOS) or ".." in ruta:
        raise PermisoDenegado(f"ruta no publica: {ruta}")
    return True


class ExchangeLectura(abc.ABC):
    """Solo consulta. Cualquier implementacion debe validar sus permisos con comprobar_permisos()."""

    @abc.abstractmethod
    def pares(self):
        """Pares disponibles contra EUR."""

    @abc.abstractmethod
    def velas(self, par, minutos):
        """Velas OHLCV (objetos velas.Vela)."""

    @abc.abstractmethod
    def reglas(self, par):
        """Minimos y decimales del par (reglas_mercado.Regla)."""
