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
from src.estudiantes import alertas, ingest, privacidad, scoring, stats, supresion

# Fragmentos con los que se reconocen los dos formularios en disco. Se comparan
# sobre el nombre normalizado porque macOS guarda los acentos descompuestos
# (NFD) y un glob con tildes no coincide.
PATRONES = ("cuentanos sobre tu bienestar emocional",
            "cuentanos sobre tus emociones")
EXTENSIONES = (".csv", ".xlsx", ".xls")


def localizar_formularios(base: str | None = None) -> list[str]:
    """Un archivo por formulario: si hay varios (CSV viejo y xlsx nuevo), el más reciente."""
    from src.estudiantes.ingest import norm_txt
    from src.core.rutas import carpeta_datos
    base = base or carpeta_datos("estudiantes")
    if not os.path.isdir(base):
        return []
    archivos = [f for f in os.listdir(base) if f.lower().endswith(EXTENSIONES)]
    rutas: list[str] = []
    for p in PATRONES:
        candidatos = [os.path.join(base, f) for f in archivos if p in norm_txt(f)]
        if candidatos:
            rutas.append(max(candidatos, key=os.path.getmtime))
    return rutas


@dataclass
class Analisis:
    """Resultado completo para un nivel educativo."""
    nivel: str
    n: int
    # Copia ENMASCARADA (todo o nada por columna, privacidad.aplicar_todo_o_nada)
    # de los datos puntuados; sin identificadores directos. No son los datos
    # crudos: un indicador que no llega al mínimo en algún grupo ya viene vacío.
    datos: pd.DataFrame
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
    # {"Colegio": {"LauV": Analisis}, "Grado": {"8": Analisis},
    #  "Colegio×Grado": {"LauV|8": Analisis}}: los resultados que la vista
    # comunidad necesita para un colegio, un grado o una celda, ya calculados
    # sobre la base publicable (privacidad.base_publicable). Existen para que el despliegue,
    # que no tiene fila por estudiante, pueda filtrar igual que la máquina que
    # procesa. Cada uno lleva `datos` vacío a propósito.
    subgrupos: dict = field(default_factory=dict)
    # Alertas de grupo (spec §5.4, alertas.py). `cortes_alerta`: una fila por
    # alerta con la forma de `cortes` (con casos, que nunca se publican); la
    # tienen el nivel y cada subgrupo, y la supresión la trata como una familia
    # más. `alertas`: la tabla plana por grupo que leen las vistas y que se
    # publica, sin casos. Sensibilidad e ítems: solo locales, del nivel. Todas
    # vacías en una corrida anterior a la fase 3.
    cortes_alerta: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas_sensibilidad: pd.DataFrame = field(default_factory=pd.DataFrame)
    alertas_items: pd.DataFrame = field(default_factory=pd.DataFrame)
    # Base publicable (privacidad.Base). Solo existe con datos crudos; no se publica.
    base: object = None


CLAVES_PRINCIPALES = ["SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro",
                      "ARI_Total", "RCADS_Dep", "RCADS_Anx", "ERQ_Reap", "ERQ_Sup",
                      "MSPSS_Total", "MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro",
                      "PSSM_Total", "TD_Total"]

PROTECTORES = ["MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro", "PSSM_Total", "ERQ_Reap", "ERQ_Sup"]


def analizar(datos_puntuados: pd.DataFrame, nivel: str,
             n_boot: int = 300, avisos: list | None = None) -> Analisis:
    d = datos_puntuados[datos_puntuados["nivel"] == nivel].copy() \
        if "nivel" in datos_puntuados.columns else datos_puntuados.copy()
    # Señal de alerta por estudiante (1 / 0 / NaN). Entra en la base publicable y
    # en el todo o nada como cualquier otra columna, así que la auditoría de
    # restas de n la cubre. Nunca se publica fila a fila.
    d = alertas.marcar(d, nivel)
    claves = [k for k in CLAVES_PRINCIPALES if k in d.columns and d[k].notna().any()]
    orden_grados = (cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA
                    else cat.ORDEN_GRADOS_PRI)

    # Toda cifra publicada sale de la copia enmascarada (todo o nada por
    # indicador) y de la misma base. `muestra` es lo único que se cuenta sobre
    # los datos crudos: tamaños (sexo, edad, grado, colegio, celdas), media y
    # DE de la edad y rango de fechas. Son columnas de identificación, no
    # indicadores, y el todo o nada no las toca.
    base = privacidad.base_publicable(d)
    dm, suprimidos = privacidad.aplicar_todo_o_nada(d, base)
    dn = dm.loc[base.nivel]           # lo que se publica a nivel de todo el nivel
    a = Analisis(nivel=nivel, n=len(d), datos=dm, escalas=claves,
                 avisos=list(avisos or []))
    a.base = base
    a.muestra = dict(
        n=len(d),
        sexo=d["Sexo"].value_counts().to_dict(),
        edad_M=round(float(d["Edad"].mean()), 2), edad_DE=round(float(d["Edad"].std()), 2),
        # claves enteras: «13», no «13.0», que es lo que se muestra al lector
        edad={int(k): int(v) for k, v in
              d["Edad"].dropna().value_counts().sort_index().items()},
        grado=d["Grado"].value_counts().to_dict(),
        colegio=d["Colegio"].value_counts().to_dict(),
        colegio_grado={privacidad.clave_celda(c, g): int(n) for (c, g), n in
                       d.groupby(["Colegio", "Grado"]).size().items()},
        base=base.resumen(),
        # valores que el todo o nada borró, por columna (para el investigador)
        suprimidos=suprimidos,
        fechas=([str(d["ts"].min().date()), str(d["ts"].max().date())]
                if "ts" in d.columns and d["ts"].notna().any() else []),
    )
    a.descriptivos = scoring.descriptivos(dn)
    a.fiabilidad = scoring.fiabilidad(dn, n_boot=n_boot)
    a.bandas = scoring.distribucion_bandas(dn, "self")
    a.cortes = scoring.sobre_cortes(dn)
    a.cortes_alerta = alertas.cortes_alerta(dn, nivel)
    a.terciles = scoring.terciles(dn)
    if "RCADS_Dep" in claves:
        a.percentiles = scoring.percentiles_por_sexo(
            dn, ["RCADS_Dep", "RCADS_Anx", "RCADS_Total"])

    corr_vars = (cat.CORR_VARS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.CORR_VARS_PRI)
    a.correlaciones = stats.correlaciones(dn, corr_vars)
    a.matriz = stats.matriz_correlaciones(dn, corr_vars)

    a.por_sexo = stats.comparar_por_sexo(dn, claves)
    en_grados = dm.loc[privacidad.union(base.grados.values())]
    en_colegios = dm.loc[privacidad.union(base.colegios.values())]
    a.por_grado, _ = stats.comparar_por_grupo(en_grados, claves, "Grado", orden_grados)
    a.por_colegio, _ = stats.comparar_por_grupo(en_colegios, claves, "Colegio")
    # Enmascarados: los colegios y grados presentes que la base no publica.
    # comparar_por_grupo ya no los ve porque solo recibe filas de la base.
    colegios_fuera = set(map(str, d["Colegio"].dropna().unique())) - set(base.colegios)
    grados_fuera = set(map(str, d["Grado"].dropna().unique())) - set(base.grados)
    a.enmascarados = {
        "Grado": ([g for g in orden_grados if g in grados_fuera]
                  + sorted(grados_fuera - set(orden_grados))),
        "Colegio": sorted(colegios_fuera),
    }
    a.por_edad = stats.correlacion_con_edad(dn, claves)

    objetivos = [k for k in ("RCADS_Dep", "RCADS_Anx", "SDQ_Total", "ARI_Total") if k in claves]
    for y in objetivos:
        m = stats.modelo(dn, y, [p for p in PROTECTORES if p in claves])
        if m:
            a.modelos.append(m)
    if "SDQ_Con" in claves and "TD_Total" in claves:
        m = stats.modelo(dn, "SDQ_Con", ["TD_Total", "ERQ_Sup", "ERQ_Reap", "PSSM_Total"])
        if m:
            a.modelos.append(m)

    a.icc = {k: stats.icc_entre_grupos(dn, k) for k in claves}
    a.solapamiento = stats.solapamiento(dn)
    a.contrastes = _contrastes(dn, claves)
    a.items_pssm = stats.medias_items(dn, "PSSM")
    a.subgrupos = subanalizar(dm, nivel, claves, base)
    # Cifras que no delatan (spec §5.4): ninguna proporción del nivel ni de sus
    # subgrupos con menos de supresion.MIN_CASOS casos o no casos, ni deducible
    # por resta. Se aplica aquí, antes de publicar y de mostrar, para que la
    # vista local y la corrida publicada vean lo mismo.
    supresion.aplicar(a)
    # Después de la supresión: la tabla plana solo lleva lo que quedó publicable
    # y el estado se calcula con esas cifras.
    a.alertas = alertas.tabla(a)
    a.alertas_sensibilidad = alertas.sensibilidad(dn, nivel, a.cortes_alerta)
    a.alertas_items = alertas.distribucion_items(dn, nivel)

    if nivel == cat.NIVEL_PRIMARIA and cat.AVISO_PRIMARIA not in a.avisos:
        a.avisos.append(cat.AVISO_PRIMARIA)
    return a


COLUMNAS_SUBGRUPO = ("Colegio", "Grado", privacidad.AGRUPACION_CRUCE)


def _contrastes(d: pd.DataFrame, claves: list[str]) -> list[dict]:
    salida = []
    for res in [k for k in ("RCADS_Dep", "SDQ_Total") if k in claves]:
        for prot in [p for p in ("MSPSS_Fam", "PSSM_Total") if p in claves]:
            c = stats.contraste_protector(d, res, prot)
            if c:
                salida.append(c)
    return salida


def subanalizar(d: pd.DataFrame, nivel: str, claves: list[str], base=None) -> dict:
    """Resultados de la vista comunidad por colegio, por grado y por celda colegio×grado.

    Solo las tablas que esa vista muestra (bandas, cortes, contrastes e ítems
    de pertenencia). Cada grupo se calcula sobre la base publicable
    (privacidad.base_publicable): así ninguna resta entre un colegio, un grado
    y sus celdas deja un grupo pequeño. `analizar` le pasa los datos ya
    enmascarados con todo o nada y su base. Sin `base`, la función la arma y
    enmascara `d` ella misma (privacidad.aplicar_todo_o_nada) antes de
    calcular; con `base`, supone que `d` ya viene enmascarado con ella.
    """
    if base is None:
        base = privacidad.base_publicable(d)
        d, _ = privacidad.aplicar_todo_o_nada(d, base)
    salida: dict = {}
    for columna, grupos in (("Colegio", base.colegios), ("Grado", base.grados),
                            (privacidad.AGRUPACION_CRUCE, base.celdas)):
        for grupo, idx in grupos.items():
            sub = d.loc[idx]
            if len(sub) < cat.MIN_GROUP_N:
                continue
            s = Analisis(nivel=nivel, n=len(sub), datos=pd.DataFrame(),
                         escalas=list(claves), muestra=dict(n=len(sub)))
            s.bandas = scoring.distribucion_bandas(sub, "self")
            s.cortes = scoring.sobre_cortes(sub)
            s.cortes_alerta = alertas.cortes_alerta(sub, nivel)
            s.items_pssm = stats.medias_items(sub, "PSSM")
            s.contrastes = _contrastes(sub, claves)
            salida.setdefault(columna, {})[str(grupo)] = s
    return salida


def cargar_y_analizar(rutas: list[str] | None = None, base: str | None = None,
                      n_boot: int = 300) -> tuple[dict[str, Analisis], list]:
    """Punto de entrada: localiza los formularios, los procesa y analiza por nivel."""
    rutas = rutas or localizar_formularios(base)
    if not rutas:
        raise FileNotFoundError(
            "No se encontraron los formularios de estudiantes. Se buscan archivos "
            f"con los patrones {PATRONES} en {base or 'la carpeta de datos fuente'} "
            "(ver src/core/rutas.py y OBS360_DATOS_DIR).")
    bruto, informes = ingest.cargar_varios(rutas)
    puntuado = scoring.puntuar(bruto)
    resultados = {}
    for inf in informes:
        avisos = list(inf.avisos)
        resultados[inf.nivel] = analizar(puntuado, inf.nivel, n_boot=n_boot, avisos=avisos)
    return resultados, informes
