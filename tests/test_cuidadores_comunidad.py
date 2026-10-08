"""Cuidadores 360 · vista de comunidad (fase 4b, spec §5.5 y §6)."""
import pickle

import pytest
from streamlit.testing.v1 import AppTest

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.estudiantes import alertas_catalogo as ac_est
from src.ui.views import cuidadores_comunidad as vc
from tests import cuidadores_comunidad_datos as datos
from tests import cuidadores_sinteticos as cs

ROLES = ("colegio", "familia", "municipio")
PALABRAS_DANO = ("daño", "autoles", "muerte", "suicid")


@pytest.fixture(scope="module")
def ac():
    return datos.preparado()


@pytest.fixture(scope="module")
def senales(ac):
    return datos.con_senales(ac)


@pytest.fixture(scope="module")
def leido():
    return datos.publicado()[0]


# ══ Tarjetas ═══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("rol", ROLES)
def test_tarjetas_por_rol(ac, rol):
    claves = [t.clave for t in vc.tarjetas(ac, rol, {})]
    assert claves == ["estres", "apoyo", "crianza", "barrio", "hijo"]
    assert len(claves) <= cc.MAX_TARJETAS


def test_animo_solo_vuelve_si_el_panel_no_salio_y_nunca_para_familia(ac):
    assert "animo" in [t.clave for t in vc.tarjetas(ac, "colegio", {}, panel_dibujado=False)]
    assert "animo" in [t.clave for t in vc.tarjetas(ac, "municipio", {}, panel_dibujado=False)]
    assert "animo" not in [t.clave for t in vc.tarjetas(ac, "familia", {},
                                                         panel_dibujado=False)]
    assert len(vc.tarjetas(ac, "colegio", {}, panel_dibujado=False)) == cc.MAX_TARJETAS


def test_las_tarjetas_traen_cifra_texto_del_catalogo_y_accion_del_rol(ac):
    for t in vc.tarjetas(ac, "colegio", {}):
        m = cc.MENSAJES[t.clave]
        assert t.titulo == m.titulo and t.significa == m.significa
        assert t.accion == m.accion["colegio"]
        assert t.cifra


def test_una_cifra_suprimida_lleva_el_texto_fijo(ac):
    grupo = next(g for g in vc.grupos(ac, "Colegio")
                 if vc.suprimida(ac, "castigo", {"colegio": g}))
    t = next(t for t in vc.tarjetas(ac, "colegio", {"colegio": grupo}) if t.clave == "crianza")
    assert t.suprimida and t.cifra == vc.CIFRA_SUPRIMIDA and t.detalle == cc.CIFRAS_PEQUENAS
    assert "%" not in t.detalle


def test_las_medias_no_existen_por_celda(ac):
    assert vc.media(ac, "PSS_Total", {}) and vc.media(ac, "PSS_Total", {"colegio": "LauV"})
    assert vc.media(ac, "PSS_Total", {"colegio": "LauV", "grado": "Quinto"}) == {}


@pytest.mark.parametrize("rol", ROLES)
@pytest.mark.parametrize("filtros", [{}, {"colegio": "LauV"}, {"grado": "Quinto"},
                                     {"colegio": "LauV", "grado": "Quinto"},
                                     {"colegio": "SJMEB"}])
def test_local_y_publicado_muestran_lo_mismo(ac, leido, rol, filtros):
    assert vc.tarjetas(ac, rol, filtros) == vc.tarjetas(leido, rol, filtros)
    assert vc.bandas_hijo(ac, filtros) == vc.bandas_hijo(leido, filtros)
    assert vc.panel_html(ac, rol, filtros) == vc.panel_html(leido, rol, filtros)


def test_los_grupos_son_los_de_la_base_en_los_dos_marcos(ac, leido):
    assert vc.grupos(ac, "Colegio") == vc.grupos(leido, "Colegio") == \
        ["JJC", "LaBalsa", "LauV", "SJMEB"]
    assert vc.grupos(ac, "Grado", "LauV") == ["Quinto", "Sexto", "Octavo"]
    assert "OTRO" not in vc.grupos(ac, "Colegio") and "CdP" not in vc.grupos(ac, "Colegio")


# ══ Señales del adulto ═════════════════════════════════════════════════════
def test_familia_no_ve_cifras_ni_nada_sobre_hacerse_dano(senales):
    assert vc.senales(senales, "familia", {}) == []
    html = vc.panel_html(senales, "familia", {})
    assert cc.AUTOCUIDADO_FAMILIA in html and "%" not in html
    for palabra in PALABRAS_DANO:
        assert palabra not in html.lower()


def test_colegio_ve_animo_con_estado_general_y_nunca_la_autolesion(senales):
    for filtros in ({}, {"colegio": "LauV"}, {"colegio": "LauV", "grado": "Quinto"}):
        lista = vc.senales(senales, "colegio", filtros)
        assert [s.alerta for s in lista] == [cat.ANIMO]
        html = vc.panel_html(senales, "colegio", filtros)
        assert cc.ESTADO_GENERAL_COLEGIO in html
        assert cc.ALERTAS[cat.AUTOLESION].nombre not in html


def test_dentro_del_colegio_los_grados_en_prioridad(senales):
    s = vc.senales(senales, "colegio", {"colegio": "LauV"})[0]
    assert s.estado == ac_est.PRIORIDAD and s.pct == 40.0
    assert s.listas == ((ac_est.TITULO_GRADOS_PRIORIDAD, ("Quinto",)),)


def test_municipio_ve_la_autolesion_solo_del_total(senales):
    for filtros in ({}, {"colegio": "LauV"}, {"grado": "Quinto"}):
        auto = [s for s in vc.senales(senales, "municipio", filtros)
                if s.alerta == cat.AUTOLESION]
        assert len(auto) == 1 and auto[0].pct == 11.0 and auto[0].listas == ()
    assert vc.fila_alerta(senales, cat.AUTOLESION, {"colegio": "LauV"})["grupo"] == "Todos"


def test_municipio_ve_colegios_y_grados_en_prioridad(senales):
    s = next(s for s in vc.senales(senales, "municipio", {}) if s.alerta == cat.ANIMO)
    assert dict(s.listas) == {ac_est.TITULO_COLEGIOS_PRIORIDAD: ("LauV",),
                              ac_est.TITULO_GRADOS_PRIORIDAD: ("Quinto",)}


def test_sin_porcentaje_no_hay_estado_ni_cifra(senales):
    s = vc.senales(senales, "colegio", {"colegio": "SJMEB"})[0]
    assert s.estado == ac_est.SIN_ESTADO and s.pct is None
    assert s.frase == cc.CIFRAS_PEQUENAS


def test_la_frase_no_cuenta_casos(senales):
    s = vc.senales(senales, "municipio", {})[0]
    assert s.frase == "1 de cada 4 cuidadores muestra señales de ánimo bajo."


def test_la_tabla_de_la_secretaria_no_trae_la_autolesion(senales):
    html = vc.tabla_secretaria_html(senales)
    assert "LauV" in html and "Prioridad" in html
    assert cc.ALERTAS[cat.AUTOLESION].nombre_corto not in html


def test_sin_tabla_de_senales_no_hay_panel_y_vuelve_la_tarjeta(ac):
    vacio = datos.con_senales(ac, vc.al.vacia())
    assert vc.senales(vacio, "municipio", {}) == []
    assert vc.panel_html(vacio, "municipio", {}) == ""


def test_el_color_maximo_es_el_naranja_de_estudiantes():
    from src.ui.views import estudiantes_alertas as va
    assert vc.va is va
    assert "#C0392B" not in va.CSS_INFORME.upper() and "#C0392B" not in va.CSS_PAGINA.upper()


# ══ Comparar entre grupos ══════════════════════════════════════════════════
def test_comparables_por_rol():
    assert "animo" not in vc.comparables("familia")
    assert "animo" in vc.comparables("colegio") and "animo" in vc.comparables("municipio")
    for rol in ROLES:
        assert not [k for k in vc.comparables(rol) if "auto" in k]


def test_la_comparacion_sin_casos_y_solo_con_porcentaje(ac):
    t = vc.prevalencia_por(ac, "castigo", "Colegio")
    assert list(t.columns) == ["grupo", "n", "pct", "ic_inf", "ic_sup"]
    assert t["pct"].notna().all()
    sin = vc.grupos_sin_cifra(ac, "castigo", "Colegio")
    assert not set(sin) & set(t["grupo"])


# ══ Página (AppTest) ═══════════════════════════════════════════════════════
def _app(tmp_path, objeto: str, pre: str = "") -> AppTest:
    ruta = tmp_path / "objetos.pkl"
    if not ruta.exists():
        with open(ruta, "wb") as fh:
            pickle.dump((datos.preparado(), datos.publicado()[0]), fh)
    codigo = (f"import pickle\nac, leido = pickle.load(open({str(ruta)!r}, 'rb'))\n{pre}\n"
              "from src.ui.views.cuidadores_comunidad import render_comunidad\n"
              f"render_comunidad({objeto})\n")
    return AppTest.from_string(codigo, default_timeout=120)


def _pantalla(at) -> str:
    partes = [str(getattr(e, "value", "")) for grupo in (at.markdown, at.caption, at.info,
                                                         at.warning, at.subheader)
              for e in grupo]
    return " ".join(partes)


@pytest.mark.parametrize("objeto", ["ac", "leido"])
@pytest.mark.parametrize("rol", ROLES)
def test_la_vista_se_dibuja_para_cada_rol(tmp_path, objeto, rol):
    at = _app(tmp_path, objeto)
    at.session_state["cuid_com_rol"] = rol
    at.run()
    assert not at.exception
    pantalla = _pantalla(at)
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in pantalla
    assert cc.TITULO_RUTA in pantalla
    if rol == "familia":
        assert cc.AUTOCUIDADO_FAMILIA in pantalla
        for palabra in PALABRAS_DANO:
            assert palabra not in pantalla.lower()
        assert "cuid_com_colegio" not in [s.key for s in at.sidebar.selectbox]


def test_familia_no_tiene_selector_de_colegio_ni_informes(tmp_path):
    at = _app(tmp_path, "ac")
    at.session_state["cuid_com_rol"] = "familia"
    at.run()
    claves = [s.key for s in at.selectbox]
    assert "cuid_com_colegio" not in claves and "cuid_inf_colegio" not in claves


def test_cambiar_de_colegio_y_grado_no_falla(tmp_path):
    at = _app(tmp_path, "leido")
    at.session_state["cuid_com_rol"] = "municipio"
    at.run()
    at.selectbox(key="cuid_com_colegio").set_value("LauV").run()
    assert not at.exception
    assert list(at.selectbox(key="cuid_com_grado").options) == ["Todos", "Quinto", "Sexto",
                                                                "Octavo"]
    at.selectbox(key="cuid_com_grado").set_value("Quinto").run()
    assert not at.exception


def test_el_colegio_y_el_rol_se_comparten_con_estudiantes(tmp_path):
    from src.ui import estado
    at = _app(tmp_path, "ac")
    at.session_state[estado.COLEGIO] = "JJC"
    at.session_state[estado.ROL] = "municipio"
    at.run()
    assert at.selectbox(key="cuid_com_colegio").value == "JJC"
    assert at.radio(key="cuid_com_rol").value == "municipio"
    at.selectbox(key="cuid_com_colegio").set_value("LauV").run()
    assert at.session_state[estado.COLEGIO] == "LauV"


def test_el_colegio_de_la_url_aplica_a_cuidadores(tmp_path):
    from src.ui import estado
    pre = ("from src.ui import estado\nfrom src.ui.views import cuidadores_comunidad as vc\n"
           "estado.aplicar_colegio_de_url(vc.colegio_de_la_url(ac))")
    at = _app(tmp_path, "ac", pre)
    at.query_params["colegio"] = "lauv"
    at.run()
    assert not at.exception
    assert at.session_state[estado.COLEGIO] == "LauV"
    assert at.selectbox(key="cuid_com_colegio").value == "LauV"


def test_un_colegio_de_la_url_sin_cifras_se_ignora(tmp_path):
    from src.ui import estado
    pre = ("from src.ui import estado\nfrom src.ui.views import cuidadores_comunidad as vc\n"
           "estado.aplicar_colegio_de_url(vc.colegio_de_la_url(ac))")
    at = _app(tmp_path, "ac", pre)
    at.query_params["colegio"] = "CdP"
    at.run()
    assert not at.exception
    assert at.selectbox(key="cuid_com_colegio").value == "Todos"
    assert at.session_state[estado.COLEGIO] == "Todos"


def test_el_aviso_interno_solo_en_el_modo_completo(monkeypatch):
    monkeypatch.setenv("OBS360_MODO", "completo")
    assert cc.TEXTOS_PENDIENTES in vc.avisos_internos()
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    assert vc.avisos_internos() == []


def test_render_publico_sin_corrida_dice_que_no_hay(monkeypatch):
    from src.cuidadores import lectura
    monkeypatch.setattr(lectura, "disponible", lambda: False)
    at = AppTest.from_string("from src.ui.views.cuidadores_comunidad import render_publico\n"
                             "render_publico()\n", default_timeout=60).run()
    assert not at.exception
    assert any(cc.NO_PUBLICADO in i.value for i in at.info)


def test_la_vista_no_importa_lo_de_investigacion():
    import inspect
    fuente = inspect.getsource(vc)
    for prohibido in ("cuidadores import ingest", "cuidadores import pipeline",
                      "cuidadores_investigador", "src.ui.cuidadores", "cuidadores import scoring",
                      "cuidadores import privacidad", "cuidadores import comunidad\n"):
        assert prohibido not in fuente
