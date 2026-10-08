"""Cuidadores 360 · ingesta (spec §3.2, §5.5): formato, privacidad, edad, grado, ola e hijo 2."""
import numpy as np
import pandas as pd
import pytest

from src.core.texto import norm_txt
from src.cuidadores import catalog as cat
from src.cuidadores import ingest
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(cs.formulario(), k=K)


# ══ Formato ═════════════════════════════════════════════════════════════════
def test_un_archivo_con_otro_orden_no_se_carga():
    df = cs.formulario()
    cols = list(df.columns)
    cols[35], cols[36] = cols[36], cols[35]
    with pytest.raises(ingest.FormatoInesperado, match="columna 35"):
        ingest.cargar(df.set_axis(cols, axis=1), k=K)


def test_sin_clave_no_se_carga(monkeypatch):
    from src.core import seudonimo as seud
    monkeypatch.delenv(seud.VARIABLE, raising=False)
    monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    with pytest.raises(seud.ClaveAusente):
        ingest.cargar(cs.formulario())


# ══ Privacidad ══════════════════════════════════════════════════════════════
def _texto_de(df: pd.DataFrame) -> str:
    return df.astype(str).to_csv(index=False) + " ".join(map(str, df.columns))


def test_ni_nombres_ni_telefono_en_ninguna_salida(carga):
    textos = [_texto_de(carga.respuestas), _texto_de(carga.ninos),
              str(carga.informe.como_dict())]
    for t in textos:
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in t
    for df in (carga.respuestas, carga.ninos):
        assert not [c for c in df.columns if "nombre" in c.lower() and c != "Colegio_nombre"]
        assert not [c for c in df.columns if "telef" in norm_txt(c)]


def test_los_seudonimos_tienen_el_formato_de_supabase(carga):
    assert carga.respuestas["ID_cuidador"].str.fullmatch(r"C[0-9a-f]{8}").all()
    assert carga.ninos["ID_nino"].str.fullmatch(r"N[0-9a-f]{8}").all()


def test_el_colegio_no_reconocido_no_lleva_su_texto(carga):
    otros = carga.ninos[carga.ninos["Colegio"] == "OTRO"]
    assert len(otros) and (otros["Colegio_nombre"] == "Otro colegio").all()
    assert "Inventado" not in _texto_de(carga.ninos)


# ══ Consentimiento, ola y quién responde ═══════════════════════════════════
def test_consentimiento(carga):
    assert carga.informe.sin_consentimiento == 1
    assert carga.informe.respuestas_validas == carga.informe.filas_archivo - 1


def test_ola_por_ano_de_la_marca_temporal(carga):
    assert set(carga.respuestas["Ola"]) == {"2025", "2026"}
    s = pd.Series(["2025-09-15 09:05:00", "15/09/2025 9:05:00", "2026-03-10 08:00:00"])
    assert ingest._ola(ingest.fecha(s)).tolist() == ["2025", "2025", "2026"]


@pytest.mark.parametrize("texto,esperado", [
    ("Mamá", cat.MAMA), ("mama", cat.MAMA), ("Papá", cat.PAPA),
    ("Abuelo o abuela", cat.OTRO), ("Tío o tía", cat.OTRO), ("Otro cuidador principal", cat.OTRO),
])
def test_quien_responde(texto, esperado):
    assert ingest.quien(texto) == esperado


# ══ Edad y grado ════════════════════════════════════════════════════════════
@pytest.mark.parametrize("texto,valor,estado", [
    ("7", 7.0, "ok"), ("10 años", 10.0, "ok"), ("12 anos", 12.0, "ok"), ("9años", 9.0, "ok"),
    ("diez", np.nan, "no_numerica"), ("10 años 5 meses", np.nan, "no_numerica"),
    ("19", np.nan, "fuera_de_rango"), ("3", np.nan, "fuera_de_rango"), ("", np.nan, "vacia"),
])
def test_edad_del_nino(texto, valor, estado):
    v, e = ingest.edad(texto)
    assert e == estado and (np.isnan(valor) and np.isnan(v) or v == valor)


VARIANTES_CURSO = [(t, g) for g, ts in cs.CURSOS.items() if g != "fuera" for t in ts] + [
    ("Sexto 602", "Sexto"), ("501", "Quinto"), ("1002", "Décimo"), ("5-2", "Quinto"),
    ("10.1", "Décimo"), ("Grado quinto", "Quinto"), ("4D", "Cuarto"), ("7mo", "Séptimo"),
    ("9no", "Noveno"), ("1ero", None), ("6to B", "Sexto"), ("Octavo jornada tarde", "Octavo"),
]


@pytest.mark.parametrize("texto,grado", VARIANTES_CURSO)
def test_curso_libre_a_grado_del_estudio(texto, grado):
    g, detalle, estado = ingest.grado_desde_curso(texto)
    if grado is None:
        assert estado == cat.ESTADO_FUERA and pd.isna(g)
    else:
        assert g == grado and detalle == grado and estado == cat.ESTADO_ESTUDIO


@pytest.mark.parametrize("texto,detalle", [
    ("Once", "Once"), ("1101", "Once"), ("11", "Once"), ("Transición", "Transición"),
    ("Jardín", "Transición"), ("Tercero", "Tercero"), ("Primero", "Primero"), ("201", "Segundo"),
])
def test_grados_fuera_del_rango_del_estudio(texto, detalle):
    g, d, estado = ingest.grado_desde_curso(texto)
    assert pd.isna(g) and d == detalle and estado == cat.ESTADO_FUERA


@pytest.mark.parametrize("texto", ["", "???", "grupo azul", "25", "A1"])
def test_curso_sin_resolver(texto):
    g, d, estado = ingest.grado_desde_curso(texto)
    assert pd.isna(g) and d == cat.SIN_DATO and estado == cat.ESTADO_SIN_DATO


# ══ Hijo 2 ══════════════════════════════════════════════════════════════════
def test_el_hijo_2_es_otra_fila_de_nino(carga):
    inf = carga.informe
    assert inf.hijo2 > 0
    assert inf.filas_nino == inf.respuestas_validas + inf.hijo2
    assert set(carga.ninos["Orden_hijo"]) == {1, 2}


# ══ Conversión de respuestas ════════════════════════════════════════════════
def test_columna_6_es_faltante_declarado(carga):
    assert carga.informe.respuestas_columna6_pss == 2
    assert "PSS" not in carga.informe.etiquetas_no_mapeadas
    assert carga.respuestas[cat.PSS.columnas].isna().sum().sum() == 2


def test_una_etiqueta_desconocida_se_cuenta_sin_mostrarla():
    df = cs.formulario()
    df.iloc[3, cat.APQ.inicio] = "Respuesta rara de prueba"
    c = ingest.cargar(df, k=K)
    assert c.informe.etiquetas_no_mapeadas == {"APQ": 1}
    assert "Respuesta rara" not in str(c.informe.como_dict())


def test_rangos_de_los_items(carga):
    r = carga.respuestas
    for b in cat.BLOQUES_CUIDADOR:
        v = r[b.columnas].stack().dropna()
        assert v.between(b.valor_min, b.valor_max).all(), b.key
    n = carga.ninos
    assert n[cat.bloque_sdq(1).columnas].stack().dropna().between(0, 2).all()
    assert n[cat.bloque_ari(1).columnas].stack().dropna().between(0, 2).all()


def test_el_ari_no_existe_en_la_ola_2025(carga):
    n = carga.ninos
    assert n.loc[n["Ola"] == "2025", cat.bloque_ari(1).columnas].isna().all().all()
    assert carga.informe.cobertura_ari["hijo 1"] > 0


def test_enunciados_de_los_items(carga):
    assert len(carga.informe.enunciados["APQ"]) == 25
    assert ingest.enunciado(" [Grita a su hijo(a) cuando se ha portado mal]") == \
        "Grita a su hijo(a) cuando se ha portado mal"
