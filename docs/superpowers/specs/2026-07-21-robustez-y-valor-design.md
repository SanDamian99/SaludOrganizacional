# Diseño — Robustez de ingesta, validez de puntajes y valor de resultados

**Fecha:** 2026-07-21
**Rama:** `feature/robustez-y-valor`
**Autor:** Refactorización asistida (Claude Code)

## Contexto

La app **Observatorio de Salud Organizacional** (Streamlit) tiene una arquitectura
modular sólida, pero sus piezas de mayor valor están construidas pero **desconectadas
o son frágiles**. Una revisión con evidencia detectó que:

1. El motor "robusto" de ingesta (`best_response_set`, `try_column_override`,
   `guess_type`, `reverse_numeric`) es **código muerto**: `process_complex_excel`
   nunca lo invoca. Existe incluso un test (`test_robust_processor.py`) que espera
   ese comportamiento y hoy falla.
2. Los puntajes de dimensión se calculan como **promedio crudo de ítems sin invertir
   los negativos**, mezclando direcciones opuestas (verificado: en "Control del Tiempo"
   los ítems positivos y negativos correlacionan ~−0.08). Los números no son válidos.
3. La imputación llena **todo**, incluidos identificadores (ID, correo, nombre, fechas).
4. El RAG (`KnowledgeBase`, Chroma) y los módulos `ResponseRouter`/`PromptBuilder`
   **no están cableados** al chat ni a los reportes.
5. `GeminiClient` se instancia en cada rerun → su caché y rate-limit nunca funcionan.
6. Bugs concretos: el botón "Generar Informe PDF" del dashboard llama a `build()`
   (no existe); la sección "laboral" del PDF filtra por `(SD)` en vez de `(LB)`;
   el PDF elimina tildes innecesariamente.
7. `chromadb` se importa pero no está en `requirements.txt` → `pytest` está rojo.

**Objetivo:** dejar el flujo de valor completo (ingesta correcta → puntuación válida →
visualización clara → informe útil) funcionando y verificado, con `pytest` y una
prueba end-to-end de Playwright **en verde**, y el repositorio listo para entregar.

**Decisiones del usuario:** rigor psicométrico completo; vistas duales
**ejecutiva + académica** (con los agregados político-poblacionales dentro de la
académica); limpieza completa del repositorio.

## Decisión arquitectónica central

**Los datos crudos se conservan intactos; los puntajes orientados se calculan al leer.**
Un módulo nuevo `src/analysis/scoring.py` es la única fuente de verdad de los puntajes
de dimensión (aplica el mapa de valencia y el reverse-scoring). Dashboard y reportes
consumen los mismos números. Alternativa descartada: invertir al ingestar (pierde
trazabilidad y arriesga doble-inversión).

Separación limpia de dos mecanismos de reversión que operan sobre columnas **disjuntas**:
- **Ingesta** (`processor.py`): reversión intrínseca de ítems genéricos que la
  requieren para codificarse (patrones `REVERSE_PATTERNS`, p. ej. instrumentos SDQ/IRI).
- **Scoring** (`scoring.py`): reversión por valencia de los ítems de dimensión `(BM)`
  de este estudio, según el mapa documentado en `docs/METODOLOGIA_PUNTAJES.md`.

Los `REVERSE_PATTERNS` no incluyen ítems `(BM)`, por lo que no hay solapamiento.

## Workstreams

### A. Ingesta robusta — `src/data/processor.py`
- Conectar el motor: en `process_complex_excel`, tras `_map_columns`, procesar cada
  columna **no protegida** con la cascada `try_column_override → best_response_set →
  guess_type`, usando un umbral de cobertura (~0.6) para aceptar la conversión.
- **Columnas protegidas** (nunca numerizar ni imputar): `ID`, `Nombre`,
  `Correo electrónico`, `Hora de inicio`, `Hora de finalización`, y cualquier columna
  detectada como identificador/fecha.
- Aplicar reverse-coding intrínseco (`is_reverse_column` + `reverse_numeric`) solo a
  columnas que matchean `REVERSE_PATTERNS`.
- Imputación responsable: solo ítems de escala/numéricos (mediana); reportar por columna.
  No imputar demografía categórica ni texto (se conserva NaN → visible en diagnóstico).
- Reporte enriquecido con **alias de compatibilidad**: además de
  `n_rows_original/n_rows_final/...`, exponer `rows_cleaned`, `columns_processed`,
  `scale_map` (columna→set detectado y cobertura), `imputation_by_column`.
- Arreglar mapeo con espacios/nbsp en claves del `DATA_DICTIONARY`.

**Contratos de test a preservar** (`test_ingestion_v2.py`): imputa ítems de escala;
`n_cells_imputed==0` cuando no hay faltantes; determinismo (mismo archivo → mismo df);
preserva columnas desconocidas; preserva escalas 1-5 y 1-7; archivo vacío → `success=False`.
**Contrato a habilitar** (`test_robust_processor.py`): "Siempre"→7, "Nunca"→1;
reverse-coding en columna que matchea patrón; "10 años"→10.0, "5,5"→5.5;
`report['rows_cleaned']`, `report['columns_processed']`, `report['extra_variables']`.

### B. Scoring psicométrico — `src/analysis/scoring.py` (nuevo, TDD)
- `ITEM_VALENCE` en `config.py`: por dimensión, lista de +1/−1 paralela a `Preguntas`
  (ver metodología). Helper `get_item_valence(dim, question)`.
- `compute_dimension_scores(df) -> dict[dim] = {score, n, std, ci95, alpha, n_items,
  estado, color, raw_mean, oriented}`: media de ítems **alineados por valencia**
  (reverse del ítem = `(min+max) − x`), de modo que toda dimensión queda "mayor = mejor".
- `cronbach_alpha(df, cols)` para la vista académica.
- Clasificación (semáforo) sobre el puntaje orientado usando el rango real de escala.
- `ReportAnalytics.calculate_averages()` delega en este módulo (una sola verdad).

### C. Capa de IA — `src/ai/`, `src/core/`
- `GeminiClient` accesible como **singleton cacheado** vía
  `@st.cache_resource def get_client()`; usar esa instancia en chat, dashboard, trends.
- `KnowledgeBase`: leer API key desde `src.core.config.get_gemini_api_key()`
  (no `os.environ`); poblar seed al inicio; degradar con gracia si Chroma/embeddings
  no están (retornar contexto vacío, no romper).
- Cablear RAG: chat y recomendaciones del informe recuperan contexto (`query_knowledge`)
  y lo inyectan al prompt; citar fuentes reales. Reutilizar `ResponseRouter` y
  `PromptBuilder` (hoy huérfanos) en `chat.py` en vez de la lógica ad-hoc duplicada.
- `chromadb` a `requirements.txt`.

### D. Dashboard dual — `src/ui/dashboard.py`
- **Resumen ejecutivo**: cabecera KPI, semáforo único, top fortalezas/riesgos, alertas.
- **Por dimensión**: gauge real (plotly indicator) + **una** barra diverging de
  distribución + estadísticas; diferencial semántico renderizado como bipolar.
- **Vista académica** (tab/toggle): α de Cronbach, tablas descriptivas, matriz de
  correlación, comparativas por grupo con N y tamaño de efecto, agregados poblacionales.
- `@st.cache_data` en cálculos; reutilizar `render_filtering_sidebar` (multiselect) y
  botón de descarga de datos filtrados.
- Paleta consistente y legible en claro/oscuro.

### E. Reportes PDF — `src/reports/`
- `ReportBuilder.build()` como alias de `build_report()` (retorna bytes); corregir
  `dashboard.py` para usar los bytes. Corregir bug `(SD)`→`(LB)`.
- Restaurar tildes (latin-1 soporta español; dejar de eliminarlas).
- Comparativas por más grupos (configurable). Anexo académico (α, tablas) opcional.
- Recomendaciones IA fundamentadas con citas del RAG.

### F. Listo para entregar
- Eliminar legacy y código muerto: `src/data/preprocessor.py`,
  `scripts/analizer_legacy.py`, scripts de depuración one-off.
- Limpiar artefactos versionados (PDFs de prueba, CSV/xlsx grandes); mover **1 dataset
  de ejemplo** a `samples/`. Actualizar `MASTER_DATA_PATH`.
- Reescribir `README.md`; actualizar `ARCHITECTURE.md`; unificar logging (quitar `print()`).
- `requirements.txt` correcto.

### G. Verificación
- `pytest -q` en verde (suite existente + nuevos tests de scoring e ingesta).
- Playwright end-to-end (con API key local): cargar datos → dimensiones puntúan →
  dashboard ejecutivo + académico → PDF por ambas rutas → chat con citas → tendencias.
  Capturas de cada paso.

## Riesgos
- **Valencia incorrecta** → puntajes engañosos. Mitigación: mapa documentado y editable
  en un solo lugar; el usuario (dominio) lo revisa.
- **Semántico PA/PC sin etiquetas** de adyacencia recuperables → se marca como
  "requiere verificación" en la metodología; se puntúa como bipolar 1-7 con valencia +1.
- **chromadb pesado** → degradación con gracia; RAG opcional, la app funciona sin él.
