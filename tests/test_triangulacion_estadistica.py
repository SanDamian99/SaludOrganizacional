"""Triangulación · estadística contra valores conocidos."""
import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from src.triangulacion import estadistica as est

# Shrout y Fleiss (1979), tabla 2: 6 sujetos × 4 jueces. CCI(2,1) = 0,29.
SHROUT_FLEISS = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8],
                          [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]])


def _desde_tabla(tabla):
    a, b = [], []
    for i, fila in enumerate(tabla):
        for j, n in enumerate(fila):
            a += [i] * n
            b += [j] * n
    return a, b


def test_cci_a1_de_shrout_y_fleiss():
    assert round(est.icc_a1(SHROUT_FLEISS), 2) == 0.29


def test_cci_es_uno_con_acuerdo_perfecto_y_quita_faltantes():
    Y = np.array([[1, 1], [2, 2], [5, 5], [np.nan, 3], [7, 7]])
    assert est.icc_a1(Y) == pytest.approx(1.0)


def test_cci_baja_con_un_sesgo_sistematico():
    x = np.arange(20, dtype=float)
    assert est.icc_a1(np.column_stack([x, x + 5])) < est.icc_a1(np.column_stack([x, x]))


def test_kappa_sin_ponderar_en_2x2_es_el_de_cohen():
    a, b = _desde_tabla([[20, 10], [5, 15]])        # po = 0,7; pe = 0,5
    assert est.kappa_ponderado(a, b, k=2) == pytest.approx(0.4)


def test_kappa_ponderado_lineal_3x3():
    """Calculado a mano con pesos de acuerdo 1 − |i − j| / 2: κw = 39/59."""
    a, b = _desde_tabla([[10, 2, 0], [3, 8, 1], [0, 2, 4]])
    assert est.kappa_ponderado(a, b, k=3) == pytest.approx(39 / 59)


def test_kappa_perfecto_y_con_faltantes():
    assert est.kappa_ponderado([0, 1, 2, 3, np.nan], [0, 1, 2, 3, 1]) == pytest.approx(1.0)


def test_bland_altman():
    r = est.bland_altman([3, 5, 7, 9], [1, 4, 5, 9])        # diferencias 2, 1, 2, 0
    s = np.std([2, 1, 2, 0], ddof=1)
    assert r["n"] == 4 and r["dif_media"] == pytest.approx(1.25)
    assert r["lim_inf"] == pytest.approx(1.25 - est.Z95 * s)
    assert r["lim_sup"] == pytest.approx(1.25 + est.Z95 * s)


def test_media_agrupada_con_familias_de_uno_es_la_t_clasica():
    y = np.array([1.0, 3, 2, 5, 4, 6, 2, 3])
    r = est.media_agrupada(y, np.arange(len(y)))
    t = sps.t.ppf(0.975, len(y) - 1)
    se = y.std(ddof=1) / np.sqrt(len(y))
    assert r["m"] == pytest.approx(y.mean())
    assert r["ic_inf"] == pytest.approx(y.mean() - t * se)
    assert r["ic_sup"] == pytest.approx(y.mean() + t * se)


def test_media_agrupada_ensancha_con_hermanos_iguales():
    y = np.repeat([1.0, 4, 2, 6, 3, 5], 2)
    solos = est.media_agrupada(y, np.arange(len(y)))
    familias = est.media_agrupada(y, np.repeat(np.arange(6), 2))
    assert familias["se"] > solos["se"] and familias["G"] == 6


def test_correlacion_con_ic_de_fisher():
    a = np.arange(30, dtype=float)
    b = a ** 2
    rho, lo, hi, p = est.correlacion_ic(a, b, "spearman")
    assert rho == pytest.approx(1.0) and hi == pytest.approx(1.0, abs=1e-5)
    rng = np.random.default_rng(3)
    x, y = rng.normal(size=50), rng.normal(size=50)
    r, lo, hi, _ = est.correlacion_ic(x, y, "pearson")
    z, se = np.arctanh(r), 1 / np.sqrt(47)
    assert lo == pytest.approx(np.tanh(z - est.Z95 * se))
    assert hi == pytest.approx(np.tanh(z + est.Z95 * se))


def test_bootstrap_por_familias_es_reproducible():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"x": rng.normal(size=60), "familia": np.repeat(np.arange(30), 2)})
    f = lambda d: d["x"].mean()                                     # noqa: E731
    uno = est.bootstrap_ic(df, f, "familia", n_boot=200, semilla=1)
    dos = est.bootstrap_ic(df, f, "familia", n_boot=200, semilla=1)
    assert uno == dos and uno[0] < df["x"].mean() < uno[1]


def test_mco_con_efecto_fijo_recupera_la_pendiente():
    rng = np.random.default_rng(1)
    colegio = pd.Series(np.repeat(["A", "B", "C"], 20))
    x = pd.Series(rng.normal(size=60))
    y = 2 * x + colegio.map({"A": 0.0, "B": 5.0, "C": -3.0}) + rng.normal(0, 0.01, 60)
    res = est.ols_agrupado(y, pd.DataFrame({"x": x}), pd.Series(np.arange(60)), colegio)
    assert list(res["predictor"]) == ["x"]
    assert res.iloc[0]["beta"] == pytest.approx(2.0, abs=0.01)
    assert res.iloc[0]["ic_inf"] < 2.0 < res.iloc[0]["ic_sup"]


def test_partes_seguras_cuenta_filas_y_familias():
    etiquetas = pd.Series([0] * 10 + [1] * 3)
    assert est.partes_seguras(etiquetas, None, [1])
    assert not est.partes_seguras(pd.Series([0] * 10 + [1] * 2), None, [1])
    assert not est.partes_seguras(pd.Series([0] * 3 + [1] * 10), None, [0, 1, 2])  # 2 vacía
    familias = pd.Series(list(range(10)) + [99, 99, 99])           # 3 casos, 1 familia
    assert not est.partes_seguras(etiquetas, familias, [1])


def test_suficiente_exige_familias_distintas():
    df = pd.DataFrame({"familia": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]})
    assert not est.suficiente(df, "familia")
    assert est.suficiente(df, None)
