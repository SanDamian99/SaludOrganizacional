"""
Seudónimos con clave local — Observatorio 360.

Un nombre propio se convierte en un identificador corto e irreversible con
HMAC-SHA256 y una clave que **solo existe en la máquina que procesa**:

    seudonimo("María Pérez", "C")  →  "C3fa91b07"

  · La letra dice qué es: «C» cuidador, «N» niño, «E» estudiante. Coincide con
    el `CHECK` de Supabase `^[ECN][0-9a-f]{8}$`.
  · El mensaje firmado lleva la letra («N|maria perez»): el mismo nombre da
    seudónimos distintos como cuidador y como niño, y la triangulación (fase 5)
    enlaza niño y estudiante calculando los dos con la letra «N».
  · Sin la clave no se puede recalcular ni comprobar un nombre, a diferencia
    del SHA-1 sin clave que usa hoy `estudiantes.ingest`.

La clave se lee de `OBS360_CLAVE_HMAC` (entorno o `.streamlit/secrets.toml`).
**No hay clave por defecto en el código.** Si falta, `ClaveAusente` explica qué
hacer. El despliegue público no la necesita: nunca procesa archivos crudos.

Este módulo es nuevo, así que tras un despliegue siempre se importa fresco.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re

from src.core.texto import norm_txt

VARIABLE = "OBS360_CLAVE_HMAC"
LARGO_MINIMO = 16
LETRAS = ("C", "N", "E")
LARGO_HEX = 8


class ClaveAusente(RuntimeError):
    """Falta la clave local para seudonimizar, o es demasiado corta."""


MENSAJE_CLAVE = (
    f"Falta la clave local `{VARIABLE}`, con la que los nombres se convierten en "
    "identificadores anónimos. Defínela en el entorno o en `.streamlit/secrets.toml` "
    f"(al menos {LARGO_MINIMO} caracteres, por ejemplo la salida de "
    "`python -c \"import secrets; print(secrets.token_hex(32))\"`). Guárdala fuera del "
    "repositorio y usa siempre la misma: si cambia, cambian todos los identificadores.")


def clave() -> bytes:
    """La clave local. Lanza `ClaveAusente` si no está o es corta."""
    valor = os.environ.get(VARIABLE, "").strip()
    if not valor:
        try:
            import streamlit as st
            valor = str(st.secrets.get(VARIABLE, "")).strip()
        except Exception:                                  # noqa: BLE001
            valor = ""
    if len(valor) < LARGO_MINIMO:
        raise ClaveAusente(MENSAJE_CLAVE)
    return valor.encode("utf-8")


PATRON = re.compile(r"^[CNE][0-9a-f]{8}$")


def es_seudonimo(texto) -> bool:
    """True si el texto ya tiene la forma de un seudónimo («N3fa91b07»)."""
    return isinstance(texto, str) and bool(PATRON.match(texto.strip()))


def seudonimo(texto, letra: str, k: bytes | None = None) -> str | None:
    """Letra + 8 hexadecimales del HMAC-SHA256 del texto normalizado. None si vacío.

    Un texto que ya es un seudónimo se devuelve tal cual: así un archivo
    desidentificado (el que vive en Supabase Storage, con seudónimos en lugar de
    nombres) produce exactamente los mismos identificadores que el original.
    """
    if letra not in LETRAS:
        raise ValueError(f"Letra de seudónimo desconocida: {letra!r}")
    if es_seudonimo(texto):
        return texto.strip()
    normalizado = norm_txt(texto)
    if not normalizado:
        return None
    k = clave() if k is None else k
    firma = hmac.new(k, f"{letra}|{normalizado}".encode("utf-8"), hashlib.sha256)
    return letra + firma.hexdigest()[:LARGO_HEX]
