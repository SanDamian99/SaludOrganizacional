"""
Pruebas del modo de despliegue.

El modo «comunidad» es lo que se expone en público. Lo que se prueba aquí es que
un visitante público no pueda llegar a la vista de investigación, al cargador de
archivos ni al panel técnico, y que no dependa de que nadie haga clic donde no
debe.
"""
import importlib
import os

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
    assert m.paginas_permitidas() == ["Estudiantes 360", "Triangulación 360", "Dónde pedir ayuda"]
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
        assert m.paginas_permitidas() == ["Estudiantes 360", "Triangulación 360", "Dónde pedir ayuda"]


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
        # la corrida publicada no trae filas: el enlace se resuelve con `muestra`
        publicado = Falso({})
        publicado.muestra = {"colegio": {"LauV": 50, "CdP": "<10"}}
        st.query_params = ParamsFalsos({"colegio": "lauv"})
        assert disp.colegio_de_la_url({"secundaria": publicado}) == "LauV"
        st.query_params = ParamsFalsos({"colegio": "CdP"})
        assert disp.colegio_de_la_url({"secundaria": publicado}) is None
    finally:
        st.query_params = original
    assert cat.MIN_GROUP_N == 10


def test_modo_y_navegacion_coinciden(con_modo):
    from src.core import navegacion as nav
    for valor in (None, "investigador", "comunidad"):
        m = con_modo(valor)
        assert m.pagina_por_defecto() == nav.pagina_inicial(m.modo())
    m = con_modo("comunidad")
    assert m.paginas_permitidas() == nav.menu(m.COMUNIDAD)


@pytest.mark.parametrize("modo_env", ["comunidad", "completo"])
def test_main_arranca_con_un_modo_rancio_de_la_version_anterior(monkeypatch, modo_env):
    """Guardia real: `src.core.modo` en memoria solo tiene la API vieja.

    Es lo que pasa tras un despliegue sin reinicio: main.py nuevo, módulo viejo.
    """
    import sys
    from types import ModuleType
    from streamlit.testing.v1 import AppTest
    import src.core

    rancio = ModuleType("src.core.modo")
    rancio.COMPLETO, rancio.COMUNIDAD, rancio.INVESTIGADOR = (
        "completo", "comunidad", "investigador")
    rancio.VALIDOS = (rancio.COMPLETO, rancio.COMUNIDAD, rancio.INVESTIGADOR)
    rancio.modo = lambda: modo_env
    rancio.es_publico = lambda: modo_env == "comunidad"
    rancio.audiencias_permitidas = (
        lambda: ["comunidad"] if modo_env == "comunidad" else None)
    rancio.audiencia_por_defecto = (
        lambda: "comunidad" if modo_env == "comunidad" else "investigador")
    monkeypatch.setitem(sys.modules, "src.core.modo", rancio)
    monkeypatch.setattr(src.core, "modo", rancio, raising=False)
    # que el despachador de estudiantes se importe de nuevo y vea el módulo rancio
    monkeypatch.delitem(sys.modules, "src.ui.estudiantes", raising=False)
    monkeypatch.setenv("OBS360_MODO", modo_env)
    monkeypatch.setenv("OBS360_DATOS_DIR", "/ruta/que/no/existe")

    at = AppTest.from_file(os.path.join(RAIZ, "main.py"), default_timeout=90).run()
    assert not at.exception
    assert not hasattr(sys.modules["src.core.modo"], "pagina_por_defecto")
