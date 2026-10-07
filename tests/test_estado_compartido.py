"""
El colegio y el rol elegidos sobreviven al cambio de página.
"""
from streamlit.testing.v1 import AppTest


def _app():
    import streamlit as st
    from src.ui import estado
    pagina = st.radio("pagina", ["A", "B"], key="pagina")
    opciones = ["Todos", "LauV", "CND"] if pagina == "A" else ["Todos", "CND"]
    clave = "a_colegio" if pagina == "A" else "b_colegio"
    estado.sembrar(clave, estado.COLEGIO, opciones)
    valor = st.selectbox("colegio", opciones, key=clave)
    estado.guardar(estado.COLEGIO, valor)


def test_el_colegio_sobrevive_al_ir_y_volver():
    at = AppTest.from_function(_app).run()
    at.selectbox(key="a_colegio").set_value("CND").run()
    at.radio(key="pagina").set_value("B").run()
    assert at.selectbox(key="b_colegio").value == "CND"
    at.radio(key="pagina").set_value("A").run()
    assert at.selectbox(key="a_colegio").value == "CND"


def test_un_valor_que_no_esta_en_las_opciones_no_se_siembra():
    at = AppTest.from_function(_app).run()
    at.selectbox(key="a_colegio").set_value("LauV").run()
    at.radio(key="pagina").set_value("B").run()
    assert at.selectbox(key="b_colegio").value == "Todos"


def test_sembrar_no_pisa_lo_que_eligio_la_persona():
    from src.ui import estado
    sesion = {"w": "CND", estado.COLEGIO: "LauV"}
    estado.sembrar("w", estado.COLEGIO, ["LauV", "CND"], sesion=sesion)
    assert sesion["w"] == "CND"


def test_el_colegio_de_la_url_se_aplica_una_sola_vez():
    from src.ui import estado
    sesion = {}
    estado.aplicar_colegio_de_url("LauV", sesion=sesion)
    assert sesion[estado.COLEGIO] == "LauV"
    sesion[estado.COLEGIO] = "CND"            # la persona cambió de colegio
    estado.aplicar_colegio_de_url("LauV", sesion=sesion)
    assert sesion[estado.COLEGIO] == "CND"


def test_sin_colegio_en_la_url_no_hace_nada():
    from src.ui import estado
    sesion = {}
    estado.aplicar_colegio_de_url(None, sesion=sesion)
    assert estado.COLEGIO not in sesion
