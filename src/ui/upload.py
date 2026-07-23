"""
UI de carga y procesamiento de archivos.
Incluye hash SHA256 para idempotencia y reporte visual de ingesta.
"""
import streamlit as st
import pandas as pd
import hashlib
from src.data.processor import DataCleaner
from src.core.state import save_new_dataset


def render_upload():
    st.markdown("## 📂 Cargar y Procesar Datos")

    uploaded_file = st.file_uploader("Sube tu archivo CSV o Excel", type=["csv", "xlsx"])

    if uploaded_file:
        st.write("### Vista Previa de Datos Originales")
        try:
            preview_df = (
                pd.read_csv(uploaded_file, nrows=5)
                if uploaded_file.name.endswith('.csv')
                else pd.read_excel(uploaded_file, nrows=5)
            )
            st.dataframe(preview_df)
            uploaded_file.seek(0)
        except Exception:
            st.warning("No se pudo generar la vista previa rápida.")
            uploaded_file.seek(0)

        if st.button("Procesar y Cargar"):
            # Calcular hash del archivo para idempotencia
            file_bytes = uploaded_file.getvalue()
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # Si es el mismo archivo, no reprocesar
            if st.session_state.get("current_file_hash") == file_hash:
                st.info("ℹ️ Este archivo ya está cargado. No es necesario reprocesar.")
                return

            cleaner = DataCleaner()

            with st.spinner("Procesando datos bajo política zero-data loss..."):
                try:
                    df_clean, report = cleaner.process_file(uploaded_file)

                    if report["success"]:
                        # Guardar con limpieza de estado previo
                        save_new_dataset(df_clean, report, file_hash)

                        st.success(
                            f"✅ Archivo cargado: {report['n_rows_final']:,} filas, "
                            f"{report['n_cols_original']} columnas"
                        )

                        # Reporte visual de ingesta
                        with st.expander("📋 Ver diagnóstico de ingesta", expanded=False):
                            from src.analysis import indicators
                            extras = report.get("unmapped_columns", [])
                            inds, scales, unknown = indicators.classify_columns(df_clean, extras)
                            n_rec = len(inds) + len(scales)

                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Filas", report["n_rows_final"])
                            c2.metric("Mapeadas (esquema)", report.get("n_cols_mapped", "N/A"))
                            c3.metric("Indicadores/escalas", n_rec)
                            c4.metric("Celdas imputadas", report["n_cells_imputed"])

                            if n_rec:
                                st.success(
                                    f"✅ {n_rec} columnas reconocidas como indicadores o ítems "
                                    f"de escala, listas para el análisis."
                                )
                            if unknown:
                                st.warning(
                                    f"⚠️ {len(unknown)} columnas no reconocidas (se conservan igual): "
                                    f"{', '.join(str(c) for c in unknown[:10])}"
                                    + (" …" if len(unknown) > 10 else "")
                                )

                        # Upload to Supabase (Optional)
                        try:
                            from src.data.supabase_client import SupabaseManager
                            supabase = SupabaseManager()
                            if supabase.is_connected():
                                uploaded_file.seek(0)
                                res_storage = supabase.upload_file(uploaded_file, uploaded_file.name)
                                if "error" not in res_storage:
                                    st.success("☁️ Respaldo guardado en Supabase Storage.")
                                else:
                                    st.warning(f"No se pudo guardar en Supabase: {res_storage['error']}")
                            else:
                                st.info("ℹ️ Sin conexión a Supabase. Datos temporales en sesión.")
                        except ImportError:
                            st.info("ℹ️ Supabase no configurado. Datos temporales en sesión.")

                    else:
                        st.error("❌ No se pudo procesar el archivo.")
                        for w in report.get("warnings", []):
                            st.warning(w)

                except Exception as e:
                    st.error(f"Error procesando el archivo: {e}")
                    if st.session_state.get("debug_mode", False):
                        import traceback
                        st.code(traceback.format_exc())
