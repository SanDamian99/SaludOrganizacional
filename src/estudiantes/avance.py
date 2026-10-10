"""
Avance de datos de Estudiantes 360 — qué celdas colegio × grado ya se ven.

Es para el equipo investigador: responde «¿qué falta para que aparezca cada
grado de cada colegio?». No calcula estadística: lee el conteo por colegio y
grado (`Analisis.muestra["colegio_grado"]`) y aplica el mínimo de siempre. Una
celda con menos de `MIN_GROUP_N` respuestas nunca dice cuántas son: solo «<10».
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from src.core import colegios
from src.estudiantes import catalog as cat

VISIBLE = "visible"                 # 10 o más: ya se muestra
FALTA_N = "falta_n"                 # hay respuestas, pero menos de 10
PENDIENTE = "pendiente"             # el equipo espera una exportación actualizada
SIN_RESPUESTAS = "sin_respuestas"   # no hay respuestas y nadie las espera

# Lo que el equipo espera recibir: (nivel, colegio) → grados. Según la
# actualización del 9 de octubre: la exportación de secundaria sigue siendo la
# del 18 de septiembre. Cuando llegue la nueva, estas celdas pasan solas a
# «visible». Editar aquí cuando cambie lo que se espera.
PENDIENTES = {
    (cat.NIVEL_SECUNDARIA, "CdP"): ("Sexto", "Séptimo"),
    (cat.NIVEL_SECUNDARIA, "JJC"): ("Décimo",),
    (cat.NIVEL_SECUNDARIA, "SJMEB"): ("Sexto",),
}

TEXTOS = {VISIBLE: "✔ {n}", FALTA_N: "falta n (<10)", PENDIENTE: "pendiente",
          SIN_RESPUESTAS: "—"}


@dataclass(frozen=True)
class Celda:
    colegio: str
    grado: str
    estado: str
    n_texto: str


def _numero(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _grados(nivel: str) -> list[str]:
    return list(cat.ORDEN_GRADOS_PRI if nivel == cat.NIVEL_PRIMARIA
                else cat.ORDEN_GRADOS_SEC)


def _codigos(muestra: dict, nivel: str) -> list[str]:
    cg = muestra.get("colegio_grado") or {}
    codigos = set((muestra.get("colegio") or {}).keys())
    codigos |= {str(k).split("|")[0] for k in cg}
    codigos |= {c for (n, c) in PENDIENTES if n == nivel}
    return sorted(codigos, key=colegios.nombre)


def celdas(analisis, nivel: str) -> list[Celda]:
    """Una celda por colegio y grado del nivel, en el orden de los grados."""
    muestra = getattr(analisis, "muestra", None) or {}
    conteos = muestra.get("colegio_grado") or {}
    salida: list[Celda] = []
    for colegio in _codigos(muestra, nivel):
        esperados = PENDIENTES.get((nivel, colegio), ())
        for grado in _grados(nivel):
            clave = f"{colegio}|{grado}"
            if clave not in conteos:
                estado = PENDIENTE if grado in esperados else SIN_RESPUESTAS
                salida.append(Celda(colegio, grado, estado, ""))
                continue
            n = _numero(conteos[clave])
            if n is not None and n >= cat.MIN_GROUP_N:
                salida.append(Celda(colegio, grado, VISIBLE, str(int(n))))
            else:
                salida.append(Celda(colegio, grado, FALTA_N, "<10"))
    return salida


def matriz(analisis, nivel: str) -> pd.DataFrame:
    """Colegios en las filas, grados en las columnas, un texto por celda."""
    lista = celdas(analisis, nivel)
    grados = _grados(nivel)
    filas = {}
    for c in lista:
        texto = TEXTOS[c.estado].format(n=c.n_texto)
        filas.setdefault(colegios.nombre(c.colegio), {})[c.grado] = texto
    return pd.DataFrame.from_dict(filas, orient="index", columns=grados)


def resumen(lista: list[Celda]) -> dict[str, int]:
    cuenta = {VISIBLE: 0, FALTA_N: 0, PENDIENTE: 0, SIN_RESPUESTAS: 0}
    for c in lista:
        cuenta[c.estado] += 1
    return cuenta


def texto_pendientes(lista: list[Celda]) -> str:
    """«Cerca de Piedra: Sexto, Séptimo; …» solo con lo que sigue pendiente, o «»."""
    por_colegio: dict[str, list[str]] = {}
    for c in lista:
        if c.estado == PENDIENTE:
            por_colegio.setdefault(c.colegio, []).append(c.grado)
    return "; ".join(f"{colegios.nombre(c)}: {', '.join(g)}"
                     for c, g in sorted(por_colegio.items(),
                                        key=lambda kv: colegios.nombre(kv[0])))


# ── Corridas en Supabase ─────────────────────────────────────────────────────
COLUMNAS_CORRIDA = "id,modulo,publicada,creada_en,n_secundaria,n_primaria,notas"


def leer_corridas(cli, limite: int = 8) -> list[dict]:
    """Las últimas corridas, de la más nueva a la más vieja."""
    return (cli.postgrest.schema("obs360").table("corridas").select(COLUMNAS_CORRIDA)
            .order("id", desc=True).limit(limite).execute().data)


def formatear_corridas(filas: list[dict]) -> list[dict]:
    """Filas listas para mostrar; la nota se recorta para que la tabla se lea."""
    salida = []
    for f in filas:
        nota = (f.get("notas") or "").strip()
        salida.append({
            "Corrida": f.get("id"),
            "Módulo": f.get("modulo") or "",
            "Fecha": str(f.get("creada_en") or "")[:10],
            "Estado": "publicada" if f.get("publicada") else "en revisión",
            "Secundaria": f.get("n_secundaria"),
            "Primaria": f.get("n_primaria"),
            "Nota": nota if len(nota) <= 100 else nota[:97] + "…",
        })
    return salida
