"""Catálogo de líneas de atención: datos completos, filtros y rutas."""
import re

from src.core import lineas_atencion as la
from src.estudiantes import alertas_catalogo as ac


def test_claves_unicas_y_campos_validos():
    claves = [x.clave for x in la.todas()]
    assert len(claves) == len(set(claves))
    for x in la.todas():
        assert x.nombre and x.resumen and x.fuente and x.fecha
        assert x.municipio in la.MUNICIPIOS
        assert x.tipo in la.TIPOS
        assert x.nivel in la.NIVELES
        assert x.para and set(x.para) <= set(la.PARA)
        assert x.temas and set(x.temas) <= set(la.TEMAS)
        if x.en_directorio:
            assert x.telefono, x.clave
        if x.marcado:
            assert re.fullmatch(r"\d+", x.marcado), x.clave


def test_estan_las_lineas_clave_del_documento():
    for clave, telefono in (("l106", "106"), ("l123", "123"), ("l155", "155"),
                            ("icbf_141", "141"), ("chia_escucha", "601 884 4444"),
                            ("sopo_codigo_dorado", "318 820 6780"),
                            ("zipaquira_esperanza", "322 814 2684"),
                            ("tocancipa_linea", "322 846 7222")):
        assert la.por_clave(clave).telefono == telefono


def test_lo_que_el_documento_pide_confirmar_conserva_su_nota():
    for clave in ("chia_escucha", "zipaquira_escucha", "cota_escucha", "tenjo_proteccion",
                  "tabio_oferta", "chia_hospital_san_antonio", "chia_clinica_chia"):
        assert "onfirmar" in la.por_clave(clave).nota or "no " in la.por_clave(clave).nota.lower()
    assert "pago" in la.por_clave("bogota_montserrat").nota.lower()


def test_directorio_excluye_entradas_sin_telefono():
    claves = {x.clave for x in la.directorio()}
    assert "orientacion_escolar" not in claves and "comisaria_familia" not in claves
    assert "l106" in claves


def test_filtrar():
    chia = la.filtrar(municipio="chia")
    assert chia and all(x.municipio == "chia" for x in chia)
    menores = la.filtrar(tema="menores")
    assert la.por_clave("icbf_141") in menores
    assert all("estudiante" in x.para for x in la.filtrar(para="estudiante"))
    assert la.filtrar(municipio="chia", tema="victimas") == [la.por_clave("chia_papsivi")]


def test_ruta_estudiante_empieza_por_106_y_123():
    ruta = la.ruta("estudiante")
    assert [n for n, _ in ruta][:2] == ["Línea 106", "Línea 123"]
    assert any("Orientación escolar" in n for n, _ in ruta)
    assert all(isinstance(n, str) and isinstance(d, str) for n, d in ruta)


def test_ruta_por_niveles():
    por = la.ruta_niveles("estudiante")
    assert set(por) == set(la.NIVELES)
    assert [x.clave for x in por["ahora"]] == ["l106", "l123"]
    assert la.por_clave("icbf_141") in por["hoy"]
    adulto = la.ruta_niveles("adulto")
    assert la.por_clave("l155") in adulto["hoy"]


def test_los_textos_de_la_ruta_no_alarman():
    for tipo in ("estudiante", "adulto"):
        for nombre, detalle in la.ruta(tipo):
            assert "suicid" not in f"{nombre} {detalle}".lower()


def test_las_rutas_de_alertas_salen_del_catalogo():
    for rol in ac.ROLES:
        assert ac.ruta(rol, "estudiante") == la.ruta("estudiante")
        assert ac.ruta(rol, "adulto") == la.ruta("adulto")


def test_cada_alerta_tiene_lineas():
    for alerta in (*ac.ALERTAS, "animo", "autolesion"):
        lineas = la.para_senal(alerta)
        assert 1 <= len(lineas) <= 3, alerta
        assert lineas[0].clave == "l106"


def test_alerta_desconocida_devuelve_lo_urgente():
    assert [x.clave for x in la.para_senal("otra")][:2] == ["l106", "l123"]
