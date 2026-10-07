"""La regla de cifras que no delatan dentro del pipeline, el publicador y la auditoría."""
import numpy as np
import pandas as pd
import pytest

from src.estudiantes import catalog as cat
from src.estudiantes import ingest, pipeline, publicar, scoring, supresion
from tests.test_estudiantes_comunidad import _formulario

NIVEL = cat.NIVEL_SECUNDARIA
CRUCE = supresion.AGRUPACION_CRUCE


def _datos(celdas: dict) -> pd.DataFrame:
    """{(colegio, grado): (n, k)} → filas con RCADS18 ≥ 2 en k de ellas."""
    filas = []
    for (c, g), (n, k) in celdas.items():
        for i in range(n):
            filas.append(dict(Colegio=c, Grado=g, Sexo="Mujer" if i % 2 else "Hombre",
                              Edad=13, nivel=NIVEL, RCADS18=3 if i < k else 0))
    return pd.DataFrame(filas)


CELDAS = {("A", "Sexto"): (20, 1), ("B", "Sexto"): (30, 6), ("C", "Sexto"): (15, 5),
          ("A", "Séptimo"): (20, 5)}


@pytest.fixture(scope="module")
def chico():
    return pipeline.analizar(_datos(CELDAS), NIVEL, n_boot=5)


@pytest.fixture(scope="module")
def sintetico():
    bruto, _ = ingest.cargar(_formulario())
    return pipeline.analizar(scoring.puntuar(bruto), NIVEL, n_boot=20)


def _pct(tabla, clave="RCADS18"):
    return tabla.loc[tabla["clave"] == clave, "pct"].iloc[0]


def test_la_celda_con_un_caso_no_publica_porcentaje(chico):
    assert pd.isna(_pct(chico.subgrupos[CRUCE]["A|Sexto"].cortes))
    assert pd.isna(chico.subgrupos[CRUCE]["A|Sexto"].cortes["casos"].iloc[0])


def test_el_grado_obliga_a_ocultar_otra_celda(chico):
    sexto = [k for k in ("B|Sexto", "C|Sexto")
             if pd.isna(_pct(chico.subgrupos[CRUCE][k].cortes))]
    assert sexto, "una sola celda oculta en Sexto se deduciría por resta"


def test_lo_que_queda_publicado_cumple_la_regla_y_la_auditoria_pasa(chico):
    assert supresion.auditar(chico) == []
    assert not pd.isna(_pct(chico.cortes))


def test_la_auditoria_detecta_una_cifra_destapada(chico):
    import copy
    a = copy.deepcopy(chico)
    t = a.subgrupos[CRUCE]["A|Sexto"].cortes
    t.loc[t["clave"] == "RCADS18", "pct"] = 5.0
    assert supresion.auditar(a)
    assert publicar.verificar_restas({NIVEL: a})


def test_el_publicador_no_publica_casos_y_deja_nulo_lo_suprimido(chico):
    filas = publicar.aplanar({NIVEL: chico})
    cortes = [f for f in filas if f["tipo"] in ("corte", "corte_grupo")]
    assert cortes
    assert all("casos" not in f["detalle"] for f in cortes)
    celda = [f for f in cortes if f["grupo"] == "A|Sexto"]
    assert celda and celda[0]["valor"] is None and celda[0]["ic_inf"] is None
    assert publicar.verificar_restas({NIVEL: chico}) == []


def test_verificar_rechaza_filas_con_casos():
    fila = publicar._fila(NIVEL, "corte", "RCADS18", 20, 10.0, casos=2)
    with pytest.raises(publicar.PublicacionInsegura):
        publicar.verificar([fila])


def test_en_el_formulario_sintetico_todo_lo_publicado_cumple(sintetico):
    assert supresion.auditar(sintetico) == []
    assert publicar.verificar_restas({NIVEL: sintetico}) == []
    for f in publicar.aplanar({NIVEL: sintetico}):
        if f["tipo"] in ("banda", "banda_grupo") and f["valor"] is not None:
            pcts = [f["detalle"][f"pct_b{i}"] for i in range(4)]
            ks = [round(p * f["n"] / 100) for p in pcts]
            assert all(supresion.MIN_CASOS <= k <= f["n"] - supresion.MIN_CASOS for k in ks)
        if f["tipo"] in ("banda", "banda_grupo") and f["valor"] is None:
            assert not any(f"pct_b{i}" in f["detalle"] for i in range(4))


# ── contrastes ─────────────────────────────────────────────────────────────
def _contraste(k_bajo, n_bajo, k_alto, n_alto):
    return dict(resultado="RCADS_Dep", resultado_etiqueta="Depresión",
                protector="MSPSS_Fam", protector_etiqueta="Apoyo de la familia",
                umbral="decil más alto (P90)",
                pct_tercil_bajo=round(100 * k_bajo / n_bajo, 1), ic_bajo=(1.0, 2.0),
                n_bajo=n_bajo, k_bajo=k_bajo,
                pct_tercil_alto=round(100 * k_alto / n_alto, 1), ic_alto=(1.0, 2.0),
                n_alto=n_alto, k_alto=k_alto, razon=2.0)


def test_contraste_con_un_tercil_de_pocos_casos_se_suprime_entero():
    lista = [_contraste(6, 30, 1, 30), _contraste(6, 30, 4, 30)]
    supresion.suprimir_contrastes(lista)
    malo, bueno = lista
    assert malo["suprimido"] is True
    for campo in ("pct_tercil_bajo", "pct_tercil_alto", "razon", "ic_bajo", "ic_alto",
                  "k_bajo", "k_alto"):
        assert malo[campo] is None
    assert not bueno.get("suprimido")


def test_el_publicador_no_sube_contrastes_suprimidos(chico):
    import copy
    a = copy.deepcopy(chico)
    a.contrastes = [_contraste(6, 30, 1, 30)]
    supresion.suprimir_contrastes(a.contrastes)
    s = a.subgrupos["Colegio"]["B"]
    s.contrastes = [_contraste(6, 30, 2, 30)]
    supresion.suprimir_contrastes(s.contrastes)
    filas = publicar.aplanar({NIVEL: a})
    assert not [f for f in filas if f["tipo"] in ("contraste", "contraste_grupo")]


def test_solapamiento_con_pocos_casos_no_se_publica():
    from src.estudiantes import stats
    n = 40
    d = pd.DataFrame({"banda_SDQ_Total": [3] * 2 + [0] * (n - 2),
                      "ARI_Total": [5] * 2 + [0] * (n - 2)})
    assert stats.solapamiento(d) == {}
    rng = np.random.default_rng(3)
    d = pd.DataFrame({"banda_SDQ_Total": rng.integers(0, 4, 200),
                      "ARI_Total": rng.integers(0, 8, 200)})
    assert stats.solapamiento(d).get("pct_ambos") is not None


# ── solapamiento: tabla 3×2 y bases iguales ────────────────────────────────
SDQ_DE_BANDA = {0: 10, 1: 16, 2: 18, 3: 25}


def _solap(celdas, extra_sin_ari=0):
    """celdas = [(banda, n, k_ari_alto)]; `extra_sin_ari` filas con SDQ y sin ARI."""
    filas = []
    for b, n, k in celdas:
        for i in range(n):
            filas.append(dict(SDQ_Total=SDQ_DE_BANDA[b], banda_SDQ_Total=b,
                              ARI_Total=4 if i < k else 0))
    for _ in range(extra_sin_ari):
        filas.append(dict(SDQ_Total=25, banda_SDQ_Total=3, ARI_Total=np.nan))
    return pd.DataFrame(filas)


def test_solapamiento_exige_la_tabla_3x2_completa():
    from src.estudiantes import stats
    # repro de la revisión: en la banda 1 solo 1 con ARI alto
    d = _solap([(0, 30, 6), (1, 12, 1), (2, 9, 4), (3, 9, 4)], extra_sin_ari=1)
    assert stats.solapamiento(d) == {}


def test_solapamiento_con_bases_distintas_omite_marginales_y_condicionados():
    from src.estudiantes import stats
    d = _solap([(0, 30, 6), (1, 12, 4), (2, 9, 4), (3, 9, 4)], extra_sin_ari=1)
    s = stats.solapamiento(d)
    assert s.get("pct_ambos") is not None and s.get("pct_alguno") is not None
    for clave in ("pct_sdq_alto", "pct_ari_alto", "pct_ari_alto_si_sdq_alto",
                  "pct_ari_alto_si_sdq_promedio"):
        assert clave not in s
    completo = stats.solapamiento(_solap([(0, 30, 6), (1, 12, 4), (2, 9, 4), (3, 9, 4)]))
    assert "pct_ari_alto_si_sdq_promedio" in completo and "pct_sdq_alto" in completo


def _con_colegios(d):
    d = d.copy().reset_index(drop=True)
    d["Colegio"] = ["A" if i % 2 else "B" for i in range(len(d))]
    d["Grado"] = "Sexto"
    d["Sexo"] = ["Mujer" if i % 3 else "Hombre" for i in range(len(d))]
    d["Edad"] = [12 + i % 4 for i in range(len(d))]
    d["nivel"] = NIVEL
    # un protector con variación: el modelo del ARI necesita algún predictor
    d["MSPSS_Fam"] = np.random.default_rng(5).uniform(1, 5, len(d)).round(2)
    return d


def test_la_auditoria_revisa_el_solapamiento():
    import copy
    a = pipeline.analizar(
        _con_colegios(_solap([(0, 30, 6), (1, 12, 4), (2, 9, 4), (3, 9, 4)],
                             extra_sin_ari=1)), NIVEL, n_boot=5)
    assert not [p for p in supresion.auditar(a) if "solapamiento" in p]
    malo = copy.deepcopy(a)
    malo.solapamiento["pct_sdq_alto"] = 30.0          # bases distintas: prohibido
    assert [p for p in supresion.auditar(malo) if "solapamiento" in p]
    b = pipeline.analizar(
        _con_colegios(_solap([(0, 30, 6), (1, 12, 1), (2, 9, 4), (3, 9, 4)])), NIVEL, n_boot=5)
    assert b.solapamiento == {}
    malo = copy.deepcopy(b)
    malo.solapamiento = dict(n=60, pct_ambos=13.3)    # tabla 3×2 con una casilla de 1
    assert [p for p in supresion.auditar(malo) if "solapamiento" in p]


# ── medias de ítems con corte publicado (PSSM7, adulto de confianza) ──────
def _pssm7(celdas):
    """{(colegio, grado): (n, k)} con PSSM7 = 1 (sin adulto) en k filas y 4 en el resto."""
    filas = []
    for (c, g), (n, k) in celdas.items():
        for i in range(n):
            filas.append(dict(Colegio=c, Grado=g, Sexo="Mujer" if i % 2 else "Hombre",
                              Edad=13, nivel=NIVEL, PSSM7=1 if i < k else 4))
    return pd.DataFrame(filas)


def _items(obj):
    t = obj.items_pssm
    return set() if t is None or t.empty else set(t["item"])


def test_cota_de_un_item_con_corte():
    # PSSM7 de 1 a 5, caso = ≤ 2. Media 4,9 en 20: a lo sumo 0 casos.
    assert supresion.item_delata("PSSM7", 4.9, 20)
    assert supresion.item_delata("PSSM7", 1.1, 20)     # casi todos son caso
    assert not supresion.item_delata("PSSM7", 3.5, 20)
    assert not supresion.item_delata("PSSM_otro", 4.9, 20)
    assert supresion.cotas_item("PSSM7", 4.0, 20) == (6, 20)


def test_la_media_del_item_se_omite_donde_su_corte_se_suprime():
    a = pipeline.analizar(_pssm7(CELDAS), NIVEL, n_boot=5)
    oculta = a.subgrupos[CRUCE]["A|Sexto"]
    assert pd.isna(_pct(oculta.cortes, "PSSM7"))
    assert "PSSM7" not in _items(oculta)
    publicados = [o for grupos in a.subgrupos.values() for o in grupos.values()
                  if not pd.isna(_pct(o.cortes, "PSSM7"))]
    assert publicados and all("PSSM7" in _items(o) for o in publicados)
    for f in publicar.aplanar({NIVEL: a}):
        if f["tipo"] in ("item", "item_grupo") and f["clave"] == "PSSM7":
            assert f["grupo"] != "A|Sexto"
    assert supresion.auditar(a) == []


def test_la_auditoria_ve_una_media_de_item_que_acota_los_casos():
    import copy
    a = pipeline.analizar(_pssm7(CELDAS), NIVEL, n_boot=5)
    malo = copy.deepcopy(a)
    oculta = malo.subgrupos[CRUCE]["A|Sexto"]
    oculta.items_pssm = pd.concat([oculta.items_pssm, pd.DataFrame(
        [dict(item="PSSM7", M=3.85, DE=0.67, n=20)])], ignore_index=True)
    assert [p for p in supresion.auditar(malo) if "PSSM7" in p]


def test_aplicar_dos_veces_no_cambia_nada(chico):
    import copy
    a = copy.deepcopy(chico)
    assert supresion.aplicar(a) == {}
    pd.testing.assert_frame_equal(a.cortes, chico.cortes)
    for col, grupos in chico.subgrupos.items():
        for g, s in grupos.items():
            pd.testing.assert_frame_equal(a.subgrupos[col][g].cortes, s.cortes)


def test_partes_por_familia_ignora_las_ya_suprimidas(chico):
    oculta = chico.subgrupos[CRUCE]["A|Sexto"]
    assert "RCADS18" not in supresion.partes_por_familia(oculta.cortes, oculta.bandas)


def test_el_mensaje_de_rechazo_nombra_los_casos_pequenos(chico, monkeypatch):
    monkeypatch.setattr(publicar, "verificar_restas", lambda analisis: ["x · y"])
    with pytest.raises(publicar.PublicacionInsegura) as exc:
        publicar.publicar({NIVEL: chico}, cliente=object())
    texto = str(exc.value)
    assert f"menos de {supresion.MIN_CASOS} casos" in texto
    assert f"menos de {cat.MIN_GROUP_N}" in texto


def test_la_ayuda_del_ensayo_dice_que_el_json_se_escribe_igual():
    import io
    from contextlib import redirect_stdout
    salida = io.StringIO()
    with redirect_stdout(salida), pytest.raises(SystemExit):
        publicar.main(["--help"])
    assert "aunque la auditoría falle" in " ".join(salida.getvalue().split())
