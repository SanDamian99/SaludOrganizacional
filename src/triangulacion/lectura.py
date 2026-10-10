"""
Lectura de la Triangulación 360 publicada — despliegue del equipo y público.

Es la otra mitad de `triangulacion.publicar`. El despliegue privado
(`OBS360_MODO = "investigador"`) no tiene los archivos de los tres actores: lee
la corrida de triangulación que subió la máquina que procesa y rearma, desde
sus filas agregadas, un objeto con la forma de `pipeline.Triangulacion`
(`capa1`, `diadas`, `enlace`, `actores`) que la vista y el ZIP consumen igual.
No hay filas de personas ni díadas: no se puede recalcular nada sobre
individuos. Las figuras se vuelven a dibujar desde las tablas (Bland–Altman
solo con las medias de grupo).

Dos caminos:
  · Equipo (por defecto): el cliente del usuario de carga, de
    `vista_previa.cliente_autenticado()`. Sin `corrida_id`, la última corrida de
    triangulación publicada; con él, esa corrida aunque esté oculta (vista
    previa). Sin ese cliente no hay nada que leer: None.
  · Público (`publico=True`, decisión del usuario del 10 oct 2026): la clave
    anon, con el mismo cliente que la página de Estudiantes
    (`estudiantes.lectura._cliente`). Solo la corrida publicada: la consulta
    exige `publicada = true` y la base (migración 2026-10-10e) solo deja ver a
    anon la última publicada de cada módulo. Nunca importa `vista_previa`.

Es un módulo nuevo: quien lo usa lo importa dentro de un `try` y consulta sus
funciones con `getattr`, y él consulta `vista_previa` igual, así que un módulo
rancio en memoria nunca tumba la página.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

LOG = logging.getLogger(__name__)
ESQUEMA = "obs360"
MODULO = "triangulacion"
NIVEL = "triangulacion"
PREFIJO = "tri_"
TIPO_META = "tri_meta"
FORMATO = 1
TABLAS = ("capa1_diferencias", "capa1_por_grado", "diadas_acuerdo",
          "diadas_acuerdo_concordantes", "diadas_bland_altman", "diadas_no_visto",
          "diadas_apoyo", "diadas_asociaciones", "capa1_municipal", "diadas_informante")
AVISO_PUBLICADO = ("Triangulación leída de la corrida subida por la máquina que procesa: "
                   "solo agregados (n ≥ 10, sin identificadores ni díadas). Desde el 10 "
                   "oct 2026 la corrida publicada también la ve el público. Las figuras "
                   "se dibujan desde esas tablas.")
AVISO_PUBLICO = ("Triangulación leída de la última corrida publicada por el equipo: solo "
                 "agregados (n ≥ 10, sin identificadores ni díadas). Las figuras se "
                 "dibujan desde esas tablas.")


@dataclass
class Capa1Publicada:
    colegios: list = field(default_factory=list)
    grados: list = field(default_factory=list)
    conteos: dict = field(default_factory=dict)     # los exactos no se publican
    diferencias: pd.DataFrame = field(default_factory=pd.DataFrame)
    clasificacion: pd.DataFrame = field(default_factory=pd.DataFrame)
    por_grado: pd.DataFrame = field(default_factory=pd.DataFrame)
    clasificacion_grado: pd.DataFrame = field(default_factory=pd.DataFrame)
    municipal: pd.DataFrame = field(default_factory=pd.DataFrame)   # vacía en corridas viejas


@dataclass
class DiadasPublicadas:
    n: object = 0                 # int ≥ 10, «<10» o 0
    familias: object = 0
    acuerdo: pd.DataFrame = field(default_factory=pd.DataFrame)
    bland_altman: pd.DataFrame = field(default_factory=pd.DataFrame)
    no_visto: pd.DataFrame = field(default_factory=pd.DataFrame)
    apoyo: pd.DataFrame = field(default_factory=pd.DataFrame)
    asociaciones: pd.DataFrame = field(default_factory=pd.DataFrame)
    acuerdo_concordantes: pd.DataFrame = field(default_factory=pd.DataFrame)
    informante: pd.DataFrame = field(default_factory=pd.DataFrame)  # vacía en corridas viejas


@dataclass
class TriangulacionPublicada:
    """Lo mismo que `pipeline.Triangulacion`, rearmado desde la corrida publicada."""
    capa1: Capa1Publicada
    diadas: DiadasPublicadas
    enlace: dict = field(default_factory=dict)      # el informe exacto no se publica
    actores: dict = field(default_factory=dict)     # {actor: int ≥ 10 o «<10»}
    calidad: pd.DataFrame = field(default_factory=pd.DataFrame)
    conteos_tabla: pd.DataFrame = field(default_factory=pd.DataFrame)
    textos: dict = field(default_factory=dict)      # metodologia, version
    corrida: dict = field(default_factory=dict)
    origen: str = "supabase"

    @property
    def n_colegios(self) -> int:
        return len(self.capa1.colegios)


# ── Clientes: usuario de carga (equipo) o clave anon (público) ──────────────
def cliente_publico():
    """El cliente anon de la página de Estudiantes, o None (sin credenciales)."""
    try:
        from src.estudiantes import lectura as lec_est
        return lec_est._cliente()
    except Exception as exc:                               # noqa: BLE001
        LOG.warning("Triangulación [cliente público]: %s.", type(exc).__name__)
        return None


def _cliente(publico: bool):
    return cliente_publico() if publico else cliente()


def cliente():
    """`vista_previa.cliente_autenticado()`, o None. Nunca la clave anon."""
    try:
        from src.core import vista_previa as vp
    except Exception as exc:                               # noqa: BLE001
        LOG.warning("Triangulación [import vista_previa]: %s.", type(exc).__name__)
        return None
    fn = getattr(vp, "cliente_autenticado", None)
    if not callable(fn):
        return None
    try:
        return fn()
    except Exception as exc:                               # noqa: BLE001
        LOG.warning("Triangulación [cliente_autenticado]: %s.", type(exc).__name__)
        return None


def _corridas(cli):
    return cli.postgrest.schema(ESQUEMA).table("corridas")


def id_corrida_publicada(publico: bool = False) -> int | None:
    """Id de la última corrida de triangulación publicada, o None."""
    cli = _cliente(publico)
    if cli is None:
        return None
    filas = (_corridas(cli).select("id").eq("modulo", MODULO).eq("publicada", True)
             .order("creada_en", desc=True).limit(1).execute().data)
    return int(filas[0]["id"]) if filas else None


def _traer(cli, corrida_id: int | None, publico: bool = False
           ) -> tuple[dict | None, list[dict]]:
    consulta = _corridas(cli).select("*").eq("modulo", MODULO)
    if corrida_id is None or publico:
        consulta = consulta.eq("publicada", True)       # el público: solo la publicada
    if corrida_id is not None:
        consulta = consulta.eq("id", corrida_id)
    corridas = consulta.order("creada_en", desc=True).limit(1).execute().data
    if not corridas:
        return None, []
    corrida = corridas[0]
    tabla = cli.postgrest.schema(ESQUEMA).table
    filas, desde, paso = [], 0, 1000
    while True:
        lote = (tabla("resultados").select("*").eq("corrida_id", corrida["id"])
                .eq("nivel", NIVEL).range(desde, desde + paso - 1).execute().data)
        filas.extend(lote)
        if len(lote) < paso:
            break
        desde += paso
    return corrida, filas


def cargar(corrida_id: int | None = None, publico: bool = False
           ) -> TriangulacionPublicada | None:
    """La corrida de triangulación (la publicada, o `corrida_id`), o None.

    Con `publico=True` lee con la clave anon y solo una corrida publicada:
    `corrida_id`, si se da, solo sirve para fijar cuál (la caché de la página).
    """
    cli = _cliente(publico)
    if cli is None:
        return None
    corrida, filas = _traer(cli, corrida_id, publico)
    if corrida is None:
        return None
    return reconstruir(filas, corrida)


# ── Reconstrucción ──────────────────────────────────────────────────────────
def _entero(v):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _df(registros: list[dict], columnas: list | None) -> pd.DataFrame:
    if not columnas and not registros:
        return pd.DataFrame()
    df = pd.DataFrame(registros, columns=columnas or None)
    for c in df.columns[df.dtypes == object]:
        df[c] = df[c].where(df[c].notna(), np.nan)      # null de JSON = NaN, como en local
    return df


def _tabla(nombre: str, filas: list[dict], meta: dict) -> pd.DataFrame:
    piezas = [(int((f.get("detalle") or {}).get("orden", 0)),
               (f.get("detalle") or {}).get("fila") or {})
              for f in filas if f.get("tipo") == PREFIJO + nombre]
    piezas += [(int(s.get("orden", 0)), s.get("fila") or {})
               for s in meta.get("sin_cifra") or [] if s.get("tabla") == nombre]
    piezas.sort(key=lambda p: p[0])
    return _df([p[1] for p in piezas], (meta.get("columnas") or {}).get(nombre))


def reconstruir(filas: list[dict], corrida: dict | None = None
                ) -> TriangulacionPublicada | None:
    filas = [f for f in filas if f.get("nivel") == NIVEL]
    meta_f = next((f for f in filas if f.get("tipo") == TIPO_META), None)
    if meta_f is None:
        return None
    meta = meta_f.get("detalle") or {}
    if _entero(meta.get("formato")) != FORMATO:
        LOG.warning("Triangulación: formato de corrida desconocido; no se muestra.")
        return None
    t = {n: _tabla(n, filas, meta) for n in TABLAS}
    cols_cl = meta.get("columnas_clasificacion") or None
    capa1 = Capa1Publicada(
        colegios=list(meta.get("colegios") or []), grados=list(meta.get("grados") or []),
        diferencias=t["capa1_diferencias"], por_grado=t["capa1_por_grado"],
        clasificacion=_df(meta.get("clasificacion") or [], cols_cl),
        clasificacion_grado=_df(meta.get("clasificacion_grado") or [], cols_cl),
        municipal=t["capa1_municipal"])
    diadas = DiadasPublicadas(
        n=_entero(meta.get("diadas_n", 0)), familias=_entero(meta.get("diadas_familias", 0)),
        acuerdo=t["diadas_acuerdo"], bland_altman=t["diadas_bland_altman"],
        no_visto=t["diadas_no_visto"], apoyo=t["diadas_apoyo"],
        asociaciones=t["diadas_asociaciones"],
        acuerdo_concordantes=t["diadas_acuerdo_concordantes"],
        informante=t["diadas_informante"])
    return TriangulacionPublicada(
        capa1=capa1, diadas=diadas,
        actores={k: _entero(v) for k, v in (meta.get("actores") or {}).items()},
        calidad=_df(meta.get("calidad") or [], ["indicador", "valor"]),
        conteos_tabla=_df(meta.get("conteos_actores") or [], None),
        textos=dict(metodologia=meta.get("metodologia") or "",
                    version=meta.get("version") or ""),
        corrida=dict(corrida or {}))
