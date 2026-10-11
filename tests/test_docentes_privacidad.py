"""
Privacidad del módulo Docentes (auditoría de relevancia, 10-oct-2026).

P1. Ninguna fila individual sale de la aplicación: no hay descarga de datos.
P2. Grupo mínimo de 10: un filtro que deja menos de 10 docentes muestra un
    mensaje fijo y ninguna cifra; el perfil y las comparaciones esconden las
    categorías y los grupos de menos de 10.
P3. El PDF nunca imprime un conteo menor de 10 ni deja deducirlo por resta.
"""
import pathlib

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.analysis import grupo_minimo as gm
from tests import docentes_sinteticos as sint

RAIZ = pathlib.Path(__file__).resolve().parents[1]


# ══ Funciones puras ═════════════════════════════════════════════════════════


@pytest.mark.parametrize("n,esperado", [(0, False), (9, False), (10, True), (479, True)])
def test_grupo_suficiente(n, esperado):
    assert gm.grupo_suficiente(n) is esperado


@pytest.mark.parametrize("n,texto", [(0, "<10"), (3, "<10"), (9, "<10"), (10, "10"),
                                     (1234, "1,234")])
def test_texto_n(n, texto):
    assert gm.texto_n(n) == texto


def test_conteos_sin_categorias_pequenas_salen_exactos():
    t = gm.conteos_protegidos(pd.Series(["A"] * 30 + ["B"] * 12))
    assert list(t["categoria"]) == ["A", "B"]
    assert list(t["texto"]) == ["30", "12"]
    assert t["visible"].all()


def test_dos_categorias_pequenas_se_enmascaran_sin_resta_posible():
    t = gm.conteos_protegidos(pd.Series(["A"] * 30 + ["B"] * 4 + ["C"] * 2))
    fila = dict(zip(t["categoria"], t["texto"]))
    assert fila == {"A": "30", "B": "<10", "C": "<10"}
    assert list(t["visible"]) == [True, False, False]


def test_una_sola_categoria_pequena_obliga_a_ocultar_otra():
    """Con el total a la vista, una sola oculta se deduce restando: se oculta otra más."""
    t = gm.conteos_protegidos(pd.Series(["A"] * 40 + ["B"] * 22 + ["C"] * 3 + [None] * 2))
    fila = dict(zip(t["categoria"], t["texto"]))
    assert fila["A"] == "40"
    assert fila["C"] == gm.MENOS_DE
    assert fila["B"] == gm.OCULTO and "22" not in fila["B"]
    assert list(t["visible"]) == [True, False, False]
    # Nunca aparece una cifra exacta menor de 10.
    for texto in t["texto"]:
        assert not (texto.isdigit() and int(texto) < 10)


def test_texto_conteos():
    s = pd.Series(["Mujer"] * 40 + ["Hombre"] * 22 + ["No binario"] * 3)
    texto = gm.texto_conteos(s)
    assert "Mujer: 40" in texto and "No binario: <10" in texto
    assert "22" not in texto and "3" not in texto.replace("<10", "")


def test_agrupar_numerica_por_decadas_para_la_edad():
    s = pd.Series([24, 25, 31, 39, 40, 58, None])
    r = gm.agrupar_numerica(s, ancho=10)
    assert list(r.dropna()) == ["20–29", "20–29", "30–39", "30–39", "40–49", "50–59"]
    assert r.isna().sum() == 1


def test_grupos_comparables_esconde_los_menores_de_10():
    agg = pd.DataFrame({"g": ["A", "B", "C", "D"], "mean": [1.0, 2.0, 3.0, 4.0],
                        "count": [30, 9, 10, 4]})
    visibles, ocultos = gm.grupos_comparables(agg, "g")
    assert list(visibles["g"]) == ["A", "C"]
    assert ocultos == ["B", "D"]


def test_grupos_comparables_con_un_solo_pequeno_oculta_otro():
    """Si solo B quedara fuera, su tamaño saldría restando del total."""
    agg = pd.DataFrame({"g": ["A", "B", "C"], "mean": [1.0, 2.0, 3.0], "count": [30, 9, 12]})
    visibles, ocultos = gm.grupos_comparables(agg, "g")
    assert list(visibles["g"]) == ["A"]
    assert sorted(ocultos) == ["B", "C"]


# ══ P1 · sin descarga de filas ══════════════════════════════════════════════


# ══ P2 · página con AppTest ═════════════════════════════════════════════════
def _pagina():
    from src.ui.dashboard import render_dashboard
    render_dashboard()


def _app():
    at = AppTest.from_function(_pagina, default_timeout=60)
    at.session_state["df"] = sint.docentes()
    return at.run()


def _todo_el_texto(at) -> str:
    partes = []
    for grupo in (at.markdown, at.caption, at.info, at.warning, at.error, at.success,
                  at.text, at.metric, at.sidebar.markdown, at.sidebar.text, at.sidebar.info):
        for e in grupo:
            partes.append(str(getattr(e, "value", "")))
            partes.append(str(getattr(e, "label", "")))
    return "\n".join(partes)


def test_sin_boton_de_descarga_csv_en_la_pagina():
    at = _app()
    assert not at.exception
    etiquetas = [getattr(b, "label", "") for b in at.get("download_button")]
    assert not [e for e in etiquetas if "CSV" in e or "datos" in e.lower()]


def test_filtrar_a_un_grupo_pequeno_muestra_solo_el_mensaje():
    at = _app()
    at.multiselect(key=f"filtro_{sint.COL_COLEGIO}").set_value([sint.COLEGIO_PEQUENO]).run()
    assert not at.exception
    assert any(gm.MENSAJE_GRUPO_PEQUENO in w.value for w in at.warning)
    assert not at.tabs
    assert not at.metric
    assert not at.get("plotly_chart")
    texto = _todo_el_texto(at)
    assert "Registros filtrados: <10" in texto
    assert f"{len(sint.docentes()[sint.docentes()[sint.COL_COLEGIO] == sint.COLEGIO_PEQUENO])} /" \
        not in texto


def test_el_pdf_tampoco_se_genera_para_un_grupo_pequeno():
    at = _app()
    at.multiselect(key=f"filtro_{sint.COL_COLEGIO}").set_value([sint.COLEGIO_PEQUENO]).run()
    boton = next(b for b in at.sidebar.button if "PDF" in b.label)
    boton.click().run()
    assert not at.exception
    assert any(gm.MENSAJE_GRUPO_PEQUENO in e.value for e in at.sidebar.error)
    assert not at.get("download_button")


def test_el_perfil_no_muestra_conteos_pequenos():
    """«No binario» tiene 3 personas: su cifra nunca aparece; sí «<10»."""
    from src.ui import dashboard as d
    df = sint.docentes()
    t = d.tabla_perfil(df[sint.COL_SEXO])
    fila = dict(zip(t["categoria"], t["texto"]))
    assert fila["No binario"] == gm.MENOS_DE
    assert fila["Mujer"] == str((df[sint.COL_SEXO] == "Mujer").sum())
    edad = d.tabla_perfil(df[sint.COL_EDAD], numerica=True, ancho=10)
    for texto in edad["texto"]:
        assert not (texto.isdigit() and int(texto) < 10)


def test_la_comparacion_por_grupo_esconde_los_pequenos():
    at = _app()
    at.selectbox(key="doc_comparar_por").set_value(sint.COL_COLEGIO).run()
    assert not at.exception
    pies = " ".join(c.value for c in at.caption)
    assert "Grande A" in pies and sint.COLEGIO_PEQUENO in pies
    assert f"{sint.COLEGIO_PEQUENO}=" not in pies
    assert "menos de 10" in pies


# ══ P3 · PDF ════════════════════════════════════════════════════════════════
def test_pdf_docentes_enmascara_el_sexo(monkeypatch):
    from src.reports import indicator_report as ir
    parrafos = []

    class _PDF:
        def __getattr__(self, nombre):
            return lambda *a, **k: None

        def add_paragraph(self, texto, *a, **k):
            parrafos.append(texto)

    ir.IndicatorReportBuilder(sint.docentes())._demographics(_PDF())
    texto = " ".join(parrafos)
    assert "No binario: <10" in texto
    assert "Hombre: " + gm.OCULTO in texto
    assert "No binario: 3" not in texto and "Hombre: 22" not in texto


@pytest.mark.parametrize("modulo,clase", [("src.reports.indicator_report",
                                           "IndicatorReportBuilder"),
                                          ("src.reports.report_builder", "ReportBuilder")])
def test_los_pdf_no_se_construyen_con_menos_de_10(modulo, clase):
    import importlib
    builder = getattr(importlib.import_module(modulo), clase)
    with pytest.raises(gm.GrupoPequeno, match="menos de 10"):
        builder(sint.docentes().head(9)).build_report()


def test_pdf_de_bienestar_sin_barras_de_menos_de_10():
    """Las barras del perfil del PDF (esquema BM) usan los conteos protegidos."""
    from src.reports import analytics as an
    df = sint.docentes()
    t = an.conteos_para_grafica(df, sint.COL_SEXO)
    fila = dict(zip(t["categoria"], t["texto"]))
    assert fila["No binario"] == gm.MENOS_DE and fila["Hombre"] == gm.OCULTO
    edad = an.conteos_para_grafica(df, sint.COL_EDAD)
    for texto in edad["texto"]:
        assert not (texto.isdigit() and int(texto) < 10)


def test_pdf_de_bienestar_compara_solo_grupos_de_10_o_mas():
    from src.reports import analytics as an
    df = sint.docentes()
    medias = an.medias_por_grupo(df[["PSS_T", "BTA_T"]], df[sint.COL_COLEGIO])
    assert set(medias.index) == {"Grande A", "Grande B"}
