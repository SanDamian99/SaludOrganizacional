"""Vista por ítem y grupo de Docentes: cálculo, privacidad y pantalla."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.docentes import catalogo as cat
from src.docentes import enunciados
from src.docentes import scoring as doc_scoring
from src.ui import docentes_items as di
from tests import docentes_sinteticos as sint


def test_todo_item_del_catalogo_tiene_enunciado():
    faltan = [i for d in cat.DIMENSIONES for i in d.items if i not in enunciados.ENUNCIADOS]
    assert not faltan
    assert enunciados.INVERTIDOS <= set(enunciados.ENUNCIADOS)


def test_escala_de_un_item():
    assert di.escala_item(cat.por_clave("Descon")) == (1, 5)          # media: la de la dimensión
    assert di.escala_item(cat.por_clave("PSS")) == (0, 4)             # suma 0-40 en 10 ítems
    assert di.escala_item(cat.por_clave("ISTAS_Exig")) == (0, 4)      # suma 0-24 en 6 ítems


def test_orientado_pone_verde_en_lo_favorable():
    assert di.orientado(5, cat.por_clave("Descon")) == 100            # mayor = mejor
    assert di.orientado(1, cat.por_clave("BTA")) == 100               # burnout mínimo = favorable
    assert di.orientado(5, cat.por_clave("BTA")) == 0
    assert di.orientado(float("nan"), cat.por_clave("BTA")) is None


def test_medias_por_item_y_celdas_pequenas_en_blanco():
    df = sint.docentes()
    n = doc_scoring.normalizar_codificacion(df)
    dim = cat.por_clave("Descon")
    grupo = df[sint.COL_COLEGIO]
    medias, _ns = di.tabla_items(n, dim, grupo, ["Grande A", sint.COLEGIO_PEQUENO])
    assert list(medias.index) == list(dim.items)
    esperado = pd.to_numeric(n["Descon1"]).mean()
    assert medias.loc["Descon1", di.TODOS] == pytest.approx(esperado)
    assert medias.loc["Descon1", "Grande A"] == pytest.approx(
        pd.to_numeric(n.loc[grupo == "Grande A", "Descon1"]).mean())
    assert medias[sint.COLEGIO_PEQUENO].isna().all()                  # 5 docentes: sin cifra


def test_el_desplazamiento_del_bat_se_aplica_al_item():
    df = sint.docentes()
    n = doc_scoring.normalizar_codificacion(df)
    dim = cat.por_clave("BTA_Agot")
    medias, _ = di.tabla_items(n, dim, None, [])
    assert medias.loc["BTA1", di.TODOS] == pytest.approx(pd.to_numeric(n["BTA1"]).mean() + 1)


def test_fondo_de_zonas_cubre_la_escala():
    for clave in ("BTA", "Descon", "ISTAS_Exig"):
        dim = cat.por_clave(clave)
        franjas = di.fondo_zonas(dim)
        assert franjas[0][0] == dim.escala[0] or dim.cortes
        assert {z for *_, z in franjas} <= {cat.ZONA_FAVORABLE, cat.ZONA_INTERMEDIA,
                                            cat.ZONA_VIGILAR}
    # Sin cortes y «mayor = peor», lo favorable queda a la izquierda.
    assert di.fondo_zonas(cat.por_clave("BLG_Som"))[0][2] == cat.ZONA_FAVORABLE
    assert di.fondo_zonas(cat.por_clave("Descon"))[0][2] == cat.ZONA_VIGILAR


def _pagina():
    from src.ui.dashboard import render_dashboard
    render_dashboard()


def _app():
    at = AppTest.from_function(_pagina, default_timeout=90)
    at.session_state["df"] = sint.docentes()
    return at.run()


def _elegir(at, clave):
    sel = next(s for s in at.selectbox if s.label == "Indicador:")
    sel.set_value(clave).run()


def test_la_seccion_por_item_se_dibuja_y_oculta_grupos_pequenos():
    at = _app()
    _elegir(at, "Descon")
    assert not at.exception
    textos = " ".join(m.value for m in at.markdown)
    assert "Resultado de cada ítem por grupo" in textos
    pies = " ".join(c.value for c in at.caption)
    assert f"{sint.COLEGIO_PEQUENO}=" not in pies                     # el de 5 no tiene columna
    assert any(s.label == "Agrupar por:" for s in at.selectbox)
    assert any(s.label == "Filtrar por (opcional):" for s in at.selectbox)


def test_agrupar_por_otro_criterio_y_filtrar_no_rompe():
    at = _app()
    _elegir(at, "BTA")
    agrupar = next(s for s in at.selectbox if s.label == "Agrupar por:")
    assert len(agrupar.options) >= 2
    otro = next(o for o in agrupar.options if o != agrupar.options[0])
    agrupar.set_value(otro).run()
    assert not at.exception
    filtro = next(s for s in at.selectbox if s.label == "Filtrar por (opcional):")
    criterio = next(o for o in filtro.options if o != di.SIN_FILTRO)
    filtro.set_value(criterio).run()
    assert not at.exception
    assert any(m.label.startswith(criterio) for m in at.multiselect)


def test_los_textos_nuevos_estan_en_la_pagina():
    at = _app()
    textos = " ".join([m.value for m in at.markdown] + [c.value for c in at.caption]
                      + [i.value for i in at.info])
    assert "va de 0 a 100" in textos
    assert "Zona favorable" in textos and "Zona a vigilar" in textos  # leyenda de colores
    assert "IC 95 %: rango donde probablemente" in textos
    assert "Cada barra cuenta cuántos docentes" in textos
    assert "Cuántos docentes hay en cada grupo" in textos
