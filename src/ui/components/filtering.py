"""
Filtros flexibles del dashboard de docentes.

La lógica (qué columnas se pueden filtrar, cómo se limpian sus categorías y cómo se
aplica la selección) vive en funciones puras sin Streamlit para poder probarla con
DataFrames pequeños. `render_filtering_sidebar` solo dibuja los controles encima.

Los filtros son los nueve que acordó el equipo investigador (`FILTROS_DOCENTES`):
colegio, edad, sexo, estado civil, nivel educativo, zona de vivienda, estrato, tipo
de contratación y nivel del cargo. Se localizan por fragmentos del nombre porque el
mismo dato llega con encabezados distintos según el archivo. Solo si un dataset no
trae ninguno se cae a un criterio descriptivo para no dejar la barra vacía.
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


# Los filtros del dashboard de docentes, en el orden en que se muestran. Los
# acordó el equipo investigador (sep 2026): ni más ni menos. Cada uno se busca
# por un fragmento del nombre normalizado de la columna, porque el mismo dato
# llega con encabezados distintos según el archivo («(SD)Sexo», «Sexo»).
FILTROS_DOCENTES = [
    ("Colegio", ("colegio", "intituc", "instituc"), "categoria"),
    ("Edad", ("edad",), "rango"),
    ("Sexo", ("sexo",), "categoria"),
    ("Estado civil", ("estado civil",), "categoria"),
    ("Nivel educativo", ("nivel educativo",), "categoria"),
    ("Zona de vivienda", ("zona",), "categoria"),
    ("Estrato", ("estrato",), "categoria"),
    ("Tipo de contratación", ("tipo de contrat",), "categoria"),
    ("Nivel del cargo", ("nivel de cargo",), "categoria"),
]


def filtros_disponibles(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """[(etiqueta, columna real, tipo)] de FILTROS_DOCENTES presentes en `df`, en orden.

    Una columna constante no sirve como filtro y se omite («Este es un colegio»
    vale 0 en todas las filas). Si dos columnas encajan con el mismo fragmento,
    gana la de nombre más corto: «Nivel de Cargo» antes que «Nivel de Cargo 2».
    """
    salida = []
    usadas: set[str] = set()
    for etiqueta, fragmentos, tipo in FILTROS_DOCENTES:
        candidatas = [c for c in df.columns if c not in usadas
                      and any(f in normalize_text(c) for f in fragmentos)
                      and df[c].dropna().nunique() >= 2]
        if not candidatas:
            continue
        col = sorted(candidatas, key=lambda c: len(str(c)))[0]
        usadas.add(col)
        salida.append((etiqueta, col, tipo))
    return salida


def columnas_filtrables(df: pd.DataFrame) -> list[str]:
    """Columnas que el dashboard ofrece como filtro, en el orden acordado.

    Se limita a la lista del equipo. Si un dataset no trae ninguna de esas
    variables (otro instrumento), se cae al criterio descriptivo de
    `_candidatas_genericas` para no dejar la barra vacía.
    """
    fijas = [col for _, col, _ in filtros_disponibles(df)]
    return fijas if fijas else _candidatas_genericas(df)


def _candidatas_genericas(df: pd.DataFrame) -> list[str]:
    """Categóricas de texto con pocas categorías, excluyendo identificadores y texto libre."""
    df = normalizar_categorias(df, _columnas_texto(df))
    candidatas = [c for c in df.columns if not is_protected_column(c) and _es_filtrable(df[c])
                  and not pd.api.types.is_numeric_dtype(df[c])]
    return sorted(candidatas, key=lambda c: normalize_text(c))


def aplicar_filtros(df: pd.DataFrame, activos: dict) -> pd.DataFrame:
    """Aplica la selección: una lista de valores filtra por pertenencia; una tupla
    (mínimo, máximo) filtra por rango cerrado. Las filas sin dato en la columna
    filtrada quedan fuera, como en cualquier filtro."""
    if not activos:
        return df
    df = normalizar_categorias(df, [c for c in activos if c in df.columns])
    for col, valores in activos.items():
        if col not in df.columns:
            continue
        if isinstance(valores, tuple) and len(valores) == 2:
            df = df[pd.to_numeric(df[col], errors="coerce").between(*valores)]
        elif valores:
            df = df[df[col].isin(valores)]
    return df


def etiqueta_filtro(col: str) -> str:
    """Nombre legible del filtro: el acordado por el equipo si la columna es una de
    las suyas; si no, el encabezado sin prefijos de sección."""
    n = normalize_text(col)
    for etiqueta, fragmentos, _ in FILTROS_DOCENTES:
        if any(f in n for f in fragmentos):
            return etiqueta
    return _etiqueta_generica(col)


def _etiqueta_generica(col: str) -> str:
    """Nombre legible: sin prefijos de sección y con los encabezados torcidos corregidos."""
    limpio = _PREFIJOS_SECCION.sub("", str(col)).strip()
    return _ETIQUETAS_LEGIBLES.get(normalize_text(limpio), limpio)


def _sanear_estado(key: str, opciones: list) -> None:
    """
    Al cambiar de dataset en la barra lateral, el estado de un multiselect puede guardar
    valores que el nuevo archivo no tiene, y Streamlit tumba la página por eso. Se
    recorta la selección a lo que sigue existiendo.
    """
    if key in st.session_state:
        st.session_state[key] = [v for v in st.session_state[key] if v in opciones]


def render_filtering_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """Dibuja los filtros acordados en la barra lateral y devuelve el DataFrame filtrado."""
    st.sidebar.markdown("### 🔍 Filtros")

    disponibles = filtros_disponibles(df)
    df_norm = normalizar_categorias(df, _columnas_texto(df))

    activos: dict = {}
    with st.sidebar.expander("Filtrar docentes", expanded=True):
        if not disponibles:
            for col in _candidatas_genericas(df)[:6]:
                disponibles.append((_etiqueta_generica(col), col, "categoria"))
        if not disponibles:
            st.caption("Este dataset no tiene variables para filtrar.")
        for etiqueta, col, tipo in disponibles:
            if tipo == "rango":
                serie = pd.to_numeric(df_norm[col], errors="coerce").dropna()
                if serie.empty:
                    continue
                minimo, maximo = int(serie.min()), int(serie.max())
                if minimo == maximo:
                    continue
                rango = st.slider(etiqueta, minimo, maximo, (minimo, maximo),
                                  key=f"filtro_{col}")
                if rango != (minimo, maximo):
                    activos[col] = rango
            else:
                valores = df_norm[col].dropna().unique().tolist()
                valores = sorted(valores, key=lambda v: (str(type(v)), v))
                _sanear_estado(f"filtro_{col}", valores)
                # Sin `default`: el valor vive en session_state (que `_sanear_estado`
                # acaba de recortar) y pasar los dos hace que Streamlit avise.
                seleccion = st.multiselect(etiqueta, options=valores,
                                           format_func=lambda v: str(v), key=f"filtro_{col}")
                if seleccion:
                    activos[col] = seleccion

    df_filtrado = aplicar_filtros(df, activos)

    if len(df_filtrado) != len(df):
        st.sidebar.info(f"Registros filtrados: {len(df_filtrado)} / {len(df)}")
    else:
        st.sidebar.text(f"Total registros: {len(df)}")

    return df_filtrado
