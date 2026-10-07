"""Panel «Señales para actuar a tiempo» en la vista, los informes y el PDF (spec §5.4, §6)."""
import colorsys
import dataclasses
import io
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.core.colegios import COLEGIOS
from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.ui.views import estudiantes_alertas as va

P, T, R, S = ac.PRIORIDAD, ac.PRESENTE, ac.REFERENCIA, ac.SIN_ESTADO


def _r(alerta, agrupacion, grupo, pct=None, estado=S, n=60):
    return dict(alerta=alerta, agrupacion=agrupacion, grupo=grupo, n=n, pct=pct,
                ic_inf=None if pct is None else pct - 5,
                ic_sup=None if pct is None else pct + 5, estado=estado)


TABLA = [
    _r("malestar", "total", "Todos", 16.7, R, n=900),
    _r("malestar", "Colegio", "LauV", 25.0, P, n=400),
    _r("malestar", "Colegio", "JJC"),
    _r("malestar", "Grado", "Octavo", 30.0, P, n=150),
    _r("malestar", "Grado", "Sexto", 12.0, T, n=150),
    _r("malestar", "Colegio×Grado", "LauV|Octavo", 35.0, P, n=90),
    _r("malestar", "Colegio×Grado", "LauV|Sexto", 33.0, P, n=95),
    _r("malestar", "Colegio×Grado", "LauV|Noveno"),
    _r("desesperanza", "total", "Todos", 17.0, R, n=900),
    _r("desesperanza", "Colegio", "LauV", 20.0, T, n=400),
]


def _ns(filas=TABLA, nivel=cat.NIVEL_SECUNDARIA):
    return SimpleNamespace(nivel=nivel, alertas=pd.DataFrame(filas, columns=al.COLUMNAS_TABLA))


def test_frase_de_la_cifra():
    assert va.frase("malestar", 16.7) == "1 de cada 6 estudiantes muestra señales de malestar."
    assert va.frase("malestar", 40) == "4 de cada 10 estudiantes muestran señales de malestar."


def test_familia_solo_ve_malestar_y_sin_listas():
    s = va.senales(_ns(), "familia", {})
    assert [x.alerta for x in s] == ["malestar"]
    assert s[0].listas == ()
    assert s[0].que_hacer == ac.ALERTAS["malestar"].que_hacer["familia"]


def test_colegio_ve_las_dos_y_los_grados_en_prioridad():
    s = {x.alerta: x for x in va.senales(_ns(), "colegio", {})}
    assert set(s) == {"malestar", "desesperanza"}
    m = s["malestar"]
    assert m.estado == R and m.etiqueta_estado == "Para tener presente" and m.visible
    assert m.frase == "1 de cada 6 estudiantes muestra señales de malestar."
    assert m.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)),)


def test_dentro_de_un_colegio_los_grados_van_en_orden_canonico():
    s = va.senales(_ns(), "colegio", {"colegio": "LauV"})[0]
    assert s.estado == P
    assert s.listas == ((ac.TITULO_GRADOS_PRIORIDAD, ("Sexto", "Octavo")),)


def test_el_municipio_ve_colegios_y_grados_en_prioridad():
    s = va.senales(_ns(), "municipio", {})[0]
    assert s.listas == ((ac.TITULO_COLEGIOS_PRIORIDAD, ("Laura Vicuña",)),
                        (ac.TITULO_GRADOS_PRIORIDAD, ("Octavo",)))


def test_un_grado_con_cifra_lleva_porcentaje_y_estado():
    s = va.senales(_ns(), "familia", {"grado": "Octavo"})[0]
    assert s.estado == P and s.pct == 30.0
    c = va.senales(_ns(), "colegio", {"colegio": "LauV", "grado": "Octavo"})[0]
    assert c.estado == P and c.frase.startswith("4 de cada 10")


@pytest.mark.parametrize("filtros", [{"colegio": "JJC"}, {"colegio": "LauV", "grado": "Noveno"},
                                     {"grado": "Noveno"}])
def test_sin_cifra_el_estado_es_neutro_y_va_el_texto_fijo(filtros):
    s = va.senales(_ns(), "colegio", filtros)[0]
    assert s.estado == S and s.etiqueta_estado == "Sin estado: cifras pequeñas"
    assert s.frase == ac.CIFRAS_PEQUENAS and s.pct is None and s.n is None


def test_el_panel_solo_usa_cifras_de_la_tabla():
    """Cada cifra de una señal es la de su fila; nada se calcula ni se cuenta aparte."""
    for filtros in ({}, {"colegio": "LauV"}, {"grado": "Octavo"}, {"colegio": "JJC"},
                    {"colegio": "LauV", "grado": "Sexto"}):
        for s in va.senales(_ns(), "municipio", filtros):
            f = va.fila(_ns(), s.alerta, filtros)
            if s.visible:
                assert (s.pct, s.ic_inf, s.ic_sup, s.n, s.estado) == \
                    (f["pct"], f["ic_inf"], f["ic_sup"], f["n"], f["estado"])
            else:
                assert f is None or pd.isna(f["pct"])
    assert {x.name for x in dataclasses.fields(va.Senal)} == {
        "alerta", "nombre", "estado", "frase", "que_hacer", "pct", "ic_inf", "ic_sup", "n",
        "listas"}


def test_las_explicaciones_son_solo_de_los_estados_que_aparecen():
    lista = va.senales(_ns(), "colegio", {})            # dos «referencia»
    assert va.explicaciones(lista) == [ac.QUE_ES_REFERENCIA]
    assert ac.QUE_ES_PRESENTE in va.explicaciones(va.senales(_ns(), "colegio", {"grado": "Sexto"}))
    assert va.explicaciones(va.senales(_ns(), "colegio", {"colegio": "JJC"})) == \
        [ac.QUE_ES_SIN_ESTADO]


def test_primaria_no_trae_desesperanza():
    assert [x.alerta for x in va.senales(_ns(nivel=cat.NIVEL_PRIMARIA), "colegio", {})] \
        == ["malestar"]


def test_sin_tabla_no_hay_panel():
    assert va.senales(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA), "colegio", {}) == []
    assert va.panel_html(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA), "colegio", {}) == ""


def _seccion(html):
    return html.split('<section class="senales')[1].split("</section>")[0]


def test_el_panel_html_no_alarma_ni_cuenta_casos():
    html = va.panel_html(_ns(), "colegio", {"colegio": "LauV"})
    sec = _seccion(html)
    assert ac.TITULO_PANEL in sec and ac.NO_ES_DIAGNOSTICO in sec and ac.NOTA_AZAR in sec
    assert "Prioridad" in sec and "casos" not in sec.lower()
    assert "#C0392B" not in sec.upper()


def test_el_recuadro_compacto_recorta_las_listas():
    filas = [_r("malestar", "total", "Todos", 16.7, R, n=900)]
    filas += [_r("malestar", "Colegio", c, 30.0, P) for _, c, _ in COLEGIOS]
    html = va.panel_html(_ns(filas), "municipio", {}, compacto=True)
    assert f"y {len(COLEGIOS) - va.MAX_NOMBRES_PAGINA} más" in html


def test_tabla_de_la_secretaria():
    html = va.tabla_secretaria_html(_ns())
    assert "Laura Vicuña" in html and "José Joaquín Casas" in html
    assert ac.CIFRAS_PEQUENAS_CORTO in html and "Total del municipio" in html
    assert ac.ESTADOS[S] in html and "casos" not in html.lower()


def _hls(color):
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def test_el_color_maximo_es_naranja_nunca_rojo():
    tono, _, saturacion = _hls(va.COLOR_PRIORIDAD)
    assert 25 <= tono * 360 <= 45 and saturacion > 0.5
    assert _hls(va.COLOR_PRESENTE)[2] < 0.2 and _hls(va.COLOR_SIN_ESTADO)[2] < 0.2
    for css in (va.CSS_INFORME, va.CSS_PAGINA):
        assert "#C0392B" not in css.upper() and va.COLOR_PRIORIDAD in css


# ══ Vista comunidad ═════════════════════════════════════════════════════════
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring  # noqa: E402
from src.ui.views import estudiantes_comunidad as vc  # noqa: E402
from tests.test_estudiantes_comunidad import _formulario  # noqa: E402


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)


def test_el_panel_reemplaza_la_tarjeta_de_muerte_para_colegio_y_municipio(analisis):
    for rol in ("colegio", "municipio"):
        assert vc.panel_reemplaza_muerte(analisis, rol)
        assert "ideacion" not in {t.clave for t in vc.tarjetas(analisis, rol)}
    assert not vc.panel_reemplaza_muerte(analisis, "familia")


def test_sin_alertas_la_tarjeta_de_muerte_vuelve(analisis):
    viejo = dataclasses.replace(analisis, alertas=pd.DataFrame())
    assert "ideacion" in {t.clave for t in vc.tarjetas(viejo, "colegio")}
    assert va.senales(viejo, "colegio", {}) == []


def test_una_corrida_publicada_sin_alertas_vuelve_a_la_tarjeta(analisis):
    filas = [f for f in publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
             if not f["tipo"].startswith("alerta")]
    viejo = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert va.senales(viejo, "colegio", {}) == []
    assert "ideacion" in {t.clave for t in vc.tarjetas(viejo, "colegio")}


def test_comparar_entre_grupos_sin_muerte_para_familia_ni_con_panel(analisis):
    assert "ideacion" not in vc.indicadores_comparables(analisis, "familia")
    assert "ideacion" not in vc.indicadores_comparables(analisis, "colegio")
    viejo = dataclasses.replace(analisis, alertas=pd.DataFrame())
    assert "ideacion" in vc.indicadores_comparables(viejo, "colegio")
    assert "ideacion" not in vc.indicadores_comparables(viejo, "familia")


def test_la_ruta_por_rol_es_la_vigente():
    for rol in cat.ROLES:
        assert vc.ruta_para_rol(rol) == list(cat.RUTA_ATENCION)


@pytest.mark.parametrize("modo,ve", [("completo", True), ("comunidad", False),
                                     ("investigador", False)])
def test_el_aviso_de_ruta_pendiente_solo_en_el_modo_completo(monkeypatch, modo, ve):
    monkeypatch.setenv("OBS360_MODO", modo)
    assert (vc.aviso_ruta_pendiente() == ac.RUTA_PENDIENTE) is ve


def test_si_el_panel_falla_la_pagina_sigue(monkeypatch, analisis):
    def falla(*a, **k):
        raise RuntimeError("módulo viejo")
    monkeypatch.setattr(va, "render_panel", falla)
    vc._panel_alertas(analisis, "colegio", {})          # no lanza


# ══ Informes ════════════════════════════════════════════════════════════════
from src.ui.views import estudiantes_informe as inf  # noqa: E402

COLEGIO = "LauV"


@pytest.fixture(scope="module", params=["archivos", "publicado"])
def fuente(request, analisis):
    if request.param == "archivos":
        return {cat.NIVEL_SECUNDARIA: analisis}
    filas = publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
    publicar.verificar(filas)
    return {cat.NIVEL_SECUNDARIA: lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)}


def test_el_informe_del_colegio_trae_el_panel(fuente):
    html = inf.informe_colegio_html(fuente, COLEGIO, fecha=date(2026, 10, 8))
    assert ac.TITULO_PANEL in html and ac.NO_ES_DIAGNOSTICO in html
    assert html.index(ac.TITULO_PANEL) < html.index("Resultados y qué hacer")
    assert "casos" not in _seccion(html).lower()
    assert "Piensa en la muerte con frecuencia" not in html     # el panel la reemplaza
    assert ac.RUTA_PENDIENTE not in html


def test_la_secretaria_trae_la_tabla_por_colegio(fuente):
    html = inf.informe_secretaria_html(fuente, fecha=date(2026, 10, 8))
    assert '<table class="senales-tabla">' in html and "Laura Vicuña" in html
    assert "Piensa en la muerte con frecuencia" not in html
    assert ac.RUTA_PENDIENTE not in html


def test_la_tabla_de_alertas_es_la_misma_desde_archivos_y_publicado(analisis):
    filas = publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
    pub = {cat.NIVEL_SECUNDARIA: lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)}

    def tabla(x):
        return inf.informe_secretaria_html(x, fecha=date(2026, 10, 8)).split(
            '<table class="senales-tabla">')[1].split("</table>")[0]
    assert tabla({cat.NIVEL_SECUNDARIA: analisis}) == tabla(pub)


def test_sin_alertas_los_informes_quedan_como_antes(analisis):
    viejo = {cat.NIVEL_SECUNDARIA: dataclasses.replace(analisis, alertas=pd.DataFrame())}
    html = inf.informe_secretaria_html(viejo, fecha=date(2026, 10, 8))
    assert ac.TITULO_PANEL not in html
    assert "Piensa en la muerte con frecuencia" in html


def test_con_modulos_viejos_los_informes_no_se_caen(monkeypatch, analisis):
    """Streamlit Cloud puede conservar un `estudiantes_comunidad` sin `ruta_para_rol`
    o un panel que falla: el informe sale igual, con la ruta vigente."""
    monkeypatch.delattr(vc, "ruta_para_rol")

    def falla(*a, **k):
        raise RuntimeError("módulo viejo")
    monkeypatch.setattr(va, "panel_html", falla)
    monkeypatch.setattr(va, "tabla_secretaria_html", falla)
    fuente = {cat.NIVEL_SECUNDARIA: analisis}
    for html in (inf.informe_colegio_html(fuente, COLEGIO, fecha=date(2026, 10, 8)),
                 inf.informe_secretaria_html(fuente, fecha=date(2026, 10, 8)),
                 inf.informe_una_pagina_html(analisis, "colegio", {})):
        assert ac.TITULO_PANEL not in html
        assert cat.RUTA_ATENCION[0][0] in html


# ══ Resumen de una página ═══════════════════════════════════════════════════
def _f(colegio="Todos", grado="Todos"):
    return {"nivel": cat.NIVEL_SECUNDARIA, "colegio": colegio, "grado": grado}


def test_el_recuadro_va_antes_de_las_tarjetas(analisis):
    html = inf.informe_una_pagina_html(analisis, "colegio", _f(colegio=COLEGIO))
    assert html.index(ac.TITULO_PANEL) < html.index("Lo más importante y qué hacer")
    assert ac.RUTA_PENDIENTE not in html


def test_el_resumen_de_familia_no_trae_desesperanza(analisis):
    html = inf.informe_una_pagina_html(analisis, "familia", _f())
    assert ac.ALERTAS["malestar"].nombre in html
    assert ac.ALERTAS["desesperanza"].nombre not in html


def test_un_grupo_pequeno_tambien_lleva_el_recuadro(analisis):
    html = inf.informe_una_pagina_html(analisis, "colegio", _f(grado="Noveno"))
    assert ac.CIFRAS_PEQUENAS in html and ac.ESTADOS[S] in html


def _peor_caso(a, nivel):
    grados = cat.ORDEN_GRADOS_SEC if nivel == cat.NIVEL_SECUNDARIA else cat.ORDEN_GRADOS_PRI
    filas = []
    for k, x in ac.ALERTAS.items():
        if nivel not in x.niveles:
            continue
        filas.append(_r(k, "total", "Todos", 17.0, R, n=900))
        filas += [_r(k, "Colegio", c, 40.0, P) for _, c, _ in COLEGIOS]
        filas += [_r(k, "Grado", g, 40.0, P, n=150) for g in grados]
    return dataclasses.replace(a, nivel=nivel,
                               alertas=pd.DataFrame(filas, columns=al.COLUMNAS_TABLA))


@pytest.mark.parametrize("nivel", [cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA])
def test_el_peor_caso_cabe_en_una_pagina(analisis, nivel):
    pytest.importorskip("weasyprint")
    from weasyprint import HTML
    html = inf.informe_una_pagina_html(_peor_caso(analisis, nivel), "municipio", _f())
    assert f"y {len(COLEGIOS) - va.MAX_NOMBRES_PAGINA} más" in html
    assert len(HTML(string=html).render().pages) == 1


# ══ Investigadores ══════════════════════════════════════════════════════════
from src.ui.views import estudiantes_investigador as vi  # noqa: E402


def test_alertas_csv_en_el_zip_y_sin_casos(analisis):
    assert "alertas.csv" in vi.ARCHIVOS_PAQUETE
    t = pd.read_csv(io.StringIO(vi.archivos_paquete({cat.NIVEL_SECUNDARIA: analisis})
                                ["alertas.csv"]))
    assert list(t.columns) == vi.COLUMNAS_ALERTAS_CSV
    assert "casos" not in t.columns and "nombre" not in t.columns
    assert (t["n"] >= cat.MIN_GROUP_N).all()
    assert (t.loc[t["pct"].isna(), "estado"] == ac.ESTADOS[S]).all()


def test_sensibilidad_e_items_no_van_al_zip(analisis):
    assert not [n for n in vi.ARCHIVOS_PAQUETE if "sensibilidad" in n or "items" in n]


def test_las_tablas_de_alertas_son_convertibles_a_arrow(analisis):
    import pyarrow as pa
    for t in (vi.alertas_tabla(analisis), vi.sensibilidad_tabla(analisis),
              vi.items_alertas_tabla(analisis)):
        assert len(t)
        pa.Table.from_pandas(t)


def test_la_metodologia_define_las_alertas(analisis):
    md = vi.metodologia_md({cat.NIVEL_SECUNDARIA: analisis})
    assert "Alertas de grupo" in md
    assert ac.ALERTAS["malestar"].regla in md and ac.REGLA_CIFRAS in md


def test_la_pestana_de_alertas_existe():
    assert vi.PESTANAS.index("Alertas") == 5 and len(vi.PESTANAS) == 9
