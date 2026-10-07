"""Alertas de grupo de Estudiantes 360 (spec 6-oct-2026, §5.4): catálogo, señales y cifras."""
import re

import numpy as np
import pandas as pd
import pytest

from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, privacidad, supresion
from tests.test_estudiantes import _formulario_sintetico


# ══ Catálogo ════════════════════════════════════════════════════════════════
def test_catalog_reexporta_alertas_y_rutas():
    assert cat.ALERTAS is ac.ALERTAS and cat.RUTAS is ac.RUTAS


def test_definiciones_de_la_spec():
    m, d = ac.ALERTAS[ac.MALESTAR], ac.ALERTAS[ac.DESESPERANZA]
    assert m.escala == "SDQ" and m.items == (5, 6, 8, 13, 19, 24)
    assert ac.UMBRAL_MALESTAR == 3 and ac.UMBRALES_SENSIBILIDAD == (2, 3, 4)
    assert set(m.niveles) == {cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA}
    assert d.escala == "RCADS" and d.niveles == (cat.NIVEL_SECUNDARIA,)
    assert ac.ITEM_MUERTE == cat.RCADS_ITEM_MUERTE == 18 and ac.ITEM_VALIA == 16
    assert set(ac.ITEMS_AMPLIA) == {1, 4}


def test_la_codificacion_es_la_de_ingest():
    assert ac.MUY_CIERTO == cat.MAP_3["muy cierto"]
    assert ac.CON_FRECUENCIA == cat.MAP_4_FREQ["con frecuencia"]
    assert ac.SIEMPRE == cat.MAP_4_FREQ["siempre"]
    # ninguno de los 6 ítems del malestar es inverso: se leen como se respondieron
    assert not set(ac.ALERTAS[ac.MALESTAR].items) & set(cat.SDQ_REVERSE_ITEMS)
    assert set(ac.ITEMS_REGLA_AMPLIA) <= set(cat.RCADS_DEP_ITEMS)


def test_roles_y_niveles_coinciden_con_catalog():
    assert set(ac.ROLES) == set(cat.ROLES)
    assert set(ac.NIVELES) == {cat.NIVEL_SECUNDARIA, cat.NIVEL_PRIMARIA}
    for a in ac.ALERTAS.values():
        assert set(a.roles) <= set(cat.ROLES) and set(a.niveles) <= set(ac.NIVELES)
        for rol in a.roles:
            assert a.que_hacer.get(rol, "").strip(), (a.clave, rol)


def test_familia_no_ve_desesperanza():
    assert "familia" not in ac.ALERTAS[ac.DESESPERANZA].roles
    assert "familia" in ac.ALERTAS[ac.MALESTAR].roles


def _textos() -> list[str]:
    textos = [v for k, v in vars(ac).items() if k.isupper() and isinstance(v, str)]
    textos += list(ac.ESTADOS.values())
    for a in ac.ALERTAS.values():
        textos += [a.nombre, a.nombre_corto, a.senal, a.regla, a.que_es, a.limite,
                   *a.que_hacer.values()]
    textos += [d for por_tipo in ac.RUTAS.values() for ruta in por_tipo.values()
               for _, d in ruta]
    return textos


def test_los_textos_no_alarman():
    for t in _textos():
        bajo = t.lower()
        assert "suicid" not in bajo, t
        assert "alarma" not in bajo, t
    assert ac.ESTADOS[ac.PRIORIDAD] == "Prioridad"
    assert ac.ESTADOS[ac.PRESENTE] == ac.ESTADOS[ac.REFERENCIA] == "Para tener presente"
    assert ac.ESTADOS[ac.SIN_ESTADO] == "Sin estado: cifras pequeñas"
    assert ac.CIFRAS_PEQUENAS == cat.CIFRAS_PEQUENAS
    assert ac.NO_ES_DIAGNOSTICO.startswith("No es un diagnóstico")
    assert "dónde mirar primero" in ac.NO_ES_DIAGNOSTICO
    assert f"al menos {supresion.MIN_CASOS} estudiantes" in ac.REGLA_CIFRAS


def test_las_rutas_no_inventan_telefonos():
    numeros = {m for por_tipo in ac.RUTAS.values() for ruta in por_tipo.values()
               for n, d in ruta for m in re.findall(r"\d{3,}", f"{n} {d}")}
    assert numeros <= {"106"}          # la línea vigente; las de Chía las confirma el equipo
    assert set(ac.RUTAS) == set(cat.ROLES)
    for rol in cat.ROLES:
        assert ac.ruta(rol, "estudiante") == list(cat.RUTA_ATENCION)
        assert ac.ruta(rol, "adulto")


def test_la_ruta_vigente_no_cambia():
    assert cat.RUTA_ATENCION == [
        ("Orientación escolar del colegio", "Primer contacto, siempre."),
        ("Línea 106", "Atención psicológica gratuita, 24 horas."),
        ("Secretaría de Salud de Chía", "Ruta de salud mental municipal."),
        ("Comisaría de Familia", "Si hay riesgo en el hogar."),
    ]


def test_quedan_marcadas_como_provisionales():
    assert ac.TEXTOS_APROBADOS is False and ac.RUTAS_VALIDADAS is False
    assert "pendiente de validación" in ac.RUTA_PENDIENTE


# ══ Señales por estudiante, desde el texto crudo del formulario ═════════════
def _poner(raw, prefijo, fila, valores: dict):
    cols = [c for c in raw.columns if c.startswith(prefijo)]
    for item, texto in valores.items():
        raw.loc[fila, cols[item - 1]] = texto


def _crudo_malestar():
    raw = _formulario_sintetico(n=12)
    for f in range(12):
        _poner(raw, "SDQ", f, {i: "No es cierto" for i in ac.ALERTAS[ac.MALESTAR].items})
    _poner(raw, "SDQ", 0, {5: "Muy cierto", 6: "Muy cierto", 8: "Muy cierto"})
    _poner(raw, "SDQ", 1, {5: "Muy cierto", 24: "Muy cierto"})
    _poner(raw, "SDQ", 2, {6: "Muy cierto", 13: "Muy cierto", 19: "Muy cierto", 24: "Muy cierto"})
    _poner(raw, "SDQ", 3, {5: "Muy cierto", 6: "Muy cierto", 8: "Muy cierto", 24: None})
    _poner(raw, "SDQ", 4, {i: "Algo cierto" for i in ac.ALERTAS[ac.MALESTAR].items})
    return raw


def _crudo_desesperanza():
    raw = _formulario_sintetico(n=12)
    for f in range(12):
        _poner(raw, "RCADS", f, {i: "Nunca" for i in ac.ITEMS_REGLA_AMPLIA})
    _poner(raw, "RCADS", 0, {18: "Siempre"})
    _poner(raw, "RCADS", 1, {18: "Con frecuencia", 16: "Con frecuencia"})
    _poner(raw, "RCADS", 2, {18: "Con frecuencia", 16: "Algunas veces"})
    _poner(raw, "RCADS", 3, {18: "Algunas veces", 16: "Siempre", 4: "Con frecuencia"})
    _poner(raw, "RCADS", 4, {18: "Nunca", 16: "Siempre"})
    return raw


def test_malestar_se_puntua_desde_el_texto_crudo():
    d, _ = ingest.cargar(_crudo_malestar())          # filas en el orden del formulario
    s = al.senal_malestar(d)
    assert s.iloc[0] == 1.0                          # 3 «Muy cierto»
    assert s.iloc[1] == 0.0                          # 2
    assert s.iloc[2] == 1.0                          # 4
    assert np.isnan(s.iloc[3])                       # falta un ítem: no se adivina
    assert s.iloc[4] == 0.0                          # «Algo cierto» no cuenta
    assert al.senal_malestar(d, 2).iloc[1] == 1.0
    assert al.senal_malestar(d, 4).iloc[0] == 0.0


def test_desesperanza_estricta_y_amplia():
    d, _ = ingest.cargar(_crudo_desesperanza())
    estricta = al.senal_desesperanza(d)
    amplia = al.senal_desesperanza(d, amplia=True)
    assert estricta.iloc[:5].tolist() == [1.0, 1.0, 0.0, 0.0, 0.0]
    assert amplia.iloc[:5].tolist() == [1.0, 1.0, 1.0, 1.0, 0.0]
    assert (amplia.dropna() >= estricta.dropna()).all()   # la amplia contiene a la estricta


def test_la_desesperanza_esta_anidada_en_el_corte_del_item_18():
    """Estricta ⊆ RCADS18 ≥ «Con frecuencia»: por eso la supresión la trata como anidada."""
    rng = np.random.default_rng(3)
    d = pd.DataFrame({f"RCADS{i}": rng.integers(0, 4, 500) for i in ac.ITEMS_REGLA_AMPLIA})
    s = al.senal_desesperanza(d)
    assert ((s == 1) <= (d["RCADS18"] >= ac.CON_FRECUENCIA)).all()
    assert al.ANIDADA == {ac.DESESPERANZA: f"RCADS{cat.RCADS_ITEM_MUERTE}"}


def test_sin_las_columnas_no_hay_senal():
    d = pd.DataFrame({"SDQ1": [0, 1]})
    assert al.senal_malestar(d).isna().all()
    assert al.senal_desesperanza(d).isna().all()


def test_marcar_agrega_las_columnas_del_nivel_y_no_toca_nada_mas():
    d, _ = ingest.cargar(_crudo_desesperanza())
    m = al.marcar(d, cat.NIVEL_SECUNDARIA)
    assert set(m.columns) - set(d.columns) == {
        "ALERTA_malestar", "ALERTA_malestar_2", "ALERTA_malestar_4",
        "ALERTA_desesperanza", "ALERTA_desesperanza_amplia"}
    pd.testing.assert_frame_equal(m[d.columns], d)
    p = al.marcar(d, cat.NIVEL_PRIMARIA)             # primaria nunca lleva desesperanza
    assert "ALERTA_malestar" in p.columns
    assert not [c for c in p.columns if c.startswith("ALERTA_desesperanza")]
    pd.testing.assert_frame_equal(al.marcar(m, cat.NIVEL_SECUNDARIA), m)   # idempotente


def test_las_columnas_de_senal_pasan_por_el_todo_o_nada():
    d = pd.DataFrame(columns=["Colegio", "Grado", "ALERTA_malestar"])
    assert "ALERTA_malestar" in privacidad.columnas_de_analisis(d)
