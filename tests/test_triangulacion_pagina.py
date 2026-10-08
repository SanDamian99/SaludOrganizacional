"""Triangulación 360 · página (fase 5): sin archivos, sin clave, módulo viejo y sintéticos."""

from src.triangulacion import catalogo as cat
from src.ui.views import triangulacion_investigador as vi
from tests import triangulacion_sinteticos as ts


def _pagina(monkeypatch, datos: str, clave: str | None):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    if clave:
        monkeypatch.setenv("OBS360_CLAVE_HMAC", clave)
    else:
        monkeypatch.delenv("OBS360_CLAVE_HMAC", raising=False)
        monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    return AppTest.from_string(
        "from src.ui.triangulacion import render_triangulacion\nrender_triangulacion()\n",
        default_timeout=180)


def test_sin_archivos_da_el_mensaje_del_despliegue(monkeypatch, tmp_path):
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any(cat.AVISO_DESPLIEGUE in i.value for i in at.info)
    assert any("Cuidadores: no" in c.value for c in at.caption)


def test_sin_clave_explica_que_falta(monkeypatch, tmp_path):
    ts.escribir(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), None).run()
    assert not at.exception
    assert any("OBS360_CLAVE_HMAC" in e.value for e in at.error)


def test_con_un_modulo_viejo_pide_reiniciar(monkeypatch, tmp_path):
    from src.estudiantes import ingest
    ts.escribir(tmp_path)

    def viejo(rutas, niveles=None):
        raise AssertionError("no debía llamarse")
    monkeypatch.setattr(ingest, "cargar_varios", viejo)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any("Reinicie" in w.value for w in at.warning)


def test_con_datos_muestra_las_pestanas_sin_nada_individual(monkeypatch, tmp_path):
    ts.escribir(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS
    at.selectbox(key="tri_ba").set_value("SDQ_Emo").run()
    assert not at.exception
    pantalla = " ".join(str(e.value) for e in at.markdown) + \
        " ".join(str(getattr(d, "value", "")) for d in at.dataframe)
    for prohibido in ts.textos_prohibidos():
        assert prohibido not in pantalla
