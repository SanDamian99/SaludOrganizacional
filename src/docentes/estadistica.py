"""
Estadística mínima del módulo Docentes: IC t de una media, IC de Wilson de una
proporción y la proporción «protegida» (k ≥ 3 y n − k ≥ 3, como en Estudiantes
y Cuidadores). Sin Streamlit; funciones puras.
"""
from __future__ import annotations

import math

import pandas as pd
from scipy import stats as sps

from src.analysis.grupo_minimo import N_MINIMO

K_MINIMO = 3   # ningún % se publica si lo forman menos de 3 personas (o su complemento)


def ic_media(serie: pd.Series, z: float = 0.95) -> tuple[float | None, float | None, float | None]:
    """(media, IC inferior, IC superior) con la t de Student. Sin IC si n < 2."""
    s = pd.to_numeric(serie, errors="coerce").dropna()
    n = len(s)
    if n == 0:
        return None, None, None
    media = float(s.mean())
    if n < 2:
        return media, None, None
    se = float(s.std(ddof=1)) / math.sqrt(n)
    t = float(sps.t.ppf(0.5 + z / 2, n - 1))
    return media, media - t * se, media + t * se


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(%, IC inferior, IC superior) con el intervalo de Wilson, en porcentaje."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    medio = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(100 * p, 1), round(100 * max(0.0, centro - medio), 1),
            round(100 * min(1.0, centro + medio), 1))


def proporcion_protegida(k: int, n: int) -> dict:
    """% con IC de Wilson, o sin cifra si k < 3, n − k < 3 o n < 10.

    Devuelve {n, pct, ic_inf, ic_sup} y, solo cuando se puede mostrar, `k`.
    """
    k, n = int(k), int(n)
    if n < N_MINIMO or k < K_MINIMO or n - k < K_MINIMO:
        return {"n": n, "pct": None, "ic_inf": None, "ic_sup": None}
    pct, inf, sup = wilson(k, n)
    return {"n": n, "k": k, "pct": pct, "ic_inf": inf, "ic_sup": sup}


def ic_welch(a: pd.Series, b: pd.Series, z: float = 0.95
             ) -> tuple[float | None, float | None, float | None]:
    """(media(a) − media(b), IC inferior, IC superior) con la t de Welch.

    Para «colegio − resto». Sin IC si alguno de los grupos tiene menos de 2 casos
    o varianza nula en ambos.
    """
    a = pd.to_numeric(a, errors="coerce").dropna()
    b = pd.to_numeric(b, errors="coerce").dropna()
    if a.empty or b.empty:
        return None, None, None
    diff = float(a.mean() - b.mean())
    if len(a) < 2 or len(b) < 2:
        return diff, None, None
    va, vb = float(a.var(ddof=1)) / len(a), float(b.var(ddof=1)) / len(b)
    if va + vb == 0:
        return diff, None, None
    gl = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    t = float(sps.t.ppf(0.5 + z / 2, gl))
    se = math.sqrt(va + vb)
    return diff, diff - t * se, diff + t * se
