"""
Capa 1 de la triangulación — por colegio (y por grado), spec §5.6.

Para cada actor y constructo: la diferencia del grupo (colegio o grado) frente
al resto del municipio del MISMO actor, en unidades de la DE individual del
actor, con su IC del 95 %:

    d = (media del grupo − media del resto) / DE del actor
    IC = d ± 1,96 · √(s²_grupo / n_grupo + s²_resto / n_resto) / DE del actor

Qué entra:
  · Colegios publicables (§5.1) en estudiantes, cuidadores y docentes a la
    vez: con los datos de octubre de 2026, LauV, JJC, SJMEB y La Balsa.
  · Cuidadores: solo los de niños en los grados del estudio (marcos cuidador
    y niño). En los dos, el mínimo cuenta cuidadores distintos.
  · Por grado: solo estudiantes y cuidadores (los docentes no tienen grado).

Cifras que no delatan, tampoco junto a lo que publica cada módulo. Cada marco
se parte en ÁTOMOS que son EXACTAMENTE las unidades de la base publicable de
su módulo (§5.1): estudiantes por nivel, como `estudiantes.pipeline` (celdas
colegio × grado con 10 o más, colegios publicados enteros y el R de cada nivel
solo si ese nivel lo incluye); cuidadores y niños sobre el marco completo,
como `cuidadores.pipeline`, y después el filtro de grados quita átomos enteros
(los que tienen alguna fila fuera de los grados del estudio). En docentes,
sin módulo publicado, los átomos son los colegios con 10 o más y R. Colegios,
grados y «resto del municipio» son uniones de átomos del módulo, así que toda
suma o resta de cifras mostradas aquí o en el módulo también lo es. Por
constructo, un átomo con 1 a 9 unidades con dato sale (todo o nada, igual que
el todo o nada del módulo), y en un constructo binario también si tiene menos
de 3 casos o no casos (filas o unidades).

Clasificación (solo pares del mismo objeto): «tensión» si los dos IC excluyen
el cero en direcciones opuestas (orientadas: positivo = mejor que el resto),
«coincidencia» si lo excluyen en la misma, y si no «sin diferencia clara».
Los demás pares son «co-ocurrencia».
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.cuidadores import privacidad as priv_cuid
from src.estudiantes import privacidad as priv_est
from src.triangulacion import catalogo as cat
from src.triangulacion.estadistica import Z95, partes_seguras

RESTO = "__resto__"
COLUMNAS_DIFERENCIAS = ["agrupacion", "grupo", "clave", "actor", "constructo", "objeto",
                        "binario", "n_grupo", "n_resto", "media_grupo", "media_resto",
                        "de_actor", "d", "ic_inf", "ic_sup", "d_orientada", "motivo"]
COLUMNAS_CLASIFICACION = ["agrupacion", "grupo", "par", "tipo", "a", "d_a", "ic_a", "b",
                          "d_b", "ic_b", "clasificacion"]
MOTIVO_POCOS = "menos de 10 con dato o cifras pequeñas"
MOTIVO_RESTO = "el resto no llega a 10"


@dataclass(frozen=True)
class Atomo:
    nombre: str
    colegio: str | None
    grado: str | None
    idx: pd.Index


@dataclass
class Capa1:
    colegios: list = field(default_factory=list)
    grados: list = field(default_factory=list)
    conteos: dict = field(default_factory=dict)          # {marco: {colegio: n unidades}}
    diferencias: pd.DataFrame = field(default_factory=pd.DataFrame)
    clasificacion: pd.DataFrame = field(default_factory=pd.DataFrame)
    por_grado: pd.DataFrame = field(default_factory=pd.DataFrame)
    clasificacion_grado: pd.DataFrame = field(default_factory=pd.DataFrame)


def _unidades(d: pd.DataFrame, marco: str) -> pd.Series:
    col = cat.UNIDAD[marco]
    return d[col] if col else pd.Series(d.index, index=d.index)


def n_unidades(d: pd.DataFrame, marco: str) -> int:
    return int(_unidades(d, marco).nunique()) if len(d) else 0


def marcos(fuentes) -> dict:
    """Las tablas de cada marco, como las recibe su módulo (índice 0..n−1).

    Cuidadores y niños NO se filtran por grado aquí: la base publicable se arma
    sobre el marco completo, como en `cuidadores.pipeline.analizar`, y el filtro
    de los grados del estudio quita átomos enteros (`atomos`).
    """
    return {m: fuentes.marco(m).reset_index(drop=True)
            for m in (cat.ESTUDIANTE, cat.CUIDADOR, cat.NINO, cat.DOCENTE)}


def conteos_por_colegio(tablas: dict) -> dict:
    """{marco: {colegio: unidades}}; sin colegio cuenta como SIN_DATO (suma = total)."""
    return {m: {str(c): n_unidades(g, m) for c, g in
                d.groupby(d["Colegio"].fillna(cat.COLEGIOS_SIN_GRUPO[-1]))}
            for m, d in tablas.items()}


def _resto_suficiente(d: pd.DataFrame, idx, marco: str) -> bool:
    if len(idx) == 0:
        return False
    if marco in (cat.CUIDADOR, cat.NINO):
        return priv_cuid._resto_suficiente(d, idx, cat.MIN_GROUP_N)
    return priv_est._resto_suficiente(d.loc[idx, "Colegio"], cat.MIN_GROUP_N)


def _atomos_de_base(d: pd.DataFrame, base) -> list[Atomo]:
    """Unidades de una base publicable (celdas y colegios enteros) y su R si entra."""
    salida: list[Atomo] = []
    for nombre, idx in priv_est.unidades(base):
        if priv_est.SEP in str(nombre):
            colegio, grado = priv_est.partir_celda(nombre)
        else:
            colegio, grado = str(nombre), None
        salida.append(Atomo(str(nombre), colegio, grado, idx))
    if base.incluye_resto:
        resto = base.nivel.difference(priv_est.union(a.idx for a in salida))
        if len(resto):
            salida.append(Atomo(RESTO, None, None, resto))
    return salida


def atomos(d: pd.DataFrame, marco: str) -> list[Atomo]:
    """Átomos de un marco: exactamente las unidades que publica su módulo.

    · Estudiantes: la base de `estudiantes.privacidad` POR NIVEL, como
      `estudiantes.pipeline.analizar` (celdas, colegios enteros y el R de cada
      nivel solo si ese nivel lo incluye).
    · Cuidadores y niños: la base de `cuidadores.privacidad` sobre el marco
      completo, como `cuidadores.pipeline.analizar`; después el filtro de los
      grados del estudio deja solo los átomos con todas sus filas en esos
      grados (un átomo entra o sale entero, nunca se recorta).
    · Docentes (sin módulo publicado): los colegios con 10 o más y R.
    Así todo conjunto de la capa 1 es unión de átomos del módulo.
    """
    if marco == cat.DOCENTE:
        salida: list[Atomo] = []
        for colegio, g in d.groupby("Colegio"):
            if colegio not in cat.COLEGIOS_SIN_GRUPO and len(g) >= cat.MIN_GROUP_N:
                salida.append(Atomo(str(colegio), str(colegio), None, g.index))
        resto = d.index.difference(priv_est.union(a.idx for a in salida))
        if _resto_suficiente(d, resto, marco):
            salida.append(Atomo(RESTO, None, None, resto))
        return salida
    if marco in (cat.CUIDADOR, cat.NINO):
        lista = _atomos_de_base(d, priv_cuid.base_publicable(d))
        return [a for a in lista if d.loc[a.idx, "Grado"].notna().all()]
    partes = ([g for _, g in d.groupby("nivel", sort=True)] if "nivel" in d.columns else [d])
    salida = []
    for g in partes:
        salida += _atomos_de_base(g, priv_est.base_publicable(g))
    return salida


def _atomo_ok(d: pd.DataFrame, a: Atomo, marco: str, c: cat.Constructo) -> bool:
    """Un átomo sin datos no aporta; con 1 a 9 (o < 3 casos o no casos) sale."""
    validas = a.idx[d.loc[a.idx, c.columna].notna().to_numpy()]
    if len(validas) == 0:
        return False
    sub = d.loc[validas]
    if a.nombre == RESTO:
        ok = _resto_suficiente(d, validas, marco)
    else:
        ok = n_unidades(sub, marco) >= cat.MIN_GROUP_N
    if ok and c.binario:
        unidades = _unidades(sub, marco) if cat.UNIDAD[marco] else None
        ok = partes_seguras(sub[c.columna], unidades, [1.0])
    return ok


def _fila(agrupacion, grupo, c: cat.Constructo, **valores) -> dict:
    fila = dict(agrupacion=agrupacion, grupo=grupo, clave=c.clave, actor=cat.ACTOR[c.marco],
                constructo=c.etiqueta, objeto=c.objeto, binario=c.binario)
    for k in COLUMNAS_DIFERENCIAS:
        fila.setdefault(k, valores.get(k, np.nan))
    fila["motivo"] = valores.get("motivo", "")
    return fila


def _del_grupo(a: Atomo, agrupacion: str, grupo: str) -> bool:
    return (a.colegio if agrupacion == "Colegio" else a.grado) == grupo


def diferencias_constructo(d: pd.DataFrame, lista: list[Atomo], c: cat.Constructo,
                           grupos: list, agrupacion: str) -> list[dict]:
    """Filas de `diferencias` de un constructo para cada grupo pedido."""
    if c.columna not in d.columns:
        return [_fila(agrupacion, g, c, motivo=MOTIVO_POCOS) for g in grupos]
    ok = [a for a in lista if _atomo_ok(d, a, c.marco, c)]
    v = d[c.columna].astype(float)

    def valores(atomos_: list[Atomo]) -> pd.Series:
        idx = priv_est.union(a.idx for a in atomos_)
        return v.loc[idx].dropna() if len(idx) else v.iloc[0:0]

    de = float(valores(ok).std(ddof=1)) if ok else float("nan")
    escala, dec = (100.0, 1) if c.binario else (1.0, 2)
    filas = []
    for g in grupos:
        propios = [a for a in ok if _del_grupo(a, agrupacion, g)]
        if not propios:
            filas.append(_fila(agrupacion, g, c, motivo=MOTIVO_POCOS))
            continue
        otros = [a for a in ok if not _del_grupo(a, agrupacion, g)]
        x, y = valores(propios), valores(otros)
        sub_resto = d.loc[y.index]
        if n_unidades(sub_resto, c.marco) < cat.MIN_GROUP_N or not de > 0:
            filas.append(_fila(agrupacion, g, c, motivo=MOTIVO_RESTO))
            continue
        dif = (x.mean() - y.mean()) / de
        se = np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y)) / de
        filas.append(_fila(
            agrupacion, g, c, n_grupo=len(x), n_resto=len(y),
            media_grupo=round(escala * x.mean(), dec), media_resto=round(escala * y.mean(), dec),
            de_actor=round(escala * de, dec), d=round(dif, 3),
            ic_inf=round(dif - Z95 * se, 3), ic_sup=round(dif + Z95 * se, 3),
            d_orientada=round(c.direccion * dif, 3)))
    return filas


def diferencias(tablas: dict, atomos_por_marco: dict, constructos, grupos: list,
                agrupacion: str) -> pd.DataFrame:
    filas = []
    for c in constructos:
        filas += diferencias_constructo(tablas[c.marco], atomos_por_marco[c.marco], c,
                                        grupos, agrupacion)
    return pd.DataFrame(filas, columns=COLUMNAS_DIFERENCIAS)


def _orientado(fila) -> tuple[float, float]:
    c = cat.POR_CLAVE[fila["clave"]]
    lo, hi = c.direccion * fila["ic_inf"], c.direccion * fila["ic_sup"]
    return min(lo, hi), max(lo, hi)


def _signo(lo: float, hi: float) -> int:
    return 1 if lo > 0 else (-1 if hi < 0 else 0)


def clasificar(par: cat.Par, fila_a, fila_b) -> str:
    if par.tipo == cat.COOCURRENCIA:
        return cat.COOCURRENCIA
    if fila_a is None or fila_b is None or pd.isna(fila_a["d"]) or pd.isna(fila_b["d"]):
        return cat.SIN_DATO
    sa, sb = _signo(*_orientado(fila_a)), _signo(*_orientado(fila_b))
    if sa == 0 or sb == 0:
        return cat.SIN_DIFERENCIA
    return cat.COINCIDENCIA if sa == sb else cat.TENSION


def _ic(fila) -> str:
    if fila is None or pd.isna(fila["d"]):
        return "—"
    return f"[{fila['ic_inf']:.2f}; {fila['ic_sup']:.2f}]"


def clasificacion(dif: pd.DataFrame, pares=cat.PARES) -> pd.DataFrame:
    if dif.empty:
        return pd.DataFrame(columns=COLUMNAS_CLASIFICACION)
    filas = []
    for (agrupacion, grupo), sub in dif.groupby(["agrupacion", "grupo"], sort=False):
        por_clave = {r["clave"]: r for _, r in sub.iterrows()}
        for par in pares:
            if par.a not in por_clave or par.b not in por_clave:
                continue
            fa, fb = por_clave[par.a], por_clave[par.b]
            filas.append(dict(
                agrupacion=agrupacion, grupo=grupo, par=par.titulo, tipo=par.tipo,
                a=cat.POR_CLAVE[par.a].etiqueta, d_a=fa["d"], ic_a=_ic(fa),
                b=cat.POR_CLAVE[par.b].etiqueta, d_b=fb["d"], ic_b=_ic(fb),
                clasificacion=clasificar(par, fa, fb)))
    return pd.DataFrame(filas, columns=COLUMNAS_CLASIFICACION)


def _grupos(lista: list[Atomo], agrupacion: str) -> set:
    return {(a.colegio if agrupacion == "Colegio" else a.grado) for a in lista} - {None}


def analizar(fuentes) -> Capa1:
    tablas = marcos(fuentes)
    por_marco = {m: atomos(d, m) for m, d in tablas.items()}
    colegios = sorted(set.intersection(*(_grupos(por_marco[m], "Colegio")
                                          for m in (cat.ESTUDIANTE, cat.CUIDADOR, cat.DOCENTE))))
    from src.cuidadores import catalog as cat_cuid
    en_todos = set.intersection(*(_grupos(por_marco[m], "Grado") for m in cat.MARCOS_GRADO))
    grados = [g for g in cat_cuid.GRADOS_ESTUDIO if g in en_todos]
    dif = diferencias(tablas, por_marco, cat.CONSTRUCTOS, colegios, "Colegio")
    en_grado = [c for c in cat.CONSTRUCTOS if c.marco in cat.MARCOS_GRADO]
    dif_g = diferencias(tablas, por_marco, en_grado, grados, "Grado")
    return Capa1(colegios=colegios, grados=grados, conteos=conteos_por_colegio(tablas),
                 diferencias=dif, clasificacion=clasificacion(dif), por_grado=dif_g,
                 clasificacion_grado=clasificacion(dif_g))
