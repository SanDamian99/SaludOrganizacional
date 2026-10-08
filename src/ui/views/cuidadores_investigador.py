"""
Vista investigador de Cuidadores 360 — Observatorio 360 (fase 4a).

Misma estructura que la de estudiantes: un selector de marco (cuidadores o
niños, como el de nivel) y las pestañas de muestra, Tabla 1, cortes y bandas,
correlaciones, por grupo, señales del adulto, ítems, calidad y exportación.

No calcula estadística: consume el `AnalisisCuidadores` de
`src.cuidadores.pipeline`. Todo lo que muestra o exporta es agregado, ya pasó
por la base publicable (cuidadores distintos) y por la supresión de cifras
pequeñas. Ninguna tabla lleva `casos`, identificadores ni filas.

Solo existe en los modos completo e investigador: `main.py` no la importa en el
despliegue público.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import zipfile

import pandas as pd
import streamlit as st

from src.cuidadores import catalog as cat

PESTANAS = ["Muestra y exclusiones", "Tabla 1 · descriptivos", "Cortes y bandas",
            "Correlaciones", "Por grupo", "Señales del adulto", "Ítems sin puntaje",
            "Calidad de datos", "Exportar"]

ARCHIVOS_PAQUETE = ["tabla1_descriptivos.csv", "cortes_y_bandas.csv", "cortes_por_grupo.csv",
                    "correlaciones_bh.csv", "comparaciones_grupo.csv",
                    "flujo_exclusiones.md", "metodologia.md", "version_analisis.txt"]

# Columnas que nunca salen de esta vista, aunque una tabla las traiga.
COLUMNAS_PROHIBIDAS = ("casos", "ID_cuidador", "ID_nino", "n_b0", "n_b1", "n_b2", "n_b3",
                       "k_bajo", "k_alto")

PASOS_EXCLUSION = [
    ("filas_archivo", "Respuestas en el archivo"),
    ("sin_consentimiento", "Sin consentimiento"),
    ("respuestas_repetidas_cuidador", "El mismo cuidador más de una vez (se queda la más reciente)"),
]

_SIN_DATO = "—"
# Indicadores que solo se muestran y exportan en el total del marco (spec §5.5:
# la autolesión, solo a nivel municipio), nunca por colegio, grado ni celda.
SOLO_EN_EL_TOTAL = ("EPDS_Autolesion",)
SOLO_TODAS = ("Con una ola elegida no se exporta nada: el paquete solo se descarga con «Todas» "
              "las olas. La vista de una ola muestra solo el total de cada marco y oculta toda "
              "cifra que, restada de «Todas», dejaría ver a menos de 10 cuidadores o a menos "
              "de 3 casos o no casos.")
SOLO_TOTAL_OLA = ("Con una ola elegida no se desagrega por colegio, grado ni celda: solo se "
                  "muestra el total de cada marco.")


# ══════════════════════════════════════════════════════════════════════════
# Funciones puras
# ══════════════════════════════════════════════════════════════════════════
def _limpia(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    out = df.drop(columns=[c for c in COLUMNAS_PROHIBIDAS if c in df.columns]).copy()
    for c in out.columns:
        if out[c].map(lambda v: isinstance(v, (list, tuple, set))).any():
            out[c] = out[c].map(lambda v: " · ".join(map(str, v))
                                if isinstance(v, (list, tuple, set)) else v)
    return out


def _con_marco(df: pd.DataFrame, marco: str) -> pd.DataFrame:
    df = _limpia(df)
    if df.empty:
        return df
    df.insert(0, "marco", marco)
    return df


def _csv(df: pd.DataFrame) -> str:
    df = _limpia(df)
    return "" if df.empty else df.to_csv(index=False)


def conteo_legible(valor) -> str:
    """Conteos de grupo: por debajo del mínimo, «<10»."""
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return _SIN_DATO
    return str(v) if v >= cat.MIN_GROUP_N else f"<{cat.MIN_GROUP_N}"


def tabla_conteos(conteos: dict, etiqueta: str, orden: list | None = None) -> pd.DataFrame:
    claves = [k for k in (orden or []) if k in conteos] + \
        sorted((k for k in conteos if k not in (orden or [])),
               key=lambda k: -int(conteos[k]) if str(conteos[k]).isdigit() else 0)
    return pd.DataFrame([(k, conteo_legible(conteos[k])) for k in claves],
                        columns=[etiqueta, "Cuidadores"])


def tabla1(ac) -> pd.DataFrame:
    filas = []
    for marco, a in ac.marcos.items():
        desc = getattr(a, "descriptivos", pd.DataFrame())
        if desc is None or desc.empty:
            continue
        fia = getattr(a, "fiabilidad", pd.DataFrame())
        fia = fia.set_index("clave") if fia is not None and not fia.empty else pd.DataFrame()
        for _, f in desc.iterrows():
            alpha = fia.loc[f["clave"]] if f["clave"] in fia.index else None
            filas.append(dict(
                marco=marco, clave=f["clave"], escala=f["escala"], n=f["n"], M=f["M"],
                DE=f["DE"], Mdn=f["Mdn"], rango=f["rango"],
                alpha=None if alpha is None else alpha["alpha"],
                alpha_ic=(_SIN_DATO if alpha is None or alpha["ic_inf"] is None
                          or pd.isna(alpha["ic_inf"])
                          else f"[{alpha['ic_inf']:.2f}–{alpha['ic_sup']:.2f}]"),
                pct_faltante=f["pct_faltante"], fuente=f["fuente"]))
    return pd.DataFrame(filas)


def cortes_y_bandas(ac) -> pd.DataFrame:
    partes = []
    for marco, a in ac.marcos.items():
        partes.append(_con_marco(getattr(a, "cortes", None), marco).assign(tabla="corte"))
        b = _limpia(getattr(a, "bandas", None))
        if not b.empty:
            b = b.drop(columns=[c for c in ("etiquetas",) if c in b.columns])
            partes.append(_con_marco(b, marco).assign(tabla="bandas_padres"))
        partes.append(_con_marco(getattr(a, "terciles", None), marco).assign(tabla="terciles"))
    partes = [p for p in partes if not p.empty]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def cortes_por_grupo(ac) -> pd.DataFrame:
    """Cortes de cada colegio, grado y celda que quedaron publicables (sin casos)."""
    filas = []
    for marco, a in ac.marcos.items():
        for agrupacion, grupos in (getattr(a, "subgrupos", None) or {}).items():
            for grupo, s in grupos.items():
                t = _limpia(getattr(s, "cortes", None))
                if not t.empty and "clave" in t.columns:
                    t = t[~t["clave"].isin(SOLO_EN_EL_TOTAL)]
                if t.empty:
                    continue
                t.insert(0, "grupo", grupo)
                t.insert(0, "agrupacion", agrupacion)
                t.insert(0, "marco", marco)
                filas.append(t)
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


def correlaciones(ac) -> pd.DataFrame:
    partes = [_con_marco(getattr(a, "correlaciones", None), m) for m, a in ac.marcos.items()]
    partes = [p for p in partes if not p.empty]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def comparaciones_grupo(ac) -> pd.DataFrame:
    partes = []
    for marco, a in ac.marcos.items():
        for nombre, campo in (("Colegio", "por_colegio"), ("Grado", "por_grado"),
                              ("Sexo del niño", "por_sexo")):
            t = _con_marco(getattr(a, campo, None), marco)
            if not t.empty:
                t.insert(1, "comparacion", nombre)
                partes.append(t)
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def senales_adulto(ac) -> pd.DataFrame:
    """Ánimo (EPDS) en el total y en cada grupo con cifra; autolesión (ítem 10), solo total."""
    t = cortes_por_grupo(ac)
    nivel = _con_marco(getattr(ac.cuidador, "cortes", None), cat.MARCO_CUIDADOR)
    if not nivel.empty:
        nivel.insert(1, "agrupacion", "Total")
        nivel.insert(2, "grupo", "Todos")
        t = pd.concat([nivel, t], ignore_index=True)
    if t.empty:
        return t
    return t[t["clave"].isin(["EPDS_Total", "EPDS_Autolesion"])].reset_index(drop=True)


def flujo_exclusiones_md(informe, ac=None) -> str:
    """Flujo de la muestra. Con una ola elegida, añade cómo se llega a la ola desde «Todas»."""
    if informe is None:
        return ""
    lineas = ["# Flujo de la muestra · Cuidadores 360", "",
              "Archivo completo (todas las olas):", ""]
    restantes = int(informe.filas_archivo)
    lineas.append(f"- {PASOS_EXCLUSION[0][1]}: {restantes}")
    for campo, etiqueta in PASOS_EXCLUSION[1:]:
        quitadas = int(getattr(informe, campo, 0) or 0)
        restantes -= quitadas
        lineas.append(f"- − {etiqueta}: {quitadas} → quedan {restantes}")
    lineas += [f"- Cuidadores distintos analizados: {informe.cuidadores_distintos}", "",
               "## Niños", "",
               f"- Filas de niño (hijo 1 y hijo 2): {informe.filas_nino}",
               f"- − El mismo niño como hijo 1 y hijo 2 en un envío: "
               f"{informe.mismo_nino_misma_respuesta}",
               f"- Niños reportados por más de un cuidador: {informe.mismo_nino_otro_cuidador}",
               f"- Niños repetidos entre olas: {informe.mismo_nino_entre_olas}",
               f"- Niños únicos analizados: {informe.ninos_unicos}", "",
               "Prioridad al deduplicar niños: la ola más reciente; luego mamá, papá, otro "
               "cuidador; luego el primer envío. Cuidadores: la respuesta más reciente."]
    flujo = getattr(ac, "flujo_ola", None) or {}
    if getattr(ac, "ola", None) and flujo:
        lineas += ["", f"## Ola {ac.ola}", "",
                   "Se deduplica sobre todas las olas y luego se filtra: la ola es parte del "
                   "total publicable de «Todas».", ""]
        for marco, nombre in ((cat.MARCO_CUIDADOR, "Cuidadores"), (cat.MARCO_NINO, "Niños")):
            f = flujo.get(marco)
            if not f:
                continue
            quedan = f["en_base"]
            lineas += [f"- {nombre} distintos (todas las olas): {f['distintos']}",
                       f"- − Fuera del total publicable de «Todas»: {f['fuera_de_base']} → "
                       f"quedan {quedan}",
                       f"- − Su respuesta más reciente es de otra ola: {f['otras_olas']} → "
                       f"quedan {quedan - f['otras_olas']}"]
    return "\n".join(lineas) + "\n"


def metodologia_md(ac) -> str:
    inf = ac.informe
    olas = ", ".join(f"{o}: {n}" for o, n in (inf.por_ola or {}).items())
    lineas = [
        "# Metodología · Cuidadores 360 (fase 4a, solo local)", "",
        "## Instrumento", "",
        "Formulario «Cuidando al Cuidador», leído por posición y verificado con el texto de "
        "cada encabezado. Cada respuesta se convierte en número por su texto, con un mapa "
        "explícito por ítem (src/cuidadores/catalog.py).", "",
        f"Olas: {olas or _SIN_DATO}. El filtro de ola existe solo en la vista local: se "
        "deduplica sobre todas las olas y la ola es parte del total publicable de «Todas». "
        "Con una ola solo se muestra el total de cada marco; una cifra se oculta si la ola o "
        "su resta con «Todas» tiene menos de 10 cuidadores distintos o menos de 3 casos o no "
        "casos. Este paquete solo se exporta con «Todas».", "",
        "## Identificadores", "",
        "Los nombres se convierten en seudónimos HMAC-SHA256 con una clave local "
        "(OBS360_CLAVE_HMAC) y no se guardan. El teléfono no se lee. Ninguna tabla de este "
        "paquete lleva identificadores ni filas.", "",
        "## Puntuación", "",
        "- PSS-10: 0–40, ítems 3, 4, 5, 7 y 9 invertidos (igual que docentes); se prorratea "
        "con 9 de 10 ítems. «Columna 6» cuenta como faltante. Sin corte: terciles.",
        f"- EPDS-10: 0–30 con los 10 ítems. Ánimo posible ≥ {cat.EPDS_POSIBLE}, probable "
        f"≥ {cat.EPDS_PROBABLE}. Autolesión: ítem 10 distinto de «No, nunca». "
        + cat.AVISO_EPDS,
        "- MSPSS del cuidador: media 1–5 por fuente (5 / 4 / 3 ítems) y total. "
        + cat.AVISO_MSPSS,
        "- Riesgo del barrio: suma de 5 ítems (0–10).",
        "- " + cat.AVISO_APQ + " " + cat.APQ_FISICO_FALTANTE,
        "- " + cat.AVISO_ESTRES_PARENTAL,
        "- SDQ de padres: subescalas estándar y bandas de la versión para padres 4-17. "
        + cat.AVISO_SDQ_EDAD,
        "- ARI de padres: ítems 1–6 (0–12) y deterioro (ítem 7). " + cat.AVISO_ARI, "",
        "## Privacidad", "",
        "- " + cat.AVISO_MINIMO,
        "- Base publicable: celdas colegio × grado con 10 o más cuidadores distintos; colegio, "
        "grado y total se calculan sobre la unión de esas celdas (spec §5.1).",
        "- Todo o nada por indicador y supresión de proporciones con menos de 3 casos o no "
        "casos, también por resta (estudiantes/supresion.py).",
        "- «OTRO» (colegio no reconocido) y «SIN_DATO» nunca forman grupo.", "",
        "## Grado", "",
        "El curso se escribe a mano. Reglas: palabra de grado («Sexto 602» → Sexto), número "
        "de una o dos cifras («5A» → Quinto) y código de curso («501» → Quinto, «1002» → "
        "Décimo). Grados del estudio: cuarto a décimo; los demás quedan «fuera del rango "
        "del estudio» y solo cuentan en el total.",
    ]
    return "\n".join(lineas) + "\n"


def _hash_estructura(ac) -> str:
    firma = "|".join(f"{m}:{','.join(map(str, a.datos.columns))}:{a.datos.shape}"
                     for m, a in ac.marcos.items() if getattr(a, "datos", None) is not None)
    return hashlib.sha1(firma.encode("utf-8")).hexdigest()


def version_analisis_txt(ac) -> str:
    return "\n".join([
        "Cuidadores 360 · versión del análisis",
        f"Fecha: {_dt.date.today().isoformat()}",
        f"Ola: {ac.ola or 'todas'}",
        f"Cuidadores analizados: {ac.cuidador.n}",
        f"Niños analizados: {ac.nino.n}",
        f"Hash de estructura: {_hash_estructura(ac)}",
    ]) + "\n"


def exportable(ac) -> bool:
    """El paquete solo se exporta con «Todas» las olas."""
    return getattr(ac, "ola", None) is None


def archivos_paquete(ac) -> dict[str, str]:
    if not exportable(ac):
        return {}
    return {
        "tabla1_descriptivos.csv": _csv(tabla1(ac)),
        "cortes_y_bandas.csv": _csv(cortes_y_bandas(ac)),
        "cortes_por_grupo.csv": _csv(cortes_por_grupo(ac)),
        "correlaciones_bh.csv": _csv(correlaciones(ac)),
        "comparaciones_grupo.csv": _csv(comparaciones_grupo(ac)),
        "flujo_exclusiones.md": flujo_exclusiones_md(ac.informe, ac),
        "metodologia.md": metodologia_md(ac),
        "version_analisis.txt": version_analisis_txt(ac),
    }


def paquete_zip(ac) -> bytes:
    if not exportable(ac):
        raise ValueError("El paquete de Cuidadores 360 solo se exporta con «Todas» las olas.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in archivos_paquete(ac).items():
            if contenido:
                z.writestr(nombre, contenido)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════
# Pestañas
# ══════════════════════════════════════════════════════════════════════════
def _df(t: pd.DataFrame) -> None:
    t = _limpia(t)
    if t.empty:
        st.caption("Sin datos para mostrar.")
    else:
        st.dataframe(t, hide_index=True, width="stretch")


def _tab_muestra(ac, a, marco: str) -> None:
    informe = ac.informe
    m = getattr(a, "muestra", {}) or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas analizadas", m.get("n", a.n))
    c2.metric("Cuidadores distintos", m.get("n_cuidadores", _SIN_DATO))
    c3.metric("Colegios con 10 o más", len(getattr(a, "subgrupos", {}).get("Colegio", {})))
    fechas = m.get("fechas") or []
    c4.metric("Recogida", f"{fechas[0]} → {fechas[1]}" if len(fechas) == 2 else _SIN_DATO)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Ola**")
        st.dataframe(tabla_conteos(m.get("ola") or {}, "Ola"), hide_index=True,
                     width="stretch")
        st.markdown("**Quién responde**")
        st.dataframe(tabla_conteos(m.get("quien") or {}, "Quién"), hide_index=True,
                     width="stretch")
    with c2:
        st.markdown("**Colegio**")
        st.dataframe(tabla_conteos(m.get("colegio") or {}, "Colegio"), hide_index=True,
                     width="stretch")
        st.markdown("**Grado del estudio**")
        st.dataframe(tabla_conteos(m.get("grado") or {}, "Grado", list(cat.GRADOS_ESTUDIO)),
                     hide_index=True, width="stretch")
    st.caption(cat.AVISO_MINIMO)
    st.divider()
    st.subheader("Flujo de la muestra")
    st.markdown(flujo_exclusiones_md(informe, ac))


def _tab_tabla1(ac, marco: str) -> None:
    t = tabla1(ac)
    _df(t[t["marco"] == marco].drop(columns=["marco"]) if not t.empty else t)
    st.caption("α con IC por bootstrap sobre casos completos. Las cifras salen de la base "
               "publicable (cuidadores distintos).")


def _tab_cortes(a, marco: str) -> None:
    st.markdown("**Prevalencias sobre corte**")
    _df(getattr(a, "cortes", None))
    if marco == cat.MARCO_NINO:
        st.markdown("**Bandas del SDQ de padres**")
        b = _limpia(getattr(a, "bandas", None))
        _df(b.drop(columns=[c for c in ("etiquetas",) if c in b.columns]) if not b.empty else b)
    st.markdown("**Terciles (escalas sin corte clínico)**")
    _df(getattr(a, "terciles", None))
    st.caption("Un «—» o una celda vacía es una cifra suprimida: menos de 3 casos o no casos, "
               "directamente o por resta.")


def _tab_correlaciones(a) -> None:
    _df(getattr(a, "correlaciones", None))
    st.caption("Spearman con IC de Fisher; q de Benjamini-Hochberg.")


def _tab_por_grupo(ac, a, marco: str) -> None:
    if not exportable(ac):
        st.caption(SOLO_TOTAL_OLA)
        return
    t = comparaciones_grupo(ac)
    _df(t[t["marco"] == marco].drop(columns=["marco"]) if not t.empty else t)
    st.markdown("**Cortes por colegio, grado y celda**")
    g = cortes_por_grupo(ac)
    _df(g[g["marco"] == marco].drop(columns=["marco"]) if not g.empty else g)
    enm = getattr(a, "enmascarados", {}) or {}
    if enm.get("Colegio") or enm.get("Grado"):
        st.caption("No se desagregan (menos de 10 cuidadores distintos o sin celda "
                   f"publicable): {len(enm.get('Colegio', []))} colegios y "
                   f"{len(enm.get('Grado', []))} grados.")


def _tab_senales(ac) -> None:
    st.info(cat.AVISO_EPDS)
    _df(senales_adulto(ac))
    st.caption("Definiciones provisionales (spec §5.5): ánimo = EPDS ≥ 13; autolesión = "
               "ítem 10 distinto de «No, nunca». La autolesión solo se muestra en el total, "
               "aquí y en la vista de comunidad (4b), nunca por colegio, grado ni celda.")


def _tab_items(ac) -> None:
    st.markdown("**APQ · prácticas de crianza (% «a veces» o más)**")
    st.caption(cat.AVISO_APQ)
    _df(getattr(ac, "items_apq", None))
    st.markdown("**Estrés parental · ítems (% «de acuerdo» o «muy de acuerdo»)**")
    st.caption(cat.AVISO_ESTRES_PARENTAL)
    _df(getattr(ac, "items_estres", None))


def _tab_calidad(ac, a) -> None:
    inf = ac.informe
    st.caption("Calidad de datos del archivo completo (todas las olas).")
    c1, c2, c3 = st.columns(3)
    c1.metric("Edades no numéricas", inf.edad_no_numerica)
    c2.metric("Edades fuera de 4–17", inf.edad_fuera_de_rango)
    c3.metric("Cursos sin resolver", inf.curso_sin_resolver)
    c1, c2, c3 = st.columns(3)
    c1.metric("«Columna 6» en la PSS", inf.respuestas_columna6_pss)
    c2.metric("Colegio no reconocido (filas de niño)", inf.colegio_no_reconocido)
    c3.metric("ARI de padres (hijo 1 / hijo 2)",
              f"{inf.cobertura_ari.get('hijo 1', 0)} / {inf.cobertura_ari.get('hijo 2', 0)}")
    st.markdown("**% de ítems faltantes por bloque**")
    st.dataframe(pd.DataFrame(sorted(inf.faltantes_por_bloque.items()),
                              columns=["Bloque", "% faltante"]),
                 hide_index=True, width="stretch")
    if inf.etiquetas_no_mapeadas:
        st.warning("Respuestas con etiquetas que el catálogo no reconoce (quedan como "
                   "faltantes): " + ", ".join(f"{k} ({n})" for k, n in
                                             sorted(inf.etiquetas_no_mapeadas.items())))
    else:
        st.success("Todas las etiquetas del formulario se mapearon a número.")
    for aviso in list(getattr(a, "avisos", []) or []) + list(inf.avisos or []):
        st.warning(aviso)


def _tab_exportar(ac) -> None:
    if not exportable(ac):
        st.caption(SOLO_TODAS)
        return
    st.caption("Todo es agregado: ni filas, ni identificadores, ni conteos de casos.")
    contenidos = archivos_paquete(ac)
    columnas = st.columns(2)
    for i, nombre in enumerate(ARCHIVOS_PAQUETE):
        with columnas[i % 2]:
            contenido = contenidos.get(nombre, "")
            st.download_button(f"⬇️ {nombre}", data=contenido.encode("utf-8-sig"),
                               file_name=nombre,
                               mime="text/csv" if nombre.endswith(".csv") else "text/markdown",
                               disabled=not contenido, width="stretch",
                               key=f"cuid_dl_{nombre}")
    st.download_button("📦 Descargar el paquete completo (ZIP)", data=paquete_zip(ac),
                       file_name=f"cuidadores360_{ac.ola or 'todas'}_"
                                 f"{_dt.date.today().isoformat()}.zip",
                       mime="application/zip", type="primary", width="stretch",
                       key="cuid_dl_zip")


def render_investigador(ac) -> None:
    st.title("Cuidadores 360 · vista investigador")
    marco = st.radio("Marco", list(cat.NOMBRES_MARCO), horizontal=True,
                     format_func=lambda m: cat.NOMBRES_MARCO[m], key="cuid_marco")
    a = ac.marcos[marco]
    if ac.ola:
        st.caption(f"Ola {ac.ola}. {cat.AVISO_OLA} {SOLO_TOTAL_OLA}")
    tabs = st.tabs(PESTANAS)
    with tabs[0]:
        _tab_muestra(ac, a, marco)
    with tabs[1]:
        _tab_tabla1(ac, marco)
    with tabs[2]:
        _tab_cortes(a, marco)
    with tabs[3]:
        _tab_correlaciones(a)
    with tabs[4]:
        _tab_por_grupo(ac, a, marco)
    with tabs[5]:
        _tab_senales(ac)
    with tabs[6]:
        _tab_items(ac)
    with tabs[7]:
        _tab_calidad(ac, a)
    with tabs[8]:
        _tab_exportar(ac)
