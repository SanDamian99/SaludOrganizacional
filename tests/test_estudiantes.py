"""
Pruebas del módulo Estudiantes 360.

Dos capas:
  1. Unitarias con datos sintéticos de resultado conocido (inversos, prorrateo,
     bandas, Wilson, invalidación del ERQ, anonimización). Corren siempre.
  2. Regresión contra la corrida de referencia
     (docs/instrumentos/fixtures/resultados_preliminares_estudiantes.json).
     Se omiten si los CSV originales no están en el directorio de trabajo.
"""
import json
import os

import numpy as np
import pandas as pd
import pytest

from src.core.rutas import carpeta_datos

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, scoring, stats

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(RAIZ, "docs", "instrumentos", "fixtures",
                       "resultados_preliminares_estudiantes.json")


# ══ 1. Catálogo ═════════════════════════════════════════════════════════════
def test_catalogo_conteo_de_items():
    esperado = {"SDQ": 25, "ARI": 7, "RCADS": 25, "ERQ": 10, "MSPSS": 12, "PSSM": 18, "TD": 10}
    assert {e.key: e.n_items for e in cat.ESCALAS} == esperado


def test_catalogo_subescalas_cubren_sus_items_sin_solaparse():
    # SDQ: las cinco subescalas reparten los 25 ítems exactamente una vez
    usados = [i for s in cat.SDQ.subescalas for i in s.items]
    assert sorted(usados) == list(range(1, 26))
    # RCADS: depresión y ansiedad son disjuntas y suman 25
    dep, anx = set(cat.RCADS_DEP_ITEMS), set(cat.RCADS_ANX_ITEMS)
    assert not dep & anx and len(dep | anx) == 25
    # ERQ: reevaluación (6) y supresión (4)
    tam = {s.key: len(s.items) for s in cat.ERQ.subescalas}
    assert tam == {"ERQ_Reap": 6, "ERQ_Sup": 4}


def test_catalogo_inversos_conocidos():
    inversos_sdq = {i for s in cat.SDQ.subescalas for i in s.reverse}
    assert inversos_sdq == set(cat.SDQ_REVERSE_ITEMS) == {7, 11, 14, 21, 25}
    assert cat.PSSM_REVERSE_ITEMS == (3, 6, 9, 12, 16)


def test_ari_excluye_el_item_de_deterioro_del_total():
    total = cat.subescala("ARI_Total")
    assert 7 not in total.items and len(total.items) == 6
    assert total.rango == (0, 12)


def test_bandas_autoinforme_distintas_de_padres():
    assert cat.BANDS_SELF["SDQ_Total"][0] == (0, 14)
    assert cat.BANDS_PARENT["SDQ_Total"][0] == (0, 13)
    assert cat.BANDS_SELF != cat.BANDS_PARENT


@pytest.mark.parametrize("valor,banda", [(0, 0), (14, 0), (15, 1), (17, 1),
                                          (18, 2), (19, 2), (20, 3), (40, 3)])
def test_bandas_sdq_total(valor, banda):
    assert cat.banda_de(valor, "SDQ_Total", "self") == banda


def test_banda_prosocial_se_lee_al_reves():
    assert cat.banda_de(10, "SDQ_Pro", "self") == 0      # alto = bien
    assert cat.banda_de(0, "SDQ_Pro", "self") == 3       # bajo = muy bajo
    assert "disminuido" in cat.etiqueta_banda("SDQ_Pro", 1)


def test_mensajes_de_ideacion_no_llegan_a_familias():
    assert "familia" not in cat.MENSAJES["ideacion"].solo_roles


# ══ 2. Puntuación con datos sintéticos ══════════════════════════════════════
def _fila_sdq(valores: dict, nivel="secundaria", **extra):
    base = {f"SDQ{i}": 0 for i in range(1, 26)}
    base.update(valores)
    base.update(dict(nivel=nivel, Edad=13, Sexo="Mujer", Grado="Séptimo",
                     Colegio="LauV", ID="E0"))
    base.update(extra)
    return base


def test_inversion_de_items():
    e = cat.SDQ
    assert scoring.invertir(pd.Series([0, 1, 2]), e).tolist() == [2, 1, 0]
    assert scoring.invertir(pd.Series([1, 3, 5]), cat.PSSM).tolist() == [5, 3, 1]


def test_sdq_subescalas_con_inversos():
    # Hiperactividad = ítems 2,10,15 directos + 21,25 inversos.
    # Todo en 0 salvo los inversos en 0 → 2+2 = 4 por los inversos.
    d = pd.DataFrame([_fila_sdq({})])
    r = scoring.puntuar(d)
    assert r["SDQ_Hip"].iloc[0] == 4          # 0+0+0 + (2-0) + (2-0)
    assert r["SDQ_Con"].iloc[0] == 2          # ítem 7 inverso
    assert r["SDQ_Pares"].iloc[0] == 4        # ítems 11 y 14 inversos
    assert r["SDQ_Emo"].iloc[0] == 0
    assert r["SDQ_Pro"].iloc[0] == 0
    assert r["SDQ_Total"].iloc[0] == 10       # 0 + 2 + 4 + 4


def test_sdq_maximo_teorico():
    d = pd.DataFrame([_fila_sdq({f"SDQ{i}": 2 for i in range(1, 26)})])
    r = scoring.puntuar(d)
    # Con todo en 2, los inversos pasan a 0
    assert r["SDQ_Emo"].iloc[0] == 10 and r["SDQ_Pro"].iloc[0] == 10
    assert r["SDQ_Con"].iloc[0] == 8          # cuatro directos en 2, uno inverso en 0
    assert r["SDQ_Total"].iloc[0] == 10 + 8 + 6 + 6


def test_prorrateo_con_un_faltante():
    v = {f"SDQ{i}": 2 for i in (3, 8, 13, 16)}
    v["SDQ24"] = np.nan                       # falta uno de los cinco emocionales
    d = pd.DataFrame([_fila_sdq(v)])
    r = scoring.puntuar(d)
    assert r["SDQ_Emo"].iloc[0] == 10         # 8 * 5/4 = 10


def test_faltan_dos_items_deja_la_subescala_vacia():
    v = {f"SDQ{i}": 2 for i in (3, 8, 13)}
    v["SDQ16"] = np.nan
    v["SDQ24"] = np.nan
    d = pd.DataFrame([_fila_sdq(v)])
    r = scoring.puntuar(d)
    assert pd.isna(r["SDQ_Emo"].iloc[0])
    assert pd.isna(r["SDQ_Total"].iloc[0])    # el total exige las cuatro subescalas


def test_pssm_invierte_los_negativos():
    fila = {f"PSSM{i}": 5 for i in range(1, 19)}
    for i in cat.PSSM_REVERSE_ITEMS:
        fila[f"PSSM{i}"] = 1                  # invertidos pasan a 5
    d = pd.DataFrame([_fila_sdq({}, **fila)])
    r = scoring.puntuar(d)
    assert r["PSSM_Total"].iloc[0] == 5.0


def test_alpha_es_uno_con_items_identicos_y_baja_con_ruido():
    rng = np.random.default_rng(0)
    base = rng.integers(0, 3, 60)
    igual = pd.DataFrame({f"i{j}": base for j in range(5)})
    assert scoring.cronbach_alpha(igual) == pytest.approx(1.0, abs=1e-9)
    ruido = pd.DataFrame({f"i{j}": rng.integers(0, 3, 60) for j in range(5)})
    assert scoring.cronbach_alpha(ruido) < 0.4


def test_wilson_centrado_y_acotado():
    p, lo, hi = stats.wilson(50, 100)
    assert p == 50.0 and lo < 50 < hi
    assert stats.wilson(0, 30)[1] == 0.0
    assert stats.wilson(30, 30)[2] == 100.0


def test_benjamini_hochberg_es_monotono_y_no_reduce_p():
    p = [0.001, 0.01, 0.04, 0.2, 0.9]
    q = stats.benjamini_hochberg(p)
    assert all(q[i] <= q[i + 1] for i in range(len(q) - 1))
    assert all(qq >= pp for qq, pp in zip(q, p))


def test_cohen_d_signo_y_magnitud():
    a = pd.Series(np.arange(50) + 10.0)
    b = pd.Series(np.arange(50) * 1.0)
    assert stats.cohen_d(a, b) > 0
    assert stats.interpretar_d(0.1) == "trivial"
    assert stats.interpretar_d(0.6) == "mediano"


# ══ 3. Ingesta: privacidad y limpieza ═══════════════════════════════════════
def _formulario_sintetico(n=40, con_nombre=True):
    rng = np.random.default_rng(7)
    filas = []
    for i in range(n):
        f = {"Marca temporal": f"{1 + i % 27}/07/2026 10:00:00",
             "¿Quieres aportar al bienestar de todos con tus respuestas?": "Sí, quiero aportar",
             "Mi nombre completo es:": f"Estudiante Apellido {i}",
             "Tengo:": f"{12 + i % 4} años",
             "Mi sexo es:": "Mujer" if i % 2 else "Hombre",
             "Estoy en grado": "Séptimo",
             "Mi colegio es:": "I.E.O Laura Vicuña"}
        for j in range(1, 26):
            f[f"SDQ [enunciado {j}]"] = rng.choice(["No es cierto", "Algo cierto", "Muy cierto"])
        for j in range(1, 8):
            f[f"ARI [enunciado {j}]"] = rng.choice(["No es cierto", "Algo cierto", "Muy cierto"])
        for j in range(1, 26):
            f[f"RCADS [enunciado {j}]"] = rng.choice(
                ["Nunca", "Algunas veces", "Con frecuencia", "Siempre"])
        for j in range(1, 11):
            f[f"ERQ-CA [enunciado {j}]"] = rng.choice(
                ["Nada parecido a mi", "Poco parecido a mi", "Se parece a mi",
                 "Bastante parecido a mi", "Exactamente igual a mi"])
        for j in range(1, 13):
            f[f"MSPSS [enunciado {j}]"] = rng.choice(
                ["Nunca", "Casi nunca", "Algunas veces", "Casi siempre", "Siempre"])
        f["Siento que soy parte de mi colegio"] = int(rng.integers(1, 6))
        for j in range(2, 19):
            f[f"PSSM enunciado {j}"] = int(rng.integers(1, 6))
        for j in range(1, 11):
            f[f"Toma de decisiones  [enunciado {j}]"] = rng.choice(
                ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"])
        filas.append(f)
    df = pd.DataFrame(filas)
    if not con_nombre:
        df = df.drop(columns=["Mi nombre completo es:"])
    return df


def test_ingesta_no_deja_pasar_nombres():
    d, inf = ingest.cargar(_formulario_sintetico())
    assert not any("nombre" in c.lower() for c in d.columns if c != "Colegio_nombre")
    texto = d.astype(str).to_csv()
    assert "Estudiante Apellido 3" not in texto
    assert d["ID"].str.startswith("E").all()
    assert d["ID"].nunique() == len(d)


def test_ingesta_detecta_las_siete_escalas_y_el_nivel():
    d, inf = ingest.cargar(_formulario_sintetico())
    assert set(inf.escalas_detectadas) == {"SDQ", "ARI", "RCADS", "ERQ", "MSPSS", "PSSM", "TD"}
    assert inf.nivel == cat.NIVEL_SECUNDARIA
    assert all(c in d.columns for c in cat.SDQ.columnas)
    assert d[cat.SDQ.columnas].max().max() <= 2


def test_nivel_primaria_cuando_no_hay_rcads():
    df = _formulario_sintetico()
    df = df.drop(columns=[c for c in df.columns if c.startswith("RCADS")])
    d, inf = ingest.cargar(df)
    assert inf.nivel == cat.NIVEL_PRIMARIA
    assert "RCADS" in inf.escalas_ausentes
    assert any("exploratorios" in a for a in inf.avisos)


def test_sin_consentimiento_se_excluye():
    df = _formulario_sintetico()
    col = "¿Quieres aportar al bienestar de todos con tus respuestas?"
    df.loc[0:4, col] = "No, no quiero aportar"
    d, inf = ingest.cargar(df)
    assert inf.sin_consentimiento == 5
    assert len(d) == len(df) - 5


def test_duplicados_conservan_el_primer_envio():
    df = _formulario_sintetico()
    df.loc[1, "Mi nombre completo es:"] = df.loc[0, "Mi nombre completo es:"]
    df.loc[1, "Marca temporal"] = "28/07/2026 10:00:00"
    d, inf = ingest.cargar(df)
    assert inf.duplicados_eliminados == 1


def test_erq_invalidado_cuando_todos_los_items_estan_en_el_minimo():
    df = _formulario_sintetico()
    for j in range(1, 11):
        df.loc[0:9, f"ERQ-CA [enunciado {j}]"] = "Nada parecido a mi"
    d, inf = ingest.cargar(df)
    assert inf.erq_invalidado == 10
    # la ingesta reordena por fecha: se cuentan las filas con el bloque entero vacío
    assert int(d[cat.ERQ.columnas].isna().all(axis=1).sum()) == 10
    r = scoring.puntuar(d)
    assert r["ERQ_Reap"].isna().sum() == 10 and r["ERQ_Sup"].isna().sum() == 10


def test_normalizacion_de_colegios():
    assert ingest.normalizar_colegio("I.EO San Josemaría Escriva de Balaguer- Sede Samaria") == \
        ("SJMEB", "San Josemaría Escrivá de Balaguer", "Samaria")
    assert ingest.normalizar_colegio("I.E.O Laura Vicuña")[0] == "LauV"
    assert ingest.normalizar_colegio("I.E.O La Balsa")[0] == "LaBalsa"
    assert ingest.normalizar_colegio("")[0] == "SIN_DATO"


def test_valores_fuera_de_rango_se_marcan_faltantes():
    df = _formulario_sintetico()
    df["Siento que soy parte de mi colegio"] = 9
    d, inf = ingest.cargar(df)
    assert d["PSSM1"].isna().all()
    assert any("fuera del rango" in a for a in inf.avisos)


def test_es_dataset_estudiantes():
    assert ingest.es_dataset_estudiantes(_formulario_sintetico())
    assert not ingest.es_dataset_estudiantes(pd.DataFrame({"a": [1], "b": [2]}))


# ══ 4. MIN_GROUP_N ══════════════════════════════════════════════════════════
def test_grupos_pequenos_nunca_se_reportan():
    df = _formulario_sintetico(n=60)
    df.loc[0:3, "Mi colegio es:"] = "I.E.O Cerca de Piedra"   # 4 casos
    df.loc[4:9, "Mi colegio es:"] = "I.E.O La Balsa"          # 6 casos
    d, inf = ingest.cargar(df)
    r = scoring.puntuar(d)
    tabla, enmascarados = stats.comparar_por_grupo(r, ["SDQ_Total"], "Colegio")
    assert "CdP" in enmascarados or "CdP" not in inf.colegios
    for col in tabla.columns:
        if col.startswith("n·"):
            assert (tabla[col] >= cat.MIN_GROUP_N).all()
    prev = stats.prevalencia_por_grupo(r, r["SDQ_Total"] > 15, "Colegio")
    assert (prev["n"] >= cat.MIN_GROUP_N).all()


# ══ 5. Regresión contra la corrida de referencia ════════════════════════════
@pytest.fixture(scope="module")
def referencia():
    if not os.path.exists(FIXTURE):
        pytest.skip("Falta el fixture de referencia")
    return json.load(open(FIXTURE, encoding="utf-8"))


@pytest.fixture(scope="module")
def analisis_real():
    rutas = pipeline.localizar_formularios(carpeta_datos('estudiantes'))
    if len(rutas) < 2:
        pytest.skip("Los CSV originales no están en el directorio de trabajo")
    res, informes = pipeline.cargar_y_analizar(rutas, n_boot=60)
    return res, informes


def test_regresion_n_valido(analisis_real, referencia):
    res, _ = analisis_real
    assert res[cat.NIVEL_SECUNDARIA].n == referencia["n_final"]["secundaria"]
    assert res[cat.NIVEL_PRIMARIA].n == referencia["n_final"]["primaria"]


def test_regresion_exclusiones(analisis_real, referencia):
    _, informes = analisis_real
    por_nivel = {i.nivel: i for i in informes}
    sec = por_nivel[cat.NIVEL_SECUNDARIA]
    assert sec.sin_consentimiento == referencia["recibido"]["sin_consentimiento_A"]
    total_dup = sum(i.duplicados_eliminados for i in informes)
    assert total_dup == referencia["exclusiones"]["duplicados_nombre_eliminados"]
    total_erq = sum(i.erq_invalidado for i in informes)
    assert total_erq == referencia["erq_invalidado"]["n_total"]


@pytest.mark.parametrize("clave", ["SDQ_Total", "SDQ_Emo", "SDQ_Pares", "ARI_Total",
                                    "RCADS_Dep", "RCADS_Anx", "MSPSS_Fam", "PSSM_Total",
                                    "ERQ_Reap", "ERQ_Sup", "TD_Total"])
def test_regresion_descriptivos(analisis_real, referencia, clave):
    res, _ = analisis_real
    obt = res[cat.NIVEL_SECUNDARIA].descriptivos.set_index("clave")
    esp = referencia["descriptivos"]["secundaria"][clave]
    assert obt.loc[clave, "n"] == esp["n"]
    assert obt.loc[clave, "M"] == pytest.approx(esp["M"], abs=0.01)
    assert obt.loc[clave, "DE"] == pytest.approx(esp["DE"], abs=0.01)


@pytest.mark.parametrize("clave", ["SDQ_Total", "ARI_Total", "RCADS_Dep", "MSPSS_Total",
                                    "PSSM_Total", "ERQ_Reap"])
def test_regresion_alfa(analisis_real, referencia, clave):
    res, _ = analisis_real
    obt = res[cat.NIVEL_SECUNDARIA].fiabilidad.set_index("clave")
    esp = referencia["alfa"]["secundaria"][clave]
    assert obt.loc[clave, "alpha"] == pytest.approx(esp["alpha"], abs=0.01)
    assert obt.loc[clave, "n"] == esp["n"]


def test_regresion_bandas_sdq(analisis_real, referencia):
    res, _ = analisis_real
    obt = res[cat.NIVEL_SECUNDARIA].bandas.set_index("clave")
    for clave, esp in referencia["bandas_sdq"]["secundaria"].items():
        for i in range(4):
            assert obt.loc[clave, f"pct_b{i}"] == pytest.approx(esp["pct"][i], abs=0.11)


def test_regresion_cortes_ari(analisis_real, referencia):
    res, _ = analisis_real
    c = res[cat.NIVEL_SECUNDARIA].cortes
    esp = referencia["ari"]["secundaria"]
    gt2 = c[c["indicador"].str.contains(">")]["pct"].iloc[0]
    ge4 = c[c["indicador"].str.contains("≥ 4")]["pct"].iloc[0]
    assert gt2 == pytest.approx(esp["pct_gt2"], abs=0.11)
    assert ge4 == pytest.approx(esp["pct_ge4"], abs=0.11)


@pytest.mark.parametrize("a,b", [("SDQ_Total", "PSSM_Total"), ("RCADS_Dep", "MSPSS_Fam"),
                                  ("RCADS_Dep", "RCADS_Anx"), ("ARI_Total", "SDQ_Total")])
def test_regresion_correlaciones(analisis_real, referencia, a, b):
    res, _ = analisis_real
    obt = res[cat.NIVEL_SECUNDARIA].correlaciones
    fila = obt[((obt.a == a) & (obt.b == b)) | ((obt.a == b) & (obt.b == a))]
    assert len(fila) == 1
    esp = [p for p in referencia["correlaciones"]["secundaria"]
           if {p["a"], p["b"]} == {a, b}][0]
    assert fila["rho"].iloc[0] == pytest.approx(esp["rho"], abs=0.01)


def test_regresion_modelo_depresion(analisis_real, referencia):
    res, _ = analisis_real
    m = [x for x in res[cat.NIVEL_SECUNDARIA].modelos if x["y"] == "RCADS_Dep"]
    assert m, "falta el modelo de depresión"
    m = m[0]
    esp = referencia["modelos"]["dep_protectores"]
    assert m["n"] == esp["n"]
    assert m["R2"] == pytest.approx(esp["R2"], abs=0.01)
    obt = {c["predictor"]: c["beta"] for c in m["coeficientes"]}
    for pred in ("MSPSS_Fam", "PSSM_Total", "ERQ_Sup"):
        assert obt[pred] == pytest.approx(esp["beta_std"][pred]["b"], abs=0.01)


def test_no_hay_columnas_identificables_en_el_analisis(analisis_real):
    res, _ = analisis_real
    for a in res.values():
        assert not any("nombre" in c.lower() for c in a.datos.columns
                       if c != "Colegio_nombre")
