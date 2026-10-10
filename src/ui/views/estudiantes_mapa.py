"""
Sección «Mapa de Chía» de Estudiantes 360 — vista comunidad.

Solo dibuja; no calcula. Recibe del llamador los colegios visibles y pequeños
(`grupos_visibles`) para no importar la vista de comunidad. Si algo falla, el
llamador sigue sin mapa: es un complemento, no la página.
"""
from __future__ import annotations

import logging

import streamlit as st

from src.estudiantes import catalog as cat
from src.geo import auditoria_mapa, colegios_geo, mapa_datos, mapa_figura, opciones

log = logging.getLogger(__name__)

NOTA_LECTURA = ("Los colegios se muestran para conocer dónde hay respuestas y qué "
                "protege a los estudiantes. No es un ranking ni un diagnóstico.")
LEYENDA = {
    "respuestas": "Tamaño del círculo: respuestas recibidas (10 a 29, 30 a 99, "
                  "100 o más). Gris: todavía sin cifras que mostrar.",
    "sentirse_parte": "Más oscuro: mayor puntaje medio de sentirse parte del "
                      "colegio. Gris: todavía sin cifras que mostrar.",
    "apoyo_social": "Más oscuro: mayor puntaje medio de apoyo social. Gris: "
                    "todavía sin cifras que mostrar.",
}


def preparar(analisis, capa: str, visibles, pequenos):
    """(puntos, filas) listos para dibujar; levanta si la auditoría no pasa."""
    puntos, avisos = colegios_geo.cargar_puntos()
    for aviso in avisos:
        log.warning("Mapa: %s", aviso)
    filas = mapa_datos.tabla_mapa(analisis, capa, [p.codigo for p in puntos],
                                  visibles, pequenos)
    auditoria_mapa.auditar(filas, capa, visibles, pequenos)
    return puntos, filas


def render_mapa(analisis, rol: str, visibles, pequenos) -> bool:
    """Dibuja la sección. False si no corresponde (rol, sin puntos o auditoría)."""
    if not opciones.rol_ve_mapa(rol):
        return False
    puntos, _ = colegios_geo.cargar_puntos()
    if not puntos:
        return False
    capas = opciones.capas_activas()
    st.markdown("#### Mapa de Chía")
    if len(capas) > 1:
        capa = st.radio("Mostrar", capas, index=capas.index(opciones.capa_inicial()),
                        format_func=lambda c: mapa_datos.ETIQUETAS_CAPA[c],
                        horizontal=True, key="est_map_capa")
    else:
        capa = capas[0]
    try:
        puntos, filas = preparar(analisis, capa, visibles, pequenos)
    except Exception:                                      # noqa: BLE001
        log.exception("El mapa no se dibuja: la auditoría o la tabla fallaron")
        st.info("El mapa no está disponible en este momento.", icon="ℹ️")
        return False
    st.plotly_chart(mapa_figura.figura_interactiva(filas, capa, puntos),
                    width="stretch", key="est_map_fig")
    st.caption(LEYENDA[capa])
    if pequenos and opciones.MAPA_MOSTRAR_CAUSA_SIN_CIFRA:
        st.caption(cat.CIFRAS_PEQUENAS)
    st.caption(NOTA_LECTURA)
    return True
