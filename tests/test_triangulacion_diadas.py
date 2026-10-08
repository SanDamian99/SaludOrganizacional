"""Triangulación · análisis de díadas sobre tablas armadas a mano."""
import numpy as np
import pandas as pd
import pytest

from src.estudiantes.stats import wilson
from src.triangulacion import catalogo as cat
from src.triangulacion import diadas as dy


def _diadas(e_total, c_total, familias=None, colegio="LauV", seed=0) -> pd.DataFrame:
    n = len(e_total)
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({
        "familia": familias if familias is not None else [f"C{i:08x}" for i in range(n)],
        "Colegio": colegio,
        "e_SDQ_Total": e_total, "c_SDQ_Total": c_total,
        "e_ALERTA_malestar": 0.0,
        "e_Sexo": np.where(np.arange(n) % 2, "Mujer", "Hombre"),
        "e_Edad": 10 + np.arange(n) % 6,
    })
    for s in ("SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro"):
        d[f"e_{s}"] = rng.integers(0, 11, n).astype(float)
        d[f"c_{s}"] = rng.integers(0, 11, n).astype(float)
    d["e_SDQ_Int"] = rng.normal(size=n)
    d["e_SDQ_Ext"] = rng.normal(size=n)
    for k in ("MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro"):
        d[f"e_{k}"] = rng.uniform(1, 5, n)
        d[f"a_{k}"] = rng.uniform(1, 5, n)
    d["a_EPDS_Total"] = rng.integers(0, 31, n).astype(float)
    d["a_PSS_Total"] = rng.integers(0, 41, n).astype(float)
    d["a_APQ_Fisico"] = ((np.arange(n) // 3) % 2).astype(float)
    d["a_BARRIO_Indice"] = rng.integers(0, 11, n).astype(float)
    return d


def _no_visto_base():
    # 10 con malestar no visto (20 / 5), 6 con malestar visto (20 / 20), 24 sin malestar.
    e = [20.0] * 16 + [5.0] * 24
    c = [5.0] * 10 + [20.0] * 6 + [5.0] * 24
    return _diadas(e, c)


def test_malestar_no_visto_con_cifras_conocidas():
    t = dy.malestar_no_visto(_no_visto_base())
    f = t.iloc[0]
    assert f["n"] == 40 and f["motivo"] == ""
    assert (f["pct_no_visto"], f["ic_inf"], f["ic_sup"]) == wilson(10, 40)
    assert f["pct_malestar"] == wilson(16, 40)[0]
    assert f["pct_no_visto_entre_malestar"] == wilson(10, 16)[0]


def test_la_senal_de_malestar_tambien_cuenta():
    d = _no_visto_base()
    d.loc[d.index[-3:], "e_ALERTA_malestar"] = 1.0           # 3 más con señal, no vistos
    f = dy.malestar_no_visto(d).iloc[0]
    assert f["pct_no_visto"] == wilson(13, 40)[0]


def test_malestar_no_visto_se_suprime_con_menos_de_3():
    e = [20.0] * 12 + [5.0] * 28
    c = [5.0] * 10 + [20.0] * 2 + [5.0] * 28                  # solo 2 «visto»
    f = dy.malestar_no_visto(_diadas(e, c)).iloc[0]
    assert f["motivo"] == dy.MOTIVO_PEQUENAS and pd.isna(f.get("pct_no_visto"))


def test_malestar_no_visto_cuenta_familias():
    d = _no_visto_base()
    d.loc[d.index[:10], "familia"] = ["F1", "F2"] * 5          # 10 no vistos de 2 familias
    f = dy.malestar_no_visto(d).iloc[0]
    assert f["motivo"] == dy.MOTIVO_PEQUENAS


def test_menos_de_10_familias_no_da_cifras():
    d = _diadas([10.0] * 12, [9.0] * 12, familias=[f"F{i % 6}" for i in range(12)])
    a = dy.acuerdo_sdq(d, n_boot=20)
    assert (a["motivo"] == dy.MOTIVO_POCAS).all()
    assert dy.bland_altman_agrupado(d).empty
    assert (dy.malestar_no_visto(d)["motivo"] == dy.MOTIVO_POCAS).all()


def test_acuerdo_perfecto():
    x = np.arange(40, dtype=float) % 25
    a = dy.acuerdo_sdq(_diadas(x, x), n_boot=50)
    f = a[a["subescala"] == "SDQ_Total"].iloc[0]
    assert f["cci"] == pytest.approx(1.0) and f["dif_media"] == 0
    assert f["rho"] == pytest.approx(1.0) and f["ba_lim_inf"] == f["ba_lim_sup"] == 0
    assert f["n"] == 40 and f["familias"] == 40


def test_bland_altman_agrupado_nunca_tiene_menos_de_10():
    x = np.arange(40, dtype=float) % 25
    ba = dy.bland_altman_agrupado(_diadas(x, x[::-1]))
    total = ba[ba["subescala"] == "SDQ_Total"]
    assert len(total) == 4                                      # 5 grupos de 8 no caben
    assert (ba["n"] >= cat.MIN_GROUP_N).all()


def test_asociaciones_con_y_sin_efecto_fijo():
    d = _diadas(np.arange(40.0), np.arange(40.0))
    d.loc[d.index[20:], "Colegio"] = "JJC"
    t = dy.asociaciones(d)
    todas = t[t["muestra"].str.startswith("Todas")]
    assert set(todas["colegios"]) == {2}
    assert len(todas) == len(cat.RESULTADOS) * len(cat.PREDICTORES)
    lauv = t[t["muestra"].str.startswith("Solo")]
    assert (lauv["motivo"] == dy.MOTIVO_MODELO).all()           # 20 díadas < 30
    assert todas["q_bh"].notna().all()


def test_un_predictor_binario_con_pocas_familias_se_omite():
    d = _diadas(np.arange(40.0), np.arange(40.0))
    d["a_APQ_Fisico"] = 0.0
    d.loc[d.index[:5], "a_APQ_Fisico"] = 1.0
    t = dy.asociaciones(d)
    assert not t["predictor"].str.contains("Castigo").any()
    assert t["nota"].str.contains("Castigo").all()


def test_apoyo_familiar_por_fuente():
    t = dy.apoyo_familiar(_diadas(np.arange(40.0), np.arange(40.0)))
    assert list(t["fuente"]) == [n for _, n in cat.FUENTES_MSPSS]
    assert (t["n"] == 40).all()


def test_ninguna_salida_lleva_familias():
    r = dy.analizar(_no_visto_base(), n_boot=20)
    for t in (r.acuerdo, r.bland_altman, r.no_visto, r.apoyo, r.asociaciones):
        assert "familia" not in t.columns
        assert not t.astype(str).apply(lambda s: s.str.fullmatch(r"C[0-9a-f]{8}")).any().any()


# ── sensibilidad: sin las díadas que no concuerdan en sexo, edad o grado ────
def _con_concordancia(n=60, discordantes=12, seed=3):
    rng = np.random.default_rng(seed)
    d = _diadas(rng.integers(0, 30, n).astype(float), rng.integers(0, 30, n).astype(float),
                seed=seed)
    d["c_Sexo"] = np.where(d["e_Sexo"] == "Mujer", "Niña", "Niño")
    d["c_Edad"] = d["e_Edad"].astype(float)
    d["e_Grado"] = "Sexto"
    d["c_Grado"] = "Sexto"
    k = discordantes // 3
    d.loc[d.index[:k], "c_Sexo"] = np.where(d.loc[d.index[:k], "e_Sexo"] == "Mujer", "Niño", "Niña")
    d.loc[d.index[k:2 * k], "c_Edad"] += 2                     # ± 1 año todavía concuerda
    d.loc[d.index[2 * k:discordantes], "c_Grado"] = "Quinto"
    d.loc[d.index[discordantes:discordantes + 3], "c_Edad"] += 1
    return d


def test_concordantes_excluye_sexo_edad_y_grado():
    d = _con_concordancia()
    assert int(dy.concordantes(d).sum()) == 48
    d.loc[d.index[0], "c_Sexo"] = np.nan                       # sin dato no es discordancia
    assert int(dy.concordantes(d).sum()) == 49


def test_sensibilidad_de_acuerdo_y_modelos_con_10_o_mas_excluidas():
    d = _con_concordancia()
    t = dy.analizar(d, n_boot=20)
    s = t.acuerdo_concordantes
    fila = s[s["subescala"] == "SDQ_Total"].iloc[0]
    assert fila["motivo"] == "" and fila["n"] == 48
    esperado = dy.acuerdo_sdq(d[dy.concordantes(d)], n_boot=20)
    assert fila["cci"] == esperado.iloc[0]["cci"]
    muestras = set(t.asociaciones["muestra"])
    assert dy.MUESTRA_CONCORDANTES in muestras
    sub = t.asociaciones[t.asociaciones["muestra"] == dy.MUESTRA_CONCORDANTES]
    assert (sub["motivo"] == "").any() and (sub["n"].dropna() <= 48).all()


def test_sensibilidad_no_se_muestra_si_las_excluidas_son_1_a_9():
    d = _con_concordancia(discordantes=6)
    t = dy.analizar(d, n_boot=20)
    s = t.acuerdo_concordantes
    assert (s["motivo"] == dy.MOTIVO_SENSIBILIDAD).all()
    assert "n" not in s.columns or s["n"].isna().all()
    sub = t.asociaciones[t.asociaciones["muestra"] == dy.MUESTRA_CONCORDANTES]
    assert (sub["motivo"] == dy.MOTIVO_SENSIBILIDAD).all()
    assert "beta" not in sub.columns or sub["beta"].isna().all()


# ── IC de las correlaciones por bootstrap de familias; predictores omitidos ─
def test_ic_de_correlaciones_por_bootstrap_de_familias():
    rng = np.random.default_rng(5)
    e = rng.integers(0, 30, 50).astype(float)
    familias = [f"C{i // 2:08x}" for i in range(50)]            # hermanos
    d = _diadas(e, e + rng.normal(0, 4, 50), familias=familias)
    f = dy.acuerdo_sdq(d, n_boot=40).iloc[0]
    from src.triangulacion import estadistica as est
    sub = d[["e_SDQ_Total", "c_SDQ_Total", "familia"]].dropna()
    lo, hi = est.bootstrap_ic(
        sub, lambda x: est.correlacion_ic(x["e_SDQ_Total"], x["c_SDQ_Total"], "spearman")[0],
        "familia", 40)
    assert (f["rho_ic_inf"], f["rho_ic_sup"]) == (round(lo, 3), round(hi, 3))
    a = dy.apoyo_familiar(d, n_boot=40).iloc[0]
    assert a["rho_ic_inf"] <= a["rho"] <= a["rho_ic_sup"]


def test_un_predictor_constante_se_anota():
    d = _diadas(np.arange(40.0), np.arange(40.0))
    d["a_BARRIO_Indice"] = 3.0
    t = dy.asociaciones(d)
    sub = t[t["muestra"] == dy.MUESTRA_TODAS]
    assert "Riesgo del barrio (z)" not in set(sub["predictor"])
    assert sub["nota"].str.contains("sin variación").all()


def test_sin_ningun_predictor_da_una_fila_con_motivo():
    d = _diadas(np.arange(40.0), np.arange(40.0))
    for p in ("a_EPDS_Total", "a_PSS_Total", "a_BARRIO_Indice"):
        d[p] = 1.0
    d["a_APQ_Fisico"] = 0.0
    t = dy.asociaciones(d)
    sub = t[t["muestra"] == dy.MUESTRA_TODAS]
    assert len(sub) == len(cat.RESULTADOS)
    assert (sub["motivo"] == dy.MOTIVO_SIN_PREDICTORES).all()
