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

`ola` filtra antes de deduplicar. Solo existe en local: no se publica por ola.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import pandas as pd

from src.cuidadores import catalog as cat
from src.cuidadores import ingest, privacidad, scoring
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


def analizar_marco(d: pd.DataFrame, marco: str, n_boot: int = 300,
                   avisos: list | None = None) -> pipe_est.Analisis:
    """Un marco ya puntuado → `Analisis` sobre la base publicable, con supresión."""
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
    supresion.aplicar(a)
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


def analizar(carga: ingest.Carga, ola: str | None = None, n_boot: int = 300
             ) -> AnalisisCuidadores:
    cuid, ninos, informe = ingest.deduplicar(carga, ola)
    cuid_p = scoring.puntuar_cuidadores(cuid)
    ninos_p = scoring.puntuar_ninos(ninos)
    avisos_c = [cat.AVISO_EPDS, cat.AVISO_APQ, cat.AVISO_MSPSS]
    avisos_n = [cat.AVISO_SDQ_EDAD, cat.AVISO_ARI]
    a_c = analizar_marco(cuid_p, cat.MARCO_CUIDADOR, n_boot=n_boot, avisos=avisos_c)
    a_n = analizar_marco(ninos_p, cat.MARCO_NINO, n_boot=n_boot, avisos=avisos_n)
    dn = a_c.datos.loc[a_c.base.nivel]
    items_apq = scoring.distribucion_items(dn, cat.APQ, informe.enunciados.get("APQ"),
                                           umbral=cat.APQ_UMBRAL)
    items_estres = scoring.distribucion_items(dn, cat.EP, informe.enunciados.get("EP"),
                                              umbral=cat.MAP_ACUERDO["de acuerdo"])
    if not items_estres.empty:
        items_estres["nota"] = items_estres["item"].map(
            lambda i: "elección forzada partida" if i in cat.EP_ELECCION_FORZADA
            else ("redactado en positivo" if i in cat.EP_POSITIVO else ""))
    olas = sorted(o for o in carga.respuestas["Ola"].dropna().unique() if o != cat.SIN_DATO)
    return AnalisisCuidadores(cuidador=a_c, nino=a_n, informe=informe, ola=ola, olas=olas,
                              items_apq=_items_publicables(
                                  items_apq, cat.APQ_UMBRAL, (cat.APQ.valor_min, cat.APQ.valor_max)),
                              items_estres=_items_publicables(
                                  items_estres, cat.MAP_ACUERDO["de acuerdo"],
                                  (cat.EP.valor_min, cat.EP.valor_max)))


def cargar_y_analizar(ruta: str | None = None, ola: str | None = None,
                      n_boot: int = 300) -> AnalisisCuidadores:
    ruta = ruta or localizar_formulario()
    if not ruta:
        raise FileNotFoundError(
            "No se encontró la exportación de «Cuidando al Cuidador» en la carpeta "
            "de datos fuente (ver src/core/rutas.py y OBS360_DATOS_DIR).")
    return analizar(ingest.cargar(ruta), ola=ola, n_boot=n_boot)
