# Docentes · Fase 1 (puntuación y faltantes) — plan

**Objetivo:** que el número detrás de cada indicador de Docentes sea el correcto: subescalas con polaridad homogénea, sin imputación, N real por constructo, semáforo anclado a cortes publicados o a la escala teórica, y «hijos = 10» como código de faltante. No se rediseña la vista (fase 2) ni el PDF (fase 3).

**Base:** `docs/analisis/2026-10-10-propuesta-docentes.md` §5 y §7 (fase 1), con los 13 puntos de §6 aprobados provisionalmente.

**Rama:** `feature/docentes-fase1` en el worktree `../SaludOrganizacional-docentes1`. Pruebas con `../SaludOrganizacional/.venv/bin/python -m pytest` y con `venv314`, exportando `OBS360_DATOS_DIR`.

## Decisiones que fija este plan

- **Codificación de ítems.** El archivo activo en Storage (y `Docentes_2026_codificado.xlsx`) está en la *codificación 1*: PRPS_CE2, CE9–16 y ERS_ACP1 invertidos, IR1 sin invertir. El script regenerado escribe la *codificación 2* (§5.1.1) y la marca con la columna `Codificación de ítems = 2`. El catálogo se define sobre la codificación 2 y `src/docentes/scoring.normalizar_codificacion` convierte un archivo en codificación 1 antes de puntuar. Así el archivo de Storage no hay que reemplazarlo para que la vista puntúe bien.
- **Puntuación desde los ítems.** La vista deja de depender de los `*_T`. Los totales nuevos del script (`<clave>_T`) son una comodidad para el equipo; la app recalcula siempre desde los ítems.
- **Sin imputación.** `ExcelProcessor` deja de rellenar con la mediana para cualquier archivo. Un constructo no medido en una ola queda faltante y su N refleja a quienes respondieron.
- **«Número de hijos» = 10** se convierte en faltante al cargar (`src/docentes/limpieza.py`), no en el archivo: es reversible si el equipo confirma otra cosa.
- **Semáforo anclado.** Con corte publicado (PSS, BAT-12, ISTAS21), la zona sale de la banda donde cae la media; sin corte, del tercio de la escala teórica, orientada. Colores verde / ámbar / naranja; nunca rojo.
- **PDF y Chat no se tocan** (fase 3 y decisión A/B del 1-oct): siguen leyendo los `*_T` del archivo y el índice relativo. Se documenta.

## Tareas

| # | Tarea | Archivos | Pruebas |
|---|---|---|---|
| 1 | Catálogo de dimensiones docentes (ítems, inversión, agregación, escala, dirección, cortes con marca «comprobar en el manual», fuente, frase, aviso de versión, solo 2025) | `src/docentes/__init__.py`, `src/docentes/catalogo.py` | `tests/test_docentes_catalogo.py` |
| 2 | Estadística mínima (IC t de la media, Wilson, proporción protegida k ≥ 3) y puntuación: `normalizar_codificacion`, `puntuar` (por docente), `resumen` (media, N, DE, IC, α, % de escala, zona, bandas) | `src/docentes/estadistica.py`, `src/docentes/scoring.py` | `tests/test_docentes_scoring.py` |
| 3 | Códigos de faltante («hijos = 10») aplicados al cargar | `src/docentes/limpieza.py`, `src/data/loader.py` | `tests/test_docentes_scoring.py` |
| 4 | Quitar la imputación por mediana | `src/data/processor.py`, `tests/test_ingestion.py`, `tests/test_ingestion_v2.py` | ídem |
| 5 | Script de preparación: inversiones de §5.1.1, totales por subescala, marca de codificación | `scripts/preparar_docentes.py`, `tests/test_preparar_docentes.py` | ídem |
| 6 | Vista: cambio mínimo para consumir el resumen nuevo (barras en % de la escala teórica, zona anclada, histograma y comparación por grupo sobre la puntuación nueva) | `src/ui/dashboard.py`, `tests/docentes_sinteticos.py`, pruebas de la página | `tests/test_docentes_relevancia.py`, `tests/test_docentes_privacidad.py` |
| 7 | Prueba con datos reales (solo agregados) y tabla de cifras que cambian | `tests/test_docentes_reales.py`, `docs/analisis/2026-10-10-docentes-fase1-cambios.md`, `docs/GUIA_DATASETS.md` | ídem |
| 8 | Suites completas en `.venv` y `venv314`; Playwright sobre la página Docentes | — | — |

## Criterio de salida

Las medias, N y α de la propuesta §5.2–5.3 se reproducen con el archivo real; Estudiantes, Cuidadores y Triangulación no cambian; la página Docentes abre sin excepciones.
