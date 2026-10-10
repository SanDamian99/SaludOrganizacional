"""El mapa dentro del informe de la Secretaría: estático, auditado y opcional."""
import base64
import re

import pytest

from src.estudiantes import catalog as cat
from src.geo import auditoria_mapa, mapa_informe, opciones
from src.geo.colegios_geo import Punto
from src.ui.views import estudiantes_informe as inf
from tests.mapa_datos_sinteticos import analisis_sintetico
from tests.test_estudiantes_informe import analisis, publicado, fuente  # noqa: F401

VISIBLES, PEQUENOS = ["JJC", "LauV", "SJMEB"], ["LaBalsa"]
PUNTOS = [Punto("LauV", "Laura Vicuña", 4.86, -74.05),
          Punto("JJC", "José Joaquín Casas", 4.85, -74.06),
          Punto("LaBalsa", "La Balsa", 4.87, -74.03)]


@pytest.fixture(autouse=True)
def _puntos_fijos(monkeypatch):
    monkeypatch.setattr(mapa_informe.colegios_geo, "cargar_puntos",
                        lambda *a, **k: (PUNTOS, []))


def _svgs(html: str) -> list[str]:
    return [base64.b64decode(m).decode("utf-8") for m in
            re.findall(r'src="data:image/svg\+xml;base64,([^"]+)"', html)]


def test_bloque_trae_una_figura_svg_por_capa_y_sus_leyendas():
    html = mapa_informe.bloque_html(analisis_sintetico(), VISIBLES, PEQUENOS)
    svgs = _svgs(html)
    assert len(svgs) == 2 and all("<svg" in s for s in svgs)
    assert 'class="mapa-informe"' in html
    assert "<style>" in html                       # lleva su propio estilo
    assert "Respuestas recibidas" in html and "Sentirse parte del colegio" in html
    assert cat.CIFRAS_PEQUENAS in html             # hay un colegio pequeño
    assert "No es un ranking ni un diagnóstico" in html


def test_sin_colegios_pequenos_no_repite_la_nota_de_cifras_pequenas():
    html = mapa_informe.bloque_html(analisis_sintetico(), VISIBLES, [])
    assert cat.CIFRAS_PEQUENAS not in html


def test_apagado_por_el_equipo_no_dibuja_nada(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_EN_INFORMES", False)
    assert mapa_informe.bloque_html(analisis_sintetico(), VISIBLES, PEQUENOS) == ""


def test_sin_capas_de_informe_no_dibuja_nada(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS_INFORME", ())
    assert mapa_informe.bloque_html(analisis_sintetico(), VISIBLES, PEQUENOS) == ""


def test_sin_puntos_no_dibuja_nada(monkeypatch):
    monkeypatch.setattr(mapa_informe.colegios_geo, "cargar_puntos",
                        lambda *a, **k: ([], ["x"]))
    assert mapa_informe.bloque_html(analisis_sintetico(), VISIBLES, PEQUENOS) == ""


def test_si_la_auditoria_falla_no_se_dibuja_ninguna_capa(monkeypatch):
    def mala(*a, **k):
        raise auditoria_mapa.AuditoriaMapa("x")
    monkeypatch.setattr(mapa_informe.auditoria_mapa, "auditar", mala)
    with pytest.raises(auditoria_mapa.AuditoriaMapa):
        mapa_informe.bloque_html(analisis_sintetico(), VISIBLES, PEQUENOS)


def test_el_informe_de_la_secretaria_incluye_el_mapa(fuente):
    html = inf.informe_secretaria_html(fuente)
    assert 'class="mapa-informe"' in html and _svgs(html)


def test_el_informe_de_la_secretaria_sigue_sin_el_mapa_si_se_apaga(fuente, monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_EN_INFORMES", False)
    assert 'class="mapa-informe"' not in inf.informe_secretaria_html(fuente)


def test_el_informe_no_se_cae_si_el_mapa_falla(fuente, monkeypatch):
    def rota(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(mapa_informe, "bloque_html", rota)
    html = inf.informe_secretaria_html(fuente)
    assert "Observatorio 360" in html and 'class="mapa-informe"' not in html


def test_el_informe_del_colegio_no_lleva_el_mapa(fuente):
    assert 'class="mapa-informe"' not in inf.informe_colegio_html(fuente, "LauV")
