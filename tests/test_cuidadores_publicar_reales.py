"""
Cuidadores 360 · publicación, vista e informes con el formulario real (se omite sin él).

Solo se comparan agregados. Ningún mensaje de fallo muestra un valor individual:
las comprobaciones cuentan (`assert n == 0`), nunca listan filas.
"""
import json
import re

import pytest

from src.cuidadores import alertas, comunidad, ingest, pipeline, publicar
from src.cuidadores import catalog as cat
from src.estudiantes import supresion

CLAVE = b"clave-de-prueba-solo-para-tests-0001"
RUTA = pipeline.localizar_formulario()
pytestmark = pytest.mark.skipif(RUTA is None, reason="sin el formulario real de cuidadores")


@pytest.fixture(scope="module")
def ac():
    return comunidad.preparar(pipeline.analizar(ingest.cargar(RUTA, k=CLAVE), n_boot=50))


@pytest.fixture(scope="module")
def filas(ac):
    return publicar.aplanar(ac)


def test_el_lote_real_pasa_las_guardas_y_la_auditoria(ac, filas):
    publicar.verificar(filas)
    assert len(publicar.verificar_restas(ac)) == 0


def test_el_lote_real_no_trae_identificadores_ni_conteos(filas):
    texto = json.dumps(filas, ensure_ascii=False, default=str)
    assert len(re.findall(r'"[ECN][0-9a-f]{8}"', texto)) == 0
    assert len(re.findall(r"\b3\d{9}\b", texto)) == 0
    assert sum(1 for f in filas if set(f["detalle"]) & {"casos", "k_bajo", "k_alto"}) == 0
    assert sum(1 for f in filas if f["n"] < cat.MIN_GROUP_N) == 0


def test_el_lote_real_no_publica_nada_por_ola(filas):
    assert sum(1 for f in filas if "ola" in (f["detalle"].get("muestra") or {})) == 0
    assert sum(1 for f in filas if "por_ola" in (f["detalle"].get("ingesta") or {})) == 0


def test_la_autolesion_real_solo_en_el_total(filas):
    propias = [f for f in filas if f["clave"] in ("EPDS_Autolesion", cat.AUTOLESION)]
    assert len(propias) == 2
    assert sum(1 for f in propias if f["agrupacion"] != "total") == 0


def test_cada_grupo_real_tiene_10_o_mas_cuidadores_distintos(ac):
    for a in ac.marcos.values():
        for idx in [*a.base.celdas.values(), *a.base.colegios.values(),
                    *a.base.grados.values()]:
            assert a.datos.loc[idx, "ID_cuidador"].nunique() >= cat.MIN_GROUP_N


def test_cada_animo_real_publicado_cumple_la_regla_de_tres(ac):
    a = ac.cuidador
    malas = 0
    for _, f in a.alertas.dropna(subset=["pct"]).iterrows():
        if f["agrupacion"] == alertas.TOTAL:
            idx = a.base.nivel
        elif f["agrupacion"] == "Colegio×Grado":
            idx = a.base.celdas[f["grupo"]]
        elif f["agrupacion"] == "Colegio":
            idx = a.base.colegios[f["grupo"]]
        else:
            idx = a.base.grados[f["grupo"]]
        v = a.datos.loc[idx, cat.ALERTAS[f["alerta"]].columna].dropna()
        malas += not supresion.proporcion_publicable(int(v.sum()), len(v))
    assert malas == 0


def test_la_vista_y_los_informes_reales_se_arman(ac):
    from src.ui.views import cuidadores_comunidad as vc
    from src.ui.views import cuidadores_informe as inf
    for rol in ("colegio", "familia", "municipio"):
        assert 0 < len(vc.tarjetas(ac, rol, {})) <= 5
    html = inf.informe_secretaria_html(ac)
    for colegio in vc.grupos(ac, "Colegio"):
        html += inf.informe_colegio_html(ac, colegio)
    assert len(re.findall(r"\b[CN][0-9a-f]{8}\b", html)) == 0


def test_el_resumen_real_del_municipio_cabe_en_una_pagina(ac):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML
    from src.ui.views import cuidadores_informe as inf
    html = inf.informe_una_pagina_html(ac, "municipio", {})
    assert len(HTML(string=html).render().pages) == 1
