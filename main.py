"""
Observatorio de Salud Organizacional — Main Entry Point
"""
import streamlit as st
from src.core.state import init_session_state
from src.ai.gemini_client import get_gemini_api_key
from src.ui.reports import render_reports_page

# Page Config
st.set_page_config(
    page_title="Observatorio de Salud Organizacional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize State
init_session_state()

# --- Debug Mode (query param: ?debug=1 OR ?debug=true) ---
debug_param = st.query_params.get("debug", "").lower()
if debug_param in ("1", "true"):
    from src.ui.diagnostics import render_diagnostics_panel
    render_diagnostics_panel()
    st.stop()

# --- Banner de API Key ausente ---
if not get_gemini_api_key():
    st.sidebar.warning(
        "⚠️ **Funcionalidades de IA no disponibles**\n\n"
        "Para habilitar el chat y el análisis automático, "
        "configura tu API key en `.streamlit/secrets.toml`:\n\n"
        "```toml\nYOUR_API_KEY = 'tu-api-key-aqui'\n```"
    )

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("Navegación")
    page = st.radio("Ir a:", [
        "Dashboard",
        "Chat con IA",
        "Cargar Datos",
        "Analisis de tendencias",
        "Reportes"
    ])

# --- Main Routing ---
if page == "Dashboard":
    from src.ui.dashboard import render_dashboard
    render_dashboard()

elif page == "Chat con IA":
    from src.ui.chat import render_chat
    render_chat()

elif page == "Cargar Datos":
    from src.ui.upload import render_upload
    render_upload()

elif page == "Analisis de tendencias":
    from src.ui.trends import render_trends
    render_trends()

elif page == "Reportes":
    render_reports_page()

# --- Footer Debug (sidebar) ---
st.sidebar.markdown("---")
st.sidebar.caption("💡 Accede al panel técnico con `?debug=1` en la URL.")
