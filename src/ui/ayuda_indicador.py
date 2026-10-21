"""
Descripción breve de lo que se ve al escoger un indicador o dimensión.

Cada selector del tablero (docentes, estudiantes, cuidadores) muestra debajo tres
líneas: qué mide y con qué ítems literales, qué significa un puntaje alto y qué
uno bajo. Los ítems son los enunciados del formulario que respondieron las
personas; solo se corrigieron erratas evidentes de ortografía. Lo que significa
«alto» sigue la dirección del catálogo (`src/docentes/catalogo.py`): en las
escalas «mayor = peor» un valor alto es la señal a vigilar.

Sin Streamlit en las funciones puras (`ayuda`, `texto`): las prueban los tests.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ayuda:
    mide: str
    items: tuple[str, ...]
    alto: str
    bajo: str


def _a(mide: str, items: tuple[str, ...], alto: str, bajo: str) -> Ayuda:
    return Ayuda(mide, items, alto, bajo)


# ── Docentes: media (o suma) de los ítems en la escala del instrumento ──────
DOCENTES: dict[str, Ayuda] = {
    "PSS": _a(
        "cuánto estrés percibe el docente: qué tan imprevisible, incontrolable y "
        "sobrecargada siente su vida (suma de 10 ítems, 0–40).",
        ("¿Se sintió nerviosa o llena de tensión?",
         "¿Tuvo problemas en manejar todas las cosas que tenía que hacer durante esos días?"),
        "más estrés percibido; hay poca sensación de control.",
        "poco estrés; siente que maneja lo que le pasa."),
    "BTA": _a(
        "burnout: agotamiento, distancia mental y deterioro cognitivo y emocional "
        "por el trabajo (media de 12 ítems, 1–5).",
        ("En mi trabajo, me siento agotado/a emocionalmente",
         "Tengo problemas para mantenerme enfocado en mi trabajo"),
        "más burnout (peor); el color usa los cortes del manual del BAT, aún por confirmar.",
        "poco burnout; conserva energía y concentración en el trabajo."),
    "BTA_Agot": _a(
        "la parte de agotamiento del burnout (3 ítems, 1–5).",
        ("En mi trabajo, me siento agotado/a emocionalmente",
         "Me siento físicamente agotado/a en mi trabajo"),
        "más agotamiento por el trabajo.",
        "poco agotamiento; recupera su energía."),
    "BTA_Dist": _a(
        "la parte de distancia mental del burnout (3 ítems, 1–5).",
        ("Me cuesta encontrar entusiasmo por mi trabajo",
         "Siento una fuerte aversión hacia mi trabajo"),
        "más desconexión e indiferencia hacia el trabajo.",
        "sigue implicado y con entusiasmo por el trabajo."),
    "BTA_Cog": _a(
        "la parte de deterioro cognitivo del burnout (3 ítems, 1–5).",
        ("Tengo problemas para mantenerme enfocado en mi trabajo",
         "Cometo errores en mi trabajo, porque tengo mi mente en otras cosas"),
        "más dificultad para concentrarse y pensar con claridad.",
        "buena concentración en el trabajo."),
    "BTA_Emo": _a(
        "la parte de deterioro emocional del burnout (3 ítems, 1–5).",
        ("En mi trabajo, me siento incapaz de controlar mis emociones",
         "Puedo reaccionar exageradamente sin querer"),
        "más dificultad para controlar las emociones en el trabajo.",
        "maneja bien sus emociones en el trabajo."),
    "BLG_Som": _a(
        "molestias físicas que el docente asocia al trabajo (5 ítems, 1–7).",
        ("Dolores de cabeza", "Alteraciones de sueño"),
        "más molestias físicas (digestivas, de cabeza, de sueño, de espalda, musculares).",
        "pocas molestias físicas."),
    "BLG_Desg": _a(
        "agotamiento y saturación por el trabajo (4 ítems, 1–7).",
        ("Agotamiento físico", "Cansancio mental"),
        "más desgaste: sobrecarga, cansancio físico y mental.",
        "poco desgaste; llega al final del día con energía."),
    "BLG_Alie": _a(
        "alienación: malestar y desafección frente al trabajo (4 ítems, 1–7).",
        ("Frustración", "Trato distante"),
        "más alienación: mal humor, frustración, trato distante.",
        "se siente realizado y cercano a su trabajo."),
    "BLG_Psicoso": _a(
        "bienestar psicosocial: cómo se siente con su motivación, autoestima y "
        "sentido del trabajo (10 ítems, 1–7; solo en la ola de 2025).",
        ("Mi motivación por el trabajo", "Mi autoestima profesional"),
        "más bienestar (mejor).",
        "menos bienestar: poca motivación, autoestima o sentido del trabajo."),
    "Comp": _a(
        "compromiso con el trabajo y con la institución (3 ítems, 0–5).",
        ("Me siento entusiasmado por mi trabajo",
         "Cuando me levanto en la mañana tengo ganas de ir a trabajar"),
        "más compromiso y entusiasmo (mejor).",
        "poco compromiso; el trabajo no motiva."),
    "DefO": _a(
        "orgullo por la institución y disposición a defenderla (3 ítems, 0–5).",
        ("Me siento orgulloso de la institución en la que laboro",
         "Recomendaría ampliamente a otros trabajar en la institución en la que laboro"),
        "más orgullo y defensa de la institución (mejor).",
        "poco orgullo; no la recomendaría."),
    "Sat": _a(
        "satisfacción con el trabajo y con lo que recibe de él (3 ítems, 0–5).",
        ("Considero mi trabajo significativo",
         "Me gusta hacer las tareas y actividades de mi trabajo"),
        "más satisfacción (mejor).",
        "poca satisfacción con el trabajo."),
    "IR": _a(
        "intención de dejar la institución (4 ítems, 0–5; el ítem «me veo aquí el "
        "próximo año» se invierte).",
        ("A menudo considero seriamente dejar mi trabajo actual",
         "He empezado a buscar activamente otro trabajo."),
        "más intención de irse (peor).",
        "planea quedarse en la institución."),
    "Descon": _a(
        "capacidad de desconectarse del trabajo fuera de él (3 ítems, 1–5).",
        ("Después del trabajo soy capaz de \"desconectarme\"",
         "Cuando termino de trabajar me olvido completamente del trabajo"),
        "se desconecta bien del trabajo (mejor).",
        "le cuesta desconectarse; el trabajo lo sigue a casa."),
    "Conf_TrFa": _a(
        "cuánto el trabajo interfiere con la vida familiar (5 ítems, 1–7).",
        ("Las exigencias de mi trabajo interfieren con mi hogar y mi vida familiar.",
         ("La cantidad de tiempo que ocupa mi trabajo dificulta el cumplimiento de las "
         "responsabilidades familiares.")),
        "más conflicto: el trabajo le quita tiempo y energía a la familia (peor).",
        "el trabajo deja espacio para la vida familiar."),
    "Conf_FaTr": _a(
        "cuánto la familia interfiere con el trabajo (5 ítems, 1–7).",
        (("Las demandas de mi familia o cónyuge / pareja interfieren con las actividades "
         "relacionadas con el trabajo"),
         ("Tengo que posponer las tareas en el trabajo debido a las exigencias de mi "
         "tiempo en casa.")),
        "más conflicto: la vida familiar afecta su desempeño en el trabajo (peor).",
        "la vida familiar casi no afecta el trabajo."),
    "MT_Control": _a(
        "control sobre qué y cómo trabaja (3 ítems, 0–5).",
        ("Tengo la opción de decidir qué hago en mi trabajo.",
         "Tengo voz y voto sobre mi propio ritmo de trabajo."),
        "más control sobre su trabajo (mejor).",
        "poca autonomía para decidir su trabajo."),
    "MT_Demandas": _a(
        "presión de tiempo y carga de trabajo (4 ítems, 0–5).",
        ("Me presionan para que trabaje muchas horas.",
         "Tengo presiones de tiempo poco realistas"),
        "más presión de tiempo y sobrecarga (peor).",
        "carga de trabajo manejable."),
    "CL": _a(
        "apoyo que siente de su líder (7 ítems, 0–5).",
        ("Si el trabajo se pone difícil, mi líder me ayudará",
         "Mi líder está dispuesto a escuchar mis problemas relacionados con el trabajo."),
        "más apoyo y reconocimiento del líder (mejor).",
        "poco apoyo del líder."),
    "AP": _a(
        "apoyo que siente de sus compañeros (3 ítems, 0–5).",
        ("Si el trabajo se pone difícil, mis compañeros de trabajo me ayudarán",
         "Mis compañeros de trabajo están dispuestos a escuchar mis problemas laborales."),
        "más apoyo de los compañeros (mejor).",
        "poco apoyo de los compañeros."),
    "CR_Claridad": _a(
        "claridad sobre lo que se espera de su rol (4 ítems, 0–5).",
        ("Tengo claro lo que se espera de mí en el trabajo.",
         "Tengo claro cuáles son mis deberes y responsabilidades"),
        "más claridad sobre su rol (mejor).",
        "poca claridad sobre qué se espera de él o ella."),
    "CR_Conflicto": _a(
        "exigencias contradictorias en el trabajo (3 ítems, 0–5).",
        ("Diferentes personas en el trabajo esperan de mí cosas contradictorias.",
         "Recibo solicitudes incompatibles de dos o más personas"),
        "más conflicto de rol: le piden cosas que chocan entre sí (peor).",
        "recibe pedidos coherentes."),
    "CO": _a(
        "qué tan bien se comunican y se consultan los cambios (4 ítems, 0–5).",
        ("Me consultan sobre cambios propuestos en el trabajo.",
         ("Estoy claramente informado sobre la naturaleza de los cambios que se producen "
         "en esta organización.")),
        "mejor gestión del cambio: lo consultan y lo informan.",
        "los cambios llegan sin consulta ni información."),
    "RO": _a(
        "qué hace la institución por la salud mental de su gente (5 ítems, 0–5).",
        ("En mi lugar de trabajo la salud física y mental es una prioridad de los líderes",
         ("Recibo entrenamiento periódico sobre pautas para el cuidado de mi salud mental "
         "en el trabajo")),
        "la institución cuida y comunica su acción en salud mental (mejor).",
        "percibe poca acción institucional en salud mental."),
    "ISTAS_Exig": _a(
        "ritmo, cantidad y carga emocional del trabajo (6 ítems, suma 0–24; el ítem de "
        "tener tiempo para llevar el trabajo al día se invierte).",
        ("¿Tienes que trabajar muy rápido?",
         "¿Tu trabajo, en general, es desgastador emocionalmente?"),
        "más exigencias psicológicas (peor); desde 10,5 cae en la zona a vigilar.",
        "exigencias bajas; hasta 7,5 es zona favorable."),
    "ISTAS_TA": _a(
        "autonomía, iniciativa, aprendizaje y sentido del trabajo (10 ítems, suma 0–40).",
        ("¿Tu trabajo permite que aprendas cosas nuevas?",
         "¿Tienen sentido tus tareas?"),
        "más trabajo activo y desarrollo (mejor).",
        "poco margen para decidir, aprender o dar sentido a su trabajo."),
    "IRI_PT": _a(
        "toma de perspectiva: ponerse en el lugar del otro (7 ítems, 0–4).",
        (("Creo que todas las cuestiones se pueden ver desde dos perspectivas e intento "
         "considerar ambas."),
         ("Antes de criticar a alguien, intento imaginar cómo me sentiría yo si estuviera "
         "en su lugar.")),
        "más facilidad para ver las cosas desde el punto de vista del otro.",
        "le cuesta ver otros puntos de vista."),
    "IRI_EC": _a(
        "preocupación empática: compasión por quien sufre (7 ítems, 0–4).",
        (("A menudo tengo sentimientos de compasión y preocupación hacia gente menos "
         "afortunada que yo."),
         "Cuando veo que se aprovechan de alguien, siento necesidad de protegerle."),
        "más compasión y preocupación por los demás.",
        "menos sensibilidad ante el sufrimiento ajeno."),
    "ERS_ACP": _a(
        "dificultad para aceptar lo que siente cuando se enoja (6 ítems, 0–3).",
        ("Cuando me enojo, me reprocho a mí mismo por ello.",
         "Cuando estoy enojado, siento que soy una persona débil"),
        "más dificultad: se culpa o se juzga por sentir enojo (peor).",
        "acepta sus emociones sin reprocharse."),
    "ERS_CON": _a(
        "dificultad para darse cuenta de lo que siente (4 ítems, 0–3). Los ítems se "
        "preguntan en positivo y el puntaje ya viene invertido.",
        ("Le presto atención a la forma cómo me siento",
         "Sé exactamente cómo me estoy sintiendo en cada momento"),
        "más desatención a las propias emociones (peor).",
        "se da cuenta de lo que siente."),
    "ERS_CLA": _a(
        "dificultad para entender lo que siente (4 ítems, 0–3).",
        ("Tengo poca idea de cómo me siento.",
         "Me cuesta trabajo entender mis emociones"),
        "más confusión sobre las propias emociones (peor).",
        "entiende con claridad lo que siente."),
    "ERS_MET": _a(
        "dificultad para trabajar cuando está enojado (2 ítems, 0–3).",
        ("Cuando estoy enojado tengo dificultad para realizar mi trabajo.",
         "Cuando me enojo, pierdo el control"),
        "más dificultad para actuar con calma estando enojado (peor).",
        "el enojo casi no afecta lo que hace."),
    "PRPS_Fam": _a(
        "doble presencia: el reparto del trabajo doméstico y familiar (1 ítem, 1–4).",
        ("¿Qué parte del trabajo familiar y doméstico haces tú?",),
        "sin dirección definida: se usa solo para describir.",
        "sin dirección definida: se usa solo para describir."),
}

# ── Estudiantes: % de estudiantes del grupo que cruzan el corte del indicador ─
ESTUDIANTES: dict[str, Ayuda] = {
    "sdq_alto": _a(
        "el % de estudiantes que, en su autoinforme SDQ de 25 ítems, reportan "
        "dificultades altas o muy altas.",
        ("Me siento a menudo triste, desanimado o con ganas de llorar",
         "Peleo mucho. Y muchas veces lo hago para obtener lo que quiero"),
        "muchos estudiantes del grupo reportan dificultades emocionales o de conducta.",
        "pocos reportan dificultades altas; no descarta casos individuales."),
    "adulto_confianza": _a(
        "el % de estudiantes que no tienen un adulto de confianza en el colegio "
        "(un solo ítem de pertenencia).",
        ("Hay al menos un profesor o adulto con quien puedo hablar en mi colegio.",),
        "muchos estudiantes sin a quién acudir en el colegio (peor).",
        "la mayoría tiene un adulto de confianza."),
    "ideacion": _a(
        "el % de estudiantes que piensan en la muerte con frecuencia o siempre "
        "(un solo ítem del RCADS).",
        ("Pienso acerca de la muerte",),
        "más estudiantes con esta señal de alerta; activa la ruta de atención, no es un "
        "diagnóstico.",
        "pocos la reportan; no descarta casos individuales."),
    "irritabilidad": _a(
        "el % de estudiantes por encima del corte de irritabilidad (suma de 6 ítems "
        "del ARI mayor que 2; es un cribado).",
        ("Pierdo la paciencia frecuentemente", "Permanezco enojado(a) mucho tiempo"),
        "muchos estudiantes del grupo con enojo frecuente e intenso.",
        "pocos por encima del corte."),
    "emocional": _a(
        "el % de estudiantes con síntomas emocionales en nivel alto (5 ítems del SDQ).",
        ("Me siento a menudo triste, desanimado o con ganas de llorar",
         "Tengo muchos miedos, me asusto fácilmente"),
        "muchos estudiantes del grupo con tristeza, preocupación o miedos.",
        "pocos con síntomas emocionales altos."),
}

# ── Cuidadores: % de cuidadores del grupo que cruzan el corte del indicador ──
CUIDADORES: dict[str, Ayuda] = {
    "animo": _a(
        "el % de cuidadores con señales de ánimo bajo (EPDS-10, 13 puntos o más de 30; "
        "es un tamizaje).",
        ("He estado ansioso(a) y preocupado(a) sin motivo alguno.",
         "Me he sentido triste y desgraciado(a)."),
        "más cuidadores con señales de ánimo bajo; conviene ofrecer apoyo, no es un "
        "diagnóstico.",
        "pocos cuidadores con esas señales."),
    "apoyo_familia": _a(
        "el % de cuidadores que sienten poco apoyo de su familia (4 ítems del MSPSS).",
        ("Mi familia me apoya emocionalmente.",
         "Puedo hablar de mis problemas con mi familia."),
        "muchos cuidadores sin una familia en la que apoyarse (peor).",
        "la mayoría siente a su familia cerca."),
    "apoyo_amigos": _a(
        "el % de cuidadores que sienten poco apoyo de sus amigos (3 ítems del MSPSS).",
        ("Puedo contar con mis amigos cuando las cosas van mal.",
         "Mis amigos tratan de ayudarme."),
        "muchos cuidadores sin amigos con quienes contar (peor).",
        "la mayoría cuenta con sus amigos."),
    "apoyo_otro": _a(
        "el % de cuidadores que sienten poco apoyo de una persona especial (5 ítems "
        "del MSPSS).",
        ("Hay una persona especial que está cerca de mí cuando la necesito.",
         "Tengo una persona especial que es una fuente de consuelo para mí."),
        "muchos cuidadores sin una persona especial que los acompañe (peor).",
        "la mayoría tiene esa persona cerca."),
    "castigo": _a(
        "el % de cuidadores que usan castigo físico «a veces» o más (3 ítems del APQ).",
        ("Le da nalgadas con la mano a su hijo(a) cuando ha hecho algo malo o incorrecto",
         ("Le pega a su hijo(a) con una correa u otro objeto cuando ha hecho algo malo "
         "o incorrecto")),
        "más cuidadores que recurren al castigo físico; es la señal para ofrecer pautas "
        "de crianza.",
        "pocos lo usan."),
    "grito": _a(
        "el % de cuidadores que gritan al hijo «a veces» o más (un solo ítem del APQ).",
        ("Grita a su hijo(a) cuando se ha portado mal",),
        "más cuidadores que gritan con frecuencia.",
        "pocos gritan."),
    "hijo_alto": _a(
        "el % de niños con dificultades altas según su cuidador (SDQ para padres, "
        "25 ítems).",
        ("Se siente a menudo infeliz, desanimado o lloroso",
         "Pelea o tiene problemas con frecuencia con otros niños/as"),
        "más niños con dificultades emocionales o de conducta según su cuidador.",
        "pocos con dificultades altas; no descarta casos individuales."),
}

AYUDAS = {"docentes": DOCENTES, "estudiantes": ESTUDIANTES, "cuidadores": CUIDADORES}


def ayuda(poblacion: str, clave: str) -> Ayuda | None:
    return AYUDAS.get(poblacion, {}).get(clave)


def texto(poblacion: str, clave: str) -> str | None:
    """Las tres líneas de ayuda (markdown) o None si el indicador no tiene descripción."""
    a = ayuda(poblacion, clave)
    if a is None:
        return None
    citas = [i.strip().rstrip(".") for i in a.items]
    if len(citas) == 1:
        items = f"Ítem: «{citas[0]}»."
    else:
        items = "Ítems, por ejemplo: " + " y ".join(f"«{i}»" for i in citas[:2]) + "."
    return "  \n".join([
        f"**Qué mide:** {a.mide[0].upper() + a.mide[1:]} {items}",
        f"**Puntaje alto:** {a.alto[0].upper() + a.alto[1:]}",
        f"**Puntaje bajo:** {a.bajo[0].upper() + a.bajo[1:]}",
    ])


def mostrar(poblacion: str, clave: str) -> None:
    """Dibuja la ayuda bajo el selector; no hace nada si el indicador no la tiene."""
    contenido = texto(poblacion, clave)
    if contenido:
        import streamlit as st
        st.info(contenido, icon="ℹ️")
