# tests/test_colegios.py
"""Tabla única de colegios: misma salida que antes salvo correcciones documentadas."""
import json
import os

import pytest

from src.core import colegios

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "colegios_estudiantes_2026-09-18.json")
CONOCIDOS = {"LauV", "JJC", "LaBalsa", "SJMEB", "CdP", "DiosCh", "Bojacá", "Fagua",
             "Fonquetá", "Fusca", "Tiquiza", "CND", "SMR"}


def test_no_regresion_con_los_formularios_del_18_sep():
    if not os.path.exists(FIXTURE):
        pytest.skip("falta el fixture")
    antes = json.load(open(FIXTURE, encoding="utf-8"))
    for texto, (cod_antes, _, sede_antes) in antes.items():
        cod, _, sede = colegios.normalizar(texto)
        # un código conocido nunca cambia a otro código conocido; un «OTRO» puede
        # pasar a reconocerse (es una corrección)
        if cod_antes in CONOCIDOS:
            assert cod == cod_antes, f"«{texto}»: {cod_antes} → {cod}"
        assert sede == sede_antes or sede_antes == ""


@pytest.mark.parametrize("texto,codigo", [
    ("I.E.O Laura Vicuña", "LauV"),
    ("San José María Escrivá", "SJMEB"),
    ("Colegio San José María sede Samaria", "SJMEB"),
    ("Conaldi", "CND"),
    ("Conadi ", "CND"),
    ("Institución educativa diversificado Conaldi", "CND"),
    ("Jj casas", "JJC"),
    ("Balaguer ", "SJMEB"),
    ("Santa María del rio", "SMR"),
    ("IE Bojacá - IE José Joaquín Casas", "Bojacá"),
    ("Cerca de Piedra", "CdP"),
])
def test_variantes_de_texto_libre(texto, codigo):
    assert colegios.normalizar(texto)[0] == codigo


def test_sedes_como_detalle():
    assert colegios.normalizar("Diversificado sede Santa Lucía") == (
        "CND", "Colegio Nacional Diversificado", "Santa Lucía")
    assert colegios.normalizar("Josemaría Escrivá - sede Samaria")[2] == "Samaria"


def test_vacio_y_desconocido():
    assert colegios.normalizar(None) == ("SIN_DATO", "Sin dato", "")
    assert colegios.normalizar("Colegio Inventado")[0] == "OTRO"


@pytest.mark.parametrize("nombre_docentes,codigo", [
    ("José Joaquín Casas", "JJC"),
    ("Diversificado · sede Santa Lucía", "CND"),
    ("Diversificado · sede Campincito", "CND"),
    ("Colegio Nacional Diversificado", "CND"),
    ("Fusca · sede El Cerro", "Fusca"),
    ("San Josemaría Escrivá de Balaguer", "SJMEB"),
    ("Santa María del Río", "SMR"),
])
def test_codigo_desde_nombre_de_docentes(nombre_docentes, codigo):
    assert colegios.codigo_desde_nombre(nombre_docentes) == codigo


def test_nombre_legible():
    assert colegios.nombre("JJC") == "José Joaquín Casas"
    assert colegios.nombre("XYZ") == "XYZ"
