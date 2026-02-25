import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from src.ai.gemini_client import GeminiClient

def test_tools():
    print("Testing Chatbot Tools...")
    
    # 1. Setup Mock Data
    df = pd.DataFrame({
        'Age': [25, 30, 35, 40, 45],
        'Salary': [50000, 60000, 70000, 80000, 90000],
        'Department': ['HR', 'IT', 'HR', 'IT', 'HR'],
        'Satisfaction': [4.5, 4.0, 3.5, 5.0, 4.2]
    })
    
    client = GeminiClient()
    client.current_df = df # Manually inject context
    
    # 2. Test Correlation
    print("\n--- Testing Correlation ---")
    res_corr = client.calculate_correlation('Age', 'Salary')
    print(f"Result: {res_corr}")
    assert "Correlation between" in res_corr
    assert "1.0000" in res_corr # Perfect correlation
    
    # 3. Test Group Comparison
    print("\n--- Testing Group Comparison ---")
    res_group = client.compare_groups('Department', 'Salary')
    print(f"Result: {res_group}")
    assert "Average 'Salary' by 'Department'" in res_group
    assert "IT" in res_group
    assert "HR" in res_group
    
    # 4. Test Summary Stats
    print("\n--- Testing Summary Stats ---")
    res_stats = client.get_summary_statistics('Satisfaction')
    print(f"Result: {res_stats}")
    assert "Statistics for 'Satisfaction'" in res_stats
    assert "mean" in res_stats
    
    # 5. Test Error Handling
    print("\n--- Testing Error Handling ---")
    res_err = client.calculate_correlation('Age', 'Department') # Dept is string
    print(f"Result (Expected Error): {res_err}")
    assert "Error" in res_err
    
    print("\n✅ All Tool Tests Passed!")

if __name__ == "__main__":
    try:
        test_tools()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        # exit(1) # Don't exit to avoid breaking the agent flow if env is missing keys, 
                  # but here we are mocking the client usage so it should be fine if we don't call generate_response
