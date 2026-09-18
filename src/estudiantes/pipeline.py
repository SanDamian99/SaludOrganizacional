"""
Orquestación del módulo de estudiantes — Observatorio 360.

`analizar(df)` produce, de una sola vez, todo lo que consumen las dos vistas y
los exportables. Es la frontera única entre el cálculo y la presentación.
"""
from __future__ import annotations


import os
from dataclasses import dataclass, field

import pandas as pd

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, scoring, stats

# Fragmentos con los que se reconocen los dos formularios en disco. Se comparan
# sobre el nombre normalizado porque macOS guarda los acentos descompuestos
# (NFD) y un glob con tildes no coincide.
PATRONES = ("cuentanos sobre tu bienestar emocional",
            "cuentanos sobre tus emociones")
EXTENSIONES = (".csv", ".xlsx", ".xls")


def localizar_formularios(base: str | None = None) -> list[str]:
    """Rutas de los formularios presentes en `base`, en el orden de PATRONES."""
    from src.estudiantes.ingest import norm_txt
    base = base or os.getcwd()
    if not os.path.isdir(base):
        return []
    archivos = [f for f in os.listdir(base) if f.lower().endswith(EXTENSIONES)]
    rutas: list[str] = []
    for p in PATRONES:
        for f in sorted(archivos):
            if p in norm_txt(f):
                ruta = os.path.join(base, f)
                if ruta not in rutas:
                    rutas.append(ruta)
    return rutas


@dataclass
class Analisis:
    """Resultado completo para un nivel educativo."""
    nivel: str
    n: int
    datos: pd.DataFrame                     # con puntuaciones; sin identificadores directos
    muestra: dict = field(default_factory=dict)
    descriptivos: pd.DataFrame = field(default_factory=pd.DataFrame)
    fiabilidad: pd.DataFrame = field(default_factory=pd.DataFrame)
    bandas: pd.DataFrame = field(default_factory=pd.DataFrame)
    cortes: pd.DataFrame = field(default_factory=pd.DataFrame)
    terciles: pd.DataFrame = field(default_factory=pd.DataFrame)
    percentiles: pd.DataFrame = field(default_factory=pd.DataFrame)
    correlaciones: pd.DataFrame = field(default_factory=pd.DataFrame)
    matriz: pd.DataFrame = field(default_factory=pd.DataFrame)
    por_sexo: pd.DataFrame = field(default_factory=pd.DataFrame)
    por_grado: pd.DataFrame = field(default_factory=pd.DataFrame)
    por_colegio: pd.DataFrame = field(default_factory=pd.DataFrame)
    por_edad: pd.DataFrame = field(default_factory=pd.DataFrame)
    enmascarados: dict = field(default_factory=dict)
    modelos: list = field(default_factory=list)
    icc: dict = field(default_factory=dict)
    solapamiento: dict = field(default_factory=dict)
    contrastes: list = field(default_factory=list)
    items_pssm: pd.DataFrame = field(default_factory=pd.DataFrame)
    escalas: list = field(default_factory=list)
    avisos: list = field(default_factory=list)


CLAVES_PRINCIPALES = ["SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro",
                      "ARI_Total", "RCADS_Dep", "RCADS_Anx", "ERQ_Reap", "ERQ_Sup",
                      "MSPSS_Total", "MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro",
                      "PSSM_Total", "TD_Total"]

PROTECTORES = ["MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro", "PSSM_Total", "ERQ_Reap", "ERQ_Sup"]


def analizar(datos_puntuados: pd.DataFrame, nivel: str,
             n_boot: int = 300, avisos: list | None = None) -> Analisis:
    d = datos_puntuados[datos_puntuados["nivel"] == nivel].copy() \
        if "nivel" in datos_puntuados.columns else datos_puntuados.copy()
    claves = [k for k in CLAVES_PRINCIPALES if k in d.columns and d[k].notna().any()]
    orden_grados = (cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA
                    else cat.ORDEN_GRADOS_PRI)

    a = Analisis(nivel=nivel, n=len(d), datos=d, escalas=claves,
                 avisos=list(avisos or []))
    a.muestra = dict(
        n=len(d),
        sexo=d["Sexo"].value_counts().to_dict(),
        edad_M=round(float(d["Edad"].mean()), 2), edad_DE=round(float(d["Edad"].std()), 2),
        edad=d["Edad"].value_counts().sort_index().to_dict(),
        grado=d["Grado"].value_counts().to_dict(),
        colegio=d["Colegio"].value_counts().to_dict(),
        fechas=([str(d["ts"].min().date()), str(d["ts"].max().date())]
                if "ts" in d.columns and d["ts"].notna().any() else []),
    )
    a.descriptivos = scoring.descriptivos(d)
    a.fiabilidad = scoring.fiabilidad(d, n_boot=n_boot)
    a.bandas = scoring.distribucion_bandas(d, "self")
    a.cortes = scoring.sobre_cortes(d)
    a.terciles = scoring.terciles(d)
    if "RCADS_Dep" in claves:
        a.percentiles = scoring.percentiles_por_sexo(
            d, ["RCADS_Dep", "RCADS_Anx", "RCADS_Total"])

    corr_vars = (cat.CORR_VARS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.CORR_VARS_PRI)
    a.correlaciones = stats.correlaciones(d, corr_vars)
    a.matriz = stats.matriz_correlaciones(d, corr_vars)

    a.por_sexo = stats.comparar_por_sexo(d, claves)
    a.por_grado, enm_g = stats.comparar_por_grupo(d, claves, "Grado", orden_grados)
    a.por_colegio, enm_c = stats.comparar_por_grupo(d, claves, "Colegio")
    a.enmascarados = {"Grado": enm_g, "Colegio": enm_c}
    a.por_edad = stats.correlacion_con_edad(d, claves)

    objetivos = [k for k in ("RCADS_Dep", "RCADS_Anx", "SDQ_Total", "ARI_Total") if k in claves]
    for y in objetivos:
        m = stats.modelo(d, y, [p for p in PROTECTORES if p in claves])
        if m:
            a.modelos.append(m)
    if "SDQ_Con" in claves and "TD_Total" in claves:
        m = stats.modelo(d, "SDQ_Con", ["TD_Total", "ERQ_Sup", "ERQ_Reap", "PSSM_Total"])
        if m:
            a.modelos.append(m)

    a.icc = {k: stats.icc_entre_grupos(d, k) for k in claves}
    a.solapamiento = stats.solapamiento(d)
    for res in [k for k in ("RCADS_Dep", "SDQ_Total") if k in claves]:
        for prot in [p for p in ("MSPSS_Fam", "PSSM_Total") if p in claves]:
            c = stats.contraste_protector(d, res, prot)
            if c:
                a.contrastes.append(c)
    a.items_pssm = stats.medias_items(d, "PSSM")

    if nivel == cat.NIVEL_PRIMARIA and cat.AVISO_PRIMARIA not in a.avisos:
        a.avisos.append(cat.AVISO_PRIMARIA)
    return a


def cargar_y_analizar(rutas: list[str] | None = None, base: str | None = None,
                      n_boot: int = 300) -> tuple[dict[str, Analisis], list]:
    """Punto de entrada: localiza los formularios, los procesa y analiza por nivel."""
    rutas = rutas or localizar_formularios(base)
    if not rutas:
        raise FileNotFoundError(
            "No se encontraron los formularios de estudiantes. Se buscan archivos "
            f"con los patrones {PATRONES} en {base or os.getcwd()}.")
    bruto, informes = ingest.cargar_varios(rutas)
    puntuado = scoring.puntuar(bruto)
    resultados = {}
    for inf in informes:
        avisos = list(inf.avisos)
        resultados[inf.nivel] = analizar(puntuado, inf.nivel, n_boot=n_boot, avisos=avisos)
    return resultados, informes
