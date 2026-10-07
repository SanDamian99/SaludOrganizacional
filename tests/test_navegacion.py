"""
Pruebas del menú: nombres, orden, qué páginas existen y cuáles ve cada modo.
"""
from src.core import navegacion as nav
from src.core.modo import COMPLETO, COMUNIDAD, INVESTIGADOR


def test_nombres_de_las_paginas():
    assert nav.PAGINA_DOCENTES == "Docentes"
    assert nav.PAGINA_ESTUDIANTES == "Estudiantes 360"
    assert nav.PAGINA_CUIDADORES == "Cuidadores 360"
    assert nav.PAGINA_TRIANGULACION == "Triangulación 360"


def test_orden_del_menu_es_el_de_la_spec():
    assert nav.MENU == (
        "Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360",
        "Chat con IA", "Cargar Datos", "Análisis de tendencias", "Reportes")


def test_ya_no_existe_la_pagina_dashboard():
    assert "Dashboard" not in nav.MENU


def test_las_paginas_sin_construir_no_salen_en_el_menu():
    """Cuidadores y Triangulación llegan en las fases 4 y 5."""
    for m in (COMPLETO, INVESTIGADOR, COMUNIDAD):
        assert nav.PAGINA_CUIDADORES not in nav.menu(m)
        assert nav.PAGINA_TRIANGULACION not in nav.menu(m)


def test_completo_e_investigador_ven_todas_las_disponibles_en_orden():
    esperado = ["Docentes", "Estudiantes 360", "Chat con IA", "Cargar Datos",
                "Análisis de tendencias", "Reportes"]
    assert nav.menu(COMPLETO) == esperado
    assert nav.menu(INVESTIGADOR) == esperado


def test_comunidad_solo_ve_paginas_publicas():
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    assert set(nav.PUBLICAS) == {nav.PAGINA_ESTUDIANTES, nav.PAGINA_CUIDADORES}


def test_triangulacion_nunca_es_publica():
    assert nav.PAGINA_TRIANGULACION not in nav.PUBLICAS


def test_cuando_cuidadores_este_disponible_comunidad_lo_ve(monkeypatch):
    monkeypatch.setattr(nav, "DISPONIBLES",
                        nav.DISPONIBLES | {nav.PAGINA_CUIDADORES, nav.PAGINA_TRIANGULACION})
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360", "Cuidadores 360"]
    assert nav.menu(INVESTIGADOR)[:4] == [
        "Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360"]


def test_pagina_inicial_por_modo():
    assert nav.pagina_inicial(COMPLETO) == "Docentes"
    assert nav.pagina_inicial(INVESTIGADOR) == "Estudiantes 360"
    assert nav.pagina_inicial(COMUNIDAD) == "Estudiantes 360"


def test_un_modo_desconocido_se_trata_como_comunidad():
    assert nav.menu("cualquier-cosa") == nav.menu(COMUNIDAD)


def test_main_en_comunidad_no_importa_modulos_internos(monkeypatch):
    """Arranca main.py de verdad en modo comunidad, sin datos ni Supabase."""
    import sys
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    monkeypatch.setenv("OBS360_DATOS_DIR", "/ruta/que/no/existe")
    for m in ("src.ui.dashboard", "src.ui.chat", "src.ui.upload", "src.ui.reports",
              "src.ui.views.estudiantes_investigador"):
        sys.modules.pop(m, None)
    at = AppTest.from_file("main.py", default_timeout=60).run()
    assert not at.exception
    for m in ("src.ui.dashboard", "src.ui.chat", "src.ui.upload", "src.ui.reports",
              "src.ui.views.estudiantes_investigador"):
        assert m not in sys.modules, f"{m} se importó en modo comunidad"
