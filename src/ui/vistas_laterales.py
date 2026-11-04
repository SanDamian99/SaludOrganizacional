"""
Cambio de vista — Observatorio 360.

Una sola regla para todos los módulos: las vistas de una página se eligen en el
panel lateral, nunca en pestañas del panel central. Solo se dibuja la vista
elegida (las pestañas de Streamlit ejecutan todas a la vez).

Vive en un módulo propio por la regla de despliegue de `navegacion.py`.
"""
from __future__ import annotations

import streamlit as st


def elegir_vista(nombres: list[str], clave: str, titulo: str = "Sección") -> int:
    """Dibuja el selector de vistas en el panel lateral; devuelve el índice elegido."""
    with st.sidebar:
        st.markdown("---")
        elegida = st.radio(titulo, nombres, key=clave)
    return nombres.index(elegida) if elegida in nombres else 0
