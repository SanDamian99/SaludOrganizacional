"""
UI de carga y procesamiento de archivos.
Incluye hash SHA256 para idempotencia, reporte visual de ingesta y, cuando el
despliegue tiene las credenciales de carga, el guardado de la versión en el
almacén de Supabase para que sobreviva al reinicio.
"""
import io
import hashlib

import pandas as pd
import streamlit as st

from src.data.processor import DataCleaner
from src.core.state import save_new_dataset
from src.data import almacen


def _leer_crudo(file_bytes: bytes, nombre: str) -> pd.DataFrame:
    """El archivo tal cual llegó, sin procesar.

    Es lo que se guarda en el almacén: al arrancar, la app vuelve a pasar la
    versión por el mismo pipeline que un archivo local, así que guardar el
    procesado lo procesaría dos veces.
    """
    if nombre.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(file_bytes))
    for enc in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(file_bytes), encoding_errors="replace")


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
            else:
                _procesar(uploaded_file, file_bytes, file_hash)

    # Fuera del botón: los clics de «Guardar» y «Activar» son reruns nuevos en los
    # que el botón de procesar ya no está pulsado, y el bloque tiene que seguir ahí.
    _render_almacen()


def _procesar(uploaded_file, file_bytes: bytes, file_hash: str):
    cleaner = DataCleaner()

    with st.spinner("Procesando datos bajo política zero-data loss..."):
        try:
            df_clean, report = cleaner.process_file(uploaded_file)

            if report["success"]:
                # Guardar con limpieza de estado previo
                save_new_dataset(df_clean, report, file_hash)
                try:
                    st.session_state["_archivo_crudo"] = _leer_crudo(file_bytes, uploaded_file.name)
                    st.session_state["_archivo_crudo_nombre"] = uploaded_file.name
                except Exception as e:                      # noqa: BLE001
                    st.session_state.pop("_archivo_crudo", None)
                    st.warning(f"El archivo se cargó en la sesión pero no se podrá guardar "
                               f"como versión: {e}")

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

                if not almacen.disponible():
                    st.info(
                        "ℹ️ La carga queda solo en esta sesión y se pierde al reiniciar. "
                        "El guardado permanente requiere las credenciales de carga del "
                        "despliegue privado (OBS360_CARGA_EMAIL / OBS360_CARGA_CLAVE)."
                    )

            else:
                st.error("❌ No se pudo procesar el archivo.")
                for w in report.get("warnings", []):
                    st.warning(w)

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")
            if st.session_state.get("debug_mode", False):
                import traceback
                st.code(traceback.format_exc())


def _render_almacen():
    """Guardar la carga actual como versión y volver a una anterior."""
    if not almacen.disponible():
        return

    st.markdown("---")
    st.markdown("### ☁️ Versiones en Supabase")

    crudo = st.session_state.get("_archivo_crudo")
    if crudo is not None:
        st.markdown("#### Guardar como nueva versión")
        st.caption(
            f"Archivo en sesión: **{st.session_state.get('_archivo_crudo_nombre', '?')}** "
            f"({len(crudo):,} filas). Las columnas que identifican personas se retiran "
            f"antes de guardar."
        )
        c1, c2 = st.columns([1, 3])
        conjunto = c1.selectbox("Conjunto", list(almacen.CONJUNTOS), key="almacen_conjunto")
        notas = c2.text_input("Notas de la versión", key="almacen_notas",
                              placeholder="p. ej. corte septiembre 2026, se corrigió el colegio X")
        if st.button("Guardar en Supabase y activar", type="primary"):
            try:
                with st.spinner("Subiendo a Storage y registrando la versión…"):
                    fila = almacen.Almacen().subir_version(
                        conjunto, crudo,
                        st.session_state.get("_archivo_crudo_nombre", "archivo"),
                        notas=notas,
                    )
                # El arranque y el selector cachean la versión activa: hay que
                # invalidar para que la próxima sesión vea la nueva.
                st.cache_data.clear()
                retiradas = fila.get("columnas_retiradas") or []
                st.success(
                    f"✅ Versión guardada y activada: {fila.get('filas', '?'):,} filas, "
                    f"{fila.get('columnas', '?')} columnas → `{fila.get('ruta', '')}`"
                )
                if retiradas:
                    st.info("Se retiraron antes de guardar: "
                            + ", ".join(str(c) for c in retiradas))
                else:
                    st.info("No había columnas de identificación que retirar.")
            except (almacen.AlmacenNoDisponible, almacen.AlmacenError, ValueError) as e:
                st.error(str(e))
            except Exception as e:                          # noqa: BLE001
                st.error(f"No se pudo guardar la versión: {e}")
    else:
        st.caption("Procesa un archivo arriba para poder guardarlo como nueva versión.")

    st.markdown("#### Versiones guardadas")
    conjunto_lista = st.selectbox("Ver versiones de", list(almacen.CONJUNTOS),
                                  key="almacen_conjunto_lista")
    try:
        versiones = almacen.Almacen().versiones(conjunto_lista)
    except (almacen.AlmacenNoDisponible, almacen.AlmacenError) as e:
        st.warning(str(e))
        return
    except Exception as e:                                  # noqa: BLE001
        st.warning(f"No se pudieron leer las versiones: {e}")
        return

    if not versiones:
        st.caption("Todavía no hay versiones guardadas de este conjunto.")
        return

    for v in versiones:
        fecha = pd.to_datetime(v.get("creada_en"), errors="coerce")
        fecha_txt = f"{fecha:%d/%m/%Y %H:%M}" if pd.notna(fecha) else "—"
        cols = st.columns([2, 1, 4, 1, 1])
        cols[0].write(fecha_txt)
        cols[1].write(f"{v.get('filas', '?')} filas")
        cols[2].write(v.get("notas") or v.get("nombre_original") or "")
        if v.get("activa"):
            cols[3].markdown("**Activa**")
        elif cols[4].button("Activar", key=f"activar_{v.get('id')}"):
            try:
                almacen.Almacen().activar(v["id"], conjunto=v.get("conjunto"))
                st.cache_data.clear()
                st.success(f"Versión del {fecha_txt} activada. Se carga en el próximo arranque.")
                st.rerun()
            except Exception as e:                          # noqa: BLE001
                st.error(f"No se pudo activar: {e}")
