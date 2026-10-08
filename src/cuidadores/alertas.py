"""
Señales del adulto de Cuidadores 360 — funciones puras (spec 6-oct-2026, §5.4 y §5.5).

Las dos señales ya existen como proporciones del marco de cuidadores, calculadas
y SUPRIMIDAS por el pipeline (`estudiantes.supresion.aplicar`, contando
cuidadores distintos):
  · «Ánimo»: la fila «probable (EPDS ≥ 13)» de la familia `EPDS_Total` de
    `scoring.sobre_cortes_cuidador` (cortes anidados con «posible ≥ 10»).
  · «Autolesión»: la familia `EPDS_Autolesion` (ítem 10 distinto de «No, nunca»).

Este módulo no calcula nada nuevo: `tabla(a)` lee esas filas ya suprimidas del
nivel y de los subgrupos y les pone el estado con `estudiantes.alertas.estado`,
que solo mira cifras publicadas (% y n del grupo y del total). Así:
  · nunca hay conteo de casos;
  · el porcentaje solo existe donde la supresión lo dejó (3 ≤ casos ≤ n − 3,
    también por resta) y, si no, el estado es «sin estado»;
  · la autolesión solo tiene la fila del total: nunca por colegio, grado ni
    celda (spec §5.5).

Es puro y liviano (no importa ingesta ni pipeline): lo usan la vista de
comunidad, los informes, la publicación y la lectura.
"""
from __future__ import annotations

import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import alertas as al_est
from src.estudiantes import alertas_catalogo as ac_est
from src.estudiantes import privacidad

TOTAL = al_est.TOTAL
TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
AGRUPACIONES = ("Colegio", "Grado", CRUCE)
COLUMNAS_TABLA = list(al_est.COLUMNAS_TABLA)

# Fila de `cortes` de la que sale cada señal: (clave, indicador o None si es la única).
INDICADOR_PROBABLE = f"Ánimo: probable (EPDS ≥ {cat.EPDS_PROBABLE})"
FUENTES = {cat.ANIMO: ("EPDS_Total", INDICADOR_PROBABLE),
           cat.AUTOLESION: ("EPDS_Autolesion", None)}
# Señales y claves de `cortes` que solo existen en el total del marco.
SOLO_TOTAL = (cat.AUTOLESION,)
CLAVES_SOLO_TOTAL = ("EPDS_Autolesion",)

# Estados: los mismos de estudiantes (mismos colores y textos de estado).
PRIORIDAD, PRESENTE = ac_est.PRIORIDAD, ac_est.PRESENTE
REFERENCIA, SIN_ESTADO = ac_est.REFERENCIA, ac_est.SIN_ESTADO


def _vacio(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or pd.isna(v)


def _num(v):
    return None if _vacio(v) else float(v)


def fila_corte(t, alerta: str) -> dict | None:
    """{n, pct, ic_inf, ic_sup} de la señal en una tabla `cortes`; None si no está."""
    if not isinstance(t, pd.DataFrame) or t.empty or "clave" not in t.columns:
        return None
    clave, indicador = FUENTES[alerta]
    sel = t[t["clave"].astype(str) == clave]
    if indicador is not None and "indicador" in sel.columns:
        sel = sel[sel["indicador"].astype(str) == indicador]
    if sel.empty or _vacio(sel.iloc[0]["n"]):
        return None
    f = sel.iloc[0]
    return dict(n=int(f["n"]), pct=_num(f["pct"]), ic_inf=_num(f.get("ic_inf")),
                ic_sup=_num(f.get("ic_sup")))


def _orden(alerta: str, agrupacion: str, grupo: str) -> tuple:
    grados = list(cat.GRADOS_ESTUDIO)

    def pos(g):
        return (grados.index(g) if g in grados else 99, str(g))
    orden_alerta = list(FUENTES).index(alerta) if alerta in FUENTES else 99
    if agrupacion == TOTAL:
        return (orden_alerta, 0, (0, ""), (0, ""))
    if agrupacion == "Colegio":
        return (orden_alerta, 1, (0, str(grupo)), (0, ""))
    if agrupacion == "Grado":
        return (orden_alerta, 2, pos(grupo), (0, ""))
    colegio, grado = privacidad.partir_celda(grupo)
    return (orden_alerta, 3, (0, colegio), pos(grado))


def ordenar(t: pd.DataFrame) -> pd.DataFrame:
    if t is None or len(t) == 0:
        return pd.DataFrame(columns=COLUMNAS_TABLA)
    claves = [_orden(a, g, str(x)) for a, g, x in zip(t["alerta"], t["agrupacion"], t["grupo"])]
    posiciones = sorted(range(len(t)), key=lambda i: claves[i])
    return t.iloc[posiciones].reset_index(drop=True)[COLUMNAS_TABLA]


def tabla(a) -> pd.DataFrame:
    """Una fila por señal y grupo del marco de cuidadores, sin casos, nunca.

    `a` es el `Analisis` del marco de cuidadores YA suprimido. La autolesión
    solo lleva la fila del total. El estado sale de `estudiantes.alertas.estado`
    con el % y el n publicados del grupo y del total.
    """
    filas: list[dict] = []
    ref: dict[str, tuple] = {}
    for alerta in FUENTES:
        f = fila_corte(getattr(a, "cortes", None), alerta)
        if f is None or f["n"] < cat.MIN_GROUP_N:
            continue
        ref[alerta] = (f["pct"], f["n"])
        filas.append(dict(alerta=alerta, agrupacion=TOTAL, grupo=TODOS, n=f["n"],
                          pct=f["pct"] if f["pct"] is not None else None,
                          ic_inf=f["ic_inf"] if f["pct"] is not None else None,
                          ic_sup=f["ic_sup"] if f["pct"] is not None else None,
                          estado=al_est.estado_total(f["pct"])))
    subgrupos = getattr(a, "subgrupos", None) or {}
    for agrupacion in AGRUPACIONES:
        for grupo, s in (subgrupos.get(agrupacion) or {}).items():
            for alerta in ref:
                if alerta in SOLO_TOTAL:
                    continue
                f = fila_corte(getattr(s, "cortes", None), alerta)
                if f is None or f["n"] < cat.MIN_GROUP_N:
                    continue
                pct_total, n_total = ref[alerta]
                con_cifra = f["pct"] is not None
                filas.append(dict(alerta=alerta, agrupacion=agrupacion, grupo=str(grupo),
                                  n=f["n"], pct=f["pct"] if con_cifra else None,
                                  ic_inf=f["ic_inf"] if con_cifra else None,
                                  ic_sup=f["ic_sup"] if con_cifra else None,
                                  estado=al_est.estado(f["pct"], f["n"], pct_total, n_total)))
    return ordenar(pd.DataFrame(filas, columns=COLUMNAS_TABLA))


def vacia() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNAS_TABLA)
