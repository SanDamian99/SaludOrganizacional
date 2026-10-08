"""
El colegio sobrevive a Estudiantes → Cuidadores → Estudiantes en el despliegue público.

En el modo comunidad `main.py` termina con `st.stop()`. Streamlit trata esa
parada como prematura y no borra el estado de los widgets que no se dibujaron:
al volver, la clave del selector de Estudiantes seguía en la sesión con su valor
viejo, `sembrar` no la tocaba y el navegador, que no recibe ese valor, dibujaba
el selector en «Todos». Este arnés reproduce la misma estructura (dos páginas y
`st.stop()` al final) con los selectores reales de las dos vistas.
"""
import pytest
from streamlit.runtime.state.session_state import SessionState
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def parada_prematura(monkeypatch):
    """Como en el navegador tras `st.stop()`: no se limpian los widgets no dibujados.

    `ScriptRunner._on_script_finished` solo llama a
    `SessionState.on_script_finished` (que borra el estado de los widgets que
    no se dibujaron) si la ejecución no se paró antes de tiempo, y `st.stop()`
    cuenta como parada prematura. El arnés de pruebas no siempre lo reproduce,
    así que aquí se fuerza.
    """
    monkeypatch.setattr(SessionState, "on_script_finished",
                        lambda self, ids: self._reset_triggers())


def _app():
    from types import SimpleNamespace
    import streamlit as st
    from src.ui import estado
    from src.ui.views import cuidadores_comunidad as vcu
    from src.ui.views import estudiantes_comunidad as ves
    from tests import cuidadores_comunidad_datos as datos

    @st.cache_resource
    def ac():
        return datos.preparado()

    colegios = ["LauV", "JJC", "SJMEB"]
    est = SimpleNamespace(subgrupos={"Colegio": {c: {} for c in colegios}, "Grado": {}},
                          muestra={}, datos=None, base=None)
    if st.query_params.get("colegio"):
        estado.aplicar_colegio_de_url(st.query_params.get("colegio"))
    pagina = st.sidebar.radio("Ir a:", ["Estudiantes", "Cuidadores"], key="nav_pagina")
    if pagina == "Estudiantes":
        ves._selector_grupo(est, "Colegio", "Colegio", nivel="secundaria")
    else:
        vcu._selector(ac(), "Colegio")
    st.stop()


def _colegio(at):
    caja = at.sidebar.selectbox[0]
    # Lo que dibuja el navegador: el valor que el servidor manda (`set_value`)
    # o, si no manda ninguno, la opción por defecto.
    assert caja.proto.set_value, f"{caja.key}: el servidor no envía el valor al navegador"
    return caja.value


def _ir(at, pagina):
    at.sidebar.radio(key="nav_pagina").set_value(pagina).run()
    assert not at.exception


def test_el_colegio_de_la_url_sobrevive_la_ida_y_vuelta():
    at = AppTest.from_function(_app, default_timeout=120)
    at.query_params["colegio"] = "LauV"
    at.run()
    assert _colegio(at) == "LauV"
    _ir(at, "Cuidadores")
    assert _colegio(at) == "LauV"
    _ir(at, "Estudiantes")
    assert _colegio(at) == "LauV"


def test_el_colegio_elegido_en_cuidadores_llega_a_estudiantes():
    at = AppTest.from_function(_app, default_timeout=120).run()
    at.sidebar.selectbox[0].set_value("LauV").run()
    _ir(at, "Cuidadores")
    assert _colegio(at) == "LauV"
    at.sidebar.selectbox[0].set_value("JJC").run()
    _ir(at, "Estudiantes")
    assert _colegio(at) == "JJC"
    _ir(at, "Cuidadores")
    assert _colegio(at) == "JJC"


def test_todos_elegido_a_proposito_se_conserva():
    from src.ui import estado
    at = AppTest.from_function(_app, default_timeout=120).run()
    at.sidebar.selectbox[0].set_value("LauV").run()
    at.sidebar.selectbox[0].set_value("Todos").run()
    assert at.session_state[estado.COLEGIO] == "Todos"
    _ir(at, "Cuidadores")
    _ir(at, "Estudiantes")
    assert at.sidebar.selectbox[0].value == "Todos"
