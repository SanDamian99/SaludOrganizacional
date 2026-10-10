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


def test_la_zona_no_cambia_al_filtrar(app):
    """Misma media, misma zona, se mire el municipio o un colegio (semáforo anclado)."""
    from src.ui import dashboard as d
    df = sint.docentes()
    todo, _ = d._resumen_docentes.__wrapped__(df)
    parte, _ = d._resumen_docentes.__wrapped__(df[df[sint.COL_COLEGIO] == "Grande A"])
    for clave in parte:
        assert parte[clave]["min"] == todo[clave]["min"] and parte[clave]["max"] == todo[clave]["max"]
    assert todo["PSS"]["n"] == len(df) and parte["PSS"]["n"] == 30
