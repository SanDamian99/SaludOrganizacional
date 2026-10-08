"""Cuidadores 360 · página (fase 4a): sin archivo, sin clave y con datos sintéticos."""

from src.cuidadores import catalog as cat
from src.ui.views import cuidadores_investigador as vi
from tests import cuidadores_sinteticos as cs


def _pagina(monkeypatch, datos: str, clave: str | None):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    if clave:
        monkeypatch.setenv("OBS360_CLAVE_HMAC", clave)
    else:
        monkeypatch.delenv("OBS360_CLAVE_HMAC", raising=False)
        monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    return AppTest.from_string(
        "from src.ui.cuidadores import render_cuidadores\nrender_cuidadores()\n",
        default_timeout=120)


def test_sin_datos_dice_que_no_esta_publicado(monkeypatch, tmp_path):
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any("aún no está publicado" in i.value for i in at.info)


def test_sin_clave_explica_que_falta(monkeypatch, tmp_path):
    cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    at = _pagina(monkeypatch, str(tmp_path), None).run()
    assert not at.exception
    assert any("OBS360_CLAVE_HMAC" in e.value for e in at.error)


def test_con_datos_muestra_las_pestanas_y_el_filtro_de_ola(monkeypatch, tmp_path):
    cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS
    ola = at.selectbox(key="cuid_ola")
    assert list(ola.options) == ["Todas", "2025", "2026"]
    ola.set_value("2026").run()
    assert not at.exception
    assert any(vi.SOLO_TODAS == c.value for c in at.caption)
    at.radio(key="cuid_marco").set_value(cat.MARCO_NINO).run()
    assert not at.exception
    pantalla = " ".join(str(e.value) for e in at.markdown) + \
        " ".join(str(getattr(d, "value", "")) for d in at.dataframe)
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in pantalla
