"""Parámetros del mapa: lo que el equipo decide y lo que no."""
from src.geo import opciones


def test_por_defecto_ofrece_tres_capas_y_abre_en_respuestas():
    assert opciones.capas_activas() == ["respuestas", "sentirse_parte", "apoyo_social"]
    assert opciones.capa_inicial() == "respuestas"


def test_una_capa_no_permitida_se_ignora(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS", ("respuestas", "sdq_total", "rcads"))
    assert opciones.capas_activas() == ["respuestas"]


def test_sin_capas_validas_queda_respuestas(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS", ("sdq_total",))
    assert opciones.capas_activas() == ["respuestas"]


def test_capa_inicial_invalida_cae_a_la_primera_activa(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS", ("apoyo_social",))
    monkeypatch.setattr(opciones, "MAPA_CAPA_INICIAL", "respuestas")
    assert opciones.capa_inicial() == "apoyo_social"


def test_familia_nunca_ve_el_mapa_aunque_se_configure(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_ROLES", ("familia", "colegio", "municipio"))
    assert opciones.rol_ve_mapa("familia") is False
    assert opciones.rol_ve_mapa("colegio") is True


def test_municipio_y_colegio_ven_el_mapa_por_defecto():
    assert opciones.rol_ve_mapa("municipio") is True
    assert opciones.rol_ve_mapa("colegio") is True
    assert opciones.rol_ve_mapa("otro") is False


def test_en_informes_por_defecto_van_respuestas_y_sentirse_parte():
    assert opciones.MAPA_EN_INFORMES is True
    assert opciones.capas_informe() == ["respuestas", "sentirse_parte"]


def test_capas_del_informe_respetan_las_capas_activas(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS", ("respuestas",))
    assert opciones.capas_informe() == ["respuestas"]


def test_capas_del_informe_solo_permitidas(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_CAPAS_INFORME", ("sdq_total", "rcads"))
    assert opciones.capas_informe() == []
