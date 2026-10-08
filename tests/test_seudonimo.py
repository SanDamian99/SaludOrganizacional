"""Seudónimos HMAC con clave local (core/seudonimo.py)."""
import re

import pytest

from src.core import seudonimo as seud

CLAVE = "clave-de-prueba-solo-para-tests-0001"


@pytest.fixture
def con_clave(monkeypatch):
    monkeypatch.setenv(seud.VARIABLE, CLAVE)


def test_formato_del_check_de_supabase(con_clave):
    for letra in ("C", "N", "E"):
        s = seud.seudonimo("María Pérez", letra)
        assert re.fullmatch(r"^[ECN][0-9a-f]{8}$", s) and s[0] == letra


def test_normaliza_antes_de_firmar(con_clave):
    assert seud.seudonimo("  MARÍA   pérez ", "N") == seud.seudonimo("maria perez", "N")


def test_la_letra_separa_dominios(con_clave):
    assert seud.seudonimo("Ana", "C")[1:] != seud.seudonimo("Ana", "N")[1:]


def test_depende_de_la_clave():
    a = seud.seudonimo("Ana Ruiz", "C", b"una-clave-de-prueba-larga-0001")
    b = seud.seudonimo("Ana Ruiz", "C", b"otra-clave-de-prueba-larga-002")
    assert a != b


def test_vacio_no_tiene_seudonimo(con_clave):
    assert seud.seudonimo("", "C") is None and seud.seudonimo(None, "N") is None


def test_sin_clave_hay_un_error_claro(monkeypatch):
    monkeypatch.delenv(seud.VARIABLE, raising=False)
    monkeypatch.setattr("streamlit.secrets", {}, raising=False)
    with pytest.raises(seud.ClaveAusente, match="OBS360_CLAVE_HMAC"):
        seud.seudonimo("Ana", "C")


def test_una_clave_corta_no_sirve(monkeypatch):
    monkeypatch.setenv(seud.VARIABLE, "corta")
    with pytest.raises(seud.ClaveAusente):
        seud.clave()


def test_letra_desconocida(con_clave):
    with pytest.raises(ValueError):
        seud.seudonimo("Ana", "X")


def test_no_hay_clave_escrita_en_el_codigo():
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parents[1]
    for f in (raiz / "src").rglob("*.py"):
        texto = f.read_text(encoding="utf-8")
        assert "clave-de-prueba" not in texto, f
