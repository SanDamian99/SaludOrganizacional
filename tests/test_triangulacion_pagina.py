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
