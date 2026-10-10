"""La sección del mapa: preparación pura y enganche en la vista de comunidad."""
import inspect

import pytest

from src.geo import auditoria_mapa, opciones
from src.geo.colegios_geo import Punto
from src.ui.views import estudiantes_comunidad as vc
from src.ui.views import estudiantes_mapa as em
from tests.mapa_datos_sinteticos import analisis_sintetico

VISIBLES, PEQUENOS = ["JJC", "LauV", "SJMEB"], ["LaBalsa"]
PUNTOS = [Punto("LauV", "Laura Vicuña", 4.86, -74.05),
          Punto("LaBalsa", "La Balsa", 4.87, -74.03)]


@pytest.fixture(autouse=True)
def _puntos_fijos(monkeypatch):
    monkeypatch.setattr(em.colegios_geo, "cargar_puntos", lambda *a, **k: (PUNTOS, []))


def test_preparar_devuelve_puntos_y_filas_auditadas():
    puntos, filas = em.preparar(analisis_sintetico(), "respuestas", VISIBLES, PEQUENOS)
    assert [p.codigo for p in puntos] == ["LauV", "LaBalsa"]
    assert {f.codigo: f.estado for f in filas} == {"LauV": "con_cifra", "LaBalsa": "pequena"}


def test_preparar_rechaza_una_capa_de_malestar():
    with pytest.raises(ValueError):
        em.preparar(analisis_sintetico(), "sdq_total", VISIBLES, PEQUENOS)


def test_preparar_no_deja_pasar_una_fila_que_falle_la_auditoria(monkeypatch):
    def mala(*a, **k):
        raise auditoria_mapa.AuditoriaMapa("x")
    monkeypatch.setattr(em.auditoria_mapa, "auditar", mala)
    with pytest.raises(auditoria_mapa.AuditoriaMapa):
        em.preparar(analisis_sintetico(), "respuestas", VISIBLES, PEQUENOS)


def test_render_no_dibuja_para_familia():
    assert em.render_mapa(analisis_sintetico(), "familia", VISIBLES, PEQUENOS) is False


def test_render_no_dibuja_si_no_hay_puntos(monkeypatch):
    monkeypatch.setattr(em.colegios_geo, "cargar_puntos", lambda *a, **k: ([], ["x"]))
    assert em.render_mapa(analisis_sintetico(), "municipio", VISIBLES, PEQUENOS) is False


def test_render_no_dibuja_si_el_equipo_quita_el_rol(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_ROLES", ("municipio",))
    assert em.render_mapa(analisis_sintetico(), "colegio", VISIBLES, PEQUENOS) is False


def test_la_vista_de_comunidad_engancha_el_mapa_y_no_se_rompe_si_falla():
    fuente = inspect.getsource(vc.render_comunidad)
    assert "render_mapa" in fuente
    # El mapa es un complemento: si falla, la página sigue.
    antes = fuente.index("render_mapa")
    assert "except" in fuente[antes:antes + 400]


def test_el_mapa_se_dibuja_despues_del_panel_de_alertas_y_antes_de_las_tarjetas():
    fuente = inspect.getsource(vc.render_comunidad)
    assert (fuente.index("_panel_alertas(a, rol, filtros)")
            < fuente.index("render_mapa")
            < fuente.index("tarjetas(a, rol, filtros"))
