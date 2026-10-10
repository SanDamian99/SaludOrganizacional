"""
Códigos de faltante del archivo de docentes.

«Número de hijos» = 10 aparece en 69 docentes, todos de 2025: casi seguro un
código del formulario («no responde»), no diez hijos. Se convierte en faltante
al cargar, no en el archivo, para que sea reversible si el equipo confirma otra
cosa (propuesta 10-oct-2026, §6 punto 8).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.core.texto import norm_txt
from src.docentes.catalogo import HIJOS_CODIGO_FALTANTE


def columnas_hijos(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if "hijos" in norm_txt(str(c))
            and pd.api.types.is_numeric_dtype(df[c])]


def codigos_faltantes(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """(copia con los códigos como NaN, {columna: celdas convertidas})."""
    out = df.copy()
    informe: dict[str, int] = {}
    for c in columnas_hijos(out):
        mascara = out[c] == HIJOS_CODIGO_FALTANTE
        n = int(mascara.sum())
        if n:
            out.loc[mascara, c] = np.nan
            informe[c] = n
    return out, informe
