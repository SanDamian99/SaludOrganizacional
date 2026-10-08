"""
Enlace de díadas niño–cuidador — solo local (spec §5.6, capa 2).

Regla única, sin coincidencias aproximadas:

    seudónimo HMAC «N…» del nombre normalizado del niño en el formulario de
    estudiantes  ==  el del hijo en el de cuidadores  (misma clave local)
    Y  mismo código de colegio en los dos (y que sea un colegio reconocido).

Un nombre escrito distinto («Nina» por «Niña» no lo arregla la normalización)
no enlaza. Un mismo nombre en colegios distintos se descarta y se cuenta.

`enlazar` devuelve las díadas (solo en memoria: nunca se guardan, se muestran
ni se exportan) y un informe de calidad que solo tiene conteos y tasas:
coincidencias, descartes por colegio y concordancia de sexo, edad (± 1 año) y
grado. La vista muestra los conteos por colegio como «<10» por debajo del
mínimo y las tasas con la regla 3 ≤ k ≤ n − 3.

Columnas de una díada: `familia` (seudónimo del cuidador, solo para agrupar
errores y contar familias distintas), `Colegio`, las del niño según él con el
prefijo `e_`, las del niño según su cuidador con `c_` y las del cuidador con
`a_`. Ningún nombre ni seudónimo del niño.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.estudiantes.supresion import proporcion_publicable
from src.triangulacion import catalogo as cat

COLUMNA_NINO = "N_hmac"
SEXO_NINO = {"Niña": "Mujer", "Niño": "Hombre"}
# Columnas que nunca pasan a una díada.
FUERA = ("N_hmac", "ID", "ID_nino", "ts", "_fila", "_edad_estado", "Colegio_nombre", "Sede")


@dataclass
class Enlace:
    diadas: pd.DataFrame
    informe: dict = field(default_factory=dict)


def _prefijo(d: pd.DataFrame, prefijo: str, quitar=()) -> pd.DataFrame:
    return d.drop(columns=[c for c in (*FUERA, *quitar) if c in d.columns]).add_prefix(prefijo)


def _concordancia(si: pd.Series, con_dato: pd.Series) -> dict:
    return dict(concordantes=int((si & con_dato).sum()), con_dato=int(con_dato.sum()))


def enlazar(estudiantes: pd.DataFrame, ninos: pd.DataFrame,
            cuidadores: pd.DataFrame) -> Enlace:
    """Díadas verificadas con el colegio e informe agregado de la calidad del enlace."""
    e = estudiantes[estudiantes[COLUMNA_NINO].notna()].drop_duplicates(COLUMNA_NINO)
    n = ninos[ninos["ID_nino"].notna() & ~ninos["ID_nino"].astype(str).str.startswith("sin-")]
    n = n.drop_duplicates("ID_nino")
    m = e.merge(n, left_on=COLUMNA_NINO, right_on="ID_nino", how="inner",
                suffixes=("_e", "_c"), validate="one_to_one")
    reconocido = ~m["Colegio_e"].isin(cat.COLEGIOS_SIN_GRUPO)
    mismo = m["Colegio_e"] == m["Colegio_c"]
    ok = m[mismo & reconocido]
    informe = dict(
        estudiantes_con_nombre=len(e), ninos_con_nombre=len(n),
        coincidencias_nombre=len(m), verificadas=len(ok),
        descartadas_colegio_distinto=int((~mismo).sum()),
        descartadas_colegio_no_reconocido=int((mismo & ~reconocido).sum()),
        familias=int(ok["ID_cuidador"].nunique()) if len(ok) else 0,
        por_colegio={str(k): int(v) for k, v in ok["Colegio_e"].value_counts().items()},
        descartes_por_colegio={str(k): int(v) for k, v in
                               m.loc[~mismo, "Colegio_e"].value_counts().items()},
        por_nivel={str(k): int(v) for k, v in ok["nivel"].value_counts().items()},
    )
    sexo_c = ok["Sexo_c"].map(SEXO_NINO)
    informe["sexo"] = _concordancia(sexo_c == ok["Sexo_e"],
                                    sexo_c.notna() & ok["Sexo_e"].isin(SEXO_NINO.values()))
    edad_ok = ok["Edad_e"].notna() & ok["Edad_c"].notna()
    informe["edad"] = _concordancia((ok["Edad_e"] - ok["Edad_c"]).abs() <= 1, edad_ok)
    informe["grado"] = _concordancia(ok["Grado_e"] == ok["Grado_c"], ok["Grado_c"].notna())

    ids = ok["ID_cuidador"].to_numpy()
    lado_e = e.set_index(COLUMNA_NINO).loc[ok[COLUMNA_NINO]].reset_index()
    lado_c = n.set_index("ID_nino").loc[ok["ID_nino"]].reset_index()
    adulto = cuidadores.drop_duplicates("ID_cuidador").set_index("ID_cuidador")
    lado_a = adulto.reindex(ids).reset_index(drop=True)
    diadas = pd.concat([
        pd.DataFrame({"familia": ids, "Colegio": ok["Colegio_e"].to_numpy()}),
        _prefijo(lado_e, "e_"), _prefijo(lado_c, "c_", quitar=("ID_cuidador",)),
        _prefijo(lado_a, "a_")], axis=1)
    return Enlace(diadas=diadas, informe=informe)


def tasa_legible(k: int, n: int) -> str:
    """Una tasa de concordancia con la regla de cifras pequeñas."""
    if n < cat.MIN_GROUP_N:
        return "—"
    if proporcion_publicable(k, n):
        return f"{100 * k / n:.1f} %".replace(".", ",")
    return "casi todas" if k > n - cat.MIN_CASOS else "casi ninguna"


def conteo_legible(valor) -> str:
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return "—"
    return str(v) if v >= cat.MIN_GROUP_N else f"<{cat.MIN_GROUP_N}"


def tabla_calidad(informe: dict) -> pd.DataFrame:
    """La calidad del enlace para mostrar y exportar: conteos legibles y tasas."""
    if not informe:
        return pd.DataFrame(columns=["indicador", "valor"])
    filas = [
        ("Estudiantes con nombre", conteo_legible(informe["estudiantes_con_nombre"])),
        ("Niños reportados por cuidadores (únicos)", conteo_legible(informe["ninos_con_nombre"])),
        ("Coincidencias exactas del seudónimo", conteo_legible(informe["coincidencias_nombre"])),
        ("Díadas verificadas con el colegio", conteo_legible(informe["verificadas"])),
        ("Familias distintas en las díadas", conteo_legible(informe["familias"])),
        ("Descartadas: colegio distinto", conteo_legible(informe["descartadas_colegio_distinto"])),
        ("Descartadas: colegio no reconocido",
         conteo_legible(informe["descartadas_colegio_no_reconocido"])),
    ]
    for colegio, v in sorted(informe["por_colegio"].items()):
        filas.append((f"Díadas en {colegio}", conteo_legible(v)))
    for nivel, v in sorted(informe["por_nivel"].items()):
        filas.append((f"Díadas en {nivel}", conteo_legible(v)))
    for clave, nombre in (("sexo", "Concordancia de sexo"),
                          ("edad", "Concordancia de edad (± 1 año)"),
                          ("grado", "Concordancia de grado")):
        c = informe[clave]
        filas.append((nombre, tasa_legible(c["concordantes"], c["con_dato"])))
    return pd.DataFrame(filas, columns=["indicador", "valor"])
