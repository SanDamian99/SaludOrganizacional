"""
Pruebas del modo de despliegue.

El modo «comunidad» es lo que se expone en público. Lo que se prueba aquí es que
un visitante público no pueda llegar a la vista de investigación, al cargador de
archivos ni al panel técnico, y que no dependa de que nadie haga clic donde no
debe.
"""
import importlib
import os
import re

import pytest

from src.core import modo as modo_app

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def con_modo(monkeypatch):
    def poner(valor):
        if valor is None:
            monkeypatch.delenv("OBS360_MODO", raising=False)
        else:
            monkeypatch.setenv("OBS360_MODO", valor)
        return importlib.reload(modo_app)
    yield poner
    monkeypatch.delenv("OBS360_MODO", raising=False)
    importlib.reload(modo_app)


def test_por_defecto_es_completo(con_modo):
    m = con_modo(None)
    assert m.modo() == m.COMPLETO
    assert m.paginas_permitidas() is None
    assert m.audiencias_permitidas() is None
    assert not m.es_publico()


def test_modo_comunidad_solo_deja_la_vista_comunidad(con_modo):
    m = con_modo("comunidad")
    assert m.es_publico()
    assert m.paginas_permitidas() == ["Estudiantes 360"]
    assert m.audiencias_permitidas() == ["comunidad"]
    assert m.audiencia_por_defecto() == "comunidad"


def test_el_investigador_ve_todo_pero_abre_en_su_vista(con_modo):
    """Un investigador es, a efectos de la aplicación, un administrador.

    Va a enseñar la plataforma a otros, así que necesita recorrerla entera; lo
    que cambia es con qué vista abre.
    """
    m = con_modo("investigador")
    assert not m.es_publico()
    assert m.paginas_permitidas() is None          # todas
    assert m.audiencias_permitidas() is None       # las dos
    assert m.audiencia_por_defecto() == "investigador"


def test_solo_el_modo_comunidad_restringe(con_modo):
    for valor in ("completo", "investigador"):
        m = con_modo(valor)
        assert m.paginas_permitidas() is None, valor
        assert m.audiencias_permitidas() is None, valor
    m = con_modo("comunidad")
    assert m.paginas_permitidas() == ["Estudiantes 360"]


@pytest.mark.parametrize("valor", ["", "  ", "publico", "COMPLETO ", "cualquier-cosa"])
def test_un_valor_desconocido_cae_en_el_modo_mas_restrictivo(con_modo, valor):
    """Una errata en la configuración no puede abrir la vista de investigación."""
    m = con_modo(valor)
    if valor.strip().lower() in ("", ):
        assert m.modo() == m.COMPLETO          # sin configurar = uso local
    elif valor.strip().lower() == "completo":
        assert m.modo() == m.COMPLETO
    else:
        assert m.modo() == m.COMUNIDAD
        assert m.audiencias_permitidas() == ["comunidad"]
        assert m.paginas_permitidas() == ["Estudiantes 360"]


def test_el_punto_de_entrada_corta_antes_de_importar_lo_demas():
    """En modo público, main.py no debe llegar a importar los módulos internos.

    Se comprueba sobre el texto porque es una garantía estructural: el `st.stop()`
    tiene que estar antes de los imports del cargador, el chat y los informes.
    """
    fuente = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    corte = fuente.index("st.stop()")
    antes, despues = fuente[:corte], fuente[corte:]

    # lo único que se importa antes del corte es el módulo de estudiantes
    assert "from src.ui.estudiantes import render_estudiantes" in antes
    # y estos quedan después, es decir, fuera del alcance del despliegue público
    for modulo in ("src.ui.reports", "src.data.loader", "src.ui.diagnostics",
                   "src.ui.chat", "src.ui.upload", "src.ui.dashboard"):
        assert modulo not in antes, f"{modulo} se importa antes del corte público"
        assert modulo in despues, f"{modulo} ya no aparece en main.py"


def test_el_panel_tecnico_queda_despues_del_corte():
    fuente = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    corte = fuente.index("st.stop()")
    assert fuente.index("debug") > corte


def test_la_navegacion_se_filtra_por_modo():
    fuente = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    assert "paginas_permitidas()" in fuente
    # el radio ya no recibe la lista completa escrita a mano
    assert not re.search(r'st\.radio\("Ir a:", \[\s*"Dashboard"', fuente)


def test_el_enlace_por_colegio_ignora_codigos_invalidos():
    """`?colegio=` no debe servir para sondear la base."""
    from src.estudiantes import catalog as cat
    from src.ui import estudiantes as disp
    import pandas as pd

    class Falso:
        def __init__(self, conteo):
            self.datos = pd.DataFrame({"Colegio": sum(
                ([c] * n for c, n in conteo.items()), [])})

    analisis = {"secundaria": Falso({"LauV": 50, "CdP": 3})}

    class ParamsFalsos(dict):
        def get(self, k, d=None):
            return super().get(k, d)

    import streamlit as st
    original = st.query_params
    try:
        st.query_params = ParamsFalsos({"colegio": "LauV"})
        assert disp.colegio_de_la_url(analisis) == "LauV"
        # un colegio por debajo del mínimo no se acepta
        st.query_params = ParamsFalsos({"colegio": "CdP"})
        assert disp.colegio_de_la_url(analisis) is None
        # un código inventado tampoco
        st.query_params = ParamsFalsos({"colegio": "NoExiste"})
        assert disp.colegio_de_la_url(analisis) is None
        st.query_params = ParamsFalsos({})
        assert disp.colegio_de_la_url(analisis) is None
    finally:
        st.query_params = original
    assert cat.MIN_GROUP_N == 10


def test_el_error_de_clave_invalida_se_explica_sin_jerga():
    """Un despliegue con la clave mal puesta debe decir qué revisar.

    Ocurrió en el primer despliegue: la app volcaba el JSON crudo de Supabase,
    que además menciona `service_role` y confunde sobre qué clave poner.
    """
    fuente = open(os.path.join(RAIZ, "src", "ui", "estudiantes.py"),
                  encoding="utf-8").read()
    assert "Invalid API key" in fuente
    assert "Settings → Secrets" in fuente
    # y advierte de no pegar la clave de escritura
    i = fuente.index("Invalid API key")
    bloque = fuente[i:i + 1400]
    assert "service_role" in bloque and "anon" in bloque


def test_no_queda_el_parametro_de_ancho_obsoleto():
    """`use_container_width` se elimina de Streamlit y llenaba el registro.

    Todas las llamadas usaban `True`, así que el reemplazo es `width="stretch"`.
    """
    import pathlib
    raiz = pathlib.Path(RAIZ)
    culpables = []
    for f in list((raiz / "src").rglob("*.py")) + [raiz / "main.py"]:
        if "use_container_width" in f.read_text(encoding="utf-8"):
            culpables.append(str(f.relative_to(raiz)))
    assert not culpables, f"usan un parámetro obsoleto: {culpables}"
