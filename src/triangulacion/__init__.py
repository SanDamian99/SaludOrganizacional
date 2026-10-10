"""
Triangulación 360 — solo investigadores (spec del 6-oct-2026, §5.6).

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
despliegue público.

Se calcula solo en la máquina que procesa (archivos, clave y díadas no salen de
ella). `publicar` sube SOLO los agregados a Supabase (modulo y nivel
«triangulacion», n ≥ 10) y `lectura` los lee en el despliegue del equipo con el
usuario de carga; el público nunca los lee (migración 2026-10-10b).
"""
