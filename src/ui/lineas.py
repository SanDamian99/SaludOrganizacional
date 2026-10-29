"""
Líneas de atención — interfaz.

Tres cosas, todas leen de `core.lineas_atencion`:
  · `cuadro_ayuda`: el cuadro «Si necesita ayuda», por niveles (ahora mismo, hoy,
    esta semana), con un acceso al directorio completo.
  · `lineas_de_la_senal`: pocas líneas, las del tema de una alerta de grupo.
  · `render_lineas`: la página «Dónde pedir ayuda» (directorio con filtros).

No lee datos ni Supabase: nunca depende de la red ni de cifras de grupo.
"""
from __future__ import annotations

import html

import streamlit as st

from src.core import lineas_atencion as la
from src.core import navegacion as nav

TODOS = "Todos"
TITULO_PAGINA = "Dónde pedir ayuda"
INTRO = ("Líneas gratuitas y servicios de salud mental para Chía y municipios vecinos. "
         "Ante un peligro inmediato, llame al **123**.")
AVISO_CONFIRMAR = ("Los horarios y sedes pueden cambiar: ante la duda, llame antes de ir.")


def _llamar(x: la.Linea) -> str:
    """Teléfono como enlace para llamar (en el celular abre el marcador)."""
    if x.marcado:
        return f"[📞 {x.telefono}](tel:{x.marcado})"
    return f"📞 {x.telefono}" if x.telefono else ""


def linea_md(x: la.Linea, completa: bool = False) -> str:
    """Una línea en markdown: nombre, teléfono y frase corta; con `completa`, todo."""
    partes = [f"**{x.nombre}** — {_llamar(x)}".rstrip(" —"), x.resumen]
    texto = " · ".join(p for p in partes if p)
    if completa:
        if x.horario:
            texto += f"  \n🕒 {x.horario}"
        if x.whatsapp:
            texto += f"  \n💬 WhatsApp: [{x.whatsapp}](https://wa.me/57{x.whatsapp})"
        if x.direccion:
            texto += f"  \n📍 {x.direccion}"
        if x.correo:
            texto += f"  \n✉️ {x.correo}"
        if x.descripcion:
            texto += f"  \n{x.descripcion}"
    if x.nota:
        texto += f"  \n⚠️ *{x.nota}*"
    return texto


def _ir_a_directorio() -> None:
    st.session_state["nav_pagina"] = nav.PAGINA_LINEAS


def _directorio_disponible() -> bool:
    try:
        from src.core import modo as modo_app
        return nav.PAGINA_LINEAS in nav.menu(modo_app.modo())
    except Exception:                                      # noqa: BLE001
        return False


def cuadro_ayuda(tipo: str = "estudiante", titulo: str = "🆘 Si un estudiante necesita ayuda",
                 clave: str = "ayuda") -> None:
    """El cuadro de ayuda por niveles. `tipo`: «estudiante» o «adulto»."""
    por = la.ruta_niveles(tipo)
    with st.container(border=True):
        st.markdown(f"#### {titulo}")
        for nivel in la.NIVELES:
            if not por[nivel]:
                continue
            st.markdown(f"**{la.NIVELES_TITULO[nivel]}**")
            for x in por[nivel]:
                st.markdown(f"- {linea_md(x)}")
        if _directorio_disponible():
            st.button("Ver todas las líneas", key=f"lineas_ver_{clave}",
                      on_click=_ir_a_directorio)
        else:
            st.caption(f"Más líneas en la sección «{TITULO_PAGINA}».")


def lineas_de_la_senal(alerta: str) -> None:
    """Pocas líneas para el tema de una alerta de grupo; plegadas, sin ocupar pantalla."""
    lineas = la.para_senal(alerta)
    if not lineas:
        return
    with st.expander("Líneas de ayuda para este tema"):
        for x in lineas:
            st.markdown(f"- {linea_md(x)}")


# ── La página ────────────────────────────────────────────────────────────────
def _tarjeta(x: la.Linea) -> None:
    with st.container(border=True):
        st.markdown(linea_md(x, completa=True))


def _opciones(diccionario: dict[str, str]) -> list[str]:
    return [TODOS, *diccionario]


def render_lineas() -> None:
    st.title(f"🆘 {TITULO_PAGINA}")
    st.markdown(INTRO)
    c1, c2, c3 = st.columns(3)
    para = c1.selectbox("¿Para quién?", _opciones(la.PARA), key="lin_para",
                        format_func=lambda k: k if k == TODOS else la.PARA[k])
    tema = c2.selectbox("¿Qué pasa?", _opciones(la.TEMAS), key="lin_tema",
                        format_func=lambda k: k if k == TODOS else la.TEMAS[k])
    lugar = c3.selectbox("¿Dónde vive?", _opciones(la.MUNICIPIOS), key="lin_lugar",
                         format_func=lambda k: k if k == TODOS else la.MUNICIPIOS[k])
    encontradas = la.filtrar(para=None if para == TODOS else para,
                             tema=None if tema == TODOS else tema,
                             municipio=None if lugar == TODOS else lugar,
                             solo_directorio=True)
    if not encontradas:
        st.info("Ninguna línea coincide con esos filtros. Pruebe con «Todos» o llame al 106 "
                "o al 123.")
    sin_filtro = para == tema == lugar == TODOS
    urgentes = la.ruta_niveles("estudiante")["ahora"] if sin_filtro else []
    if urgentes:
        st.markdown("### Primero")
        for x in urgentes:
            _tarjeta(x)
    resto = [x for x in encontradas if x not in urgentes]
    for municipio, nombre in la.MUNICIPIOS.items():
        grupo = [x for x in resto if x.municipio == municipio]
        if not grupo:
            continue
        abierto = municipio in ("nacional", "chia") or lugar == municipio
        with st.expander(f"{nombre} ({len(grupo)})", expanded=abierto):
            for x in grupo:
                _tarjeta(x)
    st.caption(AVISO_CONFIRMAR)
    st.download_button("Descargar tarjeta para imprimir (Chía)", html_tarjeta(),
                       file_name="lineas_de_ayuda_chia.html", mime="text/html",
                       key="lin_descarga")


def html_tarjeta() -> str:
    """Una página imprimible con las líneas de Chía y las nacionales urgentes."""
    filas = []
    for x in la.directorio():
        if x.municipio in ("nacional", "chia") and x.tipo != "urgencias":
            tel = html.escape(x.telefono)
            filas.append(f"<tr><td><b>{html.escape(x.nombre)}</b></td><td>{tel}</td>"
                         f"<td>{html.escape(x.resumen)}"
                         + (f"<br><i>{html.escape(x.nota)}</i>" if x.nota else "")
                         + "</td></tr>")
    return ("<!doctype html><html lang='es'><meta charset='utf-8'>"
            "<title>Líneas de ayuda en salud mental · Chía</title>"
            "<style>body{font-family:sans-serif;max-width:720px;margin:24px auto}"
            "td{border-bottom:1px solid #ccc;padding:6px;vertical-align:top}"
            "h1{font-size:20px}</style>"
            "<h1>Si necesita ayuda en salud mental · Chía</h1>"
            "<p>Ante un peligro inmediato, llame al <b>123</b>.</p>"
            f"<table>{''.join(filas)}</table>"
            f"<p style='font-size:12px'>Fuente: {html.escape(la.FUENTE)}. {AVISO_CONFIRMAR}</p>"
            "</html>")
