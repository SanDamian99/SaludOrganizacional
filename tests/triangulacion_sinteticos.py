"""
Los tres actores sintéticos para la triangulación (spec §7).

Nada sale de los datos reales. Cuidadores es el formulario sintético de la
fase 4a (`cuidadores_sinteticos`); estudiantes y docentes se arman aquí, con
niños que comparten nombre con los hijos de ese formulario:

  · Enlazan (mismo nombre y mismo colegio): los hijos 1 de los cuidadores 0 a
    71 (LauV, JJC y SJMEB), salvo el 13 (sin estudiante), el 40 (estudiante en
    otro colegio: se descarta por colegio) y el 41 (estudiante con una letra
    distinta, «Nina»: no hay coincidencias aproximadas). También los hijos 2
    de los cuidadores 3, 6, 9 y 12 (familias con dos díadas).
  · No enlazan: 12 estudiantes de La Balsa, 4 de Cerca de Piedra y 10 más de
    Laura Vicuña.
  · Docentes (archivo codificado, sin nombres): LauV 15, JJC 12, SJMEB 11,
    La Balsa 10, Cerca de Piedra 5 y 2 de la Secretaría (no es colegio).

Centinelas: todos los nombres empiezan por «Centinela» y el teléfono del
formulario de cuidadores es 3000000000. Ninguno puede aparecer en una salida.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from tests import cuidadores_sinteticos as cs

CLAVE_PRUEBA = cs.CLAVE_PRUEBA
ARCHIVO_SEC = "¡Cuéntanos sobre tu bienestar emocional! (respuestas).xlsx"
ARCHIVO_PRI = "¡Cuéntanos sobre tus emociones! (respuestas).xlsx"
ARCHIVO_CUID = "Cuidando al Cuidador (respuestas).xlsx"
ARCHIVO_DOC = "Docentes_codificado.xlsx"
PRIMARIA = ("Cuarto", "Quinto")
SIN_ESTUDIANTE, OTRO_COLEGIO, MAL_ESCRITO = 13, 40, 41
HIJOS2 = (3, 6, 9, 12)
DOCENTES = (("Laura Vicuña", 15), ("José Joaquín Casas", 12),
            ("San Josemaría Escrivá de Balaguer", 11), ("La Balsa", 10),
            ("Cerca de Piedra", 5), ("Secretaría de Educación", 2))
SDQ_OPC = ["No es cierto", "Algo cierto", "Muy cierto"]
RCADS_OPC = ["Nunca", "Algunas veces", "Con frecuencia", "Siempre"]
ERQ_OPC = ["Nada parecido a mi", "Poco parecido a mi", "Se parece a mi",
           "Bastante parecido a mi", "Exactamente igual a mi"]
MSPSS_OPC = ["Nunca", "Casi nunca", "Algunas veces", "Casi siempre", "Siempre"]
TD_OPC = ["Nunca", "Casi nunca", "A veces", "Casi siempre", "Siempre"]


def ninos_del_plan() -> list[tuple[int, str, str]]:
    """(i, texto del colegio, grado) de cada hijo 1 del formulario sintético de cuidadores."""
    salida, i = [], 0
    for colegio, grupos in cs.PLAN:
        for grado, cuantos in grupos:
            for _ in range(cuantos):
                salida.append((i, colegio, grado))
                i += 1
    return salida


def _estudiante(rng, nombre: str, colegio: str, grado: str, edad: int, sexo: str,
                secundaria: bool) -> dict:
    f = {"Marca temporal": "10/03/2026 10:00:00",
         "¿Quieres aportar al bienestar de todos con tus respuestas?": "Sí, quiero aportar",
         "Mi nombre completo es:": nombre, "Tengo:": f"{edad} años", "Mi sexo es:": sexo,
         "Estoy en grado": grado, "Mi colegio es:": colegio}
    for j in range(1, 26):
        f[f"SDQ [enunciado {j}]"] = SDQ_OPC[int(rng.integers(0, 3))]
    for j in range(1, 8):
        f[f"ARI [enunciado {j}]"] = SDQ_OPC[int(rng.integers(0, 3))]
    if secundaria:
        for j in range(1, 26):
            f[f"RCADS [enunciado {j}]"] = RCADS_OPC[int(rng.integers(0, 4))]
    for j in range(1, 11):
        f[f"ERQ-CA [enunciado {j}]"] = ERQ_OPC[int(rng.integers(0, 5))]
    for j in range(1, 13):
        f[f"MSPSS [enunciado {j}]"] = MSPSS_OPC[int(rng.integers(0, 5))]
    f["Siento que soy parte de mi colegio"] = int(rng.integers(1, 6))
    for j in range(2, 19):
        f[f"PSSM enunciado {j}"] = int(rng.integers(1, 6))
    for j in range(1, 11):
        f[f"Toma de decisiones  [enunciado {j}]"] = TD_OPC[int(rng.integers(0, 5))]
    return f


def estudiantes(semilla: int = 11) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(secundaria, primaria) como exportaciones de Google Forms."""
    rng = np.random.default_rng(semilla)
    filas = []
    plan = ninos_del_plan()
    otro = {"Colegio Laura Vicuña": "IE José Joaquín Casas"}
    for i, colegio, grado in plan:
        if colegio == "Colegio La Balsa" or i >= 72 or i == SIN_ESTUDIANTE:
            continue
        nombre = cs.nombre_nino(i, 1)
        if i == MAL_ESCRITO:
            nombre = nombre.replace("Nino", "Nina")
        if i == OTRO_COLEGIO:
            colegio = otro.get(colegio, "Colegio Laura Vicuña")
        filas.append((nombre, colegio, grado, 10 + i % 6, "Mujer" if i % 2 else "Hombre"))
        if i in HIJOS2:
            filas.append((cs.nombre_nino(i, 2), colegio, grado, 11, "Hombre"))
    for k in range(12):
        filas.append((f"Centinela Estudiante Balsa {k:02d}", "Colegio La Balsa", "Sexto", 12,
                      "Mujer" if k % 2 else "Hombre"))
    for k in range(4):
        filas.append((f"Centinela Estudiante Piedra {k:02d}", "Cerca de Piedra", "Séptimo",
                      13, "Mujer"))
    for k in range(10):
        filas.append((f"Centinela Estudiante Vicuna {k:02d}", "Colegio Laura Vicuña", "Noveno",
                      15, "Hombre" if k % 2 else "Mujer"))
    sec = [_estudiante(rng, n, c, g, e, s, True) for n, c, g, e, s in filas if g not in PRIMARIA]
    pri = [_estudiante(rng, n, c, g, e, s, False) for n, c, g, e, s in filas if g in PRIMARIA]
    return pd.DataFrame(sec), pd.DataFrame(pri)


def docentes(semilla: int = 5) -> pd.DataFrame:
    """Archivo de docentes ya codificado (como el de scripts/preparar_docentes.py)."""
    rng = np.random.default_rng(semilla)
    filas = []
    for colegio, n in DOCENTES:
        for _ in range(n):
            f = {"ID": f"D{len(filas) + 1:03d}", "Colegio": colegio}
            f.update({f"PSS{i}": int(rng.integers(0, 5)) for i in range(1, 11)})
            f.update({f"CL{i}": int(rng.integers(0, 6)) for i in range(1, 8)})
            f.update({f"AP{i}": int(rng.integers(0, 6)) for i in range(1, 4)})
            f.update({f"BLG_Desg{i}": int(rng.integers(1, 8)) for i in range(1, 5)})
            filas.append(f)
    return pd.DataFrame(filas)


def escribir(base) -> str:
    """Los tres actores en `base/{estudiantes,cuidadores,docentes}`, como en datos_fuente_360."""
    base = str(base)
    for sub in ("estudiantes", "cuidadores", "docentes"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    sec, pri = estudiantes()
    sec.to_excel(os.path.join(base, "estudiantes", ARCHIVO_SEC), index=False)
    pri.to_excel(os.path.join(base, "estudiantes", ARCHIVO_PRI), index=False)
    cs.escribir(os.path.join(base, "cuidadores", ARCHIVO_CUID))
    docentes().to_excel(os.path.join(base, "docentes", ARCHIVO_DOC), index=False)
    return base


def textos_prohibidos() -> list[str]:
    """Lo que nunca puede aparecer en ninguna salida."""
    return cs.textos_prohibidos()
