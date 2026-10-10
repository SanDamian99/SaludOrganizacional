"""La tabla del mapa: una fila por colegio, sin cifras de grupos ocultos."""
import pytest

from src.geo import mapa_datos as md
from src.ui.views.estudiantes_comunidad import grupos_visibles
from tests.mapa_datos_sinteticos import analisis_sintetico

CODIGOS = ["LauV", "JJC", "SJMEB", "LaBalsa", "Bojacá"]


def _filas(capa):
    a = analisis_sintetico()
    visibles, pequenos = grupos_visibles(a, "Colegio")
    return {f.codigo: f for f in md.tabla_mapa(a, capa, CODIGOS, visibles, pequenos)}


def test_el_analisis_sintetico_separa_visibles_y_pequenos():
    visibles, pequenos = grupos_visibles(analisis_sintetico(), "Colegio")
    assert visibles == ["JJC", "LauV", "SJMEB"]
    assert pequenos == ["LaBalsa"]


@pytest.mark.parametrize("n, tramo", [(9, None), (10, "10 a 29"), (29, "10 a 29"),
                                      (30, "30 a 99"), (99, "30 a 99"),
                                      (100, "100 o más"), ("<10", None), (None, None)])
def test_tramos(n, tramo):
    assert md.tramo_de(n) == tramo


def test_capa_respuestas_da_tramo_y_nunca_valor():
    f = _filas("respuestas")
    assert f["LauV"].estado == md.CON_CIFRA and f["LauV"].tramo == "100 o más"
    assert f["SJMEB"].tramo == "30 a 99"
    assert all(x.valor is None for x in f.values())


def test_colegio_pequeno_sale_sin_cifra_ni_tramo():
    for capa in md.CAPAS:
        f = _filas(capa)["LaBalsa"]
        assert f.estado == md.PEQUENA
        assert f.tramo is None and f.valor is None


def test_colegio_sin_formulario_se_distingue_del_pequeno():
    assert _filas("respuestas")["Bojacá"].estado == md.SIN_FORMULARIO


def test_capa_sentirse_parte_da_media_y_referencia_del_municipio():
    f = _filas("sentirse_parte")["LauV"]
    assert f.estado == md.CON_CIFRA
    assert f.valor == pytest.approx(3.4) and f.referencia == pytest.approx(3.3)


def test_capa_apoyo_social_usa_mspss():
    assert _filas("apoyo_social")["JJC"].valor == pytest.approx(4.8)


def test_colegio_visible_sin_valor_en_el_indicador_queda_sin_indicador():
    a = analisis_sintetico()
    a.por_colegio = a.por_colegio.drop(columns=["M·JJC"])
    visibles, pequenos = grupos_visibles(a, "Colegio")
    filas = {f.codigo: f for f in md.tabla_mapa(a, "sentirse_parte", CODIGOS,
                                                visibles, pequenos)}
    assert filas["JJC"].estado == md.SIN_INDICADOR and filas["JJC"].valor is None
    assert filas["JJC"].referencia is None


def test_sin_tabla_por_colegio_no_falla():
    a = analisis_sintetico()
    a.por_colegio = a.por_colegio.iloc[0:0]
    visibles, pequenos = grupos_visibles(a, "Colegio")
    filas = md.tabla_mapa(a, "apoyo_social", CODIGOS, visibles, pequenos)
    assert all(f.valor is None for f in filas)


def test_capa_de_malestar_no_existe():
    a = analisis_sintetico()
    for capa in ("sdq_total", "rcads", "alertas", "muerte"):
        with pytest.raises(ValueError):
            md.tabla_mapa(a, capa, CODIGOS, [], [])
