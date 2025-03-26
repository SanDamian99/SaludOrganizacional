# Importar librerías necesarias
import streamlit as st
import difflib
import pandas as pd
import time
import random
import seaborn as sns
from datetime import datetime, date, timedelta
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
import numpy as np # Asegurarse de importar numpy

# Importar la librería de Gemini
import google.generativeai as genai

# Configurar la API de Gemini
try:
    YOUR_API_KEY = st.secrets["YOUR_API_KEY"]  # Reemplaza con tu clave de API de Gemini
    genai.configure(api_key=YOUR_API_KEY)
except Exception as e:
    st.error(f"Error al configurar la API de Gemini. Asegúrate de que 'YOUR_API_KEY' esté en los secrets de Streamlit. Detalle: {e}")
    st.stop() # Detener la ejecución si la API no se puede configurar

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
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        safety_settings=safety_settings
    )
except Exception as e:
    st.error(f"Error al inicializar el modelo Gemini: {e}")
    st.stop()

# Definir la clase RateLimiter
class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.call_times = []

    def wait(self):
        now = time.time()
        # Eliminar timestamps más antiguos que el periodo
        self.call_times = [t for t in self.call_times if t > now - self.period]
        if len(self.call_times) >= self.max_calls:
            sleep_time = (self.call_times[0] + self.period) - now
            if sleep_time > 0:
                st.write(f"Límite de tasa alcanzado. Esperando {sleep_time:.2f} segundos...")
                time.sleep(sleep_time)
                # Recalcular 'now' y volver a filtrar después de esperar
                now = time.time()
                self.call_times = [t for t in self.call_times if t > now - self.period]
        self.call_times.append(time.time())

# --- NUEVO: Cargar el archivo CSV limpio ---
ruta_csv = 'cleaned_data.csv' # Cambiado a CSV
try:
    # Especificar tipos de datos conocidos durante la carga si es posible
    # Intentar parsear fechas directamente
    df = pd.read_csv(ruta_csv, parse_dates=['Hora de inicio', 'Hora de finalización'], dayfirst=False) # Ajusta dayfirst si es necesario
    df.dropna(axis=1, how='all', inplace=True)
    # Limpiar nombres de columnas por si acaso
    df.columns = df.columns.str.strip()
    st.success(f"Datos cargados correctamente desde {ruta_csv}")
    # Convertir columnas que deberían ser categóricas
    potential_cats = ['Sexo', 'Estado Civil', 'Nivel Educativo', 'Departamento ', 'Ciudad /Municipio',
                      'Zona de vivienda', 'Estrato socioeconomico', 'Sector Económico ', 'Sector empresa',
                      'Tamaño Empresa', 'Trabajo por turnos', 'Tipo de Contrato', 'Ingreso salarial mensual ',
                      'Cargo', 'Personas a cargo en la empresa', 'Años de experiencia laboral',
                      'Antigüedad en el cargo/labor actual ', 'Tipo de modalidad de trabajo',
                      'Tiempo promedio de traslado al trabajo/casa al día ']
    for col in potential_cats:
        if col in df.columns:
            try:
                df[col] = df[col].astype('category')
            except Exception as e:
                st.warning(f"No se pudo convertir '{col}' a categórica: {e}. Se dejará como object.")

except FileNotFoundError:
    st.error(f"Error: No se encontró el archivo '{ruta_csv}'. Asegúrate de que el archivo esté en el mismo directorio o proporciona la ruta correcta.")
    st.stop()
except Exception as e:
    st.error(f"Error al cargar o procesar el archivo CSV '{ruta_csv}': {e}")
    st.stop()


# --- Diccionario de Datos (AJUSTADO) ---
# Ajustar NombresExactos y verificar que las escalas/valores coincidan con los datos LIMPIOS (numéricos)
# Los mapas ValorNumerico (texto->número) ahora son MENOS cruciales para conversión, pero ÚTILES para interpretación/labels
# Las Escalas (número->texto) son IMPORTANTES para labels
data_dictionary = {
    "Variables Sociodemográficas": {
        "Edad": {"Tipo": "Continua", "NombreExacto": "Edad"},
        "Sexo": {"Tipo": "Categórica", "Valores": ["Hombre", "Mujer", "Otro", "Prefiero no decir"], "NombreExacto": "Sexo"},
        "Estado Civil": {"Tipo": "Categórica", "Valores": ["Soltero", "Casado", "Separado", "Unión Libre", "Viudo"], "NombreExacto": "Estado Civil"},
        "Numero de hijos": {"Tipo": "Continua", "NombreExacto": "Numero de hijos"},
        "Nivel Educativo": {"Tipo": "Categórica", "Valores": ["Primaria", "Bachiller", "Técnico", "Tecnológico", "Tecnológo", "Profesional", "Pregrado", "Posgrado", "Maestría", "Doctorado"], "NombreExacto": "Nivel Educativo"},
        "Departamento ": {"Tipo": "Categórica", "NombreExacto": "Departamento "},
        "Ciudad /Municipio": {"Tipo": "Categórica", "NombreExacto": "Ciudad /Municipio"},
        "Zona de vivienda": {"Tipo": "Categórica", "Valores": ["Urbana", "Rural"], "NombreExacto": "Zona de vivienda"},
        "Estrato socioeconomico": {"Tipo": "Categórica", "Valores": [1, 2, 3, 4, 5, 6], "NombreExacto": "Estrato socioeconomico"}
    },
    "Variables Laborales": {
        "Sector Económico ": {"Tipo": "Categórica", "NombreExacto": "Sector Económico "},
        "Sector empresa": {"Tipo": "Categórica", "Valores": ["Público", "Privado", "Mixto"], "NombreExacto": "Sector empresa"},
        "Tamaño Empresa": {"Tipo": "Categórica", "Valores": ["Menos de 10 empleados", "Entre 10 y 50 empleados", "Entre 50 y 200 empleados", "Entre 200 y 500 empleados", "Más de 500 empleados"], "NombreExacto": "Tamaño Empresa"},
        "Trabajo por turnos": {"Tipo": "Categórica", "Valores": ["Sí", "No"], "NombreExacto": "Trabajo por turnos"}, # Asumiendo limpio
        "Tipo de Contrato": {"Tipo": "Categórica", "Valores": ["Indefinido", "Termino Indefinido", "Término fijo", "Obra o labor", "Aprendizaje", "Aprendizaje- SENA", "Presentación de servicios", "Temporal", "No hay información"], "NombreExacto": "Tipo de Contrato"},
        "Número de horas de trabajo semanal ": {"Tipo": "Continua", "NombreExacto": "Número de horas de trabajo semanal "},
        "Ingreso salarial mensual ": {"Tipo": "Categórica", "Valores": ["Menos de 1 SMLV", "Entre 1 y 3 SMLV", "Entre 3 y 5 SMLV", "Entre 5 y 10 SMLV", "Más de 10 SMLV"], "NombreExacto": "Ingreso salarial mensual "},
        "Cargo": {"Tipo": "Categórica", "Valores": ["Operativo", "Administrativo", "Directivo", "Profesional", "Técnico", "Asistencial", "Aprendiz SENA"], "NombreExacto": "Cargo"},
        "Personas a cargo en la empresa": {"Tipo": "Categórica", "Valores": ["Sí", "No"], "NombreExacto": "Personas a cargo en la empresa"}, # Asumiendo limpio
        "Años de experiencia laboral": {"Tipo": "Categórica", "Valores": ["Menos de 1 año", "Entre 1 a 5", "Entre 5 a 10", "Entre 10 a 15", "Entre 15 a 20", "Entre 20 a 25", "Más de 25"], "NombreExacto": "Años de experiencia laboral"},
        "Antigüedad en el cargo/labor actual ": {"Tipo": "Categórica", "Valores": ["Menos de 1 año", "Entre 1 y 3 años", "Entre 3 y 7 años", "Entre 7 y 10 años", "Más de 10 años", "No hay información"], "NombreExacto": "Antigüedad en el cargo/labor actual "},
        "Tipo de modalidad de trabajo": {"Tipo": "Categórica", "Valores": ["Presencial", "Híbrido", "Remoto", "Teletrabajo", "Trabajo en casa"], "NombreExacto": "Tipo de modalidad de trabajo"},
        "Tiempo promedio de traslado al trabajo/casa al día ": {"Tipo": "Categórica", "Valores": ["Menos de 1 hora", "Entre 1 y 2 horas", "Entre 2 y 3 horas", "Más de 3 horas"], "NombreExacto": "Tiempo promedio de traslado al trabajo/casa al día "},
        "Horas de formación recibidas (ultimo año)": {"Tipo": "Continua", "NombreExacto": "Horas de formación recibidas (ultimo año)"}
    },
    "Dimensiones de Bienestar y Salud Mental": {
        # --- Escala Likert 1-7 (Frecuencia General) --- (AHORA SON INT)
        "Control del Tiempo": {
            "Tipo": "Likert",
            "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
            "ValorNumerico": {'nunca': 1, 'rara vez': 2, 'alguna vez': 3, 'algunas veces': 4, 'a menudo': 5, 'frecuentemente': 6, 'siempre': 7}, # Para interpretación
            "Preguntas": [
                "Tengo la opción de decidir qué hago en mi trabajo.",
                "Tengo algo que decir sobre la forma en que hago mi trabajo.", # Doble espacio quitado
                "Tengo voz y voto sobre mi propio ritmo de trabajo.", # Doble espacio quitado
                "Me presionan para que trabaje muchas horas.", # Doble espacio quitado
                "Tengo algunos plazos de entrega inalcanzables.", # Doble espacio quitado
                "Tengo presiones de tiempo poco realistas.", # Doble espacio quitado
                "Tengo que descuidar algunas tareas porque tengo mucho que hacer." # Doble espacio quitado
            ]
        },
        "Compromiso del Líder": {
            "Tipo": "Likert",
            "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
             "ValorNumerico": {'nunca': 1, 'rara vez': 2, 'alguna vez': 3, 'algunas veces': 4, 'a menudo': 5, 'frecuentemente': 6, 'siempre': 7},
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
            "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
            "ValorNumerico": {'nunca': 1, 'rara vez': 2, 'alguna vez': 3, 'algunas veces': 4, 'a menudo': 5, 'frecuentemente': 6, 'siempre': 7},
            "Preguntas": [
                "Si el trabajo se pone difícil, mis compañeros de trabajo me ayudarán.",
                "Recibo la ayuda y el apoyo que necesito de mis compañeros de trabajo.",
                "Mis compañeros de trabajo están dispuestos a escuchar mis problemas laborales."
            ]
        },
         "Claridad de Rol": {
            "Tipo": "Likert",
            "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
            "ValorNumerico": {'nunca': 1, 'rara vez': 2, 'alguna vez': 3, 'algunas veces': 4, 'a menudo': 5, 'frecuentemente': 6, 'siempre': 7},
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
            "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
            "ValorNumerico": {'nunca': 1, 'rara vez': 2, 'alguna vez': 3, 'algunas veces': 4, 'a menudo': 5, 'frecuentemente': 6, 'siempre': 7},
            "Preguntas": [
                "Me consultan sobre cambios propuestos en el trabajo.",
                "Cuando se realizan cambios en el trabajo, tengo claro cómo funcionarán en la práctica.",
                "Estoy claramente informado sobre la naturaleza de los cambios que se producen en esta organización.",
                "Puedo expresar inquietudes sobre cambios que afectan mi trabajo."
            ]
        },
        "Responsabilidad Organizacional": {
            "Tipo": "Likert",
            "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
            "ValorNumerico": {'nunca': 1, 'rara vez': 2, 'alguna vez': 3, 'algunas veces': 4, 'a menudo': 5, 'frecuentemente': 6, 'siempre': 7},
            "Preguntas": [
                "En mi lugar de trabajo la salud física y mental es un prioridad de los líderes.",
                "En mi lugar de trabajo se hacen mediciones periódicas de los niveles de salud mental de las personas.",
                "En mi lugar de trabajo existen recursos accesibles y fáciles de usar para las necesidades relacionadas con la salud mental de las personas.",
                "Recibo entrenamiento periódico sobre pautas para el cuidado de mi salud mental en el trabajo.",
                "En mi lugar de trabajo se comunican claramente los resultados de las acciones implementadas para el cuidado de la salud mental de las personas." # Nombre asumido limpio
            ]
        },
        # --- Escala Likert 1-7 (Acuerdo) --- (AHORA SON INT)
        "Conflicto Familia-Trabajo": {
            "Tipo": "Likert",
            "Escala": {1: "Totalmente en desacuerdo", 2: "Muy en desacuerdo/Mod. en desac.", 3: "Algo en desacuerdo", 4: "Ni de acuerdo ni en desacuerdo", 5: "Algo de acuerdo", 6: "Muy de acuerdo/Mod. de acuerdo", 7: "Totalmente de acuerdo"}, # Simplificado
            "ValorNumerico": {
                'totalmente en desacuerdo': 1, 'muy en desacuerdo': 2, 'moderadamente en desacuerdo': 2,
                'algo en desacuerdo': 3, 'ligeramente en desacuerdo': 3, 'ni de acuerdo ni en desacuerdo': 4,
                'algo de acuerdo': 5, 'ligeramente de acuerdo': 5, 'muy de acuerdo': 6, 'moderadamente de acuerdo': 6,
                'totalmente de acuerdo': 7
            },
            "Preguntas": [
                "Las demandas de mi familia o cónyuge / pareja interfieren con las actividades relacionadas con el trabajo.", # Dobles espacios quitados
                "Tengo que posponer las tareas en el trabajo debido a las exigencias de mi tiempo en casa.", # Dobles espacios quitados
                "Las cosas que quiero hacer en el trabajo no se hacen debido a las demandas de mi familia o mi cónyuge / pareja.", # Dobles espacios quitados
                "Mi vida hogareña interfiere con mis responsabilidades en el trabajo, como llegar al trabajo a tiempo, realizar las tareas diarias y trabajar.", # Dobles espacios quitados
                "La tensión relacionada con la familia interfiere con mi capacidad para realizar tareas relacionadas con el trabajo.", # Dobles espacios quitados
                "Las exigencias de mi trabajo interfieren con mi hogar y mi vida familiar.",
                "La cantidad de tiempo que ocupa mi trabajo dificulta el cumplimiento de las responsabilidades familiares.",
                "Las cosas que quiero hacer en casa no se hacen debido a las exigencias que me impone mi trabajo.",
                "Mi trabajo produce tensión que dificulta el cumplimiento de los deberes familiares.",
                "Debido a deberes relacionados con el trabajo, tengo que hacer cambios en mis planes para las actividades familiares." # Nombre asumido limpio
            ]
        },
        # --- Escala Likert 1-5 (Burnout) --- (AHORA SON INT)
        "Síntomas de Burnout": {
            "Tipo": "Likert",
            "Escala": {1: "Nunca", 2: "Raramente", 3: "Algunas veces", 4: "A menudo", 5: "Siempre"},
            "ValorNumerico": {"nunca": 1, "raramente": 2, "algunas veces": 3, "a menudo": 4, "siempre": 5}, # Ojo 'Alguna Veces' en mapping nuevo?
            "Preguntas": [
                "En mi trabajo, me siento agotado/a emocionalmente.", # Dobles espacios quitados
                "Al final del día de trabajo, me resulta difícil recuperar mi energía.", # Dobles espacios quitados
                "Me siento físicamente agotado/a en mi trabajo.", # Dobles espacios quitados
                "Me cuesta encontrar entusiasmo por mi trabajo.", # Dobles espacios quitados
                "Siento una fuerte aversión hacia mi trabajo.", # Dobles espacios quitados
                "Soy cínico (despreocupado) sobre lo que mi trabajo significa para los demás.", # Dobles espacios quitados
                "Tengo problemas para mantenerme enfocado en mi trabajo.", # Dobles espacios quitados
                "Cuando estoy trabajando, tengo dificultades para concentrarme.", # Dobles espacios quitados
                "Cometo errores en mi trabajo, porque tengo mi mente en otras cosas.", # Dobles espacios quitados
                "En mi trabajo, me siento incapaz de controlar mis emociones.", # Dobles espacios quitados
                "No me reconozco en la forma que reacciono en el trabajo.", # Dobles espacios quitados
                "Puedo reaccionar exageradamente sin querer." # Dobles espacios quitados
             ]
        },
        # --- Escala Likert 1-6 (Acuerdo - Compromiso, Defensa, Satisfacción, Retiro) --- (AHORA SON INT)
        "Compromiso": {
            "Tipo": "Likert",
            "Escala": {1: "Muy en desacuerdo", 2: "Moderadamente en desacuerdo", 3: "Ligeramente en desacuerdo", 4: "Ligeramente de acuerdo", 5: "Moderadamente de acuerdo", 6: "Muy de acuerdo"},
            "ValorNumerico": {"muy en desacuerdo": 1, "moderadamente en desacuerdo": 2, "ligeramente en desacuerdo": 3, "ligeramente de acuerdo": 4, "moderadamente de acuerdo": 5, "muy de acuerdo": 6},
            "Preguntas": [
                "Mi labor contribuye a la misión y visión de la empresa para la que laboro.", # Doble espacio quitado
                "Me siento entusiasmado por mi trabajo.", # Doble espacio quitado
                "Cuando me levanto en la mañana tengo ganas de ir a trabajar." # Nombre asumido limpio
            ]
        },
        "Defensa de la Organización": {
            "Tipo": "Likert",
             "Escala": {1: "Muy en desacuerdo", 2: "Moderadamente en desacuerdo", 3: "Ligeramente en desacuerdo", 4: "Ligeramente de acuerdo", 5: "Moderadamente de acuerdo", 6: "Muy de acuerdo"},
            "ValorNumerico": {"muy en desacuerdo": 1, "moderadamente en desacuerdo": 2, "ligeramente en desacuerdo": 3, "ligeramente de acuerdo": 4, "moderadamente de acuerdo": 5, "muy de acuerdo": 6},
            "Preguntas": [
                "Me siento orgulloso de la empresa en la que laboro.", # Doble espacio quitado
                "Recomendaría ampliamente a otros trabajar en la empresa en la que laboro.", # Doble espacio quitado
                "Me molesta que otros hablen mal de la empresa en la que laboro." # Nombre asumido limpio
            ]
        },
        "Satisfacción": {
            "Tipo": "Likert",
             "Escala": {1: "Muy en desacuerdo", 2: "Moderadamente en desacuerdo", 3: "Ligeramente en desacuerdo", 4: "Ligeramente de acuerdo", 5: "Moderadamente de acuerdo", 6: "Muy de acuerdo"},
            "ValorNumerico": {"muy en desacuerdo": 1, "moderadamente en desacuerdo": 2, "ligeramente en desacuerdo": 3, "ligeramente de acuerdo": 4, "moderadamente de acuerdo": 5, "muy de acuerdo": 6},
            "Preguntas": [
                "Considero mi trabajo significativo.", # Doble espacio quitado
                "Me gusta hacer las tareas y actividades de mi trabajo.", # Doble espacio quitado
                "Me siento satisfecho por el salario y los beneficios que recibo en mi trabajo." # Nombre asumido limpio
            ]
        },
        "Intención de Retiro": {
            "Tipo": "Likert",
             "Escala": {1: "Muy en desacuerdo", 2: "Moderadamente en desacuerdo", 3: "Ligeramente en desacuerdo", 4: "Ligeramente de acuerdo", 5: "Moderadamente de acuerdo", 6: "Muy de acuerdo"},
            "ValorNumerico": {"muy en desacuerdo": 1, "moderadamente en desacuerdo": 2, "ligeramente en desacuerdo": 3, "ligeramente de acuerdo": 4, "moderadamente de acuerdo": 5, "muy de acuerdo": 6},
            "Preguntas": [
                "Me veo trabajando en este lugar en el próximo año.", # Doble espacio quitado
                "A menudo considero seriamente dejar mi trabajo actual.", # Doble espacio quitado
                "Tengo la intención de dejar mi trabajo actual en los próximos 3 a 6 meses.", # Doble espacio quitado
                "He empezado a buscar activamente otro trabajo." # Nombre asumido limpio
            ]
        },
        # --- Escalas Diferencial Semántico 1-7 --- (AHORA SON INT)
        "Bienestar Psicosocial (Escala de Afectos)": {
            "Tipo": "Diferencial Semántico",
            "Escala": {1: "Extremo Izq", 7: "Extremo Der"}, # Ejemplo genérico
            "ValorNumerico": {}, # No se usa mapeo, se asume numérico
            "Preguntas": [str(i) for i in range(2, 11)] # Columnas '2' a '10'
        },
         # --- Escala Competencias --- (AHORA SON INT)
        "Bienestar Psicosocial (Escala de Competencias)": {
            "Tipo": "Diferencial Semántico",
            "Escala": {1: "Extremo Izq", 7: "Extremo Der"},
            "ValorNumerico": {},
            "Preguntas": [str(i) for i in range(11, 21)] # Columnas '11' a '20'
        },
        # --- Escala Likert 1-7 (Expectativas) --- (AHORA SON INT)
        "Bienestar Psicosocial (Escala de Expectativas)": {
            "Tipo": "Likert",
            "Escala": {1: "Bajando", 7: "Subiendo"}, # Asumido
            "ValorNumerico": {}, # No se usa mapeo, se asume numérico
            "Preguntas": [
                "Mi motivación por el trabajo", # Doble espacio quitado
                "Mi identificación con los valores de la organización.", # Nombre asumido
                "Mi rendimiento profesional.", # Nombre asumido
                "Mi capacidad para responder a mi carga de trabajo.", # Asumido sin espacio extra
                "La calidad de mis condiciones de trabajo.", # Nombre asumido
                "Mi autoestima profesional",
                "La cordialidad en mi ambiente social de trabajo.", # Nombre asumido
                "El equilibrio entre mi trabajo y mi vida privada.", # Nombre asumido
                "Mi confianza en mi futuro profesional",
                "Mi calidad de vida laboral.", # Nombre asumido
                "El sentido de mi trabajo",
                "Mi cumplimiento de las normas de la dirección.", # Nombre asumido
                "Mi estado de ánimo laboral ", # Espacio al final? Verificar CSV
                "Mis oportunidades de promoción laboral.", # Nombre asumido
                "Mi sensación de seguridad en el trabajo",
                "Mi participación en las decisiones de la organización.", # Nombre asumido
                "Mi satisfacción con el trabajo.", # Nombre asumido
                "Mi relación profesional.", # Nombre asumido
                "El nivel de excelencia de mi organización.", # Nombre asumido
                "MI eficacia profesional", # 'MI' mayúscula? Verificar CSV
                "Mi compromiso con el trabajo",
                "Mis competencias profesionales"
            ]
        },
        # --- Escala Likert 1-7 (Efectos Colaterales) --- (AHORA SON INT)
        "Factores de Efectos Colaterales (Escala de Somatización)": {
            "Tipo": "Likert",
            "Escala": {1: "Nunca", 2: "Raramente", 3: "Ocasionalmente", 4: "Algunas veces", 5: "Frecuentemente", 6: "Casi siempre", 7: "Siempre"},
            "ValorNumerico": {"nunca": 1, "raramente": 2, "ocasionalmente": 3, "algunas veces": 4, "frecuentemente": 5, "casi siempre": 6, "siempre": 7},
            "Preguntas": [
                "Trastornos digestivos", # Doble espacio quitado
                "Dolores de cabeza",
                "Alteraciones de sueño", # Doble espacio quitado
                "Dolores de espalda",
                "Tensiones musculares" # Doble espacio quitado
            ]
        },
        "Factores de Efectos Colaterales (Escala de Desgaste)": {
            "Tipo": "Likert",
             "Escala": {1: "Nunca", 2: "Raramente", 3: "Ocasionalmente", 4: "Algunas veces", 5: "Frecuentemente", 6: "Casi siempre", 7: "Siempre"},
            "ValorNumerico": {"nunca": 1, "raramente": 2, "ocasionalmente": 3, "algunas veces": 4, "frecuentemente": 5, "casi siempre": 6, "siempre": 7},
            "Preguntas": [
                "Sobrecarga de trabajo", # Doble espacio quitado
                "Desgaste emocional",
                "Agotamiento físico",
                "Cansancio mental " # Espacio al final? Verificar CSV
            ]
        },
        "Factores de Efectos Colaterales (Escala de Alienación)": {
            "Tipo": "Likert",
             "Escala": {1: "Nunca", 2: "Raramente", 3: "Ocasionalmente", 4: "Algunas veces", 5: "Frecuentemente", 6: "Casi siempre", 7: "Siempre"},
            "ValorNumerico": {"nunca": 1, "raramente": 2, "ocasionalmente": 3, "algunas veces": 4, "frecuentemente": 5, "casi siempre": 6, "siempre": 7},
            "Preguntas": [
                "Mal humor ", # Espacio al final? Verificar CSV
                "Baja realización personal", # Doble espacio quitado
                "Trato distante",
                "Frustración " # Espacio al final? Verificar CSV
            ]
        }
    }
}

# --- Limpiar nombres en 'Preguntas' y asegurar que sean strings ---
for dim_cat, dim_content in data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {}).items():
    if "Preguntas" in dim_content:
        # Asegurar que sean strings y quitar espacios extra
        dim_content["Preguntas"] = [str(p).strip() for p in dim_content["Preguntas"]]

# --- Limpiar claves de ValorNumerico ---
for dim_cat, dim_content in data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {}).items():
     if "ValorNumerico" in dim_content and isinstance(dim_content["ValorNumerico"], dict):
         dim_content["ValorNumerico"] = {str(k).lower().strip(): v for k, v in dim_content["ValorNumerico"].items()}

# --- Mapeos Manuales (proporcionados por el usuario) ---
# Estos son cruciales para interpretar los números y poner labels en los gráficos
# Asegúrate de que las claves (tuplas) y los mapeos internos sean correctos
likert_manual_mappings = {
    ('Casado', 'Separado', 'Soltero', 'Unión libre', 'Viudo'): {
        'Casado': 1, 'Separado': 2, 'Soltero': 3, 'Unión libre': 4, 'Viudo': 5
    },
    ('Entre 10 y 50 empleados', 'Entre 200 y 500 empleados', 'Entre 50 y\xa0 200 empleados', 'Más de 500 empleados', 'Menos de 10 empleados'): {
        'Menos de 10 empleados': 1, 'Entre 10 y 50 empleados': 2, 'Entre 50 y\xa0 200 empleados': 3, 'Entre 200 y 500 empleados': 4, 'Más de 500 empleados': 5
    },
    ('Entre 1 y 3 SMLV', 'Entre 3 y 5 SMLV', 'Entre 5 y 10 SMLV', 'Más de 10 SMLV', 'Menos de 1 SMLV'): {
        'Menos de 1 SMLV': 1, 'Entre 1 y 3 SMLV': 2, 'Entre 3 y 5 SMLV': 3, 'Entre 5 y 10 SMLV': 4, 'Más de 10 SMLV': 5
    },
    ('Administrativo', 'Aprendiz SENA', 'Asistencial', 'Directivo', 'Operativo', 'Profesional', 'Técnico'): {
        'Administrativo': 1, 'Aprendiz SENA': 2, 'Asistencial': 3, 'Directivo': 4, 'Operativo': 5, 'Profesional': 6, 'Técnico': 7
    },
    ('Entre 1 a 5', 'Entre 10 a 15', 'Entre 15 a 20', 'Entre 20 a 25', 'Entre 5 a 10', 'Menos de 1 año', 'Más de 25'): {
        'Menos de 1 año': 1, 'Entre 1 a 5': 2, 'Entre 5 a 10': 3, 'Entre 10 a 15': 4, 'Entre 15 a 20': 5, 'Entre 20 a 25': 6, 'Más de 25': 7
    },
    ('Híbrido', 'Presencial', 'Remoto', 'Teletrabajo', 'Trabajo en casa'): {
        'Híbrido': 1, 'Presencial': 2, 'Remoto': 3, 'Teletrabajo': 4, 'Trabajo en casa': 5
    },
    ('Alguna vez', 'Algunas veces', 'Frecuentemente', 'Nunca', 'Rara vez', 'Siempre', '\xa0A menudo'): {
        'Nunca': 1, 'Rara vez': 2, 'Alguna vez': 3, 'Algunas veces': 4, '\xa0A menudo': 5, 'Frecuentemente': 6, 'Siempre': 7
    },
    ('Algo de acuerdo', 'Algo en desacuerdo', 'Moderadamente en desacuerdo', 'Muy de acuerdo', 'Ni de acuerdo ni en desacuerdo', 'Totalmente de acuerdo', 'Totalmente en desacuerdo'): {
        'Totalmente en desacuerdo': 1, 'Moderadamente en desacuerdo': 2, 'Algo en desacuerdo': 3, 'Ni de acuerdo ni en desacuerdo': 4, 'Algo de acuerdo': 5, 'Muy de acuerdo': 6, 'Totalmente de acuerdo': 7
    },
    ('Algo de acuerdo', 'Algo en desacuerdo', 'Muy de acuerdo', 'Muy en desacuerdo', 'Ni de acuerdo ni en desacuerdo', 'Totalmente de acuerdo', 'Totalmente en desacuerdo'): {
        'Totalmente en desacuerdo': 1, 'Muy en desacuerdo': 2, 'Algo en desacuerdo': 3, 'Ni de acuerdo ni en desacuerdo': 4, 'Algo de acuerdo': 5, 'Muy de acuerdo': 6, 'Totalmente de acuerdo': 7
    },
    # OJO: 'Alguna Veces' con V mayúscula vs 'algunas veces' en data_dict. Usar la que esté en los datos. Asumimos 'Algunas veces'.
    ('A menudo', 'Algunas veces', 'Nunca', 'Raramente', 'Siempre'): { # Asumiendo 'Algunas veces'
        'Nunca': 1, 'Raramente': 2, 'Algunas veces': 3, 'A menudo': 4, 'Siempre': 5
    },
    ('Algunas veces', 'Casi siempre', 'Frecuentemente', 'Nunca', 'Ocasionalmente', 'Raramente', 'Siempre'): {
        'Nunca': 1, 'Raramente': 2, 'Ocasionalmente': 3, 'Algunas veces': 4, 'Frecuentemente': 5, 'Casi siempre': 6, 'Siempre': 7
    }
}

# Crear un mapeo inverso (número -> etiqueta) para facilitar la búsqueda de labels
label_maps = {}
for scale_tuple, mapping in likert_manual_mappings.items():
    inverse_map = {v: k for k, v in mapping.items()}
    # Asociar este mapeo inverso con las columnas correspondientes en data_dictionary
    for dim_cat, dim_content in data_dictionary.items():
        if "Preguntas" in dim_content:
            for pregunta_col in dim_content["Preguntas"]:
                # Heurística: si la escala del diccionario coincide (aprox) con la clave del mapping
                dict_escala = tuple(sorted(dim_content.get("Escala", {}).values())) if isinstance(dim_content.get("Escala"), dict) else ()
                map_key_sorted = tuple(sorted([k.replace('\xa0', ' ') for k in scale_tuple])) # Normalizar \xa0

                # Comprobar si los conjuntos de etiquetas son similares
                if set(dict_escala) == set(map_key_sorted):
                     label_maps[pregunta_col.strip()] = inverse_map
                     #st.write(f"DEBUG: Mapeo de etiquetas asignado a '{pregunta_col.strip()}'")


# Extraer información de las columnas y tipos de datos del DF CARGADO
def obtener_informacion_datos(df_loaded):
    buffer = io.StringIO()
    df_loaded.info(buf=buffer)
    s = buffer.getvalue()
    # También añadir unique values para categóricas si no son demasiados
    cat_cols_summary = []
    for col in df_loaded.select_dtypes(include=['category', 'object']).columns:
         unique_count = df_loaded[col].nunique()
         if unique_count < 50: # Mostrar solo si no hay demasiados únicos
             uniques = df_loaded[col].unique()
             cat_cols_summary.append(f"\n- {col} ({unique_count} unique): {uniques}")
         else:
             cat_cols_summary.append(f"\n- {col} ({unique_count} unique)")

    return s + "\n\nResumen de únicas en Categóricas/Object:" + "".join(cat_cols_summary)

informacion_datos = obtener_informacion_datos(df) # Pasar el df cargado

# Definir las opciones de análisis disponibles (sin cambios)
opciones_analisis = """
Opciones de análisis disponibles:

1. **Distribución de variable categórica:** Explora cómo se distribuyen los datos en una variable categórica (no numérica). Muestra la frecuencia de cada categoría mediante tablas y gráficos (barras, pastel, barras horizontales). Utiliza las etiquetas correctas si es una escala Likert mapeada.

   *Ejemplo:* Si eliges la variable "Estado Civil", el análisis mostrará cuántas veces aparece "Soltero", "Casado", etc.

2. **Estadísticas descriptivas de variable numérica:**  Calcula y muestra las estadísticas descriptivas (media, mediana, desviación estándar, mínimo, máximo, etc.) de una variable numérica, proporcionando un resumen de su distribución.  Incluye visualizaciones como histogramas, boxplots y gráficos de densidad para comprender la forma de la distribución, identificar valores atípicos y analizar la dispersión de los datos.

   *Ejemplo:*  Si eliges la variable "Edad", el análisis calculará la edad promedio, la edad que se encuentra en el medio del conjunto de datos,  cómo se agrupan las edades, etc.

3. **Relación entre dos variables numéricas:** Analiza la relación entre dos variables numéricas. Se mostrarán gráficos de dispersión, hexágonos y densidad conjunta para visualizar la correlación entre las variables. También se calculará el coeficiente de correlación para cuantificar la fuerza y dirección de la relación.

   *Ejemplo:*  Si eliges las variables "Edad" y una dimensión de bienestar como "Compromiso del Líder" (promedio o ítem específico), el análisis mostrará si existe una relación.

4. **Filtrar datos y mostrar estadísticas:** Permite filtrar los datos según criterios específicos y luego calcular estadísticas descriptivas de una variable numérica en el conjunto de datos filtrado.  Se incluyen visualizaciones como histogramas, boxplots y gráficos de densidad para el análisis del subconjunto de datos.

   *Ejemplo:* Puedes filtrar los datos para incluir solo a las personas con "Cargo" = 'Directivo' y luego analizar la distribución de la dimensión "Satisfacción".

5. **Correlación entre variables numéricas:** Calcula la correlación entre múltiples variables numéricas y muestra los resultados en una matriz de correlación.  Se incluyen visualizaciones como mapas de calor, matrices de dispersión y gráficos de correlación para identificar patrones y relaciones entre las variables.

   *Ejemplo:*  Si seleccionas "Edad", "Numero de hijos" y la dimensión "Síntomas de Burnout", el análisis mostrará la correlación entre cada par.

6. **Análisis de regresión simple:** Realiza un análisis de regresión lineal simple para modelar la relación entre dos variables numéricas. Se mostrará el coeficiente de determinación (R^2), el intercepto y los coeficientes del modelo.  Se incluyen visualizaciones como gráficos de dispersión con línea de regresión, gráficos de residuales y la distribución de los residuales para evaluar la calidad del modelo.

   *Ejemplo:*  Puedes analizar cómo la variable "Número de horas de trabajo semanal " (variable independiente) afecta a la dimensión "Conflicto Familia-Trabajo" (variable dependiente).

7. **Tablas de Contingencia y Chi-cuadrado:** Permite analizar la relación entre dos variables categóricas o entre una variable categórica y una numérica (agrupando la numérica). Se calculará la tabla de contingencia y se realizará la prueba Chi-cuadrado para ver la asociación. Los ejes de la tabla y gráfico mostrarán las etiquetas correctas.

   *Ejemplo:* Analizar la relación entre "Sexo" y "Tiene_Hijos" (derivada de Numero de hijos) o entre "Nivel Educativo" y "Satisfacción" (agrupada).
"""

# Preparar el prompt para Gemini con la info actualizada del DF
prompt_informacion_datos = f"""
Los siguientes son los datos y tipos de datos que tenemos (basado en el archivo CSV limpio):

{informacion_datos}

También tenemos un diccionario que describe las variables y sus significados, incluyendo escalas Likert (aunque ahora estén como números en los datos):
{data_dictionary}

Y las opciones de análisis disponibles son:

{opciones_analisis}

Por favor, utiliza esta información para entender los datos disponibles, los tipos de datos asociados (int, float, category, datetime, object) y las opciones de análisis que podemos realizar. Presta atención a que muchas escalas Likert ahora son numéricas (int).
"""

# Enviar el prompt inicial a Gemini
rate_limiter = RateLimiter(max_calls=4, period=61) # Ajusta si es necesario

def enviar_prompt(prompt):
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            rate_limiter.wait()
            response = model.generate_content([prompt])
            # Añadir manejo básico si la respuesta no es como se espera
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            elif response and hasattr(response, 'parts'): # Manejo alternativo para algunas versiones/respuestas
                 return "".join(part.text for part in response.parts).strip()
            else:
                st.warning(f"Respuesta inesperada de Gemini (intento {retries+1}): {response}")
                # Fallback o reintento
                if retries == max_retries - 1:
                     return "No se recibió una respuesta de texto válida de Gemini."
        except (ConnectionError, ProtocolError) as e:
            wait_time = 2 ** retries + random.random()
            st.warning(f"Error de conexión/protocolo con Gemini: {e}. Reintentando en {wait_time:.2f} segundos...")
            time.sleep(wait_time)
        except Exception as e:
            # Capturar errores más específicos de la API si es posible
            st.error(f"Error inesperado al llamar a Gemini API (intento {retries+1}): {e}")
            wait_time = 2 ** retries + random.random()
            time.sleep(wait_time) # Esperar antes de reintentar
            if "API key not valid" in str(e):
                 st.error("La clave API de Gemini no es válida. Verifica los secrets.")
                 return "Error crítico: Clave API inválida."
            if retries == max_retries - 1:
                 return "Error al comunicarse con Gemini después de varios intentos."
        retries += 1
    return "Error: No se pudo comunicar con Gemini." # Mensaje final si todos los reintentos fallan

# Enviar la información de datos a Gemini
with st.spinner("Informando a Gemini sobre la estructura de datos..."):
    respuesta_informacion_datos = enviar_prompt(prompt_informacion_datos)
    if "Error" in respuesta_informacion_datos:
        st.error(f"No se pudo informar a Gemini correctamente: {respuesta_informacion_datos}")
    else:
        st.write("Gemini ha sido informado sobre los datos y opciones de análisis.")

# --- Función para procesar una pregunta del usuario (sin cambios) ---
def procesar_pregunta(pregunta_usuario):
    prompt_pregunta = f"""
Utilizando la información de los datos proporcionados y las opciones de análisis disponibles:

{informacion_datos}
{data_dictionary}

Opciones de análisis:

{opciones_analisis}

Un miembro de la empresa ha hecho la siguiente pregunta:

{pregunta_usuario}

Por favor, decide cuál de las opciones de análisis (1-7) es más adecuada para responder a esta pregunta. Solo responde con el número de la opción más relevante (del 1 al 7). Solo puede ser un número.
"""
    respuesta = enviar_prompt(prompt_pregunta)
    # Validar que la respuesta sea un número entre 1 y 7
    try:
        opcion = int(respuesta)
        if 1 <= opcion <= 7:
            return str(opcion)
        else:
            st.warning(f"Gemini devolvió un número fuera de rango ({respuesta}). Se intentará deducir o pedir aclaración.")
            # Podríamos intentar un fallback o pedir al usuario
            return None # Indicar fallo
    except (ValueError, TypeError):
        st.warning(f"Gemini no devolvió un número válido ({respuesta}). Se intentará deducir o pedir aclaración.")
        # Podríamos intentar extraer un número del texto si lo hubiera
        match = re.search(r'\b([1-7])\b', respuesta)
        if match:
            st.info(f"Se extrajo el número {match.group(1)} de la respuesta.")
            return match.group(1)
        return None # Indicar fallo


# --- Función obtener_variables_relevantes (AJUSTADA) ---
def obtener_variables_relevantes(pregunta, tipo_variable, df_current):
    """
    Selecciona columnas relevantes del df_current según el tipo solicitado
    (numérica/categórica/todas), usando fuzzy matching con la pregunta y
    la lista de columnas disponibles en df_current.
    Prioriza dimensiones de salud mental si la pregunta lo sugiere.
    """
    keywords_salud_mental = ["salud mental", "bienestar", "burnout", "estrés", "estres", "satisfacción", "compromiso"]
    lower_pregunta = pregunta.lower()
    sugerir_dim_salud = any(kw in lower_pregunta for kw in keywords_salud_mental)

    # Listas reales de df_current
    all_cols = df_current.columns.tolist()
    numeric_cols = df_current.select_dtypes(include=np.number).columns.tolist() # Incluye int y float
    cat_cols = df_current.select_dtypes(include=['category', 'object']).columns.tolist()

    # Filtrar candidatas según 'tipo_variable'
    if tipo_variable.lower() in ["numérica", "numerica"]:
        candidate_cols = numeric_cols
    elif tipo_variable.lower() in ["categórica", "categorica"]:
        candidate_cols = cat_cols
    else: # 'todas'
        candidate_cols = all_cols

    # --- 1) Buscar en las dimensiones de salud mental (si lo amerita) ---
    prioridad_salud = []
    if sugerir_dim_salud:
        for dim_name, details in data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {}).items():
            if "Preguntas" in details:
                for col_dicc in details["Preguntas"]:
                    col_dicc_cleaned = col_dicc.strip() # Usar el nombre limpio
                    # Buscar coincidencia flexible con cada col real
                    close_matches = difflib.get_close_matches(col_dicc_cleaned, all_cols, n=1, cutoff=0.8) # Mayor cutoff
                    if close_matches:
                        col_real = close_matches[0]
                        if col_real in candidate_cols and col_real not in prioridad_salud:
                             prioridad_salud.append(col_real)

    # --- 2) Usar Gemini para sugerir columnas relevantes (más robusto) ---
    prompt_variables = f"""
    Basado en el DataFrame con estas columnas y tipos:
    {df_current.dtypes.to_string()}

    Y la pregunta del usuario: '{pregunta}'

    Considerando que se busca(n) variable(s) de tipo '{tipo_variable}',
    lista los nombres EXACTOS de las columnas del DataFrame que sean más relevantes para responder la pregunta.
    La primera variable debe ser la más relevante. Si la pregunta compara dos variables, ponlas en las posiciones 0 y 1.
    Después, lista otras variables potencialmente relevantes.
    Devuelve SOLO la lista de nombres de columna separados por comas, sin explicaciones.
    Ejemplo: Edad, Satisfacción, Nivel Educativo
    """
    resp_gemini = enviar_prompt(prompt_variables)

    # Parsear y validar respuesta de Gemini con fuzzy match
    variables_sugeridas = []
    if "Error" not in resp_gemini and resp_gemini:
        suggested_by_gemini = [x.strip() for x in resp_gemini.split(',') if x.strip()]
        for sug in suggested_by_gemini:
            close = difflib.get_close_matches(sug, candidate_cols, n=1, cutoff=0.7) # Umbral flexible
            if close and close[0] not in variables_sugeridas:
                variables_sugeridas.append(close[0])
    else:
        st.warning(f"Gemini no pudo sugerir variables relevantes: {resp_gemini}. Se usará una lista genérica.")
        # Fallback: tomar las primeras candidatas
        variables_sugeridas = candidate_cols[:5] # Tomar hasta 5 como fallback

    # --- 3) Combinar y filtrar ---
    # Unir "prioridad_salud" con "variables_sugeridas" sin duplicar, manteniendo orden
    final_list = []
    for c in prioridad_salud + variables_sugeridas:
        if c not in final_list and c in candidate_cols: # Asegurar que aún cumple el tipo
            final_list.append(c)

    # Filtrar columnas que no tengan datos (solo NaNs)
    final_list_no_empty = [col for col in final_list if df_current[col].notna().any()]

    if not final_list_no_empty:
        st.warning(f"No se encontraron columnas relevantes de tipo '{tipo_variable}' con datos para la pregunta.")
        # Fallback final: devolver las candidatas originales no vacías
        final_list_no_empty = [col for col in candidate_cols if df_current[col].notna().any()]

    #st.write(f"DEBUG - Variables relevantes ({tipo_variable}): {final_list_no_empty}")
    return final_list_no_empty


# --- Función para procesar filtros (sin cambios) ---
def procesar_filtros(filtro_natural):
    if not filtro_natural or not filtro_natural.strip():
        return None
    prompt_filtro = f"""
    Convierte el siguiente filtro descrito en lenguaje natural a una consulta de pandas ('query').
    El DataFrame tiene estas columnas y tipos de datos:
    {df.dtypes.to_string()}

    Descripción del filtro: {filtro_natural}

    Proporciona únicamente la expresión de filtrado que `pandas.query()` entiende. Usa los nombres EXACTOS de las columnas.
    Maneja strings con comillas (ej., Sexo == 'Mujer'). Para fechas, asume que la columna ya es datetime y compara con strings de fecha como 'YYYY-MM-DD' (ej., `Hora_de_inicio >= '2023-01-15'`).

    Expresión pandas.query():
    """
    filtro_pandas = enviar_prompt(prompt_filtro)
    # Limpiar la respuesta de Gemini
    if "Error" in filtro_pandas:
        st.error(f"Error al generar filtro pandas: {filtro_pandas}")
        return None
    filtro_limpio = filtro_pandas.split('pandas.query():')[-1].strip()
    # Quitar comillas triples o backticks si Gemini los añade
    filtro_limpio = re.sub(r'^[`"\']+|[`"\']+$', '', filtro_limpio)
    # Validar sintaxis básica (muy simple)
    if not filtro_limpio or filtro_limpio.lower() == 'none':
        st.warning("Gemini no pudo generar un filtro válido.")
        return None
    return filtro_limpio

# --- Función get_label_map (NUEVA) ---
def get_label_map(variable_name):
    """Busca el mapeo de número a etiqueta para una variable."""
    variable_name = variable_name.strip()
    if variable_name in label_maps:
         return label_maps[variable_name]
    # Fallback: buscar en data_dictionary por si no se creó en label_maps
    for dim_cat, dim_content in data_dictionary.items():
        if "Preguntas" in dim_content:
             if variable_name in dim_content["Preguntas"]:
                  escala = dim_content.get("Escala")
                  if isinstance(escala, dict):
                       # Asegurar que las claves son números y valores son strings
                       return {k: str(v) for k, v in escala.items() if isinstance(k, (int, float))}
    return None # No se encontró mapa


# --- Función realizar_analisis (AJUSTADA para usar labels) ---
def realizar_analisis(opcion, pregunta_usuario, filtros=None, df_base=None):
    """
    Realiza el análisis y genera gráficos, usando etiquetas donde sea apropiado.
    """
    resultados = ""
    figuras = []
    df_analisis = df_base.copy() # Trabajar sobre una copia

    # Aplicar filtros si existen
    if filtros:
        try:
            df_analisis = df_analisis.query(filtros)
            resultados += f"Aplicando filtro: `{filtros}`. Registros restantes: {len(df_analisis)}\n\n"
            if df_analisis.empty:
                 resultados += "**Advertencia:** El filtro resultó en 0 registros. No se puede continuar el análisis.\n"
                 return resultados, figuras
        except Exception as e:
            st.error(f"Error al aplicar el filtro: {e}. Se usará el DataFrame sin filtrar.")
            resultados += f"**Error al aplicar filtro:** {e}. Se continúa sin filtrar.\n\n"
            df_analisis = df_base.copy() # Revertir al df base
    else:
        resultados += f"Análisis sobre {len(df_analisis)} registros (sin filtros adicionales).\n\n"

    # ===========================================================
    # Opción 1: Distribución de variable categórica (CON LABELS)
    # ===========================================================
    if opcion == '1':
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'categórica', df_analisis)
        if not variables_relevantes:
            resultados += "No se encontraron variables categóricas relevantes.\n"
            return resultados, figuras

        var_cat = variables_relevantes[0]
        otras_vars = variables_relevantes[1:]
        if otras_vars: st.write(f"**Otras variables categóricas relevantes:** {otras_vars}")
        resultados += f"**Análisis de Distribución para:** {var_cat}\n"

        # Obtener el mapa de etiquetas si existe
        labels = get_label_map(var_cat)
        #st.write(f"DEBUG Op1: Labels para '{var_cat}': {labels}")

        # Calcular frecuencias
        conteo = df_analisis[var_cat].value_counts(dropna=False).sort_index()

        # Si hay mapa de labels y la variable es numérica (int), usar los labels
        if labels and pd.api.types.is_numeric_dtype(conteo.index):
            try:
                # Intentar mapear el índice numérico a las etiquetas
                conteo.index = conteo.index.map(labels).fillna(conteo.index.astype(str) + " (Sin Label)")
                plot_title = f'Distribución de {var_cat}'
                plot_xlabel = var_cat # El nombre de la columna
                plot_ylabel = 'Frecuencia'
            except Exception as e:
                st.warning(f"Error al aplicar labels a '{var_cat}': {e}. Se usarán los valores numéricos.")
                # Mantener conteo original si falla el mapeo
                conteo = df_analisis[var_cat].value_counts(dropna=False).sort_index()
                plot_title = f'Distribución de {var_cat} (Valores Numéricos)'
                plot_xlabel = f'{var_cat} (Valor Numérico)'
                plot_ylabel = 'Frecuencia'
        elif pd.api.types.is_categorical_dtype(df_analisis[var_cat]):
             # Si ya es categórica, usar sus categorías
             conteo.index = conteo.index.astype(str) # Asegurar que sean strings para plot
             plot_title = f'Distribución de {var_cat}'
             plot_xlabel = var_cat
             plot_ylabel = 'Frecuencia'
        else:
            # Si es object u otro tipo sin labels claros
            conteo.index = conteo.index.astype(str)
            plot_title = f'Distribución de {var_cat}'
            plot_xlabel = var_cat
            plot_ylabel = 'Frecuencia'


        resultados += f"Frecuencias:\n{conteo.to_string()}\n"

        # Gráficos
        if not conteo.empty:
            try:
                n_cats = len(conteo)
                fig_w = max(6, n_cats * 0.5) # Ajustar ancho si hay muchas categorías
                fig, axes = plt.subplots(1, 3, figsize=(min(15, fig_w*2), 5)) # Ancho dinámico

                # 1. Barras verticales
                conteo.plot(kind='bar', ax=axes[0], colormap='viridis')
                axes[0].set_title(plot_title)
                axes[0].set_xlabel(plot_xlabel)
                axes[0].set_ylabel(plot_ylabel)
                axes[0].tick_params(axis='x', rotation=45, ha='right', labelsize=8)

                # 2. Pastel (solo si no hay demasiadas categorías)
                if n_cats <= 10:
                    conteo.plot(kind='pie', autopct='%1.1f%%', ax=axes[1], startangle=90, colormap='viridis')
                    axes[1].set_ylabel('')
                    axes[1].set_title(plot_title)
                else:
                    axes[1].text(0.5, 0.5, 'Demasiadas categorías\npara gráfico de pastel', ha='center', va='center')
                    axes[1].set_axis_off()

                # 3. Barras horizontales
                conteo.plot(kind='barh', ax=axes[2], colormap='viridis')
                axes[2].set_title(plot_title)
                axes[2].set_xlabel(plot_ylabel) # Ejes invertidos
                axes[2].set_ylabel(plot_xlabel)
                axes[2].tick_params(axis='y', labelsize=8)


                plt.tight_layout()
                st.pyplot(fig)
                figuras.append(fig)
            except Exception as e:
                st.error(f"Error al generar gráficos para {var_cat}: {e}")
        else:
             resultados += "No hay datos para graficar.\n"

    # ===========================================================
    # Opción 2: Estadísticas descriptivas de variable numérica
    # ===========================================================
    elif opcion == '2':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if not vars_relevantes:
            resultados += "No se encontraron variables numéricas relevantes.\n"
            return resultados, figuras

        var_num = vars_relevantes[0]
        otras_vars = vars_relevantes[1:]
        if otras_vars: st.write(f"**Otras variables numéricas relevantes:** {otras_vars}")
        resultados += f"**Análisis Descriptivo para:** {var_num}\n"

        # Calcular estadísticas
        estadisticas = df_analisis[var_num].describe()
        resultados += f"Estadísticas descriptivas:\n{estadisticas.to_string()}\n"

        # Gráficos
        if df_analisis[var_num].notna().any():
             try:
                 fig, axes = plt.subplots(1, 3, figsize=(15, 4))

                 # Histograma
                 sns.histplot(df_analisis[var_num], kde=False, ax=axes[0], bins=15)
                 axes[0].set_title(f'Histograma de {var_num}')
                 axes[0].set_xlabel(var_num)
                 axes[0].set_ylabel('Frecuencia')

                 # Boxplot
                 sns.boxplot(x=df_analisis[var_num], ax=axes[1])
                 axes[1].set_title(f'Boxplot de {var_num}')
                 axes[1].set_xlabel(var_num)

                 # Gráfico de densidad (KDE)
                 sns.kdeplot(df_analisis[var_num], fill=True, ax=axes[2])
                 axes[2].set_title(f'Densidad de {var_num}')
                 axes[2].set_xlabel(var_num)
                 axes[2].set_ylabel('Densidad')

                 plt.tight_layout()
                 st.pyplot(fig)
                 figuras.append(fig)
             except Exception as e:
                 st.error(f"Error al generar gráficos descriptivos para {var_num}: {e}")
        else:
             resultados += "No hay datos numéricos para graficar.\n"

    # ===========================================================
    # Opción 3: Relación entre dos variables numéricas
    # ===========================================================
    elif opcion == '3':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables numéricas relevantes.\n"
            return resultados, figuras

        var_x = vars_relevantes[0]
        var_y = vars_relevantes[1]
        otras_vars = vars_relevantes[2:]
        if otras_vars: st.write(f"**Otras variables numéricas relevantes:** {otras_vars}")
        resultados += f"**Análisis de Relación entre:** {var_x} y {var_y}\n"

        df_rel = df_analisis[[var_x, var_y]].dropna() # Quitar NaNs para correlación y gráficos

        if len(df_rel) > 1: # Necesitamos al menos 2 puntos
             # Correlación
             try:
                 correlacion = df_rel[var_x].corr(df_rel[var_y])
                 resultados += f"Coeficiente de correlación de Pearson: {correlacion:.3f}\n"
             except Exception as e:
                 resultados += f"No se pudo calcular la correlación: {e}\n"

             # Gráficos
             try:
                 fig = sns.jointplot(data=df_rel, x=var_x, y=var_y, kind='scatter', height=5)
                 fig.fig.suptitle(f'Relación entre {var_x} y {var_y}', y=1.02)
                 # Añadir línea de regresión opcionalmente
                 # sns.regplot(data=df_rel, x=var_x, y=var_y, scatter=False, ax=fig.ax_joint, color='red')
                 st.pyplot(fig)
                 figuras.append(fig.fig) # Guardar la figura subyacente

                 # Gráficos adicionales (hexbin, kde) podrían ser opcionales o en subplots separados
                 # fig_hex = sns.jointplot(data=df_rel, x=var_x, y=var_y, kind='hex', height=5)
                 # st.pyplot(fig_hex)
                 # figuras.append(fig_hex.fig)

             except Exception as e:
                 st.error(f"Error al generar gráficos de relación para {var_x} vs {var_y}: {e}")
        else:
            resultados += "No hay suficientes datos (después de quitar NaNs) para analizar la relación.\n"

    # ===========================================================
    # Opción 4: Filtrar datos y mostrar estadísticas (numérica)
    # ===========================================================
    elif opcion == '4':
        # Los filtros ya se aplicaron al inicio en df_analisis
        resultados += f"**Estadísticas Descriptivas (Datos Filtrados)**\n"

        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if not vars_relevantes:
            resultados += "No se encontraron variables numéricas relevantes en los datos filtrados.\n"
            return resultados, figuras

        var_num4 = vars_relevantes[0]
        otras_vars = vars_relevantes[1:]
        if otras_vars: st.write(f"**Otras variables numéricas relevantes:** {otras_vars}")
        resultados += f"**Variable analizada:** {var_num4}\n"

        # Estadísticas
        estadisticas = df_analisis[var_num4].describe()
        resultados += f"Estadísticas descriptivas (filtrado):\n{estadisticas.to_string()}\n"

        # Gráficos (similar a opción 2 pero con datos filtrados)
        if df_analisis[var_num4].notna().any():
            try:
                fig, axes = plt.subplots(1, 3, figsize=(15, 4))
                # Hist, Box, KDE (igual que opción 2, pero con df_analisis)
                sns.histplot(df_analisis[var_num4], kde=False, ax=axes[0], bins=15)
                axes[0].set_title(f'Histograma de {var_num4} (Filt.)')
                sns.boxplot(x=df_analisis[var_num4], ax=axes[1])
                axes[1].set_title(f'Boxplot de {var_num4} (Filt.)')
                sns.kdeplot(df_analisis[var_num4], fill=True, ax=axes[2])
                axes[2].set_title(f'Densidad de {var_num4} (Filt.)')
                plt.tight_layout()
                st.pyplot(fig)
                figuras.append(fig)
            except Exception as e:
                st.error(f"Error al generar gráficos descriptivos (filtrados) para {var_num4}: {e}")
        else:
            resultados += "No hay datos numéricos para graficar después del filtro.\n"

    # ===========================================================
    # Opción 5: Correlación entre múltiples variables numéricas
    # ===========================================================
    elif opcion == '5':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables numéricas relevantes para la correlación.\n"
            return resultados, figuras

        resultados += f"**Análisis de Correlación Múltiple**\n"
        st.write(f"**Variables numéricas consideradas:** {vars_relevantes}")

        df_corr = df_analisis[vars_relevantes].dropna() # Quitar filas con NaN en CUALQUIERA de las vars

        if len(df_corr) > 1 and len(df_corr.columns) >= 2:
            correlacion = df_corr.corr()
            resultados += "Matriz de correlación:\n"
            resultados += correlacion.to_string() + "\n\n"

            # Gráficos
            try:
                # Heatmap
                fig_h, ax_h = plt.subplots(figsize=(max(6, len(vars_relevantes)*0.8), max(5, len(vars_relevantes)*0.7)))
                sns.heatmap(correlacion, annot=True, fmt='.2f', cmap='coolwarm', ax=ax_h, annot_kws={"size": 8})
                ax_h.set_title('Mapa de Calor de Correlación')
                plt.xticks(rotation=45, ha='right', fontsize=8)
                plt.yticks(rotation=0, fontsize=8)
                plt.tight_layout()
                st.pyplot(fig_h)
                figuras.append(fig_h)

                # Pairplot (opcional, puede ser pesado si hay muchas variables)
                if len(vars_relevantes) <= 6: # Limitar para no sobrecargar
                    st.write("Generando matriz de dispersión (pairplot)...")
                    try:
                         fig_p = sns.pairplot(df_corr, corner=True)
                         fig_p.fig.suptitle('Matriz de Dispersión', y=1.02)
                         st.pyplot(fig_p)
                         figuras.append(fig_p.fig)
                    except Exception as e_p:
                         st.warning(f"No se pudo generar el pairplot: {e_p}")
                else:
                    st.info("Se omite la matriz de dispersión (pairplot) por haber demasiadas variables.")

            except Exception as e:
                st.error(f"Error al generar gráficos de correlación: {e}")
        else:
            resultados += "No hay suficientes datos/variables (después de quitar NaNs) para calcular la matriz de correlación.\n"

    # ===========================================================
    # Opción 6: Análisis de regresión simple
    # ===========================================================
    elif opcion == '6':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables numéricas relevantes para la regresión.\n"
            return resultados, figuras

        var_x = vars_relevantes[0] # Independiente
        var_y = vars_relevantes[1] # Dependiente
        otras_vars = vars_relevantes[2:]
        if otras_vars: st.write(f"**Otras variables numéricas relevantes:** {otras_vars}")
        resultados += f"**Análisis de Regresión Lineal Simple**\n"
        resultados += f"Variable Independiente (X): {var_x}\n"
        resultados += f"Variable Dependiente (Y): {var_y}\n"

        df_reg = df_analisis[[var_x, var_y]].dropna()

        if len(df_reg) > 1:
            from sklearn.linear_model import LinearRegression
            X = df_reg[[var_x]]
            y = df_reg[var_y]

            try:
                modelo = LinearRegression()
                modelo.fit(X, y)
                r_sq = modelo.score(X, y)
                intercepto = modelo.intercept_
                pendiente = modelo.coef_[0]

                resultados += f"\n**Resultados del Modelo:**\n"
                resultados += f"- Coeficiente de determinación (R²): {r_sq:.4f}\n"
                resultados += f"- Intercepto (β₀): {intercepto:.4f}\n"
                resultados += f"- Coeficiente (Pendiente β₁): {pendiente:.4f}\n"
                resultados += f"- Ecuación: {var_y} ≈ {pendiente:.4f} * {var_x} + {intercepto:.4f}\n"

                # Gráficos
                fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

                # 1) Scatter con línea de regresión
                sns.regplot(x=var_x, y=var_y, data=df_reg, ax=axes[0], line_kws={"color": "red"})
                axes[0].set_title(f'Regresión: {var_y} vs {var_x}')

                # 2) Gráfico de residuales vs predichos
                predichos = modelo.predict(X)
                residuales = y - predichos
                sns.scatterplot(x=predichos, y=residuales, ax=axes[1])
                axes[1].axhline(0, color='red', linestyle='--')
                axes[1].set_title('Residuales vs. Valores Predichos')
                axes[1].set_xlabel('Valores Predichos')
                axes[1].set_ylabel('Residuales')

                # 3) Histograma de residuales
                sns.histplot(residuales, kde=True, ax=axes[2])
                axes[2].set_title('Distribución de Residuales')
                axes[2].set_xlabel('Residuales')

                plt.tight_layout()
                st.pyplot(fig)
                figuras.append(fig)

            except Exception as e:
                st.error(f"Error durante el análisis de regresión: {e}")
                resultados += f"\nError durante el análisis: {e}\n"
        else:
            resultados += "\nNo hay suficientes datos (después de quitar NaNs) para realizar la regresión.\n"

    # ===========================================================
    # Opción 7: Tablas de Contingencia y Chi-cuadrado (CON LABELS)
    # ===========================================================
    elif opcion == '7':
        resultados += "**Análisis de Asociación (Tabla de Contingencia y Chi²)**\n"
        # Obtener variables relevantes (pueden ser cat o num)
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'todas', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables relevantes.\n"
            return resultados, figuras

        var1 = vars_relevantes[0]
        var2 = vars_relevantes[1]
        otras_vars = vars_relevantes[2:]
        if otras_vars: st.write(f"**Otras variables relevantes:** {otras_vars}")
        resultados += f"Variables analizadas: **{var1}** y **{var2}**\n"

        # Preparar las series (manejar NaNs, agrupar numéricas si es necesario)
        serie1 = df_analisis[var1].copy()
        serie2 = df_analisis[var2].copy()

        # Función auxiliar para agrupar numéricas
        def agrupar_numerica(s, n_bins=5):
            if pd.api.types.is_numeric_dtype(s) and s.nunique() > n_bins * 1.5: # Agrupar si es num y tiene > ~7 únicos
                 try:
                     # Crear etiquetas para los bins
                     bins = pd.cut(s, bins=n_bins, retbins=True)[1]
                     labels = [f'{bins[i]:.1f}-{bins[i+1]:.1f}' for i in range(n_bins)]
                     return pd.cut(s, bins=n_bins, labels=labels, include_lowest=True)
                 except Exception as e:
                     st.warning(f"No se pudo agrupar la variable numérica '{s.name}': {e}. Se usarán valores directos si son pocos.")
                     return s # Devolver original si falla el binning
            return s # Devolver original si no es numérica o tiene pocos únicos

        serie1_proc = agrupar_numerica(serie1)
        serie2_proc = agrupar_numerica(serie2)

        # Obtener mapas de etiquetas
        labels1 = get_label_map(var1)
        labels2 = get_label_map(var2)

        # Crear tabla de contingencia
        try:
            df_crosstab = pd.DataFrame({'v1': serie1_proc, 'v2': serie2_proc}).dropna()
            if df_crosstab.empty:
                 resultados += "No hay datos comunes (después de quitar NaNs) para crear la tabla.\n"
                 return resultados, figuras

            crosstab = pd.crosstab(df_crosstab['v1'], df_crosstab['v2'])

            # Intentar aplicar labels a los índices/columnas si existen
            index_name = var1
            columns_name = var2
            if labels1 and pd.api.types.is_numeric_dtype(crosstab.index):
                 crosstab.index = crosstab.index.map(labels1).fillna(crosstab.index.astype(str) + " (Sin Label)")
                 index_name = f"{var1} (Etiquetas)"
            elif isinstance(crosstab.index, pd.CategoricalIndex): # Si era category
                 crosstab.index = crosstab.index.astype(str)

            if labels2 and pd.api.types.is_numeric_dtype(crosstab.columns):
                 crosstab.columns = crosstab.columns.map(labels2).fillna(crosstab.columns.astype(str) + " (Sin Label)")
                 columns_name = f"{var2} (Etiquetas)"
            elif isinstance(crosstab.columns, pd.CategoricalIndex):
                 crosstab.columns = crosstab.columns.astype(str)

            crosstab.index.name = index_name
            crosstab.columns.name = columns_name


            resultados += f"\n**Tabla de Contingencia:**\n{crosstab.to_string()}\n"

            # Test Chi-cuadrado
            if crosstab.size > 1 and crosstab.shape[0] > 1 and crosstab.shape[1] > 1:
                try:
                    chi2_stat, p_val, dof, expected = chi2_contingency(crosstab)
                    resultados += f"\n**Prueba Chi-cuadrado:**\n"
                    resultados += f"- Estadístico Chi²: {chi2_stat:.3f}\n"
                    resultados += f"- Valor p: {p_val:.4f}\n"
                    resultados += f"- Grados de libertad: {dof}\n"
                    alpha = 0.05
                    if p_val < alpha:
                        resultados += f"- Conclusión: Se rechaza la hipótesis nula (p < {alpha}). Existe una asociación estadísticamente significativa entre las variables.\n"
                    else:
                        resultados += f"- Conclusión: No se rechaza la hipótesis nula (p >= {alpha}). No hay evidencia suficiente de una asociación estadísticamente significativa.\n"
                    # Opcional: Mostrar tabla de esperados si no es muy grande
                    if expected.size <= 25:
                         df_expected = pd.DataFrame(expected, index=crosstab.index, columns=crosstab.columns)
                         resultados += f"\nFrecuencias Esperadas:\n{df_expected.round(2).to_string()}\n"

                except ValueError as ve:
                     resultados += f"\nNo se pudo realizar Chi² (puede haber ceros en esperados): {ve}\n"
                except Exception as e_chi:
                     resultados += f"\nError en prueba Chi²: {e_chi}\n"
            else:
                resultados += "\nNo se puede realizar Chi² (tabla demasiado pequeña).\n"

            # Gráfico Heatmap
            try:
                 fig_ct, ax_ct = plt.subplots(figsize=(max(6, crosstab.shape[1]*0.7), max(4, crosstab.shape[0]*0.5)))
                 sns.heatmap(crosstab, annot=True, fmt='d', cmap='Blues', ax=ax_ct, annot_kws={"size": 8})
                 ax_ct.set_title(f'Tabla de Contingencia: {index_name} vs {columns_name}', fontsize=10)
                 plt.xticks(rotation=45, ha='right', fontsize=8)
                 plt.yticks(rotation=0, fontsize=8)
                 plt.tight_layout()
                 st.pyplot(fig_ct)
                 figuras.append(fig_ct)
            except Exception as e_plot:
                 st.error(f"Error al graficar tabla de contingencia: {e_plot}")

        except Exception as e_cross:
            st.error(f"Error al crear la tabla de contingencia: {e_cross}")
            resultados += f"\nError al crear la tabla: {e_cross}\n"

    else:
        resultados += f"Opción de análisis '{opcion}' no implementada.\n"

    return resultados, figuras


# --- Función mostrar_resumen_base_datos (sin cambios, pero verificar nombres) ---
def mostrar_resumen_base_datos():
    # (El texto del resumen se mantiene igual, pero asegúrate de que los nombres
    # de variables mencionados coincidan con el data_dictionary actualizado y el CSV)
    resumen = """
Esta aplicación está diseñada para ayudarte a explorar y analizar datos relacionados con el bienestar laboral y la salud mental en el entorno de trabajo. Utiliza una base de datos rica en información sociodemográfica, laboral y en diversas dimensiones de bienestar y salud mental para proporcionarte análisis personalizados y valiosos insights.

**¿Cómo utilizar la aplicación?**
1.  **Filtra por Fecha y Empresa (Opcional):** Selecciona el rango de fechas y, si lo deseas, ingresa el ID de la empresa para enfocar el análisis.
2.  **Genera un Informe General:** Haz clic en "Generar Informe General" para obtener una visión global del bienestar en el periodo/empresa seleccionada, incluyendo un semáforo de dimensiones y comparaciones por grupos demográficos.
3.  **O Realiza un Análisis Específico:**
    *   Formula tu pregunta de investigación en el campo "Pregunta". *(Ej: "¿Cómo afecta el número de horas de trabajo semanal al nivel de estrés?")*
    *   Aplica filtros adicionales si es necesario en "Filtros". *(Ej: "empleados con más de 5 años de experiencia")*
    *   Haz clic en "Realizar Análisis". La IA interpretará tu pregunta, seleccionará el método adecuado y te mostrará los resultados y gráficos.
4.  **Explora y Descarga:** Visualiza los resultados y descarga el informe completo en PDF.

**Resumen de la Base de Datos (Basado en `cleaned_data.csv`):**

La base de datos contiene información sobre salud psicológica en el trabajo. Los datos han sido pre-procesados, y las escalas Likert se encuentran mayormente como valores numéricos (enteros).

**Principales categorías y variables:**

1.  **Variables Sociodemográficas:**
    *   **Edad** (Numérica Continua)
    *   **Sexo** (Categórica: Hombre, Mujer, Otro, etc.)
    *   **Estado Civil** (Categórica: Soltero, Casado, etc.)
    *   **Numero de hijos** (Numérica Continua)
    *   **Nivel Educativo** (Categórica: Bachiller, Técnico, etc.)
    *   **Departamento**, **Ciudad /Municipio** (Categóricas)
    *   **Zona de vivienda** (Categórica: Urbana, Rural)
    *   **Estrato socioeconomico** (Categórica/Numérica: 1-6)

2.  **Variables Laborales:**
    *   **Sector Económico**, **Sector empresa** (Categóricas)
    *   **Tamaño Empresa** (Categórica: <10, 10-50, etc.)
    *   **Trabajo por turnos** (Categórica: Sí, No)
    *   **Tipo de Contrato** (Categórica: Indefinido, Fijo, etc.)
    *   **Número de horas de trabajo semanal** (Numérica Continua)
    *   **Ingreso salarial mensual** (Categórica: <1 SMLV, 1-3 SMLV, etc.)
    *   **Cargo** (Categórica: Operativo, Admin., etc.)
    *   **Personas a cargo en la empresa** (Categórica: Sí, No)
    *   **Años de experiencia laboral** (Categórica: <1, 1-5, etc.)
    *   **Antigüedad en el cargo/labor actual** (Categórica: <1, 1-3, etc.)
    *   **Tipo de modalidad de trabajo** (Categórica: Presencial, Híbrido, etc.)
    *   **Tiempo promedio de traslado al trabajo/casa al día** (Categórica: <1h, 1-2h, etc.)
    *   **Horas de formación recibidas (ultimo año)** (Numérica Continua)

3.  **Dimensiones de Bienestar y Salud Mental (Mayormente Numéricas 1-7, 1-5, 1-6):**
    *   **Control del Tiempo**: Percepción sobre autonomía y presión temporal.
    *   **Compromiso del Líder**: Apoyo, valoración y reconocimiento del líder.
    *   **Apoyo del Grupo**: Ayuda y escucha de compañeros.
    *   **Claridad de Rol**: Claridad en expectativas y responsabilidades.
    *   **Cambio Organizacional**: Consulta e información sobre cambios.
    *   **Responsabilidad Organizacional**: Prioridad y recursos para salud mental.
    *   **Conflicto Familia-Trabajo**: Interferencia bidireccional entre trabajo y familia.
    *   **Síntomas de Burnout**: Agotamiento, cinismo, ineficacia (Escala 1-5).
    *   **Compromiso**: Contribución, entusiasmo, ganas de ir a trabajar (Escala 1-6).
    *   **Defensa de la Organización**: Orgullo, recomendación, defensa (Escala 1-6).
    *   **Satisfacción**: Significado, gusto por tareas, satisfacción salarial (Escala 1-6).
    *   **Intención de Retiro**: Planes de permanencia o búsqueda activa (Escala 1-6, algunos ítems invertidos).
    *   **Bienestar Psicosocial (Afectos, Competencias, Expectativas)**: Diferenciales semánticos y escalas sobre percepción actual y futura (Escalas 1-7).
    *   **Factores de Efectos Colaterales (Somatización, Desgaste, Alienación)**: Frecuencia de síntomas físicos y psicológicos negativos (Escalas 1-7).

**Ejemplos de preguntas:**

*   ¿Cuál es la distribución de la **Satisfacción** (numérica) entre diferentes **Cargos** (categórica)? (Opción 1 o 4)
*   ¿Existe correlación entre **Edad** y **Síntomas de Burnout** (ambas numéricas)? (Opción 3 o 5)
*   ¿Cómo afecta el **Tipo de modalidad de trabajo** (categórica) a la percepción de **Control del Tiempo** (numérica)? (Opción 7 o análisis de medias por grupo)

Por favor, realiza tu pregunta teniendo en cuenta las variables y dimensiones disponibles.
    """
    st.markdown(resumen)


######################################################
# CLASE PDFReport y funciones de limpieza (SIN CAMBIOS SIGNIFICATIVOS)
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
            topMargin=50*mm, # Margen superior más grande para el header
            bottomMargin=20*mm # Margen inferior para el footer
        )
        # Estilos personalizados
        self.styles.add(ParagraphStyle(name='CustomTitle', fontName='Helvetica-Bold', fontSize=16, spaceAfter=14, alignment=1)) # Centrado
        self.styles.add(ParagraphStyle(name='CustomHeading', fontName='Helvetica-Bold', fontSize=12, spaceBefore=12, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='CustomBodyText', fontName='Helvetica', fontSize=10, leading=12, alignment=4, spaceAfter=6)) # Justificado
        self.styles.add(ParagraphStyle(name='CustomCode', fontName='Courier', fontSize=9, leading=11, leftIndent=10, spaceAfter=6, backColor=colors.whitesmoke, borderPadding=2))
        self.styles.add(ParagraphStyle(name='CustomFooter', fontName='Helvetica', fontSize=8, textColor=colors.grey))

    def header(self, canvas, doc):
        canvas.saveState()
        try:
            # Intenta cargar la imagen del logo/header
            header_image = 'Captura de pantalla 2024-11-25 a la(s) 9.02.19 a.m..png' # Asegúrate que este archivo exista
            if os.path.isfile(header_image):
                # Dibuja la imagen ajustándola al ancho y altura definidos
                 img_width, img_height = 210*mm, 40*mm # Ancho A4, altura deseada
                 canvas.drawImage(header_image, 0, A4[1] - img_height, width=img_width, height=img_height, preserveAspectRatio=True, anchor='n')
            else:
                 # Fallback si no hay imagen: texto
                 canvas.setFont('Helvetica-Bold', 14)
                 canvas.drawCentredString(A4[0]/2.0, A4[1] - 25*mm, clean_text("Informe de Análisis de Datos"))
        except Exception as e:
            print(f"Error al dibujar header: {e}") # Imprimir error en consola
            # Fallback si hay error con la imagen
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(A4[0]/2.0, A4[1] - 25*mm, clean_text("Informe de Análisis de Datos"))

        # Línea debajo del header
        canvas.setStrokeColor(colors.grey)
        canvas.line(15*mm, A4[1] - 45*mm, A4[0] - 15*mm, A4[1] - 45*mm)
        canvas.restoreState()

    def footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        footer_text = f"Informe generado el {datetime.now().strftime('%Y-%m-%d %H:%M')} | Página {doc.page}"
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 15*mm, 10*mm, footer_text)
        # Texto de advertencia opcional a la izquierda
        warning_text = "Generado con IA. Verificar información crítica."
        canvas.drawString(15*mm, 10*mm, warning_text)
        canvas.restoreState()

    def header_footer(self, canvas, doc):
        self.header(canvas, doc)
        self.footer(canvas, doc)

    def add_paragraph(self, text, style='CustomBodyText'):
        """Añade texto simple usando un estilo."""
        text = clean_text(text) # Limpiar siempre
        p = Paragraph(text, self.styles[style])
        self.elements.append(p)
        self.elements.append(Spacer(1, 4)) # Pequeño espacio después

    def add_title(self, text, level=1):
         """Añade títulos H1, H2, etc."""
         text = clean_text(text)
         if level == 1:
             style = 'CustomTitle'
         else:
             style = 'CustomHeading' # Usar Heading para H2 en adelante
         p = Paragraph(text, self.styles[style])
         self.elements.append(p)
         self.elements.append(Spacer(1, 6))

    def add_markdown(self, md_text):
        """Convierte Markdown básico a elementos ReportLab."""
        md_text = clean_text(md_text)
        html = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
        soup = BeautifulSoup(html, 'html.parser')

        for element in soup.find_all(True): # Iterar sobre todos los elementos
            style = 'CustomBodyText'
            prefix = ""
            if element.name == 'h1':
                style = 'CustomTitle'
            elif element.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                style = 'CustomHeading'
            elif element.name == 'p':
                style = 'CustomBodyText'
            elif element.name == 'li':
                style = 'CustomBodyText'
                # Detectar nivel de lista para indentación (simple)
                if element.find_parent('ul') or element.find_parent('ol'):
                     # Simple bullet point
                     prefix = "• " # O usar números si es <ol>
                     # Podría mejorarse para manejar anidación
            elif element.name == 'code':
                 # Si es bloque de código (usualmente dentro de <pre>)
                 if element.parent.name == 'pre':
                     style = 'CustomCode'
                 else: # Código inline
                     # ReportLab no maneja bien code inline fácilmente, lo tratamos como texto normal
                     pass # Se procesará como parte del párrafo padre
            elif element.name == 'pre':
                 # El contenido ya se manejó en 'code', solo añadir spacer
                 self.elements.append(Spacer(1, 4))
                 continue # Evitar procesar el <pre> vacío
            elif element.name in ['ul', 'ol', 'br', 'hr', 'table', 'thead', 'tbody', 'tr', 'td', 'th']:
                 # Estos elementos se manejan por su contenido (li, p) o se ignoran/requieren manejo especial
                 if element.name == 'br':
                      self.elements.append(Spacer(1, 6))
                 # Tablas requerirían un manejo mucho más complejo con reportlab.platypus.Table
                 continue
            else:
                 # Otros elementos (strong, em, a, etc.) se intentan renderizar dentro del párrafo
                 pass # Se procesarán como parte del párrafo padre

            # Extraer solo el texto directo del elemento (evita duplicar hijos)
            text = ''.join(element.find_all(string=True, recursive=False)).strip()
            if text:
                 # Aplicar formato inline básico (negrita/cursiva) si es posible
                 formatted_text = prefix + self._apply_inline_formatting(element)
                 p = Paragraph(formatted_text, self.styles[style])
                 self.elements.append(p)
                 # Añadir un pequeño espacio, excepto después de títulos
                 if style not in ['CustomTitle', 'CustomHeading', 'CustomCode']:
                    self.elements.append(Spacer(1, 2))

    def _apply_inline_formatting(self, soup_element):
         """Aplica tags básicos <b>, <i> a texto para ReportLab."""
         content = []
         for item in soup_element.contents:
             if isinstance(item, str):
                 content.append(clean_text(item)) # Limpiar texto normal
             elif item.name == 'strong' or item.name == 'b':
                 content.append(f"<b>{clean_text(item.get_text())}</b>")
             elif item.name == 'em' or item.name == 'i':
                 content.append(f"<i>{clean_text(item.get_text())}</i>")
             elif item.name == 'code': # Código inline
                 # Se puede intentar un formato, pero Courier puede no estar en todos los viewers
                 content.append(f"<font name='Courier'>{clean_text(item.get_text())}</font>")
             elif item.name == 'br':
                  content.append("<br/>")
             else:
                 # Para otros tags anidados, obtener su texto limpio
                 content.append(clean_text(item.get_text()))
         return "".join(content)


    def insert_image(self, image_path_or_fig, max_width_mm=170, max_height_mm=200):
        """
        Inserta una imagen desde un archivo o una figura Matplotlib.
        Ajusta tamaño manteniendo proporción.
        """
        img = None
        temp_file_to_delete = None

        try:
            if isinstance(image_path_or_fig, str) and os.path.isfile(image_path_or_fig):
                img_path = image_path_or_fig
            elif hasattr(image_path_or_fig, 'savefig'): # Es una figura Matplotlib
                img_buffer = io.BytesIO()
                image_path_or_fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                img_buffer.seek(0)
                img_path = img_buffer # Usar el buffer directamente si RL lo soporta bien
                # Alternativa: guardar temporalmente si el buffer da problemas
                # temp_img_path = f"temp_fig_{random.randint(1000, 9999)}.png"
                # image_path_or_fig.savefig(temp_img_path, format='png', dpi=300, bbox_inches='tight')
                # img_path = temp_img_path
                # temp_file_to_delete = temp_img_path
            else:
                 self.add_paragraph(f"Error: Imagen no válida ({type(image_path_or_fig)})", style='CustomCode')
                 return

            # Usar PIL para obtener dimensiones y calcular nuevo tamaño
            with PILImage.open(img_path) as pil_img:
                orig_width_px, orig_height_px = pil_img.size

            if orig_width_px == 0 or orig_height_px == 0:
                raise ValueError("Dimensiones de imagen inválidas (0).")

            # Convertir max_width/height de mm a puntos (1 mm = 2.83465 puntos)
            max_width_pt = max_width_mm * mm
            max_height_pt = max_height_mm * mm

            ratio = float(orig_height_px) / float(orig_width_px)
            new_width_pt = max_width_pt
            new_height_pt = new_width_pt * ratio

            if new_height_pt > max_height_pt:
                new_height_pt = max_height_pt
                new_width_pt = new_height_pt / ratio

            # Crear la imagen ReportLab
            rl_img = RLImage(img_path, width=new_width_pt, height=new_height_pt)
            rl_img.hAlign = 'CENTER' # Centrar la imagen
            self.elements.append(rl_img)
            self.elements.append(Spacer(1, 12)) # Espacio después de la imagen

        except FileNotFoundError:
             self.add_paragraph(f"Error: Archivo de imagen no encontrado: {image_path_or_fig}", style='CustomCode')
        except Exception as e:
             self.add_paragraph(f"Error al insertar imagen: {e}", style='CustomCode')
        finally:
            # Limpiar archivo temporal si se creó
            if temp_file_to_delete and os.path.exists(temp_file_to_delete):
                 os.remove(temp_file_to_delete)
            # Cerrar buffer si se usó (aunque RLImage debería manejarlo)
            if isinstance(img_path, io.BytesIO):
                 img_path.close()


    def build_pdf(self):
        """Construye el PDF."""
        try:
            self.doc.build(self.elements, onFirstPage=self.header_footer, onLaterPages=self.header_footer)
        except LayoutError as e:
            st.error(f"Error de maquetación al generar PDF: {e}")
            # Intentar construir con elementos simplificados para depurar
            try:
                 simple_elements = [Paragraph(clean_text(str(el)), self.styles['CustomBodyText']) for el in self.elements if isinstance(el, (Paragraph, Spacer))]
                 self.doc.build(simple_elements, onFirstPage=self.header_footer, onLaterPages=self.header_footer)
                 st.warning("Se generó un PDF simplificado debido a errores de maquetación.")
            except Exception as e_simple:
                 st.error(f"Incluso la construcción simplificada del PDF falló: {e_simple}")
                 raise e # Relanzar error original si todo falla
        except Exception as e:
             st.error(f"Error inesperado al construir PDF: {e}")
             raise e

# Funciones de limpieza de texto (adaptadas ligeramente)
def break_long_words(text, max_length=80):
    """Intenta romper palabras largas. Menos agresivo."""
    def break_word(match):
        word = match.group(0)
        if len(word) > max_length:
            parts = []
            while len(word) > max_length:
                parts.append(word[:max_length])
                word = word[max_length:]
            parts.append(word)
            # Usar espacio rompible en lugar de guion para evitar problemas con URLs, etc.
            return ' '.join(parts)
        return word
    # Romper secuencias largas de no espacios
    return re.sub(r'\S+', break_word, text)

def clean_text(text):
    """Limpia texto para ReportLab, manejando caracteres comunes."""
    if not isinstance(text, str):
         text = str(text) # Convertir a string si no lo es

    # Reemplazar caracteres especiales HTML/XML comunes
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')

    # Manejar caracteres específicos problemáticos o comunes
    replacements = {
        '\u2013': '-', # En dash
        '\u2014': '--', # Em dash
        '\u2018': "'", # Left single quote
        '\u2019': "'", # Right single quote
        '\u201C': '"', # Left double quote
        '\u201D': '"', # Right double quote
        '\u2022': '* ', # Bullet point
        '\u00A0': ' ', # Non-breaking space
        # Añadir más si es necesario
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    # Intentar codificar/decodificar para eliminar caracteres problemáticos restantes
    try:
        text = text.encode('latin-1', 'ignore').decode('latin-1')
    except Exception:
         # Si falla latin-1, intentar con utf-8 (aunque ReportLab prefiere latin-1)
         try:
             text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
         except Exception as e:
              print(f"Advertencia: No se pudo limpiar completamente el texto: {e}")

    # Romper palabras largas (hacerlo después de reemplazos)
    # text = break_long_words(text) # Desactivado temporalmente, puede ser problemático

    return text

# --- Función informe (generar PDF para análisis específico) ---
def generar_informe(pregunta_usuario, opcion_analisis, resultados_texto, figuras):
    """Genera el informe PDF para un análisis específico."""
    pdf = PDFReport('informe_analisis_datos.pdf') # Nombre fijo para descarga

    # --- Título Principal ---
    pdf.add_title('Informe de Análisis Específico')

    # --- Introducción y Contexto ---
    pdf.add_title('1. Pregunta de Investigación y Metodología', level=2)
    pdf.add_paragraph(f"**Pregunta:** {pregunta_usuario}")
    # Obtener descripción de la opción de análisis
    opcion_desc = f"Opción {opcion_analisis}"
    match = re.search(rf"{opcion_analisis}\.\s*\*\*(.*?)\*\*", opciones_analisis, re.DOTALL)
    if match:
        opcion_desc = f"Opción {opcion_analisis}: {match.group(1).strip()}"
    pdf.add_paragraph(f"**Método de Análisis Seleccionado:** {opcion_desc}")
    # Mencionar filtros si se usaron (extraído de resultados_texto)
    filtro_match = re.search(r"Aplicando filtro: `(.*?)`", resultados_texto)
    if filtro_match:
         pdf.add_paragraph(f"**Filtros Aplicados:** {filtro_match.group(1)}")

    # --- Resultados del Análisis ---
    pdf.add_title('2. Resultados del Análisis', level=2)
    # Mostrar el texto de resultados (puede contener tablas formateadas como texto)
    # Usar add_markdown para intentar formatear texto preformateado o con sintaxis simple
    pdf.add_markdown(f"```\n{resultados_texto}\n```") # Encerrar en backticks para estilo 'code'

    # --- Gráficos ---
    if figuras:
        pdf.add_title('3. Visualizaciones', level=2)
        for idx, fig in enumerate(figuras):
            # Añadir un pequeño título/descripción para cada figura si es posible
            # (Podríamos pasar títulos junto con las figuras desde realizar_analisis)
            pdf.add_paragraph(f"**Gráfico {idx + 1}:** Visualización relacionada con el análisis.", style='CustomHeading')
            pdf.insert_image(fig) # Pasar la figura directamente

    # --- Interpretación y Conclusiones (Generadas por IA) ---
    pdf.add_title('4. Interpretación y Conclusiones', level=2)
    prompt_interpretacion = f"""
    Basado en la pregunta de investigación:
    {pregunta_usuario}

    El método de análisis fue (Opción {opcion_analisis}):
    {opcion_desc}

    Y los resultados obtenidos fueron:
    {resultados_texto}

    Considerando el diccionario de datos para interpretar las variables:
    {data_dictionary}

    Y los mapeos de etiquetas numéricas (ej. 1='Nunca', 7='Siempre'):
    {label_maps}

    Genera una interpretación clara de los resultados y las visualizaciones (si las hubo). Explica qué significan los hallazgos en el contexto de la pregunta original.
    Finalmente, proporciona 2-3 conclusiones clave y, si es pertinente, 1-2 recomendaciones prácticas basadas en estos hallazgos, desde la perspectiva de la psicología organizacional. Usa formato Markdown.
    Si los resultados indican "No hay datos suficientes" o errores, explica por qué no se pudo completar el análisis y sugiere posibles próximos pasos (ej. revisar filtros, verificar datos).
    """
    interpretacion_ia = enviar_prompt(prompt_interpretacion)
    if "Error" in interpretacion_ia:
        pdf.add_paragraph("No se pudo generar la interpretación automáticamente.")
    else:
        pdf.add_markdown(interpretacion_ia) # Usar add_markdown

    # --- Construir PDF ---
    try:
        pdf.build_pdf()
        st.success(f"Informe específico generado: {pdf.filename}")
        return pdf.filename # Devolver nombre para el botón de descarga
    except Exception as e:
        st.error(f"Error final al generar el PDF específico: {e}")
        return None


# --- Función generar_informe_general (AJUSTADA) ---
def generar_informe_general(df_original, fecha_inicio, fecha_fin):
    """
    Genera un informe general de bienestar basado en el df filtrado por fecha/ID.
    Ahora valida tipos numéricos en lugar de convertir. Usa data_dictionary.
    """
    # 0. Copia y Filtrado Inicial (como en main)
    df_informe = df_original.copy()
    # El filtrado por fecha y ID ya se hizo en main antes de llamar a esta función

    if df_informe.empty:
        st.warning("No hay datos para generar el informe general en el rango/ID seleccionado.")
        return "No hay datos para generar el informe general.", []

    st.write(f"DEBUG - Generando informe general con {df_informe.shape[0]} filas.")

    # 1. Identificar y Validar Columnas Numéricas de Dimensiones
    columnas_numericas_ok = []
    mapa_dim_cols = {} # Diccionario: dim_name -> [lista de cols numéricas válidas]

    st.write("--- Validando columnas numéricas para dimensiones ---")
    for dim_name, dim_details in data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {}).items():
        cols_candidatas = dim_details.get("Preguntas", [])
        cols_validas_para_dim = []
        for col_name in cols_candidatas:
            col_name_clean = col_name.strip() # Nombre limpio
            if col_name_clean in df_informe.columns:
                # VALIDAR si es numérica en el df_informe
                if pd.api.types.is_numeric_dtype(df_informe[col_name_clean]):
                    if df_informe[col_name_clean].notna().any(): # Asegurar que no sean solo NaNs
                        cols_validas_para_dim.append(col_name_clean)
                        if col_name_clean not in columnas_numericas_ok:
                             columnas_numericas_ok.append(col_name_clean)
                             #st.write(f"OK: '{col_name_clean}' es numérico y válido.")
                    else:
                        st.warning(f"INFO [{dim_name}]: Columna '{col_name_clean}' es numérica pero no tiene datos válidos (solo NaNs). Excluida.")
                else:
                    # Esto NO debería pasar si el CSV está bien limpio
                    st.error(f"¡ERROR CRÍTICO! [{dim_name}]: Columna '{col_name_clean}' debería ser numérica pero es {df_informe[col_name_clean].dtype}. ¡Revisar CSV o data_dictionary! Excluida.")
            #else: # No encontrada, ignorar silenciosamente o advertir
            #    st.warning(f"INFO [{dim_name}]: Columna '{col_name_clean}' del diccionario no encontrada en el DataFrame.")

        if cols_validas_para_dim:
            mapa_dim_cols[dim_name] = cols_validas_para_dim
        else:
            st.warning(f"SKIP [{dim_name}]: No se encontraron columnas numéricas válidas para esta dimensión.")

    if not columnas_numericas_ok:
        st.error("Error Fatal: No se encontraron columnas numéricas válidas pertenecientes a las dimensiones de bienestar.")
        return "Error: No hay columnas numéricas válidas para el análisis dimensional.", []

    st.write(f"DEBUG - Total columnas numéricas válidas para dimensiones: {len(columnas_numericas_ok)}")

    # 2. Calcular Promedios por Dimensión (Usando las columnas validadas)
    resultados_promedio = {}
    st.write("--- Calculando Promedios Dimensionales ---")
    for dim_name, cols_validas in mapa_dim_cols.items():
        try:
            # Calcular media de cada columna válida, luego media de esas medias
            # Usar skipna=True para robustez dentro de la dimensión
            promedio_dim = df_informe[cols_validas].mean(axis=0, skipna=True).mean(skipna=True)
            if pd.notna(promedio_dim):
                resultados_promedio[dim_name] = promedio_dim
                # Contar N promedio usado (aproximado)
                n_promedio = df_informe[cols_validas].count().mean()
                st.write(f"OK: Promedio '{dim_name}': {promedio_dim:.2f} (N aprox={n_promedio:.0f})")
            else:
                st.warning(f"SKIP [{dim_name}]: El promedio resultó NaN (posiblemente todas las columnas internas son NaN).")
        except Exception as e:
            st.error(f"ERROR calculando promedio para '{dim_name}': {e}")

    if not resultados_promedio:
        st.error("Error Fatal: No se pudo calcular el promedio para ninguna dimensión.")
        return "Error: No se calcularon promedios dimensionales.", []

    # 3. Clasificar Fortalezas, Riesgos, Intermedios (usando get_scale_range)
    inverse_dims = { # Definir qué dimensiones se interpretan inversamente
        "Conflicto Familia-Trabajo": True, "Síntomas de Burnout": True,
        "Factores de Efectos Colaterales (Escala de Desgaste)": True,
        "Factores de Efectos Colaterales (Escala de Alienación)": True,
        "Intención de Retiro": True, # OJO: Items individuales pueden variar, pero el promedio general sí.
        "Factores de Efectos Colaterales (Escala de Somatización)": True,
        # Columnas de demandas de tiempo en 'Control del Tiempo' también son inversas, pero el promedio es mixto.
        # Las últimas 3 de Claridad de Rol son inversas. Promedio mixto.
    }

    def get_scale_range(dim_name):
        """Obtiene el rango (min, max) de la escala para una dimensión desde data_dictionary."""
        details = data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {}).get(dim_name, {})
        escala = details.get("Escala", {})
        if escala and isinstance(escala, dict):
            valores_num = [k for k in escala.keys() if isinstance(k, (int, float))]
            if valores_num: return min(valores_num), max(valores_num)
        # Fallbacks basados en nombres (ajustar si es necesario)
        if "Burnout" in dim_name: return 1, 5
        if any(sub in dim_name for sub in ["Compromiso", "Defensa", "Satisfacción", "Retiro"]): return 1, 6
        return 1, 7 # Default general

    def estado_dimension(valor, dim_name):
        """Clasifica una dimensión como Fortaleza, Riesgo o Intermedio."""
        if pd.isna(valor): return ('Sin Datos', 'grey')
        min_escala, max_escala = get_scale_range(dim_name)
        rango_total = max_escala - min_escala
        if rango_total <= 0: return ('Rango Inválido', 'grey') # Evitar división por cero

        punto_medio = (min_escala + max_escala) / 2.0
        # Umbrales más flexibles: terciles aproximados del rango efectivo
        umbral_riesgo = min_escala + rango_total / 3.0
        umbral_fortaleza = max_escala - rango_total / 3.0

        es_inversa = inverse_dims.get(dim_name, False)

        # Interpretar el valor (invertir si es necesario)
        valor_interpretar = (max_escala + min_escala) - valor if es_inversa else valor

        if valor_interpretar >= umbral_fortaleza: return ('Fortaleza', 'green')
        elif valor_interpretar <= umbral_riesgo: return ('Riesgo', 'red')
        else: return ('Intermedio', 'yellow')

    fortalezas = []
    riesgos = []
    intermedios = []
    sin_datos = []

    for dim, val in resultados_promedio.items():
         estado, _ = estado_dimension(val, dim)
         if estado == 'Fortaleza': fortalezas.append((dim, val))
         elif estado == 'Riesgo': riesgos.append((dim, val))
         elif estado == 'Intermedio': intermedios.append((dim, val))
         else: sin_datos.append((dim, val)) # Incluye 'Sin Datos' o 'Rango Inválido'

    # Ordenar para presentación
    fortalezas.sort(key=lambda item: item[1], reverse=True)
    riesgos.sort(key=lambda item: item[1]) # Los menores primero
    intermedios.sort(key=lambda item: item[1])

    # 4. Generar Textos con Gemini (Resumen, Conclusiones)
    try:
        prompt_resumen = f"""
        Resultados promedio de las dimensiones de bienestar (escalas varían, típicamente 1-7, 1-5, 1-6):
        Fortalezas (valores altos interpretados positivamente): {fortalezas}
        Riesgos (valores bajos interpretados positivamente, o altos si la dim. es negativa como Burnout): {riesgos}
        Intermedios: {intermedios}
        (Nota: Algunas dimensiones como 'Conflicto Familia-Trabajo' o 'Burnout' se interpretan inversamente, donde un puntaje numérico alto es negativo).

        Genera un resumen ejecutivo conciso (1-2 párrafos) interpretando estos resultados generales para el periodo/empresa analizado. Destaca las áreas más fuertes y las de mayor riesgo potencial.
        """
        resumen_ejecutivo = enviar_prompt(prompt_resumen)
        if "Error" in resumen_ejecutivo: raise Exception(resumen_ejecutivo)

        prompt_conclusiones = f"""
        Análisis detallado de dimensiones de bienestar:
        Fortalezas: {fortalezas}
        Riesgos: {riesgos}
        Intermedios: {intermedios}
        Dimensiones con interpretación inversa (puntaje alto = negativo): {list(inverse_dims.keys())}

        Considerando el significado de cada dimensión (puedes inferirlo del nombre y contexto general de bienestar laboral):
        1. Proporciona conclusiones detalladas (1-2 párrafos) sobre el estado general del bienestar y la salud mental basado en esta clasificación.
        2. Ofrece recomendaciones prácticas y específicas (3-5 puntos clave en formato Markdown) desde la psicología organizacional para:
           a) Abordar los RIESGOS principales identificados.
           b) Potenciar o mantener las FORTALEZAS.
           c) Sugerir enfoques para las áreas INTERMEDIAS.
        """
        conclusiones_recomendaciones = enviar_prompt(prompt_conclusiones)
        if "Error" in conclusiones_recomendaciones: raise Exception(conclusiones_recomendaciones)

    except Exception as e:
        st.error(f"Error al generar textos con Gemini para el informe general: {e}")
        resumen_ejecutivo = "Error al generar resumen."
        conclusiones_recomendaciones = "Error al generar conclusiones y recomendaciones."

    # 5. Generar Gráficos
    figuras_informe = []
    fig_titles = [] # Para el PDF

    # --- Gráfico Semáforo (Radar Chart podría ser una alternativa) ---
    st.write("--- Generando Gráfico Semáforo ---")
    try:
        dims_list = list(resultados_promedio.items())
        n_dims = len(dims_list)
        if n_dims > 0:
            # Ordenar alfabéticamente para consistencia
            dims_list.sort(key=lambda item: item[0])

            cols = 3 # Columnas de semáforos
            rows = math.ceil(n_dims / cols)
            fig_semaforo, axes_semaforo = plt.subplots(rows, cols, figsize=(cols * 3.5, rows * 2.2)) # Más compacto
            if n_dims == 1: axes_semaforo = np.array([[axes_semaforo]]) # Asegurar 2D si hay 1 solo
            elif rows == 1: axes_semaforo = axes_semaforo.reshape(1, -1) # Asegurar 2D si hay 1 fila
            elif cols == 1: axes_semaforo = axes_semaforo.reshape(-1, 1) # Asegurar 2D si hay 1 columna

            axes_flat = axes_semaforo.flatten()

            for idx, (dim, val) in enumerate(dims_list):
                 ax = axes_flat[idx]
                 est, color = estado_dimension(val, dim)
                 ax.set_facecolor(color)
                 texto_promedio = f"{val:.2f}" if pd.notna(val) else "N/A"
                 nota_inversa = "(Inv)" if inverse_dims.get(dim, False) else ""
                 # Acortar nombres largos de dimensiones para el gráfico
                 dim_short = dim.replace("Factores de Efectos Colaterales", "Efectos Col.")
                 dim_short = dim_short.replace("Bienestar Psicosocial", "Bienestar Psic.")
                 dim_short = dim_short.replace("Organizacional", "Org.")
                 dim_short = dim_short.replace("Escala de ", "")

                 text_content = f"{dim_short}\n{est}\nProm: {texto_promedio} {nota_inversa}"
                 ax.text(0.5, 0.5, text_content, ha='center', va='center', fontsize=7, color='black' if color != 'grey' else 'white', wrap=True)
                 ax.set_xticks([])
                 ax.set_yticks([])
                 ax.set_xlim(0, 1)
                 ax.set_ylim(0, 1)
                 ax.spines['top'].set_visible(False)
                 ax.spines['right'].set_visible(False)
                 ax.spines['bottom'].set_visible(False)
                 ax.spines['left'].set_visible(False)

            # Ocultar ejes sobrantes
            for j in range(n_dims, len(axes_flat)):
                 axes_flat[j].set_visible(False)

            fig_semaforo.suptitle("Semáforo de Dimensiones de Bienestar (Promedios)", fontsize=12)
            fig_semaforo.tight_layout(rect=[0, 0.03, 1, 0.95]) # Ajustar para título
            figuras_informe.append(fig_semaforo)
            fig_titles.append("Figura 1: Semáforo de Dimensiones")
            st.pyplot(fig_semaforo)
        else:
            st.warning("No hay dimensiones con promedios para graficar el semáforo.")

    except Exception as e:
        st.error(f"Error generando gráfico Semáforo: {e}")

    # --- Gráficos por Grupo (Sexo, Edad, Hijos) ---
    st.write("--- Generando Gráficos Comparativos por Grupos ---")
    df_plot_groups = df_informe.copy()

    # Preparar columnas de agrupación (asegurar que sean categóricas)
    grupos = {}
    # Sexo
    col_sexo = 'Sexo'
    if col_sexo in df_plot_groups:
        if not pd.api.types.is_categorical_dtype(df_plot_groups[col_sexo]):
             df_plot_groups[col_sexo] = df_plot_groups[col_sexo].astype('category')
        if df_plot_groups[col_sexo].nunique() > 1: # Solo si hay más de una categoría
             grupos['Sexo'] = col_sexo
    # Rango Edad
    col_edad = 'Edad'
    col_rango_edad = 'Rango_Edad'
    if col_edad in df_plot_groups and pd.api.types.is_numeric_dtype(df_plot_groups[col_edad]):
        try:
            max_edad = df_plot_groups[col_edad].max()
            bins_edad = [0, 24, 34, 44, 54, 64, max_edad + 1] if max_edad >=65 else [0, 24, 34, 44, 54, max_edad + 1]
            labels_edad = ['<25', '25-34', '35-44', '45-54', '55-64', '65+'][:len(bins_edad)-1]
            df_plot_groups[col_rango_edad] = pd.cut(df_plot_groups[col_edad], bins=bins_edad, labels=labels_edad, right=False)
            if df_plot_groups[col_rango_edad].nunique() > 1:
                 grupos['Rango Edad'] = col_rango_edad
        except Exception as e_edad:
             st.warning(f"No se pudo crear 'Rango_Edad': {e_edad}")
    # Tiene Hijos
    col_num_hijos = 'Numero de hijos'
    col_tiene_hijos = 'Tiene_Hijos'
    if col_num_hijos in df_plot_groups and pd.api.types.is_numeric_dtype(df_plot_groups[col_num_hijos]):
        df_plot_groups[col_tiene_hijos] = np.where(df_plot_groups[col_num_hijos].fillna(-1) > 0, 'Con hijos', 'Sin hijos')
        df_plot_groups[col_tiene_hijos] = df_plot_groups[col_tiene_hijos].astype('category')
        if df_plot_groups[col_tiene_hijos].nunique() > 1:
             grupos['Tiene Hijos'] = col_tiene_hijos

    # Bucle para graficar cada dimensión por cada grupo
    fig_idx_start = 2 # Empezar numeración de figuras después del semáforo
    for i, (dim_name, prom_general) in enumerate(resultados_promedio.items()):
        if dim_name not in mapa_dim_cols: continue # Saltar si no tenía cols válidas
        cols_validas_dim = mapa_dim_cols[dim_name]
        min_esc, max_esc = get_scale_range(dim_name) # Límites para el eje Y

        if not grupos: # Si no hay variables de grupo válidas
             st.info(f"No hay grupos demográficos (Sexo, Edad, Hijos) con variación suficiente para comparar '{dim_name}'.")
             continue

        n_grupos_validos = len(grupos)
        fig_dim, axs_dim = plt.subplots(1, n_grupos_validos, figsize=(n_grupos_validos * 4.5, 4.0), sharey=True)
        if n_grupos_validos == 1: axs_dim = [axs_dim] # Asegurar que sea iterable
        fig_dim.suptitle(f"Comparación: {dim_name}\n(Promedio General: {prom_general:.2f})", fontsize=10, y=1.03)
        plot_count_dim = 0

        for k, (grupo_label, grupo_col) in enumerate(grupos.items()):
            ax = axs_dim[k]
            try:
                # Calcular promedio de la dimensión (promedio de sus ítems) para cada categoría del grupo
                # Agrupar, calcular media de cada item, luego media de esas medias por grupo
                grouped_means = df_plot_groups.groupby(grupo_col, observed=False)[cols_validas_dim].mean(numeric_only=True).mean(axis=1, skipna=True).dropna()

                if not grouped_means.empty:
                    color_map = plt.get_cmap('viridis')
                    colors = color_map(np.linspace(0, 1, len(grouped_means)))
                    bars = grouped_means.plot(kind='bar', color=colors, ax=ax, width=0.8)
                    ax.set_title(f"Por {grupo_label}", fontsize=9)
                    ax.set_xlabel('')
                    if k == 0: ax.set_ylabel('Promedio Dimensión') # Solo en el primero
                    ax.tick_params(axis='x', rotation=45, ha='right', labelsize=8)
                    ax.grid(axis='y', linestyle='--', alpha=0.6)
                    ax.set_ylim(bottom=min_esc - (max_esc-min_esc)*0.05, top=max_esc + (max_esc-min_esc)*0.05) # Margen eje Y
                    # Añadir valores en las barras
                    for bar in bars.patches:
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                                f'{bar.get_height():.2f}', ha='center', va='bottom', fontsize=7)
                    plot_count_dim += 1
                else:
                    ax.text(0.5, 0.5, 'No hay datos\nsuficientes', ha='center', va='center', fontsize=8, color='grey')
                    ax.set_title(f"Por {grupo_label}", fontsize=9)
                    ax.set_xlabel(''); ax.set_ylabel('')
                    ax.set_xticks([]); ax.set_yticks([])

            except Exception as e_grp:
                st.error(f"Error graficando '{dim_name}' por '{grupo_label}': {e_grp}")
                ax.text(0.5, 0.5, f'Error:\n{e_grp}', ha='center', va='center', fontsize=7, color='red')
                ax.set_title(f"Por {grupo_label}", fontsize=9)
                ax.set_xlabel(''); ax.set_ylabel('')
                ax.set_xticks([]); ax.set_yticks([])

        if plot_count_dim > 0:
            plt.tight_layout(rect=[0, 0.03, 1, 0.90]) # Ajustar para suptitle
            figuras_informe.append(fig_dim)
            fig_titles.append(f"Figura {fig_idx_start + i}: Comparación {dim_name} por Grupos")
            st.pyplot(fig_dim)
        else:
            plt.close(fig_dim) # Cerrar figura si no se pudo plotear nada

    # 6. Ensamblar Texto del Informe Final
    informe_partes = []
    informe_partes.append(f"# Informe General de Bienestar Laboral\n")
    informe_partes.append(f"Periodo Analizado: {fecha_inicio.strftime('%Y-%m-%d')} a {fecha_fin.strftime('%Y-%m-%d')}\n")
    # Añadir ID de empresa si se usó
    id_empresa_filtrado = df_original['ID'].unique() if 'ID' in df_original else []
    if len(id_empresa_filtrado) == 1:
         informe_partes.append(f"Empresa (ID): {id_empresa_filtrado[0]}\n")
    informe_partes.append(f"Número de Respuestas Analizadas: {len(df_informe)}\n")

    informe_partes.append("\n## Resumen Ejecutivo\n")
    informe_partes.append(resumen_ejecutivo + "\n")

    informe_partes.append("\n## Clasificación de Dimensiones (Según Promedio)\n")
    informe_partes.append(f"*(Interpretación basada en umbrales y si la dimensión es directa o inversa `{list(inverse_dims.keys())}`)*\n")
    if fortalezas:
        informe_partes.append("\n**Fortalezas (Áreas Positivas):**\n")
        for f, val in fortalezas: informe_partes.append(f"- {f}: {val:.2f}\n")
    else: informe_partes.append("\n*No se identificaron fortalezas claras.*\n")
    if intermedios:
        informe_partes.append("\n**Intermedios (Áreas Neutras o Mixtas):**\n")
        for i, val in intermedios: informe_partes.append(f"- {i}: {val:.2f}\n")
    else: informe_partes.append("\n*No se identificaron áreas intermedias.*\n")
    if riesgos:
        informe_partes.append("\n**Riesgos (Áreas de Atención Prioritaria):**\n")
        for r, val in riesgos: informe_partes.append(f"- {r}: {val:.2f}\n")
    else: informe_partes.append("\n*No se identificaron riesgos claros.*\n")
    if sin_datos:
         informe_partes.append("\n**Sin Datos Suficientes:**\n")
         for sd, val in sin_datos: informe_partes.append(f"- {sd}: {val}\n")

    informe_partes.append("\n## Conclusiones y Recomendaciones\n")
    informe_partes.append(conclusiones_recomendaciones)

    informe_texto_final = "".join(informe_partes)

    st.success("Informe general procesado.")
    return informe_texto_final, figuras_informe, fig_titles # Devolver también títulos


# --- Función Main (AJUSTADA) ---
def main():
    st.set_page_config(layout="wide") # Usar página ancha
    st.title("Aplicación de Análisis de Datos sobre Salud Organizacional")

    # 0) Mostrar el resumen de la base de datos
    with st.expander("Ver Resumen de la Base de Datos y Ayuda", expanded=False):
        mostrar_resumen_base_datos()

    # 1) Intentar parsear fechas al cargar es más eficiente, hecho al inicio.
    # Verificar si la columna existe y es datetime
    if 'Hora de inicio' not in df.columns or not pd.api.types.is_datetime64_any_dtype(df['Hora de inicio']):
        st.error("Error crítico: La columna 'Hora de inicio' no existe o no es de tipo fecha/hora.")
        st.stop()

    # 2) Widgets para Rango de Fechas y ID Empresa
    min_date = df['Hora de inicio'].min().date() if df['Hora de inicio'].notna().any() else date.today() - timedelta(days=365)
    max_date = df['Hora de inicio'].max().date() if df['Hora de inicio'].notna().any() else date.today()
    default_start = max(min_date, max_date - timedelta(days=360)) # Default último año o desde min_date

    col1, col2, col3 = st.columns(3)
    with col1:
        fecha_inicio = st.date_input("Fecha de inicio", value=default_start, min_value=min_date, max_value=max_date)
    with col2:
        fecha_fin = st.date_input("Fecha de fin", value=max_date, min_value=min_date, max_value=max_date)
    with col3:
        cod_empresa = st.text_input("Código Empresa (ID, opcional)")

    # 3) Filtrar el DataFrame base según fecha y ID
    try:
        # Asegurar que fecha_fin incluya todo el día
        fecha_fin_dt = pd.to_datetime(fecha_fin) + timedelta(days=1) - timedelta(seconds=1)
        df_filtrado_base = df[
            (df['Hora de inicio'] >= pd.to_datetime(fecha_inicio)) &
            (df['Hora de inicio'] <= fecha_fin_dt)
        ]
        if cod_empresa.strip() and 'ID' in df_filtrado_base.columns:
            try:
                 # Intentar convertir ID a string para comparación segura
                 df_filtrado_base = df_filtrado_base[df_filtrado_base['ID'].astype(str) == cod_empresa.strip()]
            except KeyError:
                 st.warning("Columna 'ID' no encontrada para filtrar por empresa.")
            except Exception as e_id:
                 st.warning(f"No se pudo filtrar por ID de empresa: {e_id}")

        st.info(f"Se analizarán {len(df_filtrado_base)} registros entre {fecha_inicio} y {fecha_fin}" + (f" para la empresa ID '{cod_empresa}'." if cod_empresa.strip() else "."))
        if df_filtrado_base.empty:
             st.warning("No hay datos que coincidan con los filtros seleccionados.")
             # No detener, permitir que el usuario cambie filtros

    except Exception as e_filter:
        st.error(f"Error al aplicar filtros iniciales: {e_filter}")
        st.stop()


    # Tabs para Informe General y Análisis Específico
    tab1, tab2 = st.tabs(["📊 Informe General", "❓ Análisis Específico"])

    # --------------------------------------------------------------------------
    # A) TAB: Generar Informe General
    # --------------------------------------------------------------------------
    with tab1:
        st.subheader("Informe General de Bienestar")
        st.write("Genera un resumen del estado de bienestar para el periodo y empresa seleccionados.")
        if st.button("🚀 Generar Informe General"):
            if df_filtrado_base.empty:
                 st.warning("No hay datos para generar el informe con los filtros actuales.")
            else:
                 with st.spinner("Generando informe general... Por favor espera."):
                     # Llamar a la función que hace todo el trabajo
                     informe_texto, figuras, fig_titulos = generar_informe_general(df_filtrado_base, fecha_inicio, fecha_fin)

                     if "Error" in informe_texto:
                         st.error(informe_texto)
                     else:
                         # Mostrar el texto del informe general en la app (dentro de expander)
                         with st.expander("Ver Texto del Informe General", expanded=False):
                             st.markdown(informe_texto) # Usar markdown para formato

                         # Construir el PDF
                         st.write("Construyendo PDF del informe general...")
                         pdf_general = PDFReport('informe_general.pdf')
                         # Usar add_markdown para el cuerpo principal
                         pdf_general.add_markdown(informe_texto)

                         # Insertar figuras con títulos
                         pdf_general.add_title("Visualizaciones del Informe General", level=2)
                         for fig, title in zip(figuras, fig_titulos):
                              pdf_general.add_paragraph(f"**{title}**", style='CustomHeading')
                              pdf_general.insert_image(fig)

                         try:
                             pdf_general.build_pdf()
                             st.success("Informe general en PDF generado.")
                             # Ofrecer el PDF para descargarlo
                             with open('informe_general.pdf', 'rb') as f:
                                 st.download_button(
                                     label="📥 Descargar Informe General en PDF",
                                     data=f,
                                     file_name="informe_general.pdf",
                                     mime="application/pdf"
                                 )
                         except Exception as e_pdf_gen:
                             st.error(f"Error al construir el PDF general: {e_pdf_gen}")


    # --------------------------------------------------------------------------
    # B) TAB: Análisis específico (pregunta del usuario) usando Gemini
    # --------------------------------------------------------------------------
    with tab2:
        st.subheader("Análisis Específico Guiado por IA")
        st.write("Realiza una pregunta sobre los datos y la IA seleccionará el análisis adecuado.")

        # Variables de sesión para este tab
        if "pregunta_especifica" not in st.session_state: st.session_state.pregunta_especifica = ""
        if "filtro_especifico" not in st.session_state: st.session_state.filtro_especifico = ""
        if "analisis_especifico_realizado" not in st.session_state: st.session_state.analisis_especifico_realizado = False
        if "pdf_especifico_path" not in st.session_state: st.session_state.pdf_especifico_path = None

        # Mostrar campos de entrada si no se ha realizado análisis O si se pide otro
        if not st.session_state.analisis_especifico_realizado:
            st.session_state.pregunta_especifica = st.text_area(
                "Tu Pregunta:",
                value=st.session_state.pregunta_especifica,
                height=100,
                placeholder="Ej: ¿Cuál es la relación entre la edad y los síntomas de burnout?"
            )
            st.session_state.filtro_especifico = st.text_input(
                "Filtros Adicionales (opcional, lenguaje natural):",
                value=st.session_state.filtro_especifico,
                placeholder="Ej: solo mujeres del sector privado con más de 2 años de antigüedad"
            )

            if st.button("🔍 Realizar Análisis Específico"):
                 if not st.session_state.pregunta_especifica.strip():
                     st.warning("Por favor, ingresa una pregunta.")
                 elif df_filtrado_base.empty:
                      st.warning("No hay datos para analizar con los filtros de fecha/empresa actuales.")
                 else:
                     with st.spinner('Procesando tu pregunta y realizando análisis...'):
                         # 1) Interpretar filtro natural adicional
                         filtros_query = procesar_filtros(st.session_state.filtro_especifico)
                         if filtros_query:
                              st.info(f"Filtro adicional interpretado como: `{filtros_query}`")

                         # 2) Consultar a Gemini para la opción de análisis
                         opcion_sugerida = procesar_pregunta(st.session_state.pregunta_especifica)

                         if opcion_sugerida:
                              st.success(f"IA sugiere realizar el análisis tipo: **Opción {opcion_sugerida}**")
                              # 3) Ejecutar el análisis
                              resultados_txt, figuras_list = realizar_analisis(
                                  opcion=opcion_sugerida,
                                  pregunta_usuario=st.session_state.pregunta_especifica,
                                  filtros=filtros_query,
                                  df_base=df_filtrado_base # Usar el DF ya filtrado por fecha/ID
                              )

                              # Mostrar resultados de texto en la app
                              st.markdown("### Resultados del Análisis:")
                              st.text_area("Resultados:", value=resultados_txt, height=200, disabled=True)

                              # 4) Generar informe PDF específico
                              st.write("Generando informe PDF...")
                              pdf_path = generar_informe(
                                  st.session_state.pregunta_especifica,
                                  opcion_sugerida,
                                  resultados_txt,
                                  figuras_list
                              )

                              if pdf_path:
                                   st.session_state.pdf_especifico_path = pdf_path
                                   st.session_state.analisis_especifico_realizado = True
                                   st.rerun() # Refrescar para mostrar el botón de descarga
                              else:
                                   st.error("No se pudo generar el informe PDF.")

                         else:
                              st.error("La IA no pudo determinar el tipo de análisis adecuado para tu pregunta.")

        # Si el análisis ya se hizo, mostrar botón de descarga y opción para nueva consulta
        if st.session_state.analisis_especifico_realizado:
             st.success("Análisis completado y PDF generado.")
             if st.session_state.pdf_especifico_path and os.path.exists(st.session_state.pdf_especifico_path):
                  with open(st.session_state.pdf_especifico_path, 'rb') as f:
                       st.download_button(
                           label="📥 Descargar Informe Específico en PDF",
                           data=f,
                           file_name=os.path.basename(st.session_state.pdf_especifico_path),
                           mime="application/pdf"
                       )
             else:
                  st.warning("El archivo PDF del informe no se encontró.")

             if st.button("🔄 Realizar Otra Consulta Específica"):
                  # Limpiar estado para permitir nueva consulta
                  st.session_state.analisis_especifico_realizado = False
                  st.session_state.pregunta_especifica = "" # Opcional: limpiar campos
                  st.session_state.filtro_especifico = ""
                  st.session_state.pdf_especifico_path = None
                  st.rerun()


if __name__ == "__main__":
    main()
