"""Alertas de grupo de Estudiantes 360 (spec 6-oct-2026, §5.4): catálogo, señales y cifras."""
import inspect
import re
from types import SimpleNamespace

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
def test_sensibilidad_se_muestra_entera_o_no_se_muestra():
    d = pd.DataFrame({"ALERTA_malestar_2": [1.0] * 20 + [0.0] * 80,
                      "ALERTA_malestar": [1.0] * 10 + [0.0] * 90,
                      "ALERTA_malestar_4": [1.0] * 9 + [0.0] * 91})
    s = al.sensibilidad(d, cat.NIVEL_SECUNDARIA).set_index("variante")
    assert s["pct"].isna().all()                  # 3 − 4 deja 1 estudiante: nada
    d["ALERTA_malestar_4"] = [1.0] * 5 + [0.0] * 95
    s = al.sensibilidad(d, cat.NIVEL_SECUNDARIA).set_index("variante")
    assert s.loc["malestar_3", "pct"] == 10.0 and s.loc["malestar_4", "pct"] == 5.0
    assert (s["n"] == 100).all() and "casos" not in s.columns


def test_distribucion_de_items_oculta_el_item_con_una_respuesta_rara():
    d = pd.DataFrame({"ALERTA_malestar": 0.0,
                      "SDQ5": [0] * 90 + [1] * 8 + [2] * 2,
                      "SDQ6": [0] * 60 + [1] * 30 + [2] * 10})
    t = al.distribucion_items(d, cat.NIVEL_SECUNDARIA)
    assert t[t["item"] == "SDQ5"]["pct"].isna().all()
    sdq6 = t[t["item"] == "SDQ6"]
    assert sdq6["pct"].tolist() == [60.0, 30.0, 10.0]
    assert sdq6["respuesta"].tolist() == ["No es cierto", "Algo cierto", "Muy cierto"]
    assert list(t.columns) == al.COLUMNAS_ITEMS
