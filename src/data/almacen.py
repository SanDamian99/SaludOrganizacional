"""
Almacén de versiones del archivo de docentes/cuidadores en Supabase Storage.

Los xlsx reales no viajan con el repositorio, así que el despliegue no los tiene.
Este módulo permite que el equipo suba una nueva versión desde el despliegue
privado, la deje registrada en `obs360.conjuntos_versiones` y marque cuál es la
activa; al arrancar, la app baja la activa en vez de buscar en disco.

Antes de guardar se retiran las columnas que identifican a una persona (nombre,
documento, correo…). El análisis no las necesita y así el archivo que queda en
Storage no puede volver a asociarse a nadie, ni siquiera por quien tenga la
credencial de carga.

Escribe y lee un único usuario de Supabase Auth cuyas credenciales existen solo
en los secretos del despliegue privado (`OBS360_CARGA_EMAIL` /
`OBS360_CARGA_CLAVE`). Sin ellas el módulo se declara no disponible y el resto
de la app sigue con el comportamiento de disco.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from datetime import datetime

import pandas as pd

from src.data.processor import is_protected_column, normalize_text

logger = logging.getLogger(__name__)

BUCKET = "datasets"
ESQUEMA = "obs360"
TABLA = "conjuntos_versiones"
CONJUNTOS = ("docentes", "cuidadores")

# Nombres de columna (normalizados) que identifican a una persona y que
# `is_protected_column` no cubre. Coincidencia exacta salvo los fragmentos.
_IDENTIFICADORES_EXACTOS = {
    "nombre", "nombre completo", "documento", "cedula", "telefono", "celular",
}
_IDENTIFICADORES_FRAGMENTOS = ("correo", "email", "e-mail")


class AlmacenNoDisponible(RuntimeError):
    """Faltan credenciales o no se pudo iniciar sesión con el usuario de carga."""


class AlmacenError(RuntimeError):
    """Falló una operación contra Storage o la tabla de versiones."""


# ─────────────────────────────────────────────────────────────────────────────
# Credenciales
# ─────────────────────────────────────────────────────────────────────────────

def _secreto(nombre: str) -> str | None:
    """Variable de entorno primero, después `st.secrets`.

    Streamlit copia sus secretos al entorno al arrancar, así que mirar primero
    `os.environ` cubre el despliegue; `st.secrets` queda para ejecuciones donde
    esa copia no ocurrió. Fuera de Streamlit (pruebas, scripts) `st.secrets`
    puede no existir o lanzar, y eso no es un error: simplemente no hay secreto.
    """
    valor = os.environ.get(nombre)
    if valor:
        return valor
    try:
        import streamlit as st
        valor = st.secrets.get(nombre)
    except Exception:                                      # noqa: BLE001
        valor = None
    return valor or None


def credenciales_carga() -> tuple[str | None, str | None]:
    """(email, clave) del usuario de carga, o (None, None) si falta alguno."""
    email = _secreto("OBS360_CARGA_EMAIL")
    clave = _secreto("OBS360_CARGA_CLAVE")
    if email and clave:
        return email, clave
    return None, None


def _conexion_supabase() -> tuple[str | None, str | None]:
    try:
        from src.core.config import get_supabase_url, get_supabase_key
        return get_supabase_url(), get_supabase_key()
    except Exception:                                      # noqa: BLE001
        return _secreto("SUPABASE_URL"), _secreto("SUPABASE_KEY")


def disponible() -> bool:
    """True si hay con qué iniciar sesión: URL, clave anon y usuario de carga."""
    email, clave = credenciales_carga()
    if not (email and clave):
        return False
    url, key = _conexion_supabase()
    return bool(url and key)


# ─────────────────────────────────────────────────────────────────────────────
# Retiro de identificadores
# ─────────────────────────────────────────────────────────────────────────────

def es_identificador(colname) -> bool:
    """True si la columna identifica a una persona y no debe guardarse."""
    if is_protected_column(colname):
        return True
    n = normalize_text(colname)
    if n in _IDENTIFICADORES_EXACTOS:
        return True
    return any(f in n for f in _IDENTIFICADORES_FRAGMENTOS)


def columnas_identificadoras(df: pd.DataFrame) -> list:
    return [c for c in df.columns if es_identificador(c)]


def sin_identificadores(df: pd.DataFrame) -> pd.DataFrame:
    """Copia del DataFrame sin las columnas que identifican a una persona."""
    return df.drop(columns=columnas_identificadoras(df))


# ─────────────────────────────────────────────────────────────────────────────
# Cliente
# ─────────────────────────────────────────────────────────────────────────────

def _ahora() -> datetime:
    """Separado para que las pruebas fijen la marca de tiempo de la ruta."""
    return datetime.now()


def _mensaje(e: Exception) -> str:
    """Texto corto de un error de supabase-py, sin volcar el JSON completo."""
    for atributo in ("message", "msg"):
        m = getattr(e, atributo, None)
        if isinstance(m, str) and m:
            return m
    return str(e).splitlines()[0][:200] if str(e) else e.__class__.__name__


class Almacen:
    """Sesión con el usuario de carga sobre Storage y la tabla de versiones.

    Todo se puede inyectar (`cliente` incluido) para probar sin red.
    """

    def __init__(self, url=None, key=None, email=None, clave=None, cliente=None):
        u, k = _conexion_supabase()
        e, c = credenciales_carga()
        self.url = url or u
        self.key = key or k
        self.email = email or e
        self.clave = clave or c
        self._cliente = cliente
        self._conectado = False

    # -- conexión ------------------------------------------------------------

    def conectar(self):
        """Inicia sesión con el usuario de carga. Idempotente."""
        if self._conectado:
            return self
        if not (self.email and self.clave):
            raise AlmacenNoDisponible(
                "Faltan las credenciales de carga (OBS360_CARGA_EMAIL / "
                "OBS360_CARGA_CLAVE). Solo el despliegue privado las tiene."
            )
        if self._cliente is None:
            if not (self.url and self.key):
                raise AlmacenNoDisponible(
                    "Faltan SUPABASE_URL o SUPABASE_KEY para conectar con Supabase."
                )
            try:
                from supabase import create_client
                self._cliente = create_client(self.url, self.key)
            except Exception as e:                          # noqa: BLE001
                raise AlmacenNoDisponible(
                    f"No se pudo crear el cliente de Supabase: {_mensaje(e)}"
                ) from e
        try:
            self._cliente.auth.sign_in_with_password(
                {"email": self.email, "password": self.clave}
            )
        except Exception as e:                              # noqa: BLE001
            raise AlmacenNoDisponible(
                f"Supabase rechazó al usuario de carga: {_mensaje(e)}"
            ) from e
        self._conectado = True
        return self

    def _tabla(self):
        return self.conectar()._cliente.schema(ESQUEMA).table(TABLA)

    def _bucket(self):
        return self.conectar()._cliente.storage.from_(BUCKET)

    # -- versiones -----------------------------------------------------------

    def subir_version(self, conjunto: str, df: pd.DataFrame, nombre_original: str,
                      notas: str = "") -> dict:
        """Guarda `df` sin identificadores como nueva versión activa de `conjunto`.

        Devuelve la fila insertada más `columnas_retiradas`, para que la interfaz
        pueda decir exactamente qué no se guardó.
        """
        if conjunto not in CONJUNTOS:
            raise ValueError(f"Conjunto desconocido: {conjunto!r}. Válidos: {CONJUNTOS}")
        if df is None or len(df) == 0:
            raise ValueError("No hay filas que guardar.")

        retiradas = columnas_identificadoras(df)
        limpio = df.drop(columns=retiradas)
        contenido = limpio.to_csv(index=False).encode("utf-8")
        hash_ = hashlib.sha256(contenido).hexdigest()
        ruta = f"{conjunto}/{_ahora():%Y%m%d-%H%M%S}_{hash_[:8]}.csv"

        try:
            self._bucket().upload(
                path=ruta, file=contenido,
                file_options={"content-type": "text/csv", "upsert": "false"},
            )
        except AlmacenNoDisponible:
            raise
        except Exception as e:                              # noqa: BLE001
            raise AlmacenError(f"No se pudo subir el archivo a Storage: {_mensaje(e)}") from e

        fila = {
            "conjunto": conjunto,
            "ruta": ruta,
            "nombre_original": nombre_original,
            "filas": int(len(limpio)),
            "columnas": int(len(limpio.columns)),
            "hash": hash_,
            "notas": notas or "",
            "subido_por": self.email,
            "activa": False,
        }
        try:
            res = self._tabla().insert(fila).execute()
        except Exception as e:                              # noqa: BLE001
            raise AlmacenError(
                f"El archivo subió pero no se pudo registrar la versión: {_mensaje(e)}"
            ) from e
        guardada = (res.data or [fila])[0]
        self.activar(guardada.get("id"), conjunto=conjunto)
        guardada = {**guardada, "activa": True, "columnas_retiradas": retiradas}
        return guardada

    def versiones(self, conjunto: str) -> list[dict]:
        """Versiones de `conjunto`, la más reciente primero."""
        try:
            res = (self._tabla().select("*").eq("conjunto", conjunto)
                   .order("creada_en", desc=True).execute())
        except AlmacenNoDisponible:
            raise
        except Exception as e:                              # noqa: BLE001
            raise AlmacenError(f"No se pudieron leer las versiones: {_mensaje(e)}") from e
        return list(res.data or [])

    def version_activa(self, conjunto: str) -> dict | None:
        try:
            res = (self._tabla().select("*").eq("conjunto", conjunto)
                   .eq("activa", True).order("creada_en", desc=True).execute())
        except AlmacenNoDisponible:
            raise
        except Exception as e:                              # noqa: BLE001
            raise AlmacenError(f"No se pudo consultar la versión activa: {_mensaje(e)}") from e
        datos = res.data or []
        return datos[0] if datos else None

    def activar(self, id_version, conjunto: str | None = None) -> None:
        """Deja `id_version` como única activa de su conjunto.

        No hay transacción: primero se desactivan todas las del conjunto y luego
        se activa la elegida. Si falla entre ambas, queda ninguna activa (la app
        cae a disco), nunca dos.
        """
        if id_version is None:
            raise ValueError("La versión no tiene id.")
        if conjunto is None:
            res = self._tabla().select("conjunto").eq("id", id_version).execute()
            if not res.data:
                raise AlmacenError(f"No existe la versión {id_version}.")
            conjunto = res.data[0]["conjunto"]
        try:
            self._tabla().update({"activa": False}).eq("conjunto", conjunto).execute()
            self._tabla().update({"activa": True}).eq("id", id_version).execute()
        except Exception as e:                              # noqa: BLE001
            raise AlmacenError(f"No se pudo activar la versión: {_mensaje(e)}") from e

    def descargar(self, ruta: str) -> pd.DataFrame:
        """Baja el CSV de Storage y lo devuelve como DataFrame crudo."""
        try:
            contenido = self._bucket().download(ruta)
        except AlmacenNoDisponible:
            raise
        except Exception as e:                              # noqa: BLE001
            raise AlmacenError(f"No se pudo descargar «{ruta}»: {_mensaje(e)}") from e
        return pd.read_csv(io.BytesIO(contenido))
