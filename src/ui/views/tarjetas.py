"""
Tarjetas de la vista comunidad (cuidadores y estudiantes), alineadas.

Solo presentación: recibe las tarjetas que ya armaron `tarjetas()` de cada vista
(cifra, etiqueta, textos del catálogo, notas) y las dibuja en HTML/CSS:

  · Una rejilla con subgrid: título, cifra, etiqueta y nota ocupan la misma
    fila en todas las tarjetas, así las cifras quedan a la misma altura aunque
    los títulos o las etiquetas tengan largos distintos.
  · Hasta cinco por fila en escritorio, dos en tableta y una en el celular
    (consultas de contenedor: cuenta el ancho real de la columna principal).
  · «Qué significa» y «Qué hacer» van debajo, en un desplegable con una ficha
    por tarjeta, para que la fila de cifras se lea de un vistazo.
  · Colores derivados de `currentColor`: siguen el tema claro u oscuro de
    Streamlit. Naranja como máximo para el acento; nunca rojo.
  · Todo texto pasa por `html.escape`. No se escribe texto nuevo: solo los del
    catálogo y los encabezados «Qué significa» / «Qué hacer».
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

TITULO_EXPLICACIONES = "Qué significa y qué hacer"

_CSS = """<style>
.t360-marco{container:t360marco/inline-size}
.t360-grid{display:grid;
grid-template-columns:repeat(var(--t360-cols,var(--t360-n)),minmax(0,1fr));
grid-auto-rows:auto;column-gap:.75rem;row-gap:.75rem;margin:.25rem 0 .75rem}
.t360-card{display:grid;grid-row:span 4;grid-template-rows:subgrid;row-gap:.35rem;
padding:.8rem .75rem .75rem;border-radius:.6rem;
border:1px solid color-mix(in srgb,currentColor 16%,transparent);
border-top:3px solid #D9822B;
background:color-mix(in srgb,currentColor 3%,transparent);min-width:0}
.t360-card.t360-suprimida{border-top-color:color-mix(in srgb,currentColor 30%,transparent)}
.t360-titulo{font-weight:600;font-size:.95rem;line-height:1.3;min-height:2.6em;
overflow-wrap:anywhere}
.t360-cifra{font-size:clamp(1.2rem,calc(12.5cqi / var(--t360-cols,var(--t360-n))),2.1rem);font-weight:700;line-height:1.1;
font-variant-numeric:tabular-nums lining-nums;letter-spacing:-.01em;
align-self:start;overflow-wrap:anywhere}
.t360-suprimida .t360-cifra{color:color-mix(in srgb,currentColor 55%,transparent)}
.t360-etiqueta{font-size:.9rem;line-height:1.35;min-height:2.7em;overflow-wrap:anywhere}
.t360-nota{font-size:.78rem;line-height:1.35;
color:color-mix(in srgb,currentColor 68%,transparent);
font-variant-numeric:tabular-nums;align-self:start;overflow-wrap:anywhere}
.t360-exp{container:t360exp/inline-size;display:grid;row-gap:1rem}
.t360-exp-ficha{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);
column-gap:1.25rem;row-gap:.35rem;padding-top:.75rem;
border-top:1px solid color-mix(in srgb,currentColor 12%,transparent)}
.t360-exp-ficha:first-child{border-top:0;padding-top:0}
.t360-exp-titulo{grid-column:1/-1;font-weight:600}
.t360-exp-bloque{font-size:.92rem;line-height:1.5}
.t360-exp-encabezado{display:block;font-size:.75rem;font-weight:600;
text-transform:uppercase;letter-spacing:.04em;
color:color-mix(in srgb,currentColor 68%,transparent);margin-bottom:.15rem}
@container t360marco (max-width:760px){.t360-grid{--t360-cols:2}}
@container t360marco (max-width:440px){.t360-grid{--t360-cols:1}
.t360-titulo,.t360-etiqueta{min-height:0}}
@container t360exp (max-width:560px){.t360-exp-ficha{grid-template-columns:minmax(0,1fr)}}
.t360-grid[data-n="1"]{--t360-cols:1}
@supports not (grid-template-rows:subgrid){.t360-card{display:flex;flex-direction:column}}
</style>"""


@dataclass(frozen=True)
class Ficha:
    """Lo que la rejilla necesita de una tarjeta, venga de cuidadores o de estudiantes."""
    titulo: str
    cifra: str
    etiqueta: str
    detalle: str = ""
    significa: str = ""
    accion: str = ""
    suprimida: bool = False


def ficha(t, titulo: str | None = None) -> Ficha:
    """Adapta una `Tarjeta` de cualquiera de las dos vistas (sin tocar sus textos)."""
    return Ficha(titulo=titulo if titulo is not None else getattr(t, "titulo", ""),
                 cifra=t.cifra, etiqueta=t.etiqueta, detalle=t.detalle or "",
                 significa=t.significa, accion=t.accion,
                 suprimida=bool(getattr(t, "suprimida", False)))


def _e(texto) -> str:
    return escape("" if texto is None else str(texto), quote=True)


def _tarjeta_html(f: Ficha) -> str:
    clase = "t360-card t360-suprimida" if f.suprimida else "t360-card"
    return (f'<div class="{clase}" role="listitem">'
            f'<div class="t360-titulo">{_e(f.titulo)}</div>'
            f'<div class="t360-cifra">{_e(f.cifra)}</div>'
            f'<div class="t360-etiqueta">{_e(f.etiqueta)}</div>'
            f'<div class="t360-nota">{_e(f.detalle)}</div>'
            "</div>")


def rejilla_html(fichas: list[Ficha]) -> str:
    """Rejilla de tarjetas (sin «Qué significa» ni «Qué hacer»). Una sola línea de HTML."""
    if not fichas:
        return ""
    columnas = min(len(fichas), 5)
    cuerpo = "".join(_tarjeta_html(f) for f in fichas)
    return (_CSS + '<div class="t360-marco">'
            f'<div class="t360-grid" role="list" data-n="{columnas}" style="--t360-n:{columnas}">'
            + cuerpo + "</div></div>").replace("\n", "")


def explicaciones_html(fichas: list[Ficha]) -> str:
    """Una ficha por tarjeta: título y dos columnas, «Qué significa» y «Qué hacer»."""
    partes = []
    for f in fichas:
        hacer = (f'<div class="t360-exp-bloque"><span class="t360-exp-encabezado">'
                 f'Qué hacer</span>{_e(f.accion)}</div>' if f.accion else "")
        partes.append('<div class="t360-exp-ficha">'
                      f'<div class="t360-exp-titulo">{_e(f.titulo)}</div>'
                      '<div class="t360-exp-bloque"><span class="t360-exp-encabezado">'
                      f'Qué significa</span>{_e(f.significa)}</div>'
                      + hacer + "</div>")
    return (_CSS + '<div class="t360-exp">' + "".join(partes) + "</div>").replace("\n", "")


def render(fichas: list[Ficha], expandido: bool = False) -> None:
    """Dibuja la rejilla y, debajo, el desplegable con las explicaciones."""
    import streamlit as st

    if not fichas:
        return
    st.markdown(rejilla_html(fichas), unsafe_allow_html=True)
    with st.expander(TITULO_EXPLICACIONES, expanded=expandido):
        st.markdown(explicaciones_html(fichas), unsafe_allow_html=True)
