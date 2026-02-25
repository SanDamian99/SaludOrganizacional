import streamlit as st
from src.data.supabase_client import SupabaseManager

def render_social():
    st.markdown("## 🌐 Feed de Conocimiento")
    st.info("Esta sección permitirá compartir hallazgos con el equipo.")
    
    supabase = SupabaseManager()
    
    if not supabase.is_connected():
        st.warning("⚠️ Conecta Supabase para ver los análisis compartidos.")
        return

    # Placeholder for future implementation
    st.write("### Análisis Públicos Recientes")
    
    datasets = supabase.get_public_datasets()
    if datasets:
        for file in datasets:
            st.write(f"📄 {file['name']}")
    else:
        st.write("No hay datasets públicos disponibles aún.")
