# Metodología de puntuación de dimensiones

> **Para revisión del equipo de dominio.** Este documento describe cómo se calculan los
> puntajes de cada dimensión de bienestar. La tabla de valencia por ítem es la fuente
> de verdad y vive en `src/core/config.py` (`ITEM_VALENCE`). Si un ítem está mal
> clasificado, corrígelo allí y los puntajes de toda la app se actualizan.

## Principio

Cada ítem tiene una **valencia** respecto al bienestar:

- **+1 (directo):** una respuesta más alta indica **más** bienestar.
- **−1 (inverso):** una respuesta más alta indica **menos** bienestar; se invierte con
  `x_invertido = (min_escala + max_escala) − x` antes de promediar.

El **puntaje de dimensión** es el promedio de sus ítems ya alineados por valencia. Como
resultado, **en todas las dimensiones "mayor = mejor bienestar"**, lo que permite un
semáforo y comparaciones coherentes. Para las dimensiones de riesgo (burnout, conflicto,
somatización…) también se reporta su lectura directa de "nivel de riesgo".

Por qué importa: promediar ítems crudos de valencia mixta produce números sin
significado. Ejemplo verificado en "Control del Tiempo": ítems de autonomía (positivos)
y de presión de tiempo (negativos) correlacionan ≈ −0.08; sumarlos crudos se cancela.

## Métricas académicas

Por dimensión se reporta además: **N** (respuestas válidas), **desviación estándar**,
**IC 95 %** de la media, **α de Cronbach** (consistencia interna; sobre ítems alineados)
y **nº de ítems**. α < 0.70 se marca como consistencia baja.

## Tabla de valencia por ítem

Notación: número de ítems +1 (directos) / −1 (inversos) por dimensión.

| Dimensión (acrónimo) | Ítems | Directos (+1) | Inversos (−1) |
|---|---|---|---|
| Control del Tiempo (CT) | 7 | 3 (decidir qué hago / voz sobre la forma / voz y voto sobre el ritmo) | 4 (me presionan muchas horas / plazos inalcanzables / presiones poco realistas / descuidar tareas) |
| Compromiso del Líder (CL) | 7 | 7 (todos) | 0 |
| Apoyo del Grupo (AG) | 3 | 3 (todos) | 0 |
| Claridad de Rol (CR) | 7 | 4 (claridad de expectativas, saber hacer, deberes, encaje) | 3 (exigencias difíciles a la vez / cosas contradictorias / solicitudes incompatibles) |
| Cambio Organizacional (CO) | 4 | 4 (todos) | 0 |
| Responsabilidad Organizacional (RO) | 5 | 5 (todos) | 0 |
| Conflicto Familia-Trabajo (FT) | 10 | 0 | 10 (toda interferencia es negativa) |
| Síntomas de Burnout (SB) | 12 | 0 | 12 (todos) |
| Compromiso / engagement (CP) | 3 | 3 (todos) | 0 |
| Defensa de la Organización (DO) | 3 | 3 (todos) | 0 |
| Satisfacción (ST) | 3 | 3 (todos) | 0 |
| Intención de Retiro (IR) | 4 | 1 ("me veo trabajando aquí el próximo año" = permanencia) | 3 (considerar dejarlo / intención de salir 3-6m / buscar otro trabajo) |
| Bienestar Psicosocial — Afectos (PA) | 9 | 9 (asumido; ver nota) | 0 |
| Bienestar Psicosocial — Competencias (PC) | 10 | 10 (asumido; ver nota) | 0 |
| Bienestar Psicosocial — Expectativas (PE) | 22 | 22 ("subiendo" = mejor) | 0 |
| Efectos Colaterales — Somatización (CS) | 5 | 0 | 5 (síntomas físicos) |
| Efectos Colaterales — Desgaste (CD) | 4 | 0 | 4 (todos) |
| Efectos Colaterales — Alienación (CA) | 4 | 0 | 4 (todos) |

### Notas y supuestos a validar
- **Intención de Retiro** se orienta como *permanencia* (mayor = mejor). En reportes se
  aclara la relectura para no confundir con "más intención de irse".
- **Bienestar Psicosocial (PA/PC)** son escalas de diferencial semántico cuyas columnas
  llegan como índices (`(BM),(PA)2` …) sin las etiquetas de los adjetivos. Se asume que
  el polo alto (7) es el positivo y se puntúan con valencia +1. **Requiere verificación**
  contra el instrumento original; si algún par está invertido, ajustar en `ITEM_VALENCE`.
- Los rangos de escala se leen del `DATA_DICTIONARY` (`Escala`); el reverse usa el
  min/max real de la escala de cada dimensión (p. ej. 1–7, 1–6 o 1–5).

## Cómo corregir
Editar `ITEM_VALENCE[<dimensión>]` en `src/core/config.py` (lista de +1/−1 en el mismo
orden que `Preguntas`). Ejecutar `pytest tests/test_scoring.py` para validar.
