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
  · Los errores se muestran con mensajes fijos: nunca el texto de la
    excepción (podría llevar una ruta o un valor); al registro solo va su tipo.
  · La caché del análisis se firma con los archivos y una huella SHA-256 de
    la clave: cambiar la clave invalida el análisis guardado.

Solo se enruta en los modos completo e investigador (`main.py`): el despliegue
público nunca importa este módulo ni `src.triangulacion`.
"""
from __future__ import annotations

import hashlib
import logging

import streamlit as st

from src.triangulacion import catalogo as cat

LOG = logging.getLogger(__name__)
MENSAJE_ERROR = ("No se pudo armar la triangulación. Revise que los tres archivos de esta "
                 "máquina sean los esperados y vuelva a intentarlo; el detalle técnico no se "
                 "muestra para no exponer datos.")


@st.cache_resource(show_spinner="Cargando los tres actores y enlazando díadas…")
def _analisis(firma: tuple):
    from src.triangulacion import pipeline
    return pipeline.cargar_y_analizar()


def firma(disponibles) -> tuple:
    """Archivos con su fecha y una huella de la clave (nunca la clave).

    Cambiar la clave cambia la firma, así que la caché no sirve un análisis
    hecho con otra clave. Sin la clave lanza `ClaveAusente`.
    """
    from src.core import seudonimo
    huella = hashlib.sha256(b"obs360-firma|" + seudonimo.clave()).hexdigest()[:16]
    return (*disponibles.firma(), ("clave", huella))


def _titulo() -> None:
    st.title(f"🔺 {cat.TITULO}")


def render_triangulacion() -> None:
    from src.core.seudonimo import MENSAJE_CLAVE, ClaveAusente
    from src.triangulacion import fuentes

    try:
        disponibles = fuentes.localizar()
        if not disponibles.completo:
            _titulo()
            st.info(cat.AVISO_DESPLIEGUE, icon="⏳")
            st.caption("Archivos en esta máquina: " + " · ".join(
                f"{actor}: {'sí' if hay else 'no'}"
                for actor, hay in disponibles.presentes().items()))
            return
        t = _analisis(firma(disponibles))
    except ClaveAusente:
        _titulo()
        st.error(MENSAJE_CLAVE, icon="🔑")
        return
    except fuentes.ModuloRancio:
        _titulo()
        st.warning(fuentes.MENSAJE_RANCIO, icon="🔄")
        return
    except Exception as exc:                               # noqa: BLE001
        LOG.error("Triangulación 360: falló el análisis (%s)", type(exc).__name__)
        _titulo()
        st.error(MENSAJE_ERROR)
        return

    from src.ui.views.triangulacion_investigador import render_investigador
    render_investigador(t)
