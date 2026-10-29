"""Página «Dónde pedir ayuda» y cuadro de ayuda: se dibujan sin red ni datos."""
from streamlit.testing.v1 import AppTest

from src.core import lineas_atencion as la


def _app_pagina():
    from src.ui.lineas import render_lineas
    render_lineas()


def _app_cuadro():
    from src.ui.lineas import cuadro_ayuda
    cuadro_ayuda("estudiante")


def _texto(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_la_pagina_se_dibuja_con_lo_urgente_primero():
    at = AppTest.from_function(_app_pagina).run()
    assert not at.exception
    texto = _texto(at)
    assert "Primero" in texto and "tel:106" in texto and "tel:123" in texto
    assert "Chía: Centros de Escucha" in texto
    assert len(at.expander) >= 2


def test_todas_las_combinaciones_de_filtros_funcionan():
    at = AppTest.from_function(_app_pagina).run()
    for para in ("Todos", *la.PARA):
        for tema in ("Todos", *la.TEMAS):
            at.selectbox(key="lin_para").set_value(para)
            at.selectbox(key="lin_tema").set_value(tema)
            at.run()
            assert not at.exception, (para, tema)


def test_filtro_de_municipio_abre_ese_municipio():
    at = AppTest.from_function(_app_pagina).run()
    at.selectbox(key="lin_lugar").set_value("sopo").run()
    assert not at.exception
    assert "Código Dorado" in _texto(at)
    assert "Chía: Centros de Escucha" not in _texto(at)


def test_el_cuadro_muestra_los_tres_niveles():
    at = AppTest.from_function(_app_cuadro).run()
    assert not at.exception
    texto = _texto(at)
    for titulo in la.NIVELES_TITULO.values():
        assert titulo in texto


def test_la_tarjeta_imprimible_trae_chia_y_el_123():
    from src.ui.lineas import html_tarjeta
    h = html_tarjeta()
    assert "601 884 4444" in h and "123" in h and "Sopó" not in h
