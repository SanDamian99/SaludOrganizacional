"""
Importación perezosa de librerías pesadas.

`scipy.stats` tarda ~0,4 s en importarse y `matplotlib` ~0,25 s y 60 MB de
memoria. Casi ninguna página los necesita (en pantalla se dibuja con Plotly y
las cifras publicadas ya vienen calculadas), pero varios módulos los importaban
en lo alto y cualquier página los pagaba al arrancar.

`modulo("scipy.stats")` devuelve un sustituto que importa el módulo real la
primera vez que se le pide un atributo. El código que lo usa no cambia:
`sps.norm.ppf(...)` sigue siendo `sps.norm.ppf(...)`.
"""
from __future__ import annotations

import importlib
from types import ModuleType


class _ModuloPerezoso:
    __slots__ = ("_nombre", "_modulo")

    def __init__(self, nombre: str):
        self._nombre = nombre
        self._modulo: ModuleType | None = None

    def _cargar(self) -> ModuleType:
        if self._modulo is None:
            self._modulo = importlib.import_module(self._nombre)
        return self._modulo

    def __getattr__(self, atributo: str):
        return getattr(self._cargar(), atributo)

    def __repr__(self) -> str:
        estado = "cargado" if self._modulo is not None else "sin cargar"
        return f"<módulo perezoso {self._nombre} ({estado})>"


def modulo(nombre: str) -> _ModuloPerezoso:
    """Sustituto de `import nombre` que no importa nada hasta el primer uso."""
    return _ModuloPerezoso(nombre)
