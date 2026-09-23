"""La carpeta de datos fuente se resuelve fuera del repositorio."""
import os

from src.core import rutas


def test_la_variable_de_entorno_manda(tmp_path, monkeypatch):
    (tmp_path / "estudiantes").mkdir()
    monkeypatch.setenv("OBS360_DATOS_DIR", str(tmp_path))
    assert rutas.carpeta_datos() == str(tmp_path)
    assert rutas.carpeta_datos("estudiantes") == str(tmp_path / "estudiantes")
    # una subcarpeta inexistente devuelve la base, no una ruta inventada
    assert rutas.carpeta_datos("no_existe") == str(tmp_path)


def test_sin_variable_se_usa_la_carpeta_hermana_o_la_raiz(monkeypatch):
    monkeypatch.delenv("OBS360_DATOS_DIR", raising=False)
    base = rutas.carpeta_datos()
    hermana = os.path.join(os.path.dirname(rutas.raiz_repositorio()), rutas.CARPETA_HERMANA)
    assert base == (hermana if os.path.isdir(hermana) else rutas.raiz_repositorio())


def test_el_repositorio_no_guarda_hojas_de_calculo_en_la_raiz():
    """Los datos fuente traen nombres de personas; su sitio no es el repositorio."""
    raiz = rutas.raiz_repositorio()
    sueltos = [f for f in os.listdir(raiz) if f.lower().endswith((".xlsx", ".xls", ".csv"))]
    assert sueltos == [], sueltos
