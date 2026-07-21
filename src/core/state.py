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

    # Processed data (DataFrame)
    if "df" not in st.session_state:
        st.session_state.df = None

        # Cargar el dataset precargado principal (el primero disponible).
        try:
            from src.data.loader import available_datasets, load_dataset

            datasets = available_datasets()
            if datasets:
                df, report = load_dataset(datasets[0]["resolved"])
                st.session_state.df = df
                st.session_state.last_ingestion_report = report
                st.session_state.current_dataset = datasets[0]["label"]
                st.session_state["_loaded_selector"] = datasets[0]["label"]
        except Exception as e:
            logger.warning(f"Error loading default data: {e}")

    # Analysis results (for context sharing)
    if "analysis_context" not in st.session_state:
        st.session_state.analysis_context = {}

    # Current view/page
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # User info (if we add auth later)
    if "user" not in st.session_state:
        st.session_state.user = None

    # Ingestion report
    if "last_ingestion_report" not in st.session_state:
        st.session_state.last_ingestion_report = {}

    # File hash for idempotency
    if "current_file_hash" not in st.session_state:
        st.session_state.current_file_hash = None


def get_processed_data() -> pd.DataFrame | None:
    """
    Returns the currently loaded DataFrame, or None if not available.
    Safe accessor used by trends.py, dashboard.py, etc.
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
