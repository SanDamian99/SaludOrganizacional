# Auditoría de relevancia · Observatorio 360 · 10-oct-2026

**Criterio del usuario.** Un elemento se queda si cumple cuatro condiciones: (1) da información relevante a al menos una audiencia, (2) apoya una decisión o una acción, (3) los datos lo sostienen (n y validez) y (4) no duplica otro elemento. Si no da información, no muestra cambio o no sirve, es candidato a salir. **El usuario decide.** Aquí solo se recomienda.

**Cómo se hizo.** Se leyó el código de `main.py`, `navegacion.py`, `src/ui/*` y `src/ui/views/*`, y de los informes `src/reports/*` y `estudiantes_informe`. Se recorrió la app con Playwright en tres modos:
- 8621: completo, con los archivos locales.
- 8622: comunidad, con la corrida 7 publicada (`OBS360_FUENTE=supabase`).
- 8623: investigador con `OBS360_FUENTE=supabase`. En esta máquina la vista previa abrió por defecto la corrida 8, que está en revisión. Al apagarla se ve la 7.

Los conteos de cifras visibles y suprimidas salen de las funciones puras de las vistas, corridas con datos reales. Solo se imprimieron agregados. No existe `estudiantes_avance.py`, así que no hay vista de «avance».

**Leyenda**
- **Audiencias:** R = rector, docente u orientación (rol colegio); M = funcionario del municipio; F = familia; D = módulo Docentes; I = equipo investigador.
- **Veredicto:** MANTENER · MEJORAR · QUITAR · PREGUNTAR.
- **Prioridad:** P1 = antes de abrir al público o de la próxima reunión con colegios; P2 = siguiente iteración; P3 = cuando haya tiempo.

---

## 0. Cinco hallazgos que cambian decisiones

1. **Las comparaciones entre grupos casi nunca muestran diferencias.** Con la corrida 7 hay 18 gráficos posibles en «Comparar entre grupos» de estudiantes (2 niveles × 2 dimensiones × 4–5 indicadores):
   - En 15 de los 18, todos los intervalos se solapan. Ejemplos: SDQ alto por grado en secundaria va de 19 a 22 %; ideación por grado, de 28 a 29 %.
   - 4 de los 18 tienen una sola barra. En primaria, SDQ por colegio da 1 grupo con cifra y 4 sin cifra. Primaria por grado, que es lo que se ve por defecto, también tiene una sola barra.
   - Solo «sin adulto de confianza por grado» en secundaria (29–51 %) y «irritabilidad por colegio» en primaria muestran algún contraste.

   En Cuidadores, «niños con dificultades altas (según el cuidador)» por grado sale con **0 de 7 grados con cifra**.
2. **Muchas cifras por colegio quedan suprimidas.** Sumando todas las selecciones posibles de colegio y de colegio × grado, con el rol colegio y la corrida 7:
   - Secundaria: 18 de 83 tarjetas suprimidas (22 %), y 8 de 19 gráficos de bandas suprimidos.
   - Primaria: 17 de 38 tarjetas (45 %) y 7 de 12 bandas.
   - Cuidadores, en local: 30 de 76 tarjetas (39 %), y 20 selecciones sin bandas del hijo.
   - En el informe imprimible por colegio, aproximadamente 12 de 29 cifras principales salen «—». **El informe de un colegio de primaria (41 estudiantes) no trae ninguna cifra propia: sus 3 tarjetas salen «—»**, aunque conservan textos fijos como «Priorizar los grados donde la cifra es más alta».
3. **El índice principal de Docentes es engañoso.** «Posición relativa 0-100» se calcula como (media − mínimo observado) / (máximo − mínimo observado), y de ahí salen los niveles Favorable, Intermedio y Atención. Eso tiene tres consecuencias:
   - Depende de los valores extremos de la muestra.
   - Cambia de significado con cada filtro: al filtrar por colegio se recalculan el mínimo y el máximo.
   - No es un punto de corte.

   Por eso hoy dice «Salud mental en atención: 0» y marca burnout como «Favorable». Ese mismo índice alimenta el PDF de docentes y las recomendaciones generadas con IA.
4. **El texto libre generado por IA sobre salud mental contradice el principio de texto fijo que rige Estudiantes y Cuidadores.** Aparece en seis lugares: los tres botones «✨ Interpretar … con IA» de Docentes, la sección «Recomendaciones» del PDF docente, «Análisis de tendencias» y el «Chat con IA». El chat se presenta como «Experto en Psicología Organizacional» y sugiere preguntas como «¿Cómo están los niveles de burnout?».
5. **«Análisis de tendencias» no funciona con los datos reales.** Abre con la métrica «Versión del formulario» graficada contra el tiempo, con el eje en 1970. Luego da promedios de «Versión del formulario» por sexo y una caja por grupo. No hay ninguna serie temporal real en ningún módulo.

---

## 1. Inventario por elemento

### 1.1 Navegación y elementos transversales

| Página › sección › elemento | Aud. | Pregunta / acción | Soporte de datos hoy | ¿Duplica? | Veredicto | P |
|---|---|---|---|---|---|---|
| Menú de 8 páginas (modo completo) | I | Navegar | — | — | MEJORAR: agrupar en «Comunidad» (Estudiantes, Cuidadores) · «Equipo» (Docentes, Triangulación) · «Herramientas» (Carga). Sacar Chat, Tendencias y Reportes (ver abajo) | P2 |
| Sidebar «📁 Dataset precargado» (fuera de Docentes) | D | Elegir la versión de docentes | Solo hay una opción; aparece también en Estudiantes y Cuidadores, donde no aplica | — | MEJORAR: mostrarlo solo en Docentes, Reportes y Carga | P3 |
| Aviso «Accede al panel técnico con ?debug=1» | I | Diagnóstico | Útil para el equipo | — | MEJORAR: quitarlo del pie y documentarlo en DESPLIEGUE.md | P3 |
| Panel `?debug=1` (4 pestañas) | I | Estado de ingesta, de la IA, historial | Técnico | — | MANTENER (oculto) | — |
| Aviso de API key ausente | D, I | — | Se ve solo si falta la clave | — | MANTENER | — |
| Info azul «Los resultados vienen de la corrida publicada en la base de datos…» (público) | R, M, F | Ninguna | Jerga técnica en la portada pública, encima del título | — | MEJORAR: bajarlo a una nota al pie («Datos de 2026, actualizados el …») o QUITARLO en modo comunidad | P1 |
| Radio «Estoy viendo esto como» (3 roles) | R, M, F | Adapta textos y desagregación | Funciona; pasa de una página a otra | — | MANTENER | — |

### 1.2 Docentes (`src/ui/dashboard.py`)

Con los datos reales (versión 4, 479 docentes) el dataset **no** es de tipo «bienestar BM». Por eso se ve la vista de **indicadores**, con tres pestañas: «Salud mental e indicadores», «Perfil» y «Correlaciones». Las cuatro pestañas de bienestar (Resumen ejecutivo, Dimensiones, Perfil y Vista académica) solo aparecen con el CSV de demostración.

| Página › sección › elemento | Aud. | Pregunta / acción | Soporte de datos hoy | ¿Duplica? | Veredicto | P |
|---|---|---|---|---|---|---|
| KPIs «Docentes 479 · Indicadores 27 · Salud mental en atención 0» | D, R | Cuántos y cómo están | «En atención» sale del índice relativo (hallazgo 3), así que 0 no informa nada | — | MEJORAR: sustituir por % sobre puntos de corte publicados (PSS, burnout) o por la media con referencia | P1 |
| Info «posición relativa… Ajusta etiquetas en `docs/GUIA_DATASETS.md`» | D | — | Remite a un archivo del repositorio: jerga de desarrollador | — | QUITAR la referencia al .md | P2 |
| Barras por tema (5 temas, 27 barras de «posición 0-100») | D, R | ¿Qué aspecto está peor? | La métrica no es comparable entre indicadores ni entre filtros. Hay 10 indicadores sin dirección definida (ERS, PRPS, «Conf FaTr», «Conf TrFa», Desconexión). «Bienestar psicosocial» (BLG_Psicoso) solo existe en las 189 filas de 2025 | — | MEJORAR (rehacer): media en su escala, con su rango teórico y su corte cuando exista, y con IC. Dejar solo los indicadores con dirección y codebook | P1 |
| Tema «📊 Otros indicadores» (PRPS, Conf FaTr/TrFa, Desconexión) | D, I | — | Sin dirección, etiquetas crípticas y sin codebook | — | QUITAR de la vista de colegio y dejarlos en la vista investigador | P1 |
| Mensajes «Requieren atención / Favorables» | D, R | Priorizar | Clasificación relativa: hoy dice que burnout es «Favorable» | Duplica las barras | QUITAR mientras se use el índice relativo | P1 |
| Botón «✨ Interpretar salud mental con IA» | D | Interpretación | Texto libre de Gemini sobre salud mental, construido con el índice relativo y con citas a «autores clásicos» | — | QUITAR (o PREGUNTAR si el equipo lo quiere solo para investigadores) | P1 |
| Expander «📋 Tabla completa de indicadores» | I, D | Media, DE, rango, N | Correcta. «Nivel (muestra)» es relativo | — | MEJORAR: quitar la columna «Nivel (muestra)» | P3 |
| «Explorar un indicador»: métricas e histograma | D, I | Distribución de un indicador | Útil para el equipo | — | MANTENER (equipo) | — |
| «Comparar por grupo» (barras por grupo) | D, R | ¿Hay diferencias por sexo, contrato…? | Abre por defecto con **«Fecha de respuesta»**, con eje 2 024,5–2 026,5. **No incluye Colegio** (16 categorías y el tope es 12). No aplica n mínimo: hay categorías con menos de 10 en sexo, hijos, estrato, contrato e ingreso. No da IC | — | MEJORAR: excluir fecha y versión, aplicar n ≥ 10, añadir IC y Colegio (agrupando los colegios pequeños) | P1 |
| Botón «✨ Interpretar «X» con IA» | D | — | Texto libre de IA | Duplica el anterior | QUITAR | P1 |
| Pestaña «👥 Perfil» → Sociodemográficas y Laborales (≈12 histogramas o barras) | I, D | Composición de la muestra | No aplica n mínimo («No binario», «Viudo», «Más de 10 SMLV»). Ejes con «(SD)Edad». Con filtros puede delatar a alguien | La Tabla 1 de la vista investigador sería el lugar natural | MEJORAR: una sola tabla con n y %, «<10» enmascarado | P2 |
| Pestaña «🎓 Correlaciones» (heatmap 27×27 sin cifras) | I | Relación entre indicadores | Puntajes crudos sin orientar, sin IC y sin corrección por comparaciones múltiples. Etiquetas crípticas | — | QUITAR del dashboard (o moverlo a un futuro «Docentes · investigador» con Spearman, BH e IC como en Estudiantes) | P2 |
| Sidebar «📄 Informe → Generar Informe PDF» | D, R | Informe imprimible | El PDF usa el índice relativo, incluye «Recomendaciones» generadas con IA y lista los conteos por sexo con categorías menores de 10 | **Duplica la página «Reportes»** | MEJORAR: un solo botón, con el PDF sin IA y sin conteos pequeños. Esperar la decisión A/B tras la reunión del 1-oct (no tocar sin aprobación) | P1 |
| Sidebar «🔍 Filtros» (9 filtros) | D, R | Ver su colegio o su subgrupo | Sin n mínimo: se puede bajar a grupos de 1 a 9 docentes y ver todos los gráficos y el PDF | — | MEJORAR: bloquear resultados cuando n < 10 | P1 |
| Sidebar «📥 Descargar datos filtrados (CSV)» | I | Exportar | **Descarga filas individuales de docentes** (sin nombre, pero con colegio, edad, sexo y estado civil): permite reidentificar | — | PREGUNTAR: ¿hace falta? Si no, QUITAR. Si sí, solo en modo investigador y sin cuasi-identificadores | P1 |
| Vistas de bienestar BM (Resumen ejecutivo, semáforo, gauge, Dimensiones, Vista académica, `render_tank`) | — | — | **No se muestran con los datos reales**: solo con el CSV demo | Paralelas a la vista de indicadores | PREGUNTAR: ¿se mantiene el esquema BM para futuros clientes? Si no, QUITAR el código y el `ReportBuilder` | P3 |

### 1.3 Estudiantes 360 · vista comunidad (`estudiantes_comunidad.py`)

Cifras de la corrida 7 publicada, salvo que se indique otra cosa.

| Página › sección › elemento | Aud. | Pregunta / acción | Soporte de datos hoy | ¿Duplica? | Veredicto | P |
|---|---|---|---|---|---|---|
| Sidebar: Nivel, Colegio y Grado | R, M, F | Elegir su grupo | 4 de 6 colegios visibles en secundaria y 5 de 6 en primaria. 5 grados en secundaria y 2 en primaria | — | MANTENER | — |
| 1 · «Cómo está el grupo»: bandas del SDQ total (4 bandas) | R, M, F | ¿Cuántos tienen dificultades? | Total: secundaria 64/17/9/11 %, primaria 63/15/7/14 %. Por colegio y grado: 8 de 19 suprimidas en secundaria y 7 de 12 en primaria | La tarjeta «1 de cada 5» es la suma Alto + Muy alto | MEJORAR: dejar las bandas solo en el total o fundirlas con la tarjeta (una barra apilada con la cifra «1 de cada 5» encima). Corregir la leyenda, cuyo orden es el inverso de las barras | P2 |
| 1b · Panel «Señales para actuar a tiempo» | R, M, F | ¿Dónde mirar primero? | **No aparece en público**: la corrida 7 no trae alertas porque los textos no están aprobados. En local muestra el estado «Para tener presente»: malestar 1 de cada 11 y desesperanza 1 de cada 6 | Sustituye la tarjeta de muerte | PREGUNTAR: aprobar los textos (`alertas_catalogo.TEXTOS_APROBADOS`) y publicarlo, o quitarlo. Ver la inconsistencia de la fila siguiente | P1 |
| Tarjeta «Pensamientos sobre la muerte» (R y M, en público) | R, M | Activar la ruta | 25 % (22–28) con un solo ítem (RCADS18 ≥ «Con frecuencia»). En local la reemplaza el panel, que muestra «1 de cada 6» con otra definición. **Público y local muestran dos cifras distintas sobre el mismo tema** | Panel de desesperanza | PREGUNTAR: ¿qué cifra es la oficial? Hay que publicar una sola | P1 |
| 1c · «Mapa de Chía» (3 capas) | M, R | ¿Dónde hay respuestas? ¿Dónde protege más el colegio? | Capa «respuestas»: 4–5 círculos y el resto en gris. Las capas «Sentirse parte» y «Apoyo social» muestran medias con diferencias pequeñas y sin IC (según la spec, ICC ≈ 0) | Duplica «Comparar por colegio». La capa de respuestas solo da cobertura | MEJORAR: mostrarlo solo al rol municipio, con la capa «Respuestas» (cobertura y colegios sin datos) como plan de expansión. QUITAR las capas de medias mientras haya menos de 6 colegios con cifra | P2 |
| 2 · Tarjeta «Dificultades emocionales y de comportamiento» | R, M, F | Magnitud | 20 % (17–22), n = 943. Primaria 21 % | Bandas | MANTENER | — |
| 2 · Tarjeta «Tener un adulto de confianza» | R, M, F | Acción concreta (docente de referencia) | 42 % (39–46). Es el único indicador con gradiente real por grado (29–51 %) | El enunciado PSSM7 aparece otra vez entre los «4 enunciados más bajos» | MANTENER (es la más accionable) | — |
| 2 · Tarjeta «Síntomas emocionales por sexo» | R, M, F | Brecha por sexo | Solo local (31 % vs 13 %). **No se publica**: la corrida no trae el sexo | — | PREGUNTAR: ¿publicar el contraste por sexo en el total del nivel (n de 465 y 478)? Es de los hallazgos más claros | P2 |
| 2 · Tarjetas de contraste «Apoyo en casa» y «Sentirse parte» («4 % · 21 %») | R, M, F | ¿Qué protege? | Correctas y robustas (n ≈ 330–340 por tercil). Formato difícil: dos porcentajes con un punto medio | — | MEJORAR: «5 veces menos malestar con mucho apoyo en casa» o dos barras pequeñas | P2 |
| 2 · Tarjeta «Irritabilidad» (primaria en público y en el selector) | R, M, F | — | **61 % (56–66) por encima del corte** en primaria y 52–57 % en secundaria. Un corte que marca a más de la mitad no discrimina. Corte clínico de ARI en población escolar | — | QUITAR la tarjeta y el indicador del selector hasta validar el corte (o PREGUNTAR al equipo) | P1 |
| 2 · Expander «Qué significa y qué hacer» | R, M, F | Acción | Textos fijos del catálogo | — | MANTENER | — |
| 3 · «Comparar entre grupos» (radio Grado/Colegio + selector de indicador + barras con IC) | R, M | ¿Hay un grado o colegio que concentre el problema? | Ver hallazgo 1: 15 de 18 combinaciones sin diferencias, 4 con una sola barra; en primaria por grado, que es lo que abre por defecto, 1 barra | — | MEJORAR (reducir): dejar un gráfico fijo, «sin adulto de confianza por grado». Ocultar las combinaciones con menos de 3 grupos con cifra. Si todos los IC se solapan, decir «No hay diferencias claras entre grados» en vez de graficar | P1 |
| 3 · Captions «Sin cifra: Noveno, Décimo…» y «2 colegios no se muestran…» | R, M | Transparencia | Correctos. En primaria: «Menos de 10 respuestas de grupos muy pequeños no entran…», redacción confusa | — | MEJORAR la redacción | P3 |
| 4 · «Los cuatro enunciados de pertenencia con la media más baja» | R | ¿Qué trabajar en convivencia? | Medias entre 2,73 y 2,96 de 5 (secundaria) y entre 2,97 y 3,20 (primaria): diferencias mínimas, sin IC, con 2 decimales y punto decimal (la app usa coma) | Repite PSSM7 = tarjeta «adulto de confianza» | MEJORAR: % de acuerdo («solo 4 de cada 10 sienten que se toman sus opiniones en serio»), sin repetir PSSM7. O QUITAR | P2 |
| 5 · Recuadro «🆘 Si un estudiante necesita ayuda» | R, M, F | Ruta | Contactos sin validar (aviso interno) | — | MANTENER. Validar las líneas de Chía antes de abrir (P1) | P1 |
| 6 · Avisos «tamizaje», primaria y expander «De dónde vienen los puntos de corte» | R, M, F | Cautela | Necesarios | — | MANTENER | — |
| 7 · «⬇️ Descargar resumen de una página» | R, M, F | Llevar a reunión | Sin WeasyPrint se descarga como HTML. Contenido bien enfocado (bandas + 4–5 tarjetas + ruta) | Resume la pantalla | MANTENER. Para familia, poner «qué hacer» primero | — |
| 7 · «🖨️ Informes para imprimir»: informe del colegio | R | Informe por colegio | 5 colegios. Unas 12 de 29 cifras principales suprimidas; **un informe no tiene ninguna cifra propia**. Los textos fijos («No hay un grado que concentre el problema», «Es el indicador más bajo de toda la encuesta», «Priorizar los grados…») se imprimen aunque la cifra salga «—» | Una página | MEJORAR: si más de la mitad de las cifras están suprimidas, generar un informe «del municipio con la participación del colegio». Quitar los textos condicionales cuando falta la cifra. En público, el rol colegio puede descargar el informe de **cualquier** colegio: PREGUNTAR si eso es aceptable | P1 |
| 7 · Informe para la Secretaría (solo rol municipio) | M | Política pública | El más completo. Incluye «Garantizar capacidad de respuesta… para el volumen que implica esta cifra», sobre el ítem de muerte | — | MANTENER. Revisar la cifra de muerte (ver arriba) | P1 |
| 7 · Expander «Vista previa del informe» (iframe de 900 px) | R, M | — | Pesado, duplica la descarga | Descarga | MEJORAR: abrirlo solo a demanda (ya es un expander) o QUITARLO | P3 |

### 1.4 Estudiantes 360 · vista investigador (`estudiantes_investigador.py`)

| Pestaña › elemento | Aud. | Soporte hoy (archivos locales / corrida 7) | Veredicto | P |
|---|---|---|---|---|
| Muestra y exclusiones (tablas de sexo, edad, grado, colegio, colegio × grado; flujo) | I | Completa en las dos fuentes. El aviso de 164 bloques ERQ inválidos es útil | MANTENER | — |
| Tabla 1 (N, M, DE, α con IC) | I | Buena. α < 0,70 en 5 subescalas SDQ (pares 0,45; conducta 0,51) | MANTENER | — |
| Cortes y bandas (bandas de las 6 escalas SDQ, prevalencias, terciles, percentiles por sexo) | I | Buena | MANTENER | — |
| Correlaciones (heatmap de Spearman + tabla con BH y filtros) | I | Buena | MANTENER | — |
| Por grupo (sexo con Mann-Whitney, grado y colegio con Kruskal-Wallis, edad) | I | Buena; el colegio entra con 4 grupos | MANTENER | — |
| Alertas → definiciones | I | Útiles | MANTENER | — |
| Alertas → «Prevalencia por grupo» | I | **Con la corrida 7: «Esta corrida no trae alertas (es anterior a la fase 3)»**. El texto es falso: la corrida 7 omitió las alertas a propósito, en espera de aprobación | MEJORAR el texto: «omitidas hasta que el equipo apruebe los textos» | P2 |
| Alertas → «Distribución de cada ítem» y «Sensibilidad» | I | Con la corrida publicada: «Solo con los datos locales». Vacías en el despliegue del equipo | MEJORAR: ocultarlas cuando la fuente es Supabase (hoy son dos cabeceras vacías) | P3 |
| Modelos (β estandarizados, EE robustos por colegio) + ICC | I | **3 conglomerados**: los EE robustos no son fiables (la app misma lo advierte en cada modelo) | MEJORAR: pasar a EE HC3 o efecto fijo de colegio, y dejar el cluster como sensibilidad. Una advertencia repetida 5 veces es ruido | P2 |
| Calidad de datos | I | Útil | MANTENER | — |
| Exportar (CSV sueltos + ZIP) | I | Útil para el artículo | MANTENER | — |
| Info «Los resultados vienen de la corrida publicada… se puede filtrar…» (vista investigador) | I | Habla de filtros que esta vista no tiene | MEJORAR (texto) | P3 |

### 1.5 Cuidadores 360 · vista comunidad (`cuidadores_comunidad.py`)

Solo en local: no está publicada (`CUIDADORES_PUBLICO=False`), 734 cuidadores y 862–886 niños.

| Página › sección › elemento | Aud. | Pregunta / acción | Soporte hoy | ¿Duplica? | Veredicto | P |
|---|---|---|---|---|---|---|
| Caption «734 cuidadores… todas las olas (2025 y 2026)» | todas | Base | Correcto | — | MANTENER | — |
| Panel «Señales para cuidar a quienes cuidan» (ánimo EPDS ≥ 13; autolesión solo para M) | R, M | Ruta para adultos | 1 de cada 4 con ánimo bajo, estado «Para tener presente». La EPDS es perinatal: el aviso ya lo dice | Sustituye la tarjeta de ánimo | MANTENER. PREGUNTAR la aprobación de los textos | P1 |
| Tarjeta «Estrés de crianza: 14,4 de 40» | R, M, F | — | **El título contradice la medida**: es PSS-10 (estrés percibido general), no estrés de crianza, como dice el propio «significa». Una media sin corte ni referencia no se entiende (para familias, menos) | — | MEJORAR: renombrarla «Estrés en la vida diaria» y mostrarla en terciles o frente al municipio. O QUITARLA | P1 |
| Tarjeta «Apoyo que tiene: 1 de cada 5 sin apoyo de la familia (+ amigos 29 %, persona especial 15 %)» | R, M, F | Redes de apoyo | Bien | — | MANTENER | — |
| Tarjeta «Crianza positiva y castigo físico: 3 de cada 10 (+ grito 50 %)» | R, M, F | Escuela de padres; Ley 2089 | 30 % (27–34). **El indicador más accionable de cuidadores** y el único con gradiente real por grado (17–41 %) | — | MANTENER. El título dice «crianza positiva» pero solo mide castigo: ajustarlo | P2 |
| Tarjeta «Seguridad del barrio: 2,0 de 10 en el índice de riesgo» | M | ¿Hay entornos inseguros? | Una media sin referencia. El título («seguridad») va en sentido contrario a la medida («riesgo») | — | MEJORAR: % que reporta al menos un riesgo (violencia, consumo), y solo para el rol municipio. O QUITAR | P2 |
| Tarjeta «Cómo ve el cuidador al hijo: 1 de cada 6» | R, M, F | Dificultades según los padres | 16 % (13–18), n = 862 niños | **Duplica el gráfico de bandas del hijo de más abajo** | MEJORAR: dejar la tarjeta o las bandas, no las dos | P2 |
| «Comparar entre grupos» (castigo, apoyo de la familia, hijo alto, ánimo) | R, M | ¿Qué grado o colegio priorizar? | Castigo por grado y colegio: útil (7 de 7 colegios con cifra). **«Hijo alto» por grado: 0 de 7 con cifra; por colegio: 2 de 7.** Apoyo y ánimo: 5 de 7 | — | QUITAR «hijo alto» del selector. MANTENER castigo | P1 |
| Bandas «Cómo ve el cuidador al hijo · 862 niños» | R, M, F | — | 74/10/7/9 %. Suprimidas en 20 de las selecciones por colegio | Tarjeta «hijo» | QUITAR o fundir con la tarjeta | P2 |
| Ruta «🆘 Si un cuidador necesita ayuda» + 2 avisos internos | todas | — | Dos avisos internos casi iguales seguidos | — | MEJORAR: un solo aviso | P3 |
| Expander «Sobre estas cifras», una página, informes de colegio y Secretaría | R, M, F | — | Las mismas pautas que en Estudiantes. 39 % de tarjetas suprimidas por colegio | — | MANTENER, con las mismas mejoras que en Estudiantes | P2 |

### 1.6 Cuidadores 360 · vista investigador

| Pestaña | Soporte hoy | Veredicto | P |
|---|---|---|---|
| Radio «Marco» (cuidador o niño) | Necesario | MANTENER | — |
| Muestra y exclusiones | Completa (779 → 756 → 734) | MANTENER | — |
| Tabla 1 | 16 filas | MANTENER | — |
| Cortes y bandas | Tabla de 27 × 18 con **50 % de celdas vacías** (columnas que solo aplican a un tipo de fila) | MEJORAR: dos tablas, cortes y terciles | P3 |
| Correlaciones | 36 pares | MANTENER | — |
| Por grupo | `comparaciones_grupo`: 41 × 44 con **55 % de celdas vacías** (formato ancho M·colegio). El caption «No se desagregan: 7 colegios», junto a «Colegios con 10 o más: 7», se lee como contradicción | MEJORAR: formato largo y aclarar «7 colegios pequeños más» | P2 |
| Señales del adulto | Útil | MANTENER | — |
| Ítems sin puntaje (APQ, estrés parental) | Útil hasta que llegue el libro de códigos | MANTENER | — |
| Calidad de datos | Útil (31 filas con colegio no reconocido, 19 cursos sin resolver) | MANTENER | — |
| Exportar | Útil | MANTENER | — |
| Selector «Ola (solo local)» | Muestra solo el total por ola | MANTENER | — |

### 1.7 Triangulación 360 (solo investigadores)

Datos locales: 4 colegios en la capa 1, 208 díadas y 194 familias.

| Pestaña › elemento | Contenido real hoy | Veredicto | P |
|---|---|---|---|
| Resumen → 3 métricas | Correctas | MANTENER | — |
| Resumen → «Dónde coinciden» | **Vacía** («Sin datos para mostrar»): 0 coincidencias de 68 pares (34 sin diferencia clara, 30 co-ocurrencias, 4 tensiones) | MEJORAR: una frase («Ningún par coincide en dirección») en vez de una tabla vacía. Añadir el conteo por clasificación | P2 |
| Resumen → «Dónde hay tensión» | 4 filas, legibles con `d_a`, `ic_a`, `d_b`, `ic_b` | MEJORAR: nombres en castellano y frase por fila | P2 |
| Por colegio → personas por actor | 13 filas: útil | MANTENER | — |
| Por colegio → clasificación (40 × 11), diferencias (68 × 17) y 4 figuras | Tablas anchas con jerga; las figuras sí se leen | MEJORAR: mostrar las figuras primero y dejar las tablas en el expander o el ZIP | P3 |
| Por grado (28 × 11 y 91 × 17) | Ilegible en pantalla | MEJORAR: igual que por colegio | P3 |
| Enlace de díadas (15 × 2) | Clara | MANTENER | — |
| Acuerdo SDQ (6 × 24) + Bland-Altman + concordantes (6 × 24) | Valiosa para el artículo; tablas de 24 columnas | MEJORAR: reducir a rho, IC y dif. de medias | P3 |
| Malestar no visto (2 × 13) | **El hallazgo más útil para familias y colegios** (dónde conversar primero) | MANTENER y llevar al artículo | — |
| Apoyo familiar (3 × 12) | Útil, con aviso | MANTENER | — |
| Asociaciones (36 × 13) | Útil para el artículo | MANTENER | — |
| Metodología, Exportar | Necesarias | MANTENER | — |

### 1.8 Chat, Carga, Tendencias y Reportes

| Página › elemento | Aud. | Soporte hoy | ¿Duplica? | Veredicto | P |
|---|---|---|---|---|---|
| **Chat con IA** (asistente «Experto en Psicología Organizacional», 4 preguntas sugeridas, RAG de 7 referencias) | D, I | Solo ve los datos de docentes, no los de Estudiantes, Cuidadores ni Triangulación. Genera texto libre sobre salud mental. Las preguntas sugeridas hablan de «la organización» y «el equipo» (plantilla de empresa). Tiene un enrutador de temas sensibles, pero no aplica n mínimo a «diferencias entre grupos» | — | QUITAR (o PREGUNTAR: ¿se mantiene como herramienta interna del equipo, fuera del menú y solo en modo investigador?) | P1 |
| **Cargar Datos** (subida, vista previa de 5 filas, procesar, versiones en Supabase con «Activar») | I | Útil para gestionar versiones de docentes. La vista previa muestra 5 filas crudas (si alguien sube un formulario con nombres, se ven) | — | MANTENER en modo investigador. MEJORAR: vista previa sin filas (solo columnas y conteos) | P2 |
| **Análisis de tendencias** (línea temporal, barras por grupo, boxplot, «Generar análisis prospectivo» con IA) | — | Basura con los datos reales (hallazgo 5). Sin n mínimo. IA de texto libre | Duplica «Comparar por grupo» de Docentes | **QUITAR** | P1 |
| **Reportes** (fuente: datos cargados o archivo nuevo; filtros; fechas; título; anexo; generar PDF) | D | El mismo PDF que el botón del sidebar de Docentes. «Archivo nuevo» acepta cualquier Excel sin el pipeline (sin desidentificar) | Duplica el botón de Docentes | QUITAR la página y dejar solo el botón de Docentes (después de la decisión A/B) | P1 |

---

## 2. Recuento de lo visible y lo suprimido (datos reales)

| Vista | Elemento | Con cifra | Suprimido o vacío |
|---|---|---|---|
| Estudiantes · secundaria (corrida 7) | Tarjetas en el total, por rol | 5 | 0 |
| | Tarjetas en todas las selecciones colegio[×grado] (rol colegio) | 65 | 18 (22 %) |
| | Bandas SDQ en las selecciones colegio[×grado] | 11 | 8 |
| | Comparativas por grado (5 indicadores) | 18 barras | 7 grupos «sin cifra» |
| | Comparativas por colegio | 15 barras | 5 |
| Estudiantes · primaria (corrida 7) | Tarjetas en el total | 4 (sin el contraste por sexo) | 0 |
| | Tarjetas en las selecciones colegio[×grado] | 21 | 17 (45 %) |
| | Bandas SDQ por selección | 5 | 7 |
| | Comparativas por grado / colegio | 6 / 9 barras | 2 / 11 |
| Estudiantes · familia por grado | Tarjetas | 28 (secundaria + primaria) | 4 |
| Informe imprimible por colegio (5) | Cifras principales | ≈ 17 | ≈ 12; un informe con 0 cifras propias |
| Cuidadores (local) | Tarjetas por selección colegio[×grado] | 46 | 30 (39 %) |
| | «Hijo alto» por grado / por colegio | 0 / 2 | 7 / 5 |
| | Castigo por grado / por colegio | 5 / 7 | 2 / 0 |
| Panel de alertas de estudiantes | Público (corrida 7) | — | ausente (0 alertas publicadas) |

---

## 3. Lo que recibe hoy cada audiencia

### Rector, docente u orientación (rol colegio)
- Bandas SDQ y 5 tarjetas del total. Para **su** colegio, entre un 22 % (secundaria) y un 45 % (primaria) de las cifras salen «—». En un colegio de primaria, todas.
- Una cifra clara y accionable: 4 de cada 10 no tienen un adulto de confianza, con un gradiente por grado (29–51 %).
- Los contrastes protectores (apoyo en casa y pertenencia) con su acción.
- Un informe imprimible por colegio que imprime textos condicionales aunque la cifra no exista.
- La ruta de atención, todavía sin validar.

**Huecos.** (a) No sabe qué hacer cuando su cifra está suprimida, y no hay un «informe de participación» alternativo. (b) Ningún dato de sus **docentes** junto al de sus estudiantes en la vista de comunidad: los docentes solo están en un dashboard aparte con el índice relativo. (c) Nada sobre convivencia o acoso (SDQ19, «se burlan de mí»), que el propio panel de malestar cita. (d) No tiene una lista corta de 3 prioridades para su colegio.

### Funcionario del municipio
- Total municipal por nivel, comparación por colegio (sin diferencias claras) y mapa de cobertura.
- El informe para la Secretaría, el elemento más completo para esta audiencia.
- En público, «Pensamientos sobre la muerte: 1 de cada 4», sin el panel de alertas.
- En Cuidadores (aún no publicado): castigo físico al 30 %, ánimo bajo en 1 de cada 4 cuidadores y autolesión solo en el total.
- Nada de docentes.

**Huecos.** (a) Una cifra de **demanda** para dimensionar la red: casos esperados por cada 1 000 estudiantes, con IC. (b) La cobertura (cuántos colegios y estudiantes de Chía faltan), que el mapa sugiere pero no cuantifica. (c) Una vista 360 de una página que junte estudiantes, cuidadores y docentes por colegio sin díadas. (d) Una línea base para una segunda medición: no hay ningún diseño de seguimiento.

### Familia
- Las mismas tarjetas sin desagregar por colegio, con las acciones para la familia («preguntar por los compañeros», «10 minutos sin pantallas»): bien enfocadas.
- Una comparación por grado casi plana.
- «Irritabilidad 6 de cada 10» en primaria, que alarma sin fundamento.
- Jerga técnica: «IC 95 %», «base de 943», «intervalo de Wilson» y el aviso de «corrida publicada en la base de datos».
- La ruta de atención.

**Huecos.** (a) Una versión «para familias» de una pantalla, sin IC ni gráficos comparativos. (b) Lo que aportarían los cuidadores (castigo físico y apoyo), que es directamente sobre ellas y no está publicado. (c) Recursos concretos de crianza en Chía.

### Docentes (módulo propio)
- 27 barras de un índice relativo que no significa nada clínico. Sale «0 en atención».
- Perfiles sociodemográficos sin n mínimo.
- Botones de IA que redactan recomendaciones sobre salud mental.
- Un PDF con las mismas debilidades y recomendaciones generadas con IA.
- Ninguna comparación por colegio (Colegio queda fuera por cardinalidad).

**Huecos.** (a) Prevalencias con cortes publicados: PSS alto, burnout MBI/CBI, intención de retiro. (b) Una vista de comunidad de docentes con las mismas reglas que Estudiantes (n ≥ 10, textos fijos, ruta para adultos). (c) La relación docente ↔ estudiante por colegio, que hoy solo está en Triangulación.

### Equipo investigador
- Estudiantes y Cuidadores en modo investigador: completos, trazables y exportables. Es lo mejor de la plataforma.
- Triangulación: los datos están, pero en tablas de 11 a 24 columnas con jerga. «Dónde coinciden» está vacío y «Malestar no visto» es oro.
- Modelos con 3 conglomerados: EE poco fiables.
- Docentes sin vista investigador equivalente (sin α, sin IC, correlaciones crudas).
- Con la corrida 7, la pestaña Alertas tiene 3 secciones vacías o con un texto incorrecto.

**Huecos.** (a) «Docentes · investigador» con Tabla 1, α y cortes. (b) Un registro de decisiones de análisis que enlace con el ángulo del artículo. (c) Tablas listas para el artículo en la triangulación, en formato largo.

---

## 4. Comprobaciones específicas pedidas

- **Pestañas de Docentes.** Aportan valor la tabla completa, «Explorar un indicador» y el perfil (si se le aplica n mínimo). Es ruido el índice relativo con sus niveles, el tema «Otros», el heatmap 27×27 y la comparación por fecha. Las 4 pestañas BM no se ven con los datos reales.
- **Botones de IA, Chat y Reportes.** No se alinean con el principio de texto fijo: hay seis puntos de texto libre sobre salud mental, uno de ellos dentro de un PDF que se entrega a colegios.
- **Análisis de tendencias.** Confirmado: no sirve con los datos reales. QUITAR.
- **Pestañas investigador vacías con la corrida publicada.** Estudiantes → Alertas: «Prevalencia por grupo» (con un texto incorrecto), «Distribución de cada ítem» y «Sensibilidad». El resto se llena con la corrida 7. Cuidadores y Triangulación no tienen corrida publicada para el equipo en esta máquina: la vista previa usa la corrida en revisión.
- **Comparaciones con muchos «—».** Ver la sección 2. Las comparaciones de estudiantes muestran entre 1 y 5 barras por gráfico. Primaria por colegio, con SDQ, tiene 1 de 5.
- **PDF o HTML de una página.** Su contenido es correcto y enfocado. En local se descarga como HTML porque falta WeasyPrint. En público, la versión colegio y municipio incluye la tarjeta de muerte (25 %).
- **Mapa.** Valor modesto: cobertura. Las capas de medias no muestran contraste y duplican la comparación por colegio.
- **Pestañas de Triangulación.** Se leen Resumen (métricas), Enlace, Malestar no visto, Apoyo y Metodología. «Dónde coinciden» está vacía. Por colegio, Por grado y Acuerdo son tablas anchas e ilegibles en pantalla.
- **Tarjetas de cuidadores.** Hay 2 de 5 que son medias sin referencia (estrés y barrio), con títulos que no coinciden con la medida. «Hijo» está duplicada con las bandas.
- **Textos de estado de las alertas.** «Para tener presente», «Qué quiere decir cada estado» y el «estado = referencia» son claros. El de investigador, «es anterior a la fase 3», es falso para la corrida 7.

---

Archivos de trabajo (fuera del repo): las capturas, los HTML de los informes y los scripts de conteo están en el scratchpad de la sesión, `…/scratchpad/auditoria/`.
