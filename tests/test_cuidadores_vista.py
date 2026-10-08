"""Cuidadores 360 · vista de investigadores: tablas, paquete y anonimato (fase 4a)."""
import io
import re
import zipfile

import pytest

from src.cuidadores import ingest, pipeline
from src.ui.views import cuidadores_investigador as vi
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()
SEUDONIMO = re.compile(r"\b[CN][0-9a-f]{8}\b")


@pytest.fixture(scope="module")
def ac():
    return pipeline.analizar(ingest.cargar(cs.formulario(), k=K), n_boot=10)


def test_pestanas():
    assert vi.PESTANAS == ["Muestra y exclusiones", "Tabla 1 · descriptivos", "Cortes y bandas",
                           "Correlaciones", "Por grupo", "Señales del adulto",
                           "Ítems sin puntaje", "Calidad de datos", "Exportar"]


def test_tablas_sin_casos_ni_identificadores(ac):
    for t in (vi.tabla1(ac), vi.cortes_y_bandas(ac), vi.cortes_por_grupo(ac),
              vi.correlaciones(ac), vi.comparaciones_grupo(ac), vi.senales_adulto(ac)):
        assert not t.empty
        assert not set(vi.COLUMNAS_PROHIBIDAS) & set(t.columns)


def test_cortes_por_grupo_solo_grupos_publicables(ac):
    t = vi.cortes_por_grupo(ac)
    assert set(t["grupo"]) <= {"LauV", "JJC", "SJMEB", "LaBalsa", "Quinto", "Sexto", "Octavo",
                               "Décimo", "Cuarto", "LauV|Quinto", "LauV|Sexto", "LauV|Octavo",
                               "JJC|Décimo", "JJC|Cuarto"}


def test_senales_adulto_solo_epds(ac):
    t = vi.senales_adulto(ac)
    assert set(t["clave"]) == {"EPDS_Total", "EPDS_Autolesion"}
    assert "Total" in set(t["agrupacion"])


def test_conteos_pequenos_se_enmascaran():
    t = vi.tabla_conteos({"LauV": 35, "CdP": 4}, "Colegio")
    assert t.set_index("Colegio")["Cuidadores"].to_dict() == {"LauV": "35", "CdP": "<10"}


def test_el_zip_es_agregado_y_anonimo(ac):
    z = zipfile.ZipFile(io.BytesIO(vi.paquete_zip(ac)))
    assert set(z.namelist()) == set(vi.ARCHIVOS_PAQUETE)
    for nombre in z.namelist():
        texto = z.read(nombre).decode("utf-8")
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in texto, nombre
        assert not SEUDONIMO.search(texto), nombre
        if nombre.endswith(".csv"):
            assert not set(vi.COLUMNAS_PROHIBIDAS) & set(texto.splitlines()[0].split(","))


def test_metodologia_declara_lo_pendiente(ac):
    md = vi.metodologia_md(ac)
    for fragmento in ("Columna 6", "libro de códigos", "5 / 4 / 3", "OBS360_CLAVE_HMAC",
                      "periodo perinatal", "501", "fuera del rango"):
        assert fragmento in md, fragmento


def test_con_una_ola_no_se_exporta_ni_se_desagrega():
    ac_ola = pipeline.analizar(ingest.cargar(cs.formulario(), k=K), ola="2026", n_boot=5)
    assert not vi.exportable(ac_ola)
    with pytest.raises(ValueError, match="Todas"):
        vi.paquete_zip(ac_ola)
    assert vi.archivos_paquete(ac_ola) == {}
    assert vi.cortes_por_grupo(ac_ola).empty and vi.comparaciones_grupo(ac_ola).empty
    assert "Todas" in vi.SOLO_TODAS


def test_flujo_de_la_muestra_con_una_ola_cuadra():
    carga = ingest.cargar(cs.formulario(), k=K)
    todas = pipeline.analizar(carga, n_boot=5)
    ola = pipeline.analizar(carga, ola="2025", n_boot=5)
    md = vi.flujo_exclusiones_md(ola.informe, ola)
    assert "Archivo completo" in md and "Ola 2025" in md
    for marco, a in ola.marcos.items():
        f = ola.flujo_ola[marco]
        assert f["distintos"] == todas.marcos[marco].n
        assert f["en_base"] == len(todas.marcos[marco].base.nivel)
        assert f["distintos"] - f["fuera_de_base"] - f["otras_olas"] == a.n
        assert f"quedan {a.n}" in md
    assert "## Ola" not in vi.flujo_exclusiones_md(todas.informe, todas)
