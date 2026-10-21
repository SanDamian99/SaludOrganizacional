"""
Docentes · resultado de cada ítem de una dimensión, por grupo.

Al final de «Explorar un indicador»: cada fila es una pregunta del cuestionario y
cada columna un grupo (colegio por defecto, o sexo, rango de edad, etc.), con un
filtro opcional por otro criterio. Las funciones puras (`escala_item`, `orientado`,
`tabla_items`, `fondo_zonas`, `figura_items`) no tocan Streamlit y las prueban los
tests; `render` es la única que dibuja.

Privacidad: la misma regla que el resto del módulo. Ningún grupo con menos de 10
docentes tiene columna (`universo.grupos_publicables`), ninguna celda se calcula
con menos de 10 respuestas y, con el filtro puesto, si quedan menos de 10 docentes
no se muestra nada.
"""
from __future__ import annotations

import textwrap
from html import escape

import pandas as pd
import plotly.graph_objects as go

from src.analysis import grupo_minimo as gm
from src.docentes import catalogo as cat
from src.docentes import enunciados, universo
from src.docentes import scoring as doc_scoring

TODOS = "Todos"
RANGO_EDAD = "Rango de edad"
SIN_FILTRO = "— sin filtro —"
FLECHA_INVERTIDO = " ↺"

# Del naranja (a vigilar) al verde (favorable), pasando por un neutro claro. Más
# suaves que los de las barras para que el número se lea encima.
ESCALA_COLOR = [[0.0, "#E8964A"], [0.5, "#F4EFE2"], [1.0, "#4FAE7E"]]


# ══ Funciones puras ═════════════════════════════════════════════════════════
def escala_item(dim: cat.Dimension) -> tuple[float, float]:
    """Escala de un ítem suelto: la de la dimensión si es media; si es suma, su parte."""
    lo, hi = dim.escala
    if dim.agregacion == "suma":
        n = len(dim.items)
        return lo / n, hi / n
    return lo, hi


def orientado(valor: float, dim: cat.Dimension) -> float | None:
    """Posición 0-100 del ítem en su escala, con 100 = lo más favorable."""
    if valor is None or pd.isna(valor) or dim.direccion is None:
        return None
    lo, hi = escala_item(dim)
    pct = min(100.0, max(0.0, (float(valor) - lo) / (hi - lo) * 100))
    return pct if dim.direccion == cat.MAYOR_MEJOR else 100 - pct


def etiqueta_item(columna: str) -> str:
    texto = enunciados.ENUNCIADOS.get(columna, columna)
    return texto + (FLECHA_INVERTIDO if columna in enunciados.INVERTIDOS else "")


def tabla_items(df: pd.DataFrame, dim: cat.Dimension, grupo: pd.Series | None,
                columnas: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(medias, n) con una fila por ítem y una columna por grupo más «Todos».

    `df` debe estar en la codificación 2 (`scoring.normalizar_codificacion`). Una
    celda con menos de 10 respuestas válidas queda en blanco.
    """
    X = pd.DataFrame({c: pd.to_numeric(df[c], errors="coerce") if c in df.columns
                      else pd.Series(float("nan"), index=df.index) for c in dim.items})
    desplazamiento = 0.0 if dim.agregacion == "suma" else dim.desplazamiento
    medias, ns = {}, {}

    def _celda(mask, nombre):
        sub = X[mask] if mask is not None else X
        n = sub.notna().sum()
        m = sub.mean() + desplazamiento
        medias[nombre] = m.where(n >= gm.N_MINIMO)
        ns[nombre] = n

    _celda(None, TODOS)
    g = grupo.astype(str) if grupo is not None else None
    for nombre in columnas:
        _celda(g == str(nombre), str(nombre))
    return pd.DataFrame(medias), pd.DataFrame(ns)


def fondo_zonas(dim: cat.Dimension) -> list[tuple[float, float, str]]:
    """Franjas (x0, x1, zona) del eje del puntaje: los cortes si hay, si no los tercios."""
    lo, hi = dim.escala
    if dim.cortes:
        return [(b.inferior, b.superior, b.zona) for b in sorted(dim.cortes, key=lambda b: b.inferior)]
    t = (hi - lo) / 3
    zonas = [cat.ZONA_VIGILAR, cat.ZONA_INTERMEDIA, cat.ZONA_FAVORABLE]
    if dim.direccion == cat.MAYOR_PEOR:
        zonas = zonas[::-1]
    return [(lo + i * t, lo + (i + 1) * t, z) for i, z in enumerate(zonas)]


def leyenda_zonas_html() -> str:
    """Tres puntos de color con su nombre: favorable, intermedia y a vigilar."""
    piezas = [
        f'<span style="white-space:nowrap;margin-right:16px">'
        f'<span style="color:{cat.COLOR_ZONA[z]};font-size:1.1em">●</span> '
        f'{cat.ETIQUETA_ZONA[z]}</span>'
        for z in (cat.ZONA_FAVORABLE, cat.ZONA_INTERMEDIA, cat.ZONA_VIGILAR)]
    return '<div style="margin:2px 0 10px 0;font-size:0.9em">' + "".join(piezas) + "</div>"


def color_celda(pct: float | None) -> str:
    """Color de fondo (hex) de una posición 0-100: la misma escala del mapa de calor."""
    if pct is None or pd.isna(pct):
        return ""
    p = min(100.0, max(0.0, float(pct))) / 100
    (a, ca), (b, cb) = ((0.0, ESCALA_COLOR[0][1]), (0.5, ESCALA_COLOR[1][1])) if p <= 0.5 \
        else ((0.5, ESCALA_COLOR[1][1]), (1.0, ESCALA_COLOR[2][1]))
    t = (p - a) / (b - a)
    rgb = [round(int(ca[i:i + 2], 16) + (int(cb[i:i + 2], 16) - int(ca[i:i + 2], 16)) * t)
           for i in (1, 3, 5)]
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def tabla_html_movil(medias: pd.DataFrame, ns: pd.DataFrame, dim: cat.Dimension) -> str:
    """Tabla con color para celular: pregunta fija a la izquierda y grupos que se desplazan.

    La columna de la pregunta se queda quieta (`position: sticky`) y el texto se
    ajusta; el resto de columnas mide lo justo y la tabla se desliza con el dedo.
    """
    celda = "padding:6px 3px;text-align:center;color:#1F2937;min-width:56px;border-radius:3px"
    pregunta = ("position:sticky;left:0;z-index:1;background:#FFFFFF;min-width:150px;"
                "max-width:150px;text-align:left;padding:4px 8px 4px 0;font-size:12px;"
                "line-height:1.25;color:#4B5563")
    cabeza = "".join(
        f'<th style="min-width:56px;padding:2px;font-size:11px;font-weight:600;'
        f'line-height:1.2;vertical-align:bottom">{escape(str(c))}<br>'
        f'<span style="font-weight:400;color:#6B7280">n={int(ns[c].max())}</span></th>'
        for c in medias.columns)
    filas = []
    for item in medias.index:
        celdas = []
        for col in medias.columns:
            v = medias.loc[item, col]
            fondo = color_celda(orientado(v, dim))
            texto = "—" if pd.isna(v) else f"{v:.2f}"
            estilo = celda + (f";background:{fondo}" if fondo else "")
            celdas.append(f'<td style="{estilo}">{texto}</td>')
        filas.append(f'<tr><td style="{pregunta}">{escape(etiqueta_item(item))}</td>'
                     + "".join(celdas) + "</tr>")
    return ('<div style="overflow-x:auto;max-width:100%">'
            '<table style="border-collapse:separate;border-spacing:2px;font-size:13px">'
            f'<thead><tr><th style="{pregunta}"></th>{cabeza}</tr></thead>'
            f'<tbody>{"".join(filas)}</tbody></table></div>')


def _envolver(texto: str, ancho: int = 52) -> str:
    return "<br>".join(textwrap.wrap(texto, ancho)) or texto


def figura_items(medias: pd.DataFrame, ns: pd.DataFrame, dim: cat.Dimension) -> go.Figure:
    filas = list(medias.index)
    completos = [etiqueta_item(c) for c in filas]
    z = [[orientado(v, dim) for v in medias.loc[c]] for c in filas]
    texto = [[("—" if pd.isna(v) else f"{v:.2f}") for v in medias.loc[c]] for c in filas]
    hover = [[f"{completos[i]}<br>{col}: media {texto[i][j]} · n={int(ns.loc[c, col])}"
              for j, col in enumerate(medias.columns)] for i, c in enumerate(filas)]
    columnas = [f"{_envolver(str(c), 11)}<br>n={int(ns[c].max())}" for c in medias.columns]
    fig = go.Figure(go.Heatmap(
        z=z, x=columnas, y=[_envolver(t) for t in completos],
        text=texto, texttemplate="%{text}", textfont={"color": "#1F2937", "size": 13},
        customdata=hover, hovertemplate="%{customdata}<extra></extra>",
        colorscale=ESCALA_COLOR, zmin=0, zmax=100, showscale=False,
        xgap=3, ygap=3, hoverongaps=False))
    fig.update_layout(
        height=max(220, 52 * len(filas) + 90),
        margin={"l": 10, "r": 10, "t": 60, "b": 10},
        xaxis={"side": "top", "automargin": True, "tickangle": 0, "tickfont": {"size": 10}},
        yaxis={"autorange": "reversed", "automargin": True})
    return fig


# ══ Interfaz ════════════════════════════════════════════════════════════════
def _opciones_agrupar(df: pd.DataFrame, grupos: list[str], etiqueta) -> dict[str, pd.Series]:
    """{nombre visible: serie de grupo}: colegio primero, luego el resto y el rango de edad."""
    out: dict[str, pd.Series] = {}
    if cat.COLUMNA_COLEGIO in grupos:
        out[etiqueta(cat.COLUMNA_COLEGIO)] = df[cat.COLUMNA_COLEGIO]
    for c in grupos:
        if c != cat.COLUMNA_COLEGIO and "fecha" not in str(c).lower():
            out[etiqueta(c)] = df[c]
    edad = next((c for c in df.columns if "edad" in str(c).lower()
                 and pd.api.types.is_numeric_dtype(df[c])), None)
    if edad is not None:
        out[RANGO_EDAD] = gm.agrupar_numerica(df[edad], 10)
    return out


def render(df: pd.DataFrame, dim: cat.Dimension, grupos: list[str], etiqueta=str) -> None:
    import streamlit as st

    if len(dim.items) < 2:
        return
    opciones = _opciones_agrupar(df, grupos, etiqueta)
    if not opciones:
        return
    lo, hi = escala_item(dim)
    sentido = "mejor" if dim.mayor_mejor else "peor"
    st.markdown("#### Resultado de cada ítem por grupo")
    st.caption(
        f"Cada fila es una pregunta de «{dim.nombre}» y cada columna un grupo. El número es la "
        f"media de la pregunta (escala {lo:g}–{hi:g}; en esta dimensión un valor alto es "
        f"{sentido}). El color va de naranja (a vigilar) a verde (favorable) según su posición "
        f"en esa escala: no son cortes clínicos."
        + (f" {FLECHA_INVERTIDO.strip()} marca una pregunta formulada al revés, ya invertida."
           if any(c in enunciados.INVERTIDOS for c in dim.items) else ""))

    nombres = list(opciones)
    c1, c2 = st.columns(2)
    agrupar = c1.selectbox("Agrupar por:", nombres, key="doc_items_por")
    criterios = [n for n in nombres if n != agrupar]
    filtro = c2.selectbox("Filtrar por (opcional):", [SIN_FILTRO, *criterios],
                          key="doc_items_filtro")
    base = df
    if filtro != SIN_FILTRO:
        serie_f = opciones[filtro].astype(str)
        valores = sorted(v for v in serie_f.dropna().unique() if v not in ("None", "nan"))
        elegidos = st.multiselect(f"{filtro}:", valores, key=f"doc_items_vals_{filtro}")
        if elegidos:
            base = df[serie_f.isin(elegidos)]
    if not gm.grupo_suficiente(len(base)):
        st.info(gm.MENSAJE_GRUPO_PEQUENO)
        return

    grupo = opciones[agrupar].loc[base.index]
    conteos = grupo.dropna().astype(str).value_counts()
    agg = pd.DataFrame({"grupo": conteos.index, "count": conteos.values})
    visibles, otros, absorbido, ocultos = universo.grupos_publicables(agg, "grupo")
    if visibles.empty:
        st.info("Ningún grupo llega a 10 docentes con estos filtros, así que no hay cifras por "
                "grupo. Prueba con otro agrupador o quita el filtro.")
        return
    columnas = visibles.sort_values("count", ascending=False)["grupo"].tolist()
    normal = doc_scoring.normalizar_codificacion(base)
    medias, ns = tabla_items(normal, dim, grupo, columnas)
    tabla = medias.copy()
    tabla.index = [etiqueta_item(c) for c in tabla.index]
    # Mapa de calor en escritorio; en celular (src/ui/movil.py) lo reemplaza la tabla con color.
    with st.container(key="doc_items_calor"):
        st.plotly_chart(figura_items(medias, ns, dim), width="stretch",
                        key=f"doc_items_fig_{dim.clave}")
    with st.container(key="doc_items_movil"):
        st.markdown(tabla_html_movil(medias, ns, dim), unsafe_allow_html=True)
    st.markdown(leyenda_zonas_html(), unsafe_allow_html=True)
    st.caption(universo.pie(visibles, "grupo", otros, absorbido, ocultos)
               + " Una celda en blanco tiene menos de 10 respuestas.")
    with st.container(key="doc_items_tabla"), st.expander("Ver como tabla"):
        st.dataframe(tabla.round(2), width="stretch")
