"""
Auditoría de restas entre vistas para la capa 1 de la triangulación.

Junta, por constructo, los conjuntos de filas cuyas cifras muestra la capa 1
(grupo y resto de cada colegio y grado, y el total del actor) con los que
publica el módulo de origen (estudiantes por nivel; cuidadores en su marco
completo), ya con su todo o nada. Parte las filas válidas en piezas por su
firma (en qué conjuntos cae) y cuenta las piezas con 1 a 9 unidades que son
combinación lineal de los conjuntos: esas se deducirían sumando y restando
cifras publicadas. Solo devuelve conteos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.cuidadores import privacidad as priv_cuid
from src.estudiantes import privacidad as priv_est
from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat


def conjuntos_capa1(d: pd.DataFrame, lista, c: cat.Constructo, grupos: dict) -> list[pd.Index]:
    """Filas con dato detrás de cada cifra mostrada (n_grupo, n_resto y DE del actor)."""
    ok = [a for a in lista if c1._atomo_ok(d, a, c.marco, c)]
    v = d[c.columna]

    def validas(atomos):
        idx = priv_est.union(a.idx for a in atomos)
        return idx[v.loc[idx].notna().to_numpy()] if len(idx) else pd.Index([])

    salida = [validas(ok)]
    for agrupacion, nombres in grupos.items():
        for g in nombres:
            propios = [a for a in ok if c1._del_grupo(a, agrupacion, g)]
            otros = [a for a in ok if not c1._del_grupo(a, agrupacion, g)]
            if propios:
                salida += [validas(propios), validas(otros)]
    return salida


def conjuntos_modulo(d: pd.DataFrame, marco: str, columna: str) -> list[pd.Index]:
    """Filas con dato detrás de cada cifra del módulo de origen, tras su todo o nada."""
    if marco == cat.ESTUDIANTE:
        partes = ([g for _, g in d.groupby("nivel")] if "nivel" in d.columns else [d])
        priv = priv_est
    else:
        partes, priv = [d], priv_cuid
    salida = []
    for g in partes:
        base = priv.base_publicable(g)
        dm, _ = priv.aplicar_todo_o_nada(g, base, [columna])
        validas = dm.index[dm[columna].notna().to_numpy()]
        for idx in [base.nivel, *base.colegios.values(), *base.grados.values(),
                    *base.celdas.values()]:
            salida.append(pd.Index(idx).intersection(validas))
    return salida


def piezas_deducibles(d: pd.DataFrame, conjuntos: list[pd.Index], unidad: str | None) -> int:
    """Piezas con 1 a 9 unidades que son combinación lineal de los conjuntos."""
    filas = priv_est.union(conjuntos)
    if not len(filas):
        return 0
    M = np.column_stack([np.isin(filas, idx).astype(float) for idx in conjuntos])
    firmas = pd.Series(["".join(map(str, r)) for r in M.astype(int)], index=range(len(filas)))
    unidades = d.loc[filas, unidad].to_numpy() if unidad else np.asarray(filas)
    deducibles = 0
    for firma, pos in firmas.groupby(firmas).groups.items():
        pos = np.asarray(pos)
        n = len(set(unidades[pos]))
        if "1" not in firma or not 0 < n < cat.MIN_GROUP_N:
            continue
        t = np.zeros(len(filas))
        t[pos] = 1
        x, *_ = np.linalg.lstsq(M, t, rcond=None)
        if np.allclose(M @ x, t, atol=1e-6):
            deducibles += 1
    return deducibles


def auditar_capa1(tablas: dict, capa) -> dict:
    """{clave del constructo: piezas deducibles} para estudiantes y cuidadores."""
    por_marco = {m: c1.atomos(tablas[m], m) for m in cat.MARCOS_GRADO}
    salida = {}
    for c in cat.CONSTRUCTOS:
        if c.marco not in cat.MARCOS_GRADO or c.columna not in tablas[c.marco].columns:
            continue
        d = tablas[c.marco]
        grupos = {"Colegio": capa.colegios, "Grado": capa.grados}
        conjuntos = (conjuntos_capa1(d, por_marco[c.marco], c, grupos)
                     + conjuntos_modulo(d, c.marco, c.columna))
        salida[c.clave] = piezas_deducibles(d, conjuntos, cat.UNIDAD[c.marco])
    return salida
