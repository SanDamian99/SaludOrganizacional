"""Cuidadores 360 · informes del colegio y de la Secretaría y resumen de una página."""
import pandas as pd
import pytest

from src.cuidadores import alertas
from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.ui.views import cuidadores_informe as inf
from src.ui.views import estudiantes_alertas as va
from tests import cuidadores_comunidad_datos as datos
from tests import cuidadores_sinteticos as cs


@pytest.fixture(scope="module")
def ac():
    return datos.con_senales(datos.preparado())


def _limpio(html: str) -> None:
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in html
    assert "casos" not in html.lower() or "casos o no casos" in html.lower()
    assert "suicid" not in html.lower()


def test_informe_del_colegio(ac):
    html = inf.informe_colegio_html(ac, "LauV")
    _limpio(html)
    assert "LauV" in html and cc.TITULO_RUTA in html
    assert cc.ESTADO_GENERAL_COLEGIO in html
    assert cc.ALERTAS[cat.AUTOLESION].nombre not in html
    assert "Prioridad" in html                          # LauV en «Prioridad» de ánimo
    for otro in ("JJC", "SJMEB"):
        assert otro not in html                         # un rector no ve a los demás


def test_un_colegio_sin_cifras_no_tiene_informe(ac):
    with pytest.raises(ValueError):
        inf.informe_colegio_html(ac, "CdP")


def test_informe_de_la_secretaria(ac):
    html = inf.informe_secretaria_html(ac)
    _limpio(html)
    assert cc.ALERTAS[cat.AUTOLESION].nombre in html            # solo el total
    assert cc.NOTA_SOLO_MUNICIPIO in html
    assert "Por colegio" in html and "Por grado" in html
    tabla = inf.vc.tabla_secretaria_html(ac)
    assert tabla and cc.ALERTAS[cat.AUTOLESION].nombre_corto not in tabla


@pytest.mark.parametrize("rol", ["colegio", "familia", "municipio"])
def test_resumen_de_una_pagina_por_rol(ac, rol):
    html = inf.informe_una_pagina_html(ac, rol, {})
    _limpio(html)
    assert cc.TITULO_RUTA in html
    if rol == "familia":
        caja = html.split("<body>")[1].split("Lo más importante")[0]
        assert cc.AUTOCUIDADO_FAMILIA in caja and "%" not in caja
        for palabra in ("daño", "autoles", "muerte"):
            assert palabra not in html.lower()


def _peor_caso(ac):
    """Municipio sin filtro, con todos los colegios y grados en «Prioridad»."""
    colegios = [f"Colegio número {i:02d}" for i in range(14)]
    filas = [datos._r("animo", "total", "Todos", 25.0, alertas.REFERENCIA, n=700)]
    filas += [datos._r("animo", "Colegio", c, 40.0, alertas.PRIORIDAD) for c in colegios]
    filas += [datos._r("animo", "Grado", g, 40.0, alertas.PRIORIDAD) for g in cat.GRADOS_ESTUDIO]
    filas += [datos._r("autolesion", "total", "Todos", 11.0, alertas.REFERENCIA, n=700)]
    return datos.con_senales(ac, alertas.ordenar(pd.DataFrame(filas,
                                                              columns=alertas.COLUMNAS_TABLA)))


def test_el_peor_caso_recorta_las_listas(ac):
    html = inf.informe_una_pagina_html(_peor_caso(ac), "municipio", {})
    assert f"y {14 - va.MAX_NOMBRES_PAGINA} más" in html


@pytest.mark.parametrize("rol,filtros", [("municipio", {}), ("colegio", {"colegio": "LauV"}),
                                         ("familia", {"grado": "Quinto"})])
def test_el_peor_caso_cabe_en_una_pagina(ac, rol, filtros):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML
    html = inf.informe_una_pagina_html(_peor_caso(ac), rol, filtros)
    assert len(HTML(string=html).render().pages) == 1
    assert inf.a_pdf(html)[:4] == b"%PDF"


def test_sin_weasyprint_el_pdf_es_none(monkeypatch):
    import builtins
    original = builtins.__import__

    def falla(nombre, *a, **k):
        if nombre == "weasyprint":
            raise ImportError("sin weasyprint")
        return original(nombre, *a, **k)
    monkeypatch.setattr(builtins, "__import__", falla)
    assert inf.a_pdf("<p>x</p>") is None


# ── generador de informes: audita antes de escribir ────────────────────────
def test_el_generador_aborta_sin_escribir_si_la_auditoria_falla(tmp_path, monkeypatch):
    from scripts import generar_informes_cuidadores as gen
    from src.cuidadores import publicar
    monkeypatch.setattr(gen, "cargar", lambda: (datos.preparado(), "archivos"))
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["cuidador · algo delata"])
    assert gen.main([str(tmp_path)]) == 2
    assert list(tmp_path.iterdir()) == []


def test_el_generador_escribe_si_la_auditoria_pasa(tmp_path, monkeypatch):
    from scripts import generar_informes_cuidadores as gen
    monkeypatch.setattr(gen, "cargar", lambda: (datos.preparado(), "archivos"))
    assert gen.main([str(tmp_path)]) == 0
    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert "informe_cuidadores_secretaria.html" in nombres
    assert "informe_cuidadores_LauV.html" in nombres
    for p in tmp_path.iterdir():
        _limpio(p.read_text(encoding="utf-8"))
