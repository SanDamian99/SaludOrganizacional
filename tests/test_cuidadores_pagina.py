"""Cuidadores 360 · página: sin archivo, sin clave, con datos sintéticos y con la corrida
publicada (fases 4a y 4b)."""

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.cuidadores import lectura
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import cuidadores_investigador as vi
from tests import cuidadores_sinteticos as cs


def _pagina(monkeypatch, datos: str, clave: str | None, modo: str = "investigador"):
    """La página, en el modo pedido y sin red: sin corrida publicada salvo que se simule."""
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_MODO", modo)
    monkeypatch.setattr(lectura, "disponible", lambda: False)
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


# ══ Fase 4b: selector de vista y corrida publicada ═════════════════════════
def _archivo(tmp_path):
    cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")


def _texto(at) -> str:
    return " ".join(str(getattr(e, "value", "")) for g in (at.markdown, at.caption, at.info)
                    for e in g)


def test_en_completo_abre_la_vista_de_comunidad(monkeypatch, tmp_path):
    _archivo(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA, modo="completo").run()
    assert not at.exception
    vista = at.radio(key="cuid_audiencia")
    from src.ui.cuidadores import AUDIENCIAS
    assert list(vista.options) == list(AUDIENCIAS.values()) and vista.value == "comunidad"
    assert at.radio(key="cuid_com_rol").value in cc.ROLES
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in _texto(at)
    assert cc.TEXTOS_PENDIENTES in _texto(at)          # aviso interno del modo completo
    vista.set_value("investigador").run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS


def test_en_investigador_abre_la_vista_de_investigadores(monkeypatch, tmp_path):
    _archivo(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA).run()
    assert at.radio(key="cuid_audiencia").value == "investigador"
    at.radio(key="cuid_audiencia").set_value("comunidad").run()
    assert not at.exception
    assert not [s for s in at.selectbox if s.key == "cuid_ola"]   # sin filtro de ola


def test_sin_archivo_lee_la_corrida_publicada(monkeypatch, tmp_path):
    from tests import cuidadores_comunidad_datos as datos
    publicado = datos.publicado()[0]
    at = _pagina(monkeypatch, str(tmp_path), None)
    monkeypatch.setattr(vc, "publicado", lambda: publicado)
    at.run()
    assert not at.exception
    assert any(lectura.AVISO_PUBLICADO in i.value for i in at.info)
    assert [t.label for t in at.tabs] == vi.PESTANAS
    assert not [s for s in at.selectbox if s.key == "cuid_ola"]
    at.radio(key="cuid_audiencia").set_value("comunidad").run()
    assert not at.exception
    assert at.radio(key="cuid_com_rol").value in cc.ROLES


def test_la_fuente_supabase_se_puede_forzar(monkeypatch, tmp_path):
    from tests import cuidadores_comunidad_datos as datos
    _archivo(tmp_path)
    publicado = datos.publicado()[0]
    monkeypatch.setenv("OBS360_FUENTE", "supabase")
    at = _pagina(monkeypatch, str(tmp_path), cs.CLAVE_PRUEBA)
    monkeypatch.setattr(vc, "publicado", lambda: publicado)
    at.run()
    assert not at.exception
    assert any(lectura.AVISO_PUBLICADO in i.value for i in at.info)


def test_la_vista_de_investigadores_lee_conteos_enmascarados():
    assert vi.conteo_legible("<10") == "<10"
    assert vi.conteo_legible(12) == "12" and vi.conteo_legible(4) == "<10"
    from types import SimpleNamespace
    inf = SimpleNamespace(**dict(lectura.INFORME_POR_DEFECTO, filas_archivo=779,
                                 sin_consentimiento="<10", respuestas_repetidas_cuidador=22))
    md = vi.flujo_exclusiones_md(inf)
    assert "Sin consentimiento: <10 → quedan —" in md
