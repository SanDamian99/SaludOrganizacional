import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import io
from src.data.processor import ExcelProcessor

def test_robust_processor():
    print("Creating sample Excel file...")
    
    # Create sample data simulating the user's dataset
    data = {
        # Exact match from dictionary
        "Edad": [25, 30, 35, 40, 45],
        
        # Fuzzy match (extra spaces, case)
        "  sexo ": ["Hombre", "Mujer", "Otro", "Hombre", "Mujer"],
        
        # Likert Scale (Standard Frequency)
        "(BM),(CT)Tengo la opción de decidir qué hago en mi trabajo.": [
            "Siempre", "A menudo", "Nunca", "Rara vez", "Alguna vez"
        ],
        
        # Reverse Coding Pattern (from REVERSE_PATTERNS)
        # Pattern: "dificil ver las cosas desde el punto de vista de otros"
        "Es dificil ver las cosas desde el punto de vista de otros": [
            "No me describe en absoluto", # 0 -> should be reversed (4-0 = 4)
            "Me describe muy bien",       # 4 -> should be reversed (4-4 = 0)
            "Me describe poco",           # 1 -> reversed 3
            "Me describe bastante",       # 3 -> reversed 1
            "Algo me describe"            # 2 -> reversed 2
        ],
        
        # Extra Variable (not in dictionary)
        "Satisfaccion con la cafeteria": [
            "Muy satisfecho", "Satisfecho", "Neutro", "Insatisfecho", "Muy insatisfecho"
        ],
        
        # Numeric Flexible (European format assumption)
        "Antiguedad (años)": ["10 años", "5,5", "1 año", "2,5", "0"]
    }
    
    df_sample = pd.DataFrame(data)
    
    # Save to buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_sample.to_excel(writer, index=False)
    buffer.seek(0)
    
    print("Running ExcelProcessor...")
    processor = ExcelProcessor()
    df_result, report = processor.process_complex_excel(buffer)
    
    print("\n--- Processing Report ---")
    print(f"Rows Cleaned: {report['rows_cleaned']}")
    print(f"Columns Processed: {report['columns_processed']}")
    print(f"Extra Variables: {report['extra_variables']}")
    
    print("\n--- Result DataFrame Head ---")
    print(df_result.head())
    
    print("\n--- Verifications ---")
    
    # 1. Check Exact Match & Numeric
    assert "Edad" in df_result.columns or "(SD)Edad" in df_result.columns
    print("✅ Numeric column preserved")
    
    # 2. Check Likert Encoding
    # "Siempre" -> 7 (Standard scale)
    # "Nunca" -> 1
    likert_col = "(BM),(CT)Tengo la opción de decidir qué hago en mi trabajo."
    assert df_result[likert_col].dtype == float
    assert df_result[likert_col].iloc[0] == 7.0 # Siempre
    assert df_result[likert_col].iloc[2] == 1.0 # Nunca
    print("✅ Likert scale encoded correctly")
    
    # 3. Check Reverse Coding
    # "No me describe en absoluto" is 0 in IRI_5.
    # Reversed: Max(4) - 0 + Min(0) = 4.
    rev_col = "Es dificil ver las cosas desde el punto de vista de otros"
    assert df_result[rev_col].iloc[0] == 4.0
    assert df_result[rev_col].iloc[1] == 0.0
    print("✅ Reverse coding applied correctly")
    
    # 4. Check Extra Variable
    assert "Satisfaccion con la cafeteria" in df_result.columns
    print(f"Extra variable type: {df_result['Satisfaccion con la cafeteria'].dtype}")
    print("✅ Extra variable preserved")
    
    # 5. Check Numeric Flexible
    # "10 años" -> 10.0
    # "5,5" -> 5.5
    flex_col = "Antiguedad (años)"
    assert df_result[flex_col].iloc[0] == 10.0
    assert df_result[flex_col].iloc[1] == 5.5
    assert df_result[flex_col].iloc[3] == 2.5
    print("✅ Flexible numeric conversion worked")

if __name__ == "__main__":
    try:
        test_robust_processor()
        print("\n🎉 ALL TESTS PASSED!")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
