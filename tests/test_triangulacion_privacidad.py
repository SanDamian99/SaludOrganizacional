"""
Triangulación · privacidad de punta a punta y paquete exportable (sintéticos).

Nada individual en el objeto que llega a la vista ni en el ZIP: ni nombres, ni
teléfono, ni seudónimos (C… / N… / E…), ni díadas; toda cifra con ≥ 10.
"""
import io
import re
import zipfile

import pytest

from src.triangulacion import catalogo as cat
from src.triangulacion import exportar as ex
from src.triangulacion import pipeline
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()
SEUDONIMO = re.compile(r"\b[CEN][0-9a-f]{8}\b")


@pytest.fixture(scope="module")
def tri(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_priv"))
    mp = pytest.MonkeyPatch()
    mp.setenv("OBS360_DATOS_DIR", base)
    try:
        yield pipeline.cargar_y_analizar(k=K, n_boot=30)
    finally:
        mp.undo()


def _tablas(t) -> dict:
    return ex.tablas(t)


def test_el_resultado_solo_tiene_agregados(tri):
    for nombre, df in _tablas(tri).items():
        assert not {"familia", "ID_cuidador", "ID_nino", "N_hmac", "ID"} & set(df.columns), nombre
        assert len(df) < 200, nombre                  # tablas de grupos, no de personas
    assert not hasattr(tri, "fuentes") and not hasattr(tri.diadas, "datos")


def test_ningun_texto_prohibido_ni_seudonimo_en_el_zip(tri):
    z = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(tri)))
    textos = [z.read(n).decode("utf-8") for n in z.namelist() if not n.endswith(".png")]
    for texto in textos:
        for prohibido in ts.textos_prohibidos():
            assert prohibido not in texto
        assert not SEUDONIMO.search(texto)


def test_el_zip_trae_tablas_figuras_y_metodologia(tri):
    z = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(tri)))
    nombres = set(z.namelist())
    assert {"metodologia.md", "version_analisis.txt", "capa1_diferencias.csv",
            "enlace_calidad.csv", "diadas_acuerdo_sdq.csv"} <= nombres
    for colegio in tri.capa1.colegios:
        assert z.read(f"figuras/capa1_{colegio}.png").startswith(b"\x89PNG")
    assert any(n.startswith("figuras/bland_altman_") for n in nombres)


def test_la_metodologia_es_la_plantilla_fija(tri):
    md = ex.metodologia_md(tri)
    for titulo in ("## Alcance", "## Capa 1 · por colegio y por grado",
                   "## Capa 2 · díadas niño–cuidador", "## Límites"):
        assert titulo in md
    assert cat.AVISO_ENLACE in md and cat.AVISO_COOCURRENCIA in md
    assert cat.AVISO_ECOLOGICO.format(n=tri.n_colegios) in md


def test_bland_altman_no_dibuja_diadas(tri):
    fig = ex.figura_bland_altman(tri, "SDQ_Total")
    ax = fig.axes[0]
    # Los únicos puntos son los cuadrados de los grupos (las barras de error y las
    # líneas horizontales no son datos de personas).
    puntos = sum(len(l.get_xdata()) for l in ax.get_lines() if l.get_marker() == "s")
    assert 0 < puntos <= cat.MAX_BINES_BA
    assert not ax.collections or all(len(c.get_offsets()) <= cat.MAX_BINES_BA
                                     for c in ax.collections if hasattr(c, "get_offsets"))


def test_cada_cifra_de_diadas_tiene_10_familias(tri):
    for t in (tri.diadas.acuerdo, tri.diadas.apoyo):
        con = t[t["motivo"] == ""]
        assert (con["familias"] >= cat.MIN_GROUP_N).all()
    ba = tri.diadas.bland_altman
    assert ba.empty or (ba["n"] >= cat.MIN_GROUP_N).all()
    nv = tri.diadas.no_visto
    pub = nv[nv["motivo"] == ""]
    assert pub.empty or (pub["familias"] >= cat.MIN_GROUP_N).all()


def test_nada_de_triangulacion_sube_a_supabase():
    """Ningún módulo de la triangulación importa el cliente de Supabase ni el publicador."""
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parents[1]
    archivos = [*(raiz / "src" / "triangulacion").glob("*.py"),
                raiz / "src" / "ui" / "triangulacion.py",
                raiz / "src" / "ui" / "views" / "triangulacion_investigador.py"]
    prohibidos = re.compile(r"^\s*(from|import)\s+.*(supabase|publicar|lectura|almacen)",
                            re.MULTILINE)
    for f in archivos:
        assert not prohibidos.search(f.read_text(encoding="utf-8")), f.name
