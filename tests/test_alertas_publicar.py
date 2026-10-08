"""Alertas de punta a punta sin red: pipeline → publicar → leer (spec §5.4 y §7)."""
import os
import random

import pandas as pd
import pytest

from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, lectura, pipeline, publicar, scoring, supresion
from tests.test_alertas import CONFIGURACIONES, _datos_config
from tests.test_estudiantes_comunidad import GRADO_PEQUENO, _formulario


@pytest.fixture(scope="module")
def analisis():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_SECUNDARIA, n_boot=20)


@pytest.fixture(scope="module")
def primaria():
    raw = _formulario()
    raw = raw.drop(columns=[c for c in raw.columns if c.startswith("RCADS")])
    bruto, _ = ingest.cargar(raw)
    return pipeline.analizar(scoring.puntuar(bruto), cat.NIVEL_PRIMARIA, n_boot=20)


@pytest.fixture(scope="module", params=range(len(CONFIGURACIONES)))
def config(request):
    nivel, conteos = CONFIGURACIONES[request.param]
    return nivel, pipeline.analizar(_datos_config(nivel, conteos, 5), nivel, n_boot=5)


# ══ Pipeline ════════════════════════════════════════════════════════════════
def test_el_analisis_trae_las_alertas_por_grupo(analisis):
    t = analisis.alertas
    assert list(t.columns) == al.COLUMNAS_TABLA and "casos" not in t.columns
    assert set(t["alerta"]) == {"malestar", "desesperanza"}
    assert t[t["agrupacion"] == al.TOTAL]["pct"].notna().all()
    assert not t["grupo"].astype(str).str.contains("DiosCh").any()
    assert GRADO_PEQUENO not in set(t["grupo"].astype(str))
    # cada subgrupo trae su tabla, que es la que pasa por la supresión
    celda = analisis.subgrupos[al.CRUCE]["LauV|Octavo"]
    assert list(celda.cortes_alerta.columns) == al.COLUMNAS_CORTES


def test_las_senales_individuales_quedan_solo_en_los_datos_locales(analisis):
    assert {"ALERTA_malestar", "ALERTA_desesperanza"} <= set(analisis.datos.columns)


def test_la_auditoria_de_restas_cubre_las_senales(analisis):
    assert publicar.verificar_restas({cat.NIVEL_SECUNDARIA: analisis}) == []


def test_primaria_solo_tiene_malestar(primaria):
    assert set(primaria.alertas["alerta"]) == {"malestar"}
    assert set(primaria.alertas_sensibilidad["alerta"]) == {"malestar"}


def test_sensibilidad_e_items_del_nivel(analisis):
    assert set(analisis.alertas_sensibilidad["variante"]) == set(al.VARIANTES)
    assert set(analisis.alertas_items["item"]) == {
        "SDQ5", "SDQ6", "SDQ8", "SDQ13", "SDQ19", "SDQ24",
        "RCADS1", "RCADS4", "RCADS16", "RCADS18"}


# ══ Publicar ════════════════════════════════════════════════════════════════
def _filas(a, nivel=cat.NIVEL_SECUNDARIA):
    return publicar.aplanar({nivel: a})


def test_las_alertas_se_publican_sin_casos(config):
    nivel, a = config
    filas = _filas(a, nivel)
    alertas = [f for f in filas if f["tipo"].startswith("alerta")]
    assert {f["tipo"] for f in alertas} == {"alerta", "alerta_grupo"}
    for f in alertas:
        assert not set(f["detalle"]) & set(publicar.CAMPOS_CONTEO_PROHIBIDOS)
        if f["valor"] is None:
            assert f["ic_inf"] is None and f["detalle"]["estado"] == ac.SIN_ESTADO
        else:
            # la regla, fila por fila: k = % × n queda en [3, n − 3]
            k = round(f["valor"] * f["n"] / 100)
            assert supresion.MIN_CASOS <= k <= f["n"] - supresion.MIN_CASOS
        if f["tipo"] == "alerta_grupo":
            assert f["detalle"]["n_grupo"] >= cat.MIN_GROUP_N
    publicar.verificar(filas)
    assert publicar.verificar_restas({nivel: a}) == []


def test_no_se_publican_sensibilidad_ni_items(analisis):
    tipos = {f["tipo"] for f in _filas(analisis)}
    assert not {"alerta_sensibilidad", "alerta_item"} & tipos


def test_verificar_rechaza_una_alerta_con_casos(analisis):
    fila = next(f for f in _filas(analisis) if f["tipo"] == "alerta")
    mala = dict(fila, detalle=dict(fila["detalle"], casos=5))
    with pytest.raises(publicar.PublicacionInsegura, match="casos"):
        publicar.verificar([mala])


def test_verificar_rechaza_un_estado_sin_porcentaje(analisis):
    fila = next(f for f in _filas(analisis) if f["tipo"] == "alerta_grupo")
    mala = dict(fila, valor=None, ic_inf=None, ic_sup=None,
                detalle=dict(fila["detalle"], estado=ac.PRIORIDAD))
    with pytest.raises(publicar.PublicacionInsegura, match="estado"):
        publicar.verificar([mala])


def test_verificar_restas_bloquea_una_alerta_destapada(config):
    import copy
    nivel, a = config
    for agrupacion, grupos in a.subgrupos.items():
        for grupo, s in grupos.items():
            t = s.cortes_alerta
            if len(t) and t["pct"].isna().any():
                b = copy.deepcopy(a)
                tb = b.subgrupos[agrupacion][grupo].cortes_alerta
                tb.loc[tb["pct"].isna(), "pct"] = 5.0
                assert any("alerta" in p for p in publicar.verificar_restas({nivel: b}))
                return
    pytest.skip("esta configuración no suprime ninguna alerta de subgrupo")


# ══ Supabase ════════════════════════════════════════════════════════════════
def test_la_migracion_de_alertas_y_el_esquema_dicen_lo_mismo():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "supabase", "migraciones",
                           "2026-10-07c-alertas-sin-casos.sql"), encoding="utf-8") as fh:
        migracion = fh.read()
    with open(os.path.join(raiz, "supabase", "estudiantes_schema.sql"), encoding="utf-8") as fh:
        esquema = fh.read()
    for texto in (migracion, esquema):
        assert "resultados_sin_conteos" in texto
        assert "detalle ?| ARRAY['casos', 'k_bajo', 'k_alto']" in texto
        assert "resultados_alerta_estado_con_cifra" in texto
        assert "NOT VALID" in texto
    # la misma lista de campos que rechaza `verificar`
    assert publicar.CAMPOS_CONTEO_PROHIBIDOS == ("casos", "k_bajo", "k_alto")
    assert ac.SIN_ESTADO == "sin_estado"          # el literal del CHECK y de verificar


# ══ Lectura ═════════════════════════════════════════════════════════════════
def test_las_alertas_se_leen_igual_que_se_publicaron(config):
    nivel, a = config
    filas = _filas(a, nivel)
    random.Random(5).shuffle(filas)                 # Supabase no garantiza orden
    leido = lectura._reconstruir(nivel, filas)
    pd.testing.assert_frame_equal(leido.alertas, a.alertas, check_dtype=False)
    assert leido.alertas_sensibilidad.empty and leido.alertas_items.empty


def test_el_estado_leido_se_reproduce_con_las_cifras_publicadas(config):
    nivel, a = config
    t = lectura._reconstruir(nivel, _filas(a, nivel)).alertas
    for f in t[t["agrupacion"] != al.TOTAL].to_dict("records"):
        ref = t[(t["alerta"] == f["alerta"]) & (t["agrupacion"] == al.TOTAL)].iloc[0]
        assert f["estado"] == al.estado(f["pct"], f["n"], ref["pct"], ref["n"])


def test_una_corrida_anterior_sin_alertas_se_sigue_leyendo(analisis):
    filas = [f for f in _filas(analisis) if not f["tipo"].startswith("alerta")]
    viejo = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert viejo.alertas.empty and list(viejo.alertas.columns) == al.COLUMNAS_TABLA


# ══ Alertas sin aprobar: --publicar-ya no las sube; --ensayo avisa ══════════
from tests.test_estudiantes_publicar import _Cliente  # noqa: E402


def _subidas(cli) -> list[dict]:
    return [f for p in cli.registro if p[0] == "insert" and p[1] == "resultados"
            for f in p[2]]


def _aprobar(monkeypatch, textos: bool, rutas: bool):
    from src.estudiantes import alertas_catalogo as ac
    monkeypatch.setattr(ac, "TEXTOS_APROBADOS", textos)
    monkeypatch.setattr(ac, "RUTAS_VALIDADAS", rutas)


@pytest.mark.parametrize("textos,rutas", [(False, False), (True, False), (False, True)])
def test_publicar_ya_sin_aprobacion_no_sube_alertas(analisis, monkeypatch, capsys,
                                                     textos, rutas):
    _aprobar(monkeypatch, textos, rutas)
    cli = _Cliente()
    r = publicar.publicar({cat.NIVEL_SECUNDARIA: analisis}, publicar_ya=True, cliente=cli)
    subidas = _subidas(cli)
    assert subidas and not [f for f in subidas if f["tipo"] in publicar.TIPOS_ALERTA]
    assert r["publicada"] is True and r["alertas_omitidas"] > 0
    assert publicar.AVISO_ALERTAS_NO_APROBADAS in capsys.readouterr().err


def test_publicar_ya_con_aprobacion_sube_alertas(analisis, monkeypatch, capsys):
    _aprobar(monkeypatch, True, True)
    cli = _Cliente()
    r = publicar.publicar({cat.NIVEL_SECUNDARIA: analisis}, publicar_ya=True, cliente=cli)
    tipos = {f["tipo"] for f in _subidas(cli)}
    assert {"alerta", "alerta_grupo"} <= tipos and r["alertas_omitidas"] == 0
    assert publicar.AVISO_ALERTAS_NO_APROBADAS not in capsys.readouterr().err


def test_el_ensayo_conserva_las_alertas_y_avisa(analisis, monkeypatch, capsys, tmp_path):
    import json
    _aprobar(monkeypatch, False, False)
    monkeypatch.setattr(publicar.pipeline, "cargar_y_analizar",
                        lambda base=None: ({cat.NIVEL_SECUNDARIA: analisis}, []))
    salida = tmp_path / "lote.json"
    assert publicar.main(["--ensayo", "--salida", str(salida)]) == 0
    tipos = {f["tipo"] for f in json.loads(salida.read_text())["filas"]}
    assert {"alerta", "alerta_grupo"} <= tipos
    assert publicar.AVISO_ALERTAS_NO_APROBADAS in capsys.readouterr().out


def test_la_corrida_oculta_conserva_las_alertas_y_avisa_que_no_se_abra(analisis, monkeypatch,
                                                                       capsys):
    _aprobar(monkeypatch, False, False)
    cli = _Cliente()
    r = publicar.publicar({cat.NIVEL_SECUNDARIA: analisis}, publicar_ya=False, cliente=cli)
    assert {"alerta", "alerta_grupo"} <= {f["tipo"] for f in _subidas(cli)}
    assert r["publicada"] is False and r["alertas_omitidas"] == 0
    err = capsys.readouterr().err
    assert publicar.AVISO_ALERTAS_NO_APROBADAS in err and "--publicar-ya" in err


@pytest.mark.parametrize("dano", [dict(n=None), dict(n="diez"), dict(clave=None, n=[])])
def test_una_fila_de_alerta_mal_formada_no_rompe_la_lectura(analisis, dano):
    from src.ui.views import estudiantes_comunidad as vc
    filas = publicar.aplanar({cat.NIVEL_SECUNDARIA: analisis})
    i = next(i for i, f in enumerate(filas) if f["tipo"] == "alerta_grupo")
    filas[i] = dict(filas[i], **dano)
    leido = lectura._reconstruir(cat.NIVEL_SECUNDARIA, filas)
    assert leido.alertas.empty                         # sin alertas: tarjeta de muerte
    assert "ideacion" in {t.clave for t in vc.tarjetas(leido, "colegio")}
    assert not leido.cortes.empty                      # el resto se leyó
