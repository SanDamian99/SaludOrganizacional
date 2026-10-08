"""
Estado compartido entre páginas — Observatorio 360.

El colegio y el rol que elige la persona deben seguir elegidos al pasar de
Estudiantes a Cuidadores y volver. Streamlit no lo garantiza: borra el valor de
un widget en cuanto una ejecución no lo dibuja. Por eso el valor se guarda
también en una clave de sesión que no pertenece a ningún widget, y cada página
siembra su widget desde ella.
"""
from __future__ import annotations

from typing import Any, MutableMapping, Sequence

import streamlit as st

COLEGIO = "obs360_colegio"
ROL = "obs360_rol"
_URL_APLICADA = "obs360_colegio_url_aplicada"


def _sesion(sesion: MutableMapping | None) -> MutableMapping:
    return st.session_state if sesion is None else sesion


def sembrar(clave_widget: str, clave_compartida: str, opciones: Sequence[Any],
            sesion: MutableMapping | None = None) -> None:
    """Antes de dibujar el widget: toma el valor compartido, si es una de las opciones.

    Se asigna en cada ejecución, aunque el widget ya tenga valor. En el
    despliegue público `main.py` termina con `st.stop()` y Streamlit, ante esa
    parada prematura, no borra el estado de los widgets que no se dibujaron: al
    volver a una página su clave sigue en la sesión con el valor viejo y, como no
    se asignó en esta ejecución, el navegador no lo recibe y dibuja la opción por
    defecto («Todos»). Asignarlo siempre hace que el servidor lo envíe.

    Lo que la persona elige no se pierde: el widget debe declarar
    `on_change=al_cambiar(...)`, que copia la elección al valor compartido antes
    de que corra la página.
    """
    s = _sesion(sesion)
    if s.get(clave_compartida) in list(opciones):
        s[clave_widget] = s[clave_compartida]


def al_cambiar(clave_widget: str, clave_compartida: str,
               sesion: MutableMapping | None = None):
    """Callback `on_change`: la elección de la persona pasa al valor compartido."""
    def _copiar() -> None:
        s = _sesion(sesion)
        guardar(clave_compartida, s[clave_widget], sesion=s)
    return _copiar


def guardar(clave_compartida: str, valor: Any,
            sesion: MutableMapping | None = None) -> None:
    """Después de dibujar el widget: el valor elegido pasa a ser el compartido."""
    _sesion(sesion)[clave_compartida] = valor


def aplicar_colegio_de_url(codigo: str | None,
                           sesion: MutableMapping | None = None) -> None:
    """`?colegio=` preselecciona el colegio una sola vez por sesión.

    Después manda lo que la persona elija. `codigo` ya debe venir validado
    (`estudiantes.colegio_de_la_url`).
    """
    s = _sesion(sesion)
    if codigo and not s.get(_URL_APLICADA):
        s[COLEGIO] = codigo
        s[_URL_APLICADA] = True
