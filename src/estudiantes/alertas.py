"""
Alertas de grupo de Estudiantes 360 — funciones puras (spec 6-oct-2026, §5.4).

Por estudiante se calcula una señal (1, 0 o faltante) con las reglas de
`alertas_catalogo`. Lo que sale de aquí es siempre por grupo de la base
publicable (privacidad.base_publicable) y nunca lleva el número de casos.

CÓMO SE PROTEGEN LAS CIFRAS
Cada alerta es una proporción binaria más, igual que un corte:
  · La señal es una columna de los datos (`ALERTA_*`): pasa por el todo o nada
    de la fase 1, así que la auditoría de restas de n ya la cubre.
  · `cortes_alerta` arma, para el nivel y para cada subgrupo (colegio, grado,
    celda), una tabla con la forma de `scoring.sobre_cortes`. `supresion.aplicar`
    la trata como una familia más (celdas, colegios, grados, nivel y el resto R):
    supresión primaria 3 ≤ casos ≤ n − 3, complementaria y auditoría exacta de
    sumas y restas. Los grados y las celdas llevan porcentaje cuando la
    supresión lo permite.
  · La desesperanza (regla estricta) implica RCADS 18 ≥ «Con frecuencia», que es
    el corte de la tarjeta de muerte: es un corte ANIDADO en esa familia
    (`ANIDADA`). La supresión la reparte en (n − k₁₈, k₁₈ − k, k) y nunca la
    publica donde el corte del ítem 18 está suprimido.

ESTADO («Prioridad» / «Para tener presente»)
Solo para grupos con porcentaje publicado, y solo con cifras publicadas
(`estado`): el % y el n del grupo y del nivel. El resto del nivel (nivel −
grupo) se deduce de esas cifras, así que el estado no añade información. Si el
porcentaje está suprimido, el estado es neutro («sin estado»).

LO QUE NO SE PUBLICA
La sensibilidad (umbrales 2/3/4 y regla amplia) y la distribución de los ítems
son solo para la vista local de investigadores: no van a Supabase ni al ZIP.
Aun así cumplen la regla y no deshacen la supresión de lo publicado: la
sensibilidad solo sale si la cifra vigente del nivel quedó publicada y su
reparto anidado (con el corte del ítem 18 en la desesperanza) pasa entero
`supresion.partes_publicables` (ver `sensibilidad`).

Faltantes: el malestar exige los 6 ítems respondidos; la desesperanza, los de
su regla (16 y 18 la estricta; 1, 4, 16 y 18 la amplia).

Los ítems se leen tal como los codifica `ingest` desde el texto crudo del
formulario (No es cierto = 0 … Muy cierto = 2; Nunca = 0 … Siempre = 3).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import privacidad, supresion
from src.estudiantes.stats import wilson

TOTAL = "total"
TODOS = privacidad.TODOS
CRUCE = privacidad.AGRUPACION_CRUCE
AGRUPACIONES = ("Colegio", "Grado", CRUCE)

COLUMNAS = {ac.MALESTAR: "ALERTA_malestar", ac.DESESPERANZA: "ALERTA_desesperanza"}
COLUMNA_AMPLIA = "ALERTA_desesperanza_amplia"

# Alerta → familia de `scoring.sobre_cortes` en la que está anidada (alerta ⊆ corte).
ANIDADA = {ac.DESESPERANZA: f"RCADS{ac.ITEM_MUERTE}"}


def columna_malestar(umbral: int) -> str:
    return (COLUMNAS[ac.MALESTAR] if umbral == ac.UMBRAL_MALESTAR
            else f"ALERTA_malestar_{umbral}")


# variante → (alerta, columna, etiqueta, ¿es la vigente?)
VARIANTES: dict[str, tuple[str, str, str, bool]] = {
    **{f"malestar_{u}": (ac.MALESTAR, columna_malestar(u),
                         f"«Muy cierto» en {u} o más de 6", u == ac.UMBRAL_MALESTAR)
       for u in ac.UMBRALES_SENSIBILIDAD},
    "desesperanza_estricta": (ac.DESESPERANZA, COLUMNAS[ac.DESESPERANZA],
                              "Regla estricta", True),
    "desesperanza_amplia": (ac.DESESPERANZA, COLUMNA_AMPLIA, "Regla amplia", False),
}

# Tabla por grupo de cada objeto (nivel y subgrupos), con la forma de sobre_cortes.
# `casos` es interno: lo usa la supresión y nunca se publica.
COLUMNAS_CORTES = ["clave", "indicador", "anidada_en", "n", "casos", "pct", "ic_inf",
                   "ic_sup"]
# Tabla plana que leen las vistas y que se publica. Sin casos, nunca.
COLUMNAS_TABLA = ["alerta", "agrupacion", "grupo", "n", "pct", "ic_inf", "ic_sup", "estado"]
COLUMNAS_SENSIBILIDAD = ["alerta", "variante", "etiqueta", "vigente", "n", "pct",
                         "ic_inf", "ic_sup"]
COLUMNAS_ITEMS = ["alerta", "item", "enunciado", "respuesta", "n", "pct"]

ETIQUETAS_RESPUESTA = {
    "SDQ": ("No es cierto", "Algo cierto", "Muy cierto"),
    "RCADS": ("Nunca", "Algunas veces", "Con frecuencia", "Siempre"),
}


# ── Señal por estudiante ─────────────────────────────────────────────────────
def _columnas(escala: str, items) -> list[str]:
    return [f"{escala}{i}" for i in items]


def senal_malestar(d: pd.DataFrame, umbral: int = ac.UMBRAL_MALESTAR) -> pd.Series:
    """1.0 si «Muy cierto» en ≥ `umbral` de los 6 ítems; 0.0 si no; NaN si falta alguno."""
    cols = _columnas("SDQ", ac.ALERTAS[ac.MALESTAR].items)
    if not set(cols) <= set(d.columns):
        return pd.Series(np.nan, index=d.index, dtype=float)
    X = d[cols]
    completos = X.notna().all(axis=1)
    return ((X == ac.MUY_CIERTO).sum(axis=1) >= umbral).astype(float).where(completos)


def senal_desesperanza(d: pd.DataFrame, amplia: bool = False) -> pd.Series:
    """Regla estricta (vigente) o amplia (sensibilidad); NaN si falta un ítem de la regla."""
    cols = _columnas("RCADS", ac.ITEMS_REGLA_AMPLIA if amplia else ac.ITEMS_REGLA_ESTRICTA)
    if not set(cols) <= set(d.columns):
        return pd.Series(np.nan, index=d.index, dtype=float)
    completos = d[cols].notna().all(axis=1)
    muerte = d[f"RCADS{ac.ITEM_MUERTE}"]
    valia = d[f"RCADS{ac.ITEM_VALIA}"]
    if amplia:
        otros = pd.concat([d[f"RCADS{i}"] >= ac.CON_FRECUENCIA for i in ac.ITEMS_AMPLIA],
                          axis=1).any(axis=1)
        si = (muerte >= ac.CON_FRECUENCIA) | ((valia >= ac.CON_FRECUENCIA) & otros)
    else:
        si = (muerte == ac.SIEMPRE) | ((muerte >= ac.CON_FRECUENCIA)
                                       & (valia >= ac.CON_FRECUENCIA))
    return si.astype(float).where(completos)


def marcar(d: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Copia de `d` con una columna por señal y variante (1 / 0 / NaN). No toca nada más.

    Estas columnas son individuales: viven solo en `Analisis.datos`, que nunca
    se publica ni se exporta.
    """
    nuevas: dict[str, pd.Series] = {}
    malestar = ac.ALERTAS[ac.MALESTAR]
    if nivel in malestar.niveles and set(_columnas("SDQ", malestar.items)) <= set(d.columns):
        for u in ac.UMBRALES_SENSIBILIDAD:
            nuevas[columna_malestar(u)] = senal_malestar(d, u)
    if nivel in ac.ALERTAS[ac.DESESPERANZA].niveles:
        if set(_columnas("RCADS", ac.ITEMS_REGLA_ESTRICTA)) <= set(d.columns):
            nuevas[COLUMNAS[ac.DESESPERANZA]] = senal_desesperanza(d)
        if set(_columnas("RCADS", ac.ITEMS_REGLA_AMPLIA)) <= set(d.columns):
            nuevas[COLUMNA_AMPLIA] = senal_desesperanza(d, amplia=True)
    base = d.drop(columns=[c for c in nuevas if c in d.columns])
    if not nuevas:
        return base.copy()
    return pd.concat([base, pd.DataFrame(nuevas, index=d.index)], axis=1)


def claves_del_nivel(d: pd.DataFrame, nivel: str) -> list[str]:
    """Alertas que aplican al nivel y tienen alguna señal válida en `d`."""
    return [k for k, x in ac.ALERTAS.items()
            if nivel in x.niveles and COLUMNAS[k] in d.columns and d[COLUMNAS[k]].notna().any()]


# ── Ítems con «*» en el formulario ───────────────────────────────────────────
def items_marcados_por_escala(columnas) -> dict[str, set[int]]:
    """{escala: números de ítem} de los encabezados con «*» (spec §5.4).

    Localiza cada bloque igual que `ingest` (por el prefijo normalizado), numera
    dentro del bloque y reconoce el «*» con `ingest.tiene_asterisco`, la misma
    regla que llena `InformeIngesta.items_marcados`.
    """
    from src.estudiantes.ingest import _PREFIJOS, _bloque, norm_txt, tiene_asterisco
    crudas = list(columnas)
    normalizadas = [norm_txt(c) for c in crudas]
    salida: dict[str, set[int]] = {}
    for escala, prefijo in _PREFIJOS.items():
        indices = _bloque(normalizadas, prefijo)
        marcados = {i for i, col in enumerate(indices, start=1) if tiene_asterisco(crudas[col])}
        if marcados:
            salida[escala] = marcados
    return salida


# ── Tabla por grupo de cada objeto (entra en la supresión) ──────────────────
def cortes_alerta(d: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Prevalencia de cada alerta en las filas `d`, con IC de Wilson.

    Misma forma que `scoring.sobre_cortes`; la supresión deja en blanco pct, IC
    y casos donde la cifra delataría. `casos` no sale nunca de `Analisis`.
    """
    filas = []
    for clave in claves_del_nivel(d, nivel):
        v = d[COLUMNAS[clave]].dropna()
        k, n = int(v.sum()), int(len(v))
        pct, ic_inf, ic_sup = wilson(k, n)
        filas.append(dict(clave=clave, indicador=ac.ALERTAS[clave].nombre,
                          anidada_en=ANIDADA.get(clave, ""), n=n, casos=k,
                          pct=pct, ic_inf=ic_inf, ic_sup=ic_sup))
    return pd.DataFrame(filas, columns=COLUMNAS_CORTES)


# ── Estado, solo con cifras publicadas ───────────────────────────────────────
def _vacio(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v)) or pd.isna(v)


def estado(pct, n, pct_nivel, n_nivel) -> str:
    """Estado de un grupo a partir de cifras PUBLICADAS: (%, n) del grupo y del nivel.

    · Sin porcentaje del grupo: «sin estado» (cifras pequeñas).
    · Sin porcentaje del nivel, o con un resto (nivel − grupo) de menos de
      MIN_GROUP_N respuestas: «referencia» (se lee «Para tener presente», sin
      comparación).
    · Si no, «Prioridad» cuando el límite inferior del IC de Wilson del grupo
      queda por encima del límite superior del resto, que se deduce de esas
      mismas cifras; si no, «Para tener presente».
    """
    if _vacio(pct) or _vacio(n):
        return ac.SIN_ESTADO
    if _vacio(pct_nivel) or _vacio(n_nivel):
        return ac.REFERENCIA
    n, n_nivel = int(n), int(n_nivel)
    n_resto = n_nivel - n
    if n <= 0 or n_resto < cat.MIN_GROUP_N:
        return ac.REFERENCIA
    k = float(pct) * n / 100
    k_resto = min(max(float(pct_nivel) * n_nivel / 100 - k, 0.0), float(n_resto))
    _, inferior, _ = wilson(k, n)
    _, _, superior_resto = wilson(k_resto, n_resto)
    return ac.PRIORIDAD if inferior > superior_resto else ac.PRESENTE


def estado_total(pct) -> str:
    """El nivel es la referencia de las comparaciones."""
    return ac.SIN_ESTADO if _vacio(pct) else ac.REFERENCIA


# ── Tabla plana: lo que leen las vistas y lo que se publica ─────────────────
def _orden_grupo(agrupacion: str, grupo: str, nivel: str) -> tuple:
    grados = cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.ORDEN_GRADOS_PRI

    def pos(g):
        return (grados.index(g) if g in grados else 99, str(g))
    if agrupacion == TOTAL:
        return (0, (0, ""), (0, ""))
    if agrupacion == "Colegio":
        return (1, (0, str(grupo)), (0, ""))
    if agrupacion == "Grado":
        return (2, pos(grupo), (0, ""))
    colegio, grado = privacidad.partir_celda(grupo)
    return (3, (0, colegio), pos(grado))


def ordenar(tabla: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """Orden canónico: alerta del catálogo, nivel, colegios, grados y celdas."""
    if tabla is None or len(tabla) == 0:
        return pd.DataFrame(columns=COLUMNAS_TABLA)
    orden_alerta = {k: i for i, k in enumerate(ac.ALERTAS)}
    claves = [(orden_alerta.get(a, 99), _orden_grupo(ag, str(g), nivel))
              for a, ag, g in zip(tabla["alerta"], tabla["agrupacion"], tabla["grupo"])]
    posiciones = sorted(range(len(tabla)), key=lambda i: claves[i])
    return tabla.iloc[posiciones].reset_index(drop=True)[COLUMNAS_TABLA]


def _num(v):
    return None if _vacio(v) else float(v)


def tabla(a) -> pd.DataFrame:
    """Una fila por alerta y grupo, desde las tablas YA suprimidas. Sin casos, nunca.

    Se llama después de `supresion.aplicar`. El estado sale de `estado`, que
    solo mira cifras publicadas.
    """
    propia = getattr(a, "cortes_alerta", None)
    if not isinstance(propia, pd.DataFrame) or propia.empty:
        return pd.DataFrame(columns=COLUMNAS_TABLA)
    nivel = getattr(a, "nivel", None)
    ref: dict[str, tuple] = {}
    filas: list[dict] = []
    for f in propia.to_dict("records"):
        if int(f["n"]) < cat.MIN_GROUP_N:
            continue
        ref[f["clave"]] = (_num(f["pct"]), int(f["n"]))
        filas.append(dict(alerta=f["clave"], agrupacion=TOTAL, grupo=TODOS, n=int(f["n"]),
                          pct=_num(f["pct"]), ic_inf=_num(f["ic_inf"]),
                          ic_sup=_num(f["ic_sup"]), estado=estado_total(f["pct"])))
    for agrupacion in AGRUPACIONES:
        for grupo, s in ((getattr(a, "subgrupos", None) or {}).get(agrupacion) or {}).items():
            t = getattr(s, "cortes_alerta", None)
            if not isinstance(t, pd.DataFrame) or t.empty:
                continue
            for f in t.to_dict("records"):
                if int(f["n"]) < cat.MIN_GROUP_N or f["clave"] not in ref:
                    continue
                pct_nivel, n_nivel = ref[f["clave"]]
                filas.append(dict(alerta=f["clave"], agrupacion=agrupacion, grupo=str(grupo),
                                  n=int(f["n"]), pct=_num(f["pct"]),
                                  ic_inf=_num(f["ic_inf"]), ic_sup=_num(f["ic_sup"]),
                                  estado=estado(f["pct"], f["n"], pct_nivel, n_nivel)))
    return ordenar(pd.DataFrame(filas, columns=COLUMNAS_TABLA), nivel)


# ── Sensibilidad y distribución de ítems (solo el nivel, solo local) ────────
def _publicada(publicadas, alerta: str) -> bool:
    """¿La cifra del nivel de `alerta` quedó publicada tras `supresion.aplicar`?

    `publicadas` es `Analisis.cortes_alerta` del nivel, ya suprimida. Sin esa
    tabla no se sabe: se responde que no (lo prudente para la sensibilidad).
    """
    if not isinstance(publicadas, pd.DataFrame) or publicadas.empty:
        return False
    if not {"clave", "pct"} <= set(publicadas.columns):
        return False
    filas = publicadas[publicadas["clave"] == alerta]
    return bool(len(filas)) and not any(_vacio(v) for v in filas["pct"])


def _cadena(n: int, ks) -> list[int]:
    """Reparto anidado (n − k₁, k₁ − k₂, …, k_último) con ks de mayor a menor."""
    ks = list(ks)
    return [n - ks[0]] + [ks[i] - ks[i + 1] for i in range(len(ks) - 1)] + [ks[-1]]


def sensibilidad(dn: pd.DataFrame, nivel: str, publicadas=None) -> pd.DataFrame:
    """Prevalencia del nivel con cada variante de umbral o de regla. Solo local.

    `publicadas` es la tabla `cortes_alerta` del nivel YA suprimida. Las
    variantes de una alerta solo llevan cifras cuando:
      · la cifra vigente de esa alerta en el nivel quedó publicada (si no, las
        variantes la delatarían), y
      · el reparto anidado sobre la base publicada de la alerta cumple
        `supresion.partes_publicables` en todas sus partes:
          malestar      n − k₂, k₂ − k₃, k₃ − k₄, k₄ (filas con los 6 ítems);
          desesperanza  n − k_amplia, k_amplia − k₁₈, k₁₈ − k_estricta,
                        k_estricta (filas con los ítems 16 y 18), donde k₁₈
                        es RCADS 18 ≥ «Con frecuencia», el corte publicado
                        de la tarjeta de muerte. Una fila sin el ítem 1 o el 4
                        no cuenta como amplia por la vía de la valía (sí por
                        el ítem 18, así amplia ⊇ k₁₈ ⊇ estricta).
    Si no, las filas salen con las cifras en blanco.
    """
    if dn is None or dn.empty:
        return pd.DataFrame(columns=COLUMNAS_SENSIBILIDAD)
    filas: list[dict] = []
    for alerta in claves_del_nivel(dn, nivel):
        base = dn[dn[COLUMNAS[alerta]].notna()]
        n = len(base)
        if n < cat.MIN_GROUP_N:
            continue
        variantes = [(v, col, etq, vig) for v, (a, col, etq, vig) in VARIANTES.items()
                     if a == alerta and col in dn.columns]
        ks = {v: int((base[col] == 1).sum()) for v, col, _, _ in variantes}
        if alerta == ac.DESESPERANZA:
            muerte = f"RCADS{ac.ITEM_MUERTE}"
            k18 = base[muerte] >= ac.CON_FRECUENCIA
            amplia = (base[COLUMNA_AMPLIA] == 1) if COLUMNA_AMPLIA in base else False
            if "desesperanza_amplia" in ks:
                ks["desesperanza_amplia"] = int((k18 | amplia).sum())
            cadena = sorted([*ks.values(), int(k18.sum())], reverse=True)
        else:
            cadena = sorted(ks.values(), reverse=True)
        partes = _cadena(n, cadena)
        ver = (_publicada(publicadas, alerta) and min(partes) >= 0
               and supresion.partes_publicables(partes))
        for v, _, etiqueta, vig in variantes:
            pct, ic_inf, ic_sup = wilson(ks[v], n) if ver else (None, None, None)
            filas.append(dict(alerta=alerta, variante=v, etiqueta=etiqueta, vigente=vig,
                              n=n, pct=pct, ic_inf=ic_inf, ic_sup=ic_sup))
    return pd.DataFrame(filas, columns=COLUMNAS_SENSIBILIDAD)


def distribucion_items(dn: pd.DataFrame, nivel: str) -> pd.DataFrame:
    """% de cada respuesta en los ítems de las alertas, en el nivel. Solo local.

    El reparto de respuestas de un ítem se muestra entero o no se muestra
    (`supresion.partes_publicables`): con una respuesta oculta, se deduciría
    restando las demás de n.
    """
    if dn is None or dn.empty:
        return pd.DataFrame(columns=COLUMNAS_ITEMS)
    filas: list[dict] = []
    for alerta in claves_del_nivel(dn, nivel):
        a = ac.ALERTAS[alerta]
        items = a.items if alerta == ac.MALESTAR else ac.ITEMS_REGLA_AMPLIA
        etiquetas = ETIQUETAS_RESPUESTA[a.escala]
        for i in items:
            col = f"{a.escala}{i}"
            if col not in dn.columns:
                continue
            v = dn[col].dropna()
            n = len(v)
            if n < cat.MIN_GROUP_N:
                continue
            conteos = [int((v == codigo).sum()) for codigo in range(len(etiquetas))]
            ver = supresion.partes_publicables(conteos)
            for etiqueta, c in zip(etiquetas, conteos):
                filas.append(dict(alerta=alerta, item=col,
                                  enunciado=ac.ENUNCIADOS_ITEMS.get(col, col),
                                  respuesta=etiqueta, n=n,
                                  pct=round(100 * c / n, 1) if ver else None))
    return pd.DataFrame(filas, columns=COLUMNAS_ITEMS)
