"""
Pruebas del menú: nombres, orden, qué páginas existen y cuáles ve cada modo.
"""
import os

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


def test_triangulacion_solo_para_investigadores():
    """Fase 5: completo e investigador la ven; comunidad nunca (spec §5.3 y §5.6)."""
    assert nav.PAGINA_TRIANGULACION in nav.DISPONIBLES
    assert nav.PAGINA_TRIANGULACION in nav.menu(COMPLETO)
    assert nav.PAGINA_TRIANGULACION in nav.menu(INVESTIGADOR)
    assert nav.PAGINA_TRIANGULACION not in nav.menu(COMUNIDAD)
    assert nav.PAGINA_TRIANGULACION not in nav.menu("cualquier-cosa")


def test_completo_e_investigador_ven_todas_las_disponibles_en_orden():
    esperado = ["Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360",
                "Chat con IA", "Cargar Datos", "Análisis de tendencias", "Reportes"]
    assert nav.menu(COMPLETO) == esperado
    assert nav.menu(INVESTIGADOR) == esperado


def test_comunidad_solo_ve_paginas_publicas():
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    assert set(nav.PUBLICAS) == {nav.PAGINA_ESTUDIANTES, nav.PAGINA_CUIDADORES}


def test_triangulacion_nunca_es_publica():
    assert nav.PAGINA_TRIANGULACION not in nav.PUBLICAS


def test_triangulacion_sigue_fuera_aunque_cuidadores_sea_publica(monkeypatch):
    _aprobar_cuidadores(monkeypatch)
    assert nav.PAGINA_TRIANGULACION not in nav.menu(COMUNIDAD)


def test_cuidadores_no_es_publica_hasta_la_aprobacion():
    """Existe para investigadores; el público no la ve hasta la aprobación (spec §5.5)."""
    assert nav.CUIDADORES_PUBLICO is False
    assert nav.cuidadores_publico() is False
    assert nav.PAGINA_CUIDADORES in nav.DISPONIBLES
    assert nav.PAGINA_CUIDADORES not in nav.menu(COMUNIDAD)
    assert nav.PAGINA_CUIDADORES not in nav.menu("cualquier-cosa")


def _aprobar_cuidadores(monkeypatch, bandera=True, textos=True, rutas=True):
    from src.cuidadores import comunidad_catalogo as cc
    monkeypatch.setattr(nav, "CUIDADORES_PUBLICO", bandera)
    monkeypatch.setattr(cc, "TEXTOS_APROBADOS", textos)
    monkeypatch.setattr(cc, "RUTAS_VALIDADAS", rutas)


def test_cuando_cuidadores_se_apruebe_comunidad_lo_ve(monkeypatch):
    """Fase 4b: la bandera del equipo Y los textos y la ruta aprobados en el catálogo."""
    monkeypatch.setattr(nav, "DISPONIBLES",
                        nav.DISPONIBLES | {nav.PAGINA_CUIDADORES, nav.PAGINA_TRIANGULACION})
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch, bandera=True, textos=False, rutas=False)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch, bandera=True, textos=True, rutas=False)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch, bandera=False, textos=True, rutas=True)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360"]
    _aprobar_cuidadores(monkeypatch)
    assert nav.menu(COMUNIDAD) == ["Estudiantes 360", "Cuidadores 360"]
    assert nav.menu(INVESTIGADOR)[:4] == [
        "Docentes", "Estudiantes 360", "Cuidadores 360", "Triangulación 360"]


def test_pagina_inicial_por_modo():
    assert nav.pagina_inicial(COMPLETO) == "Docentes"
    assert nav.pagina_inicial(INVESTIGADOR) == "Estudiantes 360"
    assert nav.pagina_inicial(COMUNIDAD) == "Estudiantes 360"


def test_un_modo_desconocido_se_trata_como_comunidad():
    assert nav.menu("cualquier-cosa") == nav.menu(COMUNIDAD)


PROHIBIDOS_EN_COMUNIDAD = (
    "src.ui.dashboard", "src.ui.chat", "src.ui.upload", "src.ui.reports",
    "src.ui.trends", "src.ai.gemini_client",
    "src.ui.views.estudiantes_investigador",
    "src.ui.cuidadores", "src.ui.views.cuidadores_investigador",
    "src.cuidadores.ingest", "src.cuidadores.pipeline", "src.cuidadores.scoring",
    "src.cuidadores.privacidad", "src.cuidadores.publicar", "src.cuidadores.auditoria",
    "src.cuidadores.comunidad", "src.core.seudonimo",
    "src.ui.triangulacion", "src.ui.views.triangulacion_investigador",
    "src.triangulacion.fuentes", "src.triangulacion.enlace", "src.triangulacion.diadas",
    "src.triangulacion.capa1", "src.triangulacion.pipeline",
    "src.core.vista_previa")


def _descargar(monkeypatch, modulo: str) -> None:
    """Quita el módulo de `sys.modules` y del paquete padre.

    Solo con `sys.modules` no basta: `from src.core import vista_previa` toma el
    atributo del paquete si ya existe, sin volver a registrarlo, y la prueba
    no vería la importación.
    """
    import sys
    monkeypatch.delitem(sys.modules, modulo, raising=False)
    padre, _, nombre = modulo.rpartition(".")
    if padre in sys.modules and hasattr(sys.modules[padre], nombre):
        monkeypatch.delattr(sys.modules[padre], nombre)


def _main_en_comunidad(monkeypatch):
    """Ejecuta main.py en modo comunidad con los módulos prohibidos descargados."""
    import sys
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    monkeypatch.setenv("OBS360_DATOS_DIR", "/ruta/que/no/existe")
    for m in PROHIBIDOS_EN_COMUNIDAD:
        _descargar(monkeypatch, m)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return AppTest.from_file(os.path.join(raiz, "main.py"), default_timeout=60)


def test_main_en_comunidad_no_importa_modulos_internos(monkeypatch):
    """Arranca main.py de verdad en modo comunidad.

    Puede leer la corrida publicada en Supabase si hay secretos configurados;
    solo garantiza que no lanza excepción y que no se importa ningún módulo
    interno.
    """
    import sys
    at = _main_en_comunidad(monkeypatch).run()
    assert not at.exception
    for m in PROHIBIDOS_EN_COMUNIDAD:
        assert m not in sys.modules, f"{m} se importó en modo comunidad"


def test_comunidad_con_dos_paginas_publicas_muestra_el_selector(monkeypatch):
    """Aprobada pero sin corrida publicada: la página lo dice y no se cae."""
    import sys
    from src.cuidadores import comunidad_catalogo as cc
    from src.cuidadores import lectura
    _aprobar_cuidadores(monkeypatch)
    monkeypatch.setattr(lectura, "disponible", lambda: False)
    at = _main_en_comunidad(monkeypatch).run()
    assert not at.exception
    radio = at.radio(key="nav_pagina")
    assert list(radio.options) == ["Estudiantes 360", "Cuidadores 360"]
    radio.set_value("Cuidadores 360").run()
    assert not at.exception
    assert any(cc.NO_PUBLICADO in i.value for i in at.info)
    for m in PROHIBIDOS_EN_COMUNIDAD:
        assert m not in sys.modules, f"{m} se importó en modo comunidad"


def test_comunidad_con_corrida_de_cuidadores_muestra_solo_la_vista_de_comunidad(monkeypatch):
    import sys
    from src.cuidadores import comunidad_catalogo as cc
    from src.cuidadores import lectura
    from tests import cuidadores_comunidad_datos as datos
    from src.ui.views import cuidadores_comunidad as vc
    _, base = datos.publicado()
    vc._corrida_vigente.clear()
    vc._leer_publicado.clear()
    _aprobar_cuidadores(monkeypatch)
    monkeypatch.setattr(lectura, "disponible", lambda: True)
    monkeypatch.setattr(lectura, "_cliente", lambda: base.cliente(anonimo=True))
    at = _main_en_comunidad(monkeypatch).run()
    at.radio(key="nav_pagina").set_value("Cuidadores 360").run()
    assert not at.exception
    assert at.radio(key="cuid_com_rol").value in cc.ROLES
    assert "src.ui.views.cuidadores_comunidad" in sys.modules
    for m in PROHIBIDOS_EN_COMUNIDAD:
        assert m not in sys.modules, f"{m} se importó en modo comunidad"


def test_no_queda_dashboard_visible_en_la_interfaz():
    """Lo que ve la persona dice «Docentes». Los comentarios técnicos no cuentan."""
    import pathlib
    import re
    raiz = pathlib.Path(__file__).resolve().parents[1]
    culpables = []
    for f in [raiz / "main.py", *(raiz / "src" / "ui").rglob("*.py"),
              raiz / "src" / "core" / "state.py"]:
        texto = f.read_text(encoding="utf-8")
        # cadenas entre comillas que contienen la palabra
        for m in re.finditer(r'"[^"\n]*Dashboard[^"\n]*"', texto):
            culpables.append(f"{f.relative_to(raiz)}: {m.group(0)}")
    assert not culpables, culpables


def test_main_en_investigador_ofrece_cuidadores(monkeypatch, tmp_path):
    """Sin archivos y sin corrida publicada, la página dice que no está publicada."""
    from streamlit.testing.v1 import AppTest
    from src.cuidadores import lectura
    monkeypatch.setattr(lectura, "disponible", lambda: False)
    monkeypatch.setenv("OBS360_MODO", "investigador")
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    at = AppTest.from_file(os.path.join(raiz, "main.py"), default_timeout=120).run()
    assert not at.exception
    radio = at.radio(key="nav_pagina")
    assert "Cuidadores 360" in radio.options
    radio.set_value("Cuidadores 360").run()
    assert not at.exception
    assert any("aún no está publicado" in i.value for i in at.info)


def test_main_en_investigador_ofrece_triangulacion(monkeypatch, tmp_path):
    """Sin archivos (como en el despliegue del equipo), la página lo dice y no falla."""
    from streamlit.testing.v1 import AppTest
    from src.triangulacion import catalogo as cat_tri
    monkeypatch.setenv("OBS360_MODO", "investigador")
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    at = AppTest.from_file(os.path.join(raiz, "main.py"), default_timeout=120).run()
    assert not at.exception
    radio = at.radio(key="nav_pagina")
    assert "Triangulación 360" in radio.options
    radio.set_value("Triangulación 360").run()
    assert not at.exception
    assert any(cat_tri.AVISO_DESPLIEGUE in i.value for i in at.info)
