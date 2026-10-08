"""
Textos de la vista de comunidad de Cuidadores 360 — Observatorio 360 (fase 4b).

Todo lo que leen colegios, familias y el municipio en la página de Cuidadores,
en sus informes y en el resumen de una página: las seis tarjetas, las señales
del adulto («Ánimo» y «Autolesión»), el mensaje de autocuidado para familias,
la ruta para adultos y los avisos (spec del 6-oct-2026, §5.5, §6 y §8).

PROVISIONAL. Los textos y las rutas los aprueba el equipo investigador (spec
§8, puntos 1, 4 y 5). Mientras `TEXTOS_APROBADOS` o `RUTAS_VALIDADAS` sean
False:
  · la página de Cuidadores no aparece en el despliegue público
    (`navegacion.cuidadores_publico`);
  · `publicar --publicar-ya` no sube las filas de las señales del adulto;
  · en el modo completo la vista muestra el aviso interno `TEXTOS_PENDIENTES`.

Reglas:
  · Textos fijos. Nunca los redacta la IA en tiempo de ejecución.
  · Nunca «suicidio»: «señales», «no es un diagnóstico», «dónde mirar primero».
  · El código no inventa teléfonos: la ruta es `catalog.ruta_adulto` (la de
    adultos de la fase 3) hasta que el equipo confirme las líneas de Chía.
  · Familia no lee nada sobre hacerse daño ni cifras de las señales del adulto.
  · Color máximo: naranja (lo fija la vista, con los colores de estudiantes).
  · Este módulo no importa nada de ingesta, pipeline ni vistas: lo lee también
    el despliegue público y `core.navegacion`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.cuidadores import catalog as cat

TEXTOS_APROBADOS = False
RUTAS_VALIDADAS = False

ROLES = {
    "colegio": "Rector, docente u orientación escolar",
    "familia": "Madre, padre o cuidador",
    "municipio": "Funcionario del municipio",
}
TODOS_LOS_ROLES = ("colegio", "familia", "municipio")


# ── Tarjetas (spec §5.5) ────────────────────────────────────────────────────
@dataclass(frozen=True)
class Mensaje:
    titulo: str
    etiqueta: str                 # completa la cifra («1 de cada 4 …», «17 de 40 …»)
    significa: str
    accion: dict = field(default_factory=dict)          # rol → qué hacer
    solo_roles: tuple[str, ...] = TODOS_LOS_ROLES


MENSAJES: dict[str, Mensaje] = {
    "estres": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["estres"],
        etiqueta="puntos de 40 en estrés percibido, en promedio",
        significa=("Mide cuánto sienten los cuidadores que la vida diaria se les sale de "
                   "las manos en el último mes (PSS-10). No mide solo el estrés de criar "
                   "y no tiene un punto de corte clínico: se lee comparado con el municipio."),
        accion={
            "colegio": ("Programar los encuentros con familias en horarios posibles para "
                        "quienes trabajan y ofrecer espacios cortos de pausa y apoyo entre "
                        "cuidadores."),
            "familia": ("Buscar momentos de descanso y repartir las tareas de la casa y del "
                        "cuidado. El estrés se lleva mejor acompañado."),
            "municipio": ("Articular programas de apoyo a cuidadores (respiro, escuelas de "
                          "familia) con la oferta de bienestar del municipio."),
        }),
    "animo": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["animo"],
        etiqueta="cuidadores muestran señales de ánimo bajo",
        significa=("Es un tamizaje con la escala de Edimburgo (EPDS), no un diagnóstico: "
                   "indica cuántos cuidadores podrían beneficiarse de una conversación con un "
                   "profesional."),
        accion={
            "colegio": ("Incluir en las reuniones con familias un momento sobre el cuidado de "
                        "quien cuida y dar a conocer la ruta para adultos."),
            "municipio": ("Acercar la oferta de salud mental para adultos a las comunidades "
                          "educativas."),
        },
        solo_roles=("colegio", "municipio")),
    "apoyo": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["apoyo"],
        etiqueta="cuidadores sienten poco apoyo de su familia",
        significa=("Apoyo que el cuidador siente de su familia, de sus amigos y de una "
                   "persona especial (media por debajo de 3 de 5 en cada fuente)."),
        accion={
            "colegio": ("Crear redes entre familias del mismo curso y espacios donde los "
                        "cuidadores se conozcan y se apoyen."),
            "familia": ("Pedir y aceptar ayuda: un familiar, un vecino o las familias del curso "
                        "pueden compartir tareas del cuidado."),
            "municipio": ("Fortalecer las redes comunitarias de apoyo a familias y los "
                          "programas de cuidado de cuidadores."),
        }),
    "crianza": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["crianza"],
        etiqueta=("cuidadores usan alguna forma de castigo físico a veces o más "
                  "(nalgadas, cachetadas o correa)"),
        significa=("Mientras llega el libro de códigos del cuestionario de crianza no se mide "
                   "la crianza positiva: esta tarjeta solo describe el castigo físico y el "
                   "grito. La Ley 2089 de 2021 prohíbe el castigo físico; aquí se lee como una "
                   "invitación a acompañar a las familias, no a señalarlas."),
        accion={
            "colegio": ("Ofrecer a las familias talleres de crianza con alternativas al "
                        "castigo (acuerdos, consecuencias, reconocimiento), sin señalar a "
                        "nadie."),
            "familia": ("Cuando la paciencia se acaba, tomar una pausa antes de corregir. Hay "
                        "formas de poner límites sin golpes ni gritos; la orientación del "
                        "colegio puede acompañar."),
            "municipio": ("Fortalecer y difundir en los colegios los programas de crianza sin "
                          "violencia (Ley 2089 de 2021)."),
        }),
    "barrio": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["barrio"],
        etiqueta="puntos de 10 en el índice de riesgo del barrio, en promedio",
        significa=("Suma de cinco preguntas sobre drogas, delincuencia, riñas, violencia grave "
                   "y pandillas cerca de casa. Más alto quiere decir más riesgo."),
        accion={
            "colegio": ("Revisar con las familias los trayectos entre la casa y el colegio y "
                        "los espacios seguros después de clase."),
            "familia": ("Acordar con los hijos rutas y horarios seguros y saber dónde y con "
                        "quién están."),
            "municipio": ("Llevar la oferta de convivencia, seguridad y uso del tiempo libre a "
                          "los barrios con el índice más alto."),
        }),
    "hijo": Mensaje(
        titulo=dict(cat.TARJETAS_4B)["hijo"],
        etiqueta="niños con dificultades altas o muy altas según su cuidador",
        significa=("Cuestionario SDQ en su versión para padres: es lo que el cuidador observa "
                   "en casa y puede ser distinto de lo que dice el propio niño."),
        accion={
            "colegio": ("Conversar con las familias sobre lo que ven en casa y lo que se ve en "
                        "el aula, para acompañar al niño entre las dos partes."),
            "familia": ("Si nota tristeza, miedos, peleas o inquietud que no pasan, hablar con "
                        "la orientación del colegio."),
            "municipio": ("Orientar la oferta de salud mental infantil hacia los grupos donde "
                          "más cuidadores reportan dificultades."),
        }),
}
# Orden en que se intentan; se muestran las cinco primeras con cifra que el rol puede ver.
ORDEN_TARJETAS = tuple(k for k, _ in cat.TARJETAS_4B)
MAX_TARJETAS = 5

# ── Señales del adulto (spec §5.5) ──────────────────────────────────────────
TITULO_PANEL = "Señales para cuidar a quienes cuidan"


@dataclass(frozen=True)
class SenalAdulto:
    clave: str
    nombre: str
    nombre_corto: str
    senal: str                          # para la frase de la cifra
    que_es: str
    que_hacer: dict = field(default_factory=dict)   # rol → texto
    roles: tuple[str, ...] = ()


ALERTAS: dict[str, SenalAdulto] = {
    cat.ANIMO: SenalAdulto(
        clave=cat.ANIMO,
        nombre="Señales de ánimo bajo en los cuidadores",
        nombre_corto="Ánimo",
        senal="señales de ánimo bajo",
        que_es=(f"Cuidadores con {cat.EPDS_PROBABLE} puntos o más en la escala de Edimburgo "
                "(EPDS), que indica un ánimo bajo probable. Es una señal de grupo para mirar "
                "con atención, no un diagnóstico."),
        que_hacer={
            "colegio": ("Incluir en las reuniones con familias un momento sobre el cuidado de "
                        "quien cuida y dar a conocer la ruta para adultos. No abordar a ningún "
                        "cuidador a partir de este dato."),
            "municipio": ("Llevar la oferta de salud mental para adultos (atención primaria, "
                          "grupos de apoyo) a las comunidades de los colegios en «Prioridad» y "
                          "verificar que tenga capacidad."),
        },
        roles=("colegio", "municipio")),
    cat.AUTOLESION: SenalAdulto(
        clave=cat.AUTOLESION,
        nombre="Pensamientos de hacerse daño",
        nombre_corto="Hacerse daño",
        senal="pensamientos de hacerse daño",
        que_es=("Cuidadores que respondieron haber pensado alguna vez en hacerse daño en los "
                "últimos días (pregunta 10 de la EPDS). Es una señal para garantizar la ruta, "
                "no un diagnóstico."),
        que_hacer={
            "municipio": ("Garantizar que la ruta de salud mental para adultos tenga capacidad "
                          "de respuesta y que los colegios sepan cómo orientar a un cuidador."),
        },
        roles=("municipio",)),
}
PLANTILLA_CIFRA = "{fraccion} cuidadores {verbo} {senal}."
NOTA_SOLO_MUNICIPIO = ("Esta señal se muestra solo para todo el municipio, nunca por colegio "
                       "ni por grado.")
# Rol colegio: la autolesión no tiene cifra ni estado propio; queda dentro de este
# estado general, fijo, sin cifras (spec §5.5).
ESTADO_GENERAL_COLEGIO = (
    "Cuidar a quien cuida también es parte de la ruta. Si un cuidador cuenta que ha pensado en "
    "hacerse daño, escucharlo sin juzgar y orientarlo ese mismo día a la ruta para adultos.")
# Rol familia: sin cifras y sin nada sobre hacerse daño (spec §5.5 y §6).
TITULO_AUTOCUIDADO = "Cuidarse para cuidar"
AUTOCUIDADO_FAMILIA = (
    "Criar cansa. Sentirse triste, agotado o sin ganas durante varios días seguidos no es una "
    "falla: es una señal para pedir apoyo. Hablar con alguien de confianza, descansar y buscar "
    "a un profesional ayuda. Si el malestar no pasa o pesa demasiado, la ruta para adultos "
    "está abajo.")
CIFRAS_PEQUENAS = ("En este grupo las cifras son muy pequeñas para mostrarse sin riesgo de "
                   "identificar a alguien; la ruta sigue aplicando.")
NOTA_TABLA = ("Porcentaje del colegio con señales y su margen de error. El número de "
              "cuidadores con señales no se publica nunca.")

# Estados del panel: los de estudiantes (`alertas_catalogo`), con la
# referencia adaptada a cuidadores, donde no hay niveles. Provisionales hasta
# la aprobación del equipo, como el resto de este catálogo.
NO_ES_DIAGNOSTICO = "No es un diagnóstico: indica dónde mirar primero."
NOTA_AZAR = ("Con muchas comparaciones, alguna «Prioridad» puede deberse al azar; sirve para "
             "orientar, no para concluir.")
QUE_ES_PRIORIDAD = ("«Prioridad»: en este grupo las señales son más frecuentes que en el resto "
                    "del municipio, aun contando el margen de error.")
QUE_ES_PRESENTE = ("«Para tener presente»: las señales aparecen, como en casi todos los grupos, "
                   "sin diferenciarse del resto del municipio.")
QUE_ES_SIN_ESTADO = ("«Sin estado»: con cifras tan pequeñas no se muestra ni el porcentaje ni la "
                     "comparación, para no identificar a nadie. La ruta sigue aplicando.")
QUE_ES_REFERENCIA = ("«Para tener presente», sin comparación: es el total del municipio, o un "
                     "grupo que es casi todo el municipio y no deja un resto con qué compararlo.")

# ── Ruta, avisos y textos de la página ──────────────────────────────────────
TITULO_RUTA = "Si un cuidador necesita ayuda"


def ruta(rol: str) -> list[tuple[str, str]]:
    """Ruta para adultos del rol: la de `catalog.ruta_adulto` (sin teléfonos inventados)."""
    return list(cat.ruta_adulto(rol))


AVISO_TAMIZAJE = ("Estos resultados son un tamizaje de grupo sobre los cuidadores que "
                  "respondieron, no un diagnóstico de nadie.")
AVISO_EPDS = ("La escala de ánimo (EPDS) se creó para el periodo después del parto; aquí se "
              "usa como tamizaje del ánimo de madres, padres y otros cuidadores.")
AVISO_APOYO = ("El apoyo se pregunta por fuente (familia, amigos, una persona especial) con "
               "preguntas distintas de las de los estudiantes: no se comparan directamente.")
AVISO_MINIMO = (f"Ningún grupo con menos de {cat.MIN_GROUP_N} cuidadores distintos se muestra. "
                "El grado es el del hijo o la hija por quien respondió el cuidador.")
AVISO_SIN_OLAS = ("Las cifras reúnen todas las olas de la encuesta (2025 y 2026); no se "
                  "publican por ola.")
DESCARGAS_BLOQUEADAS = ("Descargas desactivadas: la auditoría de privacidad encontró cifras "
                        "que no se pueden entregar. Quien procesa los datos debe revisarla "
                        "antes de imprimir informes.")
TEXTOS_PENDIENTES = ("Aviso interno: los textos y la ruta de esta página están pendientes de "
                     "aprobación del equipo. Solo se ve en el modo completo.")
NO_PUBLICADO = ("Cuidadores 360 todavía no tiene resultados publicados. La página mostrará las "
                "cifras de los cuidadores cuando el equipo apruebe y publique una corrida.")
SIN_SUBGRUPO = (f"Este grupo no tiene cifras publicadas: no llega a {cat.MIN_GROUP_N} "
                "cuidadores distintos.")
