"""
Desidentificación de los formularios crudos para el almacén — Observatorio 360.

Los formularios de estudiantes y de cuidadores traen nombres de personas. Para
que una copia pueda vivir en Supabase Storage (bucket privado, solo con la
credencial de carga) se reemplaza cada nombre por su seudónimo HMAC con la
clave local, y se vacían teléfono y cualquier columna de contacto. **Nada más
cambia**: las columnas quedan en la misma posición y con el mismo encabezado,
porque los módulos de ingesta leen por posición y por encabezado.

Los módulos de ingesta reconocen un seudónimo y lo dejan pasar
(`seudonimo.es_seudonimo`), así que procesar la copia desidentificada da los
mismos identificadores que procesar el original. La clave HMAC no viaja: sin
ella no se puede volver del seudónimo al nombre, ni comprobar un nombre.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.core import seudonimo as seud
from src.core.texto import norm_txt

# Encabezados (normalizados) que se vacían en cualquier conjunto crudo.
FRAGMENTOS_CONTACTO = ("correo", "email", "e mail", "telefono", "celular", "whatsapp",
                       "direccion")
# conjunto -> (patrón del nombre de archivo que usan los localizadores, extensión original)
CONJUNTOS_CRUDOS = {
    "estudiantes_secundaria": "cuentanos sobre tu bienestar emocional",
    "estudiantes_primaria": "cuentanos sobre tus emociones",
    "cuidadores": "cuidando al cuidador",
}


@dataclass
class InformeDesidentificacion:
    conjunto: str
    filas: int = 0
    columnas_seudonimizadas: list = field(default_factory=list)
    columnas_vaciadas: list = field(default_factory=list)
    nombres_reemplazados: int = 0


def _columnas_contacto(df: pd.DataFrame) -> list:
    return [c for c in df.columns if any(f in norm_txt(c) for f in FRAGMENTOS_CONTACTO)]


def _seudonimizar(serie: pd.Series, letra: str, k: bytes) -> pd.Series:
    def uno(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or not str(v).strip():
            return np.nan
        return seud.seudonimo(v, letra, k)
    return serie.map(uno)


def desidentificar(conjunto: str, df: pd.DataFrame, k: bytes | None = None
                   ) -> tuple[pd.DataFrame, InformeDesidentificacion]:
    """Copia de `df` con seudónimos en lugar de nombres y sin datos de contacto."""
    if conjunto not in CONJUNTOS_CRUDOS:
        raise ValueError(f"Conjunto crudo desconocido: {conjunto!r}. "
                         f"Válidos: {tuple(CONJUNTOS_CRUDOS)}")
    k = seud.clave() if k is None else k
    d = df.copy()
    inf = InformeDesidentificacion(conjunto=conjunto, filas=len(d))

    if conjunto.startswith("estudiantes"):
        from src.estudiantes.ingest import _IDENT, _localizar
        pos = _localizar([norm_txt(c) for c in d.columns], _IDENT["nombre"])
        if pos is None:
            raise ValueError("No se encontró la columna «Mi nombre completo es».")
        col = d.columns[pos]
        inf.nombres_reemplazados = int(d[col].notna().sum())
        d[col] = _seudonimizar(d[col], "N", k)
        inf.columnas_seudonimizadas.append(str(col))
    else:
        from src.cuidadores import catalog as cat
        from src.cuidadores.ingest import verificar_formato
        verificar_formato(d.columns)
        for posicion, letra in ((cat.COL["nombre_cuidador"], "C"),
                                (cat.COL["nombre_nino"], "N"),
                                (cat.COL["nombre_nino2"], "N")):
            col = d.columns[posicion]
            inf.nombres_reemplazados += int(d[col].notna().sum())
            d[col] = _seudonimizar(d[col], letra, k)
            inf.columnas_seudonimizadas.append(str(col))
        for posicion in cat.NUNCA_SE_LEEN:
            col = d.columns[posicion]
            d[col] = np.nan
            inf.columnas_vaciadas.append(str(col))

    for col in _columnas_contacto(d):
        if str(col) not in inf.columnas_vaciadas:
            d[col] = np.nan
            inf.columnas_vaciadas.append(str(col))
    verificar(conjunto, d)
    return d, inf


class QuedanIdentificadores(ValueError):
    """La copia que iba a subirse todavía tiene nombres o datos de contacto."""


def verificar(conjunto: str, df: pd.DataFrame) -> None:
    """Falla si alguna celda de nombre no es un seudónimo o algún contacto tiene datos.

    Se llama también al subir: el almacén nunca guarda un conjunto crudo que no
    la pase, aunque alguien salte el paso de desidentificar.
    """
    problemas = []
    if conjunto not in CONJUNTOS_CRUDOS:
        raise ValueError(f"Conjunto crudo desconocido: {conjunto!r}.")
    if not conjunto.startswith("estudiantes"):
        from src.cuidadores import catalog as cat
        if len(df.columns) < cat.N_COLUMNAS:
            raise QuedanIdentificadores(
                f"No se sube: el archivo tiene {len(df.columns)} columnas y la exportación de "
                f"«Cuidando al Cuidador» tiene {cat.N_COLUMNAS}; no se puede comprobar que "
                "esté desidentificado.")
    if conjunto.startswith("estudiantes"):
        from src.estudiantes.ingest import _IDENT, _localizar
        pos = _localizar([norm_txt(c) for c in df.columns], _IDENT["nombre"])
        posiciones = [pos] if pos is not None else []
        vaciadas = []
    else:
        from src.cuidadores import catalog as cat
        posiciones = [cat.COL["nombre_cuidador"], cat.COL["nombre_nino"], cat.COL["nombre_nino2"]]
        vaciadas = list(cat.NUNCA_SE_LEEN)
    for posicion in posiciones:
        serie = df.iloc[:, posicion].dropna()
        malas = int((~serie.map(seud.es_seudonimo)).sum())
        if malas:
            problemas.append(f"columna {posicion}: {malas} celdas que no son seudónimos")
    for posicion in vaciadas:
        if posicion < len(df.columns) and df.iloc[:, posicion].notna().any():
            problemas.append(f"columna {posicion}: debería estar vacía")
    for col in _columnas_contacto(df):
        if df[col].notna().any():
            problemas.append(f"«{col}»: datos de contacto")
    if problemas:
        raise QuedanIdentificadores(
            "No se sube: el conjunto todavía identifica personas. " + "; ".join(problemas))
