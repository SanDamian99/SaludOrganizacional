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

Además, el resto R solo entra en el nivel si, quitando su colegio más grande,
quedan al menos MARGEN_RESTO respuestas (que no sea casi un colegio solo).

Unidades. Las celdas publicables y los colegios «completos» (sin celdas
publicables pero con ≥ MIN_GROUP_N filas) son las unidades; R es una unidad
más cuando el nivel lo incluye. Todo agregado publicado es una unión de
unidades.

Todo o nada por indicador. Que una unidad tenga ≥ MIN_GROUP_N filas no basta:
si para un indicador tiene de 1 a MIN_GROUP_N − 1 respuestas válidas, una
cadena de restas (p. ej. colegio X + colegio Y − grado A − grado B) puede
aislarlas aunque ninguna resta de un paso lo haga. `aplicar_todo_o_nada`
borra, columna por columna, los valores de toda unidad (o de R) que no llegue
al mínimo de respuestas válidas. Después, cada cifra publicada de un
indicador c es la suma sobre unidades con 0 o ≥ MIN_GROUP_N valores válidos
de c; cualquier combinación de sumas y restas de cifras publicadas es, a lo
sumo, una unión de esas unidades, así que nunca deja de 1 a MIN_GROUP_N − 1.

`auditar` comprueba, por indicador, que ninguna resta de un paso entre un
agregado y sus subgrupos publicados deje entre 1 y MIN_GROUP_N − 1 respuestas;
sobre datos ya enmascarados es un control de coherencia.

Alcance. La garantía es por columna. Las cifras de dos columnas (contrastes
`stats.contraste_protector` y modelos `stats.modelo`) usan solo las filas con
ambas respondidas, y ese conjunto de pares no se audita. El riesgo práctico es
bajo: los contrastes exigen ≥ 30 pares completos y recalculan los terciles en
cada grupo, y los modelos solo se publican para el nivel, así que una resta
entre dos de esas cifras no devuelve las respuestas de un grupo pequeño.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.estudiantes import catalog as cat

SEP = "|"
TODOS = "Todos"
AGRUPACION_CRUCE = "Colegio×Grado"
MARGEN_RESTO = 3       # R sin su colegio más grande debe conservar al menos esto
COLUMNAS_ID = ("ID", "Edad", "Sexo", "Grado", "Colegio", "Colegio_nombre",
               "Sede", "ts", "nivel")


def _exigir_indice_unico(d: pd.DataFrame) -> None:
    if not d.index.is_unique:
        raise ValueError("El índice de los datos tiene etiquetas repetidas; la base "
                         "publicable se arma sobre etiquetas de fila y saldría mal. "
                         "Use d.reset_index(drop=True) antes.")


def columnas_de_analisis(d: pd.DataFrame) -> list[str]:
    """Columnas con cifras: todas menos identificación/metadatos y las «_…»."""
    return [c for c in d.columns
            if c not in COLUMNAS_ID and not str(c).startswith("_")]


def _resto_suficiente(colegios: pd.Series, minimo: int) -> bool:
    """R entra si tiene ≥ minimo, de ≥ 2 colegios y sin un colegio dominante."""
    n = len(colegios)
    if n < minimo:
        return False
    conteo = colegios.value_counts()
    return len(conteo) >= 2 and n - int(conteo.iloc[0]) >= MARGEN_RESTO


def clave_celda(colegio, grado) -> str:
    return f"{colegio}{SEP}{grado}"


def partir_celda(clave: str) -> tuple[str, str]:
    colegio, grado = str(clave).split(SEP, 1)
    return colegio, grado


def union(indices) -> pd.Index:
    """Unión de varios índices de fila, conservando el tipo (int64 sigue int64)."""
    lista = list(indices)
    if not lista:
        return pd.Index([])
    salida = lista[0][:0]            # vacío del mismo tipo: int64 sigue int64
    for i in lista:
        salida = salida.union(i)
    return salida


def activo(valor) -> bool:
    """¿El filtro tiene un valor elegido (no «Todos», vacío ni None)?"""
    return valor not in (TODOS, None, "")


# Nombres antiguos, privados; se conservan por compatibilidad.
_union = union
_activo = activo


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
        return self.n_total - len(union(self.celdas.values()))

    def resumen(self) -> dict:
        """Tamaños de la base. De las respuestas fuera de celdas publicables,
        `n_fuera_del_nivel` no entran en ninguna cifra y `n_solo_en_total` solo
        en el nivel; el resto son de colegios publicados enteros (sin celdas)."""
        return dict(n_total=self.n_total, n_nivel=len(self.nivel),
                    n_fuera_de_celdas=self.n_fuera_de_celdas,
                    n_fuera_del_nivel=self.n_total - len(self.nivel),
                    n_solo_en_total=len(self.nivel.difference(
                        union(self.colegios.values()))),
                    incluye_resto=self.incluye_resto)


def base_publicable(d: pd.DataFrame, minimo: int = cat.MIN_GROUP_N) -> Base:
    _exigir_indice_unico(d)
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
            b.colegios[str(colegio)] = union(propias)
        elif len(sub) >= minimo:
            b.colegios[str(colegio)] = sub.index
    for grado in d["Grado"].dropna().unique():
        propias = [i for k, i in b.celdas.items() if partir_celda(k)[1] == str(grado)]
        if propias:
            b.grados[str(grado)] = union(propias)
    publicado = union(b.colegios.values())
    resto = d.index.difference(publicado)
    b.incluye_resto = len(resto) == 0 or _resto_suficiente(d.loc[resto, "Colegio"], minimo)
    b.nivel = d.index if b.incluye_resto else publicado
    return b


def filas(d: pd.DataFrame, base: Base, colegio=TODOS, grado=TODOS) -> pd.DataFrame:
    """Filas sobre las que se calcula el grupo pedido; vacío si no es publicable."""
    if activo(colegio) and activo(grado):
        idx = base.celdas.get(clave_celda(colegio, grado))
    elif activo(colegio):
        idx = base.colegios.get(str(colegio))
    elif activo(grado):
        idx = base.grados.get(str(grado))
    else:
        idx = base.nivel
    if idx is None:
        return d.iloc[0:0]
    return d.loc[d.index.intersection(idx)]


def relaciones(base: Base) -> list[tuple[str, pd.Index, list[pd.Index]]]:
    """(nombre del padre, índices del padre, índices de cada hijo publicado)."""
    rel = [("Nivel−colegios", base.nivel, list(base.colegios.values())),
           ("Nivel−grados", base.nivel, list(base.grados.values()))]
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
    _exigir_indice_unico(d)
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
            resto = padre.difference(union(publicados))
            if 0 < len(resto) < minimo:
                problemas.append(f"{etiqueta}: {nombre} menos sus subgrupos publicados "
                                 f"deja {len(resto)} respuestas")
    return problemas


def unidades(base: Base) -> list[tuple[str, pd.Index]]:
    """Celdas publicables y colegios completos (sin celdas publicables)."""
    salida = list(base.celdas.items())
    con_celdas = {partir_celda(k)[0] for k in base.celdas}
    salida += [(c, idx) for c, idx in base.colegios.items() if c not in con_celdas]
    return salida


def aplicar_todo_o_nada(d: pd.DataFrame, base: Base, columnas: list[str] | None = None,
                        minimo: int = cat.MIN_GROUP_N) -> tuple[pd.DataFrame, dict]:
    """Copia de `d` donde cada unidad publica un indicador entero o no lo publica.

    Para cada columna c, por separado: se borran (NaN) los valores de c de toda
    unidad con 1 a minimo − 1 valores válidos de c, y los del resto R (filas de
    `base.nivel` fuera de las unidades, si el nivel lo incluye) cuando R no tiene
    ≥ minimo valores válidos, de ≥ 2 colegios y con margen MARGEN_RESTO sobre
    su colegio más grande. Por defecto c recorre `columnas_de_analisis(d)`.

    Cada columna se trata de forma independiente: una columna derivada (p. ej.
    `banda_SDQ_Total`) queda enmascarada igual que su fuente solo si sus
    faltantes coinciden; si difieren pueden enmascararse distinto, y eso es
    correcto porque cada una cumple la regla por sí misma.

    Devuelve (copia enmascarada, {columna: valores suprimidos}) con solo las
    columnas en que se suprimió algo. Las filas fuera del nivel publicado no se
    tocan: no entran en ninguna cifra.
    """
    _exigir_indice_unico(d)
    dm = d.copy()
    if columnas is None:
        columnas = columnas_de_analisis(d)
    lista = unidades(base)
    en_unidades = union(i for _, i in lista)
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
            n = int(validos.loc[idx].sum())
            if 0 < n < minimo:
                borrar.append(idx)
        if len(resto):
            v_resto = resto[validos.loc[resto].to_numpy()]
            if len(v_resto):
                if "Colegio" in d.columns:
                    ok = _resto_suficiente(d.loc[v_resto, "Colegio"], minimo)
                else:
                    ok = len(v_resto) >= minimo
                if not ok:
                    borrar.append(resto)
        if not borrar:
            continue
        idx = union(borrar)
        n = int(validos.loc[idx].sum())
        if n:
            dm.loc[idx, col] = np.nan
            suprimidos[col] = n
    return dm, suprimidos

