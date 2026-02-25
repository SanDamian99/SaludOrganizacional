import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from src.ui.dashboard import get_dimension_average
from src.core.config import DATA_DICTIONARY

def test_dashboard_mapping():
    print("--- Testing Dashboard Mapping Logic ---")
    
    # 1. Setup Mock Data based on Dictionary
    data = {}
    
    # Burnout Questions
    burnout_dim = DATA_DICTIONARY["Dimensiones de Bienestar y Salud Mental"]["Síntomas de Burnout"]
    burnout_qs = burnout_dim["Preguntas"]
    print(f"Burnout Questions defined: {len(burnout_qs)}")
    
    # Add to data with known values (e.g., all 4s)
    for q in burnout_qs:
        data[q] = [4, 4, 4, 4, 4]
        
    # Satisfaction Questions
    sat_dim = DATA_DICTIONARY["Dimensiones de Bienestar y Salud Mental"]["Satisfacción"]
    sat_qs = sat_dim["Preguntas"]
    print(f"Satisfaction Questions defined: {len(sat_qs)}")
    
    for q in sat_qs:
        data[q] = [5, 5, 5, 5, 5]
        
    # Add some random extra column
    data["Extra_Col"] = [1, 2, 3, 4, 5]
    
    df = pd.DataFrame(data)
    print(f"Created Mock DataFrame with {len(df.columns)} columns.")
    
    # 2. Test get_dimension_average for Burnout
    print("\nTesting 'Síntomas de Burnout'...")
    avg, cols = get_dimension_average(df, "Síntomas de Burnout")
    
    print(f"Average: {avg}")
    print(f"Columns Found: {len(cols)}")
    
    assert avg == 4.0, f"Expected average 4.0, got {avg}"
    assert len(cols) == len(burnout_qs), f"Expected {len(burnout_qs)} columns, got {len(cols)}"
    print("✅ Burnout mapping passed.")
    
    # 3. Test get_dimension_average for Satisfaction
    print("\nTesting 'Satisfacción'...")
    avg, cols = get_dimension_average(df, "Satisfacción")
    
    print(f"Average: {avg}")
    print(f"Columns Found: {len(cols)}")
    
    assert avg == 5.0, f"Expected average 5.0, got {avg}"
    assert len(cols) == len(sat_qs), f"Expected {len(sat_qs)} columns, got {len(cols)}"
    print("✅ Satisfaction mapping passed.")
    
    # 4. Test missing dimension
    print("\nTesting Non-Existent Dimension...")
    avg, cols = get_dimension_average(df, "NonExistent")
    assert avg is None
    print("✅ Missing dimension handled correctly.")

if __name__ == "__main__":
    try:
        test_dashboard_mapping()
    except Exception as e:
        print(f"\n❌ Error: {e}")
