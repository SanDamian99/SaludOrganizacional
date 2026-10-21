"""El glosario aparece en las tres vistas de investigador (AppTest, datos sintéticos)."""
import pickle

from streamlit.testing.v1 import AppTest

from src.cuidadores import catalog as cat_cuid
from src.estudiantes import catalog as cat_est
from src.estudiantes import ingest, pipeline, scoring
from tests import cuidadores_comunidad_datos as datos_cuid
from tests import test_estudiantes_comunidad as te
from tests import triangulacion_sinteticos as ts


def _expanders(at, rotulo):
    return [e for e in at.expander if rotulo in e.label]


def _contenido(expander) -> str:
    return " ".join(str(m.value) for m in expander.markdown)


def test_estudiantes_investigador_trae_el_glosario(tmp_path):
    bruto, _ = ingest.cargar(te._formulario())
    a = pipeline.analizar(scoring.puntuar(bruto), cat_est.NIVEL_SECUNDARIA, n_boot=20)
    ruta = tmp_path / "a.pkl"
    with open(ruta, "wb") as fh:
        pickle.dump({cat_est.NIVEL_SECUNDARIA: a}, fh)
    at = AppTest.from_string(
        f"import pickle\nanalisis = pickle.load(open({str(ruta)!r}, 'rb'))\n"
        "from src.ui.views.estudiantes_investigador import render_investigador\n"
        "render_investigador(analisis)\n", default_timeout=180).run()
    assert not at.exception
    (exp,) = _expanders(at, "Qué mide cada escala")
    texto = _contenido(exp)
    for esperado in ("SDQ · síntomas emocionales", "RCADS · depresión", "MSPSS · familia",
                     "PSSM · pertenencia al colegio", "Puntaje alto"):
        assert esperado in texto


def test_cuidadores_investigador_cambia_el_glosario_con_el_marco(tmp_path):
    ruta = tmp_path / "ac.pkl"
    with open(ruta, "wb") as fh:
        pickle.dump(datos_cuid.preparado(), fh)
    at = AppTest.from_string(
        f"import pickle\nac = pickle.load(open({str(ruta)!r}, 'rb'))\n"
        "from src.ui.views.cuidadores_investigador import render_investigador\n"
        "render_investigador(ac)\n", default_timeout=180).run()
    assert not at.exception
    (exp,) = _expanders(at, "Qué mide cada escala")
    assert "EPDS-10 · ánimo" in _contenido(exp)
    assert "SDQ padres · total de dificultades" not in _contenido(exp)
    at.radio(key="cuid_marco").set_value(cat_cuid.MARCO_NINO).run()
    assert not at.exception
    (exp,) = _expanders(at, "Qué mide cada escala")
    assert "SDQ padres · total de dificultades" in _contenido(exp)
    assert "EPDS-10 · ánimo" not in _contenido(exp)


def test_triangulacion_trae_el_glosario(monkeypatch, tmp_path):
    ts.escribir(tmp_path)
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    monkeypatch.setenv("OBS360_CLAVE_HMAC", ts.CLAVE_PRUEBA)
    at = AppTest.from_string(
        "from src.ui.triangulacion import render_triangulacion\nrender_triangulacion()\n",
        default_timeout=180).run()
    assert not at.exception
    (exp,) = _expanders(at, "Qué mide cada indicador")
    assert "Pertenencia al colegio (PSSM)" in _contenido(exp)
    assert "Ánimo del cuidador (EPDS-10)" in _contenido(exp)
