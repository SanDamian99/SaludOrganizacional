"""Triangulación · carga local de los tres actores (sintéticos)."""
import numpy as np
import pandas as pd
import pytest

from src.triangulacion import fuentes as fu
from tests import triangulacion_sinteticos as ts

K = ts.CLAVE_PRUEBA.encode()


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    base = ts.escribir(tmp_path_factory.mktemp("tri_fuentes"))
    return base


def test_localizar_encuentra_los_tres(datos, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    disp = fu.localizar()
    assert disp.completo and len(disp.estudiantes) == 2
    assert disp.docentes.endswith(ts.ARCHIVO_DOC)
    assert len(disp.firma()) == 4


def test_sin_archivos_no_esta_completo(tmp_path, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    disp = fu.localizar()
    assert not disp.completo
    assert disp.presentes() == {"Estudiantes": False, "Cuidadores": False, "Docentes": False}
    with pytest.raises(FileNotFoundError):
        fu.cargar(disp, k=K)


def test_docentes_prefiere_el_codificado(tmp_path):
    (tmp_path / "360 - Profesores (respuestas).xlsx").write_bytes(b"x")
    (tmp_path / "Docentes_codificado.xlsx").write_bytes(b"x")
    assert fu.localizar_docentes(str(tmp_path)).endswith("Docentes_codificado.xlsx")


def test_puntuar_docentes():
    d = ts.docentes()
    p = fu.puntuar_docentes(d)
    assert list(p.columns) == ["Colegio", "DOC_PSS", "DOC_LIDER", "DOC_GRUPO", "DOC_DESGASTE"]
    assert p["Colegio"].value_counts().to_dict() == {
        "LauV": 15, "JJC": 12, "SJMEB": 11, "LaBalsa": 10, "CdP": 5, "OTRO": 2}
    pss = d[[f"PSS{i}" for i in range(1, 11)]].sum(axis=1)
    assert np.allclose(p["DOC_PSS"], pss)
    assert p["DOC_LIDER"].between(0, 5).all() and p["DOC_DESGASTE"].between(1, 7).all()


def test_pss_docente_prorratea_con_nueve_items():
    d = ts.docentes().head(2).copy()
    d.loc[0, "PSS1"] = np.nan
    d.loc[1, ["PSS1", "PSS2"]] = np.nan
    p = fu.puntuar_docentes(d)
    nueve = d.loc[0, [f"PSS{i}" for i in range(2, 11)]].sum() * 10 / 9
    assert p.loc[0, "DOC_PSS"] == pytest.approx(nueve)
    assert np.isnan(p.loc[1, "DOC_PSS"])


def test_docentes_crudos_se_codifican_en_memoria_sin_nombres():
    from tests.test_preparar_docentes import _crudo
    crudo = _crudo()
    codificado = fu.leer_docentes(crudo)
    assert fu.es_docentes_codificado(codificado)
    assert "Nombre" not in codificado.columns
    p = fu.puntuar_docentes(codificado)
    assert "SMR" in set(p["Colegio"]) and "CND" in set(p["Colegio"])


def test_estudiantes_puntuados_con_senales_y_sin_id(datos, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    e = fu.cargar_estudiantes(fu.localizar().estudiantes, K)
    assert "ID" not in e.columns and e[fu.COLUMNA_NINO].notna().all()
    for c in ("SDQ_Total", "PSSM_Total", "MSPSS_Fam", "ALERTA_malestar", "SIN_ADULTO"):
        assert c in e.columns
    assert set(e["SIN_ADULTO"].dropna().unique()) <= {0.0, 1.0}
    assert e.loc[e["PSSM7"] <= 2, "SIN_ADULTO"].eq(1).all()


def test_modulo_rancio_pide_reiniciar(monkeypatch):
    from src.estudiantes import ingest

    def viejo(rutas, niveles=None):
        raise AssertionError("no debía llamarse")
    monkeypatch.setattr(ingest, "cargar_varios", viejo)
    with pytest.raises(fu.ModuloRancio, match="Reinicie"):
        fu.cargar_estudiantes(["x.xlsx"], K)


def test_cargar_los_tres(datos, monkeypatch):
    monkeypatch.setenv("OBS360_DATOS_DIR", datos)
    f = fu.cargar(k=K)
    assert len(f.docentes) == sum(n for _, n in ts.DOCENTES)
    assert f.cuidadores["ID_cuidador"].is_unique and f.ninos["ID_nino"].is_unique
    assert "EPDS_Total" in f.cuidadores.columns and "SDQ_Total" in f.ninos.columns
    assert isinstance(f.marco("docente"), pd.DataFrame)
