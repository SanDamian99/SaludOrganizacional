"""La ayuda bajo cada selector: cubre todos los indicadores y cabe en tres líneas."""
import pytest

from src.docentes import catalogo as cat_doc
from src.ui import ayuda_indicador as ay
from src.ui.views import cuidadores_comunidad as cuid
from src.ui.views import estudiantes_comunidad as est

# Indicadores de un solo ítem: no hay un segundo enunciado que citar.
UN_ITEM = {("estudiantes", "adulto_confianza"), ("estudiantes", "ideacion"),
           ("cuidadores", "grito"), ("docentes", "PRPS_Fam")}

TODAS = ([("docentes", d.clave) for d in cat_doc.DIMENSIONES]
         + [("estudiantes", k) for k in est.INDICADORES]
         + [("cuidadores", k) for k in cuid.INDICADORES])


@pytest.mark.parametrize("poblacion,clave", TODAS)
def test_cada_indicador_tiene_ayuda_de_tres_lineas(poblacion, clave):
    a = ay.ayuda(poblacion, clave)
    assert a is not None, f"{poblacion}/{clave} sin descripción"
    minimo = 1 if (poblacion, clave) in UN_ITEM else 2
    assert len(a.items) >= minimo
    assert all(i.strip() for i in a.items)
    lineas = ay.texto(poblacion, clave).split("  \n")
    assert len(lineas) == 3
    assert lineas[1].startswith("**Puntaje alto:**")
    assert lineas[2].startswith("**Puntaje bajo:**")


def test_indicador_desconocido_no_dibuja_nada():
    assert ay.texto("docentes", "no_existe") is None
    assert ay.texto("otra", "PSS") is None


def test_no_hay_ayudas_huerfanas():
    claves = {d.clave for d in cat_doc.DIMENSIONES}
    assert set(ay.DOCENTES) == claves
    assert set(ay.ESTUDIANTES) == set(est.INDICADORES)
    assert set(ay.CUIDADORES) == set(cuid.INDICADORES)
