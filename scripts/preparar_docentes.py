"""
Prepara el archivo de docentes para la plataforma — Observatorio 360.

Toma la exportación cruda del formulario «360 - Profesores (respuestas)» y
produce el archivo codificado que entiende el dashboard: ítems numéricos con
sus inversiones, totales por escala (`*_T`), colegio normalizado y sin la
columna de nombres. Reemplaza al script heredado de la carpeta
«Preprocesamiento 360», que estaba atado a 189 filas y a un solo export.

Reglas:
  - Solo entran las filas cuyo consentimiento dice «Sí». Las demás se cuentan
    y se descartan, y nada de ellas sale en el archivo.
  - El nombre se elimina y cada fila recibe un ID secuencial anónimo.
  - Los ítems se ubican por posición, no por texto: el formulario cambió la
    redacción de varias preguntas entre exportaciones pero no su orden. Las
    posiciones se comprueban contra el texto de la pregunta antes de codificar
    y, si algo no cuadra, el script se detiene en vez de codificar mal.
  - Las variables sociodemográficas y laborales se conservan como texto legible:
    el dashboard filtra por ellas y un «1» no le dice nada a quien filtra.

Uso:
    python -m scripts.preparar_docentes "360 - Profesores (respuestas).xlsx" salida.xlsx
"""
from __future__ import annotations

import re
import sys
import unicodedata

import numpy as np
import pandas as pd

# ══ Utilidades de texto ═════════════════════════════════════════════════════
def norm(texto) -> str:
    """Minúsculas, sin tildes, sin espacios repetidos."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return ""
    t = unicodedata.normalize("NFD", str(texto)).lower().strip()
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t)


def _mapa(pares: dict) -> dict:
    return {norm(k): v for k, v in pares.items()}


def aplicar(serie: pd.Series, mapa: dict) -> pd.Series:
    """Codifica con `mapa`; lo que no reconoce queda como NaN (no como texto).

    Un valor ya numérico dentro del rango del mapa se respeta: la exportación
    de 2026 trae los ítems de bienestar (BLG) como números de 1 a 7.
    """
    valores = set(mapa.values())

    def uno(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or not str(v).strip():
            return np.nan
        if isinstance(v, (int, float, np.number)):
            return float(v) if float(v) in valores else np.nan
        return mapa.get(norm(v), np.nan)
    return serie.map(uno)


# ══ Colegios ════════════════════════════════════════════════════════════════
# (fragmento normalizado que debe aparecer, código, nombre legible). El orden
# importa: «IE Bojacá - IE José Joaquín Casas» es Bojacá, así que va antes.
COLEGIOS = [
    ("campincito", "Dcampin", "Diversificado · sede Campincito"),
    ("santa luc", "SaLu", "Diversificado · sede Santa Lucía"),
    ("cerr", "Fcerr", "Fusca · sede El Cerro"),
    ("bojac", "Bojacá", "Bojacá"),
    ("cerca de piedra", "CdP", "Cerca de Piedra"),
    ("diversificado", "CND", "Colegio Nacional Diversificado"),
    ("conaldi", "CND", "Colegio Nacional Diversificado"),
    ("diosa", "DiosCh", "Diosa Chía"),
    ("fonquet", "Fonquetá", "Fonquetá"),
    ("fusca", "Fusca", "Fusca"),
    ("fagua", "Fagua", "Fagua"),
    ("joaqu", "JJC", "José Joaquín Casas"),
    ("jj casas", "JJC", "José Joaquín Casas"),
    ("balsa", "LaBalsa", "La Balsa"),
    ("vicu", "LauV", "Laura Vicuña"),
    ("laura", "LauV", "Laura Vicuña"),
    ("santa maria", "SMR", "Santa María del Río"),
    ("stmr", "SMR", "Santa María del Río"),
    ("balaguer", "SJMEB", "San Josemaría Escrivá de Balaguer"),
    ("escriv", "SJMEB", "San Josemaría Escrivá de Balaguer"),
    ("escriba", "SJMEB", "San Josemaría Escrivá de Balaguer"),
    ("secretaria", "SecEdu", "Secretaría de Educación"),
]


def colegio(texto) -> tuple[str, str]:
    """(código, nombre legible) del colegio, o ("", "") si no se reconoce."""
    t = norm(texto)
    if not t:
        return "", ""
    # «cerr» solo cuenta si además dice Fusca: «Cerca de Piedra» también lo contiene
    for fragmento, codigo, nombre in COLEGIOS:
        if fragmento == "cerr" and "fusca" not in t:
            continue
        if fragmento in t:
            return codigo, nombre
    return "", ""


def sede(texto) -> str:
    t = str(texto) if pd.notna(texto) else ""
    m = re.search(r"sede\s+(.+)$", t, flags=re.IGNORECASE)
    return m.group(1).strip(" .") if m else ""


# ══ Posiciones y escalas ════════════════════════════════════════════════════
# (posición, columna de salida, fragmento del enunciado que debe contener)
DEMOGRAFICAS = [
    (1, "Consentimiento", "consentimiento"), (2, "Nombre", "nombre"),
    (3, "Edad", "edad"), (4, "Sexo", "sexo"), (5, "Estado Civil", "estado civil"),
    (6, "Número de hijos", "hijos"), (7, "Nivel educativo", "nivel educativo"),
    (8, "Estrato socioeconómico", "socioecon"), (9, "Zona Vivienda", "zona"),
    (10, "Colegio", "colegio"), (11, "Este es un colegio", "este es un colegio"),
    (12, "Jornada o curso", "dicta clase"), (13, "Tipo de Contrato", "contrat"),
    (14, "Número de horas de trabajo semanal", "horas"),
    (15, "Ingreso salarial mensual", "ingreso"), (16, "Nivel de Cargo", "cargo"),
    (17, "Personas acargo", "personas a cargo"), (18, "Años experiencia laboral", "experiencia"),
]
EXTRAS = {  # solo existen en la exportación nueva
    "horas extras": "Horas extra semanales", "nivel de cargo": "Cargo (detalle)",
    "nivel dicta clase": "Nivel en que dicta clase",
}

IRI = ["IRI_EC(2)", "IRI_PT(3)", "IRI_EC(4)", "IRI_PT(8)", "IRI_EC(9)", "IRI_PT(11)",
       "IRI_EC(13)", "IRI_EC(14)", "IRI_PT(15)", "IRI_EC(18)", "IRI_EC(20)", "IRI_PT(21)",
       "IRI_EC(22)", "IRI_PT(25)", "IRI_PT(28)"]
ERS = ["ERS_CON1", "ERS_CON2", "ERS_CLA1", "ERS_CLA2", "ERS_CLA3", "ERS_CON3", "ERS_CLA4",
       "ERS_CON4", "ERS_ACP1", "ERS_MET1", "ERS_ACP2", "ERS_ACP3", "ERS_ACP4", "ERS_MET2",
       "ERS_ACP5", "ERS_ACP6"]
BLOQUES = [  # (inicio, fin excluyente, prefijo)
    (77, 84, "MT"), (84, 91, "CL"), (91, 94, "AP"), (94, 101, "CR"), (101, 105, "CO"),
    (105, 110, "RO"), (110, 115, "Conf_FaTr"), (115, 120, "Conf_TrFa"), (120, 132, "BTA"),
    (132, 135, "Comp"), (135, 138, "DefO"), (138, 141, "Sat"), (141, 145, "IR"),
    (145, 155, "BLG_Psicoso"), (155, 160, "BLG_Som"), (160, 164, "BLG_Desg"),
    (164, 168, "BLG_Alie"), (168, 171, "Descon"),
]

MAPAS = dict(
    IRI=_mapa({"no me describe en absoluto": 0, "me describe poco": 1,
               "me describe de manera moderada": 2, "algo me describe": 2,
               "me describe de manera moderada / algo me describe": 2,
               "me describe bastante": 3, "me describe muy bien": 4}),
    PSS=_mapa({"nunca": 0, "casi nunca": 1, "de vez en cuando": 2, "frecuentemente": 3,
               "casi siempre": 4}),
    ERS=_mapa({"nunca": 0, "algunas veces": 1, "alguna vez": 1, "casi siempre": 2,
               "casi simpre": 2, "siempre": 3}),
    PRPS=_mapa({"nunca": 0, "solo alguna vez": 1, "solo algunas veces": 1, "algunas veces": 2,
                "muchas veces": 3, "siempre": 4}),
    BTA=_mapa({"nunca": 0, "raramente": 1, "rara vez": 1, "algunas veces": 2, "a menudo": 3,
               "siempre": 4}),
    FRECUENCIA6=_mapa({"nunca": 0, "rara vez": 1, "alguna vez": 2, "a menudo": 3,
                       "frecuentemente": 4, "siempre": 5}),
    # En marzo de 2026 el formulario pasó de 6 opciones (muy / moderadamente /
    # ligeramente) a 5 (muy en desacuerdo, en desacuerdo, ligeramente de acuerdo,
    # de acuerdo, muy de acuerdo). Se codifican sobre la misma recta 0–5 para que
    # las dos versiones sumen igual; la columna «Versión del formulario» permite
    # separarlas en el análisis.
    ACUERDO6=_mapa({"muy en desacuerdo": 0, "moderadamente en desacuerdo": 1,
                    "en desacuerdo": 1, "ligeramente en desacuerdo": 2,
                    "ligeramente de acuerdo": 3, "moderadamente de acuerdo": 4,
                    "de acuerdo": 4, "muy de acuerdo": 5}),
    ACUERDO5=_mapa({"totalmente en desacuerdo": 1, "en desacuerdo": 2,
                    "ni de acuerdo ni en desacuerdo": 3, "de acuerdo": 4,
                    "totalmente de acuerdo": 5}),
    FRECUENCIA7=_mapa({"nunca": 1, "rara vez": 2, "alguna vez": 3, "algunas veces": 4,
                       "a menudo": 5, "frecuentemente": 6, "siempre": 7}),
)
MAPA_POR_PREFIJO = [
    ("IRI", "IRI"), ("PSS", "PSS"), ("ERS", "ERS"), ("PRPS_CE", "PRPS"), ("BTA", "BTA"),
    ("Comp", "ACUERDO6"), ("DefO", "ACUERDO6"), ("Sat", "ACUERDO6"), ("IR", "ACUERDO6"),
    ("MT", "FRECUENCIA6"), ("CL", "FRECUENCIA6"), ("AP", "FRECUENCIA6"), ("CR", "FRECUENCIA6"),
    ("CO", "FRECUENCIA6"), ("RO", "FRECUENCIA6"), ("Descon", "ACUERDO5"),
    ("BLG", "FRECUENCIA7"), ("Conf", "FRECUENCIA7"),
]
# Ítems invertidos según la documentación de cada escala (igual que el heredado)
INVERTIDOS = {4: ["IRI_PT(3)", "IRI_PT(15)", "IRI_EC(4)", "IRI_EC(13)", "IRI_EC(14)", "IRI_EC(18)",
                  "PSS3", "PSS4", "PSS5", "PSS7", "PSS9",
                  "PRPS_CE2", "PRPS_CE3", "PRPS_CE9", "PRPS_CE10", "PRPS_CE11", "PRPS_CE12",
                  "PRPS_CE13", "PRPS_CE14", "PRPS_CE15", "PRPS_CE16"],
              3: ["ERS_CON1", "ERS_CON2", "ERS_CON3", "ERS_CON4", "ERS_ACP1"]}
TOTALES = ["PSS", "MT", "CL", "AP", "CR", "CO", "RO", "Conf_FaTr", "Conf_TrFa", "BTA", "Comp",
           "DefO", "Sat", "IR", "BLG_Psicoso", "BLG_Som", "BLG_Desg", "BLG_Alie", "Descon",
           "PRPS_CE", "ERS_CLA", "ERS_CON", "ERS_ACP", "ERS_MET", "IRI_PT", "IRI_EC"]


class FormatoInesperado(ValueError):
    """La exportación no tiene las preguntas donde el script las espera."""


def _renombres(columnas: list[str]) -> dict[int, str]:
    """{posición: nombre de salida}, tras comprobar que cada posición es la esperada."""
    out: dict[int, str] = {}
    for pos, nombre, fragmento in DEMOGRAFICAS:
        if pos >= len(columnas) or fragmento not in norm(columnas[pos]):
            raise FormatoInesperado(
                f"En la columna {pos} se esperaba «{fragmento}» y está «{columnas[pos] if pos < len(columnas) else '—'}».")
        out[pos] = nombre
    for pos, nombre in zip(range(19, 34), IRI):
        out[pos] = nombre
    for pos in range(34, 44):
        out[pos] = f"PSS{pos - 33}"
    for pos, nombre in zip(range(44, 60), ERS):
        out[pos] = nombre
    for pos in range(60, 76):
        out[pos] = f"PRPS_CE{pos - 59}"
    out[76] = "PRPS_Fam_T"
    for ini, fin, prefijo in BLOQUES:
        for pos in range(ini, fin):
            out[pos] = f"{prefijo}{pos - ini + 1}"
    for pos in range(171, len(columnas)):
        t = norm(columnas[pos])
        for fragmento, nombre in EXTRAS.items():
            if all(p in t for p in fragmento.split()):
                out[pos] = nombre
    # Comprobaciones de anclaje: el primer ítem de cada bloque grande
    anclas = {19: "compasion", 34: "controlar", 44: "claridad", 60: "rapido", 77: "decidir",
              120: "agotad", 145: "motivacion", 168: "desconect"}
    for pos, fragmento in anclas.items():
        if pos < len(columnas) and fragmento not in norm(columnas[pos]):
            raise FormatoInesperado(
                f"La columna {pos} debería empezar el bloque «{fragmento}» y dice «{columnas[pos][:70]}».")
    return out


def preparar(bruto: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """(archivo codificado, informe). No modifica `bruto`."""
    informe: dict = dict(filas_archivo=len(bruto))
    columnas = list(bruto.columns)
    renombres = _renombres(columnas)

    consentimiento = bruto.iloc[:, 1].map(lambda v: norm(v) in ("si", "si, acepto", "acepto"))
    informe["sin_consentimiento"] = int((~consentimiento).sum())
    d = bruto[consentimiento].copy()
    respondieron = d.iloc[:, 3:].notna().sum(axis=1) > 0
    informe["sin_respuestas"] = int((~respondieron).sum())
    d = d[respondieron]

    d = d.rename(columns={columnas[p]: n for p, n in renombres.items()})
    d = d[[c for c in d.columns if c in set(renombres.values())]].copy()
    fechas = pd.to_datetime(bruto.loc[d.index, columnas[0]], errors="coerce")
    d = d.drop(columns=["Consentimiento", "Nombre"]).reset_index(drop=True)
    d.insert(0, "ID", [f"D{i + 1:03d}" for i in range(len(d))])
    d.insert(1, "Fecha de respuesta", fechas.dt.date.values)
    d.insert(2, "Versión del formulario",
             np.where(fechas.dt.year.values >= 2026, "2026 (acuerdo en 5 opciones)",
                      "2025 (acuerdo en 6 opciones)"))

    # ── sociodemográficas: texto legible, números donde son números
    d["Edad"] = pd.to_numeric(d["Edad"].astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    d.loc[(d["Edad"] < 18) | (d["Edad"] > 80), "Edad"] = np.nan
    for c in ("Número de hijos", "Estrato socioeconómico", "Número de horas de trabajo semanal",
              "Años experiencia laboral", "Horas extra semanales"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    for c in ("Sexo", "Estado Civil", "Nivel educativo", "Zona Vivienda", "Tipo de Contrato",
              "Ingreso salarial mensual", "Nivel de Cargo", "Personas acargo",
              "Cargo (detalle)", "Nivel en que dicta clase", "Este es un colegio"):
        if c in d.columns:
            d[c] = d[c].map(lambda v: re.sub(r"\s+", " ", str(v)).strip() if pd.notna(v) else np.nan)
    d["Nivel educativo"] = d["Nivel educativo"].replace({
        "Técnico o tecnológico, Profesional, titulo universitario, Posgrado (Especialización, Maestría o Doctorado)":
        "Posgrado (Especialización, Maestría o Doctorado)"})
    d["Jornada o curso"] = d["Jornada o curso"].map(lambda v: str(v).strip() if pd.notna(v) else np.nan)

    codigos = d["Colegio"].map(colegio)
    d["Sede"] = d["Colegio"].map(sede)
    no_reconocidos = sorted({str(v) for v, (c, _) in zip(d["Colegio"], codigos)
                             if pd.notna(v) and not c})
    d["Colegio"] = codigos.map(lambda t: t[1] or np.nan)
    informe["colegios_no_reconocidos"] = no_reconocidos
    informe["sin_colegio"] = int(d["Colegio"].isna().sum())

    # ── ítems
    sin_mapear: dict[str, list] = {}
    items = [c for c in d.columns if any(c.startswith(p) for p, _ in MAPA_POR_PREFIJO)
             and c != "PRPS_Fam_T"]
    for c in items:
        mapa = next(MAPAS[m] for p, m in MAPA_POR_PREFIJO if c.startswith(p))
        antes = d[c].copy()
        d[c] = aplicar(antes, mapa)
        perdidos = antes[antes.notna() & d[c].isna()].map(str).unique().tolist()
        if perdidos:
            sin_mapear[c] = perdidos
    informe["valores_sin_mapear"] = sin_mapear
    d["PRPS_Fam_T"] = pd.to_numeric(d["PRPS_Fam_T"].astype(str).str.extract(r"(\d+)")[0],
                                    errors="coerce")
    for maximo, cols in INVERTIDOS.items():
        for c in cols:
            if c in d.columns:
                d[c] = maximo - d[c]

    # ── totales por escala (suma de ítems; NaN si faltan todos)
    totales = {}
    for prefijo in TOTALES:
        cols = [c for c in items if re.fullmatch(rf"{re.escape(prefijo)}\d+|{re.escape(prefijo)}\(\d+\)", c)]
        if cols:
            totales[f"{prefijo}_T"] = d[cols].sum(axis=1, min_count=1)
    d = pd.concat([d, pd.DataFrame(totales, index=d.index)], axis=1)

    informe["filas_validas"] = len(d)
    informe["columnas"] = len(d.columns)
    informe["colegios"] = d["Colegio"].value_counts().to_dict()
    informe["version_formulario"] = d["Versión del formulario"].value_counts().to_dict()
    return d, informe


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    entrada, salida = argv
    bruto = pd.read_excel(entrada) if entrada.lower().endswith((".xlsx", ".xls")) else pd.read_csv(entrada)
    d, informe = preparar(bruto)
    d.to_excel(salida, index=False) if salida.lower().endswith(".xlsx") else d.to_csv(salida, index=False)
    print(f"Filas en el archivo: {informe['filas_archivo']}")
    print(f"  sin consentimiento (descartadas): {informe['sin_consentimiento']}")
    print(f"  sin ninguna respuesta (descartadas): {informe['sin_respuestas']}")
    print(f"  válidas: {informe['filas_validas']}  ·  columnas: {informe['columnas']}")
    print(f"  sin colegio: {informe['sin_colegio']}  ·  no reconocidos: {informe['colegios_no_reconocidos']}")
    for c, n in informe["colegios"].items():
        print(f"    {c}: {n}")
    print(f"  versión del formulario: {informe['version_formulario']}")
    if informe["valores_sin_mapear"]:
        print("  Valores que no se pudieron codificar (quedan vacíos):")
        for c, vals in informe["valores_sin_mapear"].items():
            print(f"    {c}: {vals}")
    print(f"✓ Escrito {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
