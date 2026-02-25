import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from src.reports.analytics import ReportAnalytics
from src.reports.pdf_generator import PDFReport

# Dummy Data for tests
data = {
    "ID": range(1, 101),
    "Agotamiento": [3.5] * 100,
    "Liderazgo": [4.2] * 100,
    "Engagement": [4.8] * 100,
    "Sexo": ["M"] * 50 + ["F"] * 50
}
df = pd.DataFrame(data)

def run_pdf_test():
    try:
        analytics = ReportAnalytics(df)
        promedios = analytics.calculate_averages()
        fortalezas, riesgos, intermedios, sin_datos = analytics.classify_dimensions(promedios)
        
        # Test AI Analysis with RAG
        print("Consultando a Gemini...")
        ai_response = analytics.generate_ai_analysis(promedios, fortalezas, riesgos)
        print("Prompt exitoso con RAG.")
        
        # Generator
        pdf = PDFReport("test_render_report.pdf")
        pdf.add_title("Reporte de Prueba RAG en PDF")
        pdf.add_markdown(ai_response)
        
        if pdf.build_pdf():
             print("PDF test_render_report.pdf generado exitosamente!")
        else:
             print("Falla en la construcción del PDF.")
    except Exception as e:
        print(f"Error generando PDF: {e}")
        
if __name__ == "__main__":
    run_pdf_test()
