"""
El CCI de cuidadores se calcula sobre los colegios de la base publicable.

Solo cuentan las filas que el colegio publica (sin sus grados pequeños) y los
colegios con al menos MIN_GROUP_N cuidadores distintos con dato: en el marco de
niños, doce filas de cinco cuidadores no son un colegio publicable.
"""
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.cuidadores import catalog as cat
from src.cuidadores import pipeline
from src.estudiantes import stats


def _datos():
    rng = np.random.default_rng(3)
    filas = []
    for colegio, n, distintos, media in (("A", 20, 20, 5.0), ("B", 20, 20, 6.0),
                                          ("C", 12, 5, 9.0)):
        for i in range(n):
            filas.append(dict(Colegio=colegio, ID_cuidador=f"{colegio}{i % distintos}",
                              SDQ_Total=float(media + rng.normal())))
    # filas de A fuera de la base (un grado pequeño): no cuentan
    for i in range(6):
        filas.append(dict(Colegio="A", ID_cuidador=f"Ax{i}", SDQ_Total=30.0))
    return pd.DataFrame(filas)


def test_el_cci_usa_solo_la_base_publicable_y_cuidadores_distintos():
    d = _datos()
    base = SimpleNamespace(colegios={"A": d.index[:20], "B": d.index[20:40],
                                     "C": d.index[40:52]})
    esperado = stats.icc_entre_grupos(d.loc[d.index[:40]], "SDQ_Total")
    assert pipeline.icc_publicable(d, base, "SDQ_Total") == esperado
    # el cálculo anterior (todas las filas del nivel) daba otra cifra
    assert stats.icc_entre_grupos(d, "SDQ_Total") != esperado


def test_con_un_solo_colegio_publicable_no_hay_cci():
    d = _datos()
    base = SimpleNamespace(colegios={"A": d.index[:20], "C": d.index[40:52]})
    assert np.isnan(pipeline.icc_publicable(d, base, "SDQ_Total"))


def test_el_analisis_usa_el_cci_publicable(monkeypatch):
    from tests import cuidadores_comunidad_datos as datos
    llamadas = []
    original = pipeline.icc_publicable

    def espia(d, base, clave):
        llamadas.append(clave)
        return original(d, base, clave)
    monkeypatch.setattr(pipeline, "icc_publicable", espia)
    datos._analisis.cache_clear()
    try:
        ac = datos.analisis()
    finally:
        datos._analisis.cache_clear()
    assert set(ac.cuidador.icc) <= set(cat.CLAVES_CUIDADOR)
    assert llamadas and set(llamadas) == set(ac.cuidador.icc) | set(ac.nino.icc)
