"""
Vista investigador del módulo Estudiantes 360 — Observatorio 360.

Replica la maqueta aprobada de «Para el equipo investigador»
(docs/superpowers/specs/2026-09-17-plan-estudiantes.html): muestra y
exclusiones, Tabla 1 con alfa, cortes y bandas, correlaciones con corrección,
comparaciones por grupo con tamaño de efecto, modelos con errores robustos por
colegio, calidad de datos y un paquete exportable por corrida.

Esta vista NO calcula estadística: consume el objeto `Analisis` que produce
`src.estudiantes.pipeline.analizar`. Si falta una cifra, se pide a
`src.estudiantes.stats`; nunca se escribe estadística propia aquí.

Privacidad: ninguna fila individual se muestra ni se exporta. Los grupos con
menos de `catalog.MIN_GROUP_N` casos llegan ya filtrados y no se reintroducen.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import zipfile

import pandas as pd
import plotly.express as px
import streamlit as st

from src.estudiantes import catalog as cat

# ── Constantes de presentación ──────────────────────────────────────────────
ALPHA_MINIMO = 0.70
COLOR_ALERTA = "#B07D0D"
COLOR_OK = "#1A7F4B"
ESCALA_DIVERGENTE = "RdBu_r"
NOMBRES_NIVEL = {cat.NIVEL_SECUNDARIA: "Secundaria · 6.º a 10.º",
                 cat.NIVEL_PRIMARIA: "Primaria · 4.º y 5.º"}

# Etiquetas del flujo de exclusiones, en el orden del diagrama de la muestra
PASOS_EXCLUSION = [
    ("filas_archivo", "Respuestas en el archivo"),
    ("sin_consentimiento", "Sin consentimiento"),
    ("excluidas_prueba", "Filas de prueba (misma persona, varios colegios el mismo día)"),
    ("excluidas_colegio_unico", "Colegios con una sola respuesta"),
    ("duplicados_eliminados", "Duplicados (se conserva el primer envío)"),
]

COLUMNAS_TABLA1 = ["nivel", "clave", "escala", "n", "M", "DE", "Mdn", "min", "max",
                   "rango", "alpha", "alpha_ic", "pct_sobre_corte", "corte_aplicado",
                   "fuente_corte", "validada"]

ARCHIVOS_PAQUETE = ["tabla1_descriptivos.csv", "bandas_y_cortes.csv", "correlaciones_bh.csv",
                    "comparaciones_grupo.csv", "modelos.csv", "flujo_exclusiones.md",
                    "metodologia.md", "version_analisis.txt"]

NOTA_ALPHA = ("α por debajo de 0,70 en naranja. En el SDQ autoinforme las subescalas de "
              "conducta y de problemas con pares suelen quedar bajas, como en casi toda la "
              "literatura: esos resultados se apoyan en el total y en internalizante / "
              "externalizante, no se leen solos.")

NOTA_ICC = ("Un CCI cercano a cero significa que casi toda la variación está entre "
            "estudiantes y prácticamente nada entre colegios: el colegio no explica el "
            "indicador y no cabe ranquearlos por él.")

_SIN_DATO = "—"


# ══════════════════════════════════════════════════════════════════════════
# Utilidades internas
# ══════════════════════════════════════════════════════════════════════════
def _niveles(analisis: dict) -> list[str]:
    """Niveles presentes, secundaria primero."""
    orden = [cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA]
    return [n for n in orden if n in analisis] + [n for n in analisis if n not in orden]


def _como_dict(analisis) -> dict:
    """Acepta un dict de niveles o un único `Analisis` y devuelve siempre el dict."""
    if isinstance(analisis, dict):
        return analisis
    if analisis is None:
        return {}
    return {getattr(analisis, "nivel", "muestra"): analisis}


def _informe_de(informes, nivel: str):
    """Informe de ingesta correspondiente a un nivel educativo, si existe."""
    for inf in informes or []:
        if getattr(inf, "nivel", None) == nivel:
            return inf
    return None


def _con_nivel(df: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Copia de `df` con el nivel educativo como primera columna."""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    out = df.copy()
    out.insert(0, "nivel", nivel)
    return out


def _texto_ic(lo, hi, decimales: int = 2, sufijo: str = "") -> str:
    if pd.isna(lo) or pd.isna(hi):
        return _SIN_DATO
    return f"[{lo:.{decimales}f}{sufijo}–{hi:.{decimales}f}{sufijo}]"


def _sin_listas(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte a texto las celdas que son listas o tuplas, para poder exportar a CSV."""
    out = df.copy()
    for c in out.columns:
        if out[c].map(lambda v: isinstance(v, (list, tuple, set))).any():
            out[c] = out[c].map(
                lambda v: " · ".join(map(str, v)) if isinstance(v, (list, tuple, set)) else v)
    return out


def _csv(df: pd.DataFrame) -> str:
    """CSV sin índice, con las celdas de tipo lista convertidas a texto."""
    if df is None or len(df) == 0:
        return ""
    return _sin_listas(df).to_csv(index=False)


def _hash_estructura(a) -> str:
    """SHA-1 de las columnas y el tamaño del DataFrame analizado, nunca de los datos."""
    datos = getattr(a, "datos", None)
    if datos is None:
        return _SIN_DATO
    firma = "|".join(map(str, datos.columns)) + f"|{datos.shape[0]}x{datos.shape[1]}"
    return hashlib.sha1(firma.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════
# Funciones puras: tablas y textos exportables
# ══════════════════════════════════════════════════════════════════════════
def _cortes_de_clave(a, clave: str) -> tuple[str, str, str]:
    """(% sobre corte, corte aplicado, fuente) para una puntuación de la Tabla 1."""
    cortes = getattr(a, "cortes", pd.DataFrame())
    if isinstance(cortes, pd.DataFrame) and not cortes.empty and "clave" in cortes.columns:
        filas = cortes[cortes["clave"] == clave]
        if not filas.empty:
            pct = " · ".join(f"{v:.1f} %" for v in filas["pct"])
            indicadores = " · ".join(str(v) for v in filas["indicador"])
            fuentes = " · ".join(dict.fromkeys(str(v) for v in filas["fuente"]))
            return pct, indicadores, fuentes

    percentiles = getattr(a, "percentiles", pd.DataFrame())
    if (isinstance(percentiles, pd.DataFrame) and not percentiles.empty
            and "clave" in percentiles.columns and clave in set(percentiles["clave"])):
        return (_SIN_DATO, "Puntuación T pendiente; percentiles propios por sexo",
                cat.RCADS.fuente)

    terciles = getattr(a, "terciles", pd.DataFrame())
    if (isinstance(terciles, pd.DataFrame) and not terciles.empty
            and "clave" in terciles.columns and clave in set(terciles["clave"])):
        return _SIN_DATO, "Terciles de esta muestra (sin corte clínico)", "Relativo a la muestra"

    escala = cat.escala_de(clave)
    return _SIN_DATO, _SIN_DATO, escala.fuente if escala else _SIN_DATO


def _tabla1_nivel(a, nivel: str) -> pd.DataFrame:
    """Tabla 1 de un solo nivel: descriptivos + fiabilidad + cortes, en orden canónico."""
    desc = getattr(a, "descriptivos", pd.DataFrame())
    if not isinstance(desc, pd.DataFrame) or desc.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA1)
    d = desc.set_index("clave")

    fia = getattr(a, "fiabilidad", pd.DataFrame())
    f = (fia.set_index("clave") if isinstance(fia, pd.DataFrame) and not fia.empty
         and "clave" in fia.columns else pd.DataFrame())

    filas = []
    for clave in cat.ORDEN_TABLA1:
        if clave not in d.index:
            continue
        fila_d = d.loc[clave]
        m = cat.meta(clave)
        alpha = ic_alpha = None
        if clave in getattr(f, "index", []):
            fila_f = f.loc[clave]
            alpha = fila_f.get("alpha")
            ic_alpha = _texto_ic(fila_f.get("ic_inf"), fila_f.get("ic_sup"), 3)
        pct, corte, fuente = _cortes_de_clave(a, clave)
        filas.append({
            "nivel": nivel, "clave": clave, "escala": m["label"],
            "n": int(fila_d["n"]), "M": fila_d["M"], "DE": fila_d["DE"],
            "Mdn": fila_d["Mdn"], "min": fila_d["min"], "max": fila_d["max"],
            "rango": fila_d["rango"],
            "alpha": alpha, "alpha_ic": ic_alpha or _SIN_DATO,
            "pct_sobre_corte": pct, "corte_aplicado": corte, "fuente_corte": fuente,
            "validada": bool(m["validada"]),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_TABLA1)


def tabla1(analisis) -> pd.DataFrame:
    """Tabla 1 del artículo: una fila por puntuación del catálogo presente y nivel.

    Acepta el dict `{nivel: Analisis}` o un único `Analisis`. Une descriptivos,
    fiabilidad y prevalencias sobre corte; respeta `catalog.ORDEN_TABLA1`.
    """
    niveles = _como_dict(analisis)
    trozos = [_tabla1_nivel(niveles[n], n) for n in _niveles(niveles)]
    trozos = [t for t in trozos if not t.empty]
    if not trozos:
        return pd.DataFrame(columns=COLUMNAS_TABLA1)
    return pd.concat(trozos, ignore_index=True)


def bandas_y_cortes(analisis) -> pd.DataFrame:
    """Tabla larga con bandas del SDQ, prevalencias sobre corte, terciles y percentiles."""
    niveles = _como_dict(analisis)
    trozos = []
    secciones = [("Bandas del SDQ (autoinforme)", "bandas"),
                 ("Prevalencia sobre corte (IC de Wilson)", "cortes"),
                 ("Terciles de la muestra", "terciles"),
                 ("Percentiles propios por sexo", "percentiles")]
    for nivel in _niveles(niveles):
        a = niveles[nivel]
        for etiqueta, campo in secciones:
            df = getattr(a, campo, pd.DataFrame())
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            t = _con_nivel(df, nivel)
            t.insert(1, "seccion", etiqueta)
            trozos.append(t)
    if not trozos:
        return pd.DataFrame()
    return _sin_listas(pd.concat(trozos, ignore_index=True))


def correlaciones_bh(analisis) -> pd.DataFrame:
    """Correlaciones de Spearman con IC, p y q de Benjamini-Hochberg, por nivel."""
    niveles = _como_dict(analisis)
    trozos = [_con_nivel(getattr(niveles[n], "correlaciones", pd.DataFrame()), n)
              for n in _niveles(niveles)]
    trozos = [t for t in trozos if not t.empty]
    return pd.concat(trozos, ignore_index=True) if trozos else pd.DataFrame()


def comparaciones_grupo(analisis) -> pd.DataFrame:
    """Comparaciones por sexo, grado, colegio y edad, apiladas con su tipo de contraste."""
    niveles = _como_dict(analisis)
    fuentes = [("Sexo (Mann-Whitney, d de Cohen)", "por_sexo"),
               ("Grado (Kruskal-Wallis)", "por_grado"),
               ("Colegio (Kruskal-Wallis)", "por_colegio"),
               ("Edad (Spearman)", "por_edad")]
    trozos = []
    for nivel in _niveles(niveles):
        a = niveles[nivel]
        for etiqueta, campo in fuentes:
            df = getattr(a, campo, pd.DataFrame())
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            t = _con_nivel(df, nivel)
            t.insert(1, "comparacion", etiqueta)
            trozos.append(t)
    if not trozos:
        return pd.DataFrame()
    return pd.concat(trozos, ignore_index=True)


def modelos_tabla(analisis) -> pd.DataFrame:
    """Un renglón por coeficiente de cada modelo, con su R², N y conglomerados."""
    niveles = _como_dict(analisis)
    filas = []
    for nivel in _niveles(niveles):
        for m in getattr(niveles[nivel], "modelos", []) or []:
            for c in m.get("coeficientes", []):
                filas.append(dict(
                    nivel=nivel, y=m.get("y"), y_etiqueta=m.get("y_etiqueta"),
                    n=m.get("n"), conglomerados=m.get("clusters"), R2=m.get("R2"),
                    predictor=c.get("predictor"), etiqueta=c.get("etiqueta"),
                    beta=c.get("beta"), se=c.get("se"), p=c.get("p"),
                    significativo=c.get("significativo"), aviso=m.get("aviso", "")))
    return pd.DataFrame(filas)


def icc_tabla(analisis) -> pd.DataFrame:
    """CCI entre colegios por puntuación y nivel."""
    niveles = _como_dict(analisis)
    filas = []
    for nivel in _niveles(niveles):
        for clave, valor in (getattr(niveles[nivel], "icc", {}) or {}).items():
            filas.append(dict(nivel=nivel, clave=clave, escala=cat.meta(clave)["label"],
                              CCI=valor))
    return pd.DataFrame(filas)


def flujo_exclusiones_md(informes: list | None) -> str:
    """Flujo de la muestra en Markdown, listo para el diagrama del artículo."""
    lineas = ["# Flujo de la muestra · Estudiantes 360", ""]
    if not informes:
        lineas += ["No hay informes de ingesta disponibles para esta corrida: el flujo de "
                   "exclusiones no se puede reconstruir.", ""]
        return "\n".join(lineas)

    lineas += ["Reglas de exclusión aplicadas en el orden en que las aplica la ingesta "
               "(`src/estudiantes/ingest.py`).", ""]
    for inf in informes:
        nivel = getattr(inf, "nivel", "sin nivel")
        lineas += [f"## {NOMBRES_NIVEL.get(nivel, nivel)}", "",
                   "| Paso | Casos | Quedan |", "| --- | ---: | ---: |"]
        restantes = int(getattr(inf, "filas_archivo", 0) or 0)
        lineas.append(f"| {PASOS_EXCLUSION[0][1]} | {restantes} | {restantes} |")
        for campo, etiqueta in PASOS_EXCLUSION[1:]:
            quitadas = int(getattr(inf, campo, 0) or 0)
            restantes -= quitadas
            lineas.append(f"| − {etiqueta} | {quitadas} | {restantes} |")
        validas = int(getattr(inf, "filas_validas", restantes) or restantes)
        lineas += [f"| **Respuestas válidas analizadas** | | **{validas}** |", ""]
        erq = int(getattr(inf, "erq_invalidado", 0) or 0)
        if erq:
            lineas += [f"Además, {erq} respuesta(s) conservan la fila pero pierden el bloque "
                       "de regulación emocional (ERQ-CA): responder el mínimo en los diez "
                       "ítems es implausible y se trata como artefacto de aplicación.", ""]
        enmascarados = list(getattr(inf, "colegios_enmascarados", []) or [])
        if enmascarados:
            lineas += [f"Colegios con menos de {cat.MIN_GROUP_N} respuestas, incluidos en el "
                       f"total pero nunca mostrados por separado: {', '.join(enmascarados)}.",
                       ""]
        ausentes = list(getattr(inf, "escalas_ausentes", []) or [])
        if ausentes:
            lineas += [f"Escalas que este formulario no trae: {', '.join(ausentes)}.", ""]
    return "\n".join(lineas)


def metodologia_md(analisis, informes: list | None = None) -> str:
    """Método completo en Markdown: instrumentos, puntuación, cortes, exclusiones y límites."""
    niveles = _como_dict(analisis)
    hoy = _dt.date.today().isoformat()
    lineas = [
        "# Metodología · Módulo Estudiantes 360",
        "",
        f"Observatorio 360 · Chía, Cundinamarca. Documento generado el {hoy} a partir del "
        "catálogo del instrumento (`src/estudiantes/catalog.py`), que es la única fuente de "
        "verdad de ítems, inversos y puntos de corte.",
        "",
        "## 1. Muestra",
        "",
    ]
    if niveles:
        for nivel in _niveles(niveles):
            a = niveles[nivel]
            m = getattr(a, "muestra", {}) or {}
            sexo = ", ".join(f"{k}: {v}" for k, v in (m.get("sexo") or {}).items())
            fechas = m.get("fechas") or []
            periodo = f"del {fechas[0]} al {fechas[1]}" if len(fechas) == 2 else "sin fechas"
            lineas.append(
                f"- **{NOMBRES_NIVEL.get(nivel, nivel)}**: n = {m.get('n', getattr(a, 'n', 0))}; "
                f"{sexo or 'sexo sin dato'}; edad media {m.get('edad_M', '—')} "
                f"(DE {m.get('edad_DE', '—')}); recogida {periodo}.")
    else:
        lineas.append("- Sin datos cargados.")

    lineas += ["", "## 2. Instrumentos", "",
               "| Escala | Ítems | Valores | Edad validada | Fuente |",
               "| --- | ---: | --- | --- | --- |"]
    for e in cat.ESCALAS:
        marca = "" if e.validada else " *(exploratoria)*"
        lineas.append(f"| {e.nombre}{marca} | {e.n_items} | {e.valor_min}–{e.valor_max} | "
                      f"{e.edad_validada[0]}–{e.edad_validada[1]} | {e.fuente} |")

    lineas += ["", "## 3. Puntuación", "",
               "- Los ítems inversos se recodifican como (mínimo + máximo) − x con el rango "
               "de su escala. Inversos del SDQ: "
               f"{', '.join(map(str, cat.SDQ_REVERSE_ITEMS))}; del PSSM: "
               f"{', '.join(map(str, cat.PSSM_REVERSE_ITEMS))}.",
               "- Cada subescala exige un mínimo de ítems respondidos; por debajo de ese "
               "mínimo la puntuación queda faltante. Dentro de la tolerancia, las sumas se "
               "prorratean al número de ítems completos y las medias se calculan sobre los "
               "ítems respondidos.",
               "- El ARI suma únicamente los ítems 1 a 6; el ítem 7 mide deterioro funcional "
               "y se reporta aparte.",
               "- Compuestas del SDQ: total de dificultades (emocional + conducta + "
               "hiperactividad + pares), internalizante (emocional + pares) y externalizante "
               "(conducta + hiperactividad).",
               "- Fiabilidad: α de Cronbach con casos completos e intervalo del 95 % por "
               "bootstrap; α por debajo de 0,70 se señala explícitamente.",
               "", "## 4. Puntos de corte y su fuente", "",
               "| Indicador | Corte | Fuente |", "| --- | --- | --- |",
               f"| SDQ, cuatro bandas ({', '.join(cat.BANDAS_LABELS)}) | "
               f"Tabla de bandas del autoinforme; alto o muy alto = banda 3 o 4 | "
               f"{cat.FUENTE_BANDS_SELF} |"]
    for etiqueta, descripcion in cat.subescala("ARI_Total").cortes:
        lineas.append(f"| ARI, irritabilidad | {etiqueta} — {descripcion} | {cat.ARI.fuente} |")
    lineas += [f"| RCADS-25 | Sin corte: la puntuación T exige tablas que no tenemos, así que "
               f"se usan percentiles propios por sexo | {cat.RCADS.fuente} |",
               f"| MSPSS y PSSM | Media por debajo de 3 (punto medio de la escala), umbral "
               f"descriptivo y no clínico | {cat.MSPSS.fuente} |",
               f"| PSSM, ítem {cat.PSSM_ITEM_ADULTO} (adulto de confianza) | Respuesta ≤ 2 | "
               f"{cat.PSSM.fuente} |",
               f"| RCADS, ítem {cat.RCADS_ITEM_MUERTE} (piensa en la muerte) | Respuesta ≥ 2; "
               "señal de alerta, nunca diagnóstico | Ítem 18 del RCADS-25 |",
               "| ERQ-CA, MSPSS, PSSM y toma de decisiones | Terciles de esta muestra | "
               "Relativo a la muestra, no clínico |",
               "",
               "Las bandas de la versión para cuidadores existen en el catálogo solo para "
               "contraste con el dataset de cuidadores: a los estudiantes se les aplican "
               "siempre las de autoinforme.",
               "",
               "## 5. Reglas de exclusión", "",
               "1. **Consentimiento**: se excluye quien no responde afirmativamente a la "
               "pregunta de consentimiento.",
               "2. **Filas de prueba**: la misma persona registrada el mismo día en más de un "
               "colegio se descarta como aplicación de prueba.",
               "3. **Colegios con una sola respuesta**: se excluyen, y la regla se reaplica "
               "porque quitar filas puede dejar a otro colegio con una sola.",
               "4. **Duplicados**: por identificador derivado del nombre, dentro de cada "
               "formulario y entre los dos formularios; se conserva el primer envío.",
               "5. **Invalidación del bloque ERQ-CA**: quien responde el valor mínimo en los "
               "diez ítems pierde ese bloque (reevaluación y supresión son estrategias "
               "opuestas: el patrón es un artefacto de aplicación, no un resultado).",
               "6. **Valores fuera del rango de la escala**: se marcan como faltantes.",
               "7. **Edad fuera del rango validado**: se conserva el caso y se declara; "
               "primaria responde SDQ y MSPSS por debajo de la edad validada.",
               "",
               "El nombre completo llega en el formulario, se convierte en un hash y la "
               "columna se elimina antes de guardar nada: ninguna salida de este módulo "
               "contiene nombres ni filas individuales.",
               ""]
    lineas += [flujo_exclusiones_md(informes).replace("# Flujo", "## Flujo", 1), ""]

    lineas += ["## 6. Análisis estadístico", "",
               "- Proporciones con intervalo de confianza del 95 % de Wilson.",
               "- Correlaciones de Spearman con IC por transformación de Fisher y corrección "
               "de Benjamini-Hochberg (q < 0,05).",
               "- Comparación por sexo con Mann-Whitney y d de Cohen; por grado y colegio con "
               "Kruskal-Wallis y eta cuadrado; asociación con la edad por Spearman.",
               "- Regresiones con predictores estandarizados y errores estándar robustos por "
               "conglomerado (colegio).",
               "- Coeficiente de correlación intraclase para cuantificar la varianza entre "
               "colegios.",
               f"- Ningún grupo con menos de {cat.MIN_GROUP_N} casos se reporta desagregado.",
               "", "## 7. Limitaciones", "",
               f"- {cat.AVISO_NORMAS}",
               f"- {cat.AVISO_TAMIZAJE}",
               f"- {cat.AVISO_PRIMARIA}",
               "- Todo es autorreporte del mismo informante: las correlaciones entre escalas "
               "comparten varianza de método y se leen con esa reserva.",
               "- Diseño transversal: ninguna asociación se puede leer como causal.",
               "- El número de colegios es pequeño, así que los errores robustos por "
               "conglomerado son aproximados y el nivel escolar no se modela.",
               "- La escala de toma de decisiones no tiene fuente documentada y se reporta "
               "como exploratoria.",
               ""]
    avisos = []
    for nivel in _niveles(niveles):
        for aviso in getattr(niveles[nivel], "avisos", []) or []:
            if aviso not in avisos:
                avisos.append(aviso)
    if avisos:
        lineas += ["## 8. Avisos de esta corrida", ""] + [f"- {a}" for a in avisos] + [""]
    return "\n".join(lineas)


def version_analisis_txt(analisis, informes: list | None = None) -> str:
    """Trazabilidad de la corrida: fecha, N por nivel y hash de la estructura analizada."""
    niveles = _como_dict(analisis)
    ahora = _dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")
    lineas = ["Observatorio 360 · Módulo Estudiantes · versión del análisis",
              "=" * 62, "",
              f"Fecha de la corrida: {ahora}",
              "Módulos: src/estudiantes/{catalog,ingest,scoring,stats,pipeline}.py",
              "Vista: src/ui/views/estudiantes_investigador.py", ""]
    total = 0
    for nivel in _niveles(niveles):
        a = niveles[nivel]
        n = int(getattr(a, "n", 0) or 0)
        total += n
        datos = getattr(a, "datos", None)
        forma = f"{datos.shape[0]} filas × {datos.shape[1]} columnas" if datos is not None \
            else _SIN_DATO
        escalas = ", ".join(getattr(a, "escalas", []) or []) or _SIN_DATO
        lineas += [f"[{nivel}]",
                   f"  N analizado .......... {n}",
                   f"  Forma del DataFrame .. {forma}",
                   f"  SHA-1 de estructura .. {_hash_estructura(a)}",
                   f"  Escalas puntuadas .... {escalas}",
                   ""]
    lineas += [f"N total: {total}", ""]
    if informes:
        lineas.append("Informes de ingesta:")
        for inf in informes:
            lineas.append(f"  {getattr(inf, 'nivel', '?')}: "
                          f"{getattr(inf, 'filas_archivo', 0)} en el archivo → "
                          f"{getattr(inf, 'filas_validas', 0)} válidas")
        lineas.append("")
    lineas += ["El hash se calcula sobre los nombres de columna y el tamaño del DataFrame "
               "analizado, no sobre los datos: identifica la estructura de la corrida sin "
               "exponer ninguna respuesta individual.", ""]
    return "\n".join(lineas)


def archivos_paquete(analisis, informes: list | None = None) -> dict[str, str]:
    """Contenido de cada exportable, como texto. Ninguno contiene filas individuales."""
    return {
        "tabla1_descriptivos.csv": _csv(tabla1(analisis)),
        "bandas_y_cortes.csv": _csv(bandas_y_cortes(analisis)),
        "correlaciones_bh.csv": _csv(correlaciones_bh(analisis)),
        "comparaciones_grupo.csv": _csv(comparaciones_grupo(analisis)),
        "modelos.csv": _csv(modelos_tabla(analisis)),
        "flujo_exclusiones.md": flujo_exclusiones_md(informes),
        "metodologia.md": metodologia_md(analisis, informes),
        "version_analisis.txt": version_analisis_txt(analisis, informes),
    }


def paquete_zip(analisis, informes: list | None = None) -> bytes:
    """ZIP de la corrida con los ocho exportables, generado en memoria."""
    buffer = io.BytesIO()
    contenidos = archivos_paquete(analisis, informes)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre in ARCHIVOS_PAQUETE:
            z.writestr(nombre, contenidos.get(nombre, ""))
    return buffer.getvalue()


# ══════════════════════════════════════════════════════════════════════════
# Pestañas de la vista
# ══════════════════════════════════════════════════════════════════════════
def _edad_legible(clave) -> str:
    """«13.0» → «13». La edad es un entero y así se lee."""
    try:
        return str(int(float(clave)))
    except (TypeError, ValueError):
        return str(clave)


def _tabla_conteos(pares, etiqueta: str) -> pd.DataFrame:
    """Tabla de conteos con la columna `n` en un solo tipo.

    Los conteos de una corrida publicada pueden venir enmascarados como «<10».
    Mezclar números y texto en la misma columna hace fallar la conversión a
    Arrow que usa `st.dataframe`: Streamlit lo arregla solo, pero llena el
    registro de trazas. Se formatea todo a texto, que además alinea mejor.
    """
    filas = [(clave, f"{int(valor):,}".replace(",", " ")
              if isinstance(valor, (int, float)) and not isinstance(valor, bool)
              else str(valor))
             for clave, valor in pares]
    return pd.DataFrame(filas, columns=[etiqueta, "n"])


def _conteo(valor) -> float:
    """Conteo como número para poder ordenar.

    Los conteos que llegan de la corrida publicada pueden venir enmascarados
    como «<10» cuando la celda está por debajo del mínimo publicable. Ese texto
    se ordena como el valor más bajo posible, que es lo que significa.
    """
    try:
        return float(valor)
    except (TypeError, ValueError):
        return -1.0


def _tab_muestra(a, informe, nivel: str) -> None:
    m = getattr(a, "muestra", {}) or {}
    st.subheader("Muestra")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("N analizado", m.get("n", getattr(a, "n", 0)))
    c2.metric("Edad media", f"{m.get('edad_M', float('nan'))}",
              help=f"DE {m.get('edad_DE', '—')}")
    c3.metric("Colegios", len(m.get("colegio") or {}))
    fechas = m.get("fechas") or []
    c4.metric("Recogida", f"{fechas[0]} → {fechas[1]}" if len(fechas) == 2 else _SIN_DATO)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Sexo**")
        st.dataframe(_tabla_conteos(sorted((m.get("sexo") or {}).items()), "Sexo"),
                     hide_index=True, width="stretch")
        st.markdown("**Edad**")
        # Las corridas anteriores guardaron la edad como «13.0»; se limpia al
        # mostrarla para no enseñar un decimal que no significa nada.
        edades = [(_edad_legible(k), v) for k, v in (m.get("edad") or {}).items()]
        st.dataframe(_tabla_conteos(sorted(edades, key=lambda kv: _conteo(kv[0])), "Edad"),
                     hide_index=True, width="stretch")
    with c2:
        orden = (cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA
                 else cat.ORDEN_GRADOS_PRI)
        grados = m.get("grado") or {}
        filas = [(g, grados[g]) for g in orden if g in grados]
        filas += [(g, n) for g, n in grados.items() if g not in orden]
        st.markdown("**Grado**")
        st.dataframe(_tabla_conteos(filas, "Grado"),
                     hide_index=True, width="stretch")
        st.markdown("**Colegio**")
        colegios = sorted((m.get("colegio") or {}).items(),
                          key=lambda kv: -_conteo(kv[1]))
        st.dataframe(_tabla_conteos(colegios, "Colegio"),
                     hide_index=True, width="stretch")
        st.caption(f"Los colegios con menos de {cat.MIN_GROUP_N} estudiantes entran en el "
                   "total pero no se muestran desagregados en ninguna otra pestaña.")

    st.divider()
    st.subheader("Flujo de exclusiones")
    if informe is None:
        st.info("No llegó el informe de ingesta de este nivel, así que el flujo de la muestra "
                "no se puede reconstruir. Vuelve a cargar los formularios para obtenerlo.")
    else:
        restantes = int(getattr(informe, "filas_archivo", 0) or 0)
        filas = [{"Paso": PASOS_EXCLUSION[0][1], "Casos": restantes, "Quedan": restantes}]
        for campo, etiqueta in PASOS_EXCLUSION[1:]:
            quitadas = int(getattr(informe, campo, 0) or 0)
            restantes -= quitadas
            filas.append({"Paso": f"− {etiqueta}", "Casos": -quitadas, "Quedan": restantes})
        filas.append({"Paso": "Respuestas válidas analizadas", "Casos": None,
                      "Quedan": int(getattr(informe, "filas_validas", restantes) or restantes)})
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
        erq = int(getattr(informe, "erq_invalidado", 0) or 0)
        if erq:
            st.warning(f"{erq} respuesta(s) conservan la fila pero pierden el bloque de "
                       "regulación emocional (ERQ-CA) por responder el mínimo en los diez "
                       "ítems: artefacto de aplicación, no resultado.")
        st.caption("Este es el diagrama de la muestra del artículo: se lee de arriba abajo y "
                   "cada resta corresponde a una regla documentada en metodologia.md.")


def _tab_tabla1(a, nivel: str) -> None:
    st.subheader("Tabla 1 · descriptivos y fiabilidad")
    t = _tabla1_nivel(a, nivel)
    if t.empty:
        st.info("No hay puntuaciones calculadas para este nivel.")
        return
    vista = t.drop(columns=["nivel", "clave"]).rename(columns={
        "escala": "Escala", "n": "N", "Mdn": "Mediana", "rango": "Rango teórico",
        "alpha": "α", "alpha_ic": "IC 95 % de α", "pct_sobre_corte": "% sobre corte",
        "corte_aplicado": "Corte aplicado", "fuente_corte": "Fuente del corte",
        "validada": "Validada"})

    def _pinta_alpha(valor):
        if valor is None or pd.isna(valor):
            return ""
        return (f"color: {COLOR_ALERTA}; font-weight: 600" if float(valor) < ALPHA_MINIMO
                else f"color: {COLOR_OK}")

    st.dataframe(vista.style.map(_pinta_alpha, subset=["α"]),
                 hide_index=True, width="stretch")
    bajas = t[t["alpha"].notna() & (t["alpha"].astype(float) < ALPHA_MINIMO)]
    st.caption(NOTA_ALPHA)
    if not bajas.empty:
        st.warning("α por debajo de 0,70 en: "
                   + ", ".join(f"{r.escala} ({r.alpha:.2f})" for r in bajas.itertuples()))


def _tab_cortes(a) -> None:
    st.subheader("Bandas del SDQ autoinforme")
    bandas = getattr(a, "bandas", pd.DataFrame())
    if isinstance(bandas, pd.DataFrame) and not bandas.empty:
        filas = []
        for r in bandas.itertuples():
            etiquetas = getattr(r, "etiquetas", cat.BANDAS_LABELS)
            for i in range(4):
                filas.append(dict(Escala=r.escala, Banda=etiquetas[i],
                                  idx=i, pct=getattr(r, f"pct_b{i}"),
                                  n=getattr(r, f"n_b{i}")))
        largo = pd.DataFrame(filas)
        tabla = bandas[["escala", "n"] + [f"pct_b{i}" for i in range(4)]
                       + ["pct_alto_o_muy_alto"]].rename(columns={
                           "escala": "Escala", "n": "N",
                           "pct_b0": "Cercano al promedio", "pct_b1": "Ligeramente elevado",
                           "pct_b2": "Alto", "pct_b3": "Muy alto",
                           "pct_alto_o_muy_alto": "Alto + muy alto"})
        st.dataframe(tabla, hide_index=True, width="stretch")
        fig = px.bar(largo, x="pct", y="Escala", color="Banda", orientation="h",
                     text="pct", custom_data=["n"],
                     category_orders={"Escala": list(bandas["escala"])},
                     color_discrete_sequence=["#1A7F4B", "#8AB833", "#FBBC04", "#C0392B"],
                     labels={"pct": "% de la muestra"})
        fig.update_traces(texttemplate="%{text:.0f}%",
                          hovertemplate="%{y}<br>%{fullData.name}: %{x:.1f} %"
                                        " (%{customdata[0]} casos)<extra></extra>")
        fig.update_layout(barmode="stack", height=60 * len(bandas) + 140,
                          xaxis=dict(range=[0, 100]), margin=dict(l=10, r=10, t=30, b=10),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
        st.caption("En la banda prosocial las etiquetas se leen al revés: la puntuación alta "
                   "es lo deseable, así que «bajo» y «muy bajo» son las bandas de alerta.")
    else:
        st.info("No hay bandas del SDQ para este nivel.")

    st.divider()
    st.subheader("Prevalencias sobre corte, con IC de Wilson")
    cortes = getattr(a, "cortes", pd.DataFrame())
    if isinstance(cortes, pd.DataFrame) and not cortes.empty:
        vista = cortes.copy()
        vista["IC 95 %"] = [_texto_ic(lo, hi, 1, " %")
                            for lo, hi in zip(vista["ic_inf"], vista["ic_sup"])]
        vista = vista[["indicador", "n", "casos", "pct", "IC 95 %", "fuente"]].rename(
            columns={"indicador": "Indicador", "n": "Base N", "casos": "Casos",
                     "pct": "%", "fuente": "Fuente del corte"})
        st.dataframe(vista, hide_index=True, width="stretch")
    else:
        st.info("No hay prevalencias sobre corte para este nivel.")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Terciles de la muestra")
        terciles = getattr(a, "terciles", pd.DataFrame())
        if isinstance(terciles, pd.DataFrame) and not terciles.empty:
            st.dataframe(terciles.rename(columns={"escala": "Escala", "n": "N",
                                                  "corte_bajo": "Corte bajo (P33)",
                                                  "corte_alto": "Corte alto (P67)",
                                                  "nota": "Nota"}).drop(columns=["clave"]),
                         hide_index=True, width="stretch")
        else:
            st.caption("Sin terciles para este nivel.")
    with c2:
        st.subheader("Percentiles propios por sexo")
        pc = getattr(a, "percentiles", pd.DataFrame())
        if isinstance(pc, pd.DataFrame) and not pc.empty:
            st.dataframe(pc.drop(columns=["clave"]).rename(columns={"escala": "Escala",
                                                                    "sexo": "Sexo", "n": "N"}),
                         hide_index=True, width="stretch")
            st.caption("Sustituyen a las puntuaciones T del RCADS, que exigen tablas "
                       "normativas que este proyecto no tiene.")
        else:
            st.caption("Este nivel no respondió el RCADS, así que no hay percentiles propios.")

    st.info(cat.AVISO_NORMAS)


def _tab_correlaciones(a) -> None:
    st.subheader("Matriz de correlaciones de Spearman")
    matriz = getattr(a, "matriz", pd.DataFrame())
    if isinstance(matriz, pd.DataFrame) and not matriz.empty:
        etiquetas = [cat.meta(c)["label"] for c in matriz.columns]
        fig = px.imshow(matriz.values, x=etiquetas, y=etiquetas, text_auto=".2f",
                        zmin=-1, zmax=1, color_continuous_scale=ESCALA_DIVERGENTE,
                        aspect="auto", labels=dict(color="ρ"))
        fig.update_layout(height=60 + 34 * len(etiquetas),
                          margin=dict(l=10, r=10, t=30, b=10),
                          coloraxis_colorbar=dict(title="ρ"))
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, width="stretch")
        st.caption("Escala divergente centrada en cero: el rojo marca asociación positiva y "
                   "el azul negativa. Todo es autorreporte del mismo informante, así que "
                   "estas correlaciones comparten varianza de método.")
    else:
        st.info("No hay matriz de correlaciones para este nivel.")

    st.divider()
    st.subheader("Correlaciones por pares, con IC y corrección de Benjamini-Hochberg")
    corr = getattr(a, "correlaciones", pd.DataFrame())
    if not isinstance(corr, pd.DataFrame) or corr.empty:
        st.info("No hay correlaciones por pares para este nivel.")
        return
    c1, c2 = st.columns([2, 1])
    minimo = c1.slider("Magnitud mínima de ρ", 0.0, 0.9, 0.10, 0.05,
                       key="inv_corr_rho")
    solo_sig = c2.checkbox("Solo las que sobreviven a la corrección (q < 0,05)", value=True,
                           key="inv_corr_sig")
    vista = corr[corr["rho"].abs() >= minimo]
    if solo_sig and "significativa" in vista.columns:
        vista = vista[vista["significativa"]]
    if vista.empty:
        st.warning("Ningún par cumple los filtros seleccionados.")
        return
    tabla = vista.copy()
    tabla["IC 95 %"] = [_texto_ic(lo, hi, 3)
                        for lo, hi in zip(tabla["ic_inf"], tabla["ic_sup"])]
    tabla = tabla[["etiqueta_a", "etiqueta_b", "rho", "IC 95 %", "p", "q_bh", "n"]].rename(
        columns={"etiqueta_a": "Variable A", "etiqueta_b": "Variable B", "rho": "ρ",
                 "q_bh": "q (BH)", "n": "N"})
    st.dataframe(tabla.style.format({"p": "{:.4f}", "q (BH)": "{:.4f}"}),
                 hide_index=True, width="stretch")
    st.caption(f"{len(vista)} de {len(corr)} pares cumplen los filtros.")


def _tab_por_grupo(a) -> None:
    st.subheader("Por sexo · Mann-Whitney y d de Cohen")
    por_sexo = getattr(a, "por_sexo", pd.DataFrame())
    if isinstance(por_sexo, pd.DataFrame) and not por_sexo.empty:
        vista = por_sexo.drop(columns=["clave"]).rename(columns={
            "escala": "Escala", "n_mujer": "N mujeres", "n_hombre": "N hombres",
            "M_mujer": "M mujeres", "M_hombre": "M hombres", "DE_mujer": "DE mujeres",
            "DE_hombre": "DE hombres", "d": "d de Cohen", "magnitud": "Magnitud",
            "q_bh": "q (BH)"})
        st.dataframe(vista.style.format({"p": "{:.4f}", "q (BH)": "{:.4f}"}),
                     hide_index=True, width="stretch")
        st.caption("d positiva = las mujeres puntúan más alto. Magnitud según los umbrales "
                   "convencionales: < 0,20 trivial, < 0,50 pequeño, < 0,80 mediano.")
    else:
        st.info("No hay comparación por sexo para este nivel.")

    for titulo, campo, nota in [
        ("Por grado · Kruskal-Wallis", "por_grado",
         "eta cuadrado es la proporción de varianza que explica el grado."),
        ("Por colegio · Kruskal-Wallis", "por_colegio",
         "Se compara, no se ranquea: con pocos colegios un orden no significa nada."),
        ("Con la edad · Spearman", "por_edad",
         "ρ positiva = la puntuación sube con la edad."),
    ]:
        st.divider()
        st.subheader(titulo)
        df = getattr(a, campo, pd.DataFrame())
        if isinstance(df, pd.DataFrame) and not df.empty:
            vista = df.drop(columns=["clave"]).rename(columns={"escala": "Escala",
                                                               "q_bh": "q (BH)"})
            st.dataframe(vista.style.format({"p": "{:.4f}", "q (BH)": "{:.4f}"}),
                         hide_index=True, width="stretch")
            st.caption(nota)
        else:
            st.info("Sin datos suficientes para esta comparación en este nivel.")

    enmascarados = getattr(a, "enmascarados", {}) or {}
    detalle = {k: v for k, v in enmascarados.items() if v}
    with st.expander(f"Grupos enmascarados ({sum(len(v) for v in detalle.values())})"):
        if not detalle:
            st.write("Ningún grupo quedó enmascarado en este nivel.")
        else:
            for columna, grupos in detalle.items():
                st.markdown(f"- **{columna}**: {', '.join(map(str, grupos))}")
            st.caption(f"Quedan fuera de las desagregaciones por tener menos de "
                       f"{cat.MIN_GROUP_N} respuestas. Siguen contando en los totales: "
                       "enmascarar no es excluir.")


def _tab_modelos(a) -> None:
    st.subheader("Modelos · β estandarizados, EE robustos por colegio")
    modelos = getattr(a, "modelos", []) or []
    if not modelos:
        st.info("No hay modelos para este nivel: la regresión exige al menos 30 casos "
                "completos en todas las variables.")
    for m in modelos:
        st.markdown(f"#### {m.get('y_etiqueta', m.get('y'))}")
        c1, c2, c3 = st.columns(3)
        c1.metric("N", m.get("n", _SIN_DATO))
        c2.metric("Conglomerados", m.get("clusters", _SIN_DATO))
        c3.metric("R²", m.get("R2", _SIN_DATO))
        coef = pd.DataFrame(m.get("coeficientes", []))
        if not coef.empty:
            vista = coef.drop(columns=["predictor"]).rename(columns={
                "etiqueta": "Predictor", "beta": "β", "se": "EE",
                "significativo": "p < 0,05"})

            def _pinta(fila):
                fuerte = bool(fila.get("p < 0,05"))
                return ["font-weight: 700" if fuerte else "" for _ in fila]

            st.dataframe(vista.style.apply(_pinta, axis=1).format({"p": "{:.4f}"}),
                         hide_index=True, width="stretch")
        if m.get("aviso"):
            st.warning(m["aviso"])
        st.divider()

    st.subheader("Coeficiente de correlación intraclase entre colegios")
    icc = getattr(a, "icc", {}) or {}
    if icc:
        tabla = pd.DataFrame([dict(Escala=cat.meta(k)["label"], CCI=v)
                              for k, v in icc.items()])
        st.dataframe(tabla, hide_index=True, width="stretch")
    else:
        st.info("No hay CCI para este nivel.")
    st.caption(NOTA_ICC)


def _tab_calidad(a, informe) -> None:
    st.subheader("Calidad de datos")
    st.caption("Esta pestaña dice si se puede confiar en el resto de la vista.")
    if informe is None:
        st.info("Sin informe de ingesta para este nivel: los indicadores de calidad de la "
                "carga no están disponibles.")
    else:
        faltantes = getattr(informe, "faltantes_por_escala", {}) or {}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**% de ítems faltantes por escala**")
            if faltantes:
                tabla = pd.DataFrame(sorted(faltantes.items(),
                                            key=lambda kv: -_conteo(kv[1])),
                                     columns=["Escala", "% faltante"])
                st.dataframe(tabla, hide_index=True, width="stretch")
            else:
                st.caption("Sin dato de faltantes.")
            st.markdown("**Edades fuera del rango validado**")
            fuera = getattr(informe, "edades_fuera_de_rango", {}) or {}
            if fuera:
                st.dataframe(pd.DataFrame(sorted(fuera.items()),
                                          columns=["Escala", "Casos fuera de rango"]),
                             hide_index=True, width="stretch")
                st.caption("Se conservan y se declaran; no se excluyen.")
            else:
                st.caption("Ninguna edad cae fuera del rango validado.")
        with c2:
            st.markdown("**Etiquetas de respuesta que no se pudieron mapear**")
            no_map = getattr(informe, "etiquetas_no_mapeadas", {}) or {}
            if no_map:
                filas = [dict(Escala=k, Etiquetas=" · ".join(map(str, v)))
                         for k, v in no_map.items()]
                st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
                st.warning("Estas respuestas quedaron como faltantes. Si son muchas, hay que "
                           "añadir la etiqueta al mapa del catálogo antes de publicar cifras.")
            else:
                st.success("Todas las etiquetas del formulario se mapearon a número.")
            st.metric("Bloques ERQ-CA invalidados",
                      int(getattr(informe, "erq_invalidado", 0) or 0),
                      help="Respuestas con el valor mínimo en los diez ítems: artefacto de "
                           "aplicación, no resultado.")
            st.markdown("**Escalas**")
            st.write("Detectadas: " + (", ".join(getattr(informe, "escalas_detectadas", []))
                                       or _SIN_DATO))
            st.write("Ausentes: " + (", ".join(getattr(informe, "escalas_ausentes", []))
                                     or "ninguna"))

    st.divider()
    st.markdown("**Faltantes en las puntuaciones derivadas**")
    desc = getattr(a, "descriptivos", pd.DataFrame())
    if isinstance(desc, pd.DataFrame) and not desc.empty and "pct_faltante" in desc.columns:
        tabla = desc[["escala", "n", "pct_faltante"]].rename(
            columns={"escala": "Escala", "n": "N con puntuación",
                     "pct_faltante": "% sin puntuación"})
        st.dataframe(tabla.sort_values("% sin puntuación", ascending=False),
                     hide_index=True, width="stretch")

    st.divider()
    st.markdown("**Avisos de esta corrida**")
    avisos = list(getattr(a, "avisos", []) or [])
    avisos += [x for x in list(getattr(informe, "avisos", []) or []) if x not in avisos] \
        if informe is not None else []
    if avisos:
        for aviso in avisos:
            st.warning(aviso)
    else:
        st.success("Sin avisos: la ingesta no encontró nada que declarar.")


def _tab_exportar(analisis: dict, informes: list | None) -> None:
    st.subheader("Paquete exportable de la corrida")
    st.caption("Todo lo que sale de aquí es agregado: ni una fila individual, ni una columna "
               "de identificación. Lo que se publique tiene que poder rastrearse hasta la "
               "corrida que lo produjo.")
    contenidos = archivos_paquete(analisis, informes)
    descripciones = {
        "tabla1_descriptivos.csv": "Tabla 1: N, M, DE, mediana, rango, α con IC y cortes.",
        "bandas_y_cortes.csv": "Bandas del SDQ, prevalencias con IC, terciles y percentiles.",
        "correlaciones_bh.csv": "Spearman con IC, p, q de Benjamini-Hochberg y N.",
        "comparaciones_grupo.csv": "Sexo, grado, colegio y edad con tamaño de efecto.",
        "modelos.csv": "Coeficientes estandarizados, EE robustos, p, R² y conglomerados.",
        "flujo_exclusiones.md": "Diagrama de la muestra, paso por paso.",
        "metodologia.md": "Instrumentos, puntuación, cortes con fuente, exclusiones y límites.",
        "version_analisis.txt": "Fecha, N por nivel y hash de la estructura analizada.",
    }
    columnas = st.columns(2)
    for i, nombre in enumerate(ARCHIVOS_PAQUETE):
        with columnas[i % 2]:
            contenido = contenidos.get(nombre, "")
            st.download_button(
                f"⬇️ {nombre}", data=contenido.encode("utf-8-sig"), file_name=nombre,
                mime="text/csv" if nombre.endswith(".csv") else "text/markdown",
                disabled=not contenido, width="stretch",
                key=f"inv_dl_{nombre}", help=descripciones.get(nombre, ""))
            st.caption(descripciones.get(nombre, ""))

    st.divider()
    sello = _dt.date.today().isoformat()
    st.download_button(
        "📦 Descargar el paquete completo (ZIP)",
        data=paquete_zip(analisis, informes),
        file_name=f"estudiantes360_corrida_{sello}.zip",
        mime="application/zip", type="primary", width="stretch",
        key="inv_dl_zip")
    st.caption(f"Contiene los {len(ARCHIVOS_PAQUETE)} archivos de arriba más el hash de "
               "estructura de la corrida.")


# ══════════════════════════════════════════════════════════════════════════
# Entrada de la vista
# ══════════════════════════════════════════════════════════════════════════
def render_investigador(analisis: dict, informes: list | None = None) -> None:
    """Dibuja la vista investigador completa a partir del resultado del pipeline."""
    st.title("Estudiantes 360 · vista investigador")
    if not analisis:
        st.info(
            "Todavía no hay datos de estudiantes cargados. Para verlos: deja los dos "
            "formularios exportados de Google Forms («¡Cuéntanos sobre tu bienestar "
            "emocional!» y «¡Cuéntanos sobre tus emociones!», en CSV o XLSX) en la carpeta "
            "de trabajo y vuelve a cargar el dataset desde la pantalla de carga. El módulo "
            "los detecta por sus columnas, deriva el identificador por hash y descarta el "
            "nombre antes de guardar nada.")
        return

    niveles = _niveles(analisis)
    if len(niveles) > 1:
        nivel = st.radio("Nivel educativo", niveles, horizontal=True,
                         format_func=lambda n: NOMBRES_NIVEL.get(n, n),
                         key="inv_nivel")
    else:
        nivel = niveles[0]
        st.caption(NOMBRES_NIVEL.get(nivel, nivel))

    a = analisis[nivel]
    informe = _informe_de(informes, nivel)
    if nivel == cat.NIVEL_PRIMARIA:
        st.warning(cat.AVISO_PRIMARIA)

    tabs = st.tabs(["Muestra y exclusiones", "Tabla 1 · descriptivos", "Cortes y bandas",
                    "Correlaciones", "Por grupo", "Modelos", "Calidad de datos", "Exportar"])
    with tabs[0]:
        _tab_muestra(a, informe, nivel)
    with tabs[1]:
        _tab_tabla1(a, nivel)
    with tabs[2]:
        _tab_cortes(a)
    with tabs[3]:
        _tab_correlaciones(a)
    with tabs[4]:
        _tab_por_grupo(a)
    with tabs[5]:
        _tab_modelos(a)
    with tabs[6]:
        _tab_calidad(a, informe)
    with tabs[7]:
        _tab_exportar(analisis, informes)

    st.caption(cat.AVISO_TAMIZAJE)
