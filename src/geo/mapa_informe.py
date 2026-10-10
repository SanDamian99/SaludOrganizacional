"""
Mapa de Chía para los informes imprimibles — Observatorio 360.

Devuelve un bloque HTML con las figuras estáticas (SVG vectorial, sin red ni
tiles) incrustadas, para el informe de la Secretaría. Pasa por la misma
auditoría que el mapa de pantalla; si no pasa, levanta `AuditoriaMapa` y el
llamador deja el informe sin mapa. Nada de Streamlit aquí.
"""
from __future__ import annotations

import base64
import io
import logging
from html import escape

from src.estudiantes import catalog as cat
from src.geo import auditoria_mapa, colegios_geo, mapa_datos, mapa_figura, opciones

log = logging.getLogger(__name__)

CSS = """.mapa-informe{break-inside:avoid;margin:10px 0 14px}
.mapa-informe .mapas{display:flex;flex-wrap:wrap;gap:12px}
.mapa-informe figure{margin:0;flex:1 1 300px;max-width:100%}
.mapa-informe img{width:100%;height:auto;display:block}
.mapa-informe figcaption{font-size:11px;color:#5b6776;margin-top:3px}
.mapa-informe .nota{font-size:10.5px;color:#5b6776;margin:6px 0 0}"""


def svg_estatico(filas, capa: str, puntos) -> str:
    """La figura estática de la capa, como texto SVG."""
    fig = mapa_figura.figura_estatica(filas, capa, puntos)
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    return buf.getvalue()


def _figura(svg: str, capa: str) -> str:
    cuerpo = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    titulo = escape(mapa_datos.ETIQUETAS_CAPA[capa])
    return (f'<figure><img alt="Mapa de Chía: {titulo}" '
            f'src="data:image/svg+xml;base64,{cuerpo}">'
            f"<figcaption><b>{titulo}.</b> {escape(mapa_datos.LEYENDAS[capa])}"
            "</figcaption></figure>")


def bloque_html(analisis, visibles, pequenos) -> str:
    """Sección con el mapa; «» si el equipo la apagó o no hay puntos que dibujar."""
    if not opciones.MAPA_EN_INFORMES:
        return ""
    capas = opciones.capas_informe()
    if not capas:
        return ""
    puntos, avisos = colegios_geo.cargar_puntos()
    for aviso in avisos:
        log.warning("Mapa del informe: %s", aviso)
    if not puntos:
        return ""
    figuras = []
    for capa in capas:
        filas = mapa_datos.tabla_mapa(analisis, capa, [p.codigo for p in puntos],
                                      visibles, pequenos)
        auditoria_mapa.auditar(filas, capa, visibles, pequenos)
        figuras.append(_figura(svg_estatico(filas, capa, puntos), capa))
    notas = [mapa_datos.NOTA_LECTURA]
    if pequenos and opciones.MAPA_MOSTRAR_CAUSA_SIN_CIFRA:
        notas.insert(0, cat.CIFRAS_PEQUENAS)
    return (f"<style>{CSS}</style>"
            '<section class="mapa-informe"><h2>Dónde hay respuestas</h2>'
            f'<div class="mapas">{"".join(figuras)}</div>'
            + "".join(f'<p class="nota">{escape(n)}</p>' for n in notas)
            + "</section>")
