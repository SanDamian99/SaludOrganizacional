"""
Página «Triangulación 360» — fase 5: solo investigadores, solo local.

  · Busca los tres archivos (estudiantes, cuidadores y docentes) en la carpeta
    de datos fuente (`core.rutas`). Si falta alguno (por ejemplo, en el
    despliegue del equipo), lo dice con un mensaje fijo y no falla: la capa por
    colegio en el despliegue necesita los agregados publicados de cuidadores,
    que llegan con la fase 4b.
  · Sin la clave local `OBS360_CLAVE_HMAC` no carga y explica qué hacer.
  · Si `estudiantes.ingest` quedó viejo en memoria (sin `clave_nino`), pide
    reiniciar la aplicación en vez de fallar.

Solo se enruta en los modos completo e investigador (`main.py`): el despliegue
público nunca importa este módulo ni `src.triangulacion`.
"""
from __future__ import annotations

import streamlit as st

from src.triangulacion import catalogo as cat


@st.cache_resource(show_spinner="Cargando los tres actores y enlazando díadas…")
def _analisis(firma: tuple):
    from src.triangulacion import pipeline
    return pipeline.cargar_y_analizar()


def render_triangulacion() -> None:
    from src.core.seudonimo import ClaveAusente
    from src.triangulacion import fuentes

    disponibles = fuentes.localizar()
    if not disponibles.completo:
        st.title(f"🔺 {cat.TITULO}")
        st.info(cat.AVISO_DESPLIEGUE, icon="⏳")
        st.caption("Archivos en esta máquina: " + " · ".join(
            f"{actor}: {'sí' if hay else 'no'}"
            for actor, hay in disponibles.presentes().items()))
        return
    try:
        t = _analisis(disponibles.firma())
    except ClaveAusente as exc:
        st.title(f"🔺 {cat.TITULO}")
        st.error(str(exc), icon="🔑")
        return
    except fuentes.ModuloRancio as exc:
        st.title(f"🔺 {cat.TITULO}")
        st.warning(str(exc), icon="🔄")
        return
    except Exception as exc:                               # noqa: BLE001
        st.title(f"🔺 {cat.TITULO}")
        st.error(f"No se pudo armar la triangulación: {exc}")
        return

    from src.ui.views.triangulacion_investigador import render_investigador
    render_investigador(t)
