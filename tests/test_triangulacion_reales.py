"""
Triangulación 360 con los archivos reales (se omite si falta alguno).

Solo se comparan AGREGADOS con el recuento del 8-oct-2026 (spec §5.6 y §7:
«recuento de díadas»). Ningún mensaje de fallo puede mostrar un valor
individual: las comprobaciones de privacidad comparan conteos (`assert n == 0`).
"""
import io
import re
import zipfile

import pandas as pd
import pytest

from src.core.texto import norm_txt
from src.triangulacion import enlace as en
from src.triangulacion import exportar as ex
from src.triangulacion import fuentes as fu
from src.triangulacion import pipeline

CLAVE = b"clave-de-prueba-solo-para-tests-0001"
DISP = fu.localizar()
pytestmark = pytest.mark.skipif(not DISP.completo,
                                reason="sin los archivos reales de los tres actores")


@pytest.fixture(scope="module")
def fuentes_reales():
    return fu.cargar(DISP, k=CLAVE)


@pytest.fixture(scope="module")
def tri(fuentes_reales):
    return pipeline.analizar(fuentes_reales, n_boot=50)


def test_actores(fuentes_reales):
    assert len(fuentes_reales.estudiantes) == 1295
    assert fuentes_reales.cuidadores["ID_cuidador"].nunique() == 734
    assert len(fuentes_reales.ninos) == 886
    assert len(fuentes_reales.docentes) == 479


def test_recuento_de_diadas(tri):
    inf = tri.enlace
    assert inf["coincidencias_nombre"] == 209
    assert inf["verificadas"] == 208 and inf["descartadas_colegio_distinto"] == 1
    assert inf["familias"] == 194
    assert inf["por_colegio"]["LauV"] == 184 and inf["por_colegio"]["JJC"] == 19
    assert inf["por_colegio"]["LaBalsa"] < 10 and inf["por_colegio"]["SJMEB"] < 10


def test_calidad_del_enlace(tri):
    inf = tri.enlace
    assert (inf["sexo"]["concordantes"], inf["sexo"]["con_dato"]) == (204, 208)
    assert (inf["edad"]["concordantes"], inf["edad"]["con_dato"]) == (202, 206)
    assert (inf["grado"]["concordantes"], inf["grado"]["con_dato"]) == (203, 208)


def test_capa1_con_los_cuatro_colegios_de_la_spec(tri):
    assert tri.capa1.colegios == ["JJC", "LaBalsa", "LauV", "SJMEB"]
    assert tri.capa1.grados == ["Cuarto", "Quinto", "Sexto", "Séptimo", "Octavo",
                                "Noveno", "Décimo"]


def test_toda_cifra_con_10_o_mas(tri):
    for t in (tri.capa1.diferencias, tri.capa1.por_grado):
        con = t[t["d"].notna()]
        pequenos = int((con["n_grupo"] < 10).sum() + (con["n_resto"] < 10).sum())
        assert pequenos == 0
    for t in (tri.diadas.acuerdo, tri.diadas.apoyo, tri.diadas.no_visto):
        con = t[t["motivo"] == ""]
        assert int((con["familias"] < 10).sum()) == 0


def _prohibidos() -> set[str]:
    """Nombres de estudiantes y de cuidadores e hijos, y teléfonos (solo en memoria)."""
    from src.cuidadores import catalog as cat_cuid
    from src.cuidadores import ingest as ing_cuid
    valores = set()
    for ruta in DISP.estudiantes:
        raw = (pd.read_excel(ruta, dtype=str) if ruta.lower().endswith((".xlsx", ".xls"))
               else pd.read_csv(ruta, dtype=str))
        col = next(c for c in raw.columns if "mi nombre completo es" in norm_txt(c))
        valores |= {str(v).strip() for v in raw[col].dropna() if len(str(v).split()) >= 2}
    raw = ing_cuid.leer(DISP.cuidadores)
    for pos in cat_cuid.COLUMNAS_NOMBRE:
        valores |= {str(v).strip() for v in raw.iloc[:, pos].dropna()
                    if len(str(v).split()) >= 2}
    valores |= {d for d in (norm_txt(v).replace(" ", "") for v in raw.iloc[:, 179].dropna())
                if d.isdigit() and len(d) >= 7}
    return valores


def test_ningun_nombre_telefono_ni_seudonimo_en_la_salida(tri):
    prohibidos = _prohibidos()
    textos = [df.astype(str).to_csv() for df in ex.tablas(tri).values()]
    z = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(tri)))
    textos += [z.read(n).decode("utf-8") for n in z.namelist() if not n.endswith(".png")]
    hallados = sum(1 for t in textos for v in prohibidos if v in t)
    assert hallados == 0
    seudonimos = sum(len(re.findall(r"\b[CEN][0-9a-f]{8}\b", t)) for t in textos)
    assert seudonimos == 0


def test_tabla_de_calidad_legible(tri):
    t = en.tabla_calidad(tri.enlace)
    valores = dict(zip(t["indicador"], t["valor"]))
    assert valores["Díadas en LaBalsa"] == "<10" and valores["Díadas en SJMEB"] == "<10"
