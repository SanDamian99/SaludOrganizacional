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
    """Antes de dibujar el widget: si no tiene valor, toma el compartido.

    Solo si ese valor es una de las opciones; si no, el widget usa su valor
    inicial. Nunca pisa lo que la persona ya eligió en este widget.
    """
    s = _sesion(sesion)
    if clave_widget not in s and s.get(clave_compartida) in list(opciones):
        s[clave_widget] = s[clave_compartida]


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
