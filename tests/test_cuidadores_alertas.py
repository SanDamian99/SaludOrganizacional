"""Cuidadores 360 · señales del adulto por grupo y preparación para la comunidad (fase 4b)."""
import pandas as pd
import pytest

from src.cuidadores import alertas, comunidad, scoring
from src.cuidadores import catalog as cat
from src.estudiantes import alertas as al_est
from src.estudiantes import supresion
from tests import cuidadores_comunidad_datos as datos


@pytest.fixture(scope="module")
def ac():
    return datos.preparado()


def test_el_indicador_de_animo_es_la_fila_probable_de_la_epds():
    d = pd.DataFrame({"EPDS_Total": [5, 12, 14, 20], "EPDS_Autolesion": [0, 1, 0, 1]})
    t = scoring.sobre_cortes_cuidador(d)
    assert alertas.INDICADOR_PROBABLE in set(t["indicador"])
    assert alertas.fila_corte(t, cat.ANIMO)["n"] == 4


def test_la_autolesion_solo_tiene_fila_del_total(ac):
    t = ac.cuidador.alertas
    auto = t[t["alerta"] == cat.AUTOLESION]
    assert len(auto) == 1 and auto.iloc[0]["agrupacion"] == alertas.TOTAL


def test_animo_por_colegio_grado_y_celda(ac):
    t = ac.cuidador.alertas
    animo = t[t["alerta"] == cat.ANIMO]
    assert set(animo["agrupacion"]) == {alertas.TOTAL, "Colegio", "Grado", "Colegio×Grado"}
    assert set(animo.loc[animo["agrupacion"] == "Colegio", "grupo"]) == \
        set(ac.cuidador.subgrupos["Colegio"])


def test_sin_casos_nunca(ac):
    assert "casos" not in ac.cuidador.alertas.columns
    assert list(ac.cuidador.alertas.columns) == alertas.COLUMNAS_TABLA


def test_el_porcentaje_es_el_de_los_cortes_ya_suprimidos(ac):
    t = ac.cuidador.alertas
    for _, f in t.iterrows():
        if f["agrupacion"] == alertas.TOTAL:
            fuente = ac.cuidador
        else:
            fuente = ac.cuidador.subgrupos[f["agrupacion"]][f["grupo"]]
        esperado = alertas.fila_corte(fuente.cortes, f["alerta"])
        assert esperado["n"] == f["n"]
        assert (esperado["pct"] is None) == pd.isna(f["pct"])


def test_el_estado_solo_donde_hay_porcentaje(ac):
    t = ac.cuidador.alertas
    sin = t[t["pct"].isna()]
    assert (sin["estado"] == alertas.SIN_ESTADO).all()
    con = t[t["pct"].notna() & (t["agrupacion"] != alertas.TOTAL)]
    total = t[(t["agrupacion"] == alertas.TOTAL) & (t["alerta"] == cat.ANIMO)].iloc[0]
    for _, f in con.iterrows():
        assert f["estado"] == al_est.estado(f["pct"], f["n"], total["pct"], total["n"])


def test_toda_cifra_publicada_cumple_la_regla_de_tres():
    """Recalculado desde los datos: cada % de ánimo publicado tiene de 3 a n − 3 casos."""
    a = datos.analisis().cuidador
    prep = comunidad.preparar(datos.analisis()).cuidador
    for _, f in prep.alertas.dropna(subset=["pct"]).iterrows():
        if f["agrupacion"] == alertas.TOTAL:
            filas = a.datos.loc[a.base.nivel]
        elif f["agrupacion"] == "Colegio×Grado":
            filas = a.datos.loc[a.base.celdas[f["grupo"]]]
        else:
            filas = a.datos.loc[getattr(a.base, {"Colegio": "colegios",
                                                 "Grado": "grados"}[f["agrupacion"]])[f["grupo"]]]
        col = cat.ALERTAS[f["alerta"]].columna
        v = filas[col].dropna()
        assert supresion.proporcion_publicable(int(v.sum()), len(v))


def test_preparar_no_toca_el_analisis_original():
    original = datos.analisis()
    claves = {g: set(s.cortes["clave"]) for g, s in original.cuidador.subgrupos["Colegio"].items()}
    comunidad.preparar(original)
    for g, s in original.cuidador.subgrupos["Colegio"].items():
        assert set(s.cortes["clave"]) == claves[g]
    assert any("EPDS_Autolesion" in c for c in claves.values())


def test_preparar_quita_la_autolesion_de_todo_grupo_y_la_ola_de_la_muestra(ac):
    for a in ac.marcos.values():
        assert "ola" not in a.muestra
        for grupos in a.subgrupos.values():
            for s in grupos.values():
                assert "EPDS_Autolesion" not in set(s.cortes["clave"])
    assert "EPDS_Autolesion" in set(ac.cuidador.cortes["clave"])
    assert ac.items_apq.empty and ac.items_estres.empty


def test_preparar_rechaza_la_vista_de_una_ola():
    a = datos.analisis()
    a.ola = "2026"
    with pytest.raises(ValueError):
        comunidad.preparar(a)


def test_el_orden_es_canonico():
    t = datos.tabla_senales()
    assert list(t["alerta"]).index(cat.AUTOLESION) == len(t) - 1
    grados = list(t.loc[(t["alerta"] == cat.ANIMO) & (t["agrupacion"] == "Grado"), "grupo"])
    assert grados == ["Quinto", "Sexto"]
