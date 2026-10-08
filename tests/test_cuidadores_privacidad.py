"""Cuidadores 360 · base publicable contando cuidadores distintos (spec §4, §5.1)."""
import numpy as np
import pandas as pd

from src.cuidadores import privacidad
from src.estudiantes import privacidad as priv_est


def _marco(filas: list[tuple[str, str, int, int]]) -> pd.DataFrame:
    """[(colegio, grado, cuidadores, niños por cuidador)] → una fila por niño."""
    out, c = [], 0
    for colegio, grado, cuidadores, hijos in filas:
        for _ in range(cuidadores):
            for h in range(hijos):
                out.append(dict(ID_cuidador=f"C{c:08x}", ID_nino=f"N{c:06x}{h:02x}",
                                Colegio=colegio, Grado=grado, X=float(c % 7)))
            c += 1
    return pd.DataFrame(out)


def test_con_un_cuidador_por_fila_es_la_base_de_estudiantes():
    d = _marco([("A", "Quinto", 12, 1), ("A", "Sexto", 6, 1), ("B", "Quinto", 15, 1),
                ("C", "Sexto", 4, 1), ("D", "Quinto", 5, 1)])
    a, b = privacidad.base_publicable(d), priv_est.base_publicable(d)
    assert a.celdas.keys() == b.celdas.keys() and a.colegios.keys() == b.colegios.keys()
    assert a.grados.keys() == b.grados.keys()
    assert a.nivel.equals(b.nivel) and a.incluye_resto == b.incluye_resto


def test_el_minimo_cuenta_cuidadores_no_ninos():
    # 6 cuidadores con 2 hijos cada uno = 12 filas, pero 6 personas: no se publica
    d = _marco([("A", "Quinto", 6, 2), ("A", "Sexto", 10, 1), ("B", "Quinto", 12, 1)])
    base = privacidad.base_publicable(d)
    assert "A|Quinto" not in base.celdas and "A|Sexto" in base.celdas
    assert priv_est.base_publicable(d).celdas.keys() >= {"A|Quinto"}   # la de estudiantes sí


def test_otro_y_sin_dato_nunca_son_grupo():
    d = _marco([("OTRO", "Quinto", 15, 1), ("SIN_DATO", "Sexto", 12, 1), ("A", "Quinto", 11, 1)])
    base = privacidad.base_publicable(d)
    assert set(base.colegios) == {"A"} and set(base.celdas) == {"A|Quinto"}


def test_el_resto_cuenta_cuidadores_distintos():
    # resto: 2 colegios, 5 cuidadores con 2 hijos (10 filas): no llega a 10 personas
    d = _marco([("A", "Quinto", 12, 1), ("B", "Quinto", 3, 2), ("C", "Sexto", 2, 2)])
    base = privacidad.base_publicable(d)
    assert not base.incluye_resto
    assert len(base.nivel) == 12


def test_todo_o_nada_cuenta_cuidadores():
    d = _marco([("A", "Quinto", 12, 1), ("A", "Sexto", 10, 2)])
    # en A|Sexto solo 5 cuidadores tienen dato (10 filas)
    sexto = d.index[(d["Grado"] == "Sexto")]
    con_dato = d.loc[sexto, "ID_cuidador"].drop_duplicates().index[:5]
    quitar = sexto.difference(d.index[d["ID_cuidador"].isin(d.loc[con_dato, "ID_cuidador"])])
    d.loc[quitar, "X"] = np.nan
    base = privacidad.base_publicable(d)
    dm, sup = privacidad.aplicar_todo_o_nada(d, base)
    assert dm.loc[sexto, "X"].isna().all() and sup == {"X": 10}
    assert dm.loc[d["Grado"] == "Quinto", "X"].notna().all()


def test_las_columnas_de_identificacion_no_se_tocan():
    d = _marco([("A", "Quinto", 12, 1)]).assign(Quien="Mamá", Ola="2026", Edad=9.0)
    assert privacidad.columnas_de_analisis(d) == ["X"]


def test_distintos_por_grupo():
    d = _marco([("A", "Quinto", 3, 2), ("B", "Sexto", 4, 1)])
    assert privacidad.distintos_por_grupo(d, "Colegio") == {"A": 3, "B": 4}
