"""
Catálogo de la Triangulación 360 — constructos, pares y textos fijos.

ÚNICA FUENTE DE VERDAD de la triangulación: qué constructo sale de qué actor y
de qué columna, hacia dónde es «mejor», qué pares hablan del mismo objeto y
los avisos fijos de la vista y de la metodología.

Los textos son provisionales (`TEXTOS_APROBADOS = False`) y los aprueba el
equipo (spec §8). Nunca los redacta la IA.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.cuidadores import catalog as cat_cuid
from src.estudiantes import catalog as cat_est

TEXTOS_APROBADOS = False

MIN_GROUP_N = cat_est.MIN_GROUP_N     # unidades distintas (cuidadores en cuidadores)
MIN_CASOS = 3                          # = estudiantes.supresion.MIN_CASOS
MIN_MODELO = 30                        # díadas completas para un modelo (como stats.modelo)
N_BOOT = 500
SEMILLA = 1
COLEGIOS_SIN_GRUPO = ("OTRO", "SIN_DATO")
COLEGIO_SENSIBILIDAD = "LauV"

# ── Marcos (de qué tabla sale cada constructo) y actores ───────────────────
ESTUDIANTE, CUIDADOR, NINO, DOCENTE = "estudiante", "cuidador", "nino", "docente"
ACTOR = {ESTUDIANTE: "Estudiantes", CUIDADOR: "Cuidadores", NINO: "Cuidadores",
         DOCENTE: "Docentes"}
# Columna que identifica a la unidad que cuenta para el mínimo de 10. En
# estudiantes y docentes cada fila es una persona; en cuidadores (también en
# el marco de niños) cuenta el cuidador distinto (spec §4).
UNIDAD = {ESTUDIANTE: None, CUIDADOR: "ID_cuidador", NINO: "ID_cuidador", DOCENTE: None}
MARCOS_GRADO = (ESTUDIANTE, CUIDADOR, NINO)       # los docentes no tienen grado

# ── Objetos y clasificación ─────────────────────────────────────────────────
MISMO_OBJETO, COOCURRENCIA = "mismo_objeto", "co-ocurrencia"
COINCIDENCIA, TENSION, SIN_DIFERENCIA, SIN_DATO = (
    "coincidencia", "tensión", "sin diferencia clara", "sin dato")


@dataclass(frozen=True)
class Constructo:
    clave: str
    marco: str
    columna: str
    etiqueta: str
    objeto: str
    direccion: int           # +1: más es mejor (protector); −1: más es peor (riesgo)
    binario: bool = False    # 0/1 por persona: se muestra como %
    corta: str = ""          # etiqueta corta para el cuadro por colegio del Resumen


CONSTRUCTOS: tuple[Constructo, ...] = (
    Constructo("est_sdq_total", ESTUDIANTE, "SDQ_Total",
               "Dificultades del niño, según él (SDQ autoinforme)", "conducta_total", -1,
               corta="dificultades (SDQ)"),
    Constructo("est_sdq_emo", ESTUDIANTE, "SDQ_Emo",
               "Síntomas emocionales, según el niño (SDQ autoinforme)", "conducta_emo", -1,
               corta="síntomas emocionales"),
    Constructo("est_sdq_con", ESTUDIANTE, "SDQ_Con",
               "Problemas de conducta, según el niño (SDQ autoinforme)", "conducta_con", -1,
               corta="problemas de conducta"),
    Constructo("est_sdq_hip", ESTUDIANTE, "SDQ_Hip",
               "Hiperactividad e inatención, según el niño (SDQ autoinforme)", "conducta_hip",
               -1, corta="hiperactividad"),
    Constructo("est_pssm", ESTUDIANTE, "PSSM_Total",
               "Pertenencia al colegio (PSSM)", "clima_escolar", +1, corta="pertenencia"),
    Constructo("est_sin_adulto", ESTUDIANTE, "SIN_ADULTO",
               "Sin un adulto de confianza en el colegio (PSSM 7)", "clima_escolar", -1,
               binario=True, corta="sin adulto de confianza"),
    Constructo("est_malestar", ESTUDIANTE, "ALERTA_malestar",
               "Señal de malestar del niño (6 ítems del SDQ)", "malestar_nino", -1,
               binario=True, corta="señal de malestar"),
    Constructo("est_mspss_fam", ESTUDIANTE, "MSPSS_Fam",
               "Apoyo de la familia que siente el niño (MSPSS)", "apoyo_familia", +1,
               corta="apoyo familiar"),
    Constructo("nin_sdq_total", NINO, "SDQ_Total",
               "Dificultades del niño, según su cuidador (SDQ padres)", "conducta_total", -1,
               corta="dificultades del hijo (SDQ padres)"),
    Constructo("nin_sdq_emo", NINO, "SDQ_Emo",
               "Síntomas emocionales, según su cuidador (SDQ padres)", "conducta_emo", -1,
               corta="síntomas emocionales del hijo"),
    Constructo("nin_sdq_con", NINO, "SDQ_Con",
               "Problemas de conducta, según su cuidador (SDQ padres)", "conducta_con", -1,
               corta="conducta del hijo"),
    Constructo("nin_sdq_hip", NINO, "SDQ_Hip",
               "Hiperactividad e inatención, según su cuidador (SDQ padres)", "conducta_hip",
               -1, corta="hiperactividad del hijo"),
    Constructo("cui_pss", CUIDADOR, "PSS_Total", "Estrés percibido del cuidador (PSS-10)",
               "estres", -1, corta="estrés"),
    Constructo("cui_epds", CUIDADOR, "EPDS_Total", "Ánimo del cuidador (EPDS-10)",
               "animo_adulto", -1, corta="ánimo (EPDS)"),
    Constructo("cui_fisico", CUIDADOR, "APQ_Fisico",
               "Usa alguna forma de castigo físico, a veces o más (APQ 22–24)", "crianza", -1,
               binario=True, corta="castigo físico"),
    Constructo("cui_barrio", CUIDADOR, "BARRIO_Indice", "Riesgo del barrio (0–10)", "barrio",
               -1, corta="riesgo del barrio"),
    Constructo("cui_mspss_fam", CUIDADOR, "MSPSS_Fam",
               "Apoyo de la familia que siente el cuidador (MSPSS)", "apoyo_familia", +1,
               corta="apoyo familiar"),
    Constructo("doc_pss", DOCENTE, "DOC_PSS", "Estrés percibido del docente (PSS-10)",
               "estres", -1, corta="estrés"),
    Constructo("doc_lider", DOCENTE, "DOC_LIDER",
               "Clima laboral: apoyo del líder (HSE, 7 ítems)", "clima_escolar", +1,
               corta="apoyo del líder"),
    Constructo("doc_grupo", DOCENTE, "DOC_GRUPO",
               "Apoyo percibido de los compañeros (HSE, 3 ítems)", "clima_escolar", +1,
               corta="apoyo de compañeros"),
    Constructo("doc_desgaste", DOCENTE, "DOC_DESGASTE",
               "Desgaste del docente (4 ítems, 1–7)", "desgaste", -1, corta="desgaste"),
    # Solo si el archivo de docentes trae los ítems MT4–7 (si no, la fila sale sin cifra).
    Constructo("doc_demandas", DOCENTE, "DOC_DEMANDAS",
               "Demandas y presión de tiempo del docente (HSE MT4–7)", "demandas", -1,
               corta="demandas / presión de tiempo"),
)
POR_CLAVE = {c.clave: c for c in CONSTRUCTOS}


@dataclass(frozen=True)
class Par:
    a: str
    b: str
    tipo: str              # MISMO_OBJETO | COOCURRENCIA
    titulo: str


PARES: tuple[Par, ...] = (
    Par("est_sdq_total", "nin_sdq_total", MISMO_OBJETO,
        "Conducta del niño: dificultades, según él y según su cuidador"),
    Par("est_sdq_emo", "nin_sdq_emo", MISMO_OBJETO,
        "Conducta del niño: síntomas emocionales, según él y según su cuidador"),
    Par("est_sdq_con", "nin_sdq_con", MISMO_OBJETO,
        "Conducta del niño: problemas de conducta, según él y según su cuidador"),
    Par("est_sdq_hip", "nin_sdq_hip", MISMO_OBJETO,
        "Conducta del niño: hiperactividad e inatención, según él y según su cuidador"),
    Par("est_pssm", "doc_lider", MISMO_OBJETO,
        "Clima escolar: pertenencia (estudiantes) y apoyo del líder (docentes)"),
    Par("est_pssm", "doc_grupo", MISMO_OBJETO,
        "Clima escolar: pertenencia (estudiantes) y apoyo de compañeros (docentes)"),
    Par("est_sin_adulto", "doc_lider", MISMO_OBJETO,
        "Clima escolar: adulto de confianza (estudiantes) y apoyo del líder (docentes)"),
    Par("est_sin_adulto", "doc_grupo", MISMO_OBJETO,
        "Clima escolar: adulto de confianza (estudiantes) y apoyo de compañeros (docentes)"),
    Par("cui_pss", "doc_pss", COOCURRENCIA,
        "Estrés (PSS-10): cuidadores y docentes, la misma escala en personas distintas"),
    Par("est_malestar", "cui_epds", COOCURRENCIA,
        "Malestar del niño y ánimo del cuidador"),
    Par("est_malestar", "doc_desgaste", COOCURRENCIA,
        "Malestar del niño y desgaste docente"),
    # Decisión del 10 oct 2026: la misma familia vista por dos de sus miembros
    # es el mismo objeto (antes: co-ocurrencia).
    Par("est_mspss_fam", "cui_mspss_fam", MISMO_OBJETO,
        "Apoyo de la familia: el que siente el niño y el que siente el cuidador"),
)

# ── Díadas (capa 2) ────────────────────────────────────────────────────────
SUBESCALAS_SDQ = ("SDQ_Total", "SDQ_Emo", "SDQ_Con", "SDQ_Hip", "SDQ_Pares", "SDQ_Pro")
FUENTES_MSPSS = (("MSPSS_Fam", "Familia"), ("MSPSS_Amigos", "Amigos"),
                 ("MSPSS_Otro", "Una persona especial"))
RESULTADOS = (("SDQ_Total", "Dificultades (SDQ autoinforme)"),
              ("SDQ_Int", "Internalizante (SDQ autoinforme)"),
              ("SDQ_Ext", "Externalizante (SDQ autoinforme)"))
PREDICTORES = (("EPDS_Total", "Ánimo del cuidador (EPDS, z)", False),
               ("PSS_Total", "Estrés del cuidador (PSS, z)", False),
               ("APQ_Fisico", "Castigo físico a veces o más (sí = 1)", True),
               ("BARRIO_Indice", "Riesgo del barrio (z)", False))
# «Malestar que el cuidador no ve»: (variante, subescala, ¿suma la señal de malestar?)
VARIANTES_NO_VISTO = (("Dificultades totales o señal de malestar (vigente)", "SDQ_Total", True),
                      ("Síntomas emocionales o señal de malestar (sensibilidad)", "SDQ_Emo",
                       True))
MAX_BINES_BA = 5
# El informante (hallazgo 2): el malestar del cuidador frente al SDQ total que
# da él mismo del niño y frente al que da el niño. (columna del cuidador, etiqueta)
PREDICTORES_INFORMANTE = (("EPDS_Total", "Ánimo del cuidador (EPDS)"),
                          ("PSS_Total", "Estrés del cuidador (PSS)"))
RESULTADO_INFORMANTE = "SDQ_Total"

# ── Cifras municipales de la capa 1 (sustento de los hallazgos 3, 4, 5 y 8) ──
ITEM_18 = "RCADS18"                   # «Pienso acerca de la muerte»
CORTE_ITEM_18 = 2                     # ≥ «Con frecuencia» (= alertas_catalogo.CON_FRECUENCIA)
EPDS_PROBABLE = "EPDS_Probable"       # EPDS ≥ 13, 0/1 (cuidadores.scoring)

# ── Avisos fijos ────────────────────────────────────────────────────────────
TITULO = "Triangulación 360 · equipo investigador"
TITULO_PUBLICO = "Triangulación 360"
AVISO_ECOLOGICO = ("Con {n} colegios esto es descriptivo y ecológico: compara promedios de "
                   "grupo, no personas, y no permite concluir relaciones individuales ni "
                   "causales. Cada actor se compara con el resto del municipio del mismo "
                   "actor, en unidades de su desviación estándar individual.")
AVISO_RESTO = ("«Resto del municipio» = las demás personas de ese actor que su módulo "
               "publica: los otros colegios publicados y, si el módulo lo admite, el resto R, "
               "que junta a los colegios con menos de 10, las respuestas fuera de las celdas "
               "publicables y las de colegio no reconocido (OTRO) o sin dato. En cuidadores "
               "solo entran grupos con todos sus niños en los grados del estudio. Si una de "
               "esas partes tiene entre 1 y 9 personas con dato en un constructo, sale entera "
               "de ese constructo (no puede deducirse restando).")
AVISO_GRADO = ("Por grado solo se comparan estudiantes y cuidadores: los docentes no "
               "tienen grado.")
AVISO_AJUSTE_GRADO = ("En estudiantes, la diferencia por colegio está ajustada por grado: d y "
                      "su IC se calculan sobre el residuo de la media del grado (así un "
                      "colegio con más grados altos no sale distinto solo por su mezcla de "
                      "grados); las medias que se muestran son brutas. Por grado no se ajusta.")
AVISO_COOCURRENCIA = ("«Co-ocurrencia»: dos cifras que se describen lado a lado sin llamarlas "
                      "acuerdo, porque no miden lo mismo o miden a personas distintas (la PSS "
                      "es la misma escala en cuidadores y docentes, pero son otras personas).")
AVISO_CLASIFICACION = ("«Tensión»: los intervalos de los dos actores excluyen el cero en "
                       "direcciones opuestas. «Coincidencia»: lo excluyen en la misma "
                       "dirección. En otro caso, «sin diferencia clara». Con muchas "
                       "comparaciones, alguna puede deberse al azar.")
AVISO_DESPLIEGUE = ("No hay en esta máquina los archivos de los tres actores (estudiantes, "
                    "cuidadores y docentes) y aún no hay una corrida de triangulación "
                    "publicada para el equipo. La máquina que procesa los formularios la sube "
                    "con «python -m src.triangulacion.publicar»: solo agregados; el equipo "
                    "la revisa oculta y, una vez publicada, la ve también el público.")
AVISO_PUBLICO_SIN_CORRIDA = ("Triangulación 360: aún no hay una corrida de triangulación "
                             "publicada. Vuelva más tarde.")
AVISO_ENLACE = ("Enlace exacto: el seudónimo HMAC del nombre normalizado del niño, calculado "
                "con la misma clave local en los dos formularios, y verificado con el "
                "colegio. No hay coincidencias aproximadas: un nombre escrito distinto no "
                "enlaza. Un seudónimo repetido dentro de un mismo colegio, en cualquiera de "
                "los dos formularios, es ambiguo: se descarta y se cuenta. Los seudónimos no "
                "se guardan ni se muestran.")
AVISO_DIADAS = ("Las díadas solo existen en la máquina que procesa los formularios. Toda "
                "cifra exige 10 o más díadas de 10 o más familias distintas; ninguna salida "
                "muestra una díada.")
AVISO_SDQ = ("Cada informante se lee con sus propias bandas: autoinforme para el niño y "
             "versión para padres para el cuidador (sdqinfo.org). " + cat_est.AVISO_PRIMARIA)
AVISO_MSPSS = cat_cuid.AVISO_MSPSS
AVISO_ASOCIACIONES = ("Regresión lineal con efecto fijo de colegio, controles de sexo y edad "
                      "del niño y errores agrupados por familia (cuidador). Con 4 colegios no "
                      "se usan errores agrupados por colegio; la sensibilidad repite el "
                      "análisis solo con Laura Vicuña. Son asociaciones, no efectos causales.")
AVISO_SENSIBILIDAD_CONCORDANCIA = (
    "Sensibilidad de concordancia: el acuerdo SDQ y las asociaciones se repiten sin las "
    "díadas en que el niño y su cuidador no concuerdan en sexo, edad (más de ± 1 año) o "
    "grado (sin dato en alguno no cuenta como discordancia). Solo se muestra si las "
    "díadas excluidas son 0 o 10 o más de 10 o más familias; si no, saldrían restando.")
AVISO_BLAND_ALTMAN = ("Bland–Altman agrupado: cada punto es el promedio de un grupo de 10 o "
                      "más díadas (quintiles del promedio de los dos informantes); no se "
                      "dibuja ninguna díada.")
AVISO_TEXTOS = ("Textos provisionales: el equipo los revisa antes de usarlos fuera de esta "
                "vista.")
AVISO_MUNICIPAL = ("Cifras municipales de la capa 1, sobre el mismo universo de personas que "
                   "las comparaciones por colegio: el cruce de la señal de malestar con el "
                   "ítem 18 (secundaria; solo si las cuatro celdas tienen 10 o más; el n del % "
                   "entre quienes marcan el ítem 18 es ese denominador), el ánimo del cuidador "
                   "por tercil de apoyo familiar (cortes por valor del puntaje, sin partir "
                   "empates: con muchos empates quedan dos grupos, bajo y alto; cada grupo con "
                   "10 o más cuidadores y 3 ≤ casos ≤ n − 3), la PSS-10 en cuidadores y "
                   "docentes (media con IC y d con IC de Welch) y el desgaste docente sobre los "
                   "predictores que trae el archivo (demandas, exigencias psicológicas, "
                   "conflicto de rol, conflicto familia→trabajo, claridad de rol y apoyo del "
                   "líder; MCO estandarizado, errores agrupados por colegio, sin docentes de "
                   "colegio no reconocido; fila r2 = R²).")
AVISO_INFORMANTE = ("El informante: correlación de Spearman (IC por bootstrap de familias) del "
                    "ánimo y el estrés del cuidador con el SDQ total que él mismo da del niño "
                    "y con el que da el niño. Si la primera es mayor que la segunda, lo que el "
                    "cuidador reporta del niño refleja en parte su propio malestar.")
