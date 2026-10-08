"""
Cuidadores 360 — formulario «Cuidando al Cuidador» (spec del 6-oct-2026, §5.5).

Fase 4a: carga, puntuación y vista de investigadores, solo en local.
Fase 4b: vista de comunidad, informes y publicación en Supabase.

Módulos: `catalog` (escalas y mapas por posición), `ingest` (consentimiento,
seudónimos, colegio, grado, ola, hijo 2 y deduplicación), `scoring`
(puntuaciones desde el texto crudo), `privacidad` (base publicable contando
cuidadores distintos) y `pipeline` (`AnalisisCuidadores`).
"""
