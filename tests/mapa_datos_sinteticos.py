"""Un Analisis de secundaria con cuatro colegios para las pruebas del mapa."""
import pandas as pd

from src.estudiantes.pipeline import Analisis


def analisis_sintetico() -> Analisis:
    """LauV 435, JJC 297, SJMEB 63 son visibles; LaBalsa 7 es pequeño."""
    a = Analisis(nivel="secundaria", n=800, datos=pd.DataFrame())
    a.muestra = {"colegio": {"LauV": 435, "JJC": 297, "SJMEB": 63, "LaBalsa": 7}}
    a.por_colegio = pd.DataFrame([
        {"clave": "PSSM_Total", "escala": "Pertenencia", "p": 0.01, "eta2": 0.02,
         "q_bh": 0.02, "n": 795,
         "M·LauV": 3.4, "n·LauV": 435, "M·JJC": 3.1, "n·JJC": 297,
         "M·SJMEB": 3.6, "n·SJMEB": 63},
        {"clave": "MSPSS_Total", "escala": "Apoyo social", "p": 0.02, "eta2": 0.01,
         "q_bh": 0.03, "n": 795,
         "M·LauV": 5.1, "n·LauV": 435, "M·JJC": 4.8, "n·JJC": 297,
         "M·SJMEB": 5.4, "n·SJMEB": 63},
    ])
    a.descriptivos = pd.DataFrame([
        {"clave": "PSSM_Total", "escala": "Pertenencia", "n": 795, "M": 3.3},
        {"clave": "MSPSS_Total", "escala": "Apoyo social", "n": 795, "M": 5.0},
    ])
    return a
