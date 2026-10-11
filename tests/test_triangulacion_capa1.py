"""Triangulación · capa 1 por colegio y por grado."""
import numpy as np
import pandas as pd
import pytest

from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import fuentes as fu
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def fuentes_sint(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_capa1"))
    mp = pytest.MonkeyPatch()
    mp.setenv("OBS360_DATOS_DIR", base)
    try:
        yield fu.cargar(k=K)
    finally:
        mp.undo()


@pytest.fixture(scope="module")
def capa(fuentes_sint):
    return c1.analizar(fuentes_sint)


def _fila(clave, d, lo, hi):
    return pd.Series(dict(clave=clave, d=d, ic_inf=lo, ic_sup=hi))


def test_clasificacion_mismo_objeto():
    par = next(p for p in cat.PARES if p.a == "est_pssm" and p.b == "doc_lider")
    # pertenencia (+) más alta y apoyo del líder (+) más alto: coincidencia
    assert c1.clasificar(par, _fila("est_pssm", .4, .1, .7),
                         _fila("doc_lider", .5, .2, .8)) == cat.COINCIDENCIA
    assert c1.clasificar(par, _fila("est_pssm", .4, .1, .7),
                         _fila("doc_lider", -.5, -.8, -.2)) == cat.TENSION
    assert c1.clasificar(par, _fila("est_pssm", .4, -.1, .7),
                         _fila("doc_lider", -.5, -.8, -.2)) == cat.SIN_DIFERENCIA
    assert c1.clasificar(par, None, _fila("doc_lider", .5, .2, .8)) == cat.SIN_DATO


def test_la_orientacion_respeta_la_direccion():
    """«Sin adulto» (riesgo) más alto y apoyo del líder (protector) más bajo: coinciden."""
    par = next(p for p in cat.PARES if p.a == "est_sin_adulto" and p.b == "doc_lider")
    assert c1.clasificar(par, _fila("est_sin_adulto", .4, .1, .7),
                         _fila("doc_lider", -.5, -.8, -.2)) == cat.COINCIDENCIA


def test_coocurrencia_nunca_es_acuerdo():
    par = next(p for p in cat.PARES if p.a == "cui_pss" and p.b == "doc_pss")
    assert par.tipo == cat.COOCURRENCIA
    assert c1.clasificar(par, _fila("cui_pss", .4, .1, .7),
                         _fila("doc_pss", .5, .2, .8)) == cat.COOCURRENCIA


def test_pares_de_mismo_objeto_son_los_de_la_spec():
    """Spec §5.6 más los ajustes del 10 oct 2026: apoyo familiar niño–cuidador es
    el mismo objeto (la misma familia) y entran conducta e hiperactividad."""
    mismos = {(p.a, p.b) for p in cat.PARES if p.tipo == cat.MISMO_OBJETO}
    assert mismos == {("est_sdq_total", "nin_sdq_total"), ("est_sdq_emo", "nin_sdq_emo"),
                      ("est_sdq_con", "nin_sdq_con"), ("est_sdq_hip", "nin_sdq_hip"),
                      ("est_pssm", "doc_lider"), ("est_pssm", "doc_grupo"),
                      ("est_sin_adulto", "doc_lider"), ("est_sin_adulto", "doc_grupo"),
                      ("est_mspss_fam", "cui_mspss_fam")}


def test_todo_constructo_tiene_etiqueta_corta_y_columna_conocida():
    for c in cat.CONSTRUCTOS:
        assert c.corta and len(c.corta) <= 40, c.clave
        assert c.objeto and c.direccion in (1, -1)
    assert len({c.clave for c in cat.CONSTRUCTOS}) == len(cat.CONSTRUCTOS)


def _estudiantes_por_grado(plan) -> pd.DataFrame:
    """plan: (colegio, grado, n, media). Valor = media + ruido determinista pequeño."""
    filas = []
    for colegio, grado, n, media in plan:
        for i in range(n):
            filas.append(dict(nivel="secundaria", Colegio=colegio, Grado=grado,
                              PSSM_Total=media + ((i * 7) % 5 - 2) * 0.05))
    return pd.DataFrame(filas)


def test_ajuste_por_grado_quita_la_composicion_de_grados():
    """A solo tiene Noveno (pertenencia baja en todo el municipio por ser Noveno)
    y B solo Sexto. Sin ajuste A sale «peor»; ajustado por grado no difiere."""
    d = _estudiantes_por_grado((("A", "Noveno", 15, 2.5), ("B", "Sexto", 15, 3.5),
                                ("C", "Noveno", 15, 2.5), ("C", "Sexto", 15, 3.5)))
    c = cat.POR_CLAVE["est_pssm"]
    lista = c1.atomos(d, cat.ESTUDIANTE)
    bruto = c1.diferencias_constructo(d, lista, c, ["A"], "Colegio", ajuste_grado=False)[0]
    ajustado = c1.diferencias_constructo(d, lista, c, ["A"], "Colegio")[0]
    assert bruto["ic_sup"] < 0 and bruto["ajuste"] == ""
    assert ajustado["ajuste"] == c1.AJUSTE_GRADO
    assert ajustado["ic_inf"] < 0 < ajustado["ic_sup"]
    assert ajustado["media_grupo"] == bruto["media_grupo"]      # las medias siguen brutas
    assert ajustado["de_actor"] == bruto["de_actor"]
    assert ajustado["n_grupo"] == 15 and ajustado["n_resto"] == 45


def test_el_ajuste_por_grado_solo_aplica_a_estudiantes_por_colegio(capa):
    dif, grado = capa.diferencias, capa.por_grado
    est = dif["actor"] == "Estudiantes"
    assert (dif.loc[est & dif["d"].notna(), "ajuste"] == c1.AJUSTE_GRADO).all()
    assert (dif.loc[~est, "ajuste"] == "").all()
    assert (grado["ajuste"] == "").all()


def test_con_ajuste_apagado_d_es_el_bruto_y_ajuste_vacio():
    d = _estudiantes_por_grado((("A", "Noveno", 15, 2.5), ("B", "Sexto", 15, 3.5)))
    c = cat.POR_CLAVE["est_pssm"]
    f = c1.diferencias_constructo(d, c1.atomos(d, cat.ESTUDIANTE), c, ["A"], "Colegio",
                                  ajuste_grado=False)[0]
    x, y = d.loc[d.Colegio == "A", "PSSM_Total"], d.loc[d.Colegio == "B", "PSSM_Total"]
    assert f["ajuste"] == "" and f["motivo"] == ""
    assert f["d"] == pytest.approx(round((x.mean() - y.mean()) / d["PSSM_Total"].std(ddof=1), 3))


def test_grados_vacios_en_el_universo_no_se_ajusta_en_silencio():
    d = _estudiantes_por_grado((("A", "Noveno", 15, 2.5), ("B", "Sexto", 15, 3.5),
                                ("C", "Noveno", 15, 2.5), ("C", "Sexto", 15, 3.5)))
    d.loc[d.index[:3], "Grado"] = None            # 3 sin grado (siguen en el colegio A)
    d["Grado"] = d["Grado"].fillna("Noveno")      # átomos como antes…
    d2 = d.copy()
    c = cat.POR_CLAVE["est_pssm"]
    lista = c1.atomos(d2, cat.ESTUDIANTE)
    d2.loc[d2.index[:3], "Grado"] = None          # …pero el grado falta al ajustar
    f = c1.diferencias_constructo(d2, lista, c, ["A"], "Colegio")[0]
    bruto = c1.diferencias_constructo(d2, lista, c, ["A"], "Colegio", ajuste_grado=False)[0]
    assert f["ajuste"] == "" and f["d"] == bruto["d"]
    assert f["motivo"] == c1.MOTIVO_SIN_GRADO.format(n="<10")
    assert "3" not in f["motivo"]                 # el conteo pequeño no se muestra


def _docentes(conteos: dict, valor=lambda i: float(i % 5)) -> pd.DataFrame:
    filas = [dict(Colegio=c, DOC_PSS=valor(i)) for c, n in conteos.items() for i in range(n)]
    return pd.DataFrame(filas)


def test_el_resto_con_1_a_9_sale_del_constructo():
    d = _docentes({"A": 12, "B": 15, "C": 4})
    atomos = c1.atomos(d, cat.DOCENTE)
    assert [a.nombre for a in atomos] == ["A", "B"]          # C (4) no es átomo ni resto
    c = cat.POR_CLAVE["doc_pss"]
    filas = c1.diferencias_constructo(d, atomos, c, ["A", "B"], "Colegio")
    assert [f["n_grupo"] for f in filas] == [12, 15]
    assert [f["n_resto"] for f in filas] == [15, 12]          # el resto no incluye a C


def test_el_resto_con_10_o_mas_de_dos_colegios_entra():
    d = _docentes({"A": 12, "B": 15, "C": 6, "D": 6})
    assert [a.nombre for a in c1.atomos(d, cat.DOCENTE)][-1] == c1.RESTO


def test_un_grupo_con_menos_de_10_con_dato_no_se_muestra():
    d = _docentes({"A": 12, "B": 15})
    d.loc[d.index[:5], "DOC_PSS"] = np.nan                     # A queda con 7 con dato
    c = cat.POR_CLAVE["doc_pss"]
    filas = c1.diferencias_constructo(d, c1.atomos(d, cat.DOCENTE), c, ["A", "B"], "Colegio")
    assert np.isnan(filas[0]["d"]) and filas[0]["motivo"] == c1.MOTIVO_POCOS
    assert filas[1]["motivo"] == c1.MOTIVO_RESTO               # su resto sería A (7)


def test_binario_con_menos_de_3_casos_no_se_muestra():
    filas = []
    for colegio, casos in (("A", 2), ("B", 6), ("C", 5)):
        for i in range(12):
            filas.append(dict(Colegio=colegio, Grado="Sexto", SIN_ADULTO=float(i < casos)))
    d = pd.DataFrame(filas)
    c = cat.POR_CLAVE["est_sin_adulto"]
    res = c1.diferencias_constructo(d, c1.atomos(d, cat.ESTUDIANTE), c, ["A", "B", "C"],
                                    "Colegio")
    assert np.isnan(res[0]["d"])
    assert res[1]["media_grupo"] == pytest.approx(50.0)        # % con 1 decimal
    assert res[1]["n_resto"] == 12                             # el resto de B es solo C


def test_diferencia_estandarizada_e_ic():
    d = _docentes({"A": 10, "B": 10}, valor=lambda i: float(i))
    d.loc[d["Colegio"] == "A", "DOC_PSS"] += 5
    c = cat.POR_CLAVE["doc_pss"]
    f = c1.diferencias_constructo(d, c1.atomos(d, cat.DOCENTE), c, ["A"], "Colegio")[0]
    x, y = d.loc[d.Colegio == "A", "DOC_PSS"], d.loc[d.Colegio == "B", "DOC_PSS"]
    de = d["DOC_PSS"].std(ddof=1)
    se = np.sqrt(x.var() / 10 + y.var() / 10) / de
    assert f["d"] == pytest.approx(round(5 / de, 3))
    assert f["ic_inf"] == pytest.approx(round(5 / de - 1.959964 * se, 3), abs=1e-3)
    assert f["d_orientada"] == pytest.approx(-f["d"])          # PSS: más es peor


def test_colegios_y_grados_sinteticos(capa):
    # La Balsa no tiene cuidadores con hijos en los grados del estudio.
    assert capa.colegios == ["JJC", "LauV", "SJMEB"]
    assert capa.grados and set(capa.grados) <= {"Cuarto", "Quinto", "Sexto", "Séptimo",
                                                 "Octavo", "Noveno", "Décimo"}
    assert set(capa.diferencias["grupo"]) == set(capa.colegios)


def test_por_grado_solo_estudiantes_y_cuidadores(capa):
    assert set(capa.por_grado["actor"]) <= {"Estudiantes", "Cuidadores"}
    assert not capa.por_grado["clave"].str.startswith("doc_").any()


def test_toda_cifra_mostrada_tiene_10_o_mas(capa):
    for t in (capa.diferencias, capa.por_grado):
        con = t[t["d"].notna()]
        assert (con["n_grupo"] >= cat.MIN_GROUP_N).all()
        assert (con["n_resto"] >= cat.MIN_GROUP_N).all()
        sin = t[t["d"].isna()]
        assert sin[["media_grupo", "media_resto", "n_grupo"]].isna().all().all()


def test_cuidadores_cuentan_distintos(fuentes_sint):
    tablas = c1.marcos(fuentes_sint)
    for m in (cat.CUIDADOR, cat.NINO):                       # solo átomos en los grados
        for a in c1.atomos(tablas[m], m):
            assert tablas[m].loc[a.idx, "Grado"].notna().all()
    for a in c1.atomos(tablas[cat.NINO], cat.NINO):
        if a.nombre != c1.RESTO:
            assert tablas[cat.NINO].loc[a.idx, "ID_cuidador"].nunique() >= cat.MIN_GROUP_N


def test_clasificacion_tiene_todos_los_pares_por_colegio(capa):
    assert len(capa.clasificacion) == len(cat.PARES) * len(capa.colegios)
    assert set(capa.clasificacion["clasificacion"]) <= {
        cat.COINCIDENCIA, cat.TENSION, cat.SIN_DIFERENCIA, cat.COOCURRENCIA, cat.SIN_DATO}


# ── I1: los átomos son exactamente la base que publica cada módulo ──────────
from src.estudiantes import catalog as cat_est          # noqa: E402
from src.estudiantes import privacidad as pe            # noqa: E402
from tests import triangulacion_span as span             # noqa: E402


def _estudiantes_dos_niveles() -> pd.DataFrame:
    """Primaria: A con celdas y B (4) solo: su R no entra. Secundaria: A con
    celdas, C (6) y D (6): su R (12, de 2 colegios) sí entra. Combinando los dos
    niveles, R = B + C + D entraría y B (4) saldría restando."""
    filas = []
    plan = ((cat_est.NIVEL_PRIMARIA, "A", "Cuarto", 12), (cat_est.NIVEL_PRIMARIA, "A", "Quinto", 12),
            (cat_est.NIVEL_PRIMARIA, "B", "Cuarto", 4),
            (cat_est.NIVEL_SECUNDARIA, "A", "Sexto", 12),
            (cat_est.NIVEL_SECUNDARIA, "A", "Séptimo", 12),
            (cat_est.NIVEL_SECUNDARIA, "C", "Sexto", 6), (cat_est.NIVEL_SECUNDARIA, "D", "Sexto", 6))
    for nivel, colegio, grado, n in plan:
        for _ in range(n):
            filas.append(dict(nivel=nivel, Colegio=colegio, Grado=grado,
                              SDQ_Total=float((7 * len(filas)) % 23)))
    return pd.DataFrame(filas)


def test_atomos_de_estudiantes_por_nivel():
    d = _estudiantes_dos_niveles()
    lista = c1.atomos(d, cat.ESTUDIANTE)
    restos = [a for a in lista if a.nombre == c1.RESTO]
    assert len(restos) == 1                                  # solo el R de secundaria
    assert set(d.loc[restos[0].idx, "Colegio"]) == {"C", "D"}
    assert not (d.loc[pe.union(a.idx for a in lista), "Colegio"] == "B").any()


def test_capa1_y_estudiantes_juntos_no_deducen_piezas_pequenas():
    d = _estudiantes_dos_niveles()
    c = cat.POR_CLAVE["est_sdq_total"]
    lista = c1.atomos(d, cat.ESTUDIANTE)
    conjuntos = (span.conjuntos_capa1(d, lista, c, {"Colegio": ["A"], "Grado": []})
                 + span.conjuntos_modulo(d, cat.ESTUDIANTE, c.columna))
    assert span.piezas_deducibles(d, conjuntos, None) == 0


def _cuidadores_con_grado_fuera() -> pd.DataFrame:
    """Colegios A y B con celdas en los grados del estudio; E sin celdas (12
    cuidadores, 3 con el hijo fuera de los grados) se publica entero."""
    filas = []
    for colegio, grado, n in (("A", "Sexto", 12), ("A", None, 3), ("B", "Sexto", 11),
                              ("E", "Sexto", 5), ("E", "Quinto", 4), ("E", None, 3)):
        for _ in range(n):
            filas.append(dict(Colegio=colegio, Grado=grado, ID_cuidador=f"c{len(filas)}",
                              PSS_Total=float((5 * len(filas)) % 17)))
    return pd.DataFrame(filas)


def test_cuidadores_el_filtro_de_grado_quita_atomos_enteros():
    d = _cuidadores_con_grado_fuera()
    lista = c1.atomos(d, cat.CUIDADOR)
    assert {a.nombre for a in lista} == {"A|Sexto", "B|Sexto"}   # E (mixto) y R salen enteros
    for a in lista:
        assert d.loc[a.idx, "Grado"].notna().all()
    c = cat.POR_CLAVE["cui_pss"]
    conjuntos = (span.conjuntos_capa1(d, lista, c, {"Colegio": ["A", "B"], "Grado": ["Sexto"]})
                 + span.conjuntos_modulo(d, cat.CUIDADOR, c.columna))
    assert span.piezas_deducibles(d, conjuntos, "ID_cuidador") == 0


def test_aviso_del_resto_dice_que_entra_en_el_resto():
    aviso = cat.AVISO_RESTO
    assert "OTRO" in aviso and "menos de 10" in aviso
    assert "reconocidos" not in aviso          # el resto incluye no reconocidos
