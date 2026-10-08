"""
Carga local de los tres actores para la triangulación — Observatorio 360.

  · Estudiantes: los dos formularios con `estudiantes.ingest.cargar_varios`,
    pidiendo el seudónimo del niño con la clave local (`clave_nino`), y su
    puntuación (`scoring.puntuar`, señales de `alertas.marcar` por nivel y
    «sin adulto de confianza», PSSM 7 ≤ 2). La columna `ID` (SHA-1 sin clave)
    se quita: la triangulación solo usa el seudónimo con clave.
  · Cuidadores: `cuidadores.ingest` (seudónimos «C…» y «N…»), deduplicados y
    puntuados en sus dos marcos (cuidador y niño), igual que la fase 4a.
  · Docentes: el archivo codificado por `scripts/preparar_docentes.py` (sin
    nombres). Si solo está la exportación cruda, se codifica en memoria con
    `preparar`, que descarta el nombre. El colegio se une con
    `core.colegios.codigo_desde_nombre`.

PRIVACIDAD: nada de aquí se escribe en disco ni se muestra. Los seudónimos
viven solo en memoria, para enlazar; `pipeline.Triangulacion` solo guarda
agregados.
"""
from __future__ import annotations

import inspect
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.colegios import codigo_desde_nombre
from src.core.texto import norm_txt
from src.triangulacion import catalogo as cat

EXTENSIONES = (".xlsx", ".xls", ".csv")
# Se prefiere el archivo ya codificado (sin nombres); si no, la exportación cruda.
PATRONES_DOCENTES = ("codificado", "profesores")
COLUMNA_NINO = "N_hmac"          # = estudiantes.ingest.COLUMNA_NINO

ITEMS_DOCENTES = {
    "DOC_PSS": [f"PSS{i}" for i in range(1, 11)],
    "DOC_LIDER": [f"CL{i}" for i in range(1, 8)],
    "DOC_GRUPO": [f"AP{i}" for i in range(1, 4)],
    "DOC_DESGASTE": [f"BLG_Desg{i}" for i in range(1, 5)],
}
PSS_MIN_ITEMS = 9

MENSAJE_RANCIO = ("La aplicación tiene en memoria una versión anterior de la carga de "
                  "estudiantes, sin el seudónimo del niño. Reinicie la aplicación (en "
                  "Streamlit Cloud, «Reboot app») y vuelva a abrir Triangulación 360.")


class ModuloRancio(RuntimeError):
    """Un módulo existente quedó viejo en memoria y no tiene lo que esta fase necesita."""


@dataclass
class Disponibles:
    estudiantes: list
    cuidadores: str | None
    docentes: str | None

    @property
    def completo(self) -> bool:
        return bool(self.estudiantes) and bool(self.cuidadores) and bool(self.docentes)

    def firma(self) -> tuple:
        rutas = list(self.estudiantes) + [self.cuidadores, self.docentes]
        return tuple((r, os.path.getmtime(r)) for r in rutas if r)

    def presentes(self) -> dict:
        return {"Estudiantes": bool(self.estudiantes), "Cuidadores": bool(self.cuidadores),
                "Docentes": bool(self.docentes)}


@dataclass
class Fuentes:
    estudiantes: pd.DataFrame
    cuidadores: pd.DataFrame
    ninos: pd.DataFrame
    docentes: pd.DataFrame
    informe_cuidadores: object = None

    def marco(self, nombre: str) -> pd.DataFrame:
        return {cat.ESTUDIANTE: self.estudiantes, cat.CUIDADOR: self.cuidadores,
                cat.NINO: self.ninos, cat.DOCENTE: self.docentes}[nombre]


# ── localizar ───────────────────────────────────────────────────────────────
def localizar_docentes(base: str | None = None) -> str | None:
    from src.core.rutas import carpeta_datos
    base = base or carpeta_datos("docentes")
    if not os.path.isdir(base):
        return None
    archivos = [f for f in os.listdir(base)
                if f.lower().endswith(EXTENSIONES) and not f.startswith("~$")]
    for patron in PATRONES_DOCENTES:
        candidatos = [os.path.join(base, f) for f in archivos if patron in norm_txt(f)]
        if candidatos:
            return max(candidatos, key=os.path.getmtime)
    return None


def localizar() -> Disponibles:
    from src.cuidadores.pipeline import localizar_formulario
    from src.estudiantes.pipeline import localizar_formularios
    return Disponibles(estudiantes=localizar_formularios(), cuidadores=localizar_formulario(),
                       docentes=localizar_docentes())


# ── docentes ────────────────────────────────────────────────────────────────
def es_docentes_codificado(df: pd.DataFrame) -> bool:
    necesarias = {"Colegio"} | {c for cols in ITEMS_DOCENTES.values() for c in cols}
    return necesarias <= set(df.columns)


def leer_docentes(fuente) -> pd.DataFrame:
    """El archivo codificado de docentes; la exportación cruda se codifica en memoria."""
    if isinstance(fuente, pd.DataFrame):
        raw = fuente
    else:
        ruta = str(fuente)
        raw = (pd.read_excel(ruta) if ruta.lower().endswith((".xlsx", ".xls"))
               else pd.read_csv(ruta))
    if es_docentes_codificado(raw):
        return raw
    from scripts.preparar_docentes import preparar
    codificado, _ = preparar(raw)
    return codificado


def _suma_prorrateada(X: pd.DataFrame, minimo: int) -> pd.Series:
    respondidos = X.notna().sum(axis=1)
    s = X.sum(axis=1) * X.shape[1] / respondidos.replace(0, np.nan)
    return s.mask(respondidos < minimo)


def puntuar_docentes(d: pd.DataFrame) -> pd.DataFrame:
    """Colegio (código) y los cuatro constructos docentes. Nada más sale de aquí.

    PSS-10: los ítems 3, 4, 5, 7 y 9 ya vienen invertidos por `preparar`; suma
    0–40 prorrateada con 9 de 10 (igual que cuidadores). Apoyo del líder (CL,
    0–5), apoyo de compañeros (AP, 0–5) y desgaste (BLG_Desg, 1–7): media con
    todos sus ítems.
    """
    out = pd.DataFrame(index=d.index)
    out["Colegio"] = d["Colegio"].map(codigo_desde_nombre)
    items = {k: d[cols].apply(pd.to_numeric, errors="coerce") for k, cols in ITEMS_DOCENTES.items()}
    out["DOC_PSS"] = _suma_prorrateada(items["DOC_PSS"], PSS_MIN_ITEMS)
    for clave in ("DOC_LIDER", "DOC_GRUPO", "DOC_DESGASTE"):
        X = items[clave]
        out[clave] = X.mean(axis=1).mask(X.isna().any(axis=1))
    return out.reset_index(drop=True)


# ── estudiantes ─────────────────────────────────────────────────────────────
def preparar_estudiantes(bruto: pd.DataFrame) -> pd.DataFrame:
    """Puntuaciones, señales de alerta por nivel y «sin adulto de confianza»."""
    from src.estudiantes import alertas, scoring
    from src.estudiantes import catalog as cat_est
    p = scoring.puntuar(bruto)
    partes = [alertas.marcar(p[p["nivel"] == nivel], nivel)
              for nivel in p["nivel"].dropna().unique()]
    d = pd.concat(partes).sort_index() if partes else p
    col = f"PSSM{cat_est.PSSM_ITEM_ADULTO}"
    if col in d.columns:
        d["SIN_ADULTO"] = (d[col] <= 2).astype(float).where(d[col].notna())
    return d.drop(columns=[c for c in ("ID",) if c in d.columns]).reset_index(drop=True)


def cargar_estudiantes(rutas: list, k: bytes) -> pd.DataFrame:
    from src.estudiantes import ingest
    if "clave_nino" not in inspect.signature(ingest.cargar_varios).parameters:
        raise ModuloRancio(MENSAJE_RANCIO)
    bruto, _ = ingest.cargar_varios(rutas, clave_nino=k)
    return preparar_estudiantes(bruto)


# ── cuidadores ──────────────────────────────────────────────────────────────
def cargar_cuidadores(fuente, k: bytes) -> tuple[pd.DataFrame, pd.DataFrame, object]:
    from src.cuidadores import ingest, scoring
    cuid, ninos, informe = ingest.deduplicar(ingest.cargar(fuente, k=k))
    return scoring.puntuar_cuidadores(cuid), scoring.puntuar_ninos(ninos), informe


def cargar(disp: Disponibles | None = None, k: bytes | None = None) -> Fuentes:
    """Los tres actores desde los archivos locales. Sin la clave, `ClaveAusente`."""
    from src.core import seudonimo
    disp = disp or localizar()
    if not disp.completo:
        raise FileNotFoundError(cat.AVISO_DESPLIEGUE)
    k = seudonimo.clave() if k is None else k
    estudiantes = cargar_estudiantes(disp.estudiantes, k)
    cuidadores, ninos, informe = cargar_cuidadores(disp.cuidadores, k)
    docentes = puntuar_docentes(leer_docentes(disp.docentes))
    return Fuentes(estudiantes=estudiantes, cuidadores=cuidadores, ninos=ninos,
                   docentes=docentes, informe_cuidadores=informe)
