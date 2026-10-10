"""
Página Docentes tras la auditoría de relevancia (10-oct-2026).

Salen: los botones «✨ Interpretar … con IA», el KPI «Salud mental en atención»
y los mensajes «Requieren atención / Favorables» (salen del índice relativo
0-100, que no es un punto de corte), el tema «📊 Otros indicadores» y la
pestaña «Correlaciones». Se quedan el Chat y las recomendaciones del PDF.
"""
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
