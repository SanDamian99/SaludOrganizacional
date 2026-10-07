"""Alertas de punta a punta sin red: pipeline → publicar → leer (spec §5.4 y §7)."""
import os
import random

import pandas as pd
import pytest

from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring, supresion
from tests.test_alertas import CONFIGURACIONES, _datos_config
from tests.test_estudiantes_comunidad import GRADO_PEQUENO, _formulario


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)


@pytest.fixture(scope="module")
def primaria():
    raw = _formulario()
    raw = raw.drop(columns=[c for c in raw.columns if c.startswith("RCADS")])
    bruto, _ = ingest.cargar(raw)
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_PRIMARIA, n_boot=20)


@pytest.fixture(scope="module", params=range(len(CONFIGURACIONES)))
def config(request):
    nivel, conteos = CONFIGURACIONES[request.param]
    return nivel, pipeline.analizar(_datos_config(nivel, conteos, 5), nivel, n_boot=5)


# ══ Pipeline ════════════════════════════════════════════════════════════════
def test_el_analisis_trae_las_alertas_por_grupo(analisis):
    t = analisis.alertas
    assert list(t.columns) == al.COLUMNAS_TABLA and "casos" not in t.columns
    assert set(t["alerta"]) == {"malestar", "desesperanza"}
    assert t[t["agrupacion"] == al.TOTAL]["pct"].notna().all()
    assert not t["grupo"].astype(str).str.contains("DiosCh").any()
    assert GRADO_PEQUENO not in set(t["grupo"].astype(str))
    # cada subgrupo trae su tabla, que es la que pasa por la supresión
    celda = analisis.subgrupos[al.CRUCE]["LauV|Octavo"]
    assert list(celda.cortes_alerta.columns) == al.COLUMNAS_CORTES


def test_las_senales_individuales_quedan_solo_en_los_datos_locales(analisis):
    assert {"ALERTA_malestar", "ALERTA_desesperanza"} <= set(analisis.datos.columns)


def test_la_auditoria_de_restas_cubre_las_senales(analisis):
    assert publicar.verificar_restas({cat.NIVEL_SECUNDARIA: analisis}) == []


def test_primaria_solo_tiene_malestar(primaria):
    assert set(primaria.alertas["alerta"]) == {"malestar"}
    assert set(primaria.alertas_sensibilidad["alerta"]) == {"malestar"}


def test_sensibilidad_e_items_del_nivel(analisis):
    assert set(analisis.alertas_sensibilidad["variante"]) == set(al.VARIANTES)
    assert set(analisis.alertas_items["item"]) == {
        "SDQ5", "SDQ6", "SDQ8", "SDQ13", "SDQ19", "SDQ24",
        "RCADS1", "RCADS4", "RCADS16", "RCADS18"}


# ══ Publicar ════════════════════════════════════════════════════════════════
def _filas(a, nivel=cat.NIVEL_SECUNDARIA):
    return publicar.aplanar({nivel: a})


def test_las_alertas_se_publican_sin_casos(config):
    nivel, a = config
    filas = _filas(a, nivel)
    alertas = [f for f in filas if f["tipo"].startswith("alerta")]
    assert {f["tipo"] for f in alertas} == {"alerta", "alerta_grupo"}
    for f in alertas:
        assert not set(f["detalle"]) & set(publicar.CAMPOS_CONTEO_PROHIBIDOS)
        if f["valor"] is None:
            assert f["ic_inf"] is None and f["detalle"]["estado"] == ac.SIN_ESTADO
        else:
            # la regla, fila por fila: k = % × n queda en [3, n − 3]
            k = round(f["valor"] * f["n"] / 100)
            assert supresion.MIN_CASOS <= k <= f["n"] - supresion.MIN_CASOS
        if f["tipo"] == "alerta_grupo":
            assert f["detalle"]["n_grupo"] >= cat.MIN_GROUP_N
    publicar.verificar(filas)
    assert publicar.verificar_restas({nivel: a}) == []


def test_no_se_publican_sensibilidad_ni_items(analisis):
    tipos = {f["tipo"] for f in _filas(analisis)}
    assert not {"alerta_sensibilidad", "alerta_item"} & tipos


def test_verificar_rechaza_una_alerta_con_casos(analisis):
    fila = next(f for f in _filas(analisis) if f["tipo"] == "alerta")
    mala = dict(fila, detalle=dict(fila["detalle"], casos=5))
    with pytest.raises(publicar.PublicacionInsegura, match="casos"):
        publicar.verificar([mala])


def test_verificar_rechaza_un_estado_sin_porcentaje(analisis):
    fila = next(f for f in _filas(analisis) if f["tipo"] == "alerta_grupo")
    mala = dict(fila, valor=None, ic_inf=None, ic_sup=None,
                detalle=dict(fila["detalle"], estado=ac.PRIORIDAD))
    with pytest.raises(publicar.PublicacionInsegura, match="estado"):
        publicar.verificar([mala])


def test_verificar_restas_bloquea_una_alerta_destapada(config):
    import copy
    nivel, a = config
    for agrupacion, grupos in a.subgrupos.items():
        for grupo, s in grupos.items():
            t = s.cortes_alerta
            if len(t) and t["pct"].isna().any():
                b = copy.deepcopy(a)
                tb = b.subgrupos[agrupacion][grupo].cortes_alerta
                tb.loc[tb["pct"].isna(), "pct"] = 5.0
                assert any("alerta" in p for p in publicar.verificar_restas({nivel: b}))
                return
    pytest.skip("esta configuración no suprime ninguna alerta de subgrupo")


# ══ Supabase ════════════════════════════════════════════════════════════════
def test_la_migracion_de_alertas_y_el_esquema_dicen_lo_mismo():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "supabase", "migraciones",
                           "2026-10-07c-alertas-sin-casos.sql"), encoding="utf-8") as fh:
        migracion = fh.read()
    with open(os.path.join(raiz, "supabase", "estudiantes_schema.sql"), encoding="utf-8") as fh:
        esquema = fh.read()
    for texto in (migracion, esquema):
        assert "resultados_sin_conteos" in texto
        assert "detalle ?| ARRAY['casos', 'k_bajo', 'k_alto']" in texto
        assert "resultados_alerta_estado_con_cifra" in texto
        assert "NOT VALID" in texto
    # la misma lista de campos que rechaza `verificar`
    assert publicar.CAMPOS_CONTEO_PROHIBIDOS == ("casos", "k_bajo", "k_alto")
    assert ac.SIN_ESTADO == "sin_estado"          # el literal del CHECK y de verificar
