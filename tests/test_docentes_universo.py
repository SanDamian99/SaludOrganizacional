"""
Universo publicable de Docentes: sedes fundidas, Secretaría fuera, y un total
que nunca deja deducir un grupo de 1 a 9 restando los grupos mostrados.
"""
import numpy as np
import pandas as pd
import pytest

from src.docentes import catalogo as cat
from src.docentes import estadistica as est
from src.docentes import universo


def test_sedes_a_su_institucion_y_secretaria_fuera():
    df = pd.DataFrame({"Colegio": ["Fusca · sede El Cerro", "Fusca", "Diversificado · sede Campincito",
                                   "Diversificado · sede Santa Lucía", "Colegio Nacional Diversificado",
                                   "Secretaría de Educación", "Bojacá", np.nan],
                       "x": range(8)})
    u = universo.aplicar(df)
    assert len(u) == 7 and "Secretaría de Educación" not in set(u["Colegio"].dropna())
    assert u["Colegio"].value_counts().to_dict() == {"Fusca": 2, "Colegio Nacional Diversificado": 3, "Bojacá": 1}
    assert u["Colegio"].isna().sum() == 1
    assert df["Colegio"].iloc[0] == "Fusca · sede El Cerro"          # el original no cambia
    assert universo.aplicar(pd.DataFrame({"x": [1]})).equals(pd.DataFrame({"x": [1]}))


@pytest.mark.parametrize("conteos,grandes,otros,absorbido", [
    ({"A": 30, "B": 12}, {"A": 30, "B": 12}, 0, None),
    ({"A": 30, "B": 12, "C": 4, "D": 7}, {"A": 30, "B": 12}, 11, None),
    ({"A": 30, "B": 12, "C": 4}, {"A": 30}, 16, "B"),            # otros 4 → absorbe al más pequeño
    ({"A": 30, "B": 30, "C": 5}, {"B": 30}, 35, "A"),            # empate: por nombre
    ({"C": 5}, {}, 5, None),
])
def test_reparto(conteos, grandes, otros, absorbido):
    assert universo.reparto(conteos) == (grandes, otros, absorbido)
    total = sum(conteos.values())
    if grandes:
        assert universo.consistente(total, grandes.values(), otros)


def test_grupos_publicables_y_pie():
    agg = pd.DataFrame({"g": ["A", "B", "C"], "mean": [1.0, 2.0, 3.0], "count": [30, 12, 4]})
    vis, otros, absorbido, ocultos = universo.grupos_publicables(agg, "g")
    assert list(vis["g"]) == ["A"] and otros == 16 and absorbido == "B" and ocultos == ["C"]
    texto = universo.pie(vis, "g", otros, absorbido, ocultos)
    assert "A=30" in texto and "16" in texto and "incluye B" in texto and "sin cifra: C" in texto
    assert "B=12" not in texto and "C=4" not in texto


def test_consistente():
    assert universo.consistente(479, [470], 9) is False
    assert universo.consistente(478, [460], 18) is True
    assert universo.consistente(478, [478], 0) is True
    assert universo.consistente(478, [460], 10) is False     # el resto real es 18, no 10


def test_ic_welch():
    a = pd.Series([1, 2, 3, 4, 5]); b = pd.Series([2, 3, 4, 5, 6, 7])
    d, inf, sup = est.ic_welch(a, b)
    assert d == pytest.approx(3 - 4.5) and inf < d < sup
    assert est.ic_welch(pd.Series([1.0]), b) == (pytest.approx(1 - 4.5), None, None)
    assert est.ic_welch(pd.Series([], dtype=float), b) == (None, None, None)
    # Welch: con varianzas desiguales el IC es más ancho que con la de a sola
    assert sup - inf == pytest.approx(2 * 2.3 * np.sqrt(a.var() / 5 + b.var() / 6), abs=0.3)


def test_los_sin_dato_cuentan_en_otros():
    agg = pd.DataFrame({"g": ["A", "B", np.nan], "mean": [1.0, 2.0, 3.0], "count": [30, 12, 69]})
    vis, otros, absorbido, ocultos = universo.grupos_publicables(agg, "g")
    assert list(vis["g"]) == ["A", "B"] and otros == 69 and absorbido is None and ocultos == []
    assert universo.consistente(111, vis["count"].tolist(), otros)
    # sin dato pequeño (4) + ningún grupo pequeño: también se absorbe para no dejar 1–9
    agg = pd.DataFrame({"g": ["A", "B", np.nan], "mean": [1.0, 2.0, 3.0], "count": [30, 12, 4]})
    vis, otros, absorbido, ocultos = universo.grupos_publicables(agg, "g")
    assert list(vis["g"]) == ["A"] and otros == 16 and absorbido == "B"
    assert universo.consistente(46, vis["count"].tolist(), otros)
