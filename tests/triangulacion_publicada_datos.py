"""
Datos de prueba de la Triangulación publicada: el análisis sintético (una sola
vez por proceso) y una base falsa con su corrida.
"""
from __future__ import annotations

import functools
import os
import tempfile

from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()


@functools.lru_cache(maxsize=1)
def analisis():
    """`pipeline.Triangulacion` de los tres actores sintéticos (n_boot corto)."""
    from src.triangulacion import pipeline
    base = ts.escribir(tempfile.mkdtemp(prefix="tri_pub_"))
    previo = os.environ.get("OBS360_DATOS_DIR")
    os.environ["OBS360_DATOS_DIR"] = base
    try:
        return pipeline.cargar_y_analizar(k=K, n_boot=30)
    finally:
        if previo is None:
            os.environ.pop("OBS360_DATOS_DIR", None)
        else:
            os.environ["OBS360_DATOS_DIR"] = previo


def publicado(publicar_ya: bool = True):
    """(resumen de la publicación, base falsa) con una corrida de triangulación."""
    from src.triangulacion import publicar
    from tests.supabase_falso import BaseFalsa
    base = BaseFalsa()
    resumen = publicar.publicar(analisis(), notas="prueba", publicar_ya=publicar_ya,
                                cliente=base.cliente())
    return resumen, base
