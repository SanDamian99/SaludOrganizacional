# Plan: limpieza y rendimiento de la plataforma

> **Estado:** plan para revisar. No cambia código.
> **Fecha:** 10-oct-2026.
> **Cuándo ejecutarlo:** después de que las dos sesiones en curso (`feature/docentes-fase1` y `feature/resumen-triangulacion`) fusionen a `main`. Las fases 1 y 2 tocan archivos que esas ramas no tocan y podrían adelantarse; las fases 3 a 5 tocan `main.py`, `src/core/state.py` y las vistas, y deben esperar.

---

## 1. Dónde está cada cosa hoy

### 1.1 Ramas y sesiones

| Worktree | Rama | Estado | Qué hace |
|---|---|---|---|
| `SaludOrganizacional` (este) | `main` | 5 commits **detrás** de `origin/main` (PR #23 triangulación pública y PR #24 video del municipio ya fusionados) | Base de trabajo; hay que hacer `git pull` antes de nada |
| `-docentes1` | `feature/docentes-fase1` | Creado hoy a las 18:08, al día con `origin/main`, sin commits propios aún | Ejecuta `docs/analisis/2026-10-10-propuesta-docentes.md`: escala fija, cortes publicados, IC 95 %, n ≥ 10, corrección de la puntuación, quitar botones de IA |
| `-resumen` | `feature/resumen-triangulacion` | Creado hoy a las 18:07, al día con `origin/main`, solo trae `docs/analisis/2026-10-10-hallazgos-triangulacion.md` sin versionar | Reescribe «Dónde coinciden» de la triangulación con los hallazgos robustos del análisis exploratorio |
| `-mapa` | `feature/video-municipio` | Fusionada (PR #24) | Se puede borrar el worktree |
| `-tripub` | `feature/triangulacion-publica` | Fusionada (PR #23) | Se puede borrar el worktree |
| `-b3` | `feature/almacen-datos-fuente` | Fusionada hace días | Se puede borrar el worktree |

Ramas locales ya fusionadas y sin uso: `feature/avance-datos`, `feature/relevancia-1`, `feature/tarjetas-alineadas`, `feature/triangulacion-publicada`, `feature/mapa-informes`, `feature/almacen-datos-fuente`, `feature/video-municipio`, `feature/triangulacion-publica`.

**Riesgo de choque con las dos sesiones.** Docentes toca `src/ui/dashboard.py`, `src/analysis/*`, `src/reports/indicator_report.py` y `main.py`. Triangulación toca `src/triangulacion/*` y `src/ui/views/triangulacion_investigador.py`. Este plan no debe tocar esos archivos hasta que fusionen; por eso las fases están ordenadas.

### 1.2 Mediciones de hoy (máquina local, Python 3.13, `.venv`)

| Medida | Valor | Comentario |
|---|---|---|
| Código de la app | 101 archivos, 24 510 líneas en `src/` | Vistas más grandes: `estudiantes_comunidad.py` (1 422), `estudiantes_investigador.py` (1 199) |
| Pruebas | 108 archivos, 11 MB en `tests/` | Ver §1.4 para la duración |
| Importar solo las vistas públicas | 186 MB de RSS | Antes de cargar ningún dato |
| Importar todas las vistas | 223 MB de RSS | — |
| Importar `src.ui.estudiantes` | 532 ms | De los cuales 424 ms son `scipy.stats`, importado en lo alto de `src/estudiantes/stats.py` |
| Importar `src.core.state` | 285 ms | Trae `pandas` y, por `dashboard`, `matplotlib.pyplot` (249 ms) |
| Importar `src.ui.reports` | 369 ms | `report_builder` → `analytics` → matplotlib, importados siempre en `main.py`, aunque la página sea otra |
| `obs360.resultados` | 12 194 filas en 9 corridas | La lectura pública baja la corrida vigente en lotes de 1 000 con `select("*")` |
| Entornos locales | `.venv` 1,1 GB + `venv` 852 MB | Dos entornos para el mismo proyecto |

### 1.3 Problemas de rendimiento y memoria encontrados

Ordenados por impacto en el despliegue público (Streamlit Community Cloud, ~1 GB de RAM por app, proceso compartido entre visitantes).

1. **El modo público carga el dataset de docentes en cada sesión nueva.** `main.py` llama a `init_session_state()` **antes** de comprobar `_PUBLICO`, y `init_session_state` descarga la versión activa de docentes desde Storage, la pasa por `ExcelProcessor` y guarda el DataFrame en `st.session_state.df`. En la app pública nadie ve docentes. Coste: una descarga + procesamiento por visitante (la caché de `_procesar_desde_storage` lo evita 10 min, pero `st.cache_data` **copia** el DataFrame en cada acceso, así que cada sesión conserva su propia copia en memoria).
   Archivos: `main.py:21`, `src/core/state.py:13-56`.

2. **`st.cache_data` con DataFrames grandes copia en cada acceso.** `load_dataset`, `_procesar_desde_storage` y las tres funciones de `dashboard.py` devuelven DataFrames por `cache_data`; cada rerun deserializa una copia. Para datos de solo lectura `st.cache_resource` comparte el objeto entre sesiones (ya se usa así en estudiantes y cuidadores). Hay que garantizar que nadie mute el objeto compartido (las vistas usan funciones puras tipo `subconjunto`, que devuelven copias filtradas; conviene verificarlo con una prueba).
   Archivos: `src/data/loader.py:55,84,93`, `src/ui/dashboard.py:25,30,343`.

3. **Importaciones pesadas en lo alto de módulos que no las necesitan en cada página.**
   - `scipy.stats` en `src/estudiantes/stats.py` (424 ms, se importa al abrir cualquier página de estudiantes, incluida la pública que solo lee cifras ya calculadas).
   - `matplotlib`/`seaborn` en `src/ui/dashboard.py`, `src/ui/views/estudiantes_comunidad.py`, `src/ui/views/estudiantes_investigador.py`, `src/reports/*`, `src/geo/mapa_figura.py`. Matplotlib solo hace falta para generar PDF o la figura del mapa; en pantalla se usa Plotly.
   - `main.py` importa `src.ui.reports` (y con él `report_builder`, `analytics`, matplotlib) en todas las páginas del modo completo.
   Efecto: arranque más lento y 100–150 MB de RSS base que nunca se liberan.

4. **El PDF de una página se cachea con `max_entries=64` por vista** (`estudiantes_comunidad._pdf_de`, `cuidadores_comunidad._pdf_de`). Cada entrada guarda el PDF (bytes) y la clave es el HTML completo. Con 64 combinaciones de rol × colegio × grado por vista, son hasta 128 PDF en memoria sin TTL. Además el HTML se genera en cada rerun para calcular la clave, aunque el usuario no pulse el botón.

5. **Se crea un cliente de Supabase por llamada.** `src/estudiantes/lectura._cliente()`, `src/cuidadores/lectura`, `src/estudiantes/avance._cliente()` llaman a `create_client` cada vez (cada llamada abre un `httpx.Client` nuevo). `vista_previa.cliente_autenticado` ya lo guarda por sesión; el cliente anónimo de lectura debería ser un `st.cache_resource` único por proceso.

6. **Lectura pública con `select("*")`.** La corrida vigente se baja entera, incluido `detalle` (JSON) de todas las filas. Si solo hace falta `detalle` para las filas `tipo = ingesta`, se puede pedir columnas concretas y reducir el payload. Medir primero el tamaño real de una corrida.

7. **Políticas RLS permisivas duplicadas** (aviso de rendimiento de Supabase): `obs360.corridas` y `obs360.resultados` tienen dos políticas SELECT para `authenticated` («cargador lee todas» y «lectura pública de publicadas»), y `public.processed_data` tiene dos SELECT para `anon`. Cada consulta evalúa ambas. Se funden en una sola con `OR`. Ver [linter 0006](https://supabase.com/docs/guides/database/database-linter?lint=0006_multiple_permissive_policies).

8. **Dependencias que se instalan y no se usan, o se usan en un solo sitio prescindible.**
   - `openpyxl` y `xlrd`: 0 importaciones en `src/`, `main.py` y `scripts/` (pandas las usa por detrás para `.xlsx`/`.xls`; `xlrd` solo para `.xls` antiguos; conviene confirmar si queda algún `.xls`).
   - `seaborn`: 1 archivo. Reemplazable por matplotlib directo.
   - `chromadb` (+ onnxruntime, tokenizers, ~400 MB instalados): solo el RAG del chat de docentes, que la auditoría de relevancia marca como candidato a quitar.
   - `google-generativeai`: chat, «Interpretar con IA» (que la propuesta de docentes quita) y «análisis prospectivo» de Tendencias (QUITAR confirmado en la auditoría).
   - `pytest` y `pytest-mock` en `requirements.txt`: se instalan en el despliegue sin necesidad.
   - `watchdog`: el comentario dice que se añadió para forzar reinicios del despliegue.

9. **Código muerto y artefactos en el repositorio.**
   - `src/ui/social.py` y `src/data/seed_data.py` no se importan desde ninguna página; ambos dependen de `src/data/supabase_client.py` (`SupabaseManager`, tabla `public.processed_data`), el camino viejo anterior al esquema `obs360`.
   - `supabase_setup.sql` y `SUPABASE_SETUP.md` (nov-2025) describen ese esquema viejo; las migraciones vigentes están en `supabase/`.
   - Vistas de bienestar «BM» del dashboard (resumen ejecutivo, semáforo, gauge, `render_tank`) solo se ven con el CSV demo, no con los datos reales (auditoría §1.2). La sesión de docentes decide qué pasa con ellas; aquí solo se anota.
   - Archivos sueltos en la raíz sin versionar: 7 PNG de julio, `informe_general.pdf` (4,4 MB), `test_output.pdf`, `test_render_report.pdf`, dos `.docx`, `__pycache__/` con `.pyc` de Python 3.10 y 3.13, `logs/` con registros de febrero.
   - Dos entornos virtuales (`.venv` y `venv`), casi 2 GB.
   - `.chroma/` local.
   - `packages.txt` lleva un comentario de «reinicio forzado» que ya no aplica.

10. **Funcionalidades que la auditoría de relevancia ya marcó QUITAR** y que pesan en código y dependencias: análisis de tendencias, botones «Interpretar con IA», heatmap de correlaciones, y probablemente el chat (PREGUNTAR). Quitarlas es lo que permite soltar `chromadb` y `google-generativeai`.

### 1.4 Pruebas

`pytest -q -x --durations=10` en `main` (d571e5f): **1 414 pasan, 8 se saltan, 47 avisos, 282 s (4 min 42 s)**.

Las diez más lentas suman 68 s y casi todas renderizan páginas enteras con Streamlit o llaman a Gemini con reintentos:

| s | Prueba |
|---|---|
| 11,2 | `test_chatbot_analysis.py::test_chatbot` |
| 10,1 | `test_triangulacion_pagina.py::test_con_datos_muestra_las_pestanas_sin_nada_individual` |
| 8,0 | `test_cuidadores_pagina.py::test_con_datos_muestra_las_pestanas_y_el_filtro_de_ola` |
| 6,9 | `test_report_generation.py::test_report_generation` |
| 6,8 | `test_cuidadores_pipeline.py::test_filtro_de_ola` |
| 6,6 | `test_trend_analysis.py::test_trend_analysis` |
| 6,0 | `test_gemini_client.py::test_api_failure_uses_fallback` |
| 4,6 | `test_modo_despliegue.py::…[comunidad]` |

Tres de ellas (`chatbot`, `trend_analysis`, `gemini_client`) desaparecen con la fase 2 si se quitan el chat y las tendencias. Un aviso de `postgrest` (`verify` deprecado) indica que conviene fijar la versión de `supabase` en `requirements.txt`.

---

## 2. Plan por fases

Cada fase es una rama corta, con pruebas en verde y una medición antes/después. Las mediciones se hacen con el mismo comando para poder compararlas:

```bash
# Tiempo de importación y memoria base
OBS360_MODO=comunidad python -X importtime -c "import src.ui.estudiantes, src.ui.views.estudiantes_comunidad, src.ui.views.cuidadores_comunidad" 2> importtime.txt
sort -t'|' -k2 -rn importtime.txt | head -20
OBS360_MODO=comunidad python -c "import resource, src.ui.estudiantes, src.ui.views.estudiantes_comunidad, src.ui.views.cuidadores_comunidad; print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024/1024, 'MB')"
# Pruebas
python -m pytest -q --durations=10
```

### Fase 0 · Línea base y orden en el repositorio (sin esperar a las sesiones)

No toca código de la app. Se puede hacer hoy.

- [ ] `git pull` en `main` (está 5 commits detrás).
- [ ] Guardar las mediciones de §1.2 y la duración de las pruebas en `docs/analisis/2026-10-10-linea-base-rendimiento.md`.
- [ ] Borrar worktrees de ramas fusionadas: `-b3`, `-mapa`, `-tripub` (`git worktree remove`), y las ramas locales fusionadas (`git branch -d`). No tocar `-docentes1` ni `-resumen`.
- [ ] Borrar un entorno virtual (dejar `.venv`, que es el de Python 3.13 que usa `runtime.txt`).
- [ ] Mover fuera del repositorio o borrar: los 7 PNG de la raíz, `informe_general.pdf`, `test_output.pdf`, `test_render_report.pdf`, `__pycache__/` de la raíz, `logs/`. Los dos `.docx` van a `docs/comunicaciones/` si el equipo los quiere conservar (están ignorados por git solo si se añade `*.docx` a `.gitignore`).
- [ ] Añadir `*.docx` y `.chroma/` ya está; añadir `.pytest_cache/` a `.gitignore`.
- [ ] Decidir con el usuario qué hacer con `docs/analisis/` y `docs/comunicaciones/` sin versionar en `main` (hoy están en el worktree principal, y la sesión de triangulación tiene una copia del de hallazgos).

### Fase 1 · Supabase (sin esperar a las sesiones)

- [ ] Migración `10f`: fundir las dos políticas SELECT de `obs360.corridas` y `obs360.resultados` para `authenticated` en una sola (`publicada OR es_cargador()`), y las dos de `public.processed_data` para `anon` en una. Comprobar después con el linter de rendimiento que no quedan avisos.
- [ ] Si `public.processed_data` ya no la usa nadie (solo `supabase_client.py`, que es código muerto), proponer dejarla de solo lectura y marcarla para borrado en una migración posterior, cuando se confirme que el despliegue no la toca.
- [ ] Medir el tamaño real de la corrida vigente (`select count(*), pg_column_size(detalle)` agrupado por `tipo`) para decidir si vale la pena pedir columnas concretas en `_traer_filas`.

### Fase 2 · Dependencias y código muerto (después de fusionar docentes, porque decide el destino del chat y los botones de IA)

- [ ] Quitar `src/ui/social.py`, `src/data/seed_data.py`, `src/data/supabase_client.py`, `supabase_setup.sql`, `SUPABASE_SETUP.md`, y sus pruebas si las hay.
- [ ] Quitar «Análisis de tendencias» y «análisis prospectivo» (QUITAR confirmado).
- [ ] Si el equipo confirma quitar el chat: quitar `src/ai/knowledge_base.py`, `src/ui/chat.py`, `chromadb` y `google-generativeai` de `requirements.txt`, y el aviso de API key de `main.py`. Si decide conservarlo: dejar el chat pero cargar `chromadb` solo al entrar a esa página (ya se importa dentro de la clase; verificar que `knowledge_base` no se importe desde `main.py` ni `state.py`).
- [ ] `requirements.txt`: quitar `pytest`, `pytest-mock` (van a `requirements-dev.txt`), `seaborn` (reemplazar su único uso), `xlrd` si no quedan `.xls`, y revisar `watchdog`. Fijar versiones máximas (`<2`, `<3`) para que Streamlit Cloud no cambie de versión mayor sin aviso.
- [ ] Medir: tamaño del entorno instalado antes/después (`pip list --format=freeze | wc -l`, `du -sh .venv/lib`) y tiempo de arranque en frío del despliegue.

### Fase 3 · Arranque y memoria del modo público (después de fusionar las dos sesiones: toca `main.py` y `state.py`)

- [ ] En `main.py`, mover la comprobación de `_PUBLICO` **antes** de `init_session_state()`, o hacer que `init_session_state` no cargue docentes cuando el modo es comunidad. Prueba: en modo comunidad, `st.session_state.df` sigue siendo `None` y no se llama a `dataset_activo_en_storage`.
- [ ] Cargar docentes de forma perezosa también en el modo completo: solo cuando la página sea Docentes, Chat, Carga o Reportes (las que lo usan). Estudiantes, Cuidadores y Triangulación no lo necesitan.
- [ ] Quitar `from src.ui.reports import render_reports_page` y `get_gemini_api_key` del nivel superior de `main.py`; importarlos dentro de su rama de la navegación, como ya se hace con el resto.
- [ ] Cambiar `load_dataset`, `_procesar_desde_storage` y las funciones cacheadas de `dashboard.py` a `st.cache_resource` (un solo DataFrame compartido por proceso). Añadir una prueba que verifique que las vistas no mutan el DataFrame cacheado (comparar un hash antes y después de renderizar con filtros).
- [ ] Medir: RSS del proceso con 1, 5 y 10 sesiones abiertas (Playwright abre 10 pestañas en modo comunidad y se lee la memoria con `ps`). Objetivo: que la memoria no crezca linealmente con las sesiones.

### Fase 4 · Importaciones perezosas y PDF (después de fusionar docentes: toca `dashboard.py` y los informes)

- [ ] `src/estudiantes/stats.py`: importar `scipy.stats` dentro de las funciones que lo usan (o en un módulo aparte). Igual en `src/triangulacion/estadistica.py`.
- [ ] `matplotlib`/`seaborn`: importar solo dentro de las funciones que dibujan para PDF o mapa (`src/reports/*`, `src/geo/mapa_figura.py`, `estudiantes_informe`, `cuidadores_informe`), nunca en lo alto de una vista de pantalla.
- [ ] PDF de una página: construir el HTML y el PDF solo al pulsar el botón (`st.button` + `st.download_button` en dos pasos, o `on_click`), y bajar `max_entries` a 16 con `ttl=3600`. Hacer lo mismo en cuidadores.
- [ ] Cliente anónimo de Supabase: una función `cliente_lectura()` con `st.cache_resource` compartida por `estudiantes.lectura`, `cuidadores.lectura`, `triangulacion.lectura` y `estudiantes.avance`. Mantener `_cliente()` en las pruebas con el cliente falso de `tests/supabase_falso.py`.
- [ ] Si la fase 1 lo justifica, `_traer_filas` pide columnas concretas y `detalle` solo para `tipo = ingesta`.
- [ ] Medir: tiempo de importación de las vistas públicas (objetivo: < 150 ms sin scipy ni matplotlib) y RSS base (objetivo: < 120 MB).

### Fase 5 · Pruebas y estructura (cuando todo lo anterior esté fusionado)

- [ ] Marcar las pruebas lentas (las 10 que lista `--durations`) con `@pytest.mark.slow` y dejar la suite rápida como la de cada commit.
- [ ] Revisar `tests/fixtures/lote_sintetico_antes_de_alertas.json` (380 KB, el archivo más grande versionado): si se puede generar en la prueba, reemplazarlo.
- [ ] Partir `estudiantes_comunidad.py` (1 422 líneas): las funciones puras de datos (`prevalencia`, `prevalencia_por`, `contraste`, `grupos_visibles`, `subconjunto`…) a `src/estudiantes/vista_datos.py`; en la vista solo quedan render y textos. Mismo criterio para `estudiantes_investigador.py`. Esto no cambia comportamiento y facilita las pruebas sin Streamlit.
- [ ] Actualizar `ARCHITECTURE.md` y `DESPLIEGUE.md` con la política de caché (qué va en `cache_resource`, qué en `cache_data`, TTLs) y el procedimiento de medición de arriba.

---

## 3. Qué debe decidir el equipo antes de las fases 2 a 4

1. **Chat con IA:** se queda o se quita. Determina si salen `chromadb` y `google-generativeai` (la mayor reducción de tamaño del entorno).
2. **Vistas BM del dashboard** (solo visibles con el CSV demo): la sesión de docentes las conserva, las quita o las deja para investigadores.
3. **Tabla `public.processed_data`:** confirmar que ningún proceso externo la lee antes de retirar sus políticas y el código que la usa.
4. **`docs/analisis/` y `docs/comunicaciones/`:** si se versionan en `main` o quedan fuera del repositorio.

## 4. Orden de ejecución sugerido

```
hoy            → Fase 0, Fase 1
tras docentes  → Fase 2, Fase 4
tras ambas     → Fase 3
después        → Fase 5
```

Cada fase en su rama, PR a `main`, con la medición antes/después en la descripción del PR.
