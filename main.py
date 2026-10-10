"""
Observatorio de Salud Organizacional — Main Entry Point
"""
import streamlit as st
# Antes de cualquier otro import de `src`: tras un despliegue en caliente sin
# sesiones abiertas, Streamlit conserva los módulos viejos (y el main.py viejo).
# `frescura` los desaloja si su archivo cambió; los imports de abajo ya leen
# del disco.
from src.core import frescura
frescura.refrescar(__file__)
from src.core import modo as modo_app
from src.core import navegacion as nav
from src.core.state import init_session_state

_MODO = modo_app.modo()
_PUBLICO = _MODO == modo_app.COMUNIDAD

# Page Config
st.set_page_config(
    page_title=("Observatorio 360 · Comunidad" if _PUBLICO
                else "Observatorio de Salud Organizacional"),
    page_icon=("🎒" if _PUBLICO else "📊"),
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize State
init_session_state()

# ─────────────────────────────────────────────────────────────────────────────
# Despliegue público: solo las vistas de comunidad.
# Se corta aquí, antes de importar el cargador de archivos, el chat, los
# informes o la vista de investigación. En esta ejecución esos módulos no
# existen, así que no hay URL ni clic que lleve a ellos.
# ─────────────────────────────────────────────────────────────────────────────
if _PUBLICO:
    _publicas = nav.menu(_MODO)
    if len(_publicas) > 1:
        with st.sidebar:
            _pagina_publica = st.radio("Ir a:", _publicas, key="nav_pagina")
    else:
        _pagina_publica = _publicas[0]
    if _pagina_publica == nav.PAGINA_ESTUDIANTES:
        from src.ui.estudiantes import render_estudiantes
        render_estudiantes()
    elif _pagina_publica == nav.PAGINA_CUIDADORES:
        # Solo la vista de comunidad, leída de la corrida publicada: nunca la
        # carga del formulario, la vista de investigadores ni la página local.
        from src.ui.views.cuidadores_comunidad import render_publico
        render_publico()
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
from src.data import loader as _loader
from src.data.loader import available_datasets, load_dataset

_datasets = available_datasets()

# La versión activa en Supabase Storage va de primera: en el despliegue es la
# única fuente real. Se pide con getattr por la misma razón que la página
# inicial: un módulo rancio en memoria no debe tumbar el arranque.
_version_activa = getattr(_loader, "version_activa_storage", None)
_etiqueta_storage = getattr(_loader, "etiqueta_storage", None)
if callable(_version_activa) and callable(_etiqueta_storage):
    try:
        _v = _version_activa("docentes")
        if _v:
            _datasets = [{"label": _etiqueta_storage(_v, "docentes"), "storage": "docentes",
                          "demo": False}] + _datasets
    except Exception as e:
        st.sidebar.caption(f"Sin acceso al almacén de versiones: {e}")

if _datasets:
    with st.sidebar:
        _labels = [d["label"] for d in _datasets]
        _sel = st.selectbox("📁 Dataset precargado", _labels, key="dataset_selector")
    # Recargar solo cuando el usuario cambia la selección (preserva archivos subidos)
    if st.session_state.get("_loaded_selector") != _sel:
        _chosen = next(d for d in _datasets if d["label"] == _sel)
        try:
            if _chosen.get("storage"):
                _df, _report, _ = _loader.dataset_activo_en_storage(_chosen["storage"])
            else:
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
    _opciones = nav.menu(_MODO)
    # El modo decide con qué página abre; después manda lo que elija la persona.
    # El menú sale de `navegacion`, un módulo nuevo: tras un despliegue nunca
    # queda en memoria una versión vieja que no tenga estas funciones.
    _inicial = nav.pagina_inicial(_MODO)
    _indice = _opciones.index(_inicial) if _inicial in _opciones else 0
    page = st.radio("Ir a:", _opciones, index=_indice, key="nav_pagina")

# --- Main Routing ---
if page == nav.PAGINA_DOCENTES:
    from src.ui.dashboard import render_dashboard
    render_dashboard()

elif page == nav.PAGINA_ESTUDIANTES:
    from src.ui.estudiantes import render_estudiantes
    render_estudiantes()

elif page == nav.PAGINA_CUIDADORES:
    # Vistas de comunidad y de investigadores, con los archivos en local o la
    # corrida publicada. El despliegue público se corta arriba y usa solo
    # `cuidadores_comunidad.render_publico`.
    from src.ui.cuidadores import render_cuidadores
    render_cuidadores()

elif page == nav.PAGINA_TRIANGULACION:
    # Fase 5: solo investigadores y solo con los archivos en local. Nunca se
    # importa en el despliegue público, que se corta arriba.
    from src.ui.triangulacion import render_triangulacion
    render_triangulacion()

elif page == nav.PAGINA_CHAT:
    from src.ui.chat import render_chat
    render_chat()

elif page == nav.PAGINA_CARGA:
    from src.ui.upload import render_upload
    render_upload()

elif page == nav.PAGINA_TENDENCIAS:
    from src.ui.trends import render_trends
    render_trends()

elif page == nav.PAGINA_REPORTES:
    render_reports_page()

# --- Footer Debug (sidebar) ---
st.sidebar.markdown("---")
st.sidebar.caption("💡 Accede al panel técnico con `?debug=1` en la URL.")
