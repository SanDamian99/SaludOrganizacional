"""
Datos sintéticos de docentes para probar la página Docentes con AppTest.

Imitan la forma del archivo real (ítems en la codificación 1 del archivo de
Storage, totales *_T, sexo, edad, colegio) sin una sola fila real. El colegio
«Pequeño» tiene 5 docentes a propósito: sirve para probar que ningún grupo de
menos de 10 se muestra.
"""
import numpy as np
import pandas as pd

# (prefijo, número de ítems, código mínimo, código máximo)
ITEMS = [("PSS", 10, 0, 4), ("BTA", 12, 0, 4), ("Sat", 3, 0, 5), ("AP", 3, 0, 5),
         ("PRPS_CE", 16, 0, 4), ("Descon", 3, 1, 5), ("Conf_FaTr", 5, 1, 7)]

COL_COLEGIO = "Intitución"
COL_SEXO = "(SD)Sexo"
COL_EDAD = "(SD)Edad"
COLEGIO_PEQUENO = "Pequeño"


def docentes(n_grande: int = 60, n_pequeno: int = 5, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = n_grande + n_pequeno
    colegios = ["Grande A"] * (n_grande // 2) + ["Grande B"] * (n_grande - n_grande // 2) \
        + [COLEGIO_PEQUENO] * n_pequeno
    # «No binario» con 3 personas: categoría pequeña que nunca debe salir con su cifra.
    sexo = ["Mujer"] * (n - 25) + ["Hombre"] * 22 + ["No binario"] * 3
    items = {f"{p}{i}": rng.integers(lo, hi + 1, n).astype(float)
             for p, k, lo, hi in ITEMS for i in range(1, k + 1)}
    return pd.DataFrame({
        **items,
        COL_COLEGIO: colegios,
        COL_SEXO: sexo,
        COL_EDAD: rng.integers(24, 62, n),
        "PSS_T": rng.integers(5, 40, n),
        "BTA_T": rng.integers(5, 30, n),
        "Sat_T": rng.integers(5, 35, n),
        "AP_T": rng.integers(5, 25, n),
        "PRPS_CE_T": rng.integers(3, 20, n),
        "Descon_T": rng.integers(3, 20, n),
        "Conf_FaTr_T": rng.integers(3, 20, n),
    })
