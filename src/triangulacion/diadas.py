"""
Capa 2 de la triangulación — análisis de díadas niño–cuidador (solo local).

Entra la tabla de díadas de `enlace.enlazar` (solo en memoria) y sale un
`Diadas` con tablas AGREGADAS:

  · `acuerdo`: SDQ del niño (autoinforme, bandas de autoinforme) frente al de
    su cuidador (versión para padres, bandas de padres), por subescala:
    Spearman y Pearson con IC de Fisher, CCI(A,1) y kappa ponderado lineal
    sobre las 4 bandas (IC por bootstrap de familias), diferencia media
    (niño − cuidador) con IC por errores agrupados y límites de Bland–Altman.
  · `bland_altman`: la figura agrupada, sin díadas: hasta 5 grupos por
    quintil del promedio de los dos informantes, cada uno con ≥ 10 díadas de
    ≥ 10 familias (si no caben, menos grupos).
  · `no_visto`: «malestar que el cuidador no ve» = el niño en banda alta o
    muy alta (o con la señal de malestar) y el cuidador lo ubica en la banda
    «cercano al promedio». % sobre todas las díadas, % de niños con malestar y
    % no visto entre ellos, con IC de Wilson. Las tres partes (sin malestar,
    malestar visto, malestar no visto) cumplen la regla 3 ≤ k ≤ n − 3 en
    díadas y en familias; si no, no se muestra ninguna cifra.
  · `apoyo`: MSPSS del niño frente al del cuidador, por fuente (aviso fijo:
    redacción y reparto de ítems distintos; no es acuerdo sobre lo mismo).
  · `asociaciones`: EPDS, PSS, castigo físico y barrio del cuidador con el
    SDQ del niño (total, internalizante, externalizante): MCO estandarizado,
    controles de sexo y edad del niño, efecto fijo de colegio y errores
    agrupados por familia; sensibilidad solo con Laura Vicuña.
  · Sensibilidad de concordancia (`acuerdo_concordantes` y una muestra más en
    `asociaciones`): sin las díadas en que niño y cuidador no concuerdan en
    sexo, edad (± 1 año) o grado. Solo se muestra si lo excluido (que saldría
    restando de la cifra principal) es 0 o ≥ 10 díadas de ≥ 10 familias.

Reglas de cifras pequeñas: toda cifra exige ≥ 10 díadas de ≥ 10 familias
distintas (los modelos, ≥ 30 díadas completas); un predictor binario exige
≥ 10 díadas y familias en cada nivel. Ninguna tabla lleva una díada.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.estudiantes import catalog as cat_est
from src.estudiantes.stats import benjamini_hochberg, wilson
from src.triangulacion import catalogo as cat
from src.triangulacion import estadistica as est

FAMILIA = "familia"
MOTIVO_POCAS = "menos de 10 díadas o de 10 familias"
MOTIVO_PEQUENAS = "cifras pequeñas: alguna parte con menos de 3 díadas o familias"
MOTIVO_MODELO = "menos de 30 díadas completas o de 10 familias"
MOTIVO_SINGULAR = "el modelo no se puede estimar (predictores redundantes)"
MOTIVO_SENSIBILIDAD = ("las díadas excluidas por la sensibilidad serían de 1 a 9 o de menos "
                       "de 10 familias (saldrían restando)")
MUESTRA_TODAS = "Todas las díadas (efecto fijo de colegio)"
MUESTRA_LAUV = "Solo Laura Vicuña (sensibilidad)"
MUESTRA_CONCORDANTES = ("Díadas que concuerdan en sexo, edad (± 1) y grado (sensibilidad, "
                        "efecto fijo de colegio)")


@dataclass
class Diadas:
    n: int = 0
    familias: int = 0
    acuerdo: pd.DataFrame = field(default_factory=pd.DataFrame)
    bland_altman: pd.DataFrame = field(default_factory=pd.DataFrame)
    no_visto: pd.DataFrame = field(default_factory=pd.DataFrame)
    apoyo: pd.DataFrame = field(default_factory=pd.DataFrame)
    asociaciones: pd.DataFrame = field(default_factory=pd.DataFrame)
    acuerdo_concordantes: pd.DataFrame = field(default_factory=pd.DataFrame)


def _r(v, dec: int = 3):
    return None if v is None or pd.isna(v) else round(float(v), dec)


def bandas(serie: pd.Series, clave: str, version: str) -> pd.Series:
    return serie.map(lambda v: cat_est.banda_de(v, clave, version) if pd.notna(v) else np.nan
                     ).astype(float)


def _par(D: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    if a not in D.columns or b not in D.columns:
        return D.iloc[0:0][[FAMILIA]]
    return D[[a, b, FAMILIA]].dropna()


def concordantes(D: pd.DataFrame) -> pd.Series:
    """Díadas sin discordancia de sexo, edad (más de ± 1 año) ni grado.

    Solo es discordancia cuando los dos informantes dan el dato y no coinciden;
    sin dato en alguno de los dos, la díada se queda.
    """
    from src.triangulacion.enlace import SEXO_NINO
    ok = pd.Series(True, index=D.index)
    if {"e_Sexo", "c_Sexo"} <= set(D.columns):
        c = D["c_Sexo"].map(SEXO_NINO)
        ok &= ~(c.notna() & D["e_Sexo"].isin(SEXO_NINO.values()) & (c != D["e_Sexo"]))
    if {"e_Edad", "c_Edad"} <= set(D.columns):
        dif = (pd.to_numeric(D["e_Edad"], errors="coerce")
               - pd.to_numeric(D["c_Edad"], errors="coerce")).abs()
        ok &= ~(dif > 1)
    if {"e_Grado", "c_Grado"} <= set(D.columns):
        ok &= ~(D["e_Grado"].notna() & D["c_Grado"].notna() & (D["e_Grado"] != D["c_Grado"]))
    return ok


def excluidas_seguras(excluidas: pd.DataFrame) -> bool:
    """Lo que una sensibilidad quita (y saldría restando) es 0 o ≥ 10 díadas y familias."""
    return excluidas.empty or est.suficiente(excluidas, FAMILIA)


def acuerdo_sdq(D: pd.DataFrame, n_boot: int = cat.N_BOOT) -> pd.DataFrame:
    filas = []
    for s in cat.SUBESCALAS_SDQ:
        e, c = f"e_{s}", f"c_{s}"
        sub = _par(D, e, c)
        fila = dict(subescala=s, escala=cat_est.meta(s)["label"])
        if not est.suficiente(sub, FAMILIA):
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        rho = est.correlacion_ic(sub[e], sub[c], "spearman")
        r = est.correlacion_ic(sub[e], sub[c], "pearson")
        icc = est.icc_a1(sub[[e, c]].to_numpy())
        icc_ic = est.bootstrap_ic(sub, lambda x: est.icc_a1(x[[e, c]].to_numpy()), FAMILIA,
                                  n_boot)
        be, bc = bandas(sub[e], s, "self"), bandas(sub[c], s, "parent")
        kw = est.kappa_ponderado(be, bc)
        kw_ic = est.bootstrap_ic(
            sub.assign(_be=be, _bc=bc),
            lambda x: est.kappa_ponderado(x["_be"], x["_bc"]), FAMILIA, n_boot)
        ba = est.bland_altman(sub[e], sub[c])
        mg = est.media_agrupada(sub[e] - sub[c], sub[FAMILIA])
        filas.append({**fila, "n": len(sub), "familias": int(sub[FAMILIA].nunique()),
                      "media_nino": _r(sub[e].mean(), 2), "media_cuidador": _r(sub[c].mean(), 2),
                      "rho": _r(rho[0]), "rho_ic_inf": _r(rho[1]), "rho_ic_sup": _r(rho[2]),
                      "r": _r(r[0]), "r_ic_inf": _r(r[1]), "r_ic_sup": _r(r[2]),
                      "cci": _r(icc), "cci_ic_inf": _r(icc_ic[0]), "cci_ic_sup": _r(icc_ic[1]),
                      "dif_media": _r(mg["m"], 2), "dif_ic_inf": _r(mg["ic_inf"], 2),
                      "dif_ic_sup": _r(mg["ic_sup"], 2), "ba_lim_inf": _r(ba["lim_inf"], 2),
                      "ba_lim_sup": _r(ba["lim_sup"], 2), "kappa_w": _r(kw),
                      "kappa_ic_inf": _r(kw_ic[0]), "kappa_ic_sup": _r(kw_ic[1]), "motivo": ""})
    return pd.DataFrame(filas)


def acuerdo_concordantes(D: pd.DataFrame, n_boot: int = cat.N_BOOT) -> pd.DataFrame:
    """`acuerdo_sdq` sin las díadas discordantes, si lo excluido no sale restando."""
    conc = concordantes(D)
    t = acuerdo_sdq(D[conc], n_boot)
    for s in cat.SUBESCALAS_SDQ:
        sub = _par(D, f"e_{s}", f"c_{s}")
        if not excluidas_seguras(sub[~conc.loc[sub.index]]):
            fila = t["subescala"] == s
            t.loc[fila, [c for c in t.columns if c not in ("subescala", "escala")]] = np.nan
            t.loc[fila, "motivo"] = MOTIVO_SENSIBILIDAD
    return t


def bland_altman_agrupado(D: pd.DataFrame) -> pd.DataFrame:
    """Promedio de la diferencia por grupos de ≥ 10 díadas y familias (sin puntos individuales)."""
    filas = []
    for s in cat.SUBESCALAS_SDQ:
        e, c = f"e_{s}", f"c_{s}"
        sub = _par(D, e, c)
        if not est.suficiente(sub, FAMILIA):
            continue
        x = (sub[e] + sub[c]) / 2
        dif = sub[e] - sub[c]
        for nb in range(cat.MAX_BINES_BA, 0, -1):
            grupo = (pd.qcut(x.rank(method="first"), nb, labels=False) if nb > 1
                     else pd.Series(0, index=x.index))
            if all(est.suficiente(sub[grupo == g], FAMILIA) for g in range(nb)):
                break
        for g in range(nb):
            m = grupo == g
            mg = est.media_agrupada(dif[m], sub.loc[m, FAMILIA])
            filas.append(dict(subescala=s, grupo=g + 1, n=int(m.sum()),
                              promedio_informantes=_r(x[m].mean(), 2),
                              dif_media=_r(mg["m"], 2), ic_inf=_r(mg["ic_inf"], 2),
                              ic_sup=_r(mg["ic_sup"], 2)))
    return pd.DataFrame(filas)


def malestar_no_visto(D: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for etiqueta, s, con_senal in cat.VARIANTES_NO_VISTO:
        e, c = f"e_{s}", f"c_{s}"
        fila = dict(variante=etiqueta)
        if e not in D.columns or c not in D.columns:
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        sub = D[D[e].notna() & D[c].notna()]
        if not est.suficiente(sub, FAMILIA):
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        malestar = bandas(sub[e], s, "self") >= 2
        if con_senal and "e_ALERTA_malestar" in sub.columns:
            malestar = malestar | (sub["e_ALERTA_malestar"] == 1)
        no_visto = malestar & (bandas(sub[c], s, "parent") == 0)
        parte = pd.Series(np.where(~malestar, 0, np.where(no_visto, 2, 1)), index=sub.index)
        if not est.partes_seguras(parte, sub[FAMILIA], (0, 1, 2)):
            filas.append({**fila, "n": len(sub), "motivo": MOTIVO_PEQUENAS})
            continue
        n, k_m, k = len(sub), int(malestar.sum()), int(no_visto.sum())
        p, lo, hi = wilson(k, n)
        pm, lom, him = wilson(k_m, n)
        pe, loe, hie = wilson(k, k_m)
        filas.append({**fila, "n": n, "familias": int(sub[FAMILIA].nunique()),
                      "pct_no_visto": p, "ic_inf": lo, "ic_sup": hi,
                      "pct_malestar": pm, "malestar_ic_inf": lom, "malestar_ic_sup": him,
                      "pct_no_visto_entre_malestar": pe, "entre_ic_inf": loe,
                      "entre_ic_sup": hie, "motivo": ""})
    return pd.DataFrame(filas)


def apoyo_familiar(D: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for clave, nombre in cat.FUENTES_MSPSS:
        e, a = f"e_{clave}", f"a_{clave}"
        sub = _par(D, e, a)
        fila = dict(fuente=nombre)
        if not est.suficiente(sub, FAMILIA):
            filas.append({**fila, "motivo": MOTIVO_POCAS})
            continue
        rho = est.correlacion_ic(sub[e], sub[a], "spearman")
        mg = est.media_agrupada(sub[e] - sub[a], sub[FAMILIA])
        filas.append({**fila, "n": len(sub), "familias": int(sub[FAMILIA].nunique()),
                      "media_nino": _r(sub[e].mean(), 2), "media_cuidador": _r(sub[a].mean(), 2),
                      "rho": _r(rho[0]), "rho_ic_inf": _r(rho[1]), "rho_ic_sup": _r(rho[2]),
                      "dif_media": _r(mg["m"], 2), "dif_ic_inf": _r(mg["ic_inf"], 2),
                      "dif_ic_sup": _r(mg["ic_sup"], 2), "motivo": ""})
    return pd.DataFrame(filas)


def _z(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=1)


def _columnas_modelo(y: str) -> list[str]:
    return [f"e_{y}", *[f"a_{p}" for p, _, _ in cat.PREDICTORES], "e_Sexo", "e_Edad",
            FAMILIA, "Colegio"]


def _modelo(datos: pd.DataFrame, y: str, etiqueta_y: str, muestra: str,
            efecto_fijo: bool) -> list[dict]:
    cols = _columnas_modelo(y)
    if any(c not in datos.columns for c in cols):
        return [dict(muestra=muestra, resultado=etiqueta_y, motivo=MOTIVO_MODELO)]
    sub = datos[cols].dropna()
    base = dict(muestra=muestra, resultado=etiqueta_y)
    if len(sub) < cat.MIN_MODELO or sub[FAMILIA].nunique() < cat.MIN_GROUP_N:
        return [{**base, "motivo": MOTIVO_MODELO}]
    X, omitidos = pd.DataFrame(index=sub.index), []
    for p, etiqueta, binario in cat.PREDICTORES:
        v = sub[f"a_{p}"].astype(float)
        if binario:
            niveles_ok = all(est.suficiente(sub[v == nivel], FAMILIA) for nivel in (0.0, 1.0))
            if not niveles_ok:
                omitidos.append(etiqueta)
                continue
            X[etiqueta] = v
        elif v.std(ddof=1) > 0:
            X[etiqueta] = _z(v)
    controles = pd.DataFrame({"_mujer": (sub["e_Sexo"] == "Mujer").astype(float),
                              "_edad": sub["e_Edad"].astype(float)}, index=sub.index)
    controles = controles.loc[:, controles.std(ddof=1) > 0]
    if "_edad" in controles:
        controles["_edad"] = _z(controles["_edad"])
    try:
        res = est.ols_agrupado(_z(sub[f"e_{y}"].astype(float)),
                               pd.concat([X, controles], axis=1), sub[FAMILIA],
                               sub["Colegio"] if efecto_fijo else None)
    except np.linalg.LinAlgError:
        return [{**base, "motivo": MOTIVO_SINGULAR}]
    res = res[res["predictor"].isin(X.columns)]
    nota = ("Omitido por cifras pequeñas: " + ", ".join(omitidos)) if omitidos else ""
    return [{**base, "predictor": f["predictor"], "beta": _r(f["beta"]), "ic_inf": _r(f["ic_inf"]),
             "ic_sup": _r(f["ic_sup"]), "p": _r(f["p"], 4), "n": len(sub),
             "familias": int(sub[FAMILIA].nunique()), "colegios": int(sub["Colegio"].nunique()),
             "motivo": "", "nota": nota} for _, f in res.iterrows()]


def asociaciones(D: pd.DataFrame) -> pd.DataFrame:
    conc = concordantes(D)
    muestras = ((MUESTRA_TODAS, D, True),
                (MUESTRA_LAUV, D[D["Colegio"] == cat.COLEGIO_SENSIBILIDAD], False),
                (MUESTRA_CONCORDANTES, D[conc], True))
    filas = []
    for muestra, datos, ef in muestras:
        for y, etiqueta_y in cat.RESULTADOS:
            if muestra == MUESTRA_CONCORDANTES:
                cols = [c for c in _columnas_modelo(y) if c in D.columns]
                completas = D[cols].dropna()
                if not excluidas_seguras(completas[~conc.loc[completas.index]]):
                    filas.append(dict(muestra=muestra, resultado=etiqueta_y,
                                      motivo=MOTIVO_SENSIBILIDAD))
                    continue
            filas += _modelo(datos, y, etiqueta_y, muestra, ef)
    t = pd.DataFrame(filas)
    if not t.empty and "p" in t.columns:
        t["q_bh"] = np.nan
        for muestra, sub in t[t["p"].notna()].groupby("muestra"):
            t.loc[sub.index, "q_bh"] = np.round(benjamini_hochberg(sub["p"].to_numpy()), 4)
    return t


def analizar(D: pd.DataFrame, n_boot: int = cat.N_BOOT) -> Diadas:
    if D.empty:
        return Diadas()
    return Diadas(n=len(D), familias=int(D[FAMILIA].nunique()),
                  acuerdo=acuerdo_sdq(D, n_boot), bland_altman=bland_altman_agrupado(D),
                  no_visto=malestar_no_visto(D), apoyo=apoyo_familiar(D),
                  asociaciones=asociaciones(D),
                  acuerdo_concordantes=acuerdo_concordantes(D, n_boot))
