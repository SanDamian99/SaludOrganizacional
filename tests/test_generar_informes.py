"""El generador de informes HTML audita antes de escribir nada."""
from scripts import generar_informes_estudiantes as gen
from src.estudiantes import catalog as cat
from tests.test_supresion_pipeline import CELDAS, NIVEL, _datos
from src.estudiantes import pipeline


def test_aborta_sin_escribir_si_la_auditoria_falla(tmp_path, monkeypatch):
    a = pipeline.analizar(_datos(CELDAS), NIVEL, n_boot=5)
    monkeypatch.setattr(gen, "cargar", lambda: {NIVEL: a})
    monkeypatch.setattr(gen.publicar, "verificar_restas",
                        lambda analisis: ["secundaria · algo delata"])
    assert gen.main([str(tmp_path)]) != 0
    assert list(tmp_path.iterdir()) == []


def test_escribe_si_la_auditoria_pasa(tmp_path, monkeypatch):
    a = pipeline.analizar(_datos(CELDAS), NIVEL, n_boot=5)
    monkeypatch.setattr(gen, "cargar", lambda: {NIVEL: a})
    assert gen.publicar.verificar_restas({NIVEL: a}) == []
    assert gen.main([str(tmp_path)]) == 0
    assert any(p.name.endswith(".html") for p in tmp_path.iterdir())
