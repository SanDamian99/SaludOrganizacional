"""
Dónde viven los datos fuente — Observatorio 360.

Los archivos con respuestas individuales (formularios de estudiantes, exportación
de docentes, cuidadores) traen nombres de personas y **no viven en el
repositorio**, ni siquiera ignorados por git: su sitio es una carpeta hermana,
`datos_fuente_360`, o la que diga `OBS360_DATOS_DIR`. Este módulo es el único
lugar que sabe eso; el resto del código le pregunta.

Orden de resolución:
  1. `OBS360_DATOS_DIR` (entorno), si está definida.
  2. `<carpeta que contiene el repositorio>/datos_fuente_360`, si existe.
  3. La raíz del repositorio, para no romper una máquina que aún tenga los
     archivos ahí.
"""
from __future__ import annotations

import os

CARPETA_HERMANA = "datos_fuente_360"


def raiz_repositorio() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def carpeta_datos(subcarpeta: str | None = None) -> str:
    """Carpeta de datos fuente; con `subcarpeta` («estudiantes», «docentes»…) si existe.

    Si la subcarpeta no existe se devuelve la carpeta base: así una instalación
    que guarde todo junto sigue funcionando.
    """
    base = os.environ.get("OBS360_DATOS_DIR", "").strip()
    if not base:
        hermana = os.path.join(os.path.dirname(raiz_repositorio()), CARPETA_HERMANA)
        base = hermana if os.path.isdir(hermana) else raiz_repositorio()
    if subcarpeta:
        candidata = os.path.join(base, subcarpeta)
        if os.path.isdir(candidata):
            return candidata
    return base
