"""
Grupo mínimo de 10 para el módulo Docentes.

Es la misma regla que ya cumplen Estudiantes y Cuidadores (`MIN_GROUP_N = 10`):
ningún grupo de menos de 10 personas se muestra, y ningún conteo menor de 10 se
imprime. Aquí viven las funciones puras que usan la página Docentes y los PDF;
no importan Streamlit.

Supresión secundaria: si en una variable solo una categoría queda escondida y
el total se ve en otra parte (siempre se ve), su cifra se deduce restando. Por
eso, cuando hay exactamente una categoría «<10», también se esconde la siguiente
más pequeña, que se muestra como «≥10 (oculto)».
"""
from __future__ import annotations

import math

import pandas as pd

N_MINIMO = 10
MENOS_DE = "<10"
OCULTO = "≥10 (oculto)"
MENSAJE_GRUPO_PEQUENO = "Grupo demasiado pequeño para mostrarse (menos de 10)"
NOTA_OCULTOS = ("Las categorías con menos de 10 docentes no muestran su cifra; si solo "
                "una quedaba oculta, se oculta otra más para que no se deduzca restando.")


class GrupoPequeno(ValueError):
    """Se pidió un resultado (p. ej. un PDF) para un grupo de menos de 10."""

    def __init__(self, mensaje: str = MENSAJE_GRUPO_PEQUENO):
        super().__init__(mensaje)


def grupo_suficiente(n) -> bool:
    """¿El grupo tiene al menos `N_MINIMO` personas?"""
    try:
        return int(n) >= N_MINIMO
    except (TypeError, ValueError):
        return False


def exigir_grupo(n) -> None:
    """Lanza `GrupoPequeno` si el grupo no llega al mínimo."""
    if not grupo_suficiente(n):
        raise GrupoPequeno()


def texto_n(n) -> str:
    """El conteo como texto, o «<10» si es menor que el mínimo."""
    return f"{int(n):,}" if grupo_suficiente(n) else MENOS_DE


def conteos_protegidos(serie: pd.Series) -> pd.DataFrame:
    """Conteo por categoría sin cifras pequeñas ni deducibles.

    Devuelve un DataFrame con `categoria`, `n` (el conteo real, solo para
    ordenar y dibujar las visibles), `texto` (lo que se puede mostrar) y
    `visible` (si `n` se puede mostrar tal cual). Los NaN no son categoría.
    """
    vc = serie.dropna().value_counts()
    t = pd.DataFrame({"categoria": list(vc.index), "n": [int(v) for v in vc.values]})
    t["visible"] = t["n"] >= N_MINIMO
    t["texto"] = [f"{n:,}" if v else MENOS_DE for n, v in zip(t["n"], t["visible"])]
    if (~t["visible"]).sum() == 1 and t["visible"].sum() >= 1:
        # La visible más pequeña también se esconde: si no, la oculta sale por resta.
        i = t[t["visible"]]["n"].idxmin()
        t.loc[i, "visible"] = False
        t.loc[i, "texto"] = OCULTO
    return t.reset_index(drop=True)


def texto_conteos(serie: pd.Series) -> str:
    """«Mujer: 40, Hombre: ≥10 (oculto), No binario: <10» para un PDF o un pie."""
    t = conteos_protegidos(serie)
    return ", ".join(f"{c}: {x}" for c, x in zip(t["categoria"], t["texto"]))


def agrupar_numerica(serie: pd.Series, ancho: int | None = None) -> pd.Series:
    """Pasa una numérica (edad, años) a rangos de texto «20–29» para poder enmascararla.

    Un histograma muestra cuántas personas caen en cada barra, también cuando
    son una o dos; en rangos se aplica la misma regla que a las categorías.
    Sin `ancho`, se usan unos cinco rangos.
    """
    s = pd.to_numeric(serie, errors="coerce")
    validos = s.dropna()
    if validos.empty:
        return pd.Series([None] * len(s), index=s.index, dtype=object)
    minimo, maximo = math.floor(validos.min()), math.floor(validos.max())
    if not ancho:
        ancho = max(1, math.ceil((maximo - minimo + 1) / 5))
    inicio = (minimo // ancho) * ancho

    def _rango(v):
        if pd.isna(v):
            return None
        a = inicio + int((math.floor(v) - inicio) // ancho) * ancho
        return f"{a}–{a + ancho - 1}" if ancho > 1 else f"{a}"
    return s.map(_rango).astype(object)


def grupos_comparables(agg: pd.DataFrame, columna: str, conteo: str = "count"
                       ) -> tuple[pd.DataFrame, list]:
    """Separa los grupos de una comparación: (los de 10 o más, nombres de los demás).

    Con la misma supresión secundaria que `conteos_protegidos`: si solo un grupo
    queda fuera, también sale el visible más pequeño, para que su tamaño no se
    deduzca restando del total.
    """
    pequeno = agg[conteo] < N_MINIMO
    if pequeno.sum() == 1 and (~pequeno).sum() >= 1:
        pequeno = pequeno.copy()
        pequeno[agg.loc[~pequeno, conteo].idxmin()] = True
    visibles = agg[~pequeno]
    ocultos = [str(g) for g in agg.loc[pequeno, columna]]
    return visibles, ocultos
