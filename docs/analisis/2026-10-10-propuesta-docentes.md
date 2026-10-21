# Propuesta: rediseño de la vista principal de «Docentes»

> **Estado:** propuesta para que el equipo la revise. No cambia código.
> **Fecha:** 10-oct-2026.
> **Datos:** versión activa de docentes (479 docentes: 189 de 2025 y 290 de 2026). Todo lo que aparece aquí son agregados; cada cifra por grupo viene de n ≥ 10.
> **Base:** `src/ui/dashboard.py`, `src/analysis/{indicators,scoring}.py`, `src/data/{loader,processor}.py`, `scripts/preparar_docentes.py`, `src/reports/indicator_report.py`, la auditoría de relevancia y la sección H de hallazgos de triangulación (ambas del 10-oct).
> **Capturas** (app local en modo completo, fuera del repositorio): `/private/tmp/claude-501/-Users-joseamorocho-Documents-app-360-observatorio-SaludOrganizacional/73d67104-c128-41eb-b044-923af344a71f/scratchpad/docentes/` (archivos `01_…` a `09_…`; las páginas del PDF actual son `10_pdf-1…9.png`).

**Principio de la propuesta.** Al equipo le gusta el tablero de Docentes y nada de lo que valora se pierde: se conservan las mismas pestañas, los temas, las barras por tema con su semáforo, la tabla completa, «Explorar un indicador», la comparación por grupo, el perfil, los filtros, el PDF con recomendaciones, el Chat y Reportes. Lo que cambia es **qué número hay detrás** de cada elemento:

- una escala fija en lugar de la posición dentro de la muestra;
- los cortes publicados, cuando existen;
- el IC 95 %;
- un mínimo de 10 docentes por grupo;
- textos fijos en lugar de la interpretación con IA de los botones.

---

## 1. Inventario actual (lo que se ve hoy con los datos reales)

Con los datos reales, el archivo **no** es del esquema «(BM)». Por eso se ve la vista de **indicadores**, que tiene 3 pestañas. Las 4 pestañas «Resumen ejecutivo / Dimensiones / Perfil / Vista académica», con su semáforo y su gauge, solo aparecen con el CSV de demostración (`indicators.is_wellbeing_dataset` es False y `compute_dimension_scores` devuelve 0 dimensiones).

| # | Sección (captura) | Qué muestra | Con qué datos | Qué valora el equipo (inferido) |
|---|---|---|---|---|
| 1 | KPIs (`01`) | Docentes 479 · Indicadores 27 · «Salud mental en atención» 0 | Conteo de filas, nº de `*_T` y nº de indicadores 🧠 con nivel «Atención» | La lectura de un vistazo: cuántos son y cuántos focos hay |
| 2 | Aviso azul (`01`) | Explica la «posición relativa» y remite a `docs/GUIA_DATASETS.md` | Texto fijo | — |
| 3 | Barras por tema: 🧠 Salud mental y estrés (6), 😊 Bienestar laboral (4), 🛠️ Recursos (6), 💗 Empatía y regulación (6), 📊 Otros (5) (`01–03`) | 27 barras horizontales de 0 a 100 en verde, ámbar o rojo, con una línea en 50 | `enrich_indicators`: (media − mín. observado)/(máx. − mín. observado), orientada | **El semáforo por tema**: ordenado, en colores, agrupado por constructo |
| 4 | Mensajes «Requieren atención / Favorables» (`01`) | Hoy: «Sin indicadores en atención» y «Favorables: Burnout, Bienestar psicosocial, Alienación» | Niveles del índice relativo | Priorizar |
| 5 | Botón «✨ Interpretar salud mental con IA» | Texto libre de Gemini | Índice relativo | — |
| 6 | Expander «📋 Tabla completa» (`04`) | Indicador, tema, media, DE, rango observado, N, «Nivel (muestra)» | `*_T` | Ver todos los números juntos |
| 7 | «Explorar un indicador» (`04–05`) | Media, rango observado, N e histograma | Columna `*_T` | Ver la distribución |
| 8 | «Comparar por grupo» (`05`) | Barras de medias por grupo con «N por grupo» | Abre por defecto con «Fecha de respuesta» (eje 2 024,5–2 026,5). No ofrece Colegio (16 categorías > tope de 12) | Comparar subgrupos |
| 9 | Botón «✨ Interpretar «X» con IA» (`05`) | Texto libre | `describe()` del indicador | — |
| 10 | Pestaña Perfil › Sociodemográficas y Laborales (`06–07`) | Unos 12 histogramas o barras (edad, sexo, estado civil, hijos…) | Columnas (SD)/(LB) | Saber quién respondió |
| 11 | Pestaña Correlaciones (`08`) | Mapa de calor 27×27 sin cifras | Pearson sobre `*_T` crudos | — |
| 12 | Sidebar «Generar Informe PDF» (`10_pdf-*`) | Portada · Resumen ejecutivo (4 KPIs: docentes, indicadores, focos de atención, fortalezas + recuadros) · Caracterización (edad media y **rango mín.–máx.**, conteos por sexo **incluido «No binario: 1»**) · 5 temas (gráfico 0–100 + un recuadro por indicador) · Recomendaciones con IA · Nota metodológica | `IndicatorReportBuilder` (mismo índice relativo) | **Un informe imprimible con recomendaciones** |
| 13 | Sidebar Filtros (9) y «Descargar CSV» | Colegio, edad, sexo, estado civil, nivel educativo, zona, estrato, contrato y cargo. El CSV trae las filas | Sin n mínimo; el filtro de Colegio ofrece sedes con 4 docentes y «Secretaría de Educación» con 1 | Ver su colegio |

---

## 2. Problemas verificados (con números)

### 2.1 El índice relativo cambia con los filtros y puede invertir el orden
El índice se recalcula sobre el mínimo y el máximo de cada subconjunto. Para el PSS-10, «mayor» significa más estrés. En la tabla, los colegios están ordenados de menor a mayor estrés medio:

| Colegio (n) | PSS medio (0–40) | Índice hoy | Nivel hoy | BAT medio (1–5) | Índice BAT | Nivel BAT |
|---|---|---|---|---|---|---|
| Fonquetá (27) | 12,9 | 51 | Intermedio | 1,78 | 74 | Favorable |
| José Joaquín Casas (60) | 13,0 | 43 | Intermedio | 1,74* | 73 | Favorable |
| Laura Vicuña (54) | 15,0 | 39 | Intermedio | 1,97 | 52 | Intermedio |
| **La Balsa (18)** | **17,2 (el más alto)** | **66** | **Favorable** | 2,22 (el más alto) | 59 | Intermedio |
| Municipio (479) | 14,3 | 63 | Intermedio | 1,89 | 73 | **Favorable** |

\*Medias del BAT recalculadas en la escala original de 1 a 5 (`BTA_T`/12 + 1).

- El colegio con **más** estrés sale como el único «Favorable» en estrés. La captura `09_filtro_labalsa.png` lo muestra en verde.
- En el municipio, el burnout sale «Favorable» y el KPI «Salud mental en atención» vale 0.
- Ninguna de estas etiquetas sale de un punto de corte.

### 2.2 Datos imputados que se presentan como reales (hallazgo nuevo)
`ExcelProcessor._impute_missing` rellena con la **mediana** todo número que falte, y el tablero carga la versión de Storage pasando por ese procesador:

- **Bienestar psicosocial (BLG_Psicoso)** solo existe en 2025 (n = 189). El tablero imputa los 290 docentes de 2026 con la mediana (63) y muestra **N = 479 y media 61,8**. Lo real es **N = 189 y media 60,0** (6,00 en la escala de 1 a 7). Ese indicador figura además como la «Principal fortaleza» del PDF.
- También se imputan «Personas a cargo» (290 celdas), «Horas extra semanales» (304) y la edad (2).

### 2.3 Totales `*_T` con polaridad mezclada o con ítems mal asignados
Ver §5. El α de los totales actuales es de 0,47 en PRPS_CE, 0,53 en MT_T, 0,59 en CR_T y 0,47 en IR_T, con correlaciones ítem-resto negativas en IR1 (−0,37), ERS_ACP1 (−0,46), PRPS_CE2 (−0,47), CE8 (−0,38), CE7 (−0,15) y CE11 (−0,07).

### 2.4 Sin mínimo de grupo
- Los filtros permiten ver gráficos y generar el PDF de 1 a 9 docentes: sedes Campincito (4) y El Cerro (4), Secretaría (1).
- «Comparar por grupo» muestra categorías pequeñas.
- El PDF publica «No binario: 1» y el rango de edad mín.–máx., que son valores individuales.
- Riesgo de resta: si se publican los 13 colegios con n ≥ 10 junto al total municipal, el resto (4 + 4 + 1 = 9) se puede deducir. **Solución:** fusionar las sedes con su institución (CND = 73, Fusca = 17) y excluir a Secretaría (1) del universo publicado. Así quedan **12 instituciones, todas con n ≥ 17**, y 478 docentes.

### 2.5 Otras sorpresas de calidad que afectan a la vista
- **«Número de hijos» = 10** en 69 docentes, todos de 2025. Es casi seguro un código (¿«no responde»?), y produce la barra fantasma de la captura `06`. Hay que tratarlo como faltante hasta que el equipo lo confirme.
- **Cambio de formulario.** En 2025 la escala de acuerdo tenía 6 opciones y en 2026 tiene 5, codificadas sobre la misma recta 0–5, pero en 2026 no existe el código 2. Responsabilidad organizacional sube **+0,71 DE** entre versiones (1,03 → 1,84). Defensa (+0,23), cambio organizacional (+0,21) y PSS (−0,22) cambian menos.
- **Cargo.** En 2025 se preguntó «Nivel de cargo» (Operativo / Directivo / Administrativo) y en 2026 «Cargo (detalle)». Unificados, quedan **Docente de aula 446 · Directivo/apoyo 33**.
- «Sede» solo tiene «Principal» con n ≥ 10. **No se propone comparar por sede.** Lo que sí funciona es «Nivel en que dicta clase» (solo en 2026): Preescolar 41 · Primaria 92 · Básica 76 · Media 81.

### 2.6 Qué escalas tienen cortes publicados y cuáles no

| Escala en el archivo | Instrumento (identificado por los ítems) | Rango para mostrar | ¿Corte publicado? | Lectura propuesta |
|---|---|---|---|---|
| PSS1–10 | Escala de Estrés Percibido, PSS-10 (Cohen) | 0–40 | **Convencional, no oficial**: 0–13 bajo · 14–26 moderado · 27–40 alto (Cohen no publicó cortes) | % por banda + media frente al punto medio (20) |
| BTA1–12 | **Burnout Assessment Tool, BAT-12** (Schaufeli et al.): agotamiento, distancia mental, deterioro cognitivo y emocional; anclas nunca…siempre | 1–5 (= código + 1) | **Sí, en el manual del BAT**: riesgo ≈ 2,59 y riesgo muy alto ≈ 3,02 (valores del BAT-23; **hay que confirmar los del BAT-12**) | % ≥ riesgo y % ≥ riesgo muy alto |
| PRPS_CE1–16 | **CoPsoQ-ISTAS21, versión corta**: ítems 1–6 = Exigencias psicológicas; 7–16 = Trabajo activo y posibilidades de desarrollo | 0–24 y 0–40 | **Sí, tablas de referencia del manual ISTAS21** (población asalariada española): exigencias 0–7 / 8–10 / 11–24; trabajo activo 40–26 / 25–21 / 20–0. **Hay que verificarlas en el manual** | % por banda |
| MT, CL, AP, CR, CO | Adaptación del **HSE Management Standards Indicator Tool** | 0–5 (6 opciones, no las 5 del HSE) | Las referencias del HSE (percentiles del Reino Unido) **no aplican**: cambian las opciones y algunos ítems | Media frente al punto medio (2,5) y frente al municipio |
| RO, Comp, DefO, Sat, IR | Ítems propios del estudio | 0–5 | No | Ídem |
| Conf_FaTr / Conf_TrFa | Conflicto familia↔trabajo (Netemeyer et al., 1996) | 1–7 | No | Media frente a 4 y frente al municipio |
| BLG_* | Cuestionario de Bienestar Laboral General, qBLG (Blanch et al.) | 1–7 | Solo baremos percentílicos; no hay corte clínico | Media frente a 4 y frente al municipio |
| Descon | Desconexión psicológica (REQ, Sonnentag y Fritz; 3 ítems) | 1–5 | No | Media frente a 3 |
| IRI_PT / IRI_EC | IRI de Davis | 0–4 | No | Solo en la vista del investigador |
| ERS_* | Escala tipo DERS-E (dificultades de regulación emocional) | 0–3 | No | Solo en la vista del investigador |

---

## 3. Propuesta sección por sección

### Reglas comunes (se aplican a todo, en pantalla y en el PDF)

| Regla | Detalle |
|---|---|
| **Colores** | 3 tonos y **nunca rojo**: verde `#1A7F4B` (zona favorable), ámbar `#B07D0D` (zona intermedia) y **naranja `#D9822B` como máximo** (zona desfavorable). Gris para «sin dato / suprimido». Desaparecen `#C0392B` y la escala rojo→verde del histograma |
| **Semáforo anclado** | (a) Con corte publicado (PSS, BAT, ISTAS): el color sale de la banda del corte. (b) Sin corte: el color sale del **tercio de la escala teórica** en que cae la media, ya orientada. Es la misma regla que ya usa `scoring.estado_from_score` en el semáforo BM que el equipo vio en la demo. El color **no cambia al filtrar**, porque no depende del mínimo ni del máximo de la muestra |
| **Etiquetas** | Se reemplazan «Favorable / Intermedio / Atención» por «Zona favorable / intermedia / a vigilar de la escala». Con corte publicado, se usa el nombre de la banda: «estrés alto (PSS ≥ 27)» |
| **Texto fijo** | Cada indicador tiene una frase fija de catálogo: qué mide, qué significa un valor alto, la fuente y el ancla verbal de la media («en promedio, entre *rara vez* y *alguna vez*»). Nada de IA en la vista |
| **n mínimo = 10** | Por debajo de 10, la vista muestra «Grupo con menos de 10 docentes: no se muestran resultados» (no se muestran barras, tabla, histograma ni PDF). Para los %, k ≥ 3 y n − k ≥ 3, como en Estudiantes y Cuidadores |
| **IC 95 %** | Medias con IC t; % con IC de Wilson; diferencias colegio − resto con IC de Welch |
| **Universo** | Sedes fusionadas con su institución y sin la Secretaría (n = 478). Bienestar psicosocial solo con 2025 y rotulado «(solo 2025, n = 189)». **Sin imputación** |
| **Versión del formulario** | Las escalas de acuerdo (Comp, DefO, Sat, IR, RO) llevan la nota «cambió el formulario en 2026». En la vista del investigador, la media se da por versión |

### 3.1 KPIs (sección 1)
**Hoy:** «479 · 27 indicadores · 0 en atención».
**Cambia:** se mantiene una fila de tarjetas, pero la tercera y la cuarta pasan a ser cifras con corte publicado.

```
┌──────────────┬────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ Docentes     │ Estrés percibido (PSS-10)  │ Burnout (BAT-12)             │ Exigencias psicológicas      │
│ 478          │ moderado o alto: 56,4 %    │ en riesgo: 12,3 %            │ (ISTAS21) en zona alta:      │
│ 12 colegios  │ [51,9–60,7] · alto 2,1 %   │ [9,7–15,6] · muy alto 5,4 %  │ 58,9 % [54,4–63,2]           │
│              │ ámbar                      │ ámbar                        │ naranja                      │
└──────────────┴────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```
**Por qué no se pierde nada y mejora:** sigue habiendo una lectura de un vistazo y cuántos son. El «0 en atención» pasa a ser un % con corte publicado e IC, que no cambia de sentido al filtrar.

### 3.2 Aviso azul (sección 2)
**Cambia:** texto fijo, sin la ruta al .md:

> «Cada barra muestra la media del grupo en la escala original del cuestionario. El color indica en qué zona de la escala cae: verde (favorable), ámbar (intermedia) o naranja (a vigilar). En el estrés, el burnout y las exigencias se usan cortes publicados. No es un diagnóstico individual.»

### 3.3 Barras por tema con semáforo (sección 3): **se conserva mejorado**
Se mantienen los temas, el orden y el color por barra. El eje deja de ser «0–100 relativo» y pasa a ser «% de la escala teórica» (0 = mínimo posible, 100 = máximo posible, orientado a «mayor = mejor»). Cada barra lleva su IC y una marca ◆ con la media municipal cuando hay un filtro activo.

```
🧠 Salud mental y estrés                       (media [IC95] · escala · fuente)
Estrés percibido PSS-10   ███████████▌░░░░░░░  14,3 [13,8–14,8] /40  ámbar  corte convencional
Burnout BAT-12            ███████████████▊░░░  1,89 [1,84–1,95] /1–5 verde  manual BAT
  · Agotamiento           ██████████▊░░░░░░░░  2,82 [2,73–2,90]      ámbar
Somatización (qBLG)       ███████████▏░░░░░░░  3,79 [3,63–3,94] /1–7 ámbar
Desgaste (qBLG)           ██████████░░░░░░░░░  4,00 [3,84–4,16] /1–7 ámbar
Alienación (qBLG)         ██████████████▋░░░░  2,47 [2,34–2,60] /1–7 verde
Bienestar psicosocial*    ████████████████▋░░  6,00 [5,86–6,15] /1–7 verde  *solo 2025, n=189
```

Composición de los temas:

- **🛠️ Recursos y demandas del trabajo:** control sobre el trabajo, demandas de tiempo, apoyo del líder, apoyo de compañeros, claridad de rol, conflicto de rol, cambio organizacional, responsabilidad organizacional, ISTAS exigencias psicológicas e ISTAS trabajo activo.
- **😊 Bienestar laboral:** compromiso, defensa de la organización, satisfacción, intención de retiro (corregida), desconexión y conflicto trabajo→familia / familia→trabajo.

Las barras desfavorables nunca pasan de naranja.

**Por qué no se pierde nada y mejora:** es el mismo gráfico con los mismos temas y el mismo semáforo. Ahora el color significa lo mismo en el municipio y en un colegio. Los indicadores del tema «Otros» que tienen dirección conocida (PRPS → ISTAS, Conf FaTr/TrFa, Desconexión) **suben** a su tema con dirección y etiqueta claras, así que no se pierden. Solo se ve diferente «Bienestar psicosocial», que muestra su N real.

### 3.4 Mensajes «Requieren atención / Favorables» (sección 4): **se reemplazan**
Se sustituyen por dos listas fijas calculadas con el semáforo anclado:

- **«Aspectos en zona a vigilar»:** los que caen en naranja según su corte o su tercio.
- **«Aspectos en zona favorable»:** los verdes.

Cada entrada lleva la cifra y su IC. **La información (qué priorizar) se conserva** y deja de decir que el burnout es «Favorable» por una cuenta relativa.

### 3.5 Tabla completa (sección 6): **se conserva mejorada**
Columnas nuevas:

- Indicador · Tema · Instrumento · Ítems · Escala teórica · Media [IC95] · DE · % en banda de corte (si existe) · Zona · N · α · Nota (versión, «solo 2025»).

Se quita «Nivel (muestra)» y el rango observado mín.–máx., que es un valor individual, pasa a la vista del investigador como P10–P90.

### 3.6 Explorar un indicador (sección 7): **se conserva mejorado**
- Métricas: media [IC], N y escala teórica, en lugar del «rango observado».
- La **distribución** se muestra con las opciones de respuesta o las bandas de corte en % (con k ≥ 3, y «<3» en las barras pequeñas), en lugar de un histograma de conteos crudos.
- Un texto fijo explica qué mide el indicador.

### 3.7 Comparar por grupo (sección 8): **se conserva mejorado**
- **Grupos disponibles:** Colegio (las 12 instituciones), Cargo unificado (aula / directivo-apoyo), Nivel en que dicta clase (2026), Sexo (F/M; el resto se agrupa como «otro / no responde» y se suprime si n < 10), Tipo de contrato (propiedad / provisionalidad; comisión, con 6, se suprime) y rangos de edad.
- **Se quitan del selector** Fecha y Versión, y pasan a la vista del investigador.
- Cada barra lleva su IC, la línea del municipio y el n. Los grupos con n < 10 no se dibujan y se indica «1 grupo con menos de 10 docentes no se muestra».

Ejemplo con datos reales (PSS-10):

| Colegio | n | Media [IC95] | Diferencia con el resto [IC95] |
|---|---|---|---|
| La Balsa | 18 | 17,2 [13,7–20,7] | +3,0 [−0,5; +6,5] |
| Laura Vicuña | 54 | 15,0 [13,6–16,5] | +0,9 [−0,7; +2,4] |
| Fonquetá | 27 | 12,9 [10,5–15,2] | −1,5 [−3,9; +0,9] |
| Municipio | 478 | 14,3 | — |

Otro ejemplo, apoyo del líder en Laura Vicuña: 2,00 frente al resto, −0,92 [−1,27; −0,58].

Factibilidad: el % con PSS ≥ 14 se puede publicar en 12 de 12 colegios, el BAT ≥ 2,59 en 11 de 12 y las exigencias ISTAS altas en 12 de 12. **El PSS alto (≥ 27) no se puede publicar en ningún colegio** (k < 3), así que solo se da para el municipio.

### 3.8 Perfil (sección 10): **se conserva mejorado**
- Se mantienen las 2 subpestañas, pero cada variable pasa a una **tabla n / %** (o a barras de %), con «<10» enmascarado y las categorías raras agrupadas (No binario, Viudo, Más de 10 SMLV…).
- La edad se presenta con media y rango intercuartílico.
- «Número de hijos = 10» se trata como faltante hasta que el equipo decida.
- Los ejes dejan de mostrar «(SD)Edad».

### 3.9 Filtros y CSV (sección 13)
- **Filtros:** se conservan los 9, y Colegio lista instituciones, no sedes.
- **n mínimo:** si la combinación deja n < 10, todo el cuerpo y el botón de PDF muestran el aviso de supresión.
- **CSV:** pasa a ser **solo para el modo investigador**, sin cuasi-identificadores (edad exacta, estado civil, hijos), o se elimina. El equipo decide (ver §6).

### 3.10 Lo que se quita (ya aprobado)
| Elemento | Por qué se quita | Dónde queda la información |
|---|---|---|
| Botón «✨ Interpretar salud mental con IA» | Texto libre sobre salud mental, construido con el índice relativo | Textos fijos por indicador (§3.3) y lista «zona a vigilar» (§3.4) |
| Botón «✨ Interpretar «X» con IA» | Ídem | Texto fijo en «Explorar» (§3.6) |
| KPI «Salud mental en atención» e índice relativo 0–100 | Cambia con los filtros y no es un corte | KPIs con corte (§3.1) y barras en escala teórica (§3.3) |
| Mensajes «Requieren atención / Favorables» del índice relativo | Clasificación relativa | Listas ancladas (§3.4) |
| Tema «📊 Otros indicadores» | Sin dirección ni etiqueta | Sus indicadores se recolocan (§3.3). PRPS_Fam (1 ítem de doble presencia) pasa a la tabla del investigador |
| Pestaña «🎓 Correlaciones» | Puntajes crudos sin orientar, sin cifras ni IC | Vista del investigador: Spearman con IC y BH, como en Estudiantes |

**Se mantienen sin cambios en esta propuesta:** Chat con IA, Reportes y el PDF con sus recomendaciones con IA (ver §3.11).

### 3.11 PDF (sección 12): **mismas secciones, números corregidos**
| Sección del PDF | Hoy | Propuesta |
|---|---|---|
| Portada | Igual | Igual; añade «Universo: N docentes de K colegios» |
| Resumen ejecutivo | 4 KPIs (docentes, indicadores, focos, fortalezas) y recuadros «Principal foco / fortaleza» | Los mismos 4 huecos con las tarjetas de §3.1. Los recuadros de foco y fortaleza salen de las listas ancladas (§3.4), en naranja o verde, nunca en rojo |
| 1. Caracterización | Edad media y **mín.–máx.**, conteos por sexo con «No binario: 1» | Edad media y RIC; tabla n / % con «<10» |
| Secciones por tema | Gráfico 0–100 y un recuadro «resultado favorable / intermedio / atención» por indicador | El gráfico de §3.3 y el recuadro con frase fija, media [IC] y zona o banda |
| Recomendaciones | Gemini, alimentado con «posición X/100» | **Se conserva**, pero el prompt recibe las cifras corregidas (media [IC], escala, banda de corte) y ningún conteo menor de 10. Pendiente de la decisión A/B del 1-oct |
| Nota metodológica | Explica la posición relativa | Explica las escalas teóricas, los cortes y sus fuentes, el n ≥ 10, la ausencia de imputación y el cambio de formulario |
| Generación | Cualquier filtro | Bloqueada si n < 10 |

---

## 4. Tabla de correspondencia «hoy → propuesta → se conserva porque»

| Hoy | Destino | Propuesta | Se conserva porque… |
|---|---|---|---|
| Pestaña «Salud mental e indicadores» | Se conserva igual | Mismo nombre y orden | — |
| KPI Docentes | Se conserva mejorado | Docentes del universo publicado + nº de colegios | Mismo dato, sin la Secretaría ni sedes de menos de 10 |
| KPI Indicadores (27) | Se reemplaza por X | Tarjeta «Estrés percibido: % moderado o alto [IC]» | Contar indicadores no informa; el hueco pasa a una cifra útil |
| KPI «Salud mental en atención» | **Se quita** (aprobado) | Tarjetas «Burnout en riesgo» y «Exigencias altas» con corte publicado | La pregunta «¿cuántos focos?» se responde con % y corte |
| Aviso azul | Se conserva mejorado | Texto fijo sin la ruta al .md | Sigue explicando cómo leer las barras |
| Barras por tema (4 temas con dirección) | Se conserva mejorado | Escala teórica, IC, semáforo anclado y marca ◆ municipal | Mismos temas, mismo orden, mismos colores (sin rojo) |
| Semáforo verde / ámbar / rojo | Se conserva mejorado | Verde / ámbar / naranja anclados a corte o a tercio teórico | El equipo conserva el semáforo, que ya no cambia al filtrar |
| Tema «Otros indicadores» | **Se quita** (aprobado) | ISTAS (2 escalas), Conflictos y Desconexión pasan a sus temas; PRPS_Fam pasa al investigador | Ningún indicador desaparece |
| «Requieren atención / Favorables» | **Se quita** (aprobado) | Listas «zona a vigilar / favorable» ancladas | Misma función de priorizar |
| Botón IA salud mental | **Se quita** (aprobado) | Frases fijas por indicador | La interpretación queda escrita, revisada y estable |
| Tabla completa | Se conserva mejorado | + instrumento, escala, IC, α, banda; − «Nivel (muestra)» | Todos los números siguen ahí, y hay más |
| Explorar un indicador | Se conserva mejorado | Media [IC], escala y distribución en % por opción o banda | Misma exploración, sin exponer valores extremos |
| Comparar por grupo | Se conserva mejorado | + Colegio, cargo unificado y nivel; IC; n ≥ 10; − fecha y versión | Más comparaciones útiles y seguras |
| Botón IA del indicador | **Se quita** (aprobado) | Frase fija | Ídem |
| Perfil (2 subpestañas) | Se conserva mejorado | Tablas n / % con «<10» | Misma información sobre la composición |
| Pestaña Correlaciones | **Se quita** (aprobado) | Vista del investigador con Spearman, IC y BH | El equipo investigador conserva el análisis |
| Filtros (9) | Se conserva mejorado | Instituciones en lugar de sedes; bloqueo con n < 10 | Mismos filtros |
| Descargar CSV | Pendiente de decisión | Modo investigador sin cuasi-identificadores, o quitar | — |
| Botón PDF (sidebar) | Se conserva mejorado | Mismas secciones con cifras corregidas | §3.11 |
| Recomendaciones IA del PDF | Se conserva igual (función) | Prompt con cifras corregidas y sin conteos pequeños | El equipo pidió mantenerlas |
| Chat con IA · Reportes | Se conserva igual | Sin cambios en esta propuesta | El equipo pidió mantenerlos |
| Vistas BM (demo) | Se conserva igual | No se tocan; solo afectan al CSV de demostración | — |

---

## 5. Corrección de la puntuación

### 5.1 Dónde se corrige
1. **`scripts/preparar_docentes.py`**:
   - Quitar de `INVERTIDOS[4]` el ítem PRPS_CE2 y los PRPS_CE9–16; dejar PRPS_CE3.
   - Quitar ERS_ACP1 de `INVERTIDOS[3]`.
   - Añadir IR1 (invertir con 5 − x).
   - Reemplazar en `TOTALES` los totales mezclados por las subescalas de la tabla 5.2. Los `*_T` viejos se renombran o se eliminan para que nadie los vuelva a sumar.
2. **Nuevo catálogo de dimensiones docentes**, en `src/analysis/indicators.py` o en un `src/docentes/catalogo.py` análogo al de estudiantes y cuidadores. Para cada dimensión: ítems, inversión, agregación (media o suma), escala teórica, dirección, corte, fuente, frase fija y «solo versión». La vista deja de depender de que la columna termine en `_T`.
3. **`src/data/processor.py`**: no imputar en el archivo docente (y no imputar ítems de escala en general). Eso corrige el N y la media de bienestar psicosocial.
4. `compute_dimension_scores` (esquema BM) no se toca, porque solo afecta al demo.

### 5.2 Definiciones (ítems en la codificación actual del archivo; «inv» = invertir)
| Dimensión nueva | Ítems | Orientación | Agregación · escala | α nuevo (antes) |
|---|---|---|---|---|
| Estrés percibido PSS-10 | PSS1–10 (3, 4, 5, 7 y 9 ya invertidos; correcto) | ↑ = más estrés | Suma 0–40 | 0,81 (=) |
| Burnout BAT-12 | BTA1–12, +1 | ↑ = más burnout | Media 1–5; subescalas 1–3 / 4–6 / 7–9 / 10–12 | 0,91 (=) |
| **Control sobre el trabajo** | MT1–3 | ↑ = mejor | Media 0–5 | 0,68 (MT_T 0,53) |
| **Demandas de tiempo** | MT4–7 | ↑ = peor | Media 0–5 | 0,83 (MT_T 0,53) |
| Apoyo del líder | CL1–7 | ↑ = mejor | Media 0–5 | 0,97 |
| Apoyo de compañeros | AP1–3 | ↑ = mejor | Media 0–5 | 0,95 |
| **Claridad de rol** | CR1–4 | ↑ = mejor | Media 0–5 | 0,89 (CR_T 0,59) |
| **Conflicto de rol** | CR5–7 | ↑ = peor | Media 0–5 | 0,84 (CR_T 0,59) |
| Cambio organizacional | CO1–4 | ↑ = mejor | Media 0–5 | 0,88 |
| Responsabilidad organizacional | RO1–5 | ↑ = mejor | Media 0–5; ⚠ efecto de versión +0,71 DE | 0,92 |
| Conflicto familia→trabajo | Conf_FaTr1–5 | ↑ = peor | Media 1–7 | 0,88 |
| Conflicto trabajo→familia | Conf_TrFa1–5 | ↑ = peor | Media 1–7 | 0,95 |
| Compromiso / Defensa / Satisfacción | Comp1–3 / DefO1–3 / Sat1–3 | ↑ = mejor | Media 0–5 | 0,85 / 0,87 / 0,79 |
| **Intención de retiro** | IR1 **inv** (5 − x), IR2–4 | ↑ = más intención de irse | Media 0–5 | 0,80 (IR_T 0,47) |
| Bienestar psicosocial (expectativas qBLG) | BLG_Psicoso1–10, **solo 2025** | ↑ = mejor | Media 1–7, **sin imputar** | 0,94 |
| Somatización / Desgaste / Alienación | BLG_Som1–5 / BLG_Desg1–4 / BLG_Alie1–4 | ↑ = peor | Media 1–7 | 0,89 / 0,94 / 0,91 |
| Desconexión psicológica | Descon1–3 | ↑ = mejor | Media 1–5 | 0,93 |
| **ISTAS Exigencias psicológicas** | CE1, CE2 (**sin invertir**), CE3 inv (ya está), CE4–6 | ↑ = peor | Suma 0–24 | 0,77 (PRPS_CE_T 0,47) |
| **ISTAS Trabajo activo y desarrollo** | CE7–8 tal cual; CE9–16 **des-invertir** (4 − x) | ↑ = mejor | Suma 0–40 | 0,76 (PRPS_CE_T 0,47) |
| ERS no aceptación (ACP) | ACP1 **des-invertir** (3 − x), ACP2–6 | ↑ = más dificultad | Media 0–3 | 0,83 (0,63) |
| ERS CON / CLA / MET | Sin cambio | ↑ = más dificultad (CON = desatención) | Media 0–3 | 0,70 / 0,73 / 0,54 |
| IRI toma de perspectiva | IRI_PT (3 y 15 invertidos) | ↑ = más | Media 0–4 | 0,70 |
| IRI preocupación empática | IRI_EC **sin el ítem 13** (en Davis es Malestar personal) | ↑ = más | Media 0–4 | 0,60 (0,59) |
| Doble presencia | PRPS_Fam_T (1 de los 4 ítems de ISTAS) | — | Solo distribución, en el investigador | — |

### 5.3 Efecto esperado sobre las cifras actuales (municipio, agregados)
| Indicador | Hoy en el tablero (media `*_T` · índice relativo · nivel) | Después (media [IC95] en la escala · zona) | Qué cambia en la lectura |
|---|---|---|---|
| Estrés PSS | 14,29 · 63 · Intermedio | 14,3 [13,8–14,8] /40; bajo 43,6 % · moderado 54,3 % · alto 2,1 % [1,1–3,8] | Mismo número, ahora con bandas. Más de la mitad, en estrés moderado |
| Burnout | 10,72 /48 · 73 · **Favorable** | 1,89 [1,84–1,95] /1–5; en riesgo (≥ 2,59) 12,3 % [9,7–15,6], muy alto (≥ 3,02) 5,4 % [3,7–7,8] (con 2,54 / 2,95: 15,0 % / 7,3 %) | De «Favorable» a «1 de cada 8 en riesgo». Agotamiento 2,82, cerca del punto medio |
| Manejo/control del tiempo | 14,23 /35 · 41 · Intermedio | **Control 2,94** [2,85–3,03] /5 (intermedio) + **Demandas 1,35** [1,26–1,45] /5 (favorable) | El total sumaba cosas opuestas y ahora son dos lecturas claras |
| Claridad de rol | 22,44 /35 · 55 · Intermedio | **Claridad 4,45** [4,38–4,51] (favorable) + **Conflicto de rol 1,55** [1,43–1,67] (favorable) | De «intermedio» a la fortaleza más alta |
| Intención de retiro | 6,43 /20 · 68 · Favorable (hoy suma «me veo aquí el próximo año» como si fuera intención de irse) | 0,72 [0,63–0,81] /5 (baja) | Mismo sentido, pero ahora la cifra es interpretable |
| PRPS «Conflicto/estrés» | 24,98 /64 · dirección «—» | **Exigencias 11,5** /24, alta (≥ 11) en el 58,9 % [54,4–63,2] · **Trabajo activo 26,0** /40, verde (≥ 26) en el 55,5 %, rojo en el 16,3 % | Un indicador sin sentido pasa a ser el foco más claro: exigencias psicológicas altas |
| Bienestar psicosocial | 61,82 /70 · N = 479 · **Principal fortaleza** | 6,00 [5,86–6,15] /7 · **N = 189 (solo 2025)** | Corrige la imputación de 290 docentes |
| Responsabilidad organizacional | 7,62 /25 · 30 · Atención | 1,52 [1,42–1,63] /5, zona a vigilar (naranja); 2025: 1,03 · 2026: 1,84 | Sigue siendo el recurso más bajo, con aviso de versión |
| Desgaste qBLG | 15,99 /28 · 50 · Intermedio | 4,00 [3,84–4,16] /7 (= punto medio) | Igual, con escala |
| Somatización | 18,94 /35 · 54 · Intermedio | 3,79 [3,63–3,94] /7 | Igual, con escala |
| Alienación | 9,89 /28 · 75 · Favorable | 2,47 [2,34–2,60] /7 | Igual |
| Conflicto trabajo→familia | 11,39 · «—» (Otros) | 2,28 [2,16–2,40] /7, favorable, ↑ = peor | Gana dirección y tema |
| Desconexión | 9,16 · «—» (Otros) | 3,05 [2,95–3,15] /5 (punto medio) | Gana dirección y tema |
| ERS ACP | 5,39 /18 · «—» | 0,77 [0,72–0,82] /3 (ACP1 corregido) | α de 0,63 a 0,83 |
| Apoyo líder · compañeros · cambio · compromiso · defensa · satisfacción | Sin cambio de ítems | 2,82 · 2,93 · 2,51 · 4,25 · 4,15 · 4,27 (/5) | Solo cambian la escala y el IC |

---

## 6. Riesgos y qué debe aprobar el equipo

| # | Decisión | Opción recomendada | Riesgo si no se decide |
|---|---|---|---|
| 1 | Cortes del PSS-10 (0–13 / 14–26 / 27–40) | Usarlos rotulados como «convencionales» y citar que Cohen no publicó cortes | Se lee como diagnóstico |
| 2 | Cortes del BAT-12 | Confirmar en el manual (Schaufeli, De Witte y Desart) los valores del BAT-12 y, mientras tanto, mostrar 2,59 / 3,02 marcados como provisionales | El % varía entre 12,3 y 15,0 según el corte |
| 3 | Uso de las tablas de referencia ISTAS21 (población española) | Aceptarlas como referencia externa, con la nota «población de referencia española» | Si no, exigencias y trabajo activo se leen solo frente al punto medio |
| 4 | Nombres visibles de las dimensiones nuevas (control / demandas, claridad / conflicto de rol, exigencias / trabajo activo, ERS) | Validar con el instrumento original. La asignación de ítems ERS a subescalas no coincide del todo con la DERS-E | Etiquetas erróneas en el PDF |
| 5 | Ítem IRI_EC(13) | Sacarlo de EC (Davis lo asigna a Malestar personal) | Mínimo: α 0,59 → 0,60 |
| 6 | Colores | Verde / ámbar / naranja, sin rojo | — |
| 7 | Semáforo sin corte = tercio de la escala teórica | Aprobar (es la regla del semáforo BM ya existente) | Los tercios son una convención, no clínicos; hay que decirlo en la nota |
| 8 | «Número de hijos = 10» (69 casos de 2025) | Tratarlo como faltante; confirmar con el formulario de 2025 | Perfil distorsionado |
| 9 | Efecto de versión en RO (+0,71 DE) y en las escalas de acuerdo | Mostrar con aviso; en la vista del investigador, por versión | Comparaciones entre colegios confundidas con la ola |
| 10 | CSV de filas | Quitarlo, o solo en modo investigador y sin cuasi-identificadores | Reidentificación |
| 11 | Sede | No comparar por sede (solo «Principal» tiene n ≥ 10) | — |
| 12 | Prompt de las recomendaciones IA del PDF | Mantener con cifras corregidas, a la espera de la decisión A/B del 1-oct | Recomendaciones basadas en el índice viejo |
| 13 | Imputación en `processor.py` | Desactivarla para docentes | N ficticios |

**Riesgos técnicos:**
- Otros consumidores de los `*_T`. `src/triangulacion/fuentes.py` usa ítems y no totales, así que no se rompe, pero hay que revisar los tests.
- Los textos fijos necesitan revisión del dominio.
- El PDF debe cumplir las mismas reglas de n que la vista.

## 7. Plan por fases

| Fase | Contenido | Archivos | Criterio de salida |
|---|---|---|---|
| **1 · Puntuación y privacidad** | Corregir las inversiones y las subescalas (§5.2); quitar la imputación; nuevo catálogo de dimensiones docentes (escala, dirección, corte, fuente, frase); universo con sedes fusionadas y sin Secretaría; utilidades n ≥ 10, k ≥ 3, IC de Wilson / t / Welch; tests con los α y las medias de §5.3 | `scripts/preparar_docentes.py`, `src/data/processor.py`, catálogo nuevo, `tests/` | Las medias y los α de §5.3 se reproducen; ningún grupo menor de 10 sale de las funciones |
| **2 · Vista** | KPIs, barras con semáforo anclado, listas ancladas, tabla, «Explorar», comparación por grupo (colegio, cargo, nivel), perfil n / %, filtros con bloqueo; quitar los 2 botones IA, el tema «Otros» y Correlaciones (lo de Correlaciones pasa a la vista del investigador) | `src/ui/dashboard.py`, `src/analysis/indicators.py`, `filtering.py` | Revisión del equipo con capturas antes y después; ningún elemento de §4 queda sin destino |
| **3 · PDF** | Mismas secciones, con las cifras de la fase 1; caracterización sin valores individuales; prompt de recomendaciones con cifras corregidas; bloqueo con n < 10 | `src/reports/indicator_report.py` | Tras la decisión A/B del 1-oct; el PDF del municipio y uno de colegio, revisados por el equipo |
