"""
Observatorio de Salud Organizacional — Main Entry Point
"""
import streamlit as st
from src.core import modo as modo_app
from src.core.state import init_session_state

_MODO = modo_app.modo()
_PUBLICO = _MODO == modo_app.COMUNIDAD

# Page Config
st.set_page_config(
    page_title=("Observatorio 360 · Estudiantes" if _PUBLICO
                else "Observatorio de Salud Organizacional"),
    page_icon=("🎒" if _PUBLICO else "📊"),
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize State
init_session_state()

# ─────────────────────────────────────────────────────────────────────────────
# Despliegue público: solo la vista de estudiantes para la comunidad.
# Se corta aquí, antes de importar el cargador de archivos, el chat, los
# informes o la vista de investigación. En esta ejecución esos módulos no
# existen, así que no hay URL ni clic que lleve a ellos.
# ─────────────────────────────────────────────────────────────────────────────
if _PUBLICO:
    from src.ui.estudiantes import render_estudiantes
    render_estudiantes()
    st.stop()

from src.ai.gemini_client import get_gemini_api_key
from src.ui.reports import render_reports_page

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

# --- Selector de dataset precargado ---
from src.data.loader import available_datasets, load_dataset

_datasets = available_datasets()
if _datasets:
    with st.sidebar:
        _labels = [d["label"] for d in _datasets]
        _sel = st.selectbox("📁 Dataset precargado", _labels, key="dataset_selector")
    # Recargar solo cuando el usuario cambia la selección (preserva archivos subidos)
    if st.session_state.get("_loaded_selector") != _sel:
        _chosen = next(d for d in _datasets if d["label"] == _sel)
        try:
            _df, _report = load_dataset(_chosen["resolved"])
            st.session_state.df = _df
            st.session_state.last_ingestion_report = _report
            st.session_state.current_dataset = _sel
            st.session_state["_loaded_selector"] = _sel
            st.session_state.messages = []  # chat fresco para el nuevo dataset
        except Exception as e:
            st.sidebar.error(f"No se pudo cargar «{_sel}»: {e}")

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("Navegación")
    _todas = ["Dashboard", "Estudiantes 360", "Chat con IA", "Cargar Datos",
              "Analisis de tendencias", "Reportes"]
    _permitidas = modo_app.paginas_permitidas()
    _opciones = [p for p in _todas if _permitidas is None or p in _permitidas]
    # El modo decide con qué página abre; después manda lo que elija la persona.
    #
    # Se consulta con getattr y con alternativa: al desplegar, Streamlit vuelve a
    # ejecutar este archivo pero conserva en memoria los módulos ya importados.
    # Durante ese hueco `main.py` es nuevo y `src.core.modo` todavía es el viejo,
    # así que pedirle una función recién añadida tumbaba la aplicación entera con
    # un AttributeError. Ninguna página vale eso: si falta, se abre en la primera.
    _pagina_inicial = getattr(modo_app, "pagina_por_defecto", None)
    _inicial = _pagina_inicial() if callable(_pagina_inicial) else _opciones[0]
    _indice = _opciones.index(_inicial) if _inicial in _opciones else 0
    page = st.radio("Ir a:", _opciones, index=_indice)

# --- Main Routing ---
if page == "Dashboard":
    from src.ui.dashboard import render_dashboard
    render_dashboard()

elif page == "Estudiantes 360":
    from src.ui.estudiantes import render_estudiantes
    render_estudiantes()

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
