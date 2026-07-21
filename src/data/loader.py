"""
Carga de datasets precargados (seleccionables en la barra lateral).

Resuelve las rutas de config.PRELOADED_DATASETS que existen en disco y las procesa
con el pipeline de ingesta robusta. El resultado se cachea por ruta.
"""
import os
import pandas as pd
import streamlit as st

from src.core.config import PRELOADED_DATASETS
from src.data.processor import ExcelProcessor


def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _resolve(path: str):
    if os.path.exists(path):
        return path
    alt = os.path.join(_base_dir(), path)
    return alt if os.path.exists(alt) else None


def available_datasets() -> list:
    """Datasets precargados presentes en disco, en orden (el primero es el principal)."""
    out = []
    for d in PRELOADED_DATASETS:
        resolved = _resolve(d["path"])
        if resolved:
            out.append({**d, "resolved": resolved})
    return out


@st.cache_data(show_spinner=False)
def load_dataset(resolved_path: str):
    """Lee y procesa un dataset. Retorna (df, ingestion_report)."""
    proc = ExcelProcessor()
    if str(resolved_path).lower().endswith((".xlsx", ".xls")):
        df, report = proc.process_complex_excel(resolved_path)
    else:
        raw = pd.read_csv(resolved_path)
        df, report = proc.process_complex_excel(None, df_input=raw)
    report["success"] = True
    return df, report
