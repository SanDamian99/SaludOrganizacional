"""Cuidadores 360 · catálogo del formulario «Cuidando al Cuidador» (spec §3.2, §5.5)."""
from src.core.texto import norm_txt
from src.cuidadores import catalog as cat
from tests import cuidadores_sinteticos as cs


def test_bloques_por_posicion_de_la_spec():
    assert (cat.BARRIO.inicio, cat.PSS.inicio, cat.EPDS.inicio, cat.MSPSS.inicio,
            cat.APQ.inicio, cat.EP.inicio) == (20, 25, 35, 45, 57, 82)
    assert (cat.BARRIO.n_items, cat.PSS.n_items, cat.EPDS.n_items, cat.MSPSS.n_items,
            cat.APQ.n_items, cat.EP.n_items) == (5, 10, 10, 12, 25, 39)
    assert cat.SDQ_INICIO == {1: 121, 2: 153} and cat.ARI_INICIO == {1: 186, 2: 193}
    assert [cat.APQ.inicio + i - 1 for i in cat.APQ_FISICO] == [78, 79, 80]
    assert cat.APQ.inicio + cat.APQ_GRITO - 1 == 81
    assert [cat.EP.inicio + i - 1 for i in cat.EP_ELECCION_FORZADA] == [103, 104, 105, 106, 107]
    assert cat.EP.inicio + cat.EP_POSITIVO[0] - 1 == 117


def test_mspss_reparte_5_4_3():
    assert [len(v) for v in cat.MSPSS_FUENTES.values()] == [5, 4, 3]
    assert sorted(i for v in cat.MSPSS_FUENTES.values() for i in v) == list(range(1, 13))


def test_pss_igual_que_docentes():
    from scripts.preparar_docentes import INVERTIDOS, MAPAS
    assert tuple(int(x[3:]) for x in INVERTIDOS[4] if x.startswith("PSS")) == cat.PSS_INVERSOS
    assert {k: MAPAS["PSS"][k] for k in cat.MAP_PSS} == cat.MAP_PSS


def test_epds_tiene_un_mapa_por_item_y_cubre_todas_las_opciones():
    assert len(cat.EPDS_MAPAS) == 10
    for i, opciones in enumerate(cs.EPDS_OPCIONES):
        valores = [cat.EPDS_MAPAS[i][norm_txt(o)] for o in opciones]
        assert sorted(valores) == [0, 1, 2, 3], i + 1
    # ítems invertidos: la primera opción del formulario vale 3
    for item in (3, 5, 6, 7, 8, 9, 10):
        assert cat.EPDS_MAPAS[item - 1][norm_txt(cs.EPDS_OPCIONES[item - 1][0])] == 3
    for item in (1, 2, 4):
        assert cat.EPDS_MAPAS[item - 1][norm_txt(cs.EPDS_OPCIONES[item - 1][0])] == 0


def test_los_nombres_y_el_telefono_estan_declarados():
    assert set(cat.COLUMNAS_NOMBRE) == {3, 4, 147, 208}
    assert 179 in cat.NUNCA_SE_LEEN and 208 in cat.NUNCA_SE_LEEN


def test_el_formulario_sintetico_pasa_la_verificacion_de_encabezados():
    cols = cs.encabezados()
    assert len(cols) == cat.N_COLUMNAS
    for pos, fragmento in cat.VERIFICAR.items():
        assert fragmento in norm_txt(cols[pos])
