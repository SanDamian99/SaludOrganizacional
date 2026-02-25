import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import plotly.graph_objects as go
from src.ui.dashboard import render_gauge, render_tank, get_dimension_average
from src.core.config import DATA_DICTIONARY

def test_deep_dashboard_logic():
    print("--- Testing Deep Dashboard Logic ---")
    
    # 1. Test Gauge Renderer
    print("\nTesting Gauge Renderer...")
    fig = render_gauge(5.5, "Test Gauge")
    assert isinstance(fig, go.Figure)
    print("✅ Gauge Figure created.")
    
    # 2. Test Tank Renderer
    print("\nTesting Tank Renderer...")
    fig = render_tank(3.5, "Left", "Right")
    assert isinstance(fig, go.Figure)
    # Check traces
    assert len(fig.data) == 2 # Background + Foreground
    print("✅ Tank Figure created with correct traces.")
    
    # 3. Test Family-Work Split Logic (Simulation)
    print("\nTesting Family-Work Split Logic...")
    # Mock Data
    ft_dim = DATA_DICTIONARY["Dimensiones de Bienestar y Salud Mental"]["Conflicto Familia-Trabajo"]
    questions = ft_dim["Preguntas"]
    
    data = {q: [i % 7 + 1 for i in range(5)] for q in questions}
    df = pd.DataFrame(data)
    
    # Get all cols
    _, valid_cols = get_dimension_average(df, "Conflicto Familia-Trabajo")
    
    # Split
    ft_cols = valid_cols[:5]
    tf_cols = valid_cols[5:]
    
    print(f"Total Questions: {len(questions)}")
    print(f"Found Columns: {len(valid_cols)}")
    print(f"Family->Work Cols: {len(ft_cols)}")
    print(f"Work->Family Cols: {len(tf_cols)}")
    
    assert len(ft_cols) == 5
    assert len(tf_cols) == 5
    print("✅ Family-Work split correct.")

if __name__ == "__main__":
    try:
        test_deep_dashboard_logic()
    except Exception as e:
        print(f"\n❌ Error: {e}")
