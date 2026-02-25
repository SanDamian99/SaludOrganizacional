import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from src.ai.gemini_client import GeminiClient
from src.core.config import DATA_DICTIONARY, CHART_CONFIG as CC

# --- Helper Functions ---

def get_dimension_average(df, dim_name):
    """Calculates the average for a dimension based on DATA_DICTIONARY."""
    if "Dimensiones de Bienestar y Salud Mental" not in DATA_DICTIONARY:
        return None, []
    
    dim_config = DATA_DICTIONARY["Dimensiones de Bienestar y Salud Mental"].get(dim_name)
    if not dim_config:
        return None, []
        
    questions = dim_config.get("Preguntas", [])
    # Find columns in df that match these questions
    valid_cols = [c for c in df.columns if c in questions and pd.api.types.is_numeric_dtype(df[c])]
    
    if not valid_cols:
        return None, []
        
    return df[valid_cols].mean(axis=1).mean(), valid_cols

def render_gauge(value, title, min_val=1, max_val=7, color_scale=['red', 'yellow', 'green']):
    """Renders a simple gauge/bar chart."""
    fig = px.bar(x=[value], y=[title], orientation='h', range_x=[min_val, max_val], 
                 color=[value], color_continuous_scale=color_scale)
    fig.update_layout(height=100, margin=dict(l=40, r=30, t=40, b=40), 
                      xaxis=dict(title=f"Escala {min_val}-{max_val}", automargin=True),
                      yaxis=dict(automargin=True),
                      showlegend=False)
    fig.update_traces(texttemplate='%{x:.2f}', textposition='inside')
    return fig

def render_tank(value, left_label, right_label, min_val=1, max_val=7):
    """Renders a 'Tank' style visualization for Semantic Differential."""
    # Normalize value to 0-100 for the tank fill
    pct = (value - min_val) / (max_val - min_val) * 100
    
    fig = go.Figure()
    
    # Background bar (empty tank)
    fig.add_trace(go.Bar(
        x=[max_val], y=[""], orientation='h', 
        marker_color='lightgrey', opacity=0.3, hoverinfo='none'
    ))
    
    # Foreground bar (fill)
    color = 'red' if pct < 33 else 'yellow' if pct < 66 else 'green'
    fig.add_trace(go.Bar(
        x=[value], y=[""], orientation='h',
        marker_color=color, text=f"{value:.2f}", textposition='auto'
    ))
    
    fig.update_layout(
        title=dict(text=f"{left_label} ↔ {right_label}", x=0.5, xanchor='center'),
        xaxis=dict(range=[0, max_val+0.5], showgrid=False, visible=False, automargin=True),
        yaxis=dict(showgrid=False, visible=False, automargin=True),
        height=80,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
        barmode='overlay'
    )
    return fig

def render_likert_distribution(df, cols, title):
    """Renders distribution of responses for a set of Likert columns."""
    # Melt dataframe to get all responses in one column
    melted = df[cols].melt(var_name="Pregunta", value_name="Respuesta")
    
    # Count frequencies
    counts = melted['Respuesta'].value_counts().sort_index()
    
    fig = px.bar(counts, x=counts.index, y=counts.values, 
                 title=f"Distribución: {title}", labels={'x': 'Respuesta', 'y': 'Frecuencia'},
                 color=counts.values, color_continuous_scale='Blues')
    fig.update_layout(
        height=400,  # Increased height for better readability
        margin=dict(l=60, r=40, t=60, b=80),
        xaxis=dict(automargin=True),
        yaxis=dict(automargin=True)
    )
    return fig

# --- Main Dashboard ---

def render_dashboard():
    df = st.session_state.df
    
    if df is None:
        st.info("⚠️ No hay datos cargados. Ve a la sección 'Cargar Datos' para comenzar.")
        return

    st.markdown("## 📊 Dashboard de Salud Organizacional")
    
    # --- Sidebar Filters ---
    with st.sidebar:
        st.subheader("📄 Reporte")
        if st.button("Generar Informe PDF"):
            from src.reports.report_builder import ReportBuilder
            with st.spinner("Generando informe profesional (esto puede tardar unos segundos)..."):
                try:
                    builder = ReportBuilder(df, "SaludOrganizacional_Reporte.pdf")
                    pdf_path = builder.build()
                    
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Descargar Informe PDF",
                            data=f,
                            file_name="SaludOrganizacional_Reporte.pdf",
                            mime="application/pdf"
                        )
                    st.success("✅ Informe generado exitosamente.")
                except Exception as e:
                    st.error(f"Error al generar informe: {e}")
        
        st.divider()
        st.subheader("🔍 Filtros Globales")
        # Filter by a categorical column if exists
        cat_cols = df.select_dtypes(include=['category', 'object']).columns
        if len(cat_cols) > 0:
            filter_col = st.selectbox("Filtrar por:", ["Ninguno"] + list(cat_cols))
            if filter_col != "Ninguno":
                unique_vals = df[filter_col].unique()
                selected_val = st.selectbox(f"Valor de {filter_col}:", unique_vals)
                df = df[df[filter_col] == selected_val]
                st.info(f"Filtrando por {filter_col} = {selected_val} ({len(df)} registros)")

    # --- TABS ---
    tab_socio, tab_labor, tab_dims = st.tabs(["👥 Sociodemográficas", "🏢 Laborales", "🧠 Dimensiones"])

    # --- 1. Sociodemográficas ---
    with tab_socio:
        st.markdown("### Variables Sociodemográficas")
        socio_vars = DATA_DICTIONARY.get("Variables Sociodemográficas", {})
        
        # Grid layout
        cols = st.columns(2)
        for i, (var_name, config) in enumerate(socio_vars.items()):
            # Find actual column name in df (fuzzy match or exact)
            # For now, assume exact match or simple normalization. 
            # In a real scenario, we'd use the map created by processor.
            # Here we try to find the column that contains the var_name
            found_col = next((c for c in df.columns if var_name in c), None)
            
            if found_col:
                with cols[i % 2]:
                    st.markdown(f"**{var_name}**")
                    if pd.api.types.is_numeric_dtype(df[found_col]):
                        st.dataframe(df[found_col].describe().to_frame().T)
                        fig = px.histogram(df, x=found_col, marginal="box")
                    else:
                        counts = df[found_col].value_counts().reset_index()
                        counts.columns = ['Valor', 'Frecuencia']
                        fig = px.bar(counts, x='Valor', y='Frecuencia', color='Frecuencia')
                    
                    fig.update_layout(
                        height=300,
                        margin=dict(l=60, r=40, t=50, b=80),
                        xaxis=dict(automargin=True),
                        yaxis=dict(automargin=True)
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                # Try looking for it without the (SD) prefix
                clean_name = var_name.split(')')[-1]
                found_col = next((c for c in df.columns if clean_name in c), None)
                if found_col:
                     with cols[i % 2]:
                        st.markdown(f"**{var_name}**")
                        counts = df[found_col].value_counts().reset_index()
                        counts.columns = ['Valor', 'Frecuencia']
                        fig = px.bar(counts, x='Valor', y='Frecuencia', color='Frecuencia')
                        fig.update_layout(height=CC['height_default'], margin=CC['margin_compact'],
                                          xaxis=dict(automargin=True), yaxis=dict(automargin=True))
                        st.plotly_chart(fig, use_container_width=True)

    # --- 2. Laborales ---
    with tab_labor:
        st.markdown("### Variables Laborales")
        labor_vars = DATA_DICTIONARY.get("Variables Laborales", {})
        
        cols = st.columns(2)
        for i, (var_name, config) in enumerate(labor_vars.items()):
            found_col = next((c for c in df.columns if var_name in c), None)
            
            if found_col:
                with cols[i % 2]:
                    st.markdown(f"**{var_name}**")
                    if pd.api.types.is_numeric_dtype(df[found_col]):
                        st.dataframe(df[found_col].describe().to_frame().T)
                        fig = px.histogram(df, x=found_col)
                    else:
                        counts = df[found_col].value_counts().reset_index()
                        counts.columns = ['Valor', 'Frecuencia']
                        fig = px.bar(counts, x='Valor', y='Frecuencia', color='Frecuencia')
                    
                    fig.update_layout(height=CC['height_default'], margin=CC['margin_compact'],
                                      xaxis=dict(automargin=True), yaxis=dict(automargin=True))
                    st.plotly_chart(fig, use_container_width=True)

    # --- 3. Dimensiones ---
    with tab_dims:
        st.markdown("### Dimensiones de Bienestar y Salud Mental")
        
        dims = DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {})
        dim_names = list(dims.keys())
        
        selected_dim = st.selectbox("Selecciona una Dimensión para analizar:", dim_names)
        
        if selected_dim:
            st.markdown(f"#### {selected_dim}")
            dim_config = dims[selected_dim]
            questions = dim_config.get("Preguntas", [])
            
            # Find columns
            valid_cols = [c for c in df.columns if c in questions and pd.api.types.is_numeric_dtype(df[c])]
            
            if valid_cols:
                # --- Special Handling for Specific Dimensions ---
                
                # 1. Conflicto Familia-Trabajo (Split)
                if selected_dim == "Conflicto Familia-Trabajo":
                    c1, c2 = st.columns(2)
                    
                    # First 5: Familia -> Trabajo
                    ft_cols = valid_cols[:5]
                    ft_avg = df[ft_cols].mean(axis=1).mean() if ft_cols else 0
                    with c1:
                        st.metric("Familia -> Trabajo", f"{ft_avg:.2f} / 7.0")
                        st.plotly_chart(render_gauge(ft_avg, "Familia -> Trabajo", color_scale=['green', 'yellow', 'red']), use_container_width=True)
                        if ft_cols:
                            st.plotly_chart(render_likert_distribution(df, ft_cols, "Familia -> Trabajo"), use_container_width=True)

                    # Last 5: Trabajo -> Familia
                    tf_cols = valid_cols[5:]
                    tf_avg = df[tf_cols].mean(axis=1).mean() if tf_cols else 0
                    with c2:
                        st.metric("Trabajo -> Familia", f"{tf_avg:.2f} / 7.0")
                        st.plotly_chart(render_gauge(tf_avg, "Trabajo -> Familia", color_scale=['green', 'yellow', 'red']), use_container_width=True)
                        if tf_cols:
                            st.plotly_chart(render_likert_distribution(df, tf_cols, "Trabajo -> Familia"), use_container_width=True)
                            
                # 2. Bienestar Psicosocial (Tanks)
                elif "Bienestar Psicosocial" in selected_dim:
                    # Expect pairs of adjectives. 
                    # The questions in config are like "(BM),(PA)2", etc.
                    # We need to map these to the adjectives if possible, or just show the items.
                    # The user prompt had specific pairs like "Insatisfecho - Satisfecho".
                    # Since we don't have the exact mapping in the config questions list (it just says indices),
                    # we might need to rely on the column names in the CSV if they are descriptive,
                    # OR hardcode the labels if they are fixed.
                    # For now, we'll iterate the valid columns and show a tank for each.
                    
                    st.markdown("##### Escala Diferencial Semántico")
                    for col in valid_cols:
                        val = df[col].mean()
                        # Try to extract label from column name if it has text
                        label = col.split(')')[-1] if ')' in col else col
                        st.plotly_chart(render_tank(val, "Izquierda", "Derecha"), use_container_width=True)
                        st.caption(f"{label}: {val:.2f}")

                # 3. Standard Likert Dimensions
                else:
                    avg = df[valid_cols].mean(axis=1).mean()
                    st.metric("Promedio General", f"{avg:.2f}")
                    
                    st.plotly_chart(render_gauge(avg, selected_dim), use_container_width=True)
                    
                    st.markdown("#### Detalle por Pregunta")
                    for col in valid_cols:
                        st.markdown(f"**{col}**")
                        # Use a unique key or title to distinguish
                        st.plotly_chart(render_likert_distribution(df, [col], col), use_container_width=True)

                    with st.expander("Ver Estadísticas Descriptivas"):
                        stats_df = df[valid_cols].describe().T[['mean', 'std', 'min', 'max']]
                        st.dataframe(stats_df.style.format("{:.2f}"))

                # --- Full Data Table ---
                st.markdown("### 📋 Datos Completos de la Dimensión")
                st.dataframe(df[valid_cols], use_container_width=True)

                # --- AI Interpretation Button ---
                st.markdown("---")
                if st.button(f"✨ Interpretar {selected_dim} con IA"):
                    client = GeminiClient()
                    if not client.is_configured():
                        st.error("⚠️ API Key no configurada.")
                    else:
                        with st.spinner("Generando análisis experto..."):
                            stats_summary = df[valid_cols].describe().to_string()
                            prompt = f"""
                            Actúa como experto en Psicología Organizacional.
                            Analiza la dimensión: {selected_dim}
                            
                            Datos Estadísticos:
                            {stats_summary}
                            
                            1. Describe el estado actual.
                            2. Identifica puntos críticos (preguntas con promedios bajos/altos).
                            3. Sugiere 2 acciones de mejora basadas en evidencia.
                            """
                            response = client.generate_response(prompt, df_context=None)
                            st.markdown(response)
            else:
                st.warning(f"No se encontraron columnas de datos para {selected_dim}")
