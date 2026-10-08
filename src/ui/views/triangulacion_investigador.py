"""
Vista investigador de la Triangulación 360 — Observatorio 360 (fase 5).

Se lee en capas (spec §6): primero el resumen («dónde coinciden» y «dónde hay
tensión»), luego las tablas de cada capa, luego la metodología y la descarga.

No calcula: consume un `pipeline.Triangulacion`, que solo tiene agregados. Los
conteos por debajo de 10 se muestran como «<10» y ninguna tabla lleva
identificadores, seudónimos ni díadas.
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from src.triangulacion import catalogo as cat
from src.triangulacion import enlace as en
from src.triangulacion import exportar as ex

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
    (metodología) menos lo mostrado nunca deja de 1 a 9.
    """
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


def _tab_resumen(t) -> None:
    st.info(cat.AVISO_ECOLOGICO.format(n=t.n_colegios))
    c1, c2, c3 = st.columns(3)
    c1.metric("Colegios en la capa 1", t.n_colegios)
    c2.metric("Díadas niño–cuidador", en.conteo_legible(t.diadas.n))
    c3.metric("Familias en las díadas", en.conteo_legible(t.diadas.familias))
    todo = pd.concat([t.capa1.clasificacion, t.capa1.clasificacion_grado], ignore_index=True)
    st.subheader("Dónde coinciden")
    _df(hallazgos(todo, cat.COINCIDENCIA))
    st.subheader("Dónde hay tensión")
    _df(hallazgos(todo, cat.TENSION))
    st.caption(cat.AVISO_CLASIFICACION)
    st.caption(cat.AVISO_TEXTOS)


def _tab_colegio(t) -> None:
    st.caption(cat.AVISO_RESTO)
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


def _tab_grado(t) -> None:
    st.caption(cat.AVISO_GRADO)
    _df(t.capa1.clasificacion_grado)
    _df(t.capa1.por_grado)


def _tab_enlace(t) -> None:
    st.caption(cat.AVISO_ENLACE)
    _df(en.tabla_calidad(t.enlace))


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


def _tab_metodologia(t) -> None:
    st.markdown(ex.metodologia_md(t))


def _tab_exportar(t) -> None:
    st.caption("Todo es agregado: ni filas, ni seudónimos, ni díadas. Nada sube a Supabase.")
    st.download_button("📦 Descargar el paquete de la triangulación (ZIP)",
                       data=ex.paquete_zip(t),
                       file_name=f"triangulacion360_{_dt.date.today().isoformat()}.zip",
                       mime="application/zip", type="primary", width="stretch",
                       key="tri_dl_zip")


def render_investigador(t) -> None:
    st.title(f"🔺 {cat.TITULO}")
    tabs = st.tabs(PESTANAS)
    for tab, fn in zip(tabs, (_tab_resumen, _tab_colegio, _tab_grado, _tab_enlace,
                              _tab_acuerdo, _tab_no_visto, _tab_apoyo, _tab_asociaciones,
                              _tab_metodologia, _tab_exportar)):
        with tab:
            fn(t)
