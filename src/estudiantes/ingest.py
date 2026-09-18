"""
Ingesta y limpieza del dataset de estudiantes — Observatorio 360.

Entrada: una exportación de Google Forms (CSV o XLSX) de cualquiera de los dos
formularios; el enunciado completo de cada ítem viene como encabezado.

Salida: DataFrame con una fila por estudiante, columnas normalizadas
(SDQ1..SDQ25, ARI1..ARI7, …) y un informe de ingesta trazable.

PRIVACIDAD — reglas que este módulo garantiza:
  · El formulario trae «Mi nombre completo es:». El ID se deriva como hash del
    nombre normalizado y **la columna de nombre no existe en la salida**.
  · Ninguna función de este módulo devuelve, registra o escribe nombres.

Las reglas de exclusión están documentadas en
docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md §8.5 y verificadas contra
docs/instrumentos/fixtures/resultados_preliminares_estudiantes.json
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.estudiantes import catalog as cat

# ── Normalización de texto ──────────────────────────────────────────────────
def norm_txt(s) -> str:
    """Minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.replace("\xa0", " ").lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def _hash_id(nombre_normalizado: str) -> str:
    return "E" + hashlib.sha1(nombre_normalizado.encode()).hexdigest()[:8]


# ── Colegios: 14 etiquetas crudas → 6 códigos + sede ────────────────────────
_COLEGIOS = [
    (("laura", "vicuna"), "LauV", "Laura Vicuña"),
    (("joaquin",), "JJC", "José Joaquín Casas"),
    (("balsa",), "LaBalsa", "La Balsa"),
    (("josemaria",), "SJMEB", "San Josemaría Escrivá de Balaguer"),
    (("escriva",), "SJMEB", "San Josemaría Escrivá de Balaguer"),
    (("cerca",), "CdP", "Cerca de Piedra"),
    (("diosa",), "DiosCh", "Diosa Chía"),
    (("bojaca",), "Bojacá", "Bojacá"),
    (("fagua",), "Fagua", "Fagua"),
    (("fonquet",), "Fonquetá", "Fonquetá"),
    (("fusca",), "Fusca", "Fusca"),
    (("tiquiza",), "Tiquiza", "Tiquiza"),
]
_SEDES = ["samaria", "principal", "preescolar", "calahorra", "polideportivo", "tiquiza",
          "mercedes", "santa lucia"]


def normalizar_colegio(raw) -> tuple[str, str, str]:
    """(código, nombre legible, sede). ('OTRO', texto crudo, '') si no se reconoce."""
    s = norm_txt(raw)
    if not s:
        return "SIN_DATO", "Sin dato", ""
    sede = ""
    for k in _SEDES:
        if k in s:
            sede = {"samaria": "Samaria", "principal": "Principal", "preescolar": "Preescolar",
                    "calahorra": "Mercedes de Calahorra", "mercedes": "Mercedes de Calahorra",
                    "polideportivo": "Polideportivo", "tiquiza": "Tiquiza",
                    "santa lucia": "Santa Lucía"}[k]
            break
    for claves, codigo, nombre in _COLEGIOS:
        if any(c in s for c in claves):
            return codigo, nombre, sede
    return "OTRO", str(raw).strip(), sede


# ── Detección de bloques de ítems en los encabezados crudos ─────────────────
# Cada escala se localiza por el prefijo con el que Google Forms agrupó la matriz.
_PREFIJOS = {
    "SDQ": "sdq",
    "ARI": "ari",
    "RCADS": "rcads",
    "ERQ": "erq ca",     # «ERQ-CA [...]» → normalizado «erq ca ...»
    "MSPSS": "mspss",
    "TD": "toma de decisiones",
}
# El PSSM llegó sin prefijo: son 18 preguntas sueltas. Se ancla en la primera.
_PSSM_ANCLA = "siento que soy parte de mi colegio"

_IDENT = {
    "nombre": ("mi nombre completo es",),
    "edad": ("tengo",),
    "sexo": ("mi sexo es",),
    "grado": ("estoy en grado",),
    "colegio": ("mi colegio es",),
    "ts": ("marca temporal", "timestamp"),
    "consent": ("quieres aportar",),
}


@dataclass
class InformeIngesta:
    nivel: str = ""
    filas_archivo: int = 0
    sin_consentimiento: int = 0
    excluidas_prueba: int = 0
    excluidas_colegio_unico: int = 0
    duplicados_eliminados: int = 0
    filas_validas: int = 0
    escalas_detectadas: list[str] = field(default_factory=list)
    escalas_ausentes: list[str] = field(default_factory=list)
    erq_invalidado: int = 0
    colegios: dict = field(default_factory=dict)
    colegios_enmascarados: list[str] = field(default_factory=list)
    etiquetas_no_mapeadas: dict = field(default_factory=dict)
    faltantes_por_escala: dict = field(default_factory=dict)
    edades_fuera_de_rango: dict = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def es_dataset_estudiantes(df: pd.DataFrame) -> bool:
    """True si el DataFrame parece una exportación de los formularios de estudiantes."""
    cols = [norm_txt(c) for c in df.columns]
    tiene_sdq = sum(c.startswith("sdq") for c in cols) >= 20
    tiene_ident = any("mi nombre completo es" in c for c in cols) or \
                  any("mi colegio es" in c for c in cols)
    return tiene_sdq and tiene_ident


def _localizar(cols_norm: list[str], claves: tuple[str, ...]) -> int | None:
    for i, c in enumerate(cols_norm):
        if any(c.startswith(k) or k in c for k in claves):
            return i
    return None


def _bloque(cols_norm: list[str], prefijo: str) -> list[int]:
    return [i for i, c in enumerate(cols_norm) if c.startswith(prefijo)]


def _mapear_bloque(df: pd.DataFrame, idx: list[int], escala: cat.Escala,
                   informe: InformeIngesta) -> pd.DataFrame:
    """Renombra a PREFIJO1..N y convierte etiquetas a números."""
    out = {}
    no_mapeadas = set()
    for k, col_i in enumerate(idx, start=1):
        serie = df.iloc[:, col_i]
        nombre = f"{escala.prefijo}{k}"
        if escala.mapa and serie.dtype == object:
            conv = serie.map(lambda x: escala.mapa.get(norm_txt(x)) if pd.notna(x) else np.nan)
            malas = serie[conv.isna() & serie.notna()].unique()
            no_mapeadas.update(str(m) for m in malas)
            out[nombre] = conv
        else:
            out[nombre] = pd.to_numeric(serie, errors="coerce")
    if no_mapeadas:
        informe.etiquetas_no_mapeadas[escala.key] = sorted(no_mapeadas)[:10]
    res = pd.DataFrame(out, index=df.index)
    fuera = ((res < escala.valor_min) | (res > escala.valor_max)).sum().sum()
    if fuera:
        informe.avisos.append(
            f"{escala.key}: {int(fuera)} valores fuera del rango "
            f"{escala.valor_min}-{escala.valor_max}; se marcan como faltantes.")
        res = res.mask((res < escala.valor_min) | (res > escala.valor_max))
    return res


def cargar(ruta_o_df, nivel: str | None = None) -> tuple[pd.DataFrame, InformeIngesta]:
    """Lee un formulario de estudiantes y devuelve (DataFrame limpio, informe).

    `nivel` fuerza 'secundaria' o 'primaria'; por defecto se infiere de la
    presencia del bloque RCADS (solo lo respondió secundaria).
    """
    if isinstance(ruta_o_df, pd.DataFrame):
        raw = ruta_o_df.copy()
    else:
        ruta = str(ruta_o_df)
        raw = pd.read_excel(ruta) if ruta.lower().endswith((".xlsx", ".xls")) \
            else pd.read_csv(ruta)

    inf = InformeIngesta(filas_archivo=len(raw))
    cols_norm = [norm_txt(c) for c in raw.columns]

    # ── identificación
    idx_ident = {k: _localizar(cols_norm, v) for k, v in _IDENT.items()}
    faltan = [k for k in ("edad", "sexo", "grado", "colegio") if idx_ident[k] is None]
    if faltan:
        raise ValueError(f"No se encontraron las columnas de identificación: {faltan}. "
                         "¿Es una exportación de los formularios de estudiantes?")

    d = pd.DataFrame(index=raw.index)
    if idx_ident["ts"] is not None:
        d["ts"] = pd.to_datetime(raw.iloc[:, idx_ident["ts"]], dayfirst=True, errors="coerce")
    d["Edad"] = pd.to_numeric(
        raw.iloc[:, idx_ident["edad"]].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    d["Sexo"] = raw.iloc[:, idx_ident["sexo"]].astype(str).str.strip()
    d["Grado"] = raw.iloc[:, idx_ident["grado"]].astype(str).str.strip()
    col_raw = raw.iloc[:, idx_ident["colegio"]]
    norm_col = col_raw.map(normalizar_colegio)
    d["Colegio"] = [x[0] for x in norm_col]
    d["Colegio_nombre"] = [x[1] for x in norm_col]
    d["Sede"] = [x[2] for x in norm_col]

    # ID por hash; el nombre nunca sale de esta función
    if idx_ident["nombre"] is not None:
        _nombre_norm = raw.iloc[:, idx_ident["nombre"]].map(norm_txt)
        d["ID"] = _nombre_norm.map(_hash_id)
        _clave_dedupe = _nombre_norm
    else:
        d["ID"] = [f"E{i:05d}" for i in range(len(raw))]
        _clave_dedupe = pd.Series([f"__{i}" for i in range(len(raw))], index=raw.index)

    # ── consentimiento
    if idx_ident["consent"] is not None:
        consent = raw.iloc[:, idx_ident["consent"]].astype(str).map(
            lambda x: norm_txt(x).startswith("si"))
        inf.sin_consentimiento = int((~consent).sum())
    else:
        consent = pd.Series(True, index=raw.index)
        inf.avisos.append("No se encontró la pregunta de consentimiento; se asume otorgado.")

    # ── bloques de ítems
    bloques: dict[str, pd.DataFrame] = {}
    for key, prefijo in _PREFIJOS.items():
        escala = cat.ESCALAS_POR_KEY[key]
        idx = _bloque(cols_norm, prefijo)
        if not idx:
            inf.escalas_ausentes.append(key)
            continue
        if len(idx) != escala.n_items:
            inf.avisos.append(f"{key}: se esperaban {escala.n_items} ítems y se encontraron "
                              f"{len(idx)}. Se usan los {min(len(idx), escala.n_items)} primeros.")
            idx = idx[:escala.n_items]
        bloques[key] = _mapear_bloque(raw, idx, escala, inf)
        inf.escalas_detectadas.append(key)

    # PSSM: 18 columnas consecutivas desde el ancla
    i_pssm = _localizar(cols_norm, (_PSSM_ANCLA,))
    if i_pssm is not None:
        idx = list(range(i_pssm, min(i_pssm + cat.PSSM.n_items, len(cols_norm))))
        bloques["PSSM"] = _mapear_bloque(raw, idx, cat.PSSM, inf)
        inf.escalas_detectadas.append("PSSM")
    else:
        inf.escalas_ausentes.append("PSSM")

    d = pd.concat([d] + list(bloques.values()), axis=1)

    # ── nivel educativo
    inf.nivel = nivel or (cat.NIVEL_SECUNDARIA if "RCADS" in bloques else cat.NIVEL_PRIMARIA)
    d["nivel"] = inf.nivel

    # ── exclusiones
    d = d[consent].copy()
    _clave_dedupe = _clave_dedupe[consent]

    # (a) filas de prueba: la misma persona el mismo día en colegios distintos
    if "ts" in d.columns:
        d["_fecha"] = d["ts"].dt.date
        g = d.assign(_k=_clave_dedupe).groupby(["_k", "_fecha"])["Colegio"].transform("nunique")
        prueba = g > 1
        inf.excluidas_prueba = int(prueba.sum())
        d = d[~prueba].copy()
        _clave_dedupe = _clave_dedupe[~prueba]

    # (b) colegios con una sola respuesta. Se recalcula DESPUÉS de quitar las
    # filas de prueba, porque quitarlas puede dejar a un colegio con una sola.
    for _ in range(3):
        vc = d["Colegio"].value_counts()
        solos = d["Colegio"].map(vc) <= 1
        if not solos.any():
            break
        inf.excluidas_colegio_unico += int(solos.sum())
        d = d[~solos].copy()
        _clave_dedupe = _clave_dedupe[~solos]

    # (c) duplicados dentro de este formulario: se conserva el primer envío
    if "ts" in d.columns:
        orden = d["ts"].fillna(pd.Timestamp.min).argsort()
        d = d.iloc[orden]
        _clave_dedupe = _clave_dedupe.iloc[orden]
    dup = _clave_dedupe.duplicated(keep="first")
    inf.duplicados_eliminados = int(dup.sum())
    d = d[~dup].copy()

    # ── invalidación del ERQ-CA (artefacto de aplicación)
    if "ERQ" in bloques:
        cols_erq = cat.ERQ.columnas
        todos_min = (d[cols_erq] == cat.ERQ.valor_min).all(axis=1)
        inf.erq_invalidado = int(todos_min.sum())
        if inf.erq_invalidado:
            d.loc[todos_min, cols_erq] = np.nan
            inf.avisos.append(
                f"ERQ-CA: {inf.erq_invalidado} respuestas con «{cat.ERQ.valor_min}» en los 10 "
                "ítems se marcan como faltantes. Reevaluación y supresión son estrategias "
                "opuestas, así que responder el mínimo en todo es implausible; es un artefacto "
                "de aplicación, no un resultado.")

    # ── edad fuera del rango validado
    for key in inf.escalas_detectadas:
        e = cat.ESCALAS_POR_KEY[key]
        lo, hi = e.edad_validada
        fuera = int(((d["Edad"] < lo) | (d["Edad"] > hi)).sum())
        if fuera:
            inf.edades_fuera_de_rango[key] = fuera

    # ── faltantes por escala
    for key in inf.escalas_detectadas:
        cols = cat.ESCALAS_POR_KEY[key].columnas
        cols = [c for c in cols if c in d.columns]
        inf.faltantes_por_escala[key] = round(float(d[cols].isna().mean().mean() * 100), 2)

    vc = d["Colegio"].value_counts()
    inf.colegios = vc.to_dict()
    inf.colegios_enmascarados = vc[vc < cat.MIN_GROUP_N].index.tolist()
    inf.filas_validas = len(d)

    if inf.nivel == cat.NIVEL_PRIMARIA:
        inf.avisos.append(cat.AVISO_PRIMARIA)

    d = d.drop(columns=[c for c in ("_fecha",) if c in d.columns])
    # Garantía final: ninguna columna con texto libre de identificación
    prohibidas = [c for c in d.columns if "nombre" in c.lower() and c != "Colegio_nombre"]
    d = d.drop(columns=prohibidas)
    return d.reset_index(drop=True), inf


def cargar_varios(rutas: list, niveles: list[str] | None = None
                  ) -> tuple[pd.DataFrame, list[InformeIngesta]]:
    """Carga los formularios, los concatena y elimina duplicados ENTRE archivos.

    Un estudiante puede haber respondido los dos formularios; deduplicar dentro
    de cada archivo no lo detecta. El cruce se hace sobre el ID (hash del
    nombre), que es determinista, así que no hace falta el nombre para esto.
    """
    dfs, infs = [], []
    for i, r in enumerate(rutas):
        nivel = niveles[i] if niveles and i < len(niveles) else None
        d, inf = cargar(r, nivel=nivel)
        dfs.append(d)
        infs.append(inf)
    todo = pd.concat(dfs, ignore_index=True)
    if "ts" in todo.columns:
        todo = todo.sort_values("ts", na_position="last")
    dup = todo["ID"].duplicated(keep="first")
    n_dup = int(dup.sum())
    if n_dup:
        eliminadas = todo[dup]
        for inf in infs:
            propios = int((eliminadas["nivel"] == inf.nivel).sum())
            if propios:
                inf.duplicados_eliminados += propios
                inf.filas_validas -= propios
                inf.avisos.append(
                    f"{propios} respuesta(s) eliminadas por aparecer también en el otro "
                    "formulario; se conserva el primer envío.")
        todo = todo[~dup]
    # los conteos por colegio se recalculan sobre el resultado final
    for inf in infs:
        vc = todo.loc[todo["nivel"] == inf.nivel, "Colegio"].value_counts()
        inf.colegios = vc.to_dict()
        inf.colegios_enmascarados = vc[vc < cat.MIN_GROUP_N].index.tolist()
    return todo.reset_index(drop=True), infs
