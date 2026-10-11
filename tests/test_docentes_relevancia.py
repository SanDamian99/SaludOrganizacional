"""
Página Docentes tras la auditoría de relevancia (10-oct-2026).

Salen: los botones «✨ Interpretar … con IA», el KPI «Salud mental en atención»
y los mensajes «Requieren atención / Favorables» (salen del índice relativo
0-100, que no es un punto de corte), el tema «📊 Otros indicadores» y la
pestaña «Correlaciones». Se quedan el Chat y las recomendaciones del PDF.
"""
import json
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

from tests import docentes_sinteticos as sint

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def _pagina():
    from src.ui.dashboard import render_dashboard
    render_dashboard()


@pytest.fixture
def app():
    at = AppTest.from_function(_pagina, default_timeout=60)
    at.session_state["df"] = sint.docentes()
    return at.run()


def _textos(at) -> str:
    partes = [m.value for m in at.markdown] + [m.label for m in at.metric]
    partes += [e.value for e in (*at.error, *at.success, *at.info, *at.warning)]
    partes += [b.label for b in at.button] + [t.label for t in at.tabs]
    return "\n".join(str(p) for p in partes)


def test_la_pagina_carga_sin_excepciones(app):
    assert not app.exception
    assert "Explorar un indicador" in _textos(app)


def test_no_hay_botones_de_interpretar_con_ia(app):
    assert not [b.label for b in app.button if "Interpretar" in b.label]
    codigo = (RAIZ / "src" / "ui" / "dashboard.py").read_text(encoding="utf-8")
    assert "Interpretar" not in codigo
    assert "_ai_interpret_mental_health" not in codigo
    assert "get_cached_client" not in codigo


def test_no_hay_kpi_ni_mensajes_del_indice_relativo(app):
    texto = _textos(app)
    assert "Salud mental en atención" not in texto
    assert "Requieren atención" not in texto
    assert "Favorables:" not in texto
    assert "Sin indicadores de salud mental en zona de atención" not in texto
    assert [m.label for m in app.metric][:2] == ["👥 Docentes", "📐 Indicadores"]


def test_no_se_muestra_el_tema_otros_indicadores(app):
    titulos = [m.value for m in app.markdown if m.value.startswith("#####")]
    assert "##### 🧠 Salud mental y estrés" in titulos
    assert not [t for t in titulos if "Otros indicadores" in t]


def test_no_hay_pestana_de_correlaciones(app):
    etiquetas = [t.label for t in app.tabs]
    # Las del perfil («Sociodemográficas», «Laborales») van anidadas.
    assert etiquetas[:2] == ["🧠 Salud mental e indicadores", "👥 Perfil"]
    assert not [e for e in etiquetas if "Correlaciones" in e]
    assert "Correlación entre indicadores" not in _textos(app)


# ══ Fase 1 (10-oct-2026): puntuación anclada en la vista ═══════════════════
def test_las_barras_son_de_la_escala_teorica_y_no_de_la_muestra(app):
    texto = _textos(app)
    assert "posición relativa" not in texto.lower()
    assert "cortes publicados" in texto and "No es un diagnóstico individual" in texto
    assert "GUIA_DATASETS" not in texto
    fig = json.loads(app.get("plotly_chart")[0].proto.spec)
    titulo = fig["layout"]["xaxis"]["title"]["text"]
    assert "escala teórica" in titulo and "muestra" not in titulo
    assert all(0 <= v <= 100 for v in fig["data"][0]["x"])
    assert "#C0392B" not in str(fig["data"][0]["marker"]["color"])   # nunca rojo


def test_explorar_usa_la_puntuacion_nueva(app):
    etiquetas = [m.label for m in app.metric]
    assert "Escala teórica" in etiquetas and "IC 95 %" in etiquetas
    assert "Rango observado" not in etiquetas
    # El selector ofrece las dimensiones del catálogo, no los *_T del archivo.
    opciones = app.selectbox[0].options
    assert "Estrés percibido (PSS-10)" in opciones and "Exigencias psicológicas (ISTAS21)" in opciones
    assert not [o for o in opciones if o.endswith("_T")]
    assert "Zona" in app.dataframe[0].value.columns


def test_la_zona_no_cambia_al_filtrar():
    """Misma media, misma zona, se mire el municipio o un colegio (semáforo anclado).

    Con el índice relativo, el subconjunto con más estrés salía «Favorable».
    """
    from src.ui import dashboard as d
    df = sint.docentes()
    pss = [f"PSS{i}" for i in range(1, 11)]
    # Municipio: PSS medio 10 (bajo), salvo «Grande A», donde todos tienen 30 (alto).
    df[pss] = 1.0
    df.loc[df[sint.COL_COLEGIO] == "Grande A", pss] = 3.0
    todo, _ = d._resumen_docentes.__wrapped__(df)
    parte, _ = d._resumen_docentes.__wrapped__(df[df[sint.COL_COLEGIO] == "Grande A"])
    assert parte["PSS"]["mean"] == 30 and parte["PSS"]["level"] == "Zona a vigilar"
    assert parte["PSS"]["color"] == "#D9822B"
    assert todo["PSS"]["mean"] < 30 and todo["PSS"]["level"] != "Zona a vigilar"
    # Y un subconjunto con la misma media que el total tiene su misma zona.
    mismo, _ = d._resumen_docentes.__wrapped__(df[df[sint.COL_COLEGIO] == "Grande B"])
    assert mismo["PSS"]["mean"] == 10 and mismo["PSS"]["level"] == "Zona favorable"
    assert parte["PSS"]["n"] == 30 and todo["PSS"]["n"] == len(df)


def test_universo_sedes_fundidas_y_secretaria_fuera():
    """El KPI «Docentes» y el filtro de colegio parten del universo publicable."""
    df = sint.docentes().rename(columns={sint.COL_COLEGIO: "Colegio"})
    df.loc[df.index[:4], "Colegio"] = "Fusca · sede El Cerro"
    df.loc[df.index[4:9], "Colegio"] = "Fusca"
    df.loc[df.index[9], "Colegio"] = "Secretaría de Educación"
    at = AppTest.from_function(_pagina, default_timeout=60)
    at.session_state["df"] = df
    at.run()
    assert not at.exception
    assert [m.value for m in at.metric if m.label == "👥 Docentes"] == [str(len(df) - 1)]
    opciones = at.multiselect(key="filtro_Colegio").options
    assert "Fusca" in opciones and "Fusca · sede El Cerro" not in opciones
    assert "Secretaría de Educación" not in opciones
    at.selectbox(key="doc_comparar_por").set_value("Colegio").run()
    assert not at.exception
    pies = " ".join(c.value for c in at.caption)
    # Fusca queda con 9 (fundida con su sede, 4 + 5): va en «otros» (9 + 5 = 14), sin cifra propia.
    assert "Fusca=" not in pies and "sin cifra: Fusca" in pies and "menos de 10): 14" in pies
    assert "Welch" in " ".join(c.value for c in at.caption)
    assert any("Diferencia con el resto [IC 95 %]" in d.value.columns for d in at.dataframe)
