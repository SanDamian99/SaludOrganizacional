"""
Formulario sintético de «Cuidando al Cuidador» para las pruebas (spec §7).

Nada sale de los datos reales: los encabezados se arman con los fragmentos de
`catalog.VERIFICAR` y las respuestas con las etiquetas de opción del
formulario (que son fijas, no datos personales). Lleva centinelas de
privacidad que nunca deben aparecer en ninguna salida:

  · nombres «Centinela …» de cuidadores y niños, y un tercer hijo en la 208;
  · el teléfono 3000000000 en la columna 179.

Configuración (después de consentimiento y deduplicación):
  · LauV: celdas de quinto (12), sexto (12) y octavo (10) → 34 cuidadores.
  · JJC: décimo (12) y cuarto (12), con el curso escrito de muchas formas.
  · SJMEB: 7 de séptimo y 7 de noveno → ninguna celda; el colegio entero (14).
  · La Balsa: 12 con once, transición, tercero o jardín → sin grado del estudio.
  · CdP (4) y un colegio que no se reconoce (3): el resto, que no llega a 10.
  · Repetidos: el cuidador 0 también respondió en 2025; el niño del cuidador 1
    lo reporta también su papá; el cuidador 2 repite al hijo 1 como hijo 2.
  · Una fila sin consentimiento, dos «Columna 6» en la PSS, una edad «diez» y
    una edad 19.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.cuidadores import catalog as cat

CLAVE_PRUEBA = "clave-de-prueba-solo-para-tests-0001"
TELEFONO = "3000000000"
PREFIJO_NOMBRE = "Centinela"

ETIQUETAS = {
    "BARRIO": ["No", "Sí, pero con baja frecuencia", "Sí, es muy frecuente"],
    "PSS": ["Nunca", "Casi nunca", "De vez en cuando", "Frecuentemente", "Casi siempre"],
    "MSPSS": ["Nunca", "Casi nunca", "Algunas veces", "Casi siempre", "Siempre"],
    "APQ": ["Nunca", "Casi nunca", "A veces", "Muy seguido", "Siempre"],
    "EP": ["Muy en desacuerdo", "En desacuerdo", "No estoy seguro", "De acuerdo",
           "Muy de acuerdo"],
    "SDQ": ["No es cierto", "Un tanto cierto", "Absolutamente cierto"],
    "ARI": ["No es cierto", "A veces cierto", "Cierto"],
}
# Las cuatro opciones de cada ítem de la EPDS, en el orden en que aparecen.
EPDS_OPCIONES = [
    ["Tanto como siempre he podido hacerlo", "No tanto ahora", "Sin duda, mucho menos ahora",
     "No, en absoluto"],
    ["Tanto como siempre", "Algo menos de lo que solía hacerlo",
     "Definitivamente menos de lo que solía hacerlo", "Prácticamente nunca"],
    ["Sí, casi siempre", "Sí, algunas veces", "No muy a menudo", "No, nunca"],
    ["No, en absoluto", "Casi nada", "Sí, a veces", "Sí, muy amenudo"],
    ["Sí, bastante", "Sí, a veces", "No, no mucho", "No, en absoluto"],
    ["Sí, la mayor parte del tiempo no he podido sobrellevarllas",
     "Sí, a veces no he podido sobrellevarlas de la mejor manera",
     "No, la mayoría de las veces he podido sobrellevarlas bastante bien",
     "No, he podido sobrellevarlas tan bien como lo he hecho simpre"],
    ["Sí, casi siempre", "Sí, a veces", "No muy a menudo", "No, en absoluto"],
    ["Sí, casi siempre", "Sí, a veces", "No muy a menudo", "No, en absoluto"],
    ["Sí, casi siempre", "Sí, a veces", "No muy a menudo", "No, nunca"],
    ["Sí, bastante a menudo", "A veces", "Casi nunca", "No, nunca"],
]

# Curso tal como lo escriben los cuidadores → grado esperado.
CURSOS = {
    "Quinto": ["Quinto", "501", "5A", "quinto B", "5°"],
    "Sexto": ["Sexto 602", "601", "6", "sexto"],
    "Octavo": ["Octavo", "803", "8vo"],
    "Décimo": ["1002", "Décimo", "10", "decimo A"],
    "Cuarto": ["Cuarto", "402", "4to", "4 - 1"],
    "Séptimo": ["Séptimo", "703"],
    "Noveno": ["Noveno", "901"],
    "fuera": ["Once", "1101", "Transición", "Tercero", "Jardín", "11"],
}

# (texto del colegio, [(grado, cuántos)])
PLAN = [
    ("Colegio Laura Vicuña", [("Quinto", 12), ("Sexto", 12), ("Octavo", 10)]),
    ("IE José Joaquín Casas", [("Décimo", 12), ("Cuarto", 12)]),
    ("San José María Escrivá de Balaguer", [("Séptimo", 7), ("Noveno", 7)]),
    ("Colegio La Balsa", [("fuera", 12)]),
    ("Cerca de Piedra", [("Quinto", 4)]),
    ("Colegio Inventado del Norte", [("Sexto", 3)]),
]


def encabezados() -> list[str]:
    return [f"{cat.VERIFICAR[p]} ({p})" if p in cat.VERIFICAR else f"Columna {p}"
            for p in range(cat.N_COLUMNAS)]


def nombre_cuidador(i: int) -> str:
    return f"{PREFIJO_NOMBRE} Cuidador {i:03d}"


def nombre_nino(i: int, hijo: int = 1) -> str:
    return f"{PREFIJO_NOMBRE} Nino {i:03d}-{hijo}"


def _fila_base(rng, i: int, colegio: str, curso: str, ts: str, quien: str = "Mamá") -> dict:
    f = {p: None for p in range(cat.N_COLUMNAS)}
    f[0] = ts
    f[1] = "Sí autorizo"
    f[2] = quien
    f[3] = nombre_cuidador(i)
    f[4] = nombre_nino(i, 1)
    f[5] = str(7 + i % 9) if i % 5 else f"{7 + i % 9} años"
    f[6] = "Niña" if i % 2 else "Niño"
    f[7] = colegio
    f[8] = "Oficial o púbico"
    f[9] = curso
    f[10], f[12], f[13], f[15] = "Sí", "Bachiller", "Sí", "Técnico o tecnólogo"
    f[17], f[18], f[19] = "Muy bueno", "Urbana (en la cuidad o pueblo)", str(1 + i % 4)
    for b in cat.BLOQUES_CUIDADOR:
        for j, p in enumerate(b.posiciones):
            if b.key == "EPDS":
                f[p] = EPDS_OPCIONES[j][int(rng.integers(0, 4))]
            else:
                opciones = ETIQUETAS[b.key]
                f[p] = opciones[int(rng.integers(0, len(opciones)))]
    for p in cat.bloque_sdq(1).posiciones:
        f[p] = ETIQUETAS["SDQ"][int(rng.integers(0, 3))]
    if ts.startswith("2026"):                     # el ARI solo existe en 2026
        for p in cat.bloque_ari(1).posiciones:
            f[p] = ETIQUETAS["ARI"][int(rng.integers(0, 3))]
    f[146] = "No"
    f[178] = "Sí"
    f[179] = TELEFONO
    f[208] = f"{PREFIJO_NOMBRE} Tercero {i:03d}"
    return f


def _hijo2(rng, f: dict, i: int, colegio: str, curso: str, nombre: str | None = None) -> None:
    f[146] = "Sí"
    f[147] = nombre or nombre_nino(i, 2)
    f[148] = str(8 + i % 7)
    f[149] = "Niño" if i % 2 else "Niña"
    f[150] = colegio
    f[151] = "Oficial o público"
    f[152] = curso
    for p in cat.bloque_sdq(2).posiciones:
        f[p] = ETIQUETAS["SDQ"][int(rng.integers(0, 3))]
    if str(f[0]).startswith("2026"):
        for p in cat.bloque_ari(2).posiciones:
            f[p] = ETIQUETAS["ARI"][int(rng.integers(0, 3))]


def formulario(semilla: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    filas: list[dict] = []
    i = 0
    for colegio, grupos in PLAN:
        for grado, cuantos in grupos:
            variantes = CURSOS[grado]
            for j in range(cuantos):
                ts = "2026-03-10 08:00:00" if i % 4 else "2025-09-15 09:00:00"
                ts = ts.replace(":00:00", f":{i % 60:02d}:00")
                f = _fila_base(rng, i, colegio, variantes[j % len(variantes)], ts,
                               quien="Abuelo o abuela" if i % 11 == 10 else "Mamá")
                if i % 3 == 0 and i > 2:
                    _hijo2(rng, f, i, colegio, variantes[(j + 1) % len(variantes)])
                filas.append(f)
                i += 1
    # Calidad: dos «Columna 6» en la PSS, una edad no numérica y una de 19.
    filas[5][cat.PSS.inicio + 6] = "Columna 6"
    filas[6][cat.PSS.inicio + 8] = "Columna 6"
    filas[7][5] = "diez"
    filas[8][5] = "19"
    # El cuidador 2 repite a su hijo 1 como hijo 2 en el mismo envío.
    _hijo2(rng, filas[2], 2, filas[2][7], filas[2][9], nombre=nombre_nino(2, 1))
    # El cuidador 0 también respondió en 2025, antes (se queda la de 2026).
    filas[0][0] = "2026-03-10 08:00:00"
    viejo = _fila_base(rng, 0, filas[0][7], filas[0][9], "2025-09-01 10:00:00")
    filas.append(viejo)
    # El papá del niño del cuidador 1 también lo reporta (se queda la mamá).
    papa = _fila_base(rng, 900, filas[1][7], filas[1][9], filas[1][0], quien="Papá")
    papa[4] = nombre_nino(1, 1)
    filas.append(papa)
    # Sin consentimiento: no entra a nada.
    no = _fila_base(rng, 901, "Colegio Laura Vicuña", "Quinto", "2026-03-11 10:00:00")
    no[1] = "No autorizo"
    filas.append(no)
    return pd.DataFrame([[f[p] for p in range(cat.N_COLUMNAS)] for f in filas],
                        columns=encabezados())


def escribir(ruta, semilla: int = 7) -> str:
    """Escribe el formulario como xlsx con el nombre que busca la aplicación."""
    import os
    os.makedirs(os.path.dirname(str(ruta)) or ".", exist_ok=True)
    formulario(semilla).to_excel(ruta, index=False)
    return str(ruta)


def textos_prohibidos() -> list[str]:
    """Lo que nunca puede aparecer en ninguna salida."""
    return [PREFIJO_NOMBRE, TELEFONO]
