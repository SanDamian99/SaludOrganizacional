"""
Estadística de la triangulación — funciones puras con numpy y scipy.

No hay `statsmodels` en `requirements.txt` y no se añade: lo que hace falta
cabe en numpy/scipy y en `estudiantes.stats.ols_cluster` (MCO con errores
agrupados CR1 y gl = G − 1), que ya usa estudiantes.

  · `icc_a1`: CCI(A,1) de McGraw y Wong (1996) = CCI(2,1) de Shrout y Fleiss
    (1979): dos vías, efectos aleatorios, acuerdo absoluto, medida única.
  · `kappa_ponderado`: kappa de Cohen (1968) con pesos lineales.
  · `bland_altman`: diferencia media y límites de acuerdo (± 1,96 DE).
  · `media_agrupada`: media con IC por errores agrupados (familia).
  · `correlacion_ic`: Spearman o Pearson con IC de Fisher.
  · `bootstrap_ic`: IC percentil remuestreando conglomerados (familias).
  · `ols_agrupado`: MCO con efectos fijos y errores agrupados.
  · `partes_seguras` y `suficiente`: las reglas de cifras pequeñas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from src.estudiantes import stats as stats_est
from src.triangulacion import catalogo as cat

Z95 = 1.959963984540054


def icc_a1(Y) -> float:
    """CCI(A,1) sobre una matriz n × k (filas con faltantes se quitan)."""
    Y = np.asarray(Y, dtype=float)
    Y = Y[~np.isnan(Y).any(axis=1)]
    n, k = Y.shape if Y.ndim == 2 else (0, 0)
    if n < 2 or k < 2:
        return float("nan")
    g = Y.mean()
    ssr = k * ((Y.mean(axis=1) - g) ** 2).sum()
    ssc = n * ((Y.mean(axis=0) - g) ** 2).sum()
    sse = ((Y - g) ** 2).sum() - ssr - ssc
    msr, msc = ssr / (n - 1), ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    den = msr + (k - 1) * mse + k * (msc - mse) / n
    return float((msr - mse) / den) if den > 0 else float("nan")


def kappa_ponderado(a, b, k: int = 4) -> float:
    """Kappa ponderado lineal entre dos clasificaciones ordinales 0..k−1."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok].astype(int), b[ok].astype(int)
    if len(a) == 0:
        return float("nan")
    O = np.zeros((k, k))
    np.add.at(O, (a, b), 1)
    O /= O.sum()
    E = np.outer(O.sum(axis=1), O.sum(axis=0))
    i, j = np.indices((k, k))
    W = np.abs(i - j) / (k - 1)
    den = (W * E).sum()
    return float(1 - (W * O).sum() / den) if den > 0 else float("nan")


def bland_altman(a, b) -> dict:
    """Diferencia media (a − b), su DE y los límites de acuerdo del 95 %."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    dif = a[ok] - b[ok]
    if len(dif) < 2:
        return dict(n=len(dif), dif_media=float("nan"), de_dif=float("nan"),
                    lim_inf=float("nan"), lim_sup=float("nan"))
    m, s = float(dif.mean()), float(dif.std(ddof=1))
    return dict(n=len(dif), dif_media=m, de_dif=s, lim_inf=m - Z95 * s, lim_sup=m + Z95 * s)


def media_agrupada(y, grupos) -> dict:
    """Media con IC del 95 % por errores agrupados (t con G − 1 gl)."""
    y = np.asarray(y, dtype=float)
    grupos = np.asarray(grupos)
    ok = ~np.isnan(y)
    y, grupos = y[ok], grupos[ok]
    if len(y) < 2:
        return dict(m=float("nan"), se=float("nan"), ic_inf=float("nan"),
                    ic_sup=float("nan"), G=len(set(grupos)))
    b, se, _, _, G = stats_est.ols_cluster(y, np.empty((len(y), 0)), grupos)
    t = sps.t.ppf(0.975, max(G - 1, 1))
    return dict(m=float(b[0]), se=float(se[0]), ic_inf=float(b[0] - t * se[0]),
                ic_sup=float(b[0] + t * se[0]), G=int(G))


def correlacion_ic(a, b, metodo: str = "spearman") -> tuple[float, float, float, float]:
    """(r, IC inferior, IC superior, p) con la transformación de Fisher."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    n = len(a)
    if n < 4 or np.std(a) == 0 or np.std(b) == 0:
        return (float("nan"),) * 4
    res = sps.spearmanr(a, b) if metodo == "spearman" else sps.pearsonr(a, b)
    r = float(res.statistic)
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    se = 1 / np.sqrt(n - 3)
    return r, float(np.tanh(z - Z95 * se)), float(np.tanh(z + Z95 * se)), float(res.pvalue)


def bootstrap_ic(df: pd.DataFrame, estadistico, grupo: str, n_boot: int = cat.N_BOOT,
                 semilla: int = cat.SEMILLA) -> tuple[float, float]:
    """IC percentil del 95 % remuestreando conglomerados enteros (familias)."""
    if df.empty or n_boot <= 0:
        return float("nan"), float("nan")
    posiciones = [np.asarray(v) for v in df.groupby(grupo, sort=True).indices.values()]
    rng = np.random.default_rng(semilla)
    valores = []
    for _ in range(n_boot):
        elegidos = rng.integers(0, len(posiciones), len(posiciones))
        idx = np.concatenate([posiciones[e] for e in elegidos])
        valores.append(estadistico(df.iloc[idx]))
    valores = np.asarray(valores, dtype=float)
    valores = valores[~np.isnan(valores)]
    if len(valores) < max(10, n_boot // 2):
        return float("nan"), float("nan")
    return float(np.percentile(valores, 2.5)), float(np.percentile(valores, 97.5))


def ols_agrupado(y: pd.Series, X: pd.DataFrame, grupos: pd.Series,
                 efectos_fijos: pd.Series | None = None) -> pd.DataFrame:
    """MCO con efectos fijos (variables indicadoras) y errores agrupados.

    Devuelve una fila por columna de `X` (no por las indicadoras ni la
    constante): beta, se, IC del 95 % y p con t de G − 1 gl.
    """
    Xf = X.astype(float)
    if efectos_fijos is not None and efectos_fijos.nunique() > 1:
        ind = pd.get_dummies(efectos_fijos.astype(str), prefix="_ef", drop_first=True,
                             dtype=float)
        Xf = pd.concat([Xf, ind], axis=1)
    b, se, p, r2, G = stats_est.ols_cluster(np.asarray(y, dtype=float), Xf.to_numpy(),
                                            np.asarray(grupos))
    t = sps.t.ppf(0.975, max(G - 1, 1))
    filas = []
    for i, nombre in enumerate(X.columns, start=1):
        filas.append(dict(predictor=nombre, beta=float(b[i]), se=float(se[i]),
                          ic_inf=float(b[i] - t * se[i]), ic_sup=float(b[i] + t * se[i]),
                          p=float(p[i]), R2=float(r2), G=int(G)))
    return pd.DataFrame(filas)


def suficiente(df: pd.DataFrame, unidad: str | None, minimo: int = cat.MIN_GROUP_N) -> bool:
    """≥ `minimo` filas y ≥ `minimo` unidades distintas (familias, cuidadores)."""
    if len(df) < minimo:
        return False
    return unidad is None or df[unidad].nunique() >= minimo


def partes_seguras(etiquetas: pd.Series, unidades: pd.Series | None, categorias,
                   minimo: int = cat.MIN_CASOS) -> bool:
    """Cada categoría y su complemento tienen ≥ `minimo` filas y unidades distintas.

    Es la regla 3 ≤ k ≤ n − 3 de `estudiantes.supresion` sobre un reparto en
    varias partes (todo o nada), contando además unidades distintas: tres
    hermanos de una misma familia no son tres casos.
    """
    etiquetas = pd.Series(etiquetas)
    if etiquetas.empty:
        return False
    for c in categorias:
        dentro = etiquetas == c
        for parte in (dentro, ~dentro):
            if int(parte.sum()) < minimo:
                return False
            if unidades is not None and pd.Series(unidades)[parte.to_numpy()].nunique() < minimo:
                return False
    return True
