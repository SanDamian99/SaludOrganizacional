"""
Alertas de grupo de Estudiantes 360 — «Señales para actuar a tiempo».

Qué ítems activan cada alerta, con qué umbral, qué lee cada rol y a dónde se
deriva (spec del 6-oct-2026, §5.4). `catalog` reexporta `ALERTAS` y `RUTAS`.

PROVISIONAL. Textos, umbrales y rutas los aprueba el equipo investigador
(spec §8, puntos 1 a 3). Mientras `TEXTOS_APROBADOS` y `RUTAS_VALIDADAS` sean
False se muestran tal cual y, solo en el modo completo, la vista añade el aviso
interno `RUTA_PENDIENTE`.

Reglas:
  · Textos fijos. Nunca los redacta la IA en tiempo de ejecución.
  · Nunca «riesgo de suicidio»: «señales», «no es un diagnóstico», «dónde
    mirar primero».
  · El código no inventa teléfonos. La «Línea 106» es de Bogotá y se queda
    hasta que el equipo confirme las líneas de Chía (p. ej. 192 opción 4 o
    ICBF 141).
  · No importa `catalog` (catalog importa este módulo): niveles, roles y el
    texto de cifras pequeñas van como texto, y una prueba comprueba que
    coinciden.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TEXTOS_APROBADOS = False
RUTAS_VALIDADAS = False

MALESTAR = "malestar"
DESESPERANZA = "desesperanza"

ROLES = ("colegio", "familia", "municipio")
NIVELES = ("secundaria", "primaria")

# Codificación de ingest (catalog.MAP_3 y catalog.MAP_4_FREQ)
MUY_CIERTO = 2
CON_FRECUENCIA = 2
SIEMPRE = 3

# Malestar: «Muy cierto» en al menos UMBRAL_MALESTAR de los 6 ítems
UMBRAL_MALESTAR = 3
UMBRALES_SENSIBILIDAD = (2, 3, 4)

# Desesperanza (solo secundaria): ítems del RCADS-25
ITEM_MUERTE = 18          # «Pienso acerca de la muerte»
ITEM_VALIA = 16           # «Me siento que no valgo nada»
ITEMS_AMPLIA = (4, 1)     # la regla amplia (sensibilidad) suma RCADS 4 o RCADS 1
ITEMS_REGLA_ESTRICTA = (ITEM_VALIA, ITEM_MUERTE)
ITEMS_REGLA_AMPLIA = (1, 4, ITEM_VALIA, ITEM_MUERTE)


@dataclass(frozen=True)
class Alerta:
    clave: str
    nombre: str                 # lo que lee la comunidad
    nombre_corto: str           # tablas e informes
    senal: str                  # «señales de malestar», para la frase de la cifra
    escala: str                 # prefijo de columna de ingest: «SDQ», «RCADS»
    items: tuple[int, ...]      # ítems que la activan (1-indexados)
    regla: str                  # la regla en palabras, para la metodología
    niveles: tuple[str, ...]
    roles: tuple[str, ...]
    marcados_en: tuple[str, ...] = ()   # formularios cuyos encabezados llevan «*» en estos ítems
    que_es: str = ""
    que_hacer: dict = field(default_factory=dict)   # rol → texto
    limite: str = ""


ALERTAS: dict[str, Alerta] = {
    MALESTAR: Alerta(
        clave=MALESTAR,
        nombre="Señales de malestar",
        nombre_corto="Malestar",
        senal="señales de malestar",
        escala="SDQ",
        items=(5, 6, 8, 13, 19, 24),
        regla=("«Muy cierto» en 3 o más de estos 6 ítems del SDQ: 5 (me enojo y pierdo el "
               "control), 6 (solitario), 8 (preocupado), 13 (triste o con ganas de llorar), "
               "19 (se burlan de mí) y 24 (muchos miedos). Se calcula con los 6 ítems "
               "respondidos."),
        niveles=("secundaria", "primaria"),
        roles=("colegio", "familia", "municipio"),
        marcados_en=("primaria",),     # hoy solo primaria trae el «*» (spec §5.4)
        que_es=("Estudiantes que marcan «muy cierto» en al menos 3 de 6 preguntas sobre "
                "enojo, soledad, preocupación, tristeza, burlas y miedos."),
        que_hacer={
            "colegio": ("Revisar con orientación escolar cómo se acompaña a este grupo: "
                        "convivencia, burlas entre compañeros y espacios para hablar de lo que "
                        "sienten. Formar a los docentes para reconocer señales y derivar por la "
                        "ruta, sin señalar a ningún estudiante."),
            "familia": ("Preguntar con calma cómo se siente y cómo le va con sus compañeros, y "
                        "escuchar sin juzgar. Si nota tristeza, miedo o enojo que no pasan, "
                        "buscar a la orientación del colegio o al servicio de salud."),
            "municipio": ("Orientar la oferta psicosocial y de convivencia escolar hacia los "
                          "grupos en «Prioridad» y verificar que la ruta de salud mental tenga "
                          "capacidad para recibir a quienes se deriven."),
        },
        limite=("Los seis ítems mezclan emociones, enojo y relación con los compañeros: por eso "
                "se nombra «malestar» y no «malestar emocional». No forman una escala validada "
                "por sí solos."),
    ),
    DESESPERANZA: Alerta(
        clave=DESESPERANZA,
        nombre="Señales de desesperanza y pensamientos de muerte",
        nombre_corto="Desesperanza",
        senal="señales de desesperanza o pensamientos de muerte",
        escala="RCADS",
        items=(ITEM_VALIA, ITEM_MUERTE),
        regla=("RCADS 18 («Pienso acerca de la muerte») en «Siempre», o RCADS 18 en «Con "
               "frecuencia» o más junto con RCADS 16 («Me siento que no valgo nada») en «Con "
               "frecuencia» o más. Se calcula con los ítems 16 y 18 respondidos."),
        niveles=("secundaria",),
        roles=("colegio", "municipio"),
        que_es=("Estudiantes que dicen pensar en la muerte siempre, o con frecuencia junto con "
                "sentir que no valen nada. Es una señal para mirar con atención y activar la "
                "ruta, no un diagnóstico."),
        que_hacer={
            "colegio": ("Verificar que la ruta de atención esté activa y que los docentes sepan "
                        "cómo derivar. Fortalecer los espacios de escucha y la formación en "
                        "primeros auxilios psicológicos. No abordar a estudiantes individuales a "
                        "partir de este dato."),
            "municipio": ("Garantizar que la ruta de salud mental adolescente tenga capacidad de "
                          "respuesta y articularla con los colegios en «Prioridad»."),
        },
        limite=("El instrumento no tiene una escala de desesperanza: son dos ítems del RCADS-25 "
                "y se leen como señal de grupo."),
    ),
}

# Enunciados resumidos de los ítems que usan las alertas (pestaña de investigadores).
# RCADS 1 y 4: pendientes de copiar del formulario aplicado.
ENUNCIADOS_ITEMS = {
    "SDQ5": "Me enojo y pierdo el control",
    "SDQ6": "Solitario",
    "SDQ8": "Preocupado",
    "SDQ13": "Triste o con ganas de llorar",
    "SDQ19": "Se burlan de mí",
    "SDQ24": "Muchos miedos",
    "RCADS1": "RCADS 1 (subescala de depresión)",
    "RCADS4": "RCADS 4 (subescala de depresión)",
    "RCADS16": "Me siento que no valgo nada",
    "RCADS18": "Pienso acerca de la muerte",
}

# ── Textos del panel ─────────────────────────────────────────────────────────
TITULO_PANEL = "Señales para actuar a tiempo"
# Estados. «referencia» se lee igual que «presente», pero no hubo comparación
# (el total del nivel, o un grupo sin resto suficiente con qué compararlo).
PRIORIDAD = "prioridad"
PRESENTE = "presente"
REFERENCIA = "referencia"
SIN_ESTADO = "sin_estado"
ESTADOS = {PRIORIDAD: "Prioridad", PRESENTE: "Para tener presente",
           REFERENCIA: "Para tener presente", SIN_ESTADO: "Sin estado: cifras pequeñas"}
NO_ES_DIAGNOSTICO = "No es un diagnóstico: indica dónde mirar primero."
PLANTILLA_CIFRA = "{fraccion} estudiantes {verbo} {senal}."
# Igual a catalog.CIFRAS_PEQUENAS (una prueba lo comprueba).
CIFRAS_PEQUENAS = ("En este grupo las cifras son muy pequeñas para mostrarse sin riesgo de "
                   "identificar a alguien; la ruta sigue aplicando.")
CIFRAS_PEQUENAS_CORTO = "Cifras muy pequeñas para mostrarse"
NOTA_AZAR = ("Con muchas comparaciones, alguna «Prioridad» puede deberse al azar; sirve para "
             "orientar, no para concluir.")
QUE_ES_PRIORIDAD = ("«Prioridad»: en este grupo las señales son más frecuentes que en el resto "
                    "del municipio, aun contando el margen de error.")
QUE_ES_PRESENTE = ("«Para tener presente»: las señales aparecen, como en casi todos los grupos, "
                   "sin diferenciarse del resto del municipio.")
QUE_ES_SIN_ESTADO = ("«Sin estado»: con cifras tan pequeñas no se muestra ni el porcentaje ni la "
                     "comparación, para no identificar a nadie. La ruta sigue aplicando.")
QUE_ES_REFERENCIA = ("«Para tener presente», sin comparación: es el total del nivel, o un "
                     "grupo que es casi todo el nivel y no deja un resto con qué compararlo.")
TITULO_GRADOS_PRIORIDAD = "Grados en «Prioridad»:"
TITULO_COLEGIOS_PRIORIDAD = "Colegios en «Prioridad»:"
NOTA_TABLA = ("Porcentaje del colegio con señales y su margen de error. El número de "
              "estudiantes con señales no se publica nunca.")
REGLA_CIFRAS = ("El porcentaje y el «1 de cada N» se muestran solo si en el grupo hay al menos "
                "3 estudiantes con señales y al menos 3 sin ellas, también después de sumar o "
                "restar cualquier par de cifras publicadas (la misma supresión de todas las "
                "proporciones). El estado se muestra solo donde se muestra el porcentaje.")
RUTA_PENDIENTE = ("Aviso interno: la ruta de atención está pendiente de validación por el "
                  "equipo (las líneas de Chía no están confirmadas). Solo se ve en el modo "
                  "completo.")

# ── Rutas por rol y por tipo de persona ──────────────────────────────────────
# Mientras el equipo no apruebe las de Chía, las tres usan la ruta vigente.
_RUTA_ESTUDIANTE = (
    ("Orientación escolar del colegio", "Primer contacto, siempre."),
    ("Línea 106", "Atención psicológica gratuita, 24 horas."),
    ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
    ("Comisaría de Familia", "Si hay riesgo en el hogar."),
)
# Para adultos (cuidadores, fase 4). Sin teléfonos hasta que el equipo los confirme.
_RUTA_ADULTO = (
    ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
    ("Comisaría de Familia", "Si hay riesgo en el hogar."),
)
RUTAS: dict[str, dict[str, tuple[tuple[str, str], ...]]] = {
    "colegio": {"estudiante": _RUTA_ESTUDIANTE, "adulto": _RUTA_ADULTO},
    "familia": {"estudiante": _RUTA_ESTUDIANTE, "adulto": _RUTA_ADULTO},
    "municipio": {"estudiante": _RUTA_ESTUDIANTE, "adulto": _RUTA_ADULTO},
}


def ruta(rol: str, tipo: str = "estudiante") -> list[tuple[str, str]]:
    """La ruta de un rol para estudiantes o adultos; la del colegio si el rol no existe."""
    por_tipo = RUTAS.get(rol) or RUTAS["colegio"]
    return list(por_tipo.get(tipo) or por_tipo["estudiante"])


def items_marcados_esperados(nivel: str) -> dict[str, set[int]]:
    """{escala: ítems} que el formulario de `nivel` debe traer marcados con «*»."""
    salida: dict[str, set[int]] = {}
    for a in ALERTAS.values():
        if nivel in a.marcados_en:
            salida.setdefault(a.escala, set()).update(a.items)
    return salida
