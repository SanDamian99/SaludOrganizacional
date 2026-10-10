"""
Figuras del mapa — Observatorio 360.

`figura_interactiva` (Plotly sobre OpenStreetMap) es la de la pantalla.
`figura_estatica` (matplotlib, sin tiles ni red) es la de los PDF y el video.
Las dos dibujan lo mismo: el contorno de Chía y un punto por colegio, con un
solo tono, sin rojo y sin semáforo.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

from src.estudiantes import catalog as cat
from src.geo import colegios_geo
from src.geo import mapa_datos as md
from src.geo import opciones

COLOR_PUNTO = "#1F5F8B"
COLOR_GRIS = "#9AA0A6"
COLOR_LIMITE = "#5F6368"
TAMANOS = {"100 o más": 24, "30 a 99": 17, "10 a 29": 11}
TAMANO_BASE = 16
TAMANO_GRIS = 10
CENTRO_POR_DEFECTO = (4.86, -74.06)
COLOR_TEXTO = "#202124"
# Un solo tono, de azul claro a oscuro; el más claro sigue viéndose sobre el mapa.
ESCALA = [[0, "#9ECAE1"], [1, "#08306B"]]
ZOOM = 11.5
ALTURA = 520


def texto_hover(fila: md.FilaMapa, capa: str) -> str:
    """Texto al pasar el cursor. Nunca lleva el número exacto de respuestas."""
    cabecera = f"<b>{fila.nombre}</b>"
    if fila.estado == md.PEQUENA:
        causa = (cat.CIFRAS_PEQUENAS if opciones.MAPA_MOSTRAR_CAUSA_SIN_CIFRA
                 else "Sin cifras")
        return f"{cabecera}<br>{causa}"
    if fila.estado == md.SIN_FORMULARIO:
        causa = ("Todavía no hay respuestas de este colegio."
                 if opciones.MAPA_MOSTRAR_CAUSA_SIN_CIFRA else "Sin cifras")
        return f"{cabecera}<br>{causa}"
    if fila.estado == md.SIN_INDICADOR:
        return f"{cabecera}<br>Sin cifra para este indicador."
    if capa == "respuestas":
        return f"{cabecera}<br>Respuestas recibidas: {fila.tramo or '10 o más'}"
    texto = f"{cabecera}<br>{md.ETIQUETAS_CAPA[capa]}: {fila.valor:.2f}"
    if opciones.MAPA_MOSTRAR_COMPARACION and fila.referencia is not None:
        texto += f"<br>Todo el municipio: {fila.referencia:.2f}"
    return texto


def _con_punto(filas, puntos):
    por_codigo = {p.codigo: p for p in puntos}
    return [(f, por_codigo[f.codigo]) for f in filas if f.codigo in por_codigo]


def _centro(puntos, anillos=None) -> tuple[float, float]:
    """Centro del contorno del municipio; si no carga, el de los puntos."""
    if anillos:
        xs = [x for a in anillos for x, _ in a]
        ys = [y for a in anillos for _, y in a]
        return (min(ys) + max(ys)) / 2, (min(xs) + max(xs)) / 2
    if not puntos:
        return CENTRO_POR_DEFECTO
    return (sum(p.lat for p in puntos) / len(puntos),
            sum(p.lon for p in puntos) / len(puntos))


def _rango(valores) -> tuple[float, float]:
    lo, hi = min(valores), max(valores)
    return (lo, hi) if hi > lo else (lo - 0.5, hi + 0.5)


def figura_interactiva(filas, capa: str, puntos) -> go.Figure:
    pares = _con_punto(filas, puntos)
    fig = go.Figure()
    anillos = colegios_geo.cargar_limite()
    for anillo in anillos:
        fig.add_trace(go.Scattermap(
            lon=[x for x, _ in anillo], lat=[y for _, y in anillo], mode="lines",
            line=dict(width=2, color=COLOR_LIMITE), hoverinfo="skip",
            showlegend=False))
    modo = "markers+text" if opciones.MAPA_MOSTRAR_NOMBRES else "markers"
    con = [(f, p) for f, p in pares if f.estado == md.CON_CIFRA]
    if con:
        marcador = dict(size=[TAMANOS.get(f.tramo, TAMANO_BASE) for f, _ in con],
                        color=COLOR_PUNTO, opacity=0.9)
        if capa != "respuestas":
            lo, hi = _rango([f.valor for f, _ in con])
            marcador = dict(size=TAMANO_BASE, color=[f.valor for f, _ in con],
                            colorscale=ESCALA, cmin=lo, cmax=hi, showscale=True,
                            colorbar=dict(title=md.ETIQUETAS_CAPA[capa], thickness=12),
                            opacity=0.95)
        fig.add_trace(go.Scattermap(
            lon=[p.lon for _, p in con], lat=[p.lat for _, p in con], mode=modo,
            marker=marcador, text=[p.nombre for _, p in con],
            textposition="top right", textfont=dict(size=12, color=COLOR_TEXTO),
            customdata=[texto_hover(f, capa) for f, _ in con],
            hovertemplate="%{customdata}<extra></extra>", showlegend=False))
    sin = [(f, p) for f, p in pares if f.estado != md.CON_CIFRA]
    if sin and opciones.MAPA_MOSTRAR_SIN_CIFRA:
        fig.add_trace(go.Scattermap(
            lon=[p.lon for _, p in sin], lat=[p.lat for _, p in sin], mode=modo,
            marker=dict(size=TAMANO_GRIS, color=COLOR_GRIS, opacity=0.8),
            text=[p.nombre for _, p in sin], textposition="top right",
            textfont=dict(size=11, color="#5F6368"),
            customdata=[texto_hover(f, capa) for f, _ in sin],
            hovertemplate="%{customdata}<extra></extra>", showlegend=False))
    lat, lon = _centro(puntos, anillos)
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=ZOOM),
        margin=dict(l=0, r=0, t=0, b=0), height=ALTURA, showlegend=False)
    return fig


def figura_estatica(filas, capa: str, puntos) -> Figure:
    """Misma imagen sin tiles: contorno gris claro y puntos, para PDF y video."""
    pares = _con_punto(filas, puntos)
    fig = Figure(figsize=(6.4, 6.0), dpi=150)
    ax = fig.subplots()
    for anillo in colegios_geo.cargar_limite():
        ax.fill([x for x, _ in anillo], [y for _, y in anillo], facecolor="#F1F3F4",
                edgecolor=COLOR_LIMITE, linewidth=1.2)
    con = [(f, p) for f, p in pares if f.estado == md.CON_CIFRA]
    sin = [(f, p) for f, p in pares if f.estado != md.CON_CIFRA]
    if sin and opciones.MAPA_MOSTRAR_SIN_CIFRA:
        ax.scatter([p.lon for _, p in sin], [p.lat for _, p in sin], s=60,
                   color=COLOR_GRIS, alpha=0.8, zorder=3)
    if con:
        if capa == "respuestas":
            ax.scatter([p.lon for _, p in con], [p.lat for _, p in con],
                       s=[TAMANOS.get(f.tramo, TAMANO_BASE) ** 2 for f, _ in con],
                       color=COLOR_PUNTO, alpha=0.9, zorder=4)
        else:
            lo, hi = _rango([f.valor for f, _ in con])
            mapa = LinearSegmentedColormap.from_list("obs360", [c for _, c in ESCALA])
            colores = [mapa((f.valor - lo) / (hi - lo)) for f, _ in con]
            ax.scatter([p.lon for _, p in con], [p.lat for _, p in con], s=260,
                       color=colores, edgecolors=COLOR_LIMITE, linewidths=0.6, zorder=4)
    if opciones.MAPA_MOSTRAR_NOMBRES:
        for f, p in pares:
            if f.estado == md.CON_CIFRA or opciones.MAPA_MOSTRAR_SIN_CIFRA:
                ax.annotate(p.nombre, (p.lon, p.lat), xytext=(6, 6),
                            textcoords="offset points", fontsize=7, color="#202124")
    lat, _ = _centro(puntos, colegios_geo.cargar_limite())
    ax.set_aspect(1 / math.cos(math.radians(lat)))
    ax.axis("off")
    fig.tight_layout()
    return fig
