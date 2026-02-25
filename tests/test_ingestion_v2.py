"""Tests de ingesta de datos — deben pasar todos antes de deploy."""
import pytest
import pandas as pd
import io
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.processor import DataCleaner


@pytest.fixture
def processor():
    return DataCleaner()


def make_csv(data: dict, encoding='utf-8') -> io.BytesIO:
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    buf.write(df.to_csv(index=False).encode(encoding))
    buf.seek(0)
    buf.name = "test_data.csv"
    return buf


# --- TEST 1: CSV bien formado ---
def test_standard_csv_loads_without_loss(processor):
    data = {
        "(SD)Edad": [25, 30, 35],
        "(SD)Sexo": ["Hombre", "Mujer", "Mujer"],
        "(BM),(SB)Burnout_1": [3, 5, 7],
        "(BM),(SB)Burnout_2": [2, 4, 6],
    }
    df, report = processor.process_file(make_csv(data))
    assert report["success"] is True
    assert report["n_rows_final"] == 3
    assert report["n_cells_imputed"] == 0


# --- TEST 2: Archivo con datos faltantes ---
def test_missing_data_gets_imputed(processor):
    data = {
        "(BM),(SB)Burnout_1": [3, None, 7, None, 5],
        "(BM),(SB)Burnout_2": [2, 4, None, 6, 1],
    }
    df, report = processor.process_file(make_csv(data))
    assert report["success"] is True
    assert report["n_cells_imputed"] > 0
    assert df.isna().sum().sum() == 0  # No quedan nulos


# --- TEST 3: Escala 1-5 y 1-7 en el mismo archivo ---
def test_mixed_likert_scales_preserved(processor):
    data = {
        "(BM),(SB)Item_1_5": [1, 2, 3, 4, 5],   # Escala 1-5
        "(BM),(CT)Item_2_7": [1, 2, 3, 4, 7],    # Escala 1-7
    }
    df, report = processor.process_file(make_csv(data))
    assert report["success"] is True
    assert df.iloc[:, 0].max() == 5
    assert df.iloc[:, 1].max() == 7


# --- TEST 4: Columnas desconocidas se preservan ---
def test_unknown_columns_preserved(processor):
    data = {
        "(SD)Edad": [25, 30],
        "columna_nueva_instrumento": [1, 2],
    }
    df, report = processor.process_file(make_csv(data))
    assert report["success"] is True
    assert len(df.columns) >= 2  # No se descartó la columna desconocida


# --- TEST 5: Archivo vacío no debe crashear ---
def test_empty_file_fails_gracefully(processor):
    buf = io.BytesIO(b"")
    buf.name = "empty.csv"
    df, report = processor.process_file(buf)
    assert report["success"] is False
    assert len(report["warnings"]) > 0


# --- TEST 6: Encoding latin-1 ---
def test_latin1_encoding(processor):
    data = {
        "(SD)Edad": [25, 30, 35],
        "(BM),(SB)Estrés_1": [3, 5, 7],
    }
    df, report = processor.process_file(make_csv(data, encoding='latin-1'))
    assert report["success"] is True
    assert report["n_rows_final"] == 3


# --- TEST 7: Idempotencia — mismo archivo dos veces = mismo resultado ---
def test_same_file_twice_same_result():
    data = {"(BM),(SB)Burnout_1": [3, 5, 7], "(SD)Edad": [25, 30, 35]}

    buf1 = make_csv(data)
    buf2 = make_csv(data)

    p1 = DataCleaner()
    p2 = DataCleaner()

    df1, _ = p1.process_file(buf1)
    df2, _ = p2.process_file(buf2)

    pd.testing.assert_frame_equal(df1.reset_index(drop=True), df2.reset_index(drop=True))


# --- TEST 8: Dataset grande no pierde filas ---
def test_large_dataset_no_row_loss(processor):
    import numpy as np
    n = 5000
    data = {
        "(SD)Edad": np.random.randint(18, 65, n),
        "(BM),(SB)Burnout_1": np.random.randint(1, 8, n),
        "(BM),(SB)Burnout_2": np.random.randint(1, 8, n),
    }
    df, report = processor.process_file(make_csv(data))
    assert report["success"] is True
    assert report["n_rows_final"] == n
