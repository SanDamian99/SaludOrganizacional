"""
Carga del archivo de docentes: sin imputación y con los códigos de faltante.

`ExcelProcessor` rellenaba con la mediana todo número que faltara; así
«Bienestar psicosocial», que solo se preguntó en 2025, salía con N = 479. Ya
no se imputa nada, para ningún archivo. Y «hijos = 10» entra como faltante.
"""
import io

import numpy as np
import pandas as pd

from src.data import loader
from src.data.processor import ExcelProcessor


def _csv(data) -> io.BytesIO:
    return io.BytesIO(pd.DataFrame(data).to_csv(index=False).encode("utf-8"))


def test_el_procesador_ya_no_imputa():
    df, report = ExcelProcessor().process_complex_excel(None, df_input=pd.DataFrame({
        "ID": range(1, 11),
        "(BM)Agotamiento": [2, np.nan, 3, np.nan, 5, np.nan, 4, np.nan, 2, np.nan],
        "BLG_Psicoso1": [np.nan] * 5 + [1, 2, 3, 4, 5],
    }))
    assert df["(BM)Agotamiento"].isna().sum() == 5
    assert df["BLG_Psicoso1"].isna().sum() == 5
    assert report["n_cells_imputed"] == 0 and report["imputation_by_column"] == {}
    assert not hasattr(ExcelProcessor, "_impute_missing")


def test_posprocesar_aplica_los_codigos_solo_a_docentes():
    base = {f"PSS{i}": [1.0] * 12 for i in range(1, 11)}
    base.update({f"BTA{i}": [1.0] * 12 for i in range(1, 13)})
    base["(SD)Numero de hijos"] = [10.0, 1, 2, 10, 0, 1, 2, 3, 1, 1, 2, 0]
    df, report = loader._posprocesar(pd.DataFrame(base), {})
    assert df["(SD)Numero de hijos"].isna().sum() == 2
    assert report["codigos_faltantes"] == {"(SD)Numero de hijos": 2}

    otro = pd.DataFrame({"(SD)Numero de hijos": [10.0, 1], "x": [1, 2]})
    df2, report2 = loader._posprocesar(otro, {})
    assert df2.equals(otro) and "codigos_faltantes" not in report2


def test_load_dataset_pasa_por_el_posprocesado(tmp_path):
    base = {f"PSS{i}": [1.0] * 12 for i in range(1, 11)}
    base.update({f"BTA{i}": [1.0] * 12 for i in range(1, 13)})
    base["Número de hijos"] = [10.0, 1, 2, 10, 0, 1, 2, 3, 1, 1, 2, 0]
    base["BLG_Psicoso1"] = [np.nan] * 6 + [5.0] * 6
    ruta = tmp_path / "docentes.csv"
    pd.DataFrame(base).to_csv(ruta, index=False)
    df, report = loader.load_dataset(str(ruta))
    col = next(c for c in df.columns if "hijos" in c.lower())
    assert df[col].isna().sum() == 2 and df["BLG_Psicoso1"].isna().sum() == 6
    assert report["n_cells_imputed"] == 0
