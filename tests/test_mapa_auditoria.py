"""La auditoría rechaza lo que el mapa nunca debe dibujar."""
import pytest

from src.geo import mapa_datos as md
from src.geo.auditoria_mapa import AuditoriaMapa, auditar

VISIBLES = ["LauV", "JJC"]
PEQUENOS = ["LaBalsa"]


def _f(codigo="LauV", estado=md.CON_CIFRA, **kw):
    return md.FilaMapa(codigo, codigo, estado, **kw)


def test_tabla_correcta_pasa():
    filas = [_f("LauV", tramo="100 o más"), _f("JJC", tramo="30 a 99"),
             _f("LaBalsa", md.PEQUENA), _f("Bojacá", md.SIN_FORMULARIO)]
    auditar(filas, "respuestas", VISIBLES, PEQUENOS)


@pytest.mark.parametrize("capa", ["sdq_total", "rcads", "alertas", "muerte", ""])
def test_capa_de_malestar_se_rechaza(capa):
    with pytest.raises(AuditoriaMapa):
        auditar([], capa, VISIBLES, PEQUENOS)


def test_cifra_de_un_colegio_pequeno_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LaBalsa", md.PEQUENA, valor=3.2)], "sentirse_parte",
                VISIBLES, PEQUENOS)


def test_colegio_pequeno_con_estado_con_cifra_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LaBalsa", md.CON_CIFRA, tramo="10 a 29")], "respuestas",
                VISIBLES, PEQUENOS)


def test_cifra_de_un_colegio_no_visible_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("Fusca", md.CON_CIFRA, tramo="10 a 29")], "respuestas",
                VISIBLES, PEQUENOS)


def test_sin_formulario_con_valor_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("Bojacá", md.SIN_FORMULARIO, tramo="10 a 29")], "respuestas",
                VISIBLES, PEQUENOS)


def test_capa_de_respuestas_no_lleva_valor():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LauV", valor=3.0)], "respuestas", VISIBLES, PEQUENOS)


def test_codigo_que_no_es_un_colegio_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("Samaria", md.SIN_FORMULARIO)], "respuestas", VISIBLES, PEQUENOS)


def test_codigo_repetido_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LauV", tramo="100 o más"), _f("LauV", tramo="100 o más")],
                "respuestas", VISIBLES, PEQUENOS)


def test_estado_desconocido_se_rechaza():
    with pytest.raises(AuditoriaMapa):
        auditar([_f("LauV", "raro")], "respuestas", VISIBLES, PEQUENOS)
