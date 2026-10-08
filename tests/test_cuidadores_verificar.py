"""
`cuidadores.publicar.verificar` rechaza identificadores y datos de contacto en
cualquier parte de la fila: nombres de columna del formulario de cuidadores y
valores con forma de identificador seudónimo o de teléfono celular, también
dentro de `detalle`.
"""
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import publicar


def _fila(**detalle):
    return publicar._fila(cat.MARCO_CUIDADOR, "descriptivo", "PSS_Total", 30, 15.0, **detalle)


def test_una_fila_limpia_pasa():
    publicar.verificar([_fila(nota="Relativo a esta muestra")])


@pytest.mark.parametrize("columna", ["id_nino", "telefono", "ola", "n_hmac", "familia",
                                     "ID_nino", "Telefono"])
def test_columnas_prohibidas_en_detalle(columna):
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila(**{columna: "x"})])


def test_columna_prohibida_anidada():
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila(muestra={"por_familia": {"telefono": 1}})])


@pytest.mark.parametrize("valor", ["C1a2b3c4d", "N0123abcd", "E89abcdef",
                                   "LauV|N0123abcd", "grupo de C1a2b3c4d"])
def test_identificadores_en_cualquier_texto(valor):
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila(nota=valor)])


def test_identificador_en_una_lista_del_detalle():
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila(avisos=["revisar N0123abcd"])])


@pytest.mark.parametrize("valor", ["3001234567", "tel 3159876543", 3001234567])
def test_telefonos(valor):
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([_fila(nota=valor)])


@pytest.mark.parametrize("valor", ["2026-10-08-f4bb19193777", "SDQ_Emo", "Colegio×Grado",
                                   0.3123456789, 33.3333333333, "30012345678901"])
def test_lo_que_no_es_identificador_ni_telefono_pasa(valor):
    publicar.verificar([_fila(nota=valor)])


def test_el_lote_sintetico_pasa():
    from tests import cuidadores_comunidad_datos as datos
    publicar.verificar(publicar.aplanar(datos.preparado()))
