"""
Fase 1 de Docentes con el archivo real (propuesta 10-oct-2026, §5.2 y §5.3).
Se omite si falta el archivo. Solo agregados del municipio: medias, N, α y %
por banda; ninguna prueba imprime filas ni identificadores.

Lo que fija: las subescalas corregidas reproducen los α y las medias de la
propuesta; los totales viejos con polaridad mezclada tenían α más bajo;
«Bienestar psicosocial» vuelve a N = 189 (solo 2025) sin imputar; «hijos = 10»
desaparece al cargar.
"""
import pandas as pd
import pytest

from src.core.rutas import carpeta_datos
from src.data import loader
from src.data.processor import ExcelProcessor
from src.docentes import catalogo as cat
from src.docentes import scoring
from src.triangulacion.fuentes import localizar_docentes


@pytest.fixture(scope="module")
def cargado():
    ruta = localizar_docentes(carpeta_datos("docentes"))
    if not ruta:
        pytest.skip("falta el archivo codificado de docentes")
    df, report = ExcelProcessor().process_complex_excel(ruta)
    df, report = loader._posprocesar(df, report)
    if len(df) != 479:
        pytest.skip("el archivo no es la versión de 479 docentes de la propuesta")
    return df, report


@pytest.fixture(scope="module")
def resumen(cargado):
    return scoring.resumen(cargado[0])


def test_sin_imputar_y_sin_el_codigo_de_hijos(cargado):
    df, report = cargado
    assert report["n_cells_imputed"] == 0
    assert report["codigos_faltantes"] == {"(SD)Numero de hijos": 69}
    hijos = next(c for c in df.columns if "hijos" in c.lower())
    assert df[hijos].max() <= 9 and df[hijos].isna().sum() >= 69
    assert scoring.codificacion(df) == 1          # el archivo de Storage aún es el viejo


# (clave, N, media, α) de §5.2–5.3 de la propuesta
ESPERADO = [
    ("PSS", 479, 14.29, 0.81), ("BTA", 479, 1.89, 0.91),
    ("MT_Control", 479, 2.94, 0.68), ("MT_Demandas", 479, 1.35, 0.83),
    ("CL", 479, 2.82, 0.97), ("AP", 479, 2.93, 0.95),
    ("CR_Claridad", 479, 4.45, 0.89), ("CR_Conflicto", 479, 1.55, 0.84),
    ("CO", 479, 2.51, 0.88), ("RO", 479, 1.52, 0.92),
    ("Conf_FaTr", 479, 1.63, 0.88), ("Conf_TrFa", 479, 2.28, 0.95),
    ("Comp", 479, 4.25, 0.85), ("DefO", 479, 4.15, 0.87), ("Sat", 479, 4.27, 0.79),
    ("IR", 479, 0.72, 0.80), ("BLG_Psicoso", 189, 6.00, 0.94),
    ("BLG_Som", 479, 3.79, 0.89), ("BLG_Desg", 479, 4.00, 0.94), ("BLG_Alie", 479, 2.47, 0.91),
    ("Descon", 479, 3.05, 0.93), ("ISTAS_Exig", 479, 11.48, 0.77), ("ISTAS_TA", 479, 25.97, 0.76),
    ("ERS_ACP", 479, 0.77, 0.83), ("ERS_CON", 479, 0.91, 0.70), ("ERS_CLA", 479, 0.72, 0.73),
    ("ERS_MET", 479, 0.75, 0.54), ("IRI_PT", 479, 2.54, 0.70), ("IRI_EC", 479, 2.79, 0.60),
]


@pytest.mark.parametrize("clave,n,media,alfa", ESPERADO)
def test_medias_n_y_alfa_de_la_propuesta(resumen, clave, n, media, alfa):
    r = resumen[clave]
    assert r["n"] == n
    assert r["media"] == pytest.approx(media, abs=0.01)
    assert r["alfa"] == pytest.approx(alfa, abs=0.01)
    assert r["ic_inf"] < r["media"] < r["ic_sup"]


def test_los_totales_viejos_mezclaban_polaridad(cargado):
    """α de los totales antiguos (ítems tal como están en el archivo) frente a las subescalas."""
    df = cargado[0]
    viejo = {
        "MT": scoring.cronbach_alpha(df[[f"MT{i}" for i in range(1, 8)]]),
        "CR": scoring.cronbach_alpha(df[[f"CR{i}" for i in range(1, 8)]]),
        "IR": scoring.cronbach_alpha(df[[f"IR{i}" for i in range(1, 5)]]),
        "PRPS_CE": scoring.cronbach_alpha(df[[f"PRPS_CE{i}" for i in range(1, 17)]]),
        "ERS_ACP": scoring.cronbach_alpha(df[[f"ERS_ACP{i}" for i in range(1, 7)]]),
    }
    assert viejo["MT"] == pytest.approx(0.53, abs=0.01)
    assert viejo["CR"] == pytest.approx(0.59, abs=0.01)
    assert viejo["IR"] == pytest.approx(0.47, abs=0.01)
    assert viejo["PRPS_CE"] == pytest.approx(0.47, abs=0.01)
    assert viejo["ERS_ACP"] == pytest.approx(0.63, abs=0.01)
    r = scoring.resumen(df)
    assert min(r["MT_Control"]["alfa"], r["MT_Demandas"]["alfa"]) > viejo["MT"]
    assert min(r["CR_Claridad"]["alfa"], r["CR_Conflicto"]["alfa"]) > viejo["CR"]
    assert r["IR"]["alfa"] > viejo["IR"] + 0.3
    assert min(r["ISTAS_Exig"]["alfa"], r["ISTAS_TA"]["alfa"]) > viejo["PRPS_CE"] + 0.25
    assert r["ERS_ACP"]["alfa"] > viejo["ERS_ACP"] + 0.15


def test_zonas_y_bandas_del_municipio(resumen):
    def banda(clave, etiqueta):
        return next(b for b in resumen[clave]["bandas"] if b["etiqueta"] == etiqueta)

    assert resumen["PSS"]["zona"] == cat.ZONA_INTERMEDIA
    assert banda("PSS", "Estrés bajo")["pct"] == pytest.approx(43.6, abs=0.1)
    assert banda("PSS", "Estrés moderado")["pct"] == pytest.approx(54.3, abs=0.1)
    assert banda("PSS", "Estrés alto")["pct"] == pytest.approx(2.1, abs=0.1)
    assert resumen["BTA"]["zona"] == cat.ZONA_FAVORABLE
    en_riesgo = banda("BTA", "En riesgo")["pct"] + banda("BTA", "Riesgo muy alto")["pct"]
    assert en_riesgo == pytest.approx(12.3, abs=0.2)
    assert banda("BTA", "Riesgo muy alto")["pct"] == pytest.approx(5.4, abs=0.1)
    assert banda("ISTAS_Exig", "Desfavorable")["pct"] == pytest.approx(58.9, abs=0.1)
    assert resumen["ISTAS_Exig"]["zona"] == cat.ZONA_VIGILAR
    assert banda("ISTAS_TA", "Favorable")["pct"] == pytest.approx(55.5, abs=0.1)
    assert banda("ISTAS_TA", "Desfavorable")["pct"] == pytest.approx(16.3, abs=0.1)
    # Sin corte: tercio de la escala teórica
    assert resumen["RO"]["zona"] == cat.ZONA_VIGILAR
    assert resumen["CR_Claridad"]["zona"] == cat.ZONA_FAVORABLE
    assert resumen["BLG_Desg"]["zona"] == cat.ZONA_INTERMEDIA
    for b in resumen["BTA"]["bandas"] + resumen["ISTAS_Exig"]["bandas"]:
        assert b["comprobar"] is True


def test_bienestar_psicosocial_solo_2025(cargado):
    df = cargado[0]
    p = scoring.puntuar(df)
    # ExcelProcessor deja la versión como número (2025 / 2026) al numerizar el texto.
    version = df[cat.COLUMNA_VERSION].astype(str).str[:4]
    assert p.loc[version == "2026", "BLG_Psicoso"].isna().all()
    assert p.loc[version == "2025", "BLG_Psicoso"].notna().sum() == 189


def test_el_archivo_regenerado_puntua_igual_que_el_de_storage(cargado):
    """La codificación 2 (script nuevo) y la 1 (Storage) dan los mismos puntajes."""
    df = cargado[0]
    v2 = scoring.normalizar_codificacion(df)
    assert scoring.codificacion(v2) == 2
    pd.testing.assert_frame_equal(scoring.puntuar(df), scoring.puntuar(v2))
