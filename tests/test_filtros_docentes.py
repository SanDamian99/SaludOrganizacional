"""
Filtros del dashboard de docentes.

El equipo investigador acordó nueve filtros y ninguno más: colegio, edad, sexo,
estado civil, nivel educativo, zona de vivienda, estrato, tipo de contratación y
nivel del cargo. Estas pruebas fijan esa lista, su orden, y que los ítems Likert,
los identificadores y el texto libre nunca aparezcan como filtro.
"""
import numpy as np
import pandas as pd

from src.data.loader import es_demo
from src.ui.components import filtering as f


def _docentes(n=40) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        "ID": [f"D{i:03d}" for i in range(n)],
        "Nombre": [f"Persona {i}" for i in range(n)],
        "(SD)Edad": rng.integers(25, 60, n),
        "(SD)Sexo": rng.choice(["Femenino", "Masculino"], n),
        "(SD)Estado Civil": rng.choice(["Soltero", "Casado"], n),
        "(SD)Nivel Educativo": rng.choice(["Profesional", "Posgrado"], n),
        "(SD)Zona de vivienda": rng.choice(["Urbana", "Rural"], n),
        "(SD)Estrato Socioeconómico": rng.integers(1, 5, n),
        "Colegio": rng.choice(["Bojacá", "Bojacá ", "Fusca"], n),
        "Este es un colegio": [0] * n,
        "(LB)Tipo de Contrato": rng.choice(["En propiedad", "En provisionalidad"], n),
        "Nivel de Cargo": rng.choice(["Operativo", "Directivo"], n),
        "Nivel de Cargo  2": rng.choice(["Docente de aula", "Rector"], n),
        "Comentario": [f"texto libre {i}" for i in range(n)],
        "PSS3": rng.integers(0, 5, n),
        "PSS_T": rng.integers(0, 41, n),
    })


def test_los_filtros_son_exactamente_los_nueve_acordados_y_en_orden():
    etiquetas = [e for e, _, _ in f.filtros_disponibles(_docentes())]
    assert etiquetas == ["Colegio", "Edad", "Sexo", "Estado civil", "Nivel educativo",
                         "Zona de vivienda", "Estrato", "Tipo de contratación", "Nivel del cargo"]


def test_cada_filtro_encuentra_su_columna_real():
    cols = dict((e, c) for e, c, _ in f.filtros_disponibles(_docentes()))
    assert cols["Colegio"] == "Colegio"                 # no «Este es un colegio», que es constante
    assert cols["Nivel del cargo"] == "Nivel de Cargo"  # no «Nivel de Cargo  2»
    assert cols["Tipo de contratación"] == "(LB)Tipo de Contrato"


def test_la_edad_es_un_rango_y_lo_demas_categorias():
    tipos = dict((e, t) for e, _, t in f.filtros_disponibles(_docentes()))
    assert tipos["Edad"] == "rango"
    assert all(t == "categoria" for e, t in tipos.items() if e != "Edad")


def test_nada_fuera_de_la_lista_entra_como_filtro():
    cols = f.columnas_filtrables(_docentes())
    for prohibida in ("Nombre", "ID", "Comentario", "PSS3", "PSS_T", "Nivel de Cargo  2"):
        assert prohibida not in cols


def test_sin_variables_acordadas_se_cae_al_criterio_generico():
    otro = pd.DataFrame({"Departamento": ["A", "B"] * 10, "Nota": range(20),
                         "Correo": [f"x{i}@y.z" for i in range(20)]})
    assert f.columnas_filtrables(otro) == ["Departamento"]


def test_normalizar_colapsa_espacios_y_conserva_nan_y_mayusculas():
    df = pd.DataFrame({"Colegio": ["Bojacá ", "Bojacá", "  Fusca", np.nan, "FUSCA"]})
    n = f.normalizar_categorias(df, ["Colegio"])
    assert n["Colegio"].tolist()[:3] == ["Bojacá", "Bojacá", "Fusca"]
    assert pd.isna(n["Colegio"].iloc[3]) and n["Colegio"].iloc[4] == "FUSCA"


def test_aplicar_filtros_por_categoria_y_por_rango():
    df = _docentes()
    r = f.aplicar_filtros(df, {"Colegio": ["Bojacá"], "(SD)Edad": (30, 40)})
    assert set(r["Colegio"].str.strip()) <= {"Bojacá"}
    assert r["(SD)Edad"].between(30, 40).all()
    # el filtro de colegio recoge también «Bojacá » (con espacio), porque se normaliza
    assert len(r) == len(df[(df["Colegio"].str.strip() == "Bojacá") & df["(SD)Edad"].between(30, 40)])
    assert len(f.aplicar_filtros(df, {})) == len(df)
    assert len(f.aplicar_filtros(df, {"Colegio": []})) == len(df)


def test_etiquetas_legibles():
    assert f.etiqueta_filtro("(LB)Tipo de Contrato") == "Tipo de contratación"
    assert f.etiqueta_filtro("Intitución") == "Colegio"
    assert f.etiqueta_filtro("(SD)Estrato Socioeconómico") == "Estrato"
    assert f.etiqueta_filtro("(BM),(CT)Otra cosa") == "Otra cosa"


def test_es_demo():
    assert es_demo("Demostración (datos sintéticos)")
    assert not es_demo("Docentes · versión 23/09/2026 (479 filas)")
    assert not es_demo(None)
