"""
Informes imprimibles de Cuidadores 360 — colegio, Secretaría y resumen de una página.

Mismo formato que los de estudiantes (`estudiantes_informe`: hoja HTML con
botón «Imprimir», y el resumen de una página en PDF con WeasyPrint o, si
falla, en HTML). Las cifras salen de las funciones de `cuidadores_comunidad`,
así que el informe no puede decir algo distinto de la pantalla.

Reglas:
  · Solo agregados de grupos con 10 o más cuidadores distintos; nunca casos.
  · El informe del colegio se compara con el total del municipio, nunca con
    otro colegio, y no trae la señal de autolesión (solo el estado general).
  · El de la Secretaría trae «Ánimo» por colegio (estado y %) y la autolesión
    solo como cifra de todo el municipio.
  · El resumen de una página cabe en una hoja carta también en el peor caso
    (rol municipio con la lista máxima de grupos en «Prioridad»).
  · Los textos vienen de `comunidad_catalogo`. La IA no redacta nada.
"""
from __future__ import annotations

import logging
from datetime import date
from html import escape

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import estudiantes_alertas as va
from src.ui.views import estudiantes_informe as inf_est

COLUMNAS_TABLA = {"castigo": "Castigo físico", "apoyo_familia": "Poco apoyo de la familia",
                  "hijo_alto": "Hijo con dificultades altas", "animo": "Ánimo bajo"}
MAX_TARJETAS_PAGINA = 4


def _e(texto) -> str:
    return escape(str(texto), quote=True)


def fecha_larga(d: date | None = None) -> str:
    return inf_est.fecha_larga(d)


def a_pdf(html: str) -> bytes | None:
    """PDF con WeasyPrint; None si falta la librería (la vista entrega el HTML)."""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception:                                      # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo generar el PDF de cuidadores")
        return None


def _comparar(p: dict, m: dict) -> str:
    return inf_est.comparar(p, m) if p and m else ""


def _tarjeta_html(ac, t: vc.Tarjeta, filtros: dict, con_municipio: bool) -> str:
    cuerpo = f'<p class="cifra">{_e(t.cifra)}</p><p class="etiqueta">{_e(t.etiqueta)}</p>'
    if t.suprimida:
        cuerpo += f'<p class="margen">{_e(cc.CIFRAS_PEQUENAS)}</p>'
    else:
        indicador = vc.INDICADOR_TARJETA.get(t.clave)
        if indicador and con_municipio:
            comp = _comparar(vc.proporcion(ac, indicador, filtros),
                             vc.proporcion(ac, indicador, {}))
            if comp:
                cuerpo += (f'<span class="chip chip-{comp}">'
                           f'{_e(inf_est.COMPARACION_TEXTO[comp])}</span>')
        if t.detalle:
            cuerpo += f'<p class="margen">{_e(t.detalle)}</p>'
    return (f'<article class="tarjeta"><h3>{_e(t.titulo)}</h3>{cuerpo}'
            f'<p class="significa"><b>Qué significa.</b> {_e(t.significa)}</p>'
            f'<p class="accion"><b>Qué hacer.</b> {_e(t.accion)}</p></article>')


def _tabla(ac, columna: str, indicadores: list[str], filtros: dict, titulo: str,
           nota: str = "") -> str:
    """Grupos × indicadores, cada celda comparada con el total del municipio."""
    indicadores = [k for k in indicadores if vc.proporcion(ac, k, {})]
    tablas = {k: vc.prevalencia_por(ac, k, columna, filtros) for k in indicadores}
    grupos: list[str] = []
    for t in tablas.values():
        for g in t["grupo"].astype(str):
            if g not in grupos:
                grupos.append(g)
    if not grupos:
        return ""
    grupos = vc._ordenar(columna, grupos)
    ref = {k: vc.proporcion(ac, k, {}) for k in indicadores}
    cabecera = "".join(f"<th>{_e(COLUMNAS_TABLA[k])}</th>" for k in indicadores)
    cuerpo = ""
    for g in grupos:
        celdas = ""
        for k in indicadores:
            sel = tablas[k][tablas[k]["grupo"].astype(str) == g]
            p = ({} if sel.empty else dict(pct=float(sel.iloc[0]["pct"]),
                                           ic_inf=float(sel.iloc[0]["ic_inf"]),
                                           ic_sup=float(sel.iloc[0]["ic_sup"]),
                                           n=int(sel.iloc[0]["n"])))
            celdas += inf_est._celda(p, ref[k])
        cuerpo += f'<tr><th scope="row">{_e(g)}</th>{celdas}</tr>'
    total = "".join(f'<td class="total">{ref[k]["pct"]:.0f} %</td>' for k in indicadores)
    return (f'<section class="bloque"><h2>{_e(titulo)}</h2><div class="desliza">'
            f'<table class="comparativa"><thead><tr><th></th>{cabecera}</tr></thead>'
            f'<tbody>{cuerpo}</tbody><tfoot><tr><th scope="row">Total del municipio</th>'
            f'{total}</tr></tfoot></table></div><p class="nota">Porcentaje del grupo y, debajo, '
            "su margen de error. ▲ más alto y ▼ más bajo que el total del municipio. Se "
            "compara, no se ranquea." + (f" {_e(nota)}" if nota else "") + "</p></section>")


def _ruta(rol: str) -> str:
    filas = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in cc.ruta(rol))
    return f'<section class="ruta"><h2>{_e(cc.TITULO_RUTA)}</h2><ul>{filas}</ul></section>'


def _avisos() -> str:
    textos = [cc.AVISO_TAMIZAJE, inf_est.NOTA_COMPARACION, cc.AVISO_EPDS, cc.AVISO_APOYO,
              cc.AVISO_MINIMO, cc.AVISO_SIN_OLAS]
    return '<footer class="avisos">' + "".join(f"<p>{_e(t)}</p>" for t in textos) + "</footer>"


def _documento(titulo: str, cuerpo: str) -> str:
    return inf_est._documento(titulo, cuerpo, va.CSS_INFORME)


def _encabezado(titulo: str, meta: str, marca: str) -> str:
    return inf_est._encabezado(marca, titulo, meta)


def informe_colegio_html(ac, colegio: str, fecha: date | None = None) -> str:
    """Informe de un colegio. ValueError si el colegio no tiene cifras de cuidadores."""
    if colegio not in vc.grupos(ac, "Colegio"):
        raise ValueError(f"El colegio {colegio} no tiene resultados de cuidadores que se puedan "
                         "mostrar.")
    filtros = {"colegio": colegio, "grado": vc.TODOS}
    panel = vc.panel_html(ac, "colegio", filtros)
    fichas = vc.tarjetas(ac, "colegio", filtros, panel_dibujado=bool(panel))
    n = vc.n_grupo(ac, filtros)
    meta = f"{n} cuidadores respondieron · {fecha_larga(fecha)}" if n else fecha_larga(fecha)
    cuerpo = (_encabezado(colegio, meta,
                          "Observatorio 360 · Cuidadores · Informe para el colegio")
              + '<p class="leer">Cada resultado trae la cifra de los cuidadores del colegio, cómo '
                "se compara con el total del municipio y qué puede hacer el colegio. Son cifras "
                "del grupo: ningún dato corresponde a una persona.</p>"
              + panel + '<h2>Resultados y qué hacer</h2><div class="tarjetas">'
              + "".join(_tarjeta_html(ac, t, filtros, True) for t in fichas) + "</div>"
              + _tabla(ac, "Grado", ["castigo", "apoyo_familia", "hijo_alto", "animo"], filtros,
                       "Por grado en el colegio",
                       nota=f"Los grados con menos de {cat.MIN_GROUP_N} cuidadores no se "
                            "muestran.")
              + _ruta("colegio") + _avisos())
    return _documento(f"Informe Cuidadores 360 · {colegio}", cuerpo)


def informe_secretaria_html(ac, fecha: date | None = None) -> str:
    """Informe para la Secretaría: total del municipio, señales y comparación entre grupos."""
    if ac is None or getattr(ac.cuidador, "n", 0) < cat.MIN_GROUP_N:
        raise ValueError("No hay resultados de cuidadores con base suficiente.")
    panel = vc.panel_html(ac, "municipio", {})
    fichas = vc.tarjetas(ac, "municipio", {}, panel_dibujado=bool(panel))
    meta = (f"{vc.n_grupo(ac, {})} cuidadores · {len(vc.grupos(ac, 'Colegio'))} colegios con "
            f"resultados · {fecha_larga(fecha)}")
    indicadores = list(COLUMNAS_TABLA)
    cuerpo = (_encabezado("Chía · total del municipio", meta,
                          "Observatorio 360 · Cuidadores · Informe para la Secretaría")
              + '<p class="leer">Primero el total del municipio y qué hacer desde la política '
                "pública; después, cómo se ubica cada colegio y cada grado frente a ese total. "
                "Son cifras de grupo: ningún dato corresponde a una persona.</p>"
              + panel + '<h2>Resultados y qué hacer</h2><div class="tarjetas">'
              + "".join(_tarjeta_html(ac, t, {}, False) for t in fichas) + "</div>"
              + vc.tabla_secretaria_html(ac)
              + _tabla(ac, "Colegio", indicadores, {}, "Por colegio")
              + _tabla(ac, "Grado", indicadores, {}, "Por grado")
              + _ruta("municipio") + _avisos())
    return _documento("Informe Cuidadores 360 · Secretaría", cuerpo)


def informe_una_pagina_html(ac, rol: str, filtros: dict | None = None,
                            fecha: date | None = None) -> str:
    """Hoja de una página con lo esencial del grupo que está en pantalla."""
    filtros = filtros or {}
    if ac is None:
        raise ValueError("No hay resultados de cuidadores.")
    con_municipio = vc.hay_filtro(filtros)
    caja = vc.panel_html(ac, rol, filtros, compacto=True)
    fichas = vc.tarjetas(ac, rol, filtros,
                         panel_dibujado=bool(caja) and rol != "familia")[:MAX_TARJETAS_PAGINA]
    n = vc.n_grupo(ac, filtros)
    partes_meta = ([f"{n} cuidadores"] if n else []) + [f"Para: {cc.ROLES.get(rol, rol)}",
                                                        fecha_larga(fecha)]
    if fichas:
        tiles = "".join(
            f'<div class="tile"><h3>{_e(t.titulo)}</h3><p class="cifra">{_e(t.cifra)}</p>'
            f'<p class="etiqueta">{_e(t.etiqueta)}</p>'
            + (f'<p class="margen">{_e(cc.CIFRAS_PEQUENAS if t.suprimida else t.detalle)}</p>'
               if (t.suprimida or t.detalle) else "")
            + f'<div class="hacer"><b>Qué hacer:</b> {_e(t.accion)}</div></div>'
            for t in fichas)
        contenido = caja + f'<h2>Lo más importante y qué hacer</h2><div class="tiles">{tiles}</div>'
    else:
        contenido = caja + f"<p>{_e(cc.SIN_SUBGRUPO)}</p>"
    ruta = "".join(f"<li><b>{_e(a)}</b> — {_e(b)}</li>" for a, b in cc.ruta(rol))
    avisos = [cc.AVISO_TAMIZAJE] + ([inf_est.NOTA_COMPARACION] if con_municipio else [])
    cuerpo = ('<div class="banda"><div class="marca">Observatorio 360 · Cuidadores · '
              f'Resumen de una página</div><h1>{_e(vc.etiqueta_filtro(filtros))}</h1>'
              f'<div class="meta">{_e(" · ".join(partes_meta))}</div></div>'
              + contenido
              + f'<div class="ruta"><h2>{_e(cc.TITULO_RUTA)}</h2><ul>{ruta}</ul></div>'
              + '<div class="pie">' + "".join(f"<p>{_e(t)}</p>" for t in avisos) + "</div>")
    return ("<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
            f"<title>Resumen Cuidadores 360 · {_e(vc.etiqueta_filtro(filtros))}</title>"
            f"<style>{inf_est._CSS_PAGINA}{va.CSS_PAGINA}</style></head><body>{cuerpo}"
            "</body></html>")
