"""Panel «Señales para actuar a tiempo» en la vista, los informes y el PDF (spec §5.4, §6)."""
import colorsys
import dataclasses
import io
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.core.colegios import COLEGIOS
from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.ui.views import estudiantes_alertas as va

P, T, R, S = ac.PRIORIDAD, ac.PRESENTE, ac.REFERENCIA, ac.SIN_ESTADO


def _r(alerta, agrupacion, grupo, pct=None, estado=S, n=60):
    return dict(alerta=alerta, agrupacion=agrupacion, grupo=grupo, n=n, pct=pct,
                ic_inf=None if pct is None else pct - 5,
                ic_sup=None if pct is None else pct + 5, estado=estado)


TABLA = [
    _r("malestar", "total", "Todos", 16.7, R, n=900),
    _r("malestar", "Colegio", "LauV", 25.0, P, n=400),
    _r("malestar", "Colegio", "JJC"),
    _r("malestar", "Grado", "Octavo", 30.0, P, n=150),
    _r("malestar", "Grado", "Sexto", 12.0, T, n=150),
    _r("malestar", "Colegio×Grado", "LauV|Octavo", 35.0, P, n=90),
    _r("malestar", "Colegio×Grado", "LauV|Sexto", 33.0, P, n=95),
    _r("malestar", "Colegio×Grado", "LauV|Noveno"),
    _r("desesperanza", "total", "Todos", 17.0, R, n=900),
    _r("desesperanza", "Colegio", "LauV", 20.0, T, n=400),
]


def _ns(filas=TABLA, nivel=cat.NIVEL_SECUNDARIA):
    return SimpleNamespace(nivel=nivel, alertas=pd.DataFrame(filas, columns=al.COLUMNAS_TABLA))


def test_frase_de_la_cifra():
    assert va.frase("malestar", 16.7) == "1 de cada 6 estudiantes muestra señales de malestar."
    assert va.frase("malestar", 40) == "4 de cada 10 estudiantes muestran señales de malestar."


def test_familia_solo_ve_malestar_y_sin_listas():
    s = va.senales(_ns(), "familia", {})
    assert [x.alerta for x in s] == ["malestar"]
    assert s[0].listas == ()
    assert s[0].que_hacer == ac.ALERTAS["malestar"].que_hacer["familia"]


def test_colegio_ve_las_dos_y_los_grados_en_prioridad():
    s = {x.alerta: x for x in va.senales(_ns(), "colegio", {})}
    assert set(s) == {"malestar", "desesperanza"}
    m = s["malestar"]
    assert m.estado == R and m.etiqueta_estado == "Para tener presente" and m.visible
    assert m.frase == "1 de cada 6 estudiantes muestra señales de malestar."
    assert m.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)),)


def test_dentro_de_un_colegio_los_grados_van_en_orden_canonico():
    s = va.senales(_ns(), "colegio", {"colegio": "LauV"})[0]
    assert s.estado == P
    assert s.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Sexto", "Octavo")),)


def test_el_municipio_ve_colegios_y_grados_en_prioridad():
    s = va.senales(_ns(), "municipio", {})[0]
    assert s.listas == ((ac.TITULO_COLEGIOS_PRIORIDAD, ("Laura Vicuña",)),
                        (ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)))


def test_un_grado_con_cifra_lleva_porcentaje_y_estado():
    s = va.senales(_ns(), "familia", {"grado": "Octavo"})[0]
    assert s.estado == P and s.pct == 30.0
    c = va.senales(_ns(), "colegio", {"colegio": "LauV", "grado": "Octavo"})[0]
    assert c.estado == P and c.frase.startswith("4 de cada 10")


@pytest.mark.parametrize("filtros", [{"colegio": "JJC"}, {"colegio": "LauV", "grado": "Noveno"},
                                     {"grado": "Noveno"}])
def test_sin_cifra_el_estado_es_neutro_y_va_el_texto_fijo(filtros):
    s = va.senales(_ns(), "colegio", filtros)[0]
    assert s.estado == S and s.etiqueta_estado == "Sin estado: cifras pequeñas"
    assert s.frase == ac.CIFRAS_PEQUENAS and s.pct is None and s.n is None


def test_el_panel_solo_usa_cifras_de_la_tabla():
    """Cada cifra de una señal es la de su fila; nada se calcula ni se cuenta aparte."""
    for filtros in ({}, {"colegio": "LauV"}, {"grado": "Octavo"}, {"colegio": "JJC"},
                    {"colegio": "LauV", "grado": "Sexto"}):
        for s in va.senales(_ns(), "municipio", filtros):
            f = va.fila(_ns(), s.alerta, filtros)
            if s.visible:
                assert (s.pct, s.ic_inf, s.ic_sup, s.n, s.estado) == \
                    (f["pct"], f["ic_inf"], f["ic_sup"], f["n"], f["estado"])
            else:
                assert f is None or pd.isna(f["pct"])
    assert {x.name for x in dataclasses.fields(va.Senal)} == {
        "alerta", "nombre", "estado", "frase", "que_hacer", "pct", "ic_inf", "ic_sup", "n",
        "listas"}


def test_las_explicaciones_son_solo_de_los_estados_que_aparecen():
    lista = va.senales(_ns(), "colegio", {})            # dos «referencia»
    assert va.explicaciones(lista) == [ac.QUE_ES_REFERENCIA]
    assert ac.QUE_ES_PRESENTE in va.explicaciones(va.senales(_ns(), "colegio", {"grado": "Sexto"}))
    assert va.explicaciones(va.senales(_ns(), "colegio", {"colegio": "JJC"})) == \
        [ac.QUE_ES_SIN_ESTADO]


def test_primaria_no_trae_desesperanza():
    assert [x.alerta for x in va.senales(_ns(nivel=cat.NIVEL_PRIMARIA), "colegio", {})] \
        == ["malestar"]


def test_sin_tabla_no_hay_panel():
    assert va.senales(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA), "colegio", {}) == []
    assert va.panel_html(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA), "colegio", {}) == ""


def _seccion(html):
    return html.split('<section class="senales')[1].split("</section>")[0]


def test_el_panel_html_no_alarma_ni_cuenta_casos():
    html = va.panel_html(_ns(), "colegio", {"colegio": "LauV"})
    sec = _seccion(html)
    assert ac.TITULO_PANEL in sec and ac.NO_ES_DIAGNOSTICO in sec and ac.NOTA_AZAR in sec
    assert "Prioridad" in sec and "casos" not in sec.lower()
    assert "#C0392B" not in sec.upper()


def test_el_recuadro_compacto_recorta_las_listas():
    filas = [_r("malestar", "total", "Todos", 16.7, R, n=900)]
    filas += [_r("malestar", "Colegio", c, 30.0, P) for _, c, _ in COLEGIOS]
    html = va.panel_html(_ns(filas), "municipio", {}, compacto=True)
    assert f"y {len(COLEGIOS) - va.MAX_NOMBRES_PAGINA} más" in html


def test_tabla_de_la_secretaria():
    html = va.tabla_secretaria_html(_ns())
    assert "Laura Vicuña" in html and "José Joaquín Casas" in html
    assert ac.CIFRAS_PEQUENAS_CORTO in html and "Total del municipio" in html
    assert ac.ESTADOS[S] in html and "casos" not in html.lower()


def _hls(color):
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def test_el_color_maximo_es_naranja_nunca_rojo():
    tono, _, saturacion = _hls(va.COLOR_PRIORIDAD)
    assert 25 <= tono * 360 <= 45 and saturacion > 0.5
    assert _hls(va.COLOR_PRESENTE)[2] < 0.2 and _hls(va.COLOR_SIN_ESTADO)[2] < 0.2
    for css in (va.CSS_INFORME, va.CSS_PAGINA):
        assert "#C0392B" not in css.upper() and va.COLOR_PRIORIDAD in css
