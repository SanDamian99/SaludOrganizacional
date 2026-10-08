"""Cuidadores 360 · publicación en Supabase (fase 4b): solo agregados, auditados."""
import json
import re

import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.cuidadores import publicar
from src.estudiantes import publicar as pub_est
from tests import cuidadores_comunidad_datos as datos
from tests import cuidadores_sinteticos as cs
from tests.supabase_falso import BaseFalsa, _check_resultado


@pytest.fixture(scope="module")
def ac():
    return datos.preparado()


@pytest.fixture(scope="module")
def filas(ac):
    return publicar.aplanar(ac)


def test_todo_es_del_nivel_cuidadores_con_su_marco(filas):
    assert filas
    assert {f["nivel"] for f in filas} == {"cuidadores"}
    assert {f["detalle"]["marco"] for f in filas} == set(cat.NOMBRES_MARCO)


def test_pasa_las_guardas_de_estudiantes_y_las_propias(filas):
    pub_est.verificar(filas)
    publicar.verificar(filas)


def test_cumple_los_check_de_la_base(filas):
    for f in filas:
        _check_resultado(f)


def test_sin_nombres_telefonos_identificadores_ni_casos(filas):
    texto = json.dumps(filas, ensure_ascii=False, default=str)
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in texto
    assert not re.search(r'"[ECN][0-9a-f]{8}"', texto)
    for f in filas:
        assert not set(f["detalle"]) & {"casos", "k_bajo", "k_alto"}


def test_nada_por_ola(filas):
    for f in filas:
        assert "ola" not in (f["detalle"].get("muestra") or {})
        assert "por_ola" not in (f["detalle"].get("ingesta") or {})
        assert f["agrupacion"] not in ("Ola",)


def test_la_autolesion_solo_en_el_total(filas):
    propias = [f for f in filas if f["clave"] in ("EPDS_Autolesion", cat.AUTOLESION)]
    assert propias and all(f["agrupacion"] == "total" for f in propias)


def test_sin_comparacion_por_sexo_ni_items_locales(filas):
    assert not [f for f in filas if f["agrupacion"] == "Sexo"]
    assert not [f for f in filas if f["tipo"] in ("item", "item_grupo")]


def test_cada_grupo_publicado_es_de_la_base(ac, filas):
    for f in filas:
        if f["tipo"] in ("corte_grupo", "banda_grupo"):
            marco = ac.marcos[f["detalle"]["marco"]]
            assert f["grupo"] in marco.subgrupos[f["agrupacion"]]


def test_la_auditoria_pasa(ac):
    assert publicar.verificar_restas(ac) == []


def test_no_se_publica_la_vista_de_una_ola(ac):
    import copy
    otra = copy.copy(ac)
    otra.ola = "2026"
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.aplanar(otra)


def test_publicar_ya_abre_la_corrida_y_cierra_solo_las_de_cuidadores(ac):
    base = BaseFalsa()
    vieja_est = base.cliente().postgrest.schema("obs360").table("corridas").insert(
        dict(modulo="estudiantes", version_analisis="x", publicada=True)).execute().data[0]
    primera = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    segunda = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert base.corrida(segunda["corrida_id"])["publicada"] is True
    assert base.corrida(primera["corrida_id"])["publicada"] is False
    assert base.corrida(vieja_est["id"])["publicada"] is True       # estudiantes intacto
    assert base.corrida(segunda["corrida_id"])["modulo"] == "cuidadores"


def test_sin_publicar_ya_queda_oculta(ac):
    base = BaseFalsa()
    r = publicar.publicar(ac, publicar_ya=False, cliente=base.cliente())
    assert base.corrida(r["corrida_id"])["publicada"] is False


def test_sin_aprobacion_publicar_ya_omite_las_senales(ac, monkeypatch):
    monkeypatch.setattr(cc, "TEXTOS_APROBADOS", False)
    base = BaseFalsa()
    r = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert r["alertas_omitidas"] > 0
    assert not [f for f in base.tablas["resultados"] if f["tipo"].startswith("alerta")]


def test_con_aprobacion_las_senales_se_publican(ac, monkeypatch):
    monkeypatch.setattr(cc, "TEXTOS_APROBADOS", True)
    monkeypatch.setattr(cc, "RUTAS_VALIDADAS", True)
    base = BaseFalsa()
    r = publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert r["alertas_omitidas"] == 0
    assert [f for f in base.tablas["resultados"] if f["tipo"] == "alerta_grupo"]


def test_una_auditoria_fallida_no_toca_la_base(ac, monkeypatch):
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["cuidador · algo delata"])
    base = BaseFalsa()
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert base.tablas == {"corridas": [], "resultados": []}


def test_si_falla_el_insert_la_corrida_no_se_abre(ac):
    base = BaseFalsa()
    original = base.tablas

    class Rota(dict):
        def __getitem__(self, k):
            if k == "resultados":
                raise RuntimeError("red caída")
            return dict.__getitem__(self, k)
    base.tablas = Rota(original)
    with pytest.raises(RuntimeError):
        publicar.publicar(ac, publicar_ya=True, cliente=base.cliente())
    assert not any(c["publicada"] for c in base.tablas["corridas"])


def _main(monkeypatch, tmp_path, *args):
    archivo = cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    monkeypatch.setenv("OBS360_CLAVE_HMAC", cs.CLAVE_PRUEBA)
    salida = tmp_path / "lote.json"
    codigo = publicar.main(["--ensayo", "--archivo", archivo, "--salida", str(salida), *args])
    return codigo, salida


def test_ensayo_sin_hallazgos_sale_con_0_y_solo_agregados(monkeypatch, tmp_path, capsys):
    codigo, salida = _main(monkeypatch, tmp_path)
    assert codigo == 0
    texto = salida.read_text(encoding="utf-8") + capsys.readouterr().out
    for prohibido in cs.textos_prohibidos():
        assert prohibido not in texto
    assert not re.search(r"\b[CN][0-9a-f]{8}\b", texto)
    assert json.loads(salida.read_text(encoding="utf-8"))["modulo"] == "cuidadores"


def test_ensayo_con_hallazgos_escribe_el_json_y_sale_con_2(monkeypatch, tmp_path):
    monkeypatch.setattr(publicar, "verificar_restas", lambda a: ["cuidador · algo delata"])
    codigo, salida = _main(monkeypatch, tmp_path)
    assert codigo == 2 and salida.exists()


def test_sin_clave_no_publica(monkeypatch, tmp_path):
    archivo = cs.escribir(tmp_path / "cuidadores" / "Cuidando al Cuidador (respuestas).xlsx")
    monkeypatch.delenv("OBS360_CLAVE_HMAC", raising=False)
    monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    assert publicar.main(["--ensayo", "--archivo", archivo,
                          "--salida", str(tmp_path / "x.json")]) == 1
    assert not (tmp_path / "x.json").exists()
