"""
Catálogo de dimensiones del instrumento de docentes — Observatorio 360.

ÚNICA FUENTE DE VERDAD para ítems, inversiones, agregación, escala teórica,
dirección, cortes, fuente y frase fija de cada dimensión. La vista, el PDF y
las pruebas leen de aquí; nadie vuelve a sumar ítems por su cuenta.

Base: docs/analisis/2026-10-10-propuesta-docentes.md, §5.2 (13 puntos de §6
aprobados provisionalmente el 10-oct-2026).

Codificación de los ítems
-------------------------
El catálogo se define sobre la **codificación 2**, la que escribe
`scripts/preparar_docentes.py` desde octubre de 2026 y marca con la columna
`COLUMNA_CODIFICACION = 2`:

  · PSS 3, 4, 5, 7 y 9 invertidos (4 − x), como siempre.
  · IRI_PT(3), IRI_PT(15), IRI_EC(4), IRI_EC(13), IRI_EC(14), IRI_EC(18) invertidos (4 − x).
  · PRPS_CE3 invertido (4 − x). CE2 y CE9–16 **sin** invertir.
  · ERS_CON1–4 invertidos (3 − x). ERS_ACP1 **sin** invertir.
  · IR1 invertido (5 − x): «me veo aquí el próximo año» pasa a medir intención de irse.

El archivo activo en Storage está en la **codificación 1** (la anterior, sin la
columna): PRPS_CE2 y CE9–16 invertidos, ERS_ACP1 invertido e IR1 sin invertir.
`RECODIFICAR_V1` dice qué ítems hay que recodificar (máximo − x) para llevar un
archivo en codificación 1 a la 2. Lo aplica `src/docentes/scoring.normalizar_codificacion`.

Cortes
------
Solo PSS-10, BAT-12 e ISTAS21 tienen bandas de referencia. Los del PSS son
convencionales (Cohen no publicó cortes). Los del BAT-12 son los del BAT-23 del
manual de Schaufeli, De Witte y Desart y los de ISTAS21 son las tablas de
referencia de población asalariada española: ambos llevan
`comprobar_en_manual=True` hasta que el equipo los confirme.
"""
from __future__ import annotations

from dataclasses import dataclass

# ── Constantes ──────────────────────────────────────────────────────────────
MAYOR_MEJOR = "mayor_mejor"
MAYOR_PEOR = "mayor_peor"

ZONA_FAVORABLE = "favorable"
ZONA_INTERMEDIA = "intermedia"
ZONA_VIGILAR = "a vigilar"
ZONA_SIN_DATO = "sin dato"

# Colores de la propuesta (§3, reglas comunes): nunca rojo.
COLOR_ZONA = {
    ZONA_FAVORABLE: "#1A7F4B",
    ZONA_INTERMEDIA: "#B07D0D",
    ZONA_VIGILAR: "#D9822B",
    ZONA_SIN_DATO: "#5F6368",
}
ETIQUETA_ZONA = {
    ZONA_FAVORABLE: "Zona favorable",
    ZONA_INTERMEDIA: "Zona intermedia",
    ZONA_VIGILAR: "Zona a vigilar",
    ZONA_SIN_DATO: "Sin dato",
}

VERSION_2025 = "2025 (acuerdo en 6 opciones)"
VERSION_2026 = "2026 (acuerdo en 5 opciones)"
COLUMNA_VERSION = "Versión del formulario"

COLUMNA_CODIFICACION = "Codificación de ítems"
CODIFICACION_ACTUAL = 2
# Ítem → valor máximo de su escala; en un archivo en codificación 1 se recodifica
# como máximo − x para llegar a la codificación 2 (ver cabecera).
RECODIFICAR_V1 = {
    **{f"PRPS_CE{i}": 4 for i in (2, 9, 10, 11, 12, 13, 14, 15, 16)},
    "ERS_ACP1": 3,
    "IR1": 5,
}

# «Número de hijos» = 10 en 69 docentes de 2025: casi seguro un código del
# formulario («no responde»). Se trata como faltante al cargar, hasta que el
# equipo lo confirme (§6, punto 8).
HIJOS_CODIGO_FALTANTE = 10

AVISO_VERSION = ("El formulario cambió en 2026: la escala de acuerdo pasó de 6 a 5 "
                 "opciones. Comparar 2025 con 2026 exige cautela.")
NOTA_SOLO_2025 = "Solo se preguntó en 2025."
NOTA_NOMBRE_PROVISIONAL = "Nombre provisional: validar con el instrumento original."

# Temas, en el orden en que se muestran.
TEMA_SALUD_MENTAL = "🧠 Salud mental y estrés"
TEMA_BIENESTAR = "😊 Bienestar laboral"
TEMA_RECURSOS = "🛠️ Recursos y demandas del trabajo"
TEMA_EMPATIA = "💗 Empatía y regulación emocional"
TEMA_INVESTIGADOR = "🔬 Solo investigador"
TEMAS = [TEMA_SALUD_MENTAL, TEMA_BIENESTAR, TEMA_RECURSOS, TEMA_EMPATIA, TEMA_INVESTIGADOR]

FUENTE_HSE = ("Adaptación del HSE Management Standards Indicator Tool (6 opciones de "
              "respuesta en lugar de 5; los percentiles del Reino Unido no aplican).")
FUENTE_PROPIA = "Ítems propios del estudio (escala de acuerdo 0–5)."
FUENTE_QBLG = "Cuestionario de Bienestar Laboral General, qBLG (Blanch et al., 2010)."
FUENTE_NETEMEYER = "Conflicto trabajo–familia (Netemeyer, Boles y McMurrian, 1996)."
FUENTE_ISTAS = ("CoPsoQ-ISTAS21, versión corta. Tablas de referencia de población "
                "asalariada española.")
FUENTE_ERS = "Escala tipo DERS-E (dificultades de regulación emocional)."
FUENTE_IRI = "Índice de Reactividad Interpersonal, IRI (Davis, 1983)."


@dataclass(frozen=True)
class Banda:
    """Una banda de corte: [inferior, superior] en la escala de presentación."""
    etiqueta: str
    inferior: float
    superior: float
    zona: str


@dataclass(frozen=True)
class Dimension:
    clave: str
    nombre: str
    tema: str
    items: tuple[str, ...]
    agregacion: str                 # "media" | "suma" | "valor" (un solo ítem)
    escala: tuple[float, float]     # escala teórica de presentación
    direccion: str | None           # MAYOR_MEJOR | MAYOR_PEOR | None
    fuente: str
    frase: str                      # qué mide y qué significa un valor alto
    desplazamiento: float = 0.0     # se suma al puntaje (BAT: código 0–4 → 1–5)
    cortes: tuple[Banda, ...] = ()
    cortes_tipo: str | None = None  # "publicado" | "convencional"
    comprobar_en_manual: bool = False
    aviso_version: bool = False     # escalas de acuerdo: cambió el formulario en 2026
    solo_version: str | None = None  # solo existe en una ola (BLG_Psicoso: 2025)
    nota: str = ""
    en_tablero: bool = True         # False: solo en la vista del investigador

    @property
    def mayor_mejor(self) -> bool | None:
        if self.direccion is None:
            return None
        return self.direccion == MAYOR_MEJOR

    @property
    def codigo_min_items(self) -> int:
        """Ítems respondidos que hacen falta para puntuar."""
        if self.agregacion == "suma":
            return len(self.items)
        return (len(self.items) + 1) // 2


def _rango(prefijo: str, a: int, b: int) -> tuple[str, ...]:
    return tuple(f"{prefijo}{i}" for i in range(a, b + 1))


# ── Dimensiones ─────────────────────────────────────────────────────────────
DIMENSIONES: tuple[Dimension, ...] = (
    # 🧠 Salud mental y estrés
    Dimension(
        "PSS", "Estrés percibido (PSS-10)", TEMA_SALUD_MENTAL, _rango("PSS", 1, 10),
        "suma", (0, 40), MAYOR_PEOR,
        "Escala de Estrés Percibido, PSS-10 (Cohen, Kamarck y Mermelstein, 1983). "
        "Cortes convencionales: Cohen no publicó cortes.",
        "Cuánto estrés sintió la persona en el último mes. Un valor alto es más estrés.",
        cortes=(Banda("Estrés bajo", 0, 13, ZONA_FAVORABLE),
                Banda("Estrés moderado", 14, 26, ZONA_INTERMEDIA),
                Banda("Estrés alto", 27, 40, ZONA_VIGILAR)),
        cortes_tipo="convencional"),
    Dimension(
        "BTA", "Burnout (BAT-12)", TEMA_SALUD_MENTAL, _rango("BTA", 1, 12),
        "media", (1, 5), MAYOR_PEOR,
        "Burnout Assessment Tool, BAT-12 (Schaufeli, De Witte y Desart, 2020). "
        "Cortes del manual (valores del BAT-23).",
        "Agotamiento, distancia mental y deterioro cognitivo y emocional por el trabajo. "
        "Un valor alto es más burnout.",
        desplazamiento=1,
        cortes=(Banda("Sin riesgo", 1, 2.58, ZONA_FAVORABLE),
                Banda("En riesgo", 2.59, 3.01, ZONA_INTERMEDIA),
                Banda("Riesgo muy alto", 3.02, 5, ZONA_VIGILAR)),
        cortes_tipo="publicado", comprobar_en_manual=True,
        nota="Cortes 2,59 / 3,02 del BAT-23: confirmar los del BAT-12 en el manual."),
    Dimension("BTA_Agot", "Burnout: agotamiento", TEMA_INVESTIGADOR, _rango("BTA", 1, 3),
              "media", (1, 5), MAYOR_PEOR, "BAT-12, subescala de agotamiento.",
              "Sentirse agotado por el trabajo. Un valor alto es más agotamiento.",
              desplazamiento=1, en_tablero=False),
    Dimension("BTA_Dist", "Burnout: distancia mental", TEMA_INVESTIGADOR, _rango("BTA", 4, 6),
              "media", (1, 5), MAYOR_PEOR, "BAT-12, subescala de distancia mental.",
              "Desconexión e indiferencia hacia el trabajo. Un valor alto es más distancia.",
              desplazamiento=1, en_tablero=False),
    Dimension("BTA_Cog", "Burnout: deterioro cognitivo", TEMA_INVESTIGADOR, _rango("BTA", 7, 9),
              "media", (1, 5), MAYOR_PEOR, "BAT-12, subescala de deterioro cognitivo.",
              "Dificultad para concentrarse y pensar con claridad en el trabajo.",
              desplazamiento=1, en_tablero=False),
    Dimension("BTA_Emo", "Burnout: deterioro emocional", TEMA_INVESTIGADOR, _rango("BTA", 10, 12),
              "media", (1, 5), MAYOR_PEOR, "BAT-12, subescala de deterioro emocional.",
              "Dificultad para controlar las emociones en el trabajo.",
              desplazamiento=1, en_tablero=False),
    Dimension(
        "BLG_Som", "Somatización (qBLG)", TEMA_SALUD_MENTAL, _rango("BLG_Som", 1, 5),
        "media", (1, 7), MAYOR_PEOR, FUENTE_QBLG,
        "Molestias físicas asociadas al trabajo. Un valor alto es más molestias."),
    Dimension(
        "BLG_Desg", "Desgaste (qBLG)", TEMA_SALUD_MENTAL, _rango("BLG_Desg", 1, 4),
        "media", (1, 7), MAYOR_PEOR, FUENTE_QBLG,
        "Agotamiento y saturación por el trabajo. Un valor alto es más desgaste."),
    Dimension(
        "BLG_Alie", "Alienación (qBLG)", TEMA_SALUD_MENTAL, _rango("BLG_Alie", 1, 4),
        "media", (1, 7), MAYOR_PEOR, FUENTE_QBLG,
        "Sentirse ajeno o sin sentido en el trabajo. Un valor alto es más alienación."),
    Dimension(
        "BLG_Psicoso", "Bienestar psicosocial (qBLG)", TEMA_SALUD_MENTAL,
        _rango("BLG_Psicoso", 1, 10), "media", (1, 7), MAYOR_MEJOR, FUENTE_QBLG,
        "Expectativas de bienestar en el trabajo. Un valor alto es más bienestar.",
        solo_version=VERSION_2025, nota=NOTA_SOLO_2025),

    # 😊 Bienestar laboral
    Dimension("Comp", "Compromiso", TEMA_BIENESTAR, _rango("Comp", 1, 3), "media", (0, 5),
              MAYOR_MEJOR, FUENTE_PROPIA,
              "Compromiso con el trabajo y la institución. Un valor alto es más compromiso.",
              aviso_version=True),
    Dimension("DefO", "Defensa de la organización", TEMA_BIENESTAR, _rango("DefO", 1, 3),
              "media", (0, 5), MAYOR_MEJOR, FUENTE_PROPIA,
              "Disposición a hablar bien de la institución. Un valor alto es más defensa.",
              aviso_version=True),
    Dimension("Sat", "Satisfacción laboral", TEMA_BIENESTAR, _rango("Sat", 1, 3), "media",
              (0, 5), MAYOR_MEJOR, FUENTE_PROPIA,
              "Satisfacción con el trabajo. Un valor alto es más satisfacción.",
              aviso_version=True),
    Dimension("IR", "Intención de retiro", TEMA_BIENESTAR, _rango("IR", 1, 4), "media",
              (0, 5), MAYOR_PEOR, FUENTE_PROPIA + " IR1 invertido.",
              "Intención de dejar la institución. Un valor alto es más intención de irse.",
              aviso_version=True),
    Dimension("Descon", "Desconexión psicológica", TEMA_BIENESTAR, _rango("Descon", 1, 3),
              "media", (1, 5), MAYOR_MEJOR,
              "Desconexión psicológica (REQ, Sonnentag y Fritz, 2007; 3 ítems).",
              "Capacidad de desconectarse del trabajo fuera de él. Un valor alto es mejor."),
    Dimension("Conf_TrFa", "Conflicto trabajo→familia", TEMA_BIENESTAR,
              _rango("Conf_TrFa", 1, 5), "media", (1, 7), MAYOR_PEOR, FUENTE_NETEMEYER,
              "El trabajo interfiere con la vida familiar. Un valor alto es más conflicto."),
    Dimension("Conf_FaTr", "Conflicto familia→trabajo", TEMA_BIENESTAR,
              _rango("Conf_FaTr", 1, 5), "media", (1, 7), MAYOR_PEOR, FUENTE_NETEMEYER,
              "La vida familiar interfiere con el trabajo. Un valor alto es más conflicto."),

    # 🛠️ Recursos y demandas del trabajo
    Dimension("MT_Control", "Control sobre el trabajo", TEMA_RECURSOS, _rango("MT", 1, 3),
              "media", (0, 5), MAYOR_MEJOR, FUENTE_HSE,
              "Margen para decidir cómo y cuándo hacer el trabajo. Un valor alto es más control."),
    Dimension("MT_Demandas", "Demandas de tiempo", TEMA_RECURSOS, _rango("MT", 4, 7),
              "media", (0, 5), MAYOR_PEOR, FUENTE_HSE,
              "Presión de tiempo y plazos. Un valor alto es más presión."),
    Dimension("CL", "Apoyo del líder", TEMA_RECURSOS, _rango("CL", 1, 7), "media", (0, 5),
              MAYOR_MEJOR, FUENTE_HSE,
              "Apoyo y respaldo de la persona que dirige. Un valor alto es más apoyo."),
    Dimension("AP", "Apoyo de compañeros", TEMA_RECURSOS, _rango("AP", 1, 3), "media",
              (0, 5), MAYOR_MEJOR, FUENTE_HSE,
              "Apoyo de los colegas. Un valor alto es más apoyo."),
    Dimension("CR_Claridad", "Claridad de rol", TEMA_RECURSOS, _rango("CR", 1, 4), "media",
              (0, 5), MAYOR_MEJOR, FUENTE_HSE,
              "Saber qué se espera de uno en el trabajo. Un valor alto es más claridad."),
    Dimension("CR_Conflicto", "Conflicto de rol", TEMA_RECURSOS, _rango("CR", 5, 7), "media",
              (0, 5), MAYOR_PEOR, FUENTE_HSE,
              "Exigencias contradictorias en el trabajo. Un valor alto es más conflicto."),
    Dimension("CO", "Cambio organizacional", TEMA_RECURSOS, _rango("CO", 1, 4), "media",
              (0, 5), MAYOR_MEJOR, FUENTE_HSE,
              "Cómo se comunican y consultan los cambios. Un valor alto es mejor gestión."),
    Dimension("RO", "Responsabilidad organizacional", TEMA_RECURSOS, _rango("RO", 1, 5),
              "media", (0, 5), MAYOR_MEJOR, FUENTE_PROPIA,
              "Lo que la institución hace por el bienestar del personal. Un valor alto es mejor.",
              aviso_version=True,
              nota="Sube +0,71 DE entre versiones del formulario (1,03 en 2025; 1,84 en 2026)."),
    Dimension(
        "ISTAS_Exig", "Exigencias psicológicas (ISTAS21)", TEMA_RECURSOS,
        _rango("PRPS_CE", 1, 6), "suma", (0, 24), MAYOR_PEOR, FUENTE_ISTAS,
        "Ritmo, cantidad y carga emocional del trabajo. Un valor alto es más exigencia.",
        cortes=(Banda("Favorable", 0, 7, ZONA_FAVORABLE),
                Banda("Intermedio", 8, 10, ZONA_INTERMEDIA),
                Banda("Desfavorable", 11, 24, ZONA_VIGILAR)),
        cortes_tipo="publicado", comprobar_en_manual=True,
        nota="Tablas de referencia de población asalariada española: verificar en el manual."),
    Dimension(
        "ISTAS_TA", "Trabajo activo y desarrollo (ISTAS21)", TEMA_RECURSOS,
        _rango("PRPS_CE", 7, 16), "suma", (0, 40), MAYOR_MEJOR, FUENTE_ISTAS,
        "Influencia, desarrollo de habilidades y sentido del trabajo. Un valor alto es mejor.",
        cortes=(Banda("Desfavorable", 0, 20, ZONA_VIGILAR),
                Banda("Intermedio", 21, 25, ZONA_INTERMEDIA),
                Banda("Favorable", 26, 40, ZONA_FAVORABLE)),
        cortes_tipo="publicado", comprobar_en_manual=True,
        nota="Tablas de referencia de población asalariada española: verificar en el manual."),

    # 💗 Empatía y regulación emocional (sin cortes; propuesta: vista del investigador)
    Dimension("IRI_PT", "Toma de perspectiva (IRI)", TEMA_EMPATIA,
              ("IRI_PT(3)", "IRI_PT(8)", "IRI_PT(11)", "IRI_PT(15)", "IRI_PT(21)",
               "IRI_PT(25)", "IRI_PT(28)"),
              "media", (0, 4), MAYOR_MEJOR, FUENTE_IRI,
              "Tendencia a adoptar el punto de vista de los demás. Un valor alto es más."),
    Dimension("IRI_EC", "Preocupación empática (IRI)", TEMA_EMPATIA,
              ("IRI_EC(2)", "IRI_EC(4)", "IRI_EC(9)", "IRI_EC(14)", "IRI_EC(18)",
               "IRI_EC(20)", "IRI_EC(22)"),
              "media", (0, 4), MAYOR_MEJOR, FUENTE_IRI + " Sin el ítem 13 (malestar personal).",
              "Sentimientos de compasión por los demás. Un valor alto es más."),
    Dimension("ERS_ACP", "Dificultad de regulación: no aceptación", TEMA_EMPATIA,
              _rango("ERS_ACP", 1, 6), "media", (0, 3), MAYOR_PEOR,
              FUENTE_ERS + " ACP1 sin invertir.",
              "Rechazo de las propias emociones. Un valor alto es más dificultad.",
              nota=NOTA_NOMBRE_PROVISIONAL),
    Dimension("ERS_CON", "Dificultad de regulación: desatención", TEMA_EMPATIA,
              _rango("ERS_CON", 1, 4), "media", (0, 3), MAYOR_PEOR, FUENTE_ERS,
              "No prestar atención a las propias emociones. Un valor alto es más dificultad.",
              nota=NOTA_NOMBRE_PROVISIONAL),
    Dimension("ERS_CLA", "Dificultad de regulación: claridad", TEMA_EMPATIA,
              _rango("ERS_CLA", 1, 4), "media", (0, 3), MAYOR_PEOR, FUENTE_ERS,
              "Confusión sobre lo que se siente. Un valor alto es más dificultad.",
              nota=NOTA_NOMBRE_PROVISIONAL),
    Dimension("ERS_MET", "Dificultad de regulación: metas", TEMA_EMPATIA,
              _rango("ERS_MET", 1, 2), "media", (0, 3), MAYOR_PEOR, FUENTE_ERS,
              "Dificultad para actuar hacia metas cuando se está alterado. Un valor alto es más dificultad.",
              nota=NOTA_NOMBRE_PROVISIONAL),

    # 🔬 Solo investigador
    Dimension("PRPS_Fam", "Doble presencia (1 ítem)", TEMA_INVESTIGADOR, ("PRPS_Fam_T",),
              "valor", (1, 4), None, FUENTE_ISTAS + " Un solo ítem de los cuatro de doble presencia.",
              "Qué parte del trabajo doméstico asume la persona. Solo se muestra su distribución.",
              en_tablero=False),
)

_POR_CLAVE = {d.clave: d for d in DIMENSIONES}


def por_clave(clave: str) -> Dimension:
    """La dimensión con esa clave; KeyError si no existe."""
    return _POR_CLAVE[clave]


def claves() -> list[str]:
    return [d.clave for d in DIMENSIONES]


def del_tablero() -> list[Dimension]:
    """Las dimensiones que se muestran en el tablero (no las del investigador)."""
    return [d for d in DIMENSIONES if d.en_tablero]


def todos_los_items() -> list[str]:
    out: list[str] = []
    for d in DIMENSIONES:
        out.extend(c for c in d.items if c not in out)
    return out
