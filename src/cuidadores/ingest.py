"""
Ingesta del formulario «Cuidando al Cuidador» — Observatorio 360.

Entrada: la exportación de Google Forms (xlsx o csv), 209 columnas, leída por
posición (catalog.COL y los bloques) y verificada con `catalog.VERIFICAR`.

Salida (`Carga`):
  · `respuestas`: una fila por respuesta con consentimiento, con el seudónimo
    del cuidador (`ID_cuidador`), la ola, quién responde, el colegio y el grado
    de su primer hijo, el contexto y los ítems del adulto ya en número.
  · `ninos`: una fila por niño reportado (hijo 1 y, si lo hay, hijo 2), con su
    seudónimo (`ID_nino`), el del cuidador, edad, sexo, colegio, grado y los
    ítems del SDQ y del ARI de padres en número.
  · `informe`: conteos trazables de la carga, nunca valores individuales.

`deduplicar(carga, ola)` deja un cuidador por `ID_cuidador` (la respuesta más
reciente) y un niño por `ID_nino` (la ola más reciente; luego mamá, papá,
otro; luego el primer envío; dentro de un envío, el hijo 1 antes que el 2).

PRIVACIDAD — reglas que este módulo garantiza:
  · Los nombres (posiciones 3, 4 y 147) se leen solo para el seudónimo HMAC con
    clave local (`core.seudonimo`) y nunca se copian a ninguna salida.
  · El teléfono (179) y el nombre de un tercer hijo (208) no se leen.
  · Un colegio escrito a mano que no se reconoce queda como «OTRO» / «Otro
    colegio»: su texto libre no viaja.
  · Ninguna función devuelve, registra ni imprime nombres o filas.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.core import seudonimo as seud
from src.core.colegios import normalizar as normalizar_colegio
from src.core.texto import norm_txt
from src.cuidadores import catalog as cat

OLA_COLUMNA = "Ola"


class FormatoInesperado(ValueError):
    """La exportación no tiene las preguntas donde el catálogo las espera."""


@dataclass
class InformeCuidadores:
    filas_archivo: int = 0
    sin_consentimiento: int = 0
    respuestas_validas: int = 0
    por_ola: dict = field(default_factory=dict)
    por_quien: dict = field(default_factory=dict)
    # cuidadores
    cuidadores_distintos: int = 0
    respuestas_repetidas_cuidador: int = 0     # quitadas: el mismo cuidador más de una vez
    cuidadores_en_dos_olas: int = 0
    # niños
    filas_nino: int = 0
    hijo2: int = 0
    ninos_sin_nombre: int = 0
    mismo_nino_misma_respuesta: int = 0        # hijo 2 = hijo 1 en el mismo envío
    mismo_nino_otro_cuidador: int = 0
    mismo_nino_entre_olas: int = 0
    ninos_unicos: int = 0
    # calidad
    edad_no_numerica: int = 0
    edad_fuera_de_rango: int = 0
    curso_sin_resolver: int = 0
    grados: dict = field(default_factory=dict)          # «Cuarto»/«Fuera…»/«Sin dato» → n
    colegios_cuidador: dict = field(default_factory=dict)
    colegios_nino: dict = field(default_factory=dict)
    colegio_no_reconocido: int = 0
    respuestas_columna6_pss: int = 0
    etiquetas_no_mapeadas: dict = field(default_factory=dict)   # bloque → nº de respuestas
    cobertura_ari: dict = field(default_factory=dict)            # «hijo 1»/«hijo 2» → n
    faltantes_por_bloque: dict = field(default_factory=dict)
    enunciados: dict = field(default_factory=dict)   # bloque → textos de los ítems (encabezados)
    avisos: list = field(default_factory=list)

    def como_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Carga:
    respuestas: pd.DataFrame
    ninos: pd.DataFrame
    informe: InformeCuidadores


# ── lectura ─────────────────────────────────────────────────────────────────
def leer(ruta) -> pd.DataFrame:
    """Lee la exportación como texto (las etiquetas se convierten aquí, no en pandas)."""
    ruta = str(ruta)
    if ruta.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(ruta, dtype=str)
    return pd.read_csv(ruta, dtype=str)


def verificar_formato(columnas) -> None:
    """Comprueba que cada posición clave tiene la pregunta esperada."""
    columnas = list(columnas)
    if len(columnas) < cat.N_COLUMNAS - 9:
        raise FormatoInesperado(
            f"Se esperaban {cat.N_COLUMNAS} columnas y llegaron {len(columnas)}. "
            "¿Es la exportación de «Cuidando al Cuidador»?")
    for pos, fragmento in cat.VERIFICAR.items():
        texto = norm_txt(columnas[pos]) if pos < len(columnas) else ""
        if fragmento not in texto:
            raise FormatoInesperado(
                f"En la columna {pos} se esperaba «{fragmento}». Revise que la "
                "exportación no haya cambiado de orden.")


def enunciado(columna) -> str:
    """Texto del ítem en el encabezado: lo que va entre corchetes, o el encabezado entero."""
    texto = str(columna).strip()
    m = re.search(r"\[(.+?)\]", texto)
    return (m.group(1) if m else texto).strip()


def es_formulario_cuidadores(df: pd.DataFrame) -> bool:
    try:
        verificar_formato(df.columns)
        return True
    except FormatoInesperado:
        return False


# ── conversiones ────────────────────────────────────────────────────────────
def mapear_bloque(raw: pd.DataFrame, bloque: cat.Bloque, informe: InformeCuidadores,
                  etiqueta: str | None = None) -> pd.DataFrame:
    """Columnas PREFIJO1..N en número, por el texto de cada respuesta."""
    etiqueta = etiqueta or bloque.key
    out, no_mapeadas, declaradas = {}, 0, 0
    for i, (pos, mapa) in enumerate(zip(bloque.posiciones, bloque.mapas), start=1):
        texto = raw.iloc[:, pos].map(norm_txt)
        valor = texto.map(lambda t: mapa.get(t, np.nan) if t else np.nan).astype(float)
        sin = (texto != "") & valor.isna()
        declaradas += int((sin & texto.isin(bloque.faltantes)).sum())
        no_mapeadas += int((sin & ~texto.isin(bloque.faltantes)).sum())
        out[f"{bloque.prefijo}{i}"] = valor
    if no_mapeadas:
        informe.etiquetas_no_mapeadas[etiqueta] = \
            informe.etiquetas_no_mapeadas.get(etiqueta, 0) + no_mapeadas
    if bloque.key == "PSS":
        informe.respuestas_columna6_pss += declaradas
    return pd.DataFrame(out, index=raw.index)


_EDAD = re.compile(r"(\d{1,2})(?: ?anos?)?")
_ORDINAL = re.compile(r"(\d{1,2})(?:ro|do|er|ero|to|mo|vo|no|o|[a-h])?")
_CODIGO = re.compile(r"(\d{1,2})(\d{2})[a-h]?")


def edad(texto) -> tuple[float, str]:
    """(edad, estado): estado «ok», «no_numerica» o «fuera_de_rango» (fuera de 4–17)."""
    t = norm_txt(texto)
    if not t:
        return np.nan, "vacia"
    m = _EDAD.fullmatch(t)
    if not m:
        return np.nan, "no_numerica"
    n = int(m.group(1))
    lo, hi = cat.EDAD_SDQ
    if not lo <= n <= hi:
        return np.nan, "fuera_de_rango"
    return float(n), "ok"


def numero_de_grado(texto) -> int | None:
    """Grado 0 (transición) a 11 (once) desde el curso escrito a mano; None si no se sabe.

    Reglas, en orden y sobre el texto normalizado:
      1. Una palabra de grado en cualquier parte: «Sexto 602» → 6.
      2. Un número de 1 o 2 cifras, con o sin sufijo («5», «5A», «4to»): «10» → 10.
      3. Un código de curso de 3 o 4 cifras, grado y grupo: «501» → 5, «1002» → 10.
    """
    tokens = norm_txt(texto).split()
    for t in tokens:
        if t in cat.PALABRAS_GRADO:
            return cat.PALABRAS_GRADO[t]
    for t in tokens:
        m = _ORDINAL.fullmatch(t)
        if m and 0 <= int(m.group(1)) <= 11:
            return int(m.group(1))
        m = _CODIGO.fullmatch(t)
        if m and 0 <= int(m.group(1)) <= 11 and 1 <= int(m.group(2)) <= 20:
            return int(m.group(1))
    return None


def grado_desde_curso(texto) -> tuple[object, str, str]:
    """(Grado del estudio o NaN, detalle legible, estado)."""
    n = numero_de_grado(texto)
    if n is None:
        return np.nan, cat.SIN_DATO, cat.ESTADO_SIN_DATO
    nombre = cat.GRADOS[n]
    if nombre in cat.GRADOS_ESTUDIO:
        return nombre, nombre, cat.ESTADO_ESTUDIO
    return np.nan, nombre, cat.ESTADO_FUERA


def quien(texto) -> str:
    t = norm_txt(texto)
    if t.startswith("mama"):
        return cat.MAMA
    if t.startswith("papa"):
        return cat.PAPA
    return cat.OTRO


def _colegio(serie: pd.Series) -> pd.DataFrame:
    """Código, nombre legible y sede. El texto libre no reconocido no viaja."""
    filas = []
    for x in serie:
        codigo, nombre, sede = normalizar_colegio(x)
        if codigo == "OTRO":
            nombre = "Otro colegio"
        filas.append((codigo, nombre, sede))
    return pd.DataFrame(filas, index=serie.index, columns=["Colegio", "Colegio_nombre", "Sede"])


def fecha(serie: pd.Series) -> pd.Series:
    """Marca temporal: ISO (xlsx leído como texto) o día/mes/año (csv de Google Forms)."""
    iso = pd.to_datetime(serie, errors="coerce", format="ISO8601")
    faltan = iso.isna() & serie.notna()
    if faltan.any():
        iso.loc[faltan] = pd.to_datetime(serie[faltan], errors="coerce", dayfirst=True,
                                         format="mixed")
    return iso


def _ola(ts: pd.Series) -> pd.Series:
    """Ola = año calendario de la marca temporal («2025», «2026»)."""
    return ts.dt.year.map(lambda a: str(int(a)) if pd.notna(a) else cat.SIN_DATO)


def _si(serie: pd.Series) -> pd.Series:
    return serie.map(norm_txt).str.startswith("si")


# ── carga ───────────────────────────────────────────────────────────────────
def _nino(raw: pd.DataFrame, filas: pd.Index, hijo: int, base: pd.DataFrame,
          k: bytes, informe: InformeCuidadores) -> pd.DataFrame:
    """Filas de niño (hijo 1 o 2) para las respuestas `filas`."""
    sub = raw.loc[filas]
    pos = (dict(nombre=cat.COL["nombre_nino"], edad=cat.COL["edad"], sexo=cat.COL["sexo"],
                colegio=cat.COL["colegio"], curso=cat.COL["curso"]) if hijo == 1 else
           dict(nombre=cat.COL["nombre_nino2"], edad=cat.COL["edad2"], sexo=cat.COL["sexo2"],
                colegio=cat.COL["colegio2"], curso=cat.COL["curso2"]))
    d = base.loc[filas, ["ID_cuidador", "ts", OLA_COLUMNA, "Quien", "_fila"]].copy()
    d["Orden_hijo"] = hijo
    ids = sub.iloc[:, pos["nombre"]].map(lambda x: seud.seudonimo(x, "N", k))
    informe.ninos_sin_nombre += int(ids.isna().sum())
    # Sin nombre no se puede deduplicar: cada fila es un niño distinto.
    d["ID_nino"] = [i if i is not None else f"sin-nombre-{hijo}-{f}"
                    for i, f in zip(ids, d["_fila"])]
    edades = sub.iloc[:, pos["edad"]].map(edad)
    d["Edad"] = [e for e, _ in edades]
    d["_edad_estado"] = [s for _, s in edades]
    d["Sexo"] = sub.iloc[:, pos["sexo"]].map(
        lambda x: str(x).strip() if norm_txt(x) in ("nino", "nina") else np.nan)
    d = pd.concat([d, _colegio(sub.iloc[:, pos["colegio"]])], axis=1)
    grados = sub.iloc[:, pos["curso"]].map(grado_desde_curso)
    d["Grado"] = [g for g, _, _ in grados]
    d["Grado_detalle"] = [x for _, x, _ in grados]
    d["Grado_estado"] = [s for _, _, s in grados]
    sdq = mapear_bloque(sub, cat.bloque_sdq(hijo), informe, "SDQ")
    ari = mapear_bloque(sub, cat.bloque_ari(hijo), informe, "ARI")
    informe.cobertura_ari[f"hijo {hijo}"] = int(ari.notna().all(axis=1).sum())
    return pd.concat([d, sdq, ari], axis=1)


def cargar(fuente, k: bytes | None = None) -> Carga:
    """Lee, verifica, filtra por consentimiento y seudonimiza. No deduplica."""
    raw = fuente.copy() if isinstance(fuente, pd.DataFrame) else leer(fuente)
    raw = raw.reset_index(drop=True)
    verificar_formato(raw.columns)
    k = seud.clave() if k is None else k      # sin clave, aquí se detiene

    inf = InformeCuidadores(filas_archivo=len(raw))
    for b in cat.BLOQUES_CUIDADOR:
        inf.enunciados[b.key] = [enunciado(raw.columns[p]) for p in b.posiciones]
    consiente = _si(raw.iloc[:, cat.COL["consentimiento"]])
    inf.sin_consentimiento = int((~consiente).sum())
    raw = raw[consiente]
    inf.respuestas_validas = len(raw)

    r = pd.DataFrame(index=raw.index)
    r["_fila"] = np.arange(len(raw))
    r["ID_cuidador"] = raw.iloc[:, cat.COL["nombre_cuidador"]].map(
        lambda x: seud.seudonimo(x, "C", k))
    sin_nombre = r["ID_cuidador"].isna()
    r.loc[sin_nombre, "ID_cuidador"] = [f"sin-nombre-{f}" for f in r.loc[sin_nombre, "_fila"]]
    r["ts"] = fecha(raw.iloc[:, cat.COL["ts"]])
    r[OLA_COLUMNA] = _ola(r["ts"])
    r["Quien"] = raw.iloc[:, cat.COL["quien"]].map(quien)
    # El colegio y el grado del cuidador son los de su primer hijo.
    r = pd.concat([r, _colegio(raw.iloc[:, cat.COL["colegio"]])], axis=1)
    g1 = raw.iloc[:, cat.COL["curso"]].map(grado_desde_curso)
    r["Grado"] = [g for g, _, _ in g1]
    r["Grado_detalle"] = [x for _, x, _ in g1]
    for nombre, clave in cat.CONTEXTO.items():
        r[nombre] = raw.iloc[:, cat.COL[clave]].map(
            lambda x: str(x).strip() if norm_txt(x) else np.nan)
    bloques = [mapear_bloque(raw, b, inf) for b in cat.BLOQUES_CUIDADOR]
    respuestas = pd.concat([r] + bloques, axis=1)

    con_hijo2 = raw.index[_si(raw.iloc[:, cat.COL["hijo2"]])]
    inf.hijo2 = len(con_hijo2)
    ninos = pd.concat([_nino(raw, raw.index, 1, r, k, inf),
                       _nino(raw, con_hijo2, 2, r, k, inf)], ignore_index=True)
    inf.filas_nino = len(ninos)

    inf.por_ola = respuestas[OLA_COLUMNA].value_counts().sort_index().to_dict()
    inf.por_quien = respuestas["Quien"].value_counts().to_dict()
    inf.edad_no_numerica = int((ninos["_edad_estado"] == "no_numerica").sum())
    inf.edad_fuera_de_rango = int((ninos["_edad_estado"] == "fuera_de_rango").sum())
    inf.curso_sin_resolver = int((ninos["Grado_estado"] == cat.ESTADO_SIN_DATO).sum())
    inf.colegio_no_reconocido = int((ninos["Colegio"] == "OTRO").sum())
    for b in cat.BLOQUES_CUIDADOR:
        inf.faltantes_por_bloque[b.key] = round(
            float(respuestas[b.columnas].isna().mean().mean() * 100), 2)
    for clave, cols in (("SDQ", cat.bloque_sdq(1).columnas), ("ARI", cat.bloque_ari(1).columnas)):
        inf.faltantes_por_bloque[clave] = round(float(ninos[cols].isna().mean().mean() * 100), 2)
    if inf.respuestas_columna6_pss:
        inf.avisos.append(f"PSS-10: {inf.respuestas_columna6_pss} respuestas sueltas "
                          "«Columna 6» cuentan como faltantes.")
    if inf.etiquetas_no_mapeadas:
        inf.avisos.append("Hay respuestas con etiquetas que el catálogo no reconoce: "
                          + ", ".join(f"{k_} ({n})" for k_, n in
                                      sorted(inf.etiquetas_no_mapeadas.items()))
                          + ". Quedan como faltantes.")
    return Carga(respuestas=respuestas.reset_index(drop=True), ninos=ninos, informe=inf)


# ── deduplicación ───────────────────────────────────────────────────────────
def deduplicar(carga: Carga, ola: str | None = None
               ) -> tuple[pd.DataFrame, pd.DataFrame, InformeCuidadores]:
    """(cuidadores, niños, informe) sin repetidos; `ola` filtra antes de deduplicar."""
    import copy
    inf = copy.deepcopy(carga.informe)
    resp, ninos = carga.respuestas, carga.ninos
    if ola:
        resp = resp[resp[OLA_COLUMNA] == ola]
        ninos = ninos[ninos[OLA_COLUMNA] == ola]

    # Cuidadores: la respuesta más reciente (el último envío si empatan).
    orden = resp.sort_values(["ts", "_fila"], na_position="first")
    cuid = orden.drop_duplicates("ID_cuidador", keep="last")
    inf.cuidadores_distintos = len(cuid)
    inf.respuestas_repetidas_cuidador = len(resp) - len(cuid)
    inf.cuidadores_en_dos_olas = int(
        (resp.groupby("ID_cuidador")[OLA_COLUMNA].nunique() > 1).sum())

    # Niños: ola más reciente → mamá, papá, otro → primer envío → hijo 1 antes que 2.
    n = ninos.assign(_prio=ninos["Quien"].map(cat.PRIORIDAD_QUIEN).fillna(9),
                     _ola_orden=pd.to_numeric(ninos[OLA_COLUMNA], errors="coerce").fillna(-1))
    n = n.sort_values(["_ola_orden", "_prio", "ts", "_fila", "Orden_hijo"],
                      ascending=[False, True, True, True, True], na_position="last")
    grupos = n.groupby("ID_nino")
    inf.mismo_nino_misma_respuesta = int(
        (grupos["_fila"].count() - grupos["_fila"].nunique()).sum())
    inf.mismo_nino_otro_cuidador = int((grupos["ID_cuidador"].nunique() > 1).sum())
    inf.mismo_nino_entre_olas = int((grupos[OLA_COLUMNA].nunique() > 1).sum())
    ninos_u = n.drop_duplicates("ID_nino", keep="first").drop(columns=["_prio", "_ola_orden"])
    inf.ninos_unicos = len(ninos_u)

    inf.grados = ninos_u["Grado_detalle"].map(
        lambda g: g if g in cat.GRADOS_ESTUDIO or g == cat.SIN_DATO else cat.FUERA_DE_RANGO
    ).value_counts().to_dict()
    inf.colegios_cuidador = cuid["Colegio"].value_counts().to_dict()
    inf.colegios_nino = ninos_u["Colegio"].value_counts().to_dict()
    return (cuid.drop(columns=["_fila"]).reset_index(drop=True),
            ninos_u.drop(columns=["_fila"]).reset_index(drop=True), inf)
