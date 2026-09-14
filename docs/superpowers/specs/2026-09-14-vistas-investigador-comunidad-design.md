# Diseño — Esquema «Familias 360» y vistas para investigadores y comunidad

**Fecha:** 2026-09-14
**Estado:** borrador para aprobación (no implementar hasta aprobar)
**Rama propuesta:** `feature/vistas-investigador-comunidad`

## Contexto

La plataforma hoy sirve dos tipos de dataset: el esquema de Bienestar laboral `(SD)/(LB)/(BM)`
y el modo Indicadores para baterías con totales (`Docentes`). El proyecto Observatorio 360 tiene
un tercer dataset, la encuesta **«Cuidando al Cuidador»** (142 cuidadores, 172 niños de 17 colegios
oficiales de Chía, septiembre de 2025), que hoy la app no puede mostrar bien:

1. Trataría EPDS, MSPSS, APQ, PSI-SF y SDQ como «otros indicadores» sin dirección ni cortes.
2. No distingue unidad de análisis (niño vs cuidador; 30 cuidadores reportan dos hijos).
3. No vincula colegios entre docentes y familias (10 instituciones comunes).
4. El SDQ del archivo procesado venía mal codificado; ya existe un script reproducible que lo
   corrige desde el crudo (`recodificar_sdq_cuidadores.py` → `Datos_Cuidador_corregido.csv`).

El equipo investigador decidirá el ángulo del artículo con el one-pager
(`Onepager_Observatorio360_equipo.docx`). La plataforma debe servir a dos audiencias nuevas
independientemente del ángulo elegido: **investigadores** (lo necesario para escribir el paper)
y **comunidad** (padres, docentes, rectores, funcionarios: sencillo, accionable, claro).

## Objetivo

Cargar el dataset de familias con puntuación psicométrica válida y ofrecer dos vistas nuevas,
seleccionables por audiencia, reutilizando la arquitectura existente (config → scoring → ui).

## Alternativas consideradas

| Opción | Descripción | Pros | Contras |
|---|---|---|---|
| A. Extender el dashboard actual | Añadir catálogo de instrumentos y dos pestañas más al dashboard | Menor esfuerzo | Dashboard ya tiene 4 pestañas y 600 líneas; mezcla audiencias; sin unidad de análisis |
| **B. Esquema «Familias» + selector de audiencia (recomendada)** | Nuevo esquema de datos con catálogo y scoring propio; selector global «¿Quién eres?» que decide qué vista se renderiza para cualquier dataset | Límites claros por módulo; testeable; reutiliza filtros, IA y PDF | Requiere refactor ligero de `render_dashboard` para despachar por audiencia |
| C. Comunidad como sitio estático aparte | Vista comunidad publicada como página independiente generada desde la app | Máxima simplicidad para la comunidad | Dos superficies que mantener; pierde filtros y actualización |

Se elige **B**. Si más adelante se quiere un sitio público, la vista comunidad ya produce el
contenido (tarjetas + PDF) que se exportaría.

## Decisiones de diseño

- **Los datos crudos se conservan; los puntajes se calculan al leer**, como en el esquema de
  Bienestar. La corrección del SDQ y el reverse-scoring viven en código, no en el archivo.
- **Unidad de análisis explícita.** El esquema Familias declara `unit: "niño"` con
  `cluster: "ID_Cuidador"`. Las vistas muestran N de niños y N de cuidadores, y las variables del
  cuidador se deduplican al describir cuidadores.
- **Cortes clínicos sólo cuando existen y están citados.** SDQ (bandas de 4 niveles de sdqinfo,
  versión padres), EPDS (≥ 10 y ≥ 13, ambos configurables), PSI-SF y APQ sin corte (se reportan
  posición relativa y percentiles de la muestra, etiquetados como tal).
- **Mínimo de N para desagregar.** Ninguna vista muestra un grupo con menos de 10 casos
  (configurable `MIN_GROUP_N`). Aplica a colegio, curso, zona, quién responde.
- **Nunca datos individuales.** Los IDs (`ID_Cuidador`, `ID_Niño`) son columnas protegidas.
- **Lenguaje por audiencia.** El catálogo tiene, por instrumento, `label_tecnico`,
  `label_comunidad` y `que_significa` (una frase), más `que_puedo_hacer` por rol.

## Arquitectura

```text
src/core/config.py            + FAMILIAS_SCHEMA (unidad, clúster, columnas protegidas)
src/analysis/family_catalog.py  catálogo de instrumentos del esquema Familias (nuevo)
src/analysis/family_scoring.py  SDQ desde ítems, subescalas, bandas; índices barrial y APQ (nuevo)
src/analysis/school_link.py     normaliza códigos de colegio y une docentes + familias (nuevo)
src/analysis/research_stats.py  Tabla 1, α, correlaciones con IC, tamaños de efecto (nuevo)
src/ui/audience.py              selector «¿Quién eres?» y despacho de vistas (nuevo)
src/ui/views/investigador.py    vista Investigador (nuevo)
src/ui/views/comunidad.py       vista Comunidad (nuevo)
src/ui/dashboard.py             render_dashboard delega en audience.dispatch()
src/reports/community_report.py PDF de una página por colegio / municipio (nuevo)
src/ai/prompt_builder.py        + plantillas «metodología» y «mensaje comunitario»
docs/METODOLOGIA_PUNTAJES.md    + sección Familias (SDQ, EPDS, APQ, PSI, barrial)
tests/test_family_scoring.py, test_school_link.py, test_research_stats.py, test_audience.py
```

Detección: `is_family_dataset(df)` = tiene ≥ 20 columnas `SDQ\d+` o los 25 ítems entre
corchetes, más `EP_MP1`/`EDPS1`. Se añade a `PRELOADED_DATASETS` la entrada
`{"label": "Familias y niños (Cuidando al Cuidador)", "path": "Datos_Cuidador_corregido.csv"}`.

## Componentes

### 1. Catálogo del esquema Familias (`family_catalog.py`)

Cada entrada: `key`, `label_tecnico`, `label_comunidad`, `tema`, `higher_is_better`,
`rango_teorico`, `items`, `inversos`, `cortes` (lista de `{umbral, etiqueta, fuente}`),
`que_significa`, `que_puedo_hacer: {padre, docente, funcionario}`, `cita`.

Instrumentos: SDQ (5 subescalas, total dificultades, internalizante, externalizante, bandas),
EPDS-10, PSS-10, MSPSS-12 (total y 3 fuentes), APQ (IP, RP, DI, PP), PSI-SF (MP, ID, ND, total),
riesgo barrial (índice 0-10 y bandera «alto»), desempeño académico percibido (ordinal 0-5).

Direcciones: SDQ dificultades, EPDS, PSS, APQ_DI, APQ_PP, PSI, barrial → mayor = peor.
SDQ prosocial, MSPSS, APQ_IP, APQ_RP, desempeño → mayor = mejor.

### 2. Scoring (`family_scoring.py`)

- `score_sdq(df)`: acepta ítems `SDQ1..SDQ25` ya en 0-2 **o** los 25 ítems entre corchetes en
  texto; invierte 7, 11, 14, 21, 25; devuelve subescalas, total, bandas. Si detecta valores 0-3 o
  permutaciones (caso del archivo legado) **rechaza con mensaje** y remite al script de corrección;
  no intenta adivinar.
- `score_scales(df)`: totales de EPDS, PSS, MSPSS, APQ, PSI a partir de ítems si faltan los `_T`;
  si existen, los valida (suma de ítems == total ± 0) y reporta discrepancias en el diagnóstico.
- `neighborhood_index(df)`, `age_filter(df, 4, 17)`, `dedupe_caregivers(df)`.
- `reliability(df, key)`: α de Cronbach (y ω si `pingouin` no es necesario: α basta en v1).

### 3. Vínculo por colegio (`school_link.py`)

Tabla maestra `SCHOOL_CODES` (código → nombre oficial → sector → zona) para las 18 + 17
instituciones. `join_by_school(df_docentes, df_familias)` devuelve una fila por colegio con
N docentes, N niños, N cuidadores y medias de los indicadores clave, marcando `suficiente_n`.

### 4. Vista Investigador (`views/investigador.py`)

Pensada para producir el material de Métodos y Resultados de un artículo:

1. **Muestra**: N por unidad, criterios de inclusión aplicados (edad 4-17, quién responde),
   flujo de exclusiones, descripción sociodemográfica exportable.
2. **Tabla 1 de instrumentos**: ítems, rango, M, DE, mediana, % sobre corte, α, N válido.
   Exportable a CSV y a Word (docx) con formato APA.
3. **Correlaciones**: matriz Spearman/Pearson con IC 95 % bootstrap, p con corrección
   Benjamini-Hochberg, selección de variables, heatmap y tabla.
4. **Comparaciones por grupo**: variable de agrupación → medias, N, d de Cohen o delta de Cliff,
   prueba adecuada al tipo de variable; respeta `MIN_GROUP_N`.
5. **Modelo exploratorio**: regresión lineal múltiple con selección de predictores y covariables,
   errores estándar robustos por clúster (`ID_Cuidador`). Mediación queda para v2.
6. **Perfil 360 por colegio**: tabla de `join_by_school` con advertencia explícita de que no
   sostiene inferencia multinivel.
7. **Calidad de datos**: alertas del catálogo (SDQ legado, EPDS fuera de contexto, mismo
   informante, muestra de conveniencia) y reporte de imputación/faltantes.
8. **Texto de Métodos (IA)**: plantilla que rellena instrumentos, N, α y limitaciones con las
   cifras reales; el investigador edita. Citas del catálogo, no inventadas.
9. **Exportar**: paquete ZIP con tablas CSV, figuras PNG 300 dpi, diccionario de datos y
   metodología en Markdown.

### 5. Vista Comunidad (`views/comunidad.py`)

Selector de rol al entrar: **Soy madre/padre o cuidador · Soy docente u orientador ·
Soy rector o funcionario**. Todas las cifras son agregadas y con N mínimo.

- **Cinco tarjetas máximo**, cada una con: dato en lenguaje llano («1 de cada 5 niños muestra
  dificultades altas»), semáforo, «qué significa» y «qué puedo hacer» según el rol.
  Los mensajes se toman del catálogo (`que_significa`, `que_puedo_hacer`), no de la IA.
- **Ruta de atención fija**, siempre visible: Línea 106 (Cundinamarca), orientación escolar del
  colegio, Secretaría de Salud de Chía, Comisaría de Familia. Texto configurable en `config`.
- **Aviso**: «Estos resultados son un tamizaje de grupo, no un diagnóstico individual».
- **Rector / funcionario**: mapa de calor por colegio y por zona de los indicadores clave
  (solo colegios con N ≥ 10), y botón «Informe de una página» (PDF) con tres prioridades y tres
  acciones sugeridas, basadas en reglas del catálogo (p. ej., EPDS ≥ 13 > 25 % → «tamizaje y
  derivación de cuidadores»).
- **Padre/madre**: sin desagregación por colegio; tres mensajes de crianza positiva y apoyo
  social con enlaces a recursos oficiales (Kit Crianza de Red PaPaz, ICBF).
- **Docente**: prevalencias por rango de edad y señales de alerta observables en el aula
  con la instrucción de derivar a orientación, nunca de diagnosticar.

### 6. Selector de audiencia (`ui/audience.py`)

Radio en la barra lateral: **Ejecutivo · Académico · Investigador · Comunidad**. Para los
esquemas Bienestar y Docentes, Investigador reutiliza los cálculos actuales con las nuevas
tablas exportables; Comunidad muestra el mismo formato de tarjetas con el catálogo de
indicadores existente (`INDICATOR_CATALOG` gana los campos de lenguaje llano).

## Flujo de datos

```text
CSV corregido ──ingesta robusta──▶ df crudo ──family_scoring──▶ puntajes (niño / cuidador)
                                                 │
                     school_link ◀── docentes ───┘
                                                 ▼
                  audience.dispatch(df, puntajes, audiencia, rol)
                    ├─ investigador: research_stats → tablas/figuras/exports/IA métodos
                    └─ comunidad:    catálogo (mensajes) → tarjetas, ruta, PDF una página
```

## Manejo de errores

- SDQ con codificación inválida → la vista muestra el bloque de calidad con el error y un
  botón que descarga el script de corrección; no puntúa.
- Grupo con N < 10 → se oculta con nota «grupo omitido por tamaño».
- Sin API key → Investigador oculta «Texto de Métodos (IA)»; Comunidad no depende de IA.
- Colegio sin código en `SCHOOL_CODES` → aparece como «Otro» y se lista en diagnóstico.

## Pruebas

- `test_family_scoring.py`: SDQ con ítems sintéticos conocidos (incluye inversos), rechazo de
  codificación 0-3, totales validados contra ítems, filtro de edad, deduplicación.
- `test_school_link.py`: normalización de códigos con tildes/espacios, unión, `suficiente_n`.
- `test_research_stats.py`: α contra valor conocido, correlaciones con IC, d de Cohen, BH.
- `test_audience.py`: despacho por audiencia; `MIN_GROUP_N` oculta grupos pequeños; mensajes
  comunitarios provienen del catálogo.
- E2E Playwright: cargar dataset Familias → Investigador exporta ZIP → Comunidad rol rector
  genera PDF.

## Fuera de alcance (v1)

Modelos de mediación y multinivel, mapa geográfico con coordenadas, autenticación por rol,
publicación externa del sitio de comunidad, ω de McDonald.

## Riesgos

- **Cortes clínicos mal citados** → cada corte lleva fuente en el catálogo y el equipo lo revisa.
- **Sobreinterpretación comunitaria** → mensajes fijos revisados por el equipo, no generados.
- **Reidentificación en colegios pequeños** → `MIN_GROUP_N` y sin cruces de dos variables en
  la vista Comunidad.
- **Divergencia con el análisis del artículo** → `research_stats` es la única fuente de las
  tablas; el artículo debe citar la versión del script.

## Aprobación pendiente

1. ¿Aprobar la opción B y el alcance v1?
2. ¿Cortes por defecto: EPDS ≥ 13 y bandas SDQ de 4 niveles?
3. ¿`MIN_GROUP_N = 10`?
