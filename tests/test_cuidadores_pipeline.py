"""Cuidadores 360 · pipeline con dos marcos, base publicable y supresión (spec §4, §5.5)."""
import copy

import numpy as np
import pandas as pd
import pytest

from src.cuidadores import catalog as cat
from src.cuidadores import ingest, pipeline
from src.estudiantes import catalog as cat_est
from src.estudiantes import pipeline as pipe_est
from src.estudiantes import supresion
from tests import cuidadores_sinteticos as cs

K = cs.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def carga():
    return ingest.cargar(cs.formulario(), k=K)


@pytest.fixture(scope="module")
def ac(carga):
    return pipeline.analizar(carga, n_boot=20)


def test_dos_marcos_con_la_clase_de_estudiantes(ac):
    assert isinstance(ac.cuidador, pipe_est.Analisis) and isinstance(ac.nino, pipe_est.Analisis)
    assert ac.cuidador.nivel == cat.MARCO_CUIDADOR and ac.nino.nivel == cat.MARCO_NINO
    assert set(ac.marcos) == {cat.MARCO_CUIDADOR, cat.MARCO_NINO}
    assert ac.cuidador.n == ac.informe.cuidadores_distintos
    assert ac.nino.n == ac.informe.ninos_unicos
    assert ac.olas == ["2025", "2026"]


def test_grupos_publicados_segun_la_configuracion_sintetica(ac):
    for a in ac.marcos.values():
        sub = a.subgrupos
        assert set(sub["Colegio×Grado"]) == {"LauV|Quinto", "LauV|Sexto", "LauV|Octavo",
                                             "JJC|Décimo", "JJC|Cuarto"}
        # SJMEB entero (sin celdas), La Balsa entera (sin grado del estudio)
        assert set(sub["Colegio"]) == {"LauV", "JJC", "SJMEB", "LaBalsa"}
        assert "CdP" not in sub["Colegio"] and "OTRO" not in sub["Colegio"]
        assert not a.base.incluye_resto          # CdP 4 + OTRO 3 no llegan a 10


def test_todo_grupo_publicado_tiene_10_o_mas_cuidadores_distintos(ac):
    for a in ac.marcos.values():
        d = a.datos
        for agrupacion, grupos in a.subgrupos.items():
            for grupo, s in grupos.items():
                assert s.muestra["n_cuidadores"] >= cat.MIN_GROUP_N, (agrupacion, grupo)
        for _, idx in [*a.base.celdas.items(), *a.base.colegios.items(), *a.base.grados.items()]:
            assert d.loc[idx, "ID_cuidador"].nunique() >= cat.MIN_GROUP_N


def test_ninguna_proporcion_publicada_delata(ac):
    for a in ac.marcos.values():
        assert a.supresion_aplicada
        objetos = [a] + [s for g in a.subgrupos.values() for s in g.values()]
        for o in objetos:
            t = o.cortes
            if t is None or t.empty:
                continue
            for _, f in t[t["pct"].notna()].iterrows():
                assert supresion.proporcion_publicable(f["casos"], f["n"]), (o.n, f["clave"])


def test_cortes_y_bandas_por_marco(ac):
    claves_c = set(ac.cuidador.cortes["clave"])
    assert {"EPDS_Total", "EPDS_Autolesion", "APQ_Fisico", "APQ_Grito"} <= claves_c
    assert set(ac.nino.cortes["clave"]) == set(cat_est.BANDS_PARENT)
    assert set(ac.nino.bandas["clave"]) == set(cat_est.BANDS_PARENT)
    assert ac.cuidador.bandas.empty


def test_puntuaciones_disponibles(ac):
    assert set(ac.cuidador.descriptivos["clave"]) == set(cat.CLAVES_CUIDADOR)
    assert set(ac.nino.descriptivos["clave"]) == set(cat.CLAVES_NINO)


def test_los_datos_enmascarados_no_llevan_nombres_ni_telefono(ac):
    for a in ac.marcos.values():
        texto = a.datos.astype(str).to_csv()
        for prohibido in cs.textos_prohibidos():
            assert prohibido not in texto


def test_filtro_de_ola(carga):
    """La ola es un subconjunto del total de «Todas»: se deduplica, se arma la base y se filtra."""
    todas = pipeline.analizar(carga, n_boot=5)
    a25 = pipeline.analizar(carga, ola="2025", n_boot=10)
    a26 = pipeline.analizar(carga, ola="2026", n_boot=10)
    assert a25.ola == "2025" and set(a25.cuidador.datos["Ola"]) == {"2025"}
    assert set(a26.nino.datos["Ola"]) == {"2026"}
    for marco in (cat.MARCO_CUIDADOR, cat.MARCO_NINO):
        nivel = len(todas.marcos[marco].base.nivel)
        assert a25.marcos[marco].n + a26.marcos[marco].n == nivel
    ids_t = set(todas.cuidador.datos["ID_cuidador"])
    assert set(a25.cuidador.datos["ID_cuidador"]) <= ids_t


def test_items_locales_sin_conteos(ac):
    assert len(ac.items_apq) == 25 and "casos" not in ac.items_apq.columns
    assert len(ac.items_estres) == 39 and "casos" not in ac.items_estres.columns
    notas = ac.items_estres.set_index("item")["nota"]
    assert notas[22] == "elección forzada partida" and notas[36] == "redactado en positivo"


def test_localizar_formulario(tmp_path):
    assert pipeline.localizar_formulario(str(tmp_path)) is None
    ruta = cs.escribir(tmp_path / "Cuidando al Cuidador - Parentalidad (respuestas).xlsx")
    (tmp_path / "otro.xlsx").write_bytes(b"")
    assert pipeline.localizar_formulario(str(tmp_path)) == ruta
    assert pipeline.localizar_formulario(str(tmp_path / "no-existe")) is None


def test_cargar_y_analizar_desde_disco(tmp_path, monkeypatch):
    monkeypatch.setenv("OBS360_CLAVE_HMAC", cs.CLAVE_PRUEBA)
    ruta = cs.escribir(tmp_path / "Cuidando al Cuidador (respuestas).xlsx")
    ac = pipeline.cargar_y_analizar(ruta, n_boot=10)
    assert ac.cuidador.n == ac.informe.cuidadores_distintos


def test_sin_archivo_hay_un_error_claro(monkeypatch, tmp_path):
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Cuidando al Cuidador"):
        pipeline.cargar_y_analizar()


def test_estudiantes_no_cambia_al_correr_cuidadores(carga):
    """Regresión: cuidadores lee el catálogo de estudiantes pero nunca lo modifica."""
    antes = copy.deepcopy((cat_est.BANDS_PARENT, cat_est.BANDS_SELF, cat_est.COMPUESTAS,
                           cat_est.MIN_GROUP_N, cat_est.ORDEN_GRADOS_PRI,
                           cat_est.ORDEN_GRADOS_SEC, [e.key for e in cat_est.ESCALAS]))
    pipeline.analizar(carga, n_boot=5)
    despues = (cat_est.BANDS_PARENT, cat_est.BANDS_SELF, cat_est.COMPUESTAS,
               cat_est.MIN_GROUP_N, cat_est.ORDEN_GRADOS_PRI, cat_est.ORDEN_GRADOS_SEC,
               [e.key for e in cat_est.ESCALAS])
    assert antes == despues


def test_items_publicables_quita_el_conteo_y_los_pct_que_delatan():
    t = pd.DataFrame({"item": [1, 2, 3], "n": [20, 20, 20], "casos": [10, 2, 18],
                      "pct": [50.0, 10.0, 90.0]})
    p = pipeline._items_publicables(t)
    assert "casos" not in p.columns
    assert p["pct"].tolist()[0] == 50.0 and p["pct"].isna().tolist()[1:] == [True, True]


# ── I1: la media de un ítem no deshace su % suprimido ─────────────────────
def test_cota_de_media_con_casos_altos():
    # APQ de 1 a 5, caso = «a veces» (3) o más. Media 1,02 en 85: a lo sumo 0 casos.
    assert supresion.media_delata(1.02, 85, 1, 5, 3, casos_altos=True)
    assert supresion.media_delata(4.98, 85, 1, 5, 3, casos_altos=True)   # casi todos caso
    assert not supresion.media_delata(3.0, 85, 1, 5, 3, casos_altos=True)
    # Estrés parental: caso = «de acuerdo» (4) o más.
    assert supresion.cotas_media(4.0, 20, 1, 5, 4, casos_altos=True) == (20, 10)
    # La versión de casos bajos es la de PSSM7 (sin cambios).
    assert supresion.cotas_media(4.0, 20, 1, 5, 2) == supresion.cotas_item("PSSM7", 4.0, 20)


def test_media_del_item_apq_no_delata_un_solo_caso():
    raw = cs.formulario()
    p = cat.APQ.inicio + 21                     # APQ22
    raw.iloc[:, p] = "Nunca"
    raw.iloc[3, p] = "A veces"                  # un solo «a veces» en todo el marco
    ac = pipeline.analizar(ingest.cargar(raw, k=K), n_boot=5)
    fila = ac.items_apq.set_index("item").loc[22]
    assert fila["n"] >= 80
    assert pd.isna(fila["pct"]) and pd.isna(fila["M"])
    # Los ítems con un % publicable conservan la media.
    otros = ac.items_apq[ac.items_apq["pct"].notna()]
    assert len(otros) and otros["M"].notna().all()


def test_items_publicables_quita_la_media_que_acota_los_casos():
    t = pd.DataFrame({"item": [1, 2], "n": [85, 40], "M": [1.02, 3.1], "casos": [1, 20],
                      "pct": [1.2, 50.0]})
    p = pipeline._items_publicables(t, umbral=3, escala=(1, 5))
    assert pd.isna(p["M"].iloc[0]) and pd.isna(p["pct"].iloc[0])
    assert p["M"].iloc[1] == 3.1 and p["pct"].iloc[1] == 50.0


# ── I2: en el marco de niños, la regla de 3 cuenta cuidadores distintos ───
def _ninos_dos_hermanos() -> pd.DataFrame:
    """3 colegios × quinto, 12 cuidadores cada uno; en LauV dos cuidadores tienen 2 hijos.

    En LauV los 3 niños en la banda «alta» del SDQ emocional son de solo 2
    cuidadores (los dos hijos del primero y el primero del segundo).
    """
    filas = []
    for col in ("LauV", "JJC", "SJMEB"):
        for i in range(12):
            for h in range(2 if (col == "LauV" and i < 2) else 1):
                filas.append(dict(ID_cuidador=f"C{col}{i}", ID_nino=f"N{col}{i}{h}",
                                  Colegio=col, Grado="Quinto", Quien="Mamá", Ola="2026",
                                  ts=pd.Timestamp("2026-03-01"), Sexo="Niña", Edad=9.0,
                                  Grado_detalle="Quinto", Orden_hijo=h + 1, _edad_estado="ok"))
    d = pd.DataFrame(filas)
    rng = np.random.default_rng(3)              # el resto varía (Kruskal-Wallis lo exige)
    for c in cat_est.SDQ.columnas:
        d[c] = rng.integers(0, 3, len(d)).astype(float)
    for i in range(1, 8):
        d[f"ARI{i}"] = rng.integers(0, 3, len(d)).astype(float)
    emo = [f"SDQ{i}" for i in cat_est.subescala("SDQ_Emo").items]
    d[emo] = 0.0

    def puntaje(ix, total):
        vals = [2] * (total // 2) + [1] * (total % 2)
        for c, v in zip(emo, vals + [0] * (5 - len(vals))):
            d.loc[ix, c] = float(v)
    for col in ("LauV", "JJC", "SJMEB"):
        for j, ix in enumerate(d.index[d["Colegio"] == col]):
            if j < 3:
                puntaje(ix, 5)          # banda alta
            elif j < 6:
                puntaje(ix, 8)          # muy alta
            elif j < 9:
                puntaje(ix, 4)          # ligeramente elevada
    return d


def _cuidadores_por_banda(d: pd.DataFrame, key: str) -> list[int]:
    b = d[key].dropna().map(lambda x: cat_est.banda_de(x, key, "parent"))
    ids = d.loc[b.index, "ID_cuidador"]
    return [int(ids[b == j].nunique()) for j in range(4)]


def test_marco_nino_cuenta_cuidadores_distintos_entre_casos():
    from src.cuidadores import scoring
    d = scoring.puntuar_ninos(_ninos_dos_hermanos())
    assert _cuidadores_por_banda(d[d["Colegio"] == "LauV"], "SDQ_Emo")[2] == 2
    a = pipeline.analizar_marco(d, cat.MARCO_NINO, n_boot=5)
    sub = a.subgrupos
    for o in (sub["Colegio"]["LauV"], sub["Colegio×Grado"]["LauV|Quinto"]):
        fila = o.bandas.set_index("clave").loc["SDQ_Emo"]
        assert pd.isna(fila["pct_b2"]) and pd.isna(fila["pct_b0"])
        assert pd.isna(o.cortes.set_index("clave").loc["SDQ_Emo", "pct"])
    # Lo publicado cumple la regla también en cuidadores distintos…
    objetos = {("total", None): a, **{("Colegio", c): s for c, s in sub["Colegio"].items()}}
    filas = {("total", None): a.base.nivel,
             **{("Colegio", c): idx for c, idx in a.base.colegios.items()}}
    for g, o in objetos.items():
        fila = o.bandas.set_index("clave").loc["SDQ_Emo"]
        if not pd.isna(fila["pct_b0"]):
            assert min(_cuidadores_por_banda(a.datos.loc[filas[g]], "SDQ_Emo")) >= 3, g
    # …y LauV no se deduce restando: total − JJC − SJMEB no puede quedar publicado entero.
    pub = [not pd.isna(o.bandas.set_index("clave").loc["SDQ_Emo", "pct_b0"])
           for o in (a, sub["Colegio"]["JJC"], sub["Colegio"]["SJMEB"])]
    assert not all(pub)


# ── C1: con una ola elegida, solo el total y solo si no se deduce el resto ─
def _carga_una_fuera(carga_ola_unica: str = "2026"):
    """Todas las respuestas en 2026 salvo un cuidador (sin repetidos) en 2025.

    Equivale a CND (Todas n = 70, ola n = 69): restar la ola de «Todas»
    dejaría ver la respuesta de una sola persona.
    """
    raw = cs.formulario()
    ts = raw.columns[0]
    raw[ts] = raw[ts].str.replace(r"^2025-09-1", "2026-03-1", regex=True)
    raw.loc[0, ts] = "2026-03-10 08:00:00"
    raw.loc[raw[ts].str.startswith("2025"), ts] = "2026-03-12 08:00:00"
    raw.loc[40, ts] = "2025-09-15 09:00:00"
    return ingest.cargar(raw, k=K)


def _publicadas(a) -> list:
    t = a.cortes
    return [] if t is None or t.empty else t.loc[t["pct"].notna(), "clave"].tolist()


def test_ola_casi_igual_a_todas_no_publica_nada():
    c = _carga_una_fuera()
    todas = pipeline.analizar(c, n_boot=5)
    ola = pipeline.analizar(c, ola="2026", n_boot=5)
    assert ola.cuidador.n == len(todas.cuidador.base.nivel) - 1
    for a in ola.marcos.values():
        assert a.subgrupos == {} and a.por_colegio.empty and a.por_grado.empty
        assert a.por_sexo.empty and a.icc == {}
        assert _publicadas(a) == []
        if not a.bandas.empty:
            assert a.bandas["pct_b0"].isna().all()
        # Solo queda la media cuya resta está vacía (el ARI existe solo en 2026: la
        # cifra de la ola es la misma que la de «Todas» y no deja ver a nadie).
        d_t = todas.marcos[a.nivel].descriptivos.set_index("clave")["n"]
        con_m = a.descriptivos[a.descriptivos["M"].notna()]
        assert all(d_t[k] == n for k, n in zip(con_m["clave"], con_m["n"]))
        assert set(con_m["clave"]) <= {"ARI_Total"}
        assert a.descriptivos.loc[a.descriptivos["M"].isna(), "DE"].isna().all()
        assert a.terciles.empty or a.terciles["corte_bajo"].isna().all()
        assert a.correlaciones.empty or (a.correlaciones["b"] == "ARI_Total").all()
        f = a.fiabilidad
        assert f.loc[f["alpha"].notna(), "clave"].isin(["ARI_Total"]).all()
    for t in (ola.items_apq, ola.items_estres):
        assert t["pct"].isna().all() and t["M"].isna().all()
    # «Todas» sí publica (la ola vacía no cambia nada en la vista general).
    assert _publicadas(todas.cuidador)


def test_ola_de_una_persona_no_publica_nada():
    ola = pipeline.analizar(_carga_una_fuera(), ola="2025", n_boot=5)
    for a in ola.marcos.values():
        assert _publicadas(a) == []
        assert a.descriptivos.empty or a.descriptivos["M"].isna().all()


def test_ola_publica_solo_el_total_y_con_complemento_seguro(carga):
    todas = pipeline.analizar(carga, n_boot=5)
    ola = pipeline.analizar(carga, ola="2026", n_boot=5)
    algo = False
    for marco, a in ola.marcos.items():
        assert a.subgrupos == {} and a.por_colegio.empty
        t = todas.marcos[marco].cortes.set_index("indicador")
        for _, f in a.cortes[a.cortes["pct"].notna()].iterrows():
            algo = True
            g = t.loc[f["indicador"]]
            assert g["n"] - f["n"] == 0 or g["n"] - f["n"] >= cat.MIN_GROUP_N, f["clave"]
            if not pd.isna(g["casos"]) and g["n"] > f["n"]:
                assert supresion.proporcion_publicable(g["casos"] - f["casos"],
                                                       g["n"] - f["n"]), f["clave"]
        d = todas.marcos[marco].descriptivos.set_index("clave")
        for _, f in a.descriptivos[a.descriptivos["M"].notna()].iterrows():
            resta = d.loc[f["clave"], "n"] - f["n"]
            assert resta == 0 or resta >= cat.MIN_GROUP_N, f["clave"]
    assert algo
