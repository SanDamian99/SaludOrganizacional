"""Cuidadores 360 · puntuación desde el texto crudo (spec §5.5)."""
import numpy as np
import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import scoring
from src.estudiantes import catalog as cat_est


def _cuidador(**items) -> pd.DataFrame:
    """Un cuidador con todos los ítems en un valor neutro, salvo los indicados."""
    fila = {}
    for b in cat.BLOQUES_CUIDADOR:
        for c in b.columnas:
            fila[c] = b.valor_min
    fila.update(items)
    return pd.DataFrame([fila])


def test_pss_invierte_3_4_5_7_y_9():
    # todo «Nunca» (0): los 5 directos suman 0 y los 5 inversos 4 cada uno → 20
    assert scoring.puntuar_cuidadores(_cuidador())["PSS_Total"].item() == 20
    todo4 = {f"PSS{i}": 4 for i in range(1, 11)}
    assert scoring.puntuar_cuidadores(_cuidador(**todo4))["PSS_Total"].item() == 20
    peor = {f"PSS{i}": (0 if i in cat.PSS_INVERSOS else 4) for i in range(1, 11)}
    assert scoring.puntuar_cuidadores(_cuidador(**peor))["PSS_Total"].item() == 40


def test_pss_prorratea_con_9_y_falta_con_8():
    nueve = _cuidador(PSS7=np.nan)
    assert scoring.puntuar_cuidadores(nueve)["PSS_Total"].item() == pytest.approx(
        (20 - 4) * 10 / 9, abs=0.05)
    ocho = _cuidador(PSS7=np.nan, PSS9=np.nan)
    assert np.isnan(scoring.puntuar_cuidadores(ocho)["PSS_Total"].item())


@pytest.mark.parametrize("total,posible,probable", [(9, 0, 0), (10, 1, 0), (12, 1, 0),
                                                    (13, 1, 1), (30, 1, 1)])
def test_epds_cortes(total, posible, probable):
    items = {f"EPDS{i}": 0 for i in range(1, 11)}
    resto = total
    for i in range(1, 11):
        items[f"EPDS{i}"] = min(3, resto)
        resto -= items[f"EPDS{i}"]
    p = scoring.puntuar_cuidadores(_cuidador(**items))
    assert p["EPDS_Total"].item() == total
    assert (p["EPDS_Posible"].item(), p["EPDS_Probable"].item()) == (posible, probable)


@pytest.mark.parametrize("item10,senal", [(0, 0), (1, 1), (2, 1), (3, 1)])
def test_autolesion_es_cualquier_respuesta_distinta_de_nunca(item10, senal):
    p = scoring.puntuar_cuidadores(_cuidador(EPDS10=item10))
    assert p["EPDS_Autolesion"].item() == senal


def test_epds_incompleta_es_faltante_pero_el_item_10_cuenta():
    p = scoring.puntuar_cuidadores(_cuidador(EPDS3=np.nan, EPDS10=2))
    assert np.isnan(p["EPDS_Total"].item()) and np.isnan(p["EPDS_Probable"].item())
    assert p["EPDS_Autolesion"].item() == 1


def test_mspss_por_fuente_5_4_3():
    items = {f"MSPSS{i}": 5 for i in range(1, 6)}
    items.update({f"MSPSS{i}": 2 for i in range(6, 10)})
    items.update({f"MSPSS{i}": 3 for i in range(10, 13)})
    p = scoring.puntuar_cuidadores(_cuidador(**items))
    assert (p["MSPSS_Otro"].item(), p["MSPSS_Fam"].item(), p["MSPSS_Amigos"].item()) == (5, 2, 3)
    assert p["MSPSS_Total"].item() == pytest.approx((25 + 8 + 9) / 12)


def test_barrio_de_0_a_10():
    p = scoring.puntuar_cuidadores(_cuidador(**{f"BARRIO{i}": 2 for i in range(1, 6)}))
    assert p["BARRIO_Indice"].item() == 10
    assert scoring.puntuar_cuidadores(_cuidador())["BARRIO_Indice"].item() == 0


@pytest.mark.parametrize("nalgadas,cachetadas,correa,senal", [
    (1, 1, 1, 0), (2, 2, 2, 0), (3, 1, 1, 1), (1, 1, 5, 1)])
def test_castigo_fisico_a_veces_o_mas(nalgadas, cachetadas, correa, senal):
    p = scoring.puntuar_cuidadores(_cuidador(APQ22=nalgadas, APQ23=cachetadas, APQ24=correa))
    assert p["APQ_Fisico"].item() == senal


def test_grito_descriptivo():
    assert scoring.puntuar_cuidadores(_cuidador(APQ25=3))["APQ_Grito"].item() == 1
    assert scoring.puntuar_cuidadores(_cuidador(APQ25=2))["APQ_Grito"].item() == 0


def test_estres_parental_no_tiene_total():
    p = scoring.puntuar_cuidadores(_cuidador())
    assert not [c for c in p.columns if c.startswith("EP_") or c in ("EP_Total", "PSI_Total")]


# ══ Niño ════════════════════════════════════════════════════════════════════
def _nino(edad_estado="ok", **items) -> pd.DataFrame:
    fila = {f"SDQ{i}": 0 for i in range(1, 26)}
    fila.update({f"ARI{i}": 0 for i in range(1, 8)})
    fila["_edad_estado"] = edad_estado
    fila.update(items)
    return pd.DataFrame([fila])


def test_sdq_de_padres_con_bandas_de_padres():
    # emocional 5 (ítems 3, 8, 13: 2 + 2 + 1): banda de padres 5–6 = «Alto»; en autoinforme sería «Ligeramente elevado»
    p = scoring.puntuar_ninos(_nino(SDQ3=2, SDQ8=2, SDQ13=1))
    assert p["SDQ_Emo"].item() == 5
    assert p["banda_SDQ_Emo"].item() == 2
    assert cat_est.banda_de(5, "SDQ_Emo", "self") == 1


def test_sdq_inversos_estandar():
    # ítems 7, 11, 14, 21 y 25 invertidos: con todo en 0 suman 2 cada uno
    p = scoring.puntuar_ninos(_nino())
    assert p["SDQ_Con"].item() == 2 and p["SDQ_Pares"].item() == 4 and p["SDQ_Hip"].item() == 4
    assert p["SDQ_Total"].item() == 10


def test_sdq_solo_con_edad_numerica_de_4_a_17():
    """Spec §5.5: edad numérica entre 4 y 17; si no es numérica (o falta), el SDQ falta."""
    assert scoring.puntuar_ninos(_nino("ok"))["SDQ_Total"].notna().item()
    for estado in ("fuera_de_rango", "no_numerica", "vacia"):
        p = scoring.puntuar_ninos(_nino(estado))
        assert np.isnan(p["SDQ_Total"].item()), estado
        assert p[[c for c in p.columns if c.startswith("banda_")]].isna().all(axis=None)


def test_ari_de_padres_items_1_a_6():
    p = scoring.puntuar_ninos(_nino(ARI1=2, ARI6=2, ARI7=2))
    assert p["ARI_Total"].item() == 4 and p["ARI_Deterioro"].item() == 2
    assert np.isnan(scoring.puntuar_ninos(_nino(ARI3=np.nan))["ARI_Total"].item())


# ══ Tablas ══════════════════════════════════════════════════════════════════
def test_cortes_de_la_epds_anidados_en_una_clave():
    d = pd.DataFrame({"EPDS_Total": [5, 10, 11, 13, 20, np.nan],
                      "EPDS_Autolesion": [0, 0, 1, 0, 1, np.nan]})
    t = scoring.sobre_cortes_cuidador(d)
    epds = t[t["clave"] == "EPDS_Total"]
    assert list(epds["casos"]) == [4, 2] and set(epds["n"]) == {5}
    assert t.loc[t["clave"] == "EPDS_Autolesion", "casos"].item() == 2


def test_las_tablas_tienen_la_forma_de_estudiantes():
    from src.estudiantes import supresion
    d = pd.DataFrame({"EPDS_Total": [5, 10, 11, 13, 20], "SDQ_Total": [1, 15, 18, 22, 30]})
    t = scoring.sobre_cortes_cuidador(d)
    assert {"clave", "indicador", "n", "casos", "pct", "ic_inf", "ic_sup", "fuente"} <= set(t.columns)
    assert supresion.partes_por_familia(t, None)["EPDS_Total"] == (1, 2, 2)


def test_distribucion_de_items():
    d = pd.DataFrame({f"APQ{i}": [1, 3, 5, 4, 2] * 4 for i in range(1, 26)})
    t = scoring.distribucion_items(d, cat.APQ, umbral=3)
    assert len(t) == 25 and set(t["n"]) == {20} and set(t["pct"]) == {60.0}
    assert list(t["columna"][:2]) == [57, 58]
