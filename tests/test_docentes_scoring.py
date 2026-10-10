"""
Puntuación de docentes desde los ítems (propuesta 10-oct-2026, §5).

Lo que se protege: la codificación 1 (archivo actual) se recodifica antes de
puntuar; un constructo que no se midió queda faltante (sin imputar) y su N es
el de quienes respondieron; el semáforo sale del corte publicado o del tercio
de la escala teórica, nunca del mínimo y máximo de la muestra; «hijos = 10» es
faltante.
"""
import numpy as np
import pandas as pd
import pytest

from src.docentes import catalogo as cat
from src.docentes import estadistica as est
from src.docentes import limpieza
from src.docentes import scoring


# ══ Estadística ═════════════════════════════════════════════════════════════
def test_ic_t_de_la_media():
    m, inf, sup = est.ic_media(pd.Series([1, 2, 3, 4, 5]))
    assert m == 3 and inf == pytest.approx(1.037, abs=0.01) and sup == pytest.approx(4.963, abs=0.01)
    assert est.ic_media(pd.Series([2.0])) == (2.0, None, None)
    assert est.ic_media(pd.Series([], dtype=float)) == (None, None, None)


def test_wilson():
    p, inf, sup = est.wilson(12, 100)
    assert p == 12.0 and inf == pytest.approx(7.0, abs=0.2) and sup == pytest.approx(19.8, abs=0.2)


@pytest.mark.parametrize("k,n,visible", [(3, 20, True), (2, 20, False), (18, 20, False),
                                         (17, 20, True), (5, 9, False)])
def test_proporcion_protegida(k, n, visible):
    r = est.proporcion_protegida(k, n)
    assert (r["pct"] is not None) is visible
    assert r["n"] == n
    if not visible:
        assert "k" not in r


# ══ Codificación ════════════════════════════════════════════════════════════
def _archivo_v1(n=12, seed=0) -> pd.DataFrame:
    """Un archivo en codificación 1, con todos los ítems del catálogo."""
    rng = np.random.default_rng(seed)
    cols = {"ID": [f"D{i:03d}" for i in range(n)],
            cat.COLUMNA_VERSION: [cat.VERSION_2025] * (n // 2) + [cat.VERSION_2026] * (n - n // 2)}
    for dim in cat.DIMENSIONES:
        lo, hi = dim.escala
        lo, hi = lo - dim.desplazamiento, hi - dim.desplazamiento
        for c in dim.items:
            if c not in cols:
                cols[c] = rng.integers(int(lo), int(hi) + 1, n).astype(float)
    return pd.DataFrame(cols)


def test_detecta_codificacion():
    d = _archivo_v1()
    assert scoring.codificacion(d) == 1
    d[cat.COLUMNA_CODIFICACION] = 2
    assert scoring.codificacion(d) == 2


def test_normalizar_recodifica_solo_la_codificacion_1():
    d = _archivo_v1()
    n = scoring.normalizar_codificacion(d)
    assert (n["IR1"] == 5 - d["IR1"]).all()
    assert (n["PRPS_CE2"] == 4 - d["PRPS_CE2"]).all()
    assert (n["PRPS_CE16"] == 4 - d["PRPS_CE16"]).all()
    assert (n["ERS_ACP1"] == 3 - d["ERS_ACP1"]).all()
    assert (n["PRPS_CE3"] == d["PRPS_CE3"]).all() and (n["IR2"] == d["IR2"]).all()
    assert n[cat.COLUMNA_CODIFICACION].eq(2).all()
    d2 = d.copy()
    d2[cat.COLUMNA_CODIFICACION] = 2
    assert scoring.normalizar_codificacion(d2)["IR1"].equals(d2["IR1"])
    assert "IR1" in d and d["IR1"].equals(_archivo_v1()["IR1"])   # no modifica el original


def test_es_archivo_docentes():
    assert scoring.es_archivo_docentes(_archivo_v1())
    assert not scoring.es_archivo_docentes(pd.DataFrame({"PSS_T": [1, 2], "x": [3, 4]}))
    assert not scoring.es_archivo_docentes(pd.DataFrame({"(BM),(CT)Item": [1]}))


# ══ Puntuación por docente ══════════════════════════════════════════════════
def test_puntuar_media_suma_y_desplazamiento():
    d = _archivo_v1()
    p = scoring.puntuar(d)
    assert list(p.index) == list(d.index)
    assert set(p.columns) == set(cat.claves())
    n = scoring.normalizar_codificacion(d)
    assert p["PSS"].equals(n[[f"PSS{i}" for i in range(1, 11)]].sum(axis=1))
    assert np.allclose(p["MT_Control"], n[["MT1", "MT2", "MT3"]].mean(axis=1))
    assert np.allclose(p["BTA"], n[[f"BTA{i}" for i in range(1, 13)]].mean(axis=1) + 1)
    assert p["BTA"].between(1, 5).all()
    assert np.allclose(p["IR"], n[["IR1", "IR2", "IR3", "IR4"]].mean(axis=1))
    assert p["PRPS_Fam"].equals(d["PRPS_Fam_T"])


def test_sin_imputar_el_n_es_el_de_quienes_respondieron():
    d = _archivo_v1(n=20)
    # Bienestar psicosocial solo se midió en 2025: la ola 2026 queda vacía.
    es_2026 = d[cat.COLUMNA_VERSION] == cat.VERSION_2026
    d.loc[es_2026, [c for c in d.columns if c.startswith("BLG_Psicoso")]] = np.nan
    r = scoring.resumen(d)
    assert r["BLG_Psicoso"]["n"] == 10 and r["PSS"]["n"] == 20
    assert r["BLG_Psicoso"]["nota"] == cat.NOTA_SOLO_2025
    p = scoring.puntuar(d)
    assert p.loc[es_2026, "BLG_Psicoso"].isna().all()


def test_una_suma_con_items_faltantes_queda_vacia_y_una_media_tolera_la_mitad():
    d = _archivo_v1(n=10)
    d.loc[0, "PSS4"] = np.nan             # suma: falta un ítem → NaN
    d.loc[1, ["CL1", "CL2", "CL3"]] = np.nan   # media: 4 de 7 → se puntúa
    d.loc[2, ["CL1", "CL2", "CL3", "CL4"]] = np.nan  # 3 de 7 → NaN
    p = scoring.puntuar(d)
    assert np.isnan(p.loc[0, "PSS"]) and not np.isnan(p.loc[1, "CL"]) and np.isnan(p.loc[2, "CL"])


# ══ Resumen y semáforo anclado ═════════════════════════════════════════════
def _con_media(clave, valor, n=30):
    """Un archivo donde la media de `clave` vale `valor` en la escala de presentación."""
    dim = cat.por_clave(clave)
    d = _archivo_v1(n=n)
    d[cat.COLUMNA_CODIFICACION] = 2
    por_item = valor - dim.desplazamiento
    if dim.agregacion == "suma":
        por_item = por_item / len(dim.items)
    for c in dim.items:
        d[c] = float(por_item)
    return d


@pytest.mark.parametrize("clave,valor,zona", [
    ("PSS", 10, cat.ZONA_FAVORABLE), ("PSS", 14.3, cat.ZONA_INTERMEDIA), ("PSS", 30, cat.ZONA_VIGILAR),
    ("BTA", 1.89, cat.ZONA_FAVORABLE), ("BTA", 2.7, cat.ZONA_INTERMEDIA), ("BTA", 3.5, cat.ZONA_VIGILAR),
    ("ISTAS_Exig", 11.5, cat.ZONA_VIGILAR), ("ISTAS_TA", 26, cat.ZONA_FAVORABLE),
    ("ISTAS_TA", 23.5, cat.ZONA_INTERMEDIA),
])
def test_zona_con_corte_publicado(clave, valor, zona):
    r = scoring.resumen(_con_media(clave, valor))[clave]
    assert r["media"] == pytest.approx(valor, abs=1e-6)
    assert r["zona"] == zona and r["color"] == cat.COLOR_ZONA[zona]
    assert r["banda"] is not None


@pytest.mark.parametrize("clave,valor,zona", [
    ("CR_Claridad", 4.45, cat.ZONA_FAVORABLE),     # mayor = mejor, tercio alto
    ("MT_Control", 2.94, cat.ZONA_INTERMEDIA),
    ("RO", 1.52, cat.ZONA_VIGILAR),
    ("MT_Demandas", 1.35, cat.ZONA_FAVORABLE),     # mayor = peor, tercio bajo
    ("CR_Conflicto", 4.0, cat.ZONA_VIGILAR),
    ("BLG_Desg", 4.0, cat.ZONA_INTERMEDIA),        # 1–7: punto medio
])
def test_zona_sin_corte_por_tercio_de_la_escala_teorica(clave, valor, zona):
    r = scoring.resumen(_con_media(clave, valor))[clave]
    assert r["zona"] == zona and r["banda"] is None


def test_pct_escala_orientada_y_no_depende_de_la_muestra():
    d = _con_media("MT_Demandas", 1.0)
    r = scoring.resumen(d)["MT_Demandas"]
    assert r["pct_escala"] == pytest.approx(80.0)       # (5 − 1) / 5 · 100, orientado
    r2 = scoring.resumen(_con_media("CR_Claridad", 4.0))["CR_Claridad"]
    assert r2["pct_escala"] == pytest.approx(80.0)
    # Con un subconjunto distinto, la zona de la misma media no cambia.
    assert scoring.resumen(d.head(12))["MT_Demandas"]["zona"] == r["zona"]


def test_resumen_trae_ic_alfa_escala_y_direccion():
    r = scoring.resumen(_archivo_v1(n=40))
    for clave, info in r.items():
        dim = cat.por_clave(clave)
        assert info["nombre"] == dim.nombre and info["tema"] == dim.tema
        assert info["escala"] == dim.escala and info["mayor_mejor"] == dim.mayor_mejor
        assert info["ic_inf"] <= info["media"] <= info["ic_sup"]
        assert info["n_items"] == len(dim.items)
        if len(dim.items) >= 2:
            assert info["alfa"] is None or info["alfa"] <= 1   # con datos al azar puede ser negativo
        else:
            assert info["alfa"] is None
    assert r["PSS"]["direccion"] == cat.MAYOR_PEOR
    assert r["PRPS_Fam"]["zona"] == cat.ZONA_SIN_DATO and r["PRPS_Fam"]["pct_escala"] is None


def test_bandas_con_k_minimo_de_3():
    """Un % solo se publica con k ≥ 3 y n − k ≥ 3 (como en Estudiantes y Cuidadores)."""
    d = _con_media("PSS", 10, n=30)
    pss = [f"PSS{i}" for i in range(1, 11)]
    d.loc[[0, 1], pss] = 3.0            # 30 → alto (2 casos: no se publica)
    d.loc[[2, 3, 4], pss] = 2.0         # 20 → moderado (3 casos)
    r = scoring.resumen(d)["PSS"]
    bandas = {b["etiqueta"]: b for b in r["bandas"]}
    assert bandas["Estrés alto"]["pct"] is None and "k" not in bandas["Estrés alto"]
    assert bandas["Estrés moderado"]["pct"] == pytest.approx(10.0) and bandas["Estrés moderado"]["k"] == 3
    assert bandas["Estrés bajo"]["pct"] == pytest.approx(83.3, abs=0.1)
    assert bandas["Estrés bajo"]["ic_inf"] < 83.3 < bandas["Estrés bajo"]["ic_sup"]
    assert all(b["comprobar"] is False for b in r["bandas"])
    assert all(b["comprobar"] for b in scoring.resumen(d)["BTA"]["bandas"])


def test_resumen_con_un_grupo_pequeno_no_devuelve_nada():
    assert scoring.resumen(_archivo_v1(n=9)) == {}
    assert scoring.resumen(pd.DataFrame()) == {}


def test_resumen_solo_tablero():
    r = scoring.resumen(_archivo_v1(n=20), solo_tablero=True)
    assert "PRPS_Fam" not in r and "BTA_Agot" not in r and "PSS" in r


# ══ Códigos de faltante ═════════════════════════════════════════════════════
@pytest.mark.parametrize("columna", ["Número de hijos", "(SD)Numero de hijos"])
def test_hijos_10_pasa_a_faltante(columna):
    d = pd.DataFrame({columna: [0, 1, 10, 2, 10, np.nan], "PSS1": range(6)})
    out, informe = limpieza.codigos_faltantes(d)
    assert out[columna].isna().sum() == 3 and (out[columna].max() == 2)
    assert informe == {columna: 2}
    assert d[columna].eq(10).sum() == 2                 # no modifica el original


def test_sin_columna_de_hijos_no_pasa_nada():
    d = pd.DataFrame({"PSS1": [1, 2]})
    out, informe = limpieza.codigos_faltantes(d)
    assert out.equals(d) and informe == {}
