"""
Página «Cuidadores 360» en los modos completo e investigador.

Un selector «Vista» (como en Estudiantes) decide qué se arma:
  · «Colegios, familias y municipio»: la vista de comunidad
    (`views/cuidadores_comunidad`), con el análisis de todas las olas ya
    preparado (`cuidadores.comunidad.preparar`), igual que lo que se publica.
  · «Equipo investigador»: la vista de investigadores de la fase 4a, con el
    filtro de ola que solo existe aquí.

Dos fuentes, en este orden:
  1. La exportación de «Cuidando al Cuidador» en la carpeta de datos fuente
     (`core.rutas`), con la clave local `OBS360_CLAVE_HMAC`.
  2. La corrida publicada en Supabase (`cuidadores.lectura`): es lo que ve el
     despliegue del equipo, que no tiene archivos. Solo agregados, de todas las
     olas. `OBS360_FUENTE=supabase` la fuerza aunque haya archivos.
Sin ninguna de las dos, dice que Cuidadores aún no está publicado y no falla.

El despliegue público nunca importa este módulo (`main.py` corta antes): allí
la página es `cuidadores_comunidad.render_publico`.
"""
from __future__ import annotations

import os

import streamlit as st

from src.core import modo as modo_app
from src.cuidadores import catalog as cat

TODAS = "Todas"
AUDIENCIAS = {"comunidad": "Colegios, familias y municipio",
              "investigador": "Equipo investigador"}
NO_PUBLICADO = ("Cuidadores aún no está publicado. Esta página muestra los resultados "
                "solo en la máquina que procesa el formulario o cuando hay una corrida de "
                "cuidadores publicada.")


@st.cache_resource(show_spinner="Leyendo el formulario de cuidadores…")
def _carga(firma: tuple):
    from src.cuidadores import ingest
    return ingest.cargar(firma[0])


@st.cache_resource(show_spinner="Puntuando y analizando…")
def _analisis(firma: tuple, ola: str | None):
    from src.cuidadores import pipeline
    return pipeline.analizar(_carga(firma), ola=ola)


def preparar_con_auditoria(analisis):
    """`comunidad.preparar` y, una sola vez, la auditoría de la publicación.

    Los hallazgos quedan en `hallazgos_auditoria`: con uno solo, la vista no
    ofrece descargas. Si la auditoría no se puede correr, también se bloquea.
    """
    from src.cuidadores import comunidad, publicar
    preparado = comunidad.preparar(analisis)
    try:
        preparado.hallazgos_auditoria = list(publicar.verificar_restas(preparado))
    except Exception as exc:                               # noqa: BLE001
        preparado.hallazgos_auditoria = [f"la auditoría no se pudo correr: {type(exc).__name__}"]
    return preparado


@st.cache_resource(show_spinner="Preparando la vista de comunidad…")
def _preparado(firma: tuple):
    return preparar_con_auditoria(_analisis(firma, None))


def _vista() -> str:
    defecto = getattr(modo_app, "audiencia_por_defecto", None)
    inicial = defecto() if callable(defecto) else "comunidad"
    opciones = list(AUDIENCIAS)
    with st.sidebar:
        st.markdown("---")
        st.markdown("**Cuidadores 360**")
        return st.radio("Vista", opciones,
                        index=opciones.index(inicial) if inicial in opciones else 0,
                        format_func=lambda k: AUDIENCIAS[k], key="cuid_audiencia")


def _sin_datos() -> None:
    st.title("👪 Cuidadores 360")
    st.info(NO_PUBLICADO, icon="⏳")


def _desde_supabase(vista: str) -> None:
    from src.cuidadores import lectura
    from src.ui.views import cuidadores_comunidad as vc
    publicado = vc.publicado()
    if publicado is None:
        _sin_datos()
        return
    st.sidebar.caption("Fuente: corrida publicada")
    st.info(lectura.AVISO_PUBLICADO, icon="🗄️")
    if vista == "comunidad":
        from src.ui import estado
        estado.aplicar_colegio_de_url(vc.colegio_de_la_url(publicado))
        vc.render_comunidad(publicado)
    else:
        from src.ui.views.cuidadores_investigador import render_investigador
        render_investigador(publicado)


def render_cuidadores() -> None:
    from src.core.seudonimo import ClaveAusente
    from src.cuidadores import pipeline

    vista = _vista()
    forzada = os.environ.get("OBS360_FUENTE", "").strip().lower() == "supabase"
    ruta = None if forzada else pipeline.localizar_formulario()
    if not ruta:
        _desde_supabase(vista)
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

    if vista == "comunidad":
        from src.ui import estado
        from src.ui.views import cuidadores_comunidad as vc
        preparado = _preparado(firma)
        estado.aplicar_colegio_de_url(vc.colegio_de_la_url(preparado))
        vc.render_comunidad(preparado)
        return

    olas = sorted(o for o in carga.respuestas["Ola"].dropna().unique() if o != cat.SIN_DATO)
    with st.sidebar:
        eleccion = st.selectbox("Ola (solo local)", [TODAS, *olas], key="cuid_ola")
        st.caption(cat.AVISO_OLA)
    ola = None if eleccion == TODAS else eleccion
    ac = _analisis(firma, ola)
    st.sidebar.caption(f"{ac.cuidador.n} cuidadores · {ac.nino.n} niños")

    from src.ui.views.cuidadores_investigador import render_investigador
    render_investigador(ac)
