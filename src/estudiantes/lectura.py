"""
Lectura de resultados publicados desde Supabase — Observatorio 360.

Es la otra mitad de `publicar.py`. Permite que la aplicación desplegada muestre
los resultados **sin tener los CSV**: los datos crudos, que traen nombres de
menores, se quedan en la máquina de quien procesa.

QUÉ RECONSTRUYE
Un objeto `Analisis` por nivel, con las tablas que consumen las vistas. Lo que
**no** puede reconstruir es `Analisis.datos`, la fila por estudiante, porque eso
nunca se publica. Queda como un DataFrame vacío, y las vistas lo tratan como lo
que es: no hay filtro por colegio ni por grado, solo las cifras del nivel
completo y las comparaciones que sí se publicaron.

Esa limitación es el diseño, no un defecto: un despliegue público no debería
poder recalcular nada sobre individuos.

Solo lee corridas con `publicada = true`, y lo hace con la clave `anon`, que no
tiene permiso de escritura.
"""
from __future__ import annotations

import os

import pandas as pd

from src.estudiantes import catalog as cat
from src.estudiantes.pipeline import Analisis

ESQUEMA = "obs360"


class InformeLeido:
    """Equivalente a `InformeIngesta` reconstruido desde lo publicado.

    Las vistas leen los campos con `getattr`, así que basta con exponerlos.
    """

    def __init__(self, nivel: str, datos: dict):
        self.nivel = nivel
        for campo, valor in (datos or {}).items():
            setattr(self, campo, valor)
        self.avisos = list(getattr(self, "avisos", []) or [])
        self.origen = "supabase"


def credenciales() -> tuple[str | None, str | None]:
    """(url, clave de lectura), por orden de precedencia.

    1. `OBS360_SUPABASE_URL` / `OBS360_SUPABASE_KEY`. Existen porque Streamlit
       copia sus secretos a `os.environ`, de modo que exportar `SUPABASE_KEY`
       no sirve para nada: el secreto lo sobrescribe al arrancar. Con estos
       nombres propios sí se puede previsualizar con otra clave.
    2. `SUPABASE_URL` / `SUPABASE_KEY` del entorno o de los secretos, que es lo
       normal en producción.
    """
    url = os.environ.get("OBS360_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("OBS360_SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (url and key):
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL")
            key = key or st.secrets.get("SUPABASE_KEY")
        except Exception:                                  # noqa: BLE001
            pass
    return url, key


def disponible() -> bool:
    url, key = credenciales()
    return bool(url and key)


def _cliente():
    from supabase import create_client
    url, key = credenciales()
    if not (url and key):
        raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_KEY.")
    return create_client(url, key)


def id_corrida_vigente() -> int | None:
    """Id de la corrida publicada más reciente, o None. Consulta mínima: una fila.

    Sirve como clave de caché en la aplicación: si aparece una corrida nueva la
    clave cambia y se vuelve a leer todo, sin esperar a que el proceso reinicie.
    """
    cli = _cliente()
    filas = (cli.postgrest.schema(ESQUEMA).table("corridas").select("id")
             .order("creada_en", desc=True).limit(1).execute().data)
    return int(filas[0]["id"]) if filas else None


def _traer_filas(cli) -> tuple[dict | None, list[dict]]:
    """(corrida publicada, filas de resultados). RLS ya filtra por `publicada`."""
    tabla = cli.postgrest.schema(ESQUEMA)
    corridas = (tabla.table("corridas").select("*")
                .order("creada_en", desc=True).limit(1).execute().data)
    if not corridas:
        return None, []
    corrida = corridas[0]
    filas, desde, paso = [], 0, 1000
    while True:
        lote = (tabla.table("resultados").select("*")
                .eq("corrida_id", corrida["id"])
                .range(desde, desde + paso - 1).execute().data)
        filas.extend(lote)
        if len(lote) < paso:
            break
        desde += paso
    return corrida, filas


def _df(filas: list[dict], columnas: list[str]) -> pd.DataFrame:
    return pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame(columns=columnas)


def _reconstruir(nivel: str, filas: list[dict]) -> Analisis:
    """Rearma las tablas del objeto `Analisis` a partir de las filas publicadas."""
    por_tipo: dict[str, list[dict]] = {}
    for f in filas:
        por_tipo.setdefault(f["tipo"], []).append(f)

    def det(f, clave, defecto=None):
        return (f.get("detalle") or {}).get(clave, defecto)

    def bandera(f, clave, defecto=False) -> bool:
        """Bandera como booleano, aunque una corrida antigua la guardara como 1.0."""
        valor = det(f, clave, defecto)
        return bool(valor) if valor is not None else bool(defecto)

    # ── muestra, avisos y escalas
    muestra, enmascarados, escalas, avisos = {}, {}, [], []
    for f in por_tipo.get("muestra", []):
        muestra = det(f, "muestra", {}) or {}
        enmascarados = det(f, "enmascarados", {}) or {}
        escalas = det(f, "escalas", []) or []
        avisos = list(det(f, "avisos", []) or [])
    n = int(muestra.get("n") or 0)

    a = Analisis(nivel=nivel, n=n, datos=pd.DataFrame(),
                 muestra=muestra, enmascarados=enmascarados,
                 escalas=escalas, avisos=avisos)

    # ── descriptivos y fiabilidad (viajan juntos en la misma fila)
    desc, fiab = [], []
    for f in por_tipo.get("descriptivo", []):
        desc.append(dict(clave=f["clave"], escala=f["escala"], n=f["n"], M=f["valor"],
                         DE=det(f, "DE"), Mdn=det(f, "Mdn"),
                         min=det(f, "minimo"), max=det(f, "maximo"),
                         rango=det(f, "rango"), pct_faltante=det(f, "pct_faltante"),
                         P25=det(f, "P25"), P75=det(f, "P75"),
                         P90=det(f, "P90"), P95=det(f, "P95"),
                         direccion=det(f, "direccion"),
                         validada=bandera(f, "validada", True)))
        if det(f, "alpha") is not None:
            alpha = det(f, "alpha")
            fiab.append(dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                             n_items=det(f, "n_items"),
                             alpha=alpha, ic_inf=det(f, "alpha_ic_inf"),
                             ic_sup=det(f, "alpha_ic_sup"),
                             aceptable=bool(alpha >= 0.70)))
    orden = {k: i for i, k in enumerate(cat.ORDEN_TABLA1)}
    a.descriptivos = _df(sorted(desc, key=lambda d: orden.get(d["clave"], 99)),
                         ["clave", "escala", "n", "M", "DE", "Mdn", "min", "max",
                          "rango", "pct_faltante", "P25", "P75", "P90", "P95",
                          "direccion", "validada"])
    a.fiabilidad = _df(sorted(fiab, key=lambda d: orden.get(d["clave"], 99)),
                       ["clave", "escala", "n_items", "n", "alpha", "ic_inf",
                        "ic_sup", "aceptable"])

    # ── bandas y cortes (compartidos con los subgrupos)
    a.bandas = _tabla_bandas(por_tipo.get("banda", []))
    a.cortes = _tabla_cortes(por_tipo.get("corte", []))

    # ── terciles y percentiles
    a.terciles = _df([dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                           corte_bajo=det(f, "corte_bajo"),
                           corte_alto=det(f, "corte_alto"), nota=det(f, "nota"))
                      for f in por_tipo.get("tercil", [])],
                     ["clave", "escala", "n", "corte_bajo", "corte_alto", "nota"])
    a.percentiles = _df([dict(clave=f["clave"], escala=f["escala"], sexo=f["grupo"],
                              n=f["n"], P50=f["valor"], P75=det(f, "P75"),
                              P85=det(f, "P85"), P90=det(f, "P90"), P95=det(f, "P95"))
                         for f in por_tipo.get("percentil", [])],
                        ["clave", "escala", "sexo", "n", "P50", "P75", "P85", "P90", "P95"])

    # ── correlaciones y su matriz
    corr = [dict(a=f["clave"], b=det(f, "variable_b"),
                 etiqueta_a=f["escala"], etiqueta_b=det(f, "etiqueta_b"),
                 rho=f["valor"], ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                 p=det(f, "p"), n=f["n"], q_bh=det(f, "q_bh"),
                 significativa=bandera(f, "significativa"))
            for f in por_tipo.get("correlacion", [])]
    a.correlaciones = _df(corr, ["a", "b", "etiqueta_a", "etiqueta_b", "rho",
                                 "ic_inf", "ic_sup", "p", "n", "q_bh", "significativa"])
    if corr:
        variables = [v for v in cat.CORR_VARS_SEC
                     if v in {c["a"] for c in corr} | {c["b"] for c in corr}]
        matriz = pd.DataFrame(1.0, index=variables, columns=variables)
        for c in corr:
            if c["a"] in variables and c["b"] in variables:
                matriz.loc[c["a"], c["b"]] = c["rho"]
                matriz.loc[c["b"], c["a"]] = c["rho"]
        a.matriz = matriz
    else:
        a.matriz = pd.DataFrame()

    # ── comparaciones por grupo
    grupos = por_tipo.get("grupo", [])
    sexo = {}
    for f in [g for g in grupos if g["agrupacion"] == "Sexo"]:
        fila = sexo.setdefault(f["clave"], dict(clave=f["clave"], escala=f["escala"],
                                                d=det(f, "d"), magnitud=det(f, "magnitud"),
                                                p=det(f, "p"), q_bh=det(f, "q_bh")))
        sufijo = "mujer" if f["grupo"] == "Mujer" else "hombre"
        fila[f"M_{sufijo}"] = f["valor"]
        fila[f"DE_{sufijo}"] = det(f, "DE")
        fila[f"n_{sufijo}"] = f["n"]
    a.por_sexo = _df(list(sexo.values()),
                     ["clave", "escala", "n_mujer", "n_hombre", "M_mujer", "M_hombre",
                      "DE_mujer", "DE_hombre", "d", "magnitud", "p", "q_bh"])

    for agrupacion, destino in (("Grado", "por_grado"), ("Colegio", "por_colegio")):
        acumulado: dict[str, dict] = {}
        for f in [g for g in grupos if g["agrupacion"] == agrupacion]:
            fila = acumulado.setdefault(f["clave"], dict(
                clave=f["clave"], escala=f["escala"], p=det(f, "p"),
                eta2=det(f, "eta2"), q_bh=det(f, "q_bh"), n=0))
            fila[f"M·{f['grupo']}"] = f["valor"]
            fila[f"n·{f['grupo']}"] = f["n"]
            fila["n"] += int(f["n"] or 0)
        setattr(a, destino, pd.DataFrame(list(acumulado.values())))

    a.por_edad = _df([dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                           rho=f["valor"], p=det(f, "p"), q_bh=det(f, "q_bh"))
                      for f in grupos if f["agrupacion"] == "Edad"],
                     ["clave", "escala", "n", "rho", "p", "q_bh"])

    # ── modelos
    modelos: dict[str, dict] = {}
    for f in por_tipo.get("modelo", []):
        m = modelos.setdefault(f["clave"], dict(
            y=f["clave"], y_etiqueta=f["escala"], n=f["n"],
            clusters=det(f, "clusters"), R2=det(f, "R2"),
            aviso=det(f, "aviso", ""), coeficientes=[]))
        m["coeficientes"].append(dict(
            predictor=det(f, "predictor"), etiqueta=det(f, "etiqueta"),
            beta=f["valor"], se=det(f, "se"), p=det(f, "p"),
            significativo=bandera(f, "significativo")))
    a.modelos = list(modelos.values())

    # ── CCI, solapamiento, contrastes e ítems
    a.icc = {f["clave"]: f["valor"] for f in por_tipo.get("icc", [])}
    for f in por_tipo.get("solapamiento", []):
        a.solapamiento = dict(det(f, "solapamiento", {}) or {}, n=f["n"])
    a.contrastes = _lista_contrastes(por_tipo.get("contraste", []))
    a.items_pssm = _tabla_items(por_tipo.get("item", []))
    a.subgrupos = _subgrupos(nivel, filas)
    return a


def _det(f, clave, defecto=None):
    return (f.get("detalle") or {}).get(clave, defecto)


def _tabla_bandas(filas: list[dict]) -> pd.DataFrame:
    bandas = []
    for f in filas:
        fila = dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                    pct_alto_o_muy_alto=f["valor"],
                    etiquetas=_det(f, "etiquetas", cat.BANDAS_LABELS))
        for i in range(4):
            pct = _det(f, f"pct_b{i}")
            fila[f"pct_b{i}"] = pct
            fila[f"n_b{i}"] = (round(f["n"] * pct / 100) if pct is not None else None)
        bandas.append(fila)
    return _df(bandas, ["clave", "escala", "n"]
               + [c for i in range(4) for c in (f"n_b{i}", f"pct_b{i}")]
               + ["pct_alto_o_muy_alto", "etiquetas"])


def _tabla_cortes(filas: list[dict]) -> pd.DataFrame:
    return _df([dict(clave=f["clave"], indicador=_det(f, "indicador"),
                     n=f["n"], casos=_det(f, "casos"), pct=f["valor"],
                     ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                     fuente=_det(f, "fuente")) for f in filas],
               ["clave", "indicador", "n", "casos", "pct", "ic_inf", "ic_sup", "fuente"])


def _lista_contrastes(filas: list[dict]) -> list[dict]:
    """El protector viaja en `agrupacion` en el nivel y en `detalle` en los subgrupos."""
    return [dict(resultado=f["clave"], resultado_etiqueta=f["escala"],
                 protector=_det(f, "protector") or f["agrupacion"],
                 protector_etiqueta=_det(f, "protector_etiqueta"),
                 umbral=_det(f, "umbral"),
                 pct_tercil_bajo=f["valor"],
                 pct_tercil_alto=_det(f, "pct_tercil_alto"),
                 n_bajo=_det(f, "n_bajo"), n_alto=_det(f, "n_alto"),
                 razon=_det(f, "razon")) for f in filas]


def _tabla_items(filas: list[dict]) -> pd.DataFrame:
    return _df(sorted([dict(item=f["clave"], M=f["valor"], DE=_det(f, "DE"),
                            n=f["n"]) for f in filas],
                      key=lambda d: d["M"] if d["M"] is not None else 99),
               ["item", "M", "DE", "n"])


TIPOS_SUBGRUPO = ("banda_grupo", "corte_grupo", "contraste_grupo", "item_grupo")


def _subgrupos(nivel: str, filas: list[dict]) -> dict:
    """Rearma {"Colegio": {"LauV": Analisis}, "Grado": {...}} desde las filas «_grupo».

    Cada subgrupo es un `Analisis` con `datos` vacío y solo las tablas que la
    vista comunidad usa, igual que el que produce `pipeline.subanalizar`.
    """
    por_clave: dict[tuple[str, str], dict[str, list[dict]]] = {}
    for f in filas:
        if f["tipo"] not in TIPOS_SUBGRUPO:
            continue
        cubo = por_clave.setdefault((f["agrupacion"], str(f["grupo"])), {})
        cubo.setdefault(f["tipo"], []).append(f)
    salida: dict = {}
    for (columna, grupo), tipos in por_clave.items():
        primera = next(iter(next(iter(tipos.values()))))
        n = int(_det(primera, "n_grupo") or primera["n"])
        s = Analisis(nivel=nivel, n=n, datos=pd.DataFrame(), muestra=dict(n=n))
        s.bandas = _tabla_bandas(tipos.get("banda_grupo", []))
        s.cortes = _tabla_cortes(tipos.get("corte_grupo", []))
        s.contrastes = _lista_contrastes(tipos.get("contraste_grupo", []))
        s.items_pssm = _tabla_items(tipos.get("item_grupo", []))
        salida.setdefault(columna, {})[grupo] = s
    return salida


def cargar_desde_supabase() -> tuple[dict, list, dict | None]:
    """(analisis por nivel, informes, corrida). Vacío si no hay corrida publicada."""
    cli = _cliente()
    corrida, filas = _traer_filas(cli)
    if not corrida or not filas:
        return {}, [], corrida

    por_nivel: dict[str, list[dict]] = {}
    for f in filas:
        por_nivel.setdefault(f["nivel"], []).append(f)

    analisis, informes = {}, []
    for nivel, propias in por_nivel.items():
        analisis[nivel] = _reconstruir(nivel, propias)
        ingesta = [f for f in propias if f["tipo"] == "ingesta"]
        if ingesta:
            informes.append(InformeLeido(
                nivel, (ingesta[0].get("detalle") or {}).get("ingesta", {})))
    return analisis, informes, corrida


AVISO_SIN_DATOS_CRUDOS = (
    "Los resultados vienen de la corrida publicada en la base de datos, no de los "
    "archivos originales: por eso no se puede filtrar por colegio ni por grado. "
    "Las respuestas individuales nunca salen del equipo que procesa los datos.")
