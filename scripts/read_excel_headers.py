import pandas as pd

file_path = "Resultados Indicadores de Bienestar y Salud Mental en el Mundo del Trabajo.xlsx"
try:
    df = pd.read_excel(file_path, nrows=5)
    print("Excel Headers:")
    for col in df.columns:
        print(col)
except Exception as e:
    print(f"Error reading Excel: {e}")
