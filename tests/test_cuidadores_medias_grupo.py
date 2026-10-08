"""
Las medias por colegio y por grado no pueden acotar un corte que se suprime.

Con Σ = M·n y una escala acotada, la media de un grupo obliga a que haya como
mucho k casos (o n − k no casos) del corte de esa escala. Si esa cota es menor
que 3, la media se borra (en la tabla del análisis, en lo que se publica y en
la vista), igual que la media de un ítem con corte en estudiantes.
"""
import math

import pandas as pd
import pytest

from src.cuidadores import pipeline, publicar


@pytest.mark.parametrize("clave,media,n,delata", [
    ("EPDS_Total", 1.0, 20, True),       # ≥10: como mucho 2 casos (Σ=20)
    ("EPDS_Total", 6.0, 20, False),
    ("EPDS_Total", 28.0, 20, True),      # casi todos ≥13: < 3 no casos
    ("MSPSS_Total", 4.9, 20, True),      # < 3: casi nadie
    ("MSPSS_Total", 1.1, 20, True),      # casi todos < 3: pocos no casos
    ("MSPSS_Fam", 3.5, 20, False),
    ("SDQ_Hip", 0.5, 20, True),          # ≥ 8: Σ=10 → como mucho 1 caso
    ("SDQ_Hip", 4.0, 20, False),
    ("SDQ_Pro", 9.9, 20, True),          # prosocial: caso ≤ 6
    ("SDQ_Pro", 7.5, 20, False),
    ("PSS_Total", 0.1, 20, False),       # sin corte: nunca
    ("ARI_Total", 0.1, 20, False),
])
def test_media_acota_corte(clave, media, n, delata):
    assert pipeline.media_acota_corte(clave, media, n) is delata


def _tabla():
    return pd.DataFrame([
        {"clave": "SDQ_Hip", "escala": "Hip", "p": 0.2, "eta2": 0.01,
         "M·LauV": 0.5, "n·LauV": 20, "M·JJC": 4.0, "n·JJC": 20},
        {"clave": "PSS_Total", "escala": "PSS", "p": 0.2, "eta2": 0.01,
         "M·LauV": 0.1, "n·LauV": 20, "M·JJC": 15.0, "n·JJC": 20},
    ])


def test_la_tabla_por_grupo_borra_solo_la_media_que_delata():
    t = pipeline.medias_de_grupo_publicables(_tabla())
    hip, pss = t.iloc[0], t.iloc[1]
    assert math.isnan(hip["M·LauV"]) and hip["M·JJC"] == 4.0
    assert pss["M·LauV"] == 0.1                       # sin corte: se queda
    assert hip["n·LauV"] == 20


def test_publicar_no_sube_la_media_que_delata():
    from types import SimpleNamespace
    from src.cuidadores import catalog as cat
    a = SimpleNamespace(descriptivos=None, bandas=None, cortes=None, terciles=None,
                        correlaciones=None, fiabilidad=None, icc={}, subgrupos={},
                        muestra=None, enmascarados={}, escalas=[], avisos=[], n=40,
                        por_grado=pd.DataFrame(),
                        por_colegio=_tabla())     # sin pasar por el pipeline: defensa doble
    filas = [f for f in publicar._filas_marco(cat.MARCO_NINO, a) if f["tipo"] == "grupo"]
    claves = {(f["clave"], f["grupo"]) for f in filas}
    assert ("SDQ_Hip", "LauV") not in claves
    assert ("SDQ_Hip", "JJC") in claves


def test_el_analisis_sintetico_no_publica_medias_que_delatan():
    from tests import cuidadores_comunidad_datos as datos
    ac = datos.analisis()
    for marco in (ac.cuidador, ac.nino):
        for t in (marco.por_colegio, marco.por_grado):
            if t is None or t.empty:
                continue
            for _, f in t.iterrows():
                for col in [c for c in t.columns if c.startswith("M·")]:
                    m, n = f[col], f["n·" + col[2:]]
                    if pd.notna(m) and pd.notna(n):
                        assert not pipeline.media_acota_corte(f["clave"], m, n), (
                            f["clave"], col)
