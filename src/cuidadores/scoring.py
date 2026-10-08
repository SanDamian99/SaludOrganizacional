"""
Puntuación del formulario «Cuidando al Cuidador» — Observatorio 360.

Todo sale de los ítems que `ingest` convirtió desde el TEXTO crudo de cada
respuesta (spec §5.5). Nada se toma de la codificación heredada
(`Datos_Cuidador_corregido.csv` / `Datos_Cuidador_AUDIT.xlsx`), que es
defectuosa.

Marco cuidador: PSS-10 (0–40, inversos 3, 4, 5, 7 y 9, prorrateo con 9 de 10),
EPDS-10 (0–30, los 10 ítems), señales de ánimo (≥ 10 posible, ≥ 13 probable) y
de autolesión (ítem 10 ≠ «No, nunca»), MSPSS por fuente (media 1–5, 5 / 4 / 3
ítems), índice de riesgo del barrio (0–10), castigo físico (APQ 22–24 «a veces
o más») y grito (APQ 25), descriptivos.

Marco niño: SDQ de padres con las subescalas estándar y las bandas
`BANDS_PARENT`; si la edad es numérica y cae fuera de 4–17, el SDQ es faltante.
ARI de padres: ítems 1–6 (0–12) y deterioro (ítem 7).

Las tablas (`descriptivos`, `sobre_cortes_*`, `terciles`, `fiabilidad`) tienen
la misma forma que las de estudiantes, para que `estudiantes.supresion` y la
vista las traten igual.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.cuidadores import catalog as cat
from src.estudiantes import catalog as cat_est
from src.estudiantes import scoring as sc_est
from src.estudiantes.stats import wilson


def _suma_prorrateada(X: pd.DataFrame, minimo: int) -> pd.Series:
    respondidos = X.notna().sum(axis=1)
    s = X.sum(axis=1) * X.shape[1] / respondidos.replace(0, np.nan)
    return s.mask(respondidos < minimo)


def _media_completa(X: pd.DataFrame) -> pd.Series:
    return X.mean(axis=1).mask(X.isna().any(axis=1))


def _indicador(condicion: pd.Series, base: pd.Series) -> pd.Series:
    """1 / 0 donde hay dato; NaN donde no."""
    return condicion.astype(float).where(base)


# ── marco cuidador ─────────────────────────────────────────────────────────
def pss_orientada(d: pd.DataFrame) -> pd.DataFrame:
    X = d[cat.PSS.columnas].copy()
    for i in cat.PSS_INVERSOS:
        X[f"PSS{i}"] = (cat.PSS.valor_min + cat.PSS.valor_max) - X[f"PSS{i}"]
    return X


def puntuar_cuidadores(d: pd.DataFrame) -> pd.DataFrame:
    """Copia con PSS, EPDS, MSPSS, barrio y castigo físico añadidos."""
    out = d.copy()
    nuevas: dict[str, pd.Series] = {}
    nuevas["PSS_Total"] = _suma_prorrateada(pss_orientada(d), cat.PSS_MIN_ITEMS).round(1)
    epds = d[cat.EPDS.columnas]
    total = epds.sum(axis=1).mask(epds.isna().any(axis=1))
    nuevas["EPDS_Total"] = total
    nuevas["EPDS_Posible"] = _indicador(total >= cat.EPDS_POSIBLE, total.notna())
    nuevas["EPDS_Probable"] = _indicador(total >= cat.EPDS_PROBABLE, total.notna())
    item10 = d[f"EPDS{cat.EPDS_ITEM_AUTOLESION}"]
    nuevas["EPDS_Autolesion"] = _indicador(item10 >= 1, item10.notna())
    for clave, items in cat.MSPSS_FUENTES.items():
        nuevas[clave] = _media_completa(d[[f"MSPSS{i}" for i in items]])
    nuevas["MSPSS_Total"] = _media_completa(d[cat.MSPSS.columnas])
    barrio = d[cat.BARRIO.columnas]
    nuevas["BARRIO_Indice"] = barrio.sum(axis=1).mask(barrio.isna().any(axis=1))
    fisico = d[[f"APQ{i}" for i in cat.APQ_FISICO]]
    nuevas["APQ_Fisico"] = _indicador((fisico >= cat.APQ_UMBRAL).any(axis=1),
                                      fisico.notna().all(axis=1))
    grito = d[f"APQ{cat.APQ_GRITO}"]
    nuevas["APQ_Grito"] = _indicador(grito >= cat.APQ_UMBRAL, grito.notna())
    return pd.concat([out, pd.DataFrame(nuevas, index=d.index)], axis=1)


# ── marco niño ─────────────────────────────────────────────────────────────
def puntuar_ninos(d: pd.DataFrame) -> pd.DataFrame:
    """Copia con el SDQ de padres (subescalas, compuestas y bandas) y el ARI-P."""
    out = d.copy()
    sdq_cols = cat_est.SDQ.columnas
    if "_edad_estado" in out.columns:
        fuera = out["_edad_estado"] == "fuera_de_rango"
        out.loc[fuera, sdq_cols] = np.nan
    nuevas: dict[str, pd.Series] = {}
    for sub in cat_est.SDQ.subescalas:
        X = sc_est.items_orientados(out, sub, cat_est.SDQ)
        nuevas[sub.key] = _suma_prorrateada(X, sub.min_items).round(0)
    for clave, c in cat_est.COMPUESTAS.items():
        nuevas[clave] = pd.concat([nuevas[p] for p in c["partes"]], axis=1).sum(
            axis=1, min_count=len(c["partes"]))
    ari = out[[f"ARI{i}" for i in cat.ARI_ITEMS_TOTAL]]
    nuevas["ARI_Total"] = ari.sum(axis=1).mask(ari.isna().any(axis=1))
    nuevas["ARI_Deterioro"] = out[f"ARI{cat.ARI_ITEM_DETERIORO}"]
    out = pd.concat([out, pd.DataFrame(nuevas, index=out.index)], axis=1)
    for key in cat_est.BANDS_PARENT:
        out[f"banda_{key}"] = out[key].map(
            lambda v: cat_est.banda_de(v, key, "parent") if pd.notna(v) else np.nan)
    return out


# ── tablas ─────────────────────────────────────────────────────────────────
def disponibles(d: pd.DataFrame, claves: list[str]) -> list[str]:
    return [k for k in claves if k in d.columns and d[k].notna().any()]


def descriptivos(d: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    filas = []
    for k in disponibles(d, claves):
        v = d[k].dropna()
        p = cat.PUNTUACIONES_POR_CLAVE[k]
        filas.append(dict(
            clave=k, escala=p.label, n=len(v), M=round(float(v.mean()), 2),
            DE=round(float(v.std(ddof=1)), 2) if len(v) > 1 else np.nan,
            Mdn=round(float(v.median()), 2), min=float(v.min()), max=float(v.max()),
            rango=f"{p.rango[0]:g}–{p.rango[1]:g}",
            pct_faltante=round(100 * (1 - len(v) / len(d)), 1) if len(d) else np.nan,
            P25=round(float(v.quantile(.25)), 2), P75=round(float(v.quantile(.75)), 2),
            direccion=p.direccion, fuente=p.fuente))
    return pd.DataFrame(filas)


def fiabilidad(d: pd.DataFrame, n_boot: int = 300) -> pd.DataFrame:
    """α con IC por bootstrap (casos completos), con los ítems ya orientados."""
    conjuntos: dict[str, pd.DataFrame] = {}
    if set(cat.PSS.columnas) <= set(d.columns):
        conjuntos["PSS_Total"] = pss_orientada(d)
    if set(cat.EPDS.columnas) <= set(d.columns):
        conjuntos["EPDS_Total"] = d[cat.EPDS.columnas]
    if set(cat.MSPSS.columnas) <= set(d.columns):
        conjuntos["MSPSS_Total"] = d[cat.MSPSS.columnas]
        for clave, items in cat.MSPSS_FUENTES.items():
            conjuntos[clave] = d[[f"MSPSS{i}" for i in items]]
    if set(cat.BARRIO.columnas) <= set(d.columns):
        conjuntos["BARRIO_Indice"] = d[cat.BARRIO.columnas]
    if set(cat_est.SDQ.columnas) <= set(d.columns):
        for sub in cat_est.SDQ.subescalas:
            conjuntos[sub.key] = sc_est.items_orientados(d, sub, cat_est.SDQ)
        conjuntos["SDQ_Total"] = pd.concat(
            [sc_est.items_orientados(d, cat_est.subescala(s), cat_est.SDQ)
             for s in cat_est.SDQ_SUBS_DIFICULTADES], axis=1)
    ari_cols = [f"ARI{i}" for i in cat.ARI_ITEMS_TOTAL]
    if set(ari_cols) <= set(d.columns):
        conjuntos["ARI_Total"] = d[ari_cols]
    filas = []
    for clave, X in conjuntos.items():
        a, lo, hi, n = sc_est.alpha_ci(X, n_boot=n_boot)
        filas.append(dict(clave=clave, escala=cat.label(clave), n_items=X.shape[1], n=n,
                          alpha=round(a, 3) if not np.isnan(a) else None,
                          ic_inf=round(lo, 3) if not np.isnan(lo) else None,
                          ic_sup=round(hi, 3) if not np.isnan(hi) else None))
    return pd.DataFrame(filas)


def _agrega(filas: list, clave: str, etiqueta: str, mask: pd.Series, base: pd.Series,
            fuente: str) -> None:
    base_n = int(base.sum())
    if base_n == 0:
        return
    k = int((mask & base).sum())
    p, lo, hi = wilson(k, base_n)
    filas.append(dict(clave=clave, indicador=etiqueta, n=base_n, casos=k, pct=p,
                      ic_inf=lo, ic_sup=hi, fuente=fuente))


def sobre_cortes_cuidador(d: pd.DataFrame) -> pd.DataFrame:
    """Prevalencias del marco cuidador (forma de estudiantes.scoring.sobre_cortes).

    Las dos filas de la EPDS comparten la clave «EPDS_Total»: son cortes
    anidados de la misma escala y la supresión las reparte en tres partes.
    """
    filas: list = []
    if "EPDS_Total" in d.columns:
        t = d["EPDS_Total"]
        _agrega(filas, "EPDS_Total", f"Ánimo: posible (EPDS ≥ {cat.EPDS_POSIBLE})",
                t >= cat.EPDS_POSIBLE, t.notna(), cat.EPDS.fuente)
        _agrega(filas, "EPDS_Total", f"Ánimo: probable (EPDS ≥ {cat.EPDS_PROBABLE})",
                t >= cat.EPDS_PROBABLE, t.notna(), cat.EPDS.fuente)
    if "EPDS_Autolesion" in d.columns:
        a = d["EPDS_Autolesion"]
        _agrega(filas, "EPDS_Autolesion",
                "Autolesión: pensó en hacerse daño (ítem 10 distinto de «No, nunca»)",
                a == 1, a.notna(), "EPDS ítem 10; señal para indagar, no diagnóstico")
    if "APQ_Fisico" in d.columns:
        f = d["APQ_Fisico"]
        _agrega(filas, "APQ_Fisico", "Usa alguna forma de castigo físico, a veces o más",
                f == 1, f.notna(), "APQ ítems 22–24 (columnas 78–80); descriptivo")
    if "APQ_Grito" in d.columns:
        g = d["APQ_Grito"]
        _agrega(filas, "APQ_Grito", "Grita al hijo cuando se porta mal, a veces o más",
                g == 1, g.notna(), "APQ ítem 25 (columna 81); descriptivo")
    for k in ("MSPSS_Total", "MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro"):
        if k in d.columns:
            _agrega(filas, k, f"{cat.label(k)}: media por debajo de 3 (descriptivo)",
                    d[k] < 3, d[k].notna(),
                    "Umbral descriptivo (punto medio de la escala), no clínico")
    return pd.DataFrame(filas)


def sobre_cortes_nino(d: pd.DataFrame) -> pd.DataFrame:
    """SDQ de padres «alto o muy alto» por subescala, con las bandas de padres."""
    filas: list = []
    for key in cat_est.BANDS_PARENT:
        if key not in d.columns:
            continue
        b = d[key].map(lambda x: cat_est.banda_de(x, key, "parent") if pd.notna(x) else np.nan)
        etiqueta = ("Prosocial bajo o muy bajo" if key == "SDQ_Pro"
                    else f"{cat.label(key)}: alto o muy alto")
        _agrega(filas, key, etiqueta, b >= 2, d[key].notna(),
                "Scoring the SDQ for age 4-17, versión para padres, sdqinfo.org")
    return pd.DataFrame(filas)


def bandas_nino(d: pd.DataFrame) -> pd.DataFrame:
    """Bandas del SDQ de padres (misma forma que estudiantes)."""
    t = sc_est.distribucion_bandas(d, "parent")
    if not t.empty:
        t["escala"] = t["clave"].map(cat.label)
    return t


def terciles(d: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for k in cat.CLAVES_TERCILES:
        if k not in d.columns:
            continue
        v = d[k].dropna()
        if len(v) < cat.MIN_GROUP_N:
            continue
        filas.append(dict(clave=k, escala=cat.label(k), n=len(v),
                          corte_bajo=round(float(v.quantile(1 / 3)), 2),
                          corte_alto=round(float(v.quantile(2 / 3)), 2),
                          nota="Relativo a esta muestra, no clínico"))
    return pd.DataFrame(filas)


# ── ítems descriptivos (solo vista local de investigadores) ────────────────
def distribucion_items(d: pd.DataFrame, bloque: cat.Bloque, enunciados: list[str] | None = None,
                       umbral: int | None = None) -> pd.DataFrame:
    """Por ítem: n, media y % con respuesta ≥ umbral (sin conteos de casos)."""
    filas = []
    for i, col in enumerate(bloque.columnas, start=1):
        if col not in d.columns:
            continue
        v = d[col].dropna()
        if v.empty:
            continue
        fila = dict(item=i, columna=bloque.inicio + i - 1,
                    enunciado=(enunciados[i - 1] if enunciados else col),
                    n=len(v), M=round(float(v.mean()), 2))
        if umbral is not None:
            k = int((v >= umbral).sum())
            fila["casos"] = k                     # se quita antes de mostrar
            fila["pct"] = round(100 * k / len(v), 1)
        filas.append(fila)
    return pd.DataFrame(filas)
