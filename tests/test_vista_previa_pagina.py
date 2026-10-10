"""Vista previa del equipo en las páginas de Estudiantes y Cuidadores (sin red).

Una base falsa con, por módulo, una corrida publicada SIN filas de alertas
(`--publicar-ya` con textos sin aprobar) y una oculta más nueva CON ellas (sin
`--publicar-ya`). Así el panel de señales solo aparece si de verdad se está
leyendo la corrida en revisión.
"""
import logging
import sys
import types

import pytest

from src.core import vista_previa as vp
from src.cuidadores import comunidad_catalogo as cc
from src.cuidadores import lectura as lec_cuid
from src.estudiantes import alertas_catalogo as ac_est
from src.estudiantes import lectura as lec_est
from tests import cuidadores_comunidad_datos as datos
from tests.supabase_falso import CREDENCIALES_CARGADOR, BaseFalsa

EMAIL, CLAVE = CREDENCIALES_CARGADOR["email"], CREDENCIALES_CARGADOR["password"]
ANON = "clave-anon-falsa-para-pruebas"
SECRETOS = (EMAIL, CLAVE, ANON)


@pytest.fixture(scope="module")
def analisis_est():
    from src.estudiantes import catalog as cat
    from src.estudiantes import ingest, pipeline, scoring
    from tests.test_estudiantes_comunidad import _formulario
    bruto, _ = ingest.cargar(_formulario())
    return {cat.NIVEL_SECUNDARIA: pipeline.analizar(scoring.puntuar(bruto),
                                                    cat.NIVEL_SECUNDARIA, n_boot=20)}


@pytest.fixture
def base(analisis_est):
    """Base con estudiantes y cuidadores: publicada sin señales + oculta con señales."""
    from src.cuidadores import publicar as pub_cuid
    from src.estudiantes import publicar as pub_est
    b = BaseFalsa()
    ids = {}
    for modulo, pub, objeto in (("estudiantes", pub_est, analisis_est),
                                ("cuidadores", pub_cuid, datos.preparado())):
        publicada = pub.publicar(objeto, publicar_ya=True, cliente=b.cliente())
        oculta = pub.publicar(objeto, publicar_ya=False, cliente=b.cliente())
        assert publicada["alertas_omitidas"] > 0 and oculta["alertas_omitidas"] == 0
        ids[modulo] = (publicada["corrida_id"], oculta["corrida_id"])
    b.ids = ids
    return b


def _entorno(monkeypatch, tmp_path, b, modo="investigador", clave=CLAVE):
    """Despliegue sin archivos, con la clave anon y las credenciales de carga."""
    from src.ui import cuidadores as ui_cuid
    from src.ui import estudiantes as ui_est
    from src.ui.views import cuidadores_comunidad as vc
    monkeypatch.setenv("OBS360_MODO", modo)
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    monkeypatch.setenv("OBS360_SUPABASE_URL", "https://falso.invalid")
    monkeypatch.setenv("OBS360_SUPABASE_KEY", ANON)
    monkeypatch.delenv("OBS360_FUENTE", raising=False)
    monkeypatch.setattr(vp, "credenciales", lambda: (EMAIL, clave))
    monkeypatch.setattr(vp, "_crear_cliente", lambda url, key: b.cliente_sin_sesion())
    monkeypatch.setattr(lec_est, "_cliente", lambda: b.cliente(anonimo=True))
    monkeypatch.setattr(lec_cuid, "_cliente", lambda: b.cliente(anonimo=True))
    for cache in (ui_est._corrida_vigente, ui_est._leer_publicado, ui_est._leer_revision,
                  ui_cuid._leer_revision, vc._corrida_vigente, vc._leer_publicado):
        cache.clear()


def _app(codigo: str):
    from streamlit.testing.v1 import AppTest
    return AppTest.from_string(codigo, default_timeout=180)


CUIDADORES = "from src.ui.cuidadores import render_cuidadores\nrender_cuidadores()\n"
ESTUDIANTES = "from src.ui.estudiantes import render_estudiantes\nrender_estudiantes()\n"


def _texto(at) -> str:
    partes = []
    for grupo in (at.markdown, at.caption, at.info, at.warning, at.error, at.success,
                  at.title, at.subheader):
        partes += [str(getattr(e, "value", "")) for e in grupo]
    partes += [str(getattr(t, "label", "")) for t in at.toggle]
    partes += [str(getattr(e, "value", "")) for e in at.sidebar.markdown]
    partes += [str(getattr(e, "value", "")) for e in at.sidebar.caption]
    return " ".join(partes)


def _banner(b, modulo) -> str:
    return f"Lo público sigue mostrando la corrida {b.ids[modulo][0]}."


# ══ Cuidadores ═════════════════════════════════════════════════════════════
def test_cuidadores_vista_previa_encendida_por_defecto(monkeypatch, tmp_path, base):
    _entorno(monkeypatch, tmp_path, base)
    at = _app(CUIDADORES).run()
    assert not at.exception
    oculta = base.ids["cuidadores"][1]
    toggle = at.toggle(key="vista_previa_cuidadores")
    assert toggle.label == f"Vista previa: corrida en revisión ({oculta})" and toggle.value
    texto = _texto(at)
    assert "Vista previa para el equipo: esta corrida no está publicada" in texto
    assert _banner(base, "cuidadores") in texto
    assert not any(lec_cuid.AVISO_PUBLICADO in i.value for i in at.info)
    # la vista de comunidad sale de la corrida oculta, con su panel y los avisos internos
    at.radio(key="cuid_audiencia").set_value("comunidad").run()
    assert not at.exception
    texto = _texto(at)
    assert cc.TITULO_PANEL in texto
    assert cc.TEXTOS_PENDIENTES in texto and ac_est.RUTA_PENDIENTE in texto
    assert cc.TEXTOS_APROBADOS is False and cc.RUTAS_VALIDADAS is False


def test_cuidadores_vista_previa_apagada_muestra_lo_publicado(monkeypatch, tmp_path, base):
    _entorno(monkeypatch, tmp_path, base)
    at = _app(CUIDADORES).run()
    at.radio(key="cuid_audiencia").set_value("comunidad").run()
    at.toggle(key="vista_previa_cuidadores").set_value(False).run()
    assert not at.exception
    texto = _texto(at)
    assert "Vista previa para el equipo" not in texto
    assert any(lec_cuid.AVISO_PUBLICADO in i.value for i in at.info)
    assert cc.TITULO_PANEL not in texto                # la publicada no trae señales
    assert cc.TEXTOS_PENDIENTES not in texto           # aviso interno solo en revisión
    # la preferencia se mantiene en la sesión
    at.run()
    assert at.toggle(key="vista_previa_cuidadores").value is False


def test_en_completo_la_vista_previa_empieza_apagada(monkeypatch, tmp_path, base):
    _entorno(monkeypatch, tmp_path, base, modo="completo")
    at = _app(CUIDADORES).run()
    assert not at.exception
    assert at.toggle(key="vista_previa_cuidadores").value is False
    assert "Vista previa para el equipo" not in _texto(at)


def test_sin_corrida_oculta_no_hay_interruptor(monkeypatch, tmp_path):
    _, b = datos.publicado()
    b.ids = {}
    _entorno(monkeypatch, tmp_path, b)
    at = _app(CUIDADORES).run()
    assert not at.exception
    assert not at.toggle
    assert any(lec_cuid.AVISO_PUBLICADO in i.value for i in at.info)


def test_un_inicio_de_sesion_fallido_cae_en_lo_publicado_sin_secretos(monkeypatch, tmp_path,
                                                                      base, caplog):
    _entorno(monkeypatch, tmp_path, base, clave="clave-equivocada-XYZ")
    with caplog.at_level(logging.DEBUG):
        at = _app(CUIDADORES).run()
    assert not at.exception and not at.toggle
    assert any(lec_cuid.AVISO_PUBLICADO in i.value for i in at.info)
    for secreto in (*SECRETOS, "clave-equivocada-XYZ"):
        assert secreto not in _texto(at) and secreto not in caplog.text


def test_ningun_secreto_en_pantalla_ni_en_los_registros(monkeypatch, tmp_path, base, caplog):
    _entorno(monkeypatch, tmp_path, base)
    with caplog.at_level(logging.DEBUG):
        at = _app(CUIDADORES).run()
        at.radio(key="cuid_audiencia").set_value("comunidad").run()
    assert not at.exception
    for secreto in SECRETOS:
        assert secreto not in _texto(at) and secreto not in caplog.text


# ══ Estudiantes ════════════════════════════════════════════════════════════
def test_estudiantes_vista_previa_con_alertas(monkeypatch, tmp_path, base):
    _entorno(monkeypatch, tmp_path, base)
    at = _app(ESTUDIANTES).run()
    assert not at.exception
    oculta = base.ids["estudiantes"][1]
    toggle = at.toggle(key="vista_previa_estudiantes")
    assert toggle.label == f"Vista previa: corrida en revisión ({oculta})" and toggle.value
    texto = _texto(at)
    assert _banner(base, "estudiantes") in texto
    assert f"Fuente: corrida en revisión ({oculta})" in texto
    at.radio(key="estudiantes_audiencia").set_value("comunidad").run()
    assert not at.exception
    texto = _texto(at)
    assert ac_est.TITULO_PANEL in texto and ac_est.RUTA_PENDIENTE in texto
    for secreto in SECRETOS:
        assert secreto not in texto


def test_estudiantes_vista_previa_apagada(monkeypatch, tmp_path, base):
    _entorno(monkeypatch, tmp_path, base)
    at = _app(ESTUDIANTES).run()
    at.radio(key="estudiantes_audiencia").set_value("comunidad").run()
    at.toggle(key="vista_previa_estudiantes").set_value(False).run()
    assert not at.exception
    texto = _texto(at)
    assert "Vista previa para el equipo" not in texto
    assert "Fuente: corrida publicada" in texto
    assert ac_est.TITULO_PANEL not in texto and ac_est.RUTA_PENDIENTE not in texto


# ══ Comunidad: la vista previa no existe ═══════════════════════════════════
def _sin_modulo(monkeypatch):
    import src.core
    monkeypatch.delitem(sys.modules, "src.core.vista_previa", raising=False)
    if hasattr(src.core, "vista_previa"):
        monkeypatch.delattr(src.core, "vista_previa")


@pytest.mark.parametrize("codigo", [
    ESTUDIANTES,
    "from src.ui.views.cuidadores_comunidad import render_publico\nrender_publico()\n"])
def test_en_comunidad_nunca_hay_vista_previa(monkeypatch, tmp_path, base, codigo):
    _entorno(monkeypatch, tmp_path, base, modo="comunidad")
    _sin_modulo(monkeypatch)
    at = _app(codigo).run()
    assert not at.exception
    assert not at.toggle
    assert "Vista previa" not in _texto(at)
    assert "src.core.vista_previa" not in sys.modules
    assert base.inicios_de_sesion == 0


# ══ Módulos rancios: nunca tumban la página ════════════════════════════════
def test_un_vista_previa_rancio_no_tumba_las_paginas(monkeypatch, tmp_path, base):
    import src.core
    _entorno(monkeypatch, tmp_path, base)
    rancio = types.ModuleType("src.core.vista_previa")     # sin ninguna función
    monkeypatch.setitem(sys.modules, "src.core.vista_previa", rancio)
    monkeypatch.setattr(src.core, "vista_previa", rancio, raising=False)
    for codigo in (CUIDADORES, ESTUDIANTES):
        at = _app(codigo).run()
        assert not at.exception
        assert not at.toggle and "Vista previa para el equipo" not in _texto(at)


def test_un_lector_rancio_cae_en_lo_publicado(monkeypatch, tmp_path, base):
    _entorno(monkeypatch, tmp_path, base)
    original_c, original_e = lec_cuid.cargar_desde_supabase, lec_est.cargar_desde_supabase
    # firma de antes: sin `corrida_id`
    monkeypatch.setattr(lec_cuid, "cargar_desde_supabase", lambda cli=None: original_c(cli))
    monkeypatch.setattr(lec_est, "cargar_desde_supabase", lambda: original_e())
    at = _app(CUIDADORES).run()
    assert not at.exception
    assert "Vista previa para el equipo" not in _texto(at)
    assert any(lec_cuid.AVISO_PUBLICADO in i.value for i in at.info)
    at = _app(ESTUDIANTES).run()
    assert not at.exception
    texto = _texto(at)
    assert "Vista previa para el equipo" not in texto and "Fuente: corrida publicada" in texto
