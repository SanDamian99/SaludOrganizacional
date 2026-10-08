"""
Triangulación 360 — solo investigadores, solo local (spec del 6-oct-2026, §5.6).

Dos capas:
  · Capa 1, por colegio (y por grado con estudiantes y cuidadores): cada actor
    frente al resto del municipio del mismo actor, en unidades de su DE
    individual, y la clasificación coincidencia / tensión / co-ocurrencia.
  · Capa 2, díadas niño–cuidador: enlace exacto por seudónimo HMAC del nombre
    del niño, verificado con el colegio, y análisis de acuerdo y asociación.

Módulos puros: `catalogo` (constructos, pares y avisos fijos), `fuentes`
(carga local de los tres actores), `estadistica`, `capa1`, `enlace`,
`diadas`, `pipeline` (`Triangulacion`, solo agregados) y `exportar` (ZIP).
La página vive en `src/ui/triangulacion.py` y nunca se importa en el
despliegue público. Nada de este paquete sube a Supabase.
"""
