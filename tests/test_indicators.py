"""Tests del detector/catálogo de indicadores para datasets genéricos."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.analysis import indicators


def _generic_df():
    return pd.DataFrame({
        "Nombre": ["P001", "P002", "P003"],
        "PSS_T": [10, 20, 30],
        "IRI_PT_Total": [7, 14, 28],
        "Sat_T": [5, 10, 15],
        "ERS_CLA_T": [0, 6, 12],
        "Sexo": [0, 1, 0],
    })


def test_is_wellbeing_vs_generic():
    generic = _generic_df()
    assert indicators.is_wellbeing_dataset(generic) is False
    wb = pd.DataFrame({"(BM),(CT)Item": [1, 2, 3]})
    assert indicators.is_wellbeing_dataset(wb) is True


def test_detect_indicators_prefers_totals():
    inds = indicators.detect_indicators(_generic_df())
    assert set(inds) == {"PSS_T", "IRI_PT_Total", "Sat_T", "ERS_CLA_T"}
    assert "Nombre" not in inds  # identificador protegido


def test_catalog_labels_and_direction():
    label, theme, hib = indicators.catalog_entry("PSS_T")
    assert "Estrés" in label and theme.startswith("🧠") and hib is False
    _, _, hib_sat = indicators.catalog_entry("Sat_T")
    assert hib_sat is True
    _, _, hib_ers = indicators.catalog_entry("ERS_CLA_T")
    assert hib_ers is None  # sin dirección definida


def test_enrich_orients_risk_indicators():
    enr = indicators.enrich_indicators(_generic_df(), ["PSS_T", "Sat_T"])
    # PSS es riesgo (mayor=peor): su posición orientada = 100 - pct crudo
    assert enr["PSS_T"]["oriented"] == 100 - enr["PSS_T"]["pct"]
    # Satisfacción es positiva: orientada = pct
    assert enr["Sat_T"]["oriented"] == enr["Sat_T"]["pct"]


def test_by_theme_groups_and_orders():
    enr = indicators.enrich_indicators(_generic_df(), ["PSS_T", "IRI_PT_Total", "Sat_T"])
    groups = indicators.by_theme(enr)
    # El primer tema no vacío debe ser salud mental (PSS)
    first_theme = next(iter(groups))
    assert first_theme.startswith("🧠")
