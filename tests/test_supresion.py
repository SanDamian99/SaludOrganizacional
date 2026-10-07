"""Supresión de proporciones con pocos casos («cifras que no delatan»).

Regla (spec 2026-10-06 §5.4): una proporción sobre n con k casos se publica
solo si MIN_CASOS ≤ k ≤ n − MIN_CASOS; además, ninguna resta entre cifras
publicadas puede devolver un conjunto de respuestas que incumpla la regla.
"""
import pytest

from src.estudiantes import supresion as sp


# ── regla primaria ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("k,n,ok", [(1, 20, False), (0, 20, False), (19, 20, False),
                                    (17, 20, True), (3, 20, True), (2, 20, False),
                                    (3, 6, True), (3, 5, False), (0, 0, False)])
def test_proporcion_publicable(k, n, ok):
    assert sp.proporcion_publicable(k, n) is ok


def test_min_casos_es_tres():
    assert sp.MIN_CASOS == 3


def test_las_bandas_son_todo_o_nada():
    assert sp.partes_publicables((10, 5, 4, 3))
    assert not sp.partes_publicables((10, 5, 4, 0))     # una banda vacía tumba todas
    assert not sp.partes_publicables((10, 5, 2, 3))


def test_union_vacia_es_segura():
    assert sp.union_segura((0, 0))
    assert not sp.union_segura((1, 9))
    assert sp.union_segura((3, 9))


# ── jerarquía sintética ────────────────────────────────────────────────────
def _binario(k, n):
    return (k, n - k)


def test_una_celda_con_k_1_se_suprime():
    jer = sp.jerarquia(celdas=["A|6", "A|7"], colegios=["A"], grados=["6", "7"],
                       con_resto=False)
    partes = {sp.atomo_celda("A|6"): _binario(1, 20), sp.atomo_celda("A|7"): _binario(8, 20)}
    sup = sp.suprimir(jer, partes)
    assert sp.CELDA("A|6") in sup


@pytest.mark.parametrize("k", [0, 19])
def test_k_cero_y_k_n_menos_1_se_suprimen(k):
    jer = sp.jerarquia(celdas=["A|6"], colegios=["A"], grados=["6"], con_resto=False)
    sup = sp.suprimir(jer, {sp.atomo_celda("A|6"): _binario(k, 20)})
    assert sp.CELDA("A|6") in sup
    assert sp.NIVEL in sup                          # el nivel es la misma celda


def test_un_grado_con_una_sola_celda_oculta_oculta_una_segunda():
    # Grado 6 = A|6 + B|6 + C|6. A|6 cae por k=1; sin más, 6 − B − C = A.
    celdas = ["A|6", "B|6", "C|6"]
    jer = sp.jerarquia(celdas=celdas, colegios=["A", "B", "C"], grados=["6"],
                       con_resto=False)
    partes = {sp.atomo_celda("A|6"): _binario(1, 20),
              sp.atomo_celda("B|6"): _binario(6, 30),
              sp.atomo_celda("C|6"): _binario(5, 15)}
    sup = sp.suprimir(jer, partes)
    assert sp.CELDA("A|6") in sup
    assert sp.CELDA("C|6") in sup                   # la hermana más pequeña
    assert sp.CELDA("B|6") not in sup
    assert sp.fugas(jer, partes, sp.publicados(jer, sup)) == []


def test_resto_con_k_2_oculta_el_colegio_mas_pequeno():
    # Nivel = A + B + C (colegios sin celdas) + R; R con k = 2.
    jer = sp.jerarquia(celdas=[], colegios=["A", "B", "C"], grados=[], con_resto=True)
    partes = {sp.atomo_colegio("A"): _binario(10, 60),
              sp.atomo_colegio("B"): _binario(5, 25),
              sp.atomo_colegio("C"): _binario(8, 40),
              sp.RESTO: _binario(2, 15)}
    sup = sp.suprimir(jer, partes)
    assert sp.COLEGIO("B") in sup
    assert sp.COLEGIO("A") not in sup and sp.COLEGIO("C") not in sup
    assert sp.NIVEL not in sup
    assert sp.fugas(jer, partes, sp.publicados(jer, sup)) == []


def test_dos_celdas_ocultas_con_union_k_1_obligan_a_ocultar_otra():
    celdas = ["A|6", "B|6", "C|6", "D|6"]
    jer = sp.jerarquia(celdas=celdas, colegios=["A", "B", "C", "D"], grados=["6"],
                       con_resto=False)
    partes = {sp.atomo_celda("A|6"): _binario(1, 20),
              sp.atomo_celda("B|6"): _binario(0, 12),
              sp.atomo_celda("C|6"): _binario(6, 30),
              sp.atomo_celda("D|6"): _binario(5, 18)}
    sup = sp.suprimir(jer, partes)
    assert {sp.CELDA("A|6"), sp.CELDA("B|6"), sp.CELDA("D|6")} <= sup
    assert sp.CELDA("C|6") not in sup
    assert sp.fugas(jer, partes, sp.publicados(jer, sup)) == []


def test_bandas_todo_o_nada_y_por_margen():
    # Grado 6 con tres celdas; A|6 tiene una banda con 1 caso: se oculta entera,
    # y el margen obliga a ocultar otra para que la resta no la devuelva.
    jer = sp.jerarquia(celdas=["A|6", "B|6", "C|6"], colegios=["A", "B", "C"],
                       grados=["6"], con_resto=False)
    partes = {sp.atomo_celda("A|6"): (10, 5, 4, 1),
              sp.atomo_celda("B|6"): (20, 8, 6, 6),
              sp.atomo_celda("C|6"): (12, 4, 3, 3)}
    sup = sp.suprimir(jer, partes)
    assert sp.CELDA("A|6") in sup and sp.CELDA("C|6") in sup
    assert sp.fugas(jer, partes, sp.publicados(jer, sup)) == []


def test_la_resta_en_dos_pasos_se_detecta_y_se_corrige():
    # Tabla 2×2 con márgenes: si solo se oculta A|6 (k=1), A|6 sale de
    # «grado 6 − B|6» y de «colegio A − A|7». La auditoría exacta lo ve.
    celdas = ["A|6", "A|7", "B|6", "B|7"]
    jer = sp.jerarquia(celdas=celdas, colegios=["A", "B"], grados=["6", "7"],
                       con_resto=False)
    partes = {sp.atomo_celda("A|6"): _binario(1, 20),
              sp.atomo_celda("A|7"): _binario(6, 20),
              sp.atomo_celda("B|6"): _binario(5, 20),
              sp.atomo_celda("B|7"): _binario(7, 20)}
    solo_primaria = {sp.CELDA("A|6")}
    assert sp.fugas(jer, partes, sp.publicados(jer, solo_primaria))
    sup = sp.suprimir(jer, partes)
    assert sp.fugas(jer, partes, sp.publicados(jer, sup)) == []
    assert sp.NIVEL not in sup


def test_el_resto_dentro_de_colegios_con_celdas_no_queda_expuesto():
    # Los colegios A y B tienen celdas; R (k=2) no se puede proteger ocultando
    # solo el agregado del colegio, porque sus celdas lo reconstruyen.
    celdas = ["A|6", "A|7", "B|6", "B|7"]
    jer = sp.jerarquia(celdas=celdas, colegios=["A", "B"], grados=["6", "7"],
                       con_resto=True)
    partes = {sp.atomo_celda("A|6"): _binario(4, 20),
              sp.atomo_celda("A|7"): _binario(6, 20),
              sp.atomo_celda("B|6"): _binario(5, 20),
              sp.atomo_celda("B|7"): _binario(7, 20),
              sp.RESTO: _binario(2, 12)}
    sup = sp.suprimir(jer, partes)
    assert sp.fugas(jer, partes, sp.publicados(jer, sup)) == []


def test_fugas_detecta_una_union_pequena_derivable():
    jer = sp.jerarquia(celdas=["A|6", "B|6", "C|6"], colegios=["A", "B", "C"],
                       grados=["6"], con_resto=False)
    partes = {sp.atomo_celda("A|6"): _binario(1, 20),
              sp.atomo_celda("B|6"): _binario(0, 20),
              sp.atomo_celda("C|6"): _binario(6, 20)}
    pub = sp.publicados(jer, {sp.CELDA("A|6"), sp.CELDA("B|6"),
                              sp.COLEGIO("A"), sp.COLEGIO("B")})
    fugas = sp.fugas(jer, partes, pub)
    assert frozenset({sp.atomo_celda("A|6"), sp.atomo_celda("B|6")}) in fugas


def test_contraste_aplica_la_regla_a_los_dos_terciles():
    assert sp.contraste_publicable(dict(k_bajo=5, n_bajo=30, k_alto=4, n_alto=30))
    assert not sp.contraste_publicable(dict(k_bajo=5, n_bajo=30, k_alto=1, n_alto=30))
    assert not sp.contraste_publicable(dict(k_bajo=28, n_bajo=30, k_alto=4, n_alto=30))
