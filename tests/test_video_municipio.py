"""Video del municipio: guion fijo, mapas auditados, borrador hasta la aprobación."""
import io
import shutil
import subprocess

import pytest
from PIL import Image

from src.estudiantes import alertas_catalogo as ac
from src.estudiantes import catalog as cat
from src.geo import auditoria_mapa, colegios_geo, mapa_figura, opciones
from src.geo import video_municipio as vm
from tests.mapa_datos_sinteticos import analisis_sintetico

PROHIBIDAS = ("suicid", "muerte", "alerta", "señales", "prioridad", "desesperanza",
              "rcads", "sdq", "106", "192", "141")


def _analisis():
    return {cat.NIVEL_SECUNDARIA: analisis_sintetico()}


@pytest.fixture(scope="module")
def por_defecto():
    """Las escenas con las opciones de fábrica, calculadas una sola vez."""
    return {f: vm.construir_escenas(_analisis(), f) for f in vm.FORMATOS}


def _textos(escenas):
    return " ".join(t for e in escenas for t in e.textos).lower()


def test_el_guion_dura_entre_60_y_90_segundos(por_defecto):
    escenas = por_defecto["horizontal"]
    total = sum(e.duracion for e in escenas) - (len(escenas) - 1) * vm.T_CRUCE
    assert 60 <= total <= 90


def test_cada_escena_es_un_png_del_tamano_del_formato(por_defecto):
    for formato, (ancho, alto) in vm.FORMATOS.items():
        for e in por_defecto[formato]:
            img = Image.open(io.BytesIO(e.png))
            assert img.size == (ancho, alto) and img.format == "PNG"


def test_el_video_nunca_habla_de_alertas_malestar_ni_rutas(por_defecto):
    texto = _textos(por_defecto["horizontal"] + por_defecto["cuadrado"])
    for palabra in PROHIBIDAS:
        assert palabra not in texto, palabra


def test_las_acciones_salen_del_catalogo_y_no_de_texto_propio(por_defecto):
    texto = _textos(por_defecto["horizontal"])
    colegio = cat.MENSAJES["adulto_confianza"].accion_colegio.split(". ")[0].rstrip(".")
    assert colegio.lower() in texto
    assert cat.MENSAJES["pertenencia"].accion_municipio.lower() in texto
    assert cat.MENSAJES["apoyo_familia"].accion_municipio.lower() in texto
    assert cat.MENSAJES["pertenencia"].significa.lower() in texto


def test_sin_acciones_si_el_equipo_las_apaga(monkeypatch):
    monkeypatch.setattr(opciones, "VIDEO_ACCIONES", False)
    texto = _textos(vm.construir_escenas(_analisis(), "horizontal"))
    assert cat.MENSAJES["pertenencia"].accion_municipio.lower() not in texto


def test_hasta_que_se_aprueba_todas_las_escenas_llevan_el_sello_de_borrador(por_defecto):
    assert opciones.VIDEO_APROBADO is False
    assert all(e.sello for e in por_defecto["horizontal"] + por_defecto["cuadrado"])
    assert vm.es_borrador() is True


def test_aprobado_no_lleva_sello(monkeypatch):
    monkeypatch.setattr(opciones, "VIDEO_APROBADO", True)
    escenas = vm.construir_escenas(_analisis(), "horizontal")
    assert not any(e.sello for e in escenas) and vm.es_borrador() is False


def test_por_defecto_el_video_no_nombra_los_colegios(monkeypatch):
    visto = []
    original = mapa_figura.figura_estatica

    def espia(filas, capa, puntos, nombres=None):
        visto.append(nombres)
        return original(filas, capa, puntos, nombres=nombres)
    monkeypatch.setattr(vm.mapa_figura, "figura_estatica", espia)
    vm.construir_escenas(_analisis(), "horizontal")
    assert visto and all(n is False for n in visto)


def test_si_el_equipo_lo_pide_el_video_nombra_los_colegios(monkeypatch):
    visto = []
    original = mapa_figura.figura_estatica
    monkeypatch.setattr(opciones, "VIDEO_NOMBRES_COLEGIOS", True)
    monkeypatch.setattr(vm.mapa_figura, "figura_estatica",
                        lambda f, c, p, nombres=None: visto.append(nombres) or original(f, c, p, nombres=nombres))
    vm.construir_escenas(_analisis(), "horizontal")
    assert visto and all(n is True for n in visto)


def test_si_la_auditoria_falla_no_hay_video(monkeypatch):
    def mala(*a, **k):
        raise auditoria_mapa.AuditoriaMapa("x")
    monkeypatch.setattr(vm.auditoria_mapa, "auditar", mala)
    with pytest.raises(auditoria_mapa.AuditoriaMapa):
        vm.construir_escenas(_analisis(), "horizontal")


def test_sin_resultados_con_base_suficiente_no_hay_video():
    with pytest.raises(ValueError):
        vm.construir_escenas({}, "horizontal")


def test_las_rutas_no_salen_sin_estar_validadas_aunque_se_pidan(monkeypatch):
    monkeypatch.setattr(opciones, "VIDEO_RUTAS", True)
    monkeypatch.setattr(ac, "RUTAS_VALIDADAS", False)
    texto = _textos(vm.construir_escenas(_analisis(), "horizontal"))
    assert all(nombre.lower() not in texto for nombre, _ in cat.RUTA_ATENCION)


def test_las_rutas_salen_solo_con_las_dos_llaves(monkeypatch):
    monkeypatch.setattr(opciones, "VIDEO_RUTAS", True)
    monkeypatch.setattr(ac, "RUTAS_VALIDADAS", True)
    texto = _textos(vm.construir_escenas(_analisis(), "horizontal"))
    assert any(nombre.lower() in texto for nombre, _ in cat.RUTA_ATENCION)


def test_los_formatos_los_decide_el_equipo(monkeypatch):
    assert vm.formatos() == ["horizontal", "cuadrado"]
    monkeypatch.setattr(opciones, "VIDEO_VARIANTE_CELULAR", False)
    assert vm.formatos() == ["horizontal"]


def test_el_nombre_del_archivo_marca_el_borrador(monkeypatch):
    assert vm.nombre_archivo("horizontal").endswith("_BORRADOR.mp4")
    monkeypatch.setattr(opciones, "VIDEO_APROBADO", True)
    assert "BORRADOR" not in vm.nombre_archivo("horizontal")


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                    reason="requiere ffmpeg y ffprobe")
def test_el_mp4_sale_con_la_duracion_y_el_tamano_esperados(tmp_path):
    escenas = [vm.Escena(duracion=1.5, png=_png(1920, 1080, c), textos=[], sello=False)
               for c in ("navy", "white", "gray")]
    ruta = tmp_path / "prueba.mp4"
    vm.escribir_video(escenas, str(ruta), t_cruce=0.3)
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,codec_name,pix_fmt:format=duration", "-of", "default=nw=1",
         str(ruta)], capture_output=True, text=True, check=True).stdout
    datos = dict(l.split("=") for l in salida.split())
    assert (datos["width"], datos["height"]) == ("1920", "1080")
    assert datos["codec_name"] == "h264" and datos["pix_fmt"] == "yuv420p"
    assert abs(float(datos["duration"]) - (3 * 1.5 - 2 * 0.3)) < 0.2


def _png(ancho, alto, color):
    buf = io.BytesIO()
    Image.new("RGB", (ancho, alto), color).save(buf, "PNG")
    return buf.getvalue()


def test_el_mapa_del_video_se_dibuja_con_los_puntos_verificados():
    puntos, _ = colegios_geo.cargar_puntos()
    assert len(puntos) >= 10
