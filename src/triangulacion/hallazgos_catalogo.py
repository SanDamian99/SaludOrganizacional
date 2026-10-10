"""
Catálogo de hallazgos e hipótesis del «Resumen» de la Triangulación 360.

TEXTOS FIJOS, pendientes de aprobación del equipo (`TEXTOS_APROBADOS = False`).
Vienen del análisis exploratorio `docs/analisis/2026-10-10-hallazgos-triangulacion.md`
(§0, §F y §G) y de la decisión del usuario del 10 oct 2026: entran los ocho
hallazgos fuertes (1–8) y las hipótesis que se apoyan SOLO en ellos (H1, H4,
H8, H10, H11, H12); los moderados (9–12) no entran todavía, ni las hipótesis
que dependían de ellos (H2 y H3, que se apoyaban en los hallazgos 9 y 13). Nunca los redacta ni los cambia la IA en tiempo de
ejecución: la vista solo rellena cifras que ya están en las tablas publicadas.

Cada hallazgo dice a qué actor le es relevante (colegio, Secretaría, familias,
docentes), en qué bloque va (patrón entre actores o tensión), qué tabla lo
sustenta y qué hipótesis lo acompañan. La regla con la que una corrida lo
sustenta (o no) vive en `hallazgos.py`.
"""
from __future__ import annotations

from dataclasses import dataclass

TEXTOS_APROBADOS = False
ESTADO_TEXTOS = "Textos pendientes de aprobación del equipo (10 oct 2026)."

PATRON, TENSION = "patron", "tension"
COLEGIO, SECRETARIA, FAMILIAS, DOCENTES = "colegio", "Secretaría", "familias", "docentes"
ACTORES = (COLEGIO, SECRETARIA, FAMILIAS, DOCENTES)


@dataclass(frozen=True)
class Hallazgo:
    numero: int
    bloque: str                 # PATRON | TENSION
    actores: tuple              # a quién le sirve
    titulo: str
    texto: str                  # el texto fijo del panel
    robustez: str
    sustento: str               # qué tabla publicada lo sustenta (texto fijo)
    hipotesis: tuple = ()       # ids de HIPOTESIS


@dataclass(frozen=True)
class Hipotesis:
    id: str
    texto: str
    patron: str
    alternativas: str
    prueba: str
    confianza: str


HALLAZGOS: tuple[Hallazgo, ...] = (
    Hallazgo(
        1, PATRON, (FAMILIAS, COLEGIO),
        "Los niños reportan más dificultades que las que ven sus cuidadores, y el acuerdo "
        "es bajo",
        "Los niños y niñas describen más dificultades emocionales de las que perciben sus "
        "cuidadores. Escuchar directamente a los niños aporta información que la familia no "
        "siempre ve.",
        "Fuerte", "díadas · acuerdo SDQ (diferencia niño − cuidador y CCI)", ("H1",)),
    Hallazgo(
        2, PATRON, (FAMILIAS, SECRETARIA),
        "Lo que un cuidador reporta de su hijo refleja sobre todo su propio malestar",
        "Cuando el cuidador está más estresado o desanimado, tiende a describir más "
        "dificultades en su hijo. Cuidar al cuidador también cambia cómo ve a su hijo.",
        "Fuerte", "díadas · informante (ρ con el reporte del cuidador y con el del niño)",
        ("H1",)),
    Hallazgo(
        3, PATRON, (COLEGIO, SECRETARIA),
        "La señal de malestar (SDQ) y el ítem 18 del RCADS identifican a estudiantes "
        "distintos",
        "La señal de malestar y la señal de desesperanza identifican a estudiantes "
        "distintos: ninguna reemplaza a la otra.",
        "Fuerte (para el diseño de alertas)", "capa 1 · cifras municipales (señales)",
        ("H12",)),
    Hallazgo(
        4, PATRON, (FAMILIAS, SECRETARIA),
        "El apoyo familiar del cuidador acompaña a su ánimo",
        "Los cuidadores que sienten más apoyo de su familia tienen mejor ánimo. Las redes "
        "de apoyo familiar son un punto de entrada.",
        "Fuerte (transversal)", "capa 1 · cifras municipales (ánimo por tercil de apoyo)",
        ("H4",)),
    Hallazgo(
        5, PATRON, (DOCENTES, FAMILIAS, SECRETARIA),
        "Cuidadores y docentes tienen el mismo nivel de estrés percibido",
        "Cuidadores y docentes reportan un nivel de estrés muy parecido: el estrés es un "
        "tema compartido por los adultos que rodean a los estudiantes.",
        "Fuerte", "capa 1 · cifras municipales (PSS-10 en cuidadores y docentes)", ()),
    Hallazgo(
        6, PATRON, (COLEGIO, SECRETARIA),
        "El adulto de confianza en el colegio disminuye con el grado",
        "A medida que avanzan de grado, menos estudiantes sienten que tienen un adulto de "
        "confianza en el colegio.",
        "Fuerte", "capa 1 · por grado (sin adulto de confianza, PSSM 7)", ("H11",)),
    Hallazgo(
        7, TENSION, (COLEGIO, DOCENTES, FAMILIAS),
        "Perfil invertido entre actores: lado familiar favorable y clima docente "
        "desfavorable",
        "En este colegio, estudiantes y familias reportan un buen apoyo familiar, mientras "
        "que los docentes reportan más presión de trabajo y menos apoyo de sus directivos.",
        "Fuerte (descriptivo)",
        "capa 1 · por colegio (apoyo familiar niño–cuidador en coincidencia; apoyo del "
        "líder y demandas de los docentes)", ("H10",)),
    Hallazgo(
        8, PATRON, (DOCENTES, SECRETARIA),
        "Las demandas pesan más que el apoyo del líder en el desgaste docente",
        "El desgaste de los docentes se asocia con las demandas y la presión de tiempo; el "
        "apoyo del líder también se asocia a menos desgaste, pero con la mitad del peso de "
        "las demandas o menos.",
        "Moderado-fuerte", "capa 1 · cifras municipales (modelo del desgaste docente)",
        ("H8",)),
)
POR_NUMERO = {h.numero: h for h in HALLAZGOS}

HIPOTESIS: tuple[Hipotesis, ...] = (
    Hipotesis(
        "H1",
        "El malestar del cuidador (ánimo, estrés, estrés parental) amplifica su reporte "
        "de las dificultades del hijo (sesgo de depresión-distorsión).",
        "Correlación alta con su propio reporte del niño y baja con el reporte del niño; "
        "la discrepancia entre informantes sigue al malestar del cuidador.",
        "El niño sí se comporta peor en casa (conducta específica del contexto); el estrés "
        "del padre es consecuencia de la conducta del hijo; varianza de método compartido.",
        "SDQ-docente del mismo niño (tercer informante); segunda ola con enlace (panel "
        "cruzado); observación estructurada.",
        "Asociación alta; dirección baja-media."),
    Hipotesis(
        "H4",
        "El apoyo familiar protege el ánimo del cuidador (amortiguación del estrés).",
        "El porcentaje con EPDS ≥ 13 baja de forma marcada del tercil bajo al alto de "
        "apoyo familiar.",
        "La depresión reduce el apoyo percibido (causalidad inversa); el estrato "
        "socioeconómico confunde.",
        "Cuidadores que respondieron las dos olas (si se pueden enlazar); ajustar por "
        "estrato y barrio; intervención de redes de apoyo.",
        "Asociación alta; dirección media."),
    Hipotesis(
        "H8",
        "El desgaste docente depende sobre todo de la organización del trabajo (demandas "
        "y presión de tiempo): el apoyo del líder sigue asociado al desgaste, pero con la "
        "mitad del peso de las demandas o menos.",
        "En el modelo del desgaste, la β de las demandas es al menos el doble de la del "
        "apoyo del líder, y las dos excluyen 0 en el sentido esperado.",
        "Método común (quien está agotado lo percibe todo peor); selección (quien se fue "
        "no respondió); el líder puede actuar a través de las demandas.",
        "Segunda ola con seudónimo docente; medidas objetivas (horas, estudiantes por "
        "docente, cargas).",
        "Media."),
    Hipotesis(
        "H10",
        "Perfil invertido entre actores: un colegio que moviliza mucho a las familias "
        "carga a sus docentes, y la tasa de respuesta selecciona a los cuidadores.",
        "Lado familiar favorable (estudiantes y cuidadores) junto a docentes con más "
        "demandas y menos apoyo del líder en el mismo colegio.",
        "Composición socioeconómica del área de influencia; ola; tamaño del colegio; "
        "selección diferencial por respuesta.",
        "Denominadores (matrícula y tasa de respuesta por colegio y actor); estrato y "
        "barrio; razón estudiantes por docente; segunda ola.",
        "Descripción alta; mecanismo bajo."),
    Hipotesis(
        "H11",
        "La transición a la secundaria erosiona el adulto de referencia: más docentes por "
        "estudiante, menos vínculo.",
        "El porcentaje sin adulto de confianza sube de grado en grado, también dentro de "
        "un mismo colegio.",
        "Efecto de cohorte; desarrollo adolescente normativo (autonomía); redacción del "
        "ítem.",
        "Seguir a la misma cohorte; preguntar por un adulto concreto; comparar colegios "
        "con tutor por curso.",
        "Patrón alto; mecanismo medio."),
    Hipotesis(
        "H12",
        "Los pensamientos frecuentes sobre la muerte del adolescente van por una vía "
        "distinta del malestar emocional general: menos pertenencia y apoyo familiar, más "
        "supresión emocional y problemas con pares.",
        "Solo una minoría de quienes marcan el ítem 18 con frecuencia tiene la señal de "
        "malestar; el ítem se asocia con la pertenencia y la supresión, no con el adulto "
        "de confianza.",
        "El ítem 18 es un solo ítem con poca fiabilidad; diferencias de interpretación "
        "del ítem.",
        "Validar con una escala breve (con protocolo de respuesta); análisis por clases "
        "latentes.",
        "Media (decisiva para el diseño de alertas)."),
)
HIPOTESIS_POR_ID = {h.id: h for h in HIPOTESIS}

TITULO_PERFIL = "Perfil por colegio"
TITULO_PATRONES = "Patrones entre actores"
TITULO_TENSION = "Dónde hay tensión"
TITULO_HIPOTESIS = "Hipótesis"
AVISO_HALLAZGOS = ("Hallazgos de un catálogo de textos fijos, pendientes de aprobación del "
                   "equipo. Cada uno se muestra solo si las tablas de esta corrida lo "
                   "sustentan; la cifra que lo acompaña sale de esas tablas (todas con 10 o "
                   "más). Ninguno es un diagnóstico ni una relación causal.")
AVISO_HIPOTESIS = ("Hipótesis de trabajo que acompañan a los hallazgos visibles. Los datos son "
                   "transversales y, por colegio, ecológicos: cada hipótesis trae sus "
                   "explicaciones alternativas y cómo ponerla a prueba.")
AVISO_SIN_HALLAZGOS = "Esta corrida no sustenta ninguno de los hallazgos de este bloque."
AVISO_SIN_TENSION = ("Ningún hallazgo de tensión se sostiene en el universo de la capa 1 con "
                     "esta corrida; abajo, los pares en tensión.")
AVISO_PERFIL = ("Por actor, los constructos en que el colegio difiere del resto del "
                "municipio (IC 95 % que excluye 0): ▲ mejor, ▼ peor; entre paréntesis, si "
                "el colegio tiene más o menos que el resto. En estudiantes, ajustado por "
                "grado.")
