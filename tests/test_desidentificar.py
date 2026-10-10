"""
Copias desidentificadas de los formularios para el almacén.

Lo que se protege: que ningún nombre ni contacto salga hacia Storage, que las
columnas no se muevan (la ingesta lee por posición) y que procesar la copia dé
los mismos identificadores que procesar el original.
"""
import numpy as np
import pandas as pd
import pytest

from src.core import seudonimo as seud
from src.data import almacen, desidentificar
from tests.test_estudiantes_comunidad import _formulario, NOMBRE_SENTINELA

K = b"clave-de-prueba-larga-de-verdad-1234"


def test_un_seudonimo_pasa_tal_cual_y_un_nombre_no():
    p = seud.seudonimo("María Pérez", "N", K)
    assert seud.es_seudonimo(p) and not seud.es_seudonimo("María Pérez")
    assert seud.seudonimo(p, "N", K) == p
    assert seud.seudonimo("  " + p + " ", "C", K) == p     # la letra no lo recalcula


def test_estudiantes_quedan_sin_nombres_y_con_las_mismas_columnas():
    crudo = _formulario(20)
    copia, inf = desidentificar.desidentificar("estudiantes_secundaria", crudo, K)
    assert list(copia.columns) == list(crudo.columns)
    assert NOMBRE_SENTINELA not in copia.to_string()
    assert inf.nombres_reemplazados == 20
    assert copia["Mi nombre completo es:"].map(seud.es_seudonimo).all()
    # el resto de celdas no cambia
    otras = [c for c in crudo.columns if c != "Mi nombre completo es:"]
    pd.testing.assert_frame_equal(copia[otras], crudo[otras])


def test_la_copia_produce_los_mismos_identificadores_que_el_original():
    from src.estudiantes import ingest
    crudo = _formulario(20)
    copia, _ = desidentificar.desidentificar("estudiantes_secundaria", crudo, K)
    a, _ = ingest.cargar(crudo, clave_nino=K)
    b, _ = ingest.cargar(copia, clave_nino=K)
    assert list(a[ingest.COLUMNA_NINO]) == list(b[ingest.COLUMNA_NINO])
    assert len(a) == len(b) and a["ID"].nunique() == b["ID"].nunique()


def test_verificar_rechaza_nombres_y_contactos():
    crudo = _formulario(10)
    with pytest.raises(desidentificar.QuedanIdentificadores):
        desidentificar.verificar("estudiantes_secundaria", crudo)
    copia, _ = desidentificar.desidentificar("estudiantes_secundaria", crudo, K)
    copia["Correo electrónico"] = "x@y.z"
    with pytest.raises(desidentificar.QuedanIdentificadores):
        desidentificar.verificar("estudiantes_secundaria", copia)


def test_el_almacen_no_sube_un_conjunto_crudo_con_nombres():
    class Falso:
        pass
    a = almacen.Almacen(cliente=Falso())
    with pytest.raises(desidentificar.QuedanIdentificadores):
        a.subir_version("estudiantes_primaria", _formulario(10), "x.csv")


def test_conjunto_desconocido():
    with pytest.raises(ValueError):
        desidentificar.desidentificar("otro", _formulario(5), K)


def test_un_archivo_que_no_es_el_formulario_de_cuidadores_no_se_sube():
    with pytest.raises(desidentificar.QuedanIdentificadores):
        desidentificar.verificar("cuidadores", pd.DataFrame({"a": [1], "b": [2]}))
