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
  · Componentes de más de MAX_ENUMERAR átomos ocultos ligados no se revisan:
    se tratan como hallazgo (fallo cerrado) y `suprimir` oculta agregados hasta
    que caben. Puede ocultar más de lo estrictamente necesario.
  · Las cifras de dos columnas con bases distintas (p. ej. solapamiento frente
    al corte del SDQ) quedan fuera, como en privacidad.auditar.
"""
from __future__ import annotations

from dataclasses import dataclass, field

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
    for m in range(1, 1 << c):
        yield [i for i in range(c) if m >> i & 1]


def fugas(jer: Jerarquia, partes: dict, pub, minimo: int = MIN_CASOS) -> list[frozenset]:
    """Conjuntos de átomos deducibles de los agregados `pub` que incumplen la regla.

    Lista vacía = nada de lo publicado deja, sumando o restando, un conjunto
    de respuestas con menos de `minimo` casos (o menos de `minimo` no casos).
    Falla cerrado: un componente de más de MAX_ENUMERAR átomos ligados, que no
    se revisa entero, cuenta como hallazgo (el componente completo).
    """
    pequenas, grandes = _fugas(jer, partes, pub, minimo)
    return pequenas + grandes


def _fugas(jer: Jerarquia, partes: dict, pub, minimo: int = MIN_CASOS
           ) -> tuple[list[frozenset], list[frozenset]]:
    """(conjuntos que incumplen, componentes demasiado grandes para revisar)."""
    largo = _largo(partes)
    vivos = sorted(a for a, p in partes.items() if sum(int(x) for x in p) > 0)
    if not vivos:
        return [], []
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
        return [], []
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
    grandes: list[frozenset] = []
    if z.shape[0]:
        for comp in _componentes(z):
            if len(comp) > MAX_ENUMERAR:
                grandes.append(frozenset(vivos[j] for j in comp))
                continue
            for sub in _subconjuntos(len(comp)):
                idx = [comp[i] for i in sub]
                if np.any(np.abs(z[:, idx].sum(axis=1)) > 1e-7):
                    continue
                if not union_segura(P[idx].sum(axis=0), minimo):
                    salida.append(frozenset(vivos[j] for j in idx))
    salida.sort(key=lambda s: (int(_suma(s, partes, largo).sum()), sorted(s)))
    return salida, grandes


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
        encontradas, grandes = _fugas(jer, partes, pub, minimo)
        if grandes:
            # Falla cerrado: se oculta el agregado publicado más pequeño que
            # toca el componente, hasta que se pueda revisar entero (o no quede
            # nada publicado que lo toque).
            tocan = [g for g in pub if jer.grupos[g] & grandes[0]]
            if not tocan:                 # no debería pasar: se oculta todo
                sup |= pub
                continue
            sup.add(min(tocan, key=lambda g: (_n(jer, g, partes, largo), str(g))))
            continue
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


# ── medias de ítems que tienen un corte publicado ─────────────────────────
# {ítem: (mínimo, máximo, último valor que cuenta como caso)}. PSSM7 («hay al
# menos un adulto con quien puedo hablar», 1 a 5, sin invertir) tiene el corte
# «sin adulto de confianza» = ≤ 2 en scoring.sobre_cortes. La media de un
# ítem acota sus casos: con Σ = M·n, k ≤ (máx·n − Σ)/(máx − c) y
# n − k ≤ (Σ − mín·n)/(c + 1 − mín).
ITEMS_CON_CORTE = {"PSSM7": (1, 5, 2)}
REDONDEO_MEDIA = 0.005           # stats.medias_items redondea la media a 2 decimales


def cotas_item(item: str, media, n, holgura: float = 0.0) -> tuple[int, int] | None:
    """(máximo de casos, máximo de no casos) que deja ver la media; None si no aplica.

    `holgura` desplaza Σ en el sentido que estrecha cada cota (conservador
    frente al redondeo de la media publicada).
    """
    if item not in ITEMS_CON_CORTE or media is None or pd.isna(media) or not n:
        return None
    lo, hi, c = ITEMS_CON_CORTE[item]
    n = int(n)
    k_max = np.floor(((hi * n) - (float(media) + holgura) * n) / (hi - c) + 1e-9)
    nk_max = np.floor(((float(media) - holgura) * n - lo * n) / (c + 1 - lo) + 1e-9)
    return int(min(k_max, n)), int(min(nk_max, n))


def item_delata(item: str, media, n, minimo: int = MIN_CASOS,
                holgura: float = REDONDEO_MEDIA) -> bool:
    """True si la media publicada obliga a que haya < minimo casos o no casos."""
    cotas = cotas_item(item, media, n, holgura)
    return cotas is not None and min(cotas) < minimo


def _omitir_items(obj, minimo: int = MIN_CASOS) -> int:
    """Quita las medias de ítems con corte cuyo corte no se publica o que lo acotan."""
    t = getattr(obj, "items_pssm", None)
    if t is None or not isinstance(t, pd.DataFrame) or t.empty or "item" not in t.columns:
        return 0
    quitar = [i for i, f in t.iterrows()
              if str(f["item"]) in ITEMS_CON_CORTE
              and (not _publicado(obj, str(f["item"]))
                   or item_delata(str(f["item"]), f["M"], f["n"], minimo))]
    if quitar:
        obj.items_pssm = t.drop(index=quitar).reset_index(drop=True)
    return len(quitar)


# ── solapamiento SDQ × ARI (solo del nivel) ───────────────────────────────
CLAVES_SOLAPAMIENTO_MISMA_BASE = ("pct_sdq_alto", "pct_ari_alto", "pct_ari_alto_si_sdq_alto",
                                  "pct_ari_alto_si_sdq_promedio")


def partes_solapamiento(d: pd.DataFrame) -> tuple[list[int] | None, bool]:
    """(casillas de la tabla 3×2, ¿bases iguales?) del solapamiento SDQ × ARI.

    Filas: banda 0, banda 1 y bandas 2-3 del SDQ total; columnas: ARI > 2 o no,
    sobre quienes respondieron los dos. Las bases son iguales si esa base
    coincide con la del corte del SDQ y con la del ARI. (None, False) si faltan
    las columnas.
    """
    if "banda_SDQ_Total" not in d.columns or "ARI_Total" not in d.columns:
        return None, False
    banda, ari = d["banda_SDQ_Total"], d["ARI_Total"]
    base = banda.notna() & ari.notna()
    if not base.any():
        return None, False
    alto = ari > 2
    casillas = [int((filas & base & a).sum())
                for filas in (banda == 0, banda == 1, banda >= 2) for a in (alto, ~alto)]
    sdq = d["SDQ_Total"].notna() if "SDQ_Total" in d.columns else banda.notna()
    n = int(base.sum())
    return casillas, n == int(sdq.sum()) == int(ari.notna().sum())


def auditar_solapamiento(sol: dict, d: pd.DataFrame, minimo: int = MIN_CASOS) -> list[str]:
    """Problemas del solapamiento publicado, recalculado sobre las filas del nivel."""
    if not sol or not any(k != "n" for k in sol):
        return []
    casillas, bases_iguales = partes_solapamiento(d)
    if casillas is None or not partes_publicables(casillas, minimo):
        return [f"solapamiento: la tabla SDQ × ARI tiene una casilla con menos de "
                f"{minimo} respuestas"]
    if not bases_iguales and any(sol.get(k) is not None
                                 for k in CLAVES_SOLAPAMIENTO_MISMA_BASE):
        return ["solapamiento: publica porcentajes por indicador o condicionados con "
                "una base distinta de la de los cortes"]
    return []


# ══ Aplicación al objeto Analisis ═════════════════════════════════════════
COLUMNAS_CORTE_NULAS = ("pct", "ic_inf", "ic_sup", "casos")
COLUMNAS_BANDA_NULAS = tuple(f"{p}_b{i}" for p in ("pct", "n") for i in range(4)) \
    + ("pct_alto_o_muy_alto",)
CAMPOS_CONTRASTE_NULOS = ("pct_tercil_bajo", "pct_tercil_alto", "ic_bajo", "ic_alto",
                          "razon", "k_bajo", "k_alto")


def _vacia(t) -> bool:
    return t is None or not isinstance(t, pd.DataFrame) or t.empty or "clave" not in t.columns


def partes_por_familia(cortes, bandas) -> dict[str, tuple]:
    """{clave: partes} de un grupo, desde sus tablas agregadas (con conteos).

    Bandas del SDQ: (b0, b1, b2, b3); su corte «alto o muy alto» es b2 + b3 y
    va con ellas. Cortes de otra escala: (n − k) y k; con varios umbrales
    anidados de la misma escala, (n − k₁, k₁ − k₂, …, k_último).
    """
    familias: dict[str, tuple] = {}
    if not _vacia(bandas):
        for _, f in bandas.iterrows():
            familias[str(f["clave"])] = tuple(int(f[f"n_b{i}"]) for i in range(4))
    if not _vacia(cortes):
        for clave, filas in cortes.groupby("clave", sort=False):
            if str(clave) in familias:
                continue
            n = int(filas["n"].iloc[0])
            ks = sorted((int(k) for k in filas["casos"]), reverse=True)
            partes = [n - ks[0]] + [ks[i] - ks[i + 1] for i in range(len(ks) - 1)] + [ks[-1]]
            if min(partes) < 0:
                raise ValueError(f"Los cortes de {clave} no están anidados")
            familias[str(clave)] = tuple(partes)
    return familias


def _anular(obj, clave: str) -> int:
    """Deja en blanco las proporciones de `clave` en las tablas de `obj`. Filas tocadas."""
    tocadas = 0
    for nombre, columnas in (("cortes", COLUMNAS_CORTE_NULAS), ("bandas", COLUMNAS_BANDA_NULAS)):
        t = getattr(obj, nombre, None)
        if _vacia(t):
            continue
        filas = t["clave"].astype(str) == clave
        if not filas.any():
            continue
        for c in columnas:
            if c in t.columns:
                t[c] = t[c].astype(float)
                t.loc[filas, c] = np.nan
        tocadas += int(filas.sum())
    return tocadas


def suprimir_contrastes(lista: list, minimo: int = MIN_CASOS) -> int:
    """Marca `suprimido` y vacía las cifras de los contrastes que no cumplen. Cuántos."""
    cuantos = 0
    for c in lista or []:
        if c.get("suprimido") or contraste_publicable(c, minimo):
            continue
        for campo in CAMPOS_CONTRASTE_NULOS:
            c[campo] = None
        c["suprimido"] = True
        cuantos += 1
    return cuantos


def _objetos(a) -> dict:
    """{nombre de agregado: objeto con tablas} del nivel y sus subgrupos."""
    sub = getattr(a, "subgrupos", None) or {}
    objs = {NIVEL: a}
    for k, s in (sub.get(AGRUPACION_CRUCE) or {}).items():
        objs[CELDA(k)] = s
    for c, s in (sub.get("Colegio") or {}).items():
        objs[COLEGIO(c)] = s
    for g, s in (sub.get("Grado") or {}).items():
        objs[GRADO(g)] = s
    return objs


def aplicar(a, minimo: int = MIN_CASOS) -> dict:
    """Suprime, en el sitio, las proporciones de `a` y de sus subgrupos que delatan.

    Trabaja solo con tablas agregadas: las partes de cada átomo salen de las
    tablas de su celda o colegio, y las del resto R, del nivel menos todos
    ellos. Devuelve {(tipo, agrupación): filas suprimidas}.
    """
    sub = getattr(a, "subgrupos", None) or {}
    celdas = list(sub.get(AGRUPACION_CRUCE) or {})
    jer = jerarquia(celdas, list(sub.get("Colegio") or {}), list(sub.get("Grado") or {}),
                    con_resto=True)
    objs = _objetos(a)
    fam = {g: partes_por_familia(getattr(o, "cortes", None), getattr(o, "bandas", None))
           for g, o in objs.items()}
    con_celdas = {k.split(SEP, 1)[0] for k in celdas}
    atomos = {atomo_celda(k): CELDA(k) for k in celdas}
    atomos.update({atomo_colegio(c): COLEGIO(c) for c in (sub.get("Colegio") or {})
                   if str(c) not in con_celdas})
    resumen: dict = {}
    for clave in sorted({c for f in fam.values() for c in f}):
        largo = max(len(f[clave]) for f in fam.values() if clave in f)
        cero = np.zeros(largo, dtype=np.int64)
        partes = {a_: np.asarray(fam[g].get(clave, cero)) for a_, g in atomos.items()}
        resto = np.asarray(fam[NIVEL].get(clave, cero)) - sum(partes.values(), cero)
        if (resto < 0).any():
            raise ValueError(f"{clave}: los subgrupos suman más que el nivel")
        partes[RESTO] = resto
        for g in suprimir(jer, {k: tuple(v) for k, v in partes.items()}, minimo):
            if g in objs:
                tocadas = _anular(objs[g], clave)
                if tocadas:
                    clave_res = (g[0], clave)
                    resumen[clave_res] = resumen.get(clave_res, 0) + 1
    for g, o in objs.items():
        n = suprimir_contrastes(getattr(o, "contrastes", None), minimo)
        if n:
            resumen[(g[0], "contraste")] = resumen.get((g[0], "contraste"), 0) + n
        n = _omitir_items(o, minimo)
        if n:
            resumen[(g[0], "item")] = resumen.get((g[0], "item"), 0) + n
    return resumen


# ══ Auditoría independiente, desde los datos enmascarados ═════════════════
def _publicado(obj, clave: str) -> bool | None:
    """True/False si la familia está publicada en `obj`; None si no aparece."""
    estados = []
    for nombre, col in (("cortes", "pct"), ("bandas", "pct_b0")):
        t = getattr(obj, nombre, None)
        if _vacia(t) or col not in t.columns:
            continue
        filas = t[t["clave"].astype(str) == clave]
        estados += [not pd.isna(v) for v in filas[col]]
    if not estados:
        return None
    if len(set(estados)) > 1:
        return True          # parcialmente publicada: se audita como publicada
    return estados[0]


def auditar(a, minimo: int = MIN_CASOS) -> list[str]:
    """Proporciones publicadas que delatan, recalculadas desde `a.datos` y `a.base`.

    No usa los conteos de las tablas del pipeline: recalcula las partes de cada
    átomo de la base con scoring y comprueba (1) que cada proporción publicada
    cumple la regla, (2) que ninguna suma o resta de lo publicado deja un
    conjunto que la incumpla (`fugas`) y (3) que cada contraste publicado cumple
    en sus dos terciles. Los mensajes nombran grupo e indicador, nunca cifras.
    """
    from src.estudiantes import privacidad, scoring, stats
    base = getattr(a, "base", None)
    d = getattr(a, "datos", None)
    if base is None or d is None or d.empty:
        return []
    jer = jerarquia(list(base.celdas), list(base.colegios), list(base.grados),
                    con_resto=base.incluye_resto)
    con_celdas = {k.split(SEP, 1)[0] for k in base.celdas}
    indices = {atomo_celda(k): idx for k, idx in base.celdas.items()}
    indices.update({atomo_colegio(c): idx for c, idx in base.colegios.items()
                    if c not in con_celdas})
    if base.incluye_resto:
        indices[RESTO] = base.nivel.difference(privacidad.union(base.colegios.values()))
    fam = {}
    for at, idx in indices.items():
        sub = d.loc[d.index.intersection(idx)]
        fam[at] = (partes_por_familia(scoring.sobre_cortes(sub),
                                      scoring.distribucion_bandas(sub, "self"))
                   if len(sub) else {})
    objs = _objetos(a)
    problemas: list[str] = []
    claves = sorted({c for f in fam.values() for c in f})
    for clave in claves:
        largo = max(len(f[clave]) for f in fam.values() if clave in f)
        partes = {at: f.get(clave, (0,) * largo) for at, f in fam.items()}
        pub = {g for g, o in objs.items() if _publicado(o, clave)}
        for g in sorted(pub, key=str):
            if g not in jer.grupos:
                problemas.append(f"{clave}: {g[0]} {g[1]} publicado fuera de la base")
                continue
            if not partes_publicables(_suma(jer.grupos[g], partes, largo), minimo):
                problemas.append(f"{clave}: {g[0]} {g[1] or ''} publica una proporción "
                                 f"con menos de {minimo} casos o no casos")
        for s in fugas(jer, partes, pub & set(jer.grupos), minimo):
            problemas.append(f"{clave}: una resta entre cifras publicadas deja un conjunto "
                             f"de {len(s)} grupo(s) con menos de {minimo} casos o no casos")
    problemas += auditar_solapamiento(getattr(a, "solapamiento", None) or {},
                                      d.loc[d.index.intersection(base.nivel)], minimo)
    for g, o in objs.items():
        if g == NIVEL:
            filas = d.loc[d.index.intersection(base.nivel)]
        elif g[0] == AGRUPACION_CRUCE:
            filas = privacidad.filas(d, base, *g[1].split(SEP, 1))
        elif g[0] == "Colegio":
            filas = privacidad.filas(d, base, colegio=g[1])
        else:
            filas = privacidad.filas(d, base, grado=g[1])
        items = getattr(o, "items_pssm", None)
        if isinstance(items, pd.DataFrame) and not items.empty and "item" in items.columns:
            for _, f in items.iterrows():
                item = str(f["item"])
                if item not in ITEMS_CON_CORTE or pd.isna(f["M"]):
                    continue
                if not _publicado(o, item):
                    problemas.append(f"{item}: {g[0]} {g[1] or ''} publica la media del "
                                     "ítem con su corte suprimido")
                    continue
                v = filas[item].dropna() if item in filas.columns else pd.Series(dtype=float)
                if len(v) and item_delata(item, v.mean(), len(v), minimo, holgura=0.0):
                    problemas.append(f"{item}: {g[0]} {g[1] or ''} publica una media que "
                                     f"acota los casos por debajo de {minimo}")
        for c in getattr(o, "contrastes", None) or []:
            if c.get("suprimido"):
                continue
            r = stats.contraste_protector(filas, c["resultado"], c["protector"])
            if r and not contraste_publicable(r, minimo):
                problemas.append(f"contraste {c['resultado']}–{c['protector']}: {g[0]} "
                                 f"{g[1] or ''} compara un tercil con menos de {minimo} "
                                 "casos o no casos")
    return problemas
