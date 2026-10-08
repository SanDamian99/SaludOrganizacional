"""
Datos de prueba de la fase 4b: el análisis sintético preparado para la comunidad,
su corrida publicada en una base falsa y una tabla de señales con todos los estados.

Todo sale de `cuidadores_sinteticos` (con sus centinelas de nombres y teléfono).
Las funciones devuelven objetos NUEVOS en cada llamada (copias): una prueba que
los modifique no afecta a otra.
"""
from __future__ import annotations

import copy
import functools

import pandas as pd

from src.cuidadores import alertas, comunidad, ingest, pipeline
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()
P, R, S, T = alertas.PRIORIDAD, alertas.REFERENCIA, alertas.SIN_ESTADO, alertas.PRESENTE


@functools.lru_cache(maxsize=1)
def _analisis():
    return pipeline.analizar(ingest.cargar(cs.formulario(), k=K), n_boot=20)


def analisis():
    """El `AnalisisCuidadores` del pipeline (todas las olas), sin preparar."""
    return copy.deepcopy(_analisis())


@functools.lru_cache(maxsize=1)
def _preparado():
    return comunidad.preparar(_analisis())


def preparado():
    return copy.deepcopy(_preparado())


def publicado(aprobado: bool = True):
    """(cuidadores publicados y leídos con el rol anónimo, base falsa).

    `aprobado=True` simula textos y ruta aprobados (si no, `--publicar-ya`
    omite las filas de señales). Se restablecen al salir.
    """
    from src.cuidadores import comunidad_catalogo as cc
    from src.cuidadores import lectura, publicar
    from tests.supabase_falso import BaseFalsa
    base = BaseFalsa()
    antes = (cc.TEXTOS_APROBADOS, cc.RUTAS_VALIDADAS)
    cc.TEXTOS_APROBADOS = cc.RUTAS_VALIDADAS = aprobado
    try:
        publicar.publicar(preparado(), publicar_ya=True, cliente=base.cliente())
    finally:
        cc.TEXTOS_APROBADOS, cc.RUTAS_VALIDADAS = antes
    leido, _ = lectura.cargar_desde_supabase(base.cliente(anonimo=True))
    return leido, base


def _r(alerta, agrupacion, grupo, pct, estado, n=30):
    con = pct is not None
    return dict(alerta=alerta, agrupacion=agrupacion, grupo=grupo, n=n, pct=pct,
                ic_inf=pct - 8 if con else None, ic_sup=pct + 8 if con else None, estado=estado)


def tabla_senales() -> pd.DataFrame:
    """Señales con todos los estados: prioridad, presente, sin estado y referencia."""
    filas = [
        _r("animo", "total", "Todos", 25.0, R, n=90),
        _r("animo", "Colegio", "LauV", 40.0, P), _r("animo", "Colegio", "JJC", 20.0, T),
        _r("animo", "Colegio", "SJMEB", None, S, n=14),
        _r("animo", "Grado", "Quinto", 38.0, P, n=13), _r("animo", "Grado", "Sexto", 22.0, T),
        _r("animo", "Colegio×Grado", "LauV|Quinto", 45.0, P, n=13),
        _r("animo", "Colegio×Grado", "LauV|Sexto", None, S, n=12),
        _r("autolesion", "total", "Todos", 11.0, R, n=90),
    ]
    return alertas.ordenar(pd.DataFrame(filas, columns=alertas.COLUMNAS_TABLA))


def con_senales(ac, tabla: pd.DataFrame | None = None):
    """Copia de `ac` cuyo marco de cuidadores trae `tabla` (por defecto, `tabla_senales`)."""
    out = copy.copy(ac)
    out.cuidador = copy.copy(ac.cuidador)
    out.cuidador.alertas = tabla_senales() if tabla is None else tabla
    return out
