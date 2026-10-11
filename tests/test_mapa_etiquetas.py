"""Las etiquetas del mapa no se superponen: ni entre sí ni con los círculos."""
import itertools

from src.geo import etiquetas as et


def _item(codigo, x, y, nombre="Colegio", radio=8):
    return et.Item(codigo, x, y, nombre, radio)


def test_un_punto_aislado_usa_la_posicion_preferida():
    pos = et.colocar([_item("a", 0, 0)])
    assert pos == {"a": "top right"}


def test_dos_puntos_cercanos_no_comparten_cuadro():
    items = [_item("a", 0, 0, "Colegio uno"), _item("b", 6, 2, "Colegio dos")]
    pos = et.colocar(items)
    cajas = [et.caja(i, pos[i.codigo]) for i in items if pos[i.codigo]]
    assert len(cajas) == 2
    assert not et.se_cruzan(cajas[0], cajas[1])


def test_lo_que_no_cabe_se_oculta_y_lo_colocado_no_se_cruza():
    items = [_item(c, 0, 0, "Colegio Nacional Diversificado") for c in "abcdefgh"]
    pos = et.colocar(items)
    assert None in pos.values()                     # no caben ocho en el mismo sitio
    colocados = [et.caja(i, pos[i.codigo]) for i in items if pos[i.codigo]]
    for a, b in itertools.combinations(colocados, 2):
        assert not et.se_cruzan(a, b)


def test_la_etiqueta_no_tapa_un_circulo_vecino():
    items = [_item("a", 0, 0, "A"), _item("b", 40, 0, "B", radio=10)]
    pos = et.colocar(items)
    caja_a = et.caja(items[0], pos["a"])
    vecino = et.caja_circulo(items[1])
    assert pos["a"] is None or not et.se_cruzan(caja_a, vecino)


def test_el_orden_de_entrada_es_la_prioridad():
    items = [_item("primero", 0, 0, "Colegio uno"), _item("segundo", 2, 1, "Colegio dos")]
    pos = et.colocar(items)
    assert pos["primero"] == "top right"


def test_sin_items_no_hay_posiciones():
    assert et.colocar([]) == {}
