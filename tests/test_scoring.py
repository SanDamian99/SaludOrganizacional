"""Tests del núcleo de puntuación psicométrica (src/analysis/scoring.py)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import pandas as pd
import pytest

from src.core.config import DATA_DICTIONARY, item_valence, get_scale_range
from src.analysis import scoring


DIMS = DATA_DICTIONARY["Dimensiones de Bienestar y Salud Mental"]


def _cols(dim):
    return list(DIMS[dim]["Preguntas"])


# --- Valencia ---------------------------------------------------------------

def test_valence_positive_dimension_all_direct():
    for q in _cols("Compromiso del Líder"):
        assert item_valence("Compromiso del Líder", q) == +1


def test_valence_risk_dimension_all_inverse():
    for q in _cols("Síntomas de Burnout"):
        assert item_valence("Síntomas de Burnout", q) == -1


def test_valence_mixed_control_del_tiempo():
    val = {q: item_valence("Control del Tiempo", q) for q in _cols("Control del Tiempo")}
    # 3 directos (autonomía) y 4 inversos (presión)
    assert sum(1 for v in val.values() if v == +1) == 3
    assert sum(1 for v in val.values() if v == -1) == 4
    # El ítem de presión es inverso
    presion = next(q for q in val if "presionan" in q.lower())
    assert val[presion] == -1


def test_valence_intencion_retiro_flip_retention_item():
    val = {q: item_valence("Intención de Retiro", q) for q in _cols("Intención de Retiro")}
    permanencia = next(q for q in val if "me veo trabajando" in q.lower())
    assert val[permanencia] == +1          # permanencia = bienestar
    resto = [v for q, v in val.items() if q != permanencia]
    assert all(v == -1 for v in resto)     # querer irse = menos bienestar


# --- Puntaje de dimensión (orientado "mayor = mejor") -----------------------

def test_positive_dimension_score_direct():
    dim = "Satisfacción"
    df = pd.DataFrame({q: [5, 5, 5] for q in _cols(dim)})
    scores = scoring.compute_dimension_scores(df)
    assert dim in scores
    assert scores[dim]["score"] == pytest.approx(5.0)
    assert scores[dim]["n"] == 3
    assert scores[dim]["n_items"] == len(_cols(dim))


def test_risk_dimension_high_raw_is_low_wellbeing():
    dim = "Síntomas de Burnout"           # escala 1-5, todos inversos
    mn, mx = get_scale_range(dim)
    df = pd.DataFrame({q: [mx, mx, mx] for q in _cols(dim)})  # máximo malestar
    scores = scoring.compute_dimension_scores(df)
    # oriented = (min+max) - x  => 1.0 (riesgo)
    assert scores[dim]["score"] == pytest.approx(float(mn))
    assert scores[dim]["estado"] == "Riesgo"


def test_risk_dimension_low_raw_is_high_wellbeing():
    dim = "Síntomas de Burnout"
    mn, mx = get_scale_range(dim)
    df = pd.DataFrame({q: [mn, mn, mn] for q in _cols(dim)})  # sin síntomas
    scores = scoring.compute_dimension_scores(df)
    assert scores[dim]["score"] == pytest.approx(float(mx))
    assert scores[dim]["estado"] == "Fortaleza"


def test_mixed_dimension_orientation():
    dim = "Control del Tiempo"            # escala 1-7 (min+max = 8)
    cols = _cols(dim)
    data = {}
    for q in cols:
        if item_valence(dim, q) == +1:
            data[q] = [6, 6, 6]           # autonomía alta = bueno
        else:
            data[q] = [2, 2, 2]           # poca presión = bueno -> oriented 8-2=6
    df = pd.DataFrame(data)
    scores = scoring.compute_dimension_scores(df)
    # Todos los ítems orientados valen 6 -> score 6.0
    assert scores[dim]["score"] == pytest.approx(6.0)


# --- Cronbach alpha ---------------------------------------------------------

def test_cronbach_alpha_range():
    dim = "Compromiso del Líder"
    # datos correlacionados: cada fila con un nivel distinto
    cols = _cols(dim)
    df = pd.DataFrame({c: [1, 3, 5, 7, 2, 4] for c in cols})
    a = scoring.cronbach_alpha(df[cols])
    # ítems idénticos -> alpha = 1.0
    assert a == pytest.approx(1.0, abs=1e-6)


def test_cronbach_alpha_insufficient_items_returns_none():
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert scoring.cronbach_alpha(df[["a"]]) is None


# --- Clasificación ----------------------------------------------------------

def test_classify_dimensions_buckets():
    scores = {
        "Satisfacción": {"score": 5.5, "estado": "Fortaleza"},
        "Síntomas de Burnout": {"score": 1.5, "estado": "Riesgo"},
        "Apoyo del Grupo": {"score": 4.0, "estado": "Intermedio"},
    }
    fort, riesgo, inter = scoring.classify_dimensions(scores)
    assert "Satisfacción" in [d for d, _ in fort]
    assert "Síntomas de Burnout" in [d for d, _ in riesgo]
    assert "Apoyo del Grupo" in [d for d, _ in inter]
