import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
import toml
import socket
from supabase import create_client

def test_connection():
    print("--- DIAGNÓSTICO DE CONEXIÓN SUPABASE ---")
    
    # 1. Leer secrets directamente para ver qué hay
    try:
        secrets = toml.load(".streamlit/secrets.toml")
        url = secrets.get("SUPABASE_URL")
        key = secrets.get("SUPABASE_KEY")
        
        print(f"1. URL leída del archivo: '{url}'")
        print(f"   Tipo: {type(url)}")
        print(f"   Longitud: {len(url) if url else 0}")
        
        if not url:
            print("❌ ERROR: SUPABASE_URL no encontrada en secrets.toml")
            return

        # 2. Verificar caracteres ocultos
        print(f"2. Análisis de URL (repr): {repr(url)}")
        
        # 3. Test de resolución DNS
        hostname = url.replace("https://", "").replace("http://", "").split("/")[0]
        print(f"3. Intentando resolver hostname: '{hostname}'")
        try:
            ip = socket.gethostbyname(hostname)
            print(f"   ✅ DNS Resuelto: {ip}")
        except Exception as e:
            print(f"   ❌ ERROR DNS: {e}")
            return

        # 4. Test de conexión Supabase
        print("4. Iniciando cliente Supabase...")
        client = create_client(url, key)
        
        print("5. Probando conexión (listar buckets)...")
        res = client.storage.list_buckets()
        print("   ✅ Conexión exitosa. Buckets encontrados:")
        for bucket in res:
            print(f"      - {bucket.name}")
            
    except Exception as e:
        print(f"\n❌ EXCEPCIÓN FINAL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()
