"""
Triangulación 360 · lectura de la corrida publicada (despliegue del equipo, sin red).

  · Solo con el cliente del usuario de carga (`vista_previa.cliente_autenticado`),
    nunca con la clave anon: sin ese cliente no hay nada que leer.
  · Publicar → leer da los MISMOS agregados que ve la vista local: tablas,
    clasificación, conteos legibles, calidad del enlace, metodología y el ZIP.
  · Lo leído sigue sin identificadores, con n ≥ 10, y la capa 1 leída pasa la
    auditoría de restas junto a lo que publican los módulos.
"""
import io
import re
import zipfile

import pandas as pd
import pytest

from src.core import vista_previa as vp
from src.triangulacion import exportar as ex
from src.triangulacion import publicar as pub
from tests import triangulacion_publicada_datos as datos
from tests.supabase_falso import CREDENCIALES_CARGADOR, BaseFalsa

from src.triangulacion import lectura  # noqa: E402
EMAIL, CLAVE = CREDENCIALES_CARGADOR["email"], CREDENCIALES_CARGADOR["password"]
SEUDONIMO = re.compile(r"(?<![0-9A-Za-z])[CEN][0-9a-f]{8}(?![0-9a-f])")


def _cargador(monkeypatch, base, clave=CLAVE, modo="investigador"):
    """La vista previa real, con la base falsa detrás y el usuario de carga."""
    monkeypatch.setenv("OBS360_MODO", modo)
    monkeypatch.setenv("OBS360_SUPABASE_URL", "https://falso.invalid")
    monkeypatch.setenv("OBS360_SUPABASE_KEY", "clave-anon-falsa")
    monkeypatch.setattr(vp, "credenciales", lambda: (EMAIL, clave))
    monkeypatch.setattr(vp, "_crear_cliente", lambda url, key: base.cliente_sin_sesion())


@pytest.fixture
def base():
    _, b = datos.publicado(publicar_ya=True)
    return b


# ══ Solo el usuario de carga ═══════════════════════════════════════════════
def test_sin_cliente_de_carga_no_lee_nada(base):
    assert lectura.cargar() is None
    assert lectura.id_corrida_publicada() is None


def test_con_el_cargador_lee_la_publicada(monkeypatch, base):
    _cargador(monkeypatch, base)
    t = lectura.cargar()
    assert t is not None and t.origen == "supabase"
    assert t.corrida["modulo"] == "triangulacion" and t.corrida["publicada"] is True


def test_un_inicio_de_sesion_fallido_no_lee_nada(monkeypatch, base):
    _cargador(monkeypatch, base, clave="otra")
    assert lectura.cargar() is None


def test_en_comunidad_nunca_lee(monkeypatch, base):
    _cargador(monkeypatch, base, modo="comunidad")
    assert lectura.cargar() is None


def test_con_un_cliente_anonimo_no_hay_filas(monkeypatch, base):
    """Si algo entregara un cliente anon, RLS no le deja ver la triangulación."""
    monkeypatch.setattr(vp, "cliente_autenticado", lambda: base.cliente(anonimo=True))
    assert lectura.cargar() is None
    assert lectura.id_corrida_publicada() is None


def test_lectura_no_crea_clientes_propios():
    import inspect
    fuente = inspect.getsource(lectura)
    assert "create_client" not in fuente
    assert not re.search(r"^\s*(from|import)\s+.*(estudiantes|cuidadores)\.lectura", fuente,
                         re.MULTILINE)
    assert "cliente_autenticado" in fuente


def test_la_corrida_en_revision_se_lee_por_id(monkeypatch, base):
    oculta = pub.publicar(datos.analisis(), publicar_ya=False, cliente=base.cliente())
    _cargador(monkeypatch, base)
    t = lectura.cargar(corrida_id=oculta["corrida_id"])
    assert t is not None and t.corrida["publicada"] is False
    # sin id, la publicada (la oculta más nueva no se cuela)
    assert lectura.cargar().corrida["id"] != oculta["corrida_id"]


def test_un_id_de_otro_modulo_no_se_lee_como_triangulacion(monkeypatch):
    from tests import cuidadores_comunidad_datos as datos_cuid
    _, b = datos_cuid.publicado()
    cid = b.tablas["corridas"][0]["id"]
    _cargador(monkeypatch, b)
    assert lectura.cargar(corrida_id=cid) is None


# ══ Ida y vuelta: lo mismo que la vista local ═════════════════════════════
@pytest.fixture
def leida(monkeypatch, base):
    _cargador(monkeypatch, base)
    return lectura.cargar()


def _igual(a: pd.DataFrame, b: pd.DataFrame, nombre: str):
    a = ex._limpia(a).reset_index(drop=True)
    b = ex._limpia(b).reset_index(drop=True)
    assert list(a.columns) == list(b.columns), nombre
    pd.testing.assert_frame_equal(a, b, check_dtype=False, obj=nombre)


def test_las_tablas_son_las_mismas(leida):
    local = datos.analisis()
    tl, tp = ex.tablas(local), ex.tablas(leida)
    assert set(tl) == set(tp)
    for nombre in tl:
        _igual(tl[nombre], tp[nombre], nombre)
    assert leida.capa1.colegios == local.capa1.colegios
    assert leida.capa1.grados == local.capa1.grados
    assert leida.n_colegios == local.n_colegios


def test_conteos_metricas_y_textos_iguales(leida):
    from src.triangulacion import enlace as en
    from src.ui.views import triangulacion_investigador as vi
    local = datos.analisis()
    _igual(vi.conteos_actores(local), vi.conteos_actores(leida), "conteos")
    assert en.conteo_legible(leida.diadas.n) == en.conteo_legible(local.diadas.n)
    assert en.conteo_legible(leida.diadas.familias) == en.conteo_legible(local.diadas.familias)
    assert ex.metodologia_md(leida) == ex.metodologia_md(local)
    assert ex.version_txt(leida) == ex.version_txt(local)


def test_el_zip_publicado_trae_lo_mismo(leida):
    zl = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(datos.analisis())))
    zp = zipfile.ZipFile(io.BytesIO(ex.paquete_zip(leida)))
    assert set(zl.namelist()) == set(zp.namelist())
    for nombre in zl.namelist():
        if nombre.endswith(".png"):
            assert zp.read(nombre).startswith(b"\x89PNG")
        else:
            assert zl.read(nombre) == zp.read(nombre), nombre


def test_las_figuras_salen_de_las_tablas(leida):
    sub = leida.diadas.bland_altman["subescala"].iloc[0]
    ax = ex.figura_bland_altman(leida, sub).axes[0]
    import src.triangulacion.catalogo as cat
    puntos = sum(len(l.get_xdata()) for l in ax.get_lines() if l.get_marker() == "s")
    assert 0 < puntos <= cat.MAX_BINES_BA
    assert ex.figura_capa1(leida, leida.capa1.colegios[0]).axes


def test_lo_leido_no_trae_identificadores(leida):
    from tests import triangulacion_sinteticos as ts
    texto = " ".join(df.to_csv() for df in ex.tablas(leida).values())
    texto += ex.metodologia_md(leida) + repr(leida.actores)
    assert not SEUDONIMO.search(texto)
    for prohibido in ts.textos_prohibidos():
        assert prohibido not in texto


def test_la_capa1_leida_pasa_la_auditoria_de_restas(leida):
    from src.triangulacion import capa1 as c1
    from tests import triangulacion_span as span
    deducibles = span.auditar_capa1(c1.marcos(datos.fuentes()), leida.capa1)
    assert deducibles and sum(deducibles.values()) == 0


def test_reconstruir_sin_filas_es_none():
    assert lectura.reconstruir([], None) is None


def test_un_formato_futuro_no_se_lee(leida, base):
    filas = [dict(f) for f in base.tablas["resultados"]]
    for f in filas:
        if f["tipo"] == pub.TIPO_META:
            f["detalle"] = dict(f["detalle"], formato=99)
    assert lectura.reconstruir(filas, {}) is None


def test_un_conteo_ya_enmascarado_se_muestra_igual():
    from src.triangulacion import enlace as en
    assert en.conteo_legible("<10") == "<10"
    assert en.conteo_legible(12) == "12" and en.conteo_legible(3) == "<10"
    assert en.conteo_legible("x") == "—"
