"""
Cifras que no delatan — supresión de proporciones con pocos casos (Estudiantes 360).

Spec 2026-10-06, §5.4. Una proporción sobre un grupo de n respuestas con k
casos solo se publica o se muestra si

        MIN_CASOS ≤ k ≤ n − MIN_CASOS.

Con k = 0, 1, 2 (o n − 2, n − 1, n), cualquiera que conozca a un estudiante del
grupo puede deducir su respuesta. Se publica el porcentaje y el n, así que el
número de casos (k = % × n) es público aunque no se escriba: por eso la regla
va sobre la proporción y el campo `casos` ya no se publica.

INDICADORES COMO PARTICIONES
Cada indicador reparte las respuestas válidas de un grupo en partes:
  · un corte binario en (k, n − k);
  · las cuatro bandas del SDQ en (b0, b1, b2, b3); el corte «alto o muy alto»
    de esa misma escala es b2 + b3, así que bandas y corte se suprimen juntos;
  · dos cortes anidados de la misma escala (irritabilidad > 2 y ≥ 4) en
    (n − k₁, k₁ − k₂, k₂): publicar los dos deja ver la franja intermedia.
Un grupo se publica si TODAS sus partes cumplen la regla (todo o nada).

SUPRESIÓN COMPLEMENTARIA
La jerarquía tiene átomos (celdas colegio×grado, colegios publicados sin
celdas y el resto R de respuestas que solo cuentan en el nivel) y agregados
publicables (celda, colegio, grado, nivel), cada uno unión de átomos. R nunca
se publica. Tras la supresión primaria:

  1. Márgenes (la regla de la spec). Para cada agregado publicado y cada forma
     de partirlo en hijos (grado → celdas, colegio → celdas, nivel → colegios
     + R, nivel → grados + colegios sin celdas + R), la unión U de los hijos
     no publicados debe ser vacía o cumplir la regla. Si no, se oculta el hijo
     publicado de menor n; si no queda ninguno, el propio agregado. Se repite
     hasta que nada cambia.
  2. Auditoría exacta (`fugas`). Un conjunto S de átomos es deducible si su
     indicador está en el espacio generado por los agregados publicados (se
     calcula con el espacio nulo). Se buscan todos los S deducibles que
     incumplen la regla; para cada uno se elige el arreglo más barato: ocultar
     los agregados que separan un átomo s ∈ S de un átomo b ∉ S (queda e_s − e_b
     en el espacio nulo) o, si sale más barato, todos los que contienen a s.
     El coste es el número de átomos del agregado, así que se prefieren celdas
     a colegios o grados, y estos al nivel.
Cada arreglo oculta al menos un agregado, así que el proceso termina; en el
peor caso no se publica nada del indicador, que también cumple la regla.

CONTRASTES
Los contrastes por tercil comparan dos proporciones (tercil bajo y alto del
protector), cada una con su n. Se publican solo si las dos cumplen la regla.
Los terciles y el umbral (P90) se recalculan dentro de cada grupo, así que las
cifras de un colegio no son suma de las de sus celdas y no hay margen que
restar: basta la regla primaria.

LÍMITES (riesgo residual)
  · La auditoría es exacta para restas y sumas de cifras publicadas; no cubre
    cotas por desigualdades (p. ej. «el colegio tiene 3 casos, luego la celda
    oculta tiene como mucho 3»).
  · Componentes de más de MAX_ENUMERAR átomos ocultos ligados se revisan con
    subconjuntos de hasta 3 átomos y sus complementos, no exhaustivamente.
  · Las cifras de dos columnas con bases distintas (p. ej. solapamiento frente
    al corte del SDQ) quedan fuera, como en privacidad.auditar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd

MIN_CASOS = 3
MAX_ENUMERAR = 16
_TOL = 1e-8

AGRUPACION_CRUCE = "Colegio×Grado"     # = privacidad.AGRUPACION_CRUCE
SEP = "|"                              # = privacidad.SEP

# Nombres de agregados: (agrupación, grupo). El nivel es ("total", None).
NIVEL = ("total", None)
RESTO_GRUPO = ("resto", None)
RESTO = "resto"                        # átomo


def CELDA(clave: str) -> tuple:                                    # noqa: N802
    return (AGRUPACION_CRUCE, str(clave))


def COLEGIO(colegio: str) -> tuple:                                # noqa: N802
    return ("Colegio", str(colegio))


def GRADO(grado: str) -> tuple:                                    # noqa: N802
    return ("Grado", str(grado))


def atomo_celda(clave: str) -> str:
    return f"celda:{clave}"


def atomo_colegio(colegio: str) -> str:
    return f"colegio:{colegio}"


# ── regla primaria ─────────────────────────────────────────────────────────
def proporcion_publicable(k, n, minimo: int = MIN_CASOS) -> bool:
    """¿Se puede publicar k/n? Falso con n = 0 o k fuera de [minimo, n − minimo]."""
    try:
        k, n = int(k), int(n)
    except (TypeError, ValueError):
        return False
    return n > 0 and minimo <= k <= n - minimo


def partes_publicables(partes, minimo: int = MIN_CASOS) -> bool:
    """Todas las partes de un reparto cumplen la regla (todo o nada)."""
    partes = [int(p) for p in partes]
    n = sum(partes)
    return n > 0 and len(partes) >= 2 and all(minimo <= p <= n - minimo for p in partes)


def union_segura(partes, minimo: int = MIN_CASOS) -> bool:
    """Un conjunto deducible es seguro si está vacío o cumple la regla."""
    return sum(int(p) for p in partes) == 0 or partes_publicables(partes, minimo)


def contraste_publicable(c: dict, minimo: int = MIN_CASOS) -> bool:
    """Las dos proporciones del contraste (tercil bajo y alto) cumplen la regla."""
    return (proporcion_publicable(c.get("k_bajo"), c.get("n_bajo"), minimo)
            and proporcion_publicable(c.get("k_alto"), c.get("n_alto"), minimo))


# ── jerarquía ──────────────────────────────────────────────────────────────
@dataclass
class Jerarquia:
    grupos: dict = field(default_factory=dict)        # nombre → frozenset de átomos
    relaciones: list = field(default_factory=list)    # (padre, [hijos])
    nunca: frozenset = frozenset()                     # agregados que no se publican


def jerarquia(celdas, colegios, grados, con_resto: bool) -> Jerarquia:
    """Jerarquía de la base publicable (privacidad.base_publicable).

    `celdas` son claves «colegio|grado»; `colegios` y `grados`, los publicados.
    Un colegio con celdas es la unión de sus celdas; uno sin celdas es un átomo.
    """
    celdas = [str(c) for c in celdas]
    por_colegio: dict[str, list[str]] = {}
    por_grado: dict[str, list[str]] = {}
    for k in celdas:
        c, g = k.split(SEP, 1)
        por_colegio.setdefault(c, []).append(k)
        por_grado.setdefault(g, []).append(k)
    grupos: dict = {}
    for k in celdas:
        grupos[CELDA(k)] = frozenset({atomo_celda(k)})
    sin_celdas = []
    for c in map(str, colegios):
        if c in por_colegio:
            grupos[COLEGIO(c)] = frozenset(atomo_celda(k) for k in por_colegio[c])
        else:
            grupos[COLEGIO(c)] = frozenset({atomo_colegio(c)})
            sin_celdas.append(c)
    for g in map(str, grados):
        grupos[GRADO(g)] = frozenset(atomo_celda(k) for k in por_grado.get(g, []))
    resto = [RESTO_GRUPO] if con_resto else []
    if con_resto:
        grupos[RESTO_GRUPO] = frozenset({RESTO})
    grupos[NIVEL] = frozenset().union(*grupos.values()) if grupos else frozenset()

    relaciones = [
        (NIVEL, [COLEGIO(c) for c in map(str, colegios)] + resto),
        (NIVEL, [GRADO(g) for g in map(str, grados)]
         + [COLEGIO(c) for c in sin_celdas] + resto),
    ]
    for c, ks in por_colegio.items():
        if COLEGIO(c) in grupos:
            relaciones.append((COLEGIO(c), [CELDA(k) for k in ks]))
    for g, ks in por_grado.items():
        if GRADO(g) in grupos:
            relaciones.append((GRADO(g), [CELDA(k) for k in ks]))
    return Jerarquia(grupos=grupos, relaciones=relaciones,
                     nunca=frozenset({RESTO_GRUPO}) if con_resto else frozenset())


def _suma(atomos, partes: dict, largo: int) -> np.ndarray:
    total = np.zeros(largo, dtype=np.int64)
    for a in atomos:
        if a in partes:
            total += np.asarray(partes[a], dtype=np.int64)
    return total


def _largo(partes: dict) -> int:
    return max((len(p) for p in partes.values()), default=2)


def publicados(jer: Jerarquia, suprimidos) -> set:
    return {g for g in jer.grupos if g not in suprimidos and g not in jer.nunca}


# ── auditoría exacta ───────────────────────────────────────────────────────
def _componentes(z: np.ndarray) -> list[list[int]]:
    """Componentes conexas de las columnas de z (matroide): vía forma escalonada."""
    r = z.copy()
    filas, cols = r.shape
    fila = 0
    for col in range(cols):
        if fila >= filas:
            break
        piv = fila + int(np.argmax(np.abs(r[fila:, col])))
        if abs(r[piv, col]) < _TOL:
            continue
        r[[fila, piv]] = r[[piv, fila]]
        r[fila] /= r[fila, col]
        for i in range(filas):
            if i != fila and abs(r[i, col]) > _TOL:
                r[i] -= r[i, col] * r[fila]
        fila += 1
    padre = list(range(cols))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i
    for i in range(fila):
        nz = np.flatnonzero(np.abs(r[i]) > _TOL)
        for j in nz[1:]:
            padre[raiz(int(j))] = raiz(int(nz[0]))
    grupos: dict[int, list[int]] = {}
    for j in range(cols):
        if np.any(np.abs(z[:, j]) > _TOL):
            grupos.setdefault(raiz(j), []).append(j)
    return list(grupos.values())


def _subconjuntos(c: int):
    if c <= MAX_ENUMERAR:
        for m in range(1, 1 << c):
            yield [i for i in range(c) if m >> i & 1]
        return
    vistos = set()
    for t in (1, 2, 3):
        for comb in combinations(range(c), t):
            for s in (comb, tuple(i for i in range(c) if i not in comb)):
                if s and s not in vistos:
                    vistos.add(s)
                    yield list(s)
    yield list(range(c))


def fugas(jer: Jerarquia, partes: dict, pub, minimo: int = MIN_CASOS) -> list[frozenset]:
    """Conjuntos de átomos deducibles de los agregados `pub` que incumplen la regla.

    Lista vacía = nada de lo publicado deja, sumando o restando, un conjunto
    de respuestas con menos de `minimo` casos (o menos de `minimo` no casos).
    """
    largo = _largo(partes)
    vivos = sorted(a for a, p in partes.items() if sum(int(x) for x in p) > 0)
    if not vivos:
        return []
    col = {a: i for i, a in enumerate(vivos)}
    filas = []
    for g in pub:
        v = np.zeros(len(vivos))
        for a in jer.grupos.get(g, ()):
            if a in col:
                v[col[a]] = 1.0
        if v.any():
            filas.append(v)
    if not filas:
        return []
    m = np.vstack(filas)
    _, s, vt = np.linalg.svd(m)
    rango = int((s > 1e-9).sum())
    z = vt[rango:]                                   # base del espacio nulo (k × átomos)
    salida: list[frozenset] = []
    P = np.array([np.asarray(partes[a], dtype=np.int64) for a in vivos]).reshape(len(vivos), largo)
    determinados = ([j for j in range(len(vivos))] if z.shape[0] == 0 else
                    [j for j in range(len(vivos)) if not np.any(np.abs(z[:, j]) > _TOL)])
    for j in determinados:
        if not union_segura(P[j], minimo):
            salida.append(frozenset({vivos[j]}))
    if z.shape[0]:
        for comp in _componentes(z):
            for sub in _subconjuntos(len(comp)):
                idx = [comp[i] for i in sub]
                if np.any(np.abs(z[:, idx].sum(axis=1)) > 1e-7):
                    continue
                if not union_segura(P[idx].sum(axis=0), minimo):
                    salida.append(frozenset(vivos[j] for j in idx))
    salida.sort(key=lambda s: (int(_suma(s, partes, largo).sum()), sorted(s)))
    return salida


# ── supresión ──────────────────────────────────────────────────────────────
def _n(jer, g, partes, largo) -> int:
    return int(_suma(jer.grupos.get(g, ()), partes, largo).sum())


def suprimir(jer: Jerarquia, partes: dict, minimo: int = MIN_CASOS) -> set:
    """Agregados que no se publican para un indicador (primaria + complementaria).

    `partes` = {átomo: (conteo de cada parte)}. Incluye los agregados sin
    respuestas válidas (n = 0) y los que nunca se publican (R).
    """
    largo = _largo(partes)
    sup = set(jer.nunca)
    for g, atomos in jer.grupos.items():
        if not partes_publicables(_suma(atomos, partes, largo), minimo):
            sup.add(g)

    # 1. márgenes, hasta un punto fijo
    cambio = True
    while cambio:
        cambio = False
        for padre, hijos in jer.relaciones:
            if padre in sup:
                continue
            cubiertos = frozenset().union(*[jer.grupos[h] for h in hijos if h not in sup])
            u = jer.grupos[padre] - cubiertos
            if union_segura(_suma(u, partes, largo), minimo):
                continue
            candidatos = [h for h in hijos if h not in sup and _n(jer, h, partes, largo) > 0]
            if candidatos:
                sup.add(min(candidatos, key=lambda h: (_n(jer, h, partes, largo), str(h))))
            else:
                sup.add(padre)
            cambio = True

    # 2. auditoría exacta y arreglo más barato, hasta que no quede ninguna fuga
    vivos = [a for a, p in partes.items() if sum(int(x) for x in p) > 0]
    while True:
        pub = publicados(jer, sup)
        encontradas = fugas(jer, partes, pub, minimo)
        if not encontradas:
            return sup
        s_conj = encontradas[0]
        mejor = None
        for s in sorted(s_conj):
            for b in [None] + sorted(a for a in vivos if a not in s_conj):
                quitar = {g for g in pub
                          if (s in jer.grupos[g]) != (b is not None and b in jer.grupos[g])}
                if not quitar:
                    continue
                coste = (sum(len(jer.grupos[g]) for g in quitar),
                         sum(_n(jer, g, partes, largo) for g in quitar), str(b))
                if mejor is None or coste < mejor[0]:
                    mejor = (coste, quitar)
        if mejor is None:                     # no debería pasar: se oculta todo
            sup |= pub
        else:
            sup |= mejor[1]
