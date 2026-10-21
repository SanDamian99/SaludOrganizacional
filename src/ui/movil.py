"""
Ajustes de pantalla angosta (celular) para toda la plataforma.

Todo el CSS vive dentro de `@media (max-width: 768px)`: con una ventana más ancha
no se aplica ni una sola regla, así que el escritorio queda exactamente como estaba.
Se inyecta una vez desde `main.py`, antes de dibujar la página.

Qué corrige, y por qué:
  · La barra de herramientas de Plotly (cámara, zoom, casa…) tapa la esquina del
    gráfico y con el dedo no sirve: se oculta.
  · Los títulos de eje largos se salían de la pantalla: se achica su letra.
  · Las métricas se apilaban una por fila: pasan a dos por fila.
  · Títulos y márgenes pensados para escritorio comían media pantalla.
  · El mapa de calor «resultado de cada ítem por grupo» no cabe con 13 colegios:
    en celular se cambia por su tabla con color (`.st-key-doc_items_*` salen de
    `st.container(key=…)` en `docentes_items.render`).
"""
from __future__ import annotations

ANCHO_MAXIMO = 768

CSS = f"""
/* Fuera de celular, la tabla alternativa no existe (va antes del bloque de celular: mismo peso) */
.st-key-doc_items_movil {{ display: none; }}
@media (max-width: {ANCHO_MAXIMO}px) {{
  /* Gráficos: sin la barra de herramientas y con títulos de eje que caben */
  .stPlotlyChart .modebar-container {{ display: none !important; }}
  .stPlotlyChart .xtitle, .stPlotlyChart .ytitle {{ font-size: 10px !important; }}

  /* Márgenes y títulos más contenidos */
  [data-testid="stMainBlockContainer"] {{
    padding-top: 3.2rem !important; padding-left: 1rem !important;
    padding-right: 1rem !important;
  }}
  h1 {{ font-size: 1.75rem !important; line-height: 1.2 !important; }}
  h2 {{ font-size: 1.5rem !important; line-height: 1.25 !important; }}
  h3 {{ font-size: 1.25rem !important; }}
  h4 {{ font-size: 1.1rem !important; }}

  /* Métricas: dos por fila en lugar de una */
  [data-testid="stColumn"]:has([data-testid="stMetric"]) {{
    min-width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important;
  }}
  [data-testid="stMetricValue"] {{ font-size: 1.6rem !important; }}
  [data-testid="stMetricLabel"] p {{ font-size: 0.85rem !important; }}

  /* Avisos y pestañas */
  [data-testid="stAlertContainer"] {{ padding: 0.6rem 0.75rem !important; }}
  [data-baseweb="tab-list"] {{ overflow-x: auto; }}

  /* Resultado de cada ítem por grupo: tabla con color en vez del mapa de calor */
  .st-key-doc_items_calor, .st-key-doc_items_tabla {{ display: none !important; }}
  .st-key-doc_items_movil {{ display: block !important; }}
}}
"""


def inyectar() -> None:
    """Escribe la hoja de estilos en la página (sin ocupar espacio visible)."""
    import streamlit as st
    st.html(f"<style>{CSS}</style>")
