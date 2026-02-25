"""
Script de prueba para el ExcelProcessor.

Este script prueba la funcionalidad del procesador de Excel complejo.
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.processor import ExcelProcessor
import pandas as pd


def test_excel_processor():
    """Prueba el ExcelProcessor con el archivo problemático."""
    
    print("=" * 70)
    print("TEST: ExcelProcessor - Archivo Excel Complejo")
    print("=" * 70)
    
    # Rutas
    excel_file = "Resultados Indicadores de Bienestar y Salud Mental en el Mundo del Trabajo (3).xlsx"
    reference_csv = "cleaned_data - cleaned_data.csv"
    
    # Verificar que los archivos existen
    if not os.path.exists(excel_file):
        print(f"\n❌ ERROR: Archivo Excel no encontrado: {excel_file}")
        print("   Asegúrate de que el archivo esté en el directorio raíz del proyecto.")
        return False
    
    if not os.path.exists(reference_csv):
        print(f"\n❌ ERROR: Archivo de referencia no encontrado: {reference_csv}")
        return False
    
    print(f"\n📁 Archivo Excel: {excel_file}")
    print(f"📁 Esquema de referencia: {reference_csv}")
    
    try:
        # Crear procesador
        processor = ExcelProcessor()
        print("\n✅ ExcelProcessor inicializado")
        
        # Procesar Excel
        print("\n⏳ Procesando archivo Excel...")
        df, report = processor.process_complex_excel(
            excel_file,
            reference_csv,
            skip_unmapped=True
        )
        
        # Mostrar resultados
        print("\n" + "=" * 70)
        print("REPORTE DE PROCESAMIENTO")
        print("=" * 70)
        print(f"📊 Fila de cabecera detectada: {report['header_row_detected']}")
        print(f"📊 Filas originales: {report['rows_original']}")
        print(f"📊 Filas limpiadas: {report['rows_cleaned']}")
        print(f"📊 Columnas mapeadas: {len(report['columns_mapped'])}")
        print(f"📊 Columnas no mapeadas: {len(report['columns_unmapped'])}")
        
        if report['columns_unmapped']:
            print(f"\n⚠️  Columnas no mapeadas ({len(report['columns_unmapped'])}):")
            for col in report['columns_unmapped'][:10]:  # Mostrar solo las primeras 10
                print(f"   - {col}")
            if len(report['columns_unmapped']) > 10:
                print(f"   ... y {len(report['columns_unmapped']) - 10} más")
        
        if report['errors']:
            print(f"\n❌ Errores encontrados:")
            for error in report['errors']:
                print(f"   - {error}")
        
        print(f"\n📊 Dimensiones del DataFrame final: {df.shape}")
        print(f"📊 Columnas totales: {len(df.columns)}")
        
        # Mostrar muestra de datos
        print("\n" + "=" * 70)
        print("MUESTRA DE DATOS (primeras 3 filas, primeras 5 columnas)")
        print("=" * 70)
        print(df.iloc[:3, :5].to_string())
        
        # Verificar columnas clave
        print("\n" + "=" * 70)
        print("VERIFICACIÓN DE COLUMNAS CLAVE")
        print("=" * 70)
        key_columns = ["(SD)Edad", "(SD)Sexo", "(SD)Nivel Educativo", "(LB)Sector Económico "]
        for col in key_columns:
            if col in df.columns:
                non_null = df[col].notna().sum()
                print(f"✅ {col}: {non_null} valores no-nulos")
            else:
                print(f"❌ {col}: NO ENCONTRADA")
        
        print("\n" + "=" * 70)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_excel_processor()
    sys.exit(0 if success else 1)
