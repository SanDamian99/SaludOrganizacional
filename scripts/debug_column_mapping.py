import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from src.core.config import DATA_DICTIONARY

def verify_mapping_logic():
    print("--- Verifying Column Mapping Logic ---")
    
    # Simulate DataFrame columns based on Dictionary
    mock_columns = []
    for cat, dims in DATA_DICTIONARY.items():
        if cat == "Dimensiones de Bienestar y Salud Mental":
            for dim_name, details in dims.items():
                if "Preguntas" in details:
                    mock_columns.extend(details["Preguntas"])
    
    print(f"Mock DataFrame has {len(mock_columns)} columns.")
    
    # Simulate the Dashboard's current (failing) logic
    print("\n1. Testing Current Dashboard Logic (Expected to FAIL):")
    burnout_cols_current = [c for c in mock_columns if "Síntomas de Burnout" in c]
    print(f"Found 'Síntomas de Burnout' cols: {len(burnout_cols_current)}")
    
    # Proposed Fix Logic
    print("\n2. Testing Proposed Fix Logic:")
    dim_name = "Síntomas de Burnout"
    target_questions = DATA_DICTIONARY["Dimensiones de Bienestar y Salud Mental"][dim_name]["Preguntas"]
    
    # Find these exact columns in the dataframe
    found_cols = [c for c in mock_columns if c in target_questions]
    print(f"Looking for dimension: '{dim_name}'")
    print(f"Defined questions: {len(target_questions)}")
    print(f"Found columns in DF: {len(found_cols)}")
    
    if len(found_cols) > 0:
        print("✅ SUCCESS: Found columns using Dictionary mapping.")
    else:
        print("❌ FAILURE: Could not find columns even with Dictionary mapping.")

if __name__ == "__main__":
    verify_mapping_logic()
