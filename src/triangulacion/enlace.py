"""
Enlace de díadas niño–cuidador — solo local (spec §5.6, capa 2).

Regla única, sin coincidencias aproximadas:

    seudónimo HMAC «N…» del nombre normalizado del niño en el formulario de
    estudiantes  ==  el del hijo en el de cuidadores  (misma clave local)
    Y  mismo código de colegio en los dos (y que sea un colegio reconocido).

Un nombre escrito distinto («Nina» por «Niña» no lo arregla la normalización)
no enlaza. Un mismo nombre en colegios distintos se descarta y se cuenta; un
seudónimo repetido dentro de un colegio (en cualquiera de los dos lados) es
ambiguo, se descarta entero y también se cuenta.

`enlazar` devuelve las díadas (solo en memoria: nunca se guardan, se muestran
ni se exportan) y un informe de calidad que solo tiene conteos y tasas:
coincidencias, descartes por colegio y concordancia de sexo, edad (± 1 año) y
grado. La vista junta los colegios con menos de 10 díadas en «otros
colegios» (`reparto_legible`), de modo que ningún conteo pequeño sale
restando del total, y da las tasas con la regla 3 ≤ k ≤ n − 3.

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


def _claves_repetidas(d: pd.DataFrame, columna: str) -> set:
    """(seudónimo, colegio) que aparecen más de una vez en un mismo lado."""
    c = d.groupby([columna, "Colegio"], dropna=False).size()
    return set(c[c > 1].index)


def _sin_claves(d: pd.DataFrame, columna: str, claves: set) -> pd.DataFrame:
    if not claves:
        return d
    fuera = pd.Series([(i, c) in claves for i, c in zip(d[columna], d["Colegio"])],
                      index=d.index)
    return d[~fuera]


def enlazar(estudiantes: pd.DataFrame, ninos: pd.DataFrame,
            cuidadores: pd.DataFrame) -> Enlace:
    """Díadas verificadas con el colegio e informe agregado de la calidad del enlace.

    Un seudónimo repetido dentro del mismo colegio en cualquiera de los dos
    lados (dos estudiantes o dos hijos con el mismo nombre normalizado) es
    ambiguo: esa clave se descarta en los dos lados y se cuenta en
    `descartadas_ambiguas` (nunca se elige «el primero»). Así
    coincidencias = verificadas + colegio distinto + no reconocido + ambiguas.
    """
    e = estudiantes[estudiantes[COLUMNA_NINO].notna()].reset_index(drop=True)
    n = ninos[ninos["ID_nino"].notna() & ~ninos["ID_nino"].astype(str).str.startswith("sin-")]
    n = n.reset_index(drop=True)
    rep_e, rep_n = _claves_repetidas(e, COLUMNA_NINO), _claves_repetidas(n, "ID_nino")
    claves_e = set(zip(e[COLUMNA_NINO], e["Colegio"]))
    claves_n = set(zip(n["ID_nino"], n["Colegio"]))
    ambiguas = (rep_e | rep_n) & claves_e & claves_n
    e1 = _sin_claves(e, COLUMNA_NINO, rep_e | rep_n)
    n1 = _sin_claves(n, "ID_nino", rep_e | rep_n)
    m = (e1.assign(_pe=e1.index).merge(n1.assign(_pn=n1.index), left_on=COLUMNA_NINO,
                                       right_on="ID_nino", how="inner", suffixes=("_e", "_c"))
         .reset_index(drop=True))
    reconocido = ~m["Colegio_e"].isin(cat.COLEGIOS_SIN_GRUPO)
    mismo = m["Colegio_e"] == m["Colegio_c"]
    ok = m[mismo & reconocido].reset_index(drop=True)
    informe = dict(
        estudiantes_con_nombre=int(e[COLUMNA_NINO].nunique()),
        ninos_con_nombre=int(n["ID_nino"].nunique()),
        coincidencias_nombre=len(m) + len(ambiguas), verificadas=len(ok),
        descartadas_colegio_distinto=int((~mismo).sum()),
        descartadas_colegio_no_reconocido=int((mismo & ~reconocido).sum()),
        descartadas_ambiguas=len(ambiguas),
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
    lado_e = e.loc[ok["_pe"]].reset_index(drop=True)
    lado_c = n.loc[ok["_pn"]].reset_index(drop=True)
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
    if isinstance(valor, str) and valor.strip() == f"<{cat.MIN_GROUP_N}":
        return valor.strip()               # ya enmascarado (corrida publicada)
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return "—"
    return str(v) if v >= cat.MIN_GROUP_N else f"<{cat.MIN_GROUP_N}"


OTROS_COLEGIOS = f"otros colegios (<{cat.MIN_GROUP_N} en total o por colegio)"
OTROS_NIVELES = f"otros niveles (<{cat.MIN_GROUP_N})"


def reparto(conteos: dict) -> tuple[dict, int, str | None]:
    """(grupos con 10 o más, total de «otros», grupo absorbido por «otros» o None).

    Los grupos con menos de 10 y los códigos que no son colegio (OTRO,
    SIN_DATO) van juntos en «otros». Si «otros» queda con 1 a 9, se le suma el
    grupo publicado más pequeño: así el total exacto, menos los grupos
    mostrados, nunca deja de 1 a 9 (ni un colegio pequeño solo).
    """
    grandes = {str(k): int(v) for k, v in conteos.items()
               if int(v) >= cat.MIN_GROUP_N and str(k) not in cat.COLEGIOS_SIN_GRUPO}
    otros = sum(int(v) for k, v in conteos.items() if str(k) not in grandes)
    absorbido = None
    if 0 < otros < cat.MIN_GROUP_N and grandes:
        absorbido = min(grandes, key=lambda k: (grandes[k], k))
        otros += grandes.pop(absorbido)
    return grandes, otros, absorbido


def reparto_legible(conteos: dict, otros: str = OTROS_COLEGIOS) -> dict:
    """{etiqueta: valor} con los grupos de 10 o más y una fila «otros» (ver `reparto`)."""
    grandes, n_otros, absorbido = reparto(conteos)
    salida = {k: str(v) for k, v in sorted(grandes.items())}
    if n_otros:
        salida[f"{absorbido} y {otros}" if absorbido else otros] = conteo_legible(n_otros)
    return salida


def total_legible(total: int, partes: list) -> str:
    """El total exacto solo si lo que no se muestra exacto suma 0 o 10 o más."""
    exactas = sum(int(p) for p in partes if int(p) >= cat.MIN_GROUP_N)
    oculto = int(total) - exactas
    if 0 < oculto < cat.MIN_GROUP_N and exactas:
        return f"más de {exactas}"
    return conteo_legible(total)


def tabla_calidad(informe: dict) -> pd.DataFrame:
    """La calidad del enlace para mostrar y exportar: conteos legibles y tasas.

    Ningún conteo pequeño sale restando: los colegios (y niveles) con menos de
    10 díadas van juntos (`reparto_legible`) y las coincidencias se dan como
    «más de N» si sus descartes pequeños sumarían 1 a 9.
    """
    if not informe:
        return pd.DataFrame(columns=["indicador", "valor"])
    descartes = [informe["descartadas_colegio_distinto"],
                 informe["descartadas_colegio_no_reconocido"],
                 informe.get("descartadas_ambiguas", 0)]
    filas = [
        ("Estudiantes con nombre", conteo_legible(informe["estudiantes_con_nombre"])),
        ("Niños reportados por cuidadores (únicos)", conteo_legible(informe["ninos_con_nombre"])),
        ("Coincidencias exactas del seudónimo",
         total_legible(informe["coincidencias_nombre"], [informe["verificadas"], *descartes])),
        ("Díadas verificadas con el colegio", conteo_legible(informe["verificadas"])),
        ("Familias distintas en las díadas", conteo_legible(informe["familias"])),
        ("Descartadas: colegio distinto", conteo_legible(informe["descartadas_colegio_distinto"])),
        ("Descartadas: colegio no reconocido",
         conteo_legible(informe["descartadas_colegio_no_reconocido"])),
    ]
    if "descartadas_ambiguas" in informe:
        filas.append(("Descartadas: seudónimo repetido en el colegio (ambiguo)",
                      conteo_legible(informe["descartadas_ambiguas"])))
    for colegio, v in reparto_legible(informe["por_colegio"]).items():
        filas.append((f"Díadas en {colegio}", v))
    for nivel, v in reparto_legible(informe["por_nivel"], OTROS_NIVELES).items():
        filas.append((f"Díadas en {nivel}", v))
    for clave, nombre in (("sexo", "Concordancia de sexo"),
                          ("edad", "Concordancia de edad (± 1 año)"),
                          ("grado", "Concordancia de grado")):
        c = informe[clave]
        filas.append((nombre, tasa_legible(c["concordantes"], c["con_dato"])))
    return pd.DataFrame(filas, columns=["indicador", "valor"])
