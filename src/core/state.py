"""
Gestión del estado de la sesión de Streamlit.
Centraliza la inicialización, limpieza y acceso al DataFrame procesado.
"""
import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def init_session_state():
    """Initializes the session state variables if they don't exist."""

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Processed data (DataFrame). No se carga aquí: el dataset de docentes solo
    # lo usan Docentes, Chat, Carga y Reportes, y `main.py` lo pide con
    # `cargar_docentes_si_falta()` al entrar en una de esas páginas. Antes se
    # descargaba y procesaba en cada sesión nueva, también en el despliegue
    # público, donde nadie lo ve.
    if "df" not in st.session_state:
        st.session_state.df = None

    # Analysis results (for context sharing)
    if "analysis_context" not in st.session_state:
        st.session_state.analysis_context = {}

    # Current view/page
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Docentes"

    # User info (if we add auth later)
    if "user" not in st.session_state:
        st.session_state.user = None

    # Ingestion report
    if "last_ingestion_report" not in st.session_state:
        st.session_state.last_ingestion_report = {}

    # File hash for idempotency
    if "current_file_hash" not in st.session_state:
        st.session_state.current_file_hash = None


def opciones_docentes() -> list[dict]:
    """Datasets de docentes disponibles, la versión activa del almacén primero.

    Cada opción trae `label` y, o bien `storage` (conjunto del almacén), o bien
    `resolved` (ruta en disco). Un fallo de red al consultar el almacén se
    anota y se sigue con el disco: nada de esto puede tumbar la aplicación.
    """
    from src.data import loader

    opciones = list(loader.available_datasets())
    try:
        version = loader.version_activa_storage("docentes")
        if version:
            opciones.insert(0, {"label": loader.etiqueta_storage(version, "docentes"),
                                "storage": "docentes", "demo": False})
    except Exception as e:                                  # noqa: BLE001
        logger.warning(f"Sin acceso al almacén de versiones: {e}")
    return opciones


def cargar_docentes(opcion: dict) -> None:
    """Deja en la sesión el dataset `opcion` (de `opciones_docentes`).

    Propaga los errores: quien llama decide cómo avisar.
    """
    from src.data import loader

    if opcion.get("storage"):
        df, report, _ = loader.dataset_activo_en_storage(opcion["storage"])
    else:
        df, report = loader.load_dataset(opcion["resolved"])
    st.session_state.df = df
    st.session_state.last_ingestion_report = report
    st.session_state.current_dataset = opcion["label"]
    st.session_state["_loaded_selector"] = opcion["label"]
    st.session_state.messages = []  # chat fresco para el nuevo dataset


def cargar_docentes_si_falta() -> None:
    """Carga el primer dataset de docentes si la sesión aún no tiene ninguno.

    Lo llaman las páginas que usan docentes. Si no hay datos disponibles, la
    sesión queda sin `df` y la página muestra su aviso de siempre.
    """
    if st.session_state.get("df") is not None or st.session_state.get("_loaded_selector"):
        return
    try:
        opciones = opciones_docentes()
        if opciones:
            cargar_docentes(opciones[0])
    except Exception as e:                                  # noqa: BLE001
        logger.warning(f"No se pudo cargar el dataset de docentes: {e}")


def get_processed_data() -> pd.DataFrame | None:
    """
    Returns the currently loaded DataFrame, or None if not available.
    Safe accessor used by dashboard.py, chat, etc.
    """
    df = st.session_state.get("df")
    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        return df
    return None


def clear_state_for_new_dataset():
    """
    Limpia TODO el estado relacionado con datos al cargar un nuevo dataset.
    Llama esta función ANTES de guardar el nuevo df.
    """
    keys_to_clear = [
        "df",
        "messages",
        "last_ingestion_report",
        "cached_charts",
        "cached_analytics",
        "current_file_hash",
        "analysis_context",
        "ai_stats",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def save_new_dataset(df: pd.DataFrame, ingestion_report: dict, file_hash: str):
    """
    Guarda un nuevo dataset de forma segura, limpiando el estado anterior.
    """
    clear_state_for_new_dataset()
    st.session_state["df"] = df
    st.session_state["last_ingestion_report"] = ingestion_report
    st.session_state["current_file_hash"] = file_hash
    st.session_state["messages"] = []  # Chat fresco para cada dataset
