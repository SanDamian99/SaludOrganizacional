"""
Figuras del mapa — Observatorio 360.

`figura_interactiva` (Plotly sobre OpenStreetMap) es la de la pantalla.
`figura_estatica` (matplotlib, sin tiles ni red) es la de los PDF y el video.
Las dos dibujan lo mismo: el contorno de Chía y un punto por colegio, con un
solo tono, sin rojo y sin semáforo.

Las etiquetas nunca se superponen. En la estática se mide el texto real y, si
junto al círculo no cabe, se aleja con una línea guía. En la interactiva no se
puede medir, así que se estima (ver `etiquetas`) y la que no cabe se oculta: su
nombre sigue en el hover y aparece al acercar el mapa.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from src.estudiantes import catalog as cat
from src.geo import colegios_geo, etiquetas
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
FIGSIZE = (7.5, 7.0)
# De la más grande a la más chica: se usa la mayor en la que caben todos los nombres.
FUENTES_PT = (9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5)


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


def _tamano(f: md.FilaMapa, capa: str) -> int:
    if f.estado != md.CON_CIFRA:
        return TAMANO_GRIS
    return TAMANOS.get(f.tramo, TAMANO_BASE) if capa == "respuestas" else TAMANO_BASE


def _orden(pares, capa):
    """Con cifra primero (los más grandes antes), luego los grises; por nombre."""
    return sorted(pares, key=lambda fp: (fp[0].estado != md.CON_CIFRA,
                                         -_tamano(fp[0], capa), fp[1].nombre))


# ── Interactiva ───────────────────────────────────────────────────────────────
def _posiciones_interactivas(pares, capa, lat_centro) -> dict[str, str | None]:
    """Posición de Plotly de cada etiqueta, o None si se oculta (ver `etiquetas`)."""
    px_por_grado = 256 * 2 ** ZOOM / 360
    k_lat = px_por_grado / math.cos(math.radians(lat_centro))
    items = [etiquetas.Item(p.codigo, p.lon * px_por_grado, p.lat * k_lat, p.nombre,
                            _tamano(f, capa) / 2) for f, p in pares]
    return etiquetas.colocar(items)


def figura_interactiva(filas, capa: str, puntos) -> go.Figure:
    pares = _orden(_con_punto(filas, puntos), capa)
    if not opciones.MAPA_MOSTRAR_SIN_CIFRA:
        pares = [(f, p) for f, p in pares if f.estado == md.CON_CIFRA]
    fig = go.Figure()
    anillos = colegios_geo.cargar_limite()
    for anillo in anillos:
        fig.add_trace(go.Scattermap(
            lon=[x for x, _ in anillo], lat=[y for _, y in anillo], mode="lines",
            line=dict(width=2, color=COLOR_LIMITE), hoverinfo="skip",
            showlegend=False))
    lat, lon = _centro(puntos, anillos)
    valores = [f.valor for f, _ in pares if f.estado == md.CON_CIFRA and capa != "respuestas"]
    lo, hi = _rango(valores) if valores else (0.0, 1.0)
    posicion = (_posiciones_interactivas(pares, capa, lat)
                if opciones.MAPA_MOSTRAR_NOMBRES else {})
    grupos: dict[tuple[bool, str | None], list] = {}
    for f, p in pares:
        grupos.setdefault((f.estado == md.CON_CIFRA, posicion.get(p.codigo)), []).append((f, p))
    escala_puesta = False
    for (con_cifra, pos), lista in sorted(grupos.items(),
                                          key=lambda kv: (not kv[0][0], str(kv[0][1]))):
        if con_cifra and capa != "respuestas":
            marcador = dict(size=TAMANO_BASE, color=[f.valor for f, _ in lista],
                            colorscale=ESCALA, cmin=lo, cmax=hi, opacity=0.95,
                            showscale=not escala_puesta,
                            colorbar=dict(title=md.ETIQUETAS_CAPA[capa], thickness=12))
            escala_puesta = True
        elif con_cifra:
            marcador = dict(size=[_tamano(f, capa) for f, _ in lista],
                            color=COLOR_PUNTO, opacity=0.9)
        else:
            marcador = dict(size=TAMANO_GRIS, color=COLOR_GRIS, opacity=0.8)
        rotulo = {"mode": "markers"}
        if pos is not None:
            rotulo = dict(mode="markers+text", text=[p.nombre for _, p in lista],
                          textposition=pos,
                          textfont=dict(size=12 if con_cifra else 11,
                                        color=COLOR_TEXTO if con_cifra else "#5F6368"))
        fig.add_trace(go.Scattermap(
            lon=[p.lon for _, p in lista], lat=[p.lat for _, p in lista],
            marker=marcador, customdata=[texto_hover(f, capa) for f, _ in lista],
            hovertemplate="%{customdata}<extra></extra>", showlegend=False, **rotulo))
    fig.update_layout(
        map=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=ZOOM),
        margin=dict(l=0, r=0, t=0, b=0), height=ALTURA, showlegend=False)
    return fig


# ── Estática ──────────────────────────────────────────────────────────────────
# 12 direcciones cada 30°, empezando por las diagonales (arriba a la derecha primero)
_DIRECCIONES = tuple((math.cos(math.radians(a)), math.sin(math.radians(a)))
                     for a in (45, 135, -45, -135, 0, 180, 90, -90,
                               15, 165, -15, -165))
_ANILLOS = 6          # cercano, y cinco más lejos con línea guía
_PASO_PT = 14         # lo que se aleja cada anillo, en puntos
_LARGO_MAX = 18       # los nombres más largos se parten en dos líneas


def _partir(nombre: str) -> str:
    """Parte un nombre largo en dos líneas, en el espacio más cercano al medio."""
    if len(nombre) <= _LARGO_MAX or " " not in nombre:
        return nombre
    medio = len(nombre) / 2
    cortes = [i for i, c in enumerate(nombre) if c == " "]
    i = min(cortes, key=lambda j: abs(j - medio))
    return nombre[:i] + "\n" + nombre[i + 1:]


def _caja_texto(texto, renderer):
    """Caja del texto solo: la de una anotación incluye la flecha hasta el punto."""
    texto.update_positions(renderer)     # aplica el desplazamiento antes de medir
    return Text.get_window_extent(texto, renderer)


def _etiquetar_estatica(fig, ax, marcas, fuente: float) -> int:
    """Pone cada nombre donde no choque con otro texto ni con un círculo.

    `marcas` es [(fila, punto, area_del_marcador)] en orden de prioridad. Mide el
    texto real con el renderizador; si junto al círculo no cabe, prueba más lejos
    (con línea guía). Devuelve cuántas etiquetas quedaron colocadas.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    k = fig.dpi / 72
    ocupado = []
    puestas = 0
    for _, p, area in marcas:
        cx, cy = ax.transData.transform((p.lon, p.lat))
        r = math.sqrt(area) / 2 * k
        ocupado.append(Bbox.from_extents(cx - r, cy - r, cx + r, cy + r))
    for _, p, area in marcas:
        radio_pt = math.sqrt(area) / 2
        colocada = False
        for anillo in range(_ANILLOS):
            distancia = radio_pt + 2 + anillo * _PASO_PT
            for dx, dy in _DIRECCIONES:
                texto = ax.annotate(
                    _partir(p.nombre), (p.lon, p.lat),
                    xytext=(dx * distancia, dy * distancia),
                    textcoords="offset points", fontsize=fuente, color=COLOR_TEXTO,
                    ha="left" if dx > 0.3 else "right" if dx < -0.3 else "center",
                    va="bottom" if dy > 0.3 else "top" if dy < -0.3 else "center",
                    linespacing=1.0,
                    arrowprops=(dict(arrowstyle="-", color=COLOR_GRIS, lw=0.6,
                                     shrinkA=0, shrinkB=0) if anillo else None))
                caja = _caja_texto(texto, renderer).expanded(1.04, 1.25)
                dentro = (caja.x0 >= fig.bbox.x0 and caja.x1 <= fig.bbox.x1
                          and caja.y0 >= fig.bbox.y0 and caja.y1 <= fig.bbox.y1)
                if dentro and not any(caja.overlaps(o) for o in ocupado):
                    ocupado.append(caja)
                    colocada = True
                    puestas += 1
                    break
                texto.remove()
            if colocada:
                break
    return puestas


def _por_aglomeracion(ax, marcas):
    """Primero los puntos con más vecinos cerca: son los que menos opciones tienen."""
    px = [ax.transData.transform((p.lon, p.lat)) for _, p, _ in marcas]
    cerca = [sum(1 for j, q in enumerate(px) if j != i
                 and math.hypot(q[0] - c[0], q[1] - c[1]) < 90)
             for i, c in enumerate(px)]
    orden = sorted(range(len(marcas)), key=lambda i: (-cerca[i], i))
    return [marcas[i] for i in orden]


def _etiquetar_lo_mejor_posible(fig, ax, marcas) -> None:
    """La fuente más grande en la que caben todos los nombres; si ninguna, la que más.

    Prueba dos órdenes de colocación (los más rodeados primero, y el de entrada).
    """
    fig.canvas.draw()
    ordenes = [_por_aglomeracion(ax, marcas), list(marcas)]
    mejor, mejor_n = (FUENTES_PT[-1], ordenes[0]), -1
    for fuente in FUENTES_PT:
        for orden in ordenes:
            n = _etiquetar_estatica(fig, ax, orden, fuente)
            if n == len(marcas):
                return
            if n > mejor_n:
                mejor, mejor_n = (fuente, orden), n
            for texto in list(ax.texts):
                texto.remove()
    _etiquetar_estatica(fig, ax, mejor[1], mejor[0])


def figura_estatica(filas, capa: str, puntos, nombres: bool | None = None) -> Figure:
    """Misma imagen sin tiles: contorno gris claro y puntos, para PDF y video.

    `nombres` manda sobre `opciones.MAPA_MOSTRAR_NOMBRES` cuando no es None (el video
    decide por separado si nombra los colegios).
    """
    pares = _orden(_con_punto(filas, puntos), capa)
    fig = Figure(figsize=FIGSIZE, dpi=150)
    FigureCanvasAgg(fig)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    ax = fig.subplots()
    anillos = colegios_geo.cargar_limite()
    for anillo in anillos:
        ax.fill([x for x, _ in anillo], [y for _, y in anillo], facecolor="#F1F3F4",
                edgecolor=COLOR_LIMITE, linewidth=1.2)
    con = [(f, p) for f, p in pares if f.estado == md.CON_CIFRA]
    sin = [(f, p) for f, p in pares if f.estado != md.CON_CIFRA]
    areas = {}
    if sin and opciones.MAPA_MOSTRAR_SIN_CIFRA:
        ax.scatter([p.lon for _, p in sin], [p.lat for _, p in sin], s=60,
                   color=COLOR_GRIS, alpha=0.8, zorder=3)
        areas.update({p.codigo: 60 for _, p in sin})
    if con:
        if capa == "respuestas":
            tamanos = [TAMANOS.get(f.tramo, TAMANO_BASE) ** 2 for f, _ in con]
            ax.scatter([p.lon for _, p in con], [p.lat for _, p in con], s=tamanos,
                       color=COLOR_PUNTO, alpha=0.9, zorder=4)
        else:
            lo, hi = _rango([f.valor for f, _ in con])
            mapa = LinearSegmentedColormap.from_list("obs360", [c for _, c in ESCALA])
            colores = [mapa((f.valor - lo) / (hi - lo)) for f, _ in con]
            tamanos = [260] * len(con)
            ax.scatter([p.lon for _, p in con], [p.lat for _, p in con], s=tamanos,
                       color=colores, edgecolors=COLOR_LIMITE, linewidths=0.6, zorder=4)
        areas.update({p.codigo: t for (_, p), t in zip(con, tamanos)})
    lat, _ = _centro(puntos, anillos)
    if anillos:
        xs = [x for a in anillos for x, _ in a]
        ys = [y for a in anillos for _, y in a]
        ax.set_xlim(min(xs) - 0.012, max(xs) + 0.012)
        ax.set_ylim(min(ys) - 0.006, max(ys) + 0.006)
    ax.set_aspect(1 / math.cos(math.radians(lat)))
    ax.axis("off")
    if opciones.MAPA_MOSTRAR_NOMBRES if nombres is None else nombres:
        marcas = [(f, p, areas[p.codigo]) for f, p in pares if p.codigo in areas]
        _etiquetar_lo_mejor_posible(fig, ax, marcas)
    return fig
