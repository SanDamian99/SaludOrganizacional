"""Triangulación 360 · página (fase 5): sin archivos, sin clave, módulo viejo y sintéticos."""

from src.triangulacion import catalogo as cat
from src.ui.views import triangulacion_investigador as vi
from tests import triangulacion_sinteticos as ts


def _pagina(monkeypatch, datos: str, clave: str | None):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    if clave:
        monkeypatch.setenv("OBS360_CLAVE_HMAC", clave)
    else:
        monkeypatch.delenv("OBS360_CLAVE_HMAC", raising=False)
        monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    return AppTest.from_string(
        "from src.ui.triangulacion import render_triangulacion\nrender_triangulacion()\n",
        default_timeout=180)


def test_sin_archivos_da_el_mensaje_del_despliegue(monkeypatch, tmp_path):
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any(cat.AVISO_DESPLIEGUE in i.value for i in at.info)
    assert any("Cuidadores: no" in c.value for c in at.caption)


def test_sin_clave_explica_que_falta(monkeypatch, tmp_path):
    ts.escribir(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), None).run()
    assert not at.exception
    assert any("OBS360_CLAVE_HMAC" in e.value for e in at.error)


def test_con_un_modulo_viejo_pide_reiniciar(monkeypatch, tmp_path):
    from src.estudiantes import ingest
    ts.escribir(tmp_path)

    def viejo(rutas, niveles=None):
        raise AssertionError("no debía llamarse")
    monkeypatch.setattr(ingest, "cargar_varios", viejo)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert any("Reinicie" in w.value for w in at.warning)


def test_con_datos_muestra_las_pestanas_sin_nada_individual(monkeypatch, tmp_path):
    ts.escribir(tmp_path)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS
    at.selectbox(key="tri_ba").set_value("SDQ_Emo").run()
    assert not at.exception
    pantalla = " ".join(str(e.value) for e in at.markdown) + \
        " ".join(str(getattr(d, "value", "")) for d in at.dataframe)
    for prohibido in ts.textos_prohibidos():
        assert prohibido not in pantalla


def test_conteos_por_colegio_sin_colegios_pequenos_deducibles():
    from types import SimpleNamespace
    from src.triangulacion import enlace as en
    capa = SimpleNamespace(colegios=["A"], conteos={
        cat.ESTUDIANTE: {"A": 50, "B": 30, "C": 4, "OTRO": 2},
        cat.CUIDADOR: {"A": 40, "B": 12, "C": 3},
        cat.DOCENTE: {"A": 20, "B": 11, "C": 15, "SIN_DATO": 1}})
    t = vi.conteos_actores(SimpleNamespace(capa1=capa))
    filas = {f["Colegio"]: f for f in t.to_dict("records")}
    assert set(filas) == {"A", "B", "C", en.OTROS_COLEGIOS}
    # Cada columna: «otros» (pequeños + OTRO/SIN_DATO) tendría 1 a 9, así que se le
    # suma el colegio publicado más pequeño (B): el total exacto no deduce nada.
    assert [filas[en.OTROS_COLEGIOS][a] for a in ("Estudiantes", "Cuidadores", "Docentes")] \
        == ["36", "15", "12"]
    assert [filas["B"][a] for a in ("Estudiantes", "Cuidadores", "Docentes")] == [vi.EN_OTROS] * 3
    assert [filas["C"][a] for a in ("Estudiantes", "Cuidadores", "Docentes")] \
        == [vi.EN_OTROS, vi.EN_OTROS, "15"]
    assert filas["A"]["En la capa 1"] == "sí" and filas[en.OTROS_COLEGIOS]["En la capa 1"] == "no"


# ── errores sin detalle en pantalla; la firma de la caché cambia con la clave ─
def test_un_error_inesperado_no_muestra_su_texto(monkeypatch, tmp_path):
    from src.triangulacion import pipeline
    ts.escribir(tmp_path)

    def falla(*a, **k):
        raise RuntimeError("detalle-interno-que-no-debe-verse")
    monkeypatch.setattr(pipeline, "cargar_y_analizar", falla)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    textos = " ".join(e.value for e in at.error)
    assert "detalle-interno" not in textos and textos


def test_si_localizar_falla_no_rompe_la_pagina(monkeypatch, tmp_path):
    from src.triangulacion import fuentes

    def falla():
        raise OSError("ruta-que-no-debe-verse")
    monkeypatch.setattr(fuentes, "localizar", falla)
    at = _pagina(monkeypatch, str(tmp_path), ts.CLAVE_PRUEBA).run()
    assert not at.exception
    assert at.error and "ruta-que-no-debe-verse" not in " ".join(e.value for e in at.error)


def test_la_firma_cambia_con_la_clave_sin_llevarla(monkeypatch, tmp_path):
    from src.triangulacion import fuentes
    from src.ui import triangulacion as pag
    ts.escribir(tmp_path)
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    disp = fuentes.localizar()
    monkeypatch.setenv("OBS360_CLAVE_HMAC", ts.CLAVE_PRUEBA)
    f1 = pag.firma(disp)
    monkeypatch.setenv("OBS360_CLAVE_HMAC", ts.CLAVE_PRUEBA + "-otra")
    f2 = pag.firma(disp)
    assert f1 != f2
    assert ts.CLAVE_PRUEBA not in repr(f1) and ts.CLAVE_PRUEBA not in repr(f2)


# ══ Despliegue del equipo: la corrida publicada (sin archivos, sin red) ═══
from tests.supabase_falso import CREDENCIALES_CARGADOR  # noqa: E402

PAGINA = "from src.ui.triangulacion import render_triangulacion\nrender_triangulacion()\n"


def _equipo(monkeypatch, tmp_path, base, modo="investigador",
            clave=CREDENCIALES_CARGADOR["password"]):
    """Despliegue sin archivos, con las credenciales de carga y la base falsa detrás."""
    from src.core import vista_previa as vp
    from src.ui import triangulacion as pag
    monkeypatch.setenv("OBS360_MODO", modo)
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    monkeypatch.setenv("OBS360_SUPABASE_URL", "https://falso.invalid")
    monkeypatch.setenv("OBS360_SUPABASE_KEY", "clave-anon-falsa")
    monkeypatch.delenv("OBS360_FUENTE", raising=False)
    monkeypatch.setattr(vp, "credenciales", lambda: (CREDENCIALES_CARGADOR["email"], clave))
    monkeypatch.setattr(vp, "_crear_cliente", lambda url, key: base.cliente_sin_sesion())
    pag._leer.clear()
    from streamlit.testing.v1 import AppTest
    return AppTest.from_string(PAGINA, default_timeout=180)


def _texto(at) -> str:
    partes = []
    for grupo in (at.markdown, at.caption, at.info, at.warning, at.error, at.title,
                  at.subheader):
        partes += [str(getattr(e, "value", "")) for e in grupo]
    partes += [str(getattr(t, "label", "")) for t in at.toggle]
    partes += [str(getattr(e, "value", "")) for e in at.sidebar.caption]
    partes += [str(getattr(d, "value", "")) for d in at.dataframe]
    return " ".join(partes)


def test_el_mensaje_fijo_dice_que_no_hay_corrida_publicada():
    assert "aún no hay una corrida de triangulación publicada" in cat.AVISO_DESPLIEGUE


def test_sin_archivos_muestra_la_corrida_publicada(monkeypatch, tmp_path):
    from src.triangulacion import lectura
    from tests import triangulacion_publicada_datos as datos
    resumen, base = datos.publicado(publicar_ya=True)
    at = _equipo(monkeypatch, tmp_path, base).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS
    assert any(lectura.AVISO_PUBLICADO in i.value for i in at.info)
    assert not any(cat.AVISO_DESPLIEGUE in i.value for i in at.info)
    assert not at.toggle                                   # nada en revisión
    texto = _texto(at)
    assert f"corrida {resumen['corrida_id']}" in texto
    at.selectbox(key="tri_ba").set_value("SDQ_Emo").run()
    assert not at.exception
    texto = _texto(at)
    for prohibido in ts.textos_prohibidos():
        assert prohibido not in texto
    assert CREDENCIALES_CARGADOR["password"] not in texto
    assert at.get("download_button")                       # el ZIP de agregados


def test_la_corrida_en_revision_con_su_franja(monkeypatch, tmp_path):
    from src.triangulacion import publicar as pub
    from tests import triangulacion_publicada_datos as datos
    resumen, base = datos.publicado(publicar_ya=True)
    oculta = pub.publicar(datos.analisis(), publicar_ya=False, cliente=base.cliente())
    at = _equipo(monkeypatch, tmp_path, base).run()
    assert not at.exception
    toggle = at.toggle(key="vista_previa_triangulacion")
    assert toggle.value and str(oculta["corrida_id"]) in toggle.label
    texto = _texto(at)
    assert "Vista previa para el equipo" in texto
    assert f"Fuente: corrida en revisión ({oculta['corrida_id']})" in texto
    assert "nunca es pública" in " ".join(str(m.value) for m in at.markdown)
    assert [t.label for t in at.tabs] == vi.PESTANAS
    at.toggle(key="vista_previa_triangulacion").set_value(False).run()
    assert not at.exception
    assert "Vista previa para el equipo" not in _texto(at)
    assert f"corrida {resumen['corrida_id']}" in _texto(at)


def test_solo_oculta_y_vista_previa_apagada_da_el_mensaje(monkeypatch, tmp_path):
    from tests import triangulacion_publicada_datos as datos
    _, base = datos.publicado(publicar_ya=False)
    at = _equipo(monkeypatch, tmp_path, base, modo="completo").run()
    assert not at.exception
    assert at.toggle(key="vista_previa_triangulacion").value is False
    assert any(cat.AVISO_DESPLIEGUE in i.value for i in at.info)
    assert not at.tabs


def test_sin_sesion_del_cargador_da_el_mensaje(monkeypatch, tmp_path):
    from tests import triangulacion_publicada_datos as datos
    _, base = datos.publicado(publicar_ya=True)
    at = _equipo(monkeypatch, tmp_path, base, clave="equivocada").run()
    assert not at.exception
    assert any(cat.AVISO_DESPLIEGUE in i.value for i in at.info)
    assert not at.tabs


def test_un_vista_previa_rancio_igual_lee_la_publicada(monkeypatch, tmp_path):
    from src.core import vista_previa as vp
    from tests import triangulacion_publicada_datos as datos
    _, base = datos.publicado(publicar_ya=True)
    at = _equipo(monkeypatch, tmp_path, base)
    monkeypatch.setattr(vp, "MODULOS", ("estudiantes", "cuidadores"))
    monkeypatch.delattr(vp, "marcar_en_uso")
    at.run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS


def test_si_la_lectura_falla_no_muestra_el_detalle(monkeypatch, tmp_path):
    from src.triangulacion import lectura
    from tests import triangulacion_publicada_datos as datos
    _, base = datos.publicado(publicar_ya=True)
    at = _equipo(monkeypatch, tmp_path, base)

    def falla(*a, **k):
        raise RuntimeError("detalle-interno-de-la-lectura")
    monkeypatch.setattr(lectura, "cargar", falla)
    at.run()
    assert not at.exception
    assert "detalle-interno" not in _texto(at)
    assert any(cat.AVISO_DESPLIEGUE in i.value for i in at.info)
