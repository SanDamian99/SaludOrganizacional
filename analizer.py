# Importar librerías necesarias
import streamlit as st
import pandas as pd
import time
import random
from datetime import datetime
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError
import matplotlib.pyplot as plt
from fpdf import FPDF  # Necesitarás instalar esta librería: pip install fpdf
import io
import base64

# Importar la librería de Gemini
import google.generativeai as genai

# Configurar la API de Gemini
YOUR_API_KEY = st.secrets["YOUR_API_KEY"]   # Reemplaza con tu clave de API de Gemini
genai.configure(api_key=YOUR_API_KEY)

# Configuración de generación
generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 1200,
}

# Configuración de seguridad
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

# Inicializar el modelo de Gemini
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    safety_settings=safety_settings
)

# Definir la clase RateLimiter para controlar la tasa de llamadas a la API
class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.call_times = []

    def wait(self):
        now = time.time()
        self.call_times = [t for t in self.call_times if t > now - self.period]
        if len(self.call_times) >= self.max_calls:
            sleep_time = self.call_times[0] + self.period - now
            st.write(f"Límite de tasa alcanzado. Esperando {sleep_time:.2f} segundos...")
            time.sleep(sleep_time)
            self.call_times = [t for t in self.call_times if t > now - self.period]
        self.call_times.append(time.time())

# Cargar el archivo CSV
ruta_csv = 'Resultados Indicadores de Bienestar y Salud Mental en el Mundo del Trabajo.xlsx'  # Reemplaza con la ruta real del archivo
df = pd.read_excel(ruta_csv)

# Extraer información de las columnas y tipos de datos
def obtener_informacion_datos(df):
    info_columnas = []
    for col in df.columns:
        tipo = str(df[col].dtype)
        info_columnas.append(f"{col}: {tipo}")
    return "\n".join(info_columnas)

informacion_datos = obtener_informacion_datos(df)

# Definir las opciones de análisis disponibles
opciones_analisis = """
Opciones de análisis disponibles:

1. Mostrar distribución de una variable categórica.
2. Calcular estadísticas descriptivas de una variable numérica.
3. Visualizar la relación entre dos variables numéricas.
4. Filtrar datos según criterios y mostrar estadísticas.
5. Mostrar correlación entre variables numéricas.
6. Realizar análisis de regresión simple.
"""

# Preparar el prompt para Gemini
prompt_informacion_datos = f"""
Los siguientes son los datos y tipos de datos que tenemos:

{informacion_datos}

Y las opciones de análisis disponibles son:

{opciones_analisis}

Por favor, utiliza esta información para entender los datos disponibles, los tipos de datos asociados y las opciones de análisis que podemos realizar.
"""

# Enviar el prompt inicial a Gemini para que entienda los datos
rate_limiter = RateLimiter(max_calls=4, period=61)

def enviar_prompt(prompt):
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            rate_limiter.wait()
            response = model.generate_text(prompt)
            if response and response.text:
                return response.text.strip()
            else:
                return "No se recibió respuesta de Gemini."
        except (ConnectionError, ProtocolError) as e:
            retries += 1
            wait_time = 2 ** retries + random.random()
            st.write(f"Error: {e}. Reintentando en {wait_time:.2f} segundos...")
            time.sleep(wait_time)
        except Exception as e:
            st.write(f"Error inesperado: {e}")
            retries += 1
            time.sleep(2 ** retries + random.random())
    return "Error al comunicarse con Gemini."

# Enviar la información de datos a Gemini
respuesta_informacion_datos = enviar_prompt(prompt_informacion_datos)
st.write("Gemini ha sido informado sobre los datos y opciones de análisis.")

# Función para procesar una pregunta del usuario
def procesar_pregunta(pregunta_usuario):
    prompt_pregunta = f"""
Utilizando la información de los datos proporcionados y las opciones de análisis disponibles:

{informacion_datos}

Opciones de análisis:

{opciones_analisis}

Un miembro de la empresa ha hecho la siguiente pregunta:

"{pregunta_usuario}"

Por favor, decide cuál de las opciones de análisis (1-6) es más adecuada para responder a esta pregunta. Solo responde con el número de la opción más relevante. El número debe ser del 1 al 6. Solo puede ser un número.
"""
    respuesta = enviar_prompt(prompt_pregunta)
    return respuesta.strip()

# Función para procesar filtros en lenguaje natural utilizando Gemini
def procesar_filtros(filtro_natural):
    if not filtro_natural.strip():
        return None  # No se proporcionó ningún filtro
    prompt_filtro = f"""
    Convierte el siguiente filtro descrito en lenguaje natural a una consulta de pandas para filtrar un DataFrame.
    El DataFrame tiene las siguientes columnas y tipos de datos:

    {informacion_datos}

    El filtro es:

    "{filtro_natural}"

    Proporciona únicamente la expresión de filtrado en el formato que pandas 'query' entiende, sin ninguna explicación adicional.
    Por ejemplo, si el filtro es 'empleados mayores de 30 años y que sean mujeres', la salida debería ser "Edad > 30 & Sexo == 'Mujer'".

    Filtro pandas:
    """
    filtro_pandas = enviar_prompt(prompt_filtro)
    # Limpiar la respuesta de Gemini
    filtro_pandas = filtro_pandas.strip().split('Filtro pandas:')[-1].strip()
    return filtro_pandas

# Modificar la función realizar_analisis para capturar resultados y figuras
def realizar_analisis(opcion, pregunta_usuario, filtros=None):
    resultados = ""
    figuras = []
    if filtros:
        # Aplicar filtros si se proporcionan
        try:
            df_filtrado = df.query(filtros)
        except Exception as e:
            st.write(f"Error al aplicar el filtro: {e}")
            df_filtrado = df
    else:
        df_filtrado = df

    # Utilizar Gemini para extraer variables relevantes de la pregunta del usuario
    def obtener_variables_relevantes(pregunta, tipo_variable):
        prompt_variables = f"""
        Basado en la siguiente pregunta:

        "{pregunta}"

        Y teniendo en cuenta las columnas y tipos de datos del DataFrame:

        {informacion_datos}

        Identifica las variables que son de tipo '{tipo_variable}' y que son relevantes para responder la pregunta. Proporciona una lista de variables separadas por comas, sin explicaciones adicionales.
        """
        respuesta = enviar_prompt(prompt_variables)
        # Limpiar y procesar la respuesta de Gemini
        variables = [var.strip() for var in respuesta.split(',') if var.strip() in df.columns]
        return variables

    if opcion == '1':
        # Mostrar distribución de una variable categórica
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'categórica')
        if variables_relevantes:
            variable = st.selectbox("Selecciona una variable categórica para analizar:", variables_relevantes)
            conteo = df_filtrado[variable].value_counts()
            resultados += f"Distribución de {variable}:\n{conteo.to_string()}\n"
            fig, ax = plt.subplots()
            conteo.plot(kind='bar', ax=ax, title=f'Distribución de {variable}')
            st.pyplot(fig)
            figuras.append(fig)
        else:
            resultados += "No se encontraron variables categóricas relevantes para la pregunta.\n"

    elif opcion == '2':
        # Calcular estadísticas descriptivas de una variable numérica
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if variables_relevantes:
            variable = st.selectbox("Selecciona una variable numérica para analizar:", variables_relevantes)
            estadisticas = df_filtrado[variable].describe()
            resultados += f"Estadísticas descriptivas de {variable}:\n{estadisticas.to_string()}\n"
            fig, ax = plt.subplots()
            df_filtrado[variable].hist(bins=10, grid=False, ax=ax)
            ax.set_title(f'Histograma de {variable}')
            st.pyplot(fig)
            figuras.append(fig)
        else:
            resultados += "No se encontraron variables numéricas relevantes para la pregunta.\n"

    elif opcion == '3':
        # Visualizar la relación entre dos variables numéricas
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if len(variables_relevantes) >= 2:
            variable_x = st.selectbox("Selecciona la variable para el eje X:", variables_relevantes)
            variable_y = st.selectbox("Selecciona la variable para el eje Y:", variables_relevantes)
            resultados += f"Visualizando relación entre {variable_x} y {variable_y}.\n"
            fig, ax = plt.subplots()
            df_filtrado.plot.scatter(x=variable_x, y=variable_y, ax=ax, title=f'Relación entre {variable_x} y {variable_y}')
            st.pyplot(fig)
            figuras.append(fig)
        else:
            resultados += "No se encontraron suficientes variables numéricas relevantes para la pregunta.\n"

    elif opcion == '4':
        # Filtrar datos según criterios y mostrar estadísticas
        resultados += "Datos después de aplicar los filtros proporcionados.\n"
        resultados += f"Total de registros después del filtro: {len(df_filtrado)}\n"
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if variables_relevantes:
            variable = st.selectbox("Selecciona una variable numérica para estadísticas descriptivas:", variables_relevantes)
            estadisticas = df_filtrado[variable].describe()
            resultados += f"Estadísticas descriptivas de {variable} después de aplicar filtros:\n{estadisticas.to_string()}\n"
            fig, ax = plt.subplots()
            df_filtrado[variable].hist(bins=10, grid=False, ax=ax)
            ax.set_title(f'Histograma de {variable} después de filtros')
            st.pyplot(fig)
            figuras.append(fig)
        else:
            resultados += "No se encontraron variables numéricas relevantes para la pregunta.\n"

    elif opcion == '5':
        # Mostrar correlación entre variables numéricas
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if len(variables_relevantes) >= 2:
            variables_seleccionadas = st.multiselect("Selecciona las variables numéricas para calcular la correlación:", variables_relevantes)
            if len(variables_seleccionadas) >= 2:
                correlacion = df_filtrado[variables_seleccionadas].corr()
                resultados += "Matriz de correlación:\n"
                resultados += correlacion.to_string() + "\n"
                fig, ax = plt.subplots()
                cax = ax.matshow(correlacion, cmap='coolwarm')
                fig.colorbar(cax)
                ax.set_xticks(range(len(variables_seleccionadas)))
                ax.set_xticklabels(variables_seleccionadas, rotation=90)
                ax.set_yticks(range(len(variables_seleccionadas)))
                ax.set_yticklabels(variables_seleccionadas)
                st.pyplot(fig)
                figuras.append(fig)
            else:
                resultados += "Debes seleccionar al menos dos variables.\n"
        else:
            resultados += "No se encontraron suficientes variables numéricas relevantes para la pregunta.\n"

    elif opcion == '6':
        # Realizar análisis de regresión simple
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if len(variables_relevantes) >= 2:
            variable_x = st.selectbox("Selecciona la variable independiente (X):", variables_relevantes)
            variable_y = st.selectbox("Selecciona la variable dependiente (Y):", variables_relevantes)
            from sklearn.linear_model import LinearRegression
            X = df_filtrado[[variable_x]].dropna()
            y = df_filtrado[variable_y].dropna()
            # Asegurarse de que X e y tienen el mismo número de filas
            df_regresion = pd.concat([X, y], axis=1).dropna()
            X = df_regresion[[variable_x]]
            y = df_regresion[variable_y]
            modelo = LinearRegression()
            modelo.fit(X, y)
            r_sq = modelo.score(X, y)
            resultados += f"Coeficiente de determinación (R^2): {r_sq}\n"
            resultados += f"Intercepto: {modelo.intercept_}\n"
            resultados += f"Coeficiente: {modelo.coef_[0]}\n"
            # Graficar la regresión
            fig, ax = plt.subplots()
            ax.scatter(X, y, color='blue')
            ax.plot(X, modelo.predict(X), color='red')
            ax.set_title(f'Regresión lineal entre {variable_x} y {variable_y}')
            ax.set_xlabel(variable_x)
            ax.set_ylabel(variable_y)
            st.pyplot(fig)
            figuras.append(fig)
        else:
            resultados += "No se encontraron suficientes variables numéricas relevantes para la pregunta.\n"
    else:
        resultados += "Opción de análisis no reconocida.\n"

    return resultados, figuras

# Función para mostrar un resumen de la base de datos y ejemplos de preguntas
def mostrar_resumen_base_datos():
    resumen = """
**Resumen de la Base de Datos:**

La base de datos contiene información sobre salud psicológica en el trabajo, incluyendo variables sociodemográficas, laborales y varias dimensiones relacionadas con el bienestar laboral y salud mental.

**Principales categorías y variables:**

1. **Variables Sociodemográficas:**
   - **Edad** (Continua): Edad de los participantes entre 18 y 70 años o más.
   - **Sexo** (Categórica): Hombre, Mujer, Otro.
   - **Estado Civil** (Categórica): Soltero, Casado, Separado, Unión Libre, Viudo.
   - **Número de Hijos** (Continua): De 0 a 10 hijos.
   - **Nivel Educativo** (Categórica): Bachiller, Técnico, Tecnológico, Profesional, Posgrado.
   - **Municipio** (Categórica): Departamento y Municipio.
   - **Zona de Vivienda** (Categórica): Urbana, Rural.
   - **Estrato Socioeconómico** (Categórica): 1 a 6.

2. **Variables Laborales:**
   - **Sector Económico** (Categórica): Sectores económicos representativos.
   - **Sector Empresa** (Categórica): Público, Privado, Mixto.
   - **Tamaño Empresa** (Categórica): Menos de 10 empleados hasta más de 500 empleados.
   - **Trabajo por Turnos** (Categórica): Sí, No.
   - **Tipo de Contrato** (Categórica): Indefinido, Término Fijo, Obra o Labor, Aprendizaje, Prestación de Servicios.
   - **Número de horas de trabajo semanal** (Continua): De 1 a 60 horas.
   - **Ingreso Salarial Mensual** (Categórica): Rangos desde menos de 1 SMLV hasta más de 10 SMLV.
   - **Nivel Cargo** (Categórica): Operativo, Administrativo, Directivo.
   - **Personas a cargo en el trabajo** (Categórica): Sí, No.
   - **Años de Experiencia Laboral** (Continua): De 1 a 60 años.
   - **Antigüedad en el cargo/labor actual** (Categórica): Menos de 1 año hasta más de 10 años.
   - **Tipo de Modalidad de Trabajo** (Categórica): Presencial, Híbrido, Remoto, Teletrabajo.
   - **Tiempo promedio de traslado al trabajo/casa al día** (Categórica): Menos de 1 hora hasta más de 3 horas.
   - **Horas de formación recibidas (último año)** (Continua): De 1 a 100 horas.

3. **Dimensiones de Bienestar y Salud Mental:**
   - **Control del Tiempo**: Percepción sobre el control y presión de tiempo en el trabajo.
   - **Compromiso del Líder**: Apoyo y valoración del líder hacia el empleado.
   - **Apoyo del Grupo**: Apoyo de los compañeros de trabajo.
   - **Claridad de Rol**: Claridad sobre deberes y responsabilidades.
   - **Cambio Organizacional**: Comunicación y gestión de cambios en la organización.
   - **Responsabilidad Organizacional**: Acciones de la organización hacia la salud física y mental de los empleados.
   - **Conflicto Familia-Trabajo**: Interferencia entre demandas familiares y laborales.
   - **Síntomas de Burnout**: Indicadores de agotamiento emocional y físico.

**Ejemplos de preguntas que se pueden resolver con esta información:**

1. **¿Cuál es la distribución del nivel de estrés laboral entre empleados de diferentes sectores económicos?**
   - *Análisis de la relación entre el sector económico y variables relacionadas con el estrés o burnout.*

2. **¿Existe una correlación entre las horas de trabajo semanales y la percepción de apoyo del líder?**
   - *Evaluación de cómo las horas trabajadas afectan la percepción del empleado sobre el apoyo recibido por parte de su líder.*

Por favor, realiza tu pregunta teniendo en cuenta las variables y dimensiones disponibles en la base de datos.
    """
    st.markdown(resumen)

# Función principal
def main():
    st.title("Aplicación de Análisis de Datos con Gemini y Streamlit")

    mostrar_resumen_base_datos()

    pregunta_usuario = st.text_input("Ingresa tu pregunta:")
    filtro_natural = st.text_input("Si deseas aplicar filtros, por favor descríbelos en lenguaje natural (opcional):")

    if st.button("Realizar Análisis"):
        with st.spinner('Procesando...'):
            filtros_usuario = procesar_filtros(filtro_natural)
            if filtros_usuario:
                st.write(f"El filtro aplicado es: {filtros_usuario}")
            else:
                st.write("No se aplicará ningún filtro.")
            respuesta = procesar_pregunta(pregunta_usuario)
            st.write(f"Gemini sugiere la opción de análisis: {respuesta}")
            resultados, figuras = realizar_analisis(respuesta, pregunta_usuario, filtros_usuario)
            st.write("**Resultados del análisis:**")
            st.write(resultados)
            # Las figuras ya se muestran en la función realizar_analisis con st.pyplot()
            # Generar el informe
            generar_informe(pregunta_usuario, respuesta, resultados, figuras)
            # Proporcionar un enlace de descarga para el informe PDF
            with open('informe_analisis_datos.pdf', 'rb') as f:
                pdf_data = f.read()
            b64 = base64.b64encode(pdf_data).decode('utf-8')
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="informe_analisis_datos.pdf">Descargar Informe en PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

# Función para generar el informe en PDF
def generar_informe(pregunta_usuario, opcion_analisis, resultados, figuras):
    pdf = PDFReport()

    # Introducción
    pdf.chapter_title('Introducción')
    # Generar el texto de la introducción usando Gemini
    prompt_introduccion = f"""
Utilizando la siguiente pregunta de investigación:

"{pregunta_usuario}"

Y el método de análisis correspondiente a la opción {opcion_analisis}, por favor genera una introducción que explique la relevancia de la pregunta y el método utilizado para analizar la información de la base de datos.
"""
    introduccion = enviar_prompt(prompt_introduccion)
    pdf.chapter_body(introduccion)

    # Resultados
    pdf.chapter_title('Resultados')
    # Agregar los resultados y visualizaciones al informe
    pdf.chapter_body('A continuación, se presentan los resultados obtenidos del análisis:')
    pdf.chapter_body(resultados)

    # Insertar las figuras generadas
    for idx, fig in enumerate(figuras):
        # Guardar la figura en un objeto BytesIO
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        img_data = buf.read()

        # Escribir la imagen en un archivo temporal
        img_path = f'figura_{idx}.png'
        with open(img_path, 'wb') as f:
            f.write(img_data)

        # Insertar la imagen en el PDF
        pdf.insert_image(img_path)

    # Conclusiones y Recomendaciones
    pdf.chapter_title('Conclusiones y Recomendaciones')
    # Generar el texto de conclusiones usando Gemini
    prompt_conclusiones = f"""
Basándote en los resultados obtenidos:

{resultados}

Por favor, proporciona conclusiones y recomendaciones que puedan ser útiles para la empresa.
"""
    conclusiones = enviar_prompt(prompt_conclusiones)
    pdf.chapter_body(conclusiones)

    # Guardar el informe en PDF
    nombre_informe = 'informe_analisis_datos.pdf'
    pdf.output(nombre_informe)
    st.write(f"Informe generado y guardado como {nombre_informe}")

# Clase para generar el informe en PDF
class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font('Arial', '', 12)

    def header(self):
        # Encabezado del documento
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Informe de Análisis de Datos', ln=True, align='C')
        self.ln(10)

    def chapter_title(self, label):
        # Título de cada sección
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, label, ln=True)
        self.ln(5)

    def chapter_body(self, text):
        # Cuerpo de texto de cada sección
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, text)
        self.ln()

    def insert_image(self, image_path):
        # Insertar una imagen en el PDF
        self.image(image_path, w=180)
        self.ln()

if __name__ == "__main__":
    main()
