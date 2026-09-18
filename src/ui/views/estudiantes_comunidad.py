"""
Vista comunidad del módulo Estudiantes 360 — para colegios, familias y el municipio.

Responde tres preguntas y nada más: cómo está mi grupo, qué significa y qué hago
mañana. Cinco tarjetas como techo, lenguaje sin jerga y una ruta de atención
siempre visible.

Reglas no negociables que este archivo respeta:
  · Ningún grupo con menos de `catalog.MIN_GROUP_N` casos se muestra, ni en los
    selectores, ni en los gráficos, ni en el informe descargable.
  · Nunca se muestra una fila individual ni una tabla de respuestas.
  · Todos los textos que lee el usuario vienen de `catalog` (MENSAJES, ROLES,
    RUTA_ATENCION, avisos). Esta vista elige y formatea; no redacta.
  · Aquí no se calcula estadística nueva: las cifras salen del objeto `Analisis`
    o, si hay filtro activo, de `stats.prevalencia_por_grupo` y
    `stats.contraste_protector`.
  · El rol «familia» no ve desagregación por colegio ni el mensaje `ideacion`.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.estudiantes import catalog as cat
from src.estudiantes import scoring, stats

# Colores del semáforo para las cuatro bandas del SDQ (verde → rojo).
COLORES_BANDAS = ["#1A7F4B", "#8FBF3F", "#B07D0D", "#C0392B"]
COLOR_BARRA = "#2E5FAC"

TODOS = "Todos"
NIVELES_LABEL = {cat.NIVEL_SECUNDARIA: "Secundaria · 6.º a 10.º",
                 cat.NIVEL_PRIMARIA: "Primaria · 4.º y 5.º"}

# Enunciados del PSSM, copiados literalmente de los encabezados del formulario
# aplicado (solo se quita el punto final y, cuando la frase lo repetía, el
# «en mi colegio» redundante). No se parafrasean: estos enunciados son el
# resultado accionable que leen los colegios, así que cambiarles el sentido
# cambiaría la conclusión. Los cinco negativos (3, 6, 9, 12 y 16) tienen abajo
# su lectura en positivo, porque la media que llega de `stats` ya está orientada.
ENUNCIADOS_PSSM: dict[str, str] = {
    "PSSM1": "Siento que soy parte de mi colegio",
    "PSSM2": "Mi colegio nota cuando soy bueno en algo",
    "PSSM3": "Es difícil para personas como yo ser aceptadas en mi colegio",
    "PSSM4": "Se toman mis opiniones en serio",
    "PSSM5": "La mayoría de los profesores están interesados en mí",
    "PSSM6": "A veces siento como si no perteneciera a este lugar",
    "PSSM7": "Hay al menos un profesor o adulto con quien puedo hablar",
    "PSSM8": "Las personas en mi colegio están interesadas en personas como yo",
    "PSSM9": "Los profesores aquí no están interesados en personas como yo",
    "PSSM10": "Participo en actividades en mi colegio",
    "PSSM11": "Me respetan tanto como a otros estudiantes",
    "PSSM12": "Me siento diferente de la mayoría de los otros estudiantes",
    "PSSM13": "Realmente puedo ser yo mismo en mi colegio",
    "PSSM14": "Las personas en mi colegio me respetan",
    "PSSM15": "Saben que puedo hacer un buen trabajo",
    "PSSM16": "Desearía estar en un colegio diferente",
    "PSSM17": "Me siento orgulloso de pertenecer a mi colegio",
    "PSSM18": "A otros estudiantes les agrado tal como soy",
}

# Lectura en positivo de los cinco enunciados negativos (3, 6, 9, 12 y 16). Se
# usa al graficar porque la media que llega de `stats.medias_items` ya está
# invertida: sin esta lectura, un enunciado negativo se leería al revés.
ENUNCIADOS_PSSM_ORIENTADOS: dict[str, str] = {
    "PSSM3": "Personas como yo son aceptadas en mi colegio",
    "PSSM6": "Siento que pertenezco a este lugar",
    "PSSM9": "Los profesores aquí están interesados en personas como yo",
    "PSSM12": "No me siento diferente de los otros estudiantes",
    "PSSM16": "No desearía estar en un colegio diferente",
}

# Etiquetas en lenguaje llano de cada indicador con corte. El umbral replica el
# que usa `scoring.sobre_cortes`, que es la fuente de `Analisis.cortes`; aquí
# solo se necesita para poder recalcular la cifra cuando hay un filtro activo.
# Ninguna etiqueta nombra un trastorno: se habla de «síntomas» y de «nivel alto».
INDICADORES: dict[str, dict] = {
    "sdq_alto": dict(
        clave="SDQ_Total",
        etiqueta="reporta dificultades altas o muy altas",
        columna="banda_SDQ_Total", umbral=("ge", 2)),
    "adulto_confianza": dict(
        clave=f"PSSM{cat.PSSM_ITEM_ADULTO}",
        etiqueta="no tiene un profesor o adulto de confianza en el colegio",
        columna=f"PSSM{cat.PSSM_ITEM_ADULTO}", umbral=("le", 2)),
    "ideacion": dict(
        clave=f"RCADS{cat.RCADS_ITEM_MUERTE}",
        etiqueta="piensa en la muerte con frecuencia o siempre",
        columna=f"RCADS{cat.RCADS_ITEM_MUERTE}", umbral=("ge", 2)),
    "irritabilidad": dict(
        clave="ARI_Total",
        etiqueta="está por encima del corte de irritabilidad",
        columna="ARI_Total", umbral=("gt", 2),
        indicador_cortes="Irritabilidad > 2 (cribado)"),
    "emocional": dict(
        clave="SDQ_Emo",
        etiqueta="tiene síntomas emocionales en nivel alto",
        columna="banda_SDQ_Emo", umbral=("ge", 2)),
}

# Contrastes protector → resultado que alimentan las tarjetas de apoyo y
# pertenencia. El resultado se busca en este orden de preferencia.
CONTRASTES = {
    "apoyo_familia": dict(protector="MSPSS_Fam",
                          resultados=("RCADS_Dep", "SDQ_Total"),
                          etiqueta="según el apoyo que siente en casa"),
    "pertenencia": dict(protector="PSSM_Total",
                        resultados=("RCADS_Dep", "SDQ_Total"),
                        etiqueta="según cuánto se siente parte del colegio"),
}

# Orden en que se intentan las tarjetas; se muestran las cinco primeras que
# tengan cifra y que el rol pueda ver.
ORDEN_TARJETAS = ["sdq_alto", "adulto_confianza", "ideacion", "emocional_sexo",
                  "apoyo_familia", "pertenencia", "irritabilidad"]
MAX_TARJETAS = 5


@dataclass(frozen=True)
class Tarjeta:
    """Una tarjeta de la vista: cifra grande, etiqueta, qué significa, qué hacer."""
    clave: str
    cifra: str
    etiqueta: str
    significa: str
    accion: str
    detalle: str = ""


# ══ Funciones puras (sin Streamlit): son las que prueban los tests ══════════
def uno_de_cada(pct: float | None) -> str:
    """Traduce un porcentaje a «1 de cada N», «X de cada 10» o «X de cada 100»."""
    if pct is None or pd.isna(pct) or pct <= 0:
        return "—"
    if pct >= 100:
        return "todos"
    n = round(100 / pct)
    if 2 <= n <= 20 and abs(100 / n - pct) <= 1.5:
        return f"1 de cada {n}"
    if pct >= 15:
        return f"{round(pct / 10)} de cada 10"
    return f"{round(pct)} de cada 100"


def mensajes_para_rol(rol: str) -> dict[str, cat.Mensaje]:
    """Mensajes del catálogo que este rol puede ver, respetando `solo_roles`."""
    return {k: m for k, m in cat.MENSAJES.items() if rol in m.solo_roles}


def accion_para_rol(mensaje: cat.Mensaje, rol: str) -> str:
    """El «qué hacer» del mensaje para el rol pedido; vacío si no le corresponde."""
    if rol not in mensaje.solo_roles:
        return ""
    return {"colegio": mensaje.accion_colegio,
            "familia": mensaje.accion_familia,
            "municipio": mensaje.accion_municipio}.get(rol, "")


def ve_colegios(rol: str) -> bool:
    """El rol familia no ve desagregación por colegio."""
    return rol != "familia"


def enunciado_pssm(item: str, orientado: bool = False) -> str:
    """Texto corto del ítem de pertenencia; el código si no está en el catálogo local.

    Con `orientado=True` devuelve la lectura en positivo de los enunciados
    negativos, que es la que corresponde a la media invertida que se grafica.
    """
    if orientado and item in ENUNCIADOS_PSSM_ORIENTADOS:
        return ENUNCIADOS_PSSM_ORIENTADOS[item]
    return ENUNCIADOS_PSSM.get(item, item)


def grupos_visibles(analisis, columna: str) -> tuple[list[str], list[str]]:
    """(visibles, pequeños) según `MIN_GROUP_N`, en el orden canónico si lo hay."""
    conteo = (analisis.muestra or {}).get(columna.lower()) if analisis else None
    if not conteo:
        if analisis is None or analisis.datos is None or columna not in analisis.datos.columns:
            return [], []
        conteo = analisis.datos[columna].value_counts().to_dict()
    orden = None
    if columna == "Grado":
        orden = (cat.ORDEN_GRADOS_SEC if analisis.nivel == cat.NIVEL_SECUNDARIA
                 else cat.ORDEN_GRADOS_PRI)
    claves = [g for g in (orden or []) if g in conteo]
    claves += sorted(g for g in conteo if g not in claves)
    visibles = [g for g in claves if conteo[g] >= cat.MIN_GROUP_N]
    pequenos = [g for g in claves if conteo[g] < cat.MIN_GROUP_N]
    return visibles, pequenos


def _mascara(datos: pd.DataFrame, cfg: dict) -> pd.Series | None:
    """Serie booleana del indicador, o None si la columna no está."""
    col = cfg["columna"]
    if col not in datos.columns:
        return None
    op, valor = cfg["umbral"]
    serie = datos[col]
    bruto = {"ge": serie >= valor, "gt": serie > valor, "le": serie <= valor}[op]
    return bruto.where(serie.notna())


def subconjunto(analisis, filtros: dict) -> pd.DataFrame:
    """Datos del nivel restringidos al colegio y grado elegidos."""
    d = analisis.datos
    for columna in ("Colegio", "Grado"):
        valor = (filtros or {}).get(columna.lower(), TODOS)
        if valor and valor != TODOS and columna in d.columns:
            d = d[d[columna] == valor]
    return d


def hay_filtro(filtros: dict) -> bool:
    return any((filtros or {}).get(c, TODOS) not in (TODOS, None, "")
               for c in ("colegio", "grado"))


def etiqueta_filtro(analisis, filtros: dict) -> str:
    """Nombre del grupo seleccionado, sin identificar a nadie."""
    partes = []
    colegio = (filtros or {}).get("colegio", TODOS)
    grado = (filtros or {}).get("grado", TODOS)
    partes.append("Todos los colegios" if colegio in (TODOS, None) else f"Colegio {colegio}")
    if grado not in (TODOS, None):
        partes.append(f"grado {grado}")
    partes.append(NIVELES_LABEL.get(analisis.nivel, analisis.nivel))
    return " · ".join(partes)


def prevalencia(analisis, indicador: str, filtros: dict | None = None) -> dict:
    """Cifra de un indicador con corte para el grupo seleccionado.

    Sin filtro se lee de `Analisis.cortes`, que ya viene calculado. Con filtro se
    delega en `stats.prevalencia_por_grupo`, que además enmascara el grupo si no
    llega a `MIN_GROUP_N`. Aquí no se calcula nada a mano.
    """
    cfg = INDICADORES.get(indicador)
    if cfg is None or analisis is None:
        return {}
    if not hay_filtro(filtros or {}):
        tabla = analisis.cortes
        if tabla is None or tabla.empty:
            return {}
        fila = tabla[tabla["clave"] == cfg["clave"]]
        if "indicador_cortes" in cfg:
            fila = fila[fila["indicador"] == cfg["indicador_cortes"]]
        if fila.empty:
            return {}
        f = fila.iloc[0]
        if int(f["n"]) < cat.MIN_GROUP_N:
            return {}
        return dict(pct=float(f["pct"]), ic_inf=float(f["ic_inf"]),
                    ic_sup=float(f["ic_sup"]), n=int(f["n"]))
    d = subconjunto(analisis, filtros or {})
    mask = _mascara(d, cfg)
    if mask is None or d.empty:
        return {}
    d = d.assign(_grupo="seleccion")
    tabla = stats.prevalencia_por_grupo(d, mask, "_grupo")
    if tabla.empty:
        return {}
    f = tabla.iloc[0]
    return dict(pct=float(f["pct"]), ic_inf=float(f["ic_inf"]),
                ic_sup=float(f["ic_sup"]), n=int(f["n"]))


def prevalencia_por(analisis, indicador: str, columna: str,
                    filtros: dict | None = None) -> pd.DataFrame:
    """Prevalencia del indicador por nivel de `columna`, vía `stats`."""
    cfg = INDICADORES.get(indicador)
    if cfg is None or analisis is None:
        return pd.DataFrame()
    d = subconjunto(analisis, filtros or {})
    if columna not in d.columns:
        return pd.DataFrame()
    mask = _mascara(d, cfg)
    if mask is None:
        return pd.DataFrame()
    orden = None
    if columna == "Grado":
        orden = (cat.ORDEN_GRADOS_SEC if analisis.nivel == cat.NIVEL_SECUNDARIA
                 else cat.ORDEN_GRADOS_PRI)
    return stats.prevalencia_por_grupo(d, mask, columna, orden)


def contraste(analisis, clave: str, filtros: dict | None = None) -> dict:
    """Contraste protector del grupo seleccionado, del `Analisis` o de `stats`."""
    cfg = CONTRASTES.get(clave)
    if cfg is None or analisis is None:
        return {}
    if not hay_filtro(filtros or {}):
        for res in cfg["resultados"]:
            for c in analisis.contrastes or []:
                if c.get("protector") == cfg["protector"] and c.get("resultado") == res:
                    return c
        return {}
    d = subconjunto(analisis, filtros or {})
    for res in cfg["resultados"]:
        if res in d.columns and cfg["protector"] in d.columns:
            c = stats.contraste_protector(d, res, cfg["protector"])
            if c:
                return c
    return {}


def items_pertenencia_bajos(analisis, k: int = 4, filtros: dict | None = None) -> list[dict]:
    """Los `k` ítems de pertenencia con la media más baja, con su enunciado.

    Sin filtro se lee de `Analisis.items_pssm`. Con filtro se recalcula sobre el
    subconjunto con `stats.medias_items`, porque si no el gráfico mostraría las
    medias de todo el nivel bajo un título que nombra un colegio o un grado.
    """
    if hay_filtro(filtros or {}):
        d = subconjunto(analisis, filtros or {})
        if len(d) < cat.MIN_GROUP_N:
            return []
        tabla = stats.medias_items(d, "PSSM")
    else:
        tabla = getattr(analisis, "items_pssm", None)
    if tabla is None or tabla.empty:
        return []
    tabla = tabla[tabla["n"] >= cat.MIN_GROUP_N] if "n" in tabla.columns else tabla
    tabla = tabla.sort_values("M").head(k)
    return [dict(item=str(f["item"]),
                 enunciado=enunciado_pssm(str(f["item"]), orientado=True),
                 literal=enunciado_pssm(str(f["item"])),
                 media=float(f["M"]), n=int(f["n"])) for _, f in tabla.iterrows()]


def bandas_sdq_total(analisis, filtros: dict | None = None) -> dict:
    """Porcentajes de las cuatro bandas del SDQ total del grupo seleccionado.

    Con un filtro activo se recalcula la distribución sobre el subconjunto con
    `scoring.distribucion_bandas`; mostrar la del nivel completo bajo un título
    que nombra un colegio sería atribuirle cifras que no son suyas.
    """
    if hay_filtro(filtros or {}):
        d = subconjunto(analisis, filtros or {})
        if len(d) < cat.MIN_GROUP_N:
            return {}
        tabla = scoring.distribucion_bandas(d, "self")
    else:
        tabla = getattr(analisis, "bandas", None)
    if tabla is None or tabla.empty or "clave" not in tabla.columns:
        return {}
    fila = tabla[tabla["clave"] == "SDQ_Total"]
    if fila.empty:
        return {}
    f = fila.iloc[0]
    if int(f["n"]) < cat.MIN_GROUP_N:
        return {}
    return dict(n=int(f["n"]),
                pct=[float(f[f"pct_b{i}"]) for i in range(4)],
                etiquetas=list(f.get("etiquetas") or cat.BANDAS_LABELS))


def tarjetas(analisis, rol: str, filtros: dict | None = None) -> list[Tarjeta]:
    """Hasta `MAX_TARJETAS` tarjetas con cifra real, textos del catálogo y acción del rol."""
    filtros = filtros or {}
    permitidos = mensajes_para_rol(rol)
    salida: list[Tarjeta] = []
    for clave in ORDEN_TARJETAS:
        clave_mensaje = "emocional_sexo" if clave == "emocional_sexo" else clave
        mensaje = permitidos.get(clave_mensaje)
        if mensaje is None:
            continue
        accion = accion_para_rol(mensaje, rol)
        if not accion:
            continue
        cifra, detalle = "", ""
        if clave in INDICADORES:
            p = prevalencia(analisis, clave, filtros)
            if not p:
                continue
            cifra = uno_de_cada(p["pct"])
            detalle = (f"{p['pct']:.0f} % (IC 95 % {p['ic_inf']:.0f}–{p['ic_sup']:.0f}); "
                       f"base de {p['n']} estudiantes")
            etiqueta = INDICADORES[clave]["etiqueta"]
        elif clave == "emocional_sexo":
            tabla = prevalencia_por(analisis, "emocional", "Sexo", filtros)
            if tabla.empty or len(tabla) < 2:
                continue
            tabla = tabla.sort_values("pct", ascending=False)
            cifra = " · ".join(f"{f['pct']:.0f} %" for _, f in tabla.iterrows())
            detalle = "; ".join(f"{f['grupo']}: {f['pct']:.0f} % de {f['n']}"
                                for _, f in tabla.iterrows())
            etiqueta = ("con síntomas emocionales en nivel alto, por sexo ("
                        + ", ".join(str(f["grupo"]) for _, f in tabla.iterrows()) + ")")
        else:
            c = contraste(analisis, clave, filtros)
            if not c:
                continue
            cifra = f"{c['pct_tercil_alto']:.0f} % · {c['pct_tercil_bajo']:.0f} %"
            etiqueta = ("en el nivel más alto de malestar, "
                        + CONTRASTES[clave]["etiqueta"])
            detalle = (f"{uno_de_cada(c['pct_tercil_alto'])} entre quienes sienten mucho, "
                       f"{uno_de_cada(c['pct_tercil_bajo'])} entre quienes sienten poco "
                       f"(n = {c['n_alto']} y {c['n_bajo']})")
        salida.append(Tarjeta(clave=clave, cifra=cifra, etiqueta=etiqueta,
                              significa=mensaje.significa, accion=accion, detalle=detalle))
        if len(salida) == MAX_TARJETAS:
            break
    return salida


def informe_markdown(analisis, rol: str, filtros: dict | None = None) -> str:
    """Informe de una página en Markdown con las cifras del grupo seleccionado.

    Solo cifras agregadas de grupos que llegan a `MIN_GROUP_N`, textos del
    catálogo y la ruta de atención. Nunca nombres ni filas individuales.
    """
    filtros = filtros or {}
    if analisis is None:
        return "# Estudiantes 360\n\nNo hay datos cargados todavía.\n"
    lineas = ["# Observatorio 360 · Estudiantes",
              f"**Cómo está el grupo:** {etiqueta_filtro(analisis, filtros)}",
              f"**Estoy viendo esto como:** {cat.ROLES.get(rol, rol)}", ""]

    b = bandas_sdq_total(analisis, filtros)
    fichas = tarjetas(analisis, rol, filtros)
    if not b and not fichas:
        # Grupo demasiado pequeño: el informe no puede traer ni una cifra, y
        # tiene que decir por qué en lugar de salir vacío.
        lineas += [f"No se muestran resultados de este grupo porque tiene menos de "
                   f"{cat.MIN_GROUP_N} estudiantes. Con grupos así de pequeños se "
                   "podría reconocer a un estudiante concreto.",
                   "",
                   "Sus respuestas sí cuentan en los totales del colegio y del nivel. "
                   "Para ver resultados, amplía la selección a todo el colegio o a "
                   "todo el nivel.",
                   ""]
    if b:
        lineas.append(f"## Cómo está el grupo · {b['n']} estudiantes")
        for etiqueta, pct in zip(b["etiquetas"], b["pct"]):
            lineas.append(f"- {etiqueta}: {pct:.0f} %")
        lineas.append("")


    if fichas:
        lineas.append("## Resultados y qué hacer")
        for t in fichas:
            mensaje = cat.MENSAJES[t.clave if t.clave in cat.MENSAJES else "sdq_alto"]
            lineas += [f"### {mensaje.titulo}",
                       f"**{t.cifra}** {t.etiqueta}.",
                       f"*Qué significa:* {t.significa}",
                       f"*Qué hacer:* {t.accion}"]
            if t.detalle:
                lineas.append(f"<!-- {t.detalle} -->")
            lineas.append("")

    items = items_pertenencia_bajos(analisis, filtros=filtros)
    if items:
        lineas.append("## Los enunciados de pertenencia con la media más baja")
        for it in items:
            lineas.append(f"- {it['enunciado']} — media {it['media']:.2f} de 5")
        lineas.append("")

    visibles_g, pequenos_g = grupos_visibles(analisis, "Grado")
    visibles_c, pequenos_c = grupos_visibles(analisis, "Colegio")
    if visibles_g:
        lineas.append("## Grupos que se muestran")
        lineas.append("- Grados: " + ", ".join(visibles_g))
        if ve_colegios(rol) and visibles_c:
            lineas.append(f"- Colegios comparados: {len(visibles_c)}")
        pequenos = pequenos_g + (pequenos_c if ve_colegios(rol) else [])
        if pequenos:
            lineas.append(f"- {len(pequenos)} grupos no se muestran por ser pequeños "
                          f"(menos de {cat.MIN_GROUP_N} estudiantes).")
        lineas.append("")

    lineas.append("## Si un estudiante necesita ayuda")
    for nombre, detalle in cat.RUTA_ATENCION:
        lineas.append(f"- **{nombre}** — {detalle}")
    lineas += ["", "---", cat.AVISO_TAMIZAJE]
    if analisis.nivel == cat.NIVEL_PRIMARIA:
        lineas.append("")
        lineas.append(cat.AVISO_PRIMARIA)
    lineas += ["", cat.AVISO_NORMAS, ""]
    return "\n".join(lineas)


# ══ Piezas visuales ════════════════════════════════════════════════════════
def figura_bandas(b: dict) -> go.Figure:
    """Barra horizontal apilada con las cuatro bandas del SDQ total."""
    fig = go.Figure()
    for i, (etiqueta, pct) in enumerate(zip(b["etiquetas"], b["pct"])):
        fig.add_trace(go.Bar(
            x=[pct], y=[""], orientation="h", name=etiqueta,
            marker_color=COLORES_BANDAS[i],
            text=[f"{pct:.0f} %"], textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"<b>{etiqueta}</b><br>%{{x:.0f}} %<extra></extra>"))
    fig.update_layout(
        barmode="stack", height=150, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.6, x=0),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(range=[0, 100], visible=False), yaxis=dict(visible=False))
    return fig


def figura_comparativa(tabla: pd.DataFrame, titulo: str) -> go.Figure:
    """Barras con IC de Wilson por grupo. `tabla` ya viene enmascarada por N."""
    fig = go.Figure(go.Bar(
        x=tabla["grupo"].astype(str), y=tabla["pct"], marker_color=COLOR_BARRA,
        text=[f"{v:.0f} %" for v in tabla["pct"]], textposition="outside",
        error_y=dict(type="data", symmetric=False,
                     array=(tabla["ic_sup"] - tabla["pct"]).tolist(),
                     arrayminus=(tabla["pct"] - tabla["ic_inf"]).tolist(),
                     color="#5F6368", thickness=1.2),
        customdata=tabla["n"],
        hovertemplate="<b>%{x}</b><br>%{y:.1f} % · base %{customdata}<extra></extra>"))
    fig.update_layout(
        title=dict(text=titulo, x=0, font=dict(size=15)),
        height=340, margin=dict(l=10, r=10, t=50, b=10), showlegend=False,
        yaxis=dict(title="% del grupo", rangemode="tozero"),
        xaxis=dict(title=""))
    return fig


def figura_items_pssm(items: list[dict]) -> go.Figure:
    """Barras horizontales con la media de los ítems de pertenencia más bajos."""
    items = list(reversed(items))
    fig = go.Figure(go.Bar(
        x=[it["media"] for it in items],
        y=[it["enunciado"] for it in items], orientation="h",
        marker_color=COLOR_BARRA,
        text=[f"{it['media']:.2f}" for it in items], textposition="outside",
        hovertemplate="<b>%{y}</b><br>Media %{x:.2f} de 5<extra></extra>"))
    fig.update_layout(
        height=max(240, 60 * len(items)), margin=dict(l=10, r=40, t=10, b=10),
        showlegend=False, xaxis=dict(range=[1, 5], title="Media del grupo (1 a 5)"),
        yaxis=dict(title=""))
    return fig


def _sin_datos() -> None:
    """Mensaje de ayuda cuando no hay nada que mostrar, sin lanzar excepción."""
    st.info(
        "Todavía no hay resultados de estudiantes para mostrar. Cargue los dos "
        "formularios («¡Cuéntanos sobre tu bienestar emocional!» y «¡Cuéntanos "
        "sobre tus emociones!») en formato CSV o Excel desde la sección de carga "
        "de datos; la vista aparece en cuanto el procesamiento termina.",
        icon="📄")


def _selector_grupo(analisis, columna: str, etiqueta: str) -> tuple[str, list[str]]:
    """Selectbox poblado solo con grupos que llegan a `MIN_GROUP_N`."""
    visibles, pequenos = grupos_visibles(analisis, columna)
    if not visibles:
        return TODOS, pequenos
    valor = st.sidebar.selectbox(etiqueta, [TODOS] + visibles,
                                 key=f"est_com_{columna.lower()}")
    return valor, pequenos


# ══ Render ═════════════════════════════════════════════════════════════════
def render_comunidad(analisis: dict, informes: list | None = None) -> None:
    """Vista comunidad del módulo de estudiantes.

    `analisis` es {"secundaria": Analisis, "primaria": Analisis}; puede faltar
    una clave o venir vacío, en cuyo caso se explica cómo cargar los datos.
    """
    st.subheader("🏫 Estudiantes · para colegios, familias y el municipio")
    st.caption("Cómo está mi grupo, qué significa y qué puedo hacer. "
               "Nada individual, nunca.")

    if not analisis:
        _sin_datos()
        return

    rol = st.radio("Estoy viendo esto como", list(cat.ROLES),
                   format_func=lambda r: cat.ROLES[r], horizontal=True,
                   key="est_com_rol")

    st.sidebar.markdown("### Estudiantes · vista comunidad")
    disponibles = [n for n in (cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA) if n in analisis]
    disponibles += [n for n in analisis if n not in disponibles]
    nivel = st.sidebar.radio("Nivel", disponibles,
                             format_func=lambda n: NIVELES_LABEL.get(n, n),
                             key="est_com_nivel")
    a = analisis.get(nivel)
    if a is None or getattr(a, "n", 0) < cat.MIN_GROUP_N:
        _sin_datos()
        return

    colegio, peq_colegio = (_selector_grupo(a, "Colegio", "Colegio")
                            if ve_colegios(rol) else (TODOS, []))
    grado, peq_grado = _selector_grupo(a, "Grado", "Grado")
    filtros = {"nivel": nivel, "colegio": colegio, "grado": grado}

    # ── 1. bandas del SDQ total
    b = bandas_sdq_total(a, filtros)
    st.markdown(f"#### Cómo está el grupo · {etiqueta_filtro(a, filtros)}")
    if b:
        st.plotly_chart(figura_bandas(b), width="stretch",
                        key="est_com_bandas")
    else:
        st.info("Este grupo no tiene suficientes respuestas para mostrar la "
                "distribución por niveles.", icon="ℹ️")

    # ── 2. tarjetas
    fichas = tarjetas(a, rol, filtros)
    if fichas:
        columnas = st.columns(len(fichas))
        for col, t in zip(columnas, fichas):
            with col:
                titulo = cat.MENSAJES[t.clave].titulo if t.clave in cat.MENSAJES else ""
                with st.container(border=True):
                    st.markdown(f"**{titulo}**")
                    st.markdown(f"## {t.cifra}")
                    st.caption(t.etiqueta)
                    st.markdown(f"**Qué significa:** {t.significa}")
                    st.markdown(f"**Qué hacer:** {t.accion}")
                    if t.detalle:
                        st.caption(t.detalle)
    else:
        st.info("Aún no hay indicadores con base suficiente para este grupo.", icon="ℹ️")

    # ── 3. comparación por grado o por colegio
    st.markdown("#### Comparar entre grupos")
    dimensiones = ["Grado"] + (["Colegio"] if ve_colegios(rol) else [])
    col_izq, col_der = st.columns([1, 1])
    with col_izq:
        dimension = st.radio("Comparar por", dimensiones, horizontal=True,
                             key="est_com_dimension")
    with col_der:
        opciones = [k for k in INDICADORES if prevalencia(a, k, {})]
        if not opciones:
            opciones = ["sdq_alto"]
        indicador = st.selectbox(
            "Indicador", opciones,
            format_func=lambda k: INDICADORES[k]["etiqueta"].capitalize(),
            key="est_com_indicador")
    tabla = prevalencia_por(a, indicador, dimension, filtros)
    if tabla.empty:
        st.info("No hay grupos con suficientes estudiantes para comparar.", icon="ℹ️")
    else:
        st.plotly_chart(
            figura_comparativa(tabla, INDICADORES[indicador]["etiqueta"].capitalize()),
            width="stretch", key="est_com_comparativa")
        st.caption("Las líneas verticales son el margen de error (intervalo de "
                   "Wilson al 95 %). Se compara, no se ranquea.")
    pequenos = peq_grado + peq_colegio
    if pequenos:
        st.caption(f"{len(pequenos)} grupos no se muestran por ser grupos pequeños "
                   f"(menos de {cat.MIN_GROUP_N} estudiantes); sus respuestas sí "
                   "cuentan en el total.")

    # ── 4. ítems de pertenencia más bajos
    items = items_pertenencia_bajos(a, 4, filtros)
    if items:
        st.markdown("#### Los cuatro enunciados de pertenencia con la media más baja")
        st.plotly_chart(figura_items_pssm(items), width="stretch",
                        key="est_com_items_pssm")
        st.caption("Enunciados tomados del instrumento aplicado. Las medias están "
                   "orientadas (mayor es mejor), así que los cinco enunciados "
                   "negativos se leen en positivo.")

    # ── 5. ruta de atención, siempre visible
    with st.container(border=True):
        st.markdown("#### 🆘 Si un estudiante necesita ayuda")
        for nombre, detalle in cat.RUTA_ATENCION:
            st.markdown(f"- **{nombre}** — {detalle}")

    # ── 6. avisos
    st.warning(cat.AVISO_TAMIZAJE, icon="⚠️")
    if nivel == cat.NIVEL_PRIMARIA:
        st.warning(cat.AVISO_PRIMARIA, icon="⚠️")
    with st.expander("De dónde vienen los puntos de corte"):
        st.markdown(cat.AVISO_NORMAS)
        for aviso in getattr(a, "avisos", []) or []:
            if aviso not in (cat.AVISO_PRIMARIA, cat.AVISO_NORMAS, cat.AVISO_TAMIZAJE):
                st.caption(f"· {aviso}")
        for inf in informes or []:
            for aviso in getattr(inf, "avisos", []) or []:
                st.caption(f"· {aviso}")

    # ── 7. descarga del informe
    st.download_button(
        "⬇️ Descargar informe de una página",
        data=informe_markdown(a, rol, filtros),
        file_name=f"informe_estudiantes_{nivel}_{rol}.md",
        mime="text/markdown", key="est_com_descarga")
