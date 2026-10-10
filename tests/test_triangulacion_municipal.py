"""Triangulación · cifras municipales de la capa 1 (sustento de los hallazgos 3, 4, 5 y 8)."""
import numpy as np
import pandas as pd
import pytest

from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import fuentes as fu
from tests import triangulacion_span as span


# ── señales de estudiantes (hallazgo 3) ─────────────────────────────────────
def _secundaria(celdas: dict, item18, malestar) -> pd.DataFrame:
    """celdas: {(colegio, grado): n}; item18 y malestar: funciones de i → valor."""
    filas, i = [], 0
    for (colegio, grado), n in celdas.items():
        for _ in range(n):
            filas.append(dict(nivel="secundaria", Colegio=colegio, Grado=grado,
                              RCADS18=float(item18(i)), ALERTA_malestar=float(malestar(i))))
            i += 1
    return pd.DataFrame(filas)


def test_senales_con_cifras_conocidas():
    # 60 estudiantes: ítem 18 frecuente en los 30 pares; malestar en 12 de esos y en 12 del resto.
    d = _secundaria({("A", "Sexto"): 30, ("B", "Sexto"): 30},
                    item18=lambda i: 2 if i % 2 == 0 else 1,
                    malestar=lambda i: 1 if i % 5 in (0, 1) else 0)
    t = c1.senales(d, c1.atomos(d, cat.ESTUDIANTE))
    por = {f["clave"]: f for f in t}
    assert por["item18_frecuente"]["valor"] == pytest.approx(50.0)
    assert por["malestar"]["valor"] == pytest.approx(40.0)
    assert por["malestar_entre_item18"]["valor"] == pytest.approx(40.0)
    assert all(f["n"] == 60 and f["motivo"] == "" for f in t)
    assert por["malestar_entre_item18"]["ic_inf"] < 40 < por["malestar_entre_item18"]["ic_sup"]


def test_senales_exige_10_en_cada_celda_del_cruce():
    d = _secundaria({("A", "Sexto"): 30, ("B", "Sexto"): 30},
                    item18=lambda i: 2 if i % 2 == 0 else 1,
                    malestar=lambda i: 1 if i < 10 else 0)       # 5 con las dos señales
    t = c1.senales(d, c1.atomos(d, cat.ESTUDIANTE))
    assert t and all(np.isnan(f["valor"]) and f["motivo"] for f in t)
    assert not any(k in f for f in t for k in ("casos", "k_bajo", "k_alto"))


def test_senales_solo_secundaria():
    d = _secundaria({("A", "Sexto"): 30, ("B", "Sexto"): 30},
                    item18=lambda i: 2 if i % 2 == 0 else 1,
                    malestar=lambda i: 1 if i % 5 in (0, 1) else 0)
    pri = d.iloc[:20].assign(nivel="primaria", Grado="Quinto", RCADS18=np.nan)
    d = pd.concat([d, pri], ignore_index=True)
    t = c1.senales(d, c1.atomos(d, cat.ESTUDIANTE))
    assert {f["n"] for f in t} == {60}


def test_senales_sin_columnas_da_motivo():
    d = _secundaria({("A", "Sexto"): 30}, item18=lambda i: 2, malestar=lambda i: 0)
    t = c1.senales(d.drop(columns=["RCADS18"]), c1.atomos(d, cat.ESTUDIANTE))
    assert t and all(f["motivo"] for f in t)


# ── apoyo familiar y ánimo del cuidador (hallazgo 4) ────────────────────────
def _cuidadores(n_por_colegio: dict, apoyo, epds) -> pd.DataFrame:
    filas, i = [], 0
    for colegio, n in n_por_colegio.items():
        for _ in range(n):
            filas.append(dict(Colegio=colegio, Grado="Sexto", ID_cuidador=f"c{i}",
                              MSPSS_Fam=float(apoyo(i)), EPDS_Probable=float(epds(i)),
                              EPDS_Total=float(epds(i)) * 14))
            i += 1
    return pd.DataFrame(filas)


def test_apoyo_animo_por_terciles():
    # 90 cuidadores; apoyo creciente con i; EPDS ≥ 13 en el tercil bajo 60 %, medio 30 %, alto 10 %.
    def epds(i):
        tercil = i // 30
        return 1 if (i % 30) < (18, 9, 3)[tercil] else 0
    d = _cuidadores({"A": 45, "B": 45}, apoyo=lambda i: 1 + 4 * i / 89, epds=epds)
    t = c1.apoyo_animo(d, c1.atomos(d, cat.CUIDADOR))
    assert [f["grupo"] for f in t] == list(c1.TERCILES)
    assert [f["n"] for f in t] == [30, 30, 30]
    assert [f["valor"] for f in t] == [pytest.approx(60.0), pytest.approx(30.0),
                                        pytest.approx(10.0)]
    assert t[0]["ic_inf"] > t[2]["ic_sup"]


def test_apoyo_animo_se_suprime_si_un_tercil_tiene_menos_de_3_casos():
    d = _cuidadores({"A": 45, "B": 45}, apoyo=lambda i: 1 + 4 * i / 89,
                    epds=lambda i: 1 if i < 20 else 0)          # tercil alto sin casos
    t = c1.apoyo_animo(d, c1.atomos(d, cat.CUIDADOR))
    assert t and all(np.isnan(f["valor"]) and f["motivo"] for f in t)


def test_apoyo_animo_cuenta_cuidadores_distintos():
    d = _cuidadores({"A": 45, "B": 45}, apoyo=lambda i: 1 + 4 * i / 89,
                    epds=lambda i: 1 if (i % 30) < 9 else 0)
    d["ID_cuidador"] = "c" + (d.index // 4).astype(str)      # 23 cuidadores en 90 filas
    t = c1.apoyo_animo(d, c1.atomos(d, cat.CUIDADOR))
    assert t and all(np.isnan(f["valor"]) and f["motivo"] for f in t)   # < 10 por tercil


# ── PSS en cuidadores y docentes (hallazgo 5) ───────────────────────────────
def test_pss_actores_media_ic_y_d():
    cuid = _cuidadores({"A": 30}, apoyo=lambda i: 3, epds=lambda i: 0)
    cuid["PSS_Total"] = [14.0 + (i % 5) for i in range(30)]
    doc = pd.DataFrame([dict(Colegio="A", DOC_PSS=14.0 + (i % 5)) for i in range(30)])
    tablas = {cat.CUIDADOR: cuid, cat.DOCENTE: doc}
    por_marco = {cat.CUIDADOR: c1.atomos(cuid, cat.CUIDADOR), cat.DOCENTE: c1.atomos(doc, cat.DOCENTE)}
    t = c1.pss_actores(tablas, por_marco)
    por = {f["clave"]: f for f in t}
    assert por["cuidadores"]["valor"] == pytest.approx(16.0) == por["docentes"]["valor"]
    assert por["cuidadores"]["n"] == 30 and por["docentes"]["n"] == 30
    assert por["diferencia"]["valor"] == pytest.approx(0.0)
    assert por["diferencia"]["ic_inf"] < 0 < por["diferencia"]["ic_sup"]
    assert por["diferencia"]["n"] == 60


def test_pss_actores_con_pocos_da_motivo():
    cuid = _cuidadores({"A": 5}, apoyo=lambda i: 3, epds=lambda i: 0).assign(PSS_Total=14.0)
    doc = pd.DataFrame([dict(Colegio="A", DOC_PSS=14.0) for i in range(30)])
    tablas = {cat.CUIDADOR: cuid, cat.DOCENTE: doc}
    por_marco = {m: c1.atomos(tablas[m], m) for m in tablas}
    t = c1.pss_actores(tablas, por_marco)
    assert all(np.isnan(f["valor"]) and f["motivo"] for f in t)


# ── desgaste docente (hallazgo 8) ───────────────────────────────────────────
def _docentes(n: int, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dem = rng.normal(size=n)
    conf = rng.normal(size=n)
    lider = rng.normal(size=n)
    desg = 4 + 0.6 * dem + 0.4 * conf + 0.05 * lider + rng.normal(scale=0.5, size=n)
    colegios = [chr(65 + i % 8) for i in range(n)]            # 8 colegios (G − 1 gl)
    return pd.DataFrame(dict(Colegio=colegios,
                             DOC_DESGASTE=desg, DOC_DEMANDAS=dem + 2, DOC_CONFLICTO_ROL=conf + 2,
                             DOC_LIDER=lider + 3, DOC_PSS=14.0))


def test_desgaste_docente_una_fila_por_predictor():
    d = _docentes(120)
    t = c1.desgaste_docente(d, c1.atomos(d, cat.DOCENTE))
    por = {f["clave"]: f for f in t}
    assert set(por) == {k for k, _ in c1.PREDICTORES_DESGASTE}
    assert por["demandas"]["ic_inf"] > 0 and por["conflicto_rol"]["ic_inf"] > 0
    assert por["lider"]["ic_inf"] < 0 < por["lider"]["ic_sup"]
    assert all(f["n"] == 120 and f["motivo"] == "" for f in t)


def test_desgaste_docente_sin_las_dimensiones_da_motivo():
    d = _docentes(120).drop(columns=["DOC_DEMANDAS"])
    t = c1.desgaste_docente(d, c1.atomos(d, cat.DOCENTE))
    assert t and all(np.isnan(f["valor"]) and f["motivo"] for f in t)


def test_puntuar_docentes_suma_las_dimensiones_opcionales():
    filas = []
    for i in range(12):
        f = {"Colegio": "Colegio Laura Vicuña"}
        f.update({f"PSS{j}": 2 for j in range(1, 11)})
        f.update({f"CL{j}": 3 for j in range(1, 8)})
        f.update({f"AP{j}": 3 for j in range(1, 4)})
        f.update({f"BLG_Desg{j}": 4 for j in range(1, 5)})
        f.update({f"MT{j}": j % 3 for j in range(1, 8)})
        f.update({f"CR{j}": 1 + j % 2 for j in range(1, 8)})
        filas.append(f)
    bruto = pd.DataFrame(filas)
    p = fu.puntuar_docentes(bruto)
    assert p["DOC_DEMANDAS"].iloc[0] == pytest.approx(np.mean([4 % 3, 5 % 3, 6 % 3, 7 % 3]))
    assert p["DOC_CONFLICTO_ROL"].iloc[0] == pytest.approx(np.mean([1 + 5 % 2, 1 + 6 % 2, 1 + 7 % 2]))
    sin = fu.puntuar_docentes(bruto.drop(columns=[f"MT{j}" for j in range(1, 8)]))
    assert "DOC_DEMANDAS" not in sin.columns and "DOC_CONFLICTO_ROL" in sin.columns
    assert fu.es_docentes_codificado(bruto.drop(columns=[f"MT{j}" for j in range(1, 8)]))


# ── la tabla entera y su auditoría ──────────────────────────────────────────
def test_municipal_arma_la_tabla_con_las_columnas_fijas():
    est = _secundaria({("A", "Sexto"): 30, ("B", "Sexto"): 30},
                      item18=lambda i: 2 if i % 2 == 0 else 1,
                      malestar=lambda i: 1 if i % 5 in (0, 1) else 0)
    cuid = _cuidadores({"A": 45, "B": 45}, apoyo=lambda i: 1 + 4 * i / 89,
                       epds=lambda i: 1 if (i % 30) < 9 else 0).assign(PSS_Total=14.0)
    cuid["PSS_Total"] += cuid.index % 5
    doc = _docentes(120)
    tablas = {cat.ESTUDIANTE: est, cat.CUIDADOR: cuid, cat.NINO: cuid.iloc[0:0],
              cat.DOCENTE: doc}
    por_marco = {m: c1.atomos(tablas[m], m) for m in tablas}
    t = c1.municipal(tablas, por_marco)
    assert list(t.columns) == c1.COLUMNAS_MUNICIPAL
    assert set(t["bloque"]) == {c1.BLOQUE_SENALES, c1.BLOQUE_APOYO_ANIMO, c1.BLOQUE_PSS,
                                c1.BLOQUE_DESGASTE}
    con = t[t["valor"].notna()]
    assert (con["n"] >= cat.MIN_GROUP_N).all()
    # auditoría de restas: señales y terciles junto a lo que publican los módulos
    for marco in (cat.ESTUDIANTE, cat.CUIDADOR):
        assert span.auditar_municipal(tablas, por_marco, marco) == 0
