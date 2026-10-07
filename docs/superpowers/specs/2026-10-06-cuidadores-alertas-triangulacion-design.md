# Observatorio 360 · Cuidadores, alertas y triangulación — diseño

**Fecha:** 6 de octubre de 2026 · **Estado:** aprobado en conversación, pendiente de revisión escrita
**Rama:** `feature/360-cuidadores-alertas-triangulacion` (sale de `feature/informe-estudiantes-html`, PR #1)

## 1. Qué se pide y por qué

El equipo investigador (Tatiana, Diana) pidió, el 6 de octubre de 2026:

1. Que los grados con 10 o más estudiantes **se vean** en el dashboard de estudiantes, también dentro de un colegio. Entregaron la lista de referencia (§3.1).
2. **Alertas** en la vista del colegio (docente y rector) y en los informes, activadas por los ítems marcados con `*`, con recomendaciones de atención y rutas para familias, rector y municipio. La alerta no debe alarmar; debe **motivar la indagación y la acción oportuna**.
3. Un **módulo de cuidadores** (formulario «Cuidando al Cuidador»), con vista de investigadores y vista de comunidad (colegio, familia, municipio) con la misma lógica que estudiantes.
4. Una vista **solo para investigadores** que **triangule** docentes, cuidadores y estudiantes: patrones, puntos en común y tensiones.
5. En la navegación, «Dashboard» pasa a **«Docentes»**: un dashboard por población más uno de triangulación.

La plataforma funciona bien y está en uso: todo esto es un **complemento**. Ninguna fase puede cambiar el comportamiento existente salvo donde se pide.

## 2. Decisiones tomadas con el usuario

| Tema | Decisión |
|---|---|
| Unidad de la alerta | **Por grupo** (colegio, grado, colegio × grado; n ≥ 10). Nunca un estudiante identificable. |
| Ítems de alerta | **Malestar emocional:** los 6 ítems del SDQ marcados con `*`, en los dos niveles. **Desesperanza:** propuesta propia sobre el RCADS, solo secundaria (§6.2). |
| Triangulación | Dos capas: **por colegio y grado** (los tres actores) y **díadas niño–cuidador** enlazadas por un identificador cifrado. |
| Alerta del adulto | **Sí:** EPDS ítem 10 o EPDS ≥ 13, alerta por grupo en el módulo de cuidadores, visible para colegio y municipio. |
| Trabajo pendiente | Los informes se integraron primero (commit `8287201`, PR #1); este trabajo sale encima. |
| Despliegue público | Muestra **Estudiantes 360 y Cuidadores 360** (vistas de comunidad). Docentes y Triangulación, solo en los modos completo e investigador. |

## 3. Datos

### 3.1 Estado y archivos

| Archivo | Dónde | Estado |
|---|---|---|
| Estudiantes secundaria (CSV, 18-sep, 979 filas) | `datos_fuente_360/estudiantes/` | **Desactualizado** |
| Estudiantes primaria (CSV, 18-sep, 283 filas) | `datos_fuente_360/estudiantes/` | Lo reemplaza el xlsx de abajo |
| Estudiantes primaria (xlsx, hasta 6-oct, 355 filas, ítems con `*`) | `datos_fuente_360/estudiantes/entrantes/` | Nuevo; mismas 89 columnas que el CSV salvo el `*` |
| Cuidadores (xlsx, sep-2025 a sep-2026, 779 filas, 209 columnas) | `datos_fuente_360/cuidadores/` | Nuevo; reemplaza al `Datos_Cuidador_corregido.csv` de 172 filas |

Los dos xlsx llegaron a la raíz del repositorio. Se movieron fuera de él el 6-oct (traen nombres de menores y teléfonos), y la prueba `test_el_repositorio_no_guarda_hojas_de_calculo_en_la_raiz` vuelve a pasar.

**Falta: la exportación actualizada de secundaria.** La lista de los investigadores coincide exactamente con nuestros datos en La Balsa (sexto 24, séptimo 52, noveno 29, décimo 32) y en Laura Vicuña (95 / 69 / 93 / 90 / 90). Pero tiene grupos que nuestro CSV no trae:

- CdP: sexto 16 y séptimo 24 (nosotros: 2 y 0).
- JJC: décimo 83 (nosotros: 0) y noveno 59 (nosotros: 58).
- SJMEB sede Samaria: sexto 50 (nosotros: 35).

Esos grupos aparecerán cuando llegue esa exportación. Ninguna corrección de código los produce.

### 3.2 Formulario de cuidadores (columnas por posición)

| Bloque | Columnas | Opciones |
|---|---|---|
| Consentimiento, quién responde, nombres (cuidador, hijo), edad, sexo, colegio, tipo, curso | 0–9 | 756 «Sí autorizo», 23 «No autorizo» |
| Contacto con madre y padre, edades, nivel educativo, hermanos, desempeño académico, zona, estrato | 10–19 | — |
| Riesgo barrial (5) | 20–24 | No / Sí baja frecuencia / Sí muy frecuente |
| PSS-10 | 25–34 | Nunca … Frecuentemente / Casi siempre (5 opciones) |
| EPDS-10 | 35–44 | 4 opciones con redacción propia por ítem |
| MSPSS-12 (del cuidador) | 45–56 | Escala de 5 puntos, igual que estudiantes |
| APQ (crianza, 25 ítems, incluye castigo físico 78–80 y grito 81) | 57–81 | Nunca … Siempre |
| Estrés parental, parte 1 (20) y parte 2 (19) = **39 ítems** | 82–120 | Muy en desacuerdo … Muy de acuerdo |
| SDQ padres del hijo 1 | 121–145 | No es cierto / Un tanto cierto / Absolutamente cierto |
| ¿Responde por otro hijo? + datos del hijo 2 | 146–152 | 217 «Sí» |
| SDQ padres del hijo 2 | 153–177 | Ídem |
| Futuras investigaciones, **teléfono** | 178–179 | Se descartan en la carga |
| Vacías | 180–185, 200–208 | Se ignoran |
| ARI padres del hijo 1 / hijo 2 | 186–192 / 193–199 | No es cierto / A veces cierto / Cierto |

Quién responde: Mamá 586, Papá 141, otros 52.

Por colegio, con consentimiento: LauV 448, JJC 119, SJMEB 27, LaBalsa 24, DiosCh 13, Bojacá 12. Además, 103 respuestas tienen colegio escrito libremente, sobre todo Conaldi/Diversificado (CND) y Santa Lucía (SaLu).

El curso viene como texto libre: «501», «1002», «2A», «Transición»…

Hay dos olas: **septiembre de 2025 (145)** y **2026 (634)**.

## 4. Principios que no se negocian (heredados)

- **Nada individual.** Ningún nombre, teléfono, fila ni grupo con menos de `MIN_GROUP_N = 10` en pantallas, informes, exportaciones de comunidad ni Supabase.
- **A Supabase solo suben agregados.** El `CHECK n >= 10` sigue siendo la última barrera.
- **Los textos sobre salud mental son fijos** y revisables por el equipo, en catálogos. Nunca los redacta la IA en tiempo de ejecución.
- **El despliegue público no importa** módulos de investigación (corte en `main.py` antes de importarlos).
- Cada fase llega en su **propio PR**, con la suite verde (salvo las 2 fallas preexistentes de `test_knowledge_base`) y la revisión con Playwright.

## 5. Fases

Orden: 0 → 1 → 2 → 3 → 4 → 5. Cada fase es entregable sola. Las fases 3, 4 y 5 dependen de la tabla de colegios compartida (§5.2).

### 5.0 Orden previo (hecho en parte)

- [x] Commit de los informes y PR #1.
- [x] Los xlsx fuera de la raíz del repositorio.
- [ ] Pedir a los investigadores la exportación actualizada de secundaria.

### 5.1 Fase 1 · Los grados que no se ven

**Causa A, datos:** CSV de secundaria viejo (§3.1).

**Causa B, código:** el despliegue no publica el cruce colegio × grado. Cuando se elige un colegio, el selector de grado queda bloqueado (`estudiantes_comunidad._selector_grupo`) y el informe no trae «Por grado en el colegio».

Cambios:

1. **Carga:**
   - `ingest` acepta `.xlsx` y quita el `*` inicial de los encabezados. El `*` se conserva como metadato para la fase 3: `ingest.items_marcados(raw) -> set[str]`.
   - `localizar_formularios` resuelve duplicados por formulario y se queda con el archivo más reciente cuando hay CSV y xlsx del mismo formulario.
   - El xlsx de primaria pasa de `entrantes/` a `estudiantes/` y el CSV viejo queda en `otros/archivo/`.
2. **Pipeline:** `subanalizar` añade la agrupación `"Colegio×Grado"`, con la clave de grupo `"LauV|Sexto"`, solo para las celdas con n ≥ 10.
3. **Supresión complementaria (nueva).** Para cada colegio, el *resto* es el total del colegio menos la suma de las celdas de grado publicadas.
   - Si el resto está entre 1 y 9, se retira también la celda publicada más pequeña, y así hasta que el resto sea 0 o ≥ 10.
   - Sin esto, la cifra de un grado pequeño se obtendría restando.
   - La misma comprobación se aplica a `Colegio` frente al total del nivel y a `Grado` frente al total del nivel.
   - Es una función pura `stats.suprimir_complementarias(conteos_hijos, total) -> set[grupo]`, probada aparte.
4. **Publicar y leer:** `publicar._aplanar_subgrupo` y `lectura._subgrupos` aceptan la agrupación nueva.
5. **Vista e informes:**
   - Con datos publicados, `subanalisis` resuelve colegio + grado contra `"Colegio×Grado"`.
   - El selector de grado se desbloquea y solo ofrece los grados con celda publicada.
   - La tabla «Por grado en el colegio» del informe sale también en el despliegue.
6. **Aceptación:**
   - Una prueba toma la lista de los investigadores como verdad para los colegios cuyos datos ya coinciden (LaBalsa, LauV).
   - Cuando llegue la exportación nueva, la prueba se extiende a todos los colegios.
   - Ningún grupo con n < 10 aparece, ni directo ni deducible por resta.

### 5.2 Pieza compartida · Tabla única de colegios

Hoy hay tres mapas divergentes:

- `estudiantes/ingest._COLEGIOS`, en códigos.
- `scripts/preparar_docentes.COLEGIOS`, que guarda nombres legibles en la columna `Colegio` de docentes.
- El CSV viejo de cuidadores, en códigos con variantes («Bojaca» sin tilde).

Se crea `src/core/colegios.py` con `normalizar(texto) -> (codigo, nombre, sede)`, `nombre(codigo)` y `codigo_desde_nombre(nombre)`.

- Une las claves de los tres mapas y agrega las variantes de texto libre de cuidadores: Conaldi, Conadi y Diversificado → CND; Santa Lucía → SaLu; «Jj casas» → JJC; Balaguer → SJMEB; Santa María del Río → SMR.
- `estudiantes.ingest` y `preparar_docentes` pasan a usarla sin cambiar sus salidas. Una prueba de no regresión compara los resultados antes y después sobre los datos reales.

### 5.3 Fase 2 · Navegación

- `src/core/modo.py` define constantes de página: `PAGINA_DOCENTES = "Docentes"`, `PAGINA_ESTUDIANTES`, `PAGINA_CUIDADORES = "Cuidadores 360"`, `PAGINA_TRIANGULACION = "Triangulación 360"`.
- `main.py` las usa en `_todas` y en el enrutamiento. Orden: Docentes, Estudiantes 360, Cuidadores 360, Triangulación 360, Chat con IA, Cargar Datos, Análisis de tendencias, Reportes.
- **Páginas por modo:**
  - Completo: todas.
  - Investigador: todas (como hoy).
  - Comunidad: **Estudiantes 360 y Cuidadores 360**, con un selector de página. El corte de importaciones de `main.py` se extiende para que tampoco se importen Triangulación ni la vista de investigador de cuidadores.
- Hay que renombrar las referencias listadas en el mapa de arquitectura: `main.py:96,113`, `modo.py:90`, `state.py:63`, `reports.py:19,24`, `dashboard.py:2,559`, `tests/test_modo_despliegue.py:114,195,233-236`, `ARCHITECTURE.md`, `README.md` y `DESPLIEGUE.md`. No se tocan las menciones al «dashboard» de Supabase.
- El título de la página de docentes pasa a «📊 Docentes · Salud organizacional».
- Una sesión con `"Dashboard"` guardado en el estado no debe romperse: si la página guardada no existe, se abre la página por defecto.

### 5.4 Fase 3 · Alertas de estudiantes: «Señales para actuar a tiempo»

#### Definiciones, nivel estudiante (puras, en `src/estudiantes/alertas.py`)

**Malestar emocional** (primaria y secundaria). Son los ítems marcados con `*`: SDQ 5 (me enojo y pierdo el control), 6 (solitario), 8 (preocupado), 13 (triste o con ganas de llorar), 19 (se burlan de mí) y 24 (muchos miedos).

- Hay señal si el estudiante responde **«Muy cierto» en 3 o más de los 6**.
- Calibración con los datos actuales: 8,8 % en secundaria y 15,6 % en primaria. Con «2 o más» saldría 22 % y 33 %, que sería poco específico.

**Desesperanza** (solo secundaria; primaria no respondió el RCADS).

- Hay señal si responde RCADS 18 «Pienso acerca de la muerte» = **Siempre**, o RCADS 18 ≥ **Con frecuencia** junto con RCADS 16 «Me siento que no valgo nada» ≥ **Con frecuencia**.
- Calibración: 17,0 %. Una regla amplia que sumaba RCADS 1 «triste o vacío» y 4 «nada me divierte» daba 33 %.
- Se descartaron esos dos ítems porque miden ánimo y anhedonia, no desesperanza.
- **Límite que hay que decir:** el instrumento no tiene una escala de desesperanza. El nombre visible es «Señales de desesperanza y pensamientos de muerte».

Los ítems y umbrales viven en el catálogo (`catalog.ALERTAS`), no en el código. Cuando el equipo marque el formulario de secundaria, se ajusta el catálogo y una prueba verifica que coinciden los ítems con `*` del archivo y los de `ALERTAS`.

#### Agregación y activación (por grupo, n ≥ 10)

Para cada grupo se calcula el porcentaje con señal, su IC de Wilson y el número de casos. La alerta tiene dos estados y **nunca se oculta**:

- **«En seguimiento»** (gris sereno): se muestra siempre. Texto tipo: «1 de cada 6 estudiantes muestra señales. No es un diagnóstico: indica dónde mirar primero». Incluye qué hacer y la ruta.
- **«Prioridad»** (naranja, nunca rojo): se activa en un grupo cuyo IC queda por encima del valor del municipio, la misma regla de `comparar()` que ya usan los informes. Dentro de un colegio se listan los grados en «Prioridad», en orden canónico y no por ranking.

**Por qué no hay un umbral fijo:** con los datos actuales, cualquier umbral razonable se activa en casi todos los grupos (desesperanza entre 11 % y 33 % por grado). Una alerta permanente deja de ser alerta.

#### Dónde y para quién

| Rol | Malestar | Desesperanza | Qué ve |
|---|---|---|---|
| Colegio (rector, docente, orientación) | Sí | Sí | Panel arriba de las tarjetas, grados en «Prioridad», qué hacer y ruta escolar |
| Municipio | Sí | Sí | Por colegio y por grado, con qué hacer de política y red |
| Familia | Sí | **No** (igual que `ideacion` hoy) | Qué hacer en casa y a dónde acudir |

- Entra en el informe del colegio, el informe de la Secretaría (una tabla de alertas por colegio) y el resumen PDF de una página. En este último, un recuadro compacto antes de las tarjetas, sin pasar de una página.
- La tarjeta actual «Pensamientos sobre la muerte» se mantiene. El panel de alertas la referencia en vez de duplicarla.
- **Investigadores:**
  - Definiciones, prevalencias por grupo y distribución de cada ítem.
  - Un análisis de sensibilidad: umbrales de 2, 3 y 4 ítems, y la regla amplia frente a la estricta.
  - Exportación en `alertas.csv` dentro del ZIP.
- **Supabase:** filas `tipo = "alerta_grupo"` (n ≥ 10) y mensajes por rol en `obs360.mensajes`.

#### Rutas por rol (catálogo)

`RUTA_ATENCION` pasa a ser `RUTAS[rol][tipo]`, para estudiante o adulto. Los textos y los teléfonos los aporta y aprueba el equipo; **el código no inventa números**. Mientras no estén aprobados, la ruta muestra las entradas actuales y un aviso interno visible solo en el modo completo: «ruta pendiente de validación».

### 5.5 Fase 4 · Cuidadores 360

Es un paquete espejo de `src/estudiantes/`, que reutiliza `stats` y el patrón de vistas.

| Archivo | Responsabilidad |
|---|---|
| `src/cuidadores/catalog.py` | Escalas, ítems por posición, inversos, bandas, `MENSAJES`, `ALERTAS`, `RUTAS` de adulto |
| `src/cuidadores/ingest.py` | Consentimiento, hash de cuidador (`C`+sha1[:8]) y de niño (`N`+sha1[:8], con la misma normalización que estudiantes, §5.6), descarte de nombres y teléfono, colegio vía `core/colegios`, curso libre → grado canónico, ola (2025/2026), expansión del hijo 2 y deduplicación |
| `src/cuidadores/scoring.py` | Puntuaciones por escala desde el texto crudo |
| `src/cuidadores/pipeline.py` | `AnalisisCuidadores` con dos marcos: **cuidador** (escalas del adulto) y **niño** (SDQ y ARI de padres, agrupado por cuidador); subgrupos Colegio, Grado y Colegio×Grado con supresión complementaria |
| `src/cuidadores/publicar.py`, `lectura.py` | Igual que estudiantes, con `modulo = "cuidadores"` |
| `src/ui/cuidadores.py` | Página con despachador de audiencia |
| `src/ui/views/cuidadores_{investigador,comunidad,informe}.py` | Vistas e informes HTML y PDF |

**Puntuación:**

- **SDQ padres:** puntuación estándar desde el raw (No es cierto = 0, Un tanto = 1, Absolutamente = 2; inversos 7, 11, 14, 21, 25) y bandas `BANDS_PARENT`.
  - Rango de edad válido: 4 a 17 años. Fuera de ese rango no se puntúa.
  - **No se reutiliza nada del AUDIT legado**, que está mal codificado.
- **ARI padres:** suma de los ítems 1–6 (0–12); el 7 es deterioro. El corte de padres (> 3) se reporta como referencia externa.
- **PSS-10:** 0–4. **Es una adaptación, no el orden estándar.** Los ítems positivos que se invierten se identifican por su redacción: «manejó bien los cambios», «confianza en manejar sus problemas», «las cosas le iban bien», «ha podido controlar sus enojos» y «ha utilizado su tiempo adecuadamente» (columnas 27, 28, 29, 31 y 33). Se confirman contra el libro de códigos y con la consistencia interna (ítem–total). Sin corte clínico: terciles y percentiles.
- **EPDS-10:** 0–3 por la posición de la opción. Los ítems 1, 2 y 4 se puntúan en orden directo y los 3 y 5–10 en inverso, según el instrumento original. El mapa opción → puntaje se escribe explícito por ítem en el catálogo porque las redacciones varían.
  - Cortes: **≥ 10 posible** y **≥ 13 probable** sintomatología depresiva.
  - Aviso: la EPDS se validó en el periodo perinatal; aquí se lee como tamizaje de malestar y no como diagnóstico.
- **MSPSS-12:** media de 1 a 5, el total y las fuentes familia, amigos y persona especial. Es comparable con el de estudiantes, que usa la misma escala.
- **APQ:** subescalas de implicación, crianza positiva, supervisión deficiente, disciplina inconsistente y castigo físico (ítems 78–80), según el libro de códigos del proyecto (`Preprocesamiento 360/codigos/Códigos.xlsx`).
  - El castigo físico también se reporta como el porcentaje que usa alguna forma «A veces» o más. La Ley 2089 de 2021 lo prohíbe; el texto de acción lo trata como oportunidad de acompañamiento, no como acusación.
- **Estrés parental (39 ítems):** **no es el PSI-SF estándar de 36 ítems.**
  - Las subescalas (malestar paterno, interacción disfuncional, niño difícil) se asignan con el libro de códigos del proyecto.
  - Si el libro no cubre los 39 ítems, solo se reporta el total, con la nota de que es una versión adaptada.
  - **Bloqueante para las subescalas:** conseguir el libro de códigos.
- **Riesgo barrial:** índice de 0 a 10 (0, 1 o 2 por ítem).

**Datos que no se deducen del archivo:**

- Edad del niño entre 2 y 27: fuera del rango del instrumento no se puntúa el SDQ.
- **Curso libre:**
  - Mapa de patrones a grado: «501» → Quinto, «1002» → Décimo, «Sexto 602» → Sexto.
  - «2A», «Transición» y «Jardín» quedan fuera de los grados del estudio, y lo que no se reconoce va a «Otro».
  - Una prueba con todas las variantes observadas.
- **Duplicados entre olas:** el mismo cuidador y niño (por hash) en 2025 y 2026 conserva la respuesta más reciente en la vista de comunidad. El investigador puede elegir ola.
- **Hijo 2:** es una fila de niño más, con el mismo `id_cuidador`. Los errores estándar se agrupan por cuidador.

**Vistas:**

- **Investigador:** las mismas 8 pestañas que estudiantes (muestra y exclusiones, tabla 1, cortes y bandas, correlaciones con corrección BH, por grupo, modelos con errores agrupados, calidad de datos y exportar en ZIP), más un filtro de ola.
- **Comunidad, roles colegio, familia y municipio.** Tarjetas sugeridas, cuyos textos se redactan en el catálogo y los aprueba el equipo:
  1. Estrés de crianza.
  2. Ánimo del cuidador (EPDS).
  3. Apoyo que tiene el cuidador (MSPSS).
  4. Crianza positiva y castigo físico.
  5. Seguridad del barrio.
  6. Cómo ve el cuidador al hijo (SDQ padres).
  - Con el mismo techo de 5 tarjetas, la misma barra de bandas, la comparación por grupo y los informes HTML (por colegio y Secretaría) y PDF de una página.
- **Alerta del adulto:** EPDS ítem 10 ≥ «A veces» o EPDS ≥ 13, por grupo, con los dos estados de §5.4.
  - Visible para colegio y municipio. A la familia se le muestra solo un mensaje general de autocuidado con la ruta de adultos, sin cifras de autolesión.

**Supabase (migración que corre el usuario):**

- `obs360.corridas.modulo` ya existe. `ultima_corrida`, `resultados_vigentes`, `lectura.id_corrida_vigente` y `_traer_filas` **filtran por módulo**. Hoy, una corrida de cuidadores pisaría la de estudiantes.
- El `CHECK nivel` acepta `'cuidadores'`.
- `mensajes` agrega `modulo`, y la restricción `UNIQUE` pasa a ser (modulo, clave, accion_rol).
- La migración es aditiva e idempotente, con prueba de que las corridas existentes de estudiantes se siguen leyendo igual.

### 5.6 Fase 5 · Triangulación 360 (solo investigadores)

`src/triangulacion/` (puro) y `src/ui/triangulacion.py`.

#### Capa 1 · Por colegio (y por grado donde haya base)

Solo entran los colegios con **n ≥ 10 en cada actor**. Con los datos nuevos se esperan al menos LauV, JJC y SJMEB.

- **Docentes:** se unen por colegio mediante `core/colegios.codigo_desde_nombre`, porque su columna `Colegio` trae el nombre legible.
- **Constructos alineados** (cada fila dice qué instrumento lo mide en cada actor):

| Constructo | Estudiantes | Cuidadores | Docentes |
|---|---|---|---|
| Malestar emocional | SDQ emocional alto, señal de malestar | EPDS ≥ 13 | BLG desgaste / BTA |
| Estrés | — | PSS-10 (adaptación) | PSS de docentes (**verificar** que sean los mismos ítems antes de compararlos en crudo; si no, solo posición relativa) |
| Apoyo social | MSPSS (5 puntos) | MSPSS (5 puntos) | — |
| Escuela y clima | PSSM, adulto de confianza | Desempeño percibido | Clima laboral, apoyo percibido |
| Conducta del niño | SDQ autoinforme | SDQ padres | — |

- **Lectura:** cada valor se expresa como posición relativa dentro de su propio actor (z respecto a la media municipal de ese actor), porque escalas distintas no se comparan en crudo.
  - **«Coincidencia»:** los actores van en la misma dirección.
  - **«Tensión»:** van en direcciones opuestas por encima de un umbral (por defecto |Δz| ≥ 0,5).
- **Aviso fijo:** con 3 a 5 colegios esto es **descriptivo y ecológico**. No permite inferir relaciones entre individuos.

#### Capa 2 · Díadas niño–cuidador

- **Enlace:** se usa el hash del nombre normalizado del niño (la misma `norm_txt` y el mismo sha1 que el ID de estudiante), **verificado** con el código de colegio.
  - Se reporta la calidad del enlace: coincidencias, descartes por colegio distinto y concordancia de sexo y edad (±1 año).
  - Primer recuento sobre los datos crudos: 209 coincidencias exactas.
  - No se usan coincidencias aproximadas en esta fase.
- **Solo en la máquina que procesa.** Las díadas nunca suben a Supabase. Si se publica algo, son estadísticos agregados con n ≥ 10.
- **Análisis:**
  - Acuerdo SDQ niño frente a padre por subescala: correlación, CCI, diferencia media con límites de Bland–Altman, y kappa ponderado sobre las bandas, cada una con su propio corte (autoinforme o padres).
  - **«Malestar que el cuidador no ve»:** el niño está en banda alta o tiene señal de malestar, y el cuidador lo ubica en banda promedio. Se da su porcentaje e IC.
  - MSPSS de familia del niño frente al MSPSS del cuidador.
  - Asociaciones con IC entre la EPDS, la PSS, el castigo físico y el barrio del cuidador, y los resultados del niño (SDQ, RCADS, señales de alerta). Errores agrupados por colegio.
- **Exportación:** ZIP con tablas, figuras y `metodologia.md` de plantilla fija.

## 6. Experiencia de usuario: reglas para no empeorarla

- Las vistas existentes de estudiantes conservan su orden y su contenido. El panel de alertas se inserta arriba de las tarjetas, compacto, con el detalle desplegable.
- **El lenguaje de las alertas sigue reglas fijas:**
  - Nunca «riesgo de suicidio».
  - Siempre «señales», «no es un diagnóstico» y «dónde mirar primero».
  - Naranja como color máximo.
  - La ruta siempre a la vista.
- El rol familia no ve desagregación por colegio ni nada sobre la muerte o la autolesión (regla vigente).
- Cuidadores usa el mismo selector de rol, los mismos colores y la misma estructura que estudiantes, para que quien conoce una vista entienda la otra.
- La triangulación se lee en tres niveles de profundidad: un resumen de hallazgos («dónde coinciden» y «dónde hay tensión»), luego las tablas y luego la metodología.

## 7. Pruebas y verificación

- **Sintéticas por módulo**, con centinelas de privacidad:
  - Nombres de cuidador y niño, y un teléfono como `3000000000`.
  - Un colegio y un grado pequeños.
  - Un colegio donde la supresión complementaria debe actuar.
- **Regresión sobre datos reales**, que se omite si faltan los archivos:
  - Los conteos colegio × grado frente a la lista de los investigadores.
  - Las prevalencias de alerta de §5.4.
  - El recuento de díadas.
- **No regresión:**
  - Las cifras actuales de estudiantes y los informes no cambian, salvo lo nuevo. Se compara la salida de `informe_secretaria_html` antes y después, sin las secciones nuevas.
  - Lo mismo para la tabla de colegios en docentes.
- **Supabase:** el circuito publicar → leer para cada módulo, y prueba de que una corrida de un módulo no altera la lectura del otro.
- **Playwright de punta a punta** en los modos comunidad (corrida publicada), completo e investigador. Cubre la navegación renombrada, el selector de grado desbloqueado, los paneles de alerta por rol, la vista de cuidadores, la triangulación invisible en comunidad, los informes y PDF de una página, y el celular.

## 8. Lo que decide el equipo (no frena el desarrollo; hay valores provisionales)

1. **Textos y rutas:** líneas telefónicas y entidades exactas por rol, tanto para estudiantes como para adultos.
2. **Umbrales de alerta:** 3 de 6 para malestar y la regla estricta para desesperanza. Se les entrega el análisis de sensibilidad.
3. **Ítems con `*` de secundaria**, para confirmar o ajustar la propuesta.
4. **Uso de la EPDS** fuera del periodo perinatal, y redacción de su tarjeta.
5. **Mensajes de las tarjetas de cuidadores.**
6. Los textos actuales del catálogo de estudiantes que no se cumplen en todos los grupos. Por ejemplo, «más del doble en las chicas» en primaria de LauV, que da 29 % frente a 29 %. Hay que decidir si se vuelven condicionales.

## 9. Bloqueantes de datos

- **La exportación actualizada de secundaria**, para la fase 1 completa.
- **El libro de códigos de cuidadores** (`Códigos.xlsx`), para las subescalas del APQ y del estrés parental. Sin él, la fase 4 entrega totales.

## 10. Fuera de alcance

- Alertas o listas individuales.
- Vínculo docente–niño.
- Coincidencias aproximadas de nombres.
- Inferencia multinivel con 3 a 5 colegios.
- Rediseño del dashboard de docentes más allá del nombre.
- Cambios en el PDF de docentes (sigue siendo la otra mitad del A/B).
