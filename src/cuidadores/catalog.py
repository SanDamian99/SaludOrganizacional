"""
Catálogo del formulario «Cuidando al Cuidador» — Observatorio 360.

ÚNICA FUENTE DE VERDAD del módulo de cuidadores: qué hay en cada columna (por
posición, spec §3.2), cómo se convierte cada respuesta en número (mapas de
texto explícitos), qué puntuaciones existen, sus rangos y sus cortes.

Reglas que este catálogo fija:
  · El formulario se lee **por posición** y cada posición clave se verifica con
    un fragmento de su encabezado (`VERIFICAR`). Si Google Forms cambia el
    orden, la carga falla con un mensaje, nunca puntúa la columna equivocada.
  · Las respuestas se convierten **por su texto**, nunca por su posición en la
    lista de opciones. La EPDS tiene un mapa por ítem: cada ítem tiene sus
    cuatro etiquetas propias y varios están invertidos.
  · Columnas que nunca se copian: nombres (3, 4, 147, 208) y teléfono (179).
    Los tres nombres de las posiciones 3, 4 y 147 solo se leen para calcular el
    seudónimo; el teléfono y la 208 no se leen.
  · Estrés parental: no hay total ni subescalas hasta el libro de códigos
    (spec §5.5). APQ: solo castigo físico (78–80) y grito (81), descriptivos.

Los textos de este módulo son provisionales (`TEXTOS_APROBADOS = False`) y los
aprueba el equipo (spec §8). Nunca los redacta la IA.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.estudiantes import catalog as cat_est

TEXTOS_APROBADOS = False

MIN_GROUP_N = cat_est.MIN_GROUP_N
MODULO = "cuidadores"

# ── Marcos de análisis ──────────────────────────────────────────────────────
MARCO_CUIDADOR = "cuidador"     # una fila por cuidador distinto
MARCO_NINO = "nino"             # una fila por niño distinto (hijo 1 y hijo 2)
NOMBRES_MARCO = {MARCO_CUIDADOR: "Cuidadores (lo que dice el adulto de sí mismo)",
                 MARCO_NINO: "Niños (lo que dice el cuidador del niño)"}

# Fragmento normalizado con el que se reconoce el archivo en disco.
PATRON_ARCHIVO = "cuidando al cuidador"
N_COLUMNAS = 209

# ── Columnas de identificación y contexto (posición) ───────────────────────
COL = dict(
    ts=0, consentimiento=1, quien=2,
    nombre_cuidador=3, nombre_nino=4,           # solo para el seudónimo
    edad=5, sexo=6, colegio=7, tipo_colegio=8, curso=9,
    vive_mama=10, educ_madre=12, vive_papa=13, educ_padre=15,
    desempeno=17, zona=18, estrato=19,
    hijo2=146, nombre_nino2=147,                # solo para el seudónimo
    edad2=148, sexo2=149, colegio2=150, tipo_colegio2=151, curso2=152,
)
# Nunca se leen: teléfono y el nombre de un tercer hijo (bloque vacío).
NUNCA_SE_LEEN = (179, 208)
COLUMNAS_NOMBRE = (COL["nombre_cuidador"], COL["nombre_nino"], COL["nombre_nino2"], 208)

# Contexto que entra al marco de cuidadores, tal como se respondió (categórico).
CONTEXTO = dict(Vive_mama="vive_mama", Educ_madre="educ_madre", Vive_papa="vive_papa",
                Educ_padre="educ_padre", Desempeno="desempeno", Zona="zona",
                Estrato="estrato")


# ── Mapas de etiquetas (claves ya normalizadas con core.texto.norm_txt) ────
MAP_BARRIO = {"no": 0, "si pero con baja frecuencia": 1, "si es muy frecuente": 2}
# Igual que docentes (scripts/preparar_docentes.py, MAPAS["PSS"]).
MAP_PSS = {"nunca": 0, "casi nunca": 1, "de vez en cuando": 2, "frecuentemente": 3,
           "casi siempre": 4}
MAP_MSPSS = {"nunca": 1, "casi nunca": 2, "algunas veces": 3, "casi siempre": 4,
             "siempre": 5}
MAP_APQ = {"nunca": 1, "casi nunca": 2, "a veces": 3, "muy seguido": 4, "siempre": 5}
MAP_ACUERDO = {"muy en desacuerdo": 1, "en desacuerdo": 2, "no estoy seguro": 3,
               "de acuerdo": 4, "muy de acuerdo": 5}
MAP_SDQ_PADRES = {"no es cierto": 0, "un tanto cierto": 1, "absolutamente cierto": 2}
MAP_ARI_PADRES = {"no es cierto": 0, "a veces cierto": 1, "cierto": 2}

# EPDS-10: un mapa por ítem, por el TEXTO de la respuesta (Cox, Holden y Sagovsky,
# 1987; versión en español). Los ítems 3 y 5 a 10 puntúan al revés del orden en
# que aparecen las opciones. Se incluyen las erratas tal como llegaron en el
# formulario («simpre», «sobrellevarllas», «amenudo») y su forma corregida.
EPDS_MAPAS: tuple[dict, ...] = (
    {"tanto como siempre he podido hacerlo": 0, "no tanto ahora": 1,
     "sin duda mucho menos ahora": 2, "no en absoluto": 3},
    {"tanto como siempre": 0, "algo menos de lo que solia hacerlo": 1,
     "definitivamente menos de lo que solia hacerlo": 2, "practicamente nunca": 3},
    {"no nunca": 0, "no muy a menudo": 1, "si algunas veces": 2, "si casi siempre": 3},
    {"no en absoluto": 0, "casi nada": 1, "si a veces": 2, "si muy amenudo": 3,
     "si muy a menudo": 3},
    {"no en absoluto": 0, "no no mucho": 1, "si a veces": 2, "si bastante": 3},
    {"no he podido sobrellevarlas tan bien como lo he hecho simpre": 0,
     "no he podido sobrellevarlas tan bien como lo he hecho siempre": 0,
     "no la mayoria de las veces he podido sobrellevarlas bastante bien": 1,
     "si a veces no he podido sobrellevarlas de la mejor manera": 2,
     "si la mayor parte del tiempo no he podido sobrellevarllas": 3,
     "si la mayor parte del tiempo no he podido sobrellevarlas": 3},
    {"no en absoluto": 0, "no muy a menudo": 1, "si a veces": 2, "si casi siempre": 3},
    {"no en absoluto": 0, "no muy a menudo": 1, "si a veces": 2, "si casi siempre": 3},
    {"no nunca": 0, "no muy a menudo": 1, "si a veces": 2, "si casi siempre": 3},
    {"no nunca": 0, "casi nunca": 1, "a veces": 2, "si bastante a menudo": 3},
)


@dataclass(frozen=True)
class Bloque:
    """Un bloque de ítems contiguos del formulario."""
    key: str
    nombre: str
    prefijo: str                 # columnas PREFIJO1..N
    inicio: int                  # posición de la primera columna
    n_items: int
    mapas: tuple                 # un dict por ítem (mismo dict repetido si es uno solo)
    valor_min: int
    valor_max: int
    marco: str
    fuente: str
    faltantes: frozenset = frozenset()   # etiquetas que cuentan como faltante declarado

    @property
    def columnas(self) -> list[str]:
        return [f"{self.prefijo}{i}" for i in range(1, self.n_items + 1)]

    @property
    def posiciones(self) -> list[int]:
        return list(range(self.inicio, self.inicio + self.n_items))


def _repetir(mapa: dict, n: int) -> tuple:
    return tuple(mapa for _ in range(n))


BARRIO = Bloque("BARRIO", "Riesgo del barrio", "BARRIO", 20, 5, _repetir(MAP_BARRIO, 5),
                0, 2, MARCO_CUIDADOR,
                "Cinco preguntas del formulario: drogas, delincuencia, riñas, "
                "violencia grave y pandillas (0 = no, 1 = baja frecuencia, 2 = muy frecuente)")
PSS = Bloque("PSS", "PSS-10 — Estrés percibido", "PSS", 25, 10, _repetir(MAP_PSS, 10),
             0, 4, MARCO_CUIDADOR,
             "Cohen, Kamarck y Mermelstein (1983); mismos ítems, orden e inversos que "
             "la PSS de docentes", faltantes=frozenset({"columna 6"}))
EPDS = Bloque("EPDS", "EPDS-10 — Escala de Edimburgo", "EPDS", 35, 10, EPDS_MAPAS,
              0, 3, MARCO_CUIDADOR, "Cox, Holden y Sagovsky (1987); versión en español")
MSPSS = Bloque("MSPSS", "MSPSS — Apoyo social percibido del cuidador", "MSPSS", 45, 12,
               _repetir(MAP_MSPSS, 12), 1, 5, MARCO_CUIDADOR,
               "Zimet et al. (1988), escala de 5 puntos; en este formulario el reparto "
               "es 5 / 4 / 3 ítems (persona especial, familia, amigos)")
APQ = Bloque("APQ", "APQ — Prácticas de crianza", "APQ", 57, 25, _repetir(MAP_APQ, 25),
             1, 5, MARCO_CUIDADOR,
             "Alabama Parenting Questionnaire (Frick, 1991); subescalas pendientes del "
             "libro de códigos")
EP = Bloque("EP", "Estrés parental (39 ítems)", "EP", 82, 39, _repetir(MAP_ACUERDO, 39),
            1, 5, MARCO_CUIDADOR,
            "Formato tipo PSI con 39 ítems; no es el PSI-SF estándar. Sin total ni "
            "subescalas hasta el libro de códigos")
BLOQUES_CUIDADOR = (BARRIO, PSS, EPDS, MSPSS, APQ, EP)

# Bloques del niño: el mismo instrumento en dos lugares (hijo 1 y hijo 2).
SDQ_INICIO = {1: 121, 2: 153}
ARI_INICIO = {1: 186, 2: 193}


def bloque_sdq(hijo: int) -> Bloque:
    return Bloque("SDQ", "SDQ — versión para padres", "SDQ", SDQ_INICIO[hijo], 25,
                  _repetir(MAP_SDQ_PADRES, 25), 0, 2, MARCO_NINO,
                  "Goodman (1997); bandas de la versión para padres 4-17, sdqinfo.org")


def bloque_ari(hijo: int) -> Bloque:
    return Bloque("ARI", "ARI — versión para padres", "ARI", ARI_INICIO[hijo], 7,
                  _repetir(MAP_ARI_PADRES, 7), 0, 2, MARCO_NINO,
                  "Stringaris et al. (2012), versión para padres")


# ── Verificación de encabezados (fragmento normalizado por posición) ────────
VERIFICAR = {
    0: "marca temporal", 1: "consentimiento informado", 2: "quien esta respondiendo",
    3: "indique su nombre completo", 4: "nombre completo de su hijo",
    5: "que edad tiene el nino", 6: "sexo del nino", 7: "en que colegio estudia su hijo",
    9: "en que curso esta", 10: "vive con la mama", 12: "nivel educativo de la madre",
    13: "vive con el papa", 15: "nivel educativo del padre", 17: "desempeno academico",
    18: "en que zona", 19: "estrato socioeconomico",
    20: "relacionados con drogas", 24: "pandillas",
    25: "no podia controlar las cosas importantes",
    34: "tantas dificultades que no podia solucionarlas",
    35: "he podido reir", 44: "he pensado en hacerme dano",
    45: "compartir mis tristezas", 50: "mi familia trata de ayudarme",
    54: "contar con mis amigos", 56: "mis amigos tratan de ayudarme",
    57: "conversaciones amigables", 78: "nalgadas", 79: "cachetadas", 80: "correa",
    81: "grita a su hijo", 82: "no puedo controlar muy bien las situaciones",
    103: "soy muy bueno a como padre", 117: "lograr que mi hijo a haga algo es muy facil",
    120: "me exige mas de lo que exigen",
    121: "tiene en cuenta los sentimientos", 145: "termina lo que empieza",
    146: "otro de sus hijos", 147: "nombre completo de su hijo a 2",
    148: "edad de su hijo", 149: "sexo del nino a 2",
    150: "nombre completo del colegio 2", 152: "en que curso este su hijo",
    153: "tiene en cuenta los sentimientos", 177: "termina lo que empieza",
    179: "telefonico",
    186: "irritan facilmente", 192: "irritabilidad le causa problemas",
    193: "irritan facilmente", 199: "irritabilidad le causa problemas",
}

# ── Quién responde ──────────────────────────────────────────────────────────
MAMA, PAPA, OTRO = "Mamá", "Papá", "Otro cuidador"
PRIORIDAD_QUIEN = {MAMA: 0, PAPA: 1, OTRO: 2}

# ── Grados ──────────────────────────────────────────────────────────────────
GRADOS = ("Transición", "Primero", "Segundo", "Tercero", "Cuarto", "Quinto", "Sexto",
          "Séptimo", "Octavo", "Noveno", "Décimo", "Once")
# Los del estudio, con los mismos nombres que estudiantes (para la triangulación).
GRADOS_ESTUDIO = tuple(cat_est.ORDEN_GRADOS_PRI + cat_est.ORDEN_GRADOS_SEC)
FUERA_DE_RANGO = "Fuera del rango del estudio"
SIN_DATO = "Sin dato"
ESTADO_ESTUDIO, ESTADO_FUERA, ESTADO_SIN_DATO = "estudio", "fuera_de_rango", "sin_dato"
PALABRAS_GRADO = {
    "transicion": 0, "preescolar": 0, "jardin": 0, "prejardin": 0, "kinder": 0,
    "prekinder": 0, "primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "setimo": 7, "octavo": 8, "noveno": 9, "decimo": 10,
    "once": 11, "undecimo": 11,
}

# Edad del niño válida para el SDQ de padres.
EDAD_SDQ = (4, 17)

# ── Puntuaciones ────────────────────────────────────────────────────────────
PSS_INVERSOS = (3, 4, 5, 7, 9)          # = preparar_docentes.INVERTIDOS (PSS3…PSS9)
PSS_MIN_ITEMS = 9                        # se prorratea con 9 de 10
MSPSS_FUENTES = {"MSPSS_Otro": tuple(range(1, 6)), "MSPSS_Fam": tuple(range(6, 10)),
                 "MSPSS_Amigos": tuple(range(10, 13))}
EPDS_POSIBLE, EPDS_PROBABLE = 10, 13
EPDS_ITEM_AUTOLESION = 10
# Castigo físico = alguno de los ítems 22–24 «a veces» o más. Conservador: el
# indicador queda FALTANTE si falta cualquiera de los tres ítems, aunque otro
# ya marque «a veces» o más (scoring.puntuar_cuidadores). Así la base es la
# misma para todos y nadie cuenta como caso con respuestas incompletas.
APQ_FISICO = {22: "Nalgadas con la mano", 23: "Cachetadas", 24: "Golpes con correa u objeto"}
APQ_FISICO_FALTANTE = ("Castigo físico: el indicador queda faltante si falta cualquiera de "
                       "los ítems 22, 23 o 24 (criterio conservador), aunque otro ya marque "
                       "«a veces» o más.")
APQ_GRITO = 25
APQ_UMBRAL = MAP_APQ["a veces"]          # «a veces o más»
EP_ELECCION_FORZADA = (22, 23, 24, 25, 26)   # columnas 103–107: una sola pregunta partida
EP_POSITIVO = (36,)                          # columna 117, redactada en positivo
ARI_ITEMS_TOTAL = (1, 2, 3, 4, 5, 6)
ARI_ITEM_DETERIORO = 7


@dataclass(frozen=True)
class Puntuacion:
    clave: str
    label: str
    label_llano: str
    rango: tuple
    direccion: str          # "riesgo" | "protector"
    marco: str
    fuente: str


PUNTUACIONES: tuple[Puntuacion, ...] = (
    Puntuacion("PSS_Total", "Estrés percibido (PSS-10)", "Estrés de la vida diaria",
               (0, 40), "riesgo", MARCO_CUIDADOR, PSS.fuente),
    Puntuacion("EPDS_Total", "Ánimo (EPDS-10)", "Ánimo del cuidador", (0, 30), "riesgo",
               MARCO_CUIDADOR, EPDS.fuente),
    Puntuacion("MSPSS_Total", "Apoyo social total (12 ítems)", "Apoyo que tiene en general",
               (1, 5), "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("MSPSS_Otro", "Apoyo de una persona especial (5 ítems)",
               "Una persona especial", (1, 5), "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("MSPSS_Fam", "Apoyo de la familia (4 ítems)", "Su familia", (1, 5),
               "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("MSPSS_Amigos", "Apoyo de los amigos (3 ítems)", "Sus amigos", (1, 5),
               "protector", MARCO_CUIDADOR, MSPSS.fuente),
    Puntuacion("BARRIO_Indice", "Riesgo del barrio (0–10)", "Seguridad del barrio",
               (0, 10), "riesgo", MARCO_CUIDADOR, BARRIO.fuente),
    Puntuacion("SDQ_Total", "SDQ padres: total de dificultades", "Dificultades en total",
               (0, 40), "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Emo", "SDQ padres: síntomas emocionales", "Tristeza, preocupación y miedos",
               (0, 10), "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Con", "SDQ padres: problemas de conducta", "Peleas, desobediencia y mentiras",
               (0, 10), "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Hip", "SDQ padres: hiperactividad e inatención",
               "Inquietud y dificultad para concentrarse", (0, 10), "riesgo", MARCO_NINO,
               "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Pares", "SDQ padres: problemas con pares",
               "Sentirse solo o molestado por otros", (0, 10), "riesgo", MARCO_NINO,
               "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Pro", "SDQ padres: conducta prosocial", "Ayudar y compartir con otros",
               (0, 10), "protector", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Int", "SDQ padres: internalizante", "Malestar hacia adentro", (0, 20),
               "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("SDQ_Ext", "SDQ padres: externalizante", "Malestar hacia afuera", (0, 20),
               "riesgo", MARCO_NINO, "Goodman (1997), versión para padres"),
    Puntuacion("ARI_Total", "Irritabilidad según el cuidador (ARI-P, ítems 1–6)",
               "Enojo frecuente e intenso", (0, 12), "riesgo", MARCO_NINO,
               "Stringaris et al. (2012), versión para padres; cobertura parcial"),
)
PUNTUACIONES_POR_CLAVE = {p.clave: p for p in PUNTUACIONES}
CLAVES_CUIDADOR = [p.clave for p in PUNTUACIONES if p.marco == MARCO_CUIDADOR]
CLAVES_NINO = [p.clave for p in PUNTUACIONES if p.marco == MARCO_NINO]
# Sin corte clínico: terciles de la muestra.
CLAVES_TERCILES = ("PSS_Total", "MSPSS_Total", "MSPSS_Otro", "MSPSS_Fam", "MSPSS_Amigos",
                   "BARRIO_Indice")


def label(clave: str) -> str:
    p = PUNTUACIONES_POR_CLAVE.get(clave)
    return p.label if p else clave


# ── Señales del adulto (spec §5.5) ─────────────────────────────────────────
# Solo las definiciones. Mensajes, textos por rol y tarjetas de comunidad: 4b.
@dataclass(frozen=True)
class AlertaAdulto:
    clave: str
    nombre: str
    regla: str
    columna: str           # indicador 0/1 por cuidador


ANIMO, AUTOLESION = "animo", "autolesion"
ALERTAS = {
    ANIMO: AlertaAdulto(ANIMO, "Ánimo", f"EPDS-10 ≥ {EPDS_PROBABLE} (probable)",
                        "EPDS_Probable"),
    AUTOLESION: AlertaAdulto(AUTOLESION, "Autolesión",
                             "EPDS ítem 10 («He pensado en hacerme daño») con cualquier "
                             "respuesta distinta de «No, nunca»", "EPDS_Autolesion"),
}


def ruta_adulto(rol: str) -> list[tuple[str, str]]:
    """Ruta de atención para adultos; la vigente de estudiantes hasta que el equipo apruebe."""
    from src.estudiantes import alertas_catalogo
    return alertas_catalogo.ruta(rol, "adulto")


# Tarjetas de la vista de comunidad (spec §5.5). Las arma la fase 4b.
TARJETAS_4B = (
    ("estres", "Estrés de crianza"),
    ("animo", "Ánimo del cuidador"),
    ("apoyo", "Apoyo que tiene"),
    ("crianza", "Crianza positiva y castigo físico"),
    ("barrio", "Seguridad del barrio"),
    ("hijo", "Cómo ve el cuidador al hijo"),
)

# ── Avisos fijos de la vista de investigadores ──────────────────────────────
AVISO_EPDS = ("La EPDS se validó en el periodo perinatal. Aquí se lee como tamizaje del "
              "ánimo del cuidador, no como diagnóstico ni como medida de depresión posparto.")
AVISO_ARI = ("El ARI de padres se añadió al formulario en 2026: no hay respuestas de la ola "
             "2025 y la cobertura es parcial. Sus cifras describen solo a quienes lo "
             "respondieron.")
AVISO_ESTRES_PARENTAL = ("Estrés parental: no se calcula total ni subescalas hasta confirmar "
                         "con el libro de códigos la dirección de los ítems. Las columnas "
                         "103–107 son las cinco opciones de una sola pregunta de elección "
                         "forzada y la 117 está redactada en positivo. Aquí solo se describen "
                         "los ítems.")
AVISO_APQ = ("APQ: mientras no llegue el libro de códigos solo se reportan el castigo físico "
             "(nalgadas, cachetadas, correa u objeto) como «usa alguna forma, a veces o más» "
             "y el grito, de forma descriptiva. La Ley 2089 de 2021 prohíbe el castigo "
             "físico; el texto para la comunidad lo planteará como acompañamiento.")
AVISO_MSPSS = ("El MSPSS del cuidador reparte los ítems 5 / 4 / 3 (persona especial, familia, "
               "amigos) y su redacción no es la de estudiantes: solo se compara por fuente, "
               "sobre todo familia, y con este aviso.")
AVISO_SDQ_EDAD = (f"SDQ de padres: solo se puntúa a los niños con una edad numérica de "
                  f"{EDAD_SDQ[0]} a {EDAD_SDQ[1]} años (spec §5.5). Con una edad no numérica, "
                  "vacía o fuera de ese rango, el SDQ queda como faltante; las edades no "
                  "numéricas y fuera de rango se declaran en la calidad de datos.")
AVISO_OLA = ("El filtro de ola solo existe en esta vista local: nada se publica por ola.")
AVISO_MINIMO = (f"Ningún grupo con menos de {MIN_GROUP_N} cuidadores distintos se muestra "
                "desagregado; en el marco de niños el mínimo también cuenta cuidadores, no "
                "niños.")
