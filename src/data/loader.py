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
    """Ruta existente del dataset: tal cual, en la carpeta de datos fuente (y su
    subcarpeta «docentes») o en la raíz del repositorio."""
    from src.core.rutas import carpeta_datos
    if os.path.exists(path):
        return path
    for base in (carpeta_datos("docentes"), carpeta_datos(), _base_dir()):
        alt = os.path.join(base, path)
        if os.path.exists(alt):
            return alt
    return None


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


def _posprocesar(df, report):
    """Lo que solo aplica al archivo de docentes: los códigos de faltante.

    «Número de hijos» = 10 se convierte en NaN al cargar (ver
    `src/docentes/limpieza.py`); el archivo no se modifica. Se ejecuta DENTRO
    de las funciones cacheadas con `cache_resource`, una sola vez por archivo
    y antes de que el objeto se comparta entre sesiones; nunca sobre el objeto
    devuelto.
    """
    from src.docentes.limpieza import posprocesar
    return posprocesar(df, report)


# Los DataFrames van en `cache_resource`, no en `cache_data`: `cache_data`
# serializa el resultado y entrega una COPIA en cada acceso, así que cada sesión
# (cada visitante) guardaba su propio dataset de docentes en memoria. Con
# `cache_resource` hay un único objeto por proceso. Nadie lo muta: las vistas
# filtran con máscaras (que devuelven copias) y `save_new_dataset` guarda uno
# nuevo en vez de modificar el cargado.
@st.cache_resource(show_spinner=False)
def load_dataset(resolved_path: str):
    """Lee y procesa un dataset. Retorna (df, ingestion_report)."""
    proc = ExcelProcessor()
    if str(resolved_path).lower().endswith((".xlsx", ".xls")):
        df, report = proc.process_complex_excel(resolved_path)
    else:
        raw = pd.read_csv(resolved_path)
        df, report = proc.process_complex_excel(None, df_input=raw)
    df, report = _posprocesar(df, report)
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


@st.cache_resource(ttl=600, show_spinner=False)
def _procesar_desde_storage(ruta: str):
    """Descarga el CSV y lo pasa por el mismo pipeline que un archivo local."""
    from src.data import almacen
    raw = almacen.Almacen().descargar(ruta)
    df, report = ExcelProcessor().process_complex_excel(None, df_input=raw)
    df, report = _posprocesar(df, report)
    report["success"] = True
    report["fuente"] = f"storage:{ruta}"
    return df, report


def invalidar() -> None:
    """Olvida la versión activa y los datasets procesados.

    Se llama al subir o activar una versión: así la próxima lectura ve la nueva
    sin esperar al TTL ni vaciar las cachés de las demás páginas.
    """
    for fn in (version_activa_storage, _procesar_desde_storage, load_dataset):
        try:
            fn.clear()
        except Exception:                                  # noqa: BLE001
            pass


def dataset_activo_en_storage(conjunto: str = "docentes"):
    """(df, report, etiqueta) de la versión activa, o None si no la hay.

    Propaga errores de red: quien llama decide si avisar o caer a disco.
    """
    version = version_activa_storage(conjunto)
    if not version or not version.get("ruta"):
        return None
    df, report = _procesar_desde_storage(version["ruta"])
    return df, report, etiqueta_storage(version, conjunto)
