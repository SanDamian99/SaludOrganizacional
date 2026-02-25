import pandas as pd
import numpy as np
import io
import os

class DataPreprocessor:
    def __init__(self):
        # Mapping from Excel headers to cleaned_data.csv headers
        # This is a best-effort mapping based on the inspection. 
        # You may need to adjust keys if the Excel headers change slightly.
        self.column_mapping = {
            'ID': 'ID',
            'Hora de inicio': 'Hora de inicio',
            'Hora de finalización': 'Hora de finalización',
            'Correo electrónico': 'Correo electrónico',
            'Nombre': 'Nombre',
            'Edad': '(SD)Edad',
            'Sexo': '(SD)Sexo',
            'Estado Civil': '(SD)Estado Civil',
            'Numero de hijos': '(SD)Numero de hijos',
            'Nivel Educativo': '(SD)Nivel Educativo',
            'Zona de vivienda': '(SD)Zona de vivienda',
            'Departamento': '(SD)Departamento\xa0', # Note the non-breaking space if present in target
            'Ciudad /Municipio': '(SD)Ciudad /Municipio',
            'Estrato Socioeconómico': '(SD)Estrato Socioeconómico',
            'Sector Económico': '(LB)Sector Económico\xa0',
            'Sector empresa': '(LB)Sector empresa',
            'Tamaño Empresa': '(LB)Tamaño Empresa',
            'Trabajo por turnos': '(LB)Trabajo por turnos',
            'Tipo de Contrato': '(LB)Tipo de Contrato',
            'Número de horas de trabajo semanal': '(LB)Número de horas de trabajo semanal\xa0',
            'Ingreso salarial mensual': '(LB)Ingreso salarial mensual\xa0',
            'Cargo': '(LB)Cargo',
            'Personas a cargo en la empresa': '(LB)Personas a cargo en la empresa',
            'Años de experiencia laboral': '(LB)Años de experiencia laboral',
            'Antigüedad en el cargo/labor actual': '(LB)Antigüedad en el cargo/labor actual\xa0',
            'Tipo de modalidad de trabajo': '(LB)Tipo de modalidad de trabajo',
            'Tiempo promedio de traslado al trabajo/casa al día': '(LB)Tiempo promedio de traslado al trabajo/casa al día\xa0',
            'Horas de formación recibidas (ultimo año)': '(LB)Horas de formación recibidas (ultimo año)',
            # Add more mappings for the Likert scale questions as needed
            # The strategy here is to normalize known columns and keep others as is or map them if they match strictly
        }

        self.likert_map = {
            'Nunca': 0,
            'Casi nunca': 1, # Assuming standard scale, verify if 'Raramente' maps here
            'Raramente': 1,
            'Ocasionalmente': 2,
            'Algunas veces': 3,
            'Frecuentemente': 4,
            'Casi siempre': 5,
            'Siempre': 6
        }

    def load_raw_file(self, file_path):
        """Loads the raw Excel file."""
        try:
            # Using openpyxl engine for xlsx
            df = pd.read_excel(file_path, engine='openpyxl')
            return df
        except Exception as e:
            print(f"Error loading file: {e}")
            return None

    def normalize_columns(self, df):
        """Renames columns to match the target schema."""
        # Normalize source columns (strip whitespace)
        df.columns = df.columns.str.strip()
        
        # Rename using the mapping
        # We use a flexible rename that doesn't fail if a column is missing, 
        # but we should log warnings in a real app.
        df = df.rename(columns=self.column_mapping)
        
        return df

    def clean_data(self, df):
        """Performs data cleaning and transformation."""
        # Example: Convert Likert scales if they are in text format
        # This iterates over all columns and applies mapping if the values look like Likert scales
        # A safer approach is to target specific columns if known.
        
        for col in df.columns:
            # Check if column contains string values that match our Likert keys
            if df[col].dtype == 'object':
                unique_vals = set(df[col].dropna().unique())
                # If intersection with likert keys is significant, try mapping
                if len(unique_vals.intersection(self.likert_map.keys())) > 0:
                    # Apply mapping, keeping original if not found (or coerce to NaN)
                    # Using replace for specific values
                    df[col] = df[col].replace(self.likert_map)
        
        # Handle numeric conversions for specific columns if needed
        # e.g., ensure 'Edad' is numeric
        if '(SD)Edad' in df.columns:
            df['(SD)Edad'] = pd.to_numeric(df['(SD)Edad'], errors='coerce')

        return df

    def process_file(self, file_path, output_path=None):
        """Main pipeline execution."""
        print(f"Processing {file_path}...")
        df = self.load_raw_file(file_path)
        if df is not None:
            df = self.normalize_columns(df)
            df = self.clean_data(df)
            
            if output_path:
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                print(f"Saved processed data to {output_path}")
            
            return df
        return None

if __name__ == "__main__":
    # Test run
    preprocessor = DataPreprocessor()
    # Assuming the file is in the current directory
    input_file = "Resultados Indicadores de Bienestar y Salud Mental en el Mundo del Trabajo (3).xlsx"
    if os.path.exists(input_file):
        preprocessor.process_file(input_file, "processed_output_test.csv")
    else:
        print(f"File {input_file} not found.")
