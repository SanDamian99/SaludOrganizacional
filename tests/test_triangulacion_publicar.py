"""
Triangulación 360 · publicación privada en Supabase (sin red).

  · SQL: la migración 2026-10-10b y el esquema completo dicen lo mismo; el
    público nunca lee triangulación.
  · Base falsa: anon no lee filas de triangulación ni de una corrida publicada;
    el usuario de carga sí; Estudiantes y Cuidadores siguen igual.
  · Lote: solo agregados, nivel/modulo «triangulacion», n ≥ 10 en cada fila,
    ningún identificador, teléfono ni columna prohibida, ninguna díada.
  · Orden de publicación: oculta → resultados → abrir → despublicar las otras
    de triangulación (no las de otros módulos).
"""
import json
import os
import re

import pytest

from src.triangulacion import catalogo as cat
from src.triangulacion import exportar as ex
from src.triangulacion import publicar as pub
from tests import cuidadores_comunidad_datos as datos_cuid
from tests import triangulacion_publicada_datos as datos
from tests.supabase_falso import BaseFalsa, ViolacionCheck

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRACION = ("migraciones", "2026-10-10b-triangulacion-privada.sql")
SEUDONIMO = re.compile(r"(?<![0-9A-Za-z])[CEN][0-9a-f]{8}(?![0-9a-f])")


def _sql(*partes) -> str:
    with open(os.path.join(RAIZ, "supabase", *partes), encoding="utf-8") as fh:
        return fh.read()


def _codigo(sql: str) -> str:
    return "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))


# ══ SQL ════════════════════════════════════════════════════════════════════
FUNCION = ("CREATE OR REPLACE FUNCTION obs360_interno.es_publica(p_id bigint) RETURNS boolean\n"
           "LANGUAGE sql STABLE SECURITY DEFINER SET search_path = obs360, pg_temp AS $$")
POLITICA_CORRIDAS = ("FOR SELECT TO anon, authenticated USING "
                     "(obs360_interno.es_publica(id));")
POLITICA_RESULTADOS = ("USING (obs360_interno.es_publica(corrida_id) AND nivel <> "
                       "'triangulacion');")
NIVELES = "CHECK (nivel IN ('secundaria', 'primaria', 'cuidadores', 'triangulacion'))"


@pytest.mark.parametrize("partes", [MIGRACION, ("estudiantes_schema.sql",)])
def test_el_sql_excluye_la_triangulacion_de_lo_publico(partes):
    sql = _sql(*partes)
    codigo = _codigo(sql)
    assert NIVELES in codigo
    assert FUNCION in codigo
    assert "lower(btrim(m.modulo)) <> 'triangulacion'" in codigo
    assert "AND obs360_interno.es_ultima_publicada(p_id)" in codigo
    assert "ALTER FUNCTION obs360_interno.es_publica(bigint) OWNER TO postgres;" in codigo
    assert "REVOKE ALL ON FUNCTION obs360_interno.es_publica(bigint) FROM PUBLIC;" in codigo
    assert POLITICA_CORRIDAS in codigo and POLITICA_RESULTADOS in codigo
    # las políticas públicas ya no usan es_ultima_publicada directamente
    assert "USING (obs360_interno.es_ultima_publicada(" not in codigo
    # la función va antes de las políticas que la usan
    assert codigo.index(FUNCION) < codigo.index(POLITICA_CORRIDAS)
    for prohibido in ("FOR INSERT", "FOR UPDATE", "FOR DELETE", "FOR ALL"):
        assert prohibido not in codigo


def test_la_migracion_solo_toca_lo_suyo_y_es_idempotente():
    codigo = _codigo(_sql(*MIGRACION))
    assert "DROP CONSTRAINT IF EXISTS resultados_nivel_valido" in codigo
    assert codigo.count("DROP POLICY IF EXISTS") == codigo.count("CREATE POLICY") == 2
    assert "CREATE OR REPLACE FUNCTION" in codigo and "CREATE SCHEMA IF NOT EXISTS" in codigo
    assert "cargador" not in codigo                     # sus políticas no cambian
    assert "GRANT INSERT" not in codigo and "GRANT ALL" not in codigo
    # no se expone por la API REST: vive en obs360_interno, no en obs360
    assert "FUNCTION obs360.es_publica" not in codigo


# ══ Base falsa: quién lee qué ═════════════════════════════════════════════
def test_anon_no_lee_triangulacion_ni_publicada_y_el_cargador_si():
    resumen, base = datos.publicado(publicar_ya=True)
    cid = resumen["corrida_id"]
    assert base.corrida(cid)["publicada"] is True
    anon = base.cliente(anonimo=True).postgrest.schema("obs360")
    assert not anon.table("corridas").select("*").eq("id", cid).execute().data
    assert not anon.table("resultados").select("*").eq("corrida_id", cid).execute().data
    assert not [f for f in anon.table("resultados").select("*").execute().data
                if f["nivel"] == pub.NIVEL]
    carg = base.cliente(cargador=True).postgrest.schema("obs360")
    assert carg.table("corridas").select("*").eq("id", cid).execute().data
    filas = carg.table("resultados").select("*").eq("corrida_id", cid).execute().data
    assert len(filas) == resumen["filas"] > 0


def test_anon_no_lee_una_fila_de_triangulacion_ni_dentro_de_otro_modulo():
    base = BaseFalsa()
    corrida = base.cliente().postgrest.schema("obs360").table("corridas").insert(
        dict(modulo="estudiantes", version_analisis="x")).execute().data[0]
    tabla = base.cliente().postgrest.schema("obs360").table("resultados")
    tabla.insert([dict(corrida_id=corrida["id"], nivel="triangulacion", tipo="tri_x",
                       clave="x", n=50, detalle={}),
                  dict(corrida_id=corrida["id"], nivel="secundaria", tipo="descriptivo",
                       clave="SDQ_Total", n=50, detalle={})]).execute()
    base.corrida(corrida["id"])["publicada"] = True
    anon = base.cliente(anonimo=True).postgrest.schema("obs360")
    niveles = {f["nivel"] for f in anon.table("resultados").select("*").execute().data}
    assert niveles == {"secundaria"}


def test_estudiantes_y_cuidadores_siguen_publicos_igual():
    _, base = datos_cuid.publicado()
    from src.cuidadores import lectura
    publicada = lectura.id_corrida_vigente(base.cliente(anonimo=True))
    assert publicada is not None
    pub.publicar(datos.analisis(), publicar_ya=True, cliente=base.cliente())
    anon = base.cliente(anonimo=True).postgrest.schema("obs360")
    assert {c["id"] for c in anon.table("corridas").select("*").execute().data} == {publicada}
    assert lectura.id_corrida_vigente(base.cliente(anonimo=True)) == publicada
    assert base.corrida(publicada)["publicada"] is True     # no la despublicó


def test_la_base_falsa_admite_el_nivel_y_rechaza_n_pequeno():
    base = BaseFalsa()
    tabla = base.cliente().postgrest.schema("obs360").table("resultados")
    tabla.insert(dict(corrida_id=1, nivel="triangulacion", tipo="tri_x", clave="x", n=10,
                      detalle={})).execute()
    with pytest.raises(ViolacionCheck):
        tabla.insert(dict(corrida_id=1, nivel="triangulacion", tipo="tri_x", clave="x", n=9,
                          detalle={})).execute()


# ══ Lote ═══════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def filas():
    return pub.aplanar(datos.analisis())


def test_el_lote_es_de_triangulacion_y_pasa_las_guardas(filas):
    assert filas
    assert {f["nivel"] for f in filas} == {pub.NIVEL} == {"triangulacion"}
    assert all(f["tipo"].startswith("tri_") for f in filas)
    assert min(f["n"] for f in filas) >= cat.MIN_GROUP_N
    pub.verificar(filas)


def test_el_lote_trae_cada_tabla(filas):
    tipos = {f["tipo"] for f in filas}
    assert {pub.TIPO_META, "tri_capa1_diferencias", "tri_capa1_por_grado",
            "tri_diadas_acuerdo", "tri_diadas_bland_altman"} <= tipos
    assert sum(f["tipo"] == pub.TIPO_META for f in filas) == 1


def test_ninguna_fila_lleva_identificadores_ni_prohibidas(filas):
    from tests import triangulacion_sinteticos as ts
    texto = json.dumps(filas, ensure_ascii=False, default=str)
    assert not SEUDONIMO.search(texto)
    for prohibido in ts.textos_prohibidos():
        assert prohibido not in texto
    claves = set()

    def recorrer(v):
        if isinstance(v, dict):
            for k, x in v.items():
                claves.add(k)
                recorrer(x)
        elif isinstance(v, list):
            for x in v:
                recorrer(x)
    recorrer(filas)
    assert not set(ex.PROHIBIDAS) & claves
    assert not {c.lower() for c in ex.PROHIBIDAS} & {c.lower() for c in claves}


def test_todo_conteo_en_el_detalle_es_de_10_o_mas(filas):
    for f in filas:
        for nombre, valor in pub.conteos_del_detalle(f):
            assert valor is None or valor >= cat.MIN_GROUP_N, (f["tipo"], nombre, valor)


def test_bland_altman_solo_grupos(filas):
    ba = [f for f in filas if f["tipo"] == "tri_diadas_bland_altman"]
    assert ba
    por_sub = {}
    for f in ba:
        por_sub.setdefault(f["clave"], []).append(f)
        assert f["n"] >= cat.MIN_GROUP_N
    assert all(len(v) <= cat.MAX_BINES_BA for v in por_sub.values())


def test_el_lote_no_sube_diadas_ni_filas_de_personas(filas):
    t = datos.analisis()
    assert len(filas) < 300
    personas = sum(v for v in t.actores.values() if isinstance(v, int))
    assert len(filas) < personas / 2


@pytest.mark.parametrize("dano", [
    lambda f: f.update(n=9),
    lambda f: f["detalle"].setdefault("fila", {}).update(nota="C0a1b2c3d"),
    lambda f: f["detalle"].update(familia="x"),
    lambda f: f["detalle"].update(ID_cuidador="x"),
    lambda f: f["detalle"].update(telefono_x="3001234567"),
    lambda f: f.update(nivel="cuidadores"),
    lambda f: f["detalle"].setdefault("fila", {}).update(familias=4),
    lambda f: f["detalle"].update(casos=12),
])
def test_verificar_rechaza_el_lote_entero(filas, dano):
    import copy
    malas = copy.deepcopy(filas)
    dano(next(f for f in malas if f["tipo"] == "tri_capa1_diferencias"))
    with pytest.raises(pub.PublicacionInsegura):
        pub.verificar(malas)


# ══ Publicar: orden y efectos ═════════════════════════════════════════════
def test_sin_publicar_ya_la_corrida_queda_oculta():
    resumen, base = datos.publicado(publicar_ya=False)
    c = base.corrida(resumen["corrida_id"])
    assert c["modulo"] == pub.MODULO == "triangulacion" and c["publicada"] is False
    assert resumen["publicada"] is False


def test_publicar_ya_despublica_solo_las_otras_de_triangulacion():
    _, base = datos_cuid.publicado()
    cuid = [c for c in base.tablas["corridas"] if c["publicada"]]
    vieja = pub.publicar(datos.analisis(), publicar_ya=True, cliente=base.cliente())
    nueva = pub.publicar(datos.analisis(), publicar_ya=True, cliente=base.cliente())
    assert base.corrida(vieja["corrida_id"])["publicada"] is False
    assert base.corrida(nueva["corrida_id"])["publicada"] is True
    assert nueva["otras_corridas_despublicadas"] is True
    assert all(base.corrida(c["id"])["publicada"] for c in cuid)


def test_si_falla_una_fila_no_queda_nada(monkeypatch):
    base = BaseFalsa()
    original = pub.aplanar

    def con_mala(t):
        filas = original(t)
        filas[-1] = dict(filas[-1], nivel="otro")     # el CHECK de la base la rechaza
        return filas
    monkeypatch.setattr(pub, "aplanar", con_mala)
    monkeypatch.setattr(pub, "verificar", lambda filas: None)
    with pytest.raises(ViolacionCheck):
        pub.publicar(datos.analisis(), cliente=base.cliente())
    assert base.tablas["corridas"] == [] and base.tablas["resultados"] == []


def test_publicar_rechaza_un_lote_inseguro_sin_tocar_la_base(monkeypatch):
    base = BaseFalsa()
    original = pub.aplanar
    monkeypatch.setattr(pub, "aplanar",
                        lambda t: [dict(f, n=3) for f in original(t)])
    with pytest.raises(pub.PublicacionInsegura):
        pub.publicar(datos.analisis(), cliente=base.cliente())
    assert base.tablas["corridas"] == []


# ══ CLI ════════════════════════════════════════════════════════════════════
def test_ensayo_escribe_el_json_y_no_toca_la_red(monkeypatch, tmp_path, capsys):
    from src.triangulacion import pipeline
    monkeypatch.setattr(pipeline, "cargar_y_analizar", lambda *a, **k: datos.analisis())

    def sin_red(*a, **k):
        raise AssertionError("el ensayo no se conecta")
    monkeypatch.setattr(pub.pub_est, "_cliente", sin_red)
    salida = tmp_path / "lote.json"
    assert pub.main(["--ensayo", "--salida", str(salida)]) == 0
    lote = json.loads(salida.read_text(encoding="utf-8"))
    assert lote["modulo"] == "triangulacion" and lote["filas"]
    out = capsys.readouterr().out
    assert "n mínimo" in out and "Nada se subió" in out
    assert not SEUDONIMO.search(out)


def test_cli_publica_oculta_por_defecto(monkeypatch, capsys):
    from src.triangulacion import pipeline
    base = BaseFalsa()
    monkeypatch.setattr(pipeline, "cargar_y_analizar", lambda *a, **k: datos.analisis())
    monkeypatch.setattr(pub.pub_est, "_cliente", lambda *a, **k: base.cliente())
    assert pub.main(["--notas", "n"]) == 0
    assert [c["publicada"] for c in base.tablas["corridas"]] == [False]
    assert pub.main(["--publicar-ya"]) == 0
    assert [c["publicada"] for c in base.tablas["corridas"]] == [False, True]


def test_cli_sin_clave_sale_con_1(monkeypatch, capsys):
    from src.core.seudonimo import ClaveAusente
    from src.triangulacion import pipeline

    def sin_clave(*a, **k):
        raise ClaveAusente("falta la clave")
    monkeypatch.setattr(pipeline, "cargar_y_analizar", sin_clave)
    assert pub.main(["--ensayo"]) == 1
