"""
Vista comunidad de Cuidadores 360 — para colegios, familias y el municipio (fase 4b).

Misma estructura, mismos roles y mismos colores que la de estudiantes: cómo
están quienes cuidan, qué significa y qué se puede hacer. Cinco tarjetas como
techo, el panel «Señales para cuidar a quienes cuidan» arriba de las tarjetas y
la ruta para adultos siempre visible.

Tarjetas por rol (orden de `comunidad_catalogo.ORDEN_TARJETAS`, techo de 5):
  · colegio y municipio: estrés, apoyo, crianza y castigo físico, barrio y cómo
    ve el cuidador al hijo. «Ánimo» está en el panel de señales; la tarjeta solo
    vuelve si el panel no se pudo dibujar (como la de muerte en estudiantes).
  · familia: las mismas cinco. Nunca «Ánimo»: familia no ve cifras de las
    señales del adulto, solo el mensaje de autocuidado y la ruta (spec §5.5).

Reglas que este archivo respeta:
  · Solo lee tablas agregadas YA suprimidas: las del análisis preparado
    (`cuidadores.comunidad.preparar`) o las de la corrida publicada
    (`cuidadores.lectura`). Las dos tienen la misma forma, así que la máquina
    que procesa y el despliegue muestran lo mismo. No recalcula nada.
  · Ningún grupo con menos de 10 cuidadores distintos: solo se ofrecen los
    grupos de la base publicable (o los subgrupos publicados).
  · «Autolesión» solo para el rol municipio y solo con la cifra de todo el
    municipio; nunca por colegio ni por grado. En el rol colegio queda dentro
    de un estado general fijo, sin cifra.
  · Ningún conteo de casos; un porcentaje solo donde la supresión lo dejó.
  · Todos los textos vienen de `comunidad_catalogo`; aquí no se redacta.
  · No importa ingesta, pipeline ni la vista de investigadores: es la única
    vista de cuidadores que carga el despliegue público.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st

from src.cuidadores import alertas as al
from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.estudiantes import alertas_catalogo as ac_est
from src.estudiantes import privacidad
from src.ui import estado
from src.ui.views import estudiantes_alertas as va
from src.ui.views.estudiantes_comunidad import COLORES_BANDAS, figura_comparativa, uno_de_cada

TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
GRADOS = list(cat.GRADOS_ESTUDIO)
EXCLUIDOS = ("OTRO", "SIN_DATO")
CUIDADOR, NINO = cat.MARCO_CUIDADOR, cat.MARCO_NINO

# Proporciones que usan las tarjetas y «Comparar entre grupos» (filas de `cortes`).
INDICADORES: dict[str, dict] = {
    "animo": dict(marco=CUIDADOR, clave="EPDS_Total", indicador=al.INDICADOR_PROBABLE,
                  etiqueta="cuidadores con señales de ánimo bajo"),
    "apoyo_familia": dict(marco=CUIDADOR, clave="MSPSS_Fam",
                          etiqueta="cuidadores que sienten poco apoyo de su familia"),
    "apoyo_amigos": dict(marco=CUIDADOR, clave="MSPSS_Amigos",
                         etiqueta="sienten poco apoyo de sus amigos"),
    "apoyo_otro": dict(marco=CUIDADOR, clave="MSPSS_Otro",
                       etiqueta="sienten poco apoyo de una persona especial"),
    "castigo": dict(marco=CUIDADOR, clave="APQ_Fisico",
                    etiqueta="cuidadores que usan castigo físico a veces o más"),
    "grito": dict(marco=CUIDADOR, clave="APQ_Grito", etiqueta="gritan al hijo a veces o más"),
    "hijo_alto": dict(marco=NINO, clave="SDQ_Total",
                      etiqueta="niños con dificultades altas según su cuidador"),
}
# Tarjeta → indicador principal; las de media → (clave, máximo de la escala).
INDICADOR_TARJETA = {"animo": "animo", "apoyo": "apoyo_familia", "crianza": "castigo",
                     "hijo": "hijo_alto"}
EXTRAS_TARJETA = {"apoyo": ("apoyo_amigos", "apoyo_otro"), "crianza": ("grito",)}
MEDIAS = {"estres": ("PSS_Total", 40), "barrio": ("BARRIO_Indice", 10)}
COMPARABLES = ("castigo", "apoyo_familia", "hijo_alto", "animo")
CIFRA_SUPRIMIDA = "—"


@dataclass(frozen=True)
class Tarjeta:
    clave: str
    titulo: str
    cifra: str
    etiqueta: str
    significa: str
    accion: str
    detalle: str = ""
    suprimida: bool = False


# ══ Grupos y objetos ═══════════════════════════════════════════════════════
def ve_colegios(rol: str) -> bool:
    """Familia no ve desagregación por colegio (spec §6)."""
    return rol != "familia"


def hay_datos_crudos(a) -> bool:
    datos = getattr(a, "datos", None)
    return datos is not None and not datos.empty


def _ordenar(columna: str, grupos) -> list[str]:
    grupos = [str(g) for g in grupos if str(g) not in EXCLUIDOS]
    if columna == "Grado":
        return [g for g in GRADOS if g in grupos] + sorted(g for g in grupos if g not in GRADOS)
    return sorted(set(grupos))


def _grupos_marco(a, columna: str, otra=TODOS) -> list[str]:
    pos = 0 if columna == "Colegio" else 1
    base = getattr(a, "base", None)
    if base is not None and hay_datos_crudos(a):
        if not privacidad.activo(otra):
            return list((base.colegios if columna == "Colegio" else base.grados).keys())
        return [privacidad.partir_celda(k)[pos] for k in base.celdas
                if privacidad.partir_celda(k)[1 - pos] == str(otra)]
    sub = getattr(a, "subgrupos", None) or {}
    if not privacidad.activo(otra):
        return list((sub.get(columna) or {}).keys())
    return [privacidad.partir_celda(k)[pos] for k in (sub.get(CRUCE) or {})
            if privacidad.partir_celda(k)[1 - pos] == str(otra)]


def grupos(ac, columna: str, otra=TODOS) -> list[str]:
    """Grupos publicables de `columna` en alguno de los dos marcos, dentro de `otra`."""
    if ac is None:
        return []
    todos: list[str] = []
    for a in ac.marcos.values():
        if a is not None:
            todos += _grupos_marco(a, columna, otra)
    return _ordenar(columna, set(todos))


def objeto(a, filtros: dict | None):
    """El nivel, o el subgrupo del colegio, del grado o de la celda; None si no existe."""
    if a is None:
        return None
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    sub = getattr(a, "subgrupos", None) or {}
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return (sub.get(CRUCE) or {}).get(privacidad.clave_celda(colegio, grado))
    if privacidad.activo(colegio):
        return (sub.get("Colegio") or {}).get(str(colegio))
    if privacidad.activo(grado):
        return (sub.get("Grado") or {}).get(str(grado))
    return a


def hay_filtro(filtros: dict | None) -> bool:
    return any(privacidad.activo((filtros or {}).get(c, TODOS)) for c in ("colegio", "grado"))


def etiqueta_filtro(filtros: dict | None) -> str:
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    partes = ["Todos los colegios" if not privacidad.activo(colegio) else f"Colegio {colegio}"]
    if privacidad.activo(grado):
        partes.append(f"grado {grado}")
    return " · ".join(partes)


def n_grupo(ac, filtros: dict | None) -> int | None:
    """Cuidadores del grupo (marco de cuidadores), o None si el grupo no tiene cifras."""
    o = objeto(ac.cuidador, filtros)
    if o is None:
        return None
    if o is ac.cuidador:
        base = (getattr(o, "muestra", None) or {}).get("base") or {}
        try:
            return int(base.get("n_nivel", o.n))
        except (TypeError, ValueError):
            return int(o.n)
    return int(o.n)


# ══ Cifras ═════════════════════════════════════════════════════════════════
def _fila_corte(a, indicador: str, filtros: dict | None):
    cfg = INDICADORES[indicador]
    o = objeto(a, filtros)
    t = getattr(o, "cortes", None) if o is not None else None
    if not isinstance(t, pd.DataFrame) or t.empty or "clave" not in t.columns:
        return None
    sel = t[t["clave"].astype(str) == cfg["clave"]]
    if cfg.get("indicador") and "indicador" in sel.columns:
        sel = sel[sel["indicador"].astype(str) == cfg["indicador"]]
    if sel.empty or pd.isna(sel.iloc[0]["n"]) or int(sel.iloc[0]["n"]) < cat.MIN_GROUP_N:
        return None
    return sel.iloc[0]


def proporcion(ac, indicador: str, filtros: dict | None = None) -> dict:
    """{pct, ic_inf, ic_sup, n} del grupo; {} si no hay o si la supresión la ocultó."""
    a = ac.marcos[INDICADORES[indicador]["marco"]]
    f = _fila_corte(a, indicador, filtros)
    if f is None or pd.isna(f["pct"]):
        return {}
    return dict(pct=float(f["pct"]), ic_inf=float(f["ic_inf"]), ic_sup=float(f["ic_sup"]),
                n=int(f["n"]))


def suprimida(ac, indicador: str, filtros: dict | None = None) -> bool:
    """El grupo tiene el indicador (n ≥ 10) pero su porcentaje se ocultó por pocos casos."""
    f = _fila_corte(ac.marcos[INDICADORES[indicador]["marco"]], indicador, filtros)
    return f is not None and pd.isna(f["pct"])


def media(ac, clave: str, filtros: dict | None = None) -> dict:
    """{M, n} de una escala sin corte: del total, de un colegio o de un grado.

    Las medias por celda colegio × grado no se publican: {}.
    """
    a = ac.cuidador
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return {}
    if not hay_filtro(filtros):
        t = getattr(a, "descriptivos", None)
        if not isinstance(t, pd.DataFrame) or t.empty:
            return {}
        sel = t[t["clave"] == clave]
        if sel.empty or pd.isna(sel.iloc[0]["M"]):
            return {}
        return dict(M=float(sel.iloc[0]["M"]), n=int(sel.iloc[0]["n"]))
    columna, grupo = (("Colegio", colegio) if privacidad.activo(colegio) else ("Grado", grado))
    t = getattr(a, "por_colegio" if columna == "Colegio" else "por_grado", None)
    if not isinstance(t, pd.DataFrame) or t.empty or f"M·{grupo}" not in t.columns:
        return {}
    sel = t[t["clave"] == clave]
    if sel.empty or pd.isna(sel.iloc[0][f"M·{grupo}"]):
        return {}
    return dict(M=float(sel.iloc[0][f"M·{grupo}"]), n=int(sel.iloc[0][f"n·{grupo}"]))


def _pct(p: dict) -> str:
    return f"{p['pct']:.0f} %"


def tarjetas(ac, rol: str, filtros: dict | None = None,
             panel_dibujado: bool = True) -> list[Tarjeta]:
    """Hasta `cc.MAX_TARJETAS` tarjetas con cifra, textos del catálogo y acción del rol."""
    filtros = filtros or {}
    salida: list[Tarjeta] = []
    for clave in cc.ORDEN_TARJETAS:
        m = cc.MENSAJES[clave]
        accion = m.accion.get(rol, "")
        if rol not in m.solo_roles or not accion:
            continue
        if clave == "animo" and panel_dibujado:
            continue
        if clave in MEDIAS:
            escala, maximo = MEDIAS[clave]
            x = media(ac, escala, filtros)
            if not x:
                continue
            detalle = f"Base de {x['n']} cuidadores"
            if hay_filtro(filtros):
                ref = media(ac, escala, {})
                if ref:
                    detalle += f" · municipio: {ref['M']:.1f} de {maximo}".replace(".", ",")
            salida.append(Tarjeta(clave, m.titulo, f"{x['M']:.1f}".replace(".", ",") + f" de {maximo}", m.etiqueta,
                                  m.significa, accion, detalle))
        else:
            indicador = INDICADOR_TARJETA[clave]
            p = proporcion(ac, indicador, filtros)
            if not p:
                if suprimida(ac, indicador, filtros):
                    salida.append(Tarjeta(clave, m.titulo, CIFRA_SUPRIMIDA, m.etiqueta,
                                          m.significa, accion, cc.CIFRAS_PEQUENAS, True))
                    if len(salida) == cc.MAX_TARJETAS:
                        break
                continue
            unidad = "niños" if INDICADORES[indicador]["marco"] == NINO else "cuidadores"
            detalle = (f"{_pct(p)} (IC 95 % {p['ic_inf']:.0f}–{p['ic_sup']:.0f}); base de "
                       f"{p['n']} {unidad}")
            extras = []
            for otro in EXTRAS_TARJETA.get(clave, ()):
                q = proporcion(ac, otro, filtros)
                if q:
                    extras.append(f"{_pct(q)} {INDICADORES[otro]['etiqueta']}")
            if extras:
                detalle += ". " + "; ".join(extras)
            salida.append(Tarjeta(clave, m.titulo, uno_de_cada(p["pct"]), m.etiqueta,
                                  m.significa, accion, detalle))
        if len(salida) == cc.MAX_TARJETAS:
            break
    return salida


def bandas_hijo(ac, filtros: dict | None = None) -> dict:
    """Las cuatro bandas del SDQ total según el cuidador, o {} si no hay o se ocultaron."""
    o = objeto(ac.nino, filtros)
    t = getattr(o, "bandas", None) if o is not None else None
    if not isinstance(t, pd.DataFrame) or t.empty or "clave" not in t.columns:
        return {}
    sel = t[t["clave"] == "SDQ_Total"]
    if sel.empty:
        return {}
    f = sel.iloc[0]
    if int(f["n"]) < cat.MIN_GROUP_N or any(pd.isna(f[f"pct_b{i}"]) for i in range(4)):
        return {}
    etiquetas = list(f["etiquetas"]) if isinstance(f.get("etiquetas"), (list, tuple)) and \
        len(f["etiquetas"]) == 4 else ["Cercano al promedio", "Ligeramente elevado", "Alto",
                                       "Muy alto"]
    return dict(n=int(f["n"]), pct=[float(f[f"pct_b{i}"]) for i in range(4)],
                etiquetas=etiquetas)


def comparables(rol: str) -> list[str]:
    """Indicadores de «Comparar entre grupos». «Ánimo» nunca para familia."""
    return [k for k in COMPARABLES if k != "animo" or rol in ("colegio", "municipio")]


def prevalencia_por(ac, indicador: str, columna: str, filtros: dict | None = None
                    ) -> pd.DataFrame:
    """El indicador por colegio o por grado, desde las tablas de cada grupo (sin casos)."""
    filtros = filtros or {}
    otra = "grado" if columna == "Colegio" else "colegio"
    valor_otra = filtros.get(otra, TODOS)
    filas = []
    for g in grupos(ac, columna, valor_otra):
        propio = filtros.get(columna.lower(), TODOS)
        if privacidad.activo(propio) and g != str(propio):
            continue
        p = proporcion(ac, indicador, {columna.lower(): g, otra: valor_otra})
        if p:
            filas.append(dict(grupo=g, n=p["n"], pct=p["pct"], ic_inf=p["ic_inf"],
                              ic_sup=p["ic_sup"]))
    return pd.DataFrame(filas, columns=["grupo", "n", "pct", "ic_inf", "ic_sup"])


def grupos_sin_cifra(ac, indicador: str, columna: str, filtros: dict | None = None) -> list[str]:
    filtros = filtros or {}
    otra = "grado" if columna == "Colegio" else "colegio"
    return [g for g in grupos(ac, columna, filtros.get(otra, TODOS))
            if suprimida(ac, indicador, {columna.lower(): g, otra: filtros.get(otra, TODOS)})]


# ══ Señales del adulto ═════════════════════════════════════════════════════
def tabla_alertas(ac) -> pd.DataFrame:
    t = getattr(ac.cuidador, "alertas", None) if ac is not None else None
    if isinstance(t, pd.DataFrame) and len(t) and set(al.COLUMNAS_TABLA) <= set(t.columns):
        return t
    return al.vacia()


def _clave_grupo(filtros: dict | None) -> tuple[str, str]:
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    if privacidad.activo(colegio) and privacidad.activo(grado):
        return CRUCE, privacidad.clave_celda(colegio, grado)
    if privacidad.activo(colegio):
        return "Colegio", str(colegio)
    if privacidad.activo(grado):
        return "Grado", str(grado)
    return al.TOTAL, TODOS


def fila_alerta(ac, alerta: str, filtros: dict | None = None) -> dict | None:
    """La fila del grupo elegido; la autolesión siempre es la del total del municipio."""
    t = tabla_alertas(ac)
    if not len(t):
        return None
    agrupacion, grupo = ((al.TOTAL, TODOS) if alerta in al.SOLO_TOTAL
                         else _clave_grupo(filtros))
    sel = t[(t["alerta"] == alerta) & (t["agrupacion"] == agrupacion)
            & (t["grupo"].astype(str) == str(grupo))]
    return None if sel.empty else sel.iloc[0].to_dict()


def _con_cifra(f) -> bool:
    return bool(f) and f.get("pct") is not None and not pd.isna(f.get("pct"))


def frase(alerta: str, pct: float) -> str:
    fraccion = uno_de_cada(pct)
    verbo = "muestra" if fraccion.startswith("1 de cada") else "muestran"
    return cc.PLANTILLA_CIFRA.format(fraccion=fraccion, verbo=verbo,
                                     senal=cc.ALERTAS[alerta].senal)


def listas_prioridad(ac, alerta: str, rol: str, filtros: dict | None = None
                     ) -> list[tuple[str, list[str]]]:
    """Grupos en «Prioridad» que el rol puede ver. Solo «Ánimo»; nunca para familia."""
    if rol == "familia" or alerta in al.SOLO_TOTAL:
        return []
    t = tabla_alertas(ac)
    if not len(t):
        return []
    t = t[(t["alerta"] == alerta) & (t["estado"] == al.PRIORIDAD)]
    agrupacion, grupo = _clave_grupo(filtros)
    salida: list[tuple[str, list[str]]] = []
    if agrupacion == "Colegio":
        prefijo = grupo + privacidad.SEP
        grados = [privacidad.partir_celda(g)[1]
                  for g in t.loc[t["agrupacion"] == CRUCE, "grupo"].astype(str)
                  if g.startswith(prefijo)]
        salida.append((ac_est.TITULO_GRADOS_PRIORIDAD, _ordenar("Grado", grados)))
    elif agrupacion == al.TOTAL:
        if rol == "municipio":
            colegios = _ordenar("Colegio", t.loc[t["agrupacion"] == "Colegio", "grupo"])
            salida.append((ac_est.TITULO_COLEGIOS_PRIORIDAD, colegios))
        salida.append((ac_est.TITULO_GRADOS_PRIORIDAD,
                       _ordenar("Grado", t.loc[t["agrupacion"] == "Grado", "grupo"])))
    return [(titulo, nombres) for titulo, nombres in salida if nombres]


def senales(ac, rol: str, filtros: dict | None = None) -> list[va.Senal]:
    """Una señal por cada una que el rol puede ver. Familia: ninguna (sin cifras)."""
    if rol == "familia" or ac is None:
        return []
    t = tabla_alertas(ac)
    salida: list[va.Senal] = []
    for alerta, definicion in cc.ALERTAS.items():
        if rol not in definicion.roles or not len(t) or not (t["alerta"] == alerta).any():
            continue
        f = fila_alerta(ac, alerta, filtros)
        listas = tuple((ti, tuple(ns)) for ti, ns in listas_prioridad(ac, alerta, rol, filtros))
        que_hacer = definicion.que_hacer.get(rol, "")
        if not _con_cifra(f):
            salida.append(va.Senal(alerta=alerta, nombre=definicion.nombre,
                                   estado=al.SIN_ESTADO, frase=cc.CIFRAS_PEQUENAS,
                                   que_hacer=que_hacer, listas=listas))
            continue
        salida.append(va.Senal(alerta=alerta, nombre=definicion.nombre,
                               estado=va.estado_valido(f["estado"]),
                               frase=frase(alerta, float(f["pct"])), que_hacer=que_hacer,
                               pct=float(f["pct"]), ic_inf=float(f["ic_inf"]),
                               ic_sup=float(f["ic_sup"]), n=int(f["n"]), listas=listas))
    return salida


def explicaciones(lista) -> list[str]:
    """Qué quiere decir cada estado de `lista` (y nada más), con los textos de cuidadores."""
    textos = {al.PRIORIDAD: cc.QUE_ES_PRIORIDAD, al.PRESENTE: cc.QUE_ES_PRESENTE,
              al.REFERENCIA: cc.QUE_ES_REFERENCIA, al.SIN_ESTADO: cc.QUE_ES_SIN_ESTADO}
    vistos: list[str] = []
    for s in lista:
        texto = textos[va.estado_valido(s.estado)]
        if texto not in vistos:
            vistos.append(texto)
    return vistos


def _e(texto) -> str:
    return escape(str(texto), quote=True)


def _unir(nombres, tope: int | None = None) -> str:
    nombres = list(nombres)
    if tope and len(nombres) > tope:
        return ", ".join(nombres[:tope]) + f" y {len(nombres) - tope} más"
    return ", ".join(nombres)


def panel_html(ac, rol: str, filtros: dict | None = None, compacto: bool = False) -> str:
    """Panel para los informes; `compacto` para el resumen de una página."""
    if rol == "familia":
        return (f'<section class="senales"><h2>{_e(cc.TITULO_AUTOCUIDADO)}</h2>'
                f'<p class="nota-senal">{_e(cc.AUTOCUIDADO_FAMILIA)}</p></section>')
    lista = senales(ac, rol, filtros)
    if not lista:
        return ""
    tope = va.MAX_NOMBRES_PAGINA if compacto else None
    bloques = []
    for s in lista:
        chip = f'<span class="estado">{_e(s.etiqueta_estado)}</span>'
        listas = "".join(f' <span class="lista">{_e(t)} {_e(_unir(ns, tope))}</span>'
                         for t, ns in s.listas)
        nota = (f' <span class="lista">{_e(cc.NOTA_SOLO_MUNICIPIO)}</span>'
                if s.alerta in al.SOLO_TOTAL and not compacto else "")
        if compacto:
            bloques.append(f'<p class="senal senal-{s.clase}">{chip} <b>{_e(s.nombre)}.</b> '
                           f'{_e(s.frase)}{listas}</p>')
            continue
        margen = (f'<p class="margen">Margen de error {s.ic_inf:.0f}–{s.ic_sup:.0f} % · base '
                  f'de {s.n} cuidadores</p>' if s.visible else "")
        hacer = (f'<p class="accion"><b>Qué hacer.</b> {_e(s.que_hacer)}</p>'
                 if s.que_hacer else "")
        bloques.append(f'<div class="senal senal-{s.clase}"><p>{chip} <b>{_e(s.nombre)}</b></p>'
                       f'<p>{_e(s.frase)}{nota}</p>'
                       + (f"<p>{listas.strip()}</p>" if listas else "") + margen + hacer
                       + "</div>")
    notas = [cc.NO_ES_DIAGNOSTICO, cc.NOTA_AZAR]
    if rol == "colegio":
        notas.insert(0, cc.ESTADO_GENERAL_COLEGIO)
    return (f'<section class="senales"><h2>{_e(cc.TITULO_PANEL)}</h2>' + "".join(bloques)
            + f'<p class="nota-senal">{_e(" ".join(notas))}</p></section>')


def _celda_html(f) -> str:
    if not _con_cifra(f):
        return (f'<td class="senal-sin-estado"><span class="estado">'
                f'{_e(ac_est.ESTADOS[al.SIN_ESTADO])}</span>'
                f'<small>{_e(ac_est.CIFRAS_PEQUENAS_CORTO)}</small></td>')
    estado_ = va.estado_valido(f["estado"])
    return (f'<td class="senal-{va.CLASE.get(estado_, va.CLASE[al.SIN_ESTADO])}">'
            f'<span class="estado">{_e(ac_est.ESTADOS[estado_])}</span> '
            f'{float(f["pct"]):.0f} %<small>{float(f["ic_inf"]):.0f}–'
            f'{float(f["ic_sup"]):.0f}</small></td>')


def tabla_secretaria_html(ac) -> str:
    """«Ánimo» por colegio para la Secretaría: estado y %, sin conteos. Nunca autolesión."""
    t = tabla_alertas(ac)
    if not len(t) or not (t["alerta"] == cat.ANIMO).any():
        return ""
    colegios = _ordenar("Colegio", t.loc[(t["agrupacion"] == "Colegio")
                                        & (t["alerta"] == cat.ANIMO), "grupo"])
    nombre = cc.ALERTAS[cat.ANIMO].nombre_corto
    cuerpo = "".join(f'<tr><th scope="row">{_e(c)}</th>'
                     f'{_celda_html(fila_alerta(ac, cat.ANIMO, {"colegio": c}))}</tr>'
                     for c in colegios)
    total = (f'<tr><th scope="row">Total del municipio</th>'
             f'{_celda_html(fila_alerta(ac, cat.ANIMO, {}))}</tr>')
    return (f'<section class="bloque senales"><h2>{_e(cc.TITULO_PANEL)} · por colegio</h2>'
            f'<div class="desliza"><table class="senales-tabla"><thead><tr><th></th>'
            f'<th>{_e(nombre)}</th></tr></thead><tbody>{cuerpo}</tbody><tfoot>{total}</tfoot>'
            f'</table></div><p class="nota">{_e(cc.NOTA_TABLA)} {_e(cc.NOTA_AZAR)}</p>'
            "</section>")


# ══ Streamlit ══════════════════════════════════════════════════════════════
def render_panel(ac, rol: str, filtros: dict | None = None) -> bool:
    """Dibuja el panel arriba de las tarjetas. True si salió «Ánimo» (colegio, municipio)."""
    if rol == "familia":
        with st.container(border=True):
            st.markdown(f"#### {cc.TITULO_AUTOCUIDADO}")
            st.markdown(cc.AUTOCUIDADO_FAMILIA)
        return True
    lista = senales(ac, rol, filtros)
    if not lista:
        return False
    with st.container(border=True):
        st.markdown(f"#### {cc.TITULO_PANEL}")
        for s in lista:
            st.markdown(f"{va._chip_html(s)} **{_e(s.nombre)}**", unsafe_allow_html=True)
            st.markdown(f"{s.frase} {cc.NO_ES_DIAGNOSTICO}")
            if s.alerta in al.SOLO_TOTAL:
                st.caption(cc.NOTA_SOLO_MUNICIPIO)
            for titulo, nombres in s.listas:
                st.markdown(f"{titulo} {_unir(nombres)}")
            if s.que_hacer:
                st.markdown(f"**Qué hacer:** {s.que_hacer}")
        if rol == "colegio":
            st.markdown(cc.ESTADO_GENERAL_COLEGIO)
        with st.expander("Qué quiere decir cada estado"):
            for s in lista:
                st.markdown(f"**{s.nombre}.** {cc.ALERTAS[s.alerta].que_es}")
                if s.visible:
                    st.caption(f"{s.pct:.0f} % · margen de error {s.ic_inf:.0f}–"
                               f"{s.ic_sup:.0f} % · base de {s.n} cuidadores")
            for texto in explicaciones(lista):
                st.caption(texto)
            st.caption(cc.NOTA_AZAR)
    return any(s.alerta == cat.ANIMO for s in lista)


def _panel(ac, rol: str, filtros: dict) -> bool:
    try:
        return bool(render_panel(ac, rol, filtros))
    except Exception:                                      # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo dibujar el panel de cuidadores")
        return False


def figura_bandas(b: dict):
    import plotly.graph_objects as go
    fig = go.Figure()
    for i, (etiqueta, pct) in enumerate(zip(b["etiquetas"], b["pct"])):
        fig.add_trace(go.Bar(x=[pct], y=[""], orientation="h", name=etiqueta,
                             marker_color=COLORES_BANDAS[i], text=[f"{pct:.0f} %"],
                             textposition="inside", insidetextanchor="middle",
                             hovertemplate=f"<b>{etiqueta}</b><br>%{{x:.0f}} %<extra></extra>"))
    fig.update_layout(barmode="stack", height=150, showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.6, x=0),
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(range=[0, 100], visible=False), yaxis=dict(visible=False))
    return fig


def _selector(ac, columna: str, colegio: str = TODOS) -> str:
    opciones = grupos(ac, columna, colegio if columna == "Grado" else TODOS)
    clave = f"cuid_com_{columna.lower()}"
    if not opciones:
        return TODOS
    if columna == "Colegio":
        estado.sembrar(clave, estado.COLEGIO, [TODOS] + opciones)
    if st.session_state.get(clave, TODOS) not in [TODOS] + opciones:
        st.session_state[clave] = TODOS
    etiqueta = "Colegio" if columna == "Colegio" else "Grado (del hijo o la hija)"
    cambio = estado.al_cambiar(clave, estado.COLEGIO) if columna == "Colegio" else None
    valor = st.sidebar.selectbox(etiqueta, [TODOS] + opciones, key=clave, on_change=cambio)
    if columna == "Colegio" and (
            valor != TODOS or st.session_state.get(estado.COLEGIO, TODOS) in [TODOS] + opciones):
        estado.guardar(estado.COLEGIO, valor)
    return valor


def colegio_de_la_url(ac) -> str | None:
    """`?colegio=LauV`, si ese colegio tiene cifras de cuidadores; si no, None."""
    try:
        pedido = str(st.query_params.get("colegio", "")).strip()
    except Exception:                                      # noqa: BLE001
        return None
    if not pedido or ac is None:
        return None
    for codigo in grupos(ac, "Colegio"):
        if codigo.lower() == pedido.lower():
            return codigo
    return None


def avisos_internos() -> list[str]:
    """Avisos de textos y ruta pendientes: en el modo completo y en la vista previa
    del equipo (corrida en revisión, despliegue privado); nunca en público."""
    try:
        from src.core import modo as modo_app
        from src.ui.views.estudiantes_comunidad import en_vista_previa
    except Exception:                                      # noqa: BLE001
        return []
    if modo_app.modo() != modo_app.COMPLETO and not en_vista_previa(cat.MODULO):
        return []
    salida = []
    if not cc.TEXTOS_APROBADOS:
        salida.append(cc.TEXTOS_PENDIENTES)
    if not cc.RUTAS_VALIDADAS:
        salida.append(ac_est.RUTA_PENDIENTE)
    return salida


def render_comunidad(ac) -> None:
    """Vista comunidad: `ac` es el análisis preparado o la corrida publicada."""
    st.subheader("👪 Cuidadores · para colegios, familias y el municipio")
    st.caption("Cómo están quienes cuidan, qué significa y qué se puede hacer. "
               "Nada individual, nunca.")
    if ac is None or getattr(ac.cuidador, "n", 0) < cat.MIN_GROUP_N:
        st.info(cc.NO_PUBLICADO, icon="⏳")
        return
    estado.sembrar("cuid_com_rol", estado.ROL, list(cc.ROLES))
    rol = st.radio("Estoy viendo esto como", list(cc.ROLES), format_func=lambda r: cc.ROLES[r],
                   horizontal=True, key="cuid_com_rol",
                   on_change=estado.al_cambiar("cuid_com_rol", estado.ROL))
    estado.guardar(estado.ROL, rol)
    st.sidebar.markdown("### Cuidadores · vista comunidad")
    colegio = _selector(ac, "Colegio") if ve_colegios(rol) else TODOS
    grado = _selector(ac, "Grado", colegio)
    filtros = {"colegio": colegio, "grado": grado}

    st.markdown(f"#### Cómo están los cuidadores · {etiqueta_filtro(filtros)}")
    n = n_grupo(ac, filtros)
    if n is None:
        st.info(cc.SIN_SUBGRUPO, icon="ℹ️")
    else:
        st.caption(f"{n} cuidadores en estas cifras. {cc.AVISO_SIN_OLAS}")

    panel_dibujado = _panel(ac, rol, filtros)
    fichas = tarjetas(ac, rol, filtros, panel_dibujado=panel_dibujado)
    if fichas:
        from src.ui.views import tarjetas as vt
        vt.render([vt.ficha(t) for t in fichas])
    else:
        st.info("Aún no hay indicadores con base suficiente para este grupo.", icon="ℹ️")

    st.markdown("#### Comparar entre grupos")
    dimensiones = ["Grado"] + (["Colegio"] if ve_colegios(rol) else [])
    izq, der = st.columns(2)
    with izq:
        dimension = st.radio("Comparar por", dimensiones, horizontal=True,
                             key="cuid_com_dimension")
    with der:
        indicador = st.selectbox("Indicador", comparables(rol),
                                 format_func=lambda k: INDICADORES[k]["etiqueta"].capitalize(),
                                 key="cuid_com_indicador")
    tabla = prevalencia_por(ac, indicador, dimension, filtros)
    if tabla.empty:
        st.info("No hay grupos con suficientes cuidadores para comparar.", icon="ℹ️")
    else:
        st.plotly_chart(figura_comparativa(tabla, INDICADORES[indicador]["etiqueta"].capitalize()),
                        width="stretch", key="cuid_com_comparativa")
        st.caption("Las líneas verticales son el margen de error (intervalo de Wilson al 95 %). "
                   "Se compara, no se ranquea.")
    sin_cifra = grupos_sin_cifra(ac, indicador, dimension, filtros)
    if sin_cifra:
        st.caption(f"Sin cifra: {', '.join(sin_cifra)}. {cc.CIFRAS_PEQUENAS}")

    b = bandas_hijo(ac, filtros)
    if b:
        st.markdown(f"#### {cc.MENSAJES['hijo'].titulo} · {b['n']} niños")
        st.plotly_chart(figura_bandas(b), width="stretch", key="cuid_com_bandas")

    with st.container(border=True):
        st.markdown(f"#### 🆘 {cc.TITULO_RUTA}")
        for nombre, detalle in cc.ruta(rol):
            st.markdown(f"- **{nombre}** — {detalle}")
        for aviso in avisos_internos():
            st.caption(f"⚠️ {aviso}")

    st.warning(cc.AVISO_TAMIZAJE, icon="⚠️")
    with st.expander("Sobre estas cifras"):
        for aviso in (cc.AVISO_EPDS, cc.AVISO_APOYO, cc.AVISO_MINIMO, cc.AVISO_SIN_OLAS):
            st.caption(f"· {aviso}")

    _boton_una_pagina(ac, rol, filtros)
    if ve_colegios(rol):
        _seccion_informes(ac, rol, colegio)


@st.cache_data(show_spinner="Preparando el PDF…", max_entries=64)
def _pdf_de(html: str) -> bytes | None:
    from src.ui.views.cuidadores_informe import a_pdf
    return a_pdf(html)


def descargas_bloqueadas(ac) -> bool:
    """True si la auditoría local encontró algo (`ui.cuidadores.preparar_con_auditoria`).

    La corrida publicada no trae el atributo: ya pasó la auditoría al publicarse.
    """
    return bool(getattr(ac, "hallazgos_auditoria", None))


def _boton_bloqueado(etiqueta: str, clave: str) -> None:
    st.download_button(etiqueta, data=b"", disabled=True, key=clave)


def _boton_una_pagina(ac, rol: str, filtros: dict) -> None:
    if descargas_bloqueadas(ac):
        _boton_bloqueado("⬇️ Descargar resumen de una página", "cuid_com_descarga")
        st.caption(cc.DESCARGAS_BLOQUEADAS)
        return
    from src.ui.views.cuidadores_informe import informe_una_pagina_html
    html = informe_una_pagina_html(ac, rol, filtros)
    pdf = _pdf_de(html)
    base = f"resumen_cuidadores_{rol}"
    for clave in ("colegio", "grado"):
        if privacidad.activo(filtros.get(clave, TODOS)):
            base += f"_{filtros[clave]}"
    if pdf:
        st.download_button("⬇️ Descargar resumen de una página (PDF)", data=pdf,
                           file_name=f"{base}.pdf", mime="application/pdf", type="primary",
                           key="cuid_com_descarga")
    else:
        st.download_button("⬇️ Descargar resumen de una página", data=html,
                           file_name=f"{base}.html", mime="text/html", type="primary",
                           key="cuid_com_descarga")
        st.caption("Se abre en el navegador; desde ahí se imprime o se guarda como PDF.")


def _seccion_informes(ac, rol: str, colegio: str) -> None:
    from src.ui.views import cuidadores_informe as inf
    st.markdown("#### 🖨️ Informes para imprimir")
    st.caption("Se descargan como página web: al abrirla en el navegador trae el botón "
               "«Imprimir», desde el que también se guarda como PDF.")
    codigos = grupos(ac, "Colegio")
    if descargas_bloqueadas(ac):
        _boton_bloqueado("⬇️ Descargar informe del colegio", "cuid_inf_desc_colegio")
        if rol == "municipio":
            _boton_bloqueado("⬇️ Descargar informe para la Secretaría",
                             "cuid_inf_desc_secretaria")
        st.caption(cc.DESCARGAS_BLOQUEADAS)
        return
    izq, der = st.columns(2)
    with izq:
        if codigos:
            indice = codigos.index(colegio) if colegio in codigos else 0
            elegido = st.selectbox("Informe del colegio", codigos, index=indice,
                                   key="cuid_inf_colegio")
            st.download_button("⬇️ Descargar informe del colegio",
                               data=inf.informe_colegio_html(ac, elegido),
                               file_name=f"informe_cuidadores_{elegido}.html", mime="text/html",
                               key="cuid_inf_desc_colegio")
        else:
            st.info("Ningún colegio tiene suficientes cuidadores para un informe.", icon="ℹ️")
    with der:
        if rol == "municipio":
            st.markdown("**Informe para la Secretaría**")
            st.download_button("⬇️ Descargar informe para la Secretaría",
                               data=inf.informe_secretaria_html(ac),
                               file_name="informe_cuidadores_secretaria.html", mime="text/html",
                               key="cuid_inf_desc_secretaria")


# ══ Despliegue público ═════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def _corrida_vigente() -> int | None:
    try:
        from src.cuidadores import lectura
        return lectura.id_corrida_vigente()
    except Exception:                                      # noqa: BLE001
        return None


@st.cache_resource(show_spinner="Leyendo los resultados publicados de cuidadores…")
def _leer_publicado(_clave: str):
    from src.cuidadores import lectura
    return lectura.cargar_desde_supabase()[0]


def publicado():
    """La corrida publicada de cuidadores, o None (sin credenciales, sin corrida o sin red)."""
    try:
        from src.cuidadores import lectura
        if not lectura.disponible():
            return None
        return _leer_publicado(f"corrida-{_corrida_vigente()}")
    except Exception:                                      # noqa: BLE001
        logging.getLogger(__name__).exception("No se pudo leer la corrida de cuidadores")
        return None


def tiene_senales(ac) -> bool:
    """True si la corrida trae las filas del total de las señales del adulto.

    Sin ellas el panel no se dibuja; en público eso no se permite.
    """
    t = getattr(getattr(ac, "cuidador", None), "alertas", None)
    return (isinstance(t, pd.DataFrame) and not t.empty and "agrupacion" in t.columns
            and bool((t["agrupacion"] == al.TOTAL).any()))


def render_publico() -> None:
    """Página de Cuidadores en el despliegue público: solo la corrida publicada.

    Nunca sin el panel de señales: una corrida sin sus filas (subida con
    `--publicar-ya` antes de aprobar textos y ruta) cuenta como no publicada.
    """
    ac = publicado()
    if ac is None or not tiene_senales(ac):
        st.title("👪 Cuidadores 360")
        st.info(cc.NO_PUBLICADO, icon="⏳")
        return
    estado.aplicar_colegio_de_url(colegio_de_la_url(ac))
    render_comunidad(ac)
