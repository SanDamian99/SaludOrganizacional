import os
from supabase import create_client, Client
from src.core.config import get_supabase_url, get_supabase_key
import pandas as pd
import io

class SupabaseManager:
    def __init__(self):
        self.url = get_supabase_url()
        self.key = get_supabase_key()
        self.client: Client = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                print(f"Error initializing Supabase: {e}")

    def is_connected(self):
        return self.client is not None

    def upload_file(self, file_buffer, file_name, bucket="datasets"):
        """Uploads a file to Supabase Storage."""
        if not self.is_connected():
            return {"error": "Supabase not connected"}
        
        try:
            # Handle different file types
            if hasattr(file_buffer, 'read'):
                # Streamlit UploadedFile or similar
                file_buffer.seek(0)  # Reset to beginning
                data = file_buffer.read()
            elif isinstance(file_buffer, io.StringIO):
                data = file_buffer.getvalue().encode('utf-8')
            elif isinstance(file_buffer, io.BytesIO):
                data = file_buffer.getvalue()
            elif isinstance(file_buffer, bytes):
                data = file_buffer
            elif isinstance(file_buffer, str):
                data = file_buffer.encode('utf-8')
            else:
                data = file_buffer

            response = self.client.storage.from_(bucket).upload(
                path=file_name,
                file=data,
                file_options={"content-type": "text/csv", "upsert": "true"}
            )
            return response
        except Exception as e:
            return {"error": str(e)}

    def insert_dataframe(self, df: pd.DataFrame, table_name="processed_data"):
        """Inserts a DataFrame into a Supabase Table."""
        if not self.is_connected():
            return {"error": "Supabase not connected"}
        
        try:
            # Convert DataFrame to list of dicts
            records = df.to_dict(orient='records')
            
            # Prepare data for JSONB insertion
            # We wrap each record in a 'data' field
            data_to_insert = [{'data': record} for record in records]
            
            # Insert in chunks to avoid payload limits
            chunk_size = 1000
            for i in range(0, len(data_to_insert), chunk_size):
                chunk = data_to_insert[i:i+chunk_size]
                self.client.table(table_name).insert(chunk).execute()
                
            return {"success": True, "rows": len(data_to_insert)}
        except Exception as e:
            return {"error": str(e)}

    def get_public_datasets(self, bucket="datasets"):
        """Lists files in the public bucket."""
        if not self.is_connected():
            return []
        
        try:
            response = self.client.storage.from_(bucket).list()
            return response
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    def table_is_empty(self, table_name="processed_data"):
        """Verifica si una tabla está vacía."""
        if not self.is_connected():
            return True
        
        try:
            response = self.client.table(table_name).select("id", count="exact").limit(1).execute()
            return response.count == 0
        except Exception as e:
            print(f"Error checking table: {e}")
            return True
    
    def seed_master_data(self, csv_path="cleaned_data - cleaned_data.csv", 
                        table_name="processed_data", force=False):
        """
        Carga el dataset maestro en Supabase si la tabla está vacía.
        
        Args:
            csv_path: Ruta al archivo CSV maestro
            table_name: Nombre de la tabla de destino
            force: Si True, carga datos incluso si la tabla no está vacía
        
        Returns:
            dict: Estadísticas de la carga
        """
        if not self.is_connected():
            return {"error": "Supabase not connected"}
        
        # Verificar si tabla está vacía
        if not force and not self.table_is_empty(table_name):
            return {
                "status": "skipped", 
                "message": "Table already contains data. Use force=True to load anyway."
            }
        
        try:
            # Cargar CSV
            import os
            if not os.path.isabs(csv_path):
                # Si la ruta es relativa, hacerla absoluta desde el directorio del proyecto
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                csv_path = os.path.join(base_dir, csv_path)
            
            df = pd.read_csv(csv_path)
            
            # Insertar usando el método existente
            result = self.insert_dataframe(df, table_name)
            
            if "error" in result:
                return {"error": result["error"], "rows": 0}
            
            return {
                "status": "success",
                "rows_loaded": result.get("rows", 0),
                "source": csv_path
            }
            
        except FileNotFoundError:
            return {"error": f"File not found: {csv_path}"}
        except Exception as e:
            return {"error": f"Error seeding data: {str(e)}"}
