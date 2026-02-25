"""
Panel de diagnóstico técnico.
Visible con: ?debug=1 o ?debug=true
"""
import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path
from src.ai.gemini_client import get_gemini_api_key


def render_diagnostics_panel():
    """Renderiza panel de diagnóstico completo."""
    st.markdown("## 🔧 Panel de Diagnóstico Técnico")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Ingesta de Datos",
        "🧠 Estado de la IA",
        "🔄 Historial de IA",
        "🏥 Integridad del Sistema"
    ])

    with tab1:
        _render_ingestion_diagnostics()

    with tab2:
        _render_ai_diagnostics()

    with tab3:
        _render_chat_history()

    with tab4:
        _render_system_health()


def _render_ingestion_diagnostics():
    report = st.session_state.get("last_ingestion_report", {})
    df = st.session_state.get("df")

    if not report:
        st.info("No hay datos cargados aún.")
        return

    st.subheader("Último reporte de ingesta")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filas originales", report.get("n_rows_original", "—"))
    col2.metric("Filas finales", report.get("n_rows_final", "—"))
    col3.metric("Columnas mapeadas", report.get("n_cols_mapped", "—"))
    col4.metric("Celdas imputadas", report.get("n_cells_imputed", 0))

    unmapped = report.get("unmapped_columns") or report.get("extra_variables", [])
    if unmapped:
        st.warning(f"Columnas no mapeadas: `{'`, `'.join(str(c) for c in unmapped)}`")

    if report.get("warnings"):
        st.subheader("Advertencias")
        for w in report["warnings"]:
            st.write(f"• {w}")

    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        st.subheader("Preview del DataFrame procesado")
        st.dataframe(df.head(10))

        st.subheader("Tipos de datos por columna")
        dtype_df = pd.DataFrame({
            "Columna": df.dtypes.index,
            "Tipo": df.dtypes.values.astype(str),
            "Valores únicos": [df[c].nunique() for c in df.columns],
            "% Nulos": [f"{df[c].isna().mean()*100:.1f}%" for c in df.columns]
        })
        st.dataframe(dtype_df)
    else:
        st.warning("No hay DataFrame actualmente procesado en memoria.")


def _render_ai_diagnostics():
    st.subheader("Configuración de la IA")
    api_configured = bool(get_gemini_api_key())
    st.write(f"API Key Gemini: {'✅ configurada' if api_configured else '❌ no encontrada'}")

    # Try to get stats from a client instance
    try:
        from src.ai.gemini_client import GeminiClient
        client = GeminiClient()
        stats = client.get_stats()
        st.info(f"Modelo: `{stats.get('model', 'desconocido')}`")
    except Exception:
        stats = {}

    st.subheader("Métricas de Uso de la Sesión")
    if 'ai_stats' not in st.session_state:
        st.session_state.ai_stats = {
            "calls": 0, "success": 0, "fails": 0, "tokens": 0, "latency": []
        }

    ai_stats = st.session_state.ai_stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Llamadas (Sesión)", ai_stats.get('calls', stats.get('calls', 0)))
    c2.metric("Errores", ai_stats.get('fails', stats.get('errors', 0)))
    c3.metric("Cache hits", stats.get('cache_hits', 0))


def _render_chat_history():
    st.subheader("Últimas consultas del chat")
    # Use 'messages' key (the actual key used by chat.py)
    messages = st.session_state.get("messages", [])
    if messages:
        for msg in reversed(messages[-10:]):
            role = "👤 Usuario" if msg.get("role") == "user" else "🤖 IA"
            content = str(msg.get("content", ""))[:200]
            with st.expander(f"{role}: {content}..."):
                st.write(msg.get("content", ""))
    else:
        st.info("Sin registros de chat.")


def _render_system_health():
    st.subheader("Estado de dependencias")

    checks = {
        "streamlit": "streamlit",
        "pandas": "pandas",
        "plotly": "plotly",
        "google.generativeai": "google-generativeai",
        "reportlab": "reportlab",
        "matplotlib": "matplotlib",
    }

    for module, pkg in checks.items():
        try:
            __import__(module)
            st.success(f"✅ {pkg}")
        except ImportError:
            st.error(f"❌ {pkg} — ejecuta: pip install {pkg}")

    st.subheader("Estado de configuración")
    api_key = get_gemini_api_key()
    st.write(f"API Key Gemini: {'✅ configurada' if api_key else '❌ no encontrada'}")

    df = st.session_state.get("df")
    if df is not None and isinstance(df, pd.DataFrame):
        st.write(f"DataFrame en memoria: ✅ {len(df):,} filas × {len(df.columns)} columnas")
    else:
        st.write("DataFrame en memoria: ⚠️ ninguno cargado")

    st.markdown("---")
    st.write("**Entorno de Servidor**")
    st.write(f"Python: {sys.version.split(' ')[0]}")
    st.write(f"Streamlit: {st.__version__}")
    st.write(f"Pandas: {pd.__version__}")
