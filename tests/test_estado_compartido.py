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
    valor = st.selectbox("colegio", opciones, key=clave,
                         on_change=estado.al_cambiar(clave, estado.COLEGIO))
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


def test_sembrar_reasigna_aunque_el_widget_ya_tenga_valor():
    """Un valor viejo que quedó en la sesión (parada prematura) no manda."""
    from src.ui import estado
    sesion = {"w": "CND", estado.COLEGIO: "LauV"}
    estado.sembrar("w", estado.COLEGIO, ["LauV", "CND"], sesion=sesion)
    assert sesion["w"] == "LauV"


def test_lo_que_elige_la_persona_pasa_al_compartido_antes_de_sembrar():
    from src.ui import estado
    sesion = {"w": "CND", estado.COLEGIO: "LauV"}
    estado.al_cambiar("w", estado.COLEGIO, sesion=sesion)()
    estado.sembrar("w", estado.COLEGIO, ["LauV", "CND"], sesion=sesion)
    assert sesion["w"] == sesion[estado.COLEGIO] == "CND"


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


# ── el colegio sobrevive al cambio de nivel en la vista comunidad ───────────
def _app_niveles():
    from types import SimpleNamespace
    import streamlit as st
    from src.ui.views import estudiantes_comunidad as vista

    def falso(colegios):
        return SimpleNamespace(subgrupos={"Colegio": {c: {} for c in colegios}, "Grado": {}},
                               muestra={}, datos=None, base=None)
    analisis = {"secundaria": falso(["LauV", "CND"]), "primaria": falso(["CND"])}
    nivel = st.radio("nivel", ["secundaria", "primaria"], key="nivel")
    vista._selector_grupo(analisis[nivel], "Colegio", "Colegio", nivel=nivel)


def test_el_colegio_sobrevive_al_cambio_de_nivel():
    from src.ui import estado
    at = AppTest.from_function(_app_niveles).run()
    assert not at.exception
    at.selectbox[0].set_value("CND").run()
    at.radio(key="nivel").set_value("primaria").run()
    assert at.selectbox[0].value == "CND"
    assert at.session_state[estado.COLEGIO] == "CND"
    at.radio(key="nivel").set_value("secundaria").run()
    assert at.selectbox[0].value == "CND"


def test_un_colegio_ausente_en_otro_nivel_no_pisa_el_compartido():
    from src.ui import estado
    at = AppTest.from_function(_app_niveles).run()
    at.selectbox[0].set_value("LauV").run()
    at.radio(key="nivel").set_value("primaria").run()
    assert at.selectbox[0].value == "Todos"          # primaria no tiene LauV
    assert at.session_state[estado.COLEGIO] == "LauV"
    at.radio(key="nivel").set_value("secundaria").run()
    assert at.selectbox[0].value == "LauV"


def test_elegir_todos_a_proposito_si_se_guarda():
    from src.ui import estado
    at = AppTest.from_function(_app_niveles).run()
    at.selectbox[0].set_value("CND").run()
    at.selectbox[0].set_value("Todos").run()
    assert at.session_state[estado.COLEGIO] == "Todos"
