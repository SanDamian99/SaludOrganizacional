"""
Puntuación del instrumento de estudiantes — Observatorio 360.

Toma el DataFrame que produce `ingest.cargar` y añade las puntuaciones de todas
las subescalas y compuestas definidas en el catálogo, más las bandas del SDQ.

Reglas:
  · Los inversos se recodifican (max + min) − x usando el rango de la escala.
  · Si falta más de lo que tolera la subescala, el puntaje es faltante; si falta
    dentro de la tolerancia, la suma se prorratea al número de ítems completos.
  · Las bandas del SDQ que se aplican son SIEMPRE las de autoinforme.

Verificado contra docs/instrumentos/fixtures/resultados_preliminares_estudiantes.json
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.estudiantes import catalog as cat


# ── utilidades ──────────────────────────────────────────────────────────────
def invertir(serie: pd.Series, escala: cat.Escala) -> pd.Series:
    return (escala.valor_min + escala.valor_max) - serie


def items_orientados(df: pd.DataFrame, sub: cat.Subescala, escala: cat.Escala) -> pd.DataFrame:
    """Matriz de ítems de la subescala con los inversos ya recodificados."""
    cols = [f"{escala.prefijo}{i}" for i in sub.items]
    presentes = [c for c in cols if c in df.columns]
    X = df[presentes].copy()
    for i in sub.reverse:
        c = f"{escala.prefijo}{i}"
        if c in X.columns:
            X[c] = invertir(X[c], escala)
    return X


def _puntuar(X: pd.DataFrame, sub: cat.Subescala) -> pd.Series:
    n = X.shape[1]
    if n == 0:
        return pd.Series(np.nan, index=X.index)
    respondidos = X.notna().sum(axis=1)
    if sub.agregacion == "media":
        out = X.mean(axis=1)
    else:
        out = X.sum(axis=1) * n / respondidos.replace(0, np.nan)
    return out.mask(respondidos < sub.min_items)


def puntuar(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una copia de `df` con todas las puntuaciones y bandas añadidas."""
    d = df.copy()
    nuevas: dict[str, pd.Series] = {}

    for escala in cat.ESCALAS:
        if not all(c in d.columns for c in escala.columnas[:1]):
            continue
        for sub in escala.subescalas:
            X = items_orientados(d, sub, escala)
            if X.shape[1] < len(sub.items):
                continue
            s = _puntuar(X, sub)
            if escala.key == "SDQ":
                s = s.round(0)
            nuevas[sub.key] = s

    for key, c in cat.COMPUESTAS.items():
        partes = [p for p in c["partes"] if p in nuevas]
        if len(partes) == len(c["partes"]):
            nuevas[key] = pd.concat([nuevas[p] for p in partes], axis=1).sum(
                axis=1, min_count=len(partes))

    d = pd.concat([d, pd.DataFrame(nuevas, index=d.index)], axis=1)

    # bandas del SDQ (siempre autoinforme)
    for key in list(cat.BANDS_SELF):
        if key in d.columns:
            d[f"banda_{key}"] = d[key].map(
                lambda v: cat.banda_de(v, key, "self") if pd.notna(v) else np.nan)
    return d


def puntuaciones_disponibles(d: pd.DataFrame) -> list[str]:
    """Claves del catálogo presentes en el DataFrame, en orden canónico."""
    return [k for k in cat.ORDEN_TABLA1 if k in d.columns and d[k].notna().any()]


# ── fiabilidad ──────────────────────────────────────────────────────────────
def cronbach_alpha(X: pd.DataFrame) -> float:
    """α con los casos completos. NaN si hay menos de 20 casos o menos de 2 ítems."""
    X = X.dropna()
    k = X.shape[1]
    if len(X) < 20 or k < 2:
        return float("nan")
    var_total = X.sum(axis=1).var(ddof=1)
    if var_total == 0:
        return float("nan")
    return float(k / (k - 1) * (1 - X.var(ddof=1).sum() / var_total))


def alpha_ci(X: pd.DataFrame, n_boot: int = 300, seed: int = 1
             ) -> tuple[float, float, float, int]:
    """(α, IC inferior, IC superior, n de casos completos) por bootstrap."""
    X = X.dropna()
    a = cronbach_alpha(X)
    if len(X) < 20 or np.isnan(a):
        return a, float("nan"), float("nan"), len(X)
    rng = np.random.default_rng(seed)
    muestras = [cronbach_alpha(X.iloc[rng.integers(0, len(X), len(X))]) for _ in range(n_boot)]
    return (a, float(np.nanpercentile(muestras, 2.5)),
            float(np.nanpercentile(muestras, 97.5)), len(X))


def fiabilidad(d: pd.DataFrame, n_boot: int = 300) -> pd.DataFrame:
    """α con intervalo para cada puntuación con ítems propios."""
    filas = []
    for key in puntuaciones_disponibles(d):
        if key in cat.COMPUESTAS:
            if key != "SDQ_Total":
                continue
            X = pd.concat(
                [items_orientados(d, cat.subescala(s), cat.SDQ)
                 for s in cat.SDQ_SUBS_DIFICULTADES], axis=1)
        else:
            sub = cat.subescala(key)
            esc = cat.escala_de(key)
            if sub is None or esc is None:
                continue
            if len(sub.items) < 2:
                continue
            X = items_orientados(d, sub, esc)
        a, lo, hi, n = alpha_ci(X, n_boot=n_boot)
        m = cat.meta(key)
        filas.append(dict(clave=key, escala=m["label"], n_items=X.shape[1], n=n,
                          alpha=round(a, 3) if not np.isnan(a) else None,
                          ic_inf=round(lo, 3) if not np.isnan(lo) else None,
                          ic_sup=round(hi, 3) if not np.isnan(hi) else None,
                          aceptable=bool(a >= 0.70) if not np.isnan(a) else None))
    return pd.DataFrame(filas)


# ── descriptivos y cortes ───────────────────────────────────────────────────
def descriptivos(d: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for key in puntuaciones_disponibles(d):
        v = d[key].dropna()
        m = cat.meta(key)
        filas.append(dict(
            clave=key, escala=m["label"], n=len(v),
            M=round(float(v.mean()), 2), DE=round(float(v.std(ddof=1)), 2),
            Mdn=round(float(v.median()), 2),
            min=float(v.min()), max=float(v.max()),
            rango=f"{m['rango'][0]:g}–{m['rango'][1]:g}",
            pct_faltante=round(100 * (1 - len(v) / len(d)), 1),
            P25=round(float(v.quantile(.25)), 2), P75=round(float(v.quantile(.75)), 2),
            P90=round(float(v.quantile(.90)), 2), P95=round(float(v.quantile(.95)), 2),
            direccion=m["direccion"], validada=m["validada"]))
    return pd.DataFrame(filas)


def distribucion_bandas(d: pd.DataFrame, version: str = "self") -> pd.DataFrame:
    """% en cada banda del SDQ, con el número de casos por banda."""
    tabla = cat.BANDS_SELF if version == "self" else cat.BANDS_PARENT
    filas = []
    for key in tabla:
        if key not in d.columns:
            continue
        v = d[key].dropna()
        if v.empty:
            continue
        b = v.map(lambda x: cat.banda_de(x, key, version))
        cnt = b.value_counts().reindex(range(4), fill_value=0)
        fila = dict(clave=key, escala=cat.meta(key)["label"], n=len(v))
        for i in range(4):
            fila[f"n_b{i}"] = int(cnt[i])
            fila[f"pct_b{i}"] = round(100 * cnt[i] / len(v), 1)
        fila["pct_alto_o_muy_alto"] = round(fila["pct_b2"] + fila["pct_b3"], 1)
        fila["etiquetas"] = [cat.etiqueta_banda(key, i) for i in range(4)]
        filas.append(fila)
    return pd.DataFrame(filas)


def sobre_cortes(d: pd.DataFrame) -> pd.DataFrame:
    """Prevalencias sobre los cortes con umbral definido, con IC de Wilson."""
    from src.estudiantes.stats import wilson
    filas = []

    def agrega(clave, etiqueta, mask, base, fuente):
        base_n = int(base.sum())
        if base_n == 0:
            return
        k = int((mask & base).sum())
        p, lo, hi = wilson(k, base_n)
        filas.append(dict(clave=clave, indicador=etiqueta, n=base_n, casos=k,
                          pct=p, ic_inf=lo, ic_sup=hi, fuente=fuente))

    base = pd.Series(True, index=d.index)
    if "SDQ_Total" in d.columns:
        for key in cat.BANDS_SELF:
            if key not in d.columns:
                continue
            b = d[key].map(lambda x: cat.banda_de(x, key, "self") if pd.notna(x) else np.nan)
            etiqueta = ("Prosocial bajo o muy bajo" if key == "SDQ_Pro"
                        else f"{cat.meta(key)['label']}: alto o muy alto")
            agrega(key, etiqueta, b >= 2, d[key].notna(), cat.FUENTE_BANDS_SELF)
    if "ARI_Total" in d.columns:
        agrega("ARI_Total", "Irritabilidad > 2 (cribado)", d["ARI_Total"] > 2,
               d["ARI_Total"].notna(), cat.ARI.fuente)
        agrega("ARI_Total", "Irritabilidad ≥ 4 (psicopatología general)", d["ARI_Total"] >= 4,
               d["ARI_Total"].notna(), cat.ARI.fuente)
    if "ARI_Deterioro" in d.columns:
        agrega("ARI_Deterioro", "La irritabilidad le causa problemas (muy cierto)",
               d["ARI_Deterioro"] == 2, d["ARI_Deterioro"].notna(), cat.ARI.fuente)
    col_muerte = f"RCADS{cat.RCADS_ITEM_MUERTE}"
    if col_muerte in d.columns:
        agrega(col_muerte, "Piensa en la muerte con frecuencia o siempre",
               d[col_muerte] >= 2, d[col_muerte].notna(),
               "Ítem 18 del RCADS-25; señal de alerta, no diagnóstico")
    col_adulto = f"PSSM{cat.PSSM_ITEM_ADULTO}"
    if col_adulto in d.columns:
        agrega(col_adulto, "Sin un adulto de confianza en el colegio",
               d[col_adulto] <= 2, d[col_adulto].notna(), cat.PSSM.fuente)
    for key in ("MSPSS_Total", "MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro", "PSSM_Total"):
        if key in d.columns:
            agrega(key, f"{cat.meta(key)['label']}: media por debajo de 3 (descriptivo)",
                   d[key] < 3, d[key].notna(),
                   "Umbral descriptivo (punto medio de la escala), no clínico")
    return pd.DataFrame(filas)


def terciles(d: pd.DataFrame, claves: list[str] | None = None) -> pd.DataFrame:
    """Cortes de tercil de la muestra para las escalas sin corte clínico."""
    claves = claves or [k for k in ("ERQ_Reap", "ERQ_Sup", "MSPSS_Total", "MSPSS_Fam",
                                    "MSPSS_Amigos", "MSPSS_Otro", "PSSM_Total", "TD_Total")
                        if k in d.columns]
    filas = []
    for k in claves:
        v = d[k].dropna()
        if len(v) < cat.MIN_GROUP_N:
            continue
        filas.append(dict(clave=k, escala=cat.meta(k)["label"], n=len(v),
                          corte_bajo=round(float(v.quantile(1 / 3)), 2),
                          corte_alto=round(float(v.quantile(2 / 3)), 2),
                          nota="Relativo a esta muestra, no clínico"))
    return pd.DataFrame(filas)


def percentiles_por_sexo(d: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """Percentiles propios, el sustituto honesto de las puntuaciones T que no tenemos."""
    filas = []
    for sexo, g in d.groupby("Sexo"):
        if len(g) < cat.MIN_GROUP_N:
            continue
        for k in claves:
            if k not in g.columns:
                continue
            v = g[k].dropna()
            if len(v) < cat.MIN_GROUP_N:
                continue
            filas.append(dict(clave=k, escala=cat.meta(k)["label"], sexo=sexo, n=len(v),
                              **{f"P{p}": round(float(v.quantile(p / 100)), 1)
                                 for p in (50, 75, 85, 90, 95)}))
    return pd.DataFrame(filas)
