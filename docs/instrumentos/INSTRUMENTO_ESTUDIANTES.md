# Instrumento de estudiantes — diccionario de datos y puntuación

> **Fuente:** `docs/instrumentos/Instrumento_estudiantes.xlsx` (el archivo original; no se versiona
> porque `.xlsx` está en `.gitignore`). Este documento es la versión canónica y legible del
> instrumento: es lo que gobierna el código de puntuación.
>
> **Estado:** el dataset todavía no llega. Este documento define **qué esperamos recibir** y
> **cómo se puntúa**, para que la ingesta sea inmediata. Última revisión: 2026-09-17.

## 1. Qué mide el instrumento

Autorreporte del estudiante, **97 ítems en 6 escalas** más 4 variables de identificación.
Es la tercera pata del Observatorio 360: ya tenemos **docentes** (n = 189) y **cuidadores con
reporte sobre el niño** (n = 172); faltaba la voz del propio estudiante.

| Bloque | Escala | Ítems | Edad | Formato de respuesta |
|---|---|---|---|---|
| 0 | Identificación | 4 | — | Edad, Sexo, Grado/Curso, Colegio |
| 1 | SDQ — Cualidades y dificultades | 25 | 11-17 | 3 puntos: No es cierto / Algo cierto / Muy cierto |
| 2 | ARI — Índice de reactividad afectiva | 7 | 9-17 | 3 puntos: No es cierto / Algo cierto / Muy cierto |
| 3 | RCADS-25 — Ansiedad y depresión | 25 | 8-18 | 4 puntos: Nunca / Algunas veces / Con frecuencia / Siempre |
| 4 | ERQ-CA — Regulación emocional | 10 | 8-18 | 5 puntos: Nada parecido a mí … Exactamente igual a mí |
| 5 | MSPSS — Apoyo social percibido | 12 | ≥ 10 | 5 puntos: Nunca / Casi nunca / Algunas veces / Casi siempre / Siempre |
| 6 | PSSM — Pertenencia a la escuela | 18 | 8-17 | 5 puntos: No es cierto (1) … Completamente cierto (5) |

**Rango de edad efectivo: 11 a 17 años**, que es la intersección de todas las escalas. El SDQ
autoinforme es el más restrictivo (11+). Estudiantes de 8 a 10 años podrían responder ARI, RCADS,
ERQ-CA y PSSM pero **no** el SDQ ni el MSPSS con garantías; si los hay en el dataset, se analizan
aparte y se reporta como tal.

## 2. Formato de archivo que necesitamos

Una fila por estudiante, una columna por ítem. **Ítem por ítem, no totales precalculados**: los
totales se recalculan aquí para poder reportar α de Cronbach y aplicar los cortes correctos.
Las respuestas pueden venir como texto (las etiquetas de arriba) o como números; la ingesta
convierte texto a número automáticamente.

| Columna | Tipo | Notas |
|---|---|---|
| `ID_Estudiante` | texto | Anonimizado (E001, E002…). **Nunca nombres.** |
| `ID_Cuidador` | texto | *Opcional pero muy valioso*: si permite enlazar con el dataset de cuidadores, habilita el análisis multi-informante (ver §5). |
| `Edad` | entero | Años cumplidos |
| `Sexo` | texto | niño / niña (según el instrumento) |
| `Grado` | texto | Grado o curso; si tiene letra, incluirla (ej. `802`, `10B`) |
| `Colegio` | texto | **Usar los códigos ya existentes**: CND, SJMEB, JJC, DiosCh, SMR, LauV, CdP, SaLu, Fagua, Fusca, Bojacá, Fonquetá, LaBalsa, Tiquiza, CdP. Si llega el nombre completo, la app lo normaliza. |
| `SDQ1` … `SDQ25` | 0-2 o texto | En el orden del instrumento (§3.1) |
| `ARI1` … `ARI7` | 0-2 o texto | |
| `RCADS1` … `RCADS25` | 0-3 o texto | |
| `ERQ1` … `ERQ10` | 1-5 o texto | |
| `MSPSS1` … `MSPSS12` | 1-5 o texto | |
| `PSSM1` … `PSSM18` | 1-5 o texto | |

Total esperado: **102 columnas**. Formatos aceptados: `.xlsx` o `.csv` en UTF-8.

> **Advertencia sobre el orden de los ítems:** toda la puntuación depende de que el orden sea el
> del instrumento original. Si el formulario reordenó, aleatorizó o numeró distinto los ítems,
> necesitamos el mapeo antes de puntuar. Si hay duda, mándennos también el archivo crudo con los
> enunciados completos como encabezado.

## 3. Puntuación por escala

### 3.1 SDQ — Cuestionario de cualidades y dificultades (autoinforme 11-17)

Codificación: **No es cierto = 0, Algo cierto = 1, Muy cierto = 2**.

> El documento original muestra dos juegos de etiquetas ("Falso / Medianamente verdadero / Muy
> verdadero" en las instrucciones y "No es cierto / Algo cierto / Muy cierto" en el campo de
> indicadores). **Hay que confirmar cuál se aplicó en campo.** Ambas son equivalentes 0-1-2, así
> que no cambia la puntuación, pero sí el texto del artículo.

**Ítems inversos (se recodifican 2 − x): 7, 11, 14, 21, 25.**

| Subescala | Ítems | Rango |
|---|---|---|
| Síntomas emocionales | 3, 8, 13, 16, 24 | 0-10 |
| Problemas de conducta | 5, 7ᴿ, 12, 18, 22 | 0-10 |
| Hiperactividad / inatención | 2, 10, 15, 21ᴿ, 25ᴿ | 0-10 |
| Problemas con pares | 6, 11ᴿ, 14ᴿ, 19, 23 | 0-10 |
| Conducta prosocial | 1, 4, 9, 17, 20 | 0-10 |
| **Total dificultades** | suma de las 4 primeras | 0-40 |
| Internalizante | emocional + pares | 0-20 |
| Externalizante | conducta + hiperactividad | 0-20 |

**Es el mismo orden, las mismas subescalas y los mismos ítems inversos que la versión para padres**
que ya usamos en el dataset de cuidadores. El código de puntuación se reutiliza tal cual; solo
cambian las bandas de corte.

**Bandas oficiales, versión autoinforme** (SDQ, cuatro bandas, muestra comunitaria del Reino Unido):

| Escala | Cercano al promedio | Ligeramente elevado | Alto | Muy alto |
|---|---|---|---|---|
| Total dificultades | 0-14 | 15-17 | 18-19 | 20-40 |
| Emocional | 0-4 | 5 | 6 | 7-10 |
| Conducta | 0-3 | 4 | 5 | 6-10 |
| Hiperactividad | 0-5 | 6 | 7 | 8-10 |
| Pares | 0-2 | 3 | 4 | 5-10 |
| Prosocial* | 7-10 | 6 | 5 | 0-4 |

\* En prosocial las bandas se leen al revés: *ligeramente disminuido / bajo / muy bajo*.
Bandas de tres niveles (clásicas), por si se comparan con literatura antigua: normal 0-15,
límite 16-19, anormal 20-40.

⚠️ **Los cortes del autoinforme son distintos a los de padres** (padres: 0-13 / 14-16 / 17-19 /
20-40). Nunca mezclarlos. Son normas británicas, no colombianas: se reportan como referencia
y se acompañan siempre de los percentiles de nuestra propia muestra.

Fuente: *Scoring the Strengths & Difficulties Questionnaire for age 4-17*, tabla 3, sdqinfo.org.

### 3.2 ARI — Índice de reactividad afectiva

Codificación: **No es cierto = 0, Algo cierto = 1, Muy cierto = 2**. Ventana: últimos 7 días.

- **Puntúan solo los ítems 1 a 6** → total **0-12**. Mayor = más irritabilidad.
- **El ítem 7** ("En general la irritabilidad causa mis problemas") **mide deterioro y NO se suma
  al total**. Se reporta aparte como indicador de interferencia funcional.

**Cortes (autoinforme):**

| Corte | Uso | Rendimiento |
|---|---|---|
| **> 2** | Cribado de irritabilidad severa / TDDEA | Clasifica correctamente 80,3 %; sensibilidad 83,6 %, especificidad 76,6 % |
| **≥ 4** | Indicador de psicopatología general | Sensibilidad y especificidad 77,4 %; AUC 0,86 |

Se reportarán ambos. El de padres es distinto (> 3) y no aplica aquí.
Fuente: Stringaris et al. (2012), *J Child Psychol Psychiatry*; validaciones posteriores.

### 3.3 RCADS-25 — Escala revisada de ansiedad y depresión infantil

Codificación: **Nunca = 0, Algunas veces = 1, Con frecuencia = 2, Siempre = 3**.

| Subescala | Ítems | Rango bruto |
|---|---|---|
| Depresión mayor | 1, 4, 8, 10, 13, 15, 16, 18, 19, 21 | 0-30 |
| Ansiedad total | 2, 3, 5, 6, 7, 9, 11, 12, 14, 17, 20, 22, 23, 24, 25 | 0-45 |
| Total | los 25 | 0-75 |

**Cortes:** se aplican sobre **puntuaciones T**, no sobre brutas. T < 65 severidad baja;
**T 65-69 límite clínico**; **T ≥ 70 clínicamente significativo**.

⚠️ **Decisión pendiente del equipo.** Las tablas T oficiales se derivan de escolares de Hawái
(EE. UU., 1998) y se indexan por **grado escolar y sexo**. Aplicarlas a adolescentes de Chía es
discutible. Tres opciones:

1. **T de EE. UU. con advertencia explícita** — comparable con la literatura internacional, pero
   sesgo cultural desconocido. Requiere conseguir las tablas de conversión por grado y sexo.
2. **Puntuaciones brutas + percentiles de nuestra muestra** — honesto y reproducible, pero no
   permite decir "clínico".
3. **Ambas**: brutas y percentiles como resultado principal, T como anexo comparativo.

Recomendación: opción 3. El ítem 18 ("Pienso acerca de la muerte") se reporta por separado como
señal de alerta, nunca como diagnóstico.
Fuente: Chorpita, Ebesutani & Spence, *RCADS User's Guide*; rcads.ucla.edu.

### 3.4 ERQ-CA — Regulación emocional en niños y adolescentes

Codificación **1-5** (Nada parecido a mí … Exactamente igual a mí). Sin ítems inversos.

| Subescala | Ítems | Interpretación |
|---|---|---|
| Reevaluación cognitiva | 1, 3, 5, 7, 8, 10 (6 ítems) | Estrategia adaptativa: mayor = mejor |
| Supresión expresiva | 2, 4, 6, 9 (4 ítems) | Estrategia menos adaptativa: mayor = más supresión |

Se reporta la **media por ítem** (1-5) para que ambas subescalas sean comparables pese a tener
distinto número de ítems. **No tiene puntos de corte clínicos**: es una medida dimensional. Se
presenta por terciles de la muestra, etiquetados explícitamente como relativos.

### 3.5 MSPSS — Apoyo social percibido

Codificación **1-5** (Nunca … Siempre).

| Subescala | Ítems |
|---|---|
| Otro significativo | 1, 2, 5, 10 |
| Familia | 3, 4, 8, 11 |
| Amigos | 6, 7, 9, 12 |

Se reporta la **media por ítem** (1-5), global y por fuente.

⚠️ **Los cortes clásicos de Zimet (bajo < 3, moderado 3-5, alto > 5) NO aplican**: están definidos
para la versión de **7 puntos** y esta es de **5 puntos**. Usarlos sobreestimaría el apoyo.
Se reportan terciles de la muestra, marcados como relativos.

✅ **Punto fuerte:** el dataset de cuidadores usa **este mismo instrumento con escala de 5 puntos**.
Estudiante y cuidador son directamente comparables. Ver §5.

### 3.6 PSSM — Sentido psicológico de pertenencia a la escuela

Codificación **1-5** (No es cierto … Completamente cierto).

**Ítems inversos (se recodifican 6 − x): 3, 6, 9, 12, 16** — los cinco enunciados negativos
("Es difícil para personas como yo ser aceptadas", "A veces siento como si no perteneciera",
"Los profesores aquí no están interesados en personas como yo", "Me siento diferente de la
mayoría", "Desearía estar en una escuela diferente").

Puntaje total 18-90, o media por ítem 1-5. Unidimensional para uso práctico. **Sin punto de corte
clínico**: se reporta por terciles de la muestra y, sobre todo, **comparado entre colegios y
grados**, que es donde tiene valor accionable.

> Nota psicométrica: varios estudios encuentran que los 5 ítems negativos forman un factor de
> método propio. Al calcular α reportaremos la versión de 18 ítems y la de 13 ítems positivos.

Fuente: Goodenow (1993); validación española en adolescentes chilenos (2016).

## 4. Lo que el equipo pidió y cómo se responde

> *"Descripción de variables y relación entre variables. Ver cómo están los niveles de las
> variables de salud mental de los grupos, con los puntos de corte de cada prueba, y cómo se
> relacionan entre ellas."*

| Petición | Salida concreta |
|---|---|
| Descripción de variables | Tabla 1: N, M, DE, mediana, rango, % de datos faltantes y α de Cronbach por escala y subescala |
| Niveles con puntos de corte | % en cada banda del SDQ; % sobre corte del ARI (> 2 y ≥ 4); % en límite y clínico del RCADS; terciles para ERQ-CA, MSPSS y PSSM, siempre etiquetados como relativos |
| Niveles **de los grupos** | Los mismos indicadores desagregados por sexo, edad o ciclo, grado y colegio, con N mínimo de 10 por grupo |
| Relación entre variables | Matriz de correlaciones (Spearman) con intervalos de confianza y corrección por comparaciones múltiples; mapa de calor; tabla exportable |

## 5. Cómo se conecta con lo que ya tenemos

Tres informantes en los **mismos colegios oficiales de Chía**:

| Fuente | N | Instrumentos compartidos |
|---|---|---|
| Docentes | 189 | PSS-10, MSPSS (parcial), burnout, recursos laborales |
| Cuidadores (reportan sobre el niño) | 172 niños | **SDQ (versión padres)**, **MSPSS (5 puntos)**, EPDS, PSS-10, APQ, PSI-SF, riesgo barrial |
| Estudiantes (autorreporte) | por definir | **SDQ (versión autoinforme)**, **MSPSS (5 puntos)**, ARI, RCADS-25, ERQ-CA, PSSM |

Dos puentes reales:

1. **SDQ en dos informantes.** Mismo constructo, mismas subescalas, distintos cortes. Permite
   estudiar **acuerdo entre informantes**, un tema con literatura propia y resultados robustos
   (los padres suelen reportar menos internalizante que los propios adolescentes). Si hay enlace
   individual, es correlación intraclase; si no, comparación a nivel de colegio.
2. **MSPSS en estudiante y cuidador**, misma escala de 5 puntos: apoyo social percibido
   intergeneracional en la misma familia.

Y el nivel escolar une los tres: bienestar docente, clima familiar y pertenencia del estudiante
en el mismo plantel.

> **Petición clave a quien envíe el dataset:** si existe cualquier forma de enlazar estudiante con
> cuidador (aunque sea un código de familia), inclúyanla. Multiplica lo que se puede publicar.
> Si no es posible, decirlo explícitamente para diseñar el análisis a nivel de colegio.

## 6. Riesgos y salvaguardas

- **Ítem de ideación (RCADS 18) y malestar alto.** El instrumento es un **tamizaje grupal, no un
  diagnóstico**. Ningún resultado individual se muestra en la plataforma. Debe existir una ruta de
  derivación acordada con los colegios *antes* de devolver resultados.
- **Normas extranjeras.** SDQ (Reino Unido), RCADS (EE. UU.), ARI (muestras clínicas). Todos los
  cortes se reportan como referencia externa, acompañados de percentiles propios.
- **Un solo informante por escala.** El autorreporte del estudiante comparte varianza de método;
  las correlaciones entre sus escalas estarán infladas. Se discute en limitaciones.
- **Reidentificación.** Colegios y grados con menos de 10 estudiantes no se desagregan.
- **Rango de edad.** Verificar que los estudiantes con SDQ tengan 11 años o más.

## 7. Estado y siguiente paso

- [x] Instrumento revisado, ítems mapeados, subescalas y cortes verificados en fuente.
- [x] Formato de dataset definido (§2).
- [ ] Recibir el dataset.
- [ ] Confirmar etiquetas del SDQ y orden de ítems con quien aplicó el instrumento.
- [ ] Decidir el tratamiento del RCADS (T de EE. UU. vs brutas y percentiles).
- [ ] Implementar puntuación y las dos vistas. Plan visual en
      `docs/superpowers/specs/2026-09-17-plan-estudiantes.html`.
