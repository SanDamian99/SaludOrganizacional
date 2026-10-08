"""
Lo que la comunidad ve y lo que se publica de Cuidadores 360 (fase 4b).

`preparar(ac)` toma el `AnalisisCuidadores` del pipeline (todas las olas) y
devuelve una COPIA lista para la vista de comunidad, los informes y la
publicación. El análisis original (el de la vista de investigadores) no cambia.

Qué cambia en la copia:
  · La autolesión (`EPDS_Autolesion`) sale de las tablas de cada colegio,
    grado y celda: solo queda en el total del marco (spec §5.5).
  · La muestra pierde el reparto por ola: nada se publica por ola.
  · El marco de cuidadores lleva `alertas`, la tabla de las señales del adulto
    (`cuidadores.alertas.tabla`), sin casos.
  · Los ítems del APQ y del estrés parental, que son solo de la vista local de
    investigadores, quedan vacíos.

Quitar cifras nunca abre una resta nueva: lo que queda publicado es un
subconjunto de lo que ya pasó por la supresión. La auditoría
(`cuidadores.auditoria`) se corre sobre esta copia, que es lo que se publica.

No importa ingesta ni pipeline: recibe el objeto ya calculado.
"""
from __future__ import annotations

import copy

import pandas as pd

from src.cuidadores import alertas

CLAVES_MUESTRA_LOCALES = ("ola",)


def _sin_solo_total(s) -> None:
    t = getattr(s, "cortes", None)
    if isinstance(t, pd.DataFrame) and not t.empty and "clave" in t.columns:
        s.cortes = t[~t["clave"].astype(str).isin(alertas.CLAVES_SOLO_TOTAL)].reset_index(
            drop=True)


def preparar(ac):
    """Copia del análisis para la comunidad y la publicación (ver el docstring del módulo)."""
    if getattr(ac, "ola", None):
        raise ValueError("La vista de comunidad y la publicación usan todas las olas: "
                         "la vista de una ola es solo local.")
    out = copy.copy(ac)
    marcos = {}
    for nombre in ("cuidador", "nino"):
        a = copy.deepcopy(getattr(ac, nombre))
        for grupos in (getattr(a, "subgrupos", None) or {}).values():
            for s in grupos.values():
                _sin_solo_total(s)
        a.muestra = {k: v for k, v in (a.muestra or {}).items()
                     if k not in CLAVES_MUESTRA_LOCALES}
        a.alertas = alertas.vacia()
        marcos[nombre] = a
    marcos["cuidador"].alertas = alertas.tabla(marcos["cuidador"])
    out.cuidador, out.nino = marcos["cuidador"], marcos["nino"]
    out.items_apq, out.items_estres = pd.DataFrame(), pd.DataFrame()
    out.flujo_ola = {}
    out.origen = "archivos"
    return out
