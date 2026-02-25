import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import io
from src.data.processor import ExcelProcessor

def test_extra_columns():
    print("Testing Extra Columns Preservation...")
    
    # 1. Create a dummy Excel file with standard + extra columns
    data = {
        'Edad': ['25', '30', '35'],
        'Sexo': ['M', 'F', 'M'],
        'Extra_Variable_1': ['A', 'B', 'C'], # Extra
        'Extra_Variable_2': [10, 20, 30]     # Extra Numeric
    }
    df_input = pd.DataFrame(data)
    
    # Save to buffer
    buffer = io.BytesIO()
    df_input.to_excel(buffer, index=False)
    buffer.seek(0)
    
    # 2. Define a minimal reference schema (only standard cols)
    ref_schema = pd.DataFrame(columns=['(SD)Edad', '(SD)Sexo'])
    
    # 3. Process
    processor = ExcelProcessor()
    # Note: skip_unmapped=False is the new default, but being explicit
    df_result, report = processor.process_complex_excel(buffer, ref_schema, skip_unmapped=False)
    
    # 4. Assertions
    print("\nReport:", report)
    print("\nResult Columns:", df_result.columns.tolist())
    
    # Check if standard columns are mapped
    assert '(SD)Edad' in df_result.columns
    assert '(SD)Sexo' in df_result.columns
    
    # Check if extra columns are preserved
    assert 'Extra_Variable_1' in df_result.columns
    assert 'Extra_Variable_2' in df_result.columns
    
    # Check report
    assert 'Extra_Variable_1' in report['extra_variables']
    assert 'Extra_Variable_2' in report['extra_variables']
    
    print("\n✅ Test Passed: Extra columns preserved!")

if __name__ == "__main__":
    try:
        test_extra_columns()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        exit(1)
