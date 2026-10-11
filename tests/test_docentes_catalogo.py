"""
Catálogo de dimensiones docentes (propuesta del 10-oct-2026, §5.2).

Lo que fija: cada dimensión tiene ítems, escala teórica, dirección, agregación,
fuente y frase; los cortes publicados existen solo para PSS, BAT-12 e ISTAS21 y
los que hay que confirmar llevan la marca «comprobar en el manual»; las
subescalas que antes se sumaban con polaridad mezclada están separadas.
"""
import pytest

from src.docentes import catalogo as cat


def _dim(clave):
    return cat.por_clave(clave)


def test_claves_unicas_y_sin_totales_mezclados():
    claves = [d.clave for d in cat.DIMENSIONES]
    assert len(claves) == len(set(claves))
    # Los totales viejos con polaridad mezclada no existen como dimensión.
    for vieja in ("MT", "CR", "PRPS_CE"):
        assert vieja not in claves
    for nueva in ("MT_Control", "MT_Demandas", "CR_Claridad", "CR_Conflicto",
                  "ISTAS_Exig", "ISTAS_TA", "IR", "ERS_ACP"):
        assert nueva in claves


def test_subescalas_de_la_propuesta():
    assert _dim("MT_Control").items == ("MT1", "MT2", "MT3")
    assert _dim("MT_Demandas").items == ("MT4", "MT5", "MT6", "MT7")
    assert _dim("CR_Claridad").items == ("CR1", "CR2", "CR3", "CR4")
    assert _dim("CR_Conflicto").items == ("CR5", "CR6", "CR7")
    assert _dim("ISTAS_Exig").items == tuple(f"PRPS_CE{i}" for i in range(1, 7))
    assert _dim("ISTAS_TA").items == tuple(f"PRPS_CE{i}" for i in range(7, 17))
    assert "IRI_EC(13)" not in _dim("IRI_EC").items and len(_dim("IRI_EC").items) == 7
    assert _dim("BTA").desplazamiento == 1 and _dim("BTA").escala == (1, 5)


def test_direccion_y_escala_en_todas():
    for d in cat.DIMENSIONES:
        assert d.direccion in (cat.MAYOR_MEJOR, cat.MAYOR_PEOR, None), d.clave
        assert d.agregacion in ("media", "suma", "valor"), d.clave
        assert d.escala[0] < d.escala[1], d.clave
        assert d.items and len(set(d.items)) == len(d.items), d.clave
        assert d.fuente and d.frase, d.clave
    assert _dim("PSS").direccion == cat.MAYOR_PEOR
    assert _dim("MT_Demandas").direccion == cat.MAYOR_PEOR
    assert _dim("CR_Claridad").direccion == cat.MAYOR_MEJOR
    assert _dim("IR").direccion == cat.MAYOR_PEOR
    assert _dim("Descon").direccion == cat.MAYOR_MEJOR
    assert _dim("ERS_ACP").direccion == cat.MAYOR_PEOR
    assert _dim("PRPS_Fam").direccion is None


def test_cortes_solo_en_pss_bat_e_istas_y_marcados():
    con_cortes = {d.clave for d in cat.DIMENSIONES if d.cortes}
    assert con_cortes == {"PSS", "BTA", "ISTAS_Exig", "ISTAS_TA"}
    # Bandas continuas [inferior, superior): el superior de una es el inferior de la
    # siguiente y cubren la escala entera.
    for clave in con_cortes:
        d = _dim(clave)
        bandas = sorted(d.cortes, key=lambda b: b.inferior)
        assert bandas[0].inferior == d.escala[0] and bandas[-1].superior == d.escala[1]
        for a, b in zip(bandas, bandas[1:]):
            assert b.inferior == a.superior
        assert {b.zona for b in bandas} <= {cat.ZONA_FAVORABLE, cat.ZONA_INTERMEDIA, cat.ZONA_VIGILAR}
    assert _dim("PSS").cortes_tipo == "convencional" and not _dim("PSS").comprobar_en_manual
    assert _dim("BTA").comprobar_en_manual and _dim("ISTAS_Exig").comprobar_en_manual
    assert _dim("ISTAS_TA").comprobar_en_manual
    assert [b.inferior for b in _dim("PSS").cortes] == [0, 13.5, 26.5]
    assert [b.inferior for b in _dim("BTA").cortes] == [1, 2.59, 3.02]
    assert [b.inferior for b in _dim("ISTAS_Exig").cortes] == [0, 7.5, 10.5]
    assert [b.inferior for b in _dim("ISTAS_TA").cortes] == [0, 20.5, 25.5]


def test_aviso_de_version_y_solo_2025():
    for clave in ("Comp", "DefO", "Sat", "IR", "RO"):
        assert _dim(clave).aviso_version, clave
    assert not _dim("PSS").aviso_version
    assert _dim("BLG_Psicoso").solo_version == cat.VERSION_2025
    assert all(d.solo_version is None for d in cat.DIMENSIONES if d.clave != "BLG_Psicoso")


def test_temas_y_tablero():
    assert set(d.tema for d in cat.DIMENSIONES) <= set(cat.TEMAS)
    visibles = [d for d in cat.DIMENSIONES if d.en_tablero]
    assert all(d.tema != cat.TEMA_INVESTIGADOR for d in visibles)
    assert _dim("PRPS_Fam").tema == cat.TEMA_INVESTIGADOR and not _dim("PRPS_Fam").en_tablero
    assert _dim("ISTAS_Exig").tema == cat.TEMA_RECURSOS
    assert _dim("Conf_TrFa").tema == cat.TEMA_BIENESTAR


def test_recodificacion_de_la_codificacion_1():
    """Lo que hay que des-invertir (o invertir) en el archivo actual (§5.2)."""
    assert cat.RECODIFICAR_V1 == {
        "PRPS_CE2": 4, "PRPS_CE9": 4, "PRPS_CE10": 4, "PRPS_CE11": 4, "PRPS_CE12": 4,
        "PRPS_CE13": 4, "PRPS_CE14": 4, "PRPS_CE15": 4, "PRPS_CE16": 4,
        "ERS_ACP1": 3, "IR1": 5,
    }
    assert cat.COLUMNA_CODIFICACION == "Codificación de ítems"


def test_codigos_de_faltante():
    assert cat.HIJOS_CODIGO_FALTANTE == 10


def test_por_clave_desconocida():
    with pytest.raises(KeyError):
        cat.por_clave("no_existe")
