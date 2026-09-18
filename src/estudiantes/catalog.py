"""
Catálogo del instrumento de estudiantes — Observatorio 360.

ÚNICA FUENTE DE VERDAD para ítems, inversos, subescalas, rangos, puntos de corte
y textos por audiencia. Si un corte cambia, cambia aquí y toda la app se actualiza.

Documentación legible: docs/instrumentos/INSTRUMENTO_ESTUDIANTES.md
Cifras de referencia:  docs/instrumentos/fixtures/resultados_preliminares_estudiantes.json

Reglas no negociables codificadas aquí:
  · El SDQ autoinforme tiene bandas distintas a la versión de padres (BANDS_PARENT
    existe solo para contraste con el dataset de cuidadores; nunca para estudiantes).
  · El ARI suma únicamente los ítems 1 a 6; el 7 mide deterioro.
  · El MSPSS es de 5 puntos: los cortes de Zimet (7 puntos) NO aplican.
  · El RCADS exige puntuaciones T que no tenemos; se usan percentiles propios.
  · ERQ-CA, MSPSS, PSSM y TD no tienen corte clínico: terciles de la muestra.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Constantes de privacidad y presentación ─────────────────────────────────
MIN_GROUP_N = 10          # ningún grupo con menos casos se muestra desagregado
ORDEN_GRADOS_SEC = ["Sexto", "Séptimo", "Octavo", "Noveno", "Décimo"]
ORDEN_GRADOS_PRI = ["Cuarto", "Quinto"]

# Nivel educativo según el formulario de origen
NIVEL_SECUNDARIA = "secundaria"
NIVEL_PRIMARIA = "primaria"


# ── Mapas de etiquetas a números (tal como llegaron en los formularios) ─────
MAP_3 = {"no es cierto": 0, "algo cierto": 1, "muy cierto": 2}
MAP_4_FREQ = {"nunca": 0, "algunas veces": 1, "con frecuencia": 2, "siempre": 3}
MAP_5_ERQ = {
    "nada parecido a mi": 1, "poco parecido a mi": 2, "se parece a mi": 3,
    "bastante parecido a mi": 4, "exactamente igual a mi": 5,
}
MAP_5_FREQ = {"nunca": 1, "casi nunca": 2, "algunas veces": 3, "casi siempre": 4, "siempre": 5}
MAP_5_FREQ_TD = {"nunca": 1, "casi nunca": 2, "a veces": 3, "casi siempre": 4, "siempre": 5}


# ── Bandas del SDQ ──────────────────────────────────────────────────────────
BANDAS_LABELS = ["Cercano al promedio", "Ligeramente elevado", "Alto", "Muy alto"]
BANDAS_LABELS_PROSOCIAL = ["Cercano al promedio", "Ligeramente disminuido", "Bajo", "Muy bajo"]

# Autoinforme 11-17. Fuente: "Scoring the SDQ for age 4-17", tabla 3, sdqinfo.org
BANDS_SELF = {
    "SDQ_Total": [(0, 14), (15, 17), (18, 19), (20, 40)],
    "SDQ_Emo":   [(0, 4), (5, 5), (6, 6), (7, 10)],
    "SDQ_Con":   [(0, 3), (4, 4), (5, 5), (6, 10)],
    "SDQ_Hip":   [(0, 5), (6, 6), (7, 7), (8, 10)],
    "SDQ_Pares": [(0, 2), (3, 3), (4, 4), (5, 10)],
    "SDQ_Pro":   [(7, 10), (6, 6), (5, 5), (0, 4)],   # se lee al revés
}
# Versión para padres 4-17. SOLO para contraste con el dataset de cuidadores.
BANDS_PARENT = {
    "SDQ_Total": [(0, 13), (14, 16), (17, 19), (20, 40)],
    "SDQ_Emo":   [(0, 3), (4, 4), (5, 6), (7, 10)],
    "SDQ_Con":   [(0, 2), (3, 3), (4, 5), (6, 10)],
    "SDQ_Hip":   [(0, 5), (6, 7), (8, 8), (9, 10)],
    "SDQ_Pares": [(0, 2), (3, 3), (4, 4), (5, 10)],
    "SDQ_Pro":   [(8, 10), (7, 7), (6, 6), (0, 5)],
}
FUENTE_BANDS_SELF = ("Scoring the Strengths & Difficulties Questionnaire for age 4-17, "
                     "tabla 3 (autoinforme), sdqinfo.org")


@dataclass(frozen=True)
class Subescala:
    """Una puntuación derivada: qué ítems la componen y cómo se interpreta."""
    key: str
    label: str                      # nombre técnico, para investigación
    label_llano: str                # nombre sin jerga, para la comunidad
    items: tuple[int, ...]          # números de ítem 1-indexados dentro de su escala
    reverse: tuple[int, ...] = ()   # ítems que se invierten
    rango: tuple[float, float] = (0, 0)
    agregacion: str = "suma"        # "suma" | "media"
    direccion: str = "riesgo"       # "riesgo" (más = peor) | "protector" (más = mejor)
    bandas: str | None = None       # clave en BANDS_SELF, si aplica
    cortes: tuple[tuple[str, str], ...] = ()   # (etiqueta, descripción) informativos
    min_items: int = 0              # ítems mínimos respondidos para puntuar


@dataclass(frozen=True)
class Escala:
    key: str
    nombre: str
    nombre_llano: str
    prefijo: str                    # prefijo de columna normalizada: SDQ1, ARI1…
    n_items: int
    mapa: dict                      # etiqueta → número
    valor_min: int
    valor_max: int
    edad_validada: tuple[int, int]
    fuente: str
    solo_secundaria: bool = False
    validada: bool = True           # False = exploratoria, sin validación conocida
    subescalas: tuple[Subescala, ...] = field(default_factory=tuple)

    @property
    def columnas(self) -> list[str]:
        return [f"{self.prefijo}{i}" for i in range(1, self.n_items + 1)]


# ── SDQ ─────────────────────────────────────────────────────────────────────
SDQ = Escala(
    key="SDQ", nombre="SDQ — Cualidades y dificultades",
    nombre_llano="Dificultades emocionales y de comportamiento",
    prefijo="SDQ", n_items=25, mapa=MAP_3, valor_min=0, valor_max=2,
    edad_validada=(11, 17), fuente=FUENTE_BANDS_SELF,
    subescalas=(
        Subescala("SDQ_Emo", "Síntomas emocionales", "Tristeza, preocupación y miedos",
                  (3, 8, 13, 16, 24), (), (0, 10), "suma", "riesgo", "SDQ_Emo", min_items=4),
        Subescala("SDQ_Con", "Problemas de conducta", "Peleas, desobediencia y mentiras",
                  (5, 7, 12, 18, 22), (7,), (0, 10), "suma", "riesgo", "SDQ_Con", min_items=4),
        Subescala("SDQ_Hip", "Hiperactividad e inatención", "Inquietud y dificultad para concentrarse",
                  (2, 10, 15, 21, 25), (21, 25), (0, 10), "suma", "riesgo", "SDQ_Hip", min_items=4),
        Subescala("SDQ_Pares", "Problemas con pares", "Sentirse solo o molestado por otros",
                  (6, 11, 14, 19, 23), (11, 14), (0, 10), "suma", "riesgo", "SDQ_Pares", min_items=4),
        Subescala("SDQ_Pro", "Conducta prosocial", "Ayudar y compartir con otros",
                  (1, 4, 9, 17, 20), (), (0, 10), "suma", "protector", "SDQ_Pro", min_items=4),
    ),
)
SDQ_REVERSE_ITEMS = (7, 11, 14, 21, 25)
SDQ_SUBS_DIFICULTADES = ("SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares")

# ── ARI ─────────────────────────────────────────────────────────────────────
ARI = Escala(
    key="ARI", nombre="ARI — Índice de reactividad afectiva", nombre_llano="Irritabilidad",
    prefijo="ARI", n_items=7, mapa=MAP_3, valor_min=0, valor_max=2,
    edad_validada=(9, 17),
    fuente="Stringaris et al. (2012), J Child Psychol Psychiatry",
    subescalas=(
        Subescala("ARI_Total", "Irritabilidad (ítems 1-6)", "Enojo frecuente e intenso",
                  (1, 2, 3, 4, 5, 6), (), (0, 12), "suma", "riesgo", None,
                  cortes=((">2", "Cribado de irritabilidad severa; sensibilidad 84 %, especificidad 77 %"),
                          ("≥4", "Indicador de psicopatología general; AUC 0,86")),
                  min_items=6),
        Subescala("ARI_Deterioro", "Deterioro funcional (ítem 7)",
                  "Si la irritabilidad le causa problemas", (7,), (), (0, 2),
                  "suma", "riesgo", None, min_items=1),
    ),
)

# ── RCADS-25 ────────────────────────────────────────────────────────────────
RCADS_DEP_ITEMS = (1, 4, 8, 10, 13, 15, 16, 18, 19, 21)
RCADS_ANX_ITEMS = tuple(i for i in range(1, 26) if i not in RCADS_DEP_ITEMS)
RCADS_ITEM_MUERTE = 18   # "Pienso acerca de la muerte": señal de alerta, nunca diagnóstico
RCADS = Escala(
    key="RCADS", nombre="RCADS-25 — Ansiedad y depresión",
    nombre_llano="Síntomas de ansiedad y depresión",
    prefijo="RCADS", n_items=25, mapa=MAP_4_FREQ, valor_min=0, valor_max=3,
    edad_validada=(8, 18), solo_secundaria=True,
    fuente="Chorpita, Ebesutani & Spence, RCADS User's Guide; rcads.ucla.edu",
    subescalas=(
        Subescala("RCADS_Dep", "Depresión mayor", "Tristeza persistente y falta de energía",
                  RCADS_DEP_ITEMS, (), (0, 30), "suma", "riesgo", None, min_items=9),
        Subescala("RCADS_Anx", "Ansiedad total", "Miedos y preocupaciones",
                  RCADS_ANX_ITEMS, (), (0, 45), "suma", "riesgo", None, min_items=14),
        Subescala("RCADS_Total", "Total", "Ansiedad y depresión juntas",
                  tuple(range(1, 26)), (), (0, 75), "suma", "riesgo", None, min_items=23),
    ),
)

# ── ERQ-CA ──────────────────────────────────────────────────────────────────
ERQ = Escala(
    key="ERQ", nombre="ERQ-CA — Regulación emocional",
    nombre_llano="Cómo maneja sus emociones",
    prefijo="ERQ", n_items=10, mapa=MAP_5_ERQ, valor_min=1, valor_max=5,
    edad_validada=(8, 18), fuente="Gullone & Taffe (2012), ERQ-CA",
    subescalas=(
        Subescala("ERQ_Reap", "Reevaluación cognitiva", "Cambiar la forma de pensar la situación",
                  (1, 3, 5, 7, 8, 10), (), (1, 5), "media", "protector", None, min_items=6),
        Subescala("ERQ_Sup", "Supresión expresiva", "Guardarse lo que siente",
                  (2, 4, 6, 9), (), (1, 5), "media", "riesgo", None, min_items=4),
    ),
)

# ── MSPSS ───────────────────────────────────────────────────────────────────
MSPSS = Escala(
    key="MSPSS", nombre="MSPSS — Apoyo social percibido", nombre_llano="Apoyo que siente de otros",
    prefijo="MSPSS", n_items=12, mapa=MAP_5_FREQ, valor_min=1, valor_max=5,
    edad_validada=(10, 18),
    fuente="Zimet et al. (1988); en este proyecto con escala de 5 puntos, "
           "por lo que los cortes originales de 7 puntos no aplican",
    subescalas=(
        Subescala("MSPSS_Total", "Apoyo social total", "Apoyo que siente en general",
                  tuple(range(1, 13)), (), (1, 5), "media", "protector", None, min_items=11),
        Subescala("MSPSS_Otro", "Otro significativo", "Una persona especial",
                  (1, 2, 5, 10), (), (1, 5), "media", "protector", None, min_items=4),
        Subescala("MSPSS_Fam", "Familia", "Su familia",
                  (3, 4, 8, 11), (), (1, 5), "media", "protector", None, min_items=4),
        Subescala("MSPSS_Amigos", "Amigos", "Sus amigos",
                  (6, 7, 9, 12), (), (1, 5), "media", "protector", None, min_items=4),
    ),
)

# ── PSSM ────────────────────────────────────────────────────────────────────
PSSM_REVERSE_ITEMS = (3, 6, 9, 12, 16)
PSSM_ITEM_ADULTO = 7   # "Hay al menos un profesor o adulto con quien puedo hablar"
PSSM = Escala(
    key="PSSM", nombre="PSSM — Pertenencia a la escuela", nombre_llano="Sentirse parte del colegio",
    prefijo="PSSM", n_items=18, mapa={}, valor_min=1, valor_max=5,   # llegó numérico
    edad_validada=(8, 17), fuente="Goodenow (1993); validación en adolescentes chilenos (2016)",
    subescalas=(
        Subescala("PSSM_Total", "Pertenencia (18 ítems)", "Sentirse parte del colegio",
                  tuple(range(1, 19)), PSSM_REVERSE_ITEMS, (1, 5), "media", "protector",
                  None, min_items=17),
        Subescala("PSSM_Pos13", "Pertenencia (13 ítems positivos)",
                  "Sentirse parte del colegio, solo enunciados positivos",
                  tuple(i for i in range(1, 19) if i not in PSSM_REVERSE_ITEMS), (),
                  (1, 5), "media", "protector", None, min_items=12),
    ),
)

# ── Toma de decisiones (exploratoria: fuente sin documentar) ────────────────
TD = Escala(
    key="TD", nombre="Toma de decisiones (exploratoria)", nombre_llano="Pensar antes de actuar",
    prefijo="TD", n_items=10, mapa=MAP_5_FREQ_TD, valor_min=1, valor_max=5,
    edad_validada=(8, 18), validada=False,
    fuente="Sin documentar: llegó en el formulario y no estaba en el instrumento. "
           "Pendiente de identificar por el equipo investigador.",
    subescalas=(
        Subescala("TD_Total", "Toma de decisiones", "Pensar antes de actuar",
                  tuple(range(1, 11)), (), (1, 5), "media", "protector", None, min_items=9),
    ),
)

ESCALAS: tuple[Escala, ...] = (SDQ, ARI, RCADS, ERQ, MSPSS, PSSM, TD)
ESCALAS_POR_KEY = {e.key: e for e in ESCALAS}


# ── Puntuaciones compuestas que no salen de una sola subescala ──────────────
COMPUESTAS = {
    "SDQ_Total": dict(label="Total de dificultades", label_llano="Dificultades en total",
                      partes=SDQ_SUBS_DIFICULTADES, rango=(0, 40),
                      direccion="riesgo", bandas="SDQ_Total"),
    "SDQ_Int":   dict(label="Internalizante", label_llano="Malestar hacia adentro",
                      partes=("SDQ_Emo", "SDQ_Pares"), rango=(0, 20),
                      direccion="riesgo", bandas=None),
    "SDQ_Ext":   dict(label="Externalizante", label_llano="Malestar hacia afuera",
                      partes=("SDQ_Con", "SDQ_Hip"), rango=(0, 20),
                      direccion="riesgo", bandas=None),
}

# Orden canónico para la Tabla 1 y los exportables
ORDEN_TABLA1 = [
    "SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro",
    "ARI_Total", "RCADS_Dep", "RCADS_Anx", "RCADS_Total",
    "ERQ_Reap", "ERQ_Sup", "MSPSS_Total", "MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro",
    "PSSM_Total", "PSSM_Pos13", "TD_Total",
]

# Variables que entran a la matriz de correlaciones (evita redundancias como el total del MSPSS)
CORR_VARS_SEC = [
    "SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro",
    "ARI_Total", "RCADS_Dep", "RCADS_Anx", "ERQ_Reap", "ERQ_Sup",
    "MSPSS_Fam", "MSPSS_Amigos", "MSPSS_Otro", "MSPSS_Total", "PSSM_Total", "TD_Total",
]
CORR_VARS_PRI = [v for v in CORR_VARS_SEC if not v.startswith("RCADS")]


def subescala(key: str) -> Subescala | None:
    for e in ESCALAS:
        for s in e.subescalas:
            if s.key == key:
                return s
    return None


def escala_de(key: str) -> Escala | None:
    """Escala a la que pertenece una puntuación (subescala o compuesta)."""
    if key in COMPUESTAS:
        return SDQ
    for e in ESCALAS:
        if any(s.key == key for s in e.subescalas):
            return e
    return None


def meta(key: str) -> dict:
    """Metadatos uniformes de cualquier puntuación, sea subescala o compuesta."""
    if key in COMPUESTAS:
        c = COMPUESTAS[key]
        return dict(key=key, label=c["label"], label_llano=c["label_llano"],
                    rango=c["rango"], direccion=c["direccion"], bandas=c["bandas"],
                    escala="SDQ", agregacion="suma", validada=True, cortes=())
    s = subescala(key)
    if s is None:
        return dict(key=key, label=key, label_llano=key, rango=(0, 0),
                    direccion="riesgo", bandas=None, escala="", agregacion="suma",
                    validada=True, cortes=())
    e = escala_de(key)
    return dict(key=key, label=s.label, label_llano=s.label_llano, rango=s.rango,
                direccion=s.direccion, bandas=s.bandas, escala=e.key if e else "",
                agregacion=s.agregacion, validada=e.validada if e else True,
                cortes=s.cortes)


def banda_de(valor: float, bandas_key: str, version: str = "self") -> int | None:
    """Índice de banda 0-3 para un puntaje del SDQ. None si no aplica."""
    tabla = BANDS_SELF if version == "self" else BANDS_PARENT
    if bandas_key not in tabla or valor is None:
        return None
    for i, (lo, hi) in enumerate(tabla[bandas_key]):
        if lo <= valor <= hi:
            return i
    return None


def etiqueta_banda(bandas_key: str, idx: int) -> str:
    labels = BANDAS_LABELS_PROSOCIAL if bandas_key == "SDQ_Pro" else BANDAS_LABELS
    return labels[idx] if idx is not None and 0 <= idx < 4 else "Sin dato"


# ── Textos por audiencia ────────────────────────────────────────────────────
# Fijos y revisables por el equipo. NUNCA los genera la IA: un texto sobre salud
# mental infantil no se improvisa. {pct} y {n} se sustituyen con cifras reales.

@dataclass(frozen=True)
class Mensaje:
    titulo: str
    significa: str
    accion_colegio: str
    accion_familia: str
    accion_municipio: str
    solo_roles: tuple[str, ...] = ("colegio", "familia", "municipio")


ROLES = {
    "colegio": "Rector, docente u orientación escolar",
    "familia": "Madre, padre o cuidador",
    "municipio": "Funcionario del municipio",
}

MENSAJES: dict[str, Mensaje] = {
    "sdq_alto": Mensaje(
        titulo="Dificultades emocionales y de comportamiento",
        significa="En una población general se espera que 1 de cada 10 esté en el nivel alto. "
                  "Lo que más pesa aquí es sentirse solo o molestado por otros, y la tristeza o "
                  "preocupación, no el mal comportamiento.",
        accion_colegio="Reforzar orientación escolar y convivencia entre pares. No hay un grado "
                       "que concentre el problema: conviene actuar en todos.",
        accion_familia="Preguntar por cómo le va con sus compañeros, no solo por las notas. "
                       "Sentirse aceptado en el curso pesa tanto como el rendimiento.",
        accion_municipio="Dimensionar la demanda de atención psicosocial escolar en la red pública.",
    ),
    "adulto_confianza": Mensaje(
        titulo="Tener un adulto de confianza en el colegio",
        significa="Es el indicador más bajo de toda la encuesta. Donde el estudiante sí tiene ese "
                  "adulto, las dificultades son menos frecuentes.",
        accion_colegio="Un docente de referencia por curso, con un espacio semanal para hablar. "
                       "Priorizar los grados donde la cifra es más alta.",
        accion_familia="Preguntarle si hay algún profesor con quien se sienta cómodo. Si no hay "
                       "ninguno, pedirlo en la reunión de curso.",
        accion_municipio="Incluir la figura del docente de referencia en los planes de convivencia "
                         "escolar del municipio.",
    ),
    "emocional_sexo": Mensaje(
        titulo="Síntomas emocionales por sexo",
        significa="La tristeza, la preocupación y los miedos pesan más del doble en las chicas. "
                  "En los grados altos la diferencia se ensancha.",
        accion_colegio="Espacios de escucha con enfoque de género en los grados altos. No asumir "
                       "que el chico que no habla está bien.",
        accion_familia="Las chicas suelen expresar el malestar hacia adentro y los chicos hacia "
                       "afuera. Los dos necesitan que se les pregunte.",
        accion_municipio="Orientar la oferta de salud mental adolescente con enfoque diferencial.",
    ),
    "apoyo_familia": Mensaje(
        titulo="El apoyo que siente en casa",
        significa="Es el factor protector más fuerte que mide este estudio. La diferencia en "
                  "síntomas depresivos entre quienes sienten mucho apoyo y poco apoyo es de "
                  "varias veces.",
        accion_colegio="Llevar este dato a la escuela de padres. Es la intervención con más "
                       "retorno por esfuerzo.",
        accion_familia="Escuchar sin corregir de entrada y ayudarle a decidir protege más que "
                       "vigilarlo. Diez minutos diarios de conversación sin pantallas cuentan.",
        accion_municipio="Fortalecer programas de crianza y parentalidad positiva.",
    ),
    "pertenencia": Mensaje(
        titulo="Sentirse parte del colegio",
        significa="Los estudiantes que se sienten parte de su colegio reportan bastante menos "
                  "malestar. Es un factor protector que el colegio sí puede mover.",
        accion_colegio="Revisar los ítems más bajos: son todos sobre la relación con los "
                       "profesores, no sobre la infraestructura.",
        accion_familia="Participar en las actividades del colegio ayuda a que el hijo sienta "
                       "que pertenece.",
        accion_municipio="Incluir clima escolar en los indicadores de calidad educativa municipal.",
    ),
    "irritabilidad": Mensaje(
        titulo="Irritabilidad",
        significa="Enojo frecuente e intenso que al estudiante le cuesta controlar. El umbral de "
                  "esta prueba se creó en muestras clínicas, así que aquí se lee como "
                  "irritabilidad elevada y no como un trastorno.",
        accion_colegio="Talleres de regulación emocional en el aula y pausas activas.",
        accion_familia="El enojo intenso a esta edad suele ser señal de algo que no logra decir "
                       "con palabras. Preguntar en frío, no en caliente.",
        accion_municipio="Formación docente en manejo del aula y regulación emocional.",
    ),
    "ideacion": Mensaje(
        titulo="Pensamientos sobre la muerte",
        significa="Es una señal de malestar, no un diagnóstico ni una medida de riesgo suicida. "
                  "Aparece casi siempre junto a la tristeza persistente. Obliga a tener una ruta "
                  "de atención activa antes de devolver resultados.",
        accion_colegio="Activar la ruta de atención y formar a los docentes en primeros auxilios "
                       "psicológicos. No abordar a estudiantes individuales a partir de este dato.",
        accion_familia="",
        accion_municipio="Garantizar capacidad de respuesta en la ruta de salud mental para el "
                         "volumen que implica esta cifra.",
        solo_roles=("colegio", "municipio"),
    ),
}

RUTA_ATENCION = [
    ("Orientación escolar del colegio", "Primer contacto, siempre."),
    ("Línea 106", "Atención psicológica gratuita, 24 horas."),
    ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
    ("Comisaría de Familia", "Si hay riesgo en el hogar."),
]

AVISO_TAMIZAJE = ("Estos resultados son un tamizaje de grupo, no un diagnóstico individual. "
                  "Ningún dato corresponde a un estudiante identificable y los grupos con menos "
                  f"de {MIN_GROUP_N} estudiantes no se muestran.")

AVISO_PRIMARIA = ("Primaria (4.º y 5.º) respondió el SDQ y el MSPSS por debajo de la edad en que "
                  "esas escalas están validadas, y no respondió el RCADS. Sus resultados son "
                  "exploratorios y sus bandas, orientativas.")

AVISO_NORMAS = ("Ninguno de los puntos de corte es colombiano: el SDQ es británico, el RCADS "
                "estadounidense y el ARI proviene de muestras clínicas. Se presentan como "
                "referencia externa y se acompañan de los percentiles de esta muestra.")
