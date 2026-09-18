"""
Modo de despliegue — Observatorio 360.

Una misma base de código sirve para dos despliegues con audiencias distintas, y
la diferencia no puede depender de que nadie haga clic donde no debe.

    OBS360_MODO = "completo"      (por defecto) todo: local y equipo interno
    OBS360_MODO = "comunidad"     SOLO la vista de estudiantes para colegios,
                                  familias y municipio. Es lo que se despliega
                                  en público.
    OBS360_MODO = "investigador"  solo el módulo de estudiantes, vista de
                                  investigación, para un despliegue privado del
                                  equipo.

En modo «comunidad» la aplicación **no importa** el módulo de la vista de
investigación, ni el cargador de archivos, ni el chat, ni los informes: no es que
estén escondidos, es que no existen en esa ejecución. Un visitante público no
puede llegar a ellos ni escribiendo la URL.

Se configura en `.streamlit/secrets.toml` o como variable de entorno. En
Streamlit Community Cloud se pone en *Advanced settings → Secrets*:

    OBS360_MODO = "comunidad"
"""
from __future__ import annotations

import os

COMPLETO = "completo"
COMUNIDAD = "comunidad"
INVESTIGADOR = "investigador"
VALIDOS = (COMPLETO, COMUNIDAD, INVESTIGADOR)


def modo() -> str:
    """Modo activo. Ante un valor desconocido, el más restrictivo."""
    valor = os.environ.get("OBS360_MODO", "").strip().lower()
    if not valor:
        try:
            import streamlit as st
            valor = str(st.secrets.get("OBS360_MODO", "")).strip().lower()
        except Exception:                                  # noqa: BLE001
            valor = ""
    if not valor:
        return COMPLETO
    return valor if valor in VALIDOS else COMUNIDAD


def es_publico() -> bool:
    """True si esta ejecución puede estar siendo vista por cualquiera."""
    return modo() == COMUNIDAD


def paginas_permitidas() -> list[str] | None:
    """Páginas visibles en este modo. None = todas."""
    m = modo()
    if m == COMUNIDAD:
        return ["Estudiantes 360"]
    if m == INVESTIGADOR:
        return ["Estudiantes 360"]
    return None


def audiencias_permitidas() -> list[str] | None:
    """Vistas del módulo de estudiantes disponibles. None = las dos."""
    m = modo()
    if m == COMUNIDAD:
        return ["comunidad"]
    if m == INVESTIGADOR:
        return ["investigador"]
    return None
