"""Las vistas y los informes con cifras suprimidas por pocos casos."""
import pandas as pd
import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import lectura, pipeline, publicar
from src.ui.views import estudiantes_comunidad as vc
from src.ui.views import estudiantes_informe as inf
from tests.test_supresion_pipeline import CELDAS, NIVEL, _datos

CELDA_OCULTA = {"nivel": NIVEL, "colegio": "A", "grado": "Sexto"}


@pytest.fixture(scope="module")
def local():
    return pipeline.analizar(_datos(CELDAS), NIVEL, n_boot=5)


@pytest.fixture(scope="module")
def publicado(local):
    filas = publicar.aplanar({NIVEL: local})
    publicar.verificar(filas)
    return lectura._reconstruir(NIVEL, filas)


@pytest.fixture(params=["local", "publicado"])
def a(request, local, publicado):
    return local if request.param == "local" else publicado


def test_la_prevalencia_suprimida_no_es_cero(a):
    assert vc.prevalencia(a, "ideacion", CELDA_OCULTA) == {}
    assert vc.cifra_suprimida(a, "ideacion", CELDA_OCULTA)
    assert not vc.cifra_suprimida(a, "ideacion", {})


def test_la_tarjeta_dice_el_texto_fijo(a):
    t = [t for t in vc.tarjetas(a, "colegio", CELDA_OCULTA) if t.clave == "ideacion"]
    assert t and t[0].suprimida
    assert t[0].cifra == cat.CIFRA_SUPRIMIDA
    assert t[0].detalle == cat.CIFRAS_PEQUENAS
    assert "%" not in t[0].cifra


def test_la_comparacion_omite_y_nombra_los_grupos_sin_cifra(a):
    tabla = vc.prevalencia_por(a, "ideacion", "Colegio", {"grado": "Sexto"})
    assert "A" not in set(tabla["grupo"].astype(str))
    assert "casos" not in tabla.columns
    assert tabla["pct"].notna().all()
    assert "A" in vc.grupos_sin_cifra(a, "ideacion", "Colegio", {"grado": "Sexto"})


def test_local_y_publicado_coinciden(local, publicado):
    for filtros in (CELDA_OCULTA, {"colegio": "B", "grado": "Sexto"}, {"grado": "Sexto"},
                    {"colegio": "A"}, {}):
        assert vc.prevalencia(local, "ideacion", filtros) == \
            vc.prevalencia(publicado, "ideacion", filtros), filtros
    for col, filtros in (("Colegio", {"grado": "Sexto"}), ("Grado", {}), ("Colegio", {})):
        x = vc.prevalencia_por(local, "ideacion", col, filtros).reset_index(drop=True)
        y = vc.prevalencia_por(publicado, "ideacion", col, filtros).reset_index(drop=True)
        pd.testing.assert_frame_equal(x, y, check_dtype=False)


def test_los_informes_no_se_caen_y_llevan_el_texto_fijo(a):
    md = vc.informe_markdown(a, "colegio", CELDA_OCULTA)
    assert cat.CIFRA_SUPRIMIDA in md
    html = inf.informe_una_pagina_html(a, "colegio", CELDA_OCULTA)
    assert cat.CIFRAS_PEQUENAS in html
    assert "nan %" not in html and "nan–" not in html


def test_por_sexo_aplica_la_regla():
    # celda grande: 20 mujeres con 1 caso emocional y 20 hombres con 8
    filas = []
    for i in range(40):
        mujer = i < 20
        filas.append(dict(Colegio="A", Grado="Sexto", Sexo="Mujer" if mujer else "Hombre",
                          Edad=13, nivel=NIVEL,
                          banda_SDQ_Emo=(3 if (mujer and i < 1) or (not mujer and i < 28)
                                         else 0)))
    d = pd.DataFrame(filas)
    a = pipeline.analizar(d, NIVEL, n_boot=5)
    assert vc.prevalencia_por_sexo(a, {}).empty
