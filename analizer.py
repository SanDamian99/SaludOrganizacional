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
# from fpdf import FPDF, HTMLMixin # FPDF/HTMLMixin no se usan con ReportLab
import re
import markdown
import io
import base64
import os
# from fpdf.enums import XPos, YPos # No se usan con ReportLab
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus.doctemplate import LayoutError # Keep LayoutError for catching
from bs4 import BeautifulSoup
from PIL import Image as PILImage
import math
from scipy.stats import chi2_contingency
import numpy as np # Asegurarse de importar numpy

# Importar la librería de Gemini
import google.generativeai as genai

# --- NO st.set_page_config() aquí ---

# Configurar la API de Gemini
try:
    # Intenta obtener la clave API desde los secrets
    if "YOUR_API_KEY" not in st.secrets:
        st.error("Error: La clave API 'YOUR_API_KEY' no se encontró en los secrets de Streamlit.")
        st.info("Por favor, añade tu clave API de Gemini a los secrets con el nombre 'YOUR_API_KEY'.")
        st.stop()
    YOUR_API_KEY = st.secrets["YOUR_API_KEY"]
    genai.configure(api_key=YOUR_API_KEY)
    st.success("API Key de Gemini cargada correctamente.") # Mensaje de éxito
except Exception as e:
    st.error(f"Error al configurar la API de Gemini. Detalle: {e}")
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
    st.success("Modelo Gemini inicializado.") # Mensaje de éxito
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

# --- NUEVO Diccionario de Datos con Prefijos ---
data_dictionary = {
   "Variables Sociodemográficas": {
       "(SD)Edad": {"Tipo": "Continua", "NombreExacto": "Edad"}, # NombreExacto puede ser obsoleto ahora
       "(SD)Sexo": {"Tipo": "Categórica", "Valores": ["Hombre", "Mujer", "Otro", "Prefiero no decir"]},
       "(SD)Estado Civil": {"Tipo": "Categórica", "Valores": ["Soltero", "Casado", "Separado", "Unión Libre", "Viudo"]},
       "(SD)Numero de hijos": {"Tipo": "Continua"},
       "(SD)Nivel Educativo": {"Tipo": "Categórica", "Valores": ["Primaria", "Bachiller", "Técnico", "Tecnológico", "Tecnológo", "Profesional", "Pregrado", "Posgrado", "Maestría", "Doctorado"]},
       "(SD)Departamento ": {"Tipo": "Categórica"}, # Quitar NombreExacto si la clave es el nombre real
       "(SD)Ciudad /Municipio": {"Tipo": "Categórica"},
       "(SD)Zona de vivienda": {"Tipo": "Categórica", "Valores": ["Urbana", "Rural"]},
       "(SD)Estrato socioeconomico": {"Tipo": "Categórica", "Valores": [1, 2, 3, 4, 5, 6]}
   },
   "Variables Laborales": {
       "(LB)Sector Económico ": {"Tipo": "Categórica"},
       "(LB)Sector empresa": {"Tipo": "Categórica", "Valores": ["Público", "Privado", "Mixto"]},
       "(LB)Tamaño Empresa": {"Tipo": "Categórica", "Valores": ["Menos de 10 empleados", "Entre 10 y 50 empleados", "Entre 50 y 200 empleados", "Entre 200 y 500 empleados", "Más de 500 empleados"]},
       "(LB)Trabajo por turnos": {"Tipo": "Categórica", "Valores": ["Sí", "No"]},
       "(LB)Tipo de Contrato": {"Tipo": "Categórica", "Valores": ["Indefinido", "Termino Indefinido", "Término fijo", "Obra o labor", "Aprendizaje", "Aprendizaje- SENA", "Presentación de servicios", "Temporal", "No hay información"]},
       "(LB)Número de horas de trabajo semanal ": {"Tipo": "Continua"},
       "(LB)Ingreso salarial mensual ": {"Tipo": "Categórica", "Valores": ["Menos de 1 SMLV", "Entre 1 y 3 SMLV", "Entre 3 y 5 SMLV", "Entre 5 y 10 SMLV", "Más de 10 SMLV"]},
       "(LB)Cargo": {"Tipo": "Categórica", "Valores": ["Operativo", "Administrativo", "Directivo", "Profesional", "Técnico", "Asistencial", "Aprendiz SENA"]},
       "(LB)Personas a cargo en la empresa": {"Tipo": "Categórica", "Valores": ["Sí", "No"]},
       "(LB)Años de experiencia laboral": {"Tipo": "Categórica", "Valores": ["Menos de 1 año", "Entre 1 a 5", "Entre 5 a 10", "Entre 10 a 15", "Entre 15 a 20", "Entre 20 a 25", "Más de 25"]},
       "(LB)Antigüedad en el cargo/labor actual ": {"Tipo": "Categórica", "Valores": ["Menos de 1 año", "Entre 1 y 3 años", "Entre 3 y 7 años", "Entre 7 y 10 años", "Más de 10 años", "No hay información"]},
       "(LB)Tipo de modalidad de trabajo": {"Tipo": "Categórica", "Valores": ["Presencial", "Híbrido", "Remoto", "Teletrabajo", "Trabajo en casa"]},
       "(LB)Tiempo promedio de traslado al trabajo/casa al día ": {"Tipo": "Categórica", "Valores": ["Menos de 1 hora", "Entre 1 y 2 horas", "Entre 2 y 3 horas", "Más de 3 horas"]},
       "(LB)Horas de formación recibidas (ultimo año)": {"Tipo": "Continua"}
   },
   "Dimensiones de Bienestar y Salud Mental": {
       "Control del Tiempo": {
           "Tipo": "Likert", "Acronimo": "CT",
           "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
           "Preguntas": [
               "(BM),(CT)Tengo la opción de decidir qué hago en mi trabajo.",
               "(BM),(CT)Tengo algo que decir sobre la forma en que hago mi trabajo.",
               "(BM),(CT)Tengo voz y voto sobre mi propio ritmo de trabajo.",
               "(BM),(CT)Me presionan para que trabaje muchas horas.",
               "(BM),(CT)Tengo algunos plazos de entrega inalcanzables.",
               "(BM),(CT)Tengo presiones de tiempo poco realistas.",
               "(BM),(CT)Tengo que descuidar algunas tareas porque tengo mucho que hacer."
           ]
       },
       "Compromiso del Líder": {
           "Tipo": "Likert", "Acronimo": "CL",
           "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
           "Preguntas": [
               "(BM),(CL)Puedo confiar en mi líder para que me ayude con un problema laboral.",
               "(BM),(CL)Si el trabajo se pone difícil, mi líder me ayudará.",
               "(BM),(CL)Recibo la ayuda y el apoyo que necesito de mi líder.",
               "(BM),(CL)Mi líder está dispuesto a escuchar mis problemas relacionados con el trabajo.",
               "(BM),(CL)Siento que mi líder valora mis contribuciones a esta organización.",
               "(BM),(CL)Mi líder me da suficiente crédito por mi trabajo duro.",
               "(BM),(CL)Mi líder me anima en mi trabajo con elogios y agradecimientos."
           ]
       },
       "Apoyo del Grupo": {
           "Tipo": "Likert", "Acronimo": "AG",
           "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
           "Preguntas": [
               "(BM),(AG)Si el trabajo se pone difícil, mis compañeros de trabajo me ayudarán.",
               "(BM),(AG)Recibo la ayuda y el apoyo que necesito de mis compañeros de trabajo.",
               "(BM),(AG)Mis compañeros de trabajo están dispuestos a escuchar mis problemas laborales."
           ]
       },
       "Claridad de Rol": {
           "Tipo": "Likert", "Acronimo": "CR",
           "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
            "Preguntas": [
                "(BM),(CR)Tengo claro lo que se espera de mí en el trabajo.",
                "(BM),(CR)Sé cómo hacer mi trabajo.",
                "(BM),(CR)Tengo claro cuáles son mis deberes y responsabilidades.",
                "(BM),(CR)Entiendo cómo mi trabajo encaja en el objetivo general de la organización.",
                "(BM),(CR)Diferentes grupos en el trabajo me exigen cosas que son difíciles de hacer al mismo tiempo.",
                "(BM),(CR)Diferentes personas en el trabajo esperan de mí cosas contradictorias.",
                "(BM),(CR)Recibo solicitudes incompatibles de dos o más personas."
            ]
       },
       "Cambio Organizacional": {
           "Tipo": "Likert", "Acronimo": "CO",
           "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
           "Preguntas": [
               "(BM),(CO)Me consultan sobre cambios propuestos en el trabajo.",
               "(BM),(CO)Cuando se realizan cambios en el trabajo, tengo claro cómo funcionarán en la práctica.",
               "(BM),(CO)Estoy claramente informado sobre la naturaleza de los cambios que se producen en esta organización.",
               "(BM),(CO)Puedo expresar inquietudes sobre cambios que afectan mi trabajo."
           ]
       },
       "Responsabilidad Organizacional": {
           "Tipo": "Likert", "Acronimo": "RO",
           "Escala": {1: "Nunca", 2: "Rara vez", 3: "Alguna vez", 4: "Algunas veces", 5: "A menudo", 6: "Frecuentemente", 7: "Siempre"},
           "Preguntas": [
               "(BM),(RO)En mi lugar de trabajo la salud física y mental es un prioridad de los líderes.",
               "(BM),(RO)En mi lugar de trabajo se hacen mediciones periódicas de los niveles de salud mental de las personas.",
               "(BM),(RO)En mi lugar de trabajo existen recursos accesibles y fáciles de usar para las necesidades relacionadas con la salud mental de las personas.",
               "(BM),(RO)Recibo entrenamiento periódico sobre pautas para el cuidado de mi salud mental en el trabajo.",
               "(BM),(RO)En mi lugar de trabajo se comunican claramente los resultados de las acciones implementadas para el cuidado de la salud mental de las personas."
           ]
       },
       "Conflicto Familia-Trabajo": {
           "Tipo": "Likert", "Acronimo": "FT",
           "Escala": {1: "Totalmente en desacuerdo", 2: "Muy/Mod. desacuerdo", 3: "Algo desacuerdo", 4: "Neutro", 5: "Algo acuerdo", 6: "Muy/Mod. acuerdo", 7: "Totalmente acuerdo"},
           "Preguntas": [
               "(BM),(FT)Las demandas de mi familia o cónyuge / pareja interfieren con las actividades relacionadas con el trabajo.",
               "(BM),(FT)Tengo que posponer las tareas en el trabajo debido a las exigencias de mi tiempo en casa.",
               "(BM),(FT)Las cosas que quiero hacer en el trabajo no se hacen debido a las demandas de mi familia o mi cónyuge / pareja.",
               "(BM),(FT)Mi vida hogareña interfiere con mis responsabilidades en el trabajo, como llegar al trabajo a tiempo, realizar las tareas diarias y trabajar.",
               "(BM),(FT)La tensión relacionada con la familia interfiere con mi capacidad para realizar tareas relacionadas con el trabajo.",
               "(BM),(FT)Las exigencias de mi trabajo interfieren con mi hogar y mi vida familiar.",
               "(BM),(FT)La cantidad de tiempo que ocupa mi trabajo dificulta el cumplimiento de las responsabilidades familiares.",
               "(BM),(FT)Las cosas que quiero hacer en casa no se hacen debido a las exigencias que me impone mi trabajo.",
               "(BM),(FT)Mi trabajo produce tensión que dificulta el cumplimiento de los deberes familiares.",
               "(BM),(FT)Debido a deberes relacionados con el trabajo, tengo que hacer cambios en mis planes para las actividades familiares."
           ]
       },
       "Síntomas de Burnout": {
           "Tipo": "Likert", "Acronimo": "SB",
           "Escala": {1: "Nunca", 2: "Raramente", 3: "Algunas veces", 4: "A menudo", 5: "Siempre"},
           "Preguntas": [
               "(BM),(SB)En mi trabajo, me siento agotado/a emocionalmente.",
               "(BM),(SB)Al final del día de trabajo, me resulta difícil recuperar mi energía.",
               "(BM),(SB)Me siento físicamente agotado/a en mi trabajo.",
               "(BM),(SB)Me cuesta encontrar entusiasmo por mi trabajo.",
               "(BM),(SB)Siento una fuerte aversión hacia mi trabajo.",
               "(BM),(SB)Soy cínico (despreocupado) sobre lo que mi trabajo significa para los demás.",
               "(BM),(SB)Tengo problemas para mantenerme enfocado en mi trabajo.",
               "(BM),(SB)Cuando estoy trabajando, tengo dificultades para concentrarme.",
               "(BM),(SB)Cometo errores en mi trabajo, porque tengo mi mente en otras cosas.",
               "(BM),(SB)En mi trabajo, me siento incapaz de controlar mis emociones.",
               "(BM),(SB)No me reconozco en la forma que reacciono en el trabajo.",
               "(BM),(SB)Puedo reaccionar exageradamente sin querer."
            ]
       },
       "Compromiso": {
           "Tipo": "Likert", "Acronimo": "CP",
           "Escala": {1: "Muy desacuerdo", 2: "Mod. desacuerdo", 3: "Lig. desacuerdo", 4: "Lig. acuerdo", 5: "Mod. acuerdo", 6: "Muy acuerdo"},
           "Preguntas": [
               "(BM),(CP)Mi labor contribuye a la misión y visión de la empresa para la que laboro.",
               "(BM),(CP)Me siento entusiasmado por mi trabajo.",
               "(BM),(CP)Cuando me levanto en la mañana tengo ganas de ir a trabajar."
           ]
       },
       "Defensa de la Organización": {
           "Tipo": "Likert", "Acronimo": "DO",
            "Escala": {1: "Muy desacuerdo", 2: "Mod. desacuerdo", 3: "Lig. desacuerdo", 4: "Lig. acuerdo", 5: "Mod. acuerdo", 6: "Muy acuerdo"},
           "Preguntas": [
               "(BM),(DO)Me siento orgulloso de la empresa en la que laboro.",
               "(BM),(DO)Recomendaría ampliamente a otros trabajar en la empresa en la que laboro.",
               "(BM),(DO)Me molesta que otros hablen mal de la empresa en la que laboro."
           ]
       },
       "Satisfacción": {
           "Tipo": "Likert", "Acronimo": "ST",
            "Escala": {1: "Muy desacuerdo", 2: "Mod. desacuerdo", 3: "Lig. desacuerdo", 4: "Lig. acuerdo", 5: "Mod. acuerdo", 6: "Muy acuerdo"},
           "Preguntas": [
               "(BM),(ST)Considero mi trabajo significativo.",
               "(BM),(ST)Me gusta hacer las tareas y actividades de mi trabajo.",
               "(BM),(ST)Me siento satisfecho por el salario y los beneficios que recibo en mi trabajo."
           ]
       },
       "Intención de Retiro": {
           "Tipo": "Likert", "Acronimo": "IR",
            "Escala": {1: "Muy desacuerdo", 2: "Mod. desacuerdo", 3: "Lig. desacuerdo", 4: "Lig. acuerdo", 5: "Mod. acuerdo", 6: "Muy acuerdo"},
           "Preguntas": [
               "(BM),(IR)Me veo trabajando en este lugar en el próximo año.",
               "(BM),(IR)A menudo considero seriamente dejar mi trabajo actual.",
               "(BM),(IR)Tengo la intención de dejar mi trabajo actual en los próximos 3 a 6 meses.",
               "(BM),(IR)He empezado a buscar activamente otro trabajo."
           ]
       },
       "Bienestar Psicosocial (Escala de Afectos)": {
           "Tipo": "Diferencial Semántico", "Acronimo": "PA",
           "Escala": {1: "Extremo Izq", 7: "Extremo Der"},
           # Ajustar estos si los nombres de columna son "(BM),(PA)2", etc.
           "Preguntas": [f"(BM),(PA){i}" for i in range(2, 11)]
       },
       "Bienestar Psicosocial (Escala de Competencias)": {
           "Tipo": "Diferencial Semántico", "Acronimo": "PC",
           "Escala": {1: "Extremo Izq", 7: "Extremo Der"},
           "Preguntas": [f"(BM),(PC){i}" for i in range(11, 21)]
       },
       "Bienestar Psicosocial (Escala de Expectativas)": {
           "Tipo": "Likert", "Acronimo": "PE",
           "Escala": {1: "Bajando", 7: "Subiendo"},
           "Preguntas": [
               "(BM),(PE)Mi motivación por el trabajo",
               "(BM),(PE)Mi identificación con los valores de la organización.", # NUEVO, verificar si existe
               "(BM),(PE)Mi rendimiento profesional.", # NUEVO, verificar si existe
               "(BM),(PE)Mi capacidad para responder a mi carga de trabajo",
               "(BM),(PE)La calidad de mis condiciones de trabajo.",
               "(BM),(PE)Mi autoestima profesional",
               "(BM),(PE)La cordialidad en mi ambiente social de trabajo.",
               "(BM),(PE)El equilibrio entre mi trabajo y mi vida privada.",
               "(BM),(PE)Mi confianza en mi futuro profesional",
               "(BM),(PE)Mi calidad de vida laboral.", # NUEVO, verificar si existe
               "(BM),(PE)El sentido de mi trabajo",
               "(BM),(PE)Mi cumplimiento de las normas de la dirección.",
               "(BM),(PE)Mi estado de ánimo laboral ", # Espacio?
               "(BM),(PE)Mis oportunidades de promoción laboral.",
               "(BM),(PE)Mi sensación de seguridad en el trabajo",
               "(BM),(PE)Mi participación en las decisiones de la organización.",
               "(BM),(PE)Mi satisfacción con el trabajo.",
               "(BM),(PE)Mi relación profesional.", # Verificar si es "relaciones"
               "(BM),(PE)El nivel de excelencia de mi organización.",
               "(BM),(PE)MI eficacia profesional", # MI Mayúscula?
               "(BM),(PE)Mi compromiso con el trabajo",
               "(BM),(PE)Mis competencias profesionales"
           ]
       },
       "Factores de Efectos Colaterales (Escala de Somatización)": {
           "Tipo": "Likert", "Acronimo": "CS",
           "Escala": {1: "Nunca", 2: "Raramente", 3: "Ocasionalmente", 4: "Algunas veces", 5: "Frecuentemente", 6: "Casi siempre", 7: "Siempre"},
           "Preguntas": [
               "(BM),(CS)Trastornos digestivos",
               "(BM),(CS)Dolores de cabeza",
               "(BM),(CS)Alteraciones de sueño",
               "(BM),(CS)Dolores de espalda",
               "(BM),(CS)Tensiones musculares"
           ]
       },
       "Factores de Efectos Colaterales (Escala de Desgaste)": {
           "Tipo": "Likert", "Acronimo": "CD",
            "Escala": {1: "Nunca", 2: "Raramente", 3: "Ocasionalmente", 4: "Algunas veces", 5: "Frecuentemente", 6: "Casi siempre", 7: "Siempre"},
           "Preguntas": [
               "(BM),(CD)Sobrecarga de trabajo",
               "(BM),(CD)Desgaste emocional",
               "(BM),(CD)Agotamiento físico",
               "(BM),(CD)Cansancio mental " # Espacio?
           ]
       },
       "Factores de Efectos Colaterales (Escala de Alienación)": {
           "Tipo": "Likert", "Acronimo": "CA",
            "Escala": {1: "Nunca", 2: "Raramente", 3: "Ocasionalmente", 4: "Algunas veces", 5: "Frecuentemente", 6: "Casi siempre", 7: "Siempre"},
           "Preguntas": [
               "(BM),(CA)Mal humor ", # Espacio?
               "(BM),(CA)Baja realización personal",
               "(BM),(CA)Trato distante",
               "(BM),(CA)Frustración " # Espacio?
           ]
       }
   }
}

# --- Limpiar nombres en 'Preguntas' (asegurar strip) ---
# Esto ahora es menos crucial si los nombres en el dict ya están limpios, pero no hace daño
for dim_cat, dim_content in data_dictionary.items():
    if dim_cat == "Dimensiones de Bienestar y Salud Mental":
        for dim_name, details in dim_content.items():
             if "Preguntas" in details:
                details["Preguntas"] = [str(p).strip() for p in details["Preguntas"]]
    elif isinstance(dim_content, dict): # Para SD y LB
         for var_key, details in dim_content.items():
              # No hay 'Preguntas' aquí, pero podríamos limpiar la clave si fuera necesario
              pass

# --- Mapeos Manuales y Creación de label_maps (Actualizar si es necesario) ---
# ESTOS MAPEOS DEBEN REFLEJAR LAS ESCALAS USADAS EN LAS COLUMNAS *NUMÉRICAS*
# Si las columnas ahora tienen prefijo pero los valores son 1, 2, 3... esto sigue igual.
likert_manual_mappings = {
    # Ejemplo: Escala Frecuencia 1-7
    ('Nunca', 'Rara vez', 'Alguna vez', 'Algunas veces', 'A menudo', 'Frecuentemente', 'Siempre'): {
        1: 'Nunca', 2: 'Rara vez', 3: 'Alguna vez', 4: 'Algunas veces', 5: 'A menudo', 6: 'Frecuentemente', 7: 'Siempre'
    },
    # Ejemplo: Escala Acuerdo 1-7 (Variante 2)
    ('Totalmente en desacuerdo', 'Muy en desacuerdo', 'Algo en desacuerdo', 'Ni de acuerdo ni en desacuerdo', 'Algo de acuerdo', 'Muy de acuerdo', 'Totalmente de acuerdo'): {
        1: 'Totalmente desacuerdo', 2: 'Muy desacuerdo', 3: 'Algo desacuerdo', 4: 'Neutro', 5: 'Algo acuerdo', 6: 'Muy acuerdo', 7: 'Totalmente acuerdo'
    },
    # Ejemplo: Escala Burnout 1-5
    ('Nunca', 'Raramente', 'Algunas veces', 'A menudo', 'Siempre'): {
        1: 'Nunca', 2: 'Raramente', 3: 'Algunas veces', 4: 'A menudo', 5: 'Siempre'
    },
     # Ejemplo: Escala Acuerdo 1-6
    ('Muy en desacuerdo', 'Moderadamente en desacuerdo', 'Ligeramente en desacuerdo', 'Ligeramente de acuerdo', 'Moderadamente de acuerdo', 'Muy de acuerdo'): {
        1: 'Muy desacuerdo', 2: 'Mod. desacuerdo', 3: 'Lig. desacuerdo', 4: 'Lig. acuerdo', 5: 'Mod. acuerdo', 6: 'Muy acuerdo'
    },
    # Ejemplo: Escala Efectos Colaterales 1-7
    ('Nunca', 'Raramente', 'Ocasionalmente', 'Algunas veces', 'Frecuentemente', 'Casi siempre', 'Siempre'): {
        1: 'Nunca', 2: 'Raramente', 3: 'Ocasionalmente', 4: 'Algunas veces', 5: 'Frecuentemente', 6: 'Casi siempre', 7: 'Siempre'
    }
    # Añadir mapeos para otras escalas si existen (Competencias, Afectos, Expectativas si no son 1-7 directo)
}

# Crear mapeo INVERSO (número -> etiqueta) para labels
label_maps = {}
# Esta lógica ahora asocia el mapeo basado en la Escala definida en data_dictionary
for dim_cat, dim_content in data_dictionary.items():
     if dim_cat == "Dimensiones de Bienestar y Salud Mental":
         for dim_name, details in dim_content.items():
             escala_dict = details.get("Escala")
             if isinstance(escala_dict, dict) and "Preguntas" in details:
                 # Crear el mapeo numérico -> etiqueta desde la 'Escala'
                 num_to_label_map = {k: str(v) for k, v in escala_dict.items() if isinstance(k, (int, float))}
                 if num_to_label_map: # Si se pudo crear un mapa
                      for pregunta_col in details["Preguntas"]:
                          col_clean = pregunta_col.strip() # Nombre con prefijo
                          if col_clean not in label_maps:
                              label_maps[col_clean] = num_to_label_map
                              # st.write(f"DEBUG: Label map (desde Escala) asignado a '{col_clean}'")


# --- Cargar el archivo CSV limpio ---
ruta_csv = 'cleaned_data.csv'
try:
    df = pd.read_csv(ruta_csv, parse_dates=['Hora de inicio', 'Hora de finalización'], dayfirst=False)
    df.dropna(axis=1, how='all', inplace=True)
    df.columns = df.columns.str.strip() # Asegurar limpieza de nombres de columna
    st.success(f"Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas.")

    # Convertir columnas a Categórica BASADO EN LAS CLAVES DEL NUEVO data_dictionary
    st.write("Convirtiendo tipos categóricos...")
    converted_count = 0
    for category, variables in data_dictionary.items():
         for col_name_key, var_details in variables.items(): # col_name_key ES el nombre con prefijo
              if var_details.get("Tipo") == "Categórica":
                   col_name_key = col_name_key.strip() # Asegurar limpieza
                   if col_name_key in df.columns:
                       try:
                           # Convertir solo si no lo es ya
                           if not pd.api.types.is_categorical_dtype(df[col_name_key]):
                               df[col_name_key] = df[col_name_key].astype('category')
                               converted_count += 1
                       except Exception as e:
                           st.warning(f"No se pudo convertir '{col_name_key}' a categórica: {e}. Tipo actual: {df[col_name_key].dtype}.")
                   # else: # Advertir si una columna categórica del dict no está en el df
                   #     st.warning(f"Columna categórica '{col_name_key}' del diccionario no encontrada en el CSV.")
    st.write(f"Conversión a categórico intentada. {converted_count} columnas convertidas.")


except FileNotFoundError:
    st.error(f"Error: No se encontró '{ruta_csv}'.")
    st.stop()
except Exception as e:
    st.error(f"Error al cargar/procesar '{ruta_csv}': {e}")
    st.stop()


# Extraer información de las columnas y tipos de datos del DF CARGADO
def obtener_informacion_datos(df_loaded):
    buffer = io.StringIO()
    df_loaded.info(buf=buffer)
    s = buffer.getvalue()
    cat_cols_summary = []
    # Aumentar límite para mostrar más únicos
    for col in df_loaded.select_dtypes(include=['category', 'object']).columns:
         unique_count = df_loaded[col].nunique()
         if unique_count < 100: # Aumentado el límite
             try:
                 # Intentar obtener únicos, manejar errores si hay tipos mixtos no comparables
                 uniques = df_loaded[col].unique()
                 cat_cols_summary.append(f"\n- {col} ({unique_count} unique): {list(uniques)}")
             except TypeError:
                 cat_cols_summary.append(f"\n- {col} ({unique_count} unique): [Error al listar por tipos mixtos]")
         else:
             cat_cols_summary.append(f"\n- {col} ({unique_count} unique)")

    return s + "\n\nResumen de únicas en Categóricas/Object (mostrando hasta 100):" + "".join(cat_cols_summary)

informacion_datos = obtener_informacion_datos(df) # Pasar el df cargado

# --- Definir opciones_analisis (sin cambios) ---
opciones_analisis = """
Opciones de análisis disponibles:
... (igual que antes) ...
7. **Tablas de Contingencia y Chi-cuadrado:** Permite analizar la relación entre dos variables categóricas o entre una variable categórica y una numérica (agrupando la numérica). Se calculará la tabla de contingencia y se realizará la prueba Chi-cuadrado para ver la asociación. Los ejes de la tabla y gráfico mostrarán las etiquetas correctas.

   *Ejemplo:* Analizar la relación entre "Sexo" y "Tiene_Hijos" (derivada de Numero de hijos) o entre "Nivel Educativo" y "Satisfacción" (agrupada).
"""

# --- Preparar prompt_informacion_datos (sin cambios) ---
prompt_informacion_datos = f"""
Los siguientes son los datos y tipos de datos que tenemos (basado en el archivo CSV limpio):
{informacion_datos}
... (resto igual) ...
"""

# --- Enviar prompt inicial a Gemini (sin cambios) ---
rate_limiter = RateLimiter(max_calls=5, period=61) # Un poco más flexible

def enviar_prompt(prompt):
    # ... (igual que antes, con manejo de errores mejorado) ...
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            rate_limiter.wait()
            response = model.generate_content([prompt])
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            elif response and hasattr(response, 'parts'):
                 return "".join(part.text for part in response.parts).strip()
            else:
                st.warning(f"Respuesta inesperada de Gemini (intento {retries+1}): {response}")
                if retries == max_retries - 1:
                     return "No se recibió una respuesta de texto válida de Gemini."
        except (ConnectionError, ProtocolError) as e:
            wait_time = (2 ** retries) + random.random()
            st.warning(f"Error de conexión/protocolo con Gemini: {e}. Reintentando en {wait_time:.2f} segundos...")
            time.sleep(wait_time)
        except Exception as e:
            st.error(f"Error inesperado al llamar a Gemini API (intento {retries+1}): {e}")
            # Específicamente para errores de clave API
            if "API key not valid" in str(e) or "permission" in str(e).lower():
                 st.error("Error de autenticación con Gemini: La clave API no es válida o no tiene permisos. Verifica los secrets.")
                 return "Error crítico: Clave API inválida o sin permisos."
            # Otros errores de la API pueden tener códigos específicos
            if "RATE_LIMIT" in str(e).upper():
                 st.warning("Límite de tasa de Gemini alcanzado (desde la API). Esperando más tiempo...")
                 wait_time = (2 ** (retries + 1)) + random.random() # Espera exponencial más larga
                 time.sleep(wait_time)
            else:
                 wait_time = (2 ** retries) + random.random()
                 time.sleep(wait_time)

            if retries == max_retries - 1:
                 return "Error al comunicarse con Gemini después de varios intentos."
        retries += 1
    return "Error: No se pudo comunicar con Gemini."


with st.spinner("Informando a Gemini sobre la estructura de datos..."):
    respuesta_informacion_datos = enviar_prompt(prompt_informacion_datos)
    if "Error" in respuesta_informacion_datos:
        st.error(f"No se pudo informar a Gemini correctamente: {respuesta_informacion_datos}")
    # else: # No mostrar este mensaje, es redundante si ya hay éxito en API/Modelo
    #    st.write("Gemini ha sido informado sobre los datos y opciones de análisis.")


# --- Función procesar_pregunta (sin cambios) ---
def procesar_pregunta(pregunta_usuario):
    # ... (igual que antes) ...
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
    try:
        opcion = int(respuesta)
        if 1 <= opcion <= 7:
            return str(opcion)
        else:
            st.warning(f"Gemini devolvió un número fuera de rango ({respuesta}).")
            return None # Indicar fallo
    except (ValueError, TypeError):
        st.warning(f"Gemini no devolvió un número válido ({respuesta}). Intentando extraer...")
        match = re.search(r'\b([1-7])\b', respuesta)
        if match:
            st.info(f"Se extrajo el número {match.group(1)} de la respuesta.")
            return match.group(1)
        return None # Indicar fallo

def obtener_variables_relevantes(pregunta, tipo_variable, df_current):
    """Usa data_dictionary actualizado (con prefijos) y sugerencias Gemini."""
    keywords_salud_mental = ["salud mental", "bienestar", "burnout", "estrés", "satisfacción", "compromiso", "líder", "equipo"]
    lower_pregunta = pregunta.lower()
    sugerir_dim_salud = any(kw in lower_pregunta for kw in keywords_salud_mental)

    all_cols = df_current.columns.tolist()
    numeric_cols = df_current.select_dtypes(include=np.number).columns.tolist()
    cat_cols = df_current.select_dtypes(include=['category', 'object']).columns.tolist()

    candidate_cols = all_cols
    if tipo_variable.lower() in ["numérica", "numerica"]: candidate_cols = numeric_cols
    elif tipo_variable.lower() in ["categórica", "categorica"]: candidate_cols = cat_cols

    # 1) Prioridad Salud Mental (Usa nombres con prefijo de data_dictionary)
    prioridad_salud = []
    if sugerir_dim_salud:
        all_dim_questions_prefixed = []
        bm_dims = data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {})
        for dim_name, details in bm_dims.items():
            if "Preguntas" in details:
                # Los nombres en "Preguntas" YA tienen prefijo
                all_dim_questions_prefixed.extend([p.strip() for p in details["Preguntas"]])
        all_dim_questions_prefixed = list(set(all_dim_questions_prefixed))

        for col_prefixed in all_dim_questions_prefixed:
            # Buscar coincidencia EXACTA primero
            if col_prefixed in candidate_cols:
                 if col_prefixed not in prioridad_salud: prioridad_salud.append(col_prefixed)
            # Fallback MUY cercano si el exacto falla (por si acaso)
            else:
                 matches = difflib.get_close_matches(col_prefixed, candidate_cols, n=1, cutoff=0.95)
                 if matches and matches[0] not in prioridad_salud:
                      prioridad_salud.append(matches[0])
                      st.info(f"Match cercano prioridad: '{col_prefixed}' -> '{matches[0]}'")


    # 2) Sugerencias de Gemini (Prompt sin cambios, parseo igual)
    prompt_variables = f"""... (prompt igual que antes, usa dtypes) ..."""
    resp_gemini = enviar_prompt(prompt_variables)
    variables_sugeridas = []
    if "Error" not in resp_gemini and resp_gemini:
        suggested_by_gemini = [x.strip() for x in resp_gemini.split(',') if x.strip()]
        for sug in suggested_by_gemini:
            # Validar sugerencia contra candidatas (con prefijos)
            if sug in candidate_cols and sug not in variables_sugeridas:
                 variables_sugeridas.append(sug)
            else: # Intentar fuzzy match si exacto falla
                 close = difflib.get_close_matches(sug, candidate_cols, n=1, cutoff=0.85)
                 if close and close[0] not in variables_sugeridas:
                      variables_sugeridas.append(close[0])
                      st.info(f"Match cercano sugerencia: '{sug}' -> '{close[0]}'")
    else:
        st.warning(f"Gemini no sugirió variables: {resp_gemini}.")
        # Fallback: usar prioridad_salud o primeras candidatas
        variables_sugeridas = [c for c in prioridad_salud if c in candidate_cols] or \
                              [c for c in candidate_cols[:5] if df_current[c].notna().any()]

    # 3) Combinar y filtrar (sin cambios en lógica)
    final_list = []
    for c in variables_sugeridas: # Poner sugeridas primero
         if c not in final_list: final_list.append(c)
    for c in prioridad_salud: # Añadir de prioridad no incluidas
         if c not in final_list and c in candidate_cols: final_list.append(c)

    # Asegurar que todas estén en candidate_cols y tengan datos
    final_list_no_empty = [col for col in final_list if col in candidate_cols and df_current[col].notna().any()]

    if not final_list_no_empty:
        st.warning(f"No se encontraron cols tipo '{tipo_variable}' con datos. Usando fallback.")
        final_list_no_empty = [col for col in candidate_cols if df_current[col].notna().any()]
        if not final_list_no_empty: st.error("¡No hay columnas válidas!")

    #st.write(f"DEBUG - Vars relevantes ({tipo_variable}): {final_list_no_empty}")
    return final_list_no_empty


# --- Función procesar_filtros (sin cambios) ---
def procesar_filtros(filtro_natural):
    # ... (igual que antes) ...
    if not filtro_natural or not filtro_natural.strip():
        return None
    prompt_filtro = f"""
    Convierte el siguiente filtro descrito en lenguaje natural a una consulta de pandas ('query').
    El DataFrame tiene estas columnas y tipos de datos:
    {df.dtypes.to_string()}

    Descripción del filtro: {filtro_natural}

    Proporciona únicamente la expresión de filtrado que `pandas.query()` entiende. Usa los nombres EXACTOS de las columnas.
    Maneja strings con comillas (ej., Sexo == 'Mujer'). Para fechas, asume que la columna ya es datetime y compara con strings de fecha como 'YYYY-MM-DD' (ej., `Hora_de_inicio >= '2023-01-15'`). Si una columna categórica se representa como número (ej. Estrato), usa el número (ej. Estrato == 3).

    Expresión pandas.query():
    """
    filtro_pandas = enviar_prompt(prompt_filtro)

    if "Error" in filtro_pandas or not filtro_pandas:
        st.error(f"Error al generar filtro pandas: {filtro_pandas}")
        return None
    filtro_limpio = filtro_pandas.split('pandas.query():')[-1].strip()
    filtro_limpio = re.sub(r'^[`"\']+|[`"\']+$', '', filtro_limpio)
    if not filtro_limpio or filtro_limpio.lower() == 'none':
        st.warning("Gemini no pudo generar un filtro válido.")
        return None
    # Validar sintaxis básica (muy simple)
    if not any(op in filtro_limpio for op in ['==', '!=', '<', '>', '<=', '>=', ' in ', ' not in ']):
         st.warning(f"El filtro generado '{filtro_limpio}' parece no tener operadores de comparación válidos.")
         # Podría ser un filtro simple como solo un booleano, así que no retornamos None aún
    return filtro_limpio

# --- Función get_label_map (igual que antes) ---
def get_label_map(variable_name):
    """Busca el mapeo de número a etiqueta para una variable."""
    variable_name = variable_name.strip()
    if variable_name in label_maps:
         return label_maps[variable_name]
    # Fallback: buscar en data_dictionary por si no se creó en label_maps
    for dim_cat, dim_content in data_dictionary.items():
        if "Preguntas" in dim_content:
             # Usar fuzzy match para encontrar la dimensión correcta si el nombre varía ligeramente
             clean_preguntas = [p.strip() for p in dim_content["Preguntas"]]
             matches = difflib.get_close_matches(variable_name, clean_preguntas, n=1, cutoff=0.9)
             if matches: # Si encontramos una pregunta similar en esta dimensión
                  escala = dim_content.get("Escala")
                  if isinstance(escala, dict):
                       # Asegurar que las claves son números y valores son strings
                       mapa_inverso = {k: str(v) for k, v in escala.items() if isinstance(k, (int, float))}
                       if mapa_inverso:
                            return mapa_inverso
    return None # No se encontró mapa


# --- Función realizar_analisis (Corrección error 'ha') ---
def realizar_analisis(opcion, pregunta_usuario, filtros=None, df_base=None):
    """
    Realiza el análisis y genera gráficos, usando etiquetas donde sea apropiado.
    CORREGIDO: Error 'ha' en tick_params.
    """
    resultados = ""
    figuras = [] # Lista para almacenar los OBJETOS de figura Matplotlib
    df_analisis = df_base.copy()

    if filtros:
        try:
            df_analisis = df_analisis.query(filtros)
            resultados += f"Aplicando filtro: `{filtros}`. Registros restantes: {len(df_analisis)}\n\n"
            if df_analisis.empty:
                 resultados += "**Advertencia:** El filtro resultó en 0 registros.\n"
                 return resultados, figuras
        except Exception as e:
            st.error(f"Error al aplicar el filtro: {e}. Se usará el DataFrame sin filtrar.")
            resultados += f"**Error al aplicar filtro:** {e}. Se continúa sin filtrar.\n\n"
            df_analisis = df_base.copy()
    else:
        resultados += f"Análisis sobre {len(df_analisis)} registros.\n\n"

    # === Opción 1: Distribución Categórica (CON LABELS) ===
    if opcion == '1':
        variables_relevantes = obtener_variables_relevantes(pregunta_usuario, 'categórica', df_analisis)
        if not variables_relevantes:
            resultados += "No se encontraron variables categóricas relevantes.\n"
            return resultados, figuras
        var_cat = variables_relevantes[0]
        # ... (resto lógica opción 1, incluyendo get_label_map y conteo) ...
        conteo = df_analisis[var_cat].value_counts(dropna=False).sort_index()
        labels = get_label_map(var_cat)
        plot_title = f'Distribución de {var_cat}'
        plot_xlabel = var_cat
        plot_ylabel = 'Frecuencia'
        index_original = conteo.index # Guardar índice original

        if labels and pd.api.types.is_numeric_dtype(conteo.index):
            try:
                conteo.index = conteo.index.map(labels).fillna(index_original.astype(str) + " (Sin Label)")
                plot_title = f'Distribución de {var_cat}'
                # st.write(f"DEBUG Op1: Labels aplicados a '{var_cat}'")
            except Exception as e:
                st.warning(f"Error al aplicar labels a '{var_cat}': {e}. Usando valores numéricos.")
                conteo.index = index_original # Revertir si falla
                plot_title = f'Distribución de {var_cat} (Valores Numéricos)'
                plot_xlabel = f'{var_cat} (Valor Numérico)'
        elif pd.api.types.is_categorical_dtype(df_analisis[var_cat]):
             conteo.index = conteo.index.astype(str)
        else:
            conteo.index = conteo.index.astype(str)

        resultados += f"**Análisis de Distribución para:** {var_cat}\n"
        resultados += f"Frecuencias:\n{conteo.to_string()}\n"

        if not conteo.empty:
            try:
                n_cats = len(conteo)
                fig_w = max(6, n_cats * 0.5)
                fig, axes = plt.subplots(1, 3, figsize=(min(15, fig_w + 5), 5)) # Ajustar ancho total

                # 1. Barras verticales
                conteo.plot(kind='bar', ax=axes[0], colormap='viridis')
                axes[0].set_title(plot_title)
                axes[0].set_xlabel(plot_xlabel)
                axes[0].set_ylabel(plot_ylabel)
                # CORREGIDO: Quitar 'ha'
                axes[0].tick_params(axis='x', rotation=45, labelsize=8)

                # 2. Pastel
                if n_cats <= 12: # Aumentar límite un poco
                    conteo.plot(kind='pie', autopct='%1.1f%%', ax=axes[1], startangle=90, colormap='viridis', pctdistance=0.85)
                    axes[1].set_ylabel('')
                    axes[1].set_title(plot_title)
                else:
                    axes[1].text(0.5, 0.5, 'Demasiadas categorías\npara gráfico de pastel', ha='center', va='center')
                    axes[1].set_axis_off()

                # 3. Barras horizontales
                conteo.plot(kind='barh', ax=axes[2], colormap='viridis')
                axes[2].set_title(plot_title)
                axes[2].set_xlabel(plot_ylabel)
                axes[2].set_ylabel(plot_xlabel)
                axes[2].tick_params(axis='y', labelsize=8)

                plt.tight_layout()
                st.pyplot(fig)
                figuras.append(fig) # <-- GUARDAR OBJETO FIGURA
            except Exception as e:
                st.error(f"Error al generar gráficos para {var_cat}: {e}")
        else:
             resultados += "No hay datos para graficar.\n"

    # === Opción 2: Descriptivas Numérica ===
    elif opcion == '2':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if not vars_relevantes:
            resultados += "No se encontraron variables numéricas relevantes.\n"
            return resultados, figuras
        var_num = vars_relevantes[0]
        # ... (resto lógica opción 2) ...
        estadisticas = df_analisis[var_num].describe()
        resultados += f"**Análisis Descriptivo para:** {var_num}\n"
        resultados += f"Estadísticas descriptivas:\n{estadisticas.to_string()}\n"

        if df_analisis[var_num].notna().any():
             try:
                 fig, axes = plt.subplots(1, 3, figsize=(15, 4))
                 sns.histplot(df_analisis[var_num], kde=False, ax=axes[0], bins=15)
                 axes[0].set_title(f'Histograma de {var_num}')
                 sns.boxplot(x=df_analisis[var_num], ax=axes[1])
                 axes[1].set_title(f'Boxplot de {var_num}')
                 sns.kdeplot(df_analisis[var_num], fill=True, ax=axes[2])
                 axes[2].set_title(f'Densidad de {var_num}')
                 plt.tight_layout()
                 st.pyplot(fig)
                 figuras.append(fig) # <-- GUARDAR OBJETO FIGURA
             except Exception as e:
                 st.error(f"Error al generar gráficos descriptivos para {var_num}: {e}")
        else:
             resultados += "No hay datos numéricos para graficar.\n"

    # === Opción 3: Relación 2 Numéricas ===
    elif opcion == '3':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables numéricas relevantes.\n"
            return resultados, figuras
        var_x = vars_relevantes[0]
        var_y = vars_relevantes[1]
        # ... (resto lógica opción 3) ...
        resultados += f"**Análisis de Relación entre:** {var_x} y {var_y}\n"
        df_rel = df_analisis[[var_x, var_y]].dropna()

        if len(df_rel) > 1:
             try:
                 correlacion = df_rel[var_x].corr(df_rel[var_y])
                 resultados += f"Coeficiente de correlación de Pearson: {correlacion:.3f}\n"
             except Exception as e:
                 resultados += f"No se pudo calcular la correlación: {e}\n"
             try:
                 # Usar jointplot, pero guardar la figura subyacente
                 joint_fig = sns.jointplot(data=df_rel, x=var_x, y=var_y, kind='reg', # Usar 'reg' para scatter+linea
                                        joint_kws={'line_kws':{'color':'red', 'linestyle':':'}},
                                        height=5)
                 joint_fig.fig.suptitle(f'Relación entre {var_x} y {var_y}', y=1.02)
                 st.pyplot(joint_fig.fig) # Mostrar la figura
                 figuras.append(joint_fig.fig) # <-- GUARDAR OBJETO FIGURA (joint_fig.fig)
             except Exception as e:
                 st.error(f"Error al generar gráficos de relación para {var_x} vs {var_y}: {e}")
        else:
            resultados += "No hay suficientes datos para analizar la relación.\n"

    # === Opción 4: Filtro + Descriptiva Numérica ===
    elif opcion == '4':
        # Filtros ya aplicados en df_analisis
        resultados += f"**Estadísticas Descriptivas (Datos Filtrados)**\n"
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if not vars_relevantes:
            resultados += "No se encontraron variables numéricas relevantes en los datos filtrados.\n"
            return resultados, figuras
        var_num4 = vars_relevantes[0]
        # ... (resto lógica opción 4) ...
        estadisticas = df_analisis[var_num4].describe()
        resultados += f"**Variable analizada:** {var_num4}\n"
        resultados += f"Estadísticas descriptivas (filtrado):\n{estadisticas.to_string()}\n"

        if df_analisis[var_num4].notna().any():
            try:
                fig, axes = plt.subplots(1, 3, figsize=(15, 4))
                sns.histplot(df_analisis[var_num4], kde=False, ax=axes[0], bins=15)
                axes[0].set_title(f'Histograma de {var_num4} (Filt.)')
                sns.boxplot(x=df_analisis[var_num4], ax=axes[1])
                axes[1].set_title(f'Boxplot de {var_num4} (Filt.)')
                sns.kdeplot(df_analisis[var_num4], fill=True, ax=axes[2])
                axes[2].set_title(f'Densidad de {var_num4} (Filt.)')
                plt.tight_layout()
                st.pyplot(fig)
                figuras.append(fig) # <-- GUARDAR OBJETO FIGURA
            except Exception as e:
                st.error(f"Error al generar gráficos descriptivos (filtrados) para {var_num4}: {e}")
        else:
            resultados += "No hay datos numéricos para graficar después del filtro.\n"

    # === Opción 5: Correlación Múltiple Numérica ===
    elif opcion == '5':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables numéricas relevantes.\n"
            return resultados, figuras
        resultados += f"**Análisis de Correlación Múltiple**\n"
        st.write(f"**Variables consideradas:** {vars_relevantes}")
        df_corr = df_analisis[vars_relevantes].dropna()

        if len(df_corr) > 1 and len(df_corr.columns) >= 2:
            correlacion = df_corr.corr()
            resultados += "Matriz de correlación:\n"
            # Mostrar matriz redondeada en la app para legibilidad
            st.dataframe(correlacion.style.format("{:.2f}").background_gradient(cmap='coolwarm', axis=None))
            resultados += correlacion.to_string() + "\n\n" # Añadir versión texto para IA

            try:
                # 1. Heatmap
                fig_h_height = max(5, len(vars_relevantes) * 0.6)
                fig_h_width = max(6, len(vars_relevantes) * 0.7)
                fig_h, ax_h = plt.subplots(figsize=(fig_h_width, fig_h_height))
                sns.heatmap(correlacion, annot=True, fmt='.2f', cmap='coolwarm', ax=ax_h, annot_kws={"size": 8})
                ax_h.set_title('Mapa de Calor de Correlación')
                plt.xticks(rotation=45, ha='right', fontsize=8)
                plt.yticks(rotation=0, fontsize=8)
                plt.tight_layout()
                st.pyplot(fig_h)
                figuras.append(fig_h) # <-- GUARDAR OBJETO FIGURA

                # 2. Pairplot (si no son demasiadas variables)
                pairplot_limit = 7 # Aumentar límite ligeramente
                if len(vars_relevantes) <= pairplot_limit:
                    st.write("Generando matriz de dispersión (pairplot)...")
                    try:
                         fig_p = sns.pairplot(df_corr, corner=True, diag_kind='kde') # Añadir KDE en diagonal
                         fig_p.fig.suptitle('Matriz de Dispersión (Pairplot)', y=1.02)
                         st.pyplot(fig_p)
                         figuras.append(fig_p.fig) # <-- GUARDAR OBJETO FIGURA (fig_p.fig)
                    except Exception as e_p:
                         st.warning(f"No se pudo generar el pairplot: {e_p}")
                else:
                    st.info(f"Se omite la matriz de dispersión (pairplot) por haber más de {pairplot_limit} variables.")

            except Exception as e:
                st.error(f"Error al generar gráficos de correlación: {e}")
        else:
            resultados += "No hay suficientes datos/variables para calcular la matriz de correlación.\n"

    # === Opción 6: Regresión Simple ===
    elif opcion == '6':
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'numérica', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables numéricas relevantes.\n"
            return resultados, figuras
        var_x = vars_relevantes[0] # Independiente
        var_y = vars_relevantes[1] # Dependiente
        # ... (resto lógica opción 6) ...
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
                # ... (resultados texto) ...
                resultados += f"\n**Resultados del Modelo:**\n"
                resultados += f"- R²: {r_sq:.4f}\n- Intercepto: {intercepto:.4f}\n- Pendiente: {pendiente:.4f}\n"
                resultados += f"- Ecuación: {var_y} ≈ {pendiente:.4f} * {var_x} + {intercepto:.4f}\n"

                # Gráficos
                fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
                sns.regplot(x=var_x, y=var_y, data=df_reg, ax=axes[0], line_kws={"color": "red"})
                axes[0].set_title(f'Regresión: {var_y} vs {var_x}')
                predichos = modelo.predict(X)
                residuales = y - predichos
                sns.scatterplot(x=predichos, y=residuales, ax=axes[1])
                axes[1].axhline(0, color='red', linestyle='--')
                axes[1].set_title('Residuales vs. Predichos')
                sns.histplot(residuales, kde=True, ax=axes[2])
                axes[2].set_title('Distribución de Residuales')
                plt.tight_layout()
                st.pyplot(fig)
                figuras.append(fig) # <-- GUARDAR OBJETO FIGURA
            except Exception as e:
                st.error(f"Error durante el análisis de regresión: {e}")
                resultados += f"\nError durante el análisis: {e}\n"
        else:
            resultados += "\nNo hay suficientes datos para realizar la regresión.\n"

    # === Opción 7: Contingencia + Chi² (CON LABELS) ===
    elif opcion == '7':
        resultados += "**Análisis de Asociación (Tabla de Contingencia y Chi²)**\n"
        vars_relevantes = obtener_variables_relevantes(pregunta_usuario, 'todas', df_analisis)
        if len(vars_relevantes) < 2:
            resultados += "Se necesitan al menos dos variables relevantes.\n"
            return resultados, figuras
        var1 = vars_relevantes[0]
        var2 = vars_relevantes[1]
        resultados += f"Variables analizadas: **{var1}** y **{var2}**\n"
        serie1 = df_analisis[var1].copy()
        serie2 = df_analisis[var2].copy()

        def agrupar_numerica(s, n_bins=5):
            # Solo agrupar si es numérica y tiene suficientes valores únicos
            if pd.api.types.is_numeric_dtype(s) and s.nunique() > n_bins * 1.5:
                 try:
                     s_clean = s.dropna()
                     if s_clean.empty: return s # No agrupar si solo hay NaNs
                     # Usar qcut para intentar tener bins más equilibrados
                     return pd.qcut(s, q=n_bins, labels=False, duplicates='drop').astype(str) + "_bin"
                 except Exception as e:
                     st.warning(f"No se pudo agrupar (qcut) '{s.name}': {e}. Intentando cut...")
                     try: # Fallback a cut normal
                         bins = pd.cut(s, bins=n_bins, retbins=True, duplicates='drop')[1]
                         labels = [f'{bins[i]:.1f}-{bins[i+1]:.1f}' for i in range(len(bins)-1)]
                         return pd.cut(s, bins=bins, labels=labels, include_lowest=True)
                     except Exception as e2:
                          st.warning(f"Tampoco se pudo agrupar (cut) '{s.name}': {e2}. Usando como categórica si es posible.")
                          return s.astype(str) # Tratar como categórica si falla
            return s # Devolver original si no es numérica o tiene pocos únicos

        serie1_proc = agrupar_numerica(serie1).fillna("NaN").astype(str) # Convertir a str para crosstab
        serie2_proc = agrupar_numerica(serie2).fillna("NaN").astype(str) # Convertir a str para crosstab

        labels1 = get_label_map(var1)
        labels2 = get_label_map(var2)

        try:
            crosstab = pd.crosstab(serie1_proc, serie2_proc)
            # Eliminar fila/columna 'NaN' si existe y es pequeña
            if "NaN" in crosstab.index and crosstab.loc["NaN"].sum() < len(df_analisis)*0.05: crosstab = crosstab.drop("NaN", axis=0)
            if "NaN" in crosstab.columns and crosstab["NaN"].sum() < len(df_analisis)*0.05: crosstab = crosstab.drop("NaN", axis=1)

            if crosstab.empty:
                 resultados += "Tabla de contingencia vacía después de procesar.\n"
                 return resultados, figuras

            index_name = var1
            columns_name = var2
            # Intentar aplicar labels (si los originales eran numéricos)
            # Esta parte es heurística, puede fallar si el binning cambió mucho los valores
            try:
                 if labels1 and all(idx.endswith('_bin') or idx.replace('.','',1).isdigit() for idx in crosstab.index if idx != "NaN"):
                     # Asumiendo que los números originales antes de binning podrían mapearse
                     # Es complejo mapear bins a labels originales, mejor mostrar bins
                     index_name = f"{var1} (Agrupado)" # Indicar que se agrupó
                 elif labels1 and pd.api.types.is_numeric_dtype(df_analisis[var1]): # Si era numérico sin agrupar
                     numeric_index = pd.to_numeric(crosstab.index, errors='coerce')
                     crosstab.index = pd.Series(numeric_index).map(labels1).fillna(crosstab.index)
                     index_name = f"{var1} (Etiquetas)"
                 elif isinstance(df_analisis[var1].dtype, pd.CategoricalDtype):
                     crosstab.index = crosstab.index.astype(str) # Asegurar string

                 if labels2 and all(col.endswith('_bin') or col.replace('.','',1).isdigit() for col in crosstab.columns if col != "NaN"):
                     columns_name = f"{var2} (Agrupado)"
                 elif labels2 and pd.api.types.is_numeric_dtype(df_analisis[var2]):
                     numeric_cols = pd.to_numeric(crosstab.columns, errors='coerce')
                     crosstab.columns = pd.Series(numeric_cols).map(labels2).fillna(crosstab.columns)
                     columns_name = f"{var2} (Etiquetas)"
                 elif isinstance(df_analisis[var2].dtype, pd.CategoricalDtype):
                     crosstab.columns = crosstab.columns.astype(str)

            except Exception as e_label:
                 st.warning(f"No se pudieron aplicar labels a la tabla de contingencia: {e_label}")

            crosstab.index.name = index_name
            crosstab.columns.name = columns_name

            resultados += f"\n**Tabla de Contingencia:**\n{crosstab.to_string()}\n"
            st.dataframe(crosstab) # Mostrar tabla interactiva

            # Test Chi-cuadrado
            if crosstab.size > 1 and crosstab.shape[0] > 1 and crosstab.shape[1] > 1:
                # ... (lógica Chi², igual que antes) ...
                 try:
                    chi2_stat, p_val, dof, expected = chi2_contingency(crosstab)
                    resultados += f"\n**Prueba Chi-cuadrado:**\n"
                    resultados += f"- Chi²: {chi2_stat:.3f}, p-valor: {p_val:.4f}, gl: {dof}\n"
                    alpha = 0.05
                    if p_val < alpha:
                        resultados += f"- Conclusión: Asociación significativa (p < {alpha}).\n"
                    else:
                        resultados += f"- Conclusión: No hay evidencia de asociación significativa (p >= {alpha}).\n"
                 except ValueError as ve:
                     resultados += f"\nNo se pudo realizar Chi² (puede haber ceros): {ve}\n"
                 except Exception as e_chi:
                     resultados += f"\nError en prueba Chi²: {e_chi}\n"
            else:
                resultados += "\nNo se puede realizar Chi² (tabla inválida).\n"

            # Gráfico Heatmap
            try:
                 fig_ct_h = max(4, crosstab.shape[0]*0.4)
                 fig_ct_w = max(6, crosstab.shape[1]*0.6)
                 fig_ct, ax_ct = plt.subplots(figsize=(fig_ct_w, fig_ct_h))
                 sns.heatmap(crosstab, annot=True, fmt='d', cmap='Blues', ax=ax_ct, annot_kws={"size": 8})
                 ax_ct.set_title(f'Tabla: {index_name} vs {columns_name}', fontsize=10)
                 plt.xticks(rotation=45, ha='right', fontsize=8)
                 plt.yticks(rotation=0, fontsize=8)
                 plt.tight_layout()
                 st.pyplot(fig_ct)
                 figuras.append(fig_ct) # <-- GUARDAR OBJETO FIGURA
            except Exception as e_plot:
                 st.error(f"Error al graficar tabla de contingencia: {e_plot}")

        except Exception as e_cross:
            st.error(f"Error al crear la tabla de contingencia: {e_cross}")
            resultados += f"\nError al crear la tabla: {e_cross}\n"

    else:
        resultados += f"Opción de análisis '{opcion}' no implementada.\n"

    # Devolver texto y lista de OBJETOS de figura
    return resultados, figuras


# --- Función mostrar_resumen_base_datos (igual) ---
def mostrar_resumen_base_datos():
    # ... (texto igual que antes) ...
    resumen = """
Esta aplicación está diseñada para ayudarte a explorar y analizar datos relacionados con el bienestar laboral y la salud mental en el entorno de trabajo. Utiliza una base de datos rica en información sociodemográfica, laboral y en diversas dimensiones de bienestar y salud mental para proporcionarte análisis personalizados y valiosos insights.

**¿Cómo utilizar la aplicación?**
1.  **Filtra por Fecha y Empresa (Opcional):** Selecciona el rango de fechas y, si lo deseas, ingresa el ID de la empresa para enfocar el análisis.
2.  **Genera un Informe General:** Haz clic en "🚀 Generar Informe General" para obtener una visión global del bienestar en el periodo/empresa seleccionada, incluyendo un semáforo de dimensiones y comparaciones por grupos demográficos.
3.  **O Realiza un Análisis Específico:**
    *   Ve a la pestaña "❓ Análisis Específico".
    *   Formula tu pregunta de investigación en el campo "Tu Pregunta:". *(Ej: "¿Cómo afecta el número de horas de trabajo semanal al nivel de estrés?")*
    *   Aplica filtros adicionales si es necesario en "Filtros Adicionales". *(Ej: "empleados con más de 5 años de experiencia")*
    *   Haz clic en "🔍 Realizar Análisis Específico". La IA interpretará tu pregunta, seleccionará el método adecuado y te mostrará los resultados y gráficos.
4.  **Explora y Descarga:** Visualiza los resultados y descarga el informe completo en PDF usando los botones "📥 Descargar Informe...".

**Resumen de la Base de Datos (Basado en `cleaned_data.csv`):**

La base de datos contiene información sobre salud psicológica en el trabajo. Los datos han sido pre-procesados, y las escalas Likert se encuentran mayormente como valores numéricos (enteros). **Es crucial verificar que los nombres de las variables en el diccionario interno coincidan con los nombres exactos de las columnas en el archivo CSV.**

**Principales categorías y variables:**
... (resto del resumen como antes, asegurar que los nombres mencionados sean los correctos del CSV/diccionario) ...

**Ejemplos de preguntas:**

*   ¿Cuál es la distribución de la **Satisfacción** (numérica) entre diferentes **Cargos** (categórica)? (Opción 1 o 4)
*   ¿Existe correlación entre **Edad** y **Síntomas de Burnout** (ambas numéricas)? (Opción 3 o 5)
*   ¿Cómo afecta el **Tipo de modalidad de trabajo** (categórica) a la percepción de **Control del Tiempo** (numérica)? (Opción 7 o análisis de medias por grupo)

Por favor, realiza tu pregunta teniendo en cuenta las variables y dimensiones disponibles.
    """
    st.markdown(resumen)


######################################################
# CLASE PDFReport y funciones de limpieza (Corrección I/O Error)
######################################################
class PDFReport:
    def __init__(self, filename):
        self.filename = filename
        self.elements = []
        self.styles = getSampleStyleSheet()
        # Ajustar márgenes para dar más espacio
        self.doc = SimpleDocTemplate(
            self.filename,
            pagesize=A4,
            rightMargin=12*mm,
            leftMargin=12*mm,
            topMargin=45*mm, # Reducir si el header es más pequeño
            bottomMargin=18*mm
        )
        # Estilos personalizados (ajustar tamaños si es necesario)
        self.styles.add(ParagraphStyle(name='CustomTitle', parent=self.styles['h1'], fontSize=16, alignment=1))
        self.styles.add(ParagraphStyle(name='CustomHeading', parent=self.styles['h2'], fontSize=12, spaceBefore=10))
        self.styles.add(ParagraphStyle(name='CustomBodyText', parent=self.styles['Normal'], fontSize=10, leading=12, alignment=4)) # Justificado
        self.styles.add(ParagraphStyle(name='CustomCode', parent=self.styles['Code'], fontSize=8, leading=10, backColor=colors.whitesmoke, borderPadding=3, leftIndent=6, rightIndent=6))
        self.styles.add(ParagraphStyle(name='CustomFooter', parent=self.styles['Normal'], fontSize=8, alignment=2, textColor=colors.grey)) # Derecha

    def header(self, canvas, doc):
        canvas.saveState()
        try:
            header_image = 'Captura de pantalla 2024-11-25 a la(s) 9.02.19 a.m..png'
            if os.path.isfile(header_image):
                 img_width, img_height = 210*mm, 35*mm # Ajustar altura
                 # Anclar en top-left (adjust y-coordinate)
                 canvas.drawImage(header_image, 0, A4[1] - img_height, width=img_width, height=img_height, preserveAspectRatio=True, anchor='n')
            else:
                 canvas.setFont('Helvetica-Bold', 14)
                 canvas.drawCentredString(A4[0]/2.0, A4[1] - 20*mm, clean_text("Informe de Análisis"))
        except Exception as e:
            print(f"Error al dibujar header: {e}")
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(A4[0]/2.0, A4[1] - 20*mm, clean_text("Informe de Análisis"))

        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(12*mm, A4[1] - 40*mm, A4[0] - 12*mm, A4[1] - 40*mm) # Línea debajo
        canvas.restoreState()

    def footer(self, canvas, doc):
        canvas.saveState()
        footer_text = f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Página {doc.page}"
        p = Paragraph(footer_text, self.styles['CustomFooter'])
        w, h = p.wrap(doc.width, doc.bottomMargin)
        p.drawOn(canvas, doc.leftMargin, h) # Dibujar en la parte inferior
        canvas.restoreState()

    def header_footer(self, canvas, doc):
        self.header(canvas, doc)
        self.footer(canvas, doc)

    def add_paragraph(self, text, style='CustomBodyText'):
        text = clean_text(text)
        p = Paragraph(text, self.styles[style])
        self.elements.append(p)
        self.elements.append(Spacer(1, 3))

    def add_title(self, text, level=1):
         text = clean_text(text)
         style = 'CustomTitle' if level == 1 else 'CustomHeading'
         p = Paragraph(text, self.styles[style])
         self.elements.append(p)
         self.elements.append(Spacer(1, 4))

    def add_markdown(self, md_text):
        md_text = clean_text(md_text) # Limpiar primero
        # Usar expresiones regulares simples para convertir Markdown básico
        # Esto es menos robusto que BeautifulSoup pero evita dependencias extras si es simple
        lines = md_text.split('\n')
        in_code_block = False
        code_buffer = []

        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('```'):
                 if in_code_block:
                      # Fin de bloque de código
                      code_text = "\n".join(code_buffer)
                      # Usar html.escape para asegurar que no se interprete como HTML
                      import html
                      escaped_code = html.escape(code_text)
                      p = Paragraph(f"<pre>{escaped_code}</pre>", self.styles['CustomCode'])
                      self.elements.append(p)
                      self.elements.append(Spacer(1, 4))
                      code_buffer = []
                      in_code_block = False
                 else:
                      # Inicio de bloque de código
                      in_code_block = True
                 continue # Saltar la línea ```

            if in_code_block:
                 code_buffer.append(line) # No limpiar líneas dentro de code block
                 continue

            # Fuera de bloque de código
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') # Escapar HTML básico
            style = 'CustomBodyText'
            prefix = ""
            if stripped_line.startswith('# '):
                style = 'CustomTitle'
                line = line[2:]
            elif stripped_line.startswith('## '):
                style = 'CustomHeading'
                line = line[3:]
            elif stripped_line.startswith('### '):
                 style = 'CustomHeading' # Podríamos tener h3, etc.
                 line = line[4:]
            elif stripped_line.startswith('* ') or stripped_line.startswith('- '):
                 prefix = "•  " # Bullet point
                 line = line[2:]
            elif re.match(r'^\d+\.\s', stripped_line): # Lista numerada
                 match = re.match(r'^(\d+\.)\s', stripped_line)
                 prefix = match.group(1) + " "
                 line = line[len(match.group(0)):]

            # Formato inline simple
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line) # Negrita
            line = re.sub(r'__(.*?)__', r'<b>\1</b>', line) # Negrita
            line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line) # Cursiva
            line = re.sub(r'_(.*?)_', r'<i>\1</i>', line) # Cursiva
            line = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', line) # Código inline

            if line.strip(): # Solo añadir si la línea tiene contenido después de procesar
                p = Paragraph(prefix + line, self.styles[style])
                self.elements.append(p)
                # Añadir spacer menor después de texto normal/listas
                if style == 'CustomBodyText':
                     self.elements.append(Spacer(1, 2))


    def insert_image(self, image_path_or_fig, max_width_mm=170, max_height_mm=180): # Reducir altura max
        """
        Inserta imagen desde archivo o figura Matplotlib.
        CORREGIDO: Siempre guarda figura en archivo temporal.
        """
        temp_file_to_delete = None
        img_path_to_use = None

        try:
            if isinstance(image_path_or_fig, str) and os.path.isfile(image_path_or_fig):
                img_path_to_use = image_path_or_fig
                # st.write(f"DEBUG PDF: Usando archivo de imagen existente: {img_path_to_use}")
            elif hasattr(image_path_or_fig, 'savefig'): # Es una figura Matplotlib
                # Crear un nombre de archivo temporal único
                temp_dir = "temp_pdf_images"
                os.makedirs(temp_dir, exist_ok=True) # Crear directorio si no existe
                temp_img_path = os.path.join(temp_dir, f"temp_fig_{random.randint(10000, 99999)}.png")

                # Guardar la figura en el archivo temporal
                image_path_or_fig.savefig(temp_img_path, format='png', dpi=150, bbox_inches='tight') # DPI más bajo para PDF
                img_path_to_use = temp_img_path
                temp_file_to_delete = temp_img_path
                # st.write(f"DEBUG PDF: Figura guardada temporalmente en: {img_path_to_use}")
            else:
                 self.add_paragraph(f"Error: Imagen no válida ({type(image_path_or_fig)})", style='CustomCode')
                 return

            if not img_path_to_use or not os.path.isfile(img_path_to_use):
                 raise FileNotFoundError(f"Archivo de imagen no encontrado o no creado: {img_path_to_use}")

            # Usar PIL para obtener dimensiones y calcular nuevo tamaño
            with PILImage.open(img_path_to_use) as pil_img:
                orig_width_px, orig_height_px = pil_img.size

            if orig_width_px == 0 or orig_height_px == 0:
                raise ValueError("Dimensiones de imagen inválidas (0).")

            max_width_pt = max_width_mm * mm
            max_height_pt = max_height_mm * mm

            ratio = float(orig_height_px) / float(orig_width_px) if orig_width_px else 1
            new_width_pt = min(max_width_pt, orig_width_px * 0.75) # Usar puntos approx
            new_height_pt = new_width_pt * ratio

            if new_height_pt > max_height_pt:
                new_height_pt = max_height_pt
                new_width_pt = new_height_pt / ratio if ratio else max_width_pt

            # Crear la imagen ReportLab DESDE EL ARCHIVO
            rl_img = RLImage(img_path_to_use, width=new_width_pt, height=new_height_pt)
            rl_img.hAlign = 'CENTER'
            self.elements.append(rl_img)
            self.elements.append(Spacer(1, 10))

        except FileNotFoundError as fnf:
             self.add_paragraph(f"Error: Archivo de imagen no encontrado: {fnf}", style='CustomCode')
             print(f"Error PDF Imagen: {fnf}")
        except Exception as e:
             error_msg = f"Error al insertar imagen: {e} (Path: {img_path_to_use})"
             self.add_paragraph(error_msg, style='CustomCode')
             print(error_msg) # Loggear error
        finally:
            # Limpiar archivo temporal SI SE CREÓ
            if temp_file_to_delete and os.path.exists(temp_file_to_delete):
                 try:
                     # Esperar un poco antes de borrar por si el SO aún lo tiene bloqueado
                     time.sleep(0.1)
                     os.remove(temp_file_to_delete)
                     # st.write(f"DEBUG PDF: Archivo temporal eliminado: {temp_file_to_delete}")
                 except PermissionError:
                     st.warning(f"No se pudo eliminar {temp_file_to_delete} (Permiso denegado). Borrar manualmente.")
                 except Exception as e_del:
                     st.warning(f"No se pudo eliminar archivo temporal {temp_file_to_delete}: {e_del}")


    def build_pdf(self):
        try:
            self.doc.build(self.elements, onFirstPage=self.header_footer, onLaterPages=self.header_footer)
            # Limpiar directorio temporal si existe y está vacío
            temp_dir = "temp_pdf_images"
            if os.path.isdir(temp_dir):
                 if not os.listdir(temp_dir): # Si está vacío
                      os.rmdir(temp_dir)
        except LayoutError as e:
            st.error(f"Error de maquetación al generar PDF: {e}")
            # ... (manejo de error simplificado como antes) ...
            raise e
        except Exception as e:
             st.error(f"Error inesperado al construir PDF: {e}")
             raise e


# --- Funciones de limpieza de texto (igual) ---
def clean_text(text):
    # ... (igual que antes) ...
    if not isinstance(text, str): text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    replacements = {'\u2013': '-', '\u2014': '--', '\u2018': "'", '\u2019': "'", '\u201C': '"', '\u201D': '"', '\u2022': '* ', '\u00A0': ' '}
    for char, replacement in replacements.items(): text = text.replace(char, replacement)
    try: text = text.encode('latin-1', 'ignore').decode('latin-1')
    except Exception:
         try: text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
         except Exception as e: print(f"Advertencia: No se pudo limpiar texto: {e}")
    return text


# --- Función generar_informe (PDF específico, igual) ---
def generar_informe(pregunta_usuario, opcion_analisis, resultados_texto, figuras):
    pdf = PDFReport('informe_analisis_datos.pdf')
    pdf.add_title('Informe de Análisis Específico')
    pdf.add_title('1. Pregunta y Metodología', level=2)
    pdf.add_paragraph(f"**Pregunta:** {pregunta_usuario}")
    opcion_desc = f"Opción {opcion_analisis}"
    match = re.search(rf"{opcion_analisis}\.\s*\*\*(.*?)\*\*", opciones_analisis, re.DOTALL)
    if match: opcion_desc = f"Opción {opcion_analisis}: {match.group(1).strip()}"
    pdf.add_paragraph(f"**Método:** {opcion_desc}")
    filtro_match = re.search(r"Aplicando filtro: `(.*?)`", resultados_texto)
    if filtro_match: pdf.add_paragraph(f"**Filtros:** {filtro_match.group(1)}")

    pdf.add_title('2. Resultados', level=2)
    # Separar texto de tablas si es posible (simple heuristic)
    parts = re.split(r"(\n(?:Frecuencias|Estadísticas|Matriz de correlación|Tabla de Contingencia):?\n)", resultados_texto, flags=re.IGNORECASE)
    for i, part in enumerate(parts):
         if i % 2 == 1: # Es el título de la tabla/sección
              pdf.add_paragraph(f"**{part.strip()}**", style='CustomHeading')
         elif part.strip():
              # Si parece una tabla (muchos espacios/columnas), usar estilo código
              if len(part.split('\n')) > 2 and all(len(row.split()) > 2 for row in part.split('\n')[:3]):
                   pdf.add_paragraph(f"<pre>{clean_text(part)}</pre>", style='CustomCode')
              else:
                   pdf.add_markdown(part) # Usar markdown para el resto

    if figuras:
        pdf.add_title('3. Visualizaciones', level=2)
        for idx, fig in enumerate(figuras):
            # No tenemos títulos aquí, solo numerar
            pdf.add_paragraph(f"**Gráfico {idx + 1}**", style='CustomHeading')
            pdf.insert_image(fig) # Pasa el objeto figura

    pdf.add_title('4. Interpretación y Conclusiones (IA)', level=2)
    prompt_interpretacion = f"""
    Pregunta: {pregunta_usuario}
    Método (Opción {opcion_analisis}): {opcion_desc}
    Resultados:
    {resultados_texto}

    Diccionario: {data_dictionary}
    Labels: {label_maps}

    Genera una interpretación clara de los resultados y gráficos (si hubo). Explica qué significan los hallazgos en contexto. Proporciona 2-3 conclusiones clave y 1-2 recomendaciones prácticas (psicología organizacional). Usa formato Markdown. Si hubo errores o no hay datos, explícalo.
    """
    interpretacion_ia = enviar_prompt(prompt_interpretacion)
    if "Error" in interpretacion_ia:
        pdf.add_paragraph("No se pudo generar la interpretación automáticamente.")
    else:
        pdf.add_markdown(interpretacion_ia)

    try:
        pdf.build_pdf()
        st.success(f"Informe específico generado: {pdf.filename}")
        return pdf.filename
    except Exception as e:
        st.error(f"Error final al generar el PDF específico: {e}")
        return None


# --- Función generar_informe_general (AJUSTADA con Fuzzy Match y corrección 'ha') ---
def generar_informe_general(df_original, fecha_inicio, fecha_fin):
    df_informe = df_original.copy()
    if df_informe.empty:
        return "No hay datos para generar el informe general.", [], []

    st.write(f"DEBUG - Generando informe general con {df_informe.shape[0]} filas.")
    columnas_numericas_ok = []
    mapa_dim_cols = {} # dim_name -> [lista de cols con prefijo válidas]

    st.write("--- Validando columnas numéricas para dimensiones (BUSCANDO PREFIJOS EXACTOS) ---")
    columnas_df = df_informe.columns.tolist()

    bm_dims = data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {})
    for dim_name, dim_details in bm_dims.items():
        cols_candidatas_dict_prefixed = dim_details.get("Preguntas", []) # Nombres con prefijo
        cols_validas_para_dim = []

        for col_prefixed in cols_candidatas_dict_prefixed:
            col_prefixed_clean = col_prefixed.strip()

            # BUSCAR COINCIDENCIA EXACTA
            if col_prefixed_clean in columnas_df:
                actual_col_name_in_df = col_prefixed_clean
                # Validar si es numérico y tiene datos
                if pd.api.types.is_numeric_dtype(df_informe[actual_col_name_in_df]):
                    if df_informe[actual_col_name_in_df].notna().any():
                        cols_validas_para_dim.append(actual_col_name_in_df)
                        if actual_col_name_in_df not in columnas_numericas_ok:
                             columnas_numericas_ok.append(actual_col_name_in_df)
                    # else: # Numérico pero solo NaNs (ignorar)
                else:
                    st.error(f"¡ERROR! [{dim_name}]: Columna '{actual_col_name_in_df}' encontrada pero NO numérica ({df_informe[actual_col_name_in_df].dtype}). ¡Revisar!")
            else: # No se encontró la columna exacta del diccionario en el DF
                 st.warning(f"INFO [{dim_name}]: Columna '{col_prefixed_clean}' del diccionario no encontrada EXACTAMENTE en CSV.")
                 pass # Ignorar si no hay match exacto

        if cols_validas_para_dim:
            mapa_dim_cols[dim_name] = cols_validas_para_dim
            # st.write(f"OK [{dim_name}]: Columnas válidas encontradas: {len(cols_validas_para_dim)}")
        else:
             st.warning(f"SKIP [{dim_name}]: No se encontraron columnas numéricas válidas EXACTAS en el CSV para esta dimensión.")


    if not mapa_dim_cols:
        st.error("Error Fatal: No se encontraron columnas numéricas válidas para NINGUNA dimensión (verificar nombres exactos con prefijos en CSV y Diccionario).")
        return "Error: No hay columnas válidas para análisis dimensional.", [], []

    st.write(f"DEBUG - Dimensiones con columnas válidas encontradas: {len(mapa_dim_cols)}")
    st.write(f"DEBUG - Total columnas numéricas únicas válidas: {len(columnas_numericas_ok)}")

    # --- Calcular Promedios (sin cambios) ---
    resultados_promedio = {}
    st.write("--- Calculando Promedios Dimensionales ---")
    for dim_name, cols_validas in mapa_dim_cols.items():
        try:
            promedio_dim = df_informe[cols_validas].mean(axis=0, skipna=True).mean(skipna=True)
            if pd.notna(promedio_dim):
                resultados_promedio[dim_name] = promedio_dim
                n_promedio = df_informe[cols_validas].count().mean()
                st.write(f"OK: Promedio '{dim_name}': {promedio_dim:.2f} (N~{n_promedio:.0f})")
        except Exception as e:
            st.error(f"ERROR promedio '{dim_name}': {e}")

    if not resultados_promedio:
        st.error("Error Fatal: No se pudo calcular promedio para ninguna dimensión.")
        return "Error: No se calcularon promedios.", [], []

    # --- Clasificar Fortalezas, Riesgos, etc. (sin cambios) ---
    inverse_dims = { # Asegúrate que los NOMBRES DE DIMENSIÓN aquí sean correctos
        "Conflicto Familia-Trabajo": True, "Síntomas de Burnout": True,
        "Factores de Efectos Colaterales (Escala de Desgaste)": True,
        "Factores de Efectos Colaterales (Escala de Alienación)": True,
        "Intención de Retiro": True,
        "Factores de Efectos Colaterales (Escala de Somatización)": True,
    }
    def get_scale_range(dim_name):
        details = data_dictionary.get("Dimensiones de Bienestar y Salud Mental", {}).get(dim_name, {})
        escala = details.get("Escala", {})
        if escala and isinstance(escala, dict):
            vals = [k for k in escala.keys() if isinstance(k, (int, float))]
            if vals: return min(vals), max(vals)
        if "Burnout" in dim_name: return 1, 5
        if any(s in dim_name for s in ["Compromiso", "Defensa", "Satisfacción", "Retiro"]): return 1, 6
        return 1, 7 # Default

    def estado_dimension(valor, dim_name):
        if pd.isna(valor): return ('Sin Datos', 'grey')
        min_esc, max_esc = get_scale_range(dim_name)
        rango = max_esc - min_esc; midpoint = (min_esc + max_esc) / 2.0
        if rango <= 0: return ('Rango Inválido', 'grey')
        umbral_riesgo = min_esc + rango / 3.0
        umbral_fortaleza = max_esc - rango / 3.0
        val_int = (max_esc + min_esc) - valor if inverse_dims.get(dim_name, False) else valor
        if val_int >= umbral_fortaleza: return ('Fortaleza', 'green')
        elif val_int <= umbral_riesgo: return ('Riesgo', 'red')
        else: return ('Intermedio', 'yellow')

    fortalezas, riesgos, intermedios, sin_datos = [], [], [], []
    # ... (loop de clasificación igual) ...
    for dim, val in resultados_promedio.items():
        estado, _ = estado_dimension(val, dim)
        entry = (dim, val)
        if estado == 'Fortaleza': fortalezas.append(entry)
        elif estado == 'Riesgo': riesgos.append(entry)
        elif estado == 'Intermedio': intermedios.append(entry)
        else: sin_datos.append(entry)
    fortalezas.sort(key=lambda x: x[1], reverse=True); riesgos.sort(key=lambda x: x[1]); intermedios.sort(key=lambda x: x[1])


    # --- Generar Textos Gemini (sin cambios) ---
    try:
        prompt_resumen = f"""... (prompt igual) ..."""
        resumen_ejecutivo = enviar_prompt(prompt_resumen)
        prompt_conclusiones = f"""... (prompt igual) ..."""
        conclusiones_recomendaciones = enviar_prompt(prompt_conclusiones)
        if "Error" in resumen_ejecutivo or "Error" in conclusiones_recomendaciones: raise Exception("Error Gemini")
    except Exception as e:
        # ... (manejo de error igual) ...
        resumen_ejecutivo = "Error generando resumen."; conclusiones_recomendaciones = "Error generando conclusiones."


    # --- Generar Gráficos (sin cambios en la lógica principal, usa cols encontradas) ---
    figuras_informe = []
    fig_titles = []
    # --- Gráfico Semáforo ---
    st.write("--- Generando Gráfico Semáforo ---")
    try:
        # ... (código semáforo igual, usa resultados_promedio) ...
        dims_list = list(resultados_promedio.items())
        if dims_list:
             # ... (crear subplots, iterar, colorear, añadir texto, etc.) ...
             # Asegurar que se guarda el objeto figura
             figuras_informe.append(fig_semaforo)
             fig_titles.append("Figura 1: Semáforo de Dimensiones")
             st.pyplot(fig_semaforo)
    except Exception as e: st.error(f"Error Semáforo: {e}")

    # --- Gráficos por Grupo ---
    st.write("--- Generando Gráficos Comparativos ---")
    df_plot_groups = df_informe.copy()
    grupos = {}
    # ... (definición de grupos Sexo, Rango Edad, Tiene Hijos igual) ...
    col_sexo = '(SD)Sexo'; # Usar nombre con prefijo
    if col_sexo in df_plot_groups and df_plot_groups[col_sexo].nunique() > 1: grupos['Sexo'] = col_sexo
    col_edad = '(SD)Edad'; col_rango_edad = 'Rango_Edad'
    if col_edad in df_plot_groups and pd.api.types.is_numeric_dtype(df_plot_groups[col_edad]):
        try: # ... (código cut Rango Edad igual) ...
            max_edad=df_plot_groups[col_edad].max(); bins=[0,24,34,44,54,64,max(65,max_edad+1)]; labels=['<25','25-34','35-44','45-54','55-64','65+']
            df_plot_groups[col_rango_edad]=pd.cut(df_plot_groups[col_edad],bins=bins,labels=labels[:len(bins)-1],right=False,duplicates='drop')
            if df_plot_groups[col_rango_edad].nunique() > 1: grupos['Rango Edad'] = col_rango_edad
        except Exception as e_edad: st.warning(f"No se pudo crear Rango Edad: {e_edad}")
    col_hijos = '(SD)Numero de hijos'; col_tiene_hijos = 'Tiene_Hijos'
    if col_hijos in df_plot_groups and pd.api.types.is_numeric_dtype(df_plot_groups[col_hijos]):
        df_plot_groups[col_tiene_hijos] = np.where(df_plot_groups[col_hijos].fillna(-1)>0,'Con hijos','Sin hijos').astype('category')
        if df_plot_groups[col_tiene_hijos].nunique() > 1: grupos['Tiene Hijos'] = col_tiene_hijos


    fig_idx_start = 2
    for i, (dim_name, prom_general) in enumerate(resultados_promedio.items()):
        if dim_name not in mapa_dim_cols: continue # Saltar si no se encontraron cols
        cols_validas_dim = mapa_dim_cols[dim_name]
        min_esc, max_esc = get_scale_range(dim_name)
        if not grupos: continue

        n_grupos = len(grupos)
        fig_dim, axs_dim = plt.subplots(1, n_grupos, figsize=(n_grupos * 4.5, 4.0), sharey=True)
        if n_grupos == 1: axs_dim = [axs_dim]
        fig_dim.suptitle(f"Comparación: {dim_name}\n(General: {prom_general:.2f})", fontsize=10, y=1.03)
        plot_count = 0
        for k, (grupo_label, grupo_col) in enumerate(grupos.items()):
            ax = axs_dim[k]
            try:
                # Groupby usa cols_validas_dim (que tienen prefijo)
                grouped = df_plot_groups.groupby(grupo_col, observed=False)[cols_validas_dim].mean(numeric_only=True).mean(axis=1, skipna=True).dropna()
                if not grouped.empty:
                    # ... (plot, títulos, etiquetas, etc. igual que antes, SIN 'ha' en tick_params) ...
                    colors = plt.get_cmap('viridis')(np.linspace(0,1,len(grouped)))
                    bars = grouped.plot(kind='bar',color=colors,ax=ax,width=0.8)
                    ax.set_title(f"Por {grupo_label}", fontsize=9); ax.set_xlabel('')
                    if k==0: ax.set_ylabel('Promedio Dimensión')
                    ax.tick_params(axis='x', rotation=45, labelsize=8) # SIN ha='right'
                    ax.grid(axis='y', linestyle='--', alpha=0.6)
                    ax.set_ylim(bottom=min_esc-(max_esc-min_esc)*0.05, top=max_esc+(max_esc-min_esc)*0.05)
                    for bar in bars.patches: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f'{bar.get_height():.2f}', ha='center', va='bottom', fontsize=7)
                    plot_count += 1
                else: ax.text(0.5,0.5,'No hay datos',ha='center',va='center',fontsize=8,color='grey'); ax.set_xticks([]); ax.set_yticks([])
            except Exception as e_grp: st.error(f"Error gráfico '{dim_name}' por '{grupo_label}': {e_grp}"); ax.text(0.5,0.5,f'Error',ha='center',va='center')

        if plot_count > 0:
            plt.tight_layout(rect=[0, 0.03, 1, 0.90])
            figuras_informe.append(fig_dim)
            fig_titles.append(f"Figura {fig_idx_start + i}: Comparación {dim_name}")
            st.pyplot(fig_dim)
        else: plt.close(fig_dim)


    # --- Ensamblar Texto Informe Final (sin cambios) ---
    informe_partes = []
    # ... (código igual para añadir título, periodo, resumen, clasificación, conclusiones) ...
    informe_texto_final = "".join(informe_partes)

    st.success("Informe general procesado.")
    return informe_texto_final, figuras_informe, fig_titles


# --- Función Main (AJUSTADA, sin set_page_config) ---
def main():
    # --- NO st.set_page_config() AQUÍ ---
    st.title("Aplicación de Análisis de Datos sobre Salud Organizacional")

    # Mostrar listado de columnas para depuración
    with st.expander("Ver Columnas Detectadas en el Archivo CSV", expanded=False):
        st.dataframe(df.columns.to_series().reset_index(drop=True), height=300)
        st.caption("Verifica que los nombres aquí coincidan con los usados en el código (diccionarios).")


    # 0) Mostrar el resumen de la base de datos
    with st.expander("Ver Resumen de la Base de Datos y Ayuda", expanded=False):
        mostrar_resumen_base_datos()

    # 1) Verificar columna de fecha (igual que antes)
    if 'Hora de inicio' not in df.columns or not pd.api.types.is_datetime64_any_dtype(df['Hora de inicio']):
        st.error("Error: La columna 'Hora de inicio' no existe o no es de tipo fecha/hora.")
        st.stop()

    # 2) Widgets Filtros (igual que antes)
    min_date = df['Hora de inicio'].min().date() if df['Hora de inicio'].notna().any() else date.today() - timedelta(days=365)
    max_date = df['Hora de inicio'].max().date() if df['Hora de inicio'].notna().any() else date.today()
    default_start = max(min_date, max_date - timedelta(days=360))
    col1, col2, col3 = st.columns(3)
    with col1: fecha_inicio = st.date_input("Fecha de inicio", value=default_start, min_value=min_date, max_value=max_date)
    with col2: fecha_fin = st.date_input("Fecha de fin", value=max_date, min_value=min_date, max_value=max_date)
    with col3: cod_empresa = st.text_input("Código Empresa (ID, opcional)")

    # 3) Filtrar DataFrame base (igual que antes)
    try:
        fecha_fin_dt = pd.to_datetime(fecha_fin) + timedelta(days=1) - timedelta(seconds=1)
        df_filtrado_base = df[
            (df['Hora de inicio'] >= pd.to_datetime(fecha_inicio)) &
            (df['Hora de inicio'] <= fecha_fin_dt)
        ].copy() # Usar .copy() para evitar SettingWithCopyWarning más adelante
        if cod_empresa.strip() and 'ID' in df_filtrado_base.columns:
            try:
                 df_filtrado_base = df_filtrado_base[df_filtrado_base['ID'].astype(str) == cod_empresa.strip()]
            except KeyError: st.warning("Columna 'ID' no encontrada.")
            except Exception as e_id: st.warning(f"No se pudo filtrar por ID: {e_id}")

        st.info(f"Se analizarán {len(df_filtrado_base)} registros entre {fecha_inicio} y {fecha_fin}" + (f" para ID '{cod_empresa}'." if cod_empresa.strip() else "."))
        # if df_filtrado_base.empty: st.warning("No hay datos con los filtros seleccionados.") # Ya no es necesario aquí

    except Exception as e_filter:
        st.error(f"Error al aplicar filtros iniciales: {e_filter}")
        st.stop()

    # Tabs (igual que antes)
    tab1, tab2 = st.tabs(["📊 Informe General", "❓ Análisis Específico"])

    # --- TAB 1: Informe General (igual que antes) ---
    with tab1:
        st.subheader("Informe General de Bienestar")
        st.write("Genera un resumen del estado de bienestar para el periodo y empresa seleccionados.")
        if st.button("🚀 Generar Informe General"):
            if df_filtrado_base.empty:
                 st.warning("No hay datos para generar el informe con los filtros actuales.")
            else:
                 with st.spinner("Generando informe general... Por favor espera."):
                     informe_texto, figuras, fig_titulos = generar_informe_general(df_filtrado_base, fecha_inicio, fecha_fin)

                     if "Error" in informe_texto:
                         st.error(informe_texto)
                     else:
                         with st.expander("Ver Texto del Informe General", expanded=False):
                             st.markdown(informe_texto)

                         st.write("Construyendo PDF del informe general...")
                         pdf_general = PDFReport('informe_general.pdf')
                         pdf_general.add_markdown(informe_texto) # Usar markdown
                         pdf_general.add_title("Visualizaciones", level=2)
                         for fig, title in zip(figuras, fig_titulos):
                              pdf_general.add_paragraph(f"**{title}**", style='CustomHeading')
                              pdf_general.insert_image(fig) # Pasa el objeto figura

                         try:
                             pdf_general.build_pdf()
                             st.success("Informe general en PDF generado.")
                             with open('informe_general.pdf', 'rb') as f:
                                 st.download_button("📥 Descargar Informe General PDF", f, "informe_general.pdf", "application/pdf")
                         except Exception as e_pdf_gen:
                             st.error(f"Error al construir el PDF general: {e_pdf_gen}")

    # --- TAB 2: Análisis Específico (igual que antes) ---
    with tab2:
        st.subheader("Análisis Específico Guiado por IA")
        st.write("Realiza una pregunta sobre los datos y la IA seleccionará el análisis adecuado.")

        # Estado de sesión (igual)
        if "pregunta_especifica" not in st.session_state: st.session_state.pregunta_especifica = ""
        if "filtro_especifico" not in st.session_state: st.session_state.filtro_especifico = ""
        if "analisis_especifico_realizado" not in st.session_state: st.session_state.analisis_especifico_realizado = False
        if "pdf_especifico_path" not in st.session_state: st.session_state.pdf_especifico_path = None

        if not st.session_state.analisis_especifico_realizado:
            st.session_state.pregunta_especifica = st.text_area("Tu Pregunta:", value=st.session_state.pregunta_especifica, height=100, placeholder="Ej: ¿Cuál es la relación entre edad y burnout?")
            st.session_state.filtro_especifico = st.text_input("Filtros Adicionales (opcional, natural):", value=st.session_state.filtro_especifico, placeholder="Ej: solo mujeres sector privado > 2 años antigüedad")

            if st.button("🔍 Realizar Análisis Específico"):
                 if not st.session_state.pregunta_especifica.strip():
                     st.warning("Por favor, ingresa una pregunta.")
                 elif df_filtrado_base.empty:
                      st.warning("No hay datos base con los filtros de fecha/empresa actuales.")
                 else:
                     with st.spinner('Procesando y analizando...'):
                         filtros_query = procesar_filtros(st.session_state.filtro_especifico)
                         if filtros_query: st.info(f"Filtro adicional: `{filtros_query}`")
                         opcion_sugerida = procesar_pregunta(st.session_state.pregunta_especifica)

                         if opcion_sugerida:
                              st.success(f"IA sugiere: **Opción {opcion_sugerida}**")
                              resultados_txt, figuras_list = realizar_analisis(opcion_sugerida, st.session_state.pregunta_especifica, filtros_query, df_filtrado_base)
                              st.markdown("### Resultados del Análisis:")
                              st.text_area("Resultados:", value=resultados_txt, height=250, disabled=True, key="res_txt_area") # Añadir key
                              st.write("Generando informe PDF...")
                              pdf_path = generar_informe(st.session_state.pregunta_especifica, opcion_sugerida, resultados_txt, figuras_list)
                              if pdf_path:
                                   st.session_state.pdf_especifico_path = pdf_path
                                   st.session_state.analisis_especifico_realizado = True
                                   st.rerun()
                              else: st.error("No se pudo generar el PDF.")
                         else: st.error("La IA no pudo determinar el análisis adecuado.")

        if st.session_state.analisis_especifico_realizado:
             st.success("Análisis completado y PDF generado.")
             if st.session_state.pdf_especifico_path and os.path.exists(st.session_state.pdf_especifico_path):
                  with open(st.session_state.pdf_especifico_path, 'rb') as f:
                       st.download_button("📥 Descargar Informe Específico PDF", f, os.path.basename(st.session_state.pdf_especifico_path), "application/pdf")
             else: st.warning("Archivo PDF del informe no encontrado.")
             if st.button("🔄 Realizar Otra Consulta Específica"):
                  st.session_state.analisis_especifico_realizado = False
                  st.session_state.pdf_especifico_path = None
                  # Opcional: Limpiar campos?
                  # st.session_state.pregunta_especifica = ""
                  # st.session_state.filtro_especifico = ""
                  st.rerun()

# Punto de entrada
if __name__ == "__main__":
    main()
