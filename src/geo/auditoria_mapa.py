"""
Auditoría del mapa — Observatorio 360.

Última barrera antes de dibujar: si la tabla del mapa trae algo que el mapa
nunca debe mostrar, se levanta `AuditoriaMapa` y la vista no dibuja nada. No
depende de que `mapa_datos` esté bien: lo revisa desde afuera.
"""
from __future__ import annotations

from src.core import colegios
from src.geo import mapa_datos as md


class AuditoriaMapa(ValueError):
    """La tabla del mapa trae algo que no se puede mostrar."""


def auditar(filas, capa: str, visibles, pequenos) -> None:
    if capa not in md.CAPAS:
        raise AuditoriaMapa(f"Capa no permitida en el mapa: {capa!r}")
    conocidos = {c for _, c, _ in colegios.COLEGIOS}
    vistos: set[str] = set()
    for f in filas:
        if f.codigo not in conocidos:
            raise AuditoriaMapa(f"{f.codigo!r} no es un colegio (¿una sede?).")
        if f.codigo in vistos:
            raise AuditoriaMapa(f"{f.codigo}: aparece dos veces.")
        vistos.add(f.codigo)
        if f.estado not in md.ESTADOS:
            raise AuditoriaMapa(f"{f.codigo}: estado desconocido {f.estado!r}.")
        con_dato = f.tramo is not None or f.valor is not None
        if f.codigo in pequenos and (f.estado != md.PEQUENA or con_dato):
            raise AuditoriaMapa(f"{f.codigo}: grupo pequeño con cifra.")
        if f.estado == md.CON_CIFRA and f.codigo not in visibles:
            raise AuditoriaMapa(f"{f.codigo}: cifra de un grupo que no es visible.")
        if f.estado in (md.PEQUENA, md.SIN_FORMULARIO, md.SIN_INDICADOR) and \
                (con_dato or f.referencia is not None):
            raise AuditoriaMapa(f"{f.codigo}: estado sin cifra pero con dato.")
        if capa == "respuestas" and f.valor is not None:
            raise AuditoriaMapa(f"{f.codigo}: la capa de respuestas no lleva valor.")
