"""
Observatorio de Salud Organizacional — Main Entry Point
"""
import streamlit as st
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

# Initialize State (solo claves vacías: ningún dato se carga aquí)
init_session_state()

# ─────────────────────────────────────────────────────────────────────────────
# Despliegue público: solo las vistas de comunidad.
# Se corta aquí, antes de importar el cargador de archivos, el chat, los
# informes o la vista de investigación. En esta ejecución esos módulos no
# existen, así que no hay URL ni clic que lleve a ellos. Tampoco se toca el
# dataset de docentes: en el público nadie lo ve.
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
    elif _pagina_publica == nav.PAGINA_TRIANGULACION:
        # Pública por decisión del usuario (10 oct 2026): solo la lectura de la
        # corrida publicada con la clave anon; nunca los archivos locales, la
        # vista previa ni el publicador. Con getattr: un módulo rancio en
        # memoria tras un despliegue no tumba la aplicación.
        from src.ui import triangulacion as _tri_publica
        _render_tri = getattr(_tri_publica, "render_publico", None)
        if callable(_render_tri):
            _render_tri()
        else:
            st.info("Esta página se está actualizando. Vuelva en unos minutos.")
    st.stop()

# --- Debug Mode (query param: ?debug=1 OR ?debug=true) ---
debug_param = st.query_params.get("debug", "").lower()
if debug_param in ("1", "true"):
    from src.ui.diagnostics import render_diagnostics_panel
    render_diagnostics_panel()
    st.stop()

# --- Sidebar: hueco del selector de dataset (se rellena solo si la página lo usa)
_hueco_dataset = st.sidebar.container()

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

# ─────────────────────────────────────────────────────────────────────────────
# Dataset de docentes: solo en las páginas que lo usan. Estudiantes, Cuidadores
# y Triangulación leen sus propias fuentes y no deben pagar la descarga ni el
# procesamiento de docentes (antes ocurría en cada sesión, en todas las páginas).
# ─────────────────────────────────────────────────────────────────────────────
_USAN_DOCENTES = {nav.PAGINA_DOCENTES, nav.PAGINA_CHAT, nav.PAGINA_CARGA, nav.PAGINA_REPORTES}

if page in _USAN_DOCENTES:
    from src.core import state as _state

    # Banner de API Key ausente (chat e interpretación con IA)
    from src.ai.gemini_client import get_gemini_api_key
    if not get_gemini_api_key():
        st.sidebar.warning(
            "⚠️ **Funcionalidades de IA no disponibles**\n\n"
            "Para habilitar el chat y el análisis automático, "
            "configura tu API key en `.streamlit/secrets.toml`:\n\n"
            "```toml\nYOUR_API_KEY = 'tu-api-key-aqui'\n```"
        )

    _datasets = _state.opciones_docentes()
    if _datasets:
        with _hueco_dataset:
            _labels = [d["label"] for d in _datasets]
            _sel = st.selectbox("📁 Dataset precargado", _labels, key="dataset_selector")
        # Recargar solo cuando cambia la selección (preserva archivos subidos)
        if st.session_state.get("_loaded_selector") != _sel:
            try:
                _state.cargar_docentes(next(d for d in _datasets if d["label"] == _sel))
            except Exception as e:
                st.sidebar.error(f"No se pudo cargar «{_sel}»: {e}")
    else:
        _state.cargar_docentes_si_falta()

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
    # Fase 5: archivos en local o corrida publicada, con vista previa. El
    # despliegue público se corta arriba y usa solo `render_publico`.
    from src.ui.triangulacion import render_triangulacion
    render_triangulacion()

elif page == nav.PAGINA_CHAT:
    from src.ui.chat import render_chat
    render_chat()

elif page == nav.PAGINA_CARGA:
    from src.ui.upload import render_upload
    render_upload()

elif page == nav.PAGINA_REPORTES:
    from src.ui.reports import render_reports_page
    render_reports_page()

# --- Footer Debug (sidebar) ---
st.sidebar.markdown("---")
st.sidebar.caption("💡 Accede al panel técnico con `?debug=1` en la URL.")
