"""
Puntuación del archivo de docentes desde los ítems — Observatorio 360.

ÚNICA fuente de los puntajes de dimensión de Docentes. Lee el catálogo
(`src/docentes/catalogo.py`), recodifica un archivo en codificación 1 y
puntúa cada dimensión por docente; `resumen` da los agregados que consumen la
vista y las pruebas: media con IC t, N real (sin imputar), DE, α, % de la
escala teórica orientado a «mayor = mejor», zona anclada al corte publicado o
al tercio de la escala, y % por banda de corte con IC de Wilson.

Nada de aquí depende del mínimo ni del máximo de la muestra: la zona de una
media es la misma en el municipio y en un colegio.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.grupo_minimo import N_MINIMO
from src.docentes import catalogo as cat
from src.docentes import estadistica as est


# ── Codificación ────────────────────────────────────────────────────────────
def codificacion(df: pd.DataFrame) -> int:
    """2 si el archivo lleva la marca de la codificación actual; 1 si no."""
    if cat.COLUMNA_CODIFICACION not in df.columns:
        return 1
    valores = pd.to_numeric(df[cat.COLUMNA_CODIFICACION], errors="coerce").dropna()
    if valores.empty:
        return 1
    return int(valores.iloc[0])


def normalizar_codificacion(df: pd.DataFrame) -> pd.DataFrame:
    """Copia del archivo en codificación 2 (recodifica si venía en la 1)."""
    out = df.copy()
    if codificacion(out) == 1:
        for item, maximo in cat.RECODIFICAR_V1.items():
            if item in out.columns:
                out[item] = maximo - pd.to_numeric(out[item], errors="coerce")
        out[cat.COLUMNA_CODIFICACION] = cat.CODIFICACION_ACTUAL
    return out


def es_archivo_docentes(df: pd.DataFrame) -> bool:
    """True si trae los ítems del PSS-10 y del BAT-12: el archivo codificado de docentes."""
    if df is None or df.empty:
        return False
    columnas = set(map(str, df.columns))
    return (set(cat.por_clave("PSS").items) <= columnas
            and set(cat.por_clave("BTA").items) <= columnas)


# ── Puntuación por docente ──────────────────────────────────────────────────
def _items(df: pd.DataFrame, dim: cat.Dimension) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    for c in dim.items:
        X[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else np.nan
    return X


def _puntaje(X: pd.DataFrame, dim: cat.Dimension) -> pd.Series:
    respondidos = X.notna().sum(axis=1)
    if dim.agregacion == "suma":
        s = X.sum(axis=1, min_count=1).where(respondidos >= len(dim.items))
    elif dim.agregacion == "valor":
        s = X.iloc[:, 0]
    else:
        s = X.mean(axis=1).where(respondidos >= dim.codigo_min_items)
    return s + dim.desplazamiento


def puntuar(df: pd.DataFrame) -> pd.DataFrame:
    """Un puntaje por docente y dimensión (columnas = claves del catálogo)."""
    n = normalizar_codificacion(df)
    out = pd.DataFrame(index=df.index)
    for dim in cat.DIMENSIONES:
        out[dim.clave] = _puntaje(_items(n, dim), dim)
    return out


def cronbach_alpha(X: pd.DataFrame) -> float | None:
    X = X.dropna()
    k = X.shape[1]
    if k < 2 or len(X) < 2:
        return None
    total = X.sum(axis=1).var(ddof=1)
    if not total or pd.isna(total):
        return None
    return float(k / (k - 1) * (1 - X.var(ddof=1).sum() / total))


# ── Zona anclada ────────────────────────────────────────────────────────────
def pct_escala(valor: float, dim: cat.Dimension) -> float | None:
    """% de la escala teórica, orientado a «mayor = mejor»; None sin dirección."""
    if dim.direccion is None or valor is None or pd.isna(valor):
        return None
    lo, hi = dim.escala
    pct = (float(valor) - lo) / (hi - lo) * 100
    pct = min(100.0, max(0.0, pct))
    return pct if dim.direccion == cat.MAYOR_MEJOR else 100 - pct


def banda_de(valor: float, dim: cat.Dimension) -> cat.Banda | None:
    """La banda [inferior, superior) donde cae `valor`; la última incluye su superior.

    Bandas continuas: una media de 13,6 en el PSS cae en «moderado» (14–26),
    no en «bajo» (0–13). Por debajo del mínimo se asigna la primera banda.
    """
    if not dim.cortes or valor is None or pd.isna(valor):
        return None
    bandas = sorted(dim.cortes, key=lambda b: b.inferior)
    for b in bandas[:-1]:
        if b.inferior <= valor < b.superior:
            return b
    return bandas[-1] if valor >= bandas[-1].inferior else bandas[0]


def zona_de(valor: float, dim: cat.Dimension) -> str:
    """Zona del semáforo: por banda de corte si la hay; si no, por tercio de la escala."""
    if valor is None or pd.isna(valor):
        return cat.ZONA_SIN_DATO
    banda = banda_de(valor, dim)
    if banda is not None:
        return banda.zona
    pct = pct_escala(valor, dim)
    if pct is None:
        return cat.ZONA_SIN_DATO
    if pct >= 200 / 3:
        return cat.ZONA_FAVORABLE
    if pct <= 100 / 3:
        return cat.ZONA_VIGILAR
    return cat.ZONA_INTERMEDIA


def _bandas(s: pd.Series, dim: cat.Dimension) -> list[dict]:
    if not dim.cortes:
        return []
    asignada = s.map(lambda v: banda_de(v, dim).etiqueta)
    out = []
    for b in sorted(dim.cortes, key=lambda b: b.inferior):
        k = int((asignada == b.etiqueta).sum())
        out.append({"etiqueta": b.etiqueta, "zona": b.zona, "inferior": b.inferior,
                    "superior": b.superior, "comprobar": dim.comprobar_en_manual,
                    **est.proporcion_protegida(k, len(s))})
    return out


# ── Resumen ─────────────────────────────────────────────────────────────────
def resumen(df: pd.DataFrame, solo_tablero: bool = False) -> dict:
    """clave → agregados de la dimensión. Vacío si el grupo tiene menos de 10 docentes.

    Una dimensión sin al menos 10 docentes puntuados no aparece.
    """
    if df is None or len(df) < N_MINIMO:
        return {}
    n = normalizar_codificacion(df)
    # Los avisos sobre el cambio de formulario solo tienen sentido si el archivo
    # trae las dos versiones; con una sola no hay nada que comparar.
    varias_olas = (cat.COLUMNA_VERSION in df.columns
                   and df[cat.COLUMNA_VERSION].dropna().nunique() > 1)
    out: dict[str, dict] = {}
    for dim in cat.DIMENSIONES:
        if solo_tablero and not dim.en_tablero:
            continue
        X = _items(n, dim)
        s = _puntaje(X, dim).dropna()
        if len(s) < N_MINIMO:
            continue
        media, ic_inf, ic_sup = est.ic_media(s)
        de = float(s.std(ddof=1))
        banda = banda_de(media, dim)
        zona = zona_de(media, dim)
        out[dim.clave] = {
            "clave": dim.clave, "nombre": dim.nombre, "tema": dim.tema,
            "direccion": dim.direccion, "mayor_mejor": dim.mayor_mejor,
            "agregacion": dim.agregacion, "escala": dim.escala,
            "n": int(len(s)), "n_items": len(dim.items),
            "media": media, "de": de, "ic_inf": ic_inf, "ic_sup": ic_sup,
            "ic95": (ic_sup - ic_inf) / 2 if ic_inf is not None else None,
            "alfa": cronbach_alpha(X) if len(dim.items) >= 2 else None,
            "pct_escala": pct_escala(media, dim),
            "zona": zona, "zona_etiqueta": cat.ETIQUETA_ZONA[zona], "color": cat.COLOR_ZONA[zona],
            "banda": banda.etiqueta if banda else None,
            "bandas": _bandas(s, dim),
            "cortes_tipo": dim.cortes_tipo, "comprobar_en_manual": dim.comprobar_en_manual,
            "aviso_version": dim.aviso_version and varias_olas, "solo_version": dim.solo_version,
            "nota": dim.nota or (dim.nota_olas if varias_olas else ""), "fuente": dim.fuente, "frase": dim.frase,
            "en_tablero": dim.en_tablero,
        }
    return out


def por_tema(res: dict) -> dict:
    """{tema: [(clave, info), …]} en el orden de `catalogo.TEMAS`."""
    grupos: dict[str, list] = {t: [] for t in cat.TEMAS}
    for clave, info in res.items():
        grupos.setdefault(info["tema"], []).append((clave, info))
    return {t: v for t, v in grupos.items() if v}
