"""
Resultados por colegio y por grado para el despliegue.

El despliegue lee la corrida publicada y no tiene fila por estudiante. Para que
pueda filtrar por colegio o por grado, el pipeline calcula por adelantado las
tablas de la vista comunidad para cada grupo que llega al mínimo, el publicador
las sube y el lector las rearma. Estas pruebas cierran ese circuito y comprueban
que las cifras que ve el despliegue son las mismas que recalcula la máquina que
procesa los archivos.
"""
import pandas as pd
import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring
from src.ui.views import estudiantes_comunidad as vc
from tests.test_estudiantes_comunidad import _formulario, COLEGIO_PEQUENO, GRADO_PEQUENO


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)


@pytest.fixture(scope="module")
def publicado(analisis):
    """El mismo análisis tras pasar por el publicador y el lector, sin red."""
    filas = publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
    publicar.verificar(filas)
    return lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)


def _colegio_grande(a):
    visibles, _ = vc.grupos_visibles(a, "Colegio")
    return visibles[0]


def test_el_pipeline_calcula_subgrupos_solo_para_grupos_suficientes(analisis):
    colegios = analisis.subgrupos["Colegio"]
    grados = analisis.subgrupos["Grado"]
    assert _colegio_grande(analisis) in colegios
    assert all(s.n >= cat.MIN_GROUP_N for s in list(colegios.values()) + list(grados.values()))
    assert GRADO_PEQUENO not in grados
    assert not any(COLEGIO_PEQUENO in g for g in colegios)


def test_los_subgrupos_no_llevan_filas_individuales(analisis):
    for grupos in analisis.subgrupos.values():
        for s in grupos.values():
            assert s.datos.empty


def test_publicar_y_leer_conserva_los_subgrupos(analisis, publicado):
    assert publicado.datos.empty
    assert set(publicado.subgrupos["Colegio"]) == set(analisis.subgrupos["Colegio"])
    assert set(publicado.subgrupos["Grado"]) == set(analisis.subgrupos["Grado"])
    colegio = _colegio_grande(analisis)
    original = analisis.subgrupos["Colegio"][colegio]
    leido = publicado.subgrupos["Colegio"][colegio]
    assert leido.n == original.n
    pd.testing.assert_frame_equal(
        leido.cortes.reset_index(drop=True), original.cortes.reset_index(drop=True),
        check_dtype=False)


def test_las_filas_de_subgrupo_respetan_el_minimo(analisis):
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
             if f["tipo"].endswith("_grupo")]
    assert filas
    assert all(f["n"] >= cat.MIN_GROUP_N for f in filas)
    assert all(f["detalle"]["n_grupo"] >= cat.MIN_GROUP_N for f in filas)
    assert {f["agrupacion"] for f in filas} <= {"Colegio", "Grado"}


def test_el_despliegue_muestra_las_mismas_cifras_que_el_recalculo(analisis, publicado):
    colegio = _colegio_grande(analisis)
    f = {"colegio": colegio}
    crudo = vc.bandas_sdq_total(analisis, f)
    desplegado = vc.bandas_sdq_total(publicado, f)
    assert crudo and desplegado["n"] == crudo["n"]
    assert desplegado["pct"] == pytest.approx(crudo["pct"], abs=0.01)

    for indicador in vc.INDICADORES:
        assert vc.prevalencia(publicado, indicador, f) == pytest.approx(
            vc.prevalencia(analisis, indicador, f), abs=0.01)

    items_crudo = vc.items_pertenencia_bajos(analisis, 4, f)
    items_desp = vc.items_pertenencia_bajos(publicado, 4, f)
    assert [i["item"] for i in items_desp] == [i["item"] for i in items_crudo]

    grado = next(iter(analisis.subgrupos["Grado"]))
    g = {"grado": grado}
    assert vc.bandas_sdq_total(publicado, g)["n"] == vc.bandas_sdq_total(analisis, g)["n"]


def test_la_comparacion_entre_grupos_sale_de_los_subgrupos(analisis, publicado):
    indicador = next(k for k in vc.INDICADORES if vc.prevalencia(analisis, k, {}))
    crudo = vc.prevalencia_por(analisis, indicador, "Grado", {})
    desp = vc.prevalencia_por(publicado, indicador, "Grado", {})
    assert list(desp.columns) == ["grupo", "n", "casos", "pct", "ic_inf", "ic_sup"]
    assert set(desp["grupo"]) == set(crudo["grupo"])
    fusion = crudo.merge(desp, on="grupo", suffixes=("_c", "_d"))
    assert (fusion["pct_c"] - fusion["pct_d"]).abs().max() < 0.01
    # con un filtro en la otra dimensión no se puede cruzar
    assert vc.prevalencia_por(publicado, indicador, "Grado",
                              {"colegio": _colegio_grande(analisis)}).empty


def test_sin_subgrupo_publicado_no_hay_cifra_y_el_informe_lo_explica(analisis, publicado):
    colegio = _colegio_grande(analisis)
    grado = next(iter(analisis.subgrupos["Grado"]))
    cruce = {"colegio": colegio, "grado": grado}
    assert vc.subanalisis(publicado, cruce) is None
    assert vc.bandas_sdq_total(publicado, cruce) == {}
    assert vc.items_pertenencia_bajos(publicado, 4, cruce) == []
    assert vc.tarjetas(publicado, "colegio", cruce) == []
    informe = vc.informe_markdown(publicado, "colegio", cruce)
    assert "por colegio y por grado" in informe
    # y un grupo pequeño tampoco aparece, publicado o no
    assert vc.bandas_sdq_total(publicado, {"grado": GRADO_PEQUENO}) == {}


def test_una_corrida_antigua_sin_subgrupos_sigue_leyendose(analisis):
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
             if not f["tipo"].endswith("_grupo")]
    viejo = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert viejo.subgrupos == {}
    assert vc.bandas_sdq_total(viejo, {}) == vc.bandas_sdq_total(analisis, {})
    assert vc.bandas_sdq_total(viejo, {"colegio": _colegio_grande(analisis)}) == {}
