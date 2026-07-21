# Observatorio de Salud Organizacional

Aplicación **Streamlit** para diagnóstico de bienestar y salud mental en el trabajo.
Ingiere resultados de encuestas, los transforma con rigor psicométrico, y genera valor
mediante un dashboard dual (ejecutivo + académico), un asistente de IA anclado en los
datos y en literatura científica, y reportes PDF profesionales.

## Qué hace

- **Ingesta robusta:** detecta y convierte escalas Likert en texto a numéricas, aplica
  reverse-coding a los ítems que lo requieren, protege identificadores (ID, correo,
  fechas) e imputa solo ítems de escala. Conserva columnas desconocidas sin pérdida.
- **Puntuación psicométrica válida:** cada dimensión se calcula orientando sus ítems por
  valencia (los negativos se invierten), de modo que **mayor = mejor bienestar**. Reporta
  α de Cronbach, N, desviación e IC 95 %. Ver [docs/METODOLOGIA_PUNTAJES.md](docs/METODOLOGIA_PUNTAJES.md).
- **Dashboard dual:**
  - *Ejecutivo:* KPIs, semáforo de bienestar (índice 0-100), fortalezas y áreas de atención.
  - *Académico:* tabla de fiabilidad, matriz de correlación entre dimensiones y
    comparativas por grupo con N.
- **Chat con IA (Gemini):** responde con puntajes reales calculados y cita fuentes del
  RAG (ChromaDB); enruta temas sensibles e individuales con salvaguardas.
- **Reportes PDF:** informe narrativo (portada, resumen ejecutivo, diagnóstico,
  comparativas, recomendaciones IA con citas) + anexo técnico/académico opcional.

## Estructura

```text
main.py                     Punto de entrada (navegación)
src/
  core/        config (diccionario de datos + valencia), estado, IA base, logger
  data/        processor (ingesta robusta), supabase_client, samples/
  analysis/    scoring (puntuación psicométrica — única fuente de verdad)
  ai/          gemini_client, knowledge_base (RAG), response_router, prompt_builder
  reports/     analytics, report_builder, pdf_generator
  ui/          dashboard, chat, trends, upload, reports, diagnostics, components/
docs/          METODOLOGIA_PUNTAJES.md, specs/
tests/         suite pytest
```

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Crea `.streamlit/secrets.toml`:

```toml
YOUR_API_KEY = "tu-api-key-de-gemini"   # también acepta la variable de entorno GEMINI_API_KEY

# Opcional (respaldo en la nube)
SUPABASE_URL = "https://..."
SUPABASE_KEY = "..."
```

Sin API key la app funciona igual, pero se desactivan el chat y las interpretaciones de IA.

## Ejecución

```bash
streamlit run main.py
```

Al iniciar carga un dataset de ejemplo ([src/data/samples/](src/data/samples/)) si no hay
un dataset maestro local. Sube el tuyo desde la pestaña **Cargar Datos**.
Panel técnico de diagnóstico: añade `?debug=1` a la URL.

## Pruebas

```bash
pytest -q
```

## Datos que puedes cargar

La app se adapta a dos tipos de dataset: el **esquema de Bienestar** (prefijos
`(SD)/(LB)/(BM)`, con diagnóstico completo e informe PDF) y **datasets genéricos**
(baterías con totales de subescala, p. ej. docentes) que entran en **modo Indicadores**
con foco en salud mental. Guía completa: **[docs/GUIA_DATASETS.md](docs/GUIA_DATASETS.md)**.

Puedes elegir entre datasets precargados en la barra lateral o subir el tuyo en
“Cargar Datos”. Los archivos de datos (`.csv`, `.xlsx`) y PDFs generados no se versionan
(ver `.gitignore`); solo se incluye un dataset de muestra pequeño para la demo.
