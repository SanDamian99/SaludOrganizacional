"""
Panel «Señales para actuar a tiempo» — alertas de grupo de Estudiantes 360.

Funciones puras que leen `Analisis.alertas` (alertas.py) y los textos fijos de
`alertas_catalogo`; `render_panel` es lo único que dibuja con Streamlit. Lo
usan la vista comunidad, el informe del colegio, el de la Secretaría y el
resumen de una página: todos dicen lo mismo.

Reglas (spec §5.4 y §6):
  · Nunca un conteo de casos. Porcentaje, «1 de cada N», margen de error y
    estado solo si la tabla trae el porcentaje (la supresión ya decidió).
  · Sin porcentaje, estado neutro «Sin estado: cifras pequeñas», el texto fijo
    y la ruta. El panel nunca se oculta.
  · Naranja como máximo; nunca rojo.
  · Familia no ve desesperanza ni listas por colegio.
  · Es un módulo nuevo: se importa fresco aunque el despliegue conserve
    módulos viejos en memoria. Lee `Analisis.alertas` con getattr.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape

import pandas as pd

from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import privacidad

TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE

# Gris sereno, gris claro (sin estado) y naranja. Nunca rojo (#C0392B es el de
# las bandas del SDQ).
COLOR_PRESENTE = "#5B6776"
FONDO_PRESENTE = "#F2F4F7"
COLOR_SIN_ESTADO = "#7A8594"
FONDO_SIN_ESTADO = "#FAFBFC"
COLOR_PRIORIDAD = "#B86E00"
FONDO_PRIORIDAD = "#FFF3E0"
MAX_NOMBRES_PAGINA = 6

# Clase CSS por estado: «referencia» se pinta como «presente».
CLASE = {ac.PRIORIDAD: "prioridad", ac.PRESENTE: "presente", ac.REFERENCIA: "presente",
         ac.SIN_ESTADO: "sin-estado"}


def estado_valido(estado) -> str:
    """El estado tal cual si se conoce; si no (una corrida de otra versión), «sin estado»."""
    return estado if isinstance(estado, str) and estado in ac.ESTADOS else ac.SIN_ESTADO


@dataclass(frozen=True)
class Senal:
    alerta: str
    nombre: str
    estado: str
    frase: str
    que_hacer: str
    pct: float | None = None
    ic_inf: float | None = None
    ic_sup: float | None = None
    n: int | None = None
    listas: tuple = ()

    @property
    def visible(self) -> bool:
        return self.pct is not None

    @property
    def etiqueta_estado(self) -> str:
        return ac.ESTADOS[estado_valido(self.estado)]

    @property
    def clase(self) -> str:
        return CLASE.get(estado_valido(self.estado), CLASE[ac.SIN_ESTADO])


# ══ Datos ═══════════════════════════════════════════════════════════════════
def tabla(analisis) -> pd.DataFrame:
    t = getattr(analisis, "alertas", None)
    if isinstance(t, pd.DataFrame) and len(t) and set(al.COLUMNAS_TABLA) <= set(t.columns):
        return t
    return pd.DataFrame(columns=al.COLUMNAS_TABLA)


def hay_alerta(analisis, alerta: str) -> bool:
    t = tabla(analisis)
    return bool(len(t)) and bool((t["alerta"] == alerta).any())


def alertas_para_rol(analisis, rol: str) -> list[str]:
    nivel = getattr(analisis, "nivel", None)
    return [k for k, x in ac.ALERTAS.items()
            if rol in x.roles and nivel in x.niveles and hay_alerta(analisis, k)]


def clave_grupo(filtros: dict | None) -> tuple[str, str]:
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return CRUCE, privacidad.clave_celda(colegio, grado)
    if privacidad.activo(colegio):
        return "Colegio", str(colegio)
    if privacidad.activo(grado):
        return "Grado", str(grado)
    return al.TOTAL, TODOS


def fila(analisis, alerta: str, filtros: dict | None = None) -> dict | None:
    t = tabla(analisis)
    if not len(t):
        return None
    agrupacion, grupo = clave_grupo(filtros)
    sel = t[(t["alerta"] == alerta) & (t["agrupacion"] == agrupacion)
            & (t["grupo"].astype(str) == str(grupo))]
    return None if sel.empty else sel.iloc[0].to_dict()


def _con_cifra(f) -> bool:
    return bool(f) and f.get("pct") is not None and not pd.isna(f.get("pct"))


def frase(alerta: str, pct: float) -> str:
    from src.ui.views.estudiantes_comunidad import uno_de_cada
    fraccion = uno_de_cada(pct)
    verbo = "muestra" if fraccion.startswith("1 de cada") else "muestran"
    return ac.PLANTILLA_CIFRA.format(fraccion=fraccion, verbo=verbo,
                                     senal=ac.ALERTAS[alerta].senal)


def _ordenar_grados(grados, nivel) -> list[str]:
    orden = cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.ORDEN_GRADOS_PRI
    return sorted(grados, key=lambda g: (orden.index(g) if g in orden else 99, g))


def listas_prioridad(analisis, alerta: str, rol: str,
                     filtros: dict | None = None) -> list[tuple[str, list[str]]]:
    """(título, nombres) de los grupos en «Prioridad» que este rol puede ver."""
    if rol == "familia":
        return []
    t = tabla(analisis)
    if not len(t):
        return []
    t = t[(t["alerta"] == alerta) & (t["estado"] == ac.PRIORIDAD)]
    agrupacion, grupo = clave_grupo(filtros)
    nivel = getattr(analisis, "nivel", None)
    salida: list[tuple[str, list[str]]] = []
    if agrupacion == "Colegio":
        prefijo = grupo + privacidad.SEP
        grados = [privacidad.partir_celda(g)[1]
                  for g in t.loc[t["agrupacion"] == CRUCE, "grupo"].astype(str)
                  if g.startswith(prefijo)]
        salida.append((ac.TITULO_GRADOS_PRIORIDAD, _ordenar_grados(grados, nivel)))
    elif agrupacion == al.TOTAL:
        if rol == "municipio":
            from src.estudiantes.ingest import nombre_colegio
            colegios = sorted((nombre_colegio(g) for g in
                               t.loc[t["agrupacion"] == "Colegio", "grupo"].astype(str)),
                              key=str.lower)
            salida.append((ac.TITULO_COLEGIOS_PRIORIDAD, colegios))
        grados = list(t.loc[t["agrupacion"] == "Grado", "grupo"].astype(str))
        salida.append((ac.TITULO_GRADOS_PRIORIDAD, _ordenar_grados(grados, nivel)))
    return [(titulo, nombres) for titulo, nombres in salida if nombres]


def senales(analisis, rol: str, filtros: dict | None = None) -> list[Senal]:
    """Una señal por alerta que el rol puede ver, para el grupo elegido."""
    salida: list[Senal] = []
    for alerta in alertas_para_rol(analisis, rol):
        definicion = ac.ALERTAS[alerta]
        f = fila(analisis, alerta, filtros)
        listas = tuple((t, tuple(ns)) for t, ns in
                       listas_prioridad(analisis, alerta, rol, filtros))
        if not _con_cifra(f):
            salida.append(Senal(alerta=alerta, nombre=definicion.nombre,
                                estado=ac.SIN_ESTADO, frase=ac.CIFRAS_PEQUENAS,
                                que_hacer=definicion.que_hacer.get(rol, ""), listas=listas))
            continue
        salida.append(Senal(
            alerta=alerta, nombre=definicion.nombre, estado=estado_valido(f["estado"]),
            frase=frase(alerta, float(f["pct"])), que_hacer=definicion.que_hacer.get(rol, ""),
            pct=float(f["pct"]), ic_inf=float(f["ic_inf"]), ic_sup=float(f["ic_sup"]),
            n=int(f["n"]), listas=listas))
    return salida


def explicaciones(lista: list[Senal]) -> list[str]:
    """Qué quiere decir cada estado que aparece en `lista` (y nada más)."""
    textos = {ac.PRIORIDAD: ac.QUE_ES_PRIORIDAD, ac.PRESENTE: ac.QUE_ES_PRESENTE,
              ac.REFERENCIA: ac.QUE_ES_REFERENCIA, ac.SIN_ESTADO: ac.QUE_ES_SIN_ESTADO}
    vistos: list[str] = []
    for s in lista:
        texto = textos[estado_valido(s.estado)]
        if texto not in vistos:
            vistos.append(texto)
    return vistos


# ══ HTML (informes y PDF) ═══════════════════════════════════════════════════
def _e(texto) -> str:
    return escape(str(texto), quote=True)


def _unir(nombres, tope: int | None = None) -> str:
    nombres = list(nombres)
    if tope and len(nombres) > tope:
        return ", ".join(nombres[:tope]) + f" y {len(nombres) - tope} más"
    return ", ".join(nombres)


def panel_html(analisis, rol: str, filtros: dict | None = None,
               compacto: bool = False) -> str:
    """Panel para el informe del colegio o, `compacto`, recuadro del PDF de una página."""
    lista = senales(analisis, rol, filtros)
    if not lista:
        return ""
    tope = MAX_NOMBRES_PAGINA if compacto else None
    bloques = []
    for s in lista:
        estado = f'<span class="estado">{_e(s.etiqueta_estado)}</span>'
        listas = "".join(f' <span class="lista">{_e(t)} {_e(_unir(ns, tope))}</span>'
                         for t, ns in s.listas)
        if compacto:
            bloques.append(f'<p class="senal senal-{s.clase}">{estado} <b>{_e(s.nombre)}.</b> '
                           f'{_e(s.frase)}{listas}</p>')
            continue
        margen = (f'<p class="margen">Margen de error {s.ic_inf:.0f}–{s.ic_sup:.0f} % · base '
                  f'de {s.n} estudiantes</p>' if s.visible else "")
        hacer = (f'<p class="accion"><b>Qué hacer.</b> {_e(s.que_hacer)}</p>'
                 if s.que_hacer else "")
        bloques.append(f'<div class="senal senal-{s.clase}"><p>{estado} <b>{_e(s.nombre)}</b></p>'
                       f'<p>{_e(s.frase)}</p>'
                       + (f"<p>{listas.strip()}</p>" if listas else "") + margen + hacer
                       + "</div>")
    notas = [ac.NO_ES_DIAGNOSTICO, ac.NOTA_AZAR]
    if not compacto and getattr(analisis, "nivel", None) == cat.NIVEL_PRIMARIA:
        notas.append(cat.AVISO_PRIMARIA)
    return (f'<section class="senales"><h2>{_e(ac.TITULO_PANEL)}</h2>' + "".join(bloques)
            + f'<p class="nota-senal">{_e(" ".join(notas))}</p></section>')


def _celda_html(f) -> str:
    if not _con_cifra(f):
        return (f'<td class="senal-sin-estado"><span class="estado">'
                f'{_e(ac.ESTADOS[ac.SIN_ESTADO])}</span>'
                f'<small>{_e(ac.CIFRAS_PEQUENAS_CORTO)}</small></td>')
    estado = estado_valido(f["estado"])
    return (f'<td class="senal-{CLASE.get(estado, CLASE[ac.SIN_ESTADO])}"><span class="estado">'
            f'{_e(ac.ESTADOS[estado])}'
            f'</span> {float(f["pct"]):.0f} %<small>{float(f["ic_inf"]):.0f}–'
            f'{float(f["ic_sup"]):.0f}</small></td>')


def tabla_secretaria_html(analisis) -> str:
    """Tabla por colegio para el informe de la Secretaría: estado y %, sin conteos."""
    from src.estudiantes.ingest import nombre_colegio
    claves = alertas_para_rol(analisis, "municipio")
    if not claves:
        return ""
    t = tabla(analisis)
    colegios = sorted({str(g) for g in t.loc[(t["agrupacion"] == "Colegio")
                                             & t["alerta"].isin(claves), "grupo"]},
                      key=lambda c: nombre_colegio(c).lower())
    cabecera = "".join(f"<th>{_e(ac.ALERTAS[k].nombre_corto)}</th>" for k in claves)
    cuerpo = "".join(
        f'<tr><th scope="row">{_e(nombre_colegio(c))}</th>'
        + "".join(_celda_html(fila(analisis, k, {"colegio": c})) for k in claves) + "</tr>"
        for c in colegios)
    total = ('<tr><th scope="row">Total del municipio</th>'
             + "".join(_celda_html(fila(analisis, k, {})) for k in claves) + "</tr>")
    grados = []
    for k in claves:
        for titulo, nombres in listas_prioridad(analisis, k, "municipio", {}):
            if titulo == ac.TITULO_GRADOS_PRIORIDAD:
                grados.append(f'<p class="nota"><b>{_e(ac.ALERTAS[k].nombre_corto)}.</b> '
                              f"{_e(titulo)} {_e(_unir(nombres))}</p>")
    return (f'<section class="bloque senales"><h2>{_e(ac.TITULO_PANEL)} · por colegio</h2>'
            '<div class="desliza"><table class="senales-tabla"><thead><tr><th></th>'
            + cabecera + f"</tr></thead><tbody>{cuerpo}</tbody><tfoot>{total}</tfoot>"
            "</table></div>" + "".join(grados)
            + f'<p class="nota">{_e(ac.NOTA_TABLA)} {_e(ac.NOTA_AZAR)}</p></section>')


CSS_INFORME = (
    ".senales{border:1px solid #dde3ea;border-radius:6px;padding:12px 16px;margin:0 0 22px;"
    "break-inside:avoid}"
    ".senal{border-left:4px solid " + COLOR_PRESENTE + ";background:" + FONDO_PRESENTE + ";"
    "border-radius:4px;padding:8px 12px;margin:0 0 10px}"
    ".senal p{margin:3px 0;font-size:13.5px}"
    ".senal-prioridad{border-left-color:" + COLOR_PRIORIDAD + ";background:" + FONDO_PRIORIDAD + "}"
    ".senal-sin-estado{border-left-color:" + COLOR_SIN_ESTADO + ";background:"
    + FONDO_SIN_ESTADO + "}"
    ".senales .estado{display:inline-block;padding:1px 9px;border-radius:10px;font-size:12px;"
    "font-weight:700;background:#fff;color:" + COLOR_PRESENTE + ";margin-right:6px}"
    ".senal-prioridad .estado{color:" + COLOR_PRIORIDAD + "}"
    ".senal-sin-estado .estado{color:" + COLOR_SIN_ESTADO + ";font-weight:600}"
    ".senales .lista{color:#5b6776}"
    ".nota-senal{font-size:11.5px;color:#5b6776;margin:6px 0 0}"
    ".senales-tabla{width:100%;border-collapse:collapse;font-size:13px}"
    ".senales-tabla th,.senales-tabla td{border-bottom:1px solid #dde3ea;padding:6px 8px;"
    "text-align:center;vertical-align:top}"
    ".senales-tabla tbody th,.senales-tabla tfoot th{text-align:left}"
    ".senales-tabla small{display:block;font-size:10.5px;color:#5b6776}"
    ".senales-tabla td.senal-prioridad{background:" + FONDO_PRIORIDAD + "}"
    "@media print{.senales{padding:6px 12px;margin-bottom:12px}.senal{padding:5px 9px}"
    ".senal p{font-size:10.5px}.senales-tabla{font-size:10.5px}"
    ".senales-tabla th,.senales-tabla td{padding:3px 6px}}"
)

CSS_PAGINA = (
    ".senales{border:1px solid #dde3ea;border-radius:6px;padding:5px 9px 6px;margin-bottom:8px}"
    ".senales h2{margin-bottom:3px}"
    ".senal{margin:2px 0;font-size:8.3pt;line-height:1.3}"
    ".senal .estado{display:inline-block;padding:0 6px;border-radius:7px;font-size:7.4pt;"
    "font-weight:bold;margin-right:4px;background:" + FONDO_PRESENTE + ";color:"
    + COLOR_PRESENTE + "}"
    ".senal-prioridad .estado{background:" + FONDO_PRIORIDAD + ";color:" + COLOR_PRIORIDAD + "}"
    ".senal-sin-estado .estado{background:" + FONDO_SIN_ESTADO + ";color:"
    + COLOR_SIN_ESTADO + "}"
    ".senal .lista{color:#5b6776}"
    ".nota-senal{font-size:7pt;color:#5b6776;margin:2px 0 0}"
)


# ══ Streamlit ═══════════════════════════════════════════════════════════════
def _chip_html(s: Senal) -> str:
    color, fondo = {"prioridad": (COLOR_PRIORIDAD, FONDO_PRIORIDAD),
                    "presente": (COLOR_PRESENTE, FONDO_PRESENTE),
                    "sin-estado": (COLOR_SIN_ESTADO, FONDO_SIN_ESTADO)}[s.clase]
    return (f'<span style="background:{fondo};color:{color};border-radius:10px;'
            f'padding:1px 9px;font-size:0.85em;font-weight:600">{_e(s.etiqueta_estado)}</span>')


def render_panel(analisis, rol: str, filtros: dict | None = None) -> bool:
    """Dibuja el panel arriba de las tarjetas. False si la corrida no trae alertas."""
    import streamlit as st
    lista = senales(analisis, rol, filtros)
    if not lista:
        return False
    with st.container(border=True):
        st.markdown(f"#### {ac.TITULO_PANEL}")
        for s in lista:
            st.markdown(f"{_chip_html(s)} **{_e(s.nombre)}**", unsafe_allow_html=True)
            st.markdown(f"{s.frase} {ac.NO_ES_DIAGNOSTICO}")
            for titulo, nombres in s.listas:
                st.markdown(f"{titulo} {_unir(nombres)}")
            if s.que_hacer:
                st.markdown(f"**Qué hacer:** {s.que_hacer}")
        if getattr(analisis, "nivel", None) == cat.NIVEL_PRIMARIA:
            st.caption(cat.AVISO_PRIMARIA)
        with st.expander("Qué quiere decir cada estado"):
            for s in lista:
                st.markdown(f"**{s.nombre}.** {ac.ALERTAS[s.alerta].que_es}")
                if s.visible:
                    st.caption(f"{s.pct:.0f} % · margen de error {s.ic_inf:.0f}–"
                               f"{s.ic_sup:.0f} % · base de {s.n} estudiantes")
            for texto in explicaciones(lista):
                st.caption(texto)
            st.caption(ac.NOTA_AZAR)
    return True
