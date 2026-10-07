"""
Alertas de grupo de Estudiantes 360 — funciones puras (spec 6-oct-2026, §5.4).

Por estudiante se calcula una señal (1, 0 o faltante) con las reglas de
`alertas_catalogo`. Lo que sale de aquí es siempre por grupo de la base
publicable (privacidad.base_publicable) y nunca lleva el número de casos.

CÓMO SE PROTEGEN LAS CIFRAS
Cada alerta es una proporción binaria más, igual que un corte:
  · La señal es una columna de los datos (`ALERTA_*`): pasa por el todo o nada
    de la fase 1, así que la auditoría de restas de n ya la cubre.
  · `cortes_alerta` arma, para el nivel y para cada subgrupo (colegio, grado,
    celda), una tabla con la forma de `scoring.sobre_cortes`. `supresion.aplicar`
    la trata como una familia más (celdas, colegios, grados, nivel y el resto R):
    supresión primaria 3 ≤ casos ≤ n − 3, complementaria y auditoría exacta de
    sumas y restas. Los grados y las celdas llevan porcentaje cuando la
    supresión lo permite.
  · La desesperanza (regla estricta) implica RCADS 18 ≥ «Con frecuencia», que es
    el corte de la tarjeta de muerte: es un corte ANIDADO en esa familia
    (`ANIDADA`). La supresión la reparte en (n − k₁₈, k₁₈ − k, k) y nunca la
    publica donde el corte del ítem 18 está suprimido.

ESTADO («Prioridad» / «Para tener presente»)
Solo para grupos con porcentaje publicado, y solo con cifras publicadas
(`estado`): el % y el n del grupo y del nivel. El resto del nivel (nivel −
grupo) se deduce de esas cifras, así que el estado no añade información. Si el
porcentaje está suprimido, el estado es neutro («sin estado»).

LO QUE NO SE PUBLICA
La sensibilidad (umbrales 2/3/4 y regla amplia) y la distribución de los ítems
son solo para la vista local de investigadores: no van a Supabase ni al ZIP.
Aun así cumplen la regla: cada reparto anidado se muestra entero o no se
muestra (`supresion.partes_publicables`).

Faltantes: el malestar exige los 6 ítems respondidos; la desesperanza, los de
su regla (16 y 18 la estricta; 1, 4, 16 y 18 la amplia).

Los ítems se leen tal como los codifica `ingest` desde el texto crudo del
formulario (No es cierto = 0 … Muy cierto = 2; Nunca = 0 … Siempre = 3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import privacidad, supresion
from src.estudiantes.stats import wilson

TOTAL = "total"
TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
AGRUPACIONES = ("Colegio", "Grado", CRUCE)

COLUMNAS = {ac.MALESTAR: "ALERTA_malestar", ac.DESESPERANZA: "ALERTA_desesperanza"}
COLUMNA_AMPLIA = "ALERTA_desesperanza_amplia"

# Alerta → familia de `scoring.sobre_cortes` en la que está anidada (alerta ⊆ corte).
ANIDADA = {ac.DESESPERANZA: f"RCADS{ac.ITEM_MUERTE}"}


def columna_malestar(umbral: int) -> str:
    return (COLUMNAS[ac.MALESTAR] if umbral == ac.UMBRAL_MALESTAR
            else f"ALERTA_malestar_{umbral}")


# variante → (alerta, columna, etiqueta, ¿es la vigente?)
VARIANTES: dict[str, tuple[str, str, str, bool]] = {
    **{f"malestar_{u}": (ac.MALESTAR, columna_malestar(u),
                         f"«Muy cierto» en {u} o más de 6", u == ac.UMBRAL_MALESTAR)
       for u in ac.UMBRALES_SENSIBILIDAD},
    "desesperanza_estricta": (ac.DESESPERANZA, COLUMNAS[ac.DESESPERANZA],
                              "Regla estricta", True),
    "desesperanza_amplia": (ac.DESESPERANZA, COLUMNA_AMPLIA, "Regla amplia", False),
}

# Tabla por grupo de cada objeto (nivel y subgrupos), con la forma de sobre_cortes.
# `casos` es interno: lo usa la supresión y nunca se publica.
COLUMNAS_CORTES = ["clave", "indicador", "anidada_en", "n", "casos", "pct", "ic_inf",
                   "ic_sup"]
# Tabla plana que leen las vistas y que se publica. Sin casos, nunca.
COLUMNAS_TABLA = ["alerta", "agrupacion", "grupo", "n", "pct", "ic_inf", "ic_sup", "estado"]
COLUMNAS_SENSIBILIDAD = ["alerta", "variante", "etiqueta", "vigente", "n", "pct",
                         "ic_inf", "ic_sup"]
COLUMNAS_ITEMS = ["alerta", "item", "enunciado", "respuesta", "n", "pct"]

ETIQUETAS_RESPUESTA = {
    "SDQ": ("No es cierto", "Algo cierto", "Muy cierto"),
    "RCADS": ("Nunca", "Algunas veces", "Con frecuencia", "Siempre"),
}


# ── Señal por estudiante ─────────────────────────────────────────────────────
def _columnas(escala: str, items) -> list[str]:
    return [f"{escala}{i}" for i in items]


def senal_malestar(d: pd.DataFrame, umbral: int = ac.UMBRAL_MALESTAR) -> pd.Series:
    """1.0 si «Muy cierto» en ≥ `umbral` de los 6 ítems; 0.0 si no; NaN si falta alguno."""
    cols = _columnas("SDQ", ac.ALERTAS[ac.MALESTAR].items)
    if not set(cols) <= set(d.columns):
        return pd.Series(np.nan, index=d.index, dtype=float)
    X = d[cols]
    completos = X.notna().all(axis=1)
    return ((X == ac.MUY_CIERTO).sum(axis=1) >= umbral).astype(float).where(completos)


def senal_desesperanza(d: pd.DataFrame, amplia: bool = False) -> pd.Series:
    """Regla estricta (vigente) o amplia (sensibilidad); NaN si falta un ítem de la regla."""
    cols = _columnas("RCADS", ac.ITEMS_REGLA_AMPLIA if amplia else ac.ITEMS_REGLA_ESTRICTA)
    if not set(cols) <= set(d.columns):
        return pd.Series(np.nan, index=d.index, dtype=float)
    completos = d[cols].notna().all(axis=1)
    muerte = d[f"RCADS{ac.ITEM_MUERTE}"]
    valia = d[f"RCADS{ac.ITEM_VALIA}"]
    if amplia:
        otros = pd.concat([d[f"RCADS{i}"] >= ac.CON_FRECUENCIA for i in ac.ITEMS_AMPLIA],
                          axis=1).any(axis=1)
        si = (muerte >= ac.CON_FRECUENCIA) | ((valia >= ac.CON_FRECUENCIA) & otros)
    else:
        si = (muerte == ac.SIEMPRE) | ((muerte >= ac.CON_FRECUENCIA)
                                       & (valia >= ac.CON_FRECUENCIA))
    return si.astype(float).where(completos)


def marcar(d: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Copia de `d` con una columna por señal y variante (1 / 0 / NaN). No toca nada más.

    Estas columnas son individuales: viven solo en `Analisis.datos`, que nunca
    se publica ni se exporta.
    """
    nuevas: dict[str, pd.Series] = {}
    malestar = ac.ALERTAS[ac.MALESTAR]
    if nivel in malestar.niveles and set(_columnas("SDQ", malestar.items)) <= set(d.columns):
        for u in ac.UMBRALES_SENSIBILIDAD:
            nuevas[columna_malestar(u)] = senal_malestar(d, u)
    if nivel in ac.ALERTAS[ac.DESESPERANZA].niveles:
        if set(_columnas("RCADS", ac.ITEMS_REGLA_ESTRICTA)) <= set(d.columns):
            nuevas[COLUMNAS[ac.DESESPERANZA]] = senal_desesperanza(d)
        if set(_columnas("RCADS", ac.ITEMS_REGLA_AMPLIA)) <= set(d.columns):
            nuevas[COLUMNA_AMPLIA] = senal_desesperanza(d, amplia=True)
    base = d.drop(columns=[c for c in nuevas if c in d.columns])
    if not nuevas:
        return base.copy()
    return pd.concat([base, pd.DataFrame(nuevas, index=d.index)], axis=1)


def claves_del_nivel(d: pd.DataFrame, nivel: str) -> list[str]:
    """Alertas que aplican al nivel y tienen alguna señal válida en `d`."""
    return [k for k, x in ac.ALERTAS.items()
            if nivel in x.niveles and COLUMNAS[k] in d.columns and d[COLUMNAS[k]].notna().any()]
