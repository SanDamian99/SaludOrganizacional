"""Alertas de grupo de Estudiantes 360 (spec 6-oct-2026, §5.4): catálogo, señales y cifras."""
import inspect
import random
import re
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.estudiantes import alertas as al
from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, privacidad, supresion
from tests.test_estudiantes import _formulario_sintetico
from tests.test_estudiantes_comunidad import CON_RESTO, PRIMARIA
from tests.test_supresion_propiedades import _fuerza_bruta


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


# ══ Ítems con «*»: una sola regla, la de ingest ═════════════════════════════
@pytest.mark.parametrize("encabezado,marcado", [
    ("*SDQ [x]", True), ("SDQ [x] *", True), (" *SDQ [x]", True),
    ("SDQ [x]", False), ("SDQ [x*y]", False)])
def test_tiene_asterisco(encabezado, marcado):
    assert ingest.tiene_asterisco(encabezado) is marcado


def test_items_marcados_al_principio_o_al_final():
    raw = _formulario_sintetico(n=12)
    cols = [c for c in raw.columns if c.startswith("SDQ")]
    raw = raw.rename(columns={cols[4]: "*" + cols[4], cols[5]: cols[5] + " *"})
    assert al.items_marcados_por_escala(raw.columns) == {"SDQ": {5, 6}}
    _, inf = ingest.cargar(raw)                     # ingest usa la misma regla
    assert len(inf.items_marcados) == 2


def test_los_items_esperados_salen_del_catalogo():
    assert ac.items_marcados_esperados(cat.NIVEL_PRIMARIA) == {"SDQ": {5, 6, 8, 13, 19, 24}}
    assert ac.items_marcados_esperados(cat.NIVEL_SECUNDARIA) == {}   # hoy sin marcar


def test_un_formulario_marcado_como_el_catalogo_coincide_y_se_carga():
    raw = _formulario_sintetico(n=12)
    cols = [c for c in raw.columns if c.startswith("SDQ")]
    raw = raw.rename(columns={cols[i - 1]: "*" + cols[i - 1]
                              for i in ac.ALERTAS[ac.MALESTAR].items})
    assert al.items_marcados_por_escala(raw.columns) == \
        ac.items_marcados_esperados(cat.NIVEL_PRIMARIA)
    d, inf = ingest.cargar(raw)                     # el «*» no rompe la carga
    assert len(inf.items_marcados) == 6 and "SDQ5" in d.columns


# ══ Tabla de cada grupo, estado y tablas locales ═══════════════════════════
def test_estado_prioridad_contra_el_resto():
    assert al.estado(75.0, 40, 30.6, 160) == ac.PRIORIDAD      # 30/40 frente a 19/120
    assert al.estado(10.0, 40, 30.6, 160) == ac.PRESENTE


def test_sin_porcentaje_no_hay_estado():
    assert al.estado(None, 40, 30.0, 160) == ac.SIN_ESTADO
    assert al.estado(float("nan"), 40, 30.0, 160) == ac.SIN_ESTADO
    assert al.estado_total(None) == ac.SIN_ESTADO


def test_sin_resto_con_que_comparar_es_referencia():
    assert al.estado(30.0, 155, 30.0, 160) == ac.REFERENCIA      # resto de 5
    assert al.estado(30.0, 40, None, 160) == ac.REFERENCIA       # nivel suprimido
    assert al.estado_total(17.0) == ac.REFERENCIA


def test_el_estado_solo_recibe_cifras_publicadas():
    """El estado es función del % y el n publicados del grupo y del nivel: nada más."""
    assert list(inspect.signature(al.estado).parameters) == ["pct", "n", "pct_nivel", "n_nivel"]
    assert list(inspect.signature(al.estado_total).parameters) == ["pct"]


def test_cortes_alerta_tiene_la_forma_de_los_cortes():
    d = pd.DataFrame({"ALERTA_malestar": [1.0] * 6 + [0.0] * 14 + [np.nan] * 2,
                      "ALERTA_desesperanza": [1.0] * 4 + [0.0] * 18})
    t = al.cortes_alerta(d, cat.NIVEL_SECUNDARIA).set_index("clave")
    assert list(al.cortes_alerta(d, cat.NIVEL_SECUNDARIA).columns) == al.COLUMNAS_CORTES
    assert (t.loc["malestar", "n"], t.loc["malestar", "casos"]) == (20, 6)
    assert t.loc["malestar", "pct"] == 30.0 and t.loc["malestar", "anidada_en"] == ""
    assert t.loc["desesperanza", "anidada_en"] == "RCADS18"
    assert list(al.cortes_alerta(d, cat.NIVEL_PRIMARIA)["clave"]) == ["malestar"]


def _objeto(filas):
    return SimpleNamespace(cortes_alerta=pd.DataFrame(filas, columns=al.COLUMNAS_CORTES))


def _c(clave, n, k, pct):
    nulo = pct is None
    return dict(clave=clave, indicador="", anidada_en="", n=n, casos=None if nulo else k,
                pct=pct, ic_inf=None if nulo else pct - 5, ic_sup=None if nulo else pct + 5)


def test_la_tabla_plana_sale_de_las_tablas_suprimidas():
    a = _objeto([_c("malestar", 160, 49, 30.6)])
    a.nivel = cat.NIVEL_SECUNDARIA
    a.subgrupos = {
        "Colegio": {"A": _objeto([_c("malestar", 40, 30, 75.0)]),
                    "B": _objeto([_c("malestar", 40, None, None)])},     # suprimida
        "Grado": {"Sexto": _objeto([_c("malestar", 8, 2, 25.0)])},        # n < 10: fuera
        al.CRUCE: {}}
    t = al.tabla(a)
    assert list(t.columns) == al.COLUMNAS_TABLA and "casos" not in t.columns
    assert list(zip(t["agrupacion"], t["grupo"], t["estado"])) == [
        (al.TOTAL, al.TODOS, ac.REFERENCIA), ("Colegio", "A", ac.PRIORIDAD),
        ("Colegio", "B", ac.SIN_ESTADO)]
    assert t["pct"].isna().tolist() == [False, False, True]


def test_sin_tabla_de_alertas_la_tabla_plana_queda_vacia():
    t = al.tabla(SimpleNamespace(nivel=cat.NIVEL_SECUNDARIA))
    assert t.empty and list(t.columns) == al.COLUMNAS_TABLA


def test_ordenar_es_estable_ante_filas_barajadas():
    filas = [dict(alerta=a, agrupacion=ag, grupo=g, n=40, pct=None, ic_inf=None, ic_sup=None,
                  estado=ac.SIN_ESTADO)
             for a in ("desesperanza", "malestar")
             for ag, g in ((al.CRUCE, "A|Octavo"), ("Grado", "Octavo"), (al.CRUCE, "A|Sexto"),
                           ("Colegio", "B"), ("Grado", "Sexto"), (al.TOTAL, al.TODOS),
                           ("Colegio", "A"))]
    t = al.ordenar(pd.DataFrame(filas), cat.NIVEL_SECUNDARIA)
    assert list(t["alerta"][:7]) == ["malestar"] * 7
    assert list(zip(t["agrupacion"], t["grupo"]))[:7] == [
        (al.TOTAL, al.TODOS), ("Colegio", "A"), ("Colegio", "B"), ("Grado", "Sexto"),
        ("Grado", "Octavo"), (al.CRUCE, "A|Sexto"), (al.CRUCE, "A|Octavo")]
    barajada = t.sample(frac=1, random_state=3)
    pd.testing.assert_frame_equal(al.ordenar(barajada, cat.NIVEL_SECUNDARIA), t)


# ── sensibilidad e ítems: solo el nivel, solo local ───────────────────────
def _publicadas(**pcts) -> pd.DataFrame:
    """Tabla `cortes_alerta` del nivel YA suprimida: {alerta: pct o None}."""
    return pd.DataFrame([dict(clave=k, n=100, pct=v) for k, v in pcts.items()])


def test_sensibilidad_del_malestar_entera_o_nada_y_solo_si_la_vigente_se_publica():
    d = pd.DataFrame({"ALERTA_malestar_2": [1.0] * 20 + [0.0] * 80,
                      "ALERTA_malestar": [1.0] * 10 + [0.0] * 90,
                      "ALERTA_malestar_4": [1.0] * 9 + [0.0] * 91})
    s = al.sensibilidad(d, cat.NIVEL_SECUNDARIA, _publicadas(malestar=10.0))
    assert s.set_index("variante")["pct"].isna().all()   # 3 − 4 deja 1 estudiante: nada
    d["ALERTA_malestar_4"] = [1.0] * 5 + [0.0] * 95
    s = al.sensibilidad(d, cat.NIVEL_SECUNDARIA, _publicadas(malestar=10.0)).set_index("variante")
    assert s.loc["malestar_3", "pct"] == 10.0 and s.loc["malestar_4", "pct"] == 5.0
    assert (s["n"] == 100).all() and "casos" not in s.columns
    # mismo reparto, pero la cifra vigente quedó suprimida en el nivel: nada
    for publicadas in (_publicadas(malestar=None), None):
        s = al.sensibilidad(d, cat.NIVEL_SECUNDARIA, publicadas)
        assert s["pct"].isna().all() and s["ic_inf"].isna().all()


def _dn_desesperanza(estrictas, muerte_sin_valia, amplia_extra, sin_items_amplia=0, n=100):
    """Ítems codificados → `marcar`. Las filas sin ítems 1 y 4 llevan valía alta."""
    filas = []
    for i in range(n):
        f = {f"SDQ{j}": 0 for j in ITEMS_MALESTAR}
        f.update(RCADS1=0, RCADS4=0, RCADS16=0, RCADS18=0)
        if i < estrictas:
            f.update(RCADS18=ac.CON_FRECUENCIA, RCADS16=ac.CON_FRECUENCIA)
        elif i < estrictas + muerte_sin_valia:
            f.update(RCADS18=ac.CON_FRECUENCIA)
        elif i < estrictas + muerte_sin_valia + amplia_extra:
            f.update(RCADS16=ac.CON_FRECUENCIA, RCADS4=ac.CON_FRECUENCIA)
        elif i < estrictas + muerte_sin_valia + amplia_extra + sin_items_amplia:
            f.update(RCADS16=ac.CON_FRECUENCIA, RCADS1=np.nan, RCADS4=np.nan)
        filas.append(f)
    return al.marcar(pd.DataFrame(filas), cat.NIVEL_SECUNDARIA)


def _des(s):
    return s[s["alerta"] == ac.DESESPERANZA].set_index("variante")


def test_sensibilidad_de_la_desesperanza_con_la_cadena_de_cuatro_partes():
    dn = _dn_desesperanza(estrictas=10, muerte_sin_valia=5, amplia_extra=10)
    s = _des(al.sensibilidad(dn, cat.NIVEL_SECUNDARIA, _publicadas(desesperanza=10.0)))
    assert s.loc["desesperanza_estricta", "pct"] == 10.0
    assert s.loc["desesperanza_amplia", "pct"] == 25.0
    assert (s["n"] == 100).all()


def test_sensibilidad_de_la_desesperanza_oculta_si_la_vigente_no_se_publica():
    """Escenario leak1: la estricta suprimida no puede salir por la sensibilidad."""
    dn = _dn_desesperanza(estrictas=10, muerte_sin_valia=5, amplia_extra=10)
    for publicadas in (_publicadas(desesperanza=None), None):
        s = _des(al.sensibilidad(dn, cat.NIVEL_SECUNDARIA, publicadas))
        assert s["pct"].isna().all()


def test_sensibilidad_de_la_desesperanza_oculta_si_el_item_18_deja_un_hueco():
    """k₁₈ − k_estricta = 1: con el corte del ítem 18 publicado, se deduciría."""
    dn = _dn_desesperanza(estrictas=10, muerte_sin_valia=1, amplia_extra=10)
    s = _des(al.sensibilidad(dn, cat.NIVEL_SECUNDARIA, _publicadas(desesperanza=10.0)))
    assert s["pct"].isna().all()


def test_sensibilidad_de_la_desesperanza_usa_la_base_publicada():
    """Sin ítems 1 o 4 la fila sigue en la base (16 y 18 respondidos) y no es amplia."""
    dn = _dn_desesperanza(estrictas=10, muerte_sin_valia=5, amplia_extra=10,
                          sin_items_amplia=5)
    s = _des(al.sensibilidad(dn, cat.NIVEL_SECUNDARIA, _publicadas(desesperanza=10.0)))
    assert (s["n"] == 100).all()
    assert s.loc["desesperanza_amplia", "pct"] == 25.0


def test_sensibilidad_escenario_leak1_por_el_pipeline():
    filas = []
    for i in range(100):
        f = dict(Colegio="A" if i < 50 else "B", Grado="Sexto",
                 Sexo="Mujer" if i % 2 else "Hombre", Edad=13, nivel=cat.NIVEL_SECUNDARIA)
        f.update({f"SDQ{j}": 0 for j in ITEMS_MALESTAR})
        f.update(RCADS1=0, RCADS4=0, RCADS16=0, RCADS18=0)
        if i % 10 == 0:
            f.update(RCADS18=2, RCADS16=2)
        if i == 1:
            f.update(RCADS18=2)
        if i in (3, 4, 5, 53, 54, 55, 56, 57, 58, 59):
            f.update(RCADS16=2, RCADS4=2)
        filas.append(f)
    a = pipeline.analizar(pd.DataFrame(filas), cat.NIVEL_SECUNDARIA, n_boot=5)
    t = a.alertas
    assert t[(t["alerta"] == ac.DESESPERANZA) & (t["agrupacion"] == al.TOTAL)]["pct"].isna().all()
    assert _des(a.alertas_sensibilidad)["pct"].isna().all()
    assert supresion.auditar(a) == []


def test_distribucion_de_items_oculta_el_item_con_una_respuesta_rara():
    d = pd.DataFrame({"ALERTA_malestar": 0.0,
                      "SDQ5": [0] * 90 + [1] * 8 + [2] * 2,
                      "SDQ6": [0] * 60 + [1] * 30 + [2] * 10})
    t = al.distribucion_items(d, cat.NIVEL_SECUNDARIA, _publicadas(malestar=None))
    assert t[t["item"] == "SDQ5"]["pct"].isna().all()
    sdq6 = t[t["item"] == "SDQ6"]
    assert sdq6["pct"].tolist() == [60.0, 30.0, 10.0]
    assert sdq6["respuesta"].tolist() == ["No es cierto", "Algo cierto", "Muy cierto"]
    assert list(t.columns) == al.COLUMNAS_ITEMS


def test_distribucion_de_items_usa_la_base_de_la_alerta():
    d = pd.DataFrame({"ALERTA_malestar": [0.0] * 100 + [np.nan] * 10,
                      "SDQ6": [0] * 60 + [1] * 30 + [2] * 10 + [2] * 10})
    t = al.distribucion_items(d, cat.NIVEL_SECUNDARIA, _publicadas(malestar=None))
    sdq6 = t[t["item"] == "SDQ6"]
    assert (sdq6["n"] == 100).all() and sdq6["pct"].tolist() == [60.0, 30.0, 10.0]


def test_distribucion_de_items_omite_los_de_la_alerta_publicada():
    d = pd.DataFrame({"ALERTA_malestar": 0.0,
                      "SDQ6": [0] * 60 + [1] * 30 + [2] * 10})
    for publicadas in (_publicadas(malestar=4.0), None):
        sdq6 = al.distribucion_items(d, cat.NIVEL_SECUNDARIA, publicadas)
        sdq6 = sdq6[sdq6["item"] == "SDQ6"]
        assert sdq6["pct"].isna().all()
        assert (sdq6["nota"] == al.OMITIDA_POR_ALERTA).all()
    assert al.OMITIDA_POR_ALERTA == ("Se omite: combinada con la alerta publicada podría "
                                     "identificar a alguien")


def test_distribucion_de_items_escenario_leak3():
    """Desesperanza publicada (6 %) + reparto del ítem 18 → «frecuente con valía» = 1."""
    filas = []
    for i in range(100):
        f = dict(Colegio="A" if i < 50 else "B", Grado="Sexto",
                 Sexo="Mujer" if i % 2 else "Hombre", Edad=13, nivel=cat.NIVEL_SECUNDARIA)
        f.update({f"SDQ{j}": 0 for j in ITEMS_MALESTAR})
        f.update(RCADS1=0, RCADS4=0, RCADS16=1 if i % 3 else 0, RCADS18=1 if i % 4 == 0 else 0)
        if i in (0, 10, 20, 60, 70):
            f["RCADS18"] = 3
        if i == 30:
            f.update(RCADS18=2, RCADS16=2)
        if i in (40, 80, 90):
            f.update(RCADS18=2, RCADS16=0)
        if i in (1, 2, 51):
            f["RCADS16"] = 2
        filas.append(f)
    a = pipeline.analizar(pd.DataFrame(filas), cat.NIVEL_SECUNDARIA, n_boot=5)
    t = a.alertas
    total = t[(t["alerta"] == ac.DESESPERANZA) & (t["agrupacion"] == al.TOTAL)]
    assert not total["pct"].isna().any()                 # la alerta sí se publica
    it = a.alertas_items
    componentes = it[it["item"].isin(["RCADS16", "RCADS18"])]
    assert len(componentes) and componentes["pct"].isna().all()
    assert (componentes["nota"] == al.OMITIDA_POR_ALERTA).all()


# ══ Cifras de las alertas: la supresión general ═════════════════════════════
# Las tres configuraciones reales de resta: todo en celdas; colegio publicado
# entero sin celdas y respuestas fuera del nivel (primaria, oct-2026); resto R
# dentro del nivel (CON_RESTO).
TODO_EN_CELDAS = {("A", "Sexto"): 20, ("B", "Sexto"): 30, ("C", "Sexto"): 15,
                  ("A", "Séptimo"): 20}
CONFIGURACIONES = [(cat.NIVEL_SECUNDARIA, TODO_EN_CELDAS), (cat.NIVEL_PRIMARIA, PRIMARIA),
                   (cat.NIVEL_SECUNDARIA, CON_RESTO)]
ITEMS_MALESTAR = ac.ALERTAS[ac.MALESTAR].items


def _datos_config(nivel, conteos: dict, semilla: int) -> pd.DataFrame:
    """Filas con ítems ya codificados. Probabilidades bajas: muchas celdas con 0 a 2 casos."""
    rng = random.Random(semilla)
    p_mal, p_des, p_18 = rng.choice([.03, .08, .2]), rng.choice([.03, .1]), rng.choice([.05, .2])
    filas = []
    for (c, g), n in conteos.items():
        for i in range(n):
            f = dict(Colegio=c, Grado=g, Sexo="Mujer" if i % 2 else "Hombre", Edad=13,
                     nivel=nivel)
            malestar = rng.random() < p_mal
            for item in ITEMS_MALESTAR:
                f[f"SDQ{item}"] = ac.MUY_CIERTO if malestar and item in (5, 6, 8) else 0
            if nivel == cat.NIVEL_SECUNDARIA:
                u = rng.random()
                muerte = (ac.SIEMPRE if u < p_des else ac.CON_FRECUENCIA if u < p_des + p_18
                          else 0)
                f.update(RCADS1=0, RCADS4=0, RCADS16=0, RCADS18=muerte)
            filas.append(f)
    return pd.DataFrame(filas)


def _nombre(agrupacion: str, grupo: str):
    return supresion.NIVEL if agrupacion == al.TOTAL else (agrupacion, str(grupo))


def _partes_reales(a, alerta: str):
    """{átomo: partes} desde los datos enmascarados, sin pasar por la supresión."""
    familia = al.ANIDADA.get(alerta, "")
    partes = {}
    for at, idx in supresion.indices_atomos(a.base).items():
        sub = a.datos.loc[a.datos.index.intersection(idx)]
        s = sub[al.COLUMNAS[alerta]].dropna() if al.COLUMNAS[alerta] in sub else pd.Series(dtype=float)
        k, n = int(s.sum()), len(s)
        if familia:
            k18 = int((sub[familia].dropna() >= ac.CON_FRECUENCIA).sum())
            partes[at] = (n - k18, k18 - k, k)
        else:
            partes[at] = (n - k, k)
    return partes


@pytest.mark.parametrize("nivel,conteos", CONFIGURACIONES)
def test_lo_publicado_de_las_alertas_resiste_restas(nivel, conteos):
    """Fuerza bruta: ningún conjunto de átomos deducible de lo publicado incumple la regla."""
    for semilla in range(12):
        a = pipeline.analizar(_datos_config(nivel, conteos, semilla), nivel, n_boot=5)
        assert supresion.auditar(a) == [], semilla
        jer = supresion.jerarquia(list(a.base.celdas), list(a.base.colegios),
                                  list(a.base.grados), con_resto=a.base.incluye_resto)
        for alerta in al.claves_del_nivel(a.datos, nivel):
            t = a.alertas[a.alertas["alerta"] == alerta]
            pub = {_nombre(f["agrupacion"], f["grupo"]) for f in t.to_dict("records")
                   if f["pct"] is not None and not pd.isna(f["pct"])}
            partes = _partes_reales(a, alerta)
            assert _fuerza_bruta(jer, partes, pub) == set(), (semilla, alerta)
            for f in t.to_dict("records"):
                if pd.isna(f["pct"]):
                    assert f["estado"] == ac.SIN_ESTADO and pd.isna(f["ic_inf"])


def test_los_grados_y_las_celdas_llevan_porcentaje_cuando_se_puede():
    conteos = {("A", "Sexto"): 40, ("A", "Séptimo"): 40, ("B", "Sexto"): 40,
               ("B", "Séptimo"): 40}
    filas = []
    for (c, g), n in conteos.items():
        k = 30 if (c, g) == ("A", "Sexto") else 6
        for i in range(n):
            f = dict(Colegio=c, Grado=g, Sexo="Mujer", Edad=13, nivel=cat.NIVEL_SECUNDARIA)
            f.update({f"SDQ{j}": ac.MUY_CIERTO if i < k and j in (5, 6, 8) else 0
                      for j in ITEMS_MALESTAR})
            filas.append(f)
    a = pipeline.analizar(pd.DataFrame(filas), cat.NIVEL_SECUNDARIA, n_boot=5)
    t = a.alertas.set_index(["agrupacion", "grupo"])
    for clave in (("Grado", "Sexto"), ("Grado", "Séptimo"), (al.CRUCE, "A|Sexto"),
                  ("Colegio", "A")):
        assert not pd.isna(t.loc[clave, "pct"]), clave
    assert t.loc[(al.CRUCE, "A|Sexto"), "estado"] == ac.PRIORIDAD
    assert t.loc[("Grado", "Séptimo"), "estado"] == ac.PRESENTE
    assert t.loc[(al.TOTAL, al.TODOS), "estado"] == ac.REFERENCIA
    assert list(a.alertas.columns) == al.COLUMNAS_TABLA and "casos" not in a.alertas


def test_la_desesperanza_nunca_se_publica_donde_el_item_18_esta_suprimido():
    for semilla in range(12):
        a = pipeline.analizar(_datos_config(cat.NIVEL_SECUNDARIA, CON_RESTO, semilla),
                              cat.NIVEL_SECUNDARIA, n_boot=5)
        for g, o in supresion._objetos(a).items():
            if supresion._publicado_alerta(o, ac.DESESPERANZA):
                assert supresion._publicado(o, al.ANIDADA[ac.DESESPERANZA]), (semilla, g)


def test_si_las_bases_no_coinciden_la_desesperanza_no_se_publica():
    d = _datos_config(cat.NIVEL_SECUNDARIA, TODO_EN_CELDAS, 1)
    d.loc[d.index[:3], "RCADS16"] = np.nan       # 18 respondido, 16 no: bases distintas
    a = pipeline.analizar(d, cat.NIVEL_SECUNDARIA, n_boot=5)
    des = a.alertas[a.alertas["alerta"] == ac.DESESPERANZA]
    assert len(des) and des["pct"].isna().all()
    assert (des["estado"] == ac.SIN_ESTADO).all()
    assert supresion.auditar(a) == []


def test_la_auditoria_detecta_una_alerta_destapada():
    import copy
    for semilla in range(12):
        a = pipeline.analizar(_datos_config(cat.NIVEL_SECUNDARIA, TODO_EN_CELDAS, semilla),
                              cat.NIVEL_SECUNDARIA, n_boot=5)
        celda = a.subgrupos[al.CRUCE]["A|Sexto"]
        t = celda.cortes_alerta
        fila = t["clave"] == ac.MALESTAR
        if fila.any() and t.loc[fila, "pct"].isna().all():
            b = copy.deepcopy(a)
            b.subgrupos[al.CRUCE]["A|Sexto"].cortes_alerta.loc[fila, "pct"] = 5.0
            assert any(p.startswith("alerta malestar") for p in supresion.auditar(b))
            return
    pytest.fail("ninguna semilla dejó la celda suprimida")


def test_suprimir_nunca_destapa_lo_que_ya_venia_oculto():
    jer = supresion.jerarquia(["A|Sexto", "B|Sexto"], ["A", "B"], ["Sexto"], con_resto=False)
    partes = {supresion.atomo_celda("A|Sexto"): (20, 10), supresion.atomo_celda("B|Sexto"): (20, 10)}
    assert supresion.suprimir(jer, partes) == set()
    sup = supresion.suprimir(jer, partes, previos={supresion.COLEGIO("A")})
    assert supresion.COLEGIO("A") in sup


@pytest.mark.parametrize("semilla", range(6))
def test_el_estado_de_la_tabla_se_reproduce_con_lo_publicado(semilla):
    """Con las cifras publicadas de la tabla (sin datos) sale el mismo estado."""
    a = pipeline.analizar(_datos_config(*CONFIGURACIONES[0], semilla=semilla), CONFIGURACIONES[0][0],
                          n_boot=5)
    t = a.alertas
    for f in t[t["agrupacion"] != al.TOTAL].to_dict("records"):
        nivel = t[(t["alerta"] == f["alerta"]) & (t["agrupacion"] == al.TOTAL)].iloc[0]
        assert f["estado"] == al.estado(f["pct"], f["n"], nivel["pct"], nivel["n"])


def test_con_una_supresion_vieja_la_tabla_sale_vacia(monkeypatch):
    """Módulo `supresion` anterior a la fase 3 en memoria: no suprimió las alertas."""
    a = pipeline.analizar(_datos_config(cat.NIVEL_SECUNDARIA, TODO_EN_CELDAS, 1),
                          cat.NIVEL_SECUNDARIA, n_boot=5)
    assert len(al.tabla(a))
    viejo = SimpleNamespace(**{k: v for k, v in vars(supresion).items()
                               if k != "TABLAS_ALERTA"})
    monkeypatch.setattr(al, "supresion", viejo)
    t = al.tabla(a)
    assert t.empty and list(t.columns) == al.COLUMNAS_TABLA
