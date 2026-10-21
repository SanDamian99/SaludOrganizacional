"""Glosario de escalas de las vistas de investigador: cubre lo que las tablas listan."""
import pytest

from src.cuidadores import catalog as cat_cuid
from src.estudiantes import catalog as cat_est
from src.triangulacion import catalogo as cat_tri
from src.ui import ayuda_escalas as ae
from src.ui import ayuda_indicador as ay

UN_ITEM = {("estudiantes", "SIN_ADULTO"), ("cuidadores", "APQ_Grito")}

TODAS = ([("estudiantes", k) for k in ae.ESTUDIANTES] + [("cuidadores", k) for k in ae.CUIDADORES])


def test_las_tablas_de_estudiantes_tienen_glosario():
    esperadas = {*cat_est.ORDEN_TABLA1, *cat_est.COMPUESTAS, "SIN_ADULTO", "ALERTA_malestar"}
    assert esperadas <= set(ae.ESTUDIANTES)


def test_las_tablas_de_cuidadores_tienen_glosario():
    esperadas = {*cat_cuid.CLAVES_CUIDADOR, *cat_cuid.CLAVES_NINO, "APQ_Fisico", "APQ_Grito"}
    assert esperadas <= set(ae.CUIDADORES)


def test_todo_constructo_de_la_triangulacion_tiene_glosario():
    assert {c.clave for c in cat_tri.CONSTRUCTOS} == set(ae.CONSTRUCTO_AYUDA)
    texto = ae.glosario_constructos(cat_tri.CONSTRUCTOS)
    for c in cat_tri.CONSTRUCTOS:
        assert f"**{c.etiqueta}**" in texto, c.clave


@pytest.mark.parametrize("poblacion,clave", TODAS)
def test_cada_escala_trae_items_y_tres_lineas(poblacion, clave):
    nombre, a = ae.ESCALAS[poblacion][clave]
    assert nombre.strip()
    assert len(a.items) >= (1 if (poblacion, clave) in UN_ITEM else 2)
    lineas = ae.texto_escala(poblacion, clave).split("  \n")
    assert len(lineas) == 4                                  # nombre + las tres líneas
    assert lineas[2].startswith("*Puntaje alto:*") and lineas[3].startswith("*Puntaje bajo:*")


def test_los_items_citados_son_del_formulario_y_no_llevan_errata_conocida():
    texto = ae.glosario("estudiantes") + ae.glosario("cuidadores")
    for errata in ("instutución", "trsite", "de que algo malo"):
        assert errata not in texto


def test_escala_desconocida_no_dibuja_nada():
    assert ae.texto_escala("estudiantes", "NO_EXISTE") is None
    assert ae.glosario("otra") == ""
    assert ay.ayuda("docentes", "PSS") is not None
