"""
Triangulación 360 en el despliegue público (decisión del usuario, 10 oct 2026).

El usuario decidió que la triangulación se vea en público «todo como lo ve el
equipo»: todas las pestañas, díadas, asociaciones y el ZIP, leídas de la última
corrida de triangulación PUBLICADA con la clave anon. Las corridas ocultas
siguen ocultas para el público.

  · SQL (migración 2026-10-10e y esquema completo): `es_publica` = última
    publicada de su módulo, sin excluir triangulación; la política pública de
    resultados ya no excluye el nivel 'triangulacion'.
  · Base falsa: anon lee la última corrida publicada de triangulación, nunca
    una oculta (ni de triangulación ni de otro módulo).
  · Lectura pública: cliente anon de estudiantes, solo la publicada.
  · Página pública: todas las pestañas, aviso de textos provisionales, sin
    vista previa; sin corrida, un mensaje fijo.
"""
from __future__ import annotations

import os
import sys

import pytest

from src.triangulacion import catalogo as cat
from src.triangulacion import lectura
from src.triangulacion import publicar as pub
from src.ui.views import triangulacion_investigador as vi
from tests import triangulacion_publicada_datos as datos
from tests import triangulacion_sinteticos as ts

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRACION = ("migraciones", "2026-10-10e-triangulacion-publica.sql")
FUNCION = ("CREATE OR REPLACE FUNCTION obs360_interno.es_publica(p_id bigint) RETURNS boolean\n"
           "LANGUAGE sql STABLE SECURITY DEFINER SET search_path = obs360, pg_temp AS $$")
POLITICA_CORRIDAS = ("FOR SELECT TO anon, authenticated USING "
                     "(obs360_interno.es_publica(id));")
POLITICA_RESULTADOS = ("FOR SELECT TO anon, authenticated\n"
                       "    USING (obs360_interno.es_publica(corrida_id));")
# En el esquema consolidado, desde la 2026-10-10f, hay una política por rol:
# anon solo es_publica; authenticated es_publica o cargador. Mismo alcance.
POLITICAS_ESQUEMA = (
    "FOR SELECT TO anon USING (obs360_interno.es_publica(id));",
    "USING (obs360_interno.es_publica(id) OR obs360.es_cargador());",
    "FOR SELECT TO anon USING (obs360_interno.es_publica(corrida_id));",
    "USING (obs360_interno.es_publica(corrida_id) OR obs360.es_cargador());",
)


def _sql(*partes) -> str:
    with open(os.path.join(RAIZ, "supabase", *partes), encoding="utf-8") as fh:
        return fh.read()


def _codigo(sql: str) -> str:
    return "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))


def _cuerpo_es_publica(codigo: str) -> str:
    inicio = codigo.rindex(FUNCION)
    return codigo[inicio:codigo.index("$$;", inicio)]


# ══ SQL ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("partes", [MIGRACION, ("estudiantes_schema.sql",)])
def test_es_publica_es_la_ultima_publicada_sin_excluir_triangulacion(partes):
    codigo = _codigo(_sql(*partes))
    cuerpo = _cuerpo_es_publica(codigo)
    assert "obs360_interno.es_ultima_publicada(p_id)" in cuerpo
    assert "triangulacion" not in cuerpo
    assert "ALTER FUNCTION obs360_interno.es_publica(bigint) OWNER TO postgres;" in codigo
    assert "REVOKE ALL ON FUNCTION obs360_interno.es_publica(bigint) FROM PUBLIC;" in codigo
    assert ("GRANT EXECUTE ON FUNCTION obs360_interno.es_publica(bigint)\n"
            "    TO anon, authenticated, service_role;") in codigo
    if partes == MIGRACION:
        politicas = (POLITICA_CORRIDAS, POLITICA_RESULTADOS)
    else:
        politicas = POLITICAS_ESQUEMA
    for politica in politicas:
        assert politica in codigo, politica
    assert "nivel <> 'triangulacion'" not in codigo
    assert codigo.rindex(FUNCION) < codigo.rindex(politicas[-1])
    for prohibido in ("FOR INSERT", "FOR UPDATE", "FOR DELETE", "FOR ALL"):
        assert prohibido not in codigo


def test_la_migracion_es_idempotente_y_solo_toca_lectura():
    sql = _sql(*MIGRACION)
    codigo = _codigo(sql)
    assert codigo.count("DROP POLICY IF EXISTS") == codigo.count("CREATE POLICY") == 2
    assert "CREATE OR REPLACE FUNCTION" in codigo
    assert "cargador" not in codigo
    assert "GRANT INSERT" not in codigo and "GRANT ALL" not in codigo
    assert "FUNCTION obs360.es_publica" not in codigo
    # la decisión queda escrita en la cabecera
    assert "Decisión del usuario" in sql and "10 oct 2026" in sql
    assert "ocultas" in sql


def test_la_decision_queda_en_despliegue_y_en_la_spec():
    with open(os.path.join(RAIZ, "DESPLIEGUE.md"), encoding="utf-8") as fh:
        despliegue = fh.read()
    assert "2026-10-10e-triangulacion-publica.sql" in despliegue
    with open(os.path.join(RAIZ, "docs", "superpowers", "specs",
                           "2026-10-06-cuidadores-alertas-triangulacion-design.md"),
              encoding="utf-8") as fh:
        spec = fh.read()
    seccion = spec[spec.index("### 5.6"):spec.index("## 6.")]
    assert "Decisión posterior (10 oct 2026)" in seccion
    with open(os.path.join(RAIZ, "supabase", "README.md"), encoding="utf-8") as fh:
        assert "2026-10-10e" in fh.read()


# ══ Base falsa ═════════════════════════════════════════════════════════════
def test_anon_lee_la_ultima_corrida_publicada_de_triangulacion():
    resumen, base = datos.publicado(publicar_ya=True)
    cid = resumen["corrida_id"]
    anon = base.cliente(anonimo=True).postgrest.schema("obs360")
    assert [c["id"] for c in anon.table("corridas").select("*").execute().data] == [cid]
    filas = anon.table("resultados").select("*").eq("corrida_id", cid).execute().data
    assert len(filas) == resumen["filas"] > 0
    assert {f["nivel"] for f in filas} == {"triangulacion"}


def test_anon_no_lee_corridas_ocultas_ni_de_triangulacion_ni_de_otros_modulos():
    resumen, base = datos.publicado(publicar_ya=True)
    oculta = pub.publicar(datos.analisis(), publicar_ya=False, cliente=base.cliente())
    otra = base.cliente().postgrest.schema("obs360").table("corridas").insert(
        dict(modulo="estudiantes", version_analisis="x")).execute().data[0]
    anon = base.cliente(anonimo=True).postgrest.schema("obs360")
    ids = {c["id"] for c in anon.table("corridas").select("*").execute().data}
    assert ids == {resumen["corrida_id"]}
    assert not anon.table("resultados").select("*").eq(
        "corrida_id", oculta["corrida_id"]).execute().data
    assert not anon.table("resultados").select("*").eq("corrida_id", otra["id"]).execute().data


def test_sin_corrida_publicada_anon_no_lee_nada():
    _, base = datos.publicado(publicar_ya=False)
    anon = base.cliente(anonimo=True).postgrest.schema("obs360")
    assert not anon.table("corridas").select("*").execute().data
    assert not anon.table("resultados").select("*").execute().data


# ══ Lectura pública ════════════════════════════════════════════════════════
def test_lectura_publica_usa_el_cliente_anon_de_estudiantes(monkeypatch):
    from src.estudiantes import lectura as lec_est
    _, base = datos.publicado(publicar_ya=True)
    monkeypatch.setattr(lec_est, "_cliente", lambda: base.cliente(anonimo=True))
    t = lectura.cargar(publico=True)
    assert t is not None and t.corrida["publicada"] is True
    assert lectura.id_corrida_publicada(publico=True) == t.corrida["id"]


def test_lectura_publica_sin_credenciales_da_none(monkeypatch):
    from src.estudiantes import lectura as lec_est

    def sin_credenciales():
        raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_KEY.")
    monkeypatch.setattr(lec_est, "_cliente", sin_credenciales)
    assert lectura.cliente_publico() is None
    assert lectura.cargar(publico=True) is None
    assert lectura.id_corrida_publicada(publico=True) is None


def test_lectura_publica_nunca_lee_una_corrida_oculta(monkeypatch):
    _, base = datos.publicado(publicar_ya=True)
    oculta = pub.publicar(datos.analisis(), publicar_ya=False, cliente=base.cliente())
    # aunque el cliente lo viera todo (servicio), el camino público exige publicada
    monkeypatch.setattr(lectura, "cliente_publico", lambda: base.cliente())
    assert lectura.cargar(corrida_id=oculta["corrida_id"], publico=True) is None
    assert lectura.cargar(publico=True).corrida["id"] != oculta["corrida_id"]


def test_lectura_publica_no_importa_la_vista_previa(monkeypatch):
    from tests.test_navegacion import _descargar
    _, base = datos.publicado(publicar_ya=True)
    _descargar(monkeypatch, "src.core.vista_previa")
    monkeypatch.setattr(lectura, "cliente_publico", lambda: base.cliente(anonimo=True))
    assert lectura.cargar(publico=True) is not None
    assert "src.core.vista_previa" not in sys.modules


# ══ Página pública ═════════════════════════════════════════════════════════
def _publica(monkeypatch, cliente, consulta: str = ""):
    from streamlit.testing.v1 import AppTest
    from src.ui import triangulacion as pag
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    monkeypatch.setattr(lectura, "cliente_publico", cliente)
    pag._leer_publico.clear()
    at = AppTest.from_string(
        "from src.ui.triangulacion import render_publico\nrender_publico()\n",
        default_timeout=180)
    if consulta:
        at.query_params["colegio"] = consulta
    return at


def _texto(at) -> str:
    from tests.test_triangulacion_pagina import _texto as texto
    return texto(at)


def test_la_pagina_publica_muestra_todas_las_pestanas(monkeypatch):
    resumen, base = datos.publicado(publicar_ya=True)
    pub.publicar(datos.analisis(), publicar_ya=False, cliente=base.cliente())  # oculta
    at = _publica(monkeypatch, lambda: base.cliente(anonimo=True)).run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS
    assert not at.toggle                                   # sin vista previa
    texto = _texto(at)
    assert cat.AVISO_TEXTOS in texto
    from src.triangulacion import hallazgos_catalogo as hc
    subs = [s.value for s in at.subheader]
    assert [hc.TITULO_PERFIL, hc.TITULO_PATRONES, hc.TITULO_TENSION, hc.TITULO_HIPOTESIS] == \
        [s for s in subs if s in (hc.TITULO_PERFIL, hc.TITULO_PATRONES, hc.TITULO_TENSION,
                                  hc.TITULO_HIPOTESIS)]
    assert cat.TITULO_PUBLICO in " ".join(t.value for t in at.title)
    assert "solo investigadores" not in " ".join(t.value for t in at.title)
    assert f"corrida {resumen['corrida_id']}" in texto
    assert any(lectura.AVISO_PUBLICO in i.value for i in at.info)
    for prohibido in ts.textos_prohibidos():
        assert prohibido not in texto
    assert at.get("download_button")                       # el ZIP de agregados
    at.selectbox(key="tri_ba").set_value("SDQ_Emo").run()
    assert not at.exception


def test_la_pagina_publica_sin_corrida_da_el_mensaje_fijo(monkeypatch):
    _, base = datos.publicado(publicar_ya=False)
    at = _publica(monkeypatch, lambda: base.cliente(anonimo=True)).run()
    assert not at.exception
    assert any(cat.AVISO_PUBLICO_SIN_CORRIDA in i.value for i in at.info)
    assert not at.tabs
    assert "aún no hay una corrida de triangulación publicada" in cat.AVISO_PUBLICO_SIN_CORRIDA


def test_la_pagina_publica_sin_credenciales_no_falla(monkeypatch):
    at = _publica(monkeypatch, lambda: None).run()
    assert not at.exception
    assert any(cat.AVISO_PUBLICO_SIN_CORRIDA in i.value for i in at.info)


def test_la_pagina_publica_si_la_lectura_lanza_no_falla(monkeypatch):
    def roto():
        raise ConnectionError("https://secreto.invalid?apikey=xyz")
    at = _publica(monkeypatch, roto).run()
    assert not at.exception
    assert "secreto.invalid" not in _texto(at)
    assert any(cat.AVISO_PUBLICO_SIN_CORRIDA in i.value for i in at.info)


def test_el_parametro_colegio_no_rompe_la_pagina(monkeypatch):
    _, base = datos.publicado(publicar_ya=True)
    at = _publica(monkeypatch, lambda: base.cliente(anonimo=True), consulta="LauV").run()
    assert not at.exception
    assert [t.label for t in at.tabs] == vi.PESTANAS


def test_la_pagina_publica_no_importa_lo_local(monkeypatch):
    from tests.test_navegacion import _descargar
    _, base = datos.publicado(publicar_ya=True)
    prohibidos = ("src.triangulacion.fuentes", "src.triangulacion.pipeline",
                  "src.triangulacion.publicar", "src.triangulacion.diadas",
                  "src.triangulacion.capa1", "src.core.vista_previa", "src.core.seudonimo")
    for m in prohibidos:
        _descargar(monkeypatch, m)
    at = _publica(monkeypatch, lambda: base.cliente(anonimo=True)).run()
    assert not at.exception
    for m in prohibidos:
        assert m not in sys.modules, m
