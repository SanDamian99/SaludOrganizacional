"""
Filtros flexibles del dashboard de docentes.

Se prueba la lógica pura (sin Streamlit): qué columnas se ofrecen como filtro, en qué
orden, cómo se limpian las categorías con espacios sobrantes y cómo se aplica la
selección. También la marca de dataset de demostración.
"""
import numpy as np
import pandas as pd
import pytest

from src.ui.components import filtering as f
from src.data.loader import es_demo


@pytest.fixture
def docentes():
    """Parecido al archivo real: colegio con siglas, constante inútil, nombre y texto libre."""
    n = 40
    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "Nombre": [f"Persona {i}" for i in range(n)],
        "Correo electrónico": [f"p{i}@x.co" for i in range(n)],
        "Intitución": ["Bojacá", "Bojacá ", "CND", "SMR"] * (n // 4),
        "Este es un colegio:": [0] * n,
        "(SD)Sexo": rng.choice([1, 2], n).tolist(),
        "(SD)Estado Civil": rng.choice([1, 2, 3, 4, 5], n).tolist(),
        "(SD)Edad": rng.integers(22, 65, n).tolist(),
        "(LB)Tipo de Contrato": rng.choice([1, 2, 3], n).tolist(),
        "Comentario libre": [f"opinión distinta {i}" for i in range(n)],
        "PSS1": rng.choice([1, 2, 3, 4, 5], n).tolist(),
    })


def test_colegio_va_primero(docentes):
    cols = f.columnas_filtrables(docentes)
    assert cols[0] == "Intitución"
    assert f.columna_colegio(docentes) == "Intitución"


def test_despues_del_colegio_vienen_las_del_diccionario_en_orden(docentes):
    cols = f.columnas_filtrables(docentes)
    assert cols[1:4] == ["(SD)Sexo", "(SD)Estado Civil", "(LB)Tipo de Contrato"]
    # Un ítem Likert numérico fuera del diccionario no se ofrece como filtro.
    assert "PSS1" not in cols


def test_excluye_identificadores_constantes_texto_libre_y_continuas(docentes):
    cols = f.columnas_filtrables(docentes)
    assert "Nombre" not in cols
    assert "Correo electrónico" not in cols
    assert "Este es un colegio:" not in cols
    assert "Comentario libre" not in cols
    assert "(SD)Edad" not in cols


def test_constante_con_nombre_de_colegio_no_es_el_colegio():
    df = pd.DataFrame({"Este es un colegio:": [0] * 10, "x": range(10)})
    assert f.columna_colegio(df) is None


def test_espacios_finales_se_colapsan(docentes):
    df = f.normalizar_categorias(docentes, ["Intitución"])
    assert sorted(df["Intitución"].unique()) == ["Bojacá", "CND", "SMR"]
    assert (df["Intitución"] == "Bojacá").sum() == 20


def test_normalizar_conserva_nan_y_mayusculas():
    df = pd.DataFrame({"c": ["  La  Balsa ", None, "cnd", np.nan]})
    out = f.normalizar_categorias(df, ["c"])
    assert out["c"].tolist()[0] == "La Balsa"
    assert out["c"].tolist()[2] == "cnd"
    assert out["c"].isna().sum() == 2


def test_aplicar_filtros_con_dos_columnas(docentes):
    out = f.aplicar_filtros(docentes, {"Intitución": ["Bojacá"], "(SD)Sexo": [1]})
    assert len(out) > 0
    assert set(out["Intitución"]) == {"Bojacá"}
    assert set(out["(SD)Sexo"]) == {1}
    # La selección sobre la categoría limpia también recoge las filas con espacio final.
    assert len(f.aplicar_filtros(docentes, {"Intitución": ["Bojacá"]})) == 20


def test_aplicar_filtros_lista_vacia_no_filtra(docentes):
    assert len(f.aplicar_filtros(docentes, {"Intitución": []})) == len(docentes)
    assert len(f.aplicar_filtros(docentes, {})) == len(docentes)


def test_etiqueta_filtro():
    assert f.etiqueta_filtro("Intitución") == "Colegio"
    assert f.etiqueta_filtro("(SD)Sexo") == "Sexo"
    assert f.etiqueta_filtro("(LB)Tipo de Contrato") == "Tipo de Contrato"
    assert f.etiqueta_filtro("(BM),(CT)Tengo la opción") == "Tengo la opción"
    assert f.etiqueta_filtro("PSS1") == "PSS1"


def test_es_demo():
    assert es_demo("Demostración (datos sintéticos)") is True
    assert es_demo("Docentes (AUDIT)") is False
    assert es_demo("archivo_subido.xlsx") is False
    assert es_demo(None) is False


def test_los_items_likert_numericos_no_se_ofrecen_como_filtro():
    """Fuera del diccionario, solo las columnas de texto entran como filtro."""
    import pandas as pd
    from src.ui.components.filtering import columnas_filtrables
    df = pd.DataFrame({
        "Intitución": ["CND", "SMR"] * 10,
        "(SD)Sexo": [0, 1] * 10,                 # numérica pero del diccionario: entra
        "PSS3": [0, 1, 2, 3] * 5,               # ítem Likert: no entra
        "Nivel de Cargo": ["Docente", "Directivo"] * 10,   # texto: entra
    })
    cols = columnas_filtrables(df)
    assert cols[0] == "Intitución"
    assert "(SD)Sexo" in cols and "Nivel de Cargo" in cols
    assert "PSS3" not in cols
