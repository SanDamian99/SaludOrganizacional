"""
Orquestación de Cuidadores 360 — Observatorio 360.

`analizar(carga, ola)` produce un `AnalisisCuidadores` con dos marcos:

  · `cuidador`: una fila por cuidador distinto (lo que el adulto dice de sí
    mismo: estrés, ánimo, apoyo, barrio, castigo físico).
  · `nino`: una fila por niño distinto (lo que el cuidador dice del niño: SDQ
    y ARI de padres).

Cada marco es un `estudiantes.pipeline.Analisis` (misma clase, mismas tablas),
calculado sobre la base publicable que cuenta cuidadores distintos
(`cuidadores.privacidad`) y pasado por la supresión general de cifras pequeñas
(`estudiantes.supresion.aplicar`). Así la vista de investigadores, la de
comunidad (4b) y la publicación (4b) leen lo mismo que en estudiantes.

`ola` filtra DESPUÉS de deduplicar sobre todas las olas, así que la vista de
una ola es un subconjunto exacto de «Todas». Con una ola elegida solo hay el
total de cada marco, y cada cifra se publica solo si ni la ola ni su resta
con lo publicado en «Todas» (`ComparadorOla`) tienen menos de 10 cuidadores
distintos o menos de 3 casos o no casos. Solo existe en local: no se
publica por ola y el paquete solo se exporta con «Todas».
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd

from src.cuidadores import catalog as cat
from src.cuidadores import ingest, privacidad, scoring
from src.estudiantes import catalog as cat_est
from src.estudiantes import pipeline as pipe_est
from src.estudiantes import privacidad as priv_est
from src.estudiantes import stats, supresion

EXTENSIONES = (".xlsx", ".xls", ".csv")
CORR_CUIDADOR = ["PSS_Total", "EPDS_Total", "MSPSS_Otro", "MSPSS_Fam", "MSPSS_Amigos",
                 "BARRIO_Indice"]
SEXO_A_STATS = {"Niña": "Mujer", "Niño": "Hombre"}
CORR_NINO = ["SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro", "ARI_Total"]


@dataclass
class AnalisisCuidadores:
    """Resultado completo del módulo de cuidadores."""
    cuidador: pipe_est.Analisis
    nino: pipe_est.Analisis
    informe: ingest.InformeCuidadores
    ola: str | None = None
    olas: list = field(default_factory=list)
    # Solo locales (vista de investigadores): ítems del APQ y del estrés
    # parental, ya filtrados por la regla de cifras pequeñas.
    items_apq: pd.DataFrame = field(default_factory=pd.DataFrame)
    items_estres: pd.DataFrame = field(default_factory=pd.DataFrame)
    # Solo con una ola: {marco: distintos (todas las olas), en_base (total publicable de
    # «Todas»), fuera_de_base, otras_olas}; distintos − fuera − otras = n de la ola.
    flujo_ola: dict = field(default_factory=dict)

    @property
    def marcos(self) -> dict:
        return {cat.MARCO_CUIDADOR: self.cuidador, cat.MARCO_NINO: self.nino}


def localizar_formulario(base: str | None = None) -> str | None:
    """La exportación más reciente de «Cuidando al Cuidador» en la carpeta de datos."""
    from src.core.rutas import carpeta_datos
    from src.core.texto import norm_txt
    base = base or carpeta_datos("cuidadores")
    if not os.path.isdir(base):
        return None
    candidatos = [os.path.join(base, f) for f in os.listdir(base)
                  if f.lower().endswith(EXTENSIONES) and cat.PATRON_ARCHIVO in norm_txt(f)]
    return max(candidatos, key=os.path.getmtime) if candidatos else None


def _muestra(d: pd.DataFrame, base, suprimidos: dict, marco: str) -> dict:
    m = dict(
        n=len(d),
        n_cuidadores=int(d["ID_cuidador"].nunique()) if len(d) else 0,
        ola=d["Ola"].value_counts().sort_index().to_dict(),
        quien=d["Quien"].value_counts().to_dict(),
        colegio=privacidad.distintos_por_grupo(d, "Colegio"),
        grado=privacidad.distintos_por_grupo(d, "Grado"),
        colegio_grado={priv_est.clave_celda(c, g): int(n) for (c, g), n in
                       d.groupby(["Colegio", "Grado"])["ID_cuidador"].nunique().items()},
        base=base.resumen(),
        suprimidos=suprimidos,
        fechas=([str(d["ts"].min().date()), str(d["ts"].max().date())]
                if "ts" in d.columns and d["ts"].notna().any() else []),
    )
    if marco == cat.MARCO_NINO:
        m["sexo"] = d["Sexo"].value_counts().to_dict()
        m["edad_M"] = round(float(d["Edad"].mean()), 2) if d["Edad"].notna().any() else None
        m["grado_detalle"] = d["Grado_detalle"].value_counts().to_dict()
    return m


def _subgrupos(dm: pd.DataFrame, marco: str, claves: list[str], base) -> dict:
    """Las tablas de cada colegio, grado y celda (bandas y cortes), sobre la base."""
    salida: dict = {}
    for columna, grupos in (("Colegio", base.colegios), ("Grado", base.grados),
                            (priv_est.AGRUPACION_CRUCE, base.celdas)):
        for grupo, idx in grupos.items():
            sub = dm.loc[idx]
            s = pipe_est.Analisis(nivel=marco, n=len(sub), datos=pd.DataFrame(),
                                  escalas=list(claves),
                                  muestra=dict(n=len(sub),
                                               n_cuidadores=int(sub["ID_cuidador"].nunique())))
            if marco == cat.MARCO_NINO:
                s.bandas = scoring.bandas_nino(sub)
                s.cortes = scoring.sobre_cortes_nino(sub)
            else:
                s.cortes = scoring.sobre_cortes_cuidador(sub)
            salida.setdefault(columna, {})[str(grupo)] = s
    return salida


def _por_sexo(dn: pd.DataFrame, claves: list[str]) -> pd.DataFrame:
    """Niñas frente a niños con `stats.comparar_por_sexo`, que espera «Mujer» y «Hombre»."""
    t = stats.comparar_por_sexo(dn.assign(Sexo=dn["Sexo"].map(SEXO_A_STATS)), claves)
    if t.empty:
        return t
    t = t.rename(columns=lambda c: c.replace("_mujer", "_niña").replace("_hombre", "_niño"))
    t["escala"] = t["clave"].map(cat.label)
    return t


def partes_por_banda(d: pd.DataFrame, key: str) -> pd.Series:
    """Banda (0–3) del SDQ de padres de cada fila con dato en `key`."""
    return d[key].dropna().map(lambda x: cat_est.banda_de(x, key, "parent"))


def bandas_con_cuidadores_distintos(parte: pd.Series, ids: pd.Series,
                                    minimo: int = supresion.MIN_CASOS) -> bool:
    """Cada banda tiene ≥ `minimo` cuidadores distintos dentro y fuera (vacío = seguro)."""
    return parte.empty or all(
        ids.loc[parte.index[parte == j]].nunique() >= minimo
        and ids.loc[parte.index[parte != j]].nunique() >= minimo for j in range(4))


def regla_cuidadores_distintos(d: pd.DataFrame, base, claves,
                               minimo: int = supresion.MIN_CASOS,
                               atomos: dict | None = None) -> dict:
    """{clave: regla(conjunto de átomos) -> bool} para el marco de niños.

    En el marco de niños dos filas pueden ser hermanos: 3 niños «caso» pueden
    venir de 2 cuidadores. Un conjunto de átomos de la base (celdas, colegios
    sin celdas y resto) es seguro si sus filas con dato están vacías o si cada
    banda del SDQ de padres tiene ≥ `minimo` cuidadores distintos dentro y
    fuera de ella. `supresion.aplicar` la exige en lo publicado, en los
    márgenes y en todo lo deducible, junto con la regla por conteos.
    """
    atomos = supresion.indices_atomos(base) if atomos is None else atomos
    reglas: dict = {}
    for key in claves:
        if key not in d.columns or key not in cat_est.BANDS_PARENT:
            continue
        parte = partes_por_banda(d, key)
        ids = d.loc[parte.index, privacidad.UNIDAD]
        memo: dict = {}

        def regla(conjunto, parte=parte, ids=ids, memo=memo) -> bool:
            if conjunto not in memo:
                idx = priv_est.union(atomos[a] for a in conjunto if a in atomos)
                memo[conjunto] = bandas_con_cuidadores_distintos(
                    parte.loc[parte.index.intersection(idx)], ids, minimo)
            return memo[conjunto]
        reglas[key] = regla
    return reglas


def analizar_marco(d: pd.DataFrame, marco: str, n_boot: int = 300,
                   avisos: list | None = None, solo_nivel: bool = False) -> pipe_est.Analisis:
    """Un marco ya puntuado → `Analisis` sobre la base publicable, con supresión.

    `solo_nivel` (vista de una ola): solo el total del marco; ni colegios, ni
    grados, ni celdas, ni comparaciones entre grupos.
    """
    d = d.reset_index(drop=True)
    claves_marco = cat.CLAVES_NINO if marco == cat.MARCO_NINO else cat.CLAVES_CUIDADOR
    claves = scoring.disponibles(d, claves_marco)
    base = privacidad.base_publicable(d)
    dm, suprimidos = privacidad.aplicar_todo_o_nada(d, base)
    dn = dm.loc[base.nivel]
    a = pipe_est.Analisis(nivel=marco, n=len(d), datos=dm, escalas=claves,
                          avisos=list(avisos or []))
    a.base = base
    a.muestra = _muestra(d, base, suprimidos, marco)
    a.descriptivos = scoring.descriptivos(dn, claves)
    a.fiabilidad = scoring.fiabilidad(dn, n_boot=n_boot)
    if marco == cat.MARCO_NINO:
        a.bandas = scoring.bandas_nino(dn)
        a.cortes = scoring.sobre_cortes_nino(dn)
        corr = [c for c in CORR_NINO if c in claves]
    else:
        a.cortes = scoring.sobre_cortes_cuidador(dn)
        corr = [c for c in CORR_CUIDADOR if c in claves]
    a.terciles = scoring.terciles(dn)
    a.correlaciones = stats.correlaciones(dn, corr)
    if not a.correlaciones.empty:
        a.correlaciones["etiqueta_a"] = a.correlaciones["a"].map(cat.label)
        a.correlaciones["etiqueta_b"] = a.correlaciones["b"].map(cat.label)
    a.matriz = stats.matriz_correlaciones(dn, corr)
    if solo_nivel:
        a.enmascarados = {"Grado": [], "Colegio": []}
        extra = (regla_cuidadores_distintos(dm, base, claves,
                                            atomos={supresion.RESTO: base.nivel})
                 if marco == cat.MARCO_NINO else None)
        supresion.aplicar(a, extra_por_clave=extra)
        return a
    en_grados = dm.loc[priv_est.union(base.grados.values())]
    en_colegios = dm.loc[priv_est.union(base.colegios.values())]
    a.por_grado, _ = stats.comparar_por_grupo(en_grados, claves, "Grado",
                                              list(cat.GRADOS_ESTUDIO))
    a.por_colegio, _ = stats.comparar_por_grupo(en_colegios, claves, "Colegio")
    for t in (a.por_grado, a.por_colegio):
        if not t.empty:
            t["escala"] = t["clave"].map(cat.label)
    if marco == cat.MARCO_NINO:
        a.por_sexo = _por_sexo(dn, claves)
    a.enmascarados = {
        "Grado": sorted(set(map(str, d["Grado"].dropna().unique())) - set(base.grados)),
        "Colegio": sorted(set(map(str, d["Colegio"].dropna().unique())) - set(base.colegios)),
    }
    a.icc = {k: stats.icc_entre_grupos(dn, k) for k in claves}
    a.subgrupos = _subgrupos(dm, marco, claves, base)
    extra = (regla_cuidadores_distintos(dm, base, claves) if marco == cat.MARCO_NINO
             else None)
    supresion.aplicar(a, extra_por_clave=extra)
    return a


def _items_publicables(t: pd.DataFrame, umbral: int | None = None,
                       escala: tuple[int, int] = (1, 5)) -> pd.DataFrame:
    """Quita el % de los ítems con menos de MIN_CASOS casos o no casos; nunca deja `casos`.

    La media del ítem también acota sus casos (caso = respuesta ≥ `umbral` en
    una escala `escala`): se quita la media donde el % se suprime o donde la
    media sola obliga a que haya menos de MIN_CASOS casos o no casos
    (`supresion.media_delata`, la misma regla que PSSM7 en estudiantes).
    """
    if t.empty:
        return t
    t = t.copy()
    if "casos" in t.columns:
        ok = pd.Series([supresion.proporcion_publicable(k, n)
                        for k, n in zip(t["casos"], t["n"])], index=t.index)
        t.loc[~ok, "pct"] = float("nan")
        if "M" in t.columns and umbral is not None:
            delata = pd.Series([supresion.media_delata(m, n, escala[0], escala[1], umbral,
                                                       casos_altos=True)
                                for m, n in zip(t["M"], t["n"])], index=t.index)
            quitar = ~ok | delata
            for c in ("M", "DE"):
                if c in t.columns:
                    t[c] = t[c].astype(float)
                    t.loc[quitar, c] = float("nan")
        t = t.drop(columns=["casos"])
    return t


# ══ Vista de una ola: solo el total, y solo lo que no se deduce restando ═══
CLAVE_FILA = {cat.MARCO_CUIDADOR: "ID_cuidador", cat.MARCO_NINO: "ID_nino"}
COLUMNAS_MEDIA = ("M", "DE", "Mdn", "min", "max", "P25", "P75")


def _nivel_enmascarado(d: pd.DataFrame, clave_fila: str) -> tuple[pd.DataFrame, object]:
    """(datos enmascarados indexados por la clave de fila, base publicable)."""
    d = d.reset_index(drop=True)
    base = privacidad.base_publicable(d)
    dm, _ = privacidad.aplicar_todo_o_nada(d, base)
    dm.index = d[clave_fila].to_numpy()
    return dm, base


def _validas(df: pd.DataFrame, cols: list[str]) -> set:
    if df.empty or any(c not in df.columns for c in cols):
        return set()
    return set(df.index[df[cols].notna().all(axis=1)])


@dataclass
class ComparadorOla:
    """Lo que alguien deduce restando la vista de una ola de lo publicado con «Todas».

    La ola es un subconjunto de «Todas» (se deduplica primero y luego se
    filtra), así que cada resta es un conjunto real de filas, con los mismos
    valores. Para una columna (o un par) da los conjuntos deducibles:
      · Todas − ola (el complemento);
      · Todas − ola − otras olas (lo que queda sin ola o fuera de las bases);
      · cada colegio, grado o celda de «Todas» que contiene a toda la ola,
        menos la ola.
    None (falla cerrado) si alguna ola tiene con dato una fila que «Todas»
    no tiene en su base: la resta ya no es un conjunto.
    """
    marco: str
    ola: str
    todas: pd.DataFrame                 # «Todas» enmascarado, indexado por clave de fila
    nivel: pd.Index                     # claves del total de «Todas»
    grupos: list                        # claves de cada colegio, grado y celda de «Todas»
    olas: dict                          # ola → total enmascarado de esa ola (por clave)

    @property
    def propia(self) -> pd.DataFrame:
        return self.olas[self.ola]

    def deducibles(self, cols: list[str]) -> list[pd.DataFrame] | None:
        import itertools
        tv = _validas(self.todas.loc[self.nivel], cols)
        wv = {o: _validas(df, cols) for o, df in self.olas.items()}
        if not wv[self.ola] <= tv:
            return None
        conjuntos = [tv - wv[self.ola]]
        otras = [o for o in wv if o != self.ola]
        for r in range(1, len(otras) + 1):
            for comb in itertools.combinations(otras, r):
                if any(not wv[o] <= tv for o in comb):
                    return None
                conjuntos.append(tv - wv[self.ola] - set().union(*(wv[o] for o in comb)))
        for g in self.grupos:
            gv = _validas(self.todas.loc[g], cols)
            if wv[self.ola] and wv[self.ola] <= gv:
                conjuntos.append(gv - wv[self.ola])
        return [self.todas.loc[sorted(c)] for c in conjuntos]

    def media_ok(self, cols: list[str]) -> bool:
        """Una media (o una correlación) se publica si la ola y cada resta tienen ≥ 10."""
        w = self.propia
        if len({*w.loc[sorted(_validas(w, cols)), privacidad.UNIDAD]}) < cat.MIN_GROUP_N:
            return False
        conjuntos = self.deducibles(cols)
        return conjuntos is not None and all(
            D.empty or D[privacidad.UNIDAD].nunique() >= cat.MIN_GROUP_N for D in conjuntos)

    def proporcion_ok(self, cols: list[str], partes) -> bool:
        """`partes(D)` → reparto del indicador en D. Regla de 3 en la ola y en cada resta."""
        if not self.media_ok(cols):
            return False
        w = self.propia.loc[sorted(_validas(self.propia, cols))]
        for D in [w] + self.deducibles(cols):
            if D.empty:
                continue
            p = partes(D)
            if p is None or not supresion.partes_publicables(p):
                return False
            if self.marco == cat.MARCO_NINO and cols[0] in cat_est.BANDS_PARENT:
                b = partes_por_banda(D.reset_index(drop=True), cols[0])
                ids = D.reset_index(drop=True).loc[b.index, privacidad.UNIDAD]
                if not bandas_con_cuidadores_distintos(b, ids):
                    return False
        return True


def _partes_familia(marco: str, clave: str):
    def partes(D: pd.DataFrame):
        D = D.reset_index(drop=True)
        if marco == cat.MARCO_NINO:
            fam = supresion.partes_por_familia(scoring.sobre_cortes_nino(D),
                                               scoring.bandas_nino(D))
        else:
            fam = supresion.partes_por_familia(scoring.sobre_cortes_cuidador(D), None)
        return fam.get(clave)
    return partes


def _anular_filas(t: pd.DataFrame, filas, columnas) -> None:
    for c in columnas:
        if c in t.columns:
            t[c] = t[c].astype(float)
            t.loc[filas, c] = float("nan")


def restringir_a_ola(a: pipe_est.Analisis, comp: ComparadorOla) -> None:
    """Deja en la vista de una ola solo lo que ni ella ni sus restas delatan (en el sitio)."""
    claves_fam = set()
    for t in (a.cortes, a.bandas):
        if t is not None and not t.empty and "clave" in t.columns:
            claves_fam |= set(map(str, t["clave"]))
    for clave in sorted(claves_fam):
        if not comp.proporcion_ok([clave], _partes_familia(comp.marco, clave)):
            supresion._anular(a, clave)
    for nombre, columnas in (("descriptivos", COLUMNAS_MEDIA),
                             ("fiabilidad", ("alpha", "ic_inf", "ic_sup")),
                             ("terciles", ("corte_bajo", "corte_alto"))):
        t = getattr(a, nombre, None)
        if t is None or t.empty:
            continue
        malas = [i for i, k in t["clave"].items() if not comp.media_ok([str(k)])]
        _anular_filas(t, malas, columnas)
    if a.correlaciones is not None and not a.correlaciones.empty:
        ok = [comp.media_ok([str(x), str(y)])
              for x, y in zip(a.correlaciones["a"], a.correlaciones["b"])]
        a.correlaciones = a.correlaciones[ok].reset_index(drop=True)
    if a.matriz is not None and not a.matriz.empty:
        m = a.matriz.astype(float)
        for x in m.index:
            for y in m.columns:
                if x != y and not comp.media_ok([str(x), str(y)]):
                    m.loc[x, y] = float("nan")
        a.matriz = m


def _items_de_ola(t: pd.DataFrame, comp: ComparadorOla, bloque: cat.Bloque,
                  umbral: int) -> pd.DataFrame:
    """Ítems de la vista de una ola: % y media solo si ninguna resta delata."""
    if t.empty:
        return t
    t = t.copy()
    for i, f in t.iterrows():
        col = f"{bloque.prefijo}{int(f['item'])}"

        def partes(D, col=col):
            k = int((D[col] >= umbral).sum())
            return (len(D) - k, k)
        if not comp.proporcion_ok([col], partes):
            _anular_filas(t, [i], ("pct",))
        if not comp.media_ok([col]):
            _anular_filas(t, [i], ("M", "DE"))
    return t


def de_la_ola(todas: pd.DataFrame, nivel: pd.Index, ola: str) -> pd.DataFrame:
    """Filas de una ola dentro del total publicado de «Todas», con sus valores enmascarados.

    Así cada cifra con dato en la ola también tiene dato en «Todas» y cada
    resta es un conjunto de filas.
    """
    t = todas.loc[nivel]
    return t[t[ingest.OLA_COLUMNA] == ola].reset_index(drop=True)


def comparador(d_todas: pd.DataFrame, marco: str, ola: str, olas: list) -> ComparadorOla:
    """`ComparadorOla` de un marco ya puntuado, con las vistas de todas las olas."""
    clave = CLAVE_FILA[marco]
    dm, base = _nivel_enmascarado(d_todas, clave)
    claves_fila = dm.index.to_numpy()
    nivel = pd.Index(claves_fila[base.nivel])
    grupos = [pd.Index(claves_fila[idx])
              for grupos in (base.celdas, base.colegios, base.grados) for idx in grupos.values()]
    niveles = {}
    for o in olas:
        dw, bw = _nivel_enmascarado(de_la_ola(dm, nivel, o), clave)
        niveles[o] = dw.loc[dw.index[bw.nivel]] if len(dw) else dw
    return ComparadorOla(marco=marco, ola=ola, todas=dm, nivel=nivel, grupos=grupos,
                         olas=niveles)


def _items(dn: pd.DataFrame, informe) -> tuple[pd.DataFrame, pd.DataFrame]:
    items_apq = scoring.distribucion_items(dn, cat.APQ, informe.enunciados.get("APQ"),
                                           umbral=cat.APQ_UMBRAL)
    items_estres = scoring.distribucion_items(dn, cat.EP, informe.enunciados.get("EP"),
                                              umbral=cat.MAP_ACUERDO["de acuerdo"])
    if not items_estres.empty:
        items_estres["nota"] = items_estres["item"].map(
            lambda i: "elección forzada partida" if i in cat.EP_ELECCION_FORZADA
            else ("redactado en positivo" if i in cat.EP_POSITIVO else ""))
    return items_apq, items_estres


def analizar(carga: ingest.Carga, ola: str | None = None, n_boot: int = 300
             ) -> AnalisisCuidadores:
    """Los dos marcos. Con `ola`, la vista de esa ola (solo el total; ver `ComparadorOla`).

    Se deduplica siempre sobre todas las olas (la respuesta más reciente de
    cada cuidador y de cada niño) y después se filtra: la vista de una ola es
    un subconjunto exacto de «Todas».
    """
    cuid, ninos, informe = ingest.deduplicar(carga)
    cuid_p = scoring.puntuar_cuidadores(cuid)
    ninos_p = scoring.puntuar_ninos(ninos)
    olas = sorted(o for o in carga.respuestas["Ola"].dropna().unique() if o != cat.SIN_DATO)
    avisos_c = [cat.AVISO_EPDS, cat.AVISO_APQ, cat.AVISO_MSPSS]
    avisos_n = [cat.AVISO_SDQ_EDAD, cat.AVISO_ARI]
    umbral_ep = cat.MAP_ACUERDO["de acuerdo"]
    escala_apq = (cat.APQ.valor_min, cat.APQ.valor_max)
    escala_ep = (cat.EP.valor_min, cat.EP.valor_max)
    flujo: dict = {}
    if ola is None:
        a_c = analizar_marco(cuid_p, cat.MARCO_CUIDADOR, n_boot=n_boot, avisos=avisos_c)
        a_n = analizar_marco(ninos_p, cat.MARCO_NINO, n_boot=n_boot, avisos=avisos_n)
        items_apq, items_estres = _items(a_c.datos.loc[a_c.base.nivel], informe)
    else:
        ola = str(ola)
        olas_vista = sorted(set(olas) | {ola})
        comp_c = comparador(cuid_p, cat.MARCO_CUIDADOR, ola, olas_vista)
        comp_n = comparador(ninos_p, cat.MARCO_NINO, ola, olas_vista)
        a_c = analizar_marco(de_la_ola(comp_c.todas, comp_c.nivel, ola), cat.MARCO_CUIDADOR,
                             n_boot=n_boot, avisos=avisos_c, solo_nivel=True)
        a_n = analizar_marco(de_la_ola(comp_n.todas, comp_n.nivel, ola), cat.MARCO_NINO,
                             n_boot=n_boot, avisos=avisos_n, solo_nivel=True)
        restringir_a_ola(a_c, comp_c)
        restringir_a_ola(a_n, comp_n)
        items_apq, items_estres = _items(a_c.datos.loc[a_c.base.nivel], informe)
        flujo = {}
        for marco, d, comp, a in ((cat.MARCO_CUIDADOR, cuid_p, comp_c, a_c),
                                  (cat.MARCO_NINO, ninos_p, comp_n, a_n)):
            flujo[marco] = dict(distintos=len(d), en_base=len(comp.nivel),
                                fuera_de_base=len(d) - len(comp.nivel),
                                otras_olas=len(comp.nivel) - a.n)
        items_apq = _items_de_ola(items_apq, comp_c, cat.APQ, cat.APQ_UMBRAL)
        items_estres = _items_de_ola(items_estres, comp_c, cat.EP, umbral_ep)
    return AnalisisCuidadores(cuidador=a_c, nino=a_n, informe=informe, ola=ola, olas=olas,
                              flujo_ola=flujo,
                              items_apq=_items_publicables(items_apq, cat.APQ_UMBRAL, escala_apq),
                              items_estres=_items_publicables(items_estres, umbral_ep, escala_ep))


def cargar_y_analizar(ruta: str | None = None, ola: str | None = None,
                      n_boot: int = 300) -> AnalisisCuidadores:
    ruta = ruta or localizar_formulario()
    if not ruta:
        raise FileNotFoundError(
            "No se encontró la exportación de «Cuidando al Cuidador» en la carpeta "
            "de datos fuente (ver src/core/rutas.py y OBS360_DATOS_DIR).")
    return analizar(ingest.cargar(ruta), ola=ola, n_boot=n_boot)
