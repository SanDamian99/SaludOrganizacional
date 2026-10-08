"""
Estudiantes · seudónimo del niño con clave (fase 5).

La carga de estudiantes solo añade `N_hmac` si quien llama pasa la clave
(`clave_nino`). Sin ella, la salida es exactamente la de antes: el pipeline,
la vista y la publicación de estudiantes no cambian.
"""
import pandas as pd

from src.core import seudonimo as seud
from src.estudiantes import ingest
from tests import cuidadores_sinteticos as cs
from tests import triangulacion_sinteticos as ts

K = cs.CLAVE_PRUEBA.encode()


def _formularios(tmp_path):
    ts.escribir(tmp_path)
    base = tmp_path / "estudiantes"
    return [str(base / ts.ARCHIVO_SEC), str(base / ts.ARCHIVO_PRI)]


def test_sin_clave_la_salida_no_cambia(tmp_path):
    sec, _ = ts.estudiantes()
    sin, inf_sin = ingest.cargar(sec)
    con, inf_con = ingest.cargar(sec, clave_nino=K)
    assert ingest.COLUMNA_NINO not in sin.columns
    assert [c for c in con.columns if c != ingest.COLUMNA_NINO] == list(sin.columns)
    pd.testing.assert_frame_equal(con.drop(columns=[ingest.COLUMNA_NINO]), sin)
    assert inf_sin.como_dict() == inf_con.como_dict()


def test_el_seudonimo_es_el_del_hijo_en_cuidadores():
    sec, _ = ts.estudiantes()
    con, _ = ingest.cargar(sec, clave_nino=K)
    esperado = seud.seudonimo(cs.nombre_nino(30, 1), "N", K)
    assert esperado in set(con[ingest.COLUMNA_NINO])
    assert con[ingest.COLUMNA_NINO].str.fullmatch(r"N[0-9a-f]{8}").all()


def test_sin_columna_de_nombre_el_seudonimo_queda_vacio():
    sec, _ = ts.estudiantes()
    con, _ = ingest.cargar(sec.drop(columns=["Mi nombre completo es:"]), clave_nino=K)
    assert con[ingest.COLUMNA_NINO].isna().all()


def test_cargar_varios_pasa_la_clave(tmp_path):
    rutas = _formularios(tmp_path)
    sin, _ = ingest.cargar_varios(rutas)
    con, _ = ingest.cargar_varios(rutas, clave_nino=K)
    assert ingest.COLUMNA_NINO not in sin.columns
    assert con[ingest.COLUMNA_NINO].notna().all()
    pd.testing.assert_frame_equal(con.drop(columns=[ingest.COLUMNA_NINO]), sin)


def test_el_pipeline_de_estudiantes_nunca_pide_la_clave(tmp_path):
    from src.estudiantes import pipeline
    resultados, _ = pipeline.cargar_y_analizar(_formularios(tmp_path), n_boot=10)
    for a in resultados.values():
        assert ingest.COLUMNA_NINO not in a.datos.columns
        assert not any(str(c).startswith("N_") for c in a.datos.columns)
