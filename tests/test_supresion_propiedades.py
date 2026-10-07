"""Propiedad: `supresion.fugas` coincide con la fuerza bruta sobre jerarquías al azar.

La fuerza bruta recorre todos los subconjuntos de átomos, se queda con los
deducibles de lo publicado (ortogonales al espacio nulo) y busca los que
incumplen la regla. Adaptado de la revisión independiente (rev2/fuzz.py).
"""
import random

import numpy as np

from src.estudiantes import supresion as sp


def _fuerza_bruta(jer, partes, pub, minimo=sp.MIN_CASOS) -> set[frozenset]:
    vivos = sorted(a for a, p in partes.items() if sum(p) > 0)
    if not vivos:
        return set()
    col = {a: i for i, a in enumerate(vivos)}
    filas = []
    for g in pub:
        v = np.zeros(len(vivos))
        for a in jer.grupos.get(g, ()):
            if a in col:
                v[col[a]] = 1
        if v.any():
            filas.append(v)
    if not filas:
        return set()
    _, s, vt = np.linalg.svd(np.vstack(filas))
    z = vt[int((s > 1e-9).sum()):]
    n = len(vivos)
    P = np.array([partes[a] for a in vivos])
    idx = np.arange(1, 1 << n)
    B = ((idx[:, None] >> np.arange(n)) & 1).astype(float)
    en_espacio = (np.all(np.abs(B @ z.T) < 1e-7, axis=1) if z.shape[0]
                  else np.ones(len(idx), bool))
    malos = set()
    for m in idx[en_espacio]:
        S = [i for i in range(n) if m >> i & 1]
        if not sp.union_segura(P[S].sum(axis=0), minimo):
            malos.add(frozenset(vivos[i] for i in S))
    return malos


def _caso(rng):
    cols = [f"C{i}" for i in range(rng.randint(1, 5))]
    grs = [f"G{j}" for j in range(rng.randint(1, 4))]
    celdas = [f"{c}|{g}" for c in cols for g in grs if rng.random() < rng.choice([.5, .8, 1])]
    extra = [f"S{i}" for i in range(rng.randint(0, 2))]
    resto = rng.random() < .7
    largo = rng.choice([2, 2, 3, 4])
    colegios = sorted({k.split("|")[0] for k in celdas}) + extra
    jer = sp.jerarquia(celdas, colegios, sorted({k.split("|")[1] for k in celdas}), resto)

    def partes():
        n = rng.randint(10, 30)
        if largo == 2:
            k = max(0, min(n, rng.choice([0, 1, 2, 3, 4, 5, rng.randint(0, n), n - 1, n])))
            return (k, n - k)
        cortes = sorted(rng.choices(range(n + 1), k=largo - 1))
        if rng.random() < .5:
            cortes[0] = rng.choice([0, 1, 2])
        return tuple([cortes[0]] + [cortes[i] - cortes[i - 1] for i in range(1, len(cortes))]
                     + [n - cortes[-1]])
    p = {sp.atomo_celda(k): partes() for k in celdas}
    p.update({sp.atomo_colegio(c): partes() for c in extra})
    if resto:
        p[sp.RESTO] = partes()
    return jer, p


def test_fugas_y_suprimir_contra_fuerza_bruta():
    rng = random.Random(20261007)
    probados = 0
    while probados < 400:
        jer, partes = _caso(rng)
        if not 2 <= len(partes) <= 12:
            continue
        probados += 1
        # 1. lo que deja `suprimir` cumple la regla primaria y no tiene fugas
        sup = sp.suprimir(jer, partes)
        pub = sp.publicados(jer, sup)
        largo = sp._largo(partes)
        for g in pub:
            assert sp.partes_publicables(sp._suma(jer.grupos[g], partes, largo)), g
        assert _fuerza_bruta(jer, partes, pub) == set()
        # 2. sobre una publicación al azar, fugas detecta lo mismo que la fuerza bruta
        azar = {g for g in jer.grupos if g not in jer.nunca and rng.random() < .6}
        bruta = _fuerza_bruta(jer, partes, azar)
        halladas = sp.fugas(jer, partes, azar)
        assert bool(bruta) == bool(halladas)
        assert set(halladas) <= bruta
