"""
Universo publicable del módulo Docentes.

(a) Las sedes se funden con su institución (`catalogo.SEDES`): una sede nunca
    se compara sola.
(b) La Secretaría de Educación queda fuera del universo comparable
    (`catalogo.FUERA_DEL_UNIVERSO`): no es un colegio.
(c) El total que se muestra y la lista de grupos son consistentes: con
    `reparto`, los grupos con menos de 10 van juntos en «otros» y, si «otros»
    queda entre 1 y 9, absorbe al grupo publicado más pequeño. Así el total
    exacto menos los grupos mostrados nunca deja de 1 a 9 (misma regla que
    `src/triangulacion/enlace.reparto`).
"""
from __future__ import annotations

import pandas as pd

from src.analysis.grupo_minimo import N_MINIMO
from src.docentes import catalogo as cat

OTROS = "otros (grupos con menos de 10)"


def institucion(serie: pd.Series) -> pd.Series:
    """Nombre de la institución: las sedes pasan a su colegio principal."""
    return serie.map(lambda v: cat.SEDES.get(v, v) if isinstance(v, str) else v)


def aplicar(df: pd.DataFrame, columna: str = cat.COLUMNA_COLEGIO) -> pd.DataFrame:
    """Copia del archivo con las sedes fundidas y sin las filas fuera del universo."""
    if columna not in df.columns:
        return df.copy()
    out = df.copy()
    out[columna] = institucion(out[columna])
    return out[~out[columna].isin(cat.FUERA_DEL_UNIVERSO)].reset_index(drop=True)


def reparto(conteos: dict) -> tuple[dict, int, str | None]:
    """(grupos con 10 o más, total de «otros», grupo absorbido por «otros» o None)."""
    grandes = {str(k): int(v) for k, v in conteos.items() if int(v) >= N_MINIMO}
    otros = sum(int(v) for k, v in conteos.items() if str(k) not in grandes)
    absorbido = None
    if 0 < otros < N_MINIMO and grandes:
        absorbido = min(grandes, key=lambda k: (grandes[k], k))
        otros += grandes.pop(absorbido)
    return grandes, otros, absorbido


def grupos_publicables(agg: pd.DataFrame, columna: str, conteo: str = "count"
                       ) -> tuple[pd.DataFrame, int, str | None, list[str]]:
    """Filas de `agg` que se muestran, n de «otros», grupo absorbido y nombres ocultos.

    Los NaN de la columna de grupo cuentan en «otros».
    """
    sin_dato = agg[columna].isna()
    con_dato = agg[~sin_dato]
    conteos = {str(r[columna]): int(r[conteo]) for _, r in con_dato.iterrows()}
    grandes, otros, absorbido = reparto(conteos)
    n_sin_dato = int(agg.loc[sin_dato, conteo].sum())
    if n_sin_dato and 0 < otros + n_sin_dato < N_MINIMO and grandes:
        # «otros» (grupos pequeños + sin dato) quedaría entre 1 y 9: absorbe uno más.
        absorbido = min(grandes, key=lambda k: (grandes[k], k))
        otros += grandes.pop(absorbido)
    otros += n_sin_dato
    visibles = con_dato[con_dato[columna].astype(str).isin(grandes.keys())]
    ocultos = [k for k in conteos if k not in grandes and k != absorbido]
    return visibles, otros, absorbido, ocultos


def consistente(total: int, mostrados: list[int], otros: int) -> bool:
    """True si el total no deja deducir un grupo de 1 a 9: total − mostrados = otros,
    con otros igual a 0 o 10 o más."""
    resto = int(total) - sum(int(m) for m in mostrados)
    return resto == int(otros) and (resto == 0 or resto >= N_MINIMO)


def pie(agg, columna, otros, absorbido, ocultos) -> str:
    """«N por grupo: A=30, B=12. Otros (grupos con menos de 10): 15 (incluye C; sin cifra: D, E).»"""
    partes = []
    if not agg.empty:
        partes.append("N por grupo: " + ", ".join(
            f"{r[columna]}={int(r['count'])}" for _, r in agg.iterrows()) + ".")
    if otros:
        detalle = []
        if absorbido:
            detalle.append(f"incluye {absorbido}")
        if ocultos:
            detalle.append("con menos de 10 docentes, sin cifra: " + ", ".join(ocultos))
        partes.append(f"{OTROS.capitalize()}: {otros}" + (f" ({'; '.join(detalle)})" if detalle else "") + ".")
    return " ".join(partes)
