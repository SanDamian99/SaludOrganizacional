"""Figuras del mapa: interactiva (Plotly) y estática (matplotlib, sin red)."""
import io

from src.estudiantes import catalog as cat
from src.geo import mapa_datos as md
from src.geo import mapa_figura as mf
from src.geo import opciones
from src.geo.colegios_geo import Punto

PUNTOS = [Punto("LauV", "Laura Vicuña", 4.86, -74.05),
          Punto("JJC", "José Joaquín Casas", 4.85, -74.06),
          Punto("LaBalsa", "La Balsa", 4.87, -74.03),
          Punto("Bojacá", "Bojacá", 4.86, -74.04)]


def _filas_respuestas():
    return [md.FilaMapa("LauV", "Laura Vicuña", md.CON_CIFRA, tramo="100 o más"),
            md.FilaMapa("JJC", "José Joaquín Casas", md.CON_CIFRA, tramo="30 a 99"),
            md.FilaMapa("LaBalsa", "La Balsa", md.PEQUENA),
            md.FilaMapa("Bojacá", "Bojacá", md.SIN_FORMULARIO)]


def _filas_puntaje():
    return [md.FilaMapa("LauV", "Laura Vicuña", md.CON_CIFRA, valor=3.4, referencia=3.3),
            md.FilaMapa("JJC", "José Joaquín Casas", md.CON_CIFRA, valor=3.1, referencia=3.3),
            md.FilaMapa("LaBalsa", "La Balsa", md.PEQUENA),
            md.FilaMapa("Bojacá", "Bojacá", md.SIN_FORMULARIO)]


def _hover_total(fig) -> str:
    return " ".join(str(t) for tr in fig.data if tr.customdata is not None
                    for t in tr.customdata)


def test_hover_de_respuestas_da_tramo_y_no_numero():
    texto = mf.texto_hover(_filas_respuestas()[0], "respuestas")
    assert "100 o más" in texto and "435" not in texto


def test_hover_de_colegio_pequeno_no_lleva_cifras():
    texto = mf.texto_hover(_filas_respuestas()[2], "respuestas")
    assert cat.CIFRAS_PEQUENAS in texto
    assert not any(c.isdigit() for c in texto)


def test_hover_de_puntaje_incluye_el_municipio_si_esta_activo(monkeypatch):
    f = _filas_puntaje()[0]
    assert "Todo el municipio: 3.30" in mf.texto_hover(f, "sentirse_parte")
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_COMPARACION", False)
    assert "municipio" not in mf.texto_hover(f, "sentirse_parte")


def test_hover_sin_causa_si_el_equipo_la_apaga(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_CAUSA_SIN_CIFRA", False)
    texto = mf.texto_hover(_filas_respuestas()[2], "respuestas")
    assert cat.CIFRAS_PEQUENAS not in texto and "Sin cifras" in texto


def test_interactiva_dibuja_contorno_cifras_y_grises():
    fig = mf.figura_interactiva(_filas_respuestas(), "respuestas", PUNTOS)
    assert len(fig.data) >= 3          # contorno + con cifra + sin cifra
    assert fig.layout.map.style == "open-street-map"


def test_interactiva_sin_grises_si_el_equipo_los_apaga(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_SIN_CIFRA", False)
    fig = mf.figura_interactiva(_filas_respuestas(), "respuestas", PUNTOS)
    hover = _hover_total(fig)
    assert "Laura Vicuña" in hover
    assert "La Balsa" not in hover and "Bojacá" not in hover


def test_interactiva_sin_nombres_no_rotula(monkeypatch):
    monkeypatch.setattr(opciones, "MAPA_MOSTRAR_NOMBRES", False)
    fig = mf.figura_interactiva(_filas_respuestas(), "respuestas", PUNTOS)
    assert all("text" not in (tr.mode or "") for tr in fig.data)


def test_interactiva_de_puntaje_usa_escala_de_un_solo_tono():
    fig = mf.figura_interactiva(_filas_puntaje(), "sentirse_parte", PUNTOS)
    con = [tr for tr in fig.data if tr.marker is not None and tr.marker.showscale]
    assert len(con) == 1 and con[0].marker.colorscale is not None


def test_interactiva_ignora_filas_sin_punto():
    sin_punto = [md.FilaMapa("Fusca", "Fusca", md.CON_CIFRA, tramo="10 a 29")]
    fig = mf.figura_interactiva(sin_punto, "respuestas", PUNTOS)
    assert "Fusca" not in _hover_total(fig)


def test_estatica_se_genera_sin_red_como_png():
    fig = mf.figura_estatica(_filas_respuestas(), "respuestas", PUNTOS)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert buf.getvalue()[:8] == b"\x89PNG\r\n\x1a\n" and len(buf.getvalue()) > 5000


def test_estatica_de_puntaje_tambien_se_genera():
    fig = mf.figura_estatica(_filas_puntaje(), "apoyo_social", PUNTOS)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert len(buf.getvalue()) > 5000
