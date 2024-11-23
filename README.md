## Aplicación de Análisis de Datos sobre Salud Organizacional

Esta aplicación es una herramienta interactiva desarrollada con Streamlit que permite explorar y analizar datos relacionados con el bienestar laboral y la salud mental en el entorno de trabajo. Utiliza inteligencia artificial a través de la API de Gemini de Google para procesar preguntas en lenguaje natural, identificar variables relevantes y generar informes detallados en formato PDF.

## Tabla de Contenidos

* Características Principales
* Requisitos Previos
* Instalación
* Configuración de la API de Gemini
* Ejecución de la Aplicación
* Uso de la Aplicación
* Estructura del Código
* Dependencias
* Consideraciones de Seguridad
* Contribución
* Licencia
* Contacto


## Características Principales

* **Interfaz Amigable:** Aplicación web interactiva y fácil de usar.
* **Análisis Automatizado:** Utiliza IA para seleccionar el método de análisis más adecuado según la pregunta del usuario.
* **Generación de Informes:** Crea informes en PDF que incluyen introducción, resultados, conclusiones y recomendaciones.
* **Visualizaciones:** Genera gráficos y visualizaciones de datos para una mejor comprensión de los resultados.
* **Filtros Personalizados:** Permite aplicar filtros en lenguaje natural para enfocar el análisis en subconjuntos de datos específicos.


## Requisitos Previos

* Python 3.7 o superior
* Cuenta y clave de API de Google Generative AI (Gemini)
* Librerías Python (listadas en requirements.txt)


## Instalación

1. **Clonar el repositorio**

   ```bash
   git clone https://github.com/tu_usuario/tu_repositorio.git
   cd tu_repositorio
   ```

2. **Crear un entorno virtual (opcional pero recomendado)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar las dependencias**

   ```bash
   pip install -r requirements.txt
   ```

4. **Colocar el archivo de datos**

   Asegúrate de que el archivo de datos (por ejemplo, `Resultados Indicadores de Bienestar y Salud Mental en el Mundo del Trabajo.xlsx`) esté en el mismo directorio que el script `analizer.py` o ajusta la ruta en el código si está en otra ubicación.


## Configuración de la API de Gemini

La aplicación utiliza la API de Gemini para procesar preguntas en lenguaje natural y generar texto para las secciones de introducción y conclusiones en el informe.

1. **Obtener la clave de API de Gemini**

   Regístrate y obtén tu clave de API en la plataforma de Google Cloud.

2. **Configurar la clave de API**

   * **Localmente:**
     
     * Crea un archivo `secrets.toml` en el directorio `.streamlit`:
     
       ```bash
       mkdir .streamlit
       nano .streamlit/secrets.toml  # Puedes usar cualquier editor de texto
       ```

     * Agrega la clave de API en el archivo `secrets.toml`:

       ```toml
       [YOUR_API_KEY]
       key = "TU_CLAVE_DE_API_DE_GEMINI"
       ```

   * **En Streamlit Cloud:**
   
     * Ve a la sección "Secrets" en la configuración de tu aplicación y agrega:

       ```json
       {
         "YOUR_API_KEY": "TU_CLAVE_DE_API_DE_GEMINI"
       }
       ```

3. **En el Código (`analizer.py`):**

   Asegúrate de que el código para configurar la API de Gemini es el siguiente:

   ```python
   # Configurar la API de Gemini
   YOUR_API_KEY = st.secrets["YOUR_API_KEY"]
   genai.configure(api_key=YOUR_API_KEY)
   ```


## Ejecución de la Aplicación

Ejecuta la aplicación con el siguiente comando:

```bash
streamlit run analizer.py
```

La aplicación se abrirá en tu navegador predeterminado o puedes acceder a ella en `http://localhost:8501`.


## Uso de la Aplicación

1. **Resumen de la Base de Datos**
   
   Al iniciar, se mostrará un resumen de la base de datos con las variables y categorías disponibles.

2. **Ingresar una Pregunta**
   
   En el campo "Ingresa tu pregunta:", escribe la pregunta de investigación que deseas explorar. 
   
   Ejemplo: "¿Existe una relación entre el nivel de estrés y el número de horas trabajadas semanalmente?"

3. **Aplicar Filtros (Opcional)**
   
   Describe los filtros en lenguaje natural en el campo "Si deseas aplicar filtros, por favor descríbelos en lenguaje natural (opcional):".
   
   Ejemplo: "Analizar solo empleados del sector tecnológico con más de 5 años de experiencia."

4. **Realizar el Análisis**
   
   Haz clic en el botón "Realizar Análisis".
   
   La aplicación procesará tu pregunta y sugerirá el método de análisis más adecuado.

5. **Explorar Resultados**
   
   * **Resultados del Análisis:** Se mostrarán los resultados, incluyendo tablas y gráficos.
   * **Descargar Informe:** Puedes descargar un informe en PDF con la introducción, resultados y conclusiones.


## Estructura del Código

* **`analizer.py`:** Archivo principal que contiene el código de la aplicación.

**Funciones Principales**

* `main()`: Función que ejecuta la aplicación Streamlit.
* `mostrar_resumen_base_datos()`: Muestra el resumen de la base de datos.
* `procesar_pregunta(pregunta_usuario)`: Procesa la pregunta del usuario utilizando la API de Gemini.
* `procesar_filtros(filtro_natural)`: Convierte filtros en lenguaje natural a consultas de pandas.
* `realizar_analisis(opcion, pregunta_usuario, filtros)`: Realiza el análisis y genera resultados.
* `generar_informe(pregunta_usuario, opcion_analisis, resultados, figuras)`: Genera el informe en PDF.

**Clases**

* `RateLimiter`: Controla la tasa de llamadas a la API de Gemini.
* `PDFReport`: Crea el informe en PDF utilizando la librería FPDF.

**Diccionario de Datos**

* `data_dictionary`: Contiene información detallada de las variables, categorías, tipos de datos y significados de los valores.

   ```python
   # Ejemplo del diccionario de datos
   data_dictionary = {
       "Variables Sociodemográficas": {
           "Edad": {
               "Tipo": "Continua",
               "Valores": "18 a 70 o más"
           },
           # ... más variables
       },
       # ... más categorías
   }
   ```


## Dependencias

Las dependencias están listadas en el archivo `requirements.txt`. Algunas de las principales son:

* `streamlit`
* `pandas`
* `matplotlib`
* `google-generativeai`
* `fpdf`
* `scikit-learn`
* `requests`
* `urllib3`


## Consideraciones de Seguridad

* No incluyas la clave de API de Gemini directamente en el código. Utiliza Streamlit secrets o variables de entorno.
* Implementa un control de la tasa de llamadas a la API para evitar exceder los límites.
* Maneja los errores de conexión y las respuestas inesperadas de la API.


## Contribución

Se aceptan contribuciones y mejoras al código. Por favor, crea un "pull request" con tus cambios.


## Licencia

[Especifica la licencia de tu proyecto, por ejemplo, MIT License]


## Contacto

[Tu nombre o nombre de usuario de GitHub] - [Tu correo electrónico]


**¡Espero que esto te ayude a crear un README efectivo para tu repositorio de GitHub!** 

