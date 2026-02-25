import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import streamlit as st
from src.ai.gemini_client import GeminiClient

# Mock Streamlit secrets
if not hasattr(st, "secrets"):
    st.secrets = {}

def test_trend_analysis():
    print("Creating dummy trend data...")
    # Create data with a time column
    data = {
        "Year": [2021, 2021, 2022, 2022, 2023, 2023],
        "(BM)Burnout": [3.5, 3.6, 3.8, 3.9, 4.2, 4.3],
        "(BM)Satisfaction": [4.0, 3.9, 3.5, 3.4, 3.0, 2.9]
    }
    df = pd.DataFrame(data)
    
    print("Simulating Trend Analysis Logic...")
    time_col = "Year"
    bm_cols = ["(BM)Burnout", "(BM)Satisfaction"]
    
    # Group by time
    trend_df = df.groupby(time_col)[bm_cols].mean().sort_index()
    print("\nCalculated Trends:")
    print(trend_df)
    
    # Verify calculation
    assert trend_df.loc[2021, "(BM)Burnout"] == 3.55
    assert trend_df.loc[2023, "(BM)Burnout"] == 4.25
    print("✅ Trend calculation correct.")
    
    print("\nTesting AI Interpretation...")
    client = GeminiClient()
    if not client.is_configured():
        print("⚠️ API Key not configured. Skipping AI test.")
        return

    summary_str = trend_df.to_string()
    prompt = f"""
    Actúa como un experto en Psicología Organizacional.
    Analiza las siguientes tendencias temporales:
    {summary_str}
    
    Identifica patrones y da recomendaciones.
    """
    
    response = client.generate_response(prompt, df_context=None)
    print(f"\nAI Response:\n{response}")
    print("✅ AI Interpretation received.")

if __name__ == "__main__":
    try:
        test_trend_analysis()
    except Exception as e:
        print(f"\n❌ Error: {e}")
