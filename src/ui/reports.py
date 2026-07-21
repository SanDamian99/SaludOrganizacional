"""
UI de generación de informes PDF.
Usa ReportBuilder para crear el documento con estructura narrativa completa.
"""
import streamlit as st
import pandas as pd
from src.reports.report_builder import ReportBuilder
from src.reports.indicator_report import IndicatorReportBuilder
from src.analysis import indicators


def render_reports_page():
    st.header("📄 Generador de Informes")

    # --- Data Selection ---
    st.sidebar.subheader("Configuración del Informe")
    data_source = st.sidebar.radio(
        "Fuente de Datos",
        ["Datos Cargados (Dashboard)", "Archivo Nuevo"]
    )

    df_report = None

    if data_source == "Datos Cargados (Dashboard)":
        if 'df' in st.session_state and st.session_state.df is not None:
            df_report = st.session_state.df
            st.success(f"✅ Usando datos activos: **{len(df_report):,} registros.**")
        else:
            st.warning(
                "⚠️ No hay datos cargados. Ve a 'Cargar Datos' o selecciona "
                "'Archivo Nuevo' en la barra lateral."
            )
    else:
        uploaded_file = st.sidebar.file_uploader(
            "Subir Excel/CSV para Informe", type=["xlsx", "xls", "csv"]
        )
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_report = pd.read_csv(uploaded_file)
                else:
                    df_report = pd.read_excel(uploaded_file)
                st.success(f"Archivo cargado: {len(df_report):,} registros.")
            except Exception as e:
                st.error(f"Error al cargar archivo: {e}")

    if df_report is None:
        return

    # --- Optional Filters ---
    try:
        from src.ui.components.filtering import render_filtering_sidebar
        df_filtered = render_filtering_sidebar(df_report)
    except (ImportError, Exception):
        df_filtered = df_report

    # Date filter
    if 'Hora de inicio' in df_filtered.columns:
        df_filtered['Hora de inicio'] = pd.to_datetime(
            df_filtered['Hora de inicio'], errors='coerce'
        )
        if df_filtered['Hora de inicio'].notna().any():
            min_date = df_filtered['Hora de inicio'].min().date()
            max_date = df_filtered['Hora de inicio'].max().date()
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 📅 Rango de Fechas")
            start_date = st.sidebar.date_input("Fecha Inicio", min_date)
            end_date = st.sidebar.date_input("Fecha Fin", max_date)
            mask = (
                (df_filtered['Hora de inicio'].dt.date >= start_date) &
                (df_filtered['Hora de inicio'].dt.date <= end_date)
            )
            df_filtered = df_filtered[mask].copy()
            st.sidebar.info(f"Tras fecha: {len(df_filtered):,}")

    # --- Report Config ---
    st.sidebar.markdown("---")
    org_name = st.sidebar.text_input(
        "Nombre de la Organización", "Organización"
    )
    report_title = st.sidebar.text_input(
        "Título del Informe", "Informe de Diagnóstico de Bienestar"
    )
    include_annex = st.sidebar.checkbox(
        "Incluir anexo técnico/académico (α, tablas)", value=True
    )

    # --- Generate Report ---
    if st.button("🚀 Generar Informe General PDF"):
        if df_filtered.empty:
            st.error("El conjunto de datos filtrado está vacío.")
            return

        with st.spinner("⏳ Analizando datos y generando PDF profesional..."):
            try:
                if indicators.is_wellbeing_dataset(df_filtered):
                    builder = ReportBuilder(
                        df_filtered,
                        title=report_title,
                        org_name=org_name,
                        include_academic_annex=include_annex,
                    )
                    file_name = "informe_bienestar.pdf"
                else:
                    # Dataset genérico (p. ej. docentes): informe de indicadores
                    doc_title = (report_title
                                 if report_title != "Informe de Diagnóstico de Bienestar"
                                 else "Informe de Salud Mental y Bienestar Docente")
                    builder = IndicatorReportBuilder(
                        df_filtered, title=doc_title, org_name=org_name)
                    file_name = "informe_salud_mental_docente.pdf"
                pdf_bytes = builder.build_report()

                if pdf_bytes and len(pdf_bytes) > 1000:
                    st.success(
                        f"✅ Informe generado exitosamente "
                        f"({len(pdf_bytes) / 1024:.0f} KB)"
                    )
                    st.download_button(
                        "📥 Descargar PDF",
                        data=pdf_bytes,
                        file_name=file_name,
                        mime="application/pdf",
                    )
                else:
                    st.error("El PDF generado está vacío o es demasiado pequeño.")

            except Exception as e:
                st.error(f"Error generando el informe: {e}")
                if st.session_state.get("debug_mode", False):
                    st.exception(e)
