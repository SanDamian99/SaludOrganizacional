import os
import streamlit as st
import unicodedata
import re

# --- Environment Variables ---
def get_gemini_api_key():
    if "YOUR_API_KEY" in st.secrets:
        return st.secrets["YOUR_API_KEY"]
    return os.environ.get("GEMINI_API_KEY")

def get_supabase_url():
    if "SUPABASE_URL" in st.secrets:
        return st.secrets["SUPABASE_URL"]
    return os.environ.get("SUPABASE_URL")

def get_supabase_key():
    if "SUPABASE_KEY" in st.secrets:
        return st.secrets["SUPABASE_KEY"]
    return os.environ.get("SUPABASE_KEY")

# --- Master Data Configuration ---
MASTER_DATA_PATH = "cleaned_data - cleaned_data.csv"

# --- Data Dictionary & Configuration ---

DATA_DICTIONARY = {
   "Variables Sociodemográficas": {
       "(SD)Edad": {"Tipo": "Continua", "NombreExacto": "Edad"},
       "(SD)Sexo": {"Tipo": "Categórica", "Valores": ["Hombre", "Mujer", "Otro", "Prefiero no decir"]},
       "(SD)Estado Civil": {"Tipo": "Categórica", "Valores": ["Soltero", "Casado", "Separado", "Unión Libre", "Viudo"]},
       "(SD)Numero de hijos": {"Tipo": "Continua"},
       "(SD)Nivel Educativo": {"Tipo": "Categórica", "Valores": ["Primaria", "Bachiller", "Técnico", "Tecnológico", "Tecnológo", "Profesional", "Pregrado", "Posgrado", "Maestría", "Doctorado"]},
       "(SD)Departamento ": {"Tipo": "Categórica"},
       "(SD)Ciudad /Municipio": {"Tipo": "Categórica"},
       "(SD)Zona de vivienda": {"Tipo": "Categórica", "Valores": ["Urbana", "Rural"]},
       "(SD)Estrato Socioeconómico": {"Tipo": "Categórica", "Valores": [1, 2, 3, 4, 5, 6]}
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
               "(BM),(PE)Mi identificación con los valores de la organización.",
               "(BM),(PE)Mi rendimiento profesional.",
               "(BM),(PE)Mi capacidad para responder a mi carga de trabajo",
               "(BM),(PE)La calidad de mis condiciones de trabajo.",
               "(BM),(PE)Mi autoestima profesional",
               "(BM),(PE)La cordialidad en mi ambiente social de trabajo.",
               "(BM),(PE)El equilibrio entre mi trabajo y mi vida privada.",
               "(BM),(PE)Mi confianza en mi futuro profesional",
               "(BM),(PE)Mi calidad de vida laboral.",
               "(BM),(PE)El sentido de mi trabajo",
               "(BM),(PE)Mi cumplimiento de las normas de la dirección.",
               "(BM),(PE)Mi estado de ánimo laboral ",
               "(BM),(PE)Mis oportunidades de promoción laboral.",
               "(BM),(PE)Mi sensación de seguridad en el trabajo",
               "(BM),(PE)Mi participación en las decisiones de la organización.",
               "(BM),(PE)Mi satisfacción con el trabajo.",
               "(BM),(PE)Mi relación profesional.",
               "(BM),(PE)El nivel de excelencia de mi organización.",
               "(BM),(PE)MI eficacia profesional",
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
               "(BM),(CD)Cansancio mental "
           ]
       },
       "Factores de Efectos Colaterales (Escala de Alienación)": {
           "Tipo": "Likert", "Acronimo": "CA",
            "Escala": {1: "Nunca", 2: "Raramente", 3: "Ocasionalmente", 4: "Algunas veces", 5: "Frecuentemente", 6: "Casi siempre", 7: "Siempre"},
           "Preguntas": [
               "(BM),(CA)Mal humor ",
               "(BM),(CA)Baja realización personal",
               "(BM),(CA)Trato distante",
               "(BM),(CA)Frustración "
           ]
       }
   }
}

# --- Robust Preprocessing Configuration (v3.6) ---

def _norm_key(s):
    if not s: return ""
    s = str(s)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('“','"').replace('”','"').replace("’","'").replace("´", "'")
    s = s.replace(' sólo ', ' solo ')
    # Canonicalize extra
    s = re.sub(r'\bamenudo\b', 'a menudo', s)
    s = s.replace('simpre', 'siempre')
    s = s.replace('sobrell', 'sobrelle')
    s = s.replace('llevarllas', 'llevarlas')
    s = re.sub(r'\bmuy seguidoa\b', 'muy seguido', s)
    s = re.sub(r'\bseguido\(a\)\b', 'seguido', s)
    s = re.sub(r'\bmuy seguido\(a\)\b', 'muy seguido', s)
    s = re.sub(r'no estoy segur[oa@x]\b', 'no estoy seguro', s)
    s = re.sub(r'no estoy seguro\s*\(?a\)?', 'no estoy seguro', s)
    s = s.replace('si, ', 'sí, ')
    return s

def _make_map(pairs):
    return {_norm_key(k): v for k,v in pairs}

# Response Sets
RESPONSE_SETS = {
    'sdq_3': _make_map([('No es cierto', 1), ('Un tanto cierto', 2), ('A veces es cierto', 2), ('Es cierto', 3), ('Cierto', 3), ('Absolutamente cierto', 3)]),
    'iri_5': _make_map([('No me describe en absoluto', 0), ('Me describe poco', 1), ('Me describe de manera moderada', 2), ('Algo me describe', 2), ('Me describe bastante', 3), ('Me describe muy bien', 4)]),
    'desc_5_json': _make_map([('No me describe', 1), ('Me describe un poco', 2), ('Me describe moderadamente', 3), ('Me describe mucho', 4), ('Me describe perfectamente', 5)]),
    'pss_5': _make_map([('nunca', 0), ('casi nunca', 1), ('de vez en cuando', 2), ('frecuentemente', 3), ('casi siempre', 4)]),
    'ers_4': _make_map([('nunca', 0), ('algunas veces', 1), ('casi siempre', 2), ('siempre', 3)]),
    'istas_5': _make_map([('nunca', 0), ('solo alguna vez', 1), ('sólo alguna vez', 1), ('algunas veces', 2), ('muchas veces', 3), ('siempre', 4)]),
    'tipo1_freq_4': _make_map([('nunca', 0), ('a veces', 1), ('a menudo', 2), ('siempre', 3)]),
    'tipo5_cert_4': _make_map([('nada cierto', 0), ('algo cierto', 1), ('bastante cierto', 2), ('muy cierto', 3)]),
    'tipo6_freq_3': _make_map([('no',0), ('sí, a veces',1), ('si, a veces',1), ('sí, a menudo',2), ('si, a menudo',2)]),
    'tipo7_int_3': _make_map([('no en absoluto',0), ('un poco',1), ('mucho',2)]),
    'tipo8_int_4v2': _make_map([('no, para nada',1), ('un poco',2), ('bastante',3), ('mucho',4)]),
    'tipo9_agr_3': _make_map([('en desacuerdo',1), ('ni de acuerdo ni en desacuerdo',2), ('de acuerdo',3)]),
    'tipo10_agr_4': _make_map([('muy en desacuerdo',1), ('desacuerdo',2), ('acuerdo',3), ('muy de acuerdo',4)]),
    'tipo12_int_5': _make_map([('para nada',1), ('muy poco',2), ('algo',3), ('bastante',4), ('mucho',5)]),
    'tipo13_fv': _make_map([('falso',1), ('verdadero',2)]),
    'tipo14_agr_4v2': _make_map([('totalmente en desacuerdo',1), ('en desacuerdo',2), ('de acuerdo',3), ('totalmente de acuerdo',4)]),
    'tipo15_si_no_inv': _make_map([('no',1), ('si',0), ('sí',0)]),
    'tipo16_no_si': _make_map([('no',0), ('si',1), ('sí',1)]),
    'tipo17_no_aplica': _make_map([('no aplica',0), ('no',1), ('si',2), ('sí',2)]),
    'tipo18_nuevo': _make_map([('nunca', 0), ('casi nunca', 1), ('algunas veces', 2), ('casi siempre', 3), ('siempre', 4)]),
    'tipo19_nuevo': _make_map([('nunca', 0), ('casi nunca', 1), ('a veces', 2), ('muy seguido', 3), ('siempre', 4)]),
    'tipo20_nuevo': _make_map([('muy en desacuerdo', 0), ('en desacuerdo', 1), ('no estoy seguro', 2), ('de acuerdo', 3), ('muy de acuerdo', 4)]),
    'likert_7_freq': _make_map([('Nunca', 1), ('Rara vez', 2), ('Alguna vez', 3), ('Algunas veces', 4), ('A menudo', 5), ('Frecuentemente', 6), ('Siempre', 7)]),
    'likert_7_agree': _make_map([('Totalmente desacuerdo', 1), ('Muy desacuerdo', 2), ('Algo desacuerdo', 3), ('Neutro', 4), ('Algo acuerdo', 5), ('Muy acuerdo', 6), ('Totalmente acuerdo', 7)]),
    'familiares_31': _make_map([
        ('no hago ninguna o casi ninguna de estas tareas', 0),
        ('solo hago tareas muy puntuales', 1),
        ('sólo hago tareas muy puntuales', 1),
        ('hago mas o menos una cuarta parte de las tareas familiares y domesticas', 2),
        ('hago más o menos una cuarta parte de las tareas familiares y domésticas', 2),
        ('hago aproximadamente la mitad de las tareas familiares y domesticas', 3),
        ('hago aproximadamente la mitad de las tareas familiares y domésticas', 3),
        ('soy la/el principal responsable y hago la mayor parte de las tareas familiares y domesticas', 4),
        ('soy la/el principal responsable y hago la mayor parte de las tareas familiares y domésticas', 4),
    ]),
}

# Reverse Patterns
REVERSE_PATTERNS = [
    r'dificil ver las cosas desde el punto de vista de otros',
    r'no pierdo mucho tiempo escuchando los argumentos',
    r'no me dan mucha lastima|no me dan mucha lástima',
    r'permanezco tranquilo',
    r'no suelen angustiarme mucho',
    r'no suelo sentir mucha pena',
    r'manej[oó] bien los cambios',
    r'confianz(a|o).*poder manejar',
    r'(iban|estaban) yendo bien|le estaban yendo bien',
    r'ha podido controlar sus enojos|pudo controlar sus enojos',
    r'ha utilizado su tiempo adecuadamente|uso su tiempo',
    r'tengo total claridad sobre mis sentimientos',
    r'le pre[s|st]t[oó] atenci[oó]n a la forma c[oó]mo me siento',
    r's[eé] exactamente c[oó]mo me estoy sintiendo|se exactamente como me estoy siento',
    r'cuando me enojo, reconozco el estado emocional',
    r'me reprocho a m[ií] mismo',
    r'tiempo de llevar al d[ií]a tu trabajo',
    r'influencia sobre la cantidad de trabajo',
    r'se tiene en cuenta tu opini[oó]n',
    r'influencia sobre el orden en el que realizas las tareas',
    r'puedes decidir cu[aá]ndo haces un descanso',
    r'puedes dejar tu puesto de trabajo',
    r'tu trabajo requiere que tengas iniciativa',
    r'tu trabajo permite que aprendas cosas nuevas',
    r'te sientes comprometido con tu profesi[oó]n',
    r'tienen sentido tus tareas',
    r'hablas con entusiasmo de tu empresa',
]

# Column Overrides
COLUMN_ORDERED_OPTIONS_EXACT = {
    _norm_key('Nivel educativo del padre '): ["Bachiller","Posgrado","Primaria","Profesional","Técnico o tecnólogo"],
    _norm_key(' En general, el desempeño académico de mi hijo(a) en el colegio puede ser considerado, de acuerdo con sus notas y aprendizaje, cómo:'): ["Bajo o regular","Deficiente o muy bajo","Excelente o sobresaliente","Muy bueno","Normal o promedio"],
    _norm_key('¿En qué zona está ubicada la vivienda?'): ["Rural (en el campo o lejos del casco urbano)","Urbana (en la cuidad o pueblo)"],
    _norm_key('1. ¿En su barrio hay problemas relacionados con drogas y/o alcohol? (consumo o venta)'): ["No","Sí, es muy frecuente","Sí, pero con baja frecuencia"],
    _norm_key('2. ¿En su barrio hay delincuencia común cómo robos o atracos?'): ["No","Sí, es muy frecuente","Sí, pero con baja frecuencia"],
    _norm_key('3. ¿En su barrio se presentan riñas o peleas callejeras?'): ["No","Sí, es muy frecuente","Sí, pero con baja frecuencia"],
    _norm_key('5. ¿En su barrio hay presencia de pandillas o bandas?'): ["No","Sí, es muy frecuente","Sí, pero con baja frecuencia"],
    _norm_key('1. He podido reír y ver el lado bueno de las cosas.'): ["No tanto ahora","No, en absoluto","Sin duda, mucho menos ahora","Tanto como siempre he podido hacerlo"],
    _norm_key('2. He mirado el futuro con placer para hacer las cosas.'): ["Algo menos de lo que solía hacerlo","Definitivamente menos de lo que solía hacerlo","Prácticamente nunca","Tanto como siempre"],
    _norm_key('3. Me he culpado sin necesidad cuando las cosas marchaban mal.'): ["No muy a menudo","No, nunca","Sí, algunas veces","Sí, casi siempre"],
    _norm_key('4. He estado ansioso(a) y preocupado(a) sin motivo alguno.'): ["Casi nada","No, en absoluto","Sí, a veces","Sí, muy a menudo"],
    _norm_key('5. He pensado en hacerme daño.'): ["A veces","Casi nunca","No, nunca","Sí, bastante a menudo"],
    _norm_key('Sexo del niño(a).1'): ["Niña","Niño"],
    _norm_key('Este es un colegio:.1'): ["Oficial o público","Privado"],
}

COLUMN_ORDERED_OPTIONS_KEYWORD = {
    _norm_key('tiene en cuenta los sentimientos de otras personas'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('comparte frecuentemente con otros niños chucherías, juguetes, lápices'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('por lo general es obediente, suele hacer lo que le piden los adultos'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('ofrece ayuda cuando alguien resulta herido, disgustado o enfermo'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('tiene por lo menos un/a buen/a amigo/a'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('por lo general cae bien a los otros niños/niñas'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('trata bien a los niños/niñas más pequeños'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('a menudo se ofrece para ayudar a padres, profesores, otro niños'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('termina lo que empieza, tiene buena concentración'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
    _norm_key('piensa las cosas antes de hacerlas'): ["Absolutamente cierto","No es cierto","Un tanto cierto"],
}

# --- Configuración visual centralizada ---

CHART_CONFIG = {
    "height_default": 350,
    "height_small": 200,
    "height_large": 500,
    "margin": dict(l=80, r=60, t=60, b=100),
    "margin_compact": dict(l=60, r=40, t=40, b=80),
    "colors": {
        "primary":   "#1B3358",
        "success":   "#34A853",
        "warning":   "#FBBC04",
        "danger":    "#EA4335",
        "neutral":   "#5F6368",
    }
}

# Para gráficas matplotlib (reportes PDF)
MATPLOTLIB_CONFIG = {
    "figure_dpi": 120,
    "tight_layout_pad": 2.0,
    "xlim_right_factor": 1.35,
    "savefig_bbox": "tight",
    "savefig_pad_inches": 0.3,
}

# --- Valencia psicométrica por ítem -----------------------------------------
# +1 = una respuesta más alta implica MÁS bienestar (ítem directo)
# -1 = una respuesta más alta implica MENOS bienestar (ítem inverso; se invierte)
#
# Estructura: por dimensión, una valencia `default` y una lista `flip` de subcadenas
# de los ítems cuya valencia es OPUESTA al default. Esto orienta todas las dimensiones
# a "mayor = mejor bienestar". Documentado en docs/METODOLOGIA_PUNTAJES.md.
# Es la fuente de verdad: corregir aquí actualiza dashboard y reportes.
DIMENSION_VALENCE = {
    "Control del Tiempo": {"default": +1, "flip": [
        "me presionan para que trabaje muchas horas",
        "plazos de entrega inalcanzables",
        "presiones de tiempo poco realistas",
        "descuidar algunas tareas",
    ]},
    "Compromiso del Líder": {"default": +1, "flip": []},
    "Apoyo del Grupo": {"default": +1, "flip": []},
    "Claridad de Rol": {"default": +1, "flip": [
        "difíciles de hacer al mismo tiempo",
        "cosas contradictorias",
        "solicitudes incompatibles",
    ]},
    "Cambio Organizacional": {"default": +1, "flip": []},
    "Responsabilidad Organizacional": {"default": +1, "flip": []},
    "Conflicto Familia-Trabajo": {"default": -1, "flip": []},
    "Síntomas de Burnout": {"default": -1, "flip": []},
    "Compromiso": {"default": +1, "flip": []},
    "Defensa de la Organización": {"default": +1, "flip": []},
    "Satisfacción": {"default": +1, "flip": []},
    "Intención de Retiro": {"default": -1, "flip": [
        "me veo trabajando en este lugar",
    ]},
    "Bienestar Psicosocial (Escala de Afectos)": {"default": +1, "flip": []},
    "Bienestar Psicosocial (Escala de Competencias)": {"default": +1, "flip": []},
    "Bienestar Psicosocial (Escala de Expectativas)": {"default": +1, "flip": []},
    "Factores de Efectos Colaterales (Escala de Somatización)": {"default": -1, "flip": []},
    "Factores de Efectos Colaterales (Escala de Desgaste)": {"default": -1, "flip": []},
    "Factores de Efectos Colaterales (Escala de Alienación)": {"default": -1, "flip": []},
}

# Dimensiones que representan RIESGO (su lectura natural es "más = peor").
# Se orientan a bienestar para el semáforo, pero se reporta también su nivel de riesgo.
RISK_DIMENSIONS = {
    "Conflicto Familia-Trabajo",
    "Síntomas de Burnout",
    "Intención de Retiro",
    "Factores de Efectos Colaterales (Escala de Somatización)",
    "Factores de Efectos Colaterales (Escala de Desgaste)",
    "Factores de Efectos Colaterales (Escala de Alienación)",
}


def item_valence(dim_name: str, question: str) -> int:
    """Devuelve +1 (directo) o -1 (inverso) para un ítem de una dimensión.

    Ver docs/METODOLOGIA_PUNTAJES.md. Ítems no registrados se asumen directos (+1).
    """
    cfg = DIMENSION_VALENCE.get(dim_name)
    if not cfg:
        return +1
    q = _norm_key(question)
    default = cfg.get("default", +1)
    for sub in cfg.get("flip", []):
        if _norm_key(sub) in q:
            return -default
    return default


def get_scale_range(dim_name: str):
    """Rango (min, max) de la escala de una dimensión, leído del DATA_DICTIONARY."""
    details = DATA_DICTIONARY.get("Dimensiones de Bienestar y Salud Mental", {}).get(dim_name, {})
    escala = details.get("Escala", {})
    vals = [k for k in escala.keys() if isinstance(k, (int, float))] if isinstance(escala, dict) else []
    if vals:
        return min(vals), max(vals)
    # Fallbacks razonables por familia de dimensión
    if "Burnout" in dim_name:
        return 1, 5
    if any(s in dim_name for s in ["Compromiso", "Defensa", "Satisfacción", "Retiro"]):
        return 1, 6
    return 1, 7
