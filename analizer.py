# Importar librerías necesarias
import streamlit as st
import difflib
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
import math
from scipy.stats import chi2_contingency

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

df.dropna(axis=1, how='all', inplace=True)

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
7. **Tablas de Contingencia y Chi-cuadrado:** Permite analizar la relación entre dos variables categóricas o entre una variable categórica (agrupando valores) y una numérica. Se calculará la tabla de contingencia y se realizará la prueba Chi-cuadrado para ver la asociación. Si es variable numérica, se agrupará en rangos para generar la tabla.

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

Por favor, decide cuál de las opciones de análisis (1-7) es más adecuada para responder a esta pregunta. Solo responde con el número de la opción más relevante. El número debe ser del 1 al 6. Solo puede ser un número.
"""
    respuesta = enviar_prompt(prompt_pregunta)
    return respuesta.strip()

def obtener_variables_relevantes(pregunta, tipo_variable, df):
    """
    Selecciona columnas relevantes según el tipo de dato (numérico/categórico) solicitado,
    priorizando las relacionadas con salud mental cuando la pregunta lo sugiere,
    y asegurando que no queden series completamente vacías.
    
    Si no se encuentra nada (ni con la priorización de salud mental),
    se toma como 'último recurso' todas las columnas de salud mental
    que correspondan al tipo (numérico o categórico).
    """
    
    keywords_salud_mental = ["salud mental", "bienestar", "burnout", "estrés", "estres"]
    lower_pregunta = pregunta.lower()
    sugerir_dim_salud = any(kw in lower_pregunta for kw in keywords_salud_mental)

    #st.write("DEBUG - (FLEX) Pregunta:", pregunta)
    #st.write("DEBUG - (FLEX) Tipo variable:", tipo_variable)
    #st.write("DEBUG - (FLEX) Menciona salud mental:", sugerir_dim_salud)

    # Listas reales de df
    numeric_cols = df.select_dtypes(include=['int64','float64','int32','float32']).columns.tolist()
    cat_cols     = df.select_dtypes(include=['object','category']).columns.tolist()
    all_cols     = df.columns.tolist()

    # Filtrar según 'tipo_variable'
    if tipo_variable.lower() in ["numérica", "numerica"]:
        candidate_cols = numeric_cols
    elif tipo_variable.lower() in ["categórica", "categorica"]:
        candidate_cols = cat_cols
    else:
        candidate_cols = all_cols

    # --- 1) Buscar en las dimensiones de salud mental (si lo amerita)
    prioridad_salud = []
    if sugerir_dim_salud:
        # Recolectar TODAS las columnas definidas en "dimensiones"
        # y encontrar el "closest match" en df.columns
        for dim_name, lista_col_dicc in dimensiones.items():
            for col_dicc in lista_col_dicc:
                # Buscar coincidencia flexible con cada col real
                close_matches = difflib.get_close_matches(col_dicc, all_cols, n=1, cutoff=0.7)
                if close_matches:
                    col_real = close_matches[0]
                    if col_real in candidate_cols:
                        # Revisar que no sea ya incluida
                        if col_real not in prioridad_salud:
                            prioridad_salud.append(col_real)

    #st.write("DEBUG - (FLEX) prioridad_salud inicial:", prioridad_salud)

    # --- 2) Buscar qué columnas *genéricamente* coinciden con la pregunta
    # (opcional: podemos hacer un "fuzzy" con la pregunta... o no)
    # Para simplificar, podemos suponer que Gemini sugiere nombres y
    # nosotros validamos con fuzzy y candidate_cols.

    # Llamamos a Gemini con un prompt que pida "columns that might be relevant"
    prompt_variables = f"""
    Aquí tienes las columnas del DataFrame:
    {all_cols}

    El usuario pregunta: '{pregunta}'
    Busca columnas de tipo '{tipo_variable}' relevantes.

    Lista sólo los nombres de columna tal cual en el DF
    (o su match aproximado) separados por comas. La primera variable debe ser la más relevante,
    seguida de la segunda más relevante, si te hacen una pregunta por dos variables importantes, 
    los dos primeros elementos deben ser las dos variables sobre las que hace la pregunta, en la posición 0 y 1. Luego,
    de la tercera posición (2) en adelante, escribe las demas variables que puedan ser relevantes. 
    Escribe solo la lista de columnas en formato python, sin ningun otro tipo de comentario.
    """

    resp = enviar_prompt(prompt_variables)
    #st.write("DEBUG - (FLEX) Respuesta Gemini:", resp)

    # Parse la respuesta
    suggested = [x.strip() for x in resp.split(',') if x.strip()]

    # Hacer un fuzzy match con lo sugerido y candidate_cols
    variables_sugeridas = []
    for sug in suggested:
        # Buscar la columna real más parecida
        close = difflib.get_close_matches(sug, candidate_cols, n=1, cutoff=0.6)
        if close:
            variables_sugeridas.append(close[0])

    #st.write("DEBUG - (FLEX) variables_sugeridas tras fuzzy:", variables_sugeridas)

    # Unir "prioridad_salud" con "variables_sugeridas" sin duplicar
    final_list = []
    for c in prioridad_salud + variables_sugeridas:
        if c not in final_list:
            final_list.append(c)

    # Filtrar non_empty
    final_list_no_empty = []
    for col in final_list:
        non_null_count = df[col].dropna().shape[0]
        if non_null_count > 0:
            final_list_no_empty.append(col)

    # Si sigue vacío, devolvemos final_list_no_empty
    if not final_list_no_empty:
        st.write("ADVERTENCIA: No se encontraron columnas relevantes con datos.")
    return final_list_no_empty


# Función para procesar filtros en lenguaje natural utilizando Gemini
def procesar_filtros(filtro_natural):
    if not filtro_natural.strip():
        return None  # No se proporcionó ningún filtro
    prompt_filtro = f"""
    Convierte el siguiente filtro descrito en lenguaje natural a una consulta de pandas para filtrar un DataFrame.
    El DataFrame tiene las siguientes columnas y tipos de datos:

    {informacion_datos}

    El filtro es:

    {filtro_natural}

    Proporciona únicamente la expresión de filtrado en el formato que pandas 'query' entiende, sin ninguna explicación adicional.
    Por ejemplo, si el filtro es 'empleados mayores de 30 años y que sean mujeres', la salida debería ser "Edad > 30 & Sexo == 'Mujer'".

    Filtro pandas:
    """
    filtro_pandas = enviar_prompt(prompt_filtro)
    # Limpiar la respuesta de Gemini
    filtro_pandas = filtro_pandas.strip().split('Filtro pandas:')[-1].strip()
    return filtro_pandas
    
def realizar_analisis(opcion, pregunta_usuario, filtros=None, df_base=None):
    """
    Realiza el análisis de datos según la 'opcion' (1..7) detectada, 
    tomando automáticamente las dos primeras variables relevantes 
    en caso de que la opción requiera dos variables (o si es la opción 7),
    sin que el usuario deba seleccionarlas manualmente.
    
    Además, muestra en la aplicación las variables relevantes que 
    NO fueron utilizadas, para que el usuario las conozca.
    Incluye visualizaciones en subplots 1x3 para evitar recortes y 
    permitir ver 3 gráficos en la misma figura.
    """

    #st.write("DEBUG: Entrando a realizar_analisis con opcion=", opcion)
    #st.write("DEBUG: pregunta_usuario =", pregunta_usuario)
    #st.write("DEBUG: filtros =", filtros)

    resultados = ""
    figuras = []

    # Usar df_base si se proporciona, sino usar df global
    if df_base is not None:
        df_filtrado_inicial = df_base
    else:
        df_filtrado_inicial = df.copy()

    # (1) Manejo adicional de filtros si se proporcionan
    if filtros:
        try:
            #st.write("DEBUG: Aplicando filtro:", filtros)
            df_filtrado = df_filtrado_inicial.query(filtros)
        except Exception as e:
            st.write(f"Error al aplicar el filtro: {e}")
            df_filtrado = df_filtrado_inicial.copy()
    else:
        #st.write("DEBUG: Sin filtros adicionales.")
        df_filtrado = df_filtrado_inicial.copy()

    #st.write("DEBUG: df_filtrado.shape =", df_filtrado.shape)

    # Función auxiliar para obtener info de una variable desde data_dictionary
    def get_variable_info(variable_name):
        for category, variables_ in data_dictionary.items():
            if variable_name in variables_:
                return variables_[variable_name]
        return None

    # ===========================================================
    # Opción 1: Distribución de variable categórica
    # ===========================================================
    if opcion == '1':
        #st.write("DEBUG: Opción 1 - Distribución de variable categórica")
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'categórica', df_filtrado)

        if not variables_relevantes:
            resultados += "No se encontraron variables categóricas relevantes para la pregunta.\n"
            return resultados, figuras

        # Toma la primera variable categórica relevante
        var_cat = variables_relevantes[0]
        # Las demás, muéstralas como "no utilizadas"
        otras_vars = variables_relevantes[1:]
        if otras_vars:
            st.write(f"**Otras variables categóricas relevantes no utilizadas:** {otras_vars}")

        #st.write("DEBUG: Usando la variable categórica =>", var_cat)

        # Análisis
        conteo = df_filtrado[var_cat].value_counts(dropna=False)
        resultados += f"Frecuencias de {var_cat}:\n{conteo.to_string()}\n"

        # Intentar mapear valores según diccionario
        variable_info = get_variable_info(var_cat)
        if variable_info and 'Valores' in variable_info:
            valores = variable_info['Valores']
            if isinstance(valores, list):
                mapping = {i: v for i, v in enumerate(valores)}
                df_filtrado[var_cat] = df_filtrado[var_cat].map(mapping).fillna(df_filtrado[var_cat])
                conteo = df_filtrado[var_cat].value_counts(dropna=False)

        # Gráficos en subplots 1x3
        try:
            fig, axes = plt.subplots(1, 3, figsize=(13, 4))
            plt.tight_layout()

            # Gráfico 1 (barras)
            try:
                conteo.plot(kind='bar', ax=axes[0])
                axes[0].set_title(f'Distribución de {var_cat}')
                axes[0].set_xlabel(var_cat)
                axes[0].set_ylabel('Frecuencia')
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de barras: {e}")

            # Gráfico 2 (pie)
            try:
                conteo.plot(kind='pie', autopct='%1.1f%%', ax=axes[1])
                axes[1].set_ylabel('')
                axes[1].set_title(f'Distribución de {var_cat}')
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de pastel: {e}")

            # Gráfico 3 (barh)
            try:
                conteo.plot(kind='barh', ax=axes[2])
                axes[2].set_title(f'Distribución de {var_cat}')
                axes[2].set_xlabel('Frecuencia')
                axes[2].set_ylabel(var_cat)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de barras horizontal: {e}")

            plt.tight_layout()
            st.pyplot(fig)
            figuras.append(fig)
        except Exception as e:
            st.write(f"ERROR: No se pudo crear la figura de distribuciones: {e}")

    # ===========================================================
    # Opción 2: Estadísticas descriptivas de variable numérica
    # ===========================================================
    elif opcion == '2':
        #st.write("DEBUG: Opción 2 - Estadísticas descriptivas (numérica)")
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_filtrado)
        if not vars_relevantes:
            resultados += "No se encontraron variables numéricas relevantes para la pregunta.\n"
            return resultados, figuras

        # Tomar la primera variable
        var_num = vars_relevantes[0]
        otras_vars = vars_relevantes[1:]
        if otras_vars:
            st.write(f"**Otras variables numéricas relevantes no utilizadas:** {otras_vars}")

        #st.write("DEBUG: Usando la variable numérica =>", var_num)

        estadisticas = df_filtrado[var_num].describe()
        resultados += f"Estadísticas descriptivas de {var_num}:\n{estadisticas.to_string()}\n"

        # Gráficos 1x3: hist, boxplot, kde
        try:
            fig, axes = plt.subplots(1, 3, figsize=(13, 4))
            plt.tight_layout()

            # Histograma
            try:
                df_filtrado[var_num].hist(bins=10, grid=False, ax=axes[0])
                axes[0].set_title(f'Histograma de {var_num}')
                axes[0].set_xlabel(var_num)
                axes[0].set_ylabel('Frecuencia')
            except Exception as e:
                st.write(f"No se pudo generar el histograma: {e}")

            # Boxplot
            try:
                df_filtrado.boxplot(column=var_num, ax=axes[1])
                axes[1].set_title(f'Boxplot de {var_num}')
            except Exception as e:
                st.write(f"No se pudo generar el boxplot: {e}")

            # Gráfico de densidad (kde)
            try:
                df_filtrado[var_num].plot(kind='kde', ax=axes[2])
                axes[2].set_title(f'Densidad de {var_num}')
                axes[2].set_xlabel(var_num)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de densidad: {e}")

            plt.tight_layout()
            st.pyplot(fig)
            figuras.append(fig)
        except Exception as e:
            st.write(f"ERROR: No se pudo crear la figura para estadísticos de {var_num}: {e}")

    # ===========================================================
    # Opción 3: Relación entre dos variables numéricas
    # ===========================================================
    elif opcion == '3':
        #st.write("DEBUG: Opción 3 - Relación entre dos variables numéricas")
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_filtrado)

        if len(vars_relevantes) < 2:
            resultados += "No se encontraron suficientes variables numéricas relevantes para la pregunta.\n"
            return resultados, figuras

        var_x = vars_relevantes[0]
        var_y = None
        for v in vars_relevantes[1:]:
            if v != var_x:
                var_y = v
                break
        if var_y is None:
            resultados += "No se encontraron dos variables numéricas diferentes para la pregunta.\n"
            return resultados, figuras

        idx_unused = vars_relevantes.index(var_y) + 1
        otras_vars = vars_relevantes[idx_unused:]
        if otras_vars:
            st.write(f"**Otras variables numéricas relevantes no utilizadas:** {otras_vars}")

        #st.write("DEBUG: Analizando la relación entre =>", var_x, "y", var_y)
        resultados += f"Analizando la relación entre {var_x} y {var_y}.\n"

        # Crear 3 subplots: scatter, hexbin, kde
        try:
            fig, axes = plt.subplots(1, 3, figsize=(13,4))
            plt.tight_layout()

            # Dispersión
            try:
                df_filtrado.plot.scatter(x=var_x, y=var_y, ax=axes[0])
                axes[0].set_title(f'Dispersión: {var_x} vs {var_y}')
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de dispersión: {e}")

            # Hexbin
            try:
                df_filtrado.plot.hexbin(x=var_x, y=var_y, gridsize=25, ax=axes[1])
                axes[1].set_title(f'Hexbin: {var_x} vs {var_y}')
            except Exception as e:
                st.write(f"No se pudo generar el gráfico hexbin: {e}")

            # kdeplot 2D
            try:
                sns.kdeplot(data=df_filtrado, x=var_x, y=var_y, ax=axes[2])
                axes[2].set_title(f'Densidad conjunta: {var_x} vs {var_y}')
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de densidad conjunta: {e}")

            plt.tight_layout()
            st.pyplot(fig)
            figuras.append(fig)
        except Exception as e:
            st.write("ERROR: No se pudo crear la figura de relación 2 num:", e)

        # Correlación numérica
        try:
            correlacion = df_filtrado[[var_x, var_y]].corr().iloc[0,1]
            resultados += f"Correlación entre {var_x} y {var_y}: {correlacion}\n"
        except Exception as e:
            st.write(f"No se pudo calcular la correlación: {e}")

    # ===========================================================
    # Opción 4: Filtrar datos y mostrar estadísticas de 1 var num
    # ===========================================================
    elif opcion == '4':
        #st.write("DEBUG: Opción 4 - Filtrar datos y estadísticos de 1 var num")
        resultados += "Datos después de aplicar los filtros proporcionados.\n"
        resultados += f"Total de registros después del filtro: {len(df_filtrado)}\n"

        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_filtrado)
        if not vars_relevantes:
            resultados += "No se encontraron variables numéricas relevantes para mostrar después de aplicar los filtros.\n"
            return resultados, figuras

        var_num4 = vars_relevantes[0]
        otras_vars = vars_relevantes[1:]
        if otras_vars:
            st.write(f"**Otras variables numéricas relevantes no utilizadas:** {otras_vars}")

        #st.write("DEBUG: Usando la variable numérica =>", var_num4)

        estadisticas = df_filtrado[var_num4].describe()
        resultados += f"Estadísticas descriptivas de {var_num4} (después de filtros):\n{estadisticas.to_string()}\n"

        # Subplots 1x3: hist, boxplot, kde
        try:
            fig, axes = plt.subplots(1, 3, figsize=(13,4))
            plt.tight_layout()

            # Hist
            try:
                df_filtrado[var_num4].hist(bins=10, grid=False, ax=axes[0])
                axes[0].set_title(f'Histograma de {var_num4} (filtrado)')
                axes[0].set_xlabel(var_num4)
                axes[0].set_ylabel('Frecuencia')
            except Exception as e:
                st.write(f"No se pudo generar el histograma: {e}")

            # Boxplot
            try:
                df_filtrado.boxplot(column=var_num4, ax=axes[1])
                axes[1].set_title(f'Boxplot de {var_num4} (filtrado)')
            except Exception as e:
                st.write(f"No se pudo generar el boxplot: {e}")

            # KDE
            try:
                df_filtrado[var_num4].plot(kind='kde', ax=axes[2])
                axes[2].set_title(f'Densidad de {var_num4} (filtrado)')
                axes[2].set_xlabel(var_num4)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de densidad: {e}")

            plt.tight_layout()
            st.pyplot(fig)
            figuras.append(fig)
        except Exception as e:
            st.write("ERROR: No se pudo crear la figura de estadísticos (opcion4):", e)

    # ===========================================================
    # Opción 5: Correlación entre múltiples variables numéricas
    # ===========================================================
    elif opcion == '5':
        #st.write("DEBUG: Opción 5 - Correlación de múltiples variables numéricas")
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_filtrado)
        if len(vars_relevantes) < 2:
            resultados += "No se encontraron suficientes variables numéricas para calcular la correlación.\n"
            return resultados, figuras

        st.write(f"**Variables numéricas relevantes para la correlación:** {vars_relevantes}")
        correlacion = df_filtrado[vars_relevantes].corr()
        resultados += "Matriz de correlación:\n"
        resultados += correlacion.to_string() + "\n"

        # Heatmap
        try:
            fig1, ax1 = plt.subplots(figsize=(6,5))
            sns.heatmap(correlacion, annot=True, fmt='.2f', cmap='coolwarm', ax=ax1)
            ax1.set_title('Mapa de calor de la correlación')
            plt.tight_layout()
            st.pyplot(fig1)
            figuras.append(fig1)
        except Exception as e:
            st.write(f"No se pudo generar el heatmap: {e}")

        # Pairplot
        try:
            fig2 = sns.pairplot(df_filtrado[vars_relevantes], corner=True)
            st.pyplot(fig2)
            figuras.append(fig2)
        except Exception as e:
            st.write(f"No se pudo generar la matriz de dispersión: {e}")

        # Matshow con anotaciones
        try:
            import numpy as np
            fig3, ax3 = plt.subplots(figsize=(6,5))
            cax = ax3.matshow(correlacion, cmap='coolwarm')
            fig3.colorbar(cax)
            ax3.set_xticks(range(len(vars_relevantes)))
            ax3.set_xticklabels(vars_relevantes, rotation=90)
            ax3.set_yticks(range(len(vars_relevantes)))
            ax3.set_yticklabels(vars_relevantes)
            for (i, j), z in np.ndenumerate(correlacion):
                ax3.text(j, i, '{:0.2f}'.format(z), ha='center', va='center')
            ax3.set_title("Matriz de Correlación", pad=20)
            plt.tight_layout()
            st.pyplot(fig3)
            figuras.append(fig3)
        except Exception as e:
            st.write(f"No se pudo generar el gráfico de correlación matshow: {e}")

    # ===========================================================
    # Opción 6: Análisis de regresión simple (2 var num)
    # ===========================================================
    elif opcion == '6':
        #st.write("DEBUG: Opción 6 - Regresión lineal simple")
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_filtrado)

        if len(vars_relevantes) < 2:
            resultados += "No se encontraron suficientes variables numéricas para realizar la regresión.\n"
            return resultados, figuras

        varx = vars_relevantes[0]
        vary = None
        for v in vars_relevantes[1:]:
            if v != varx:
                vary = v
                break

        if vary is None:
            resultados += "No se encontraron dos variables numéricas diferentes para realizar la regresión.\n"
            return resultados, figuras

        idx_unused = vars_relevantes.index(vary) + 1
        otras_vars = vars_relevantes[idx_unused:]
        if otras_vars:
            st.write(f"**Otras variables numéricas relevantes no utilizadas:** {otras_vars}")

        #st.write("DEBUG: Eje X =>", varx, ", Eje Y =>", vary)

        from sklearn.linear_model import LinearRegression
        X = df_filtrado[[varx]].dropna()
        y = df_filtrado[vary].dropna()
        df_regresion = pd.concat([X, y], axis=1).dropna()
        X = df_regresion[[varx]]
        y = df_regresion[vary]

        if len(X) == 0 or len(y) == 0:
            resultados += "No hay datos suficientes para la regresión tras filtrar.\n"
            return resultados, figuras

        modelo = LinearRegression()
        modelo.fit(X, y)
        r_sq = modelo.score(X, y)

        resultados += f"Regresión lineal simple entre {varx} (X) y {vary} (Y):\n"
        resultados += f"Coeficiente de determinación (R^2): {r_sq}\n"
        resultados += f"Intercepto: {modelo.intercept_}\n"
        resultados += f"Coeficiente (pendiente): {modelo.coef_[0]}\n"

        # Subplots 1x3: scatter con línea, residuales, hist residuales
        try:
            fig, axes = plt.subplots(1,3, figsize=(13,4))
            plt.tight_layout()

            # 1) Scatter con línea
            try:
                axes[0].scatter(X, y, color='blue', alpha=0.7)
                axes[0].plot(X, modelo.predict(X), color='red')
                axes[0].set_title(f'Regresión: {varx} vs {vary}')
                axes[0].set_xlabel(varx)
                axes[0].set_ylabel(vary)
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de regresión lineal: {e}")

            # 2) Gráfico de residuales
            try:
                residuales = y - modelo.predict(X)
                axes[1].scatter(modelo.predict(X), residuales, alpha=0.7)
                axes[1].axhline(y=0, color='red')
                axes[1].set_title('Gráfico de residuales')
                axes[1].set_xlabel('Valores predichos')
                axes[1].set_ylabel('Residuales')
            except Exception as e:
                st.write(f"No se pudo generar el gráfico de residuales: {e}")

            # 3) Histplot de residuales
            try:
                sns.histplot(residuales, kde=True, ax=axes[2])
                axes[2].set_title('Distribución de los residuales')
            except Exception as e:
                st.write(f"No se pudo generar el histograma de residuales: {e}")

            plt.tight_layout()
            st.pyplot(fig)
            figuras.append(fig)
        except Exception as e:
            st.write("ERROR: No se pudo crear la figura de regresión simple:", e)

    # ===========================================================
    # Opción 7: Tablas de contingencia y Chi-cuadrado (2 vars)
    # ===========================================================
    elif opcion == '7':
        # 7) Tablas de contingencia y Chi-cuadrado
        resultados += "Análisis de Tablas de Contingencia y Chi-cuadrado.\n\n"
    
        #st.write("DEBUG: Entrando a la Opción 7 - Tablas de Contingencia")
        #st.write("DEBUG: La pregunta del usuario es:", pregunta_usuario)
        #st.write("DEBUG: df_filtrado.shape =", df_filtrado.shape)
    
        # --- 1) Busca todas las columnas relevantes (sin importar si son cat o num)
        #st.write("DEBUG: Llamando obtener_variables_relevantes con tipo='todas'")
        all_relevant = obtener_variables_relevantes(pregunta_usuario, 'todas', df_filtrado)
        #st.write("DEBUG - (opción7) all_relevant:", all_relevant)
    
        if len(all_relevant) < 2:
            resultados += "No hay suficientes columnas relevantes para la tabla.\n"
            #st.write("DEBUG - Motivo: len(all_relevant) < 2 =>", len(all_relevant))
            return resultados, figuras
    
        # 2) Separa en cat y num
        cats_encontradas = []
        nums_encontradas = []
    
        #st.write("DEBUG: df_filtrado dtypes:\n", df_filtrado.dtypes)
    
        for col in all_relevant:
            if col not in df_filtrado.columns:
                #st.write(f"DEBUG: La columna '{col}' NO está en df_filtrado.columns (mismatch).")
                continue
            real_dtype = df_filtrado[col].dtype
            #st.write(f"DEBUG: Columna '{col}', dtype -> {real_dtype}")
            if real_dtype in [object, 'category']:
                cats_encontradas.append(col)
            elif str(real_dtype).startswith('float') or str(real_dtype).startswith('int'):
                nums_encontradas.append(col)
            else:
                st.write(f"DEBUG: '{col}' es dtype {real_dtype}, no es cat ni num.")
    
        #st.write("DEBUG - cats_encontradas:", cats_encontradas)
        #st.write("DEBUG - nums_encontradas:", nums_encontradas)
    
        # 3) Lógica para Tablas de contingencia
        var1, var2 = None, None
    
        #st.write("DEBUG: Reglas para asignar var1, var2 ...")
    
        if len(cats_encontradas) >= 2:
            var1 = cats_encontradas[0]
            var2 = cats_encontradas[1]
            #st.write(f"DEBUG - Usando 2 categóricas: var1={var1}, var2={var2}")
        elif len(cats_encontradas) == 1 and len(nums_encontradas) >= 1:
            var1 = cats_encontradas[0]
            var2 = nums_encontradas[0]
            #st.write(f"DEBUG - Usando cat={var1} y num={var2}")
        else:
            resultados += "No se pudo encontrar dos columnas adecuadas (categ y/o num) para la tabla.\n"
            #st.write("DEBUG - No se cumplieron las condiciones para tener var1 y var2")
            return resultados, figuras
    
        import numpy as np
        from scipy.stats import chi2_contingency
    
        def agrupar_si_es_num(s, nbins=5):
            """Si la columna es numérica, agrupar en nbins. Si es categórica, devolver tal cual."""
            #st.write(f"DEBUG: agrupar_si_es_num -> dtype={s.dtype}, length={len(s)}")
            if str(s.dtype).startswith('float') or str(s.dtype).startswith('int'):
                return pd.cut(s, nbins, labels=False).astype(str)
            else:
                return s.astype(str)
    
        #st.write(f"DEBUG: Cantidad de nulos en '{var1}': {df_filtrado[var1].isna().sum()}.")
        #st.write(f"DEBUG: Cantidad de nulos en '{var2}': {df_filtrado[var2].isna().sum()}.")
        serie1 = df_filtrado[var1].dropna()
        serie2 = df_filtrado[var2].dropna()
    
        #st.write(f"DEBUG: serie1 (var1={var1}) length tras dropna -> {len(serie1)}")
        #st.write(f"DEBUG: serie2 (var2={var2}) length tras dropna -> {len(serie2)}")
    
        if serie1.empty or serie2.empty:
            resultados += "No hay datos suficientes (serie vacía) para generar la tabla.\n"
            #st.write("DEBUG - Motivo: serie1/serie2 está vacía.")
            return resultados, figuras
    
        # Agrupar si es num
        serie1 = agrupar_si_es_num(serie1)
        serie2 = agrupar_si_es_num(serie2)
    
        #st.write("DEBUG: Después de agrupar_si_es_num => unique en serie1:", serie1.unique())
        #st.write("DEBUG: Después de agrupar_si_es_num => unique en serie2:", serie2.unique())
    
        crosstab = pd.crosstab(serie1, serie2)
        #st.write("DEBUG - crosstab shape:", crosstab.shape)
        #st.write("DEBUG - crosstab:\n", crosstab)
    
        if crosstab.empty:
            resultados += "Tabla de contingencia vacía.\n"
            #st.write("DEBUG - crosstab está vacío => no se genera la tabla.")
            return resultados, figuras
    
        resultados += f"**Tabla de Contingencia** entre {var1} y {var2}:\n{crosstab.to_string()}\n\n"
        chi2, p, dof, expected = chi2_contingency(crosstab)
        resultados += f"**Chi-cuadrado**: {chi2:.2f}\n"
        resultados += f"**p-value**: {p:.4f}\n"
        resultados += f"**Grados de libertad**: {dof}\n"
        resultados += f"**Valores esperados**:\n{expected}\n\n"
    
        # Plot heatmap
        try:
            fig_ct, ax_ct = plt.subplots(figsize=(6,4))
            sns.heatmap(crosstab, annot=True, fmt='d', cmap='Blues', ax=ax_ct)
            ax_ct.set_title(f"Heatmap de {var1} vs {var2}", fontsize=10)
            ax_ct.set_xlabel(var2)
            ax_ct.set_ylabel(var1)
            plt.tight_layout()
            st.pyplot(fig_ct)
            figuras.append(fig_ct)
        except Exception as e:
            st.write(f"No se pudo graficar la tabla de contingencia: {e}")
    
        return resultados, figuras

    else:
        #st.write("DEBUG: Opción no reconocida =>", opcion)
        resultados += "Opción de análisis no reconocida.\n"

    # -----------------------------------------------------------
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

    def insert_image(self, image_path, max_width=400, max_height=550):
        """
        Ajusta la imagen para que no exceda max_width ni max_height,
        conservando la relación de aspecto.
        """
        if os.path.isfile(image_path):
            from PIL import Image as PILImage
            with PILImage.open(image_path) as im:
                orig_width, orig_height = im.size
            if orig_width == 0 or orig_height == 0:
                # Caso extremo, se asigna un tamaño fijo
                new_width = max_width
                new_height = max_width
            else:
                # Calcular la relación de aspecto
                ratio = float(orig_height) / float(orig_width)
                # Iniciar con el ancho deseado
                new_width = min(max_width, orig_width)
                new_height = new_width * ratio
    
                # Si la altura resultante supera max_height, ajustar de nuevo
                if new_height > max_height:
                    new_height = max_height
                    new_width = new_height / ratio
    
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
    """Breaks long words while preserving Markdown structure."""

    def break_word(word):
        """Breaks a single word."""
        new_word = ""
        while len(word) > max_length:
            new_word += word[:max_length - 1] + "-"
            word = word[max_length - 1:]
        new_word += word
        return new_word

    # Use a regular expression to find words (sequences of non-whitespace characters)
    return re.sub(r"\S+", lambda m: break_word(m.group(0)), text)


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
    variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'todas', df)
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

    {pregunta_usuario}

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

    {pregunta_usuario}

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

# Definimos varios "diccionarios de escalas" en un solo lugar:
likert_7_extended = {
    "Nunca": 1,
    "Rara vez": 2,
    "Raramente": 2,   # por si aparece "Raramente" en vez de "Rara vez"
    "Alguna vez": 3,
    "Algunas veces": 4,
    "A menudo": 5,
    "Frecuentemente": 6,
    "Siempre": 7
}

acuerdo_7 = {
    "Muy en desacuerdo": 1,
    "Moderadamente en desacuerdo": 2,
    "Ligeramente en desacuerdo": 3,
    "Ni de acuerdo ni en desacuerdo": 4,  # si existiese
    "Ligeramente de acuerdo": 4,         # a veces se numeran 1..6
    "Moderadamente de acuerdo": 5,
    "Muy de acuerdo": 6,
    "Totalmente de acuerdo": 7
}

burnout_5 = {
    "Nunca": 1,
    "Raramente": 2,
    "Algunas veces": 3,
    "A menudo": 4,
    "Siempre": 5
}

likert_7_extended_map = {k.lower().strip(): v for k, v in likert_7_extended.items()}
acuerdo_7_map = {k.lower().strip(): v for k, v in acuerdo_7.items()}
burnout_5_map = {k.lower().strip(): v for k, v in burnout_5.items()}

def mapear_valores(serie):
    """
    Detecta si la serie corresponde a una escala Likert conocida
    y la convierte a valores numéricos. Si no, intenta mapear valores similares.
    Si no se puede mapear, devuelve la serie original.
    """

    unique_vals = serie.dropna().unique().tolist()
    print(f"DEBUG - mapear_valores: valores únicos = {unique_vals}")

    serie_limpia = serie.astype(str).str.strip().str.lower()

    def safe_map_replace(series, mapping_dict):
        mapped_series = series.replace(mapping_dict)
        # Check if any values failed to map and print a warning (for debugging)
        unmapped_values = series[~series.isin(mapping_dict.keys())].unique()
        if len(unmapped_values) > 0 and not all(pd.isna(unmapped_values)): # Check if unmapped_values is not just NaNs
            print(f"WARNING - Unmapped values in series: {unmapped_values}")
        return mapped_series

    def all_in_dict_keys(vals, dic):
        dic_keys_lower = set(dic.keys())
        return all(str(v).lower().strip() in dic_keys_lower for v in vals if not pd.isna(v))

    if all_in_dict_keys(unique_vals, likert_7_extended_map):
        print("DEBUG - Se detectó una escala Likert 1..7 (Nunca..Siempre).")
        return safe_map_replace(serie_limpia, likert_7_extended_map).astype(float, errors='ignore')

    elif all_in_dict_keys(unique_vals, acuerdo_7_map):
        print("DEBUG - Se detectó una escala de Acuerdo 1..7 (Muy/Totalmente de acuerdo...).")
        return safe_map_replace(serie_limpia, acuerdo_7_map).astype(float, errors='ignore')

    elif all_in_dict_keys(unique_vals, burnout_5_map):
        print("DEBUG - Se detectó escala de Burnout 1..5 (Nunca..Siempre).")
        return safe_map_replace(serie_limpia, burnout_5_map).astype(float, errors='ignore')

    else:
        print("DEBUG - No coincide con escalas definidas, intentando mapeo aproximado...")
        # Attempt approximate mapping for Likert 7 extended as a fallback
        mapped_serie = safe_map_replace(serie_limpia, likert_7_extended_map).astype(float, errors='ignore')
        if not mapped_serie.isna().all(): # If at least some values were mapped, return mapped series
            print("DEBUG - Mapeo aproximado Likert 7 aplicado.")
            return mapped_serie
        else:
            print("DEBUG - No se aplicó mapeo, se devuelve serie original.")
            return serie # Return original if no mapping applied
    
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
    df_filtrado = df[
        (df['Hora de inicio'] >= pd.to_datetime(fecha_inicio)) &
        (df['Hora de inicio'] <= pd.to_datetime(fecha_fin))
    ].copy() # Use .copy() to avoid modifying original df

    if df_filtrado.empty:
        return "No se encontraron datos en el rango de fechas especificado.", []

    # --- DATA CLEANING AND STANDARDIZATION ---
    for col in df_filtrado.select_dtypes(include='object').columns:
        # Strip whitespace and non-breaking spaces, convert to lowercase
        df_filtrado[col] = df_filtrado[col].str.strip().str.replace('\xa0', ' ', regex=False).str.lower()

    # Special handling for 'Edad' and 'Numero de hijos'
    if 'Edad' in df_filtrado.columns:
        df_filtrado['Edad'] = pd.to_numeric(df_filtrado['Edad'], errors='coerce')
    if 'Numero de hijos' in df_filtrado.columns:
        df_filtrado['Numero de hijos'] = df_filtrado['Numero de hijos'].replace('sin hijos', 0, regex=False).fillna(0) # Replace 'sin hijos' with 0 and handle NaN
        df_filtrado['Numero de hijos'] = pd.to_numeric(df_filtrado['Numero de hijos'], errors='coerce', downcast='integer') # Convert to numeric, coerce errors to NaN

    # Convert todo a valores numéricos según la escala fija para las dimensiones
    df_num = df_filtrado.copy()
    for col in df_num.columns:
        if df_num[col].dtype == object:
            # EJEMPLO: print de debug
            #print("DEBUG - Antes de mapear_valores, df_num[column].value_counts():")
            print(df_num[col].value_counts(dropna=False))

            # Llamada a mapear_valores
            df_num[col] = mapear_valores(df_num[col])

            # Después
            #print("DEBUG - Después de mapear_valores, df_num[column].value_counts():")
            print(df_num[col].value_counts(dropna=False))

    # Definir umbrales
    # Fortaleza: >=5, Riesgo: <=3, Intermedio: (3,5)
    resultados = {}
    for dim, vars_dim in dimensiones.items():
        vars_exist = [v for v in vars_dim if v in df_num.columns]
        if vars_exist:
            prom = df_num[vars_exist].mean(skipna=True, numeric_only=True).mean()
            resultados[dim] = prom

    fortalezas = [(d,v) for d,v in resultados.items() if v >=5]
    riesgos = [(d,v) for d,v in resultados.items() if v <=3]
    intermedios = [(d,v) for d,v in resultados.items() if 3 < v < 5]

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
    fig_titles = []

    # ------------------------------------------------------------------
    # 1. Semáforo de Dimensiones
    # ------------------------------------------------------------------
    inverse_dims = {
        "Conflicto Familia-Trabajo": True,
        "Síntomas de Burnout": True,
        "Factores de Efectos Colaterales (Escala de Desgaste)": True,
        "Factores de Efectos Colaterales (Escala de Alienación)": True,
        # Si deseas que "Control del Tiempo" sea inversa también:
        "Control del Tiempo": True
    }

    def estado_dimension(valor):
        if valor >= 5:
            return ('Fortaleza', 'green')
        elif valor <= 3:
            return ('Riesgo', 'red')
        else:
            return ('Intermedio', 'yellow')

    dims_list = list(resultados.items())  # [('Dimension1', prom1), ...]
    n_dims = len(dims_list)
    cols = 3
    rows = math.ceil(n_dims / cols)

    # Aumentar el figsize para evitar que se recorten
    fig_semaforo, axes_semaforo = plt.subplots(
        rows, cols, figsize=(cols*3, rows*2.2)
    )
    axes_semaforo = axes_semaforo.flatten() if n_dims > 1 else [axes_semaforo]

    for idx, (dim, val) in enumerate(dims_list):
        if dim in inverse_dims and inverse_dims[dim]:
            val_display = 8 - val
        else:
            val_display = val
        est, color = estado_dimension(val_display)
        ax = axes_semaforo[idx]
        ax.set_facecolor(color)

        text_content = f"{dim}\n{est}\nProm: {val_display:.2f}"
        ax.text(
            0.5, 0.5, text_content,
            ha='center', va='center',
            fontsize=8, color='black',
            wrap=True
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlim(0,1)
        ax.set_ylim(0,1)

    # Ocultar ejes sobrantes (si sobran casillas)
    for j in range(idx+1, len(axes_semaforo)):
        axes_semaforo[j].set_visible(False)

    fig_semaforo.suptitle("Semáforo de Dimensiones (Resumen)", fontsize=12)
    fig_semaforo.tight_layout()
    figuras.append(fig_semaforo)
    fig_titles.append("Figura: Semáforo de Dimensiones")

    # ------------------------------------------------------------------
    # 2. Análisis por Sexo, Rango de Edad y Hijos
    # ------------------------------------------------------------------
    df_cat = df_filtrado.copy()

    # Convertir Edad a numérico
    if 'Edad' in df_cat.columns:
        df_cat['Edad'] = pd.to_numeric(df_cat['Edad'], errors='coerce')
        # Crear rangos
        bins = [0, 24, 34, 44, 200]
        labels = ['<25', '25-34', '35-44', '45+']
        df_cat['Rango_Edad'] = pd.cut(df_cat['Edad'], bins=bins, labels=labels, include_lowest=True)
    else:
        df_cat['Rango_Edad'] = 'SinDatoEdad'

    # Crear columna Hijos (0/1)
    if 'Numero de hijos' in df_cat.columns:
        df_cat['Hijos'] = df_cat['Numero de hijos'].apply(
            lambda x: 0 if str(x).strip().lower()=='sin hijos' else 1
        )
    else:
        df_cat['Hijos'] = 0

    # Convertir todo a numérico en df_mix
    df_mix = df_filtrado.copy()
    for colname in df_mix.columns:
        # NO mapear si es 'Sexo' u otras columnas que no sean Likert
        if colname in ["Sexo", "Estado Civil", "ID", "Municipio", "Sector Económico"]:
            continue

        # Verificar si dtype es object
        if df_mix[colname].dtype == object:
            # Aplicar mapear_valores
            df_mix[colname] = mapear_valores(df_mix[colname])

    # Añadir las columnas auxiliares
    df_mix['Rango_Edad'] = df_cat['Rango_Edad']
    df_mix['Hijos'] = df_cat['Hijos']

    # Recorremos cada dimensión
    for dim, vars_dim in dimensiones.items():
        vars_exist = [v for v in vars_dim if v in df_mix.columns]
        if not vars_exist:
            continue

        # Creamos un 2x2 subplots (quedará uno vacío)
        fig_dim, axs_dim = plt.subplots(2, 2, figsize=(10,6))
        fig_dim.suptitle(f"{dim} comparado por Sexo, Rango de Edad y Hijos", fontsize=10)

        # Subplot (0,0): Por Sexo
        ax_sexo = axs_dim[0,0]

        # Imprimir columnas de df_mix para verificar si existe 'Sexo'
        print("DEBUG - df_mix columns:", df_mix.columns)

        if 'Sexo' in df_mix.columns:
            print("DEBUG - La columna 'Sexo' SÍ está presente en df_mix.")
            # Agrupación y promedio de las variables de la dimensión
            df_sexo = df_mix.groupby('Sexo')[vars_exist].mean().mean(axis=1)

            print("DEBUG - df_sexo shape:", df_sexo.shape)
            print("DEBUG - df_sexo contenido:\n", df_sexo)

            if df_sexo.empty:
                print("DEBUG - df_sexo está vacío. Ocultando ax_sexo.")
                ax_sexo.set_visible(False)
            else:
                # Agrupar si hay más de 10 categorías
                df_sexo_counts = df_sexo.reset_index()
                df_sexo_counts.columns = ['Sexo', 'MeanValue']

                print("DEBUG - df_sexo_counts (antes de agrupar 'Otros'):\n", df_sexo_counts)

                if len(df_sexo_counts) > 10:
                    print("DEBUG - Hay más de 10 categorías, agrupando en 'Otros'.")
                    top_9 = df_sexo_counts.nlargest(9, 'MeanValue')
                    others_sum = df_sexo_counts.iloc[9:]['MeanValue'].sum()
                    top_9.loc[len(top_9)] = ['Otros', others_sum]
                    df_sexo = top_9.set_index('Sexo')['MeanValue']
                    print("DEBUG - df_sexo después de agrupar 'Otros':\n", df_sexo)

                print("DEBUG - Se ploteará df_sexo:\n", df_sexo)
                df_sexo.plot(kind='bar', color='lightblue', ax=ax_sexo)
                ax_sexo.set_title("Por Sexo", fontsize=8)
                ax_sexo.set_xlabel('')
                ax_sexo.set_ylabel('Promedio')
                ax_sexo.set_ylim([1,7])
        else:
            print("DEBUG - La columna 'Sexo' NO se encuentra en df_mix.columns. Ocultando ax_sexo.")
            ax_sexo.set_visible(False)

        # Subplot (0,1): Por Rango de Edad
        ax_edad = axs_dim[0,1]
        if 'Rango_Edad' in df_mix.columns:
            df_edad = df_mix.groupby('Rango_Edad')[vars_exist].mean().mean(axis=1)
            if df_edad.empty:
                ax_edad.set_visible(False)
            else:
                # Agrupar si hay >10 (raro en rangos de edad, pero por consistencia)
                df_edad_counts = df_edad.reset_index()
                df_edad_counts.columns = ['Rango_Edad', 'MeanValue']
                if len(df_edad_counts) > 10:
                    top_9 = df_edad_counts.nlargest(9, 'MeanValue')
                    others_sum = df_edad_counts.iloc[9:]['MeanValue'].sum()
                    top_9.loc[len(top_9)] = ['Otros', others_sum]
                    df_edad = top_9.set_index('Rango_Edad')['MeanValue']

                df_edad.plot(kind='bar', color='lightgreen', ax=ax_edad)
                ax_edad.set_title("Por Rango de Edad", fontsize=8)
                ax_edad.set_xlabel('')
                ax_edad.set_ylabel('Promedio')
                ax_edad.set_ylim([1,7])
        else:
            ax_edad.set_visible(False)

        # Subplot (1,0): Por Hijos
        ax_hijos = axs_dim[1,0]
        if 'Hijos' in df_mix.columns:
            df_hijos = df_mix.groupby('Hijos')[vars_exist].mean().mean(axis=1)
            if df_hijos.empty:
                ax_hijos.set_visible(False)
            else:
                df_hijos_index = df_hijos.rename(index={0:'Sin hijos', 1:'Con hijos'}).copy()
                # Agrupar si hay >10 (poco probable)
                if len(df_hijos_index) > 10:
                    top_9 = df_hijos_index.nlargest(9)
                    others_sum = df_hijos_index.iloc[9:].sum()
                    top_9.loc['Otros'] = others_sum
                    df_hijos_index = top_9

                df_hijos_index.plot(kind='bar', color='orange', ax=ax_hijos)
                ax_hijos.set_title("Por Hijos", fontsize=8)
                ax_hijos.set_xlabel('')
                ax_hijos.set_ylabel('Promedio')
                ax_hijos.set_ylim([1,7])
        else:
            ax_hijos.set_visible(False)

        # Subplot (1,1): Este quedará vacío
        axs_dim[1,1].axis('off')  # o axs_dim[1,1].set_visible(False)

        plt.tight_layout()
        figuras.append(fig_dim)
        fig_titles.append(f"Figura: Comparación Sexo-Edad-Hijos - {dim}")

    # ------------------------------------------------------------------
    # GENERAR INFORME TEXTO
    # ------------------------------------------------------------------
    informe = []
    informe.append("Este informe presenta un análisis general de las dimensiones "
                   "de bienestar laboral en el rango de fechas especificado.\n")
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

    # Opcional: Crear índice de figuras si lo deseas
    # ...
    # (No lo mostramos completo para simplificar, pero aquí podrías
    # generar un índice con fig_titles)

    informe_texto = "".join(informe)
    return informe_texto, figuras
    
def main():
    """
    Función principal de la aplicación Streamlit para el análisis de datos 
    sobre salud organizacional.

    Incluye:
    1) Filtro por fecha y código de empresa (ID).
    2) "Generar Informe General" para el rango de fechas/ID.
    3) Análisis específico a partir de una pregunta del usuario, 
       invocando a Gemini para sugerir la opción (1..7).
    4) Uso de la función 'realizar_analisis' con las 2 variables 
       más relevantes (si el método lo requiere), sin que el usuario 
       tenga que elegirlas manualmente.
    5) Generación de un informe PDF al final del análisis y 
       opción de "Realizar otra consulta".
    """
    # Título de la app
    st.title("Aplicación de Análisis de Datos sobre Salud Organizacional")

    # 0) Mostrar el resumen de la base de datos
    mostrar_resumen_base_datos()

    # 1) Convertir columna 'Hora de inicio' a datetime (una sola vez)
    df['Hora de inicio'] = pd.to_datetime(df['Hora de inicio'], errors='coerce')

    # 2) Widgets para escoger rango de fechas
    fecha_inicio = st.date_input("Fecha de inicio", date.today() - timedelta(days=360))
    fecha_fin = st.date_input("Fecha de fin", date.today())

    # 3) Opción para filtrar por código de empresa (ID)
    cod_empresa = st.text_input("Código de la empresa (ID). Déjelo vacío si no desea filtrar por empresa:")

    # 4) Filtrar el DataFrame original según el rango de fechas
    df_rango = df[
        (df['Hora de inicio'] >= pd.to_datetime(fecha_inicio)) &
        (df['Hora de inicio'] <= pd.to_datetime(fecha_fin))
    ]

    # Filtrar por código de empresa si se especificó
    if cod_empresa.strip():
        df_rango = df_rango[df_rango['ID'].astype(str) == cod_empresa.strip()]

    # --------------------------------------------------------------------------
    # A) BOTÓN: Generar Informe General
    # --------------------------------------------------------------------------
    if st.button("Generar Informe General"):
        with st.spinner("Generando informe general..."):
            # Llamamos a la función que genera un informe general en PDF
            # (análisis de todas las dimensiones, semáforo, etc.)
            informe_texto, figs = generar_informe_general(df_rango, fecha_inicio, fecha_fin)

            # Mostramos el texto del informe general en la app
            st.write(informe_texto)

            # Construimos el PDF
            pdf_general = PDFReport('informe_general.pdf')
            pdf_general.chapter_title("Informe General de Bienestar Laboral")
            pdf_general.chapter_body(informe_texto)

            # Insertamos cada figura en el PDF
            for idx, f in enumerate(figs):
                img_path = f'figura_general_{idx}.png'
                f.savefig(img_path)
                pdf_general.insert_image(img_path)

            # Finalmente construimos y guardamos el PDF
            pdf_general.build_pdf()

            # Ofrecemos el PDF para descargarlo
            with open('informe_general.pdf', 'rb') as f:
                pdf_data = f.read()
            b64 = base64.b64encode(pdf_data).decode('utf-8')
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="informe_general.pdf">Descargar Informe General en PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # B) Análisis específico (pregunta del usuario) usando Gemini
    # --------------------------------------------------------------------------

    # Variables de sesión para manejar el flujo de un único análisis
    if "opcion_analisis" not in st.session_state:
        st.session_state["opcion_analisis"] = None
    if 'pregunta_usuario' not in st.session_state:
        st.session_state['pregunta_usuario'] = ''
    if 'filtro_natural' not in st.session_state:
        st.session_state['filtro_natural'] = ''
    if 'analisis_realizado' not in st.session_state:
        st.session_state['analisis_realizado'] = False

    # Si aún NO se realizó el análisis en esta ejecución
    if not st.session_state['analisis_realizado']:
        st.write("Ingresa tu pregunta de investigación y opcionalmente filtros en lenguaje natural:")

        # Campos de texto para la pregunta y el filtro
        st.session_state['pregunta_usuario'] = st.text_input(
            "Pregunta:",
            value=st.session_state['pregunta_usuario']
        )
        st.session_state['filtro_natural'] = st.text_input(
            "Filtros (opcional):",
            value=st.session_state['filtro_natural']
        )

        # Botón para realizar el análisis
        if st.button("Realizar Análisis"):
            if st.session_state['pregunta_usuario'].strip() == '':
                st.warning("Por favor, ingresa una pregunta.")
            else:
                with st.spinner('Enviando pregunta a Gemini...'):
                    # 1) Interpretar el filtro en lenguaje natural, si existe
                    filtros_usuario = procesar_filtros(st.session_state['filtro_natural'])
                    if filtros_usuario:
                        st.write(f"**Filtro pandas generado**: {filtros_usuario}")
                    else:
                        st.write("No se aplicará ningún filtro adicional.")

                    # 2) Consultar a Gemini cuál de las 7 opciones de análisis es más adecuada
                    respuesta = procesar_pregunta(st.session_state['pregunta_usuario'])
                    st.session_state["opcion_analisis"] = respuesta
                    st.write(f"**Gemini sugiere la opción de análisis:** {respuesta}")

                    # 3) Llamar a 'realizar_analisis' para ejecutar esa opción 
                    #    con las variables relevantes detectadas automáticamente
                    resultados, figuras = realizar_analisis(
                        opcion=respuesta,
                        pregunta_usuario=st.session_state['pregunta_usuario'],
                        filtros=filtros_usuario,
                        df_base=df_rango
                    )

                    # 4) Generar el informe en PDF con los resultados y figuras
                    generar_informe(
                        st.session_state['pregunta_usuario'],  # Pregunta
                        respuesta,                              # Opción sugerida
                        resultados,                             # Texto final de resultados
                        figuras                                 # Figuras producidas
                    )

                    # Botón de descarga del PDF recién generado
                    with open('informe_analisis_datos.pdf', 'rb') as f:
                        pdf_data = f.read()
                    b64 = base64.b64encode(pdf_data).decode('utf-8')
                    href = f'<a href="data:application/octet-stream;base64,{b64}" download="informe_analisis_datos.pdf">Descargar Informe en PDF</a>'
                    st.markdown(href, unsafe_allow_html=True)

                    # Marcar que se realizó el análisis
                    st.session_state['analisis_realizado'] = True

                    # Ofrecer volver a hacer otra consulta
                    st.write("Si deseas realizar otra consulta, haz clic en el botón a continuación:")
                    if st.button("Realizar otra consulta"):
                        st.session_state['pregunta_usuario'] = ''
                        st.session_state['filtro_natural'] = ''
                        st.session_state['analisis_realizado'] = False

    else:
        # Si 'analisis_realizado' == True, ya se hizo el análisis en esta sesión
        st.write("Si deseas realizar otra consulta, haz clic en el botón:")
        if st.button("Realizar otra consulta"):
            st.session_state['pregunta_usuario'] = ''
            st.session_state['filtro_natural'] = ''
            st.session_state['analisis_realizado'] = False


if __name__ == "__main__":
    main()
