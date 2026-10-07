# tests/test_privacidad.py
"""Base publicable y auditoría de restas (spec 6-oct-2026 §5.1)."""
import pandas as pd
import pytest

from src.estudiantes import privacidad as pv


def _d(conteos: dict[tuple[str, str], int], **cols) -> pd.DataFrame:
    filas = [dict(Colegio=c, Grado=g) for (c, g), n in conteos.items() for _ in range(n)]
    d = pd.DataFrame(filas)
    for k, v in cols.items():
        d[k] = v(d) if callable(v) else v
    return d


# Secundaria del 18-sep: Décimo = LaBalsa 32 + LauV 90 + CdP 6
DECIMO = {("LaBalsa", "Décimo"): 32, ("LauV", "Décimo"): 90, ("CdP", "Décimo"): 6,
          ("CdP", "Sexto"): 2, ("DiosCh", "Sexto"): 3, ("LauV", "Sexto"): 95}
# Primaria nueva: SJMEB 6 + 8, sin celdas publicables
PRIMARIA = {("CdP", "Cuarto"): 11, ("CdP", "Quinto"): 30, ("LauV", "Quinto"): 97,
            ("SJMEB", "Cuarto"): 6, ("SJMEB", "Quinto"): 8, ("DiosCh", "Cuarto"): 2}
# Primaria del 18-sep: CdP total 15 = cuarto 5 + quinto 10
CDP15 = {("CdP", "Cuarto"): 5, ("CdP", "Quinto"): 10, ("LauV", "Cuarto"): 86}


def test_las_celdas_publicables_son_las_de_diez_o_mas():
    b = pv.base_publicable(_d(DECIMO))
    assert set(b.celdas) == {"LaBalsa|Décimo", "LauV|Décimo", "LauV|Sexto"}


def test_el_grado_excluye_los_colegios_pequenos():
    b = pv.base_publicable(_d(DECIMO))
    assert len(b.grados["Décimo"]) == 122          # sin los 6 de CdP


def test_el_colegio_es_la_union_de_sus_celdas():
    b = pv.base_publicable(_d(CDP15))
    assert len(b.colegios["CdP"]) == 10            # el cuarto de 5 queda fuera


def test_colegio_sin_celdas_pero_grande_se_publica_entero():
    b = pv.base_publicable(_d(PRIMARIA))
    assert len(b.colegios["SJMEB"]) == 14
    assert "SJMEB|Cuarto" not in b.celdas


def test_el_nivel_incluye_el_resto_solo_si_es_grande_y_de_dos_colegios():
    grande = pv.base_publicable(_d({**DECIMO, ("DiosCh", "Octavo"): 5}))
    assert grande.incluye_resto                    # 6 + 2 + 3 + 5 = 16, 2 colegios
    chico = pv.base_publicable(_d(PRIMARIA))
    assert not chico.incluye_resto                 # 2, un colegio
    assert len(chico.nivel) == len(_d(PRIMARIA)) - 2


@pytest.mark.parametrize("conteos", [DECIMO, PRIMARIA, CDP15])
def test_ninguna_resta_deja_un_grupo_pequeno(conteos):
    d = _d(conteos)
    b = pv.base_publicable(d)
    assert pv.auditar(d, b, []) == []


def test_la_auditoria_detecta_una_resta_peligrosa():
    """Si se publicara el grado completo, Décimo − celdas = CdP décimo (6)."""
    d = _d(DECIMO)
    b = pv.base_publicable(d)
    b.grados["Décimo"] = d.index[d["Grado"] == "Décimo"]   # el error que evitamos
    problemas = pv.auditar(d, b, [])
    assert any("Grado Décimo" in p and "6" in p for p in problemas)


def test_la_auditoria_mira_cada_indicador_por_separado():
    """Con faltantes, el resto válido de un indicador puede quedar pequeño."""
    conteos = {("A", "X"): 12, ("A", "Y"): 12, ("B", "X"): 12}
    d = _d(conteos)
    d["SDQ_Total"] = 1.0
    # 3 respuestas válidas de A|Y y el resto faltante: la celda no publica el
    # indicador, pero el colegio A sí (15 válidas) → A − A|X = 3
    idx = d.index[(d.Colegio == "A") & (d.Grado == "Y")]
    d.loc[idx[3:], "SDQ_Total"] = None
    b = pv.base_publicable(d)
    assert any(p.startswith("SDQ_Total") for p in pv.auditar(d, b, ["SDQ_Total"]))


def test_filas_respeta_la_base():
    d = _d(DECIMO)
    b = pv.base_publicable(d)
    assert len(pv.filas(d, b, colegio="CdP")) == 0
    assert len(pv.filas(d, b, grado="Décimo")) == 122
    assert len(pv.filas(d, b, colegio="LauV", grado="Décimo")) == 90
    assert len(pv.filas(d, b, colegio="CdP", grado="Décimo")) == 0
