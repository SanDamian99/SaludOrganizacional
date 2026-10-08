"""Cuidadores 360 · textos de la comunidad (fase 4b, spec §5.5, §6 y §8)."""
import re
from dataclasses import fields, is_dataclass

from src.cuidadores import catalog as cat
from src.cuidadores import comunidad_catalogo as cc
from src.estudiantes import catalog as cat_est


def _textos(objeto) -> list[str]:
    """Todas las cadenas de un valor del catálogo (dataclasses, dicts, tuplas)."""
    if isinstance(objeto, str):
        return [objeto]
    if is_dataclass(objeto) and not isinstance(objeto, type):
        return [t for f in fields(objeto) for t in _textos(getattr(objeto, f.name))]
    if isinstance(objeto, dict):
        return [t for v in objeto.values() for t in _textos(v)]
    if isinstance(objeto, (list, tuple)):
        return [t for v in objeto for t in _textos(v)]
    return []


def _todo() -> list[str]:
    return [t for nombre in dir(cc) if not nombre.startswith("_")
            for t in _textos(getattr(cc, nombre))]


def test_provisional_hasta_la_aprobacion():
    assert cc.TEXTOS_APROBADOS is False and cc.RUTAS_VALIDADAS is False


def test_mismos_roles_que_estudiantes():
    assert cc.ROLES == cat_est.ROLES


def test_una_tarjeta_por_cada_una_de_la_spec_en_su_orden():
    assert cc.ORDEN_TARJETAS == tuple(k for k, _ in cat.TARJETAS_4B)
    assert set(cc.MENSAJES) == set(cc.ORDEN_TARJETAS)
    assert cc.MAX_TARJETAS == 5
    for clave, titulo in cat.TARJETAS_4B:
        assert cc.MENSAJES[clave].titulo == titulo


def test_cada_rol_tiene_accion_en_las_tarjetas_que_ve():
    for clave, m in cc.MENSAJES.items():
        for rol in m.solo_roles:
            assert m.accion.get(rol), (clave, rol)


def test_familia_no_ve_la_tarjeta_de_animo():
    assert "familia" not in cc.MENSAJES["animo"].solo_roles
    assert set(cc.MENSAJES["animo"].solo_roles) == {"colegio", "municipio"}


def test_autolesion_solo_para_el_municipio_y_animo_nunca_para_familia():
    assert cc.ALERTAS[cat.AUTOLESION].roles == ("municipio",)
    assert set(cc.ALERTAS[cat.ANIMO].roles) == {"colegio", "municipio"}
    assert set(cc.ALERTAS) == {cat.ANIMO, cat.AUTOLESION}


def test_nunca_suicidio_en_ningun_texto():
    textos = _todo()
    assert len(textos) > 40
    for texto in textos:
        assert "suicid" not in texto.lower()


def test_lo_que_lee_familia_no_habla_de_hacerse_dano_ni_de_la_muerte():
    familia = [cc.AUTOCUIDADO_FAMILIA, cc.TITULO_AUTOCUIDADO,
               *[m.accion.get("familia", "") for m in cc.MENSAJES.values()],
               *[m.significa for m in cc.MENSAJES.values() if "familia" in m.solo_roles],
               *[m.etiqueta for m in cc.MENSAJES.values() if "familia" in m.solo_roles]]
    for texto in familia:
        for palabra in ("daño", "autoles", "muerte", "morir", "suicid"):
            assert palabra not in texto.lower(), (palabra, texto[:40])


def test_la_ruta_es_la_de_adultos_y_no_inventa_telefonos():
    for rol in cc.ROLES:
        assert cc.ruta(rol) == cat.ruta_adulto(rol)
        for nombre, detalle in cc.ruta(rol):
            assert not re.search(r"\d{3,}", nombre + detalle)


def test_ningun_texto_trae_numeros_de_telefono():
    for texto in _todo():
        assert not re.search(r"\b\d{7,}\b", texto)


def test_el_catalogo_no_importa_ingesta_ni_pipeline():
    import inspect
    fuente = inspect.getsource(cc)
    for prohibido in ("ingest", "pipeline", "scoring", "privacidad", "streamlit"):
        assert f"import {prohibido}" not in fuente and f"cuidadores.{prohibido}" not in fuente
