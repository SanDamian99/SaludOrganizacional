# Docentes · fase 1: cifras que cambian

> **Fecha:** 10-oct-2026. **Rama:** `feature/docentes-fase1`.
> **Datos:** versión activa de docentes (479 docentes: 189 de 2025 y 290 de 2026). Solo agregados del municipio.
> **Base:** `docs/analisis/2026-10-10-propuesta-docentes.md`, §5 (puntuación) y §7 (fase 1). Los 13 puntos de §6 se tomaron como aprobados provisionalmente.

## Qué cambió en el código

| Cambio | Dónde | Efecto |
|---|---|---|
| Catálogo de dimensiones docentes: ítems, inversión, agregación, escala teórica, dirección, cortes, fuente, frase, aviso de versión, «solo 2025» | `src/docentes/catalogo.py` | Una sola fuente de verdad; la vista deja de depender de que la columna termine en `_T` |
| Puntuación desde los ítems, con recodificación del archivo actual | `src/docentes/scoring.py` | El archivo de Storage (codificación 1) se puntúa bien sin reemplazarlo: `normalizar_codificacion` des-invierte PRPS_CE2, CE9–16 y ERS_ACP1 e invierte IR1 |
| Sin imputación por mediana | `src/data/processor.py` | Ningún archivo se rellena. Bienestar psicosocial vuelve a N = 189 |
| «Número de hijos» = 10 → faltante al cargar | `src/docentes/limpieza.py`, `src/data/loader.py` | 69 celdas (todas de 2025) pasan a vacías en la app; el archivo no se toca |
| Script de preparación con las inversiones de §5.1.1 y totales por subescala | `scripts/preparar_docentes.py` | El archivo regenerado lleva `Codificación de ítems = 2`; desaparecen `MT_T`, `CR_T`, `PRPS_CE_T` y aparecen `MT_Control_T`, `MT_Demandas_T`, `CR_Claridad_T`, `CR_Conflicto_T`, `ISTAS_Exig_T`, `ISTAS_TA_T`… |
| Universo publicable: sedes fundidas con su institución (`catalogo.SEDES`), Secretaría fuera, grupos < 10 en «otros» con absorción si «otros» queda entre 1 y 9, IC de Welch grupo − resto | `src/docentes/universo.py`, `src/docentes/estadistica.py` | KPI «Docentes» = 478 en 12 instituciones (CND 73, Fusca 17); ningún total menos los grupos mostrados deja de 1 a 9 |
| Vista Docentes (cambio mínimo) | `src/ui/dashboard.py` | Barras en % de la escala teórica con zona anclada (verde / ámbar / naranja, nunca rojo); tabla con IC 95 %, α y zona; «Explorar» y «Comparar por grupo» sobre el puntaje nuevo. El resto de la vista es la fase 2 |

**No cambia:** Estudiantes, Cuidadores y Triangulación (sus pruebas son idénticas; la triangulación usa PSS, CL, AP y BLG_Desg, que no se recodifican). **Tampoco cambian todavía** el PDF de Docentes ni el Chat: siguen leyendo los `*_T` del archivo y el índice relativo hasta la fase 3 (decisión A/B del 1-oct).

## Semáforo anclado

- Con corte publicado: la zona es la banda donde cae la media. PSS-10 (convencional: 0–13 / 14–26 / 27–40), BAT-12 (2,59 / 3,02, **valores del BAT-23: comprobar en el manual**), ISTAS21 exigencias (0–7 / 8–10 / 11–24) y trabajo activo (0–20 / 21–25 / 26–40), **tablas de población asalariada española: comprobar en el manual**.
- Sin corte: tercio de la escala teórica, orientada (misma regla que el semáforo BM). Ya no depende del mínimo ni del máximo de la muestra, así que **no cambia al filtrar por colegio**.
- Los % por banda llevan IC de Wilson y solo se publican con k ≥ 3 y n − k ≥ 3.
- Las bandas son continuas y semiabiertas, con el límite en el medio punto para las sumas enteras: PSS «0–13» = [0, 13,5), «14–26» = [13,5, 26,5); ISTAS exigencias [0, 7,5) / [7,5, 10,5) / [10,5, 24]; trabajo activo [0, 20,5) / [20,5, 25,5) / [25,5, 40]. Una media de 13,6 cae en «moderado».

## Universo publicable (municipio, 479 respuestas)

| Institución | n |
|---|---|
| Santa María del Río | 72 |
| José Joaquín Casas | 60 |
| Colegio Nacional Diversificado (con sedes Santa Lucía y Campincito) | 73 |
| Laura Vicuña | 54 |
| San Josemaría Escrivá de Balaguer | 46 |
| Diosa Chía | 37 |
| Cerca de Piedra | 28 |
| Fonquetá | 27 |
| Bojacá | 27 |
| Fagua | 19 |
| La Balsa | 18 |
| Fusca (con sede El Cerro) | 17 |
| **Total del universo** | **478** (la Secretaría de Educación, 1 respuesta, queda fuera del universo comparable) |

«Otros» = 0: las 12 instituciones tienen 10 o más y el total es exactamente la suma de los grupos mostrados. Para las demás variables de agrupación (sexo, contrato, estrato…), los grupos con menos de 10 van juntos en «otros» y, si «otros» queda entre 1 y 9, absorbe al grupo publicado más pequeño; una prueba con el archivo real comprueba, para cada variable y cada colegio, que el total menos lo mostrado nunca deja de 1 a 9.

## Tabla de cifras que cambian (municipio)

«Antes» es lo que mostraba el tablero (media del `*_T`, N tras imputar, índice relativo 0–100 y nivel relativo). «Después» es la media en la escala de presentación con su IC 95 %, el N real y la zona anclada.

| Dimensión | N antes → después | Media antes (`*_T`) → después [IC 95 %] (escala) | Nivel antes → zona después | α antes → después |
|---|---|---|---|---|
| Estrés percibido (PSS-10) | 479 → 479 | 14,29 → 14,29 [13,76–14,83] (0–40) | Intermedio (63) → intermedia; bajo 43,6 % · moderado 54,3 % · alto 2,1 % | 0,81 → 0,81 |
| Burnout (BAT-12) | 479 → 479 | 10,72 (0–48) → 1,89 [1,84–1,95] (1–5) | **Favorable (73) → favorable, pero 12,3 % en riesgo (≥ 2,59) y 5,4 % muy alto** | 0,91 → 0,91 |
| Manejo/control del tiempo → **Control sobre el trabajo** | 479 → 479 | 14,23 (0–35) → 2,94 [2,85–3,03] (0–5) | Intermedio (41) → intermedia | **0,53 → 0,68** |
| Manejo/control del tiempo → **Demandas de tiempo** | — → 479 | — → 1,35 [1,26–1,45] (0–5), ↑ = peor | — → favorable | **0,53 → 0,83** |
| Claridad de rol → **Claridad de rol** | 479 → 479 | 22,44 (0–35) → 4,45 [4,38–4,52] (0–5) | Intermedio (55) → **favorable** | **0,59 → 0,89** |
| Claridad de rol → **Conflicto de rol** | — → 479 | — → 1,55 [1,43–1,67] (0–5), ↑ = peor | — → favorable | **0,59 → 0,84** |
| Intención de retiro | 479 → 479 | 6,43 (0–20, con IR1 al revés) → 0,72 [0,63–0,81] (0–5) | Favorable (68) → favorable | **0,47 → 0,80** |
| PRPS «Conflicto/estrés» → **Exigencias psicológicas (ISTAS21)** | 479 → 479 | 24,98 (0–64, sin dirección) → 11,48 [11,08–11,88] (0–24), ↑ = peor | «—» → **a vigilar; 58,9 % en zona desfavorable (≥ 11)** | **0,47 → 0,77** |
| PRPS «Conflicto/estrés» → **Trabajo activo y desarrollo (ISTAS21)** | — → 479 | — → 25,97 [25,45–26,50] (0–40), ↑ = mejor | — → intermedia; favorable 55,5 % · desfavorable 16,3 % | **0,47 → 0,76** |
| **Bienestar psicosocial (qBLG)** | **479 → 189** | **61,82 (imputado) → 6,00 [5,86–6,15] (1–7)** | Favorable (81) → favorable, rotulado «solo 2025» | 0,94 → 0,94 |
| Responsabilidad organizacional | 479 → 479 | 7,62 (0–25) → 1,52 [1,42–1,63] (0–5) | Atención (30) → a vigilar, con aviso de versión (2025: 1,03 · 2026: 1,84) | 0,92 → 0,92 |
| Somatización (qBLG) | 479 → 479 | 18,94 (5–35) → 3,79 [3,63–3,94] (1–7) | Intermedio (54) → intermedia | 0,89 → 0,89 |
| Desgaste (qBLG) | 479 → 479 | 15,99 (4–28) → 4,00 [3,84–4,16] (1–7) | Intermedio (50) → intermedia | 0,94 → 0,94 |
| Alienación (qBLG) | 479 → 479 | 9,89 (4–28) → 2,47 [2,34–2,60] (1–7) | Favorable (75) → favorable | 0,91 → 0,91 |
| Conflicto trabajo→familia | 479 → 479 | 11,39 (5–35, sin dirección) → 2,28 [2,16–2,40] (1–7), ↑ = peor | «—» → favorable | 0,95 → 0,95 |
| Conflicto familia→trabajo | 479 → 479 | 8,17 (5–35, sin dirección) → 1,63 [1,56–1,71] (1–7), ↑ = peor | «—» → favorable | 0,88 → 0,88 |
| Desconexión psicológica | 479 → 479 | 9,16 (3–15, sin dirección) → 3,05 [2,95–3,15] (1–5), ↑ = mejor | «—» → intermedia | 0,93 → 0,93 |
| Regulación emocional (ACP) → **no aceptación** | 479 → 479 | 5,39 (0–18, sin dirección) → 0,77 [0,72–0,83] (0–3), ↑ = más dificultad | «—» → favorable | **0,63 → 0,83** |
| Regulación emocional CON / CLA / MET | 479 → 479 | 3,65 / 2,89 / 1,49 → 0,91 / 0,72 / 0,75 (0–3), ↑ = más dificultad | «—» → favorable | 0,70 / 0,73 / 0,54 (=) |
| Empatía: toma de perspectiva (IRI) | 479 → 479 | 17,81 (0–28) → 2,54 [2,49–2,60] (0–4) | Intermedio (54) → intermedia | 0,74 → 0,70 |
| Empatía: preocupación empática (IRI) | 479 → 479 | 22,13 (0–32, con el ítem 13) → 2,79 [2,74–2,84] (0–4, sin el 13) | Intermedio (51) → favorable | 0,71 → 0,60 |
| Apoyo del líder · compañeros · cambio · compromiso · defensa · satisfacción | 479 (=) | 19,71 · 8,79 · 10,05 · 12,76 · 12,46 · 12,80 → 2,82 · 2,93 · 2,51 · 4,25 · 4,15 · 4,27 (0–5) | Intermedio · Intermedio · Intermedio · Favorable · Favorable · Favorable → intermedia · intermedia · intermedia · favorable · favorable · favorable | sin cambio |
| PRPS «Familiar» (doble presencia, 1 ítem) | 479 → 479 | 1,82 → 1,82 (1–4) | «—» → sale del tablero (solo investigador) | — |

Nota sobre los α del IRI: la propuesta daba 0,70 (PT) y 0,60 (EC sin el ítem 13); se reproducen. El α «antes» de EC (0,71, con el ítem 13) sale de los 8 ítems tal como están en el archivo.

## Qué debe saber el equipo

1. **El PDF y el Chat de Docentes siguen con las cifras viejas** (índice relativo, `*_T`, Bienestar psicosocial con N = 479 cuando el archivo pase por el procesador… ahora ya sin imputar, N = 189 pero con el índice relativo). Se corrigen en la fase 3, tras la decisión A/B.
2. **Los cortes del BAT-12 e ISTAS21 están marcados «comprobar en el manual»** (`comprobar_en_manual=True` en el catálogo) y la vista lo muestra como nota. Si cambian, se cambia una línea del catálogo.
3. **Nombres de las dimensiones nuevas** (control / demandas, claridad / conflicto de rol, exigencias / trabajo activo, regulación emocional) son los de la propuesta; los de ERS llevan la nota «nombre provisional».
4. **No reemplazar aún la versión de Storage.** Regenerar el archivo con `python -m scripts.preparar_docentes` produce la codificación 2 (IR1 invertido, PRPS_CE2/9–16 y ERS_ACP1 sin invertir, totales por subescala) y una prueba con datos reales comprueba que puntúa idéntico al archivo de Storage. Pero el PDF y el Chat catalogan todavía los `*_T` viejos (`MT_T`, `CR_T`, `PRPS_CE_T`…) y con el archivo nuevo mostrarían etiquetas genéricas para los totales nuevos: se sube la versión nueva cuando la fase 3 los haya pasado al catálogo.
6. **Universo.** El tablero compara 12 instituciones (sedes fundidas) y deja fuera a la Secretaría; el KPI «Docentes» dice 478, no 479. La tabla de arriba es la que se puede publicar.
5. **«Número de hijos» = 10** no aparece ya en el perfil (69 docentes de 2025 quedan sin dato en esa variable). Confirmar con el formulario de 2025.
