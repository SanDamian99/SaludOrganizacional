"""
Tabla del mapa — Observatorio 360.

Una fila por colegio con lo que el mapa dibuja. No calcula estadística: lee de
`Analisis` lo que la plataforma ya muestra (conteo por colegio, medias por
colegio y media del nivel) y respeta los grupos visibles que decide la vista de
comunidad. Nunca lleva el número exacto de respuestas: solo el tramo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from src.core import colegios

# capa → indicador del catálogo de estudiantes (None: es de cobertura)
CAPAS = {"respuestas": None, "sentirse_parte": "PSSM_Total",
         "apoyo_social": "MSPSS_Total"}
ETIQUETAS_CAPA = {"respuestas": "Respuestas recibidas",
                  "sentirse_parte": "Sentirse parte del colegio",
                  "apoyo_social": "Apoyo social"}
TRAMOS = ((100, "100 o más"), (30, "30 a 99"), (10, "10 a 29"))

CON_CIFRA = "con_cifra"
PEQUENA = "pequena"                  # grupo bajo el mínimo: sin cifra
SIN_FORMULARIO = "sin_formulario"    # el colegio no aparece en la corrida
SIN_INDICADOR = "sin_indicador"      # visible, pero sin cifra de este indicador
ESTADOS = (CON_CIFRA, PEQUENA, SIN_FORMULARIO, SIN_INDICADOR)


@dataclass(frozen=True)
class FilaMapa:
    codigo: str
    nombre: str
    estado: str
    tramo: str | None = None
    valor: float | None = None
    referencia: float | None = None


def _numero(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def tramo_de(n) -> str | None:
    """Tramo de respuestas; None si no es un número o está bajo el mínimo."""
    v = _numero(n)
    if v is None:
        return None
    return next((nombre for corte, nombre in TRAMOS if v >= corte), None)


def _valor_colegio(tabla, clave: str, codigo: str) -> float | None:
    if tabla is None or tabla.empty or "clave" not in tabla.columns:
        return None
    fila = tabla[tabla["clave"] == clave]
    columna = f"M·{codigo}"
    if fila.empty or columna not in fila.columns:
        return None
    return _numero(fila.iloc[0][columna])


def _referencia(analisis, clave: str | None) -> float | None:
    d = getattr(analisis, "descriptivos", None)
    if clave is None or d is None or d.empty or "clave" not in d.columns:
        return None
    fila = d[d["clave"] == clave]
    return None if fila.empty or "M" not in fila.columns else _numero(fila.iloc[0]["M"])


def tabla_mapa(analisis, capa: str, codigos, visibles, pequenos) -> list[FilaMapa]:
    """Una fila por código de `codigos`, en ese orden."""
    if capa not in CAPAS:
        raise ValueError(f"Capa no permitida en el mapa: {capa!r}")
    clave = CAPAS[capa]
    conteos = (getattr(analisis, "muestra", None) or {}).get("colegio") or {}
    tabla = getattr(analisis, "por_colegio", None)
    referencia = _referencia(analisis, clave)
    filas: list[FilaMapa] = []
    for codigo in codigos:
        nombre = colegios.nombre(codigo)
        if codigo in pequenos:
            filas.append(FilaMapa(codigo, nombre, PEQUENA))
        elif codigo not in visibles:
            filas.append(FilaMapa(codigo, nombre, SIN_FORMULARIO))
        elif clave is None:
            filas.append(FilaMapa(codigo, nombre, CON_CIFRA,
                                  tramo=tramo_de(conteos.get(codigo))))
        else:
            valor = _valor_colegio(tabla, clave, codigo)
            if valor is None:
                filas.append(FilaMapa(codigo, nombre, SIN_INDICADOR))
            else:
                filas.append(FilaMapa(codigo, nombre, CON_CIFRA, valor=valor,
                                      referencia=referencia))
    return filas
