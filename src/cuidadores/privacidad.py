"""
Base publicable de Cuidadores 360 — el mínimo cuenta CUIDADORES DISTINTOS.

Misma regla que `estudiantes.privacidad` (spec §5.1), con una diferencia
(spec §4): en el marco de niños dos filas pueden ser del mismo cuidador (sus
dos hijos), y lo que identifica a alguien es el adulto que respondió. Por eso
cada umbral de `MIN_GROUP_N` se cuenta con `nunique` de `ID_cuidador`:

  · celda colegio × grado publicable si reúne ≥ 10 cuidadores distintos;
  · colegio = unión de sus celdas; sin celdas, el colegio completo si llega;
  · grado = unión de sus celdas;
  · nivel = todos si el resto R es vacío o reúne ≥ 10 cuidadores de ≥ 2
    colegios con margen `MARGEN_RESTO` sobre su colegio más grande;
  · «OTRO» (colegio escrito a mano que no se reconoce) y «SIN_DATO» no son
    colegios: nunca forman celda ni colegio y solo cuentan en el total;
  · todo o nada por indicador: una unidad con 1 a 9 cuidadores con dato en un
    indicador pierde ese indicador.

Devuelve un `estudiantes.privacidad.Base`, así que `filas`, `relaciones`,
`unidades`, `estudiantes.supresion` y la vista lo usan sin cambios. En el
marco de cuidadores (una fila por cuidador) el resultado es idéntico al de
estudiantes, y hay una prueba que lo comprueba.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import privacidad as priv

UNIDAD = "ID_cuidador"
# Códigos que no son un colegio: nunca forman celda ni colegio publicable.
# Sus respuestas cuentan en el total del marco (como resto), si el resto llega.
COLEGIOS_SIN_GRUPO = ("OTRO", "SIN_DATO")
COLUMNAS_ID = ("ID_cuidador", "ID_nino", "ts", "Ola", "Quien", "Colegio", "Colegio_nombre",
               "Sede", "Grado", "Grado_detalle", "Grado_estado", "Orden_hijo", "Edad",
               "Sexo", *cat.CONTEXTO)


def _distintos(d: pd.DataFrame, idx) -> int:
    if UNIDAD not in d.columns:
        return len(idx)
    return int(d.loc[idx, UNIDAD].nunique())


def columnas_de_analisis(d: pd.DataFrame) -> list[str]:
    """Columnas numéricas con cifras: sin identificación, contexto ni «_…»."""
    return [c for c in d.columns
            if c not in COLUMNAS_ID and not str(c).startswith("_")
            and pd.api.types.is_numeric_dtype(d[c])]


def _resto_suficiente(d: pd.DataFrame, idx, minimo: int) -> bool:
    sub = d.loc[idx]
    if _distintos(d, idx) < minimo:
        return False
    por_colegio = sub.groupby("Colegio")[UNIDAD].nunique() if UNIDAD in sub.columns \
        else sub["Colegio"].value_counts()
    if len(por_colegio) < 2:
        return False
    return _distintos(d, idx) - int(por_colegio.max()) >= priv.MARGEN_RESTO


def base_publicable(d: pd.DataFrame, minimo: int = cat.MIN_GROUP_N) -> priv.Base:
    priv._exigir_indice_unico(d)
    b = priv.Base(n_total=len(d))
    if d.empty or not {"Colegio", "Grado"} <= set(d.columns):
        b.nivel = d.index
        return b
    agrupable = d[~d["Colegio"].isin(COLEGIOS_SIN_GRUPO)]
    for (colegio, grado), sub in agrupable.groupby(["Colegio", "Grado"]):
        if _distintos(d, sub.index) >= minimo:
            b.celdas[priv.clave_celda(colegio, grado)] = sub.index
    for colegio, sub in agrupable.groupby("Colegio"):
        propias = [i for k, i in b.celdas.items() if priv.partir_celda(k)[0] == str(colegio)]
        if propias:
            b.colegios[str(colegio)] = priv.union(propias)
        elif _distintos(d, sub.index) >= minimo:
            b.colegios[str(colegio)] = sub.index
    for grado in d["Grado"].dropna().unique():
        propias = [i for k, i in b.celdas.items() if priv.partir_celda(k)[1] == str(grado)]
        if propias:
            b.grados[str(grado)] = priv.union(propias)
    publicado = priv.union(b.colegios.values())
    resto = d.index.difference(publicado)
    b.incluye_resto = len(resto) == 0 or _resto_suficiente(d, resto, minimo)
    b.nivel = d.index if b.incluye_resto else publicado
    return b


def aplicar_todo_o_nada(d: pd.DataFrame, base: priv.Base, columnas: list[str] | None = None,
                        minimo: int = cat.MIN_GROUP_N) -> tuple[pd.DataFrame, dict]:
    """Como `estudiantes.privacidad.aplicar_todo_o_nada`, contando cuidadores distintos."""
    priv._exigir_indice_unico(d)
    dm = d.copy()
    columnas = columnas_de_analisis(d) if columnas is None else columnas
    lista = priv.unidades(base)
    en_unidades = priv.union(i for _, i in lista)
    resto = (d.index.intersection(base.nivel).difference(en_unidades)
             if base.incluye_resto else d.index[:0])
    grupos = [d.index.intersection(i) for _, i in lista]
    suprimidos: dict = {}
    for col in columnas:
        if col not in d.columns:
            continue
        validos = d[col].notna()
        borrar = []
        for idx in grupos:
            n = _distintos(d, idx[validos.loc[idx].to_numpy()])
            if 0 < n < minimo:
                borrar.append(idx)
        if len(resto):
            v_resto = resto[validos.loc[resto].to_numpy()]
            if len(v_resto) and not _resto_suficiente(d, v_resto, minimo):
                borrar.append(resto)
        if not borrar:
            continue
        idx = priv.union(borrar)
        n = int(validos.loc[idx].sum())
        if n:
            dm.loc[idx, col] = np.nan
            suprimidos[col] = n
    return dm, suprimidos


def distintos_por_grupo(d: pd.DataFrame, columna: str) -> dict:
    """{grupo: cuidadores distintos}."""
    if d.empty or columna not in d.columns:
        return {}
    return {str(k): int(v) for k, v in d.groupby(columna)[UNIDAD].nunique().items()}
