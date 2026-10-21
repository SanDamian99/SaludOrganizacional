"""La ayuda aparece en pantalla al escoger un indicador (AppTest, sin datos reales)."""
import pickle

from streamlit.testing.v1 import AppTest

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, scoring
from src.ui import ayuda_indicador as ay
from src.ui.views import cuidadores_comunidad as vc
from src.ui.views import estudiantes_comunidad as ve
from tests import cuidadores_comunidad_datos as datos_cuid
from tests import docentes_sinteticos as sint
from tests import test_estudiantes_comunidad as te


def _infos(at) -> str:
    return " ".join(str(i.value) for i in at.info)


def _pagina_docentes():
    from src.ui.dashboard import render_dashboard
    render_dashboard()


def test_docentes_muestra_la_ayuda_del_indicador_escogido():
    at = AppTest.from_function(_pagina_docentes, default_timeout=60)
    at.session_state["df"] = sint.docentes()
    at.run()
    assert not at.exception
    selector = next(s for s in at.selectbox if s.label == "Indicador:")
    for clave in ("Descon", "BTA"):
        selector.set_value(clave).run()
        assert not at.exception
        selector = next(s for s in at.selectbox if s.label == "Indicador:")
        esperado = ay.ayuda("docentes", clave)
        infos = _infos(at)
        assert "Qué mide:" in infos and "Puntaje alto:" in infos
        assert esperado.items[0].rstrip(".") in infos


def test_cuidadores_muestra_la_ayuda_del_indicador_escogido(tmp_path):
    ruta = tmp_path / "ac.pkl"
    with open(ruta, "wb") as fh:
        pickle.dump(datos_cuid.preparado(), fh)
    at = AppTest.from_string(
        f"import pickle\nac = pickle.load(open({str(ruta)!r}, 'rb'))\n"
        "from src.ui.views.cuidadores_comunidad import render_comunidad\nrender_comunidad(ac)\n",
        default_timeout=120)
    at.session_state["cuid_com_rol"] = "municipio"
    at.run()
    assert not at.exception
    selector = at.selectbox(key="cuid_com_indicador")
    claves = {i["etiqueta"].capitalize(): k for k, i in vc.INDICADORES.items()}
    for etiqueta in selector.options:
        selector.set_value(claves[etiqueta]).run()
        assert not at.exception
        selector = at.selectbox(key="cuid_com_indicador")
        assert ay.ayuda("cuidadores", claves[etiqueta]).items[0].rstrip(".") in _infos(at)


def test_estudiantes_muestra_la_ayuda_del_indicador_escogido(tmp_path):
    bruto, _ = ingest.cargar(te._formulario())
    analisis = pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)
    ruta = tmp_path / "a.pkl"
    with open(ruta, "wb") as fh:
        pickle.dump({cat.NIVEL_SECUNDARIA: analisis}, fh)
    at = AppTest.from_string(
        f"import pickle\nanalisis = pickle.load(open({str(ruta)!r}, 'rb'))\n"
        "from src.ui.views.estudiantes_comunidad import render_comunidad\n"
        "render_comunidad(analisis)\n", default_timeout=120)
    at.run()
    assert not at.exception
    selector = at.selectbox(key="est_com_indicador")
    assert len(selector.options) >= 1
    claves = {i["etiqueta"].capitalize(): k for k, i in ve.INDICADORES.items()}
    for etiqueta in selector.options:
        selector.set_value(claves[etiqueta]).run()
        assert not at.exception
        selector = at.selectbox(key="est_com_indicador")
        assert ay.ayuda("estudiantes", claves[etiqueta]).items[0].rstrip(".") in _infos(at)
