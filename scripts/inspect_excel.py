import pandas as pd
import os

file_path = "Resultados Indicadores de Bienestar y Salud Mental en el Mundo del Trabajo.xlsx"

try:
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        print("Columns:")
        print(df.columns.tolist())
        print("\nData Types:")
        print(df.dtypes)
        print("\nFirst 5 rows:")
        print(df.head().to_string())
        
        # Check for Likert-like columns (object type with few unique values)
        print("\nPotential Likert Columns Analysis:")
        for col in df.select_dtypes(include=['object']):
            unique_vals = df[col].unique()
            if len(unique_vals) < 20:
                print(f"Column: {col}")
                print(f"Unique Values ({len(unique_vals)}): {unique_vals}")
    else:
        print(f"File not found: {file_path}")
except Exception as e:
    print(f"Error reading excel: {e}")
