"""
Informes imprimibles de Estudiantes 360 — uno por colegio y uno para la Secretaría.

Son páginas HTML autocontenidas: se abren en cualquier navegador y desde ahí se
imprimen o se guardan como PDF. Conviven con el PDF de docentes a propósito, para
que el equipo compare los dos formatos antes de decidir cómo se harán los
informes (acordado el 28 de septiembre de 2026).

Reglas que este archivo respeta, las mismas de la vista comunidad:
  · Solo cifras agregadas de grupos con al menos `catalog.MIN_GROUP_N` casos.
    Nunca una fila, un nombre ni un grupo pequeño.
  · Todos los textos sobre salud mental salen de `catalog` (MENSAJES,
    RUTA_ATENCION, avisos). Aquí solo se añaden títulos, etiquetas y la
    instrucción de impresión.
  · Las cifras salen de las funciones de `estudiantes_comunidad`, así que el
    informe no puede decir algo distinto de lo que muestra la pantalla.
  · El informe de un colegio se compara con el total del municipio, nunca con
    otro colegio: un rector no ve las cifras de los demás.
"""
from __future__ import annotations

import logging
from datetime import date
from html import escape

from src.estudiantes import catalog as cat
from src.estudiantes.ingest import nombre_colegio
from src.ui.views import estudiantes_comunidad as vc

# Encabezados cortos para las tablas comparativas. Solo nombran lo que se mide.
COLUMNAS_TABLA: dict[str, str] = {
    "sdq_alto": "Dificultades altas",
    "emocional": "Síntomas emocionales altos",
    "adulto_confianza": "Sin adulto de confianza",
    "ideacion": "Piensa en la muerte con frecuencia",
    "irritabilidad": "Irritabilidad sobre el corte",
}

# Columnas de la tabla por grado dentro del informe de un colegio: las que
# tienen un «priorizar los grados» o equivalente en el catálogo.
COLUMNAS_GRADO_COLEGIO = ["sdq_alto", "adulto_confianza", "ideacion"]

# Cómo se nombra cada extremo de un contraste protector.
POLOS_CONTRASTE = {
    "apoyo_familia": ("Siente mucho apoyo en casa", "Siente poco apoyo en casa"),
    "pertenencia": ("Se siente muy parte del colegio", "Se siente poco parte del colegio"),
}

COMPARACION_TEXTO = {
    "mayor": "Más alto que en el municipio",
    "menor": "Más bajo que en el municipio",
    "similar": "Parecido al municipio",
}

NOTA_COMPARACION = ("«Más alto» o «más bajo» solo se dice cuando la cifra del municipio "
                    "queda fuera del margen de error del grupo (intervalo de Wilson al 95 %). "
                    "Si no, la diferencia puede ser azar y se lee como parecida.")

INSTRUCCION_IMPRESION = (
    "Para imprimir o guardar como PDF: pulse «Imprimir» (o Ctrl + P en Windows, "
    "⌘ + P en Mac). En «Destino» elija su impresora o «Guardar como PDF». En «Más "
    "ajustes» active «Gráficos de fondo» para que se vean los colores. Papel carta "
    "o A4, vertical.")

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]

EXCLUIDOS = {"OTRO", "SIN_DATO"}


# ══ Funciones de datos (puras) ═════════════════════════════════════════════
def fecha_larga(d: date | None = None) -> str:
    d = d or date.today()
    return f"{d.day} de {_MESES[d.month - 1]} de {d.year}"


def colegios_del_nivel(analisis) -> list[str]:
    """Colegios del nivel con cifras publicables (base o subgrupos publicados)."""
    if analisis is None:
        return []
    return [g for g in vc.grupos_publicables(analisis, "Colegio") if g not in EXCLUIDOS]


def colegios_con_informe(analisis: dict) -> list[str]:
    """Colegios que tienen informe en al menos un nivel, ordenados por nombre."""
    codigos = {c for a in (analisis or {}).values() for c in colegios_del_nivel(a)}
    return sorted(codigos, key=lambda c: nombre_colegio(c).lower())


def comparar(grupo: dict, municipio: dict) -> str:
    """'mayor', 'menor' o 'similar' según el IC del grupo; '' si falta una cifra."""
    if not grupo or not municipio:
        return ""
    if municipio["pct"] < grupo["ic_inf"]:
        return "mayor"
    if municipio["pct"] > grupo["ic_sup"]:
        return "menor"
    return "similar"


def _niveles(analisis: dict) -> list[str]:
    orden = [n for n in (cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA) if n in (analisis or {})]
    return orden + [n for n in (analisis or {}) if n not in orden]


def _nivel_valido(a) -> bool:
    return a is not None and getattr(a, "n", 0) >= cat.MIN_GROUP_N


# ══ Piezas HTML ════════════════════════════════════════════════════════════
def _e(texto) -> str:
    return escape(str(texto), quote=True)


def _pct(v: float) -> str:
    return f"{v:.0f} %"


def _barra_bandas(etiqueta: str, b: dict) -> str:
    tramos = "".join(
        f'<span style="width:{p:.2f}%;background:{vc.COLORES_BANDAS[i]}" '
        f'title="{_e(b["etiquetas"][i])}: {_pct(p)}">{_pct(p) if p >= 6 else ""}</span>'
        for i, p in enumerate(b["pct"]))
    return (f'<div class="bandas-fila"><div class="bandas-etq">{_e(etiqueta)}'
            f'<small>{b["n"]} estudiantes</small></div>'
            f'<div class="bandas-barra">{tramos}</div></div>')


def _leyenda_bandas(etiquetas: list[str]) -> str:
    return '<div class="leyenda">' + "".join(
        f'<span><i style="background:{vc.COLORES_BANDAS[i]}"></i>{_e(t)}</span>'
        for i, t in enumerate(etiquetas)) + "</div>"


def _bloque_bandas(filas: list[tuple[str, dict]]) -> str:
    filas = [(etq, b) for etq, b in filas if b]
    if not filas:
        return ""
    return ('<section class="bloque"><h2>Cómo está el grupo</h2>'
            '<p class="sub">Dificultades emocionales y de comportamiento (SDQ), en cuatro '
            'niveles.</p>'
            + "".join(_barra_bandas(etq, b) for etq, b in filas)
            + _leyenda_bandas(filas[0][1]["etiquetas"]) + "</section>")


def _barra_simple(etiqueta: str, pct: float, clase: str = "") -> str:
    return (f'<div class="barra-fila {clase}"><span class="barra-etq">{_e(etiqueta)}</span>'
            f'<span class="barra-pista"><span style="width:{min(pct, 100):.2f}%"></span></span>'
            f'<span class="barra-val">{_pct(pct)}</span></div>')


def _chip(comparacion: str) -> str:
    if not comparacion:
        return ""
    return f'<span class="chip chip-{comparacion}">{COMPARACION_TEXTO[comparacion]}</span>'


def _tarjeta_html(t: vc.Tarjeta, cuerpo: str) -> str:
    titulo = cat.MENSAJES[t.clave].titulo if t.clave in cat.MENSAJES else ""
    return (f'<article class="tarjeta"><h3>{_e(titulo)}</h3>{cuerpo}'
            f'<p class="significa"><b>Qué significa.</b> {_e(t.significa)}</p>'
            f'<p class="accion"><b>Qué hacer.</b> {_e(t.accion)}</p></article>')


def _cuerpo_tarjeta(a, t: vc.Tarjeta, filtros: dict, etiqueta_grupo: str,
                    con_municipio: bool) -> tuple[str, str]:
    """(HTML con cifra y barras, comparación con el municipio o '')."""
    if t.clave in vc.INDICADORES:
        p = vc.prevalencia(a, t.clave, filtros)
        m = vc.prevalencia(a, t.clave, {}) if con_municipio else {}
        comp = comparar(p, m) if con_municipio else ""
        barras = _barra_simple(etiqueta_grupo, p["pct"])
        if m:
            barras += _barra_simple("Municipio", m["pct"], "ref")
        cuerpo = (f'<p class="cifra">{_e(t.cifra)}</p>'
                  f'<p class="etiqueta">{_e(t.etiqueta)}</p>{barras}{_chip(comp)}'
                  f'<p class="margen">Margen de error {p["ic_inf"]:.0f}–{p["ic_sup"]:.0f} %'
                  f' · base de {p["n"]} estudiantes</p>')
        return cuerpo, comp
    if t.clave == "emocional_sexo":
        tabla = vc.prevalencia_por_sexo(a, filtros)
        barras = "".join(_barra_simple(str(f["grupo"]), f["pct"]) for _, f in tabla.iterrows())
        cuerpo = ('<p class="etiqueta">con síntomas emocionales en nivel alto, por sexo</p>'
                  + barras)
        return cuerpo, ""
    c = vc.contraste(a, t.clave, filtros)
    mucho, poco = POLOS_CONTRASTE.get(t.clave, ("Mucho", "Poco"))
    cuerpo = ('<p class="etiqueta">en el nivel más alto de malestar, '
              f'{_e(vc.CONTRASTES[t.clave]["etiqueta"])}</p>'
              + _barra_simple(mucho, c["pct_tercil_alto"])
              + _barra_simple(poco, c["pct_tercil_bajo"], "alerta")
              + f'<p class="margen">{vc.uno_de_cada(c["pct_tercil_alto"])} frente a '
                f'{vc.uno_de_cada(c["pct_tercil_bajo"])} (n = {int(c["n_alto"])} y '
                f'{int(c["n_bajo"])})</p>')
    return cuerpo, ""


def _bloque_items(items: list[dict]) -> str:
    if not items:
        return ""
    filas = "".join(
        f'<div class="barra-fila"><span class="barra-etq">{_e(it["enunciado"])}</span>'
        f'<span class="barra-pista"><span style="width:{(it["media"] - 1) / 4 * 100:.2f}%">'
        f'</span></span><span class="barra-val">{it["media"]:.1f} / 5</span></div>'
        for it in items)
    return ('<section class="bloque"><h2>Lo que menos sienten en el colegio</h2>'
            '<p class="sub">Los cuatro enunciados de pertenencia con la media más baja '
            '(1 = nada de acuerdo, 5 = totalmente de acuerdo). Los negativos se leen en '
            'positivo.</p>' + filas + "</section>")


def _celda(p: dict, ref: dict) -> str:
    if not p:
        return '<td class="vacia">—</td>'
    comp = comparar(p, ref)
    marca = {"mayor": " ▲", "menor": " ▼"}.get(comp, "")
    return (f'<td class="c-{comp or "similar"}">{_pct(p["pct"])}{marca}'
            f'<small>{p["ic_inf"]:.0f}–{p["ic_sup"]:.0f}</small></td>')


def _tabla_comparativa(a, columna: str, indicadores: list[str], filtros: dict,
                       titulo: str, etiqueta_grupo, nota: str = "") -> str:
    """Tabla grupos × indicadores; cada celda se compara con el total del nivel."""
    indicadores = [k for k in indicadores if vc.prevalencia(a, k, {})]
    tablas = {k: vc.prevalencia_por(a, k, columna, filtros) for k in indicadores}
    grupos: list[str] = []
    for t in tablas.values():
        for g in (t["grupo"].astype(str).tolist() if not t.empty else []):
            if g not in grupos and g not in EXCLUIDOS:
                grupos.append(g)
    if not grupos:
        return ""
    if columna == "Colegio":
        grupos.sort(key=lambda g: nombre_colegio(g).lower())
    ref = {k: vc.prevalencia(a, k, {}) for k in indicadores}
    cabecera = "".join(f"<th>{_e(COLUMNAS_TABLA[k])}</th>" for k in indicadores)
    cuerpo = ""
    for g in grupos:
        celdas = ""
        for k in indicadores:
            fila = tablas[k][tablas[k]["grupo"].astype(str) == g] if not tablas[k].empty else None
            p = ({} if fila is None or fila.empty else
                 dict(pct=float(fila.iloc[0]["pct"]), ic_inf=float(fila.iloc[0]["ic_inf"]),
                      ic_sup=float(fila.iloc[0]["ic_sup"]), n=int(fila.iloc[0]["n"])))
            celdas += _celda(p, ref[k])
        n = next((int(t[t["grupo"].astype(str) == g].iloc[0]["n"]) for t in tablas.values()
                  if not t.empty and (t["grupo"].astype(str) == g).any()), None)
        cuerpo += (f'<tr><th scope="row">{_e(etiqueta_grupo(g))}'
                   f'<small>{n} estudiantes</small></th>{celdas}</tr>')
    total = "".join(f'<td class="total">{_pct(ref[k]["pct"])}</td>' for k in indicadores)
    return (f'<section class="bloque"><h2>{_e(titulo)}</h2>'
            '<div class="desliza"><table class="comparativa"><thead><tr><th></th>'
            + cabecera + "</tr></thead>"
            f"<tbody>{cuerpo}</tbody><tfoot><tr><th scope=\"row\">Total del municipio</th>"
            f"{total}</tr></tfoot></table></div>"
            '<p class="nota">Porcentaje del grupo y, debajo, su margen de error. ▲ más alto y '
            '▼ más bajo que el total del municipio. Se compara, no se ranquea.'
            + (f" {_e(nota)}" if nota else "") + "</p></section>")


def _bloque_ruta() -> str:
    filas = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in cat.RUTA_ATENCION)
    return f'<section class="ruta"><h2>Si un estudiante necesita ayuda</h2><ul>{filas}</ul></section>'


def _avisos(niveles: list[str], notas: list[str] | None = None) -> str:
    textos = [cat.AVISO_TAMIZAJE, NOTA_COMPARACION, *[n for n in (notas or []) if n]]
    if cat.NIVEL_PRIMARIA in niveles:
        textos.append(cat.AVISO_PRIMARIA)
    textos.append(cat.AVISO_NORMAS)
    return '<footer class="avisos">' + "".join(f"<p>{_e(t)}</p>" for t in textos) + "</footer>"


def _resumen(comparaciones: list[tuple[str, str, dict, dict]]) -> str:
    """Caja «En resumen» con lo que queda por encima o por debajo del municipio."""
    mayores = [(t, p, m) for t, comp, p, m in comparaciones if comp == "mayor"]
    menores = [(t, p, m) for t, comp, p, m in comparaciones if comp == "menor"]
    if not comparaciones:
        return ""

    def lista(filas):
        return "".join(f"<li>{_e(t)}: {_pct(p['pct'])} frente a {_pct(m['pct'])} en el "
                       "municipio</li>" for t, p, m in filas)
    partes = []
    if mayores:
        partes.append(f"<p><b>Más alto que en el municipio</b></p><ul>{lista(mayores)}</ul>")
    if menores:
        partes.append(f"<p><b>Más bajo que en el municipio</b></p><ul>{lista(menores)}</ul>")
    if not partes:
        partes.append("<p>En todos los indicadores el colegio está en un rango parecido al "
                      "del municipio: las cifras de abajo son las del colegio y las acciones "
                      "aplican igual.</p>")
    return '<section class="resumen"><h2>En resumen</h2>' + "".join(partes) + "</section>"


# ══ Documento ══════════════════════════════════════════════════════════════
_CSS = """
:root{--tinta:#1d2733;--suave:#5b6776;--linea:#dde3ea;--fondo:#eef1f5;--hoja:#fff;
--azul:#2E5FAC;--ref:#a9b4c2;--alto:#C0392B;--bajo:#1A7F4B;--acento:#16365f}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
font:15px/1.45 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
-webkit-print-color-adjust:exact;print-color-adjust:exact}
.imprimir{position:sticky;top:0;z-index:5;background:var(--acento);color:#fff;
padding:12px 16px;display:flex;gap:16px;align-items:center;justify-content:center;flex-wrap:wrap}
.imprimir p{margin:0;max-width:720px;font-size:13.5px}
.imprimir button{background:#fff;color:var(--acento);border:0;border-radius:6px;
padding:9px 18px;font-weight:700;font-size:14px;cursor:pointer}
.hoja{background:var(--hoja);max-width:820px;margin:24px auto;padding:36px 44px;
border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.encabezado{border-bottom:3px solid var(--acento);padding-bottom:12px;margin-bottom:18px}
.encabezado .marca{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--suave)}
.encabezado h1{margin:4px 0 2px;font-size:26px;line-height:1.2}
.encabezado .meta{color:var(--suave);font-size:13.5px}
.leer{background:#f5f7fa;border-left:4px solid var(--azul);padding:10px 14px;margin:0 0 18px;font-size:14px}
h2{font-size:17px;margin:0 0 6px;color:var(--acento)}
.sub{margin:0 0 10px;color:var(--suave);font-size:13px}
.bloque{margin:0 0 22px;break-inside:avoid}
.resumen{border:1px solid var(--linea);border-radius:6px;padding:12px 16px;margin:0 0 22px;break-inside:avoid}
.resumen p{margin:6px 0 2px}.resumen ul{margin:2px 0 6px;padding-left:20px}
.bandas-fila{display:flex;align-items:center;gap:10px;margin:6px 0}
.bandas-etq{width:150px;font-weight:600;font-size:13.5px}
.bandas-etq small{display:block;font-weight:400;color:var(--suave);font-size:12px}
.bandas-barra{flex:1;display:flex;height:26px;border-radius:4px;overflow:hidden}
.bandas-barra span{display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:600;
white-space:nowrap;overflow:hidden}
.leyenda{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:12.5px;color:var(--suave)}
.leyenda i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.tarjetas{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:0 0 22px}
.tarjeta{border:1px solid var(--linea);border-radius:6px;padding:12px 14px;break-inside:avoid}
.tarjeta h3{margin:0 0 4px;font-size:14.5px}
.cifra{font-size:24px;font-weight:700;margin:2px 0 0;color:var(--acento)}
.etiqueta{margin:0 0 8px;font-size:13.5px}
.significa,.accion{font-size:13px;margin:8px 0 0}
.accion{background:#f5f7fa;border-radius:4px;padding:7px 9px}
.margen{margin:4px 0 0;font-size:11.5px;color:var(--suave)}
.barra-fila{display:grid;grid-template-columns:minmax(90px,38%) 1fr 48px;gap:8px;align-items:center;margin:4px 0;font-size:12.5px}
.bloque .barra-fila{grid-template-columns:minmax(160px,55%) 1fr 52px;font-size:13px}
.barra-pista{height:12px;background:#eef1f5;border-radius:3px;overflow:hidden}
.barra-pista span{display:block;height:100%;background:var(--azul)}
.barra-fila.ref .barra-pista span{background:var(--ref)}
.barra-fila.alerta .barra-pista span{background:var(--alto)}
.barra-val{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.chip{display:inline-block;margin-top:6px;padding:2px 9px;border-radius:10px;font-size:12px;font-weight:600}
.chip-mayor{background:#fbe9e7;color:var(--alto)}.chip-menor{background:#e6f4ec;color:var(--bajo)}
.chip-similar{background:#eef1f5;color:var(--suave)}
.desliza{overflow-x:auto;-webkit-overflow-scrolling:touch}
.comparativa{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
.comparativa th,.comparativa td{border-bottom:1px solid var(--linea);padding:6px 8px;text-align:center;vertical-align:top}
.comparativa thead th{font-size:12px;color:var(--suave);font-weight:600}
.comparativa tbody th,.comparativa tfoot th{text-align:left}
.comparativa small{display:block;font-size:10.5px;color:var(--suave);font-weight:400}
.comparativa .c-mayor{color:var(--alto);font-weight:700}.comparativa .c-menor{color:var(--bajo);font-weight:700}
.comparativa tfoot td,.comparativa tfoot th{font-weight:700;border-bottom:0}
.nota{font-size:11.5px;color:var(--suave);margin:6px 0 0}
.ruta{border:2px solid var(--alto);border-radius:6px;padding:10px 16px;margin:0 0 18px;break-inside:avoid}
.ruta h2{color:var(--alto)}.ruta ul{margin:4px 0;padding-left:18px;font-size:13.5px}
.avisos{border-top:1px solid var(--linea);padding-top:8px}
.avisos p{font-size:11px;color:var(--suave);margin:4px 0}
.nivel+.nivel{break-before:page;margin-top:28px}
.nivel>h2.titulo-nivel{font-size:19px;border-bottom:1px solid var(--linea);padding-bottom:4px;margin-bottom:12px}
@media (max-width:640px){.hoja{padding:20px 16px;margin:0;border-radius:0}.tarjetas{grid-template-columns:1fr}
.bandas-etq{width:96px}.comparativa{font-size:11.5px}}
@page{margin:13mm 12mm}
@media print{body{background:#fff;font-size:11px;line-height:1.35}.imprimir{display:none}
.hoja{box-shadow:none;margin:0;padding:0;max-width:none;border-radius:0}
.encabezado{padding-bottom:6px;margin-bottom:10px}.encabezado h1{font-size:20px}
.leer{padding:6px 10px;margin-bottom:10px;font-size:11px}
h2{font-size:13.5px;margin-bottom:4px}.sub{font-size:10.5px;margin-bottom:6px}
.bloque,.resumen{margin-bottom:12px}.bloque{break-inside:auto}.resumen{padding:6px 12px}
.bandas-fila{margin:3px 0}.bandas-barra{height:18px}.bandas-etq{width:120px;font-size:11px}
.bandas-barra span{font-size:10px}.leyenda{margin-top:4px;font-size:10px}
.tarjetas{gap:8px;margin-bottom:12px}.tarjeta{padding:8px 10px}.tarjeta h3{font-size:12px}
.cifra{font-size:18px}.etiqueta{font-size:11px;margin-bottom:4px}
.significa,.accion{font-size:10.5px;margin-top:5px}.accion{padding:5px 7px}
.barra-fila,.bloque .barra-fila{margin:2px 0;font-size:10.5px}.barra-pista{height:9px}
.chip{margin-top:3px;font-size:10px;padding:1px 7px}.margen,.nota{font-size:9.5px}
.comparativa{font-size:10.5px}.comparativa th,.comparativa td{padding:3px 6px}
.comparativa thead th{font-size:10px}.comparativa tr{break-inside:avoid}
.ruta{padding:6px 12px;margin-bottom:10px}.ruta ul{font-size:11px}.avisos p{font-size:9px}
.nivel+.nivel{margin-top:0}.nivel>h2.titulo-nivel{font-size:15px;margin-bottom:8px}}
"""


def _documento(titulo: str, cuerpo: str) -> str:
    return ("<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{_e(titulo)}</title><style>{_CSS}</style></head><body>"
            '<div class="imprimir"><p>' + _e(INSTRUCCION_IMPRESION) + "</p>"
            '<button type="button" onclick="window.print()">Imprimir</button></div>'
            f'<main class="hoja">{cuerpo}</main></body></html>')


def _encabezado(marca: str, titulo: str, meta: str) -> str:
    return (f'<header class="encabezado"><div class="marca">{_e(marca)}</div>'
            f"<h1>{_e(titulo)}</h1><div class=\"meta\">{_e(meta)}</div></header>")


def informe_colegio_html(analisis: dict, colegio: str, fecha: date | None = None) -> str:
    """Informe imprimible de un colegio: una sección por cada nivel con cifras.

    Lanza ValueError si el colegio no tiene cifras mostrables en ningún nivel,
    para que nadie genere un informe vacío o de un grupo pequeño.
    """
    niveles = [n for n in _niveles(analisis)
               if _nivel_valido(analisis[n]) and colegio in colegios_del_nivel(analisis[n])]
    if not niveles:
        raise ValueError(f"El colegio {colegio} no tiene resultados que se puedan mostrar.")
    nombre = nombre_colegio(colegio)
    total = 0
    secciones = []
    for nivel in niveles:
        a = analisis[nivel]
        filtros = {"nivel": nivel, "colegio": colegio, "grado": vc.TODOS}
        b = vc.bandas_sdq_total(a, filtros)
        total += b["n"] if b else 0
        fichas = vc.tarjetas(a, "colegio", filtros)
        tarjetas_html, comparaciones = [], []
        for t in fichas:
            cuerpo, comp = _cuerpo_tarjeta(a, t, filtros, "Colegio", con_municipio=True)
            tarjetas_html.append(_tarjeta_html(t, cuerpo))
            if comp:
                comparaciones.append((cat.MENSAJES[t.clave].titulo, comp,
                                      vc.prevalencia(a, t.clave, filtros),
                                      vc.prevalencia(a, t.clave, {})))
        grados = _tabla_comparativa(
            a, "Grado", COLUMNAS_GRADO_COLEGIO, filtros, "Por grado en el colegio",
            lambda g: g, nota="Los grados con menos de "
            f"{cat.MIN_GROUP_N} estudiantes no se muestran.")
        secciones.append(
            f'<section class="nivel"><h2 class="titulo-nivel">'
            f'{_e(vc.NIVELES_LABEL.get(nivel, nivel))}</h2>'
            + _resumen(comparaciones)
            + _bloque_bandas([("Colegio", b), ("Municipio", vc.bandas_sdq_total(a, {}))])
            + '<h2>Resultados y qué hacer</h2><div class="tarjetas">'
            + "".join(tarjetas_html) + "</div>"
            + grados
            + _bloque_items(vc.items_pertenencia_bajos(a, 4, filtros))
            + "</section>")
    meta = (f"{total} estudiantes respondieron · "
            + " y ".join(vc.NIVELES_LABEL.get(n, n) for n in niveles)
            + f" · {fecha_larga(fecha)}")
    cuerpo = (_encabezado("Observatorio 360 · Estudiantes · Informe para el colegio",
                          nombre, meta)
              + '<p class="leer">Cada resultado trae la cifra del colegio, cómo se compara '
                "con el total del municipio y qué puede hacer el colegio. Son cifras del "
                "grupo: ningún dato corresponde a un estudiante.</p>"
              + "".join(secciones) + _bloque_ruta()
              + _avisos(niveles, [vc.nota_base(analisis[n]) for n in niveles]))
    return _documento(f"Informe Estudiantes 360 · {nombre}", cuerpo)


def informe_secretaria_html(analisis: dict, fecha: date | None = None) -> str:
    """Informe imprimible para la Secretaría: total del municipio y comparación entre colegios."""
    niveles = [n for n in _niveles(analisis) if _nivel_valido(analisis[n])]
    if not niveles:
        raise ValueError("No hay resultados de estudiantes con base suficiente.")
    secciones = []
    notas_base: list[str] = []
    total = 0
    colegios = set()
    for nivel in niveles:
        a = analisis[nivel]
        total += a.n
        colegios.update(colegios_del_nivel(a))
        fichas = vc.tarjetas(a, "municipio", {})
        tarjetas_html = [_tarjeta_html(t, _cuerpo_tarjeta(a, t, {}, "Municipio",
                                                          con_municipio=False)[0])
                         for t in fichas]
        nota_peq = vc.texto_ocultos(a)
        base = vc.nota_base(a)
        if base and base not in nota_peq:
            notas_base.append(base)
        secciones.append(
            f'<section class="nivel"><h2 class="titulo-nivel">'
            f'{_e(vc.NIVELES_LABEL.get(nivel, nivel))} · {a.n} estudiantes</h2>'
            + _bloque_bandas([("Municipio", vc.bandas_sdq_total(a, {}))])
            + '<h2>Resultados y qué hacer</h2><div class="tarjetas">'
            + "".join(tarjetas_html) + "</div>"
            + _tabla_comparativa(a, "Colegio", list(COLUMNAS_TABLA), {}, "Por colegio",
                                 nombre_colegio, nota=nota_peq)
            + _tabla_comparativa(a, "Grado", list(COLUMNAS_TABLA), {}, "Por grado",
                                 lambda g: g)
            + "</section>")
    meta = (f"{total} estudiantes · {len(colegios)} colegios con resultados · "
            f"{fecha_larga(fecha)}")
    cuerpo = (_encabezado("Observatorio 360 · Estudiantes · Informe para la Secretaría",
                          "Chía · total del municipio", meta)
              + '<p class="leer">Primero el total del municipio y qué hacer desde la política '
                "pública; después, cómo se ubica cada colegio y cada grado frente a ese "
                "total. Son cifras de grupo: ningún dato corresponde a un estudiante.</p>"
              + "".join(secciones) + _bloque_ruta() + _avisos(niveles, notas_base))
    return _documento("Informe Estudiantes 360 · Secretaría", cuerpo)


# ══ Resumen de una página (PDF) ═════════════════════════════════════════════
# Lo que descarga el botón «informe de una página» de la vista comunidad. Antes
# era un Markdown, que rectores y familias no saben abrir. Ahora es una hoja
# carta pensada para imprimir, convertida a PDF con WeasyPrint.
MAX_TARJETAS_PAGINA = 4

_CSS_PAGINA = """
@page{size:letter;margin:11mm 12mm 10mm}
*{box-sizing:border-box}
body{margin:0;color:#1d2733;font-family:"Helvetica Neue",Helvetica,Arial,"Liberation Sans","DejaVu Sans",sans-serif;
font-size:9.6pt;line-height:1.32}
.banda{background:#16365f;color:#fff;border-radius:7px;padding:11px 16px 12px;margin-bottom:10px}
.banda .marca{font-size:7.6pt;letter-spacing:.09em;text-transform:uppercase;opacity:.8}
.banda h1{margin:3px 0 2px;font-size:17pt;line-height:1.15}
.banda .meta{font-size:8.8pt;opacity:.9}
h2{font-size:10.5pt;margin:0 0 5px;color:#16365f}
.bloque{margin-bottom:10px}
.bandas-fila{display:flex;align-items:center;margin:3px 0}
.bandas-etq{width:92px;font-weight:bold;font-size:8.6pt}
.bandas-etq small{display:block;font-weight:normal;color:#5b6776;font-size:7.4pt}
.bandas-barra{flex:1;display:flex;height:17px;border-radius:3px;overflow:hidden}
.bandas-barra span{display:block;height:17px;color:#fff;font-size:7.6pt;font-weight:bold;
text-align:center;line-height:17px;white-space:nowrap;overflow:hidden}
.leyenda{margin-top:4px;font-size:7.6pt;color:#5b6776}
.leyenda span{margin-right:12px}
.leyenda i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px}
.tiles{display:flex;flex-wrap:wrap;justify-content:space-between}
.tile{width:49%;border:1px solid #dde3ea;border-radius:6px;padding:8px 10px 9px;margin-bottom:7px;
break-inside:avoid}
.tile h3{margin:0;font-size:9.2pt}
.cifra{font-size:17pt;font-weight:bold;color:#16365f;margin:2px 0 0;line-height:1.1}
.etiqueta{margin:1px 0 4px;font-size:8.6pt}
.barra-fila{display:flex;align-items:center;margin:2px 0;font-size:8pt}
.barra-etq{width:44%}
.barra-pista{flex:1;height:7px;background:#eef1f5;border-radius:2px;overflow:hidden;margin:0 6px}
.barra-pista span{display:block;height:7px;background:#2E5FAC}
.barra-fila.ref .barra-pista span{background:#a9b4c2}
.barra-fila.alerta .barra-pista span{background:#C0392B}
.barra-val{width:30px;text-align:right;font-weight:bold}
.chip{display:inline-block;margin-top:3px;padding:1px 7px;border-radius:8px;font-size:7.6pt;font-weight:bold}
.chip-mayor{background:#fbe9e7;color:#C0392B}.chip-menor{background:#e6f4ec;color:#1A7F4B}
.chip-similar{background:#eef1f5;color:#5b6776}
.margen{margin:2px 0 0;font-size:7.2pt;color:#5b6776}
.hacer{margin-top:5px;background:#f2f5f9;border-left:3px solid #2E5FAC;padding:4px 7px;font-size:8.3pt}
.ruta{border:1.5px solid #C0392B;border-radius:6px;padding:6px 10px;margin-top:3px}
.ruta h2{color:#C0392B;margin-bottom:3px}
.ruta ul{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap}
.ruta li{width:50%;font-size:8.3pt;margin:1px 0}
.pie{margin-top:7px;font-size:6.9pt;color:#5b6776}
.pie p{margin:2px 0}
"""


def _tile_pagina(a, t: vc.Tarjeta, filtros: dict, con_municipio: bool) -> str:
    """Tarjeta compacta: cifra, comparación y qué hacer. El «qué significa» va en el informe largo."""
    etiqueta_grupo = "Este grupo" if con_municipio else "Municipio"
    cuerpo, _ = _cuerpo_tarjeta(a, t, filtros, etiqueta_grupo, con_municipio)
    titulo = cat.MENSAJES[t.clave].titulo if t.clave in cat.MENSAJES else ""
    return (f'<div class="tile"><h3>{_e(titulo)}</h3>{cuerpo}'
            f'<div class="hacer"><b>Qué hacer:</b> {_e(t.accion)}</div></div>')


def informe_una_pagina_html(analisis, rol: str, filtros: dict | None = None,
                            fecha: date | None = None) -> str:
    """Hoja de una página con lo esencial del grupo que está en pantalla.

    Mismas cifras y textos que la vista: bandas del SDQ, hasta cuatro
    resultados con su «qué hacer» para el rol, comparación con el total del
    municipio cuando hay un colegio o un grado elegido, y la ruta de atención.
    """
    filtros = filtros or {}
    if analisis is None:
        raise ValueError("No hay datos cargados todavía.")
    con_municipio = vc.hay_filtro(filtros)
    b = vc.bandas_sdq_total(analisis, filtros)
    fichas = vc.tarjetas(analisis, rol, filtros)[:MAX_TARJETAS_PAGINA]

    colegio = filtros.get("colegio", vc.TODOS)
    grado = filtros.get("grado", vc.TODOS)
    titulo = ("Todos los colegios" if colegio in (vc.TODOS, None, "")
              else nombre_colegio(colegio))
    if grado not in (vc.TODOS, None, ""):
        titulo += f" · grado {grado}"
    partes_meta = [vc.NIVELES_LABEL.get(analisis.nivel, analisis.nivel)]
    if b:
        partes_meta.append(f"{b['n']} estudiantes")
    partes_meta += [f"Para: {cat.ROLES.get(rol, rol)}", fecha_larga(fecha)]

    if b or fichas:
        filas_bandas = [("Este grupo" if con_municipio else "Municipio", b)]
        if con_municipio:
            filas_bandas.append(("Municipio", vc.bandas_sdq_total(analisis, {})))
        filas_bandas = [(e, x) for e, x in filas_bandas if x]
        bandas = ""
        if filas_bandas:
            bandas = ('<div class="bloque"><h2>Cómo está el grupo</h2>'
                      + "".join(_barra_bandas(e, x) for e, x in filas_bandas)
                      + _leyenda_bandas(filas_bandas[0][1]["etiquetas"]) + "</div>")
        contenido = (bandas + '<h2>Lo más importante y qué hacer</h2><div class="tiles">'
                     + "".join(_tile_pagina(analisis, t, filtros, con_municipio)
                               for t in fichas) + "</div>")
    elif con_municipio and not vc.hay_datos_crudos(analisis):
        contenido = f"<p>{_e(vc.SIN_SUBGRUPO_PUBLICADO)}</p>"
    else:
        contenido = (f"<p>Este grupo tiene menos de {cat.MIN_GROUP_N} estudiantes, así que "
                     "no se muestran sus resultados: con grupos tan pequeños se podría "
                     "reconocer a un estudiante. Sus respuestas sí cuentan en los totales.</p>")

    ruta = "".join(f"<li><b>{_e(n)}</b> — {_e(d)}</li>" for n, d in cat.RUTA_ATENCION)
    avisos = [cat.AVISO_TAMIZAJE]
    if con_municipio:
        avisos.append(NOTA_COMPARACION)
    if analisis.nivel == cat.NIVEL_PRIMARIA:
        avisos.append(cat.AVISO_PRIMARIA)
    cuerpo = ('<div class="banda"><div class="marca">Observatorio 360 · Estudiantes · '
              f'Resumen de una página</div><h1>{_e(titulo)}</h1>'
              f'<div class="meta">{_e(" · ".join(partes_meta))}</div></div>'
              + contenido
              + f'<div class="ruta"><h2>Si un estudiante necesita ayuda</h2><ul>{ruta}</ul></div>'
              + '<div class="pie">' + "".join(f"<p>{_e(t)}</p>" for t in avisos) + "</div>")
    return ("<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
            f"<title>Resumen Estudiantes 360 · {_e(titulo)}</title>"
            f"<style>{_CSS_PAGINA}</style></head><body>{cuerpo}</body></html>")


def a_pdf(html: str) -> bytes | None:
    """PDF de un HTML con WeasyPrint; None si la librería o sus dependencias faltan."""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except Exception:                                      # noqa: BLE001
        # En el despliegue las librerías de sistema vienen de packages.txt; si
        # faltan, la vista entrega el HTML en vez de caerse.
        logging.getLogger(__name__).exception("No se pudo generar el PDF")
        return None
