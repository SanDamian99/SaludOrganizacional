import pandas as pd
import io
from src.data.processor import DataCleaner

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
