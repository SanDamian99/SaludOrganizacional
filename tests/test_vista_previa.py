"""Vista previa para el equipo: la corrida oculta, solo en el despliegue privado.

Sin red: la base es `tests/supabase_falso.BaseFalsa`, con sus tres roles
(servicio, anónimo y el usuario de carga de la migración 2026-10-10).
"""
import logging
import os

import pytest

from src.core import vista_previa as vp
from tests import cuidadores_comunidad_datos as datos
from tests.supabase_falso import CREDENCIALES_CARGADOR, BaseFalsa

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL, CLAVE = CREDENCIALES_CARGADOR["email"], CREDENCIALES_CARGADOR["password"]


# ══ SQL: la migración y el esquema dicen lo mismo ═════════════════════════
def _sql(*partes) -> str:
    with open(os.path.join(RAIZ, "supabase", *partes), encoding="utf-8") as fh:
        return fh.read()


POLITICAS = (
    'CREATE POLICY "cargador lee todas las corridas" ON obs360.corridas\n'
    "    FOR SELECT TO authenticated USING (obs360.es_cargador());",
    'CREATE POLICY "cargador lee todos los resultados" ON obs360.resultados\n'
    "    FOR SELECT TO authenticated USING (obs360.es_cargador());",
)


def test_la_migracion_da_lectura_al_cargador_y_nada_mas():
    sql = _sql("migraciones", "2026-10-10-vista-previa-cargador.sql")
    for politica in POLITICAS:
        assert politica in sql
    assert 'DROP POLICY IF EXISTS "cargador lee todas las corridas"' in sql
    assert 'DROP POLICY IF EXISTS "cargador lee todos los resultados"' in sql
    codigo = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    for prohibido in ("FOR INSERT", "FOR UPDATE", "FOR DELETE", "FOR ALL", "GRANT",
                      "lectura publica", "TO anon"):
        assert prohibido not in codigo, prohibido


def test_el_esquema_incluye_la_migracion_sin_tocar_la_politica_publica():
    sql = _sql("estudiantes_schema.sql")
    for politica in POLITICAS:
        assert politica in sql
    # La política pública: la última publicada de cada módulo, nunca triangulación
    # (es_publica = es_ultima_publicada y módulo distinto de triangulación, 2026-10-10b).
    assert ("FOR SELECT TO anon, authenticated USING "
            "(obs360_interno.es_publica(id));") in sql
    assert ("USING (obs360_interno.es_publica(corrida_id) AND nivel <> 'triangulacion');"
            in sql)
    assert "AND obs360_interno.es_ultima_publicada(p_id)" in sql
    # la función se define antes de las políticas que la usan
    assert sql.index("FUNCTION obs360.es_cargador()") < sql.index(POLITICAS[0])


# ══ La base: anónimo solo lo publicado, cargador todo ═════════════════════
def _base_cuidadores():
    """(base, id publicada, id oculta más nueva con sus filas de señales)."""
    from src.cuidadores import lectura, publicar
    _, base = datos.publicado()
    publicada = lectura.id_corrida_vigente(base.cliente(anonimo=True))
    oculta = publicar.publicar(datos.preparado(), publicar_ya=False,
                               cliente=base.cliente())["corrida_id"]
    return base, publicada, oculta


def test_el_anonimo_solo_ve_la_publicada_y_el_cargador_ve_la_oculta():
    base, publicada, oculta = _base_cuidadores()
    anon = base.cliente(anonimo=True).postgrest.schema("obs360")
    ids = {c["id"] for c in anon.table("corridas").select("*").execute().data}
    assert ids == {publicada}
    assert not anon.table("resultados").select("*").eq("corrida_id", oculta).execute().data
    carg = base.cliente(cargador=True).postgrest.schema("obs360")
    assert {publicada, oculta} <= {c["id"] for c in carg.table("corridas").select("*").execute().data}
    assert carg.table("resultados").select("*").eq("corrida_id", oculta).execute().data


def test_el_cargador_no_escribe():
    base, _, oculta = _base_cuidadores()
    with pytest.raises(PermissionError):
        (base.cliente(cargador=True).postgrest.schema("obs360").table("corridas")
         .update({"publicada": True}).eq("id", oculta).execute())
    assert base.corrida(oculta)["publicada"] is False


# ══ Lectores: el camino normal no cambia; con id, la corrida pedida ═══════
def test_cuidadores_el_camino_normal_sigue_leyendo_la_publicada_con_el_cargador():
    from src.cuidadores import lectura
    base, publicada, _ = _base_cuidadores()
    _, corrida = lectura.cargar_desde_supabase(base.cliente(cargador=True))
    assert corrida["id"] == publicada


def test_cuidadores_la_corrida_en_revision_se_lee_con_sus_senales():
    from src.cuidadores import lectura
    from src.ui.views import cuidadores_comunidad as vc
    base, _, oculta = _base_cuidadores()
    ac, corrida = lectura.cargar_desde_supabase(base.cliente(cargador=True), corrida_id=oculta)
    assert corrida["id"] == oculta and corrida["publicada"] is False
    assert vc.tiene_senales(ac)


def test_cuidadores_el_anonimo_no_lee_la_oculta_aunque_la_pida():
    from src.cuidadores import lectura
    base, _, oculta = _base_cuidadores()
    assert lectura.cargar_desde_supabase(base.cliente(anonimo=True), corrida_id=oculta) == \
        (None, None)


@pytest.fixture(scope="module")
def analisis_est():
    from src.estudiantes import catalog as cat
    from src.estudiantes import ingest, pipeline, scoring
    from tests.test_estudiantes_comunidad import _formulario
    bruto, _ = ingest.cargar(_formulario())
    return {cat.NIVEL_SECUNDARIA: pipeline.analizar(scoring.puntuar(bruto),
                                                    cat.NIVEL_SECUNDARIA, n_boot=20)}


def base_estudiantes(analisis):
    """(base, id publicada sin alertas, id oculta con alertas), con textos sin aprobar."""
    from src.estudiantes import publicar
    base = BaseFalsa()
    publicada = publicar.publicar(analisis, publicar_ya=True, cliente=base.cliente())
    oculta = publicar.publicar(analisis, publicar_ya=False, cliente=base.cliente())
    assert publicada["alertas_omitidas"] > 0 and oculta["alertas_omitidas"] == 0
    return base, publicada["corrida_id"], oculta["corrida_id"]


def test_estudiantes_el_camino_normal_exige_publicada(analisis_est, monkeypatch):
    from src.estudiantes import lectura
    base, publicada, _ = base_estudiantes(analisis_est)
    # aunque el cliente vea todo (servicio o cargador), se lee la publicada
    for cli in (base.cliente(), base.cliente(cargador=True)):
        monkeypatch.setattr(lectura, "_cliente", lambda cli=cli: cli)
        assert lectura.id_corrida_vigente() == publicada
        assert lectura.cargar_desde_supabase()[2]["id"] == publicada


def test_estudiantes_la_corrida_en_revision_trae_las_alertas(analisis_est):
    from src.estudiantes import lectura
    base, publicada, oculta = base_estudiantes(analisis_est)
    analisis, _, corrida = lectura.cargar_desde_supabase(base.cliente(cargador=True),
                                                        corrida_id=oculta)
    assert corrida["id"] == oculta
    assert not next(iter(analisis.values())).alertas.empty
    publicado, _, corrida = lectura.cargar_desde_supabase(base.cliente(anonimo=True))
    assert corrida["id"] == publicada
    assert next(iter(publicado.values())).alertas.empty
    assert lectura.cargar_desde_supabase(base.cliente(anonimo=True), corrida_id=oculta)[0] == {}


# ══ vista_previa: disponible ══════════════════════════════════════════════
def _credenciales(monkeypatch, email=EMAIL, clave=CLAVE):
    monkeypatch.setattr(vp, "credenciales", lambda: (email, clave))
    monkeypatch.setenv("OBS360_SUPABASE_URL", "https://falso.invalid")
    monkeypatch.setenv("OBS360_SUPABASE_KEY", "clave-anon-falsa")


@pytest.mark.parametrize("modo,esperado", [("investigador", True), ("completo", True),
                                            ("comunidad", False), ("raro", False)])
def test_disponible_solo_en_los_modos_privados(monkeypatch, modo, esperado):
    _credenciales(monkeypatch)
    monkeypatch.setenv("OBS360_MODO", modo)
    assert vp.disponible() is esperado


def test_sin_credenciales_de_carga_no_hay_vista_previa(monkeypatch):
    _credenciales(monkeypatch, None, None)
    monkeypatch.setenv("OBS360_MODO", "investigador")
    assert vp.disponible() is False and vp.activa() is False


def test_las_credenciales_son_las_del_almacen(monkeypatch):
    from src.data import almacen
    monkeypatch.setattr(almacen, "credenciales_carga", lambda: ("a@b.c", "x"))
    assert vp.credenciales() == ("a@b.c", "x")


# ══ vista_previa: cliente autenticado ═════════════════════════════════════
def _fabrica(monkeypatch, base):
    creados = []

    def crear(url, key):
        cli = base.cliente_sin_sesion()
        creados.append((url, key))
        return cli
    monkeypatch.setattr(vp, "_crear_cliente", crear)
    return creados


def test_el_cliente_autenticado_ve_la_oculta_y_se_reutiliza(monkeypatch):
    base, _, oculta = _base_cuidadores()
    _credenciales(monkeypatch)
    monkeypatch.setenv("OBS360_MODO", "investigador")
    creados = _fabrica(monkeypatch, base)
    cli = vp.cliente_autenticado()
    assert cli is not None and vp.cliente_autenticado() is cli
    assert len(creados) == 1 and base.inicios_de_sesion == 1
    assert creados[0] == ("https://falso.invalid", "clave-anon-falsa")
    assert vp.corrida_en_revision("cuidadores", cli) == oculta


def test_el_cliente_se_renueva_cuando_caduca(monkeypatch):
    base, _, _ = _base_cuidadores()
    _credenciales(monkeypatch)
    monkeypatch.setenv("OBS360_MODO", "investigador")
    _fabrica(monkeypatch, base)
    reloj = [1000.0]
    monkeypatch.setattr(vp, "_ahora", lambda: reloj[0])
    vp.cliente_autenticado()
    reloj[0] += vp.TTL_CLIENTE + 1
    vp.cliente_autenticado()
    assert base.inicios_de_sesion == 2


def test_un_inicio_de_sesion_fallido_no_vuelca_secretos(monkeypatch, caplog):
    base, _, _ = _base_cuidadores()
    _credenciales(monkeypatch, EMAIL, "clave-equivocada-XYZ")
    monkeypatch.setenv("OBS360_MODO", "investigador")
    _fabrica(monkeypatch, base)
    with caplog.at_level(logging.DEBUG):
        assert vp.cliente_autenticado() is None
        assert vp.revision("cuidadores") is None
    assert caplog.records                               # se registró el fallo…
    texto = caplog.text
    for secreto in ("clave-equivocada-XYZ", EMAIL, "clave-anon-falsa"):
        assert secreto not in texto                     # …sin el secreto


def test_los_fallos_tragados_dicen_donde_y_que_tipo(monkeypatch, caplog):
    """En producción solo hay registros: el paso y el tipo bastan, sin el mensaje."""
    base, _, _ = _base_cuidadores()
    _credenciales(monkeypatch, EMAIL, "clave-equivocada-XYZ")
    monkeypatch.setenv("OBS360_MODO", "investigador")
    _fabrica(monkeypatch, base)
    with caplog.at_level(logging.WARNING):
        assert vp.cliente_autenticado() is None
    assert "iniciar sesión del usuario de carga" in caplog.text
    tipos = {r.getMessage().rsplit(": ", 1)[-1].split(".")[0] for r in caplog.records}
    assert tipos and all(t.isidentifier() for t in tipos)

    caplog.clear()
    vp._RESPALDO.clear()
    _credenciales(monkeypatch)
    _fabrica(monkeypatch, base)

    def _roto(*_a, **_k):
        raise ConnectionError(f"fallo con {EMAIL}")

    monkeypatch.setattr(vp, "corrida_en_revision", _roto)
    with caplog.at_level(logging.WARNING):
        assert vp.revision("cuidadores") is None
    assert "revision(cuidadores): corrida_en_revision" in caplog.text
    assert "ConnectionError" in caplog.text and EMAIL not in caplog.text


def test_sin_credenciales_avisa_que_falta_sin_valores(monkeypatch, caplog):
    monkeypatch.setenv("OBS360_MODO", "investigador")
    monkeypatch.setattr(vp, "credenciales", lambda: (EMAIL, None))
    monkeypatch.setattr(vp, "_conexion", lambda: ("https://falso.invalid", "clave-anon-falsa"))
    monkeypatch.setattr(vp, "_AVISADO_SIN_CREDENCIALES", False)
    with caplog.at_level(logging.WARNING):
        assert vp.disponible() is False
        assert vp.disponible() is False
    avisos = [r for r in caplog.records if "faltan" in r.getMessage()]
    assert len(avisos) == 1 and "OBS360_CARGA_CLAVE" in avisos[0].getMessage()
    for secreto in (EMAIL, "clave-anon-falsa", "falso.invalid"):
        assert secreto not in caplog.text


def test_en_comunidad_nunca_hay_cliente(monkeypatch):
    base, _, _ = _base_cuidadores()
    _credenciales(monkeypatch)
    monkeypatch.setenv("OBS360_MODO", "comunidad")
    _fabrica(monkeypatch, base)
    assert vp.cliente_autenticado() is None and base.inicios_de_sesion == 0


# ══ vista_previa: corrida en revisión ═════════════════════════════════════
def test_sin_corrida_oculta_no_hay_revision():
    _, base = datos.publicado()
    assert vp.corrida_en_revision("cuidadores", base.cliente(cargador=True)) is None


def test_el_anonimo_no_ve_revision_aunque_exista():
    base, _, _ = _base_cuidadores()
    assert vp.corrida_en_revision("cuidadores", base.cliente(anonimo=True)) is None


def test_la_revision_es_por_modulo():
    base, publicada, oculta = _base_cuidadores()
    cli = base.cliente(cargador=True)
    assert vp.corrida_en_revision("estudiantes", cli) is None
    assert vp.corrida_publicada("cuidadores", cli) == publicada


def test_una_oculta_mas_vieja_que_la_publicada_no_cuenta():
    from src.cuidadores import publicar
    base = BaseFalsa()
    publicar.publicar(datos.preparado(), publicar_ya=False, cliente=base.cliente())
    nueva = publicar.publicar(datos.preparado(), publicar_ya=True, cliente=base.cliente())
    cli = base.cliente(cargador=True)
    assert vp.corrida_en_revision("cuidadores", cli) is None
    assert vp.corrida_publicada("cuidadores", cli) == nueva["corrida_id"]


def test_revision_resume_y_memoriza(monkeypatch):
    base, publicada, oculta = _base_cuidadores()
    _credenciales(monkeypatch)
    monkeypatch.setenv("OBS360_MODO", "investigador")
    _fabrica(monkeypatch, base)
    info = vp.revision("cuidadores")
    assert info == dict(modulo="cuidadores", en_revision=oculta, publicada=publicada)
    assert vp.revision("cuidadores") == info and base.inicios_de_sesion == 1


# ══ Textos ════════════════════════════════════════════════════════════════
def test_banner_y_etiqueta():
    info = dict(modulo="cuidadores", en_revision=7, publicada=5)
    assert vp.etiqueta_interruptor(info) == "Vista previa: corrida en revisión (7)"
    texto = vp.texto_banner(info)
    assert texto.startswith("Vista previa para el equipo: esta corrida no está publicada; "
                            "los textos de alertas y de Cuidadores son provisionales y están "
                            "pendientes de aprobación.")
    assert "Lo público sigue mostrando la corrida 5." in texto
    sin = vp.texto_banner(dict(info, publicada=None))
    assert "Lo público todavía no muestra ninguna corrida" in sin


def test_activa_por_defecto_solo_en_investigador(monkeypatch):
    _credenciales(monkeypatch)
    monkeypatch.setenv("OBS360_MODO", "investigador")
    assert vp.activa() is True
    monkeypatch.setenv("OBS360_MODO", "completo")
    assert vp.activa() is False
    vp._sesion()[vp.CLAVE_ACTIVA] = True
    assert vp.activa() is True


def test_en_uso_por_modulo():
    assert not vp.en_uso("estudiantes")
    vp.marcar_en_uso("estudiantes", True)
    assert vp.en_uso("estudiantes") and not vp.en_uso("cuidadores")
    vp.marcar_en_uso("estudiantes", False)
    assert not vp.en_uso("estudiantes")
