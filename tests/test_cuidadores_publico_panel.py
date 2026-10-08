"""
En público la página de Cuidadores nunca sale sin el panel de señales.

Si la corrida publicada no trae las filas de las señales del adulto (se
publicó con `--publicar-ya` antes de aprobar textos y ruta), la página dice
que aún no está publicada en vez de mostrarse sin el panel.
"""
import pytest
from streamlit.testing.v1 import AppTest

from src.cuidadores import comunidad_catalogo as cc
from src.ui.views import cuidadores_comunidad as vc
from tests import cuidadores_comunidad_datos as datos


def _pagina(monkeypatch, aprobado: bool):
    from src.cuidadores import lectura
    _, base = datos.publicado(aprobado=aprobado)
    monkeypatch.setattr(lectura, "disponible", lambda: True)
    monkeypatch.setattr(lectura, "_cliente", lambda: base.cliente(anonimo=True))
    monkeypatch.setattr(cc, "TEXTOS_APROBADOS", True)
    monkeypatch.setattr(cc, "RUTAS_VALIDADAS", True)
    vc._leer_publicado.clear()
    vc._corrida_vigente.clear()
    at = AppTest.from_string("from src.ui.views.cuidadores_comunidad import render_publico\n"
                             "render_publico()\n", default_timeout=120)
    at.session_state["cuid_com_rol"] = "municipio"
    return at.run()


def test_tiene_senales():
    assert vc.tiene_senales(datos.publicado(aprobado=True)[0])
    assert not vc.tiene_senales(datos.publicado(aprobado=False)[0])
    assert not vc.tiene_senales(None)


def test_sin_filas_de_senales_dice_no_publicado(monkeypatch):
    at = _pagina(monkeypatch, aprobado=False)
    assert not at.exception
    assert any(cc.NO_PUBLICADO in i.value for i in at.info)
    assert not at.selectbox                      # no se dibujó la vista


def test_con_senales_se_dibuja_la_vista(monkeypatch):
    at = _pagina(monkeypatch, aprobado=True)
    assert not at.exception
    assert not any(cc.NO_PUBLICADO in i.value for i in at.info)
    assert at.sidebar.selectbox
