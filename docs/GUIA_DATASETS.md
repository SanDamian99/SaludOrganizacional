# Guía de datos — ¿Qué puedo cargar en el Observatorio?

Esta guía es para quien recibe la aplicación y quiere alimentarla con sus propios datos.
La app acepta **encuestas en formato tabla** (una fila por participante) y se adapta
automáticamente a dos tipos de dataset.

## Formatos aceptados

- **Excel** (`.xlsx`, `.xls`) o **CSV** (UTF-8 recomendado; detecta encoding).
- Hasta ~200 MB por archivo. Una fila = un participante; una columna = una variable.
- Cárgalos desde la pestaña **“Cargar Datos”**, o déjalos como **datasets precargados**
  (ver más abajo) para que aparezcan en el selector de la barra lateral.

La app **nunca descarta columnas**: las que no reconoce se conservan. Los identificadores
(**ID, Nombre, Correo electrónico, Hora de inicio/finalización, marca temporal**) se
detectan y **no se transforman ni se imputan**.

## Los dos tipos de dataset

### 1) Dataset de Bienestar Laboral (esquema del Observatorio)

Úsalo para obtener el **diagnóstico completo**: semáforo, dimensiones, α de Cronbach,
comparativas e **informe PDF**. Requiere columnas con estos prefijos:

| Prefijo | Significado | Ejemplo de columna |
|---|---|---|
| `(SD)` | Variable sociodemográfica | `(SD)Edad`, `(SD)Sexo` |
| `(LB)` | Variable laboral | `(LB)Tipo de Contrato` |
| `(BM),(XX)` | Ítem de una dimensión de bienestar (XX = acrónimo) | `(BM),(CT)Tengo la opción de decidir…` |

- Las respuestas pueden venir como **texto** (“Nunca”, “Siempre”…) o **números**: la app
  convierte el texto a escala automáticamente.
- Los ítems inversos se recodifican y cada dimensión se orienta a **“mayor = mejor”**.
  Ver [METODOLOGIA_PUNTAJES.md](METODOLOGIA_PUNTAJES.md) para la tabla de valencia.
- Acrónimos de dimensión (`XX`): CT, CL, AG, CR, CO, RO, FT, SB, CP, DO, ST, IR, PA, PC,
  PE, CS, CD, CA (ver `src/core/config.py → DATA_DICTIONARY`).

### 2) Dataset genérico / batería psicométrica (p. ej. Docentes)

Para estudios con **otros instrumentos** (PSS, IRI, ERS, AUDIT…) o con **totales de
subescala ya calculados**. La app entra en **modo Indicadores**:

- Detecta automáticamente las columnas de total (terminadas en **`_T`** o **`_Total`**),
  o, si no hay, las columnas numéricas de tipo escala.
- Las agrupa por tema (**🧠 Salud mental, 😊 Bienestar laboral, 🛠️ Recursos del trabajo,
  💗 Empatía y regulación emocional, 📊 Otros**) y muestra su posición relativa, tablas,
  distribuciones, comparativas por grupo, correlaciones e interpretación con IA.
- Las variables sociodemográficas comunes (Edad, Sexo, Estado Civil, Nivel educativo,
  Tipo de Contrato, Zona de vivienda…) se reconocen y alimentan la pestaña **Perfil**.

> **Importante sobre la interpretación:** en modo Indicadores, el “nivel”
> (Favorable / Intermedio / Atención) es **relativo a la muestra cargada**, no un punto
> de corte clínico. La dirección (mayor = mejor o mayor = riesgo) se toma del catálogo de
> instrumentos conocidos; los no catalogados se muestran de forma **neutral**.

## Personalizar el catálogo de indicadores

Las etiquetas legibles, el tema y la dirección de cada indicador viven en
`src/analysis/indicators.py → INDICATOR_CATALOG`. Formato:

```python
"PSS":     ("Estrés percibido (PSS)", "🧠 Salud mental y estrés", False),  # mayor = peor
"IRI_PT":  ("Empatía: toma de perspectiva", "💗 Empatía y regulación emocional", True),
"ERS_CLA": ("Regulación emocional: claridad", "💗 Empatía y regulación emocional", None),  # sin definir
```

- El tercer valor es `higher_is_better`: `True` (mayor = mejor), `False` (mayor = riesgo),
  `None` (sin definir → se muestra neutral).
- La clave se compara con el nombre del indicador sin el sufijo `_T`/`_Total`
  (p. ej. `PSS_T` → `PSS`).
- **Si conoces el codebook de tu instrumento, edítalo aquí** y toda la app se actualiza.

## Añadir datasets precargados (selector de la barra lateral)

Edita `src/core/config.py → PRELOADED_DATASETS` (el primero que exista es el principal
y se carga por defecto):

```python
PRELOADED_DATASETS = [
    {"label": "Docentes (AUDIT)", "path": "Datos_Docentes_AUDIT 2.xlsx"},
    {"label": "Bienestar laboral", "path": "cleaned_data - cleaned_data.csv"},
]
```

Solo se muestran los archivos presentes en disco. Los datos no se versionan en git
(`.gitignore` excluye `*.csv`/`*.xlsx`); coloca tus archivos junto al proyecto.

## Recomendaciones de calidad

- Nombra las columnas de forma consistente (usa los prefijos si buscas el diagnóstico completo).
- Revisa el **diagnóstico de ingesta** tras cargar (filas, columnas mapeadas, celdas
  imputadas, columnas no reconocidas) — panel también disponible con `?debug=1`.
- Para IA (chat, interpretaciones, informe) configura la API key de Gemini
  (`.streamlit/secrets.toml`). Ver [README](../README.md).
