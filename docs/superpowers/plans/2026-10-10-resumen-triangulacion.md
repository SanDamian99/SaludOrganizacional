# Resumen de la Triangulación 360 · plan de implementación

**Fecha:** 10 de octubre de 2026 · **Rama:** `feature/resumen-triangulacion` (desde `origin/feature/triangulacion-publica`) · **Worktree:** `SaludOrganizacional-resumen`.

**Objetivo:** que la pestaña «Resumen» deje de mostrar «Dónde coinciden: Sin datos para mostrar» y entre con los 8 hallazgos fuertes (1–8) de `docs/analisis/2026-10-10-hallazgos-triangulacion.md` y los tres ajustes de método que propone (§G): ajuste por grado en estudiantes, apoyo familiar niño–cuidador como mismo objeto, y los pares SDQ conducta e hiperactividad. Los hallazgos moderados (9–12) no entran.

**Decisión del usuario (10 oct 2026):** se registra en la spec `2026-10-06-cuidadores-alertas-triangulacion-design.md` §6 como «Decisión posterior».

## Reglas que no se negocian

- Textos FIJOS en un catálogo (`src/triangulacion/hallazgos_catalogo.py`), marcados «pendientes de aprobación del equipo». Nunca los redacta la IA en tiempo de ejecución. Solo se rellenan cifras agregadas que ya están en las tablas publicadas.
- Un hallazgo se muestra SOLO si la corrida lo sustenta (su cifra sale de `t.capa1.*` o `t.diadas.*`) y se oculta sin error si la tabla no trae la fila. Funciona igual con `pipeline.Triangulacion` y con `lectura.TriangulacionPublicada` (equipo y público).
- Toda cifra nueva: n ≥ 10 (cuidadores distintos; díadas de ≥ 10 familias), proporciones con cada parte ≥ 10 en los cruces de señales sensibles, sin identificadores, sin `casos`/`k_bajo`/`k_alto`, y la auditoría de span lineal (`tests/triangulacion_span.py`) cubre los conjuntos nuevos.

## Tareas

### T1 · Catálogo de constructos y pares (`catalogo.py`)
- Constructos nuevos: `est_sdq_con`, `est_sdq_hip`, `nin_sdq_con`, `nin_sdq_hip`; etiqueta corta (`corta`) en todos para el cuadro por colegio.
- `est_mspss_fam`/`cui_mspss_fam` pasa a `MISMO_OBJETO`; pares nuevos conducta e hiperactividad (mismo objeto).
- Avisos: `AVISO_AJUSTE_GRADO`, `AVISO_MUNICIPAL`, `AVISO_INFORMANTE`, `AVISO_HALLAZGOS`.
- Pruebas: `test_triangulacion_capa1.py::test_pares_de_mismo_objeto_son_los_de_la_spec` (actualizar).

### T2 · Ajuste por grado en la capa 1 (`capa1.py`)
- En estudiantes y agrupación «Colegio», `d` e IC se calculan sobre el residuo de la media del grado (universo = átomos válidos); las medias mostradas siguen brutas; DE del actor bruta. Columna nueva `ajuste` («grado» o vacío).
- Pruebas: un colegio con solo grados altos no sale «peor» por composición; por grado no se ajusta; docentes/cuidadores sin ajuste.

### T3 · Cifras municipales de la capa 1 (`capa1.municipal`)
Tabla `capa1.municipal` (columnas `bloque, clave, grupo, n, valor, ic_inf, ic_sup, motivo`):
- `senales` (estudiantes de secundaria del universo de átomos): % ítem 18 ≥ «con frecuencia», % señal de malestar, % con señal entre quienes marcan el ítem 18 (Wilson). Solo si las 4 celdas del cruce tienen ≥ 10. Sustenta el hallazgo 3.
- `apoyo_animo` (cuidadores del universo): % EPDS ≥ 13 por tercil de apoyo familiar (Wilson), cada tercil ≥ 10 cuidadores y 3 ≤ k ≤ n − 3. Hallazgo 4.
- `pss` (cuidadores y docentes): media con IC y `d` cuidadores − docentes con IC de Welch. Hallazgo 5.
- `desgaste_docente`: MCO del desgaste (z) sobre demandas (MT4–7), conflicto de rol (CR5–7) y apoyo del líder (z), errores agrupados por colegio; una fila por predictor. Hallazgo 8. Requiere `fuentes.puntuar_docentes` con `DOC_DEMANDAS` y `DOC_CONFLICTO_ROL` opcionales.
- Auditoría: `tests/triangulacion_span.py::auditar_capa1` incluye los conjuntos de señales y terciles.

### T4 · Informante en las díadas (`diadas.informante`)
- ρ (bootstrap por familias) del EPDS y la PSS del cuidador con el SDQ total que da el cuidador y con el que da el niño. Hallazgo 2.
- Hallazgo 1 ya sale de `diadas.acuerdo`; hallazgo 6 de `capa1.por_grado` (sin adulto); hallazgo 7 de `clasificacion` + `diferencias`.

### T5 · Publicar, leer, exportar
- `publicar.TABLAS` += `capa1_municipal`, `diadas_informante` (VALOR, `_clave`); `lectura` reconstruye `capa1.municipal` y `diadas.informante` (formato 1, las corridas viejas siguen leyéndose con tablas vacías).
- `exportar.tablas` += los dos CSV; `metodologia_md` describe el ajuste por grado, los pares nuevos, el bloque municipal y el de informante.
- Pruebas: ida y vuelta (`test_triangulacion_lectura.py`), lote (`test_triangulacion_publicar.py`), ZIP.

### T6 · Catálogo de hallazgos e hipótesis (`hallazgos_catalogo.py`, `hallazgos.py`)
- `Hallazgo(numero, bloque, actores, titulo, texto, hipotesis)` × 8 y `Hipotesis` (H1, H2, H3, H4, H8, H10, H11, H12) con los textos del documento.
- `hallazgos.evaluar(t)` → lista de `Visible(hallazgo, cifra, grupo)`; cada evaluador lee tablas con `getattr` y devuelve None si falta la fila.
- Pruebas: con tablas armadas a mano cada hallazgo aparece y desaparece; con `t` vacío no falla; ningún texto se genera.

### T7 · Vista «Resumen» (`triangulacion_investigador._tab_resumen`)
1. Perfil por colegio: métricas + cuadro corto (▲/▼ con etiqueta corta por actor, IC que excluye 0).
2. Patrones entre actores: hallazgos de bloque «patrón» + expander con los pares de la capa 1 en coincidencia.
3. Dónde hay tensión: hallazgos de bloque «tensión» + pares en tensión.
4. Hipótesis: las ligadas a los hallazgos visibles.
- Pruebas: `test_triangulacion_pagina.py`, `test_triangulacion_publica.py` (los bloques existen en local y publicado; sin textos prohibidos).

### T8 · Spec, verificación
- Spec §6: «Decisión posterior (10 oct 2026) · Resumen con hallazgos fijos».
- Suite completa en `.venv` y en `venv314` con `OBS360_DATOS_DIR`; pipeline local en ensayo (`python -m src.triangulacion.publicar --ensayo`); Playwright sobre `streamlit run main.py` en modo investigador: los 4 bloques con cifras y las 10 pestañas sin excepción.
