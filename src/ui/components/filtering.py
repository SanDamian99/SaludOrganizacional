"""
Filtros flexibles del dashboard de docentes.

La lógica (qué columnas se pueden filtrar, cómo se limpian sus categorías y cómo se
aplica la selección) vive en funciones puras sin Streamlit para poder probarla con
DataFrames pequeños. `render_filtering_sidebar` solo dibuja los controles encima.

El criterio de "columna filtrable" es deliberadamente descriptivo y no depende del
diccionario de datos: los archivos reales traen columnas que el diccionario no
conoce (el colegio de los docentes llega como «Intitución», con esa ortografía) y la
usuaria pidió poder elegir cualquier corte razonable, no solo los previstos.
"""
import re

import pandas as pd
import streamlit as st

from src.core.config import DATA_DICTIONARY
from src.data.processor import is_protected_column, normalize_text

# Más de 50 valores ya no cabe en un desplegable y suele ser texto libre.
MAX_CATEGORIAS = 50
# Una numérica con más de 12 valores distintos se trata como continua (edad, horas,
# puntajes totales), no como categoría; las escalas Likert quedan por debajo.
MAX_VALORES_NUMERICOS = 12
# Si más de la mitad de las filas trae un valor propio, es texto libre (comentarios,
# curso con letra), no una categoría compartida.
MAX_RATIO_UNICOS = 0.5

# Fragmentos (ya normalizados) que delatan la columna de colegio. "intituc" recoge la
# ortografía real del archivo de docentes («Intitución»).
_PALABRAS_COLEGIO = ("instituc", "intituc", "colegio", "sede")

# Prefijos de sección del diccionario: "(SD)", "(LB)", "(BM),(CT)"...
_PREFIJOS_SECCION = re.compile(r"^(?:\([A-Za-z]{2,3}\),?\s*)+")

# Nombres legibles para columnas cuyo encabezado real no se entiende o está mal escrito.
_ETIQUETAS_LEGIBLES = {
    "intitucion": "Colegio",
    "institucion": "Colegio",
}


def _categoricas_diccionario() -> list[str]:
    """Claves categóricas de las secciones sociodemográfica y laboral, en su orden."""
    claves = []
    for seccion in ("Variables Sociodemográficas", "Variables Laborales"):
        for clave, meta in DATA_DICTIONARY.get(seccion, {}).items():
            if meta.get("Tipo") == "Categórica":
                claves.append(clave)
    return claves


def _limpiar_texto(valor):
    """Quita espacios sobrantes de una cadena; deja intacto lo que no sea texto (y los NaN)."""
    if isinstance(valor, str):
        return re.sub(r"\s+", " ", valor).strip()
    return valor


def normalizar_categorias(df: pd.DataFrame, columnas) -> pd.DataFrame:
    """
    Colapsa espacios en las columnas de texto indicadas para que «Bojacá » y «Bojacá»
    cuenten como la misma categoría. No toca mayúsculas ni acentos: el filtro debe
    mostrar los valores tal como los escribió quien recogió los datos.
    """
    df = df.copy()
    for col in columnas:
        if col in df.columns and (df[col].dtype == object or pd.api.types.is_string_dtype(df[col])):
            df[col] = df[col].map(_limpiar_texto)
    return df


def _columnas_texto(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])]


def _es_filtrable(serie: pd.Series) -> bool:
    """Una columna sirve como filtro si tiene pocas categorías compartidas por muchas filas."""
    validos = serie.dropna()
    if validos.empty:
        return False
    n_unicos = validos.nunique()
    if n_unicos < 2 or n_unicos > MAX_CATEGORIAS:
        return False
    if pd.api.types.is_numeric_dtype(serie) and n_unicos > MAX_VALORES_NUMERICOS:
        return False
    if n_unicos / len(validos) > MAX_RATIO_UNICOS:
        return False
    return True


def columna_colegio(df: pd.DataFrame) -> str | None:
    """
    Primera columna cuyo nombre habla de institución, colegio o sede y que de verdad
    distingue registros. «Este es un colegio:» es constante en el archivo de docentes
    y se descarta por eso, no por el nombre.
    """
    df = normalizar_categorias(df, _columnas_texto(df))
    for col in df.columns:
        nombre = normalize_text(col)
        if any(p in nombre for p in _PALABRAS_COLEGIO) and df[col].dropna().nunique() >= 2:
            return col
    return None


def columnas_filtrables(df: pd.DataFrame) -> list[str]:
    """
    Columnas candidatas a filtro, ordenadas por utilidad: el colegio primero, luego las
    categóricas del diccionario en su orden y por último el resto alfabéticamente.
    Excluye identificadores (nombre, correo, marcas de tiempo), texto libre y
    numéricas continuas.
    """
    df = normalizar_categorias(df, _columnas_texto(df))
    candidatas = [
        c for c in df.columns
        if not is_protected_column(c) and _es_filtrable(df[c])
    ]
    if not candidatas:
        return []

    orden: list[str] = []
    colegio = columna_colegio(df)
    if colegio in candidatas:
        orden.append(colegio)

    # Las claves del diccionario a veces traen espacios finales que el archivo no tiene.
    por_nombre = {normalize_text(c): c for c in candidatas}
    for clave in _categoricas_diccionario():
        col = por_nombre.get(normalize_text(clave))
        if col and col not in orden:
            orden.append(col)

    # Fuera del diccionario, una columna numérica con pocos valores casi siempre es
    # un ítem Likert (AP1, PSS3…), y ofrecer ciento cincuenta de esos como filtro
    # sepulta los que sirven. Del resto entran solo las de texto.
    resto = sorted((c for c in candidatas
                    if c not in orden and not pd.api.types.is_numeric_dtype(df[c])),
                   key=lambda c: normalize_text(c))
    return orden + resto


def aplicar_filtros(df: pd.DataFrame, activos: dict) -> pd.DataFrame:
    """
    Conserva las filas cuyo valor está en la lista elegida para cada columna. Una lista
    vacía no filtra. Se normaliza antes de comparar para que la selección hecha sobre
    categorías limpias encuentre también los valores con espacios sobrantes.
    """
    df = normalizar_categorias(df, _columnas_texto(df))
    for col, valores in activos.items():
        if col in df.columns and valores:
            df = df[df[col].isin(list(valores))]
    return df


def etiqueta_filtro(col: str) -> str:
    """Nombre legible: sin prefijos de sección y con los encabezados torcidos corregidos."""
    limpio = _PREFIJOS_SECCION.sub("", str(col)).strip()
    return _ETIQUETAS_LEGIBLES.get(normalize_text(limpio), limpio)


def _filtros_por_defecto(df: pd.DataFrame, opciones: list[str]) -> list[str]:
    """Colegio (si existe) más las dos primeras del diccionario presentes; máximo tres."""
    defecto = []
    colegio = columna_colegio(df)
    if colegio in opciones:
        defecto.append(colegio)
    por_nombre = {normalize_text(c): c for c in opciones}
    for clave in _categoricas_diccionario():
        col = por_nombre.get(normalize_text(clave))
        if col and col not in defecto:
            defecto.append(col)
        if len(defecto) - (1 if colegio in defecto else 0) >= 2:
            break
    return defecto[:3]


def _sanear_estado(key: str, opciones: list) -> None:
    """
    Al cambiar de dataset en la barra lateral, el estado del multiselect puede guardar
    columnas o valores que el nuevo archivo no tiene, y Streamlit tumba la página por
    eso. Se recorta la selección a lo que sigue existiendo.
    """
    if key in st.session_state:
        st.session_state[key] = [v for v in st.session_state[key] if v in opciones]


def render_filtering_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """Dibuja los filtros en la barra lateral y devuelve el DataFrame filtrado y normalizado."""
    st.sidebar.markdown("### 🔍 Filtros Avanzados")

    opciones = columnas_filtrables(df)
    df_norm = normalizar_categorias(df, _columnas_texto(df))

    activos: dict[str, list] = {}
    with st.sidebar.expander("Seleccionar Filtros", expanded=True):
        if not opciones:
            st.caption("Este dataset no tiene columnas categóricas para filtrar.")
        else:
            _sanear_estado("filtros_columnas", opciones)
            elegidas = st.multiselect(
                "Filtrar por",
                options=opciones,
                default=_filtros_por_defecto(df, opciones),
                format_func=etiqueta_filtro,
                key="filtros_columnas",
            )
            for col in elegidas:
                valores = df_norm[col].dropna().unique().tolist()
                valores = sorted(valores, key=lambda v: (str(type(v)), v))
                _sanear_estado(f"filtro_{col}", valores)
                seleccion = st.multiselect(
                    etiqueta_filtro(col),
                    options=valores,
                    default=[],
                    format_func=lambda v: str(v),
                    key=f"filtro_{col}",
                )
                if seleccion:
                    activos[col] = seleccion

    df_filtrado = aplicar_filtros(df, activos)

    if len(df_filtrado) != len(df):
        st.sidebar.info(f"Registros filtrados: {len(df_filtrado)} / {len(df)}")
    else:
        st.sidebar.text(f"Total registros: {len(df)}")

    return df_filtrado
