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
