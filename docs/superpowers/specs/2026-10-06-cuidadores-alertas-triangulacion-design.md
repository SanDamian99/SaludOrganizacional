# Observatorio 360 · Cuidadores, alertas y triangulación — diseño

**Fecha:** 6 de octubre de 2026 · **Versión:** 2, tras una revisión independiente
**Estado:** pendiente de revisión del usuario
**Rama:** `feature/360-cuidadores-alertas-triangulacion`, que sale de `feature/informe-estudiantes-html` (PR #1)

## 1. Qué se pide

El equipo investigador hizo cinco pedidos el 6 de octubre de 2026:

1. **Los grados con 10 o más estudiantes deben verse**, también dentro de un colegio. Entregaron una lista de referencia (§3.1).
2. **Alertas** en la vista del colegio (docente y rector) y en los informes.
   - Las activan los ítems marcados con `*`.
   - Llevan recomendaciones de atención y rutas para familias, rector y municipio.
   - **No deben alarmar.** Deben motivar la indagación y la acción oportuna.
3. **Módulo de cuidadores** (formulario «Cuidando al Cuidador»).
   - Una vista para investigadores y otra para la comunidad (colegio, familia y municipio).
   - Con la misma lógica que estudiantes.
4. **Triangulación solo para investigadores** entre docentes, cuidadores y estudiantes: patrones, puntos en común y tensiones.
5. **Navegación:** «Dashboard» pasa a llamarse «Docentes», con un dashboard por población y uno de triangulación.

La plataforma está en uso y funciona bien. Todo esto es un **complemento**: ninguna fase cambia lo existente salvo donde se pide.

## 2. Decisiones del usuario

| Tema | Decisión |
|---|---|
| Unidad de la alerta | **Por grupo** con n ≥ 10. Nunca un estudiante ni un cuidador identificable. |
| Ítems de alerta | **Señales de malestar:** los 6 ítems del SDQ marcados con `*`, en los dos niveles. **Desesperanza:** propuesta sobre el RCADS, revisada, solo para secundaria (§5.4). |
| Triangulación | Capa por colegio y capa de **díadas** niño–cuidador, enlazadas con un identificador cifrado. Las díadas solo existen en local. |
| Alerta del adulto | Sí, a partir de la EPDS. Tras la revisión se divide en «ánimo» y «autolesión» (§5.5). |
| Orden de trabajo | Los informes entraron primero (commit `8287201`, PR #1). |
| Despliegue público | Estudiantes 360 y Cuidadores 360 (vistas de comunidad). La página de Cuidadores se habilita cuando sus textos estén aprobados (§5.5). |
| Privacidad de los grados | **Todo agregado publicado se calcula sobre las celdas publicables.** Los totales «por grado» excluyen a los colegios pequeños, que siguen contando en el total del nivel (§5.1). |
| Sedes | **La unidad es el colegio.** La sede es un detalle visible solo para investigadores. |

## 3. Datos

### 3.1 Estado

| Archivo | Ubicación | Estado |
|---|---|---|
| Estudiantes de secundaria (CSV del 18 de septiembre, 979 filas) | `datos_fuente_360/estudiantes/` | **Desactualizado** |
| Estudiantes de primaria (CSV del 18 de septiembre, 283 filas) | `datos_fuente_360/estudiantes/` | Lo reemplaza el xlsx siguiente |
| Estudiantes de primaria (xlsx hasta el 6 de octubre, 355 filas, 352 válidas hoy) | `datos_fuente_360/estudiantes/entrantes/` | Contiene a todos los del CSV, con las mismas 89 columnas más el `*` |
| Cuidadores (xlsx de sep-2025 a sep-2026, 779 filas, 209 columnas) | `datos_fuente_360/cuidadores/` | Nuevo. Sustituye el CSV de 172 filas |

**La lista de los investigadores son conteos crudos**, antes de limpiar.

- Comparada en crudo, coincide en La Balsa y Laura Vicuña.
- Después de limpiar, las cifras cambian algunas unidades: Laura Vicuña octavo 93 → 91, Laura Vicuña quinto 98 → 97, JJC noveno 58 → 57.
- La plataforma mostrará **«n válidas de N respuestas»** para que ambas cifras se reconcilien a la vista.

**Falta la exportación actualizada de secundaria.** Sin ella no aparecen:

- CdP sexto 16 y séptimo 24.
- JJC décimo 83.
- SJMEB sexto 50.

Ningún cambio de código los produce.

**San Josemaría** se trata como colegio.

- Séptimo tiene 29 estudiantes: 25 de la sede Samaria y 4 de Principal.
- La lista de los investigadores da el séptimo de Samaria (25). La diferencia se explica en la pestaña de muestra.

### 3.2 Formulario de cuidadores (columnas por posición)

| Bloque | Columnas | Nota |
|---|---|---|
| Datos de base | 0–9 | Consentimiento (756 sí, 23 no), quién responde (mamá 586, papá 141, otros 52), nombres, edad, sexo, colegio, tipo, curso |
| Familia y contexto | 10–19 | — |
| Riesgo barrial (5 ítems) | 20–24 | — |
| PSS-10 | 25–34 | **Mismos ítems y orden que la PSS de docentes**; inversos 3, 4, 5, 7 y 9 (`preparar_docentes.py:150,184`). Hay respuestas sueltas «Columna 6»: cuentan como faltantes. |
| EPDS-10 | 35–44 | Cada ítem tiene 4 etiquetas propias y únicas |
| MSPSS del cuidador | 45–56 | **Reparto 5/4/3** (persona especial, familia, amigos), no el 4/4/4 de estudiantes |
| APQ | 57–81 | Castigo físico en 78–80, grito en 81 |
| Estrés parental, «39 ítems» | 82–120 | **No es el PSI-SF estándar.** Las columnas 103–107 son las cinco opciones de una sola pregunta de elección forzada, partidas en ítems Likert. La 117 está redactada en positivo. |
| SDQ de padres, hijo 1 | 121–145 | — |
| Hijo 2 | 146–152 y SDQ en 153–177 | 217 cuidadores responden por un segundo hijo |
| Teléfono | 178–179 | Se descarta en la carga |
| ARI de padres, hijo 1 / hijo 2 | 186–192 / 193–199 | **Cobertura parcial:** 382 de 756 y 94 de 217. Nada en la ola 2025. |
| Columnas vacías | 180–185 y 200–208 | Se ignoran |

**Por colegio**, con consentimiento y normalizador corregido (§5.2):

- LauV 448, JJC 119 y SJMEB unos 39.
- La Balsa 24, DiosCh 13 y Bojacá 12.
- Unas 100 con el colegio escrito a mano (Conaldi o Diversificado, Santa Lucía…).

**Dos olas:** 145 respuestas en sep-2025 y 634 en 2026.

**Niños:**

- Hay 973 filas de niño (hijo 1 más hijo 2) y **886 niños únicos**.
- 87 son repetidos: casi siempre los dos padres respondieron por el mismo niño; solo 5 se repiten entre olas.
- Edad del niño: hay 89 valores no numéricos y el máximo es 19.

## 4. Principios que no se negocian

- **Nada individual.** Ningún nombre, teléfono, fila, identificador ni grupo con menos de `MIN_GROUP_N = 10` en pantallas, informes, exportaciones de comunidad o Supabase.
  - En cuidadores, el mínimo cuenta **cuidadores distintos**, no filas de niño.
- **Nada deducible.** Ningún grupo de 1 a 9 puede obtenerse restando cifras publicadas, ni dentro de una corrida ni entre corridas (§5.1).
- **A Supabase solo suben agregados.** El `CHECK n >= 10` sigue siendo la última barrera.
- **Los textos sobre salud mental son fijos.** Viven en catálogos que revisa el equipo y nunca los redacta la IA.
- **El despliegue público no importa** los módulos de investigación.
- **Cada fase va en su propio PR**, con la suite verde (salvo las 2 fallas previas de `test_knowledge_base`) y la revisión con Playwright.

## 5. Fases

Orden: 0 → 1 → 2 → 3 → 4a → 4b → 5. La tabla de colegios (§5.2) entra en la fase 1.

### 5.0 Orden previo

- [x] Commit de los informes y PR #1.
- [x] Sacar los xlsx de la raíz del repositorio.
- [ ] Pedir a los investigadores la exportación actualizada de secundaria y el libro de códigos de cuidadores (`Códigos.xlsx`, que no está en Documents).

### 5.1 Fase 1 · Los grados que no se ven, con privacidad por resta resuelta

**Causas:**

- **Datos:** el CSV de secundaria es viejo.
- **Código:** el despliegue no publica el cruce colegio × grado. Eso afecta a tres lugares:
  - El selector de grado queda bloqueado al elegir un colegio (`estudiantes_comunidad.py:655-680`).
  - «Comparar entre grupos → Grado» con un colegio elegido sale vacío (`:345-350`).
  - El informe no trae «Por grado en el colegio».

**Cambios:**

1. **Carga.**
   - `ingest` ya lee xlsx y `norm_txt` ya quita el `*`.
   - Hay que añadir `ingest.items_marcados(raw)`, que devuelve el conjunto de ítems con `*` para la fase 3.
   - `localizar_formularios` debe quedarse con un archivo por formulario (el más reciente si hay CSV y xlsx).
   - El xlsx de primaria pasa de `entrantes/` a `estudiantes/`; el CSV viejo va a `otros/archivo/`.
2. **Base publicable.** La unidad mínima es la **celda colegio × grado con n ≥ 10**. A partir de ahí:
   - **Colegio:** se calcula sobre la unión de sus celdas publicables. Si el colegio no tiene ninguna celda publicable, se usa el colegio completo, siempre que llegue a 10.
   - **Grado:** se calcula sobre la unión de sus celdas publicables. Los colegios pequeños quedan fuera del grado.
   - **Nivel:** usa todos los estudiantes, siempre que el **resto** (lo que no está en ningún colegio publicado) sea 0 o reúna ≥ 10 estudiantes de ≥ 2 colegios. Si no, el nivel también se calcula sobre la base publicable.
   - **La pantalla y los informes lo dicen:** «Cálculo sobre los grupos de 10 o más; 11 respuestas de grupos pequeños cuentan solo en el total».
3. **Todo o nada por celda.** Si un indicador de una celda tiene n < 10 por datos faltantes, la celda publica ese indicador como no disponible y **ningún otro indicador lleva `n` ni `casos` que permitan reconstruirlo**. Hoy `_aplanar_subgrupo` descarta filas sueltas y eso abre otra resta.
4. **Auditoría de publicación.** `publicar.verificar` construye el conjunto de estudiantes de cada agregado. Prueba todas las restas de un paso entre agregados anidados y disjuntos (padre menos la suma de hijos que lo cubren) para cada estadístico con `n` o `casos`.
   - Si alguna da entre 1 y 9, **se niega a publicar** y dice dónde.
   - Es una función pura con pruebas propias, incluidos los casos reales: el décimo de CdP, el quinto de SJMEB y el cuarto de CdP en primaria.
5. **Entre corridas.** Al aprobar una corrida, el publicador **despublica la anterior del mismo módulo**. Las vistas `ultima_corrida` y `resultados_vigentes` exponen solo la última publicada **por módulo**.
   - Restando dos corridas se aislarían las respuestas nuevas: CdP pasa de 15 a 41 en primaria.
6. **Filtro por módulo, adelantado a esta fase.**
   - `lectura.id_corrida_vigente`, `_traer_filas` y las vistas filtran por `modulo`.
   - El `CHECK` de identificadores pasa a `^[ECN][0-9a-f]{8}$`.
   - Así queda desplegado antes de que exista cualquier corrida de cuidadores.
   - La migración es aditiva e idempotente y la corre el usuario.
7. **Publicar y leer.** Se añade la agrupación `"Colegio×Grado"`, con clave `"LauV|Sexto"`. Una corrida vieja sin esas filas se sigue leyendo; la vista explica que el cruce no está disponible, como hoy.
8. **Vista e informes.**
   - El selector de grado se desbloquea y ofrece solo las celdas publicadas.
   - La comparación por grado dentro de un colegio funciona.
   - El informe trae «Por grado en el colegio» también en el despliegue.
9. **Investigadores.** La pestaña de muestra suma la tabla **colegio × grado** con «válidas / respuestas» y la sede como detalle.
10. **Aceptación.**
    - Prueba con la lista de los investigadores sobre **conteos crudos**: La Balsa y LauV hoy, todos los colegios cuando llegue la exportación.
    - La auditoría (punto 4) pasa sobre los datos reales.
    - Ningún grupo de 1 a 9 queda expuesto, ni directamente ni por resta.

### 5.2 Tabla única de colegios (dentro de la fase 1)

Se crea `src/core/colegios.py`, con estas funciones:

- `normalizar(texto) -> (codigo, nombre, sede)`
- `nombre(codigo)`
- `codigo_desde_nombre(nombre_docentes)`

Reglas:

- **Unidad = colegio; la sede es detalle.** Santa Lucía es una sede de Diversificado (CND), y Fusca·El Cerro una sede de Fusca.
- **Docentes no cambia lo que muestra.** Su columna `Colegio` sigue con los nombres actuales, incluida «Diversificado · sede Santa Lucía». La tabla solo da el código para unir en la triangulación.
- **Variantes que se agregan:**
  - «San José María», con espacio. Hoy se pierde: SJMEB de cuidadores daba 27 con el normalizador de estudiantes y 39 con el de docentes.
  - Conaldi, Conadi y Diversificado → CND.
  - «Jj casas» → JJC.
  - Balaguer → SJMEB.
  - Santa María del Río → SMR.
- **Prueba de no regresión.** Los códigos asignados a estudiantes y docentes sobre los datos reales no cambian, salvo la corrección de «San José María», que se documenta.

### 5.3 Fase 2 · Navegación

- **Constantes en `modo.py`:** `PAGINA_DOCENTES = "Docentes"`, `PAGINA_ESTUDIANTES`, `PAGINA_CUIDADORES = "Cuidadores 360"` y `PAGINA_TRIANGULACION = "Triangulación 360"`.
- **Orden del menú:** Docentes, Estudiantes 360, Cuidadores 360, Triangulación 360, Chat con IA, Cargar Datos, Análisis de tendencias, Reportes.
- **Por modo:**
  - **Completo e investigador:** todas las páginas.
  - **Comunidad:** Estudiantes 360 y, cuando se habilite, Cuidadores 360. Elige la página en un selector.
  - El corte de importaciones de `main.py` se extiende: en comunidad no se importan Triangulación ni la vista de investigador de cuidadores.
- **Renombrar.**
  - Archivos: `main.py:96,113`, `modo.py:90`, `state.py:63`, `reports.py:19,24` y `dashboard.py:2,559`.
  - Pruebas: `tests/test_modo_despliegue.py:95-100,114,195,233-236`.
  - Documentación: `ARCHITECTURE.md`, `README.md` y `DESPLIEGUE.md`.
  - El `page_title` público pasa a «Observatorio 360 · Comunidad».
  - No se tocan las menciones al «dashboard» de Supabase.
- **Estado entre páginas.** El colegio y el rol elegidos se guardan en el estado de sesión fuera de los widgets, para no perderlos al cambiar entre Estudiantes y Cuidadores. `?colegio=` aplica a las dos páginas.

### 5.4 Fase 3 · Alertas de estudiantes: «Señales para actuar a tiempo»

#### Definiciones por estudiante

Viven en `src/estudiantes/alertas.py` (funciones puras). Los ítems y umbrales están en `catalog.ALERTAS`.

**Señales de malestar** (primaria y secundaria):

- **Ítems marcados con `*`:**
  - SDQ 5: me enojo y pierdo el control.
  - SDQ 6: solitario.
  - SDQ 8: preocupado.
  - SDQ 13: triste o con ganas de llorar.
  - SDQ 19: se burlan de mí.
  - SDQ 24: muchos miedos.
- **Regla:** «Muy cierto» en **3 o más de los 6**.
- **Calibración:** 8,8 % en secundaria; 15,1 % en primaria con el xlsx nuevo. Con «2 o más» serían 22,0 % y 32,4 %.
- Se nombra «malestar» y no «malestar emocional» porque los ítems incluyen enojo y relación con pares.
- En primaria va junto al aviso de validez de edad.

**Señales de desesperanza y pensamientos de muerte** (solo secundaria):

- **Regla:** RCADS 18 («Pienso acerca de la muerte») = **Siempre**, o RCADS 18 ≥ **Con frecuencia** junto con RCADS 16 («Me siento que no valgo nada») ≥ **Con frecuencia**.
- **Calibración:** 17,0 % en total; entre 10,8 % y 21,5 % según el grado.
- Para el análisis de sensibilidad, la **regla amplia** se define exactamente así: RCADS 18 ≥ Con frecuencia, o RCADS 16 ≥ Con frecuencia junto con (RCADS 4 o RCADS 1) ≥ Con frecuencia.
- **Límite:** el instrumento no tiene una escala de desesperanza.

**Unificación con la tarjeta actual de muerte.** Hoy la tarjeta «Pensamientos sobre la muerte» (RCADS 18 ≥ Con frecuencia, 24,9 %) mostraría otra cifra sobre el mismo ítem. Para los roles colegio y municipio **el panel de alertas la reemplaza**. En la vista de investigadores, la prevalencia de RCADS 18 sigue en «Cortes y bandas».

Una prueba verifica que los ítems con `*` de cada archivo coinciden con `catalog.ALERTAS`. Hoy solo primaria está marcado; cuando el equipo marque secundaria se ajusta el catálogo.

#### Agregación y estados

Para cada grupo publicable de §5.1 se calculan el porcentaje con señal y su IC de Wilson. El panel **nunca se oculta** y tiene dos estados:

- **«Para tener presente»** (gris sereno). Por ejemplo: «1 de cada 6 estudiantes muestra señales. No es un diagnóstico: indica dónde mirar primero». Incluye qué hacer y la ruta.
- **«Prioridad»** (naranja como máximo, nunca rojo). Se activa cuando el IC del grupo queda **por encima del resto del municipio**. La comparación es contra el resto, no contra el total: Laura Vicuña es el 46 % de secundaria.
  - Dentro de un colegio se listan los grados en «Prioridad» en orden canónico.
  - **Nota fija:** con muchas comparaciones, alguna «Prioridad» puede deberse al azar; sirve para orientar, no para concluir.

**Cifras que no delatan:**

- **Nunca se publica ni se muestra el número de casos** de ninguna alerta.
- El porcentaje y el «1 de cada N» se muestran **solo si el número de casos está entre 3 y n − 3**.
- Si no, el panel dice: «En este grupo las cifras son muy pequeñas para mostrarse sin riesgo de identificar a alguien; la ruta sigue aplicando».

**¿Por qué no hay un umbral fijo?** Cualquier umbral razonable se activa en casi todos los grupos, y una alerta permanente deja de ser alerta.

#### Quién ve qué

| Rol | Malestar | Desesperanza | Qué ve |
|---|---|---|---|
| Colegio | Sí | Sí | Panel arriba de las tarjetas (compacto, con detalle desplegable), grados en «Prioridad», qué hacer y ruta escolar |
| Municipio | Sí | Sí | Por colegio y por grado; qué hacer en política y red |
| Familia | Sí | **No** (regla vigente) | Qué hacer en casa y a dónde acudir |

- **Informes:**
  - El informe del colegio lleva el panel.
  - El de la Secretaría lleva una tabla de alertas por colegio, sin conteos.
  - El PDF de una página lleva un recuadro compacto antes de las tarjetas.
- **Investigadores:**
  - Definiciones, prevalencias por grupo y la distribución de cada ítem.
  - Sensibilidad: umbrales de 2, 3 y 4, y regla estricta frente a amplia.
  - `alertas.csv` (solo por grupo) en el ZIP.
- **Supabase:** filas `alerta_grupo` sin `casos`, y mensajes por rol.

#### Rutas

`RUTA_ATENCION` pasa a `RUTAS[rol][tipo]`, donde el tipo es estudiante o adulto.

- **El código no inventa teléfonos.** La «Línea 106» actual es de Bogotá.
- El equipo confirma las líneas para Chía, por ejemplo la 192 opción 4 o el ICBF 141.
- Mientras no estén aprobadas, se muestran las entradas actuales. En el modo completo aparece además el aviso interno «ruta pendiente de validación».

### 5.5 Fase 4 · Cuidadores 360

Va en dos PR. **4a:** carga, puntuación y vista de investigadores. **4b:** vista de comunidad, informes y publicación.

| Archivo | Responsabilidad |
|---|---|
| `src/cuidadores/catalog.py` | Escalas, ítems por posición, mapas texto → puntaje explícitos por ítem, bandas, `MENSAJES`, `ALERTAS`, `RUTAS` de adulto |
| `src/cuidadores/ingest.py` | Consentimiento, identificadores con **HMAC con clave local** (`C…` para el cuidador, `N…` para el niño), descarte de nombres y teléfono, colegio vía `core/colegios`, curso libre → grado, ola, expansión del hijo 2 y deduplicación |
| `src/cuidadores/scoring.py` | Puntuaciones desde el texto crudo |
| `src/cuidadores/pipeline.py` | `AnalisisCuidadores` con dos marcos (**cuidador** y **niño**) y la base publicable de §5.1 |
| `src/cuidadores/publicar.py`, `lectura.py` | Igual que estudiantes, con `modulo = "cuidadores"` |
| `src/ui/cuidadores.py`, `src/ui/views/cuidadores_{investigador,comunidad,informe}.py` | Página y vistas |

**Deduplicación de niños:** queda una fila por niño.

- **Prioridad:** la ola más reciente; si hay empate, quien responde como mamá, luego papá, luego otro; si persiste, el primer envío.
- La deduplicación de cuidadores entre olas usa la respuesta más reciente.
- El mínimo de 10 se aplica a **cuidadores distintos**.

**Puntuación:**

- **SDQ de padres:** estándar desde el raw, con bandas `BANDS_PARENT`. Edad **numérica entre 4 y 17**; si no es numérica, falta. Nada del AUDIT legado.
- **ARI de padres:** ítems 1–6 (rango 0–12). La cobertura parcial se declara en pantalla y en la metodología.
- **PSS-10:** 0–4, con inversos 3, 4, 5, 7 y 9, igual que docentes. Sin corte: terciles.
- **EPDS-10:** **por texto de la respuesta**, con un mapa explícito de cada ítem en el catálogo. No se usa la posición.
  - **Ánimo:** ≥ 10 posible, ≥ 13 probable (23,3 %).
  - **Autolesión:** ítem 10 ≥ «Casi nunca» (11,0 %), siguiendo la práctica estándar de atender cualquier respuesta distinta de cero.
  - **Aviso:** la EPDS se validó en el periodo perinatal; aquí se lee como tamizaje.
- **MSPSS del cuidador:** media 1–5 **por fuente**. La comparación con estudiantes es solo por fuente (sobre todo familia) y con aviso de redacción distinta.
- **APQ:** subescalas según el libro de códigos. Mientras no llegue, solo se reportan los ítems de castigo físico (78–80) como «usa alguna forma, a veces o más». La Ley 2089 de 2021 lo prohíbe; el texto lo plantea como acompañamiento.
- **Estrés parental:** **no hay total ni subescalas hasta confirmar la dirección de los ítems** con el libro de códigos, por las columnas 103–107 y 117. Hasta entonces, solo los ítems descriptivos en la vista de investigadores.
- **Riesgo barrial:** índice de 0 a 10.
- **Curso libre:**
  - Mapa de patrones: «501» → Quinto, «1002» → Décimo, «Sexto 602» → Sexto.
  - Grados del estudio: cuarto a décimo. Once, transición y primero a tercero quedan en «fuera del rango del estudio».
  - Prueba con todas las variantes observadas.

**Vistas:**

- **Investigador (4a):** las mismas 8 pestañas que estudiantes, más un filtro de ola que **solo existe en local** y no se publica por ola.
- **Comunidad (4b):** mismos roles y misma estructura que estudiantes. Tarjetas:
  1. Estrés de crianza (PSS).
  2. Ánimo del cuidador (EPDS).
  3. Apoyo que tiene (MSPSS por fuente).
  4. Crianza positiva y castigo físico.
  5. Seguridad del barrio.
  6. Cómo ve el cuidador al hijo (SDQ de padres).

  Se mantiene el techo de 5 tarjetas.
- **Alertas del adulto:**
  - **«Ánimo»** (EPDS ≥ 13): por grupo, para colegio y municipio, con las reglas de cifras de §5.4.
  - **«Autolesión»** (ítem 10): **solo a nivel municipio**, sin conteos y con la regla de 3 a n − 3. En el colegio queda dentro de un estado general.
  - **Familia:** un mensaje de autocuidado con la ruta para adultos, sin cifras.
- **Despliegue público:** la página de Cuidadores se habilita en modo comunidad **solo cuando** el equipo aprueba sus textos y rutas y hay una corrida de cuidadores publicada. Hasta entonces existe en los modos completo e investigador.

### 5.6 Fase 5 · Triangulación 360 (solo investigadores)

Código en `src/triangulacion/` (puro) y `src/ui/triangulacion.py`.

#### Capa 1 · Por colegio

**Colegios que entran:** los que tienen **n ≥ 10 en cada actor**. Con los datos actuales son 4: LauV, JJC, SJMEB y La Balsa (221 estudiantes, 24 cuidadores, 18 docentes).

**Quiénes entran:**

- **Cuidadores:** solo los de niños en los grados del estudio (631 de 756).
- **Docentes:** se unen con `codigo_desde_nombre`.
- **Por grado** solo es posible con estudiantes y cuidadores; los docentes no tienen grado. La vista lo dice.

**Medida:** para cada actor y constructo, la diferencia del colegio frente al **resto del municipio de ese mismo actor**, en unidades de la DE individual del actor, con su IC.

**Clasificación:**

- **Coincidencia o tensión** solo en constructos que hablan **del mismo objeto**:
  - La conducta del niño, según él (SDQ autoinforme) y según su cuidador (SDQ de padres).
  - El clima escolar, según los estudiantes (PSSM, adulto de confianza) y según los docentes (clima laboral, apoyo percibido).
  - El estrés, entre cuidadores y docentes. Es la misma PSS, pero mide a personas distintas, así que se clasifica como co-ocurrencia.
  - Hay **«tensión»** solo si los IC de los dos actores excluyen el cero **en direcciones opuestas**. Hay **«coincidencia»** si lo excluyen en la misma dirección. En otro caso: «sin diferencia clara».
- **Los demás cruces son «co-ocurrencia».** Por ejemplo, el malestar del niño junto a la EPDS del cuidador y al desgaste docente: se describen lado a lado sin llamarlos acuerdo, porque no miden lo mismo.

**Aviso fijo:** con 4 colegios esto es descriptivo y ecológico.

**En el despliegue de investigador** (sin archivos crudos) solo existe esta capa, desde agregados publicados con la base de §5.1.

#### Capa 2 · Díadas niño–cuidador (solo local)

**Enlace:**

- HMAC con clave local del nombre normalizado del niño, en los dos archivos, **verificado con el colegio**.
- Se reporta la calidad del enlace: coincidencias, descartes por colegio y concordancia de sexo y edad (±1 año).
- Primer recuento: 209 niños. Por colegio verificado: LauV unos 204 filas, JJC 20, La Balsa 4, SJMEB 3.
- No hay coincidencias aproximadas.

**Análisis:**

- **Acuerdo SDQ entre el niño y su cuidador**, por subescala: correlación, CCI, diferencia media con límites de Bland–Altman, y kappa ponderado sobre las bandas (cada informante con su propio corte).
- **«Malestar que el cuidador no ve»:** el niño en banda alta o con señal de malestar, y el cuidador lo ubica en la banda promedio. Se da su porcentaje e IC.
- **MSPSS de familia** del niño frente al del cuidador, por fuente y con aviso.
- **Asociaciones** de la EPDS, la PSS, el castigo físico y el barrio con los resultados del niño.
  - Errores **agrupados por familia**, con efecto fijo de colegio.
  - Sensibilidad solo con LauV, porque 4 conglomerados escolares no sostienen errores robustos.

**Exportación:** ZIP local con tablas, figuras y `metodologia.md` de plantilla fija. Nada de esto sube a Supabase.

## 6. Experiencia de usuario

- **Lo existente no se mueve.** Estudiantes conserva su orden y su contenido. El panel de alertas entra arriba de las tarjetas, compacto, y reemplaza la tarjeta de muerte solo para colegio y municipio.
- **Lenguaje de las alertas:**
  - Nunca «riesgo de suicidio».
  - Siempre «señales», «no es un diagnóstico» y «dónde mirar primero».
  - Estados: «Para tener presente» y «Prioridad».
  - Color máximo: naranja.
  - La ruta siempre está a la vista.
- **Familia** no ve desagregación por colegio, ni nada sobre la muerte o la autolesión, ni cifras de autolesión del adulto.
- **Cuidadores** usa el mismo selector de rol, los mismos colores y la misma estructura que estudiantes.
- **Las cifras se reconcilian** con «n válidas de N respuestas» y con la nota de la base publicable.
- **La triangulación se lee en capas:** primero un resumen («dónde coinciden» y «dónde hay tensión»), luego las tablas, luego la metodología.

## 7. Pruebas y verificación

- **Pruebas sintéticas por módulo**, con centinelas de privacidad:
  - Nombres de cuidador y de niño, y el teléfono `3000000000`.
  - Un colegio y un grado pequeños.
  - **Las tres configuraciones reales de resta**: décimo de CdP, quinto de SJMEB y cuarto de CdP en primaria.
- **Auditoría de resta:** pruebas propias, y bloquea la publicación ante cualquier fallo.
- **Regresión sobre datos reales** (se omite si faltan los archivos):
  - Conteos crudos colegio × grado frente a la lista.
  - Prevalencias de alertas (§5.4).
  - Recuento de díadas.
  - No regresión de los códigos de colegio (§5.2).
- **No regresión de pantallas:** las cifras e informes actuales de estudiantes no cambian, salvo lo nuevo y la base publicable. Las diferencias por la base publicable se listan y se aprueban explícitamente.
- **Supabase:**
  - Circuito publicar → leer por módulo.
  - Una corrida de cuidadores no altera la lectura de estudiantes.
  - Solo se lee la última corrida por módulo.
- **PDF de una página:** pruebas del peor caso (rol municipio, lista máxima de «Prioridad», ambos niveles), que debe seguir cabiendo en una página.
- **Playwright de punta a punta** en los modos comunidad, completo e investigador:
  - Navegación renombrada y estado entre páginas.
  - Selector de grado desbloqueado y comparación por grado dentro de un colegio.
  - Alertas por rol y regla de cifras.
  - Cuidadores visible u oculto según su habilitación.
  - Triangulación invisible en comunidad.
  - Informes, PDF y celular.

## 8. Lo que decide el equipo (hay valores provisionales)

1. Textos y rutas por rol, para estudiantes y adultos, con las líneas exactas para Chía.
2. Umbrales de alerta. Se les entrega la sensibilidad.
3. Ítems con `*` de secundaria.
4. Uso y redacción de la EPDS fuera del periodo perinatal.
5. Mensajes de las tarjetas de cuidadores (condiciona la habilitación pública).
6. Textos actuales de estudiantes que no se cumplen en todos los grupos. Ejemplo: «más del doble en las chicas» cuando primaria de LauV da 29 % frente a 29 %.

## 9. Bloqueantes de datos

- **Exportación actualizada de secundaria:** la necesita la fase 1 completa.
- **Libro de códigos de cuidadores:** lo necesitan las subescalas del APQ y el estrés parental. Sin él, la fase 4 sale sin esas puntuaciones.

## 10. Fuera de alcance

- Alertas o listas individuales.
- Vínculo entre docente y niño.
- Coincidencias aproximadas de nombres.
- Inferencia multinivel con 4 colegios.
- Publicar por ola.
- Rediseñar el dashboard de docentes más allá del nombre.
- Cambiar el PDF de docentes: es la otra mitad del A/B.
