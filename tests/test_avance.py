"""Avance de datos: qué celdas colegio × grado ya se ven y cuáles faltan."""
import inspect

import pytest

from src.estudiantes import avance as av
from src.ui.views import estudiantes_investigador as vi
from tests.mapa_datos_sinteticos import analisis_sintetico


def _a(colegio_grado: dict):
    a = analisis_sintetico()
    a.muestra = dict(a.muestra, colegio_grado=colegio_grado)
    return a


def _estado(celdas, colegio, grado):
    return next(c for c in celdas if c.colegio == colegio and c.grado == grado)


def test_celda_con_diez_o_mas_es_visible():
    c = _estado(av.celdas(_a({"LauV|Sexto": 40}), "secundaria"), "LauV", "Sexto")
    assert c.estado == av.VISIBLE and c.n_texto == "40"


def test_celda_con_pocas_respuestas_falta_n_y_no_dice_el_numero():
    c = _estado(av.celdas(_a({"LauV|Séptimo": 5}), "secundaria"), "LauV", "Séptimo")
    assert c.estado == av.FALTA_N and "5" not in c.n_texto and "<10" in c.n_texto


def test_celda_enmascarada_en_la_corrida_publicada_falta_n():
    c = _estado(av.celdas(_a({"JJC|Octavo": "<10"}), "secundaria"), "JJC", "Octavo")
    assert c.estado == av.FALTA_N


def test_celda_esperada_sin_respuestas_esta_pendiente():
    celdas = av.celdas(_a({"LauV|Sexto": 40}), "secundaria")
    assert _estado(celdas, "CdP", "Sexto").estado == av.PENDIENTE
    assert _estado(celdas, "JJC", "Décimo").estado == av.PENDIENTE
    assert _estado(celdas, "SJMEB", "Sexto").estado == av.PENDIENTE


def test_celda_pendiente_que_ya_llego_se_ve():
    celdas = av.celdas(_a({"CdP|Sexto": 25}), "secundaria")
    assert _estado(celdas, "CdP", "Sexto").estado == av.VISIBLE


def test_celda_no_esperada_y_sin_respuestas_queda_sin_respuestas():
    c = _estado(av.celdas(_a({"LauV|Sexto": 40}), "secundaria"), "LauV", "Décimo")
    assert c.estado == av.SIN_RESPUESTAS


def test_los_grados_siguen_el_orden_del_nivel():
    celdas = av.celdas(_a({"LauV|Sexto": 40}), "secundaria")
    vistos = [c.grado for c in celdas if c.colegio == "LauV"]
    assert vistos == ["Sexto", "Séptimo", "Octavo", "Noveno", "Décimo"]


def test_primaria_usa_sus_grados_y_no_los_pendientes_de_secundaria():
    celdas = av.celdas(_a({"LauV|Cuarto": 50}), "primaria")
    assert {c.grado for c in celdas} == {"Cuarto", "Quinto"}
    assert all(c.estado != av.PENDIENTE for c in celdas)


def test_sin_conteos_por_celda_no_falla():
    a = analisis_sintetico()
    a.muestra = {}
    assert all(c.estado in (av.PENDIENTE, av.SIN_RESPUESTAS)
               for c in av.celdas(a, "secundaria"))


def test_la_matriz_muestra_texto_por_estado():
    m = av.matriz(_a({"LauV|Sexto": 40, "LauV|Séptimo": 5}), "secundaria")
    assert m.loc["Laura Vicuña", "Sexto"].endswith("40")
    assert "falta n" in m.loc["Laura Vicuña", "Séptimo"]
    assert "pendiente" in m.loc["Cerca de Piedra", "Sexto"]
    assert m.loc["Laura Vicuña", "Décimo"] == "—"


def test_resumen_cuenta_cada_estado():
    r = av.resumen(av.celdas(_a({"LauV|Sexto": 40, "LauV|Séptimo": 5}), "secundaria"))
    assert r[av.VISIBLE] == 1 and r[av.FALTA_N] == 1 and r[av.PENDIENTE] == 4


def test_formatear_corridas_no_expone_notas_largas_y_marca_la_estado():
    filas = [dict(id=9, modulo="cuidadores", publicada=False, n_secundaria=None,
                  n_primaria=None, creada_en="2026-10-10T12:23:57+00:00", notas="x" * 500),
             dict(id=7, modulo="estudiantes", publicada=True, n_secundaria=943,
                  n_primaria=352, creada_en="2026-10-08T23:28:30+00:00", notas="")]
    out = av.formatear_corridas(filas)
    assert [r["Corrida"] for r in out] == [9, 7]
    assert out[0]["Estado"] == "en revisión" and out[1]["Estado"] == "publicada"
    assert out[0]["Fecha"] == "2026-10-10" and out[1]["Secundaria"] == 943
    assert all(len(str(v)) < 120 for r in out for v in r.values())


def test_el_texto_de_pendientes_solo_lista_lo_que_sigue_sin_llegar():
    lista = av.celdas(_a({"SJMEB|Sexto": 34}), "secundaria")
    texto = av.texto_pendientes(lista)
    assert "Cerca de Piedra: Sexto, Séptimo" in texto
    assert "José Joaquín Casas: Décimo" in texto
    assert "San Josemaría" not in texto            # esa celda ya llegó


def test_sin_pendientes_el_texto_queda_vacio():
    lista = av.celdas(_a({"CdP|Sexto": 20, "CdP|Séptimo": 20, "JJC|Décimo": 20,
                          "SJMEB|Sexto": 20}), "secundaria")
    assert av.texto_pendientes(lista) == ""


def _base_con_corridas():
    from tests.supabase_falso import BaseFalsa
    base = BaseFalsa()
    for i, (modulo, publicada) in enumerate([("estudiantes", True), ("estudiantes", False),
                                             ("cuidadores", False)], start=1):
        base.tablas["corridas"].append(dict(
            id=base.siguiente(), creada_en=f"2026-10-0{i}T10:00:00+00:00", modulo=modulo,
            publicada=publicada, n_secundaria=943 if modulo == "estudiantes" else None,
            n_primaria=352 if modulo == "estudiantes" else None, notas="n" * 300))
    return base


def test_el_cargador_ve_todas_las_corridas_de_la_mas_nueva_a_la_mas_vieja():
    base = _base_con_corridas()
    filas = av.formatear_corridas(av.leer_corridas(base.cliente(cargador=True)))
    assert [f["Corrida"] for f in filas] == [3, 2, 1]
    assert [f["Estado"] for f in filas] == ["en revisión", "en revisión", "publicada"]


def test_el_publico_solo_ve_la_corrida_publicada():
    base = _base_con_corridas()
    filas = av.leer_corridas(base.cliente(anonimo=True))
    assert [f["id"] for f in filas] == [1]


def test_el_limite_de_corridas_se_respeta():
    base = _base_con_corridas()
    assert len(av.leer_corridas(base.cliente(cargador=True), limite=2)) == 2


def test_la_pestana_muestra_engancha_el_avance_y_no_se_rompe_si_falla():
    fuente = inspect.getsource(vi._tab_muestra)
    assert "render_avance" in fuente
    assert "except" in fuente[fuente.index("render_avance"):][:400]
