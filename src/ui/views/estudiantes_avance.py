"""
Sección «Avance de datos» de la vista investigador de Estudiantes 360.

Muestra qué celdas colegio × grado ya tienen cifras y cuáles esperan una
exportación, y (a pedido) las últimas corridas de Supabase. Solo dibuja: el
cálculo vive en `src.estudiantes.avance`. Si algo falla, el llamador sigue sin
la sección.
"""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from src.estudiantes import avance as av

log = logging.getLogger(__name__)

LEYENDA = ("✔ n: ya hay cifras (mínimo 10 respuestas). falta n: hay respuestas pero "
           "menos de 10, por eso no se muestran. pendiente: se espera una exportación "
           "actualizada. —: no hay respuestas.")


def _cliente():
    """(cliente, qué ve): el usuario de carga si existe, si no el de lectura pública."""
    try:
        from src.core import vista_previa
        cli = vista_previa.cliente_autenticado()
        if cli is not None:
            return cli, "Con el usuario de carga: se ven también las corridas en revisión."
    except Exception:                                      # noqa: BLE001
        log.exception("Avance: no se pudo obtener el cliente del usuario de carga")
    try:
        from src.estudiantes import lectura
        if lectura.disponible():
            return lectura._cliente(), "Solo se ve la corrida publicada."
    except Exception:                                      # noqa: BLE001
        log.exception("Avance: no se pudo obtener el cliente de lectura")
    return None, ""


def _corridas() -> None:
    cli, nota = _cliente()
    if cli is None:
        st.info("No hay conexión con Supabase desde esta sesión.", icon="ℹ️")
        return
    try:
        filas = av.formatear_corridas(av.leer_corridas(cli))
    except Exception:                                      # noqa: BLE001
        log.exception("Avance: no se pudieron leer las corridas")
        st.info("No se pudieron leer las corridas de Supabase.", icon="ℹ️")
        return
    st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)
    st.caption(nota)


def render_avance(a, nivel: str) -> None:
    st.subheader("Avance de datos")
    lista = av.celdas(a, nivel)
    r = av.resumen(lista)
    c1, c2, c3 = st.columns(3)
    c1.metric("Celdas con cifras", r[av.VISIBLE])
    c2.metric("Con menos de 10", r[av.FALTA_N])
    c3.metric("Pendientes de exportación", r[av.PENDIENTE])
    m = av.matriz(a, nivel)
    if m.empty:
        st.info("Todavía no hay conteos por colegio y grado en esta corrida.", icon="ℹ️")
    else:
        st.dataframe(m, width="stretch")
        st.caption(LEYENDA)
    pendientes = av.texto_pendientes(lista)
    if pendientes:
        st.markdown(f"**Se espera en la próxima exportación:** {pendientes}. "
                    "Cuando llegue, desde «Cargar Datos», estas celdas pasan solas a "
                    "«✔» si tienen 10 o más respuestas.")
    if st.checkbox("Ver las últimas corridas de Supabase", key="inv_avance_corridas"):
        _corridas()
