"""
Detección y resumen de indicadores para datasets genéricos (no de bienestar laboral).

Cuando un dataset no usa el esquema (BM) del Observatorio (p. ej. baterías con totales
de subescala precalculados: PSS_T, IRI_*_Total, ERS_*_T…), se tratan esas columnas como
"indicadores" y se resumen de forma neutral (media, DE, rango, N). No se asume dirección
de riesgo/bienestar sin codebook: la interpretación se deja al usuario / a la IA.
"""
import re
import pandas as pd

from src.data.processor import is_protected_column

_TOTAL_RE = re.compile(r"(_T$|_Total$|_TOTAL$|_total$)")


def is_wellbeing_dataset(df: pd.DataFrame) -> bool:
    """True si el dataset usa el esquema de dimensiones (BM) del Observatorio."""
    return any("(BM),(" in str(c) for c in df.columns)


def detect_indicators(df: pd.DataFrame) -> list:
    """Devuelve las columnas-indicador de un dataset genérico.

    Prioriza los totales precalculados (*_T / *_Total). Si no hay, cae a columnas
    numéricas de tipo escala (rango acotado), excluyendo identificadores.
    """
    if df is None or df.empty:
        return []

    totals = [c for c in df.columns
              if _TOTAL_RE.search(str(c)) and pd.api.types.is_numeric_dtype(df[c])]
    if totals:
        return totals

    out = []
    for c in df.columns:
        if is_protected_column(c) or not pd.api.types.is_numeric_dtype(df[c]):
            continue
        s = df[c].dropna()
        if s.empty:
            continue
        rng = float(s.max() - s.min())
        if 1 <= rng <= 80 and s.nunique() <= 60:
            out.append(c)
    return out


def indicator_stats(df: pd.DataFrame, cols: list) -> dict:
    """Estadísticos descriptivos por indicador."""
    rows = {}
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if s.empty:
            continue
        n = int(s.shape[0])
        rows[c] = {
            "mean": float(s.mean()),
            "std": float(s.std(ddof=1)) if n > 1 else 0.0,
            "min": float(s.min()),
            "max": float(s.max()),
            "n": n,
        }
    return rows
