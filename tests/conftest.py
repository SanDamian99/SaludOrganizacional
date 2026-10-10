"""Configuración común de las pruebas.

La vista previa del equipo (`src.core.vista_previa`) inicia sesión en Supabase
con el usuario de carga si encuentra sus credenciales, y la máquina de quien
procesa las tiene en `.streamlit/secrets.toml`. Ninguna prueba debe tocar la
base real: aquí se corta la creación del cliente, y la prueba que necesite uno
lo inyecta (una base falsa de `tests/supabase_falso.py`).
"""
import pytest


@pytest.fixture(autouse=True)
def _vista_previa_sin_red(monkeypatch):
    try:
        from src.core import vista_previa
    except Exception:                                      # noqa: BLE001
        yield
        return

    def _sin_red(*_a, **_k):
        raise RuntimeError("las pruebas no se conectan a Supabase")

    monkeypatch.setattr(vista_previa, "_crear_cliente", _sin_red)
    vista_previa._RESPALDO.clear()
    yield
    vista_previa._RESPALDO.clear()
