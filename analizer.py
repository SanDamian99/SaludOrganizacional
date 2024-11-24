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
ruta_csv = 'Resultados Indicadores de Bienestar y Salud Mental en el Mundo del Trabajo.xlsx'

# Data Dictionary
data_dictionary = {
    "Variables Sociodemográficas": {
        "Edad": {
            "Tipo": "Continua",
            "Valores": "18 a 70 o más (en el análisis se agrupan por criterios)"
        },
        "Sexo": {
            "Tipo": "Categórica",
            "Valores": ["Hombre", "Mujer", "Otro"]
        },
        "Estado Civil": {
            "Tipo": "Categórica",
            "Valores": ["Soltero", "Casado", "Separado", "Unión Libre", "Viudo"]
        },
        "Número de Hijos": {
            "Tipo": "Continua",
            "Valores": "0 a 10"
        },
        "Nivel Educativo": {
            "Tipo": "Categórica",
            "Valores": ["Bachiller", "Técnico", "Tecnológico", "Profesional", "Posgrado"]
        },
        "Municipio": {
            "Tipo": "Categórica",
            "Valores": "Departamento y Municipio (lista desplegable)"
        },
        "Zona de Vivienda": {
            "Tipo": "Categórica",
            "Valores": ["Urbana", "Rural"]
        },
        "Estrato Socioeconómico": {
            "Tipo": "Categórica",
            "Valores": [1, 2, 3, 4, 5, 6]
        }
    },
    "Variables Laborales": {
        "Sector Económico": {
            "Tipo": "Categórica",
            "Valores": "Sectores económicos representativos (lista desplegable)"
        },
        "Sector Empresa": {
            "Tipo": "Categórica",
            "Valores": ["Público", "Privado", "Mixto"]
        },
        "Tamaño Empresa": {
            "Tipo": "Categórica",
            "Valores": [
                "Menos de 10 empleados",
                "Entre 10 y 50 empleados",
                "Entre 50 y 200 empleados",
                "Entre 200 y 500 empleados",
                "Más de 500 empleados"
            ]
        },
        "Trabajo por Turnos": {
            "Tipo": "Categórica",
            "Valores": ["Sí", "No"]
        },
        "Tipo de Contrato": {
            "Tipo": "Categórica",
            "Valores": [
                "Indefinido",
                "Término Fijo",
                "Obra o Labor",
                "Aprendizaje",
                "Prestación de Servicios"
            ]
        },
        "Número horas trabajo semanal": {
            "Tipo": "Continua",
            "Valores": "1 a 60 horas (agrupado por criterios en análisis)"
        },
        "Ingreso SalDejaVu Mensual": {
            "Tipo": "Categórica",
            "Valores": [
                "Menos de 1 SMLV",
                "Entre 1 y 3 SMLV",
                "Entre 3 y 5 SMLV",
                "Entre 5 y 10 SMLV",
                "Más de 10 SMLV"
            ]
        },
        "Nivel Cargo": {
            "Tipo": "Categórica",
            "Valores": ["Operativo", "Administrativo", "Directivo"]
        },
        "Personas a cargo en el trabajo": {
            "Tipo": "Categórica",
            "Valores": ["Sí", "No"]
        },
        "Años Experiencia Laboral": {
            "Tipo": "Continua",
            "Valores": "1 a 60 años (agrupado por criterios en análisis)"
        },
        "Antigüedad en el cargo/labor actual": {
            "Tipo": "Categórica",
            "Valores": [
                "Menos de 1 año",
                "Entre 1 y 3 años",
                "Entre 3 y 7 años",
                "Entre 7 y 10 años",
                "Más de 10 años"
            ]
        },
        "Tipo de Modalidad de Trabajo": {
            "Tipo": "Categórica",
            "Valores": ["Presencial", "Híbrido", "Remoto", "Teletrabajo"]
        },
        "Tiempo promedio de traslado al trabajo/casa al día": {
            "Tipo": "Categórica",
            "Valores": [
                "Menos de 1 hora",
                "Entre 1 y 2 horas",
                "Entre 2 y 3 horas",
                "Más de 3 horas"
            ]
        },
        "Horas de formación recibidas (último año)": {
            "Tipo": "Continua",
            "Valores": "1 a 100 horas (agrupado por criterios en análisis)"
        }
    },
    "Dimensiones de Bienestar y Salud Mental": {
        "Control del Tiempo": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                2: "Rara vez",
                3: "Alguna vez",
                4: "Algunas veces",
                5: "A menudo",
                6: "Frecuentemente",
                7: "Siempre"
            },
            "Preguntas": [
                "Tengo la opción de decidir qué hago en mi trabajo.",
                "Tengo algo que decir sobre la forma en que hago mi trabajo.",
                "Tengo voz y voto sobre mi propio ritmo de trabajo.",
                "Me presionan para que trabaje muchas horas.",
                "Tengo algunos plazos de entrega inalcanzables.",
                "Tengo presiones de tiempo poco realistas.",
                "Tengo que descuidar algunas tareas porque tengo mucho que hacer."
            ]
        },
        "Compromiso del Líder": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                2: "Rara vez",
                3: "Alguna vez",
                4: "Algunas veces",
                5: "A menudo",
                6: "Frecuentemente",
                7: "Siempre"
            },
            "Preguntas": [
                "Puedo confiar en mi líder para que me ayude con un problema laboral.",
                "Si el trabajo se pone difícil, mi líder me ayudará.",
                "Recibo la ayuda y el apoyo que necesito de mi líder.",
                "Mi líder está dispuesto a escuchar mis problemas relacionados con el trabajo.",
                "Siento que mi líder valora mis contribuciones a esta organización.",
                "Mi líder me da suficiente crédito por mi trabajo duro.",
                "Mi líder me anima en mi trabajo con elogios y agradecimientos."
            ]
        },
        "Apoyo del Grupo": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                2: "Rara vez",
                3: "Alguna vez",
                4: "Algunas veces",
                5: "A menudo",
                6: "Frecuentemente",
                7: "Siempre"
            },
            "Preguntas": [
                "Si el trabajo se pone difícil, mis compañeros de trabajo me ayudarán.",
                "Recibo la ayuda y el apoyo que necesito de mis compañeros de trabajo.",
                "Mis compañeros de trabajo están dispuestos a escuchar mis problemas laborales."
            ]
        },
        "Claridad de Rol": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                2: "Rara vez",
                3: "Alguna vez",
                4: "Algunas veces",
                5: "A menudo",
                6: "Frecuentemente",
                7: "Siempre"
            },
            "Preguntas": [
                "Tengo claro lo que se espera de mí en el trabajo.",
                "Sé cómo hacer mi trabajo.",
                "Tengo claro cuáles son mis deberes y responsabilidades.",
                "Entiendo cómo mi trabajo encaja en el objetivo general de la organización.",
                "Diferentes grupos en el trabajo me exigen cosas que son difíciles de hacer al mismo tiempo.",
                "Diferentes personas en el trabajo esperan de mí cosas contradictorias.",
                "Recibo solicitudes incompatibles de dos o más personas."
            ]
        },
        "Cambio Organizacional": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                2: "Rara vez",
                3: "Alguna vez",
                4: "Algunas veces",
                5: "A menudo",
                6: "Frecuentemente",
                7: "Siempre"
            },
            "Preguntas": [
                "Me consultan sobre cambios propuestos en el trabajo.",
                "Cuando se realizan cambios en el trabajo, tengo claro cómo funcionarán en la práctica.",
                "Estoy claramente informado sobre la naturaleza de los cambios que se producen en esta organización.",
                "Puedo expresar inquietudes sobre cambios que afectan mi trabajo."
            ]
        },
        "Responsabilidad Organizacional": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                2: "Rara vez",
                3: "Alguna vez",
                4: "Algunas veces",
                5: "A menudo",
                6: "Frecuentemente",
                7: "Siempre"
            },
            "Preguntas": [
                "En mi lugar de trabajo la salud física y mental es una prioridad de los líderes.",
                "En mi lugar de trabajo se hacen mediciones periódicas de los niveles de salud mental de las personas.",
                "En mi lugar de trabajo existen recursos accesibles y fáciles de usar para las necesidades relacionadas con la salud mental de las personas.",
                "Recibo entrenamiento periódico sobre pautas para el cuidado de mi salud mental en el trabajo.",
                "En mi lugar de trabajo se comunican claramente los resultados de las acciones implementadas para el cuidado de la salud mental de las personas."
            ]
        },
        "Conflicto Familia-Trabajo": {
            "Tipo": "Likert",
            "Escala": {
                1: "Totalmente en desacuerdo",
                2: "Muy en desacuerdo",
                3: "Algo en desacuerdo",
                4: "Ni de acuerdo ni en desacuerdo",
                5: "Algo de acuerdo",
                6: "Muy de acuerdo",
                7: "Totalmente de acuerdo"
            },
            "Preguntas": [
                "Las demandas de mi familia o cónyuge/pareja interfieren con las actividades relacionadas con el trabajo.",
                "Tengo que posponer las tareas en el trabajo debido a las exigencias de mi tiempo en casa.",
                "Las cosas que quiero hacer en el trabajo no se hacen debido a las demandas de mi familia o mi cónyuge/pareja.",
                "Mi vida hogareña interfiere con mis responsabilidades en el trabajo, como llegar al trabajo a tiempo, realizar las tareas diarias y trabajar.",
                "La tensión relacionada con la familia interfiere con mi capacidad para realizar tareas relacionadas con el trabajo.",
                "Las exigencias de mi trabajo interfieren con mi hogar y mi vida familiar.",
                "La cantidad de tiempo que ocupa mi trabajo dificulta el cumplimiento de las responsabilidades familiares.",
                "Las cosas que quiero hacer en casa no se hacen debido a las exigencias que me impone mi trabajo.",
                "Mi trabajo produce tensión que dificulta el cumplimiento de los deberes familiares.",
                "Debido a deberes relacionados con el trabajo, tengo que hacer cambios en mis planes para las actividades familiares."
            ]
        },
        "Síntomas de Burnout": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                2: "Raramente",
                3: "Algunas veces",
                4: "A menudo",
                5: "Siempre"
            },
            "Preguntas": [
                "En mi trabajo, me siento agotado/a emocionalmente.",
                "Al final del día de trabajo, me resulta difícil recuperar mi energía.",
                "Me siento físicamente agotado/a en mi trabajo.",
                "Me cuesta encontrar entusiasmo por mi trabajo.",
                "Siento una fuerte aversión hacia mi trabajo.",
                "Soy cínico sobre lo que mi trabajo significa para los demás.",
                "Tengo problemas para mantenerme enfocado en mi trabajo.",
                "Cuando estoy trabajando, tengo dificultades para concentrarme.",
                "Cometo errores en mi trabajo porque tengo mi mente en otras cosas.",
                "En mi trabajo, me siento incapaz de controlar mis emociones.",
                "No me reconozco en la forma que reacciono en el trabajo.",
                "Puedo reaccionar exageradamente sin querer."
            ]
        },
        "Compromiso": {
            "Tipo": "Likert",
            "Escala": {
                1: "Muy en desacuerdo",
                2: "Moderadamente en desacuerdo",
                3: "Ligeramente en desacuerdo",
                4: "Ligeramente de acuerdo",
                5: "Moderadamente de acuerdo",
                6: "Muy de acuerdo"
            },
            "Preguntas": [
                "Mi labor contribuye a la misión y visión de la empresa para la que laboro.",
                "Me siento entusiasmado por mi trabajo.",
                "Cuando me levanto en la mañana tengo ganas de ir a trabajar."
            ]
        },
        "Defensa de la Organización": {
            "Tipo": "Likert",
            "Escala": {
                1: "Muy en desacuerdo",
                2: "Moderadamente en desacuerdo",
                3: "Ligeramente en desacuerdo",
                4: "Ligeramente de acuerdo",
                5: "Moderadamente de acuerdo",
                6: "Muy de acuerdo"
            },
            "Preguntas": [
                "Me siento orgulloso de la empresa en la que laboro.",
                "Recomendaría ampliamente a otros trabajar en la empresa en la que laboro.",
                "Me molesta que otros hablen mal de la empresa en la que laboro."
            ]
        },
        "Satisfacción": {
            "Tipo": "Likert",
            "Escala": {
                1: "Muy en desacuerdo",
                2: "Moderadamente en desacuerdo",
                3: "Ligeramente en desacuerdo",
                4: "Ligeramente de acuerdo",
                5: "Moderadamente de acuerdo",
                6: "Muy de acuerdo"
            },
            "Preguntas": [
                "Considero mi trabajo significativo.",
                "Me gusta hacer las tareas y actividades de mi trabajo.",
                "Me siento satisfecho por el salario y los beneficios que recibo en mi trabajo."
            ]
        },
        "Intención de Retiro": {
            "Tipo": "Likert",
            "Escala": {
                1: "Muy en desacuerdo",
                2: "Moderadamente en desacuerdo",
                3: "Ligeramente en desacuerdo",
                4: "Ligeramente de acuerdo",
                5: "Moderadamente de acuerdo",
                6: "Muy de acuerdo"
            },
            "Preguntas": [
                "Me veo trabajando en este lugar en el próximo año.",
                "A menudo considero seriamente dejar mi trabajo actual.",
                "Tengo la intención de dejar mi trabajo actual en los próximos 3 a 6 meses.",
                "He empezado a buscar activamente otro trabajo."
            ]
        },
        "Bienestar Psicosocial (Escala de Afectos)": {
            "Tipo": "Diferencial Semántico",
            "Escala": {
                1: "Insatisfecho",
                7: "Satisfecho"
            },
            "Pares de Adjetivos": [
                "Insatisfecho - Satisfecho",
                "Inseguridad - Seguridad",
                "Intranquilidad - Tranquilidad",
                "Impotencia - Potencia",
                "Malestar - Bienestar",
                "Desconfianza - Confianza",
                "Incertidumbre - Certidumbre",
                "Confusión - Claridad",
                "Desesperanza - Esperanza",
                "Dificultad - Facilidad"
            ]
        },
        "Bienestar Psicosocial (Escala de Competencias)": {
            "Tipo": "Diferencial Semántico",
            "Escala": {
                1: "Insensibilidad",
                7: "Sensibilidad"
            },
            "Pares de Adjetivos": [
                "Insensibilidad - Sensibilidad",
                "Irracionalidad - Racionalidad",
                "Incompetencia - Competencia",
                "Inmoralidad - Moralidad",
                "Maldad - Bondad",
                "Fracaso - Éxito",
                "Incapacidad - Capacidad",
                "Pesimismo - Optimismo",
                "Ineficacia - Eficacia",
                "Inutilidad - Utilidad"
            ]
        },
        "Bienestar Psicosocial (Escala de Expectativas)": {
            "Tipo": "Likert",
            "Escala": {
                1: "Bajando",
                7: "Subiendo"
            },
            "Preguntas": [
                "Mi motivación por el trabajo.",
                "Mi identificación con los valores de la organización.",
                "Mi rendimiento profesional.",
                "Mi capacidad para responder a mi carga de trabajo.",
                "La calidad de mis condiciones de trabajo.",
                "Mi autoestima profesional.",
                "La cordialidad en mi ambiente social de trabajo.",
                "El equilibrio entre mi trabajo y mi vida privada.",
                "Mi confianza en mi futuro profesional.",
                "Mi calidad de vida laboral.",
                "El sentido de mi trabajo.",
                "Mi cumplimiento de las normas de la dirección.",
                "Mi estado de ánimo laboral.",
                "Mis oportunidades de promoción laboral.",
                "Mi sensación de seguridad en el trabajo.",
                "Mi participación en las decisiones de la organización.",
                "Mi satisfacción con el trabajo.",
                "Mi relación profesional.",
                "El nivel de excelencia de mi organización.",
                "Mi eficacia profesional.",
                "Mi compromiso con el trabajo.",
                "Mis competencias profesionales."
            ]
        },
        "Factores de Efectos Colaterales (Escala de Somatización)": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                7: "Siempre"
            },
            "Preguntas": [
                "Trastornos digestivos.",
                "Dolores de cabeza.",
                "Alteraciones de sueño.",
                "Dolores de espalda.",
                "Tensiones musculares."
            ]
        },
        "Factores de Efectos Colaterales (Escala de Desgaste)": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                7: "Siempre"
            },
            "Preguntas": [
                "Sobrecarga de trabajo.",
                "Desgaste emocional.",
                "Agotamiento físico.",
                "Cansancio mental."
            ]
        },
        "Factores de Efectos Colaterales (Escala de Alienación)": {
            "Tipo": "Likert",
            "Escala": {
                1: "Nunca",
                7: "Siempre"
            },
            "Preguntas": [
                "Mal humor.",
                "Baja realización personal.",
                "Trato distante.",
                "Frustración."
            ]
        }
    }
}

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
            response = model.generate_content([prompt])
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
{data_dictionary}

Opciones de análisis:

{opciones_analisis}

Un miembro de la empresa ha hecho la siguiente pregunta:

"{pregunta_usuario}"

Por favor, decide cuál de las opciones de análisis (1-6) es más adecuada para responder a esta pregunta. Solo responde con el número de la opción más relevante. El número debe ser del 1 al 6. Solo puede ser un número.
"""
    respuesta = enviar_prompt(prompt_pregunta)
    return respuesta.strip()

# Utilizar Gemini para extraer variables relevantes de la pregunta del usuario
def obtener_variables_relevantes(pregunta, tipo_variable):
    prompt_variables = f"""
    Tieniendo una base de datos con esta información: 

    {data_dictionary}

    Basado en la siguiente pregunta:

    "{pregunta}"

    Y teniendo en cuenta las columnas y tipos de datos del DataFrame:

    {informacion_datos}

    Identifica las variables que son de tipo '{tipo_variable}' y que son relevantes para responder la pregunta.
    
    Proporciona una lista de variables separadas por comas, sin explicaciones adicionales.

    """
    respuesta = enviar_prompt(prompt_variables)
    # Limpiar y procesar la respuesta de Gemini
    variables = [var.strip() for var in respuesta.split(',') if var.strip() in df.columns]
    return variables

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

def realizar_analisis(opcion, pregunta_usuario, filtros=None):
    resultados = ""
    figuras = []
    if filtros:
        # Aplicar filtros si se proporcionan
        try:
            df_filtrado = df.query(filtros)
        except Exception as e:
            st.write(f"Error al aplicar el filtro: {e}")
            df_filtrado = df.copy()
    else:
        df_filtrado = df.copy()

    # Función para obtener información de la variable desde el diccionario de datos
    def get_variable_info(variable_name):
        for category, variables in data_dictionary.items():
            if variable_name in variables:
                return variables[variable_name]
        return None

    if opcion == '1':
        # Mostrar distribución de una variable categórica
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'categórica')
        if variables_relevantes:
            variable = st.selectbox("Selecciona una variable categórica para analizar:", variables_relevantes)
            conteo = df_filtrado[variable].value_counts()
            resultados += f"Frecuencias de {variable}:\n{conteo.to_string()}\n"

            # Obtener información de la variable desde el diccionario de datos
            variable_info = get_variable_info(variable)
            if variable_info and 'Valores' in variable_info:
                valores = variable_info['Valores']
                if isinstance(valores, list):
                    # Mapear valores si es necesario
                    mapping = {i: v for i, v in enumerate(valores)}
                    df_filtrado[variable] = df_filtrado[variable].map(mapping).fillna(df_filtrado[variable])
                    conteo = df_filtrado[variable].value_counts()

            # Primera visualización: Gráfico de barras
            try:
                fig1, ax1 = plt.subplots()
                conteo.plot(kind='bar', ax=ax1)
                ax1.set_title(f'Distribución de {variable}')
                ax1.set_xlabel(variable)
                ax1.set_ylabel('Frecuencia')
                st.pyplot(fig1)
                figuras.append(fig1)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de barras: {e}")

            # Segunda visualización: Gráfico de pastel
            try:
                fig2, ax2 = plt.subplots()
                conteo.plot(kind='pie', ax=ax2, autopct='%1.1f%%')
                ax2.set_ylabel('')
                ax2.set_title(f'Distribución de {variable}')
                st.pyplot(fig2)
                figuras.append(fig2)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de pastel: {e}")

            # Tercera visualización: Gráfico de barras horizontal
            try:
                fig3, ax3 = plt.subplots()
                conteo.plot(kind='barh', ax=ax3)
                ax3.set_title(f'Distribución de {variable}')
                ax3.set_xlabel('Frecuencia')
                ax3.set_ylabel(variable)
                st.pyplot(fig3)
                figuras.append(fig3)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de barras horizontal: {e}")
        else:
            resultados += "No se encontraron variables categóricas relevantes para la pregunta.\n"

    elif opcion == '2':
        # Calcular estadísticas descriptivas de una variable numérica
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if variables_relevantes:
            variable = st.selectbox("Selecciona una variable numérica para analizar:", variables_relevantes)
            estadisticas = df_filtrado[variable].describe()
            resultados += f"Estadísticas descriptivas de {variable}:\n{estadisticas.to_string()}\n"

            # Primera visualización: Histograma
            try:
                fig1, ax1 = plt.subplots()
                df_filtrado[variable].hist(bins=10, grid=False, ax=ax1)
                ax1.set_title(f'Histograma de {variable}')
                ax1.set_xlabel(variable)
                ax1.set_ylabel('Frecuencia')
                st.pyplot(fig1)
                figuras.append(fig1)
            except Exception as e:
                st.write(f"No se pudo generar el histograma: {e}")

            # Segunda visualización: Boxplot
            try:
                fig2, ax2 = plt.subplots()
                df_filtrado.boxplot(column=variable, ax=ax2)
                ax2.set_title(f'Boxplot de {variable}')
                st.pyplot(fig2)
                figuras.append(fig2)
            except Exception as e:
                st.write(f"No se pudo generar el boxplot: {e}")

            # Tercera visualización: Gráfico de densidad
            try:
                fig3, ax3 = plt.subplots()
                df_filtrado[variable].plot(kind='kde', ax=ax3)
                ax3.set_title(f'Densidad de {variable}')
                ax3.set_xlabel(variable)
                st.pyplot(fig3)
                figuras.append(fig3)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de densidad: {e}")
        else:
            resultados += "No se encontraron variables numéricas relevantes para la pregunta.\n"

    elif opcion == '3':
        # Visualizar la relación entre dos variables numéricas
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if len(variables_relevantes) >= 2:
            variable_x = st.selectbox("Selecciona la variable para el eje X:", variables_relevantes)
            variable_y = st.selectbox("Selecciona la variable para el eje Y:", variables_relevantes)
            resultados += f"Analizando la relación entre {variable_x} y {variable_y}.\n"

            # Primera visualización: Gráfico de dispersión
            try:
                fig1, ax1 = plt.subplots()
                df_filtrado.plot.scatter(x=variable_x, y=variable_y, ax=ax1)
                ax1.set_title(f'Dispersión entre {variable_x} y {variable_y}')
                st.pyplot(fig1)
                figuras.append(fig1)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de dispersión: {e}")

            # Segunda visualización: Gráfico de hexágonos
            try:
                fig2, ax2 = plt.subplots()
                df_filtrado.plot.hexbin(x=variable_x, y=variable_y, gridsize=25, ax=ax2)
                ax2.set_title(f'Hexbin entre {variable_x} y {variable_y}')
                st.pyplot(fig2)
                figuras.append(fig2)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico hexbin: {e}")

            # Tercera visualización: Gráfico de densidad conjunta
            try:
                import seaborn as sns
                fig3, ax3 = plt.subplots()
                sns.kdeplot(data=df_filtrado, x=variable_x, y=variable_y, ax=ax3)
                ax3.set_title(f'Densidad conjunta entre {variable_x} y {variable_y}')
                st.pyplot(fig3)
                figuras.append(fig3)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de densidad conjunta: {e}")

            # Cálculo de la correlación
            try:
                correlacion = df_filtrado[[variable_x, variable_y]].corr().iloc[0,1]
                resultados += f"Correlación entre {variable_x} y {variable_y}: {correlacion}\n"
            except Exception as e:
                st.write(f"No se pudo calcular la correlación: {e}")
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

            # Primera visualización: Histograma
            try:
                fig1, ax1 = plt.subplots()
                df_filtrado[variable].hist(bins=10, grid=False, ax=ax1)
                ax1.set_title(f'Histograma de {variable} después de filtros')
                ax1.set_xlabel(variable)
                ax1.set_ylabel('Frecuencia')
                st.pyplot(fig1)
                figuras.append(fig1)
            except Exception as e:
                st.write(f"No se pudo generar el histograma: {e}")

            # Segunda visualización: Boxplot
            try:
                fig2, ax2 = plt.subplots()
                df_filtrado.boxplot(column=variable, ax=ax2)
                ax2.set_title(f'Boxplot de {variable} después de filtros')
                st.pyplot(fig2)
                figuras.append(fig2)
            except Exception as e:
                st.write(f"No se pudo generar el boxplot: {e}")

            # Tercera visualización: Gráfico de densidad
            try:
                fig3, ax3 = plt.subplots()
                df_filtrado[variable].plot(kind='kde', ax=ax3)
                ax3.set_title(f'Densidad de {variable} después de filtros')
                ax3.set_xlabel(variable)
                st.pyplot(fig3)
                figuras.append(fig3)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de densidad: {e}")
        else:
            resultados += "No se encontraron variables numéricas relevantes para mostrar después de aplicar los filtros.\n"

    elif opcion == '5':
        # Mostrar correlación entre variables numéricas
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica')
        if len(variables_relevantes) >= 2:
            variables_seleccionadas = st.multiselect("Selecciona las variables numéricas para calcular la correlación:", variables_relevantes)
            if len(variables_seleccionadas) >= 2:
                correlacion = df_filtrado[variables_seleccionadas].corr()
                resultados += "Matriz de correlación:\n"
                resultados += correlacion.to_string() + "\n"

                # Primera visualización: Heatmap de correlación
                try:
                    import seaborn as sns
                    fig1, ax1 = plt.subplots()
                    sns.heatmap(correlacion, annot=True, fmt='.2f', cmap='coolwarm', ax=ax1)
                    ax1.set_title('Mapa de calor de la correlación')
                    st.pyplot(fig1)
                    figuras.append(fig1)
                except Exception as e:
                    st.write(f"No se pudo generar el heatmap: {e}")

                # Segunda visualización: Matriz de dispersión
                try:
                    import seaborn as sns
                    fig2 = sns.pairplot(df_filtrado[variables_seleccionadas])
                    st.pyplot(fig2)
                    figuras.append(fig2)
                except Exception as e:
                    st.write(f"No se pudo generar la matriz de dispersión: {e}")

                # Tercera visualización: Gráfico de correlación con valores
                try:
                    fig3, ax3 = plt.subplots()
                    cax = ax3.matshow(correlacion, cmap='coolwarm')
                    fig3.colorbar(cax)
                    ax3.set_xticks(range(len(variables_seleccionadas)))
                    ax3.set_xticklabels(variables_seleccionadas, rotation=90)
                    ax3.set_yticks(range(len(variables_seleccionadas)))
                    ax3.set_yticklabels(variables_seleccionadas)
                    for (i, j), z in np.ndenumerate(correlacion):
                        ax3.text(j, i, '{:0.2f}'.format(z), ha='center', va='center')
                    st.pyplot(fig3)
                    figuras.append(fig3)
                except Exception as e:
                    st.write(f"No se pudo generar el gráfico de correlación: {e}")
            else:
                resultados += "Debes seleccionar al menos dos variables.\n"
        else:
            resultados += "No se encontraron suficientes variables numéricas para calcular la correlación.\n"

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

            # Primera visualización: Gráfico de dispersión con línea de regresión
            try:
                fig1, ax1 = plt.subplots()
                ax1.scatter(X, y, color='blue')
                ax1.plot(X, modelo.predict(X), color='red')
                ax1.set_title(f'Regresión lineal entre {variable_x} y {variable_y}')
                ax1.set_xlabel(variable_x)
                ax1.set_ylabel(variable_y)
                st.pyplot(fig1)
                figuras.append(fig1)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de regresión: {e}")

            # Segunda visualización: Residuales
            try:
                residuales = y - modelo.predict(X)
                fig2, ax2 = plt.subplots()
                ax2.scatter(modelo.predict(X), residuales)
                ax2.hlines(y=0, xmin=modelo.predict(X).min(), xmax=modelo.predict(X).max(), colors='red')
                ax2.set_title('Gráfico de residuales')
                ax2.set_xlabel('Valores predichos')
                ax2.set_ylabel('Residuales')
                st.pyplot(fig2)
                figuras.append(fig2)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de residuales: {e}")

            # Tercera visualización: Distribución de los residuales
            try:
                fig3, ax3 = plt.subplots()
                sns.histplot(residuales, kde=True, ax=ax3)
                ax3.set_title('Distribución de los residuales')
                st.pyplot(fig3)
                figuras.append(fig3)
            except Exception as e:
                st.write(f"No se pudo generar el histograma de residuales: {e}")
        else:
            resultados += "No se encontraron suficientes variables numéricas para realizar la regresión.\n"

    else:
        resultados += "Opción de análisis no reconocida.\n"

    return resultados, figuras

# Función para mostrar un resumen de la base de datos y ejemplos de preguntas
def mostrar_resumen_base_datos():
    resumen = """
Esta aplicación está diseñada para ayudarte a explorar y analizar datos relacionados con el bienestar laboral y la salud mental en el entorno de trabajo. Utiliza una base de datos rica en información sociodemográfica, laboral y en diversas dimensiones de bienestar y salud mental para proporcionarte análisis personalizados y valiosos insights.

¿Cómo utilizar la aplicación?
1. Formula tu pregunta de investigación:

    Ingresa en el campo correspondiente una pregunta relacionada con el bienestar laboral o la salud mental que desees investigar.
    Ejemplo: "¿Cómo afecta el número de horas de trabajo semanal al nivel de estrés en empleados del sector tecnológico?"
    
2. Aplica filtros (opcional):

    Si deseas enfocar tu análisis en un grupo específico, describe los filtros en lenguaje natural.
    Ejemplo: "Analizar únicamente a empleados con más de 5 años de experiencia que trabajan en modalidad remota."

3. Realiza el análisis:

    Haz clic en el botón "Realizar Análisis".
    La aplicación procesará tu pregunta, identificará las variables relevantes y seleccionará el método de análisis más adecuado.

4. Explora los resultados:

    Visualiza los resultados del análisis, incluyendo estadísticas descriptivas, gráficos interactivos y conclusiones interpretadas.
    Puedes descargar un informe completo en PDF que incluye una introducción, metodología, resultados y recomendaciones.


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
   - **Ingreso SalDejaVu Mensual** (Categórica): Rangos desde menos de 1 SMLV hasta más de 10 SMLV.
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
    st.title("Aplicación de Análisis de Datos sobre Salud Organizacional")

    mostrar_resumen_base_datos()

    # Inicializar o restablecer los valores en st.session_state
    if 'pregunta_usuario' not in st.session_state:
        st.session_state['pregunta_usuario'] = ''
    if 'filtro_natural' not in st.session_state:
        st.session_state['filtro_natural'] = ''
    if 'analisis_realizado' not in st.session_state:
        st.session_state['analisis_realizado'] = False

    if not st.session_state['analisis_realizado']:
        st.write("Por favor, ingresa tu pregunta y opcionalmente aplica filtros.")

        st.session_state['pregunta_usuario'] = st.text_input("Ingresa tu pregunta:", value=st.session_state['pregunta_usuario'])
        st.session_state['filtro_natural'] = st.text_input("Si deseas aplicar filtros, por favor descríbelos (opcional):", value=st.session_state['filtro_natural'])

        if st.button("Realizar Análisis"):
            if st.session_state['pregunta_usuario'].strip() == '':
                st.warning("Por favor, ingresa una pregunta para realizar el análisis.")
            else:
                with st.spinner('Procesando...'):
                    filtros_usuario = procesar_filtros(st.session_state['filtro_natural'])
                    if filtros_usuario:
                        st.write(f"El filtro aplicado es: {filtros_usuario}")
                    else:
                        st.write("No se aplicará ningún filtro.")
                    respuesta = procesar_pregunta(st.session_state['pregunta_usuario'])
                    st.write(f"Gemini sugiere la opción de análisis: {respuesta}")
                    resultados, figuras = realizar_analisis(respuesta, st.session_state['pregunta_usuario'], filtros_usuario)
                    st.write("**Resultados del análisis:**")
                    st.write(resultados)
                    # Las figuras ya se muestran en la función realizar_analisis con st.pyplot()
                    # Generar el informe
                    generar_informe(st.session_state['pregunta_usuario'], respuesta, resultados, figuras)
                    # Proporcionar un enlace de descarga para el informe PDF
                    with open('informe_analisis_datos.pdf', 'rb') as f:
                        pdf_data = f.read()
                    b64 = base64.b64encode(pdf_data).decode('utf-8')
                    href = f'<a href="data:application/octet-stream;base64,{b64}" download="informe_analisis_datos.pdf">Descargar Informe en PDF</a>'
                    st.markdown(href, unsafe_allow_html=True)

                    # Marcar que el análisis ha sido realizado
                    st.session_state['analisis_realizado'] = True

                    st.write("Si deseas realizar otra consulta, haz clic en el botón a continuación.")
                    # Mostrar botón para realizar otra consulta
                    if st.button("Realizar otra consulta"):
                        # Reiniciar los valores en st.session_state
                        st.session_state['pregunta_usuario'] = ''
                        st.session_state['filtro_natural'] = ''
                        st.session_state['analisis_realizado'] = False
                        # Reiniciar la aplicación
                        st.rerun()

    else:
        st.write("Si deseas realizar otra consulta, haz clic en el botón a continuación.")
        # Mostrar botón para realizar otra consulta
        if st.button("Realizar otra consulta"):
            # Reiniciar los valores en st.session_state
            st.session_state['pregunta_usuario'] = ''
            st.session_state['filtro_natural'] = ''
            st.session_state['analisis_realizado'] = False
            # Reiniciar la aplicación
            st.rerun()

def generar_informe(pregunta_usuario, opcion_analisis, resultados, figuras):
    pdf = PDFReport()

    # Extract relevant variables
    variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'todas')
    data_dictionary_relevante = {}
    for categoria, variables in data_dictionary.items():
        variables_relevantes_categoria = {}
        for variable in variables:
            if variable in variables_relevantes:
                variables_relevantes_categoria[variable] = variables[variable]
        if variables_relevantes_categoria:
            data_dictionary_relevante[categoria] = variables_relevantes_categoria

    # Introducción
    pdf.chapter_title('Introducción')

    prompt_introduccion = f"""
    Utilizando la siguiente pregunta de investigación:

    "{pregunta_usuario}"

    Y el método de análisis correspondiente a la opción {opcion_analisis}, por favor genera una introducción que explique la relevancia de la pregunta y el método utilizado para analizar la información de la base de datos.

    Para interpretar correctamente los resultados del análisis, aquí tienes un diccionario de datos de las variables relevantes:

    {data_dictionary_relevante}

    Por favor, utiliza esta información para contextualizar y explicar los hallazgos en la introducción, asegurándote de interpretar adecuadamente los valores de las variables según su significado.
    """
    introduccion = enviar_prompt(prompt_introduccion)
    pdf.chapter_body(introduccion)

    # Resultados
    pdf.chapter_title('Resultados')
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

    Y considerando la siguiente pregunta de investigación:

    "{pregunta_usuario}"

    Utilizando el siguiente diccionario de datos para interpretar correctamente los valores:

    {data_dictionary}

    Por favor, proporciona conclusiones y recomendaciones que puedan ser útiles para la empresa, asegurándote de interpretar correctamente los valores de las variables y los hallazgos del análisis según su significado.

    Si los datos no son suficientes para responder a la pregunta o no se generaron datos, integra la respuesta con teoría y fundamenta tus conclusiones y recomendaciones en la literatura académica real, citando en formato APA séptima edición y garantizando que las fuentes citadas existen.

    Responde desde la perspectiva de la psicología organizacional y la psicología de la salud, y asegúrate de que la interpretación de los resultados y las recomendaciones respondan a la pregunta planteada.
    """
    conclusiones = enviar_prompt(prompt_conclusiones)
    pdf.chapter_body(conclusiones)

    # Guardar el informe en PDF
    nombre_informe = 'informe_analisis_datos.pdf'
    pdf.output(nombre_informe)
    st.write(f"Informe generado y guardado como {nombre_informe}")

# Clase PDFReport modificada
class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.add_page()
        self.set_auto_page_break(auto=True, margin=15)
        
        # Registrar la fuente DejaVu Sans
        self.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        self.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf', uni=True)
        self.set_font('DejaVu', '', 12)

    def header(self):
        # Encabezado del documento
        self.set_font('DejaVu', 'B', 16)
        self.cell(0, 10, 'Informe de Análisis de Datos', ln=True, align='C')
        self.ln(10)

    def chapter_title(self, label):
        # Título de cada sección
        self.set_font('DejaVu', 'B', 14)
        self.cell(0, 10, label, ln=True)
        self.ln(5)

    def chapter_body(self, text):
        # Cuerpo de texto de cada sección
        self.set_font('DejaVu', '', 12)
        self.multi_cell(0, 10, text)
        self.ln()

    def insert_image(self, image_path):
        # Insertar una imagen en el PDF
        self.image(image_path, w=180)
        self.ln()

if __name__ == "__main__":
    main()
