"""
`cuidadores.lectura` filtra `publicada = true` aunque la base ya lo haga (RLS).

Defensa doble: con un cliente que ve todo (p. ej. la clave de servicio en la
máquina que publica), una corrida subida sin `--publicar-ya` nunca se lee.
"""
from src.cuidadores import lectura, publicar
from tests import cuidadores_comunidad_datos as datos


def _base_con_oculta_mas_nueva():
    leido, base = datos.publicado()
    publicada = lectura.id_corrida_vigente(base.cliente(anonimo=True))
    oculta = publicar.publicar(datos.preparado(), publicar_ya=False, cliente=base.cliente())
    assert base.corrida(oculta["corrida_id"])["publicada"] is False
    return base, publicada, oculta["corrida_id"]


def test_la_corrida_vigente_es_la_publicada_aunque_el_cliente_vea_todo():
    base, publicada, oculta = _base_con_oculta_mas_nueva()
    assert oculta > publicada
    assert lectura.id_corrida_vigente(base.cliente()) == publicada


def test_cargar_lee_la_publicada_aunque_el_cliente_vea_todo():
    base, publicada, _ = _base_con_oculta_mas_nueva()
    ac, corrida = lectura.cargar_desde_supabase(base.cliente())
    assert corrida["id"] == publicada and corrida["publicada"] is True


def test_sin_corridas_publicadas_no_hay_nada():
    from tests.supabase_falso import BaseFalsa
    base = BaseFalsa()
    publicar.publicar(datos.preparado(), publicar_ya=False, cliente=base.cliente())
    assert lectura.id_corrida_vigente(base.cliente()) is None
    assert lectura.cargar_desde_supabase(base.cliente())[0] is None
