"""
Página «Triangulación 360» — fase 5: solo investigadores.

Dos fuentes, en este orden:
  1. Los tres archivos (estudiantes, cuidadores y docentes) en la carpeta de
     datos fuente (`core.rutas`), con la clave local `OBS360_CLAVE_HMAC`: la
     máquina que procesa calcula todo, díadas incluidas (solo en memoria).
  2. Sin los tres archivos (el despliegue del equipo) o con
     `OBS360_FUENTE=supabase`: la corrida de triangulación que subió esa máquina
     (`triangulacion.lectura`), leída SOLO con el usuario de carga
     (`vista_previa.cliente_autenticado`). Son los mismos agregados, con las
     mismas pestañas, figuras dibujadas desde las tablas y el mismo ZIP. El
     público nunca la lee (migración 2026-10-10b).
Sin ninguna de las dos, un mensaje fijo: aún no hay una corrida publicada.

Vista previa del equipo (`src.core.vista_previa`): si hay una corrida de
triangulación OCULTA más nueva que la abierta, el interruptor de la barra
lateral la muestra (encendido por defecto en el modo investigador), con una
franja arriba que lo advierte.

  · Sin la clave local, con archivos, no carga y explica qué hacer.
  · Si `estudiantes.ingest` quedó viejo en memoria (sin `clave_nino`), pide
    reiniciar la aplicación en vez de fallar.
  · Los errores se muestran con mensajes fijos: nunca el texto de la
    excepción (podría llevar una ruta o un valor); al registro solo va su tipo.
  · La caché del análisis local se firma con los archivos y una huella SHA-256
    de la clave: cambiar la clave invalida el análisis guardado.
  · Módulos nuevos (`lectura`) o con símbolos nuevos (`vista_previa`) se usan
    dentro de un `try` y con `getattr`: un módulo rancio en memoria tras un
    despliegue nunca tumba la página (cae en el mensaje fijo).

Solo se enruta en los modos completo e investigador (`main.py`): el despliegue
público nunca importa este módulo ni `src.triangulacion`.
"""
from __future__ import annotations

import hashlib
import logging
import os

import streamlit as st

from src.triangulacion import catalogo as cat

LOG = logging.getLogger(__name__)
MODULO = "triangulacion"
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


# ── Corrida publicada para el equipo ────────────────────────────────────────
def _lectura():
    """Módulo `triangulacion.lectura`, o None (ausente o rancio)."""
    try:
        from src.triangulacion import lectura
    except Exception as exc:                               # noqa: BLE001
        LOG.warning("Triangulación [import lectura]: %s.", type(exc).__name__)
        return None
    if not all(callable(getattr(lectura, n, None)) for n in ("cargar", "id_corrida_publicada")):
        LOG.warning("Triangulación: módulo lectura rancio.")
        return None
    return lectura


def _vista_previa():
    """Módulo `vista_previa`, o None (modo comunidad, ausente o rancio)."""
    from src.core import modo as modo_app
    if modo_app.modo() == modo_app.COMUNIDAD:
        return None
    try:
        from src.core import vista_previa as vp
    except Exception as exc:                               # noqa: BLE001
        LOG.warning("Vista previa [triangulación: import]: %s.", type(exc).__name__)
        return None
    if not callable(getattr(vp, "interruptor", None)):
        LOG.warning("Vista previa [triangulación]: módulo vista_previa rancio.")
        return None
    return vp


def _marcar_en_uso(vp, en_uso: bool) -> None:
    fn = getattr(vp, "marcar_en_uso", None) if vp is not None else None
    if callable(fn):
        try:
            fn(MODULO, en_uso)
        except Exception as exc:                           # noqa: BLE001
            LOG.warning("Vista previa [triangulación: marcar_en_uso]: %s.", type(exc).__name__)


@st.cache_resource(show_spinner="Leyendo la triangulación del equipo…")
def _leer(corrida_id: int, origen: str):
    """La corrida `corrida_id` con el usuario de carga. Lanza si no se puede leer
    (así un fallo no queda guardado en la caché)."""
    lectura = _lectura()
    t = lectura.cargar(corrida_id=corrida_id) if lectura is not None else None
    if t is None:
        raise LookupError("corrida no legible")
    return t


def texto_franja(info: dict) -> str:
    abierta = info.get("publicada")
    cola = (f"La corrida abierta para el equipo es la {abierta}." if abierta is not None
            else "Aún no hay ninguna corrida de triangulación abierta para el equipo.")
    return ("Vista previa para el equipo: esta corrida de triangulación se subió sin abrir "
            "(sin --publicar-ya). " + cola + " La triangulación nunca es pública.")


def _franja(info: dict) -> None:
    from html import escape
    st.markdown(
        '<div class="obs360-vista-previa" role="alert" style="position:sticky;top:3.25rem;'
        "z-index:999;background:#fff4d6;color:#4a3500;border:2px solid #e0a800;"
        'border-radius:8px;padding:0.75rem 1rem;margin-bottom:1rem;font-weight:600">'
        f"🔍 {escape(texto_franja(info))}</div>",
        unsafe_allow_html=True)


def _en_revision(vp):
    """(información, corrida oculta) si el interruptor la muestra; si no, (None, None)."""
    if vp is None:
        return None, None
    paso = "interruptor"
    try:
        info = vp.interruptor(MODULO)
        if not info:
            return None, None
        paso = f"_leer({info['en_revision']})"
        return info, _leer(int(info["en_revision"]), "revision")
    except Exception as exc:                               # noqa: BLE001
        LOG.warning("Vista previa [triangulación: %s]: %s. Se muestra la abierta.",
                    paso, type(exc).__name__)
        return None, None


def _publicada(lectura):
    try:
        cid = lectura.id_corrida_publicada()
        return _leer(int(cid), "publicada") if cid is not None else None
    except Exception as exc:                               # noqa: BLE001
        LOG.warning("Triangulación: no se pudo leer la corrida publicada (%s).",
                    type(exc).__name__)
        return None


def _sin_corrida(disponibles) -> None:
    _titulo()
    st.info(cat.AVISO_DESPLIEGUE, icon="⏳")
    if disponibles is not None:
        st.caption("Archivos en esta máquina: " + " · ".join(
            f"{actor}: {'sí' if hay else 'no'}"
            for actor, hay in disponibles.presentes().items()))


def _desde_supabase(disponibles) -> None:
    lectura = _lectura()
    vp = _vista_previa()
    info, t = (None, None) if lectura is None else _en_revision(vp)
    if t is None and lectura is not None:
        info, t = None, _publicada(lectura)
    _marcar_en_uso(vp, info is not None)
    if t is None:
        _sin_corrida(disponibles)
        return
    if info is not None:
        _franja(info)
        st.sidebar.caption(f"Fuente: corrida en revisión ({info['en_revision']}), "
                           "no abierta para el equipo")
    else:
        st.sidebar.caption(f"Fuente: corrida {t.corrida.get('id')} publicada para el equipo")
        st.info(lectura.AVISO_PUBLICADO, icon="🗄️")
    from src.ui.views.triangulacion_investigador import render_investigador
    render_investigador(t)


def render_triangulacion() -> None:
    from src.core.seudonimo import MENSAJE_CLAVE, ClaveAusente
    from src.triangulacion import fuentes

    disponibles = None
    try:
        disponibles = fuentes.localizar()
        forzada = os.environ.get("OBS360_FUENTE", "").strip().lower() == "supabase"
        if forzada or not disponibles.completo:
            _desde_supabase(disponibles)
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
