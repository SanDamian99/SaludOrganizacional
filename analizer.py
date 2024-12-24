# Importar librerías necesarias
import streamlit as st
import pandas as pd
import time
import random
import seaborn as sns
from datetime import datetime
from datetime import date, timedelta
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError
import matplotlib.pyplot as plt
from fpdf import FPDF, HTMLMixin
import re
import markdown
import io
import base64
import os
from fpdf.enums import XPos, YPos
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus.doctemplate import LayoutError
from bs4 import BeautifulSoup
from PIL import Image as PILImage


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
    "max_output_tokens": 8190,
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
        "Ingreso Salarial Mensual": {
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

1. **Distribución de variable categórica:** Explora cómo se distribuyen los datos en una variable categórica (no numérica). Muestra la frecuencia de cada categoría mediante tablas y gráficos (barras, pastel, barras horizontales). 

   *Ejemplo:* Si eliges la variable "color", el análisis mostrará cuántas veces aparece cada color (rojo, azul, verde, etc.) en el conjunto de datos.

2. **Estadísticas descriptivas de variable numérica:**  Calcula y muestra las estadísticas descriptivas (media, mediana, desviación estándar, mínimo, máximo, etc.) de una variable numérica, proporcionando un resumen de su distribución.  Incluye visualizaciones como histogramas, boxplots y gráficos de densidad para comprender la forma de la distribución, identificar valores atípicos y analizar la dispersión de los datos.

   *Ejemplo:*  Si eliges la variable "edad", el análisis calculará la edad promedio, la edad que se encuentra en el medio del conjunto de datos,  cómo se agrupan las edades, etc.

3. **Relación entre dos variables numéricas:** Analiza la relación entre dos variables numéricas. Se mostrarán gráficos de dispersión, hexágonos y densidad conjunta para visualizar la correlación entre las variables. También se calculará el coeficiente de correlación para cuantificar la fuerza y dirección de la relación.

   *Ejemplo:*  Si eliges las variables "ingresos" y "gastos", el análisis mostrará si existe una relación (positiva, negativa o nula) entre ambas.

4. **Filtrar datos y mostrar estadísticas:** Permite filtrar los datos según criterios específicos y luego calcular estadísticas descriptivas de una variable numérica en el conjunto de datos filtrado.  Se incluyen visualizaciones como histogramas, boxplots y gráficos de densidad para el análisis del subconjunto de datos.

   *Ejemplo:* Puedes filtrar los datos para incluir solo a las personas mayores de 30 años y luego analizar la distribución de sus ingresos.

5. **Correlación entre variables numéricas:** Calcula la correlación entre múltiples variables numéricas y muestra los resultados en una matriz de correlación.  Se incluyen visualizaciones como mapas de calor, matrices de dispersión y gráficos de correlación para identificar patrones y relaciones entre las variables.

   *Ejemplo:*  Si seleccionas "edad", "ingresos" y "nivel educativo", el análisis mostrará la correlación entre cada par de variables.

6. **Análisis de regresión simple:** Realiza un análisis de regresión lineal simple para modelar la relación entre dos variables numéricas. Se mostrará el coeficiente de determinación (R^2), el intercepto y los coeficientes del modelo.  Se incluyen visualizaciones como gráficos de dispersión con línea de regresión, gráficos de residuales y la distribución de los residuales para evaluar la calidad del modelo.

   *Ejemplo:*  Puedes analizar cómo la variable "años de experiencia" (variable independiente) afecta a la variable "salario" (variable dependiente).
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

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus.doctemplate import LayoutError

import os
import markdown
from bs4 import BeautifulSoup

######################################################
# CLASE PDFReport
######################################################
class PDFReport:
    def __init__(self, filename):
        self.filename = filename
        self.elements = []
        self.styles = getSampleStyleSheet()
        self.doc = SimpleDocTemplate(
            self.filename,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=50*mm,
            bottomMargin=20*mm
        )
        # Estilos personalizados
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=16,
            spaceAfter=12,
            textColor=colors.black
        ))
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            fontName='Helvetica',
            fontSize=12,
            leading=14,
            alignment=4,  # 4 = TA_JUSTIFY, 1 = TA_CENTER, etc.
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            textColor=colors.black
        ))
        self.styles.add(ParagraphStyle(
            name='DataSectionTitle',
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
            textColor=colors.white,
            backColor=colors.purple,
            alignment=1,  # TA_CENTER
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='CustomItalic',
            fontName='Helvetica-Oblique',
            fontSize=12,
            leading=14,
            textColor=colors.black
        ))
        self.styles.add(ParagraphStyle(
            name='Footer',
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.white
        ))
        self.styles.add(ParagraphStyle(
            name='Heading',
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
            spaceAfter=12,
            textColor=colors.black
        ))

    def header(self, canvas, doc):
            """
            Encabezado del documento: una imagen que cubre toda la parte superior (opcional).
            """
            canvas.saveState()
            header_image = 'Captura de pantalla 2024-11-25 a la(s) 9.02.19 a.m..png'
            if os.path.isfile(header_image):
                canvas.drawImage(header_image, 0, A4[1]-40*mm, width=A4[0], height=40*mm)
            else:
                canvas.setFont('Helvetica-Bold', 16)
                header_text = 'Informe de Análisis de Datos'
                header_text = clean_text(header_text)
                canvas.drawCentredString(A4[0]/2.0, A4[1]-30*mm, header_text)
            canvas.restoreState()
            
    def footer(self, canvas, doc):
        """
        Pie de página
        """
        canvas.saveState()
        canvas.setFillColor(colors.black)
        canvas.rect(0, 0, A4[0], 15*mm, fill=1)
        footer_text = 'Informe generado con IA. Puede contener errores e imprecisiones.'
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(15*mm, 5*mm, clean_text(footer_text))
        page_number_text = f'Página {doc.page}'
        canvas.drawRightString(A4[0]-15*mm, 5*mm, page_number_text)
        canvas.restoreState()

    def header_footer(self, canvas, doc):
        self.header(canvas, doc)
        self.footer(canvas, doc)

    def chapter_title(self, text):
        text = clean_text(text)
        paragraph = Paragraph(text, self.styles['CustomTitle'])
        self.elements.append(paragraph)

    def chapter_body(self, text):
        """
        Añade el cuerpo de texto manejando el formato Markdown
        (encabezados, listas, saltos, etc.) recursivamente.
        """
        text = clean_text(text)
        html = markdown.markdown(text)
        soup = BeautifulSoup(html, 'html.parser')

        # Recorremos TODOS los nodos relevantes recursivamente
        for block in soup.find_all():
            if block.name in ['p', 'h1','h2','h3','h4','h5','h6','ul','ol','li','br']:
                block_html = str(block)
                if block.name in ['h1','h2','h3','h4','h5','h6']:
                    style = self.styles['Heading']
                else:
                    style = self.styles['CustomBodyText']
                paragraph = Paragraph(block_html, style)
                self.elements.append(paragraph)

        self.elements.append(Spacer(1, 12))

    def insert_data_section(self, text):
        title = Paragraph('Datos generados por el modelo', self.styles['DataSectionTitle'])
        self.elements.append(title)

        text = clean_text(text)
        html = markdown.markdown(text)
        soup = BeautifulSoup(html, 'html.parser')

        for block in soup.find_all():
            if block.name in ['p','h1','h2','h3','h4','h5','h6','ul','ol','li','br']:
                block_html = str(block)
                paragraph = Paragraph(block_html, self.styles['CustomBodyText'])
                self.elements.append(paragraph)

        self.elements.append(Spacer(1, 12))

    def insert_image(self, image_path, max_width=480):
        """
        Ajusta la imagen para que no exceda max_width, preservando relación de aspecto.
        """
        if os.path.isfile(image_path):
            with PILImage.open(image_path) as im:
                orig_width, orig_height = im.size
            if orig_width == 0:
                new_width = max_width
                new_height = max_width
            else:
                ratio = float(orig_height) / float(orig_width)
                new_width = min(max_width, orig_width)
                new_height = new_width * ratio

            img = RLImage(image_path, width=new_width, height=new_height)
            self.elements.append(img)
            self.elements.append(Spacer(1, 12))
        else:
            self.elements.append(Paragraph('Imagen no encontrada', self.styles['CustomItalic']))
            self.elements.append(Spacer(1, 12))

    def resultados_recomendaciones(self, text):
        self.chapter_title('Resultados y Recomendaciones')
        self.chapter_body(text)

    def build_pdf(self):
        try:
            self.doc.build(self.elements, onFirstPage=self.header_footer, onLaterPages=self.header_footer)
        except LayoutError as e:
            raise e

# Funciones de limpieza de texto
def break_long_words(text, max_length=50):
    """
    Inserta guiones en palabras que excedan el máximo permitido para evitar errores de renderizado.
    """
    words = text.split()
    new_words = []
    for word in words:
        while len(word) > max_length:
            new_words.append(word[:max_length-1] + '-')
            word = word[max_length-1:]
        new_words.append(word)
    return ' '.join(new_words)


def clean_text(text):
    """
    Reemplaza caracteres no soportados y limpia el texto,
    intentando conservar la estructura para Markdown -> HTML.
    """
    # Diccionario de reemplazos para caracteres no soportados
    replacements = {
        '≈': 'aprox.',
        '≤': '<=',
        '≥': '>=',
        '≠': '!=',
        '√': 'raíz',
        '∞': 'infinito',
        'π': 'pi',
        '∑': 'sumatoria',
        '∆': 'delta',
        '∫': 'integral',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    # Eliminar caracteres no soportados en PDF
    text = text.encode('latin-1', 'ignore').decode('latin-1')

    # Insertar guiones en palabras largas
    text = break_long_words(text, max_length=50)
    return text

def generar_informe(pregunta_usuario, opcion_analisis, resultados, figuras):
    pdf = PDFReport('informe_analisis_datos.pdf')

    # Extraer variables relevantes
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

    Y el método de análisis correspondiente a la opción {opcion_analisis}, recuerda que estas eran las opciones: {opciones_analisis}. 
    
    Por favor genera una introducción que explique la relevancia de la pregunta y el método utilizado para analizar la información de la base de datos.

    Para interpretar correctamente los resultados del análisis, aquí tienes un diccionario de datos de las variables relevantes:

    {data_dictionary_relevante}

    Por favor, utiliza esta información para contextualizar y explicar el planteamiento del análisis, asegurándote de interpretar adecuadamente los valores de las variables según su significado.
    """
    
    introduccion = enviar_prompt(prompt_introduccion)
    pdf.chapter_body(introduccion)

    # Datos generados por el modelo
    pdf.insert_data_section(resultados)

    # Insertar las figuras generadas
    for idx, fig in enumerate(figuras):
        img_path = f'figura_{idx}.png'
        fig.savefig(img_path)
        pdf.insert_image(img_path)
        # Opcional: eliminar la imagen temporal
        # os.remove(img_path)

    # Conclusiones y Recomendaciones
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
    pdf.resultados_recomendaciones(conclusiones)

    # Guardar el informe en PDF
    try:
        pdf.build_pdf()
        st.write(f"Informe generado y guardado como {pdf.filename}")
    except Exception as e:
        st.write(f"Error al generar el PDF: {e}")

respuesta_map = {
    "Nunca": 1,
    "Rara vez": 2,
    "Alguna vez": 3,
    "Algunas veces": 4,
    "A menudo": 5,
    "Frecuentemente": 6,
    "Siempre": 7
}

# Función para mapear valores
def mapear_valores(serie):
    return serie.replace(respuesta_map).apply(pd.to_numeric, errors='coerce')
dimensiones = {
    "Control del Tiempo": [
        "Tengo la opción de decidir qué hago en mi trabajo.",
        "Tengo   algo que decir sobre la forma en que hago mi trabajo.",
        "Tengo   voz y voto sobre mi propio ritmo de trabajo.",
        "Me   presionan para que trabaje muchas horas.",
        "Tengo   algunos plazos de entrega inalcanzables.",
        "Tengo   presiones de tiempo poco realistas.",
        "Tengo   que descuidar algunas tareas porque tengo mucho que hacer."
    ],
    "Compromiso del Líder": [
        "Puedo confiar en mi líder para que me ayude con un problema laboral.",
        "Si el trabajo se pone difícil, mi líder me ayudará.",
        "Recibo la ayuda y el apoyo que necesito de mi líder.",
        "Mi líder está dispuesto a escuchar mis problemas relacionados con el trabajo.",
        "Siento que mi líder valora mis contribuciones a esta organización.",
        "Mi líder me da suficiente crédito por mi trabajo duro.",
        "Mi líder me anima en mi trabajo con elogios y agradecimientos."
    ],
    "Apoyo del Grupo": [
        "Si el trabajo se pone difícil, mis compañeros de trabajo me ayudarán.",
        "Recibo la ayuda y el apoyo que necesito de mis compañeros de trabajo.",
        "Mis compañeros de trabajo están dispuestos a escuchar mis problemas laborales."
    ],
    "Claridad de Rol": [
        "Tengo claro lo que se espera de mí en el trabajo.",
        "Sé cómo hacer mi trabajo.",
        "Tengo claro cuáles son mis deberes y responsabilidades.",
        "Entiendo cómo mi trabajo encaja en el objetivo general de la organización.",
        "Diferentes grupos en el trabajo me exigen cosas que son difíciles de hacer al mismo tiempo.",
        "Diferentes personas en el trabajo esperan de mí cosas contradictorias.",
        "Recibo solicitudes incompatibles de dos o más personas."
    ],
    "Cambio Organizacional": [
        "Me consultan sobre cambios propuestos en el trabajo.",
        "Cuando se realizan cambios en el trabajo, tengo claro cómo funcionarán en la práctica.",
        "Estoy claramente informado sobre la naturaleza de los cambios que se producen en esta organización.",
        "Puedo expresar inquietudes sobre cambios que afectan mi trabajo."
    ],
    "Responsabilidad Organizacional": [
        "En mi lugar de trabajo la salud física y mental es un prioridad de los líderes.",
        "En mi lugar de trabajo se hacen mediciones periódicas de los niveles de salud mental de las personas.",
        "En mi lugar de trabajo existen recursos accesibles y fáciles de usar para las necesidades relacionadas con la salud mental de las personas.",
        "Recibo entrenamiento periódico sobre pautas para el cuidado de mi salud mental en el trabajo.",
        "En mi lugar de trabajo se comunican claramente los resultados de las acciones implementadas para el cuidado de la salud mental de las personas."
    ],
    "Conflicto Familia-Trabajo": [
        "Las   demandas de mi familia o cónyuge / pareja interfieren con las actividades   relacionadas con el trabajo.",
        "Tengo   que posponer las tareas en el trabajo debido a las exigencias de mi tiempo en   casa.",
        "Las   cosas que quiero hacer en el trabajo no se hacen debido a las demandas de mi   familia o mi cónyuge / pareja.",
        "Mi vida   hogareña interfiere con mis responsabilidades en el trabajo, como llegar al   trabajo a tiempo, realizar las tareas diarias y trabajar.",
        "La   tensión relacionada con la familia interfiere con mi capacidad para realizar   tareas relacionadas con el trabajo.",
        "Las exigencias de mi trabajo interfieren con mi hogar y mi vida familiar.",
        "La cantidad de tiempo que ocupa mi trabajo dificulta el cumplimiento de las responsabilidades familiares.",
        "Las cosas que quiero hacer en casa no se hacen debido a las exigencias que me impone mi trabajo.",
        "Mi trabajo produce tensión que dificulta el cumplimiento de los deberes familiares.",
        "Debido a deberes relacionados con el trabajo, tengo que hacer cambios en mis planes para las actividades familiares."
    ],
    "Síntomas de Burnout": [
        "En mi   trabajo, me siento agotado/a emocionalmente.",
        "Al final   del día de trabajo, me resulta difícil recuperar mi energía.",
        "Me   siento físicamente agotado/a en mi trabajo.",
        "Me   cuesta encontrar entusiasmo por mi trabajo.",
        "Siento   una fuerte aversión hacia mi trabajo.",
        "Soy   cínico (despreocupado) sobre lo que mi trabajo significa para los demás.",
        "Tengo   problemas para mantenerme enfocado en mi trabajo.",
        "Cuando   estoy trabajando, tengo dificultades para concentrarme.",
        "Cometo   errores en mi trabajo, porque tengo mi mente en otras cosas.",
        "En mi   trabajo, me siento incapaz de controlar mis emociones.",
        "No me   reconozco en la forma que reacciono en el trabajo.",
        "Puedo   reaccionar exageradamente sin querer."
    ],
    "Compromiso": [
        "Mi labor   contribuye a la misión y visión de la empresa para la que laboro.",
        "Me   siento entusiasmado por mi trabajo.",
        "Cuando   me levanto en la mañana tengo ganas de ir a trabajar."
    ],
    "Defensa de la Organización": [
        "Me   siento orgulloso de la empresa en la que laboro.",
        "Recomendaría   ampliamente a otros trabajar en la empresa en la que laboro.",
        "Me   molesta que otros hablen mal de la empresa en la que laboro."
    ],
    "Satisfacción": [
        "Considero   mi trabajo significativo.",
        "Me gusta   hacer las tareas y actividades de mi trabajo.",
        "Me   siento satisfecho por el salario y los beneficios que recibo en mi trabajo."
    ],
    "Intención de Retiro": [
        "Me veo   trabajando en este lugar en el próximo año.",
        "A menudo   considero seriamente dejar mi trabajo actual.",
        "Tengo la   intención de dejar mi trabajo actual en los próximos 3 a 6 meses.",
        "He   empezado a buscar activamente otro trabajo."
    ],
    "Bienestar Psicosocial (Escala de Afectos)": [
        "Marque para cada uno de los pares de adjetivos dispuestos, el número que mejor se identifica.  \n",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10"
    ],
    "Bienestar Psicosocial (Escala de Competencias)": [
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20"
    ],
    "Bienestar Psicosocial (Escala de Expectativas)": [
        "Mi motivación por   el trabajo",
        "Mi capacidad para   responder a mi cargo de trabajo ",
        "Mi autoestima   profesional",
        "Mi confianza en mi   futuro profesional",
        "El sentido de mi   trabajo",
        "Mi estado de ánimo   laboral ",
        "Mi sensación de   seguridad en el trabajo",
        "MI eficacia   profesional",
        "Mi compromiso con   el trabajo",
        "Mis competencias   profesionales"
    ],
    "Factores de Efectos Colaterales (Escala de Somatización)": [
        "Trastornos   digestivos",
        "Dolores de cabeza",
        "Alteraciones de   sueño",
        "Dolores de espalda",
        "Tensiones   musculares"
    ],
    "Factores de Efectos Colaterales (Escala de Desgaste)": [
        "Sobrecarga de   trabajo",
        "Desgaste emocional",
        "Agotamiento físico",
        "Cansancio   mental "
    ],
    "Factores de Efectos Colaterales (Escala de Alienación)": [
        "Mal humor ",
        "Baja realización   personal",
        "Trato distante",
        "Frustración "
    ]
}

def generar_informe_general(df, fecha_inicio, fecha_fin):
    import math

    # Filtrar por rango de fechas usando 'Hora de inicio'
    df['Hora de inicio'] = pd.to_datetime(df['Hora de inicio'], errors='coerce')
    df_filtrado = df[(df['Hora de inicio'] >= pd.to_datetime(fecha_inicio)) & (df['Hora de inicio'] <= pd.to_datetime(fecha_fin))]

    if df_filtrado.empty:
        return "No se encontraron datos en el rango de fechas especificado.", []
    
    # Convertir todo a valores numéricos según la escala fija para las dimensiones
    df_num = df_filtrado.copy()
    for col in df_num.columns:
        if df_num[col].dtype == object:
            df_num[col] = mapear_valores(df_num[col])

    # Definir umbrales:
    # Fortaleza: >=5
    # Riesgo: <=3
    # Intermedio: 3<valor<5

    # Calcular promedios por dimensión
    resultados = {}
    for dim, vars_dim in dimensiones.items():
        vars_exist = [v for v in vars_dim if v in df_num.columns]
        if vars_exist:
            prom = df_num[vars_exist].mean(skipna=True, numeric_only=True).mean()
            resultados[dim] = prom

    fortalezas = [(d,v) for d,v in resultados.items() if v >=5]
    riesgos = [(d,v) for d,v in resultados.items() if v <=3]
    intermedios = [(d,v) for d,v in resultados.items() if v>3 and v<5]

    # Crear un resumen ejecutivo con Gemini
    prompt_resumen = f"""
    Estas son las dimensiones y sus promedios:
    Fortalezas: {fortalezas}
    Riesgos: {riesgos}
    Intermedios: {intermedios}

    Genera un resumen ejecutivo describiendo las fortalezas, las debilidades (riesgos) y las dimensiones intermedias, 
    ofreciendo una visión general de la situación y recomendaciones generales.
    """
    resumen_ejecutivo = enviar_prompt(prompt_resumen)

    prompt_conclusiones = f"""
    Basándote en los resultados:
    Fortalezas: {fortalezas}
    Riesgos: {riesgos}
    Intermedios: {intermedios}

    Proporciona conclusiones detalladas y recomendaciones prácticas para mejorar las áreas en riesgo y mantener las fortalezas, 
    desde una perspectiva organizacional, considerando aspectos psicosociales y del bienestar laboral.
    """
    conclusiones = enviar_prompt(prompt_conclusiones)

    figuras = []
    fig_titles = []  # Para llevar un índice de figuras

    # Función para determinar estado de la dimensión
    def estado_dimension(valor):
        if valor >= 5:
            return 'Fortaleza', 'green'
        elif valor <= 3:
            return 'Riesgo', 'red'
        else:
            return 'Intermedio', 'yellow'

    # ---------------------------
    # 1. Semáforo en forma de matriz de subplots
    # ---------------------------
    dims_list = list(resultados.items())  # [(dim, val), (dim, val), ...]
    n_dims = len(dims_list)
    cols = 3  # Ajustar si deseas más o menos columnas
    rows = math.ceil(n_dims / cols)

    fig_semaforo, axes_semaforo = plt.subplots(rows, cols, figsize=(cols*2.5, rows*1.5))
    axes_semaforo = axes_semaforo.flatten() if n_dims > 1 else [axes_semaforo]

    for idx, (dim, val) in enumerate(dims_list):
        estado, color = estado_dimension(val)
        ax = axes_semaforo[idx]
        ax.set_facecolor(color)
        ax.text(0.5, 0.5, f"{dim}\n{estado}\nProm: {val:.2f}", ha='center', va='center', 
                fontsize=8, color='black', wrap=True)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(0,1)
        ax.set_ylim(0,1)

    # Ocultar ejes sobrantes si hay menos dimensiones que subplots
    for j in range(idx+1, len(axes_semaforo)):
        axes_semaforo[j].set_visible(False)

    fig_semaforo.suptitle("Semáforo de Dimensiones (Resumen)", fontsize=12)
    fig_semaforo.tight_layout()
    figuras.append(fig_semaforo)
    fig_titles.append("Figura: Semáforo de Dimensiones")

    # ---------------------------
    # 2. Análisis por sexo, edad y hijos
    # ---------------------------
    df_cat = df_filtrado.copy()

    # Convertir Edad a numérico si posible
    if 'Edad' in df_cat.columns:
        df_cat['Edad'] = pd.to_numeric(df_cat['Edad'], errors='coerce')

    # Crear rangos de edad
    if 'Edad' in df_cat.columns:
        bins = [0, 24, 34, 44, 200]
        labels = ['<25', '25-34', '35-44', '45+']
        df_cat['Rango_Edad'] = pd.cut(df_cat['Edad'], bins=bins, labels=labels, include_lowest=True)
    else:
        df_cat['Rango_Edad'] = 'SinDatoEdad'

    # Crear variable Hijos (0/1)
    if 'Numero de hijos' in df_cat.columns:
        df_cat['Hijos'] = df_cat['Numero de hijos'].apply(lambda x: 0 if str(x).strip().lower()=='sin hijos' else 1)
    else:
        df_cat['Hijos'] = 0

    # Recalcular df_mix con valores numéricos
    df_mix = df_filtrado.copy()
    for c in df_mix.columns:
        if df_mix[c].dtype == object:
            df_mix[c] = mapear_valores(df_mix[c])

    # Añadimos las columnas auxiliares al df_mix
    df_mix['Rango_Edad'] = df_cat['Rango_Edad']
    df_mix['Hijos'] = df_cat['Hijos']

    # Para cada dimensión, generamos UNA figura con 3 subplots (sexo, edad, hijos)
    for dim, vars_dim in dimensiones.items():
        vars_exist = [v for v in vars_dim if v in df_mix.columns]
        if not vars_exist:
            continue

        # Creamos la figura con 3 columnas (Sexo, Rango_Edad, Hijos)
        fig_dim, axs_dim = plt.subplots(1, 3, figsize=(9,3))
        fig_dim.suptitle(f"{dim} comparado por Sexo, Rango de Edad y Hijos", fontsize=10)

        # Subplot 0: por sexo
        if 'Sexo' in df_mix.columns:
            df_sexo = df_mix.groupby('Sexo')[vars_exist].mean().mean(axis=1)
            ax0 = axs_dim[0]
            if not df_sexo.empty:
                df_sexo.plot(kind='bar', color='lightblue', ax=ax0)
                ax0.set_title("Por Sexo", fontsize=8)
                ax0.set_xlabel('')
                ax0.set_ylabel('Promedio')
            else:
                ax0.set_visible(False)
        else:
            axs_dim[0].set_visible(False)

        # Subplot 1: por rango de edad
        if 'Rango_Edad' in df_mix.columns:
            df_edad = df_mix.groupby('Rango_Edad')[vars_exist].mean().mean(axis=1)
            ax1 = axs_dim[1]
            if not df_edad.empty:
                df_edad.plot(kind='bar', color='lightgreen', ax=ax1)
                ax1.set_title("Por Rango de Edad", fontsize=8)
                ax1.set_xlabel('')
                ax1.set_ylabel('Promedio')
            else:
                ax1.set_visible(False)
        else:
            axs_dim[1].set_visible(False)

        # Subplot 2: por hijos
        if 'Hijos' in df_mix.columns:
            df_hijos = df_mix.groupby('Hijos')[vars_exist].mean().mean(axis=1)
            ax2 = axs_dim[2]
            if not df_hijos.empty:
                df_hijos_index = df_hijos.rename(index={0:'Sin hijos',1:'Con hijos'})
                df_hijos_index.plot(kind='bar', color='orange', ax=ax2)
                ax2.set_title("Por Hijos", fontsize=8)
                ax2.set_xlabel('')
                ax2.set_ylabel('Promedio')
            else:
                ax2.set_visible(False)
        else:
            axs_dim[2].set_visible(False)

        plt.tight_layout()
        figuras.append(fig_dim)
        fig_titles.append(f"Figura: Comparación por Sexo, Edad, Hijos - {dim}")

    # ---------------------------
    # 3. Gráficas descriptivas para cada variable según su tipo
    # ---------------------------
    for col in df_filtrado.columns:
        if col in ["ID", "Hora de inicio", "Hora de finalización", "Correo electrónico", "Nombre", "Column"]:
            continue

        # Para cada variable, creamos UNA figura con 2 subplots (si es numérica),
        # o 1 subplot si es categórica
        if df_filtrado[col].dtype == object:
            conteo = df_filtrado[col].value_counts()
            if not conteo.empty:
                fig_c, ax_c = plt.subplots(figsize=(5,3))
                conteo.plot(kind='bar', ax=ax_c, color='skyblue')
                ax_c.set_title(f'Distribución de {col}')
                ax_c.set_xlabel(col)
                ax_c.set_ylabel('Frecuencia')
                plt.tight_layout()
                figuras.append(fig_c)
                fig_titles.append(f"Figura: Distribución de {col}")
        else:
            # Histograma y Boxplot en una sola figura con 2 subplots
            fig_desc, (ax_h, ax_b) = plt.subplots(1, 2, figsize=(8,3))
            # Histograma
            df_filtrado[col].dropna().hist(bins=10, ax=ax_h, color='lightgreen')
            ax_h.set_title(f'Histograma de {col}')
            ax_h.set_xlabel(col)
            ax_h.set_ylabel('Frecuencia')

            # Boxplot
            df_filtrado[[col]].boxplot(ax=ax_b)
            ax_b.set_title(f'Boxplot de {col}')

            plt.tight_layout()
            figuras.append(fig_desc)
            fig_titles.append(f"Figura: Descriptivas de {col}")

    # Crear texto del informe
    informe = []
    informe.append("Este informe presenta un análisis general de las dimensiones de bienestar laboral en el rango de fechas especificado.\n")
    informe.append("**Resumen Ejecutivo:**\n")
    informe.append(resumen_ejecutivo + "\n\n")
    informe.append("**Clasificación de Dimensiones:**\n")
    if fortalezas:
        informe.append("**Fortalezas:**\n")
        for f, val in fortalezas:
            informe.append(f"- {f} (Promedio: {val:.2f})\n")
    else:
        informe.append("No se identificaron fortalezas.\n")

    informe.append("\n")
    if riesgos:
        informe.append("**Riesgos:**\n")
        for r, val in riesgos:
            informe.append(f"- {r} (Promedio: {val:.2f})\n")
    else:
        informe.append("No se identificaron riesgos.\n")

    informe.append("\n")
    if intermedios:
        informe.append("**Intermedios:**\n")
        for i, val in intermedios:
            informe.append(f"- {i} (Promedio: {val:.2f})\n")
    else:
        informe.append("No se identificaron dimensiones en nivel intermedio.\n")

    informe.append("\n**Conclusiones y Recomendaciones:**\n")
    informe.append(conclusiones)
    informe.append("\n")

    # Índice de figuras
    if fig_titles:
        informe.append("\n**Índice de Figuras:**\n")
        for idx, t in enumerate(fig_titles, start=1):
            informe.append(f"Figura {idx}: {t}\n")

    informe_texto = "".join(informe)

    return informe_texto, figuras


# Función principal
def main():
    st.title("Aplicación de Análisis de Datos sobre Salud Organizacional")

    mostrar_resumen_base_datos()
    
    # Campos para fecha
    fecha_inicio = st.date_input("Fecha de inicio",date.today() - timedelta(days=30))
    fecha_fin = st.date_input("Fecha de fin", date.today())

    # Botón para generar informe general
    if st.button("Generar Informe General"):
        with st.spinner("Generando informe general..."):
            informe_texto, figs = generar_informe_general(df, fecha_inicio, fecha_fin)
            st.write(informe_texto)
            # Generar PDF
            pdf_general = PDFReport('informe_general.pdf')
            pdf_general.chapter_title("Informe General de Bienestar Laboral")
            pdf_general.chapter_body(informe_texto)
            for idx, f in enumerate(figs):
                img_path = f'figura_general_{idx}.png'
                f.savefig(img_path)
                pdf_general.insert_image(img_path)
            pdf_general.build_pdf()

            with open('informe_general.pdf', 'rb') as f:
                pdf_data = f.read()
            b64 = base64.b64encode(pdf_data).decode('utf-8')
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="informe_general.pdf">Descargar Informe General en PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
    
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
                        st.experimental_rerun()

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
        
if __name__ == "__main__":
    main()
