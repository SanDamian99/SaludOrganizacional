"""
Auditoría de lo que se publica de Cuidadores 360 (fase 4b, spec §4, §5.1 y §5.4).

Es la misma auditoría que corre estudiantes antes de publicar o de escribir un
informe (`estudiantes.publicar.verificar_restas`), adaptada a cuidadores:

  1. `auditar_restas`: ninguna resta de un paso entre un agregado y sus
     subgrupos publicados (nivel − colegios, nivel − grados, colegio − celdas,
     grado − celdas) deja de 1 a 9 CUIDADORES DISTINTOS, por indicador. En el
     marco de niños cuenta cuidadores, no filas (spec §4).
  2. `auditar_cifras`: recalcula desde los datos enmascarados, con la
     puntuación de cuidadores, el reparto de cada indicador en cada átomo de la
     base y comprueba que cada proporción publicada (también la de cada
     colegio, grado y celda) tiene de 3 a n − 3 casos, que ninguna suma o resta
     de lo publicado deja un conjunto que no cumpla (`supresion.fugas`) y, en
     el marco de niños, que los casos y los no casos vienen de 3 o más
     cuidadores distintos (`pipeline.regla_cuidadores_distintos`).
  3. `auditar_solo_total`: la autolesión no aparece en ningún grupo, ni en las
     tablas ni en las señales del adulto.

Se corre sobre lo que de verdad se publica: la copia de `comunidad.preparar`.
Los mensajes nombran marco, grupo e indicador; nunca cifras de personas.
"""
from __future__ import annotations

import pandas as pd

from src.cuidadores import alertas
from src.cuidadores import catalog as cat
from src.cuidadores import pipeline, privacidad, scoring
from src.estudiantes import privacidad as priv
from src.estudiantes import supresion

UNIDAD = privacidad.UNIDAD


def _distintos(d: pd.DataFrame, idx) -> int:
    return int(d.loc[idx, UNIDAD].nunique()) if len(idx) else 0


def auditar_restas(d: pd.DataFrame, base, columnas: list[str],
                   minimo: int = cat.MIN_GROUP_N) -> list[str]:
    """Restas de un paso que dejarían de 1 a minimo − 1 cuidadores distintos."""
    priv._exigir_indice_unico(d)
    problemas: list[str] = []
    for col in [None, *columnas]:
        if col is not None and col not in d.columns:
            continue
        validos = d.index if col is None else d.index[d[col].notna()]
        etiqueta = "respuestas" if col is None else col
        for nombre, idx_padre, hijos in priv.relaciones(base):
            padre = idx_padre.intersection(validos)
            if _distintos(d, padre) < minimo:
                continue
            publicados = [h.intersection(validos) for h in hijos]
            publicados = [h for h in publicados if _distintos(d, h) >= minimo]
            if not publicados:
                continue
            resto = padre.difference(priv.union(publicados))
            n = _distintos(d, resto)
            if 0 < n < minimo:
                problemas.append(f"{etiqueta}: {nombre} menos sus subgrupos publicados "
                                 f"deja menos de {minimo} cuidadores distintos")
    return problemas


def _familias(sub: pd.DataFrame, marco: str) -> dict:
    if sub.empty:
        return {}
    if marco == cat.MARCO_NINO:
        return supresion.partes_por_familia(scoring.sobre_cortes_nino(sub),
                                            scoring.bandas_nino(sub))
    return supresion.partes_por_familia(scoring.sobre_cortes_cuidador(sub), None)


def fugas(jer, partes: dict, pub: set, minimo: int, extra=None) -> list[frozenset]:
    """`supresion.fugas`, exacta también cuando solo se publica el total.

    Con un único agregado publicado (el total, como la autolesión) lo único que
    se deduce es ese mismo total: el espacio generado es una sola recta y un
    conjunto de átomos con indicador 0/1 en ella es vacío o el total entero.
    `supresion.fugas` no lo enumera cuando el total tiene más de MAX_ENUMERAR
    átomos y lo da por hallazgo (falla cerrado); aquí se comprueba directamente.
    """
    if pub and pub <= {supresion.NIVEL}:
        atomos = jer.grupos[supresion.NIVEL]
        largo = max((len(p) for p in partes.values()), default=2)
        return [] if supresion._seguro(atomos, partes, largo, minimo, extra) else [atomos]
    return supresion.fugas(jer, partes, pub, minimo, extra=extra)


def auditar_cifras(a, minimo: int = supresion.MIN_CASOS) -> list[str]:
    """Proporciones publicadas que delatan, recalculadas desde `a.datos` y `a.base`."""
    base, d = getattr(a, "base", None), getattr(a, "datos", None)
    if base is None or d is None or d.empty:
        return []
    jer = supresion.jerarquia(list(base.celdas), list(base.colegios), list(base.grados),
                              con_resto=base.incluye_resto)
    indices = supresion.indices_atomos(base)
    fam = {at: _familias(d.loc[d.index.intersection(idx)], a.nivel)
           for at, idx in indices.items()}
    objs = supresion._objetos(a)
    claves = sorted({c for f in fam.values() for c in f})
    reglas = (pipeline.regla_cuidadores_distintos(d, base, claves, minimo)
              if a.nivel == cat.MARCO_NINO else {})
    problemas: list[str] = []
    for clave in claves:
        largo = max(len(f[clave]) for f in fam.values() if clave in f)
        partes = {at: f.get(clave, (0,) * largo) for at, f in fam.items()}
        extra = reglas.get(clave)
        pub = {g for g, o in objs.items() if supresion._publicado(o, clave)}
        for g in sorted(pub, key=str):
            if g not in jer.grupos:
                problemas.append(f"{clave}: {g[0]} {g[1]} publicado fuera de la base")
                continue
            atomos = jer.grupos[g]
            if not supresion.partes_publicables(supresion._suma(atomos, partes, largo), minimo):
                problemas.append(f"{clave}: {g[0]} {g[1] or ''} publica una proporción con "
                                 f"menos de {minimo} casos o no casos")
            elif extra is not None and not extra(frozenset(atomos)):
                problemas.append(f"{clave}: {g[0]} {g[1] or ''} publica una proporción cuyos "
                                 f"casos o no casos vienen de menos de {minimo} cuidadores")
        for s in fugas(jer, partes, pub & set(jer.grupos), minimo, extra=extra):
            problemas.append(f"{clave}: una resta entre cifras publicadas deja un conjunto de "
                             f"{len(s)} grupo(s) con menos de {minimo} casos o no casos")
    return problemas


def auditar_solo_total(a) -> list[str]:
    """La autolesión solo en el total: ni en subgrupos ni en las señales por grupo."""
    problemas: list[str] = []
    for agrupacion, grupos in (getattr(a, "subgrupos", None) or {}).items():
        for grupo, s in grupos.items():
            t = getattr(s, "cortes", None)
            if (isinstance(t, pd.DataFrame) and not t.empty and "clave" in t.columns
                    and t["clave"].astype(str).isin(alertas.CLAVES_SOLO_TOTAL).any()):
                problemas.append(f"autolesión: {agrupacion} {grupo} la publica por grupo")
    t = getattr(a, "alertas", None)
    if isinstance(t, pd.DataFrame) and not t.empty:
        malas = t[t["alerta"].isin(alertas.SOLO_TOTAL) & (t["agrupacion"] != alertas.TOTAL)]
        if len(malas):
            problemas.append("autolesión: la tabla de señales la trae por grupo")
    return problemas


def auditar(marcos: dict) -> list[str]:
    """Todas las auditorías de cada marco con datos. Lista vacía = se puede publicar."""
    problemas: list[str] = []
    for marco, a in (marcos or {}).items():
        if a is None:
            continue
        problemas += [f"{marco} · {p}" for p in auditar_solo_total(a)]
        if getattr(a, "base", None) is None or a.datos is None or a.datos.empty:
            continue
        problemas += [f"{marco} · {p}" for p in
                      auditar_restas(a.datos, a.base, privacidad.columnas_de_analisis(a.datos))]
        problemas += [f"{marco} · {p}" for p in auditar_cifras(a)]
    return problemas
