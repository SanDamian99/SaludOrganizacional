import streamlit as st
import pandas as pd
from src.core.config import DATA_DICTIONARY

def render_filtering_sidebar(df):
    """
    Renders a filtering sidebar/expander and returns the filtered DataFrame.
    """
    st.sidebar.markdown("### 🔍 Filtros Avanzados")
    
    df_filtered = df.copy()
    
    # 1. Identify Filterable Columns from Dictionary
    # We prioritize "Variables Laborales" and "Variables Sociodemográficas"
    priority_filters = []
    
    if "Variables Laborales" in DATA_DICTIONARY:
        for k, v in DATA_DICTIONARY["Variables Laborales"].items():
            if v.get("Tipo") == "Categórica":
                priority_filters.append(k)
                
    if "Variables Sociodemográficas" in DATA_DICTIONARY:
        for k, v in DATA_DICTIONARY["Variables Sociodemográficas"].items():
            if v.get("Tipo") == "Categórica":
                priority_filters.append(k)
    
    # Clean keys (remove prefixes for display if needed, but keep for matching)
    # We need to find the actual column name in the DF that matches the dictionary key
    
    active_filters = {}
    
    with st.sidebar.expander("Seleccionar Filtros", expanded=True):
        # Iterate through priority filters and check if they exist in DF
        for key in priority_filters:
            # Try exact match
            col_name = None
            if key in df.columns:
                col_name = key
            else:
                # Try fuzzy/stripped match
                for c in df.columns:
                    if key.strip() in c or c in key: # Simple containment check
                        col_name = c
                        break
            
            if col_name:
                # Get unique values
                unique_vals = df[col_name].dropna().unique().tolist()
                if len(unique_vals) > 1 and len(unique_vals) < 50: # Reasonable limit for dropdown
                    selected = st.multiselect(
                        f"Filtrar por {key.split(')')[-1].strip()}",
                        options=unique_vals,
                        default=[],
                        key=f"filter_{col_name}"
                    )
                    if selected:
                        active_filters[col_name] = selected

    # Apply Filters
    for col, values in active_filters.items():
        df_filtered = df_filtered[df_filtered[col].isin(values)]
        
    # Show stats
    if len(df_filtered) != len(df):
        st.sidebar.info(f"Registros filtrados: {len(df_filtered)} / {len(df)}")
    else:
        st.sidebar.text(f"Total registros: {len(df)}")
        
    return df_filtered
