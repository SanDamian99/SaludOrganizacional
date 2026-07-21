"""
Núcleo de puntuación psicométrica — única fuente de verdad de los puntajes de dimensión.

Aplica la valencia por ítem (config.DIMENSION_VALENCE) y el reverse-scoring, de modo que
TODAS las dimensiones quedan orientadas a "mayor = mejor bienestar". Dashboard y reportes
consumen exactamente estos números. Ver docs/METODOLOGIA_PUNTAJES.md.
"""
import math
import pandas as pd

from src.core.config import (
    DATA_DICTIONARY,
    item_valence,
    get_scale_range,
    RISK_DIMENSIONS,
)


def _bm_dims() -> dict:
    return DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {})


def dimension_columns(df: pd.DataFrame, dim_name: str) -> list:
    """Columnas numéricas del df que pertenecen a la dimensión, por acrónimo (BM),(ACR)."""
    details = _bm_dims().get(dim_name, {})
    acr = details.get("Acronimo")
    if not acr:
        return []
    target = f"(BM),({acr})"
    return [c for c in df.columns
            if target in c and pd.api.types.is_numeric_dtype(df[c])]


def orient_items(df: pd.DataFrame, dim_name: str, cols: list) -> pd.DataFrame:
    """Devuelve los ítems orientados a bienestar (invierte los de valencia -1)."""
    mn, mx = get_scale_range(dim_name)
    span = mn + mx
    out = {}
    for c in cols:
        if item_valence(dim_name, c) < 0:
            out[c] = span - df[c]
        else:
            out[c] = df[c]
    return pd.DataFrame(out, index=df.index)


def cronbach_alpha(item_df: pd.DataFrame):
    """Alfa de Cronbach (consistencia interna). None si no es computable."""
    item_df = item_df.dropna(axis=0, how="any")
    k = item_df.shape[1]
    if k < 2 or len(item_df) < 2:
        return None
    item_vars = item_df.var(axis=0, ddof=1)
    total_var = item_df.sum(axis=1).var(ddof=1)
    if not total_var or pd.isna(total_var):
        return None
    alpha = (k / (k - 1)) * (1 - item_vars.sum() / total_var)
    return float(alpha)


def estado_from_score(score, dim_name: str):
    """Clasifica un puntaje YA orientado (mayor = mejor) en el semáforo."""
    mn, mx = get_scale_range(dim_name)
    rango = mx - mn
    if rango <= 0 or score is None or pd.isna(score):
        return "Sin Datos", "grey"
    umbral_riesgo = mn + rango / 3.0
    umbral_fortaleza = mx - rango / 3.0
    if score >= umbral_fortaleza:
        return "Fortaleza", "green"
    if score <= umbral_riesgo:
        return "Riesgo", "red"
    return "Intermedio", "yellow"


def compute_dimension_scores(df: pd.DataFrame) -> dict:
    """Calcula puntaje orientado + métricas por dimensión.

    Retorna: dim -> {score, n, std, ci95, alpha, n_items, estado, color,
                     scale_min, scale_max, is_risk, raw_mean, acronimo}
    """
    results = {}
    if df is None or df.empty:
        return results

    for dim_name in _bm_dims().keys():
        cols = dimension_columns(df, dim_name)
        if not cols:
            continue

        oriented = orient_items(df, dim_name, cols)
        per_respondent = oriented.mean(axis=1, skipna=True)
        valid = per_respondent.dropna()
        if valid.empty:
            continue

        n = int(valid.shape[0])
        score = float(valid.mean())
        std = float(valid.std(ddof=1)) if n > 1 else 0.0
        ci95 = (1.96 * std / math.sqrt(n)) if n > 1 else 0.0
        alpha = cronbach_alpha(oriented) if len(cols) >= 2 else None
        estado, color = estado_from_score(score, dim_name)
        mn, mx = get_scale_range(dim_name)

        raw_series = df[cols].mean(axis=1, skipna=True).dropna()
        raw_mean = float(raw_series.mean()) if not raw_series.empty else None

        results[dim_name] = {
            "score": score,          # orientado: mayor = mejor bienestar
            "n": n,
            "std": std,
            "ci95": ci95,
            "alpha": alpha,
            "n_items": len(cols),
            "estado": estado,
            "color": color,
            "scale_min": mn,
            "scale_max": mx,
            "is_risk": dim_name in RISK_DIMENSIONS,
            "raw_mean": raw_mean,
            "acronimo": _bm_dims()[dim_name].get("Acronimo"),
        }
    return results


def classify_dimensions(scores: dict):
    """Separa en (fortalezas, riesgos, intermedios), cada uno lista de (dim, score)."""
    fort, riesgo, inter = [], [], []
    for dim, info in scores.items():
        estado = info.get("estado")
        entry = (dim, info.get("score"))
        if estado == "Fortaleza":
            fort.append(entry)
        elif estado == "Riesgo":
            riesgo.append(entry)
        elif estado == "Intermedio":
            inter.append(entry)
    fort.sort(key=lambda x: x[1], reverse=True)
    riesgo.sort(key=lambda x: x[1])
    inter.sort(key=lambda x: x[1])
    return fort, riesgo, inter


def averages_only(df: pd.DataFrame) -> dict:
    """Compatibilidad: {dim: score_orientado} para código que espera promedios simples."""
    return {dim: info["score"] for dim, info in compute_dimension_scores(df).items()}
