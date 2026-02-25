# Guía de Configuración Supabase

Esta guía te llevará paso a paso para configurar Supabase y cargar los datos iniciales de la aplicación.

## Requisitos Previos

- Una cuenta en [Supabase](https://supabase.com) (gratuita)
- Un proyecto creado en Supabase

## Paso 1: Ejecutar el Script SQL

### 1.1 Abrir SQL Editor

1. Ve a tu proyecto en Supabase Dashboard
2. En el menú lateral, selecciona **SQL Editor**
3. Crea una nueva query

### 1.2 Ejecutar el Script

Copia y pega **TODO** el contenido del archivo [`supabase_setup.sql`](file:///Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional/supabase_setup.sql) en el editor SQL.

El script creará:
- ✅ Tabla `processed_data` con columna JSONB flexible para almacenar datos
- ✅ Campo `filename` para tracking de archivos
- ✅ Timestamps automáticos
- ✅ Políticas RLS (Row Level Security) para acceso público

Haz clic en **Run** (o presiona `Cmd/Ctrl + Enter`).

### 1.3 Verificar Creación

En el SQL Editor, ejecuta esta query para verificar:

```sql
SELECT COUNT(*) FROM processed_data;
```

Debe retornar **0 filas** (la tabla está vacía, lo cual es correcto).

---

## Paso 2: Crear Bucket de Storage

### 2.1 Ir a Storage

1. En el menú lateral de Supabase, selecciona **Storage**
2. Haz clic en **Create a new bucket**

### 2.2 Configurar el Bucket

- **Name**: `datasets`
- **Public bucket**: ✅ **Activar** (marcar como público)
- Haz clic en **Create bucket**

### 2.3 Verificar Configuración

El bucket `datasets` debe aparecer en la lista con un ícono de 🌐 (público).

---

## Paso 3: Configurar Credenciales

### 3.1 Obtener Credenciales

1. En Supabase Dashboard, ve a **Settings** → **API**
2. Copia los siguientes valores:
   - **Project URL** (ejemplo: `https://xxxxx.supabase.co`)
   - **anon/public** key (la clave anon, NO la service_role)

### 3.2 Configurar en la Aplicación

Abre el archivo `.streamlit/secrets.toml` y agrega:

```toml
SUPABASE_URL = "https://tu-proyecto.supabase.co"
SUPABASE_KEY = "tu-anon-key-aqui"
```

> **⚠️ IMPORTANTE**: Este archivo NO debe subirse a Git. Ya está en `.gitignore`.

### 3.3 Alternativa: Variables de Entorno

También puedes configurar las credenciales como variables de entorno:

```bash
export SUPABASE_URL="https://tu-proyecto.supabase.co"
export SUPABASE_KEY="tu-anon-key-aqui"
```

---

## Paso 4: Cargar Datos Maestros

### 4.1 Verificar Instalación de Dependencias

Asegúrate de tener todas las dependencias instaladas:

```bash
pip install -r requirements.txt
```

### 4.2 Ejecutar Seed Data

Desde el directorio raíz del proyecto, ejecuta:

```bash
python -m src.data.seed_data
```

Este script:
1. ✅ Verifica la conexión a Supabase
2. ✅ Verifica que la tabla esté vacía
3. ✅ Carga el archivo `cleaned_data - cleaned_data.csv`
4. ✅ Inserta ~2,231 filas en la tabla `processed_data`

Deberías ver una salida similar a:

```
============================================================
SEED DATA - Carga de Datos Maestros en Supabase
============================================================
✅ Conectado a Supabase exitosamente

📁 Archivo fuente: /path/to/cleaned_data - cleaned_data.csv

⏳ Cargando datos en Supabase...

============================================================
✅ ÉXITO: 2231 filas cargadas
   Fuente: /path/to/cleaned_data - cleaned_data.csv
============================================================
```

### 4.3 Verificar Carga

En Supabase SQL Editor, ejecuta:

```sql
SELECT COUNT(*) FROM processed_data;
```

Debe retornar **~2,231 filas**.

---

## Paso 5: Validación Final

### 5.1 Test de Conexión

Ejecuta este comando para verificar la conexión desde Python:

```bash
python -c "from src.data.supabase_client import SupabaseManager; sm = SupabaseManager(); print('Conectado:', sm.is_connected())"
```

Debe imprimir: `Conectado: True`

### 5.2 Test de Datos

Ejecuta esta query en SQL Editor:

```sql
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT data->>'(SD)Sexo') as unique_genders,
    COUNT(DISTINCT data->>'(LB)Sector Económico ') as unique_sectors
FROM processed_data;
```

Debe mostrar estadísticas de los datos cargados.

---

## Solución de Problemas

### Error: "Supabase not connected"

- ✅ Verifica que `SUPABASE_URL` y `SUPABASE_KEY` estén correctamente configurados
- ✅ Verifica que la URL termine en `.supabase.co`
- ✅ Asegúrate de usar la clave **anon**, no la service_role

### Error: "Table already contains data"

Si quieres recargar los datos, usa el flag `--force`:

```bash
python -m src.data.seed_data --force
```

### Error: "File not found: cleaned_data - cleaned_data.csv"

Verifica que el archivo exista en el directorio raíz del proyecto.

---

## Próximos Pasos

Una vez completada la configuración:

1. ✅ Ejecuta la aplicación: `streamlit run main.py`
2. ✅ Prueba cargar un archivo Excel usando el nuevo `ExcelProcessor`
3. ✅ Los datos se guardarán automáticamente en Supabase

---

## Arquitectura de Datos

### Tabla `processed_data`

```sql
CREATE TABLE processed_data (
    id BIGINT PRIMARY KEY,
    created_at TIMESTAMP,
    data JSONB,        -- Contiene toda la fila del CSV/Excel
    filename TEXT,     -- Nombre del archivo origen
    processed_at TIMESTAMP
);
```

### Ventajas del Esquema JSONB

✅ **Flexibilidad**: Acepta cualquier estructura de columnas  
✅ **Evolución sin migracione**: Agregar nuevas columnas sin ALTER TABLE  
✅ **Consultas potentes**: Supabase permite consultas JSON nativas  
✅ **Compatibilidad**: Funciona con Excel y CSV de diferentes formatos  

### Ejemplo de Consulta

```sql
-- Obtener todas las mujeres del sector salud
SELECT 
    data->>'(SD)Edad' as edad,
    data->>'(SD)Sexo' as sexo,
    data->>'(LB)Sector Económico ' as sector
FROM processed_data
WHERE 
    data->>'(SD)Sexo' = 'Mujer'
    AND data->>'(LB)Sector Económico ' = 'Salud';
```
