"""
Estadística para el módulo de estudiantes — Observatorio 360.

Es la ÚNICA fuente de las cifras que salen a las dos vistas y a los exportables,
para que la vista comunidad, la vista investigador y el artículo no puedan
divergir.

Toda función que desagregue por grupo respeta `catalog.MIN_GROUP_N`: los grupos
con menos casos se omiten y se informan como enmascarados, nunca se muestran.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from src.estudiantes import catalog as cat


# ── proporciones ────────────────────────────────────────────────────────────
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(%, IC inferior, IC superior) con el intervalo de Wilson."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    medio = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(100 * p, 1), round(100 * max(0, centro - medio), 1),
            round(100 * min(1, centro + medio), 1))


def cohen_d(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna(), b.dropna()
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                 / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / sp) if sp > 0 else float("nan")


def benjamini_hochberg(p: list[float] | np.ndarray) -> np.ndarray:
    """q-valores de Benjamini-Hochberg."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    if n == 0:
        return p
    orden = np.argsort(p)
    ajustado = np.empty(n)
    escalado = p[orden] * n / np.arange(1, n + 1)
    ajustado[orden] = np.minimum.accumulate(escalado[::-1])[::-1]
    return np.minimum(ajustado, 1.0)


def interpretar_d(d: float) -> str:
    a = abs(d)
    if np.isnan(a):
        return "sin dato"
    return "trivial" if a < 0.2 else "pequeño" if a < 0.5 else "mediano" if a < 0.8 else "grande"


# ── correlaciones ───────────────────────────────────────────────────────────
def correlaciones(d: pd.DataFrame, variables: list[str] | None = None) -> pd.DataFrame:
    """Spearman por pares, con IC de Fisher y corrección de Benjamini-Hochberg."""
    import itertools
    variables = [v for v in (variables or cat.CORR_VARS_SEC) if v in d.columns]
    filas = []
    for a, b in itertools.combinations(variables, 2):
        v = d[[a, b]].dropna()
        if len(v) < 4:
            continue
        r = sps.spearmanr(v[a], v[b])
        z = np.arctanh(np.clip(r.statistic, -0.999999, 0.999999))
        se = 1 / np.sqrt(len(v) - 3) if len(v) > 3 else np.nan
        filas.append(dict(
            a=a, b=b, etiqueta_a=cat.meta(a)["label"], etiqueta_b=cat.meta(b)["label"],
            rho=round(float(r.statistic), 3),
            ic_inf=round(float(np.tanh(z - 1.96 * se)), 3),
            ic_sup=round(float(np.tanh(z + 1.96 * se)), 3),
            p=float(r.pvalue), n=len(v)))
    if not filas:
        return pd.DataFrame()
    out = pd.DataFrame(filas)
    out["q_bh"] = benjamini_hochberg(out["p"].values)
    out["significativa"] = out["q_bh"] < 0.05
    return out.sort_values("rho", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def matriz_correlaciones(d: pd.DataFrame, variables: list[str] | None = None) -> pd.DataFrame:
    variables = [v for v in (variables or cat.CORR_VARS_SEC) if v in d.columns]
    return d[variables].corr(method="spearman").round(3)


# ── comparaciones por grupo ─────────────────────────────────────────────────
def comparar_por_sexo(d: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    filas = []
    for k in claves:
        if k not in d.columns:
            continue
        a = d.loc[d["Sexo"] == "Mujer", k].dropna()
        b = d.loc[d["Sexo"] == "Hombre", k].dropna()
        if len(a) < cat.MIN_GROUP_N or len(b) < cat.MIN_GROUP_N:
            continue
        u = sps.mannwhitneyu(a, b)
        dd = cohen_d(a, b)
        filas.append(dict(clave=k, escala=cat.meta(k)["label"],
                          n_mujer=len(a), n_hombre=len(b),
                          M_mujer=round(float(a.mean()), 2), M_hombre=round(float(b.mean()), 2),
                          DE_mujer=round(float(a.std(ddof=1)), 2),
                          DE_hombre=round(float(b.std(ddof=1)), 2),
                          d=round(dd, 2), magnitud=interpretar_d(dd), p=float(u.pvalue)))
    if not filas:
        return pd.DataFrame()
    out = pd.DataFrame(filas)
    out["q_bh"] = benjamini_hochberg(out["p"].values)
    return out


def comparar_por_grupo(d: pd.DataFrame, claves: list[str], columna: str,
                       orden: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Kruskal-Wallis entre los niveles con N suficiente. Devuelve (tabla, enmascarados)."""
    vc = d[columna].value_counts()
    validos = [g for g in (orden or vc.index.tolist())
               if g in vc.index and vc[g] >= cat.MIN_GROUP_N]
    enmascarados = [g for g in vc.index if vc[g] < cat.MIN_GROUP_N]
    filas = []
    for k in claves:
        if k not in d.columns:
            continue
        grupos = {g: d.loc[d[columna] == g, k].dropna() for g in validos}
        grupos = {g: v for g, v in grupos.items() if len(v) >= cat.MIN_GROUP_N}
        if len(grupos) < 2:
            continue
        kw = sps.kruskal(*grupos.values())
        n_total = sum(len(v) for v in grupos.values())
        eta2 = (kw.statistic - len(grupos) + 1) / (n_total - len(grupos))
        fila = dict(clave=k, escala=cat.meta(k)["label"], p=float(kw.pvalue),
                    eta2=round(float(eta2), 3), n=n_total)
        for g, v in grupos.items():
            fila[f"M·{g}"] = round(float(v.mean()), 2)
            fila[f"n·{g}"] = len(v)
        filas.append(fila)
    if not filas:
        return pd.DataFrame(), enmascarados
    out = pd.DataFrame(filas)
    out["q_bh"] = benjamini_hochberg(out["p"].values)
    return out, enmascarados


def correlacion_con_edad(d: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    filas = []
    for k in claves:
        if k not in d.columns:
            continue
        v = d[[k, "Edad"]].dropna()
        if len(v) < cat.MIN_GROUP_N:
            continue
        r = sps.spearmanr(v[k], v["Edad"])
        filas.append(dict(clave=k, escala=cat.meta(k)["label"], n=len(v),
                          rho=round(float(r.statistic), 3), p=float(r.pvalue)))
    if not filas:
        return pd.DataFrame()
    out = pd.DataFrame(filas)
    out["q_bh"] = benjamini_hochberg(out["p"].values)
    return out


def prevalencia_por_grupo(d: pd.DataFrame, mask: pd.Series, columna: str,
                          orden: list[str] | None = None) -> pd.DataFrame:
    """% de `mask` por nivel de `columna`, con IC de Wilson y enmascarado por N."""
    filas = []
    vc = d[columna].value_counts()
    niveles = [g for g in (orden or vc.index.tolist()) if g in vc.index]
    for g in niveles:
        sub = d[d[columna] == g]
        if len(sub) < cat.MIN_GROUP_N:
            continue
        m = mask.reindex(sub.index)
        base = int(m.notna().sum())
        if base == 0:
            continue
        p, lo, hi = wilson(int(m.fillna(False).sum()), base)
        filas.append(dict(grupo=g, n=base, casos=int(m.fillna(False).sum()),
                          pct=p, ic_inf=lo, ic_sup=hi))
    return pd.DataFrame(filas)


# ── modelos ─────────────────────────────────────────────────────────────────
def ols_cluster(y: np.ndarray, X: np.ndarray, cluster: np.ndarray
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, int]:
    """OLS con errores estándar robustos por conglomerado. (b, se, p, R², G)."""
    X = np.column_stack([np.ones(len(X)), X])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    XtX_inv = np.linalg.inv(X.T @ X)
    grupos = np.unique(cluster)
    G = len(grupos)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in grupos:
        idx = cluster == c
        u = X[idx].T @ e[idx]
        meat += np.outer(u, u)
    n, k = X.shape
    ajuste = (G / max(G - 1, 1)) * ((n - 1) / (n - k))
    V = XtX_inv @ meat @ XtX_inv * ajuste
    se = np.sqrt(np.diag(V))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = b / se
    p = 2 * sps.t.sf(np.abs(t), max(G - 1, 1))
    r2 = 1 - e.var() / y.var() if y.var() > 0 else float("nan")
    return b, se, p, float(r2), G


def modelo(d: pd.DataFrame, y: str, predictores: list[str],
           controles: tuple[str, ...] = ("Sexo", "Edad"),
           cluster: str = "Colegio") -> dict:
    """Regresión estandarizada con errores robustos por colegio."""
    cols = [y] + [p for p in predictores if p in d.columns] + [cluster]
    cols += [c for c in controles if c in d.columns]
    sub = d[cols].dropna()
    if len(sub) < 30:
        return {}
    X = sub[[p for p in predictores if p in d.columns]].copy()
    etiquetas = {p: cat.meta(p)["label"] for p in X.columns}
    if "Sexo" in controles and "Sexo" in sub.columns:
        X["mujer"] = (sub["Sexo"] == "Mujer").astype(float)
        etiquetas["mujer"] = "Mujer (vs hombre)"
    if "Edad" in controles and "Edad" in sub.columns:
        X["edad"] = sub["Edad"].astype(float)
        etiquetas["edad"] = "Edad"
    Xs = (X - X.mean()) / X.std(ddof=1)
    ys = (sub[y] - sub[y].mean()) / sub[y].std(ddof=1)
    b, se, p, r2, G = ols_cluster(ys.values, Xs.values, sub[cluster].values)
    nombres = ["(constante)"] + list(Xs.columns)
    return dict(
        y=y, y_etiqueta=cat.meta(y)["label"], n=len(sub), clusters=G, R2=round(r2, 3),
        coeficientes=[
            dict(predictor=nom, etiqueta=etiquetas.get(nom, nom),
                 beta=round(float(bb), 3), se=round(float(ss), 3), p=round(float(pp), 4),
                 significativo=bool(pp < 0.05))
            for nom, bb, ss, pp in zip(nombres, b, se, p)],
        aviso=("Con solo %d conglomerados, los errores robustos son aproximados; "
               "reportar como análisis de sensibilidad." % G) if G < 10 else "")


def icc_entre_grupos(d: pd.DataFrame, clave: str, columna: str = "Colegio") -> float:
    """Coeficiente de correlación intraclase: cuánta varianza está entre grupos."""
    sub = d[[clave, columna]].dropna()
    vc = sub[columna].value_counts()
    sub = sub[sub[columna].isin(vc[vc >= cat.MIN_GROUP_N].index)]
    grupos = [g[clave].values for _, g in sub.groupby(columna)]
    G, n = len(grupos), len(sub)
    if G < 2 or n <= G:
        return float("nan")
    n0 = (n - sum(len(g) ** 2 for g in grupos) / n) / (G - 1)
    gm = sub[clave].mean()
    msb = sum(len(g) * (g.mean() - gm) ** 2 for g in grupos) / (G - 1)
    msw = sum(((g - g.mean()) ** 2).sum() for g in grupos) / (n - G)
    den = msb + (n0 - 1) * msw
    return round(float((msb - msw) / den), 3) if den != 0 else float("nan")


# ── contrastes útiles para la vista comunidad ───────────────────────────────
def contraste_protector(d: pd.DataFrame, resultado: str, protector: str,
                        umbral_resultado: str = "P90") -> dict:
    """Prevalencia del resultado en el tercil bajo y el alto del protector.

    Es la forma más honesta de mostrar un efecto a un público no técnico: dos
    porcentajes comparables, sin coeficientes.
    """
    sub = d[[resultado, protector]].dropna()
    if len(sub) < 3 * cat.MIN_GROUP_N:
        return {}
    if umbral_resultado.startswith("P"):
        corte = sub[resultado].quantile(int(umbral_resultado[1:]) / 100)
        alto = sub[resultado] >= corte
        desc_umbral = f"decil más alto ({umbral_resultado})"
    else:
        corte = float(umbral_resultado)
        alto = sub[resultado] >= corte
        desc_umbral = f"≥ {corte:g}"
    t1, t2 = sub[protector].quantile(1 / 3), sub[protector].quantile(2 / 3)
    bajo, arriba = sub[protector] <= t1, sub[protector] >= t2
    if bajo.sum() < cat.MIN_GROUP_N or arriba.sum() < cat.MIN_GROUP_N:
        return {}
    p_b, lo_b, hi_b = wilson(int(alto[bajo].sum()), int(bajo.sum()))
    p_a, lo_a, hi_a = wilson(int(alto[arriba].sum()), int(arriba.sum()))
    return dict(resultado=resultado, resultado_etiqueta=cat.meta(resultado)["label"],
                protector=protector, protector_etiqueta=cat.meta(protector)["label"],
                umbral=desc_umbral,
                pct_tercil_bajo=p_b, ic_bajo=(lo_b, hi_b), n_bajo=int(bajo.sum()),
                pct_tercil_alto=p_a, ic_alto=(lo_a, hi_a), n_alto=int(arriba.sum()),
                razon=round(p_b / p_a, 1) if p_a > 0 else None)


def solapamiento(d: pd.DataFrame) -> dict:
    """Comorbilidad entre los indicadores con corte: cuánto se superponen."""
    out = {}
    if "banda_SDQ_Total" not in d.columns or "ARI_Total" not in d.columns:
        return out
    sdq_alto = d["banda_SDQ_Total"] >= 2
    ari_alto = d["ARI_Total"] > 2
    base = d["banda_SDQ_Total"].notna() & d["ARI_Total"].notna()
    n = int(base.sum())
    if n == 0:
        return out
    out["n"] = n
    out["pct_sdq_alto"] = wilson(int((sdq_alto & base).sum()), n)[0]
    out["pct_ari_alto"] = wilson(int((ari_alto & base).sum()), n)[0]
    out["pct_ambos"] = wilson(int((sdq_alto & ari_alto & base).sum()), n)[0]
    out["pct_alguno"] = wilson(int(((sdq_alto | ari_alto) & base).sum()), n)[0]
    sub = d[base]
    if (sub["banda_SDQ_Total"] >= 2).sum() >= cat.MIN_GROUP_N:
        out["pct_ari_alto_si_sdq_alto"] = wilson(
            int((sub.loc[sub["banda_SDQ_Total"] >= 2, "ARI_Total"] > 2).sum()),
            int((sub["banda_SDQ_Total"] >= 2).sum()))[0]
    if (sub["banda_SDQ_Total"] == 0).sum() >= cat.MIN_GROUP_N:
        out["pct_ari_alto_si_sdq_promedio"] = wilson(
            int((sub.loc[sub["banda_SDQ_Total"] == 0, "ARI_Total"] > 2).sum()),
            int((sub["banda_SDQ_Total"] == 0).sum()))[0]
    return out


def medias_items(d: pd.DataFrame, escala_key: str, orientados: bool = True) -> pd.DataFrame:
    """Media por ítem de una escala, para ver qué enunciados puntúan más bajo."""
    from src.estudiantes.scoring import invertir
    e = cat.ESCALAS_POR_KEY[escala_key]
    cols = [c for c in e.columnas if c in d.columns]
    if not cols:
        return pd.DataFrame()
    X = d[cols].copy()
    if orientados:
        inversos = set()
        for s in e.subescalas:
            inversos.update(f"{e.prefijo}{i}" for i in s.reverse)
        for c in inversos & set(X.columns):
            X[c] = invertir(X[c], e)
    out = pd.DataFrame(dict(item=cols, M=X.mean().round(2).values,
                            DE=X.std(ddof=1).round(2).values,
                            n=X.notna().sum().values))
    return out.sort_values("M").reset_index(drop=True)
