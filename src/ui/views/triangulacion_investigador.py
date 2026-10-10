"""
Vista investigador de la Triangulación 360 — Observatorio 360 (fase 5).

Se lee en capas (spec §6): primero el resumen (perfil por colegio, patrones
entre actores, dónde hay tensión e hipótesis, con los hallazgos fijos de
`hallazgos_catalogo` que la corrida sustenta), luego las tablas de cada capa,
luego la metodología y la descarga.

No calcula: consume un `pipeline.Triangulacion` (máquina que procesa) o un
`lectura.TriangulacionPublicada` (despliegue del equipo), que solo tienen
agregados; el publicado ya trae legibles las personas por colegio
(`conteos_tabla`) y la calidad del enlace (`calidad`). Los conteos por debajo de
10 se muestran como «<10» y ninguna tabla lleva identificadores, seudónimos ni
díadas.
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from src.triangulacion import catalogo as cat
from src.triangulacion import enlace as en
from src.triangulacion import exportar as ex
from src.triangulacion import hallazgos as hz
from src.triangulacion import hallazgos_catalogo as hc

PESTANAS = ["Resumen", "Por colegio", "Por grado", "Enlace de díadas", "Acuerdo SDQ",
            "Malestar no visto", "Apoyo familiar", "Asociaciones", "Metodología", "Exportar"]


def _df(t: pd.DataFrame | None, columnas: list | None = None) -> None:
    t = ex._limpia(t)
    if t.empty:
        st.caption("Sin datos para mostrar.")
        return
    if columnas:
        t = t[[c for c in columnas if c in t.columns]]
    st.dataframe(t, hide_index=True, width="stretch")


def hallazgos(clasificacion: pd.DataFrame, tipo: str) -> pd.DataFrame:
    if clasificacion is None or clasificacion.empty:
        return pd.DataFrame()
    t = clasificacion[clasificacion["clasificacion"] == tipo]
    return t[["agrupacion", "grupo", "par", "d_a", "ic_a", "d_b", "ic_b"]].reset_index(drop=True)


EN_OTROS = "incluido en «otros»"


def conteos_actores(t) -> pd.DataFrame:
    """Personas por colegio y actor sin que ningún colegio pequeño salga restando.

    Por actor, los colegios con menos de 10 (y OTRO/SIN_DATO) van juntos en
    «otros colegios»; si esa fila quedara con 1 a 9, se le suma el colegio
    publicado más pequeño (`enlace.reparto`). Así el total exacto del actor
    (metodología) menos lo mostrado nunca deja de 1 a 9. Una corrida publicada
    trae esta tabla ya armada (los conteos exactos no se publican).
    """
    pre = getattr(t, "conteos_tabla", None)
    if isinstance(pre, pd.DataFrame):
        return pre
    conteos = t.capa1.conteos or {}
    actores = ((cat.ESTUDIANTE, "Estudiantes"), (cat.CUIDADOR, "Cuidadores"),
               (cat.DOCENTE, "Docentes"))
    repartos = {m: en.reparto(conteos.get(m, {})) for m, _ in actores}
    colegios = sorted({c for g, _, _ in repartos.values() for c in g}
                      | {a for _, _, a in repartos.values() if a})
    filas = []
    for c in colegios:
        fila = dict(Colegio=c)
        for m, nombre in actores:
            grandes, _, _ = repartos[m]
            fila[nombre] = (str(grandes[c]) if c in grandes
                            else EN_OTROS if c in conteos.get(m, {}) else "—")
        fila["En la capa 1"] = "sí" if c in t.capa1.colegios else "no"
        filas.append(fila)
    if any(n for _, n, _ in repartos.values()):
        fila = dict(Colegio=en.OTROS_COLEGIOS)
        for m, nombre in actores:
            n_otros = repartos[m][1]
            fila[nombre] = en.conteo_legible(n_otros) if n_otros else "—"
        fila["En la capa 1"] = "no"
        filas.append(fila)
    return pd.DataFrame(filas)


def _hallazgo(v: hz.Visible) -> None:
    h = v.hallazgo
    donde = f" · {v.grupo}" if v.grupo else ""
    st.markdown(f"**{h.numero}. {h.titulo}{donde}**  \n"
                f"<small>Relevante para: {', '.join(h.actores)} · robustez: {h.robustez}</small>",
                unsafe_allow_html=True)
    st.markdown(h.texto)
    st.caption(f"Cifra que lo sustenta ({h.sustento}): {v.cifra}")


def _bloque_hallazgos(visibles: list, bloque: str, clasificacion: pd.DataFrame,
                      tipo: str, titulo_pares: str) -> None:
    lista = hz.por_bloque(visibles, bloque)
    if not lista:
        st.caption(hc.AVISO_SIN_HALLAZGOS)
    for v in lista:
        _hallazgo(v)
    pares = hallazgos(clasificacion, tipo)
    with st.expander(f"{titulo_pares} ({len(pares)})"):
        st.caption(cat.AVISO_CLASIFICACION)
        _df(pares)


def _tab_resumen(t) -> None:
    """Cuatro bloques (decisión del usuario del 10 oct 2026): perfil por colegio,
    patrones entre actores, dónde hay tensión e hipótesis. Los textos son fijos
    (`hallazgos_catalogo`) y cada hallazgo sale solo si la corrida lo sustenta."""
    st.info(cat.AVISO_ECOLOGICO.format(n=t.n_colegios))
    st.warning(hc.ESTADO_TEXTOS + " " + cat.AVISO_TEXTOS)
    visibles = hz.evaluar(t)
    todo = pd.concat([t.capa1.clasificacion, t.capa1.clasificacion_grado], ignore_index=True)

    st.subheader(hc.TITULO_PERFIL)
    c1, c2, c3 = st.columns(3)
    c1.metric("Colegios en la capa 1", t.n_colegios)
    c2.metric("Díadas niño–cuidador", en.conteo_legible(t.diadas.n))
    c3.metric("Familias en las díadas", en.conteo_legible(t.diadas.familias))
    st.caption(hc.AVISO_PERFIL)
    _df(hz.perfil_colegios(t))

    st.subheader(hc.TITULO_PATRONES)
    st.caption(hc.AVISO_HALLAZGOS)
    _bloque_hallazgos(visibles, hc.PATRON, todo, cat.COINCIDENCIA,
                      "Pares de la capa 1 en coincidencia")

    st.subheader(hc.TITULO_TENSION)
    _bloque_hallazgos(visibles, hc.TENSION, todo, cat.TENSION, "Pares de la capa 1 en tensión")

    st.subheader(hc.TITULO_HIPOTESIS)
    st.caption(hc.AVISO_HIPOTESIS)
    lista = hz.hipotesis_de(visibles)
    if not lista:
        st.caption(hc.AVISO_SIN_HALLAZGOS)
    for h in lista:
        with st.expander(f"{h.id} · {h.texto}"):
            st.markdown(f"**Patrón que la sugiere.** {h.patron}")
            st.markdown(f"**Explicaciones alternativas.** {h.alternativas}")
            st.markdown(f"**Cómo ponerla a prueba.** {h.prueba}")
            st.markdown(f"**Confianza.** {h.confianza}")


def _tab_colegio(t) -> None:
    st.caption(cat.AVISO_RESTO)
    st.caption(cat.AVISO_AJUSTE_GRADO)
    st.markdown("**Personas por colegio y actor**")
    _df(conteos_actores(t))
    st.markdown("**Clasificación de los pares**")
    _df(t.capa1.clasificacion)
    st.caption(cat.AVISO_COOCURRENCIA)
    st.markdown("**Cada actor frente al resto del municipio**")
    _df(t.capa1.diferencias)
    for colegio in t.capa1.colegios:
        with st.expander(f"Figura · {colegio}"):
            st.pyplot(ex.figura_capa1(t, colegio))
    st.markdown("**Cifras municipales**")
    st.caption(cat.AVISO_MUNICIPAL)
    _df(getattr(t.capa1, "municipal", None))


def _tab_grado(t) -> None:
    st.caption(cat.AVISO_GRADO)
    _df(t.capa1.clasificacion_grado)
    _df(t.capa1.por_grado)


def calidad(t) -> pd.DataFrame:
    """La calidad del enlace: la publicada si viene en `t`, si no, del informe local."""
    pre = getattr(t, "calidad", None)
    if isinstance(pre, pd.DataFrame):
        return pre
    return en.tabla_calidad(getattr(t, "enlace", None) or {})


def _tab_enlace(t) -> None:
    st.caption(cat.AVISO_ENLACE)
    _df(calidad(t))


def _tab_acuerdo(t) -> None:
    st.caption(cat.AVISO_DIADAS)
    st.caption(cat.AVISO_SDQ)
    _df(t.diadas.acuerdo)
    st.caption(cat.AVISO_BLAND_ALTMAN)
    ba = t.diadas.bland_altman
    if not ba.empty:
        sub = st.selectbox("Subescala", list(ba["subescala"].unique()), key="tri_ba")
        st.pyplot(ex.figura_bland_altman(t, sub))
        _df(ba[ba["subescala"] == sub])
    st.markdown("**Sensibilidad: solo díadas concordantes en sexo, edad y grado**")
    st.caption(cat.AVISO_SENSIBILIDAD_CONCORDANCIA)
    _df(t.diadas.acuerdo_concordantes)


def _tab_no_visto(t) -> None:
    st.caption("El niño en banda alta o muy alta de su autoinforme, o con la señal de "
               "malestar, y su cuidador lo ubica en «cercano al promedio». No es un "
               "diagnóstico: indica dónde conversar primero con las familias.")
    _df(t.diadas.no_visto)


def _tab_apoyo(t) -> None:
    st.warning(cat.AVISO_MSPSS)
    _df(t.diadas.apoyo)


def _tab_asociaciones(t) -> None:
    st.caption(cat.AVISO_ASOCIACIONES)
    st.caption(cat.AVISO_SENSIBILIDAD_CONCORDANCIA)
    _df(t.diadas.asociaciones)
    st.markdown("**El informante: el malestar del cuidador y lo que reporta cada uno**")
    st.caption(cat.AVISO_INFORMANTE)
    _df(getattr(t.diadas, "informante", None))


def _tab_metodologia(t) -> None:
    st.markdown(ex.metodologia_md(t))


def _tab_exportar(t) -> None:
    st.caption("Todo es agregado: ni filas, ni seudónimos, ni díadas.")
    st.download_button("📦 Descargar el paquete de la triangulación (ZIP)",
                       data=ex.paquete_zip(t),
                       file_name=f"triangulacion360_{_dt.date.today().isoformat()}.zip",
                       mime="application/zip", type="primary", width="stretch",
                       key="tri_dl_zip")


def render_investigador(t, titulo: str | None = None) -> None:
    """Las pestañas de la triangulación. La página pública pasa su propio título
    (las mismas pestañas: decisión del usuario del 10 oct 2026)."""
    st.title(f"🔺 {titulo or cat.TITULO}")
    tabs = st.tabs(PESTANAS)
    for tab, fn in zip(tabs, (_tab_resumen, _tab_colegio, _tab_grado, _tab_enlace,
                              _tab_acuerdo, _tab_no_visto, _tab_apoyo, _tab_asociaciones,
                              _tab_metodologia, _tab_exportar)):
        with tab:
            fn(t)
