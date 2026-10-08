"""Cuidadores 360 · publicar → leer por módulo, sin tocar la lectura de estudiantes."""
import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import lectura, publicar
from src.estudiantes import catalog as cat_est
from src.estudiantes import lectura as lec_est
from src.estudiantes import pipeline as pipe_est
from src.estudiantes import publicar as pub_est
from tests import cuidadores_comunidad_datos as datos
from tests.supabase_falso import BaseFalsa


@pytest.fixture(scope="module")
def ida_y_vuelta():
    leido, base = datos.publicado()
    return datos.preparado(), leido, base


@pytest.fixture(scope="module")
def estudiantes():
    from src.estudiantes import ingest, scoring
    from tests.test_estudiantes_comunidad import _formulario
    bruto, _ = ingest.cargar(_formulario())
    return {cat_est.NIVEL_SECUNDARIA: pipe_est.analizar(scoring.puntuar(bruto),
                                                         cat_est.NIVEL_SECUNDARIA, n_boot=20)}


def _sin_vacios(t: pd.DataFrame) -> pd.DataFrame:
    return t.reset_index(drop=True).astype(object).where(t.notna().reset_index(drop=True), None)


def test_la_lectura_reconstruye_las_mismas_cifras(ida_y_vuelta):
    local, leido, _ = ida_y_vuelta
    for marco in cat.NOMBRES_MARCO:
        a, b = local.marcos[marco], leido.marcos[marco]
        columnas = ["clave", "indicador", "n", "pct", "ic_inf", "ic_sup"]
        assert _sin_vacios(a.cortes[columnas]).equals(_sin_vacios(b.cortes[columnas]))
        for agrupacion, grupos in a.subgrupos.items():
            assert set(grupos) == set(b.subgrupos.get(agrupacion, {}))
            for g, s in grupos.items():
                assert _sin_vacios(s.cortes[columnas]).equals(
                    _sin_vacios(b.subgrupos[agrupacion][g].cortes[columnas]))
        assert list(a.descriptivos["M"]) == list(b.descriptivos["M"])
        assert a.n == b.n


def test_la_tabla_de_senales_es_la_misma(ida_y_vuelta):
    local, leido, _ = ida_y_vuelta
    assert _sin_vacios(local.cuidador.alertas).equals(_sin_vacios(leido.cuidador.alertas))
    assert leido.nino.alertas.empty


def test_lo_leido_no_trae_filas_ni_olas(ida_y_vuelta):
    _, leido, _ = ida_y_vuelta
    for a in leido.marcos.values():
        assert a.datos.empty and a.base is None
        assert "ola" not in a.muestra
    assert leido.ola is None and leido.origen == "supabase"
    assert leido.informe.por_ola == {}


def test_los_conteos_pequenos_del_informe_llegan_enmascarados(ida_y_vuelta):
    _, leido, _ = ida_y_vuelta
    inf = leido.informe
    assert inf.sin_consentimiento == "<10"           # una sola fila sin consentimiento
    assert isinstance(inf.filas_archivo, int) and inf.filas_archivo >= cat.MIN_GROUP_N


def test_sin_aprobacion_la_corrida_se_lee_sin_senales():
    leido, _ = datos.publicado(aprobado=False)
    assert leido.cuidador.alertas.empty
    assert not leido.cuidador.cortes.empty


def test_la_autolesion_por_grupo_se_ignora_aunque_llegara():
    filas = [dict(nivel="cuidadores", tipo="alerta_grupo", clave=cat.AUTOLESION,
                  agrupacion="Colegio", grupo="LauV", n=30, valor=10.0, ic_inf=5.0,
                  ic_sup=15.0, detalle={"marco": "cuidador", "estado": "presente"})]
    assert lectura._alertas(filas).empty


def test_solo_lee_la_ultima_corrida_publicada_de_cuidadores(ida_y_vuelta):
    _, _, base = ida_y_vuelta
    cli = base.cliente(anonimo=True)
    vigente = lectura.id_corrida_vigente(cli)
    assert base.corrida(vigente)["modulo"] == "cuidadores"
    publicar.publicar(datos.preparado(), publicar_ya=False, cliente=base.cliente())
    assert lectura.id_corrida_vigente(cli) == vigente       # la oculta no se ve


def test_publicar_cuidadores_no_cambia_la_lectura_de_estudiantes(estudiantes, monkeypatch):
    base = BaseFalsa()
    pub_est.publicar(estudiantes, publicar_ya=True, cliente=base.cliente())
    monkeypatch.setattr(lec_est, "_cliente", lambda: base.cliente(anonimo=True))
    antes_id = lec_est.id_corrida_vigente()
    antes, _, corrida_antes = lec_est.cargar_desde_supabase()
    publicar.publicar(datos.preparado(), publicar_ya=True, cliente=base.cliente())
    publicar.publicar(datos.preparado(), publicar_ya=True, cliente=base.cliente())
    despues, _, corrida_despues = lec_est.cargar_desde_supabase()
    assert lec_est.id_corrida_vigente() == antes_id
    assert corrida_antes == corrida_despues
    assert set(antes) == set(despues) == {cat_est.NIVEL_SECUNDARIA}
    a, b = antes[cat_est.NIVEL_SECUNDARIA], despues[cat_est.NIVEL_SECUNDARIA]
    assert _sin_vacios(a.cortes).equals(_sin_vacios(b.cortes))
    # y la de cuidadores lee la suya, no la de estudiantes
    leido, corrida = lectura.cargar_desde_supabase(base.cliente(anonimo=True))
    assert corrida["modulo"] == "cuidadores" and leido is not None


def test_sin_corrida_no_hay_nada_que_leer():
    base = BaseFalsa()
    assert lectura.cargar_desde_supabase(base.cliente(anonimo=True)) == (None, None)
    assert lectura.id_corrida_vigente(base.cliente(anonimo=True)) is None


def test_el_lector_no_importa_ingesta_ni_pipeline_de_cuidadores():
    import inspect
    fuente = inspect.getsource(lectura)
    for prohibido in ("cuidadores import ingest", "cuidadores import pipeline",
                      "cuidadores.ingest", "cuidadores.pipeline", "cuidadores import scoring"):
        assert prohibido not in fuente
