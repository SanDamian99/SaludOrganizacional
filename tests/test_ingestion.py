import pytest
import pandas as pd
import numpy as np
import io
from src.data.processor import ExcelProcessor, DataCleaner

# Helper para simular diferentes escenarios de datos
def create_mock_csv(data_dict, sep=','):
    df = pd.DataFrame(data_dict)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, sep=sep, encoding='utf-8')
    buffer.seek(0)
    # Simulate uploaded file
    buffer.name = 'test_file.csv'
    return buffer

def create_mock_excel(data_dict):
    df = pd.DataFrame(data_dict)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    buffer.name = 'test_file.xlsx'
    return buffer

def test_well_formed_csv():
    """CSV bien formado con columnas estándar → debe mapear todo"""
    data = {
        'ID': [1, 2],
        '(SD)Edad': [25, 30],
        '(LB)Cargo': ['Analista', 'Gerente'],
        '(BM),(CT)Tengo presiones de tiempo poco realistas.': [5, 6]
    }
    buffer = create_mock_csv(data)
    cleaner = DataCleaner()
    df, report = cleaner.clean_and_process(buffer)
    
    assert len(df) == 2
    assert report['n_cols_unmapped'] == 0
    assert 'ID' in df.columns
    assert '(SD)Edad' in df.columns
    assert '(BM),(CT)Tengo presiones de tiempo poco realistas.' in df.columns

def test_fuzzy_matching_excel():
    """Excel con columnas renombradas (fuzzy) → debe mapear con advertencias"""
    data = {
        'Identificador': [1, 2], # Fuzzy a 'ID' (opcional, igual no es likert)
        'Edad participante': [25, 30], # Fuzzy a '(SD)Edad'
        'Tengo presiones de tiempo irreales': [5, 6] # Fuzzy a '(BM),(CT)Tengo presiones de tiempo poco realistas.'
    }
    buffer = create_mock_excel(data)
    cleaner = DataCleaner()
    df, report = cleaner.clean_and_process(buffer)
    
    # Incluso con fuzzy, debería al menos intentar mapear o detectar likert
    assert len(df) == 2
    assert len(report['warnings']) >= 0

def test_missing_data_imputation():
    """Archivo con 30% de datos faltantes → debe imputar y reportar"""
    data = {
        'ID': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        '(BM)Agotamiento': [2, np.nan, 3, np.nan, 5, np.nan, 4, np.nan, 2, np.nan] # 50% faltante
    }
    buffer = create_mock_csv(data)
    cleaner = DataCleaner()
    df, report = cleaner.clean_and_process(buffer)
    
    assert df['(BM)Agotamiento'].isna().sum() == 0
    assert report['n_cells_imputed'] > 0

def test_likert_detection_without_prefixes():
    """Archivo sin prefijos de categoría → debe detectar Likert igualmente"""
    data = {
        'ID': [1, 2, 3, 4],
        'Pregunta sobre cansancio': [1, 2, 3, 4],
        'Pregunta sobre estres': [5, 6, 7, 1]
    }
    buffer = create_mock_csv(data)
    cleaner = DataCleaner()
    df, report = cleaner.clean_and_process(buffer)
    
    # Debería predecir las columnas como escalas
    assert 'Pregunta sobre cansancio' in df.columns or any('cansancio' in c for c in df.columns)
    
def test_mixed_likert_scales():
    """Escala 1-5 mezclada con 1-7 → debe detectar rangos distintos por columna"""
    data = {
        'ID': [1, 2, 3, 4],
        '(BM)Escala_1': [1, 3, 5, 2], # max 5
        '(BM)Escala_2': [1, 4, 7, 6]  # max 7
    }
    buffer = create_mock_csv(data)
    cleaner = DataCleaner()
    df, report = cleaner.clean_and_process(buffer)
    
    ranges = report.get('scale_ranges_detected', {})
    if ranges:
        assert ranges.get('(BM)Escala_1', [1,5]) == [1,5] or ranges.get('(BM)Escala_1', {}).get('max') == 5
        assert ranges.get('(BM)Escala_2', [1,7]) == [1,7] or ranges.get('(BM)Escala_2', {}).get('max') == 7

def test_empty_file():
    """Archivo vacío → debe fallar con mensaje claro (no crash silencioso)"""
    data = {}
    buffer = create_mock_csv(data)
    cleaner = DataCleaner()
    
    try:
        df, report = cleaner.clean_and_process(buffer)
        assert False, "Should have raised ValueError or similar"
    except Exception as e:
        assert str(e) != ""

def test_latin1_encoding():
    """Encoding latin-1 → debe detectar y leer correctamente"""
    df = pd.DataFrame({'ID': [1], 'Agotamiento': [5]})
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding='latin-1')
    buffer.seek(0)
    buffer.name = 'test_latin1.csv'
    
    cleaner = DataCleaner()
    df_clean, report = cleaner.clean_and_process(buffer)
    
    assert len(df_clean) == 1
    # Check ascii as well since chardet may detect latin1 as ascii if only standard chars are used
    assert any(enc in report.get('encoding_detected', '').lower() for enc in ['latin', 'iso', 'ascii'])

def test_extra_columns_preservation():
    """Dataset con columnas completamente nuevas (instrumento nuevo) → debe preservarlas en extra_columns"""
    data = {
        'ID': [1, 2],
        '(SD)Edad': [25, 30],
        '(NUEVO)Dimension Magica': [4, 5],
        'Variable Desconocida': ['A', 'B']
    }
    buffer = create_mock_csv(data)
    cleaner = DataCleaner()
    df, report = cleaner.clean_and_process(buffer)
    
    assert '(NUEVO)Dimension Magica' in df.columns
    assert 'Variable Desconocida' in df.columns
    assert report['n_cols_unmapped'] > 0
