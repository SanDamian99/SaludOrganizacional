"""
Script para cargar datos maestros en Supabase.

Este script carga el archivo 'cleaned_data - cleaned_data.csv' en la tabla 
'processed_data' de Supabase si la tabla está vacía.

Uso:
    python -m src.data.seed_data
    
    O desde Python:
    from src.data.seed_data import seed_database
    seed_database()
"""

from src.data.supabase_client import SupabaseManager
import os
import sys


def seed_database(csv_path=None, force=False):
    """
    Carga el dataset maestro en Supabase.
    
    Args:
        csv_path: Ruta al archivo CSV maestro (opcional)
        force: Si True, carga datos incluso si la tabla no está vacía
    
    Returns:
        dict: Resultado de la operación
    """
    print("=" * 60)
    print("SEED DATA - Carga de Datos Maestros en Supabase")
    print("=" * 60)
    
    # Conectar a Supabase
    manager = SupabaseManager()
    
    if not manager.is_connected():
        print("❌ ERROR: No se pudo conectar a Supabase.")
        print("   Verifica que SUPABASE_URL y SUPABASE_KEY estén configurados.")
        return {"error": "No connection to Supabase"}
    
    print("✅ Conectado a Supabase exitosamente")
    
    # Determinar ruta del CSV
    if csv_path is None:
        # Usar ruta por defecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        csv_path = os.path.join(base_dir, "cleaned_data - cleaned_data.csv")
    
    print(f"\n📁 Archivo fuente: {csv_path}")
    
    # Verificar que el archivo existe
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: El archivo no existe: {csv_path}")
        return {"error": "File not found"}
    
    # Cargar datos
    print("\n⏳ Cargando datos en Supabase...")
    result = manager.seed_master_data(csv_path, force=force)
    
    # Mostrar resultado
    print("\n" + "=" * 60)
    if "error" in result:
        print(f"❌ ERROR: {result['error']}")
    elif result.get("status") == "skipped":
        print(f"⚠️  OMITIDO: {result.get('message')}")
        print("   Usa force=True si deseas cargar de todas formas.")
    else:
        print(f"✅ ÉXITO: {result.get('rows_loaded', 0)} filas cargadas")
        print(f"   Fuente: {result.get('source')}")
    print("=" * 60)
    
    return result


def main():
    """Función principal para ejecutar desde línea de comandos."""
    force = "--force" in sys.argv or "-f" in sys.argv
    
    if force:
        print("⚠️  Modo FORCE activado: se cargarán datos aunque la tabla no esté vacía\n")
    
    result = seed_database(force=force)
    
    # Retornar código de salida apropiado
    if "error" in result:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
