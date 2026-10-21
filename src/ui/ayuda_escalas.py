"""
Glosario de escalas para las vistas de investigador (estudiantes, cuidadores,
triangulación).

Las tablas del investigador listan escalas por su sigla (SDQ_Emo, RCADS_Dep,
MSPSS_Fam…). Aquí cada una trae lo mismo que la ayuda de los selectores de la
vista comunitaria (`ayuda_indicador`): qué mide, dos ítems literales del
formulario y qué significa un puntaje alto y uno bajo. Los ítems son los
enunciados de los encabezados de cada formulario; solo se corrigieron erratas.

Funciones puras (`glosario`, `texto_escala`): las prueban los tests. `mostrar`
es la única que dibuja.
"""
from __future__ import annotations

from src.ui import ayuda_indicador as ay

_a = ay.Ayuda

# ── Estudiantes: autoinforme, clave = subescala del catálogo ─────────────────
ESTUDIANTES: dict[str, tuple[str, ay.Ayuda]] = {
    "SDQ_Total": ("SDQ · total de dificultades", _a(
        "las cuatro escalas de dificultades del SDQ juntas (20 ítems, 0–40).",
        ("Me siento a menudo triste, desanimado o con ganas de llorar",
         "Peleo mucho. Y muchas veces lo hago para obtener lo que quiero"),
        "más dificultades emocionales y de conducta; sus bandas van de «cercano al promedio» a «muy alto».",
        "pocas dificultades.")),
    "SDQ_Emo": ("SDQ · síntomas emocionales", _a(
        "tristeza, preocupación y miedos (5 ítems, 0–10).",
        ("Me siento a menudo triste, desanimado o con ganas de llorar",
         "Tengo muchos miedos, me asusto fácilmente"),
        "más síntomas emocionales.", "pocos síntomas emocionales.")),
    "SDQ_Con": ("SDQ · problemas de conducta", _a(
        "peleas, desobediencia y mentiras (5 ítems, 0–10).",
        ("Peleo mucho. Y muchas veces lo hago para obtener lo que quiero",
         "A menudo me acusan de mentir o de hacer trampa"),
        "más problemas de conducta.", "pocos problemas de conducta.")),
    "SDQ_Hip": ("SDQ · hiperactividad e inatención", _a(
        "inquietud y dificultad para concentrarse (5 ítems, 0–10).",
        ("Soy inquieto/a, no puedo permanecer quieto/a por mucho tiempo",
         "Me distraigo con facilidad, me cuesta concentrarme"),
        "más inquietud e inatención.", "poca inquietud; se concentra con facilidad.")),
    "SDQ_Pares": ("SDQ · problemas con pares", _a(
        "sentirse solo o molestado por otros (5 ítems, 0–10).",
        ("Otros niños de mi edad me molestan o se burlan de mí",
         "Soy más bien solitario/a y tiendo a jugar solo/a"),
        "más problemas con sus compañeros.", "buena relación con sus compañeros.")),
    "SDQ_Pro": ("SDQ · conducta prosocial", _a(
        "ayudar y compartir con otros (5 ítems, 0–10). Es una fortaleza.",
        ("Ayudo a alguien si se lastima, está triste o se siente mal",
         "Normalmente comparto con otros mis juegos, lápices, útiles, etc."),
        "más conducta de ayuda y cooperación (mejor).", "menos conducta prosocial.")),
    "SDQ_Int": ("SDQ · internalizante", _a(
        "malestar hacia adentro: síntomas emocionales más problemas con pares (10 ítems, 0–20).",
        ("Tengo muchos miedos, me asusto fácilmente",
         "Soy más bien solitario/a y tiendo a jugar solo/a"),
        "más malestar hacia adentro.", "poco malestar hacia adentro.")),
    "SDQ_Ext": ("SDQ · externalizante", _a(
        "malestar hacia afuera: conducta más hiperactividad (10 ítems, 0–20).",
        ("Peleo mucho. Y muchas veces lo hago para obtener lo que quiero",
         "Me distraigo con facilidad, me cuesta concentrarme"),
        "más malestar hacia afuera.", "poco malestar hacia afuera.")),
    "ARI_Total": ("ARI · irritabilidad", _a(
        "enojo frecuente e intenso (6 ítems, 0–12).",
        ("Pierdo la paciencia frecuentemente", "Permanezco enojado(a) mucho tiempo"),
        "más irritabilidad; por encima de 2 es un cribado, no un diagnóstico.",
        "poca irritabilidad.")),
    "RCADS_Dep": ("RCADS · depresión", _a(
        "tristeza persistente y falta de energía (10 ítems, 0–30).",
        ("Me siento triste o vacío/a", "Ya nada me divierte mucho"),
        "más síntomas de depresión.", "pocos síntomas de depresión.")),
    "RCADS_Anx": ("RCADS · ansiedad", _a(
        "miedos y preocupaciones (15 ítems, 0–45).",
        ("Me preocupo cuando pienso que no hice algo bien",
         "Me preocupa que algo malo me vaya a suceder"),
        "más síntomas de ansiedad.", "pocos síntomas de ansiedad.")),
    "RCADS_Total": ("RCADS · ansiedad y depresión", _a(
        "ansiedad y depresión juntas (25 ítems, 0–75).",
        ("Me siento triste o vacío/a", "Me preocupa que algo malo me vaya a suceder"),
        "más síntomas de ansiedad y depresión.", "pocos síntomas.")),
    "ERQ_Reap": ("ERQ · reevaluación", _a(
        "manejar una emoción cambiando la forma de pensar la situación (6 ítems, 1–5).",
        ("Cuando me enfrento a una situación estresante, intento pensar sobre esa situación "
         "de una forma que me ayude a mantener la calma",
         "Controlo mis emociones cambiando mi manera de pensar acerca de la situación en la "
         "que estoy"),
        "usa mucho esta estrategia, que suele ser favorable.", "la usa poco."),),
    "ERQ_Sup": ("ERQ · supresión", _a(
        "guardarse lo que siente (4 ítems, 1–5).",
        ("Me reservo mis emociones para mí mismo/a", "Controlo mis emociones, no expresándolas"),
        "se guarda lo que siente con frecuencia, algo que suele asociarse a más malestar.",
        "expresa lo que siente.")),
    "MSPSS_Total": ("MSPSS · apoyo total", _a(
        "apoyo que el estudiante siente de su familia, sus amigos y una persona especial "
        "(12 ítems, 1–5).",
        ("Mi familia realmente intenta ayudarme.",
         "Puedo contar con mis amigos cuando las cosas van mal."),
        "siente mucho apoyo (mejor).", "siente poco apoyo.")),
    "MSPSS_Otro": ("MSPSS · persona especial", _a(
        "apoyo de una persona especial (4 ítems, 1–5).",
        ("Hay una persona especial que está cerca cuando la necesito.",
         "Tengo una persona especial que es una verdadera fuente de consuelo para mí."),
        "siente mucho apoyo de esa persona (mejor).", "siente poco apoyo de esa persona.")),
    "MSPSS_Fam": ("MSPSS · familia", _a(
        "apoyo de su familia (4 ítems, 1–5).",
        ("Mi familia realmente intenta ayudarme.", "Puedo hablar de mis problemas con mi familia."),
        "siente mucho apoyo familiar (mejor).", "siente poco apoyo familiar.")),
    "MSPSS_Amigos": ("MSPSS · amigos", _a(
        "apoyo de sus amigos (4 ítems, 1–5).",
        ("Mis amigos realmente tratan de ayudarme.",
         "Puedo hablar de mis problemas con mis amigos"),
        "siente mucho apoyo de sus amigos (mejor).", "siente poco apoyo de sus amigos.")),
    "PSSM_Total": ("PSSM · pertenencia al colegio", _a(
        "qué tan parte del colegio se siente (18 ítems, 1–5; los 5 enunciados negativos se "
        "invierten).",
        ("Siento que soy parte de mi colegio", "Me siento orgulloso/a de pertenecer a mi colegio"),
        "más pertenencia (mejor).", "poca pertenencia al colegio.")),
    "PSSM_Pos13": ("PSSM · pertenencia, 13 ítems positivos", _a(
        "lo mismo que la pertenencia pero solo con los 13 enunciados positivos (1–5).",
        ("Siento que soy parte de mi colegio", "Me siento orgulloso/a de pertenecer a mi colegio"),
        "más pertenencia (mejor).", "poca pertenencia al colegio.")),
    "TD_Total": ("Toma de decisiones (exploratoria)", _a(
        "pensar antes de actuar (10 ítems, 1–5). La fuente del instrumento no está "
        "documentada.",
        ("Antes de tomar una decisión, pienso en lo que puede pasar después.",
         "Pienso en las consecuencias antes de actuar."),
        "más reflexión antes de actuar.", "menos reflexión antes de actuar.")),
    "SIN_ADULTO": ("Sin un adulto de confianza en el colegio", _a(
        "el % de estudiantes que no tienen un adulto de confianza en el colegio (un solo "
        "ítem de pertenencia).",
        ("Hay al menos un profesor o adulto con quien puedo hablar en mi colegio.",),
        "más estudiantes sin a quién acudir (peor).", "la mayoría tiene un adulto de confianza.")),
    "ALERTA_malestar": ("Señal de malestar", _a(
        "el % de estudiantes que marcan «muy cierto» en 3 o más de 6 ítems del SDQ.",
        ("Cuando me enojo, me enojo mucho y pierdo el control",
         "A menudo estoy preocupado/a"),
        "más estudiantes con señales de malestar; indica dónde mirar primero, no es un "
        "diagnóstico.", "pocos estudiantes con esa señal.")),
}

# ── Cuidadores: «cuidador» (su propio bienestar) y «niño» (según su cuidador) ─
CUIDADORES: dict[str, tuple[str, ay.Ayuda]] = {
    "PSS_Total": ("PSS-10 · estrés percibido", _a(
        "cuánto estrés percibe el cuidador en su vida diaria (10 ítems, 0–40).",
        ("¿Se sintió nerviosa o llena de tensión?",
         "¿Tuvo problemas en manejar todas las cosas que tenía que hacer durante esos días?"),
        "más estrés percibido.", "poco estrés; siente que maneja lo que le pasa.")),
    "EPDS_Total": ("EPDS-10 · ánimo", _a(
        "señales de ánimo bajo en el cuidador (10 ítems, 0–30).",
        ("He estado ansioso(a) y preocupado(a) sin motivo alguno.",
         "Me he sentido triste y desgraciado(a)."),
        "más señales de ánimo bajo; desde 13 puntos es «probable», un tamizaje y no un "
        "diagnóstico.", "pocas señales.")),
    "MSPSS_Total": ("MSPSS · apoyo total", _a(
        "apoyo que el cuidador siente de su familia, sus amigos y una persona especial "
        "(12 ítems, 1–5).",
        ("Mi familia me apoya emocionalmente.",
         "Puedo contar con mis amigos cuando las cosas van mal."),
        "siente mucho apoyo (mejor).", "siente poco apoyo.")),
    "MSPSS_Otro": ("MSPSS · persona especial", _a(
        "apoyo de una persona especial (5 ítems, 1–5).",
        ("Hay una persona especial con la que puedo compartir mis alegrías.",
         "Tengo una persona especial que es una fuente de consuelo para mí."),
        "siente mucho apoyo de esa persona (mejor).", "siente poco apoyo de esa persona.")),
    "MSPSS_Fam": ("MSPSS · familia", _a(
        "apoyo de su familia (4 ítems, 1–5).",
        ("Mi familia me apoya emocionalmente.", "Puedo hablar de mis problemas con mi familia."),
        "siente mucho apoyo familiar (mejor).", "siente poco apoyo familiar.")),
    "MSPSS_Amigos": ("MSPSS · amigos", _a(
        "apoyo de sus amigos (3 ítems, 1–5).",
        ("Puedo contar con mis amigos cuando las cosas van mal.", "Mis amigos tratan de ayudarme."),
        "siente mucho apoyo de sus amigos (mejor).", "siente poco apoyo de sus amigos.")),
    "BARRIO_Indice": ("Riesgo del barrio", _a(
        "problemas del barrio: drogas, delincuencia, riñas, violencia grave y pandillas "
        "(5 preguntas, 0–10).",
        ("¿En su barrio hay delincuencia común cómo robos o atracos?",
         "¿En su barrio hay presencia de pandillas o bandas?"),
        "más riesgo en el barrio (peor).", "barrio más seguro.")),
    "APQ_Fisico": ("APQ · castigo físico", _a(
        "el % de cuidadores que usan castigo físico «a veces» o más (3 ítems).",
        ("Le da nalgadas con la mano a su hijo(a) cuando ha hecho algo malo o incorrecto",
         "Le pega a su hijo(a) con una correa u otro objeto cuando ha hecho algo malo o "
         "incorrecto"),
        "más cuidadores que recurren al castigo físico.", "pocos lo usan.")),
    "APQ_Grito": ("APQ · gritos", _a(
        "el % de cuidadores que gritan al hijo «a veces» o más (un solo ítem).",
        ("Grita a su hijo(a) cuando se ha portado mal",),
        "más cuidadores que gritan con frecuencia.", "pocos gritan.")),
    "SDQ_Total": ("SDQ padres · total de dificultades", _a(
        "dificultades del niño según su cuidador (20 ítems, 0–40).",
        ("Se siente a menudo infeliz, desanimado o lloroso",
         "Pelea o tiene problemas con frecuencia con otros niños/as"),
        "más dificultades emocionales y de conducta según el cuidador.",
        "pocas dificultades.")),
    "SDQ_Emo": ("SDQ padres · síntomas emocionales", _a(
        "tristeza, preocupación y miedos del niño (5 ítems, 0–10).",
        ("Tiene muchas preocupaciones, a menudo parece preocupado",
         "Tiene muchos miedos, se asusta fácilmente"),
        "más síntomas emocionales.", "pocos síntomas emocionales.")),
    "SDQ_Con": ("SDQ padres · problemas de conducta", _a(
        "peleas, desobediencia y mentiras del niño (5 ítems, 0–10).",
        ("Frecuentemente tiene rabietas o mal genio", "A menudo miente o engaña"),
        "más problemas de conducta.", "pocos problemas de conducta.")),
    "SDQ_Hip": ("SDQ padres · hiperactividad e inatención", _a(
        "inquietud y dificultad para concentrarse del niño (5 ítems, 0–10).",
        ("Es inquieto/a, hiperactivo/a, no se queda quieto/a por mucho tiempo",
         "Se distrae con facilidad, su concentración tiende a dispersarse"),
        "más inquietud e inatención.", "poca inquietud; se concentra con facilidad.")),
    "SDQ_Pares": ("SDQ padres · problemas con pares", _a(
        "el niño solo o molestado por otros (5 ítems, 0–10).",
        ("Los otros niños se meten o se burlan de el/ella",
         "Es más bien solitario y tiende a jugar solo"),
        "más problemas con sus compañeros.", "buena relación con sus compañeros.")),
    "SDQ_Pro": ("SDQ padres · conducta prosocial", _a(
        "el niño ayuda y comparte con otros (5 ítems, 0–10). Es una fortaleza.",
        ("Tiene en cuenta los sentimientos de otras personas",
         "A menudo se ofrece para ayudar a padres, profesores, otro niños"),
        "más conducta de ayuda y cooperación (mejor).", "menos conducta prosocial.")),
    "SDQ_Int": ("SDQ padres · internalizante", _a(
        "malestar del niño hacia adentro (10 ítems, 0–20).",
        ("Tiene muchos miedos, se asusta fácilmente",
         "Es más bien solitario y tiende a jugar solo"),
        "más malestar hacia adentro.", "poco malestar hacia adentro.")),
    "SDQ_Ext": ("SDQ padres · externalizante", _a(
        "malestar del niño hacia afuera (10 ítems, 0–20).",
        ("Frecuentemente tiene rabietas o mal genio",
         "Se distrae con facilidad, su concentración tiende a dispersarse"),
        "más malestar hacia afuera.", "poco malestar hacia afuera.")),
    "ARI_Total": ("ARI padres · irritabilidad", _a(
        "enojo frecuente e intenso del niño según su cuidador (6 ítems, 0–12; cobertura "
        "parcial).",
        ("Pierde la paciencia frecuentemente", "Permanece enojado(a) mucho tiempo"),
        "más irritabilidad.", "poca irritabilidad.")),
}

ESCALAS = {"estudiantes": ESTUDIANTES, "cuidadores": CUIDADORES}

# Constructos de la triangulación → (población de la ayuda, clave de la ayuda)
CONSTRUCTO_AYUDA: dict[str, tuple[str, str]] = {
    "est_sdq_total": ("estudiantes", "SDQ_Total"), "est_sdq_emo": ("estudiantes", "SDQ_Emo"),
    "est_sdq_con": ("estudiantes", "SDQ_Con"), "est_sdq_hip": ("estudiantes", "SDQ_Hip"),
    "est_pssm": ("estudiantes", "PSSM_Total"), "est_sin_adulto": ("estudiantes", "SIN_ADULTO"),
    "est_malestar": ("estudiantes", "ALERTA_malestar"),
    "est_mspss_fam": ("estudiantes", "MSPSS_Fam"),
    "nin_sdq_total": ("cuidadores", "SDQ_Total"), "nin_sdq_emo": ("cuidadores", "SDQ_Emo"),
    "nin_sdq_con": ("cuidadores", "SDQ_Con"), "nin_sdq_hip": ("cuidadores", "SDQ_Hip"),
    "cui_pss": ("cuidadores", "PSS_Total"), "cui_epds": ("cuidadores", "EPDS_Total"),
    "cui_fisico": ("cuidadores", "APQ_Fisico"), "cui_barrio": ("cuidadores", "BARRIO_Indice"),
    "cui_mspss_fam": ("cuidadores", "MSPSS_Fam"),
    "doc_pss": ("docentes", "PSS"), "doc_lider": ("docentes", "CL"),
    "doc_grupo": ("docentes", "AP"), "doc_desgaste": ("docentes", "BLG_Desg"),
    "doc_demandas": ("docentes", "MT_Demandas"),
}


# ══ Funciones puras ═════════════════════════════════════════════════════════
def _tres_lineas(a: ay.Ayuda) -> str:
    citas = [i.strip().rstrip(".") for i in a.items]
    items = (f"Ítem: «{citas[0]}»." if len(citas) == 1
             else "Ítems, por ejemplo: " + " y ".join(f"«{i}»" for i in citas[:2]) + ".")
    mayus = lambda t: t[0].upper() + t[1:]          # noqa: E731
    return "  \n".join([f"{mayus(a.mide)} {items}",
                        f"*Puntaje alto:* {mayus(a.alto)}",
                        f"*Puntaje bajo:* {mayus(a.bajo)}"])


def texto_escala(poblacion: str, clave: str) -> str | None:
    """Las tres líneas de una escala, con su nombre en negrita; None si no hay."""
    nombre_ayuda = ESCALAS.get(poblacion, {}).get(clave)
    if nombre_ayuda is None:
        return None
    nombre, a = nombre_ayuda
    return f"**{nombre}** (`{clave}`)  \n" + _tres_lineas(a)


def glosario(poblacion: str, claves: list[str] | None = None) -> str:
    """El glosario (markdown) de las escalas pedidas, en el orden dado."""
    claves = claves if claves is not None else list(ESCALAS.get(poblacion, {}))
    return "\n\n".join(t for t in (texto_escala(poblacion, c) for c in claves) if t)


def glosario_constructos(constructos) -> str:
    """Glosario de la triangulación: un bloque por constructo, con su etiqueta del catálogo."""
    bloques = []
    for c in constructos:
        destino = CONSTRUCTO_AYUDA.get(c.clave)
        if destino is None:
            continue
        pob, clave = destino
        a = (ay.ayuda(pob, clave) if pob == "docentes"
             else ESCALAS[pob].get(clave, (None, None))[1])
        if a is not None:
            bloques.append(f"**{c.etiqueta}**  \n" + _tres_lineas(a))
    return "\n\n".join(bloques)


def mostrar(poblacion: str, claves: list[str] | None = None,
            titulo: str = "📖 Qué mide cada escala") -> None:
    """Expander con el glosario, para el principio de una vista de investigador."""
    contenido = glosario(poblacion, claves)
    if contenido:
        import streamlit as st
        with st.expander(titulo):
            st.markdown(contenido)
