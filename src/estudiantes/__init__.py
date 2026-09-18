"""
Módulo Estudiantes 360 — autorreporte de estudiantes de colegios oficiales de Chía.

Capas, de abajo hacia arriba:
  catalog  — única fuente de verdad: ítems, inversos, cortes, textos por audiencia
  ingest   — lee los formularios, anonimiza, limpia y normaliza
  scoring  — puntúa subescalas, bandas, fiabilidad, descriptivos
  stats    — correlaciones, comparaciones, modelos; respeta MIN_GROUP_N
  pipeline — orquesta todo y cachea el resultado para las vistas

Las vistas (src/ui/views/estudiantes_*.py) NO calculan: solo presentan lo que
devuelve `pipeline.analizar`, para que comunidad, investigación y artículo no
puedan divergir.
"""
from src.estudiantes import catalog  # noqa: F401

__all__ = ["catalog", "ingest", "scoring", "stats", "pipeline"]
