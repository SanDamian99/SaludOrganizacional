"""
Lectura de la corrida publicada de Cuidadores 360 — Observatorio 360 (fase 4b).

Es la otra mitad de `cuidadores.publicar`. La usan el despliegue público
(vista de comunidad) y el despliegue del equipo (vista de investigadores sin
archivos): rearma, desde las filas agregadas, un objeto con la forma de
`AnalisisCuidadores` (`cuidador`, `nino`, `informe`, `marcos`), con `datos`
vacío y sin nada por ola. No puede recalcular nada sobre individuos: no hay
filas de personas.

Solo lee la ÚLTIMA corrida publicada del módulo «cuidadores» (filtro por
`modulo`, y la política RLS solo deja ver la última publicada de cada módulo),
con la clave `anon`, que no escribe. Nunca toca la de estudiantes.

Es un módulo nuevo y liviano: no importa ingesta, pipeline ni puntuación, así
que puede cargarse en el despliegue público.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pandas as pd

from src.cuidadores import alertas
from src.cuidadores import catalog as cat
from src.estudiantes.pipeline import Analisis

ESQUEMA = "obs360"
MODULO = cat.MODULO
NIVEL = "cuidadores"
TIPOS_SUBGRUPO = ("banda_grupo", "corte_grupo")

# Campos del informe de la carga con su valor si la corrida no los trae.
INFORME_POR_DEFECTO = dict(
    filas_archivo=0, sin_consentimiento=0, respuestas_validas=0, por_ola={}, por_quien={},
    cuidadores_distintos=0, respuestas_repetidas_cuidador=0, cuidadores_en_dos_olas=0,
    filas_nino=0, hijo2=0, ninos_sin_nombre=0, mismo_nino_misma_respuesta=0,
    mismo_nino_otro_cuidador=0, mismo_nino_entre_olas=0, ninos_unicos=0,
    edad_no_numerica=0, edad_fuera_de_rango=0, curso_sin_resolver=0, grados={},
    colegios_cuidador={}, colegios_nino={}, colegio_no_reconocido=0,
    respuestas_columna6_pss=0, etiquetas_no_mapeadas={}, cobertura_ari={},
    faltantes_por_bloque={}, enunciados={}, avisos=[])


@dataclass
class CuidadoresPublicados:
    """Lo mismo que `pipeline.AnalisisCuidadores`, rearmado desde la corrida publicada."""
    cuidador: Analisis
    nino: Analisis
    informe: object
    corrida: dict = field(default_factory=dict)
    ola: str | None = None
    olas: list = field(default_factory=list)
    items_apq: pd.DataFrame = field(default_factory=pd.DataFrame)
    items_estres: pd.DataFrame = field(default_factory=pd.DataFrame)
    flujo_ola: dict = field(default_factory=dict)
    origen: str = "supabase"

    @property
    def marcos(self) -> dict:
        return {cat.MARCO_CUIDADOR: self.cuidador, cat.MARCO_NINO: self.nino}


# ── Conexión (la misma de estudiantes: clave anon de lectura) ───────────────
def credenciales() -> tuple[str | None, str | None]:
    from src.estudiantes import lectura as lec_est
    return lec_est.credenciales()


def disponible() -> bool:
    url, key = credenciales()
    return bool(url and key)


def _cliente():
    from supabase import create_client
    url, key = credenciales()
    if not (url and key):
        raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_KEY.")
    return create_client(url, key)


def id_corrida_vigente(cli=None) -> int | None:
    """Id de la corrida de cuidadores publicada más reciente, o None."""
    cli = cli or _cliente()
    filas = (cli.postgrest.schema(ESQUEMA).table("corridas").select("id")
             .eq("modulo", MODULO).order("creada_en", desc=True).limit(1).execute().data)
    return int(filas[0]["id"]) if filas else None


def _traer_filas(cli) -> tuple[dict | None, list[dict]]:
    tabla = cli.postgrest.schema(ESQUEMA)
    corridas = (tabla.table("corridas").select("*").eq("modulo", MODULO)
                .order("creada_en", desc=True).limit(1).execute().data)
    if not corridas:
        return None, []
    corrida = corridas[0]
    filas, desde, paso = [], 0, 1000
    while True:
        lote = (tabla.table("resultados").select("*").eq("corrida_id", corrida["id"])
                .range(desde, desde + paso - 1).execute().data)
        filas.extend(lote)
        if len(lote) < paso:
            break
        desde += paso
    return corrida, filas


# ── Reconstrucción ──────────────────────────────────────────────────────────
def _det(f: dict, clave: str, defecto=None):
    return (f.get("detalle") or {}).get(clave, defecto)


def _df(filas: list[dict], columnas: list[str]) -> pd.DataFrame:
    return pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame(columns=columnas)


def _bandas(filas: list[dict]) -> pd.DataFrame:
    return _df([dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                     **{f"pct_b{i}": _det(f, f"pct_b{i}") for i in range(4)},
                     pct_alto_o_muy_alto=f["valor"], etiquetas=_det(f, "etiquetas", []))
                for f in filas],
               ["clave", "escala", "n", "pct_b0", "pct_b1", "pct_b2", "pct_b3",
                "pct_alto_o_muy_alto", "etiquetas"])


def _cortes(filas: list[dict]) -> pd.DataFrame:
    # Sin `casos`: nunca se publican. Un `pct` vacío es una cifra suprimida.
    return _df([dict(clave=f["clave"], indicador=_det(f, "indicador"), n=f["n"],
                     pct=f["valor"], ic_inf=f["ic_inf"], ic_sup=f["ic_sup"],
                     fuente=_det(f, "fuente")) for f in filas],
               ["clave", "indicador", "n", "pct", "ic_inf", "ic_sup", "fuente"])


def _subgrupos(marco: str, filas: list[dict]) -> dict:
    por_grupo: dict[tuple[str, str], dict[str, list[dict]]] = {}
    for f in filas:
        if f["tipo"] in TIPOS_SUBGRUPO:
            cubo = por_grupo.setdefault((f["agrupacion"], str(f["grupo"])), {})
            cubo.setdefault(f["tipo"], []).append(f)
    salida: dict = {}
    for (columna, grupo), tipos in por_grupo.items():
        primera = next(iter(next(iter(tipos.values()))))
        n = int(_det(primera, "n_grupo") or primera["n"])
        s = Analisis(nivel=marco, n=n, datos=pd.DataFrame(), muestra=dict(n=n))
        s.bandas = _bandas(tipos.get("banda_grupo", []))
        s.cortes = _cortes(tipos.get("corte_grupo", []))
        salida.setdefault(columna, {})[grupo] = s
    return salida


def _alertas(filas: list[dict]) -> pd.DataFrame:
    salida = []
    for f in filas:
        if f["tipo"] not in ("alerta", "alerta_grupo"):
            continue
        total = f["tipo"] == "alerta"
        if not total and f["clave"] in alertas.SOLO_TOTAL:
            continue                      # nunca por grupo, aunque llegara
        salida.append(dict(alerta=f["clave"],
                           agrupacion=alertas.TOTAL if total else f["agrupacion"],
                           grupo=alertas.TODOS if total else str(f["grupo"]),
                           n=int(f["n"]), pct=f["valor"], ic_inf=f["ic_inf"],
                           ic_sup=f["ic_sup"],
                           estado=_det(f, "estado", alertas.SIN_ESTADO) or alertas.SIN_ESTADO))
    return alertas.ordenar(_df(salida, alertas.COLUMNAS_TABLA))


def _marco(marco: str, filas: list[dict]) -> Analisis:
    por_tipo: dict[str, list[dict]] = {}
    for f in filas:
        por_tipo.setdefault(f["tipo"], []).append(f)
    muestra, enmascarados, escalas, avisos = {}, {}, [], []
    for f in por_tipo.get("muestra", []):
        muestra = _det(f, "muestra", {}) or {}
        enmascarados = _det(f, "enmascarados", {}) or {}
        escalas = list(_det(f, "escalas", []) or [])
        avisos = list(_det(f, "avisos", []) or [])
    a = Analisis(nivel=marco, n=int(muestra.get("n") or 0), datos=pd.DataFrame(),
                 muestra=muestra, enmascarados=enmascarados, escalas=escalas, avisos=avisos)
    desc, fiab = [], []
    for f in por_tipo.get("descriptivo", []):
        desc.append(dict(clave=f["clave"], escala=f["escala"], n=f["n"], M=f["valor"],
                         DE=_det(f, "DE"), Mdn=_det(f, "Mdn"), rango=_det(f, "rango"),
                         pct_faltante=_det(f, "pct_faltante"), P25=_det(f, "P25"),
                         P75=_det(f, "P75"), direccion=_det(f, "direccion"),
                         fuente=_det(f, "fuente")))
        if _det(f, "alpha") is not None:
            fiab.append(dict(clave=f["clave"], escala=f["escala"],
                             n_items=_det(f, "n_items"), n=f["n"], alpha=_det(f, "alpha"),
                             ic_inf=_det(f, "alpha_ic_inf"), ic_sup=_det(f, "alpha_ic_sup")))
    orden = {p.clave: i for i, p in enumerate(cat.PUNTUACIONES)}
    a.descriptivos = _df(sorted(desc, key=lambda d: orden.get(d["clave"], 99)),
                         ["clave", "escala", "n", "M", "DE", "Mdn", "rango", "pct_faltante",
                          "P25", "P75", "direccion", "fuente"])
    a.fiabilidad = _df(fiab, ["clave", "escala", "n_items", "n", "alpha", "ic_inf", "ic_sup"])
    a.bandas = _bandas(por_tipo.get("banda", []))
    a.cortes = _cortes(por_tipo.get("corte", []))
    a.terciles = _df([dict(clave=f["clave"], escala=f["escala"], n=f["n"],
                           corte_bajo=_det(f, "corte_bajo"), corte_alto=_det(f, "corte_alto"),
                           nota=_det(f, "nota")) for f in por_tipo.get("tercil", [])],
                     ["clave", "escala", "n", "corte_bajo", "corte_alto", "nota"])
    a.correlaciones = _df([dict(a=f["clave"], b=_det(f, "variable_b"), etiqueta_a=f["escala"],
                                etiqueta_b=_det(f, "etiqueta_b"), rho=f["valor"],
                                ic_inf=f["ic_inf"], ic_sup=f["ic_sup"], p=_det(f, "p"),
                                n=f["n"], q_bh=_det(f, "q_bh"),
                                significativa=bool(_det(f, "significativa", False)))
                           for f in por_tipo.get("correlacion", [])],
                          ["a", "b", "etiqueta_a", "etiqueta_b", "rho", "ic_inf", "ic_sup",
                           "p", "n", "q_bh", "significativa"])
    grupos = por_tipo.get("grupo", [])
    for agrupacion, destino in (("Grado", "por_grado"), ("Colegio", "por_colegio")):
        acumulado: dict[str, dict] = {}
        for f in [g for g in grupos if g["agrupacion"] == agrupacion]:
            fila = acumulado.setdefault(f["clave"], dict(
                clave=f["clave"], escala=f["escala"], p=_det(f, "p"), eta2=_det(f, "eta2"),
                q_bh=_det(f, "q_bh"), n=0))
            fila[f"M·{f['grupo']}"] = f["valor"]
            fila[f"n·{f['grupo']}"] = f["n"]
            fila["n"] += int(f["n"] or 0)
        setattr(a, destino, pd.DataFrame(list(acumulado.values())))
    a.icc = {f["clave"]: f["valor"] for f in por_tipo.get("icc", [])}
    a.subgrupos = _subgrupos(marco, filas)
    a.alertas = _alertas(filas) if marco == cat.MARCO_CUIDADOR else alertas.vacia()
    return a


def informe_desde(filas: list[dict]) -> SimpleNamespace:
    """El informe de la carga, con todos los campos (los conteos pequeños llegan «<10»)."""
    datos = dict(INFORME_POR_DEFECTO)
    for f in filas:
        if f["tipo"] == "ingesta":
            datos.update(_det(f, "ingesta", {}) or {})
    datos["origen"] = "supabase"
    return SimpleNamespace(**datos)


def reconstruir(filas: list[dict], corrida: dict | None = None) -> CuidadoresPublicados | None:
    """Objeto con la forma de `AnalisisCuidadores`; None si no hay filas de cuidadores."""
    propias = [f for f in filas if f.get("nivel") == NIVEL]
    por_marco: dict[str, list[dict]] = {m: [] for m in cat.NOMBRES_MARCO}
    for f in propias:
        marco = _det(f, "marco")
        if marco in por_marco:
            por_marco[marco].append(f)
    if not any(por_marco.values()):
        return None
    return CuidadoresPublicados(
        cuidador=_marco(cat.MARCO_CUIDADOR, por_marco[cat.MARCO_CUIDADOR]),
        nino=_marco(cat.MARCO_NINO, por_marco[cat.MARCO_NINO]),
        informe=informe_desde(propias), corrida=dict(corrida or {}))


def cargar_desde_supabase(cli=None) -> tuple[CuidadoresPublicados | None, dict | None]:
    """(cuidadores publicados, corrida). (None, corrida o None) si no hay nada que leer."""
    cli = cli or _cliente()
    corrida, filas = _traer_filas(cli)
    if not corrida or not filas:
        return None, corrida
    return reconstruir(filas, corrida), corrida


AVISO_PUBLICADO = ("Las cifras vienen de la corrida publicada de cuidadores: solo agregados de "
                   "grupos con 10 o más cuidadores distintos y de todas las olas.")
