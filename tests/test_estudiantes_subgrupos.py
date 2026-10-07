"""
Resultados por colegio y por grado para el despliegue.

El despliegue lee la corrida publicada y no tiene fila por estudiante. Para que
pueda filtrar por colegio o por grado, el pipeline calcula por adelantado las
tablas de la vista comunidad para cada grupo que llega al mínimo, el publicador
las sube y el lector las rearma. Estas pruebas cierran ese circuito y comprueban
que las cifras que ve el despliegue son las mismas que recalcula la máquina que
procesa los archivos.
"""
import dataclasses

import pandas as pd
import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, lectura, pipeline, privacidad, publicar, scoring
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
    # el número de casos no se publica (supresion.py): se compara sin él
    pd.testing.assert_frame_equal(
        leido.cortes.reset_index(drop=True),
        original.cortes.drop(columns=["casos"]).reset_index(drop=True),
        check_dtype=False)


def test_las_filas_de_subgrupo_respetan_el_minimo(analisis):
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
             if f["tipo"].endswith("_grupo")]
    assert filas
    assert all(f["n"] >= cat.MIN_GROUP_N for f in filas)
    assert all(f["detalle"]["n_grupo"] >= cat.MIN_GROUP_N for f in filas)
    assert {f["agrupacion"] for f in filas} <= {"Colegio", "Grado", "Colegio×Grado"}


def test_el_pipeline_publica_el_cruce_colegio_grado(analisis):
    cruce = analisis.subgrupos["Colegio×Grado"]
    assert set(cruce) == {"LauV|Séptimo", "LauV|Octavo"}
    assert all(s.n >= cat.MIN_GROUP_N for s in cruce.values())


def test_el_colegio_excluye_su_grado_pequeno(analisis):
    # LauV tiene 4 respuestas en Noveno: el colegio publicado son sus dos celdas
    assert analisis.subgrupos["Colegio"]["LauV"].n == 62


def test_los_datos_del_analisis_ya_estan_enmascarados(analisis):
    # todo o nada es idempotente: sobre datos ya enmascarados no borra nada más
    assert isinstance(analisis.base, privacidad.Base)
    assert privacidad.aplicar_todo_o_nada(analisis.datos, analisis.base)[1] == {}
    assert analisis.n == len(analisis.datos) == 70
    assert analisis.muestra["base"]["n_nivel"] == len(analisis.base.nivel) == 62
    assert isinstance(analisis.muestra["suprimidos"], dict)


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
    assert vc.bandas_sdq_total(publicado, g) == vc.bandas_sdq_total(analisis, g)
    assert vc.n_bandas(publicado, g) == vc.n_bandas(analisis, g) > 0


def test_la_comparacion_entre_grupos_sale_de_los_subgrupos(analisis, publicado):
    indicador = next(k for k in vc.INDICADORES if vc.prevalencia(analisis, k, {}))
    for filtros in ({}, {"colegio": "LauV"}):
        crudo = vc.prevalencia_por(analisis, indicador, "Grado", filtros)
        desp = vc.prevalencia_por(publicado, indicador, "Grado", filtros)
        assert list(desp.columns) == ["grupo", "n", "pct", "ic_inf", "ic_sup"]
        ocultos = vc.grupos_sin_cifra(publicado, indicador, "Grado", filtros)
        assert ocultos == vc.grupos_sin_cifra(analisis, indicador, "Grado", filtros)
        assert set(desp["grupo"]) == set(crudo["grupo"])
        assert not desp.empty or ocultos
        fusion = crudo.merge(desp, on="grupo", suffixes=("_c", "_d"))
        if not fusion.empty:
            assert (fusion["pct_c"] - fusion["pct_d"]).abs().max() < 0.01


def test_el_cruce_publicado_da_las_mismas_cifras_que_el_recalculo(analisis, publicado):
    f = {"colegio": "LauV", "grado": "Octavo"}
    assert vc.n_bandas(publicado, f) == vc.n_bandas(analisis, f) == 31
    assert vc.bandas_sdq_total(publicado, f) == vc.bandas_sdq_total(analisis, f)
    for indicador in vc.INDICADORES:
        assert vc.prevalencia(publicado, indicador, f) == pytest.approx(
            vc.prevalencia(analisis, indicador, f), abs=0.01)


def test_un_cruce_pequeno_no_da_cifras_y_el_informe_lo_explica(analisis, publicado):
    cruce = {"colegio": "LauV", "grado": GRADO_PEQUENO}
    for a in (analisis, publicado):
        assert vc.bandas_sdq_total(a, cruce) == {}
        assert vc.items_pertenencia_bajos(a, 4, cruce) == []
        assert vc.tarjetas(a, "colegio", cruce) == []
    assert vc.subanalisis(publicado, cruce) is None
    informe = vc.informe_markdown(publicado, "colegio", cruce)
    assert "por colegio y por grado" in informe
    assert vc.bandas_sdq_total(publicado, {"grado": GRADO_PEQUENO}) == {}


def test_una_corrida_antigua_sin_subgrupos_sigue_leyendose(analisis):
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
             if not f["tipo"].endswith("_grupo")]
    viejo = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert viejo.subgrupos == {}
    assert vc.bandas_sdq_total(viejo, {}) == vc.bandas_sdq_total(analisis, {})
    assert vc.bandas_sdq_total(viejo, {"colegio": _colegio_grande(analisis)}) == {}


def test_los_grupos_fuera_de_la_base_se_informan_como_enmascarados(analisis):
    assert "DiosCh" in analisis.enmascarados["Colegio"]
    assert "LauV" not in analisis.enmascarados["Colegio"]
    assert analisis.enmascarados["Grado"] == [GRADO_PEQUENO]


def test_subanalizar_sin_base_tambien_enmascara():
    bruto, _ = ingest.cargar(_formulario())
    d = scoring.puntuar(bruto)
    d = d[d["nivel"] == cat.NIVEL_SECUNDARIA].reset_index(drop=True)
    base = privacidad.base_publicable(d)
    # la celda LauV|Octavo queda con 3 respuestas válidas de SDQ_Total
    celda = base.celdas["LauV|Octavo"]
    d.loc[celda[3:], "SDQ_Total"] = float("nan")
    claves = [k for k in pipeline.CLAVES_PRINCIPALES if k in d.columns]
    dm, suprimidos = privacidad.aplicar_todo_o_nada(d, base)
    assert suprimidos["SDQ_Total"] == 3

    def bandas(sub):
        return sub["Colegio×Grado"]["LauV|Octavo"].bandas.reset_index(drop=True)

    sin_base = pipeline.subanalizar(d, cat.NIVEL_SECUNDARIA, claves)
    enmascarado = pipeline.subanalizar(dm, cat.NIVEL_SECUNDARIA, claves, base)
    crudo = pipeline.subanalizar(d, cat.NIVEL_SECUNDARIA, claves, base)
    pd.testing.assert_frame_equal(bandas(sin_base), bandas(enmascarado))
    assert not bandas(crudo).equals(bandas(enmascarado))


def test_el_cci_se_publica_con_el_n_del_nivel(analisis):
    # en el formulario sintético solo LauV entra al nivel y el CCI no se define;
    # se fija uno para comprobar con qué n sale la fila
    con_cci = dataclasses.replace(analisis, icc={"SDQ_Total": 0.05})
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: con_cci})
             if f["tipo"] == "icc"]
    assert filas
    assert all(f["n"] == len(analisis.base.nivel) == 62 for f in filas)


def test_los_grupos_publicables_son_los_mismos_desde_el_despliegue(analisis, publicado):
    for columna, otra in (("Grado", "LauV"), ("Grado", vc.TODOS),
                          ("Colegio", vc.TODOS), ("Colegio", "Octavo")):
        assert vc.grupos_publicables(publicado, columna, otra) == \
            vc.grupos_publicables(analisis, columna, otra)
    assert vc.grupos_publicables(publicado, "Grado", "LauV") == ["Séptimo", "Octavo"]
    # el despliegue recibe «<10» en vez del número y lo dice igual
    assert vc.nota_base(publicado)
