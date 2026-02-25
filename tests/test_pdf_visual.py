"""
Test visual del reporte PDF.
Genera un PDF con datos ficticios para verificación.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

np.random.seed(42)
n = 100

test_df = pd.DataFrame({
    "(SD)Edad": np.random.randint(22, 60, n),
    "(SD)Sexo": np.random.choice(["Hombre", "Mujer"], n),
    "(BM),(SB)Burnout_1": np.random.randint(1, 8, n),
    "(BM),(SB)Burnout_2": np.random.randint(1, 8, n),
    "(BM),(CT)Compromiso_1": np.random.randint(1, 8, n),
    "(BM),(CT)Compromiso_2": np.random.randint(4, 8, n),  # Sesgo alto = fortaleza
    "(BM),(CL)Clima_1": np.random.randint(1, 4, n),       # Sesgo bajo = riesgo
    "(BM),(CL)Clima_2": np.random.randint(1, 5, n),
    "(BM),(AG)Agotamiento_1": np.random.randint(2, 7, n),
    "(BM),(AG)Agotamiento_2": np.random.randint(3, 7, n),
})

print("Generando PDF de prueba...")
from src.reports.report_builder import ReportBuilder

builder = ReportBuilder(test_df)
pdf_bytes = builder.build_report(
    title="Informe de Prueba Visual",
    org_name="Empresa de Prueba S.A.",
)

assert len(pdf_bytes) > 5_000, f"PDF demasiado pequeno: {len(pdf_bytes)} bytes"

output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_output.pdf")
with open(output_path, "wb") as f:
    f.write(pdf_bytes)

print(f"✅ PDF generado: {output_path}")
print(f"   Tamaño: {len(pdf_bytes) / 1024:.0f} KB")
