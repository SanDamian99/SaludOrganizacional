"""Triangulación · enlace exacto de díadas, verificado con el colegio."""
import pandas as pd
import pytest

from src.core import seudonimo as seud
from src.triangulacion import enlace as en
from src.triangulacion import fuentes as fu
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def enlace_sint(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_enlace"))
    mp = pytest.MonkeyPatch()
    mp.setenv("OBS360_DATOS_DIR", base)
    try:
        f = fu.cargar(k=K)
    finally:
        mp.undo()
    return en.enlazar(f.estudiantes, f.ninos, f.cuidadores)


def _est(nombre, colegio, **extra):
    return dict(N_hmac=seud.seudonimo(nombre, "N", K), Colegio=colegio, Grado="Sexto",
                Edad=11, Sexo="Mujer", nivel="secundaria", SDQ_Total=10.0, **extra)


def _nino(nombre, colegio, cuidador="C00000001", **extra):
    return dict(ID_nino=seud.seudonimo(nombre, "N", K), ID_cuidador=cuidador,
                Colegio=colegio, Grado="Sexto", Edad=11.0, Sexo="Niña", SDQ_Total=8.0, **extra)


def test_enlaza_solo_con_el_mismo_colegio():
    e = pd.DataFrame([_est("Ana Uno", "LauV"), _est("Ana Dos", "JJC")])
    n = pd.DataFrame([_nino("Ana Uno", "LauV"), _nino("Ana Dos", "LauV", "C00000002")])
    c = pd.DataFrame({"ID_cuidador": ["C00000001", "C00000002"], "EPDS_Total": [5.0, 9.0]})
    r = en.enlazar(e, n, c)
    assert r.informe["coincidencias_nombre"] == 2 and r.informe["verificadas"] == 1
    assert r.informe["descartadas_colegio_distinto"] == 1
    assert len(r.diadas) == 1 and r.diadas.loc[0, "a_EPDS_Total"] == 5.0


def test_no_hay_coincidencias_aproximadas():
    e = pd.DataFrame([_est("María José Pérez", "LauV"), _est("Maria Jose Perez", "JJC")])
    n = pd.DataFrame([_nino("Maria Jose Peres", "LauV"), _nino("MARÍA  JOSÉ PÉREZ", "JJC")])
    c = pd.DataFrame({"ID_cuidador": ["C00000001"], "EPDS_Total": [5.0]})
    r = en.enlazar(e.iloc[[0]], n, c)
    # «Peres» no enlaza con «Pérez»; mayúsculas, tildes y espacios sí (normalización),
    # pero esa coincidencia está en otro colegio y se descarta.
    assert r.informe["coincidencias_nombre"] == 1 and r.informe["verificadas"] == 0


def test_un_colegio_no_reconocido_no_verifica():
    e = pd.DataFrame([_est("Luis", "OTRO")])
    n = pd.DataFrame([_nino("Luis", "OTRO")])
    c = pd.DataFrame({"ID_cuidador": ["C00000001"]})
    r = en.enlazar(e, n, c)
    assert r.informe["verificadas"] == 0 and r.informe["descartadas_colegio_no_reconocido"] == 1


def test_las_diadas_no_llevan_nombres_ni_seudonimos_del_nino():
    e = pd.DataFrame([_est("Ana Uno", "LauV")])
    n = pd.DataFrame([_nino("Ana Uno", "LauV")])
    r = en.enlazar(e, n, pd.DataFrame({"ID_cuidador": ["C00000001"]}))
    columnas = set(r.diadas.columns)
    assert not columnas & {"N_hmac", "ID_nino", "e_N_hmac", "c_ID_nino", "ID", "e_ID"}
    assert {"familia", "Colegio", "e_SDQ_Total", "c_SDQ_Total"} <= columnas


def test_sintetico_enlaza_lo_esperado(enlace_sint):
    inf = enlace_sint.informe
    # 72 hijos 1 de LauV, JJC y SJMEB menos el 13 (sin estudiante) y el 41 (mal escrito)
    # = 70 coincidencias, más 4 hijos 2; el 40 está en otro colegio y se descarta.
    assert inf["coincidencias_nombre"] == 74
    assert inf["verificadas"] == 73 and inf["descartadas_colegio_distinto"] == 1
    assert inf["por_colegio"] == {"LauV": 37, "JJC": 22, "SJMEB": 14}
    assert inf["familias"] < inf["verificadas"]          # familias con dos díadas
    assert inf["grado"]["concordantes"] == inf["grado"]["con_dato"]


def test_tasas_y_conteos_legibles():
    assert en.conteo_legible(9) == "<10" and en.conteo_legible(10) == "10"
    assert en.tasa_legible(97, 100) == "97,0 %"
    assert en.tasa_legible(99, 100) == "casi todas"
    assert en.tasa_legible(2, 100) == "casi ninguna"
    assert en.tasa_legible(5, 9) == "—"


def test_tabla_de_calidad_oculta_los_conteos_pequenos(enlace_sint):
    t = en.tabla_calidad(enlace_sint.informe)
    valores = dict(zip(t["indicador"], t["valor"]))
    assert valores["Descartadas: colegio distinto"] == "<10"
    assert valores["Díadas en LauV"] == "37"
