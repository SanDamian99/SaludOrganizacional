import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.core.state import get_processed_data
from src.ai.gemini_client import get_gemini_client, GeminiClient

def render_trends():
    st.title("📈 Análisis de Tendencias")
    st.markdown("---")

    df = get_processed_data()
    if df is None or df.empty:
        st.info("Por favor carga datos para ver el análisis de tendencias.")
        return

    # --- 1. Global Trends (if date column exists) ---
    # Attempt to find a date column
    date_cols = [col for col in df.columns if 'fecha' in col.lower() or 'date' in col.lower() or 'tiempo' in col.lower()]
    
    if date_cols:
        date_col = date_cols[0]
        try:
            df[date_col] = pd.to_datetime(df[date_col])
            st.subheader("Evolución Temporal")
            
            # Select numeric columns for trend
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                selected_metric = st.selectbox("Selecciona métrica para ver tendencia:", numeric_cols)
                
                # Group by date (e.g., monthly)
                trend_df = df.groupby(pd.Grouper(key=date_col, freq='M'))[selected_metric].mean().reset_index()
                
                fig = px.line(trend_df, x=date_col, y=selected_metric, title=f"Tendencia de {selected_metric} en el tiempo", markers=True)
                fig.update_layout(
                    template="plotly_white",
                    height=400,
                    margin=dict(l=60, r=40, t=60, b=80),
                    xaxis=dict(automargin=True),
                    yaxis=dict(automargin=True)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No se encontraron columnas numéricas para analizar tendencias temporales.")
        except Exception as e:
            st.error(f"Error procesando fechas: {e}")
    else:
        st.info("No se detectó una columna de fecha para análisis temporal. Mostrando análisis comparativo.")

    # --- 2. Comparative Analysis (Categorical) ---
    st.subheader("Análisis Comparativo por Grupos")
    
    # Identify categorical columns
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    # Filter out likely non-grouping columns (too many unique values)
    group_cols = [c for c in cat_cols if df[c].nunique() < 20]
    
    if group_cols:
        col1, col2 = st.columns(2)
        with col1:
            group_by_col = st.selectbox("Agrupar por:", group_cols)
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            with col2:
                metric_col = st.selectbox("Métrica a comparar:", numeric_cols)
            
            # Bar chart
            avg_df = df.groupby(group_by_col)[metric_col].mean().reset_index().sort_values(by=metric_col, ascending=False)
            
            fig_bar = px.bar(avg_df, x=group_by_col, y=metric_col, color=metric_col, 
                             title=f"Promedio de {metric_col} por {group_by_col}",
                             color_continuous_scale="Viridis")
            fig_bar.update_layout(
                template="plotly_white",
                height=450,
                margin=dict(l=60, r=40, t=60, b=100),
                xaxis=dict(tickangle=-45, automargin=True),
                yaxis=dict(automargin=True)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Box plot for distribution
            st.markdown("#### Distribución Detallada")
            fig_box = px.box(df, x=group_by_col, y=metric_col, color=group_by_col,
                             title=f"Distribución de {metric_col} por {group_by_col}")
            fig_box.update_layout(
                template="plotly_white",
                height=450,
                margin=dict(l=60, r=40, t=60, b=100),
                xaxis=dict(tickangle=-45, automargin=True),
                yaxis=dict(automargin=True)
            )
            st.plotly_chart(fig_box, use_container_width=True)

            # --- AI Interpretation ---
            st.markdown("### 🤖 Interpretación IA")
            if st.button("Generar Análisis Prospectivo"):
                with st.spinner("Analizando tendencias..."):
                    try:
                        client = get_gemini_client()
                        if client:
                            # Prepare summary data for AI
                            summary_stats = df.groupby(group_by_col)[metric_col].describe().to_markdown()
                            prompt = f"""
                            Actúa como un experto en psicología organizacional y análisis de datos.
                            Analiza los siguientes datos estadísticos sobre '{metric_col}' agrupados por '{group_by_col}':
                            
                            {summary_stats}
                            
                            Por favor, proporciona:
                            1. Un análisis de las tendencias observadas.
                            2. Identificación de grupos de riesgo o fortalezas.
                            3. Recomendaciones prospectivas para la toma de decisiones en la empresa.
                            
                            Sé claro, profesional y directo.
                            """
                            
                            response = client.generate_response(prompt)
                            st.markdown(response)
                        else:
                            st.error("No se pudo conectar con el servicio de IA.")
                    except Exception as e:
                        st.error(f"Error generando análisis: {e}")

    else:
        st.warning("No se encontraron columnas categóricas adecuadas para agrupar.")
