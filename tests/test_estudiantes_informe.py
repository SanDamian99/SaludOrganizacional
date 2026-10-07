"""
Pruebas de los informes imprimibles de Estudiantes 360 (por colegio y Secretaría).

Mismas garantías que la vista comunidad: nada individual, ningún grupo pequeño,
textos del catálogo y cifras idénticas desde los archivos y desde la corrida
publicada.
"""
from datetime import date

import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring
from src.ui.views import estudiantes_informe as inf
from tests.test_estudiantes_comunidad import (COLEGIO_PEQUENO, GRADO_PEQUENO,
                                              NOMBRE_SENTINELA, _formulario)

COLEGIO = "LauV"


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    a = pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)
    return {cat.NIVEL_SECUNDARIA: a}


@pytest.fixture(scope="module")
def publicado(analisis):
    filas = publicar.aplanar(analisis)
    publicar.verificar(filas)
    return {cat.NIVEL_SECUNDARIA: lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)}


@pytest.fixture(scope="module", params=["archivos", "publicado"])
def fuente(request, analisis, publicado):
    return analisis if request.param == "archivos" else publicado


def test_solo_hay_informe_de_colegios_con_base_suficiente(fuente):
    codigos = inf.colegios_con_informe(fuente)
    assert codigos == [COLEGIO]


def test_un_colegio_pequeno_no_tiene_informe(fuente):
    with pytest.raises(ValueError):
        inf.informe_colegio_html(fuente, "DiosCh")


def test_informe_del_colegio_trae_lo_acordado(fuente):
    html = inf.informe_colegio_html(fuente, COLEGIO, fecha=date(2026, 10, 1))
    assert "Laura Vicuña" in html
    assert "1 de octubre de 2026" in html
    assert "window.print()" in html and "Guardar como PDF" in html
    assert "Municipio" in html
    for nombre, _ in cat.RUTA_ATENCION:
        assert nombre in html
    assert "tamizaje de grupo" in html


def test_informe_del_colegio_no_filtra_nombres_ni_grupos_pequenos(fuente):
    html = inf.informe_colegio_html(fuente, COLEGIO)
    assert NOMBRE_SENTINELA not in html
    assert "Diosa Chía" not in html and "DiosCh" not in html
    assert GRADO_PEQUENO not in html


def test_el_colegio_usa_las_acciones_del_rol_colegio(fuente):
    html = inf.informe_colegio_html(fuente, COLEGIO)
    for m in cat.MENSAJES.values():
        assert m.accion_municipio not in html or m.accion_municipio == m.accion_colegio


def test_informe_de_secretaria_compara_colegios_sin_grupos_pequenos(fuente):
    html = inf.informe_secretaria_html(fuente)
    assert "Informe para la Secretaría" in html
    assert "Laura Vicuña" in html
    assert "Diosa Chía" not in html and GRADO_PEQUENO not in html
    assert NOMBRE_SENTINELA not in html
    assert "Se compara, no se ranquea" in html


def _tablas(html: str) -> list[str]:
    return [t.split("</table>")[0] for t in html.split('<table class="comparativa">')[1:]]


def test_las_cifras_son_las_mismas_desde_archivos_y_publicado(analisis, publicado):
    # La tarjeta por sexo solo existe con datos crudos (la corrida publicada no
    # trae ese cruce, igual que en la vista); las tablas sí deben coincidir.
    a = inf.informe_secretaria_html(analisis, fecha=date(2026, 9, 28))
    b = inf.informe_secretaria_html(publicado, fecha=date(2026, 9, 28))
    assert _tablas(a) and _tablas(a) == _tablas(b)


def test_comparar_usa_el_margen_de_error():
    grupo = dict(pct=30.0, ic_inf=25.0, ic_sup=35.0)
    assert inf.comparar(grupo, dict(pct=20.0)) == "mayor"
    assert inf.comparar(grupo, dict(pct=40.0)) == "menor"
    assert inf.comparar(grupo, dict(pct=27.0)) == "similar"
    assert inf.comparar({}, dict(pct=27.0)) == ""


def test_sin_datos_no_hay_informe_de_secretaria():
    with pytest.raises(ValueError):
        inf.informe_secretaria_html({})


def test_nombre_de_colegio_desconocido_devuelve_el_codigo():
    assert ingest.nombre_colegio("JJC") == "José Joaquín Casas"
    assert ingest.nombre_colegio("XYZ") == "XYZ"


# ══ Resumen de una página (PDF) ═════════════════════════════════════════════
def _f(colegio="Todos", grado="Todos"):
    return {"nivel": cat.NIVEL_SECUNDARIA, "colegio": colegio, "grado": grado}


@pytest.mark.parametrize("rol", list(cat.ROLES))
def test_resumen_de_una_pagina_no_filtra_nada_individual(fuente, rol):
    a = fuente[cat.NIVEL_SECUNDARIA]
    html = inf.informe_una_pagina_html(a, rol, _f())
    assert NOMBRE_SENTINELA not in html
    assert "Diosa Chía" not in html and GRADO_PEQUENO not in html
    for nombre, _ in cat.RUTA_ATENCION:
        assert nombre in html
    assert cat.ROLES[rol] in html


def test_resumen_de_familia_sin_ideacion(fuente):
    a = fuente[cat.NIVEL_SECUNDARIA]
    html = inf.informe_una_pagina_html(a, "familia", _f())
    assert cat.MENSAJES["ideacion"].titulo not in html


def test_resumen_de_un_colegio_se_compara_con_el_municipio(fuente):
    a = fuente[cat.NIVEL_SECUNDARIA]
    html = inf.informe_una_pagina_html(a, "colegio", _f(colegio=COLEGIO))
    assert "Laura Vicuña" in html and "Municipio" in html
    assert "Parecido al municipio" in html or "que en el municipio" in html


def test_resumen_de_un_grupo_pequeno_lo_explica_sin_cifras(analisis):
    a = analisis[cat.NIVEL_SECUNDARIA]
    html = inf.informe_una_pagina_html(a, "colegio", _f(grado=GRADO_PEQUENO))
    assert "menos de 10 estudiantes" in html
    assert "Lo más importante" not in html


def test_el_resumen_cabe_en_una_pagina_de_pdf(fuente):
    pytest.importorskip("weasyprint")
    a = fuente[cat.NIVEL_SECUNDARIA]
    pdf = inf.a_pdf(inf.informe_una_pagina_html(a, "colegio", _f(colegio=COLEGIO)))
    assert pdf and pdf.startswith(b"%PDF")
    from weasyprint import HTML
    doc = HTML(string=inf.informe_una_pagina_html(a, "colegio", _f(colegio=COLEGIO))).render()
    assert len(doc.pages) == 1


def test_la_vista_ya_no_ofrece_markdown():
    import inspect
    from src.ui.views import estudiantes_comunidad as vc
    fuente_vista = inspect.getsource(vc._boton_una_pagina) + inspect.getsource(vc.render_comunidad)
    assert "text/markdown" not in fuente_vista
