"""
Cuidadores 360 con el formulario real (se omite si falta el archivo).

Solo se comparan AGREGADOS con la spec (§3.2, §5.5) y con el recuento del
8-oct-2026. Ningún mensaje de fallo puede mostrar un valor individual: las
comprobaciones de privacidad comparan conteos (`assert n == 0`), nunca listas.
"""
import io
import zipfile

import pytest

from src.core.texto import norm_txt
from src.cuidadores import catalog as cat
from src.cuidadores import ingest, pipeline

CLAVE = b"clave-de-prueba-solo-para-tests-0001"
RUTA = pipeline.localizar_formulario()
pytestmark = pytest.mark.skipif(RUTA is None, reason="sin el formulario real de cuidadores")


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(RUTA, k=CLAVE)


@pytest.fixture(scope="module")
def ac(carga):
    return pipeline.analizar(carga, n_boot=50)


def test_formato_y_consentimiento(carga):
    inf = carga.informe
    assert inf.filas_archivo == 779 and inf.sin_consentimiento == 23
    assert inf.respuestas_validas == 756
    assert inf.por_ola == {"2025": 142, "2026": 614}
    assert inf.etiquetas_no_mapeadas == {}
    assert inf.respuestas_columna6_pss == 4


def test_ninos_y_repetidos(ac):
    inf = ac.informe
    assert inf.filas_nino == 973 and inf.hijo2 == 217
    assert inf.ninos_unicos == 886
    assert inf.mismo_nino_misma_respuesta == 72
    assert inf.mismo_nino_otro_cuidador == 6 and inf.mismo_nino_entre_olas == 5
    assert inf.cuidadores_distintos == 734 and inf.cuidadores_en_dos_olas == 6


def test_calibracion_de_la_epds(carga):
    """Spec §5.5: probable 23,3 % y autolesión 11,0 % sobre las 756 respuestas."""
    from src.cuidadores import scoring
    p = scoring.puntuar_cuidadores(carga.respuestas)
    assert round(100 * p["EPDS_Probable"].mean(), 1) == 23.3
    assert round(100 * p["EPDS_Autolesion"].mean(), 1) == 11.0


def test_colegios_con_el_normalizador_corregido(carga):
    c = carga.respuestas["Colegio"].value_counts().to_dict()
    assert c["LauV"] == 448 and c["SJMEB"] == 39 and c["LaBalsa"] == 24
    assert c["DiosCh"] == 13 and c["Bojacá"] == 12 and c["JJC"] == 121


def test_curso_casi_siempre_resuelto(ac):
    assert ac.informe.curso_sin_resolver <= 20
    assert ac.informe.grados.get(cat.SIN_DATO, 0) <= 20


def test_ari_solo_en_2026(carga):
    n = carga.ninos
    assert n.loc[n["Ola"] == "2025", [f"ARI{i}" for i in range(1, 8)]].isna().all().all()
    assert carga.informe.cobertura_ari == {"hijo 1": 382, "hijo 2": 93}


def test_ningun_grupo_publicado_con_menos_de_10_cuidadores(ac):
    for a in ac.marcos.values():
        for agrupacion, grupos in a.subgrupos.items():
            pequenos = sum(s.muestra["n_cuidadores"] < cat.MIN_GROUP_N for s in grupos.values())
            assert pequenos == 0, agrupacion
        assert "OTRO" not in a.subgrupos.get("Colegio", {})


def _prohibidos() -> set[str]:
    """Nombres completos y teléfonos del archivo real (solo en memoria, nunca se imprimen).

    Nombres: dos o más palabras (un «Ninguno» en la casilla del nombre no es un
    nombre y coincide con una opción de nivel educativo). Teléfonos: 7 o más
    dígitos.
    """
    raw = ingest.leer(RUTA)
    valores = set()
    for pos in cat.COLUMNAS_NOMBRE:
        valores |= {str(v).strip() for v in raw.iloc[:, pos].dropna()
                    if len(str(v).split()) >= 2}
    valores |= {d for d in (norm_txt(v).replace(" ", "") for v in raw.iloc[:, 179].dropna())
                if d.isdigit() and len(d) >= 7}
    return valores


def test_ningun_nombre_ni_telefono_en_marcos_ni_exportacion(ac):
    from src.ui.views import cuidadores_investigador as vi
    prohibidos = _prohibidos()
    textos = [a.datos.astype(str).to_csv() for a in ac.marcos.values()]
    z = zipfile.ZipFile(io.BytesIO(vi.paquete_zip(ac)))
    textos += [z.read(n).decode("utf-8") for n in z.namelist()]
    hallados = sum(1 for t in textos for v in prohibidos if v in t)
    assert hallados == 0
