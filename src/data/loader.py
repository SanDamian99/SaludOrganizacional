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


def es_demo(label) -> bool:
    """
    True si el label corresponde a un dataset sintético de demostración.

    Se compara contra la config y no contra el texto del label para que cambiar el
    nombre visible no apague el aviso. Un label desconocido (archivo subido por la
    persona) no es demo.
    """
    if not label:
        return False
    return any(d["label"] == label and d.get("demo", False) for d in PRELOADED_DATASETS)


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


# ─────────────────────────────────────────────────────────────────────────────
# Versión activa en Supabase Storage
#
# En el despliegue no hay xlsx en disco (están fuera de git), así que la fuente
# principal pasa a ser la versión activa del almacén. Se consulta primero la
# fila (barata, cacheada 10 min) y se cachea la descarga por `ruta`: una versión
# nueva tiene ruta nueva, así que activarla invalida sola el caché del archivo.
# ─────────────────────────────────────────────────────────────────────────────

def etiqueta_storage(version: dict, conjunto: str = "docentes") -> str:
    """Texto del selector para una versión del almacén."""
    fecha = pd.to_datetime(version.get("creada_en"), errors="coerce")
    fecha_txt = f"{fecha:%d/%m/%Y}" if pd.notna(fecha) else "sin fecha"
    return f"{conjunto.capitalize()} · versión {fecha_txt} ({version.get('filas', '?')} filas)"


@st.cache_data(ttl=600, show_spinner=False)
def version_activa_storage(conjunto: str = "docentes"):
    """Fila de la versión activa, o None si no hay credenciales ni versión."""
    from src.data import almacen
    if not almacen.disponible():
        return None
    return almacen.Almacen().version_activa(conjunto)


@st.cache_data(ttl=600, show_spinner=False)
def _procesar_desde_storage(ruta: str):
    """Descarga el CSV y lo pasa por el mismo pipeline que un archivo local."""
    from src.data import almacen
    raw = almacen.Almacen().descargar(ruta)
    df, report = ExcelProcessor().process_complex_excel(None, df_input=raw)
    report["success"] = True
    report["fuente"] = f"storage:{ruta}"
    return df, report


def dataset_activo_en_storage(conjunto: str = "docentes"):
    """(df, report, etiqueta) de la versión activa, o None si no la hay.

    Propaga errores de red: quien llama decide si avisar o caer a disco.
    """
    version = version_activa_storage(conjunto)
    if not version or not version.get("ruta"):
        return None
    df, report = _procesar_desde_storage(version["ruta"])
    return df, report, etiqueta_storage(version, conjunto)
