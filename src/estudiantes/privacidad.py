"""
Base publicable y auditoría de restas — Estudiantes 360.

La unidad mínima que se publica es la celda colegio × grado con al menos
MIN_GROUP_N estudiantes. Todo agregado publicado (colegio, grado, nivel) se
calcula sobre la unión de esas celdas, para que ningún grupo pequeño pueda
obtenerse restando cifras publicadas (spec del 6-oct-2026, §5.1):

  · colegio = unión de sus celdas; si no tiene ninguna y llega al mínimo, el
    colegio completo;
  · grado   = unión de sus celdas (los colegios pequeños quedan fuera);
  · nivel   = todos, si el resto que no cae en ningún colegio publicado es 0 o
    reúne ≥ MIN_GROUP_N respuestas de ≥ 2 colegios; si no, la unión publicada.

`auditar` comprueba, por indicador, que ninguna resta de un paso entre un
agregado y sus subgrupos publicados deje entre 1 y MIN_GROUP_N − 1 respuestas.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.estudiantes import catalog as cat

SEP = "|"
TODOS = "Todos"
AGRUPACION_CRUCE = "Colegio×Grado"


def clave_celda(colegio, grado) -> str:
    return f"{colegio}{SEP}{grado}"


def partir_celda(clave: str) -> tuple[str, str]:
    colegio, grado = str(clave).split(SEP, 1)
    return colegio, grado


def _union(indices) -> pd.Index:
    salida = pd.Index([])
    for i in indices:
        salida = salida.union(i)
    return salida


def _activo(valor) -> bool:
    return valor not in (TODOS, None, "")


@dataclass
class Base:
    celdas: dict = field(default_factory=dict)     # «LauV|Sexto» → índices
    colegios: dict = field(default_factory=dict)   # «LauV» → índices
    grados: dict = field(default_factory=dict)     # «Sexto» → índices
    nivel: pd.Index = field(default_factory=lambda: pd.Index([]))
    n_total: int = 0
    incluye_resto: bool = True

    @property
    def n_fuera_de_celdas(self) -> int:
        return self.n_total - len(_union(self.celdas.values()))

    def resumen(self) -> dict:
        return dict(n_total=self.n_total, n_nivel=len(self.nivel),
                    n_fuera_de_celdas=self.n_fuera_de_celdas,
                    incluye_resto=self.incluye_resto)


def base_publicable(d: pd.DataFrame, minimo: int = cat.MIN_GROUP_N) -> Base:
    b = Base(n_total=len(d))
    if d.empty or not {"Colegio", "Grado"} <= set(d.columns):
        b.nivel = d.index
        return b
    for (colegio, grado), sub in d.groupby(["Colegio", "Grado"]):
        if len(sub) >= minimo:
            b.celdas[clave_celda(colegio, grado)] = sub.index
    for colegio, sub in d.groupby("Colegio"):
        propias = [i for k, i in b.celdas.items() if partir_celda(k)[0] == str(colegio)]
        if propias:
            b.colegios[str(colegio)] = _union(propias)
        elif len(sub) >= minimo:
            b.colegios[str(colegio)] = sub.index
    for grado in d["Grado"].dropna().unique():
        propias = [i for k, i in b.celdas.items() if partir_celda(k)[1] == str(grado)]
        if propias:
            b.grados[str(grado)] = _union(propias)
    publicado = _union(b.colegios.values())
    resto = d.index.difference(publicado)
    colegios_resto = d.loc[resto, "Colegio"].nunique() if len(resto) else 0
    b.incluye_resto = len(resto) == 0 or (len(resto) >= minimo and colegios_resto >= 2)
    b.nivel = d.index if b.incluye_resto else publicado
    return b


def filas(d: pd.DataFrame, base: Base, colegio=TODOS, grado=TODOS) -> pd.DataFrame:
    """Filas sobre las que se calcula el grupo pedido; vacío si no es publicable."""
    if _activo(colegio) and _activo(grado):
        idx = base.celdas.get(clave_celda(colegio, grado))
    elif _activo(colegio):
        idx = base.colegios.get(str(colegio))
    elif _activo(grado):
        idx = base.grados.get(str(grado))
    else:
        idx = base.nivel
    if idx is None:
        return d.iloc[0:0]
    return d.loc[d.index.intersection(idx)]


def relaciones(base: Base) -> list[tuple[str, pd.Index, list[pd.Index]]]:
    """(nombre del padre, índices del padre, índices de cada hijo publicado)."""
    rel = [("Nivel", base.nivel, list(base.colegios.values())),
           ("Nivel", base.nivel, list(base.grados.values()))]
    for c, idx in base.colegios.items():
        hijos = [i for k, i in base.celdas.items() if partir_celda(k)[0] == c]
        if hijos:
            rel.append((f"Colegio {c}", idx, hijos))
    for g, idx in base.grados.items():
        hijos = [i for k, i in base.celdas.items() if partir_celda(k)[1] == g]
        rel.append((f"Grado {g}", idx, hijos))
    return rel


def auditar(d: pd.DataFrame, base: Base, columnas: list[str],
            minimo: int = cat.MIN_GROUP_N) -> list[str]:
    """Restas que dejarían un grupo de 1 a minimo − 1. Lista vacía = se puede publicar."""
    problemas: list[str] = []
    for col in [None, *columnas]:
        if col is not None and col not in d.columns:
            continue
        validos = d.index if col is None else d.index[d[col].notna()]
        etiqueta = "respuestas" if col is None else col
        for nombre, idx_padre, hijos in relaciones(base):
            padre = idx_padre.intersection(validos)
            if len(padre) < minimo:
                continue
            publicados = [h.intersection(validos) for h in hijos]
            publicados = [h for h in publicados if len(h) >= minimo]
            if not publicados:
                continue
            resto = padre.difference(_union(publicados))
            if 0 < len(resto) < minimo:
                problemas.append(f"{etiqueta}: {nombre} menos sus subgrupos publicados "
                                 f"deja {len(resto)} respuestas")
    return problemas


def columnas_publicadas(a) -> list[str]:
    """Columnas de `a.datos` cuyas cifras salen publicadas por grupo o por nivel."""
    cols = set(a.escalas or [])
    for tabla in (a.cortes, a.bandas, a.items_pssm):
        if tabla is not None and not tabla.empty:
            col = "item" if "item" in tabla.columns else "clave"
            cols.update(str(v) for v in tabla[col])
    for c in a.contrastes or []:
        cols.update([c["resultado"], c["protector"]])
    return sorted(cols)
