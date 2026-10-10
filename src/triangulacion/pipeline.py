"""
Orquestación de la Triangulación 360 — solo local, solo agregados.

`analizar(fuentes)` arma la capa 1 (por colegio y por grado), enlaza las
díadas y las analiza. Devuelve un `Triangulacion` que SOLO tiene tablas
agregadas: ni filas, ni seudónimos, ni la tabla de díadas (que vive y muere
dentro de esta función). Lo que ve la página y lo que exporta el ZIP sale de
aquí.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import diadas as dy
from src.triangulacion import enlace as en
from src.triangulacion import fuentes as fu


@dataclass
class Triangulacion:
    capa1: c1.Capa1
    enlace: dict = field(default_factory=dict)        # informe agregado del enlace
    diadas: dy.Diadas = field(default_factory=dy.Diadas)
    actores: dict = field(default_factory=dict)       # {actor: unidades analizadas}

    @property
    def n_colegios(self) -> int:
        return len(self.capa1.colegios)


def analizar(fuentes: fu.Fuentes, n_boot: int = cat.N_BOOT) -> Triangulacion:
    capa = c1.analizar(fuentes)
    enlace = en.enlazar(fuentes.estudiantes, fuentes.ninos, fuentes.cuidadores)
    resultado = dy.analizar(enlace.diadas, n_boot=n_boot)
    actores = {
        "Estudiantes": len(fuentes.estudiantes),
        "Cuidadores (distintos)": int(fuentes.cuidadores["ID_cuidador"].nunique()),
        "Niños reportados por cuidadores": len(fuentes.ninos),
        "Docentes": len(fuentes.docentes),
    }
    return Triangulacion(capa1=capa, enlace=enlace.informe, diadas=resultado, actores=actores)


def cargar_y_analizar(k: bytes | None = None, n_boot: int = cat.N_BOOT,
                      disp: fu.Disponibles | None = None) -> Triangulacion:
    """`disp` permite pasar los archivos ya localizados (p. ej. bajados del almacén)."""
    return analizar(fu.cargar(disp, k=k), n_boot=n_boot)
