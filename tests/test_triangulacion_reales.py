"""
Triangulación 360 con los archivos reales (se omite si falta alguno).

Solo se comprueban AGREGADOS con relaciones y rangos robustos (identidades del
recuento de díadas, mínimos de 10, coherencia de la concordancia), no cifras
fijas: los archivos se renuevan. Ningún mensaje de fallo puede mostrar un
valor individual: las comprobaciones de privacidad comparan conteos
(`assert n == 0`).
"""
import io
import re
import zipfile

import pandas as pd
import pytest

from src.core.texto import norm_txt
from src.estudiantes import privacidad as pe
from src.triangulacion import capa1 as c1
from src.triangulacion import catalogo as cat
from src.triangulacion import enlace as en
from src.triangulacion import exportar as ex
from src.triangulacion import fuentes as fu
from src.triangulacion import pipeline

CLAVE = b"clave-de-prueba-solo-para-tests-0001"
MIN = cat.MIN_GROUP_N
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
    """Los tres actores llegan con datos (sin fijar recuentos: los archivos se renuevan)."""
    assert len(fuentes_reales.estudiantes) >= MIN
    assert fuentes_reales.cuidadores["ID_cuidador"].nunique() >= MIN
    assert len(fuentes_reales.ninos) >= fuentes_reales.ninos["ID_cuidador"].nunique() > 0
    assert len(fuentes_reales.docentes) >= MIN


def test_recuento_de_diadas(tri):
    inf = tri.enlace
    descartes = (inf["descartadas_colegio_distinto"] + inf["descartadas_colegio_no_reconocido"]
                 + inf["descartadas_ambiguas"])
    assert inf["coincidencias_nombre"] == inf["verificadas"] + descartes
    assert inf["verificadas"] == sum(inf["por_colegio"].values()) == sum(inf["por_nivel"].values())
    assert MIN <= inf["familias"] <= inf["verificadas"]
    assert inf["verificadas"] <= min(inf["estudiantes_con_nombre"], inf["ninos_con_nombre"])
    assert cat.COLEGIO_SENSIBILIDAD in inf["por_colegio"]
    assert tri.diadas.n == inf["verificadas"] and tri.diadas.familias == inf["familias"]


def test_calidad_del_enlace(tri):
    """Concordancia coherente y alta: un enlace roto la hundiría."""
    inf = tri.enlace
    for clave in ("sexo", "edad", "grado"):
        c = inf[clave]
        assert 0 <= c["concordantes"] <= c["con_dato"] <= inf["verificadas"]
        assert c["concordantes"] >= 0.8 * c["con_dato"]


def test_capa1_con_colegios_y_grados_validos(tri):
    from src.cuidadores import catalog as cat_cuid
    colegios, grados = tri.capa1.colegios, tri.capa1.grados
    assert len(colegios) >= 2 and colegios == sorted(colegios)
    assert not set(colegios) & set(cat.COLEGIOS_SIN_GRUPO)
    assert grados and grados == [g for g in cat_cuid.GRADOS_ESTUDIO if g in grados]
    assert set(tri.capa1.diferencias["grupo"]) == set(colegios)


def _unidades_minimas(fuentes, capa) -> int:
    """Cifras de la capa 1 cuyo grupo o resto tiene menos de 10 UNIDADES distintas
    (cuidadores en los marcos de cuidadores y niños, no filas)."""
    tablas = c1.marcos(fuentes)
    por_marco = {m: c1.atomos(d, m) for m, d in tablas.items()}
    pequenas = 0
    for agrupacion, t in (("Colegio", capa.diferencias), ("Grado", capa.por_grado)):
        for _, f in t[t["d"].notna()].iterrows():
            c = cat.POR_CLAVE[f["clave"]]
            d = tablas[c.marco]
            ok = [a for a in por_marco[c.marco] if c1._atomo_ok(d, a, c.marco, c)]
            for lado in (True, False):
                sel = [a for a in ok if c1._del_grupo(a, agrupacion, f["grupo"]) == lado]
                idx = pe.union(a.idx for a in sel)
                idx = idx[d.loc[idx, c.columna].notna().to_numpy()]
                pequenas += int(c1.n_unidades(d.loc[idx], c.marco) < MIN)
    return pequenas


def test_toda_cifra_con_10_o_mas(fuentes_reales, tri):
    assert int(tri.capa1.diferencias["d"].notna().sum()) > 0
    assert _unidades_minimas(fuentes_reales, tri.capa1) == 0
    d = tri.diadas
    for t in (d.acuerdo, d.apoyo, d.no_visto, d.acuerdo_concordantes, d.asociaciones):
        con = t[t["motivo"] == ""] if "motivo" in t.columns else t
        if con.empty:
            continue
        pocas = int((con["familias"] < MIN).sum() + (con["n"] < MIN).sum())
        assert pocas == 0
    ba = d.bland_altman
    assert ba.empty or int((ba["n"] < MIN).sum()) == 0


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
    por_colegio = {k: v for k, v in valores.items() if k.startswith("Díadas en ")
                   and k[len("Díadas en "):] not in tri.enlace["por_nivel"]
                   and en.OTROS_NIVELES not in k}
    # ningún colegio con menos de 10 díadas aparece solo; «otros» llega a 10 o más
    pequenos = [c for c, v in tri.enlace["por_colegio"].items() if v < 10]
    solos = sum(1 for c in pequenos if f"Díadas en {c}" in valores)
    assert solos == 0
    assert all(v != "<10" for v in por_colegio.values()) or len(por_colegio) == 1


def test_capa1_junto_a_los_modulos_no_deduce_piezas_pequenas(fuentes_reales, tri):
    """Capa 1 + lo que publican estudiantes (por nivel) y cuidadores: 0 piezas de 1 a 9."""
    from tests import triangulacion_span as span
    deducibles = span.auditar_capa1(c1.marcos(fuentes_reales), tri.capa1)
    hay_constructos = len(deducibles) > 0
    total = int(sum(deducibles.values()))
    assert hay_constructos
    assert total == 0
