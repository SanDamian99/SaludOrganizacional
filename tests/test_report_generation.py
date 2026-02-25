import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import os
from src.reports.report_builder import ReportBuilder
from src.core.config import DATA_DICTIONARY

def test_report_generation():
    print("--- Testing Report Generation ---")
    
    # 1. Create Mock Data
    data = {
        "Edad": [25, 30, 35, 40, 45],
        "Sexo": ["Hombre", "Mujer", "Hombre", "Mujer", "Hombre"],
    }
    
    # Add dimension data
    burnout_dim = DATA_DICTIONARY["Dimensiones de Bienestar y Salud Mental"]["Síntomas de Burnout"]
    for q in burnout_dim["Preguntas"]:
        data[q] = [3, 4, 3, 5, 2]
        
    df = pd.DataFrame(data)
    print(f"Mock DataFrame created: {df.shape}")
    
    # 2. Initialize Builder
    output_pdf = "test_report.pdf"
    if os.path.exists(output_pdf):
        os.remove(output_pdf)
        
    builder = ReportBuilder(df, output_pdf)
    
    # 3. Build Report
    print("Building PDF...")
    try:
        builder.build()
        if os.path.exists(output_pdf):
            print(f"✅ PDF generated successfully: {output_pdf}")
            print(f"Size: {os.path.getsize(output_pdf)} bytes")
        else:
            print("❌ PDF file not found after build.")
    except Exception as e:
        print(f"❌ Error building PDF: {e}")

if __name__ == "__main__":
    test_report_generation()
