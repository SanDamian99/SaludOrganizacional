import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
import pandas as pd
import streamlit as st
from src.ai.gemini_client import GeminiClient

# Mock Streamlit secrets if not present
if not hasattr(st, "secrets"):
    st.secrets = {}

# Ensure API Key is available (mock or env)
# Assuming the environment has the key or the user has it in secrets.toml
# If running in this environment, I might need to rely on the existing secrets.toml or os.environ.

def test_chatbot():
    print("Initializing GeminiClient...")
    client = GeminiClient()
    
    if not client.is_configured():
        print("❌ API Key not configured. Skipping test.")
        return

    print("Creating dummy dataset...")
    # Create a dataset relevant to organizational psychology
    data = {
        "Age": [25, 30, 35, 40, 45, 50, 55, 60],
        "Burnout_Score": [2.5, 3.0, 3.5, 4.0, 4.5, 2.0, 1.5, 3.0],
        "Job_Satisfaction": [4.0, 3.5, 3.0, 2.5, 2.0, 4.5, 5.0, 3.5],
        "Workload": [3.0, 3.5, 4.0, 4.5, 5.0, 2.5, 2.0, 3.5],
        "Department": ["HR", "IT", "Sales", "Sales", "IT", "HR", "HR", "IT"]
    }
    df = pd.DataFrame(data)
    
    # Mock session state for history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    print("\n--- Test 1: Correlation Analysis ---")
    question = "Is there a relationship between Workload and Burnout? Calculate the correlation and explain it using the JD-R model."
    print(f"User: {question}")
    
    response = client.generate_response(question, df_context=df)
    print(f"\nAI Response:\n{response}")
    
    print("\n--- Test 2: Group Comparison ---")
    question = "Which department has the highest Job Satisfaction?"
    print(f"User: {question}")
    
    response = client.generate_response(question, df_context=df)
    print(f"\nAI Response:\n{response}")

if __name__ == "__main__":
    try:
        test_chatbot()
    except Exception as e:
        print(f"\n❌ Error: {e}")
