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


# ══ Revisión del 7-oct: todo o nada por indicador, margen del resto, índice ══
import numpy as np

from src.estudiantes import catalog as cat

# Puente de dos pasos: cada celda tiene ≥ 10 filas pero < 10 respuestas válidas
PUENTE = {("X", "A"): (12, 5), ("X", "B"): (12, 5), ("Y", "A"): (12, 5),
          ("Y", "B"): (12, 5), ("Z", "C"): (12, 5), ("Z", "D"): (12, 5),
          ("W", "C"): (12, 5), ("W", "D"): (12, 5), ("X", "C"): (12, 3)}


def _d_validos(conteos: dict, columna: str = "SDQ_Total") -> pd.DataFrame:
    """conteos: (colegio, grado) → (filas, respuestas válidas de `columna`)."""
    filas = [dict(Colegio=c, Grado=g, **{columna: 1.0 if k < v else np.nan})
             for (c, g), (n, v) in conteos.items() for k in range(n)]
    return pd.DataFrame(filas)


def _validos(d, b, col, colegio=pv.TODOS, grado=pv.TODOS) -> pd.Index:
    sub = pv.filas(d, b, colegio=colegio, grado=grado)
    return sub.index[sub[col].notna()]


def _puente(d, b, col="SDQ_Total") -> int:
    """|X ∪ Y| − |A| − |B| en respuestas válidas: X|C si A y B son X|·, Y|·."""
    x, y = _validos(d, b, col, colegio="X"), _validos(d, b, col, colegio="Y")
    a, bb = _validos(d, b, col, grado="A"), _validos(d, b, col, grado="B")
    return len(x) + len(y) - len(a) - len(bb)


def test_el_puente_de_dos_pasos_escapa_a_la_auditoria_de_un_paso():
    d = _d_validos(PUENTE)
    b = pv.base_publicable(d)
    assert pv.auditar(d, b, ["SDQ_Total"]) == []
    assert _puente(d, b) == 3                      # X|C reconstruido


def test_todo_o_nada_cierra_el_puente():
    d = _d_validos(PUENTE)
    b = pv.base_publicable(d)
    dm, suprimidos = pv.aplicar_todo_o_nada(d, b)
    assert pv.auditar(dm, b, ["SDQ_Total"]) == []
    combinacion = _puente(dm, b)
    assert combinacion == 0 or combinacion >= cat.MIN_GROUP_N
    assert suprimidos == {"SDQ_Total": 8 * 5 + 3}
    assert d["SDQ_Total"].notna().sum() == 43      # no toca el original


def test_todo_o_nada_conserva_las_unidades_completas():
    conteos = {**PUENTE, ("X", "A"): (12, 10), ("X", "B"): (12, 11)}
    d = _d_validos(conteos)
    b = pv.base_publicable(d)
    dm, suprimidos = pv.aplicar_todo_o_nada(d, b)
    assert len(_validos(dm, b, "SDQ_Total", colegio="X", grado="A")) == 10
    assert len(_validos(dm, b, "SDQ_Total", colegio="X")) == 21   # sin X|C
    assert suprimidos == {"SDQ_Total": 6 * 5 + 3}
    assert pv.auditar(dm, b, ["SDQ_Total"]) == []


def test_resto_con_pocas_respuestas_validas_se_suprime():
    """Como ERQ en secundaria: el resto tiene 11 filas (8 + 3) y 4 respuestas."""
    conteos = {("LauV", "Sexto"): (95, 95), ("LaBalsa", "Décimo"): (32, 30),
               ("CdP", "Décimo"): (8, 3), ("DiosCh", "Sexto"): (3, 1)}
    d = _d_validos(conteos, "ERQ_Reap")
    b = pv.base_publicable(d)
    assert b.incluye_resto
    assert any("deja 4" in p for p in pv.auditar(d, b, ["ERQ_Reap"]))
    dm, suprimidos = pv.aplicar_todo_o_nada(d, b)
    assert suprimidos == {"ERQ_Reap": 4}
    resto = dm["Colegio"].isin(["CdP", "DiosCh"])
    assert dm.loc[resto, "ERQ_Reap"].isna().all()
    assert pv.auditar(dm, b, ["ERQ_Reap"]) == []


def test_las_columnas_de_identificacion_no_se_tocan():
    d = _d_validos(PUENTE)
    d["Edad"] = 12
    d["_peso"] = 1.0
    dm, suprimidos = pv.aplicar_todo_o_nada(d, pv.base_publicable(d))
    assert set(suprimidos) == {"SDQ_Total"}
    assert dm["Edad"].notna().all() and dm["_peso"].notna().all()


def test_margen_del_resto_dominado_por_un_colegio():
    assert pv.MARGEN_RESTO == 3
    base = {("LauV", "Sexto"): 95, ("LaBalsa", "Décimo"): 32}
    justo = pv.base_publicable(_d({**base, ("CdP", "Décimo"): 8, ("DiosCh", "Sexto"): 3}))
    assert justo.incluye_resto                     # 11 − 8 = 3
    dominado = pv.base_publicable(_d({**base, ("CdP", "Décimo"): 9, ("DiosCh", "Sexto"): 2}))
    assert not dominado.incluye_resto              # 11 − 9 = 2
    assert len(dominado.nivel) == 127


def test_margen_del_resto_por_indicador():
    """El resto llega a 10 respuestas, pero 9 son de un solo colegio."""
    conteos = {("LauV", "Sexto"): (95, 95), ("LaBalsa", "Décimo"): (32, 32),
               ("CdP", "Décimo"): (9, 9), ("DiosCh", "Sexto"): (5, 1)}
    d = _d_validos(conteos)
    b = pv.base_publicable(d)
    assert b.incluye_resto                         # filas: 14 − 9 = 5
    dm, suprimidos = pv.aplicar_todo_o_nada(d, b)
    assert suprimidos == {"SDQ_Total": 10}


@pytest.mark.parametrize("funcion", ["base_publicable", "auditar", "aplicar_todo_o_nada"])
def test_indice_duplicado_se_rechaza(funcion):
    d = _d(DECIMO)
    b = pv.base_publicable(d)
    dup = pd.concat([d.iloc[:5], d.iloc[:5]])
    llamadas = {"base_publicable": lambda: pv.base_publicable(dup),
                "auditar": lambda: pv.auditar(dup, b, []),
                "aplicar_todo_o_nada": lambda: pv.aplicar_todo_o_nada(dup, b)}
    with pytest.raises(ValueError, match="índice"):
        llamadas[funcion]()


def test_las_relaciones_de_nivel_tienen_nombres_distintos():
    nombres = [r[0] for r in pv.relaciones(pv.base_publicable(_d(DECIMO)))]
    assert "Nivel−colegios" in nombres and "Nivel−grados" in nombres
    assert "Nivel" not in nombres


def test_union_conserva_el_tipo_entero():
    u = pv.union([pd.Index([3, 1], dtype="int64"), pd.Index([2], dtype="int64")])
    assert u.dtype == "int64" and list(u) == [1, 2, 3]


def test_ayudantes_publicos_y_alias_antiguos():
    assert pv._union is pv.union and pv._activo is pv.activo
    assert pv.activo("LauV") and not pv.activo(pv.TODOS) and not pv.activo(None)
    assert not pv.activo("")


def test_datos_reales_enmascarados_pasan_la_auditoria():
    from src.core.rutas import carpeta_datos
    from src.estudiantes import ingest, pipeline, scoring
    rutas = pipeline.localizar_formularios(carpeta_datos('estudiantes'))
    if not rutas:
        pytest.skip("Los formularios originales no están en el directorio de trabajo")
    todo, _ = ingest.cargar_varios(rutas)
    todo = scoring.puntuar(todo)
    for nivel, d in todo.groupby("nivel"):
        b = pv.base_publicable(d)
        dm, _ = pv.aplicar_todo_o_nada(d, b)
        assert pv.auditar(dm, b, pv.columnas_de_analisis(dm)) == [], nivel


def test_el_resumen_distingue_lo_que_queda_fuera_del_nivel():
    # PRIMARIA: SJMEB (14) se publica entero; DiosCh (2) queda fuera del nivel
    r = pv.base_publicable(_d(PRIMARIA)).resumen()
    assert r["n_fuera_de_celdas"] == 16
    assert r["n_fuera_del_nivel"] == 2
    assert r["n_solo_en_total"] == 0
    # con un resto grande, las 16 respuestas cuentan solo en el total
    r = pv.base_publicable(_d({**DECIMO, ("DiosCh", "Octavo"): 5})).resumen()
    assert r["incluye_resto"] and r["n_fuera_del_nivel"] == 0
    assert r["n_solo_en_total"] == r["n_fuera_de_celdas"] == 16
