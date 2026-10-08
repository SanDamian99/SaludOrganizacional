"""
Página «Cuidadores 360» — fase 4a: solo la vista de investigadores, en local.

  · Busca la exportación de «Cuidando al Cuidador» en la carpeta de datos
    fuente (`core.rutas`). Si no está (por ejemplo, en el despliegue), dice
    que Cuidadores aún no está publicado y no falla.
  · Sin la clave local `OBS360_CLAVE_HMAC` no carga y explica qué hacer.
  · El filtro de ola vive en la barra lateral y solo existe aquí.

La vista de comunidad, los informes y la corrida publicada llegan en la 4b.
La página solo se enruta en los modos completo e investigador (`main.py`).
"""
from __future__ import annotations

import os

import streamlit as st

from src.cuidadores import catalog as cat

TODAS = "Todas"
NO_PUBLICADO = ("Cuidadores aún no está publicado. Esta página muestra los resultados "
                "solo en la máquina que procesa el formulario; la vista para colegios, "
                "familias y municipio llegará cuando el equipo apruebe sus textos.")


@st.cache_resource(show_spinner="Leyendo el formulario de cuidadores…")
def _carga(firma: tuple):
    from src.cuidadores import ingest
    return ingest.cargar(firma[0])


@st.cache_resource(show_spinner="Puntuando y analizando…")
def _analisis(firma: tuple, ola: str | None):
    from src.cuidadores import pipeline
    return pipeline.analizar(_carga(firma), ola=ola)


def render_cuidadores() -> None:
    from src.cuidadores import pipeline
    from src.core.seudonimo import ClaveAusente

    ruta = pipeline.localizar_formulario()
    if not ruta:
        st.title("👪 Cuidadores 360")
        st.info(NO_PUBLICADO, icon="⏳")
        return
    firma = (ruta, os.path.getmtime(ruta))
    try:
        carga = _carga(firma)
    except ClaveAusente as exc:
        st.title("👪 Cuidadores 360")
        st.error(str(exc), icon="🔑")
        return
    except Exception as exc:                               # noqa: BLE001
        st.title("👪 Cuidadores 360")
        st.error(f"No se pudo leer el formulario de cuidadores: {exc}")
        return

    olas = sorted(o for o in carga.respuestas["Ola"].dropna().unique() if o != cat.SIN_DATO)
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Cuidadores 360**")
        eleccion = st.selectbox("Ola (solo local)", [TODAS, *olas], key="cuid_ola")
        st.caption(cat.AVISO_OLA)
    ola = None if eleccion == TODAS else eleccion
    ac = _analisis(firma, ola)
    st.sidebar.caption(f"{ac.cuidador.n} cuidadores · {ac.nino.n} niños")

    from src.ui.views.cuidadores_investigador import render_investigador
    render_investigador(ac)
