"""
Las vistas e informes de cuidadores usan sus propios textos de estado.

«No es un diagnóstico», la nota del azar y qué quiere decir cada estado
vienen de `comunidad_catalogo`; la referencia habla del total del municipio
(en cuidadores no hay niveles).
"""
import inspect

from streamlit.testing.v1 import AppTest

from src.cuidadores import alertas as al
from src.cuidadores import comunidad_catalogo as cc
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import cuidadores_informe as vi
from tests import cuidadores_comunidad_datos as datos

TEXTOS = ("NO_ES_DIAGNOSTICO", "NOTA_AZAR", "QUE_ES_PRIORIDAD", "QUE_ES_PRESENTE",
          "QUE_ES_SIN_ESTADO", "QUE_ES_REFERENCIA")


def test_el_catalogo_de_cuidadores_tiene_sus_textos():
    for nombre in TEXTOS:
        assert getattr(cc, nombre)
    assert "total del municipio" in cc.QUE_ES_REFERENCIA
    assert "nivel" not in cc.QUE_ES_REFERENCIA


def test_las_vistas_no_toman_estos_textos_de_estudiantes():
    for modulo in (vc, vi):
        fuente = inspect.getsource(modulo)
        for nombre in TEXTOS:
            assert f"ac_est.{nombre}" not in fuente, (modulo.__name__, nombre)
        assert "va.explicaciones" not in fuente


def test_explicaciones_de_cuidadores():
    senales = vc.senales(datos.con_senales(datos.preparado()), "municipio")
    textos = vc.explicaciones(senales)
    assert textos and all(t in {getattr(cc, n) for n in TEXTOS[2:]} for t in textos)
    from src.ui.views.estudiantes_alertas import Senal
    ref = Senal(alerta="animo", nombre="x", estado=al.REFERENCIA, frase="", que_hacer="")
    assert vc.explicaciones([ref]) == [cc.QUE_ES_REFERENCIA]


def test_el_panel_html_usa_las_notas_de_cuidadores():
    html = vc.panel_html(datos.con_senales(datos.preparado()), "municipio", {})
    from html import escape
    assert escape(cc.NO_ES_DIAGNOSTICO) in html and escape(cc.NOTA_AZAR) in html


def test_el_panel_en_pantalla_usa_los_textos_de_cuidadores(tmp_path):
    import pickle
    ruta = tmp_path / "s.pkl"
    with open(ruta, "wb") as fh:
        pickle.dump(datos.con_senales(datos.preparado()), fh)
    at = AppTest.from_string(
        f"import pickle\nac = pickle.load(open({str(ruta)!r}, 'rb'))\n"
        "from src.ui.views.cuidadores_comunidad import render_panel\n"
        "render_panel(ac, 'municipio', {})\n", default_timeout=120).run()
    assert not at.exception
    pantalla = " ".join(str(e.value) for g in (at.markdown, at.caption) for e in g)
    assert cc.NO_ES_DIAGNOSTICO in pantalla and cc.NOTA_AZAR in pantalla
    assert cc.QUE_ES_REFERENCIA in pantalla
